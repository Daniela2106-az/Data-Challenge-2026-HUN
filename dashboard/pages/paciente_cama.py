"""
dashboard/pages/paciente_cama.py  -  pagina del dashboard multipagina (19-nov-2026)
Tarea A6b: ¿CUANTO TIEMPO MAS SEGUIRA EN CAMA ESTE PACIENTE?

Espeja dashboard/pages/paciente.py (el estimador de la ESPERA de cama, "Paciente en espera"): mismo
patron de formulario, tarjetas, grafico con doble vista y ficha tecnica plegable. La diferencia de
fondo esta en el modelo que consulta (src/estimador_estancia_restante.py) y en que responde una
pregunta distinta: no "¿cuando le darán cama?" sino "paciente YA hospitalizado, ¿cuánto le falta para
el alta?".

POR QUE SE VUELVE A INTENTAR
Un estimador de estancia se habia descartado antes por mala precision: una prueba rapida (21-oct) con
regresion directa al ingreso dio R2≈0 (igual que adivinar la mediana), y un modelo explicativo
posterior (src/factores_estancia.py, 3-nov) con mas variables (incl. diagnostico) solo llego a
R2=7,9-10,8%. Ambos entrenaban UN SOLO modelo al momento del ingreso, prediciendo la estancia TOTAL.
Lo que no se habia probado es la misma arquitectura que si funciona para la espera: un modelo por cada
hora YA PASADA en cama ("landmark"), reestimando el riesgo de alta con lo que se sabe en ese momento.
Resultado medido (src/comparar_estimadores_estancia.py, prueba jul-2025 a 9-ene-2026): mejora modesta
y real frente al rango por perfil que ya usa el dashboard (que_esperar.py) -- se declara tal cual,
sin maquillarla, en la ficha tecnica de esta pagina. Se publica igual, con esos limites explicitos.

CAMBIOS RESPECTO A /paciente (no es un espejo literal)
  - "Horas que lleva esperando" -> "Horas que lleva en cama" (el reloj es desde la asignacion de cama).
  - Se quita el bloque de "etapas en urgencias": no aplica a una estancia ya iniciada.
  - Se mantiene, visible y desplegable, "Si ya estuvo hospitalizado antes" (a diferencia del rediseno
    del 14-nov de /paciente, que lo escondio): aqui se deja porque el historial de estancias previas es
    la unica fuente de diagnostico que no tiene riesgo de fuga.
  - El grafico usa bloques POR DIA (1 a 10 dias + "mas de 10 dias"), no por franja de 4 bloques: la
    estancia mediana (~70 h) es mucho mayor que la espera mediana (~18,6 h) y los bloques de 4 franjas
    por dia dejarian casi toda la probabilidad en "despues".
  - No pide ni usa el diagnostico de ESTA estancia (fuga: casi todos los diagnosticos se registran
    tarde); solo el de una hospitalizacion ANTERIOR, si la hubo.

DATOS  No se conecta a la base. Usa el modelo guardado (fuera del proyecto, se entrena al primer uso).
"""
import sys
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))        # dashboard/ para el tema de graficos y los widgets compartidos
import comparar_estimadores_estancia as cee  # noqa: E402
import confianza_perfil as cp  # noqa: E402
import estimador_estancia_restante as eer  # noqa: E402
import tema_graficos as tg  # noqa: E402
from componentes import mensaje, metodo  # noqa: E402

from eleccion_modelos import tarjeta_eleccion  # noqa: E402
from componentes import ETAPAS_Y_PRUEBAS, secciones  # noqa: E402
from widgets_paciente import GRUPOS_DX, LABS_FUERA, TIPOS_INFO, info_badge, stepper, tabla_html, tarjeta, rango_widget, campo_stepper_clientside  # noqa: E402

dash.register_page(__name__, path="/paciente-cama", name="Paciente en cama", title="¿Cuánto le falta de estancia? - HUN", order=3)

GRIS, AZUL, NARANJA = "#6b6b6b", "#2a6fb0", "#eb6834"

