"""
dashboard/pages/pronostico.py  -  pagina del dashboard multipagina (10-nov-2026, migrada de dashboard/app.py v4;
rediseno del 13-nov-2026: controles tipo switch centrados, recuadro rotativo de metricas, rango con animacion
estable por ids fijos, y panel tecnico con la estacionalidad anual de Samuel (ficha A9))
PRONOSTICO DE DEMANDA INTERACTIVO. El usuario elige solo DOS cosas: hasta cuando quiere ver y que quiere ver
(ingresos al hospital o ingresos a cama). El modelo corre en el momento (menos de 0,1 s porque trabaja sobre
el panel diario ya agregado, sin pacientes) y el grafico muestra como cambian los datos.

REDISEÑO (13-nov-2026):
  - Controles sin numeracion, centrados como fila (clase "control-row").
  - "Total esperado" y "Error tipico" viven en UN solo recuadro centrado ("lead-rotator") que alterna entre
    las dos metricas con una animacion de deslizamiento, en bucle, por CSS puro (sin depender del servidor).
  - La metrica de rango ("range-metric") ahora usa ids FIJOS para el relleno, el punto y las etiquetas de los
    extremos: el calback solo cambia su `style`/`children`, nunca reemplaza los nodos, asi que la transicion
    CSS (theme.css, .range-metric__fill/marker/endlabel) si se ve al cambiar los controles.
  - Panel tecnico nuevo (para evaluadores): linea de tiempo de como se construyo el modelo (pasar el mouse por
    cada etapa), el comparativo de error con/sin la forma del año (ficha A9, src/estacionalidad_anual.py y
    rondas siguientes: dengue, GAM, IRA y EDA del SIVIGILA) y la tabla de que se probo y se descarto. Fuente:
    docs/estacionalidad_anual.md y docs/documento_final.md seccion 6.1 (version del 13-nov-2026).

Misma logica de datos que la version standalone (dashboard/app.py, ya retirada); solo cambian los ids de
componentes (prefijo "pron-") para que no choquen con las otras paginas en la misma app, y el registro con
`dash.register_page` en vez de crear su propio `Dash(__name__)`.

DATOS  datos/procesados/para_equipo/panel_diario.csv. NO se conecta a la base del hospital.
MODELO src/modelo_pronostico.py
"""
import sys
from pathlib import Path

import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))        # dashboard/ para el tema de graficos
import modelo_pronostico as mp  # noqa: E402
import tema_graficos as tg  # noqa: E402
from componentes import mensaje, metodo  # noqa: E402

dash.register_page(__name__, path="/pronostico", name="Pronóstico", title="Pronóstico de demanda - HUN", order=1)

SUPUESTO = "historico"                                      # nivel de los 12 meses del periodo confiable

# Carga perezosa y defensiva: con `use_pages=True` TODAS las paginas se importan al arrancar `main.py`, asi que
# si panel_diario.csv no esta disponible en este equipo (vive fuera del repo, CLAUDE.md), no debe tumbar el
# arranque de las otras 3 paginas -- se muestra un aviso en vez de la pagina (igual patron que perfiles.py).
try:
    LIMPIO = mp.cargar_panel()                                  # el modelo se entrena sin los dias atipicos ni los posteriores al 9-abr-2026
    REAL = mp.cargar_panel(limpiar=False)                       # lo que se dibuja como "lo que paso": todos los dias
    SERIES = {obj: LIMPIO[obj] for obj in mp.OBJETIVOS}
    # El backtest de la banda usa el MISMO escenario que el pronostico que se dibuja (SUPUESTO="historico"), para que la banda
    # incluya la incertidumbre del nivel anclado; paso=7 da mas cortes y estabiliza los tramos largos. Se calcula una vez al abrir la app.
    BT = {obj: mp.retroceso(s, paso=7, escenario=SUPUESTO) for obj, s in SERIES.items()}
    ERR = {obj: mp.tabla_error(BT[obj], sin_caida=True) for obj in mp.OBJETIVOS}
    ULTIMO_CONFIABLE = LIMPIO.dropna(how="all").index.max()     # 9-abr-2026
    ULTIMO_REAL = REAL.dropna(how="all").index.max()
    DATOS_OK = True
except (FileNotFoundError, OSError):
    DATOS_OK = False

