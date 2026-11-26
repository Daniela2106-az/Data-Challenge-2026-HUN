"""
dashboard/pages/presentacion.py  -  «Presentación» de la final del Data Challenge (26-nov-2026, version 2 con los comentarios de Daniela)

Doce diapositivas para presentar en 10 minutos ante el hospital, con el mismo estilo del dashboard. Nadie toca el computador: solo se pasa de
diapositiva (flechas, AvPág/RePág, espacio o el clicker). Lo demas ocurre solo (dashboard/assets/presentacion.js):
  - todo entra con una animacion escalonada; «Qué construimos» arma la cadena de modulos sola, una pieza tras otra;
  - el Simulador integral se reproduce al llegar; cuando salta una alerta se deja ver y se aplica sola la mejora (la primera vez) o se continua.
    Si se vuelve a su diapositiva desde la anterior, arranca de nuevo; si se vuelve desde la siguiente, se queda como iba;
  - las dos preguntas del asistente se «escriben» solas con respuestas reales del asistente guardadas antes (presentacion_asistente.json).

Orden (lo pidieron los organizadores: valor agregado, solidez de la metodologia, resultados y aplicabilidad en el hospital):
  0 portada · 1 el problema · 2 el cuello de botella · 3 quien espera mas · 4 que construimos y valor agregado · 5 simulador en vivo ·
  6 resultados del simulador · 7 que gana el hospital · 8 ¿y si…? · 9 por que confiar · 10 como lo usa el hospital · 11 cierre

Los cinco modulos se nombran siempre como en el dashboard: Pronosticador, Paciente en espera, Paciente en cama, Planeación de camas y Simulador integral.

REUTILIZA, no recalcula: las graficas de Resumen, Ocupación, Llegada y altas y Perfiles (llamando a sus funciones), el Simulador integral completo (su
layout, con sus callbacks) y sus modulos de resultados. Los modulos de pages/ se toman de dash.page_registry al usarlos: Dash ejecuta cada archivo de
pages/ una sola vez y una importacion propia registraria sus callbacks dos veces.

CASO EN VIVO: temporada alta (llega 10 % mas pacientes) durante 90 dias desde el 9-abr-2026. En ese caso la alerta «Faltarán camas» propone sola la
operacion optima (R7 15 % + R4 30 %). CIFRAS FIJAS (diapositivas 7, 8 y 11): src/impacto_presentacion.py (mismo caso y plazo, 400 repeticiones,
semilla fija), corrido el 26-nov-2026; todas las diapositivas citan las mismas. La validacion de la diapositiva 9 se calcula en vivo con el mismo motor (backtest ene a 9-abr-2026, entrenado hasta
dic-2025), con la serie real completa.
"""
import json
import sys
from pathlib import Path

import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from componentes import AZUL, NARANJA, PIZARRA, coma, estilo  # noqa: E402
from modo import repeticiones  # noqa: E402

dash.register_page(__name__, path="/presentacion", name="Presentación", title="Presentación - HUN", order=0.2)

CAMAS = 106
DIAS_SIM = 90                       # «90 días» en el selector del simulador (PLAZOS de pages/simulador.py): la reproduccion dura menos de un minuto
LLEGADAS_CASO = 10                  # caso en vivo: temporada alta, llega 10 % mas pacientes

# ---------------------------------------------------------------- cifras fijas (src/impacto_presentacion.py, 26-nov-2026)
# 90 dias desde el 9-abr-2026, 400 repeticiones. «sat» = % de dias con mas pacientes que las 106 camas; «faltan» = camas que faltan en promedio.
IMPACTO = {
    "hoy":         {"camas": 109.3, "sat": 59.2, "cola": 25.1, "faltan": 6.3, "ingresos": 19.36, "cap10": 124},
    "optima":      {"camas": 105.6, "sat": 45.5, "cola": 24.4, "faltan": 4.2, "ingresos": 19.37, "cap10": 120},
    "estancia_m5": {"camas": 104.8, "sat": 42.5, "cola": 23.9, "faltan": 3.9, "ingresos": 19.38, "cap10": 119},
    "alta":        {"camas": 119.3, "sat": 86.8, "cola": 28.3, "faltan": 14.0, "ingresos": 21.23, "cap10": 134},
    "alta_optima": {"camas": 115.3, "sat": 78.6, "cola": 27.5, "faltan": 10.5, "ingresos": 21.24, "cap10": 130},
    "tu_doble":    {"camas": 123.3, "sat": 92.4, "cola": 26.6, "faltan": 17.6, "ingresos": 21.07, "cap10": 138},
    # un año completo (365 dias, 1000 repeticiones), operacion normal, sin y con todas las recomendaciones medibles (R7 + R4); totales del año
    "anio_hoy":    {"camas": 112.13, "dias_sobre": 246.5, "faltan": 8.48, "cola_dias": 9229.8, "ingresos_anio": 7167.7, "llegadas_anio": 94477.4},
    "anio_todas":  {"camas": 107.40, "dias_sobre": 192.0, "faltan": 5.47, "cola_dias": 8950.3, "ingresos_anio": 7168.7, "llegadas_anio": 94477.4},
}
A, M = IMPACTO["alta"], IMPACTO["alta_optima"]                                      # el caso en vivo, sin y con la mejora
CAMAS_LIBRES = A["camas"] - M["camas"]                                             # 4,0 camas desocupadas en promedio
MENOS_FALTAN = 100 * (1 - M["faltan"] / A["faltan"])                                # 25 % menos camas faltantes
ESTANCIA_MEDIA = M["camas"] / M["ingresos"]                                         # 5,4 dias (ley de Little: camas = ingresos x estancia)
EXTRA_DIA = CAMAS_LIBRES / ESTANCIA_MEDIA                                          # ~0,7 pacientes hospitalizados mas por dia
EXTRA_CASO, EXTRA_ANIO = EXTRA_DIA * DIAS_SIM, EXTRA_DIA * 365
EXTRA_ANIO_TXT = f"~{int(round(EXTRA_ANIO, -1))}"
EXTRA_CASO_TXT = f"~{int(round(EXTRA_CASO))}"
# Qué gana el hospital en un año completo con todas las recomendaciones
YH, YT = IMPACTO["anio_hoy"], IMPACTO["anio_todas"]
ANIO_DIAS_CAMA = (YH["camas"] - YT["camas"]) * 365                                  # ~1.730 dias-cama liberados en el año
ANIO_PACIENTES = ANIO_DIAS_CAMA / ESTANCIA_MEDIA                                     # ~320 pacientes hospitalizados mas
ANIO_DIAS_SOBRE = YH["dias_sobre"] - YT["dias_sobre"]                                # ~54 dias menos con sobrecupo
ANIO_HORAS_ESPERA = (YH["cola_dias"] - YT["cola_dias"]) * 24                         # ~6.700 horas menos de espera por cama
ANIO_MENOS_FALTAN = 100 * (1 - YT["faltan"] / YH["faltan"])                          # 35 % menos camas faltantes


