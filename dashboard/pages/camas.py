"""
dashboard/pages/camas.py  -  pagina del dashboard multipagina (10-nov-2026, migrada de dashboard/camas.py standalone)
"Planeación de camas": el unico de los tres piezas (paciente / perfiles / camas) que es un "que pasaria si":
el usuario cambia un supuesto sobre el futuro (mas ingresos, menos estancia, otra mezcla de perfiles) y ve como
reacciona el hospital completo. No describe un paciente (eso es pages/paciente.py) ni lee una tabla historica
fija (eso es pages/perfiles.py).

REUTILIZA POR COMPLETO el motor de A5 (src/simulacion_camas_montecarlo.py): simular() y curva_capacidad(), sin
tocar su codigo. Desde el 10-nov ese archivo separa con `if __name__ == "__main__":` el backtest/escenarios
(solo corren al ejecutarlo como script) de la parte esencial, asi que importarlo aqui solo paga el costo de
cargar los datos y construir el bootstrap (~1-2 s).

ESCENARIO D: mezcla de perfiles concentrada en los que MAS ESTANCIA tienen (no espera: la estancia es lo que
mueve la ocupacion, docs/simulacion.md). Se construye mezclando la mezcla real de 2025 con una mezcla "de
estres" (proporcional a la mediana de estancia de cada grupo_edad/ruta) segun un control de intensidad (0% =
mezcla real de hoy, 100% = concentrado en el peor caso). Se presenta SIEMPRE como caso de estres, nunca como
"mas realista que el muestreo aleatorio de A5".

"VER DESDE ESTE PUNTO": mueve el `corte` de la simulacion a una fecha de la lista de dias de alta demanda de
pages/perfiles.py (resultados/tablas/dias_alta_demanda.csv). Resuelto a UNA sola pregunta ("¿que proyecta el
motor arrancando cerca de esa fecha?"), nunca "simular ese pico especifico".

Misma logica que la version standalone (dashboard/camas.py, ya retirada); solo cambian los ids de componentes
(prefijo "camas-") para no chocar con las otras paginas de la misma app.
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
import simulacion_camas_montecarlo as scm  # noqa: E402  (import liviano desde el 10-nov: ~1-2 s, no corre el backtest)

dash.register_page(__name__, path="/camas", name="Planeación de camas", title="Planeación de camas - HUN")

GRIS, AZUL, NARANJA, VERDE = "#6b6b6b", "#2a6fb0", "#eb6834", "#2e8b57"
RAIZ = Path(__file__).resolve().parent.parent.parent
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
N_REP_INTERACTIVO = 300
GRUPOS = ["total", "ninos", "adultos"]
NOMBRES_GRUPO = {"total": "Total", "ninos": "Niños (0-4, 5-14)", "adultos": "Adultos (15+)"}

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


try:
    _dias_pico = pd.read_csv(TABLAS / "dias_alta_demanda.csv", parse_dates=["fecha"]).sort_values("fecha", ascending=False)
    OPCIONES_FECHA = [{"label": "Hoy (proyección estándar, desde el 9-abr-2026)", "value": str(scm.ULTIMO_CONFIABLE.date())}] + \
                     [{"label": f"{f.date()} (día de alta demanda, +{p:.0f}% llegadas)", "value": str(f.date())}
                      for f, p in zip(_dias_pico.fecha, _dias_pico.pct_sobre_umbral)][:60]
except (FileNotFoundError, OSError):
    OPCIONES_FECHA = [{"label": "Hoy (proyección estándar, desde el 9-abr-2026)", "value": str(scm.ULTIMO_CONFIABLE.date())}]


def campo(etiqueta, control, ayuda=""):
    return html.Div([html.Label(etiqueta, style={"fontWeight": 600, "fontSize": "14px"}), control,
                     html.Div(ayuda, style={"fontSize": "11px", "color": GRIS})], style={"marginBottom": "16px"})


def tarjeta(titulo, valor, detalle=""):
    return html.Div([html.Div(titulo, style={"fontSize": "12px", "color": GRIS}),
                     html.Div(valor, style={"fontSize": "22px", "fontWeight": 700}),
                     html.Div(detalle, style={"fontSize": "12px", "color": GRIS})],
                    style={"border": "1px solid #ddd", "borderRadius": "8px", "padding": "10px 14px", "minWidth": "160px"})


def layout():
    return html.Div(style={"fontFamily": "system-ui, sans-serif", "maxWidth": "1200px", "margin": "0 auto", "padding": "16px"}, children=[
        html.H2("Planeación de camas: ¿qué pasaría si...?"),
        html.P("Cambia un supuesto sobre el futuro (más ingresos, menos estancia, otra mezcla de perfiles) y ve cómo "
               "reacciona la ocupación proyectada. Es simulación hacia adelante sobre un escenario hipotético, no la "
               "lectura de un hecho ya ocurrido (eso está en «Perfiles y picos») ni el cálculo de un paciente concreto "
               "(eso está en «Paciente en espera»). Detalle y límites del motor en docs/modelo_camas.md y docs/simulacion.md.",
               style={"color": GRIS}),
        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "32px", "alignItems": "flex-start"}, children=[
            html.Div(style={"flex": "0 0 300px"}, children=[
                campo("Ingresos a cama (B)", dcc.Slider(id="camas-ajuste_ingresos", min=-30, max=30, step=5, value=0,
                                                         marks={i: f"{i}%" for i in range(-30, 31, 10)}),
                      "Escenario B del plan mínimo = +10 %."),
                campo("Estancia en cama (C)", dcc.Slider(id="camas-ajuste_estancia", min=-20, max=20, step=5, value=0,
                                                          marks={i: f"{i}%" for i in range(-20, 21, 10)}),
                      "Escenario C del plan mínimo = −5 %."),
                campo("Escenario D: intensidad de la mezcla de estrés", dcc.Slider(id="camas-intensidad_d", min=0, max=100, step=10, value=0,
                                                                                    marks={0: "0% (hoy)", 50: "50%", 100: "100% (peor caso)"}),
                      "Concentra la mezcla de perfiles hacia los grupos/rutas de mayor estancia histórica. "
                      "Es un caso de estrés explícito, NO una simulación más realista que el muestreo aleatorio por defecto."),
                campo("Ver la proyección desde este punto", dcc.Dropdown(id="camas-corte", options=OPCIONES_FECHA,
                                                                          value=OPCIONES_FECHA[0]["value"], clearable=False),
                      "Mueve el punto de partida de la simulación a una fecha de la lista de «Perfiles y picos». "
                      "Muestra qué proyecta el motor arrancando cerca de ese día — no reconstruye ni repite ese pico."),
                html.Button("Simular", id="camas-simular", n_clicks=0, style={"marginTop": "4px", "padding": "8px 18px"}),
                html.Div(f"n = {N_REP_INTERACTIVO} repeticiones para la interacción (los documentos citan la cifra "
                         "oficial con 1.000; el resultado aquí es una aproximación rápida).",
                         style={"fontSize": "11px", "color": GRIS, "marginTop": "8px"}),
                html.Div(id="camas-nota_r7", style={"fontSize": "12px", "marginTop": "10px"}),
            ]),
            html.Div(style={"flex": "1 1 650px"}, children=[
                dcc.RadioItems(id="camas-grupo", options=[{"label": NOMBRES_GRUPO[g], "value": g} for g in GRUPOS],
                               value="total", inline=True, style={"marginBottom": "8px"}),
                html.Div(id="camas-tarjetas", style={"display": "flex", "flexWrap": "wrap", "gap": "10px", "marginBottom": "10px"}),
                dcc.Graph(id="camas-grafico_proyeccion", config={"displaylogo": False}),
                html.Label("Capacidad a probar en la curva de riesgo", style={"fontWeight": 600, "fontSize": "13px"}),
                dcc.Slider(id="camas-capacidad_prueba", min=60, max=160, step=2, value=106, marks={c: str(c) for c in range(60, 161, 20)}),
                dcc.Graph(id="camas-grafico_curva", config={"displaylogo": False}),
            ]),
        ]),
        dcc.Store(id="camas-censos_guardados"),
        html.P("Supuestos: B y C se aplican de forma uniforme en todo el horizonte; D es un caso de estrés explícito "
               "(no un pronóstico); ningún escenario cambia la capacidad física (106/18/88, dato del HUN). Asociación, "
               "no causa.", style={"fontSize": "11px", "color": GRIS, "marginTop": "10px"}),
    ])


@callback(Output("camas-censos_guardados", "data"), Output("camas-nota_r7", "children"),
          Input("camas-simular", "n_clicks"),
          State("camas-ajuste_ingresos", "value"), State("camas-ajuste_estancia", "value"),
          State("camas-intensidad_d", "value"), State("camas-corte", "value"))
def correr_simulacion(_, pct_ingresos, pct_estancia, intensidad_d, corte):
    me, mr = (mezcla_escenario_d(intensidad_d / 100) if intensidad_d else (None, None))
    fechas, censos = scm.simular(scm.serie_ingresos, pd.Timestamp(corte), scm.HORIZONTE_PROYECCION,
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


@callback(Output("camas-grafico_proyeccion", "figure"), Output("camas-tarjetas", "children"), Output("camas-grafico_curva", "figure"),
          Input("camas-censos_guardados", "data"), Input("camas-grupo", "value"), Input("camas-capacidad_prueba", "value"))
def mostrar(data, grupo, capacidad):
    if not data:
        return go.Figure(), [], go.Figure()
    fechas = pd.to_datetime(data["fechas"])
    censos = {g: np.array(data[g]) for g in GRUPOS}
    c = censos[grupo]
    p10, p50, p90 = np.percentile(c, 10, axis=0), np.percentile(c, 50, axis=0), np.percentile(c, 90, axis=0)
    cap_hun = scm.CAPACIDAD[grupo]

    fig = go.Figure([
        go.Scatter(x=fechas, y=p90, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"),
        go.Scatter(x=fechas, y=p10, mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(42,111,176,0.15)",
                   name="Banda 10-90 %"),
        go.Scatter(x=fechas, y=p50, mode="lines", line=dict(color=AZUL, width=2), name="Mediana simulada"),
        go.Scatter(x=fechas, y=[cap_hun] * len(fechas), mode="lines", line=dict(color=NARANJA, dash="dash"),
                   name=f"Capacidad HUN ({cap_hun})"),
    ])
    fig.update_layout(title=f"Ocupación proyectada — {NOMBRES_GRUPO[grupo]}", yaxis_title="Camas ocupadas",
                      template="simple_white", legend=dict(orientation="h", y=-0.2), margin=dict(l=40, r=20, t=50, b=40))

    pct_sat = round(100 * float((c > cap_hun).mean()), 1)
    tarjetas = [tarjeta("Ocupación media", f"{c.mean():.0f} camas", f"mediana diaria {np.median(p50):.0f}"),
                tarjeta("% días-repetición saturados", f"{pct_sat} %", f"sobre la capacidad HUN ({cap_hun})"),
                tarjeta("p90 de ocupación", f"{p90.max():.0f} camas", "máximo de la banda alta en el horizonte")]

    tabla_cap, minima = scm.curva_capacidad(censos, grupo, range(max(10, cap_hun - 40), cap_hun + 41, 2))
    fig_cap = go.Figure([go.Scatter(x=tabla_cap.capacidad, y=tabla_cap["prob_saturacion_%"], mode="lines+markers", line=dict(color=AZUL))])
    fig_cap.add_vline(x=cap_hun, line_dash="dash", line_color=NARANJA, annotation_text="HUN")
    fig_cap.add_vline(x=capacidad, line_dash="dot", line_color=GRIS, annotation_text="a probar")
    fig_cap.update_layout(title=f"Curva de capacidad — {NOMBRES_GRUPO[grupo]} (mínimo para riesgo ≤10%: "
                                 f"{minima if minima else 'fuera de rango'} camas)",
                          xaxis_title="Capacidad (camas)", yaxis_title="% de días-repetición saturados",
                          template="simple_white", margin=dict(l=40, r=20, t=50, b=40))
    return fig, tarjetas, fig_cap