GRIS, AZUL, ROJO, VERDE = "#6b6b6b", "#2a6fb0", "#c0392b", "#2e9b5b"
PLAZOS = [("7 días", 7), ("30 días", 30), ("6 meses", 182), ("1 año", 365)]
QUE_VER = {"llegadas_con_atencion": "Ingresos al hospital (pacientes que llegan a urgencias)",
           "ingresos_a_cama": "Ingresos a cama (pacientes que se hospitalizan)"}
CORTO = {"llegadas_con_atencion": "ingresos al hospital por día", "ingresos_a_cama": "ingresos a cama por día"}
INFO_VER = {"llegadas_con_atencion": "Pacientes que llegan a urgencias y reciben alguna atención, se hospitalicen o no.",
            "ingresos_a_cama": "Pacientes que quedan hospitalizados, es decir, que llegan a ocupar una cama."}

# ----------------------------------------------------------------------
# Panel tecnico: comparativo de error con/sin la forma del año (ficha A9), numeros tal como quedaron en
# docs/documento_final.md seccion 6.1 (version del 13-nov-2026) y docs/estacionalidad_anual.md.
# ----------------------------------------------------------------------
TRAMOS_WAPE = ["1-7 días", "1-3 meses", "3-6 meses", "6-12 meses"]
COMPARATIVO_WAPE = {
    "llegadas_con_atencion": {
        "nombre_sin": "Sin la forma del año", "nombre_con": "Con el dengue (vigente)",
        "sin": [8.0, 9.3, 11.4, 11.6], "con": [8.0, 8.6, 9.1, 9.6],
    },
    "ingresos_a_cama": {
        "nombre_sin": "Solo la curva del año (GAM)", "nombre_con": "+ IRA y EDA del SIVIGILA (vigente)",
        "sin": [18.2, 19.3, 19.7, 19.4], "con": [18.0, 18.7, 19.3, 19.0],
    },
}

ETAPAS_PIPELINE = [
    ("1. Calendario", "Variables de día de la semana, festivos de Colombia, víspera/día después, fin de "
     "año y Semana Santa y Carnaval de Barranquilla (~17 % menos llegadas), calculadas para cualquier fecha "
     "pasada o futura con holidays y la fecha de Pascua."),
    ("2. Regresión de Poisson", "Un modelo de Poisson con enlace logarítmico, ajustado a mano por mínimos "
     "cuadrados reponderados iterativamente (IRLS, sin librerías de estadística), sobre esas variables de "
     "calendario y el nivel de los últimos 12 meses confiables."),
    ("3. Backtest (retroceso)", "Se pronostican 365 días desde muchos cortes del pasado (cada 7-14 días, "
     "desde el día 400 de los datos) y se compara contra lo que de verdad pasó después — así se mide el "
     "error por plazo de anticipación sin usar el futuro para calibrar."),
    ("4. Forma del año (A9)", "Con solo ~3 ciclos anuales confiables no se puede aprender la estacionalidad "
     "directamente. Se probaron 7 fuentes externas públicas (dengue, IRA, EDA, lluvia, temperatura, "
     "calendario escolar, El Niño, población) y se adoptó solo lo que mejoraba la validación sin empeorar "
     "el corto plazo, confirmado luego en la prueba de 2026."),
    ("5. Banda recalibrada", "Para cada plazo de anticipación se eligió el percentil de error que cubre al "
     "menos el 80 % de los días en una validación aparte, con un límite para que la banda no se angoste al "
     "crecer el horizonte."),
]

TABLA_DECISIONES = [
    ("Climatología de dengue (SIVIGILA, 2 semanas antes)", "Entra en llegadas", "Mejora 3-12 meses; describe la forma del año (efecto negativo, no causal)"),
    ("Curva cíclica del año (GAM, 4 grados de libertad)", "Entra en ingresos a cama", "Mejora pequeña, confirmada en la prueba de 2026"),
    ("IRA + EDA (SIVIGILA, misma semana)", "Entra en ingresos a cama", "Mejora validación y prueba en todos los plazos"),
    ("Armónicos de Fourier (1-3, aprendidos de nuestros datos)", "No entra", "Peor que el dengue; empeora el corto plazo en la prueba"),
    ("Lluvia (NASA POWER e IDEAM) y temperatura", "No entra", "Sin mejora clara; la del IDEAM empeora la prueba de 2026"),
    ("Calendario escolar oficial de Barranquilla", "No entra", "Empeora las dos series (se solapa con festivos ya modelados)"),
    ("Índice de El Niño (ONI) y población (DANE)", "No entra", "Efecto nulo en las dos series"),
    ("Modelo SARIMAX (alternativa a Poisson)", "No entra", "Mejor en validación, pero peor a 1-7 días y en la prueba de 2026"),
]


