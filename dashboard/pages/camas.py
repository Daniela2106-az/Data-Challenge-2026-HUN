"""
dashboard/pages/camas.py  -  pagina del dashboard multipagina
"¿Cuántos pacientes se quedarán sin cama?": el unico de los tres piezas (paciente / perfiles / camas) que es un
"que pasaria si": el usuario cambia un supuesto sobre el futuro (mas ingresos, menos estancia, otra mezcla de
perfiles) y ve como reacciona el hospital completo. No describe un paciente (eso es pages/paciente.py) ni lee
una tabla historica fija (eso es pages/perfiles.py).

REUTILIZA POR COMPLETO el motor de A5 (src/simulacion_camas_montecarlo.py): simular() y curva_capacidad(), sin
tocar su codigo. Desde el 10-nov ese archivo separa con `if __name__ == "__main__":` el backtest/escenarios
(solo corren al ejecutarlo como script) de la parte esencial, asi que importarlo aqui solo paga el costo de
cargar los datos y construir el bootstrap (~1-2 s).

REDISEÑO (14-nov-2026), con una critica honesta del enfoque original:
  - **Titulo**: "¿cuando se llenan las 106 camas?" no es una pregunta real para el hospital -- los datos
    (docs/modelo_camas.md, docs/saturacion_y_espera.md) muestran que el hospital opera casi siempre al borde o
    por encima de su capacidad (65,4 % de los dias-repeticion la supera). Lo que de verdad le sirve al hospital
    es saber CUANTOS pacientes quedarian sin cama (en espera) en ese escenario -- el cuello de botella real.
  - **Filtros**: "¿Hasta cuando quieres ver?" (igual a pronostico.py) alimenta el horizonte de `scm.simular`;
    "¿Que quieres ver?" (igual a pronostico.py, icono + info_badge) reemplaza el RadioItems simple de
    niños/adultos/total.
  - **Dropdown "ver desde este punto" RETIRADO (medido, no solo intuido):** no media lo que decia. Las 5 fechas
    probadas (pct_sobre_umbral de 0,1 % a 20,8 %) dieron una ocupacion casi plana (114,7-116,1 camas) porque la
    variacion real venia de reanclar `escenario="historico"` a la ventana de 364 dias de OTRO año calendario,
    no del tamaño del pico. El slider de ingresos (+-10 %) mueve el resultado ~2,2x mas. Se deja fijo en
    `scm.ULTIMO_CONFIABLE` (el unico corte que de verdad corresponde a "hoy").
  - **Filtro de sexo probado y DESCARTADO:** 42 celdas (edad x sexo x ruta) en vez de las 21 actuales si tienen
    señal real (11 de 19 celdas comparables con brecha de mediana > 10 %, media 13,8 %), pero 5 de 42 celdas
    quedan con menos de 30 casos y el ruido de suavizado (ancho de Silverman relativo a la mediana de la celda)
    sube de 24,7 % a 28,3 % en promedio (hasta 57,8 % en las celdas chicas) -- mas inestabilidad que señal util,
    y sin un relato de "escenario de estres" tan claro como el de edad/ruta (que ya documenta
    docs/factores_estancia.md). No se añade.
  - **Metricas**: un solo componente animado (peor/base/mejor caso de ocupacion -> pacientes en espera -> % de
    dias sin cama -> dias totales sin cama -> vuelve a empezar), puro CSS (theme.css, bloque ".camas-loop").
  - **Sliders**: fila horizontal (como pronostico), con el titulo + icono de info (el texto de ayuda se mueve al
    tooltip) y el mismo lenguaje visual de .range-metric (linea + punto), via overrides de rc-slider en theme.css.
  - **Grafico**: se corrigio el hueco blanco entre el tramo azul y el rojo (el punto de cambio ahora se incluye
    en ambas series, asi las dos lineas se tocan en vez de dejar un NaN en la frontera).
  - **¿Como se interpreta?/Ficha tecnica**: el parrafo largo que iba debajo del titulo se reparte en estos dos
    paneles plegables, igual patron que pronostico.py/paciente.py.

Misma logica de datos que la version anterior; solo cambian los ids de componentes (prefijo "camas-") para no
chocar con las otras paginas de la misma app.
"""
import os
import sys
from pathlib import Path

import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))        # dashboard/ para el tema de graficos
import simulacion_camas_montecarlo as scm  # noqa: E402  (import liviano desde el 10-nov: ~1-2 s, no corre el backtest)
import tema_graficos as tg  # noqa: E402
from componentes import bloque, coma, leer, mensaje, metodo  # noqa: E402

from eleccion_modelos import tarjeta_eleccion  # noqa: E402
from componentes import ETAPAS_Y_PRUEBAS, secciones  # noqa: E402
dash.register_page(__name__, path="/camas", name="Planeación de camas", title="Planeación de camas - HUN", order=3)