campo_stepper_clientside("pec-edad", 0, 110)
campo_stepper_clientside("pec-horas", 0, cee.MAX_H_ESTANCIA - 1)

# ----------------------------------------------------------------------
# Ficha tecnica
# ----------------------------------------------------------------------
ETAPAS_PIPELINE_A6B = [
    ("1. Preparar los datos", "Para cada hora YA PASADA en cama (0, 6, 12, 24 y 48 h) se construye una fila "
     "por cada estancia que seguía en cama en ese momento, con todo lo que se sabía al llegar a la cama. Desde "
     "las 72 h se usa un solo modelo combinado."),
    ("2. Un modelo por landmark", "5 modelos de árboles de gradiente (HistGradientBoostingClassifier), cada "
     "uno entrenado solo con quienes seguían en cama a esa hora exacta, más un modelo combinado desde las 72 h "
     "-- se probó un landmark propio también en 72/120/168 h y midió peor que el modelo combinado en los tres "
     "puntos (muestra ya chica: 1.954/1.219/814 estancias en la prueba), por eso el corte quedó en 72 h."),
    ("3. Censura correcta", "Las estancias sin alta resuelta (aún hospitalizadas, o que terminan después del "
     "periodo confiable) no se descartan: siguen aportando como censuradas (en riesgo, sin marcar un alta que "
     "no se sabe si ocurrió). Los dos intentos anteriores las descartaban, sesgando contra las estancias largas."),
    ("4. Evitar la fuga del diagnóstico", "Casi todos los diagnósticos se registran tarde (la mayoría después "
     "de la mitad de la estancia). Por eso el modelo NO usa el diagnóstico de esta estancia, solo el de una "
     "hospitalización anterior, si la hubo."),
    ("5. Medir contra el rango por perfil", "El punto de comparación no es R² (ya se sabía que falla, ver "
     "abajo) sino la pérdida de cuantiles frente al rango por perfil que ya usa el dashboard (que_esperar.py)."),
]


# Cifras de src/comparar_estimadores_estancia.py (prueba jul-2025 a 9-ene-2026; 72/120/168 h ya usan el
# modelo agrupado, mejor medido alli que un landmark propio -- ver cabecera de ese script).
HORAS_MEJORA_ESTANCIA = ["0 h", "6 h", "12 h", "24 h", "48 h", "72 h", "120 h", "168 h"]
MEJORA_ESTANCIA = [1.7, 1.7, 1.6, 1.5, 1.2, 0.6, -0.7, -0.4]


def grafico_mejora_estancia():
    """Mejora (%) de este modelo frente al rango por perfil (que_esperar.py), por hora ya en cama --
    src/comparar_estimadores_estancia.py. Los dos intentos anteriores (regresión al ingreso) se citan aparte,
    en R², porque nunca llegaron a medirse con esta misma métrica de pérdida de cuantiles."""
    fig = go.Figure([go.Bar(x=HORAS_MEJORA_ESTANCIA, y=MEJORA_ESTANCIA, marker_color=AZUL,
                            hovertemplate="%{x}<br>%{y:.1f} %% de mejora<extra></extra>")])
    fig.add_hline(y=0, line_color=GRIS, line_width=1)
    fig.update_layout(title="Mejora frente al rango por perfil (que_esperar.py), por hora ya en cama",
                      yaxis_title="Mejora (%)", template="simple_white", margin=dict(l=40, r=20, t=50, b=40))
    return fig