def hoy():
    return pd.Timestamp.today().normalize()


def info_badge(texto):
    return html.Span(className="info-badge tooltip-trigger", children=[
        "i", html.Span(texto, className="tooltip-content")])


def opcion_icono(ico, texto_info):
    return html.Span(className="pill-icon-option", children=[
        html.Span(className=f"nav__ico {ico}"), info_badge(texto_info)])


def tabla_error_popup(e, lead0):
    """Tabla completa de error por horizonte (los 5 tramos de retroceso()/tabla_error()), con el tramo
    vigente resaltado -- se muestra en el popup de la metrica "Error típico"."""
    filas = [html.Tr([html.Th("Días"), html.Th("Error"), html.Th("Sesgo"), html.Th("Cobertura 80%")])]
    for _, r in e.iterrows():
        a, b = (int(x) for x in r.tramo_dias.split("-"))
        vigente = a <= lead0 <= b
        estilo = {"fontWeight": 700, "color": AZUL} if vigente else {}
        filas.append(html.Tr(style=estilo, children=[
            html.Td(f"{r.tramo_dias} d" + (" ←" if vigente else "")), html.Td(f"{r.wape_pct:.0f} %"),
            html.Td(f"{r.sesgo_pct:+.0f} %"), html.Td(f"{r.cobertura_80_pct:.0f} %")]))
    return html.Div([
        html.Div("Error validado contra el pasado, por qué tan lejos se pronostica:", className="metodo__rotulo"),
        html.Table(filas),
        html.Div("Cobertura 80 %: de los días ya conocidos, qué % cayó dentro del rango probable que se dibujó para ese plazo.",
                 style={"color": GRIS, "marginTop": "6px", "fontSize": "11px"}),
    ])


def _pos(v, lo, hi):
    return max(0.0, min(100.0, (v - lo) / (hi - lo) * 100))


def posiciones_rango(mean_val, low, high):
    """Devuelve (pos_low, pos_high, pos_mean) en % sobre una escala con margen alrededor de low/high."""
    ancho = max(high - low, max(mean_val * 0.05, 1.0))
    esc_lo, esc_hi = max(0.0, low - ancho * 0.4), high + ancho * 0.4
    esc_hi = max(esc_hi, esc_lo + 1.0)
    return _pos(low, esc_lo, esc_hi), _pos(high, esc_lo, esc_hi), _pos(mean_val, esc_lo, esc_hi)


def panel_contexto():
    """Panel de 4 partes que ya define docs/estructura_dashboard.md (seccion 2): que se ve, como se calculo,
    que significa para el hospital y que NO dice. Para el personal del hospital, en palabras simples."""
    return html.Details(className="metodo metodo--panel", children=[
        html.Summary([html.Span("¿Cómo se interpreta?", className="metodo__titulo"), html.Span("qué ves, cómo se calculó y qué no dice", className="metodo__sub")]),
        html.Div(className="metodo__apilado", style={"display": "grid"}, children=[
            html.Div([html.Div("Qué estás viendo", className="metodo__rotulo"),
                      html.Div("Cuántos pacientes se espera que lleguen (o se hospitalicen) cada día desde hoy, "
                               "con una zona sombreada que muestra el rango dentro del cual probablemente va a "
                               "caer el valor real.")]),
            html.Div([html.Div("Cómo se calculó", className="metodo__rotulo"),
                      html.Div("Con el calendario del hospital (día de la semana, festivos, Semana Santa, Carnaval) "
                               "y el nivel de pacientes de los meses confiables (febrero de 2023 a abril de 2026). "
                               "El ancho de la zona sombreada se calibró revisando, muchas veces en el pasado, qué "
                               "tan lejos estuvo este mismo método de la realidad (pasa el mouse sobre «Error "
                               "típico» para ver el detalle por plazo).")]),
            html.Div([html.Div("Qué significa para el hospital", className="metodo__rotulo"),
                      html.Div("Sirve para anticipar la carga de los próximos días o meses y planear personal y "
                               "camas con tiempo. Para decisiones de corto plazo (días) es más preciso; para "
                               "decisiones de largo plazo (meses) hay que mirar todo el rango, no solo la línea "
                               "central. Los ingresos a cama de un día suelto son casi ruido de conteo: para planear camas "
                               "conviene mirar el total de la semana (en la versión anterior del modelo, el error de los ingresos a cama "
                               "bajaba de ~22 % por día a 9,5 % por semana). "),
                      dcc.Link("Cómo se eligió este modelo y qué alternativas se descartaron", href="/modelos", className="enlace-chip")]),
            html.Div([html.Div("Qué NO dice", className="metodo__rotulo"),
                      html.Div("No anticipa brotes, cortes del sistema de registro, ni cambios del hospital después "
                               "del 9 de abril de 2026 (el registro de ese momento en adelante está incompleto y no "
                               "se usa para calcular el nivel). Es una tendencia con incertidumbre, no una promesa "
                               "exacta para un día puntual.")]),
        ]),
    ])


