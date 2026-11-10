"""
dashboard/pages/pronostico.py  -  version 5 (9-nov-2026; antes era dashboard/app.py v4 del 2-nov)
Pagina 3.1 del dashboard: PRONOSTICO DE DEMANDA INTERACTIVO (docs/estructura_dashboard.md 3.1).
El usuario elige solo DOS cosas: hasta cuando quiere ver y que quiere ver (ingresos al hospital o ingresos a cama). El modelo corre en el
momento (menos de 0,1 s porque trabaja sobre el panel diario ya agregado, sin pacientes) y el grafico muestra como cambian los datos.

DECISIONES
  - Solo vista dia por dia, sin "ajuste extra %" ni elegir un "supuesto" de nivel (1-nov-2026).
  - El pronostico PARTE DE HOY (el dia en que se abre el dashboard) y el grafico muestra SOLO el pronostico, sin datos anteriores (2-nov-2026). Usa el nivel y el calendario de febrero de 2023 al 9 de abril de 2026: la auditoria en la base
    (CLAUDE.md 4.9) mostro que desde el 10-abr-2026 el registro de las etapas esta degradado (mas visitas sin etapas, menos visitas con etapa ER), asi que
    esos dias NO se usan para estimar nivel ni error (y ya no se dibujan).
  - La banda es la del plazo contado desde el ultimo dato confiable (unos 7 meses): mas ancha que un pronostico a pocos dias.
  - 9-nov: pasa a ser una pagina del dashboard multipagina (dashboard/app.py); los ids llevan el prefijo "pro-" para no chocar con otras paginas.

DATOS  datos/procesados/para_equipo/panel_diario.csv (una fila por dia; sin ids ni datos de pacientes).
       NO se conecta a la base del hospital (VPN, solo lectura, datos clinicos). Para publicar la app hay que subir solo ese archivo.
MODELO src/modelo_pronostico.py
"""
import sys
from pathlib import Path

import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "dashboard"))
import modelo_pronostico as mp  # noqa: E402
from componentes import AZUL, GRIS, tarjeta  # noqa: E402

dash.register_page(__name__, path="/", name="3.1 Pronóstico de demanda", title="Pronóstico de demanda - HUN", order=31)

try:
    LIMPIO = mp.cargar_panel()                              # el modelo se entrena sin los dias atipicos ni los posteriores al 9-abr-2026
    SERIES = {obj: LIMPIO[obj] for obj in mp.OBJETIVOS}
    BT = {obj: mp.retroceso(s) for obj, s in SERIES.items()}    # se calcula una vez al abrir la app
    ERR = {obj: mp.tabla_error(BT[obj], sin_caida=True) for obj in mp.OBJETIVOS}
    ERROR_CARGA = None
except Exception as err:                                    # sin panel_diario.csv: la pagina avisa y el resto del dashboard sigue
    ERROR_CARGA = f"{type(err).__name__}: {err}"
SUPUESTO = "historico"                                      # nivel de los 12 meses del periodo confiable

PLAZOS = [("7 días", 7), ("30 días", 30), ("6 meses", 182), ("1 año", 365)]
QUE_VER = {"llegadas_con_atencion": "Ingresos al hospital (pacientes que llegan a urgencias)",
           "ingresos_a_cama": "Ingresos a cama (pacientes que se hospitalizan)"}
CORTO = {"llegadas_con_atencion": "ingresos al hospital por día", "ingresos_a_cama": "ingresos a cama por día"}


def hoy():
    return pd.Timestamp.today().normalize()


def layout():
    """El diseno se arma cada vez que se abre la pagina, para que "hoy" sea siempre el dia actual."""
    if ERROR_CARGA:
        return html.Div([html.H2("¿Cuántos pacientes ingresarán al hospital?"),
                         html.P("Falta panel_diario.csv (src/exportar_para_equipo.py lo genera en HUN_PROCESADOS/para_equipo/).", style={"color": GRIS}),
                         html.Pre(ERROR_CARGA, style={"fontSize": "12px", "color": GRIS})])
    return html.Div([
        html.H2("¿Cuántos pacientes ingresarán al hospital?"),
        html.P(f"Estimación para los próximos días a partir de hoy, {hoy():%d-%m-%Y}, según la historia confiable del hospital. "
               "Elige dos cosas y el gráfico se actualiza.", style={"color": GRIS}),
        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "40px", "alignItems": "flex-start"}, children=[
            html.Div([html.Label("1. ¿Hasta cuándo quieres ver?", style={"fontWeight": 600}),
                      dcc.RadioItems(id="pro-plazo", options=[{"label": " " + n, "value": d} for n, d in PLAZOS], value=30)]),
            html.Div([html.Label("2. ¿Qué quieres ver?", style={"fontWeight": 600}),
                      dcc.RadioItems(id="pro-objetivo", options=[{"label": " " + n, "value": o} for o, n in QUE_VER.items()],
                                     value="llegadas_con_atencion")], style={"maxWidth": "420px"}),
        ]),
        html.Div(id="pro-tarjetas", style={"display": "flex", "flexWrap": "wrap", "gap": "12px", "margin": "16px 0"}),
        dcc.Graph(id="pro-grafico", config={"displaylogo": False}),
        html.Div(id="pro-nota", style={"fontSize": "13px", "color": GRIS, "marginTop": "8px"}),
    ])


@callback(Output("pro-grafico", "figure"), Output("pro-tarjetas", "children"), Output("pro-nota", "children"),
          Input("pro-plazo", "value"), Input("pro-objetivo", "value"))
def actualizar(dias, objetivo):
    serie, bt = SERIES[objetivo], BT[objetivo]
    f = mp.pronostico_con_banda(serie, bt, dias, SUPUESTO, 0.0, True, False, hoy())
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
    nota = ("Cómo se calculó: según el calendario (día de la semana, festivos, semana santa, Carnaval) y el nivel de pacientes de febrero de 2023 a abril de 2026. "
            "Desde el 10-abr-2026 el registro de las etapas del hospital está incompleto: esos días no se usan para estimar el nivel. "
            "No anticipa brotes ni cortes de sistema, ni lo que haya cambiado en el hospital desde entonces. Es una tendencia, no una predicción precisa.")
    return fig, tarjetas, nota