def panel_interpretacion():
    return html.Details(className="metodo metodo--panel", children=[
        html.Summary([html.Span("¿Cómo se interpreta?", className="metodo__titulo"), html.Span("qué ves, cómo se calculó y qué no dice", className="metodo__sub")]),
        html.Div(className="metodo__apilado", children=[
            html.Div([html.Div("Qué estás viendo", className="metodo__rotulo"),
                      html.Div("La probabilidad de que el paciente reciba el alta en cada uno de los próximos 10 días, y "
                               "un bloque final que junta todo lo que sigue después.")]),
            html.Div([html.Div("Cómo se calculó", className="metodo__rotulo"),
                      html.Div("Con un modelo entrenado en la historia del hospital que, a partir del paciente y cuántas "
                               "horas ya lleva en cama, calcula qué tan probable es el alta en cada día (detalle completo "
                               "más abajo, en la ficha técnica).")]),
            html.Div([html.Div("Qué significa cada cosa del gráfico", className="metodo__rotulo"),
                      html.Ul([
                          html.Li("La barra naranja es el día con mayor probabilidad de alta."),
                          html.Li("«Día 1» es el día de hoy (desde ahora hasta la misma hora de mañana), no el calendario."),
                          html.Li("«Más de 10 días» junta TODO lo que sigue, sin límite: no es comparable con un bloque de 24 h."),
                      ], style={"marginTop": "4px"})]),
            html.Div([html.Div("El switch «Normal / Acumulada»", className="metodo__rotulo"),
                      html.Div("«Normal» (barras) responde «¿en qué día?». «Acumulada» responde «¿para cuándo ya habría "
                               "salido?»: la misma información, sumada paso a paso; por construcción esa línea siempre sube.")]),
            html.Div([html.Div("Qué NO dice", className="metodo__rotulo"), html.Div(id="pec-nota")]),
        ]),
    ])


def panel_tecnico():
    pasos = [html.Div(className="pipeline__step tooltip-trigger", children=[
                html.Div(className="pipeline__dot"), html.Div(titulo, className="pipeline__label"),
                html.Span(detalle, className="tooltip-content")])
             for titulo, detalle in ETAPAS_PIPELINE_A6B]
    return html.Details(className="metodo metodo--panel", children=[
        html.Summary([html.Span("Ficha técnica del estimador", className="metodo__titulo"), html.Span("cómo funciona por dentro", className="metodo__sub")]),
        html.Div(className="metodo__apilado", children=[
            html.Div([
                html.Div("Cómo funciona por dentro", className="metodo__rotulo"),
                html.Div("Hay un modelo de árboles de gradiente distinto para cada hora ya pasada en cama (0, 6, 12, 24 "
                         "y 48 h; desde las 72 h, uno combinado). Cada uno responde una sola pregunta: "
                         "«dado que el paciente sigue en cama ahora, ¿cuál es la probabilidad de que le den el alta en la "
                         "próxima hora?». Encadenando esas probabilidades hora por hora se construye la curva completa. "
                         "Usa edad, sexo, tipo de visita, horas ya en cama, hora del reloj, día de la semana, ocupación de "
                         "la zona y, si estuvo hospitalizado antes, su historial.", style={"fontSize": "13px", "lineHeight": "1.6"}),
                html.Div("No usa el diagnóstico de esta estancia (fuga: se registra tarde) ni el recorrido en urgencias "
                         "(eso es el tramo antes de la cama, no la estancia en ella).", style={"fontSize": "12px", "color": GRIS, "marginTop": "4px"}),
            ]),
            html.Div([
                html.Div("Por qué los intentos anteriores no funcionaban", className="metodo__rotulo"),
                html.Div("Los dos intentos anteriores entrenaban un solo modelo AL INGRESAR, prediciendo la estancia "
                         "total con lo que se sabía ese día: una prueba rápida (21-oct) dio R² ≈ 0,00-0,02 (igual que "
                         "adivinar la mediana); un modelo explicativo con más variables (factores_estancia.py, 3-nov) "
                         "llegó a R² = 7,9-10,8 %, declarado ahí mismo como «explica, no predice». Este estimador reusa, "
                         "en cambio, la arquitectura que sí funciona para la espera de cama: un modelo distinto por cada "
                         "hora YA TRANSCURRIDA, que puede usar lo que pasó desde que llegó a la cama.", style={"fontSize": "13px", "lineHeight": "1.6"}),
            ]),
            html.Div([
                html.Div("Etapas de construcción (pasa el mouse sobre cada una)", className="metodo__rotulo"),
                html.Div(className="pipeline", children=pasos),
            ]),
            html.Div([
                html.Div("Comparativo contra el rango por perfil", className="metodo__rotulo"),
                html.Div("Mejora frente al rango por perfil que ya usa el dashboard (que_esperar.py), medida con "
                         "estancias de jul-2025 a 9-ene-2026 que el modelo no vio (90 días de margen para que las "
                         "estancias largas alcancen a resolverse). No es R²: esa métrica solo se cita arriba para los "
                         "intentos anteriores, ya descartados.", style={"fontSize": "12px", "color": GRIS, "marginBottom": "4px"}),
                dcc.Graph(figure=grafico_mejora_estancia(), config={"displaylogo": False}),
            ]),
            html.Div([
                html.Div("Límites", className="metodo__rotulo"),
                html.Div("La mejora es real pero modesta (muy por debajo del ~9-11 % del estimador de espera): lo que "
                         "no se registra (servicio, tipo de cama, gravedad clínica) sigue explicando la mayor parte de "
                         "cuánto dura una estancia. A horas ya avanzadas (120-168 h) la muestra de prueba es chica y la "
                         "ventaja frente al rango por perfil se vuelve inestable; en esos casos el rango que se muestra "
                         "es, sobre todo, una descripción de pacientes parecidos, no una predicción afinada. No usa el "
                         "diagnóstico de esta estancia ni la gravedad clínica (UCI, procedimientos): esos datos no tienen "
                         "una hora confiable antes del alta.", style={"fontSize": "12.5px", "color": GRIS}),
            ]),
        ]),
    ])