def panel_tecnico():
    """Panel para evaluadores/jueces: como se construyo el modelo (linea de tiempo interactiva), la
    estacionalidad anual que agrego Samuel integrando datos externos (ficha A9) y que se probo y se descarto.
    Fuente: docs/estacionalidad_anual.md y docs/documento_final.md seccion 6.1."""
    pasos = [html.Div(className="pipeline__step tooltip-trigger", children=[
                html.Div(className="pipeline__dot"), html.Div(titulo, className="pipeline__label"),
                html.Span(detalle, className="tooltip-content")])
             for titulo, detalle in ETAPAS_PIPELINE]
    filas_decision = [html.Tr([html.Th("Variable probada"), html.Th("Resultado"), html.Th("Por qué")])] + [
        html.Tr([html.Td(v), html.Td(r, style={"fontWeight": 700, "color": VERDE if "Entra" in r else GRIS}), html.Td(por_que)])
        for v, r, por_que in TABLA_DECISIONES]
    return html.Details(className="metodo metodo--panel", children=[
        html.Summary([html.Span("Ficha técnica del pronóstico", className="metodo__titulo"), html.Span("cómo se construyó y qué se probó", className="metodo__sub")]),
        html.Div(className="metodo__apilado", children=[
            html.Div([
                html.Div("Etapas de construcción (pasa el mouse sobre cada una)", className="metodo__rotulo"),
                html.Div(className="pipeline", children=pasos),
            ]),
            html.Div([
                html.Div([html.B("La forma del año (ficha A9, "), html.Code("src/estacionalidad_anual.py"), html.B("). "),
                          "Con solo ~3 ciclos anuales confiables en el hospital, el modelo no podía aprender solo de sus "
                          "propios datos qué meses tienen más pacientes. Se tomó prestada la ", html.B("forma típica del año"),
                          " (no los valores futuros) de climatologías públicas de muchos años, probando 7 fuentes y "
                          "aceptando solo lo que mejoraba la validación de jul-dic 2025 sin empeorar el corto plazo, y "
                          "confirmándolo después en la prueba de 2026 (datos que no se usaron para elegir)."],
                         style={"marginBottom": "10px", "lineHeight": "1.6"}),
                html.Div(["El error con y sin la forma del año, por horizonte, está en ", dcc.Link("Resultados · Forma del año", href="/estacionalidad"), "."],
                         style={"fontSize": "13px", "color": GRIS}),
            ]),
            html.Div([
                html.Div("Qué se probó y qué se descartó", className="metodo__rotulo"),
                html.Div(html.Table(filas_decision, className="metodo__tabla"), className="metodo__scroll"),
                html.Div("Detalle completo de cada ronda de prueba (datos, fuentes y por qué se descartó cada una): "
                         "docs/estacionalidad_anual.md. Documento final del equipo con las 7 recomendaciones y sus "
                         "fuentes: docs/documento_final.pdf.", style={"color": GRIS, "fontSize": "11.5px", "marginTop": "8px"}),
            ]),
        ]),
    ])


