"""
dashboard/pages/resumen.py  -  pagina «Resumen» (13-nov-2026; formato de presentacion)
El proyecto en una pantalla: los ocho hallazgos del resumen ejecutivo, cada uno con el enlace a su pagina, y lo que se propone.
Es la segunda parada del recorrido, despues del inicio.

DATOS  Texto y cifras del resumen ejecutivo (docs/documento_final.md, seccion 1), escritos aqui como constantes. No lee ninguna tabla.
"""
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import AZUL, PIZARRA, bloque, cifra, coma, estilo, grafico, hecho, lamina, leer, mensaje, metodo, pagina, portada  # noqa: E402

dash.register_page(__name__, path="/resumen", name="Resumen", title="Resumen de hallazgos - HUN", order=5)

# (hallazgo, explicacion, pagina donde se ve, texto del enlace)
HALLAZGOS = [
    ("El cuello de botella es la espera de cama",
     "De la llegada a la asignación de la cama pasan 18,6 horas en mediana, y 1 de cada 10 pacientes espera más de 74. El 98 % de ese "
     "tiempo transcurre en urgencias.", "/espera", "Espera de cama"),
    ("Los peores casos empeoran",
     "La espera típica casi no cambió entre 2023 y 2026, pero la de los pacientes que más esperan pasó de 61 a 81 horas.",
     "/espera", "Espera de cama"),
    ("La cama llega en dos olas, por la tarde y por la noche",
     "El 61 % de las camas se asigna de 15 a 17 h o de 20 a 23 h, porque el 63 % de las altas sale por la tarde. Quien llega en la "
     "mañana espera hasta entonces.", "/altas", "Llegada y altas"),
    ("Hay un límite de proceso, no solo de camas",
     "Una cama que se libera en la mañana tarda 1,8 horas en volver a asignarse, aunque siempre haya unos 26 pacientes esperando.",
     "/altas", "Llegada y altas"),
    ("La ocupación sube porque los pacientes se quedan más",
     "Las camas ocupadas pasaron de 94 a 105, frente a las 106 del hospital. Los ingresos siguen en unos 20 por día; la estancia subió 16 %.",
     "/ocupacion", "Ocupación de camas"),
    ("Se puede anticipar el día y el año",
     "Las llegadas se pronostican con cerca de 8 % de error a una semana y 10 % a un año, y una alerta a mediodía detecta 13 de cada "
     "15 días congestionados.", "/pronostico", "Pronóstico"),
    ("La estancia es la palanca más barata",
     "En la simulación, bajar la estancia 5 % reduce los días saturados casi tanto como los aumentaría un 10 % más de ingresos.",
     "/camas", "Planeación de camas"),
    ("Se puede estimar cuándo recibirá cama cada paciente",
     "El estimador acierta sus rangos y mejora con las horas de espera. Con la gravedad y el servicio registrados al llegar, la mejora "
     "se duplicaría.", "/paciente", "Paciente en espera"),
]
PROPUESTAS = [
    ("1", "Registrar mejor", "La salida de urgencias, la asignación de cama, la gravedad, el servicio y la hora de la orden de hospitalización."),
    ("2", "Reunión diaria de camas", "Apoyada en las alertas de día congestionado y de ocupación alta."),
    ("3", "Adelantar altas y asignar enseguida", "Poner camas libres en la mañana y no dejar pasar horas antes de volver a ocuparlas."),
    ("4", "Alerta por paciente sin cama", "A las 48 horas de espera, con una persona responsable de resolver cada caso."),
    ("5", "Revisar las estancias largas", "Cada semana: son el 7 % de las estancias y ocupan un tercio de las camas."),
]


def _hallazgo(numero, titulo, texto, ruta, pagina_):
    return dcc.Link(href=ruta, className="hecho modelo hallazgo", children=[
        html.Div(f"{numero:02d}", className="lamina__num"), html.Div(titulo, className="modelo__pregunta"),
        html.P(texto, className="hallazgo__txt"), html.Span(f"Ver en {pagina_}", className="menu-card__go")])


def layout():
    return pagina(
        portada("Contexto · Resumen", "El cuello de botella es la espera de cama, y se puede anticipar y reducir",
                "El proyecto completo en una pantalla: ocho hallazgos, cada uno con su página, y lo que proponemos al hospital.",
                [cifra("18,6 h", "de espera mediana por una cama"), cifra("105 de 106", "camas ocupadas en promedio en 2025"),
                 cifra("7", "recomendaciones, cuatro con firmeza alta")]),
        lamina(1, "El problema en una gráfica: la espera típica no cambia, la de los peores casos sube cada año",
               "Horas desde que el paciente llega hasta que se le asigna cama, por año. **La barra gris es el paciente típico; la azul, "
               "el que espera más que 9 de cada 10.**",
               grafico("res-espera", alto=320), dato=("61 → 81 h", "esperan los peores casos, de 2023 a 2026"))
        if leer("espera_cubo.csv") is not None else None,
        bloque("Lo que encontramos, en ocho puntos", "Toca un hallazgo para ver su página con las gráficas y el detalle"),
        html.Div(className="hechos hechos--2", children=[_hallazgo(i, *h) for i, h in enumerate(HALLAZGOS, 1)]),
        bloque("Lo que proponemos", "Cinco líneas de acción; el detalle y la evidencia están en la página de Recomendaciones"),
        html.Div(className="hechos", children=[hecho(*p) for p in PROPUESTAS]),
        mensaje("Más que faltar camas, falta **liberarlas, asignarlas y desocuparlas a tiempo**.", titulo="En una frase"),
        metodo(
            "Datos del hospital de febrero de 2023 al 9 de abril de 2026, ya limpios (página de Datos y calidad). Cada cifra sale de la "
            "página o del documento que se enlaza; aquí solo se resumen.",
            "Casi todo son **asociaciones y escenarios** con supuestos escritos, no causas ni promesas. La meta de tiempos del hospital y "
            "la causa del cambio de registro desde abril de 2026 no se conocen.",
            "Fuente: docs/documento_final.md, sección 1 (resumen ejecutivo)."))


@callback(Output("res-espera", "figure"), Input("theme-store", "data"))
def espera(tema):
    c = leer("espera_cubo.csv", dtype={"anio": str})
    fig = go.Figure()
    if c is not None:
        t = c[(c.tipo_visita == "Todos") & (c.grupo_edad == "Todos") & (c.anio != "Todos")].sort_values("anio")
        x = [a if a != "2026" else "2026 (ene–abr)" for a in t.anio]
        fig.add_trace(go.Bar(x=x, y=t.mediana, name="Paciente típico (mediana)", marker_color=PIZARRA, text=[f"{coma(v, 0)} h" for v in t.mediana],
                             textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:.1f} h de espera mediana<extra></extra>"))
        fig.add_trace(go.Bar(x=x, y=t.p90, name="Peores casos (1 de cada 10)", marker_color=AZUL, text=[f"{coma(v, 0)} h" for v in t.p90],
                             textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:.1f} h en los peores casos<extra></extra>"))
        fig.update_yaxes(range=[0, t.p90.max() * 1.2])
    estilo(fig, tema, leyenda=True).update_yaxes(ticksuffix=" h")
    fig.update_xaxes(type="category")
    fig.update_layout(barmode="group", bargap=0.34, bargroupgap=0.06)
    return fig
