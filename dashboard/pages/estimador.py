"""
dashboard/pages/estimador.py  -  version 2 (9-nov-2026; antes era dashboard/estimador.py v1, una app aparte en el puerto 8051)
Pagina 3.7 del dashboard (tarea A6): ¿CUANDO RECIBIRA CAMA ESTE PACIENTE?

Se describe al paciente (edad, sexo, tipo de visita, cuantas horas lleva esperando y, si se sabe, su hospitalizacion anterior, sus etapas de
atencion en urgencias y sus laboratorios de las primeras 6 h) y la pagina muestra:
  - la probabilidad de recibir cama en cada bloque del dia (madrugada, mañana, tarde, noche) de hoy, mañana y pasado mañana, y la acumulada;
  - el rango de lo que le falta (percentiles 25, 50, 75 y 90) y la probabilidad de recibirla en 6, 12 y 24 horas;
  - los avisos de la funcion (solo vale para quien ya tiene orden de hospitalizacion, atraso del modelo, ocupacion supuesta);
  - que tan bien funciona el estimador en la prueba (jul-2025 a 9-abr-2026), si las tablas de validacion estan disponibles.
Es la misma funcion de consulta de src/estimador_tiempo_restante.py: rango de pacientes parecidos, no una promesa para una persona.
Los ids llevan el prefijo "est-" para no chocar con otras paginas.

DATOS  No se conecta a la base. Usa el modelo guardado (HUN_PROCESADOS/modelos/, fuera del proyecto; si no existe lo entrena la primera vez,
       ~2 min, y para eso necesita HUN_PROCESADOS, HUN_TABLAS y HUN_CRUDOS) y, para la seccion de validacion, las tablas agregadas de
       src/utilidad_estimador.py (utilidad_*.csv en HUN_TABLAS). Ninguna tabla tiene datos de pacientes.
       Si el modelo no esta disponible, la pagina lo dice en vez de romper el dashboard.
"""
import sys
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "dashboard"))
from componentes import AZUL, GRIS, NARANJA, coma, tarjeta  # noqa: E402

try:
    import comparar_estimadores as ce  # noqa: E402
    import estimador_tiempo_restante as etr  # noqa: E402
    import estimador_tiempos as et  # noqa: E402
    TIPOS, ERROR_CARGA = et.TIPOS, None
except Exception as err:                                  # sin las tablas del proyecto: la pagina avisa y el resto del dashboard sigue
    TIPOS, ERROR_CARGA = ["Urgencias"], f"{type(err).__name__}: {err}"

dash.register_page(__name__, path="/estimador", name="3.7 ¿Cuándo recibirá cama?", title="¿Cuándo recibirá cama? - HUN", order=37)

LABS = [("leuc_max", "Leucocitos, el más alto (miles/µL)", "alto si > 12"), ("leuc_min", "Leucocitos, el más bajo (miles/µL)", "bajo si < 4"),
        ("hb_min", "Hemoglobina, la más baja (g/dL)", "anemia si < 10"), ("creat_max", "Creatinina, la más alta (mg/dL)", "alta si > 1,5: riñón"),
        ("bun_max", "BUN, el más alto (mg/dL)", "alto si > 40: riñón"), ("lactato_max", "Lactato, el más alto (mmol/L)", "alto si > 2,2: falta de oxígeno"),
        ("k_max", "Potasio, el más alto (mEq/L)", "alto si > 5,5"), ("na_min", "Sodio, el más bajo (mEq/L)", "bajo si < 130"),
        ("na_max", "Sodio, el más alto (mEq/L)", "alto si > 150"), ("troponina_max", "Troponina, la más alta (ng/mL)", "alta si > 1: daño al corazón"),
        ("pcr_max", "PCR, la más alta (mg/L)", "alta si > 50: inflamación o infección")]


def campo(etiqueta, control, ayuda=""):
    return html.Div([html.Label(etiqueta, style={"fontWeight": 600, "fontSize": "14px"}), control,
                     html.Div(ayuda, style={"fontSize": "11px", "color": GRIS})], style={"marginBottom": "10px"})