def _redondo(x, a):
    return f"{int(round(x / a) * a):,}".replace(",", ".")

ETAPAS = ["Problema", "Solución", "Resultados", "Confianza", "Aplicación"]
MODULOS = [("ico-forecast", "Pronosticador"), ("ico-wait", "Paciente en espera"), ("ico-stay", "Paciente en cama"),
           ("ico-bed", "Planeación de camas"), ("ico-models", "Simulador integral")]

PREGUNTAS = Path(__file__).resolve().parent.parent / "presentacion_asistente.json"


def _modulo(ruta):
    """El modulo ya cargado de una pagina (p. ej. «/simulador»), tal como lo importo Dash."""
    for p in dash.page_registry.values():
        if p["path"] == ruta:
            return sys.modules.get(p["module"])
    return None


# ---------------------------------------------------------------- piezas
def ico(nombre, clase=""):
    return html.Span(className=f"pres-ico {clase}", children=html.Span(className="nav__ico " + nombre))


def diapo(n, etapa, titulo, bajada, *contenido, clase="", auto=None):
    """Una diapositiva: rotulo de la etapa, titulo (la conclusion), una frase y el contenido."""
    attrs = {"data-n": str(n), "data-etapa": etapa or ""}
    if auto:
        attrs["data-auto"] = auto
    cab = [html.Div(etapa, className="pres-eyebrow")] if etapa else []
    cab += [html.H2(titulo, className="pres-titulo")]
    if bajada:
        cab.append(dcc.Markdown(bajada, className="pres-bajada"))
    return html.Section(className="pres-diapo " + clase, **attrs, children=[
        html.Header(cab, className="pres-cab"), html.Div(list(contenido), className="pres-cuerpo")])


def numero(valor, texto, tono="", icono=None):
    """Cifra grande con su explicacion (y un icono, si se da)."""
    cuerpo = html.Div(className="pres-num__txt", children=[html.B(valor), html.Span(texto)])
    return html.Div(className="pres-num " + tono, children=[ico(icono)] + [cuerpo] if icono else [cuerpo])


def contador(valor, decimales=0, pre="", suf=""):
    """Cifra que se cuenta sola de 0 a `valor` al entrar a la diapositiva (assets/presentacion.js, [data-contar])."""
    final = pre + (coma(valor, decimales) if decimales else f"{valor:,.0f}".replace(",", ".")) + suf
    return html.B(final, **{"data-contar": str(valor), "data-dec": str(decimales), "data-pre": pre, "data-suf": suf})


ECG = ('<svg class="pres-ecg" viewBox="0 0 1600 160" preserveAspectRatio="none"><path d="M0 100 H520 L560 100 L585 40 L610 150 L640 10 L670 120 '
       'L700 100 H1000 L1030 100 L1050 70 L1070 120 L1090 100 H1600"/></svg>')


def item(titulo, texto, icono=None):
    return html.Div(className="pres-item", children=([ico(icono)] if icono else []) + [html.Div([html.B(titulo), html.Span(texto)], className="pres-item__txt")])


def tarjeta(titulo, *hijos, clase=""):
    return html.Div(className="pres-tarjeta " + clase, children=[html.Div(titulo, className="pres-tarjeta__t") if titulo else None, *hijos])


def g(id_, alto):
    return dcc.Graph(id=id_, config={"displayModeBar": False, "displaylogo": False, "responsive": True}, style={"height": f"{alto}px"})


def fuente(texto):
    return html.P(texto, className="pres-fuente")


# ---------------------------------------------------------------- simulador embebido
def _sin_persistencia(c):
    """Recorre el layout del simulador: sin persistencia de sesion (la presentacion siempre arranca igual) y con el plazo en 6 meses."""
    if c is None or isinstance(c, (str, int, float)):
        return c
    if isinstance(c, (list, tuple)):
        return [_sin_persistencia(x) for x in c]
    if getattr(c, "persistence", None):
        c.persistence = False
    if getattr(c, "storage_type", None) == "session":
        c.storage_type = "memory"
    if getattr(c, "id", None) == "simint-plazo":
        c.value = DIAS_SIM
    if getattr(c, "id", None) == "simint-velocidad":
        c.value = 7
    if getattr(c, "id", None) == "simint-ajuste_llegadas":
        c.value = LLEGADAS_CASO
    hijos = getattr(c, "children", None)
    if hijos is not None and not isinstance(hijos, str):
        c.children = _sin_persistencia(hijos)
    return c


def _simulador():
    sim = _modulo("/simulador")
    if sim is None:
        return html.Div("El simulador no está disponible.", className="pres-aviso")
    raiz = _sin_persistencia(sim.layout())
    # se quitan el encabezado de la pagina, el texto «Qué significa» y la documentacion plegada; se queda todo lo que tiene id (los callbacks lo usan)
    raiz.children = [h for h in raiz.children if (getattr(h, "className", "") or "").split(" ")[0] not in ("page-head", "mensaje", "metodo")]
    raiz.className = "pres-sim"
    return raiz


# ---------------------------------------------------------------- las diapositivas
def d0():
    return html.Section(className="pres-diapo pres-portada", **{"data-n": "0", "data-etapa": ""}, children=[
        html.Div(className="hero__heart"),
        dcc.Markdown(ECG, dangerously_allow_html=True, className="pres-ecg-caja"),
        html.Div(className="pres-portada__izq", children=[
            html.Div(className="pres-portada__logo", children=html.Img(src=dash.get_asset_url("logo_hun.png"), alt="Hospital Universidad del Norte")),
            html.Div("Data Challenge HUN 2026 · Final", className="pres-portada__eyebrow"),
            html.H1("Menos espera por una cama: anticipar, simular y decidir", className="pres-portada__t"),
            html.P("Flujo de pacientes del Hospital Universidad del Norte", className="pres-portada__sub"),
            html.Div(className="pres-portada__equipo", children=[html.Span(n) for n in ("Daniela Amaya", "Samuel Amador", "Anthony Amaya")])]),
        html.Div(className="pres-portada__camas", children=[
            html.Div(className="pres-portada__grid", children=[html.Span(style={"--k": str(k)}) for k in range(CAMAS)] +
                     [html.Span(className="sobre", style={"--k": str(CAMAS + k)}) for k in range(8)]),
            html.Div("Un hospital que trabaja al límite de sus camas", className="pres-portada__camas-t")])])


