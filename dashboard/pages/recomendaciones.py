"""
dashboard/pages/recomendaciones.py  -  pagina 4.1 «Qué hacemos con esto» (13-nov-2026)
Las 7 recomendaciones del proyecto, cada una con lo que dicen nuestros datos, la evidencia externa verificada, su firmeza,
su limite y como medirla. Sigue la plantilla de docs/estructura_dashboard.md (titulo = conclusion, pregunta, control,
tarjetas, pie con la fuente).

DATOS  datos/tablas_dashboard/recomendaciones_tabla.csv (tabla escrita a mano a partir de docs/recomendaciones.md; sin datos
       por paciente). Si falta, la pagina muestra un aviso en vez de tumbar el arranque del dashboard.
"""
from pathlib import Path

import dash
import pandas as pd
from dash import Input, Output, callback, dcc, html

dash.register_page(__name__, path="/recomendaciones", name="Recomendaciones", title="Recomendaciones - HUN", order=5)

TABLA = Path(__file__).resolve().parents[2] / "datos" / "tablas_dashboard" / "recomendaciones_tabla.csv"
try:
    RECS = pd.read_csv(TABLA, encoding="utf-8").sort_values("prioridad")
    DATOS_OK = True
except (FileNotFoundError, OSError):
    RECS, DATOS_OK = pd.DataFrame(), False

FILTROS = [("Todas", "todas"), ("Firmeza alta", "Alta"), ("Firmeza media", "Media")]
NO_RECOMENDAMOS = [
    ("Reforzar el personal según el día de la semana", "El día de la semana y los festivos casi no cambian la espera."),
    ("Ordenar la fila según el riesgo de cada paciente al llegar",
     "El mejor modelo marcaría al 44 % de los pacientes, con 4 de cada 10 falsas alarmas."),
    ("Un centro de comando como solución por sí mismo", "El estudio mejor diseñado (Bradford, Reino Unido) no encontró efecto."),
    ("Calcular cuántas camas más hacen falta",
     "Los datos no lo permiten con certeza: antes de pensar en camas nuevas, atacar la estancia y la asignación."),
]


def chip(firmeza):
    return html.Span(f"Firmeza {firmeza.lower()}", className=f"rec-chip rec-chip--{firmeza.lower()}")


def bloque(titulo, texto):
    return html.Div(className="rec-block", children=[html.Div(titulo, className="rec-block__label"), html.P(texto)])


def tarjeta(r):
    return html.Div(className="card rec-card", children=[
        html.Div(className="rec-card__head", children=[
            html.Span(str(int(r.prioridad)), className="rec-card__num"),
            html.Div(r.recomendacion, className="rec-card__title"),
            chip(r.firmeza),
        ]),
        html.Div(className="rec-card__body", children=[
            bloque("Lo que dicen nuestros datos", r.impacto_estimado),
            bloque("Lo que se encontró en otros hospitales", r.evidencia_externa),
        ]),
        html.Details(className="rec-card__more", children=[
            html.Summary("Límite, cómo medirla y fuente"),
            bloque("Límite", r.limite),
            bloque("Cómo medirla", r.como_medir),
            html.P(f"Fuente en el repositorio: {r.fuente_datos}", className="rec-card__src"),
        ]),
    ])


def layout():
    if not DATOS_OK:
        return html.Div(className="page-container", children=[
            html.H2("Recomendaciones"),
            html.P("No se encontró datos/tablas_dashboard/recomendaciones_tabla.csv en este equipo.", style={"color": "#c0392b"}),
        ])
    n_alta = int((RECS.firmeza == "Alta").sum())
    return html.Div(className="page-container", children=[
        html.H2("Más que faltar camas, falta liberarlas, asignarlas y desocuparlas a tiempo"),
        html.P("¿Qué puede hacer el hospital con lo que encontramos? Siete acciones, de la más básica a la más específica, cada una "
               "respaldada por los datos del HUN y por lo que se ha encontrado en otros hospitales.", className="rec-lead"),
        html.Div(className="stat-row rec-stats", children=[
            html.Div(className="metric-card", children=[html.Div("Recomendaciones"), html.Div(str(len(RECS))),
                                                         html.Div(f"{n_alta} con firmeza alta y {len(RECS) - n_alta} media")]),
            html.Div(className="metric-card", children=[html.Div("Fuentes externas"), html.Div("38"),
                                                         html.Div("cada una leída en su versión original")]),
            html.Div(className="metric-card", children=[html.Div("Pacientes con más de 48 h sin cama"), html.Div("1 de cada 5"),
                                                         html.Div("periodo confiable, feb-2023 a abr-2026")]),
        ]),
        html.Div(className="card rec-why", children=[
            html.Div("Por qué vale la pena actuar", className="rec-block__label"),
            html.P("Esperar mucho por una cama no es solo incómodo: en un estudio de 41.256 ingresos la mortalidad pasó de 2,5 % en "
                   "quienes esperaron menos de 2 horas a 4,5 % en quienes esperaron 12 horas o más (Singer 2011), y una revisión de 21 "
                   "estudios asocia las esperas largas con más errores de medicación y retrasos en el tratamiento (Dowling 2026)."),
        ]),
        html.Div(className="rec-filter", children=[
            html.Label("Mostrar", style={"fontWeight": 600}),
            dcc.RadioItems(id="rec-filtro", options=[{"label": " " + n, "value": v} for n, v in FILTROS], value="todas",
                           inline=True, inputStyle={"marginLeft": "14px"}),
        ]),
        html.Div(id="rec-lista", className="rec-list"),
        html.H4("Lo que no recomendamos", className="section-title"),
        html.Div(className="rec-no", children=[
            html.Div(className="card rec-no__item", children=[html.Div(t, className="rec-card__title"), html.P(d)])
            for t, d in NO_RECOMENDAMOS]),
        html.P(["Cómo leer la firmeza: es «alta» cuando se cumplen tres condiciones: los datos del HUN muestran el problema con claridad; al "
                "menos tres estudios independientes, o uno multicéntrico, coinciden en que actuar ahí ayuda (o, para las alertas, en que el "
                "problema vigilado se asocia con daño); y la acción es de bajo costo y riesgo. Es «media» cuando falta una de las tres. Todo son "
                "asociaciones y escenarios con supuestos escritos, no promesas. Detalle y verificación de las 38 fuentes: ",
                html.Code("docs/recomendaciones.md"), "."], className="rec-foot"),
    ])


@callback(Output("rec-lista", "children"), Input("rec-filtro", "value"))
def filtrar(valor):
    if not DATOS_OK:
        return []
    filas = RECS if valor == "todas" else RECS[RECS.firmeza == valor]
    return [tarjeta(r) for r in filas.itertuples()]
