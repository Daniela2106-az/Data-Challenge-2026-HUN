"""
dashboard/pages/estacionalidad.py  -  pagina «Forma del año» (13-nov-2026; ficha A9, docs/estacionalidad_anual.md; formato de presentacion)
La estacionalidad anual del pronostico: cuanto sube o baja la demanda esperada en cada epoca del año y cuanto mejora el pronostico
al saberlo. Control: serie (llegadas con atencion o ingresos a cama).

DATOS  estacionalidad_efecto.csv y estacionalidad_error.csv (dashboard/preparar_datos.py, con src/modelo_pronostico.py).
       La forma del año sale de climatologias publicas (dengue, IRA y EDA de Barranquilla): no hay datos por paciente.
"""
import sys
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import (AZUL, MESES, PIZARRA, aviso_datos, bloque, cifra, coma, dato, estilo, filtro, grafico, hecho, lamina, leer, mensaje,  # noqa: E402
                         metodo, pagina, portada)

dash.register_page(__name__, path="/estacionalidad", name="Forma del año", title="La forma del año del pronóstico - HUN", order=32)

TITULO = "El pronóstico ahora sabe en qué época del año llegan más pacientes"
SERIES = [("llegadas_con_atencion", "Llegadas con atención"), ("ingresos_a_cama", "Ingresos a cama")]
QUE = {"llegadas_con_atencion": "llegadas", "ingresos_a_cama": "ingresos a cama"}
FUENTE = {"llegadas_con_atencion": ("Dengue", "la forma del año sale del dengue en Barranquilla, 2007–2022"),
          "ingresos_a_cama": ("IRA y EDA", "infección respiratoria y diarrea (SIVIGILA, 2016–2019) más una curva del año")}
HORIZONTES = {"1-7": "1–7 días", "8-30": "8–30 días", "31-91": "1–3 meses", "92-182": "3–6 meses", "183-365": "6–12 meses"}
MES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
ENTRO = [("Dengue en Barranquilla (2007–2022)", "en las llegadas"),
         ("Infección respiratoria y diarrea (SIVIGILA, 2016–2019)", "en los ingresos a cama"),
         ("Curva suave del año", "en los ingresos a cama")]
ORIGEN = [
    ("3 años", "Tiene el hospital", "No alcanzan para distinguir una temporada real de una casualidad: por eso la forma se toma de afuera."),
    ("16 años", "De dengue en Barranquilla", "De 2007 a 2022. Marca la temporada de más consultas; se usa para las llegadas."),
    ("4 años", "De infección respiratoria y diarrea", "Vigilancia nacional de 2016 a 2019, antes de la pandemia; se usa para los ingresos a cama."),
    ("2026", "Todavía sin publicar", "Los datos públicos del año en curso no están: el modelo usa el patrón típico, no un brote actual."),
]
DESCARTADO = ["Lluvia (NASA e IDEAM)", "Temperatura", "Calendario escolar oficial", "Fenómeno de El Niño", "Población (DANE)",
              "Consultas y hospitalizaciones de la ciudad", "Modelo SARIMAX"]


def layout():
    if leer("estacionalidad_efecto.csv") is None or leer("estacionalidad_error.csv") is None:
        return aviso_datos(TITULO, ["estacionalidad_efecto.csv", "estacionalidad_error.csv"])
    return pagina(
        portada("Predicción · Forma del año", TITULO,
                "Con datos públicos de vigilancia de muchos años, el pronóstico a varios meses deja de ser una línea plana y el hospital "
                "puede planear por temporadas.", id_cifras="est-cifras"),
        html.Div(className="filtros", children=[filtro("est-serie", "Serie", SERIES, "llegadas_con_atencion")]),
        lamina(1, html.Span(id="est-titular"),
               "La línea muestra cuánto se aparta la demanda esperada del promedio del año en cada época (suavizado a 15 días). Con solo "
               "tres años de datos del hospital no se puede aprender esta forma: sale de **datos públicos de salud de Barranquilla**.",
               grafico("est-efecto", alto=340), id_dato="est-dato-fuente"),
        lamina(2, "Cuanto más lejos se mira, más ayuda saberlo",
               "Error diario del pronóstico según el horizonte, sin y con la forma del año. A una semana casi no cambia; a varios meses, "
               "el error baja.",
               grafico("est-error", alto=340), id_dato="est-dato-error", invertida=True),
        lamina(3, "Las llegadas y los ingresos a cama no tienen la misma temporada",
               "Cambio esperado en cada mes frente al promedio del año, para las dos series. **Las llegadas suben de abril a junio, "
               "con la temporada de dengue; los ingresos a cama, en julio y agosto.** Esta gráfica no cambia con el filtro.",
               grafico("est-meses", alto=320), dato=("2 temporadas", "distintas: por eso cada serie lleva su propia forma del año")),
        bloque("De dónde sale la forma del año", "Datos públicos de salud de muchos años, no los tres del hospital"),
        html.Div(className="hechos", children=[hecho(*o) for o in ORIGEN]),
        bloque("Todo lo que se probó", "Solo entró al modelo lo que mejoró el pronóstico en datos que el modelo no había visto"),
        html.Div(className="card est-prueba", children=[html.Div(className="est-prueba__grid", children=[
            html.Div([html.Div("Entró al modelo", className="rec-block__label"),
                      html.Div(className="est-chips", children=[
                          html.Span([html.B(n), f" · {d}"], className="rec-chip rec-chip--alta") for n, d in ENTRO])]),
            html.Div([html.Div("Se probó y se descartó", className="rec-block__label"),
                      html.Div(className="est-chips", children=[html.Span(n, className="rec-chip est-chip--neutro") for n in DESCARTADO])]),
        ])]),
        mensaje("El hospital puede **planear personal y camas con meses de anticipación**, sabiendo qué épocas traen más pacientes y "
                "cuáles traen menos."),
        metodo(
            "Cada variable se eligió con julio a diciembre de 2025 y se confirmó en 2026, un periodo que no se usó para elegir. El error "
            "es el del backtest con destinos hasta el 9-abr-2026 (`src/modelo_pronostico.py`).",
            "El dengue funciona como **marcador de la temporada**, no como causa: no significa que traiga o quite pacientes. El modelo no "
            "anticipa brotes, y los datos públicos de 2026 todavía no están publicados.",
            "Fuente: estacionalidad_efecto.csv y estacionalidad_error.csv (dashboard/preparar_datos.py) · docs/estacionalidad_anual.md · "
            "datos públicos: SIVIGILA del Instituto Nacional de Salud y Harvard Dataverse.", ruta="/estacionalidad"))


