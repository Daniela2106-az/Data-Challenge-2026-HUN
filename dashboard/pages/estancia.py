"""
dashboard/pages/estancia.py  -  pagina «Estancias largas» (13-nov-2026; pagina 2.7 de docs/estructura_dashboard.md; formato de presentacion)
Por que subio la estancia media y que comparten las estancias que se disparan (tareas A2 y A2b).

DATOS  Cifras ya publicadas (docs/factores_estancia.md, docs/estancias_disparadas.md y CLAUDE.md 4.8), escritas aqui como constantes.
       No lee ninguna tabla. Estancias unicas con alta completa; «larga» = mas de 14 dias en cama.
"""
import sys
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import AZUL, PIZARRA, TENUE, bloque, cifra, coma, estilo, grafico, hecho, lamina, leer, mensaje, metodo, pagina, portada  # noqa: E402

dash.register_page(__name__, path="/estancia", name="Estancias largas", title="Estancias largas - HUN", order=26)

# camas ocupadas que suma o resta cada tramo de duracion entre 2023 y 2025 (la ocupacion media sube 11 camas)
CAMAS = [("Hasta 7 días", -2.5), ("De 7 a 14 días", 2.9), ("De 14 a 30 días", 3.6), ("Más de 30 días", 6.9)]
# (año, estancia media en dias, % de estancias de mas de 14 dias)
POR_ANIO = [(2023, 4.57, 5.5), (2024, 4.90, 6.6), (2025, 5.31, 7.3)]
# (grupo de edad, cuantas veces mas probable es una estancia larga frente a los de 15 a 29 años)
EDAD = [("15 a 29 años", 1.0), ("45 a 59 años", 2.0), ("60 a 74 años", 2.5), ("75 años o más", 3.0)]
# (grupo de diagnostico, cuantas veces mas probable es una estancia larga frente al resto)
POR_DX = [("Cáncer y tumores", 2.8), ("Infecciosas", 2.7), ("Salud mental", 2.6), ("Musculoesquelético", 2.3), ("Neurológico", 2.1),
          ("Renal y urinario", 0.5), ("Embarazo y parto", 0.4)]
COMPARTEN = [
    ("21 veces", "Catéter central (PICC)", "Más frecuente en las estancias largas que en el resto: 11,6 % frente a 0,6 %."),
    ("8 veces", "Nutrición hospitalaria", "El 23 % de las estancias largas la recibe, frente al 3 % de las demás."),
    ("6 veces", "Transfusión de glóbulos rojos", "13 % frente a 2 %. Marca pacientes complejos, no una causa."),
    ("5 a 7 veces", "Cultivos de sangre", "Los hemocultivos tempranos indican sospecha de infección desde el inicio."),
]


def _mensual():
    """Estancias largas por mes (datos/tablas_dashboard/disparadas_por_mes.csv), o None. Largas: más de 14 días; muy largas: más de 30."""
    t = leer("disparadas_por_mes.csv")
    return None if t is None or t.empty else t.assign(mes=pd.to_datetime(t.mes)).sort_values("mes")


def _lamina_mensual():
    t = _mensual()
    if t is None:
        return []
    ini, fin = t.pct_largas.head(12).mean(), t.pct_largas.tail(12).mean()
    return [lamina(5, "Las estancias largas se van volviendo más frecuentes mes a mes",
                   f"De cada 100 pacientes hospitalizados, los que se quedan **más de 14 días** pasaron de **{coma(ini, 1)}** en el primer año a **{coma(fin, 1)}** en los últimos "
                   "12 meses. Las de más de 30 días son pocas, pero ocupan muchas camas. Es una asociación y las barras mensuales se mueven un poco por azar.",
                   grafico("lar-mensual", alto=320), dato=(f"{coma(ini, 1)} → {coma(fin, 1)} %", "de los hospitalizados se queda más de 14 días"), invertida=True)]