def layout():
    ahora = pd.Timestamp.now().floor("h")
    return html.Div(className="page-container", children=[
        html.Div(className="page-head", children=[
            html.H2("¿Cuánto le falta de estancia a este paciente?"),
            html.P("Describe a un paciente YA hospitalizado y el estimador muestra en qué día es más probable que reciba el alta.",
                   className="page-head__sub"),
        ]),
        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "32px", "alignItems": "flex-start"}, children=[
            html.Div(className="form-panel", style={"flex": "0 0 320px"}, children=[
                html.Div(className="field-group", children=[
                    html.Span("Edad (años)", className="field-group__label"),
                    stepper("pec-edad", 67, 0, 110),
                ]),
                html.Div(className="field-group", children=[
                    html.Span("Sexo", className="field-group__label"),
                    dcc.RadioItems(id="pec-sexo", className="pill-switch pill-switch--icons", value="Mujer", options=[
                        {"value": "Mujer", "label": html.Span(className="pill-icon-option", children=[
                            html.Span("♀", className="gender-icon", style={"color": "#d6336c", "fontWeight": 700})])},
                        {"value": "Hombre", "label": html.Span(className="pill-icon-option", children=[
                            html.Span("♂", className="gender-icon", style={"color": AZUL, "fontWeight": 700})])},
                    ]),
                ]),
                html.Div(className="field-group", children=[
                    html.Span(["Tipo de visita ", info_badge("Los tres tipos que trae la base. Pasa el mouse sobre cada "
                               "código para ver qué significa.")], className="field-group__label"),
                    dcc.RadioItems(id="pec-tipo", className="pill-switch pill-switch--compact", value="Urgencias", options=[
                        {"value": tv, "label": html.Span(className="pill-icon-option", children=[cod, info_badge(info)])}
                        for tv, (cod, info) in TIPOS_INFO.items()]),
                ]),
                html.Div(className="field-group", children=[
                    html.Span("Horas que lleva en cama", className="field-group__label"),
                    stepper("pec-horas", 0, 0, cee.MAX_H_ESTANCIA - 1),
                ]),
                html.Div(className="field-group", children=[
                    html.Span("Fecha y hora de ahora", className="field-group__label"),
                    dcc.Input(id="pec-ahora", type="text", value=f"{ahora:%Y-%m-%d %H:%M}", style={"width": "100%"}),
                    html.Div("formato AAAA-MM-DD HH:MM", className="field-group__help"),
                ]),
                html.Details(className="field-group", open=True, children=[
                    html.Summary("Si ya estuvo hospitalizado antes (opcional)", className="field-group__label", style={"cursor": "pointer"}),
                    html.Div("Su historial ayuda a afinar la estimación. Si nunca estuvo hospitalizado, déjalo en 0.", className="field-group__help"),
                    html.Span("Veces que estuvo hospitalizado", className="field-group__label"),
                    dcc.Input(id="pec-prev-n", type="number", min=0, step=1, value=0, style={"width": "100%"}),
                    html.Span("Horas que esperó cama la última vez", className="field-group__label"),
                    dcc.Input(id="pec-prev-espera", type="number", min=0, step=1, style={"width": "100%"}),
                    html.Span("Días que estuvo hospitalizado la última vez", className="field-group__label"),
                    dcc.Input(id="pec-prev-estancia", type="number", min=0, step=1, style={"width": "100%"}),
                    html.Span("Hace cuántos días salió", className="field-group__label"),
                    dcc.Input(id="pec-prev-dias", type="number", min=0, step=1, style={"width": "100%"}),
                    html.Span("Diagnóstico de esa visita anterior", className="field-group__label"),
                    dcc.Dropdown(id="pec-dx-previo", options=GRUPOS_DX, placeholder="No se sabe", clearable=True),
                ]),
                html.Details(className="field-group", children=[
                    html.Summary("Laboratorios del ingreso (primeras 6 horas de la visita, opcional)", className="field-group__label", style={"cursor": "pointer"}),
                    html.Div("Lo que se sabía al llegar a la cama (no cambia durante la estancia en esta versión). Marca lo que salió fuera de rango.", className="field-group__help"),
                    dcc.RadioItems(id="pec-labs-si", className="pill-switch pill-switch--compact", value="no",
                                   options=[{"label": "No le tomaron", "value": "no"}, {"label": "Sí le tomaron", "value": "si"}]),
                    dcc.Checklist(id="pec-labs", options=[{"label": t, "value": k} for k, (_c, _v, t) in LABS_FUERA.items()], value=[],
                                  style={"display": "grid", "gap": "4px", "marginTop": "8px", "fontSize": "13px"}),
                ]),
                html.Div(className="field-group", children=[
                    html.Span("Camas ocupadas ahora en su zona (opcional)", className="field-group__label"),
                    dcc.Input(id="pec-ocup", type="number", min=0, step=1, style={"width": "100%"}),
                    html.Div("Si no lo sabes, se usa la ocupación típica de los últimos meses.", className="field-group__help"),
                ]),
                html.Button("Estimar", id="pec-estimar", n_clicks=0, className="btn-primary", style={"width": "100%", "marginTop": "6px"}),
                html.Div(id="pec-alerta-perfil"),
            ]),
            html.Div(style={"flex": "1 1 600px"}, children=[
                html.Div(className="pac-metrics-row", children=[
                    html.Div(id="pec-lead", className="pac-lead-wrap"),
                    html.Div(id="pec-rango", className="pac-rango-wrap"),
                ]),
                html.Div(style={"display": "flex", "justifyContent": "flex-end", "marginBottom": "12px"}, children=[
                    dcc.RadioItems(id="pec-vista", className="pill-switch", value="normal", options=[
                        {"label": "Normal", "value": "normal"}, {"label": "Acumulada", "value": "acumulada"}]),
                ]),
                dcc.Graph(id="pec-grafico", config={"displaylogo": False}),
                dcc.Store(id="pec-ventanas-datos"),
            ]),
        ]),
        tarjeta_eleccion("/paciente-cama"),
        mensaje("**Es el rango de pacientes parecidos, no una promesa para una persona.** Sirve para responder a un paciente y a su familia en qué "
                "día es más probable el alta, y para la planeación de camas (cuántos de los hospitalizados hoy seguirían ocupando cama en 1, 3 o 7 "
                "días). Solo aplica a pacientes que YA tienen cama asignada; la mejora frente al rango por perfil es real pero modesta."),
        metodo("Para cada hora ya pasada en cama, el modelo estima la probabilidad de recibir el alta en la hora siguiente según la hora del reloj, "
               "el día, la ocupación, la edad, el sexo, el tipo de visita, el historial de hospitalizaciones anteriores y sus laboratorios del "
               "ingreso. Encadenando esas probabilidades sale el rango completo de lo que falta. Se entrena con las estancias del periodo confiable, "
               "y las estancias sin alta resuelta aportan como censuradas en vez de descartarse. Probado con estancias que no había visto: mejora "
               "modesta frente a darle a cada perfil su propio rango (ver cifras reales en la ficha técnica).",
               "No usa el diagnóstico de esta estancia (se registra tarde) ni la gravedad clínica (UCI, procedimientos), que es de lo que más "
               "depende la estancia real. La mejora medida es mucho menor que la del estimador de espera: la mayor parte de cuánto dura una "
               "estancia no está en lo que la base registra. A horas ya avanzadas (120-168 h) el rango es, sobre todo, descriptivo.",
               "Fuente: src/estimador_estancia_restante.py y src/comparar_estimadores_estancia.py. Detalle: documentación, sección 6.10.", ruta="/paciente-cama",
               antes=secciones(panel_interpretacion(), solo=("Qué estás viendo", "Qué significa cada cosa del gráfico")) + [html.Div([html.Div("Avisos de esta estimación", className="metodo__rotulo"), html.Div(id="pec-nota")])], despues=secciones(panel_tecnico(), solo=ETAPAS_Y_PRUEBAS), pasos=False, modelo=False),
    ])