GRIS, AZUL, NARANJA, VERDE, ROJO = "#6b6b6b", "#2a6fb0", "#eb6834", "#2e8b57", "#c0392b"
RAIZ = Path(__file__).resolve().parent.parent.parent
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
from modo import repeticiones  # noqa: E402  (modo ligero en servidores pequenos como Render)
N_REP_INTERACTIVO = repeticiones(300)
_CACHE = {}      # resultados ya calculados por (cambios, plazo, dia): repetir una simulacion es instantaneo
CAMAS_HUN_TOTAL = 106            # camas de hospitalizacion que informo el HUN
_BASE = {}      # caso base (mediana por grupo) por (plazo, dia de arranque): se calcula una vez y se reutiliza
GRUPOS = ["total", "ninos", "adultos"]
NOMBRES_GRUPO = {"total": "Total", "ninos": "Niños (0-4, 5-14)", "adultos": "Adultos (15+)"}
ICONO_GRUPO = {"total": "ico-group", "ninos": "ico-child", "adultos": "ico-patient"}
INFO_GRUPO = {
    "total": "Todos los pacientes hospitalizados, sin separar por edad.",
    "ninos": "Grupos de edad 0-4 y 5-14 años. Proxy de las camas pediátricas + neonatales (18 camas).",
    "adultos": "15 años en adelante. Proxy de las camas de adultos, intermedia, intensiva y TPR (88 camas).",
}
NOMBRES_CASO = {"mejor": "Mejor caso", "base": "Caso base (mediana)", "peor": "Peor caso"}
PLAZOS = [("7 días", 7), ("30 días", 30), ("6 meses", 182), ("1 año", 365)]

# ----------------------------------------------------------------------
# Escenario D: mezcla de "peor caso" por estancia, mezclada con la mezcla real segun una intensidad 0-100 %
# ----------------------------------------------------------------------
_mediana_ruta = {r: float(np.median(np.concatenate([v for (g, t), v in scm.BOOTSTRAP_PERFIL.items() if t == r])))
                  for r in scm.RUTAS_HIST.index}
_peso_edad = scm.resumen_reciente["mediana"].reindex(scm.GRUPOS_HIST)
_peso_edad = (_peso_edad / _peso_edad.sum()).to_dict()
_peso_ruta = pd.Series(_mediana_ruta)
_peso_ruta = (_peso_ruta / _peso_ruta.sum()).to_dict()
_real_edad = dict(zip(scm.GRUPOS_HIST, scm.PROB_GRUPOS))
_real_ruta = dict(scm.RUTAS_HIST)


def mezcla_escenario_d(intensidad):
    """intensidad en [0, 1]: 0 = mezcla real de 2025 (igual al default de simular()), 1 = 100 % concentrado en
    los grupos/rutas de mayor estancia mediana. Devuelve (mezcla_edad, mezcla_ruta), normalizados a sumar 1."""
    me = {g: (1 - intensidad) * _real_edad[g] + intensidad * _peso_edad[g] for g in scm.GRUPOS_HIST}
    mr = {r: (1 - intensidad) * _real_ruta[r] + intensidad * _peso_ruta[r] for r in scm.RUTAS_HIST.index}
    me = {k: v / sum(me.values()) for k, v in me.items()}
    mr = {k: v / sum(mr.values()) for k, v in mr.items()}
    return me, mr


# ----------------------------------------------------------------------
# Ficha tecnica (para evaluadores): que se probo y se descarto, con los numeros medidos esta sesion
# (ver el docstring del modulo) y los de docs/modelo_camas.md / docs/simulacion.md.
# ----------------------------------------------------------------------
ETAPAS_PIPELINE_CAMAS = [
    ("1. Series base", "Ingresos a cama y ocupación real se reconstruyen directo de "
     "estancias_hospitalizacion.csv (25.777 estancias únicas), con la misma fórmula que ya usa "
     "exportar_para_equipo.py — se reprodujo y coincide con docs/CONTEXTO_TECNICO.md 4.8."),
    ("2. Bootstrap por perfil", "La duración de cada estancia simulada se saca al azar de pacientes reales "
     "con la misma edad Y la misma ruta de llegada (Urgencias/Treatment urgency/Ambulatorio) — separar por "
     "ruta importa porque Treatment urgency se queda 63 % más tiempo que Urgencias a la misma edad."),
    ("3. Suavizado gaussiano", "Cada valor remuestreado se desplaza con ruido de ancho de Silverman (más "
     "ancho en celdas con pocos casos), para no repetir siempre los mismos valores exactos ni dejar un "
     "atípico con una probabilidad fija de 1/n."),
    ("4. Motor de Monte Carlo", "Cada repetición: ingresos diarios ~ Poisson(pronóstico), un perfil "
     "(edad × ruta) y una estancia por paciente, censo diario = ingresos acumulados − altas acumuladas. "
     "Siembra el día 0 con el censo real del corte (si no, el hospital tardaría 3-4 semanas en \"llenarse\")."),
    ("5. Backtest", "Se simula enero-9abr 2026 entrenando el pronóstico solo hasta dic-2025 y se compara "
     "contra la ocupación real de esos días — puerta de decisión antes de usar el motor para proyectar."),
    ("6. Escenarios y curva de capacidad", "B (+10 % ingresos), C (−5 % estancia), D (mezcla de perfiles de "
     "estrés) y la curva de capacidad (cuántas camas harían falta para un riesgo dado) se leen sobre la MISMA "
     "proyección ya simulada — no hace falta volver a correr el motor."),
]