def d1():
    return diapo(1, "Problema", "Un paciente que necesita cama espera casi un día en urgencias",
                 "Y los que más esperan, cada año esperan más.",
                 html.Div(className="pres-dos", children=[
                     html.Div(className="pres-col", children=[
                         numero("18,6 h", "espera la mitad de los pacientes, desde que llega hasta que recibe cama", icono="ico-clock"),
                         numero("73,9 h", "o más espera 1 de cada 10: más de 3 días", "malo", icono="ico-wait"),
                         numero("1 de 5", "pasa más de 48 horas sin cama", "malo", icono="ico-alert"),
                         html.Div(className="pres-nota", children=[
                             html.B("Por qué importa: "), "esperar 12 h o más se asocia a más mortalidad (de 2,5 % a 4,5 %, Singer 2011). "
                             "La guía internacional usa 4 horas como meta."])]),
                     tarjeta("Horas de espera por una cama, por año", g("pres-g1", 430),
                             html.P("Gris: el paciente típico. Azul: el que espera más que 9 de cada 10.", className="pres-leyenda"), clase="pres-col--ancha")]))


def d2():
    return diapo(2, "Problema", "El cuello de botella es la espera de cama, y no es un problema de días puntuales",
                 "Las camas se liberan tarde y cada paciente ocupa la cama más días que antes.",
                 html.Div(className="pres-dos", children=[
                     tarjeta("Las camas se liberan y se asignan por la tarde", g("pres-g2b", 280),
                             html.P("Línea: a qué hora salen las altas (pico de 15 a 17 h). Barras: a qué hora se asigna la cama. Después del pico de altas, "
                                    "las camas se siguen asignando en una segunda ola por la noche: limpiar y reasignar cada cama toma tiempo.", className="pres-leyenda"),
                             html.Div(className="pres-fila-num", children=[
                                 numero("63 %", "de las altas sale entre las 14 y las 19 h", icono="ico-clock"),
                                 numero("61 %", "de las camas se asigna en dos olas: 15–17 h y 20–23 h", icono="ico-bed"),
                                 numero("1,8 h", "tarda en reasignarse una cama liberada en la mañana", icono="ico-wait")])),
                     tarjeta("La ocupación sube porque los pacientes se quedan más", g("pres-g2a", 280),
                             html.P("Días que pasa en cama, en promedio, cada paciente hospitalizado. Debajo de cada año, cuántos se quedan más de 14 días.", className="pres-leyenda"),
                             html.Div(className="pres-fila-num", children=[
                                 numero("94 → 105", "camas ocupadas en promedio, de 2023 a 2025", icono="ico-occup"),
                                 numero("+16 %", "de estancia media: de 4,6 a 5,3 días", icono="ico-stay"),
                                 numero("~20", "ingresos a cama por día: no cambian", icono="ico-demand")]))]),
                 html.P("Ningún día tuvo una espera fuera de lo esperado: es un problema crónico del proceso, no de días malos.", className="pres-remate"))


def d3():
    quien = [("ico-profiles", "Mujeres: 22,3 h", "frente a 14,3 h de los hombres, +27 % con todo lo demás igual. Lo queremos revisar con el hospital."),
             ("ico-group", "Adultos desde 30 años: 24–27 h", "los niños de 0 a 4 años esperan 7,8 h."),
             ("ico-clock", "Quien llega en la tarde: ~25 h", "quien llega de madrugada, 12–15 h."),
             ("ico-demand", "Quien entra por urgencias: 20,8 h", "por «Treatment urgency», 9,8 h; por consulta, 11,3 h."),
             ("ico-dx", "Musculoesquelético, renal y cáncer: 29–39 h", "cardiovascular, neurológico y respiratorio: 9–13 h.")]
    return diapo(3, "Problema", "La espera depende de quién es el paciente",
                 "Mediana de horas desde que llega hasta que recibe cama. El día de la semana y los festivos casi no la cambian.",
                 html.Div(className="pres-dos", children=[
                     html.Div(className="pres-col", children=[html.Div(className="pres-lista-num", children=[item(b, c, a) for a, b, c in quien])]),
                     tarjeta("Espera de cama según la edad y la forma de llegada (horas, mediana)", g("pres-g3", 470),
                             html.P("Entre más oscuro, más espera. Los adultos que llegan por urgencias son los que más esperan.", className="pres-leyenda"), clase="pres-col--ancha")]))


def d4():
    pasos = [("ico-data", "Datos del hospital", "2023 a abril de 2026, explorados y limpiados a fondo", ""),
             ("ico-forecast", "Pronosticador", "¿Cuántos pacientes llegarán? Con la temporada del año (dengue como marcador)", "Módulo 1"),
             ("ico-wait", "Paciente en espera", "¿Cuándo recibirá cama este paciente?", "Módulo 2"),
             ("ico-stay", "Paciente en cama", "¿Qué día es más probable su alta?", "Módulo 3"),
             ("ico-bed", "Planeación de camas", "¿Cuántas camas se ocuparán y qué tan seguido se superan las 106?", "Módulo 4"),
             ("ico-models", "Simulador integral", "Junta los cuatro: llegan, esperan, ocupan cama y salen, día a día. Avisa y propone la mejora", "Módulo 5")]
    flujo = []
    for i, (icono, t, d, rot) in enumerate(pasos):
        if i:
            flujo.append(html.Div(html.Span(className="pres-flecha__l"), className="pres-flecha pres-frag"))
        flujo.append(html.Div(className="pres-paso pres-frag" + (" pres-paso--final" if i == len(pasos) - 1 else "") + (" pres-paso--datos" if i == 0 else ""), children=[
            html.Div(rot, className="pres-paso__rot") if rot else None, ico(icono, "pres-ico--grande"), html.B(t), html.Span(d)]))
    valor = [("ico-models", "Cinco módulos conectados", "todos alimentan al simulador"),
             ("ico-alert", "Avisa y propone", "alerta → recomendación → mejora medida"),
             ("ico-compare", "Probado con el futuro", "validado en meses que no conocía"),
             ("ico-period", "Proceso automatizable", "datos nuevos: limpia, recalcula y compara")]
    return diapo(4, "Solución", "Construimos cinco módulos que van del dato a la decisión",
                 "Cada módulo responde una pregunta del hospital, y el Simulador integral los junta.",
                 html.Div(className="pres-flujo", children=flujo),
                 html.Div(className="pres-valor pres-frag", children=[
                     html.Div([ico("ico-summary"), "Valor agregado"], className="pres-valor__t"),
                     html.Div(className="pres-valor__fila", children=[
                         html.Div(className="pres-valor__c", children=[ico(a, "pres-ico--grande"), html.B(b), html.Span(c)]) for a, b, c in valor])]),
                 auto="secuencia")