def _tabla_laboratorios():
    """Examenes de laboratorio de las primeras 48 h mas asociados a las estancias largas (datos/tablas_dashboard/disparadas_laboratorios.csv)."""
    t = leer("disparadas_laboratorios.csv")
    if t is None or t.empty:
        return []
    cab = html.Thead(html.Tr([html.Th(c) for c in ["Examen (primeras 48 h)", "Estancias con el examen", "% de las estancias largas", "% de las demás", "Veces más frecuente"]]))
    filas = [html.Tr([html.Td(r.nombre), html.Td(f"{int(r.estancias):,}".replace(",", ".")), html.Td(f"{coma(r.pct_largas, 1)} %"), html.Td(f"{coma(r.pct_otras, 1)} %"),
                      html.Td(f"{coma(r.razon, 1)}×")]) for r in t.itertuples()]
    return [bloque("Laboratorios más asociados a las estancias largas", "Exámenes de las primeras 48 horas que aparecen mucho más en quienes se quedan más de 14 días"),
            html.Div(className="tech-table-wrap", children=[html.Table(className="tech-table", children=[cab, html.Tbody(filas)])]),
            html.P("Un examen frecuente indica sospecha, no causa: los pacientes más graves tienen más exámenes. Los nombres son los de la base.", style={"fontSize": "12px", "opacity": .75, "marginTop": "6px"})]


def layout():
    return pagina(
        portada("Resultados · Estancias largas", "Unas pocas estancias muy largas explican casi todo el aumento de la ocupación",
                "La estancia media subió 16 % en dos años. No es que cada paciente se quede un poco más: creció la cola de pacientes que "
                "se quedan semanas.",
                [cifra("7 %", "de las estancias dura más de 14 días"), cifra("1 de cada 3", "camas la ocupa una de esas estancias largas"),
                 cifra("63 → 117", "estancias de más de 30 días por año, de 2023 a 2025")]),
        lamina(1, "De las 11 camas que subió la ocupación, 7 vienen de estancias de más de 30 días",
               "Cada barra es cuántas camas ocupadas sumó o restó ese tramo de duración entre 2023 y 2025. **Las estancias cortas ocupan "
               "hoy menos camas que antes**; todo el aumento está en las largas.",
               grafico("lar-camas", alto=340), dato=("+10,5 camas", "suman las estancias de más de 14 días")),
        lamina(2, "Cada año hay más estancias largas",
               "Porcentaje de estancias que duran más de 14 días, por año de ingreso. La subida es gradual, sobre todo desde finales de "
               "2024: no hay «meses malos» puntuales.",
               grafico("lar-anio", alto=320), dato=("+16 %", "de estancia media: de 4,6 a 5,3 días"), invertida=True),
        lamina(3, "A mayor edad, más riesgo de quedarse semanas",
               "Cuántas veces más probable es una estancia larga frente a los pacientes de 15 a 29 años. También pesa la ruta: las visitas "
               "de tipo «treatment urgency» tienen 2,4 veces más estancias largas.",
               grafico("lar-edad", alto=320), dato=("3 veces", "más probable desde los 75 años")),
        lamina(4, "Cáncer, infecciones y salud mental casi triplican el riesgo",
               "Cuántas veces más probable es una estancia larga en cada grupo de diagnóstico frente al resto. **En gris, los grupos "
               "con menos riesgo**: los partos y los problemas renales casi nunca se alargan.",
               grafico("lar-dx", alto=330), dato=("12,7 %", "de las visitas «treatment urgency» termina en una estancia larga, el doble que el resto"),
               invertida=True),
        *_lamina_mensual(),
        bloque("Qué comparten las estancias largas", "Procedimientos y exámenes mucho más frecuentes en ellas que en el resto"),
        html.Div(className="hechos", children=[hecho(*c) for c in COMPARTEN]),
        *_tabla_laboratorios(),
        mensaje("**Revisar cada semana las estancias largas es la forma más directa de liberar camas** (recomendación 7): son el 7 % de "
                "las estancias y ocupan un tercio de las camas. Bajar la estancia 5 % equivale a unas 5 camas."),
        metodo(
            "Estancias únicas con alta completa del periodo confiable. El aporte en camas compara la ocupación media de 2023 y de 2025 por "
            "tramo de duración. El riesgo por edad sale de un modelo logístico con lo que se sabe al llegar (AUC 0,69): describe, no "
            "predice una estancia individual.",
            "Los procedimientos tienen **sesgo de duración**: quien se queda más tiempo acumula más procedimientos, así que no son causas. "
            "Un cultivo temprano indica sospecha, no confirma una infección. El diagnóstico se registra tarde.",
            "Fuente: docs/factores_estancia.md · docs/estancias_disparadas.md · CLAUDE.md 4.8 · asociación, no causa.", ruta="/estancia"))