def frase_ventana_dia(v):
    if v.startswith("más de"):
        return f"En {v}"
    return v.capitalize()


def construir_grafico_normal(v, ventana_mas_probable, dark):
    """Vista 'Normal': una barra por día (1 a 10) más 'más de 10 días' -- no por franja del día, a diferencia
    del estimador de espera: la estancia opera a escala de días, no de horas."""
    xs = list(range(len(v)))
    colores = [NARANJA if ventana == ventana_mas_probable else AZUL for ventana in v.ventana]
    etiquetas = [f"día {i + 1}" if i < len(v) - 1 else "más de\n10 días" for i in range(len(v))]
    fig = go.Figure([go.Bar(x=xs, y=[round(100 * p, 1) for p in v.probabilidad], marker_color=colores,
                            customdata=list(v.ventana), hovertemplate="%{customdata}<br>%{y} %%<extra></extra>")])
    fig.update_layout(title="¿En qué día recibirá el alta?", yaxis_title="Probabilidad (%)",
                      template="simple_white", margin=dict(l=40, r=20, t=50, b=60), bargap=0.3,
                      xaxis=dict(tickmode="array", tickvals=xs, ticktext=etiquetas))
    tg.aplicar(fig, dark)
    return fig


def construir_grafico_acumulada(v, ventana_mas_probable, dark):
    """Vista 'Acumulada': 1 - S(j), leída por día en vez de por bloque del día."""
    xs = list(range(len(v)))
    etiquetas = [f"día {i + 1}" if i < len(v) - 1 else "más de\n10 días" for i in range(len(v))]
    ys = [round(100 * a, 1) for a in v.acumulada]
    pos_destacada = next((i for i, ventana in enumerate(v.ventana) if ventana == ventana_mas_probable), None)
    fig = go.Figure([go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color=AZUL, width=2.5),
                                marker=dict(size=[15 if i == pos_destacada else 7 for i in xs],
                                            color=[NARANJA if i == pos_destacada else AZUL for i in xs]),
                                customdata=list(v.ventana), hovertemplate="%{customdata}<br>%{y} %% ya tiene alta<extra></extra>")])
    if pos_destacada is not None:
        fig.add_annotation(x=xs[pos_destacada], y=ys[pos_destacada], text="mayor probabilidad aquí",
                           showarrow=True, arrowhead=2, ax=0, ay=-32, font=dict(size=11, color=NARANJA))
    fig.update_layout(title="Probabilidad acumulada de ya tener el alta", yaxis_title="Probabilidad acumulada (%)",
                      yaxis_range=[0, 100], template="simple_white", margin=dict(l=40, r=20, t=50, b=60),
                      xaxis=dict(tickmode="array", tickvals=xs, ticktext=etiquetas))
    tg.aplicar(fig, dark)
    return fig