def d5():
    caso = [("ico-season", "Periodo", "3 meses desde el 9 de abril de 2026"),
            ("ico-demand", "Situación", f"temporada alta: llega {LLEGADAS_CASO} % más pacientes, como en una temporada de infecciones respiratorias"),
            ("ico-group", "Pacientes", "todos los perfiles, con la mezcla real de 2025 (edad y forma de llegada)"),
            ("ico-alert", "Alerta", "«Faltarán camas»: propone revisar las estancias largas (15 % menos) y adelantar el 30 % de las altas de la tarde"),
            ("ico-occup", "Qué se ve", "arriba, llegadas y altas; en el medio, camas ocupadas frente a las 106; abajo, pacientes esperando cama. "
                                       "En gris punteado, cómo habría seguido sin la mejora")]
    return diapo(5, "Resultados", "Simulador integral: una temporada alta, en vivo",
                 "Los cinco módulos juntos: el hospital corre día a día, salta la alerta y se aplica la mejora de nuestras recomendaciones.",
                 html.Div(className="pres-sim-fila", children=[
                     html.Div(className="pres-caso", children=[html.Div("El caso", className="pres-caso__t"),
                                                               *[item(b, c, a) for a, b, c in caso]]),
                     html.Div(className="pres-ajustar", children=html.Div(className="pres-sim-caja", children=[
                         _simulador(),
                         html.Div(id="pres-previa", className="pres-previa", children=dcc.Graph(
                             id="pres-previa-graf", config={"displayModeBar": False, "responsive": True}, style={"height": "720px"}))]))]),
                 html.Div(id="pres-sim-ganancia", className="pres-notifs", children=[
                     html.Div(className="pres-notif", children=[ico(a, "pres-ico--blanco"), html.Div([html.B(b), html.Span(c)])]) for a, b, c in (
                         ("ico-bed", f"{coma(CAMAS_LIBRES, 1)} camas desocupadas cada día", "con la mejora, sin adquirir camas nuevas"),
                         ("ico-patient", f"{EXTRA_CASO_TXT} pacientes hospitalizados más", "en estos 3 meses de temporada alta"),
                         ("ico-occup", f"{coma(MENOS_FALTAN, 0)} % menos camas faltantes", f"de {coma(A['faltan'], 1)} a {coma(M['faltan'], 1)} en promedio"),
                         ("ico-alert", f"{coma(100 * (1 - M['sat'] / A['sat']), 0)} % menos días con sobrecupo", f"de {coma(A['sat'], 0)} % a {coma(M['sat'], 0)} % de los días"))]),
                 html.Div(id="pres-cursor", className="pres-cursor"), clase="pres-diapo--sim", auto="simulador")


def d6():
    return diapo(6, "Resultados", "Qué muestra la simulación: camas, estancias largas y quién espera más",
                 "Los 3 meses de temporada alta simulados, con la mejora aplicada.",
                 html.Div(id="pres-sim-resultados", className="pres-sim-res", children=html.P(
                     "Los resultados aparecen cuando el simulador de la diapositiva anterior termina de calcular.", className="pres-aviso")))


def d7():
    filas = [("ico-stay", "Revisión semanal de estancias largas", "15 % menos de duración en las estancias de más de 14 días", "Desocupa las camas: casi toda la ganancia viene de aquí"),
             ("ico-clock", "Altas antes del mediodía", "30 % de las altas de la tarde pasa a la mañana", "Menos pacientes esperando cama a la vez"),
             ("ico-recs", "Reunión diaria de camas y alerta a las 48 h", "Lo que permite actuar a tiempo sobre lo anterior", "En otros hospitales, la espera bajó de 16,6 a 9,5 h (Alotaibi 2021)")]
    return diapo(7, "Resultados", "Qué gana el hospital en un año, con las mismas camas",
                 "Un año completo de operación normal, sin y con todas nuestras recomendaciones aplicadas.",
                 html.Div(className="pres-ganancias", children=[
                     html.Div(className="pres-gran", children=[ico("ico-patient", "pres-ico--blanco"), html.B(f"~{_redondo(ANIO_PACIENTES, 10)}"),
                                                               html.Span("pacientes más hospitalizados al año"),
                                                               html.Small("capacidad extra para quienes necesitan cama")]),
                     html.Div(className="pres-gran", children=[ico("ico-bed", "pres-ico--blanco"), html.B(f"≈{int(round(YH['camas'] - YT['camas']))}"),
                                                               html.Span("camas ganadas, sin adquirirlas"),
                                                               html.Small(f"{coma(YH['camas'] - YT['camas'], 1)} camas libres más cada día")]),
                     html.Div(className="pres-gran pres-gran--claro", children=[ico("ico-wait"), html.B(f"~{_redondo(ANIO_HORAS_ESPERA, 100)}"),
                                                                                html.Span("horas menos esperando cama"),
                                                                                html.Small(f"entre los ~{_redondo(YT['ingresos_anio'], 100)} pacientes que la necesitan al año")]),
                     html.Div(className="pres-gran pres-gran--claro", children=[ico("ico-occup"), html.B(f"−{coma(ANIO_MENOS_FALTAN, 0)} %"),
                                                                                html.Span("camas faltantes"),
                                                                                html.Small(f"de {coma(YH['faltan'], 1)} a {coma(YT['faltan'], 1)} en promedio cada día")])]),
                 html.Div(className="pres-recs", children=[
                     html.Div(className="pres-rec", children=[ico(a, "pres-ico--grande"), html.Div([html.B(b), html.Span(c), html.Em(d)], className="pres-rec__txt")])
                     for a, b, c, d in filas]),
                 html.Div(className="pres-nota pres-nota--sim", children=[ico("ico-models"), html.Span([
                     html.B("Antes de invertir: "), "el Simulador integral muestra escenarios futuros antes de comprar camas, contratar personal o cambiar procesos."])]),
                 fuente(f"Simulador integral, 365 días desde el 9-abr-2026, 1.000 repeticiones; mejoras medidas: estancias largas −15 % y 30 % de altas a la mañana. "
                        f"Pacientes más = días-cama liberados ÷ estancia media ({coma(ESTANCIA_MEDIA, 1)} días): es una aproximación."))