TABLA_DECISIONES_CAMAS = [
    ("Filtro de sexo (42 celdas edad×sexo×ruta)", "No entra",
     "Señal real en 11 de 19 celdas comparables (brecha de mediana > 10 %, media 13,8 %), pero 5 de 42 celdas "
     "quedan con menos de 30 casos y el ruido de suavizado sube de 24,7 % a 28,3 % en promedio (hasta 57,8 % en "
     "las celdas chicas) — más inestabilidad que señal útil, sin un relato de \"escenario de estrés\" claro"),
    ("Dropdown \"ver desde este punto\" (mover el corte a un día de pico)", "No entra",
     "No medía lo que decía: 5 fechas con picos de 0,1 % a 20,8 % dieron una ocupación casi plana (114,7-116,1 "
     "camas) porque la variación venía de reanclar el pronóstico a otro año calendario, no del tamaño del "
     "pico. El slider de ingresos mueve el resultado ~2,2x más"),
    ("mezcla_edad / mezcla_ruta (Escenario D)", "Entra",
     "El bootstrap ya está separado por ruta y edad; permite simular, p. ej., que Treatment urgency siga "
     "creciendo (ya duplicó su peso entre 2023 y 2025, docs/factores_estancia.md)"),
]

INFO_SLIDER = {
    "ingresos": "Sube o baja los ingresos a cama un % fijo en todo el horizonte (Escenario B del plan mínimo "
                "= +10 %: simula un aumento sostenido de demanda, por ejemplo un brote o temporada alta).",
    "estancia": "Sube o baja cuánto dura cada estancia un % fijo (Escenario C del plan mínimo = −5 %: simula "
                "más eficiencia clínica, altas más tempranas). Es la palanca más barata: bajar la estancia 5 % "
                "mueve la ocupación casi tanto como +10 camas físicas.",
    "escenario_d": "Concentra la mezcla de pacientes (edad y ruta de llegada) hacia los grupos que históricamente "
                   "más tiempo se quedan — un caso de ESTRÉS explícito (100 % = el peor caso posible de mezcla), "
                   "NO una simulación más realista que la mezcla real de 2025 (0 %). Es el Escenario D del plan "
                   "mínimo.",
}


def info_badge(texto):
    return html.Span(className="info-badge tooltip-trigger", children=[
        "i", html.Span(texto, className="tooltip-content")])


def opcion_icono(ico, texto_info):
    return html.Span(className="pill-icon-option", children=[
        html.Span(className=f"nav__ico {ico}"), info_badge(texto_info)])


def campo_slider(etiqueta, clave_info, control):
    return html.Div(className="camas-slider-group", children=[
        html.Span(className="camas-slider-group__label", children=[etiqueta, info_badge(INFO_SLIDER[clave_info])]),
        control,
    ])


def caso_columna(clave, valor_medio, cap):
    """Una columna del componente animado. En el MISMO lugar y una tras otra: (1) las CAMAS OCUPADAS (tope en
    `cap`, naranja si de verdad lo supera), (2) los pacientes que quedarian SIN CAMA (excedente sobre `cap`),
    cuyo numero luego se convierte en un PUNTO del color del numero (verde si 0, rojo si hay excedente). La
    tarjeta de fondo y las etiquetas se desvanecen dejando solo el numero antes de que se vuelva punto."""
    capado = min(valor_medio, cap)
    excedente = max(valor_medio - cap, 0)
    color_ocup = NARANJA if excedente > 0 else AZUL
    color = ROJO if excedente > 0 else VERDE
    return html.Div(className="camas-loop__caso", children=[
        html.Div(className="camas-loop__caso-card"),
        html.Div(NOMBRES_CASO[clave], className="camas-loop__caso-nombre"),
        html.Div(className="camas-loop__ocupadas", children=[
            html.Div(f"{capado:.0f}", className="camas-loop__ocupadas-valor", style={"color": color_ocup}),
            html.Div("camas ocupadas", className="camas-loop__ocupadas-cap"),
        ]),
        html.Div(f"{excedente:.0f}", className="camas-loop__num", style={"color": color}),
        html.Div("sin cama", className="camas-loop__sincama-cap"),
        html.Div(className="camas-loop__dot", style={"background": color, "boxShadow": f"0 0 0 4px {color}33"}),
    ])


def panel_metricas_animado(medias, cap, pct_sat, dias_sin_cama, total_dias):
    """Componente unico en bucle (CSS puro, ver theme.css '.camas-loop'):
    (1) 3 casos (mejor/base/peor) muestran los PACIENTES SIN CAMA en tarjetas; (2) las tarjetas y las etiquetas
    desaparecen y quedan solo los numeros, que se convierten en puntos rojos unidos por una linea; (3) los puntos
    se funden en el centro y de ahi emerge, centrado y un poco mas grande, el % de dias sin cama (con su tarjeta)
    y, un momento despues, el numero de dias sin cama; vuelve a empezar. Tiempos cortos. Los dos bloques (casos y
    final) estan superpuestos en '.camas-loop__stage' para que todo ocurra en la MISMA ubicacion centrada."""
    return html.Div(className="camas-loop", children=[
        html.Div(className="camas-loop__stage", children=[
            html.Div(className="camas-loop__casos", children=[
                caso_columna("mejor", medias["mejor"], cap),
                caso_columna("base", medias["base"], cap),
                caso_columna("peor", medias["peor"], cap),
                html.Div(className="camas-loop__linea"),           # linea roja que une los 3 puntos
            ]),
            html.Div(className="camas-loop__final", children=[
                html.Div(className="camas-loop__final-card", children=[
                    html.Div(className="camas-loop__final-item camas-loop__final-item--pct", children=[
                        html.Div(f"{pct_sat:.0f} %", className="camas-loop__final-valor"),
                        html.Div("de los días-repetición faltan camas", className="camas-loop__final-caption"),
                    ]),
                    html.Div(className="camas-loop__final-item camas-loop__final-item--dias", children=[
                        html.Div(f"{dias_sin_cama} de {total_dias}", className="camas-loop__final-valor"),
                        html.Div("días (según la mediana) sin camas suficientes", className="camas-loop__final-caption"),
                    ]),
                ]),
            ]),
        ]),
    ])