def layout():
    """El diseno se arma cada vez que se abre la pagina, para que "hoy" sea siempre el dia actual."""
    if not DATOS_OK:
        return html.Div(className="page-container", children=[
            html.H2("Pronóstico de demanda"),
            html.P("Los datos no están disponibles en este equipo (falta datos/procesados/para_equipo/panel_diario.csv, "
                   "que vive fuera del repositorio). Pedir la tabla al equipo o regenerarla con "
                   "src/exportar_para_equipo.py.", style={"color": "#c0392b"}),
        ])
    return html.Div(className="page-container", children=[
        html.Div(className="page-head", children=[
            html.H2("¿Cuántos pacientes ingresarán al hospital?"),
            html.P(f"Estimación para los próximos días a partir de hoy, {hoy():%d-%m-%Y}, según la historia confiable del hospital. "
                   "Elige dos cosas y el gráfico se actualiza.", className="page-head__sub"),
        ]),

        html.Div(className="control-row", children=[
            html.Div(className="control-group", children=[
                html.Span("¿Hasta cuándo quieres ver?", className="control-group__label"),
                dcc.RadioItems(id="pron-plazo", className="pill-switch",
                               options=[{"label": n, "value": d} for n, d in PLAZOS], value=30)]),
            html.Div(className="control-group", children=[
                html.Span("¿Qué quieres ver?", className="control-group__label"),
                dcc.RadioItems(id="pron-objetivo", className="pill-switch pill-switch--icons",
                               options=[{"label": opcion_icono("ico-patient", INFO_VER["llegadas_con_atencion"]), "value": "llegadas_con_atencion"},
                                        {"label": opcion_icono("ico-bed", INFO_VER["ingresos_a_cama"]), "value": "ingresos_a_cama"}],
                               value="llegadas_con_atencion")]),
        ]),

        # Fila resumen: recuadro rotativo (izq) + metrica de rango (der), ocupando el ancho de la pagina
        html.Div(className="pron-summary", children=[
            # Recuadro rotativo: Total esperado <-> Error tipico (un solo recuadro, animacion por CSS)
            html.Div(className="lead-rotator", children=[
                html.Div(className="lead-rotator__slide lead-rotator__slide--a", children=[
                    html.Div("Total esperado", className="lead-rotator__title"),
                    html.Div(id="pron-lead-a-value", className="lead-rotator__value"),
                    html.Div(id="pron-lead-a-detail", className="lead-rotator__detail"),
                ]),
                html.Div(className="lead-rotator__slide lead-rotator__slide--b tooltip-trigger", children=[
                    html.Div("Error típico", className="lead-rotator__title"),
                    html.Div(id="pron-lead-b-value", className="lead-rotator__value"),
                    html.Div(id="pron-lead-b-detail", className="lead-rotator__detail"),
                    html.Div(id="pron-lead-b-popup", className="tooltip-content"),
                ]),
                html.Div(className="lead-rotator__dots", children=[html.Div(className="lead-rotator__dot"), html.Div(className="lead-rotator__dot")]),
            ]),

            # Metrica de rango: ids fijos para que el callback solo cambie estilo/texto (asi SI se anima)
            html.Div(className="range-metric", children=[
                html.Div("Se espera por día (rango probable, 8 de cada 10 casos)", className="range-metric__title"),
                html.Div(className="range-metric__line", children=[
                    html.Div(className="range-metric__track"),
                    html.Div(id="pron-range-fill", className="range-metric__fill"),
                    html.Div(id="pron-range-low", className="range-metric__endlabel"),
                    html.Div(id="pron-range-high", className="range-metric__endlabel"),
                    html.Div(id="pron-range-marker", className="range-metric__marker", children=[
                        html.Div(id="pron-range-marker-value", className="range-metric__marker-value"),
                        html.Div(className="range-metric__marker-dot"),
                    ]),
                ]),
                html.Div("El punto azul es el promedio esperado; los extremos de la línea son el rango dentro del cual "
                         "cae el valor real la mayoría de los días.", className="range-metric__caption"),
            ]),
        ]),

        html.Div(className="page-section", children=[dcc.Graph(id="pron-grafico", config={"displaylogo": False})]),
        mensaje("**Sirve para planear la semana, no para adivinar un día.** A una semana el pronóstico de llegadas se equivoca cerca de 8 % y a un "
                "año cerca de 10 %. Los ingresos a cama de un día son más ruidosos (~18 %), pero por semana el error baja a ~9,5 %, que es como se "
                "planean las camas. Úselo para dimensionar turnos y camas por semana y para anticipar la temporada alta de mitad de año."),
        panel_contexto(),
        metodo("Un modelo de conteos (regresión de Poisson) que combina el calendario (día de la semana, festivos, Semana Santa, fin de año y "
               "Carnaval, que baja las llegadas ~17 %), el nivel reciente del hospital y la **forma del año**, tomada de datos públicos de vigilancia "
               "(dengue para las llegadas; infección respiratoria y diarrea para los ingresos a cama). Se entrenó con feb-2023 a jun-2025 y se probó "
               "con meses que no había visto; el rango probable del 80 % sale de los errores de esa prueba y en las llegadas cubre el 78–82 % de los días.",
               "No anticipa brotes, cortes de sistema ni lo que haya cambiado en el hospital después del 9-abr-2026, el último dato confiable. No dice "
               "cuántos pacientes quedarán sin atender ni cuánto esperará cada uno (eso está en «Paciente en espera»). Las llegadas incluyen ~4 % de "
               "registros replicados, estables en el tiempo.",
               "Fuente: src/modelo_pronostico.py sobre panel_diario.csv (agregado por día, sin pacientes). Detalle: documentación, sección 6.1, y docs/estacionalidad_anual.md.", ruta="/pronostico"),
        panel_tecnico(),
    ])