def d8():
    h, o = IMPACTO["hoy"], IMPACTO["optima"]
    pasos = [("ico-forecast", "1. Pronosticador", "anticipa cuántos pacientes llegarán en la temporada"),
             ("ico-wait", "2. Paciente en espera y Paciente en cama", "estiman cuánto esperará y cuánto se quedará cada paciente: el simulador usa esos mismos tiempos reales"),
             ("ico-models", "3. Planeación de camas y Simulador integral", "calculan cuántas camas faltarán y prueban la mejora antes de aplicarla"),
             ("ico-recs", "4. Se aplican las recomendaciones antes", "y el hospital llega preparado a la temporada")]
    return diapo(8, "Resultados", "Prepararse antes: si viene una temporada alta, el simulador dice cuántas camas faltarán",
                 "Camas que faltarían en promedio cada día durante 3 meses, sin y con nuestras recomendaciones.",
                 html.Div(className="pres-dos", children=[
                     tarjeta(None, g("pres-g8", 540), clase="pres-col--ancha"),
                     html.Div(className="pres-col", children=[
                         html.Div(className="pres-lista-num", children=[item(b, c, a) for a, b, c in pasos]),
                         html.Div(className="pres-nota", children=[
                             html.B("Para que el sobrecupo sea raro "), f"(1 de cada 10 días) harían falta {h['cap10']} camas en operación normal y {A['cap10']} en temporada alta; "
                             f"con nuestras recomendaciones, {o['cap10']} y {M['cap10']}. Antes de pensar en camas nuevas, conviene acortar las estancias largas."])])]))


def d9():
    def caja(icono, nombre, texto, id_):
        return html.Div(className="pres-valida", children=[
            html.Div(className="pres-valida__cab", children=[ico(icono), html.Div([html.B(nombre), html.Span(texto)])]), g(id_, 190)])
    return diapo(9, "Confianza", "Los cinco módulos se probaron contra el futuro",
                 "Lo que cada módulo estimó, frente a lo que de verdad pasó en meses que no conocía.",
                 html.Div(className="pres-valida-grid", children=[
                     caja("ico-forecast", "Pronosticador", "pacientes que llegarían cada día, pronosticados con una semana de anticipación: error de ~8 %", "pres-v1"),
                     caja("ico-wait", "Paciente en espera", "si dice «la mitad recibe cama antes de X horas», ¿pasó así? 5.430 pacientes nuevos: casi exacto", "pres-v2"),
                     caja("ico-stay", "Paciente en cama", "si dice «la mitad sale de alta antes de X días», ¿pasó así? 3.900 pacientes nuevos: casi exacto", "pres-v3"),
                     caja("ico-bed", "Planeación de camas", "camas ocupadas reales dentro de la banda que dio la planeación: el 78,8 % de los días", "pres-v4"),
                     caja("ico-models", "Simulador integral", "pacientes esperando cama cada día: lo que simuló frente a lo que pasó (25 frente a 27 en promedio)", "pres-v5")]))


def d10():
    uso = [("ico-clock", "Cada mañana", "Reunión de camas", "El Pronosticador y las alertas dicen si el día viene congestionado: la alerta de las 12 h detecta 13 de cada 15 días."),
           ("ico-stay", "Cada semana", "Coordinación de altas", "Paciente en cama y la lista de estancias largas dicen a quién revisar primero."),
           ("ico-models", "Antes de cada temporada", "Dirección del hospital", "El Simulador integral prueba escenarios: cuántas camas harán falta y qué mejora aplicar.")]
    return diapo(10, "Aplicación", "Cómo lo usaría el hospital en su día a día",
                 "Se conecta a la base del hospital: con datos nuevos se limpian y recalculan los cinco módulos (con 2027 se planea 2028).",
                 html.Div(className="pres-dos", children=[
                     html.Div(className="pres-col", children=[
                         html.Div(className="pres-uso", children=[
                             html.Div(className="pres-uso__f", children=[ico(a, "pres-ico--grande"), html.Div(className="pres-uso__txt", children=[
                                 html.Div([html.B(b), html.Span(" · " + c)], className="pres-uso__cab"), html.Span(d)])]) for a, b, c, d in uso]),
                         html.Div(className="pres-nota", children=[html.B("Son prácticas permanentes, no solo para el periodo simulado: "),
                                                                   "7 recomendaciones que se aplican siempre, y el sistema mide cada mes si están funcionando para ir mejorando poco a poco."]),
                         html.Div(className="pres-nota pres-nota--pedido", children=[
                             html.B("Lo que pedimos: "), "registrar el triage y el servicio al llegar. Con eso, Paciente en espera duplica su mejora (de 8,4 % a 16,9 %)."])]),
                     html.Div(className="pres-col pres-col--ancha", children=[
                         html.Div(className="pres-chat asis-scope", children=[
                             html.Div(className="pres-chat__cab", children=[ico("ico-chat"), html.B("Asistente de flujo HUN"),
                                                                             html.Span("preguntas en lenguaje natural sobre el análisis", className="pres-chat__sub")]),
                             html.Div(id="pres-chat-log", className="asis-log pres-chat__log")])])]),
                 auto="asistente")