def panel_altas():
    """Escenario aparte: adelantar a la mañana una parte de las altas que hoy se dan después del mediodia (tablas de src/simulacion_altas.py)."""
    return html.Div(className="card", style={"padding": "16px 20px", "margin": "18px 0"}, children=[
        bloque("Si se adelantan las altas de la tarde", "Un escenario aparte: no cambia la simulación de arriba"),
        html.P("Hoy el 86 % de las altas se da después del mediodía. Elige qué parte pasaría a darse entre las 9 y las 12 h y mira cuántas camas quedarían libres "
               "a mediodía y cuánto ayudaría a la espera.", style={"fontSize": "13.5px"}),
        html.Div(className="camas-slider-group", children=[
            html.Span("Altas de la tarde que se adelantan", className="camas-slider-group__label"),
            dcc.Slider(id="camas-altas", min=0, max=100, step=10, value=30, marks={0: "0 %", 30: "30 %", 50: "50 %", 100: "100 %"},
                       tooltip={"placement": "bottom", "always_visible": True})]),
        html.Div(id="camas-altas-cifras", className="hechos"),
        dcc.Graph(id="camas-altas-grafico", config={"displaylogo": False, "displayModeBar": False}, style={"height": "300px"}),
        html.P(id="camas-altas-nota", style={"fontSize": "12px", "color": GRIS}),
    ])


def panel_interpretacion():
    return html.Details(className="metodo metodo--panel", children=[
        html.Summary([html.Span("¿Cómo se interpreta?", className="metodo__titulo"), html.Span("qué ves, cómo se calculó y qué no dice", className="metodo__sub")]),
        html.Div(className="metodo__apilado", children=[
            html.Div([html.Div("Qué estás viendo", className="metodo__rotulo"),
                      html.Div("Cuántos pacientes habría en cama cada día, de aquí al plazo elegido, en tres "
                               "escenarios (mejor caso, caso base y peor caso), y cuántos de ellos se quedarían "
                               "esperando porque ya no quedan de las 106 camas reales.")]),
            html.Div([html.Div("Cómo se calculó", className="metodo__rotulo"),
                      html.Div("Con una simulación de Monte Carlo: cada día, los ingresos a cama salen de una "
                               "distribución de Poisson alrededor del pronóstico, y a cada paciente se le asigna "
                               "una duración de estancia sacada al azar de pacientes reales parecidos (misma "
                               "edad y misma ruta de llegada). Se repite 300 veces (los documentos oficiales "
                               "citan la cifra con 1.000) para ver el rango de lo que podría pasar, no solo un "
                               "número.")]),
            html.Div([html.Div("Qué significa para el hospital", className="metodo__rotulo"),
                      html.Div("El hospital opera, en el escenario típico, al borde o por encima de su capacidad "
                               "declarada — no por debajo con margen. El riesgo se concentra en adultos (70,6 % "
                               "de probabilidad de saturar sus 88 camas) mucho más que en niños (34,5 % de 18). "
                               "Moviendo los sliders se ve qué pesa más: bajar la estancia 5 % mueve la ocupación "
                               "casi tanto como +10 camas físicas — la estancia es la palanca más barata antes de "
                               "pensar en ampliar capacidad.")]),
            html.Div([html.Div("Qué NO dice", className="metodo__rotulo"),
                      html.Div("No es una predicción exacta para un día puntual (la banda de incertidumbre es "
                               "ancha a propósito). No separa por sexo ni por servicio/piso exacto (se probó "
                               "sexo y no mejoró lo suficiente para justificar la inestabilidad que añade — "
                               "detalle en la ficha técnica). Es asociación proyectada hacia adelante sobre un "
                               "patrón histórico, no una garantía de que ese patrón se mantenga.")]),
        ]),
    ])


