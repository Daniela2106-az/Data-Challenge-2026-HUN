"""
dashboard/estimador.py  -  version 1 (8-nov-2026)
Pagina del dashboard (Dash) para la tarea A6: ¿CUANDO RECIBIRA CAMA ESTE PACIENTE?

Se describe al paciente (edad, sexo, tipo de visita, cuantas horas lleva esperando y, si se sabe, su hospitalizacion anterior y sus etapas de
atencion en urgencias) y la pagina muestra:
  - la probabilidad de recibir cama en cada bloque del dia (madrugada, mañana, tarde, noche) de hoy, mañana y pasado mañana, y la acumulada;
  - el rango de lo que le falta (percentiles 25, 50, 75 y 90) y la probabilidad de recibirla en 6, 12 y 24 horas;
  - que tan bien funciona el estimador en la prueba (jul-2025 a 9-abr-2026), si las tablas de validacion estan disponibles.
Es la misma funcion de consulta de src/estimador_tiempo_restante.py: rango de pacientes parecidos, no una promesa para una persona.

COMO CORRERLO
  HUN_PROCESADOS=... HUN_TABLAS=... HUN_CRUDOS=... python3 dashboard/estimador.py    y abrir http://127.0.0.1:8051
  La primera vez entrena el modelo (~1 min) si no existe en HUN_PROCESADOS/modelos/.

DATOS  No se conecta a la base. Usa el modelo guardado (fuera del proyecto) y, para la seccion de validacion, las tablas agregadas de
       src/utilidad_estimador.py (utilidad_*.csv en HUN_TABLAS). Ninguna tabla tiene datos de pacientes.
       Falta decidir con Daniela si el modelo guardado puede publicarse con el dashboard (sale de datos clinicos).
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import comparar_estimadores as ce  # noqa: E402
import confianza_perfil as cp  # noqa: E402
import estimador_tiempo_restante as etr  # noqa: E402
import estimador_tiempos as et  # noqa: E402

GRIS, AZUL, NARANJA = "#6b6b6b", "#2a6fb0", "#eb6834"

app = Dash(__name__, title="¿Cuándo recibirá cama? - HUN")
server = app.server


def tarjeta(titulo, valor, detalle=""):
    return html.Div([html.Div(titulo, style={"fontSize": "12px", "color": GRIS}),
                     html.Div(valor, style={"fontSize": "24px", "fontWeight": 700}),
                     html.Div(detalle, style={"fontSize": "12px", "color": GRIS})],
                    style={"border": "1px solid #ddd", "borderRadius": "8px", "padding": "10px 14px", "minWidth": "190px"})


def coma(x, decimales=1):
    return f"{x:.{decimales}f}".replace(".", ",")


def campo(etiqueta, control, ayuda=""):
    return html.Div([html.Label(etiqueta, style={"fontWeight": 600, "fontSize": "14px"}), control,
                     html.Div(ayuda, style={"fontSize": "11px", "color": GRIS})], style={"marginBottom": "10px"})


def validacion():
    """Resumen de que tan bien funciona, leido de las tablas agregadas de utilidad_estimador.py (si existen)."""
    try:
        v = pd.read_csv(ce.TABLAS / "utilidad_ventanas.csv").set_index("horas_esperando")
        c = pd.read_csv(ce.TABLAS / "utilidad_censo.csv")
        a = pd.read_csv(ce.TABLAS / "utilidad_alerta.csv")
    except (FileNotFoundError, OSError):
        return html.P("Las tablas de validación no están disponibles (correr src/utilidad_estimador.py).", style={"color": GRIS})
    v0, c13 = v.loc[0], c[(c.hora_del_censo == "13:00") & (c.plazo_h == 24)].iloc[0]
    a40 = a[a.corte.str.contains("40")].iloc[0]
    return html.Ul([
        html.Li(f"Ventanas: la real está entre las 2 más probables en el {v0.real_entre_las_2_mas_probables_pct:.0f} % de los pacientes "
                f"(sin modelo, {v0.referencia_2_mas_probables_pct:.0f} %), y las probabilidades dicen la verdad: cuando dice 10 %, pasa cerca del 10 %."),
        html.Li(f"Censo de las 13:00 para la reunión de camas: de unos {c13.en_espera_promedio:.0f} pacientes en espera, cuántos tendrán cama en 24 h, con un "
                f"error de {coma(c13.error_abs_medio)} pacientes por día, en el mínimo que permite el azar ({coma(c13.piso_de_ruido_error_abs)}). Su rango "
                f"del 80 % acierta el {c13.dentro_banda_80_pct:.0f} % de los días; por semana el error es de {c13.error_pct_por_semana:.0f} %."),
        html.Li(f"Alerta a las 12 h con probabilidad ≥ 40 %: {coma(a40.alertas_por_dia)} alertas por día, acierta en el {a40.precision_pct:.0f} % "
                f"(sin modelo, {a.iloc[0].precision_pct:.0f} %)."),
    ], style={"fontSize": "13px"})


def diseno():
    ahora = pd.Timestamp.now().floor("h")
    return html.Div(style={"fontFamily": "system-ui, sans-serif", "maxWidth": "1150px", "margin": "0 auto", "padding": "16px"}, children=[
        html.H2("¿Cuándo recibirá cama este paciente?"),
        html.P("Describe al paciente y el estimador muestra en qué momento del día es más probable que reciba cama. Es el rango de pacientes "
               "parecidos en la historia del hospital, no una promesa para una persona.", style={"color": GRIS}),
        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "32px", "alignItems": "flex-start"}, children=[
            html.Div(style={"flex": "0 0 300px"}, children=[
                campo("Edad (años)", dcc.Input(id="edad", type="number", min=0, max=110, value=67, style={"width": "100%"})),
                campo("Sexo", dcc.RadioItems(id="sexo", options=["Mujer", "Hombre"], value="Mujer", inline=True)),
                campo("Tipo de visita", dcc.Dropdown(id="tipo", options=et.TIPOS, value="Urgencias", clearable=False)),
                campo("Horas que lleva esperando", dcc.Input(id="horas", type="number", min=0, max=200, value=0, style={"width": "100%"})),
                campo("Fecha y hora de ahora", dcc.Input(id="ahora", type="text", value=f"{ahora:%Y-%m-%d %H:%M}", style={"width": "100%"}),
                      "formato AAAA-MM-DD HH:MM"),
                html.Details([html.Summary("Hospitalización anterior (opcional)"),
                              campo("Espera de esa vez (h)", dcc.Input(id="esp_prev", type="number", min=0, style={"width": "100%"})),
                              campo("Estancia de esa vez (h)", dcc.Input(id="est_prev", type="number", min=0, style={"width": "100%"})),
                              campo("Hace cuántos días salió", dcc.Input(id="dias_prev", type="number", min=0, style={"width": "100%"})),
                              campo("Hospitalizaciones anteriores", dcc.Input(id="n_prev", type="number", min=1, value=1, style={"width": "100%"}))]),
                html.Details([html.Summary("Etapas en urgencias de esta visita (opcional)"),
                              campo("Etapas de atención ya cerradas", dcc.Input(id="n_cerr", type="number", min=0, value=0, style={"width": "100%"})),
                              campo("Etapas de atención abiertas ahora", dcc.Input(id="n_abie", type="number", min=0, value=1, style={"width": "100%"}),
                                    "Si no se sabe, dejar 1 (lo más común).")]),
                html.Button("Estimar", id="estimar", n_clicks=0, style={"marginTop": "8px", "padding": "8px 18px"}),
            ]),
            html.Div(style={"flex": "1 1 600px"}, children=[
                html.Div(id="tarjetas", style={"display": "flex", "flexWrap": "wrap", "gap": "10px", "marginBottom": "10px"}),
                dcc.Graph(id="grafico", config={"displaylogo": False}),
                html.Div(id="nota", style={"fontSize": "13px", "color": GRIS}),
            ]),
        ]),
        html.H4("¿Qué tan bien funciona?", style={"marginTop": "24px"}),
        validacion(),
        html.P("Límites: la base no registra el triage, el servicio ni el tipo de cama, que es de lo que más depende la espera; la «cama» es la asignación "
               "administrativa, que puede ser una silla o camilla de apoyo; probado con jul-2025 a 9-abr-2026. Detalle en docs/estimador_tiempos.md.",
               style={"fontSize": "12px", "color": GRIS}),
    ])


app.layout = diseno


def etapas_desde_conteos(n_cerradas, n_abiertas, horas):
    """Convierte los conteos en etapas aproximadas: las cerradas repartidas desde la llegada y las abiertas empezando despues."""
    n_cerradas, n_abiertas = int(n_cerradas or 0), int(n_abiertas or 0)
    paso = horas / (n_cerradas + 1) if horas > 0 else 0
    etapas = [(i * paso, (i + 1) * paso) for i in range(n_cerradas)]
    inicio = n_cerradas * paso
    etapas += [(inicio + j * 0.01, None) for j in range(n_abiertas)]
    return etapas


@app.callback(Output("grafico", "figure"), Output("tarjetas", "children"), Output("nota", "children"),
              Input("estimar", "n_clicks"),
              State("edad", "value"), State("sexo", "value"), State("tipo", "value"), State("horas", "value"), State("ahora", "value"),
              State("esp_prev", "value"), State("est_prev", "value"), State("dias_prev", "value"), State("n_prev", "value"),
              State("n_cerr", "value"), State("n_abie", "value"))
def actualizar(_, edad, sexo, tipo, horas, ahora, esp_prev, est_prev, dias_prev, n_prev, n_cerr, n_abie):
    try:
        horas = float(horas or 0)
        hp = {"espera_h": esp_prev, "estancia_h": est_prev, "dias_desde": dias_prev, "n_previas": n_prev or 1} if esp_prev is not None else None
        r = etr.estimar_tiempo_restante(float(edad), sexo, tipo, horas, ahora, hospitalizacion_previa=hp,
                                        etapas_urgencias=etapas_desde_conteos(n_cerr, n_abie, horas), admisiones=[0.0])
    except Exception as err:                                             # datos mal escritos: mostrar el motivo en vez de romper la pagina
        return go.Figure(), [], f"No se pudo estimar: {err}"
    v = pd.DataFrame(r["ventanas"])
    fig = go.Figure()
    fig.add_trace(go.Bar(x=v.ventana, y=100 * v.probabilidad, marker_color=[NARANJA if n == r["ventana_mas_probable"] else AZUL for n in v.ventana],
                         name="Probabilidad de recibir cama en esa ventana", hovertemplate="%{x}<br>%{y:.0f} %<extra></extra>"))
    fig.add_trace(go.Scatter(x=v.ventana, y=100 * v.acumulada, mode="lines+markers", line=dict(color=GRIS, dash="dot"),
                             name="Acumulada: ya tendrá cama al terminar esa ventana", hovertemplate="%{x}<br>%{y:.0f} % acumulado<extra></extra>"))
    fig.update_layout(title="¿En qué momento recibirá cama?", yaxis_title="%", yaxis_range=[0, 100], template="simple_white",
                      legend=dict(orientation="h", y=-0.45), margin=dict(l=40, r=20, t=50, b=40))
    fig.update_xaxes(tickangle=-40)
    perfil = cp.clasificar_perfil(edad, sexo, tipo)
    tarjetas = [
        tarjeta("Lo más probable", r["ventana_mas_probable"], f"{100 * v.probabilidad.max():.0f} % de probabilidad"),
        tarjeta("Le falta (mediana)", f"{r['faltan_p50_h']:.0f} h", f"la mitad de los parecidos ya tendría cama: {r['hora_estimada_mediana'][5:]}"),
        tarjeta("Rango típico", f"{r['faltan_p25_h']:.0f} a {r['faltan_p75_h']:.0f} h", f"1 de cada 10 tarda más de {r['faltan_p90_h']:.0f} h"),
        tarjeta("Cama en 6 / 12 / 24 h", f"{100 * r['prob_cama_en_6h']:.0f} / {100 * r['prob_cama_en_12h']:.0f} / {100 * r['prob_cama_en_24h']:.0f} %",
                "En las primeras horas, parte de esta probabilidad puede ser el trámite de registrar al paciente, no una predicción (docs/estimador_tiempos.md, sección 7)."),
    ]
    avisos_html = [html.Li(a) for a in r["avisos"]]
    if perfil["poco_comun"]:
        avisos_html.append(html.Li(
            f"Este perfil (edad {perfil['grupo_edad']}, {sexo}, {tipo}) tiene pocos casos históricos en la base "
            f"({perfil['n_estancias']} estancias, {perfil['n_episodios_atencion']} episodios atendidos desde feb-2023): "
            "el rango puede ser menos estable que para un perfil común.", style={"color": NARANJA}))
    nota = html.Div([
        html.P(f"Zona: {'niños' if r['zona'] == 'ninos' else 'adultos'}; camas ocupadas usadas: {r['ocupacion_usada']:.0f} (típico de los últimos meses). "
               "Las etapas en urgencias se aproximan a partir de los conteos.", style={"margin": "0 0 4px 0"}),
        html.Ul(avisos_html, style={"margin": 0, "paddingLeft": "18px"}),
    ])
    return fig, tarjetas, nota


if __name__ == "__main__":
    app.run(debug=False, port=8051)
