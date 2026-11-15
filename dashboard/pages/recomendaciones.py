"""
dashboard/pages/recomendaciones.py  -  pagina 4.1 «Qué hacemos con esto» (13-nov-2026)
Las 7 recomendaciones del proyecto, cada una con lo que dicen nuestros datos, la evidencia externa verificada, su firmeza,
su limite y como medirla. Sigue la plantilla de docs/estructura_dashboard.md (titulo = conclusion, pregunta, control,
tarjetas, pie con la fuente), con el encabezado en formato de presentacion de dashboard/componentes.py.

DATOS  datos/tablas_dashboard/recomendaciones_tabla.csv (tabla escrita a mano a partir de docs/recomendaciones.md; sin datos
       por paciente). Si falta, la pagina muestra un aviso en vez de tumbar el arranque del dashboard.
"""
import sys
from pathlib import Path

import dash
import pandas as pd
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import bloque as titulo_bloque, cifra, filtro, mensaje, portada  # noqa: E402
dash.register_page(__name__, path="/recomendaciones", name="Recomendaciones", title="Recomendaciones - HUN", order=5)

TABLA = Path(__file__).resolve().parents[2] / "datos" / "tablas_dashboard" / "recomendaciones_tabla.csv"
try:
    RECS = pd.read_csv(TABLA, encoding="utf-8").sort_values("prioridad")
    for _c in ("alerta_ids", "paginas_respaldo"):          # columnas de enlace (dashboard/catalogo.py); vacias si la tabla es la version anterior
        RECS[_c] = RECS[_c].fillna("") if _c in RECS else ""
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
        portada("Propuestas · Recomendaciones", "Más que faltar camas, falta liberarlas, asignarlas y desocuparlas a tiempo",
                "Siete acciones para el hospital, de la más básica a la más específica, cada una respaldada por los datos del HUN y por "
                "lo que se ha encontrado en otros hospitales.",
                [cifra(str(len(RECS)), f"recomendaciones: {n_alta} con firmeza alta y {len(RECS) - n_alta} con firmeza media"),
                 cifra("38", "fuentes externas, cada una leída en su versión original"),
                 cifra("1 de cada 5", "pacientes espera más de 48 horas por una cama")]),
        mensaje("Esperar mucho por una cama no es solo incómodo: en un estudio de 41.256 ingresos la mortalidad pasó de **2,5 %** en "
                "quienes esperaron menos de 2 horas a **4,5 %** en quienes esperaron 12 horas o más (Singer 2011), y una revisión de 21 "
                "estudios asocia las esperas largas con más errores de medicación y retrasos en el tratamiento (Dowling 2026).",
                titulo="Por qué vale la pena actuar"),
        html.Div(className="filtros", children=[filtro("rec-filtro", "Mostrar", [(v, n) for n, v in FILTROS], "todas")]),
        html.Div(id="rec-lista", className="rec-list"),
        titulo_bloque("Lo que no recomendamos", "Ideas que se evaluaron y que los datos no respaldan"),
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