def d11():
    """Cierre: el mismo tablero de 106 camas de la portada, ahora vaciando el desborde y liberando camas (en verde), junto a la frase final.
    Ilustrativo, sin cifras: las cifras ya se dijeron en «Qué gana el hospital»."""
    verbos = [("ico-forecast", "Anticipar", "cuántos pacientes llegarán"), ("ico-models", "Simular", "qué pasará en el hospital"),
              ("ico-recs", "Decidir", "qué hacer antes de que pase")]
    camas = ([html.Span(style={"--k": str(k)}) for k in range(CAMAS - 4)] +
             [html.Span(className="libre", style={"--k": str(k)}) for k in range(4)] +
             [html.Span(className="sobre", style={"--k": str(k)}) for k in range(8)])
    return html.Section(className="pres-diapo pres-cierre-final", **{"data-n": "11", "data-etapa": ""}, children=[
        html.Div(className="hero__heart"),
        dcc.Markdown(ECG, dangerously_allow_html=True, className="pres-ecg-caja"),
        html.Div(className="pres-cierre-final__izq", children=[
            html.H2("Más que faltar camas, falta liberarlas, asignarlas y desocuparlas a tiempo", className="pres-cierre-final__t"),
            html.Div(className="pres-cierre-final__verbos", children=[
                html.Div(className="pres-verbo", style={"--v": str(k)}, children=[html.Span(className="nav__ico " + a), html.B(b), html.Span(c)])
                for k, (a, b, c) in enumerate(verbos)]),
            html.Div("Gracias", className="pres-cierre-final__gracias")]),
        html.Div(className="pres-portada__camas pres-cierre-final__camas", children=[
            html.Div(className="pres-portada__grid", children=camas),
            html.Div("El mismo hospital, preparado antes de que pase", className="pres-portada__camas-t")])])