def numero(id_, **kw):
    return dcc.Input(id=id_, type="number", style={"width": "100%"}, **kw)


def validacion():
    """Resumen de que tan bien funciona, leido de las tablas agregadas de utilidad_estimador.py (si existen)."""
    try:
        v = pd.read_csv(ce.TABLAS / "utilidad_ventanas.csv").set_index("horas_esperando")
        c = pd.read_csv(ce.TABLAS / "utilidad_censo.csv")
        a = pd.read_csv(ce.TABLAS / "utilidad_alerta.csv")
    except Exception:
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


def layout():
    if ERROR_CARGA:
        return html.Div([html.H2("¿Cuándo recibirá cama este paciente?"),
                         html.P("Esta página necesita el modelo del estimador, que se entrena con datos clínicos que no se publican "
                                "(ver docs/estimador_tiempos.md, «Cómo reproducirlo»).", style={"color": GRIS}),
                         html.Pre(ERROR_CARGA, style={"fontSize": "12px", "color": GRIS})])
    ahora = pd.Timestamp.now().floor("h")
    return html.Div([
        html.H2("¿Cuándo recibirá cama este paciente?"),
        html.P("Para un paciente que ya tiene orden de hospitalización y espera cama: describe al paciente y el estimador muestra en qué momento "
               "del día es más probable que reciba cama. Es el rango de pacientes parecidos en la historia del hospital, no una promesa para una persona.",
               style={"color": GRIS}),
        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "32px", "alignItems": "flex-start"}, children=[
            html.Div(style={"flex": "0 0 300px"}, children=[
                campo("Edad (años)", numero("est-edad", min=0, max=110, value=67)),
                campo("Sexo", dcc.RadioItems(id="est-sexo", options=["Mujer", "Hombre"], value="Mujer", inline=True)),
                campo("Tipo de visita", dcc.Dropdown(id="est-tipo", options=TIPOS, value="Urgencias", clearable=False)),
                campo("Horas que lleva esperando", numero("est-horas", min=0, max=200, value=0)),
                campo("Fecha y hora de ahora", dcc.Input(id="est-ahora", type="text", value=f"{ahora:%Y-%m-%d %H:%M}", style={"width": "100%"}),
                      "formato AAAA-MM-DD HH:MM"),
                html.Details([html.Summary("Hospitalización anterior (opcional)"),
                              campo("Espera de esa vez (h)", numero("est-esp-prev", min=0)),
                              campo("Estancia de esa vez (h)", numero("est-est-prev", min=0)),
                              campo("Hace cuántos días salió", numero("est-dias-prev", min=0)),
                              campo("Hospitalizaciones anteriores", numero("est-n-prev", min=1, value=1))]),
                html.Details([html.Summary("Etapas en urgencias de esta visita (opcional)"),
                              campo("Etapas de atención ya cerradas", numero("est-n-cerr", min=0, value=0)),
                              campo("Etapas de atención abiertas ahora", numero("est-n-abie", min=0, value=1), "Si no se sabe, dejar 1 (lo más común).")]),
                html.Details([html.Summary("Laboratorios de las primeras 6 h (opcional, cuentan desde las 6 h de espera)"),
                              html.Div("Deja vacío lo que no le hayan tomado; vacío cuenta como normal.", style={"fontSize": "11px", "color": GRIS}),
                              *[campo(n, numero(f"est-lab-{c}", min=0), a) for c, n, a in LABS]]),
                html.Button("Estimar", id="est-estimar", n_clicks=0, style={"marginTop": "8px", "padding": "8px 18px"}),
            ]),
            html.Div(style={"flex": "1 1 600px"}, children=[
                html.Div(id="est-tarjetas", style={"display": "flex", "flexWrap": "wrap", "gap": "10px", "marginBottom": "10px"}),
                dcc.Loading(dcc.Graph(id="est-grafico", config={"displaylogo": False})),
                html.Div(id="est-nota", style={"fontSize": "13px", "color": GRIS}),
            ]),
        ]),
        html.H4("¿Qué tan bien funciona?", style={"marginTop": "24px"}),
        validacion(),
        html.P("Límites: se entrenó solo con pacientes que recibieron cama, así que no sirve para quien todavía no tiene orden de hospitalización; "
               "la base no registra el triage, el servicio ni el tipo de cama, que es de lo que más depende la espera; la «cama» es la asignación "
               "administrativa; parte de lo que aporta el recorrido en urgencias puede ser el propio trámite de hospitalización; los datos confiables "
               "terminan el 9-abr-2026. Detalle en docs/estimador_tiempos.md.", style={"fontSize": "12px", "color": GRIS}),
    ])