def panel_tecnico():
    pasos = [html.Div(className="pipeline__step tooltip-trigger", children=[
                html.Div(className="pipeline__dot"), html.Div(titulo, className="pipeline__label"),
                html.Span(detalle, className="tooltip-content")])
             for titulo, detalle in ETAPAS_PIPELINE_CAMAS]
    filas_decision = [html.Tr([html.Th("Qué se probó"), html.Th("Resultado"), html.Th("Por qué")])] + [
        html.Tr([html.Td(v), html.Td(r, style={"fontWeight": 700, "color": VERDE if r == "Entra" else GRIS}), html.Td(por_que)])
        for v, r, por_que in TABLA_DECISIONES_CAMAS]
    return html.Details(className="metodo metodo--panel", children=[
        html.Summary([html.Span("Ficha técnica del planeador", className="metodo__titulo"), html.Span("cómo se construyó y qué se probó", className="metodo__sub")]),
        html.Div(className="metodo__apilado", children=[
            html.Div([
                html.Div("Etapas de construcción (pasa el mouse sobre cada una)", className="metodo__rotulo"),
                html.Div(className="pipeline", children=pasos),
            ]),
            html.Div([
                html.Div("Qué hace cada control", className="metodo__rotulo"),
                html.Div(f"El botón «Simular» corre el motor de Monte Carlo con n = {N_REP_INTERACTIVO} repeticiones: "
                         "es una aproximación rápida pensada para moverse con los sliders sin esperar — los documentos "
                         "oficiales (docs/modelo_camas.md, docs/simulacion.md) citan la cifra final con 1.000 "
                         "repeticiones. La diferencia entre ambas es chica: comparando el mismo escenario base con "
                         "300 y con 1.000 repeticiones, la media sale casi igual (111,0 contra 111,1 camas) y el % "
                         "de días saturados también (65,3 % contra 65,4 %) — reducir repeticiones para la interacción "
                         "en vivo no distorsiona la respuesta.", style={"fontSize": "12px", "color": GRIS, "marginBottom": "8px"}),
                html.Ul(style={"fontSize": "13px", "lineHeight": "1.7", "paddingLeft": "18px"}, children=[
                    html.Li([html.B("Ingresos a cama: "), INFO_SLIDER["ingresos"]]),
                    html.Li([html.B("Estancia en cama: "), INFO_SLIDER["estancia"]]),
                    html.Li([html.B("Escenario D (mezcla de estrés): "), INFO_SLIDER["escenario_d"]]),
                ]),
            ]),
            html.Div([
                html.Div("Backtest (puerta de decisión): enero a 9-abr-2026, entrenado solo hasta dic-2025", className="metodo__rotulo"),
                html.Table(className="tech-table", children=[
                    html.Thead(html.Tr([html.Th("Métrica"), html.Th("Resultado"), html.Th("Meta")])),
                    html.Tbody([
                        html.Tr([html.Td("Error absoluto medio"), html.Td("8,6 camas"), html.Td("—")]),
                        html.Tr([html.Td("Sesgo (simulada − real)"), html.Td("+7,0 camas"), html.Td("—")]),
                        html.Tr([html.Td("% de días con la ocupación real dentro de la banda 10-90 %"), html.Td(html.B("78,8 %")), html.Td("entre 70 % y 90 %")]),
                    ]),
                ], style={"width": "100%", "marginBottom": "6px"}),
                html.Div("Cumple la puerta de decisión: el error relativo (~6-7 % sobre una ocupación de ~100-108) "
                         "es razonable para un modelo que proyecta 3-4 meses hacia adelante sin ver esos datos.",
                         style={"fontSize": "12px", "color": GRIS}),
            ], className="tech-table-wrap"),
            html.Div([
                html.Div("Qué se probó y qué se descartó", className="metodo__rotulo"),
                html.Div(html.Table(filas_decision, className="metodo__tabla"), className="metodo__scroll"),
            ]),
            html.Div([
                html.Div("Cuántas camas harían falta", className="metodo__rotulo"),
                html.Div("Sobre la MISMA proyección ya calculada, se barre un rango de "
                         "capacidades hipotéticas y se mide qué tan seguido no alcanzarían. Con el umbral de "
                         "riesgo del 10 %, el total necesitaría ~126 camas (+20 sobre las 106 actuales), "
                         "adultos ~108 (+20) y niños ~22 (+4) — mucho más que un ajuste cosmético.",
                         style={"fontSize": "13px", "lineHeight": "1.6"}),
            ]),
            html.Div([
                html.Div("Límites", className="metodo__rotulo"),
                html.Ul(style={"fontSize": "12.5px", "color": GRIS, "lineHeight": "1.6", "paddingLeft": "18px"}, children=[
                    html.Li("El proxy niños/adultos usa los bins de grupo_edad disponibles (0-4/5-14 vs. 15-29+), "
                            "más grueso que el corte \"menor de 1 año\" que el equipo usó una vez a mano."),
                    html.Li("El backtest formal es solo del censo total; los censos de niños/adultos no tienen "
                            "una serie real separada contra la cual compararse."),
                    html.Li("Los ingresos se simulan con una sola fuente de aleatoriedad por día; no se "
                            "remuestrea además el margen de error propio del pronóstico semanal."),
                    html.Li("A los pacientes ya hospitalizados el día de corte se les asigna un tiempo restante "
                            "del mismo bootstrap de estancias completas, sin corregir el sesgo de selección "
                            "(\"inspection paradox\") — solo afecta a los primeros días, no a la ocupación de régimen."),
                    html.Li("Asociación, no causa; 106/18/88 es la cifra que dio el HUN el 29-oct sin fecha de corte conocida."),
                ]),
                html.Div("Detalle completo: docs/modelo_camas.md y docs/simulacion.md.", style={"fontSize": "11px", "color": GRIS, "marginTop": "6px"}),
            ]),
        ]),
    ])