@callback(Output("est-cifras", "children"), Output("est-titular", "children"), Output("est-efecto", "figure"),
          Output("est-dato-fuente", "children"), Output("est-error", "figure"), Output("est-dato-error", "children"),
          Output("est-meses", "figure"),
          Input("est-serie", "value"), Input("theme-store", "data"))
def actualizar(obj, tema):
    ef, er = leer("estacionalidad_efecto.csv"), leer("estacionalidad_error.csv")
    todo = ef
    ef, er = ef[ef.objetivo == obj].sort_values("dia_del_anio"), er[er.objetivo == obj].sort_values("orden")
    por_mes = ef.groupby("mes").efecto_pct.mean()
    alto, bajo = por_mes.idxmax(), por_mes.idxmin()
    largo = er.iloc[-1]
    mas, menos = coma(por_mes[alto]), coma(abs(por_mes[bajo]))
    cifras = [cifra(f"+{mas} %", f"en {MES_LARGO[alto - 1]}, el mes con más {QUE[obj]}"),
              cifra(f"−{menos} %", f"en {MES_LARGO[bajo - 1]}, el mes con menos"),
              cifra(f"{coma(largo.wape_con)} %", f"de error a 6–12 meses (sin la forma del año: {coma(largo.wape_sin)} %)")]
    titular = f"{MES_LARGO[alto - 1].capitalize()} trae {mas} % más {QUE[obj]}; {MES_LARGO[bajo - 1]}, {menos} % menos"

    fechas = pd.to_datetime(dict(year=2027, month=ef.mes, day=ef.dia))
    suave = ef.efecto_pct.rolling(15, center=True, min_periods=1).mean()
    efecto = go.Figure(go.Scatter(x=fechas, y=suave, mode="lines", line=dict(color=AZUL, width=2), fill="tozeroy",
                                  fillcolor="rgba(42,111,176,0.10)", customdata=[f"{f.day} de {MESES[f.month - 1]}" for f in fechas],
                                  hovertemplate="%{customdata}: %{y:+.1f} % frente al promedio<extra></extra>"))
    for i, etiqueta in [(suave.idxmax(), "pico"), (suave.idxmin(), "mínimo")]:
        efecto.add_annotation(x=fechas.loc[i], y=suave.loc[i], text=f"{etiqueta}: {suave.loc[i]:+.0f} %".replace("-", "−"), showarrow=False,
                              yshift=14 if suave.loc[i] > 0 else -14)
    estilo(efecto, tema).update_yaxes(ticksuffix=" %", zeroline=True, zerolinewidth=1)
    efecto.update_xaxes(tickmode="array", tickvals=[pd.Timestamp(2027, m, 15) for m in range(1, 13)], ticktext=MESES)

    x = [HORIZONTES.get(t, t) for t in er.tramo_dias]
    error = go.Figure()
    error.add_trace(go.Bar(x=x, y=er.wape_sin, name="Sin la forma del año", marker_color=PIZARRA,
                           hovertemplate="%{x}: %{y:.1f} % de error sin la forma del año<extra></extra>"))
    error.add_trace(go.Bar(x=x, y=er.wape_con, name="Con la forma del año", marker_color=AZUL, text=[f"{coma(v)} %" for v in er.wape_con],
                           textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:.1f} % de error con la forma del año<extra></extra>"))
    estilo(error, tema, leyenda=True).update_yaxes(ticksuffix=" %", rangemode="tozero", range=[0, max(er.wape_sin.max(), er.wape_con.max()) * 1.2])
    error.update_layout(barmode="group", bargap=0.38, bargroupgap=0.08)
    mejora = dato(f"−{coma(largo.wape_sin - largo.wape_con)} puntos", "de error al pronosticar a 6–12 meses")

    por_serie = todo.groupby(["objetivo", "mes"]).efecto_pct.mean().unstack(0)
    meses = go.Figure()
    for clave, nombre in SERIES:
        meses.add_trace(go.Bar(x=MESES, y=por_serie[clave].values, name=nombre, marker_color=AZUL if clave == SERIES[0][0] else PIZARRA,
                               hovertemplate=nombre + ", %{x}: %{y:+.1f} %<extra></extra>"))
    estilo(meses, tema, leyenda=True).update_yaxes(ticksuffix=" %", zeroline=True, zerolinewidth=1)
    meses.update_layout(barmode="group", bargap=0.3, bargroupgap=0.05)
    return cifras, titular, efecto, dato(*FUENTE[obj]), error, mejora, meses