def etapas_desde_conteos(n_cerradas, n_abiertas, horas):
    """Convierte los conteos en etapas aproximadas: las cerradas repartidas desde la llegada y las abiertas empezando despues."""
    n_cerradas, n_abiertas = int(n_cerradas or 0), int(n_abiertas or 0)
    paso = horas / (n_cerradas + 1) if horas > 0 else 0
    etapas = [(i * paso, (i + 1) * paso) for i in range(n_cerradas)]
    inicio = n_cerradas * paso
    etapas += [(inicio + j * 0.01, None) for j in range(n_abiertas)]
    return etapas


@callback(Output("est-grafico", "figure"), Output("est-tarjetas", "children"), Output("est-nota", "children"),
          Input("est-estimar", "n_clicks"),
          State("est-edad", "value"), State("est-sexo", "value"), State("est-tipo", "value"), State("est-horas", "value"), State("est-ahora", "value"),
          State("est-esp-prev", "value"), State("est-est-prev", "value"), State("est-dias-prev", "value"), State("est-n-prev", "value"),
          State("est-n-cerr", "value"), State("est-n-abie", "value"), *[State(f"est-lab-{c}", "value") for c, _, _ in LABS])
def actualizar(_, edad, sexo, tipo, horas, ahora, esp_prev, est_prev, dias_prev, n_prev, n_cerr, n_abie, *labs):
    try:
        horas = float(horas or 0)
        hp = {"espera_h": esp_prev, "estancia_h": est_prev, "dias_desde": dias_prev, "n_previas": n_prev or 1} if esp_prev is not None else None
        lab = {c: v for (c, _, _), v in zip(LABS, labs) if v is not None} or None
        r = etr.estimar_tiempo_restante(float(edad), sexo, tipo, horas, ahora, hospitalizacion_previa=hp,
                                        etapas_urgencias=etapas_desde_conteos(n_cerr, n_abie, horas), admisiones=[0.0], laboratorios_6h=lab)
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
    tarjetas = [
        tarjeta("Lo más probable", r["ventana_mas_probable"], f"{100 * v.probabilidad.max():.0f} % de probabilidad"),
        tarjeta("Le falta (mediana)", f"{r['faltan_p50_h']:.0f} h", f"la mitad de los parecidos ya tendría cama: {r['hora_estimada_mediana'][5:]}"),
        tarjeta("Rango típico", f"{r['faltan_p25_h']:.0f} a {r['faltan_p75_h']:.0f} h", f"1 de cada 10 tarda más de {r['faltan_p90_h']:.0f} h"),
        tarjeta("Cama en 6 / 12 / 24 h", f"{100 * r['prob_cama_en_6h']:.0f} / {100 * r['prob_cama_en_12h']:.0f} / {100 * r['prob_cama_en_24h']:.0f} %"),
    ]
    nota = html.Div([html.Div(f"Zona: {'niños' if r['zona'] == 'ninos' else 'adultos'}; camas ocupadas usadas: {r['ocupacion_usada']:.0f}. "
                              "Las etapas en urgencias se aproximan a partir de los conteos."
                              + (" Los laboratorios solo cuentan desde las 6 h de espera." if lab and horas < 6 else "")),
                     html.Ul([html.Li(a) for a in r.get("avisos", [])], style={"margin": "6px 0"})])
    return fig, tarjetas, nota