@callback(Output("pec-ventanas-datos", "data"), Output("pec-lead", "children"), Output("pec-rango", "children"),
          Output("pec-nota", "children"), Output("pec-alerta-perfil", "children"),
          Input("pec-estimar", "n_clicks"),
          State("pec-edad", "value"), State("pec-sexo", "value"), State("pec-tipo", "value"), State("pec-horas", "value"), State("pec-ahora", "value"),
          State("pec-prev-n", "value"), State("pec-prev-espera", "value"), State("pec-prev-estancia", "value"), State("pec-prev-dias", "value"),
          State("pec-dx-previo", "value"), State("pec-labs-si", "value"), State("pec-labs", "value"), State("pec-ocup", "value"))
def actualizar(_, edad, sexo, tipo, horas, ahora, prev_n, prev_espera, prev_estancia, prev_dias, dx_previo, labs_si, labs, ocup):
    try:
        horas = float(horas or 0)
        previa = None
        if prev_n and int(prev_n) > 0 and None not in (prev_espera, prev_estancia, prev_dias):
            previa = {"espera_h": float(prev_espera), "estancia_h": 24.0 * float(prev_estancia), "dias_desde": float(prev_dias), "n_previas": int(prev_n)}
        valores_lab = None
        if labs_si == "si":
            valores_lab = {LABS_FUERA[k][0]: LABS_FUERA[k][1] for k in (labs or []) if k in LABS_FUERA} or {"leuc_max": 8.0}
        r = eer.estimar_estancia_restante(float(edad), sexo, tipo, horas, ahora, ocupacion_zona=float(ocup) if ocup else None,
                                          hospitalizacion_previa=previa, diagnostico_previo=dx_previo or None, laboratorios_ingreso=valores_lab)
    except Exception as err:
        return None, [], [], f"No se pudo estimar: {err}", []
    v = pd.DataFrame(r["ventanas"])
    datos = {"ventanas": r["ventanas"], "ventana_mas_probable": r["ventana_mas_probable"]}

    lead = [tarjeta("Día más probable del alta", frase_ventana_dia(r["ventana_mas_probable"]),
                    f"{100 * v.probabilidad.max():.0f} % de probabilidad", destacada=True)]
    rango = [rango_widget(r["faltan_p25_h"], r["faltan_p50_h"], r["faltan_p75_h"], r["faltan_p90_h"])]

    perfil = cp.clasificar_perfil(edad, sexo, tipo)
    avisos_html = [html.Li(a) for a in r["avisos"]]
    nota = html.Div([
        html.P(f"Zona: {'niños' if r['zona'] == 'ninos' else 'adultos'}; camas ocupadas usadas: {r['ocupacion_usada']:.0f} ({'la que indicaste' if ocup else 'típico de los últimos meses'}).",
               style={"margin": "0 0 4px 0"}),
        html.Ul(avisos_html, style={"margin": 0, "paddingLeft": "18px"}),
    ])
    alerta = []
    if perfil["poco_comun"]:
        alerta = html.Div(className="alert-inline", children=[
            "⚠ Perfil poco común: ", f"edad {perfil['grupo_edad']}, {sexo}, {tipo} tiene solo {perfil['n_estancias']} estancias "
            "desde feb-2023 en la base. El rango puede ser menos estable que para un perfil común."])
    return datos, lead, rango, nota, alerta


@callback(Output("pec-grafico", "figure"), Input("pec-ventanas-datos", "data"), Input("pec-vista", "value"), State("theme-store", "data"))
def mostrar_grafico(datos, vista, tema):
    """Separado de actualizar(): cambiar el switch Normal/Acumulada solo redibuja, no vuelve a estimar."""
    if not datos:
        return go.Figure()
    v = pd.DataFrame(datos["ventanas"])
    dark = tg.es_oscuro(tema)
    if vista == "acumulada":
        return construir_grafico_acumulada(v, datos["ventana_mas_probable"], dark)
    return construir_grafico_normal(v, datos["ventana_mas_probable"], dark)
