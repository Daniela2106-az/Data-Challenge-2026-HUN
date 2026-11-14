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

dash.register_page(__name__, path="/camas", name="Planeación de camas", title="Planeación de camas - HUN", order=3)

GRIS, AZUL, NARANJA, VERDE, ROJO = "#6b6b6b", "#2a6fb0", "#eb6834", "#2e8b57", "#c0392b"
RAIZ = Path(__file__).resolve().parent.parent.parent
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
N_REP_INTERACTIVO = 300
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
     "exportar_para_equipo.py — se reprodujo y coincide con CLAUDE.md 4.8."),
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


def panel_interpretacion():
    return html.Details(className="page-section", children=[
        html.Summary("¿Cómo se interpreta?"),
        html.Div(style={"padding": "10px 4px 2px", "display": "grid", "gap": "14px", "fontSize": "13.5px", "lineHeight": "1.6"}, children=[
            html.Div([html.Div("Qué estás viendo", style={"fontWeight": 700, "color": AZUL, "marginBottom": "3px"}),
                      html.Div("Cuántos pacientes habría en cama cada día, de aquí al plazo elegido, en tres "
                               "escenarios (mejor caso, caso base y peor caso), y cuántos de ellos se quedarían "
                               "esperando porque ya no quedan de las 106 camas reales.")]),
            html.Div([html.Div("Cómo se calculó", style={"fontWeight": 700, "color": AZUL, "marginBottom": "3px"}),
                      html.Div("Con una simulación de Monte Carlo: cada día, los ingresos a cama salen de una "
                               "distribución de Poisson alrededor del pronóstico, y a cada paciente se le asigna "
                               "una duración de estancia sacada al azar de pacientes reales parecidos (misma "
                               "edad y misma ruta de llegada). Se repite 300 veces (los documentos oficiales "
                               "citan la cifra con 1.000) para ver el rango de lo que podría pasar, no solo un "
                               "número.")]),
            html.Div([html.Div("Qué significa para el hospital", style={"fontWeight": 700, "color": AZUL, "marginBottom": "3px"}),
                      html.Div("El hospital opera, en el escenario típico, al borde o por encima de su capacidad "
                               "declarada — no por debajo con margen. El riesgo se concentra en adultos (70,6 % "
                               "de probabilidad de saturar sus 88 camas) mucho más que en niños (34,5 % de 18). "
                               "Moviendo los sliders se ve qué pesa más: bajar la estancia 5 % mueve la ocupación "
                               "casi tanto como +10 camas físicas — la estancia es la palanca más barata antes de "
                               "pensar en ampliar capacidad.")]),
            html.Div([html.Div("Qué NO dice", style={"fontWeight": 700, "color": NARANJA, "marginBottom": "3px"}),
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
    return html.Details(className="page-section", children=[
        html.Summary("Ficha técnica del planeador"),
        html.Div(style={"padding": "14px 4px 4px", "display": "grid", "gap": "22px"}, children=[
            html.Div([
                html.Div("Etapas de construcción (pasa el mouse sobre cada una)", style={"fontWeight": 700, "marginBottom": "4px"}),
                html.Div(className="pipeline", children=pasos),
            ]),
            html.Div([
                html.Div("Qué hace cada control", style={"fontWeight": 700, "marginBottom": "6px"}),
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
                html.Div("Backtest (puerta de decisión): enero a 9-abr-2026, entrenado solo hasta dic-2025", style={"fontWeight": 700, "marginBottom": "4px"}),
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
                html.Div("Qué se probó y qué se descartó", style={"fontWeight": 700, "marginBottom": "6px"}),
                html.Table(filas_decision, style={"width": "100%", "fontSize": "12.5px", "borderCollapse": "collapse"}),
            ]),
            html.Div([
                html.Div("Cuántas camas harían falta", style={"fontWeight": 700, "marginBottom": "4px"}),
                html.Div("Sobre la MISMA proyección ya calculada, se barre un rango de "
                         "capacidades hipotéticas y se mide qué tan seguido no alcanzarían. Con el umbral de "
                         "riesgo del 10 %, el total necesitaría ~126 camas (+20 sobre las 106 actuales), "
                         "adultos ~108 (+20) y niños ~22 (+4) — mucho más que un ajuste cosmético.",
                         style={"fontSize": "13px", "lineHeight": "1.6"}),
            ]),
            html.Div([
                html.Div("Límites", style={"fontWeight": 700, "color": NARANJA, "marginBottom": "4px"}),
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
                html.Div(id="camas-metricas"),
                dcc.Graph(id="camas-grafico_proyeccion", config={"displaylogo": False}),
            ]),
        ]),

        dcc.Store(id="camas-censos_guardados"),
        html.P("Supuestos: B y C se aplican de forma uniforme en todo el horizonte; D es un caso de estrés explícito "
               "(no un pronóstico); ningún escenario cambia la capacidad física (106/18/88, dato del HUN). Asociación, "
               "no causa.", style={"fontSize": "11px", "color": GRIS, "marginTop": "10px"}),
        panel_interpretacion(),
        panel_tecnico(),
    ])


@callback(Output("camas-censos_guardados", "data"), Output("camas-nota_r7", "children"),
          Input("camas-simular", "n_clicks"),
          State("camas-ajuste_ingresos", "value"), State("camas-ajuste_estancia", "value"),
          State("camas-intensidad_d", "value"), State("camas-plazo", "value"))
def correr_simulacion(_, pct_ingresos, pct_estancia, intensidad_d, dias):
    me, mr = (mezcla_escenario_d(intensidad_d / 100) if intensidad_d else (None, None))
    fechas, censos = scm.simular(scm.serie_ingresos, scm.ULTIMO_CONFIABLE, dias,
                                  ajuste_ingresos=1 + pct_ingresos / 100, ajuste_estancia=1 + pct_estancia / 100,
                                  n_rep=N_REP_INTERACTIVO, mezcla_edad=me, mezcla_ruta=mr)
    nota = ""
    if pct_estancia < 0:
        nota = html.Div([html.B("R7 (recomendaciones): "),
                          "revisión semanal de pacientes con más de 7 días de estancia, con gestión de casos, foco en "
                          "más de 14 días. Bajar la estancia 5 % libera ~5 camas según la ley de Little; volver a la "
                          "estancia de 2023, ~15."], style={"border": f"1px solid {VERDE}", "borderRadius": "6px", "padding": "6px 10px"})
    data = {"fechas": [str(f.date()) for f in fechas], **{g: censos[g].tolist() for g in GRUPOS}}
    return data, nota


@callback(Output("camas-grafico_proyeccion", "figure"), Output("camas-metricas", "children"),
          Input("camas-censos_guardados", "data"), Input("camas-grupo", "value"),
          State("theme-store", "data"))
def mostrar(data, grupo, tema):
    if not data:
        return go.Figure(), []
    fechas = pd.to_datetime(data["fechas"])
    censos = {g: np.array(data[g]) for g in GRUPOS}
    c = censos[grupo]
    p10, p50, p90 = np.percentile(c, 10, axis=0), np.percentile(c, 50, axis=0), np.percentile(c, 90, axis=0)
    cap_hun = scm.CAPACIDAD[grupo]

    sobre = p50 > cap_hun                                    # dias (de la mediana simulada) sin camas suficientes
    # La linea naranja debe ser el punto EXACTO donde el color cambia: en vez de compartir los dos puntos reales
    # que rodean la transicion (eso deja que cada tramo "se pase" del umbral, porque uno de los dos puntos
    # reales que comparten esta por definicion del otro lado), se interpola el cruce exacto (x, cap_hun) entre
    # cada par de puntos consecutivos que cambian de lado y se inserta ESE punto (no los reales) en ambas series.
    x_normal, y_normal, x_sobre, y_sobre, deficit_normal, deficit_sobre = [], [], [], [], [], []
    n = len(p50)
    for i in range(n):
        valor, deficit_i = float(p50[i]), max(float(p50[i]) - cap_hun, 0.0)
        if sobre[i]:
            x_sobre.append(fechas[i]); y_sobre.append(valor); deficit_sobre.append(deficit_i)
        else:
            x_normal.append(fechas[i]); y_normal.append(valor); deficit_normal.append(0.0)
        if i < n - 1 and sobre[i] != sobre[i + 1]:
            frac = (cap_hun - float(p50[i])) / (float(p50[i + 1]) - float(p50[i]))
            x_cruce = fechas[i] + frac * (fechas[i + 1] - fechas[i])
            x_normal.append(x_cruce); y_normal.append(cap_hun); deficit_normal.append(0.0)
            x_sobre.append(x_cruce); y_sobre.append(cap_hun); deficit_sobre.append(0.0)
    deficit = np.clip(p50 - cap_hun, 0, None)                 # pacientes sin cama ese dia, segun la mediana simulada (para el panel)

    fig = go.Figure([
        go.Scatter(x=fechas, y=p90, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"),
        go.Scatter(x=fechas, y=p10, mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(42,111,176,0.15)",
                   name="Banda 10-90 %", hoverinfo="skip"),
        go.Scatter(x=x_normal, y=y_normal, mode="lines", line=dict(color=AZUL, width=2), name="Pacientes en cama",
                   customdata=deficit_normal, hovertemplate="%{x|%d-%m-%Y}<br>%{y:.0f} pacientes en cama<extra></extra>"),
        go.Scatter(x=x_sobre, y=y_sobre, mode="lines", line=dict(color=ROJO, width=2.5), name="Sin cama suficiente",
                   customdata=deficit_sobre, hovertemplate="%{x|%d-%m-%Y}<br><b>%{customdata:.0f} pacientes sin cama ese día</b><extra></extra>"),
        go.Scatter(x=fechas, y=[cap_hun] * len(fechas), mode="lines", line=dict(color=NARANJA, dash="dash"),
                   name=f"Capacidad HUN ({cap_hun})", hoverinfo="skip"),
    ])
    fig.update_layout(title=f"Ocupación proyectada — {NOMBRES_GRUPO[grupo]}", yaxis_title="Pacientes en cama",
                      template="simple_white", legend=dict(orientation="h", y=-0.2), margin=dict(l=40, r=20, t=50, b=40))

    pct_sat = round(100 * float((c > cap_hun).mean()), 1)
    dias_sin_cama = int((p50 > cap_hun).sum())
    medias = {"mejor": float(p10.mean()), "base": float(p50.mean()), "peor": float(p90.mean())}
    metricas = panel_metricas_animado(medias, cap_hun, pct_sat, dias_sin_cama, len(fechas))

    dark = tg.es_oscuro(tema)
    tg.aplicar(fig, dark)
    return fig, metricas