def layout():
    return html.Div(className="page-container", children=[
        html.Div(className="page-head", children=[
            html.H2("¿Cuántos pacientes se quedarán sin cama?"),
            html.P("Cambia un supuesto sobre el futuro (más ingresos, menos estancia, otra mezcla de perfiles) y "
                   "ve cuántos pacientes quedarían esperando cama. Simulación hacia adelante, no una lectura de "
                   "lo que ya pasó.", className="page-head__sub"),
        ]),

        html.Div(className="control-row", children=[
            html.Div(className="control-group", children=[
                html.Span("¿Hasta cuándo quieres ver?", className="control-group__label"),
                dcc.RadioItems(id="camas-plazo", className="pill-switch",
                               options=[{"label": n, "value": d} for n, d in PLAZOS], value=182)]),
            html.Div(className="control-group", children=[
                html.Span("Edad", className="control-group__label"),
                dcc.RadioItems(id="camas-grupo", className="pill-switch pill-switch--icons",
                               options=[{"label": opcion_icono(ICONO_GRUPO[g], INFO_GRUPO[g]), "value": g} for g in GRUPOS],
                               value="total")]),
        ]),

        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "32px", "alignItems": "stretch"}, children=[
            html.Div(className="form-panel", style={"flex": "0 0 320px", "display": "flex", "flexDirection": "column"}, children=[
                html.Div(style={"display": "flex", "flexDirection": "column", "justifyContent": "space-evenly",
                                "flex": "1 1 auto", "gap": "26px"}, children=[
                    campo_slider("Ingresos a cama", "ingresos", dcc.Slider(id="camas-ajuste_ingresos", min=-30, max=30, step=5, value=0)),
                    campo_slider("Estancia en cama", "estancia", dcc.Slider(id="camas-ajuste_estancia", min=-20, max=20, step=5, value=0)),
                    campo_slider("Mezcla de pacientes", "escenario_d", dcc.Slider(id="camas-intensidad_d", min=0, max=100, step=10, value=0)),
                ]),
                html.Div(style={"marginTop": "18px"}, children=[
                    html.Button("Simular", id="camas-simular", n_clicks=0, className="btn-primary", style={"width": "100%"}),
                    html.Div(id="camas-nota_r7", style={"fontSize": "12px", "marginTop": "10px"}),
                ]),
            ]),
            html.Div(style={"flex": "1 1 600px"}, children=[
                dcc.Loading(type="dot", color="#0071bc", children=[
                    html.Div(id="camas-metricas"),
                    dcc.Graph(id="camas-grafico_proyeccion", config={"displaylogo": False})]),
            ]),
        ]),

        dcc.Store(id="camas-censos_guardados"),
        html.P("Supuestos: B y C se aplican de forma uniforme en todo el horizonte; D es un caso de estrés explícito "
               "(no un pronóstico); ningún escenario cambia la capacidad física (106/18/88, dato del HUN). Asociación, "
               "no causa.", style={"fontSize": "11px", "color": GRIS, "marginTop": "10px"}),
        panel_altas(),
        tarjeta_eleccion("/camas"),
        mensaje("**Es un «qué pasa si», no un pronóstico del censo de hoy.** Sirve para ver cuántos días del próximo semestre podrían quedar por encima de las 106 camas "
                "y cuánto cambiaría eso con más ingresos, estancias más cortas o una mezcla distinta de pacientes. La mayor presión está en los adultos."),
        metodo("Para cada día futuro se toman los ingresos pronosticados y estancias reales por perfil (niños y adultos), y se cuenta cuántos pacientes siguen en cama. "
               "Con miles de repeticiones sale la probabilidad de superar las 106 camas. Se validó con un backtest (enero a 9-abr-2026, entrenando solo hasta 2025): la banda "
               "del 80 % cubre ~79 % de los días reales.",
               "No predice la estancia de ningún paciente concreto (R² cerca de 0). Arranca del último censo confiable (9-abr-2026), no del de hoy, porque después el registro "
               "de etapas está incompleto: se simulan los días hasta hoy y se muestra desde mañana, como el pronóstico de demanda. Las camas totales (106) son lo que informó el HUN; el exceso observado puede ser camas de apoyo o camillas.",
               "Fuente: src/simulacion_camas_montecarlo.py. Detalle: documentación, sección 6.5, y docs/modelo_camas.md.", ruta="/camas",
               antes=[], despues=secciones(panel_tecnico(), solo=ETAPAS_Y_PRUEBAS), pasos=False, modelo=False),
    ])


@callback(Output("camas-censos_guardados", "data"), Output("camas-nota_r7", "children"),
          Input("camas-simular", "n_clicks"),
          State("camas-ajuste_ingresos", "value"), State("camas-ajuste_estancia", "value"),
          State("camas-intensidad_d", "value"), State("camas-plazo", "value"))