def _preguntas():
    try:
        return json.loads(PREGUNTAS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def layout(**_parametros):          # Dash pasa aqui los parametros de la direccion (p. ej. ?diapo=5, que usa presentacion.js para ensayar)
    diapos = [d0(), d1(), d2(), d3(), d4(), d5(), d6(), d7(), d8(), d9(), d10(), d11()]
    return html.Div(id="pres-raiz", className="pres", **{"data-preguntas": json.dumps(_preguntas(), ensure_ascii=False)}, children=[
        html.Div(className="pres-escenario", id="pres-escenario", children=[
            html.Div(className="pres-lienzo", id="pres-lienzo", children=[
                html.Div(className="pres-etapas", children=[html.Span(e, className="pres-etapa", **{"data-etapa": e}) for e in ETAPAS]),
                *diapos,
                html.Div(className="pres-pie", children=[html.Span("Data Challenge HUN 2026"), html.Span(id="pres-contador", className="pres-contador")])])]),
        html.Div(className="pres-mandos", children=[
            html.Button("←", id="pres-ant", className="pres-mando", title="Anterior (←)"),
            html.Button("→", id="pres-sig", className="pres-mando", title="Siguiente (→, espacio o AvPág)"),
            html.Button([html.Span(className="nav__ico ico-present"), "Pantalla completa"], id="pres-completa", className="pres-mando pres-mando--completa",
                        title="Pantalla completa (F)")]),
    ])


# ---------------------------------------------------------------- graficas
@callback(Output("pres-g1", "figure"), Output("pres-g2a", "figure"), Output("pres-g2b", "figure"), Output("pres-g3", "figure"), Output("pres-g8", "figure"),
          Input("theme-store", "data"))
def figuras(tema):
    vacio = go.Figure()
    res, ocu, alt, per = (_modulo(r) for r in ("/resumen", "/ocupacion", "/altas", "/perfiles"))
    g1 = res.espera(tema) if res else vacio
    g2a = ocu.actualizar("mes", tema)[0] if ocu else vacio
    g2b = alt.actualizar("Todos", tema)[1] if alt else vacio
    esp, est = _modulo("/espera"), _modulo("/estancia")
    from componentes import leer
    cubo = leer("espera_cubo.csv", dtype={"anio": str})
    g3 = esp.figura_quien(cubo, "Todos", tema)[1] if esp is not None and cubo is not None else vacio
    g2a = _estancia_por_anio(est, tema) if est else g2a
    for f in (g1, g2a, g2b, g3):
        f.update_layout(font_size=15)
    g3.update_layout(font_size=18)
    g3.update_traces(textfont_size=24)
    return g1, g2a, g2b, g3, _escenarios(tema)


def _estancia_por_anio(est, tema):
    """Estancia media por año y % de estancias de mas de 14 dias (las cifras de la pagina «Estancias largas», est.POR_ANIO)."""
    anios = [str(a) for a, *_ in est.POR_ANIO]
    media = [m for _, m, _ in est.POR_ANIO]
    fig = go.Figure(go.Bar(x=[f"{a}<br><span style='font-size:13px'>{coma(pc, 1)} % más de 14 días</span>" for a, (_, _, pc) in zip(anios, est.POR_ANIO)], y=media,
                           marker_color=[PIZARRA, "#5b8fc4", AZUL], text=[f"{coma(m, 1)} días" for m in media], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y:.2f} días en promedio<extra></extra>"))
    estilo(fig, tema)
    fig.update_yaxes(range=[0, max(media) * 1.25], ticksuffix=" d")
    fig.update_layout(bargap=0.45, margin=dict(l=44, r=10, t=10, b=60))
    return fig


def _escenarios(tema):
    cats = ["Operación normal", f"Temporada alta (+{LLEGADAS_CASO} % llegadas)"]
    sin, con = [IMPACTO["hoy"]["faltan"], A["faltan"]], [IMPACTO["optima"]["faltan"], M["faltan"]]
    fig = go.Figure([go.Bar(x=cats, y=sin, name="Sin recomendaciones", marker_color=NARANJA, text=[f"{coma(v, 1)} camas" for v in sin], textposition="outside", cliponaxis=False),
                     go.Bar(x=cats, y=con, name="Con nuestras recomendaciones", marker_color=AZUL, text=[f"{coma(v, 1)} camas" for v in con], textposition="outside", cliponaxis=False)])
    estilo(fig, tema, leyenda=True)
    fig.update_yaxes(range=[0, max(sin) * 1.25], title_text="Camas que faltan en promedio")
    fig.update_layout(font_size=19, barmode="group", bargap=0.3, bargroupgap=0.08, margin=dict(l=70, r=20, t=50, b=40))
    return fig


# validacion del simulador: se calcula una vez por proceso y se guarda (tarda ~1 s en un computador)
_BT = {}


def _backtest():
    if "d" not in _BT:
        import simulador_integral as si
        dias = (pd.Timestamp("2026-04-09") - pd.Timestamp(si.BACKTEST_CORTE)).days
        fechas, out, _info = si.simular_integral(si.BACKTEST_CORTE, dias, n_rep=repeticiones(300))
        d = pd.DataFrame({"fecha": fechas})
        for s, real in (("total", si.scm.ocup_d["mean"]), ("cola", si.COLA_REAL_D)):
            r = real.reindex(fechas).copy()
            d[f"{s}_real"] = r.values
            for p in (10, 50, 90):
                d[f"{s}_p{p}"] = np.percentile(out[s], p, axis=0)
        _BT["d"] = d
    return _BT["d"]


# Validacion de cada modulo con datos que no conocia (documento final 6.1, 6.4, 6.5 y 6.9).
# Paciente en espera: % de pacientes que recibio cama antes de cada percentil estimado (prueba jul-2025 a 9-abr-2026, 5.430 estancias, al llegar;
# resultados/tablas/calibracion_corte_paso3.csv, p90 calibrado). Si el estimador acierta, el % real coincide con el percentil.
CALIBRACION_ESPERA = [("1 de cada 4", 25, 26.8), ("La mitad", 50, 52.5), ("3 de cada 4", 75, 74.9), ("9 de cada 10", 90, 91.9)]
# Paciente en cama: lo mismo con el alta (prueba jul-2025 a 9-ene-2026, 3.900 estancias, al asignarse la cama; src/comparar_estimadores_estancia.py,
# resultados/tablas/comparacion_estimadores_estancia.csv, corrido el 26-nov-2026).
CALIBRACION_ESTANCIA = [("1 de cada 4", 25, 24.3), ("La mitad", 50, 48.4), ("3 de cada 4", 75, 73.7), ("9 de cada 10", 90, 88.8)]
_BT_CAMAS = {}


def _backtest_camas():
    """Prueba retrospectiva del motor de Planeación de camas: entrenado hasta dic-2025, simula ene a 9-abr-2026 y se compara con lo real."""
    if "d" not in _BT_CAMAS:
        import simulacion_camas_montecarlo as scm
        dias = (pd.Timestamp("2026-04-09") - pd.Timestamp(scm.BACKTEST_CORTE)).days
        fechas, censos = scm.simular(scm.serie_ingresos, scm.BACKTEST_CORTE, dias, n_rep=repeticiones(300))
        real = scm.ocup_d["mean"].reindex(fechas).copy()
        t = censos["total"]
        _BT_CAMAS["d"] = pd.DataFrame({"fecha": fechas, "real": real.values, "p10": np.percentile(t, 10, axis=0),
                                       "p50": np.percentile(t, 50, axis=0), "p90": np.percentile(t, 90, axis=0)})
    return _BT_CAMAS["d"]


def _chica(fig, tema, leyenda=False):
    estilo(fig, tema, leyenda=leyenda)
    fig.update_layout(title=None, font_size=14, margin=dict(l=44, r=10, t=30 if leyenda else 8, b=30), legend=dict(y=1.2, font_size=13))
    return fig


def _banda_y_real(x, p10, p90, real, sim, nombre_real, nombre_banda, tema):
    fig = go.Figure([go.Scatter(x=x, y=p90, line=dict(width=0), hoverinfo="skip", showlegend=False),
                     go.Scatter(x=x, y=p10, line=dict(width=0), fill="tonexty", fillcolor="rgba(235,104,52,0.18)", name=nombre_banda)])
    if sim is not None:
        fig.add_trace(go.Scatter(x=x, y=sim, name="Simulado", line=dict(color=NARANJA, width=2.4, dash="dot")))
    fig.add_trace(go.Scatter(x=x, y=real, name=nombre_real, line=dict(color=AZUL, width=2.4), connectgaps=True))
    _chica(fig, tema, True).update_xaxes(tickformat="%b", dtick="M1")
    return fig


def _calibracion(datos, tema):
    """Barras de lo que el estimador dijo (percentil) frente a lo que de verdad paso (% de pacientes por debajo)."""
    cats = [c for c, *_ in datos]
    fig = go.Figure([go.Bar(x=cats, y=[e for _, e, _ in datos], name="Lo que estimó", marker_color=NARANJA,
                            text=[f"{e} %" for _, e, _ in datos], textposition="outside", cliponaxis=False),
                     go.Bar(x=cats, y=[r for *_, r in datos], name="Lo que pasó", marker_color=AZUL,
                            text=[f"{coma(r, 1)} %" for *_, r in datos], textposition="outside", cliponaxis=False)])
    _chica(fig, tema, True).update_yaxes(range=[0, 115], ticksuffix=" %")
    fig.update_layout(barmode="group", bargap=0.3)
    return fig


@callback(Output("pres-v1", "figure"), Output("pres-v2", "figure"), Output("pres-v3", "figure"), Output("pres-v4", "figure"), Output("pres-v5", "figure"),
          Input("theme-store", "data"))
def validacion(tema):
    vacio = go.Figure()
    pron = _modulo("/pronostico")
    v1 = vacio
    if pron is not None:
        bt = pron.BT["llegadas_con_atencion"]
        bt = bt[(bt.lead == 7) & (bt.fecha >= "2025-10-01")].sort_values("fecha")
        v1 = go.Figure([go.Scatter(x=bt.fecha, y=bt.real, name="Lo que llegó", line=dict(color=AZUL, width=2.2)),
                        go.Scatter(x=bt.fecha, y=bt.pronostico, name="Lo que pronosticó", line=dict(color=NARANJA, width=2.2, dash="dot"))])
        _chica(v1, tema, True).update_xaxes(tickformat="%b", dtick="M1")
    v2, v3 = _calibracion(CALIBRACION_ESPERA, tema), _calibracion(CALIBRACION_ESTANCIA, tema)
    v4 = v5 = vacio
    try:
        d = _backtest_camas()
        v4 = _banda_y_real(d.fecha, d.p10, d.p90, d.real, None, "Camas ocupadas reales", "Banda de la planeación", tema)
    except Exception:
        pass
    try:
        d = _backtest()
        v5 = _banda_y_real(d.fecha, d.cola_p10, d.cola_p90, d.cola_real, d.cola_p50, "Lo que pasó", "Rango simulado", tema)
    except Exception:
        pass
    return v1, v2, v3, v4, v5


# ---------------------------------------------------------------- resultados del simulador (diapositiva 6): la misma corrida que se vio correr
@callback(Output("pres-sim-resultados", "children"), Input("simint-datos", "data"), State("theme-store", "data"), prevent_initial_call=True)
def resultados_simulacion(data, tema):
    sim = _modulo("/simulador")
    if not data or sim is None or "composicion" not in data or not data.get("dist"):
        return dash.no_update
    n = len(data["fechas"])
    perfiles, dist = data["perfiles"], data["dist"]
    ad, ni = float(np.mean(data["adultos_p50"])), float(np.mean(data["ninos_p50"]))
    antes = data.get("sinmej_total_p50")
    con = np.asarray(data["total_p50"], dtype=float)
    lineas = []
    if antes:
        antes = np.asarray(antes, dtype=float)
        lineas.append(("ico-bed", f"Camas: con la mejora se desocupan en promedio {coma(CAMAS_LIBRES, 1)} camas cada día. "
                                  "El tablero muestra la ocupación promedio; en rojo, cuando las camas se sobresaturan."))
    else:
        lineas.append(("ico-bed", "Camas: el tablero muestra la ocupación promedio; en rojo, cuando las camas se sobresaturan."))
    lineas += [("ico-stay", "Estancia: entre más edad, más días en cama. Las estancias largas son 3 veces más frecuentes desde los 75 años; "
                            "por eso la revisión semanal empieza por ellos."),
               ("ico-profiles", "Quién espera más: los adultos de 30 a 59 años y las mujeres; los niños pequeños son los que menos esperan.")]
    return [
        html.Div(className="pres-tres", children=[
            html.Div(className="pres-modulo", children=[sim.modulo_tablero_camas(ad, ni)]),
            html.Div(className="pres-modulo", children=[_estancia_media_por_edad(sim, dist, perfiles, n, tema)]),
            html.Div(className="pres-modulo", children=[_ranking_espera(sim, dist, perfiles, n, tema)])]),
        html.Div(className="pres-lineas", children=[html.Div([ico(a), html.Span(t)], className="pres-linea") for a, t in lineas])]


def _estancia_media_por_edad(sim, dist, perfiles, n, tema):
    """Dias en cama en promedio por grupo de edad, en la corrida que se vio (mismo calculo que el carrusel «Estancia en cama» del simulador)."""
    suma = np.asarray(dist["estancia_suma"], dtype=float)[:n].sum(axis=0)
    cuenta = np.asarray(dist["estancia_total"], dtype=float)[:n].sum(axis=0)
    edad, _r, _s = sim._medias_por_dimension(suma, cuenta, perfiles)
    cats = [e for e in sim.EDAD_ORDEN if e in edad]
    vals = [edad[c] / 24 for c in cats]
    fig = go.Figure(go.Bar(x=cats, y=vals, marker_color=[sim.EDAD_COLORES.get(c, sim.GRIS) for c in cats], text=[f"{coma(v, 1)} d" for v in vals],
                           textposition="outside", cliponaxis=False, hovertemplate="%{x} años: %{y:.1f} días<extra></extra>"))
    estilo(fig, tema).update_yaxes(range=[0, max(vals) * 1.25], ticksuffix=" d")
    fig.update_layout(font_size=16, margin=dict(l=44, r=10, t=10, b=34))
    return html.Div(className="simint-radio__modulo", children=[
        html.Div("Días en cama en promedio, por edad", className="simint-radio__modulo-titulo"),
        dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True}, style={"height": "400px"})])