@callback(Output("lar-camas", "figure"), Output("lar-anio", "figure"), Output("lar-edad", "figure"), Output("lar-dx", "figure"),
          Input("theme-store", "data"))
def figuras(tema):
    def barras(x, y, colores, textos, flotante):
        fig = go.Figure(go.Bar(x=x, y=y, marker_color=colores, text=textos, textposition="outside", cliponaxis=False, hovertemplate=flotante))
        estilo(fig, tema)
        return fig

    v = [c for _, c in CAMAS]
    camas = barras([n for n, _ in CAMAS], v, [TENUE, TENUE, AZUL, AZUL], [f"{c:+.1f}".replace(".", ",").replace("-", "−") for c in v],
                   "%{x}: %{y:+.1f} camas ocupadas entre 2023 y 2025<extra></extra>")
    camas.update_yaxes(range=[-4.5, 8.5], zeroline=True, zerolinewidth=1, title_text="camas ocupadas")
    camas.update_layout(margin_l=64)

    anio = barras([str(a) for a, *_ in POR_ANIO], [p for *_, p in POR_ANIO], [TENUE, TENUE, AZUL], [f"{coma(p)} %" for *_, p in POR_ANIO],
                  "%{x}: %{y:.1f} % de las estancias dura más de 14 días · estancia media de %{customdata} días<extra></extra>")
    anio.update_traces(customdata=[coma(m, 2) for _, m, _ in POR_ANIO])
    anio.update_yaxes(ticksuffix=" %", range=[0, 8.8])
    anio.update_xaxes(type="category")

    edad = barras([e for e, _ in EDAD], [m for _, m in EDAD], [TENUE, TENUE, TENUE, AZUL], [f"{coma(m)} ×" for _, m in EDAD],
                  "%{x}: %{y:.1f} veces la probabilidad de una estancia larga<extra></extra>")
    edad.update_yaxes(range=[0, 3.6], ticksuffix=" ×")

    dx = go.Figure(go.Bar(y=[g for g, _ in POR_DX], x=[v for _, v in POR_DX], orientation="h",
                          marker_color=[AZUL if v > 1 else TENUE for _, v in POR_DX], text=[f"{coma(v)} ×" for _, v in POR_DX],
                          textposition="outside", cliponaxis=False,
                          hovertemplate="<b>%{y}</b><br>%{x:.1f} veces la probabilidad de una estancia larga<extra></extra>"))
    estilo(dx, tema)
    dx.add_vline(x=1, line=dict(color="rgba(127,140,155,0.7)", width=1, dash="dot"))
    dx.update_layout(margin=dict(l=10, r=44, t=6, b=6), bargap=0.36)
    dx.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    dx.update_xaxes(showticklabels=False, showline=False, range=[0, 3.3])
    return camas, anio, edad, dx


@callback(Output("lar-mensual", "figure"), Input("theme-store", "data"))
def figura_mensual(tema):
    fig, t = go.Figure(), _mensual()
    if t is not None:
        fig.add_trace(go.Scatter(x=t.mes, y=t.pct_largas, mode="lines+markers", name="Más de 14 días", line=dict(color=AZUL, width=2.5),
                                 hovertemplate="%{x|%b %Y}: %{y:.1f} % se queda más de 14 días<extra></extra>"))
        fig.add_trace(go.Scatter(x=t.mes, y=t.pct_muy_largas, mode="lines+markers", name="Más de 30 días", line=dict(color=PIZARRA, width=2),
                                 hovertemplate="%{x|%b %Y}: %{y:.1f} % se queda más de 30 días<extra></extra>"))
        estilo(fig, tema, leyenda=True).update_yaxes(ticksuffix=" %", rangemode="tozero")
    return fig