def correr_simulacion(_, pct_ingresos, pct_estancia, intensidad_d, dias):
    llave = (pct_ingresos, pct_estancia, intensidad_d, int(dias), str(pd.Timestamp.today().date()))
    if llave in _CACHE:
        return _CACHE[llave]
    me, mr = (mezcla_escenario_d(intensidad_d / 100) if intensidad_d else (None, None))
    # El motor arranca del ultimo censo confiable (9-abr-2026) y se simulan tambien los dias hasta hoy; se muestra solo lo que viene,
    # desde mañana, igual que el pronostico de demanda. Asi "7 dias" son los proximos 7 dias y no el 10 al 16 de abril.
    manana = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
    previos = max((manana - pd.Timestamp(scm.ULTIMO_CONFIABLE)).days - 1, 0)
    fechas, censos = scm.simular(scm.serie_ingresos, scm.ULTIMO_CONFIABLE, previos + dias,
                                  ajuste_ingresos=1 + pct_ingresos / 100, ajuste_estancia=1 + pct_estancia / 100,
                                  n_rep=N_REP_INTERACTIVO, mezcla_edad=me, mezcla_ruta=mr)
    desde = np.where(np.asarray(fechas) >= np.datetime64(manana))[0][:dias]
    fechas, censos = fechas[desde], {g: c[:, desde] for g, c in censos.items()}
    nota = ""
    if pct_estancia < 0:
        nota = html.Div([html.B("R7 (recomendaciones): "),
                          "revisión semanal de pacientes con más de 7 días de estancia, con gestión de casos, foco en "
                          "más de 14 días. Bajar la estancia 5 % libera ~5 camas según la ley de Little; volver a la "
                          "estancia de 2023, ~15."], style={"border": f"1px solid {VERDE}", "borderRadius": "6px", "padding": "6px 10px"})
    cambio = bool(pct_ingresos or pct_estancia or intensidad_d)
    clave = (int(dias), str(manana.date()))
    if not cambio:                                           # sin cambios, esta corrida ya es el caso base
        _BASE[clave] = {g: np.percentile(censos[g], 50, axis=0).tolist() for g in GRUPOS}
    elif clave not in _BASE:
        fb, cb = scm.simular(scm.serie_ingresos, scm.ULTIMO_CONFIABLE, previos + dias, n_rep=N_REP_INTERACTIVO)
        db = np.where(np.asarray(fb) >= np.datetime64(manana))[0][:dias]
        _BASE[clave] = {g: np.percentile(cb[g][:, db], 50, axis=0).tolist() for g in GRUPOS}
    # Al navegador solo va lo que se dibuja (percentiles por dia y la fraccion sobre la capacidad), no las 300 repeticiones: antes eran ~3 MB por corrida.
    resumen = {g: {"p10": np.percentile(censos[g], 10, axis=0).round(1).tolist(), "p50": np.percentile(censos[g], 50, axis=0).round(1).tolist(),
                   "p90": np.percentile(censos[g], 90, axis=0).round(1).tolist(), "pct_sat": round(100 * float((censos[g] > scm.CAPACIDAD[g]).mean()), 1)} for g in GRUPOS}
    data = {"fechas": [str(f.date()) for f in fechas], "base": _BASE[clave], "cambio": cambio, "resumen": resumen}
    _CACHE[llave] = (data, nota)
    return data, nota


@callback(Output("camas-grafico_proyeccion", "figure"), Output("camas-metricas", "children"),
          Input("camas-censos_guardados", "data"), Input("camas-grupo", "value"),
          State("theme-store", "data"))
