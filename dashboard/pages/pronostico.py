"""
dashboard/pages/pronostico.py  -  pagina del dashboard multipagina (10-nov-2026, migrada de dashboard/app.py v4)
PRONOSTICO DE DEMANDA INTERACTIVO. El usuario elige solo DOS cosas: hasta cuando quiere ver y que quiere ver
(ingresos al hospital o ingresos a cama). El modelo corre en el momento (menos de 0,1 s porque trabaja sobre
el panel diario ya agregado, sin pacientes) y el grafico muestra como cambian los datos.

Misma logica que la version standalone (dashboard/app.py, ya retirada); solo cambian los ids de componentes
(prefijo "pron-") para que no choquen con las otras paginas en la misma app, y el registro con
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

GRIS, AZUL, ROJO = "#6b6b6b", "#2a6fb0", "#c0392b"
PLAZOS = [("7 días", 7), ("30 días", 30), ("6 meses", 182), ("1 año", 365)]
QUE_VER = {"llegadas_con_atencion": "Ingresos al hospital (pacientes que llegan a urgencias)",
           "ingresos_a_cama": "Ingresos a cama (pacientes que se hospitalizan)"}
CORTO = {"llegadas_con_atencion": "ingresos al hospital por día", "ingresos_a_cama": "ingresos a cama por día"}


def hoy():
    return pd.Timestamp.today().normalize()


def tarjeta(titulo, valor, detalle=""):
    return html.Div(className="metric-card", children=[
        html.Div(titulo, style={"fontSize": "12px"}),
        html.Div(valor, style={"fontSize": "26px", "fontWeight": 700}),
        html.Div(detalle, style={"fontSize": "12px", "color": GRIS})])


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
    html.H2("¿Cuántos pacientes ingresarán al hospital?"),
    html.P(f"Estimación para los próximos días a partir de hoy, {hoy():%d-%m-%Y}, según la historia confiable del hospital. "
           "Elige dos cosas y el gráfico se actualiza.", style={"color": GRIS}),
    html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "40px", "alignItems": "flex-start"}, children=[
        html.Div([html.Label("1. ¿Hasta cuándo quieres ver?", style={"fontWeight": 600}),
                  dcc.RadioItems(id="pron-plazo", options=[{"label": " " + n, "value": d} for n, d in PLAZOS], value=30)]),
        html.Div([html.Label("2. ¿Qué quieres ver?", style={"fontWeight": 600}),
                  dcc.RadioItems(id="pron-objetivo", options=[{"label": " " + n, "value": o} for o, n in QUE_VER.items()],
                                 value="llegadas_con_atencion")], style={"maxWidth": "420px"}),
    ]),
    html.Div(id="pron-tarjetas", style={"display": "flex", "flexWrap": "wrap", "gap": "12px", "margin": "16px 0"}),
    dcc.Graph(id="pron-grafico", config={"displaylogo": False}),
    html.Div(id="pron-nota", style={"fontSize": "13px", "color": GRIS, "marginTop": "8px"}),
    mensaje("**Sirve para planear la semana, no para adivinar un día.** A una semana el pronóstico de llegadas se equivoca cerca de 8 % y a un "
            "año cerca de 10 %. Los ingresos a cama de un día son más ruidosos (~18 %), pero por semana el error baja a ~9,5 %, que es como se "
            "planean las camas. Úselo para dimensionar turnos y camas por semana y para anticipar la temporada alta de mitad de año."),
    metodo("Un modelo de conteos (regresión de Poisson) que combina el calendario (día de la semana, festivos, Semana Santa, fin de año y "
           "Carnaval, que baja las llegadas ~17 %), el nivel reciente del hospital y la **forma del año**, tomada de datos públicos de vigilancia "
           "(dengue para las llegadas; infección respiratoria y diarrea para los ingresos a cama). Se entrenó con feb-2023 a jun-2025 y se probó "
           "con meses que no había visto; el rango probable del 80 % sale de los errores de esa prueba y en las llegadas cubre el 78–82 % de los días.",
           "No anticipa brotes, cortes de sistema ni lo que haya cambiado en el hospital después del 9-abr-2026, el último dato confiable. No dice "
           "cuántos pacientes quedarán sin atender ni cuánto esperará cada uno (eso está en «Paciente en espera»). Las llegadas incluyen ~4 % de "
           "registros replicados, estables en el tiempo.",
           "Fuente: src/modelo_pronostico.py sobre panel_diario.csv (agregado por día, sin pacientes). Detalle: documentación, sección 6.1, y docs/estacionalidad_anual.md."),
    ])


@callback(Output("pron-grafico", "figure"), Output("pron-tarjetas", "children"), Output("pron-nota", "children"),
          Input("pron-plazo", "value"), Input("pron-objetivo", "value"), State("theme-store", "data"))
def actualizar(dias, objetivo, tema):
    if not DATOS_OK:                                            # no deberia dispararse (sin datos no se renderizan los controles), defensivo
        return go.Figure(), [], "Datos no disponibles."
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

    e = ERR[objetivo]
    lead0 = int(f.dias_adelante.iloc[0])
    fila = e[e.tramo_dias.map(lambda t: int(t.split("-")[0]) <= lead0)].iloc[-1]
    meses = lead0 / 30.4
    tarjetas = [
        tarjeta("Se espera por día", f"{f.pronostico.mean():.0f}", f"promedio de los próximos {dias} días"),
        tarjeta("Rango probable por día", f"{f.banda_baja.mean():.0f} a {f.banda_alta.mean():.0f}", "8 de cada 10 casos"),
        tarjeta("Total esperado", f"{f.pronostico.sum():,.0f}".replace(",", "."), f"ingresos en los próximos {dias} días"),
        tarjeta("Error típico", f"{fila.wape_pct:.0f} %", f"por día; el último dato confiable es de hace unos {meses:.0f} meses"),
    ]
    nota = (f"Cómo se calculó: según el calendario (día de la semana, festivos, semana santa, Carnaval), la época del año (página «Forma del año») y el nivel de pacientes de febrero de 2023 a abril de 2026. "
            f"Desde el 10-abr-2026 el registro de las etapas del hospital está incompleto: esos días no se usan para estimar el nivel. "
            "No anticipa brotes ni cortes de sistema, ni lo que haya cambiado en el hospital desde entonces. Es una tendencia, no una predicción precisa.")
    tg.aplicar(fig, tg.es_oscuro(tema))
    return fig, tarjetas, nota