@callback(
    Output("pron-grafico", "figure"),
    Output("pron-lead-a-value", "children"), Output("pron-lead-a-detail", "children"),
    Output("pron-lead-b-value", "children"), Output("pron-lead-b-detail", "children"), Output("pron-lead-b-popup", "children"),
    Output("pron-range-fill", "style"), Output("pron-range-low", "style"), Output("pron-range-low", "children"),
    Output("pron-range-high", "style"), Output("pron-range-high", "children"),
    Output("pron-range-marker", "style"), Output("pron-range-marker-value", "children"),
    Input("pron-plazo", "value"), Input("pron-objetivo", "value"), State("theme-store", "data"),
)
def actualizar(dias, objetivo, tema):
    dark = tg.es_oscuro(tema)
    if not DATOS_OK:                                            # no deberia dispararse (sin datos no se renderizan los controles), defensivo
        vacio = go.Figure()
        return (vacio, "", "", "", "", "", {}, {}, "", {}, "", {}, "")
    serie, bt = SERIES[objetivo], BT[objetivo]
    desde = hoy()
    f = mp.pronostico_con_banda(serie, bt, dias, SUPUESTO, 0.0, True, False, desde)
    nombre = CORTO[objetivo]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=f.fecha, y=f.banda_alta, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=f.fecha, y=f.banda_baja, mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(42,111,176,0.15)", name="Rango probable (8 de cada 10 casos)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=f.fecha, y=f.pronostico, mode="lines", line=dict(color=AZUL, width=2.4), name="Lo que se espera",
                             customdata=np.c_[f.banda_baja, f.banda_alta],
                             hovertemplate="%{x|%d-%m-%Y}<br>Se espera: %{y:.0f}<br>Rango probable: %{customdata[0]:.0f} a %{customdata[1]:.0f}<extra></extra>"))
    fig.update_layout(title=f"{nombre.capitalize()} esperados, día por día", hovermode="x unified", legend=dict(orientation="h", y=-0.15),
                      margin=dict(l=40, r=20, t=60, b=40), yaxis_title=nombre, template="simple_white")
    fig.update_xaxes(tickformat="%d-%m" if dias <= 30 else "%m-%Y")      # fechas en numeros (plotly escribe los meses en ingles)
    tg.aplicar(fig, dark)

    e = ERR[objetivo]
    lead0 = int(f.dias_adelante.iloc[0])
    fila = e[e.tramo_dias.map(lambda t: int(t.split("-")[0]) <= lead0)].iloc[-1]
    meses = lead0 / 30.4

    lead_a_val = f"{f.pronostico.sum():,.0f}".replace(",", ".")
    lead_a_det = f"ingresos en los próximos {dias} días"
    lead_b_val = f"{fila.wape_pct:.0f} %"
    lead_b_det = f"por día; dato de hace ~{meses:.0f} meses — con el recuadro visible, pasa el mouse para el detalle"
    lead_b_popup = tabla_error_popup(e, lead0)

    p_low, p_high, p_mean = posiciones_rango(f.pronostico.mean(), f.banda_baja.mean(), f.banda_alta.mean())
    estilo_fill = {"left": f"{p_low}%", "width": f"{p_high - p_low}%"}
    estilo_low = {"left": f"{p_low}%"}
    estilo_high = {"left": f"{p_high}%"}
    estilo_marker = {"left": f"{p_mean}%"}


    return (fig, lead_a_val, lead_a_det, lead_b_val, lead_b_det, lead_b_popup,
            estilo_fill, estilo_low, f"{f.banda_baja.mean():.0f}", estilo_high, f"{f.banda_alta.mean():.0f}",
            estilo_marker, f"{f.pronostico.mean():.0f}")