def mostrar(data, grupo, tema):
    if not data:
        return go.Figure(), []
    fechas = pd.to_datetime(data["fechas"])
    r = data["resumen"][grupo]
    p10, p50, p90 = np.array(r["p10"]), np.array(r["p50"]), np.array(r["p90"])
    cap_hun = scm.CAPACIDAD[grupo]

    sobre = p50 > cap_hun                                    # dias (de la mediana simulada) sin camas suficientes
    # La linea naranja debe ser el punto EXACTO donde el color cambia: en vez de compartir los dos puntos reales
    # que rodean la transicion (eso deja que cada tramo "se pase" del umbral, porque uno de los dos puntos
    # reales que comparten esta por definicion del otro lado), se interpola el cruce exacto (x, cap_hun) entre
    # cada par de puntos consecutivos que cambian de lado y se inserta ESE punto (no los reales) en ambas series.
    x_normal, y_normal, x_sobre, y_sobre = [], [], [], []
    n = len(p50)
    for i in range(n):
        valor = float(p50[i])
        if sobre[i]:
            x_sobre.append(fechas[i]); y_sobre.append(valor)
        else:
            x_normal.append(fechas[i]); y_normal.append(valor)
        if i < n - 1 and sobre[i] != sobre[i + 1]:
            frac = (cap_hun - float(p50[i])) / (float(p50[i + 1]) - float(p50[i]))
            x_cruce = fechas[i] + frac * (fechas[i + 1] - fechas[i])
            x_normal.append(x_cruce); y_normal.append(cap_hun)
            x_sobre.append(x_cruce); y_sobre.append(cap_hun)

    # El tramo rojo NO son "pacientes sin cama": superar las 106 camas reportadas es sobreocupacion o una
    # capacidad real mayor (docs/CONTEXTO_TECNICO.md 4.8), asi que el hover muestra la ocupacion total, igual que el azul.
    fig = go.Figure([
        go.Scatter(x=fechas, y=p90, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"),
        go.Scatter(x=fechas, y=p10, mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(42,111,176,0.15)",
                   name="Banda 10-90 %", hoverinfo="skip"),
        go.Scatter(x=x_normal, y=y_normal, mode="lines", line=dict(color=AZUL, width=2), name="Pacientes en cama",
                   hovertemplate="%{x|%d-%m-%Y}<br>%{y:.0f} pacientes en cama<extra></extra>"),
        go.Scatter(x=x_sobre, y=y_sobre, mode="lines", line=dict(color=ROJO, width=2.5),
                   name=f"Por encima de la capacidad ({cap_hun})",
                   hovertemplate="%{x|%d-%m-%Y}<br>%{y:.0f} pacientes en cama<extra></extra>"),
        go.Scatter(x=fechas, y=[cap_hun] * len(fechas), mode="lines", line=dict(color=NARANJA, dash="dash"),
                   name=f"Capacidad HUN ({cap_hun})", hoverinfo="skip"),
    ])
    base = (data.get("base") or {}).get(grupo) if data.get("cambio") else None
    if base is not None:
        fig.add_trace(go.Scatter(x=fechas, y=base, mode="lines", line=dict(color=GRIS, width=1.5, dash="dot"), name="Caso base (sin cambios)",
                                 hovertemplate="%{x|%d-%m-%Y}<br>%{y:.0f} pacientes en cama en el caso base<extra></extra>"))
    fig.update_layout(title=f"Ocupación proyectada — {NOMBRES_GRUPO[grupo]}", yaxis_title="Pacientes en cama",
                      template="simple_white", legend=dict(orientation="h", y=-0.2), margin=dict(l=40, r=20, t=50, b=40))

    pct_sat = r["pct_sat"]
    dias_sin_cama = int((p50 > cap_hun).sum())
    medias = {"mejor": float(p10.mean()), "base": float(p50.mean()), "peor": float(p90.mean())}
    metricas = panel_metricas_animado(medias, cap_hun, pct_sat, dias_sin_cama, len(fechas))
    if base is not None:
        dif = float(np.mean(p50) - np.mean(base))
        dias_dif = int((p50 > cap_hun).sum() - (np.array(base) > cap_hun).sum())
        frase = (f"Frente al caso base: {'+' if dif >= 0 else '−'}{coma(abs(dif), 1)} camas ocupadas en promedio y "
                 f"{abs(dias_dif)} {'día' if abs(dias_dif) == 1 else 'días'} {'más' if dias_dif >= 0 else 'menos'} sin camas suficientes.")
        metricas = html.Div([metricas, html.Div(frase, style={"textAlign": "center", "fontWeight": 600, "marginTop": "8px"})])

    dark = tg.es_oscuro(tema)
    tg.aplicar(fig, dark)
    return fig, metricas


@callback(Output("camas-altas-cifras", "children"), Output("camas-altas-grafico", "figure"), Output("camas-altas-nota", "children"),
          Input("camas-altas", "value"), State("theme-store", "data"))
def altas_adelantadas(pct, tema):
    esc, horas = leer("escenario_altas_antes.csv"), leer("escenario_camas_por_hora.csv")
    if esc is None or horas is None:
        return [], go.Figure(), "No se encontraron las tablas del escenario de altas."
    p = (pct or 0) / 100
    x = [0.0] + esc.proporcion_movida.tolist()
    dato = lambda col: float(np.interp(p, x, [0.0] + esc[col].tolist()))            # las camas liberadas crecen en proporcion directa con el porcentaje
    libres = horas.camas_libres_adicionales * (p / 0.30)                             # la tabla de camas por hora esta calculada con el 30 %
    libres12 = float(libres[horas.hora == 12].iloc[0])
    est, cota = dato("estimacion_pct_del_exceso"), dato("cota_superior_pct_del_exceso")
    cifras = [hecho_altas(coma(dato("altas_movidas_por_dia"), 1), "Altas adelantadas por día", "De las que hoy se dan después del mediodía."),
              hecho_altas(coma(libres12, 1), "Camas libres más a las 12 h", "Frente a lo que hay hoy a mediodía."),
              hecho_altas(f"{coma(est, 1)} %", "De la espera por encima de lo normal se evitaría", f"Estimación; como máximo {coma(cota, 1)} %.")]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=horas.hora, y=horas.ocupacion_base, mode="lines", name="Hoy", line=dict(color=GRIS, width=2, dash="dot"),
                             hovertemplate="%{x} h: %{y:.0f} camas ocupadas hoy<extra></extra>"))
    fig.add_trace(go.Scatter(x=horas.hora, y=horas.ocupacion_base - libres, mode="lines", name="Con las altas adelantadas", line=dict(color=AZUL, width=3),
                             hovertemplate="%{x} h: %{y:.0f} camas ocupadas<extra></extra>"))
    fig.add_trace(go.Scatter(x=[0, 23], y=[CAMAS_HUN_TOTAL, CAMAS_HUN_TOTAL], mode="lines", line=dict(color=NARANJA, dash="dash", width=2), name="106 camas informadas por el hospital", hoverinfo="skip"))
    fig.update_layout(template="simple_white", legend=dict(orientation="h", y=-0.25), margin=dict(l=40, r=20, t=20, b=40),
                      xaxis_title="Hora del día", yaxis_title="Camas ocupadas", yaxis_range=[horas.ocupacion_base.min() - 8, 110])
    tg.aplicar(fig, tg.es_oscuro(tema))
    nota = ("Es un escenario con supuestos, no una predicción: las altas de los demás pacientes no cambian y cada cama liberada se vuelve a ocupar con parte de los ingresos. "
            "Adelantar altas ayuda, pero no resuelve las esperas de varios días: el 83 % de las horas de espera viene de pacientes que esperan más de un día.")
    return cifras, fig, nota


def hecho_altas(numero, titulo, texto):
    return html.Div(className="hecho", children=[html.Div(numero, className="hecho__num"), html.Div(titulo, className="hecho__titulo"), html.P(texto, className="hecho__txt")])