def _ranking_espera(sim, dist, perfiles, n, tema):
    """El modulo «Perfiles que más esperan» del simulador, mas grande (mismo calculo: espera media de cada perfil edad x forma de llegada)."""
    suma = np.asarray(dist["espera_suma"], dtype=float)[:n].sum(axis=(0, 2))
    cuenta = np.asarray(dist["espera_cuenta"], dtype=float)[:n].sum(axis=(0, 2))
    filas = sorted([(gr, r, suma[i] / cuenta[i]) for i, (gr, r) in enumerate(perfiles) if cuenta[i] >= 5], key=lambda x: x[2], reverse=True)[:7][::-1]
    fig = go.Figure(go.Bar(x=[v for *_, v in filas], y=[f"{gr} años · {sim.RUTA_ABREV.get(r, r)}" for gr, r, _ in filas], orientation="h",
                           marker_color=[sim.EDAD_COLORES.get(gr, sim.GRIS) for gr, *_ in filas], text=[f"{v:.0f} h" for *_, v in filas],
                           textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x:.1f} h<extra></extra>"))
    estilo(fig, tema).update_xaxes(ticksuffix=" h", rangemode="tozero", showgrid=True)
    fig.update_yaxes(showgrid=False)
    fig.update_layout(font_size=16, margin=dict(l=10, r=40, t=10, b=30), bargap=0.3)
    fig.update_yaxes(automargin=True)
    return html.Div(className="simint-radio__modulo", children=[
        html.Div("Perfiles que más esperan cama (horas en promedio)", className="simint-radio__modulo-titulo"),
        html.Div("URG = urgencias · TU = Treatment urgency · AMB = consulta", className="pres-leyenda"),
        dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True}, style={"height": "380px"})])


# ---------------------------------------------------------------- vista previa del simulador (diapositiva 5)
# Antes de pulsar, encima del simulador se ve el resultado completo del caso (sin la mejora), quieto, para explicar las tres graficas. Es la misma
# figura del simulador (su funcion mostrar() con la corrida entera); al pulsar, se oculta y el simulador corre desde cero. Se guarda en memoria:
# es la misma corrida cada vez (semilla fija).
_PREVIA = {}


@callback(Output("pres-previa-graf", "figure"), Input("theme-store", "data"))
def vista_previa(tema):
    sim = _modulo("/simulador")
    if sim is None:
        return go.Figure()
    if "d" not in _PREVIA:
        ids = [{"type": "simint-caso", "caso": k} for k in sim.MODELOS_FIJOS]
        data, _nota = sim._ejecutar(DIAS_SIM, LLEGADAS_CASO, 0, 0, 0, 0, 0, ["si"], [0] * len(ids), ids)
        _PREVIA["d"], _ = sim._sacar_pacientes(data)
    return sim.mostrar(_PREVIA["d"], CAMAS, "todo", 7, [], None, tema)[0]
