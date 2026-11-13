"""
dashboard/pages/datos.py  -  pagina «Datos y calidad» (13-nov-2026; pagina 1.3 de docs/estructura_dashboard.md; formato de presentacion)
De 3,3 millones de etapas a 337 mil episodios: que habia en la base, que se corrigio y por que solo se usa hasta el 9-abr-2026.
Pagina de contexto: cifras ya documentadas (CLAUDE.md 4.1 a 4.10, docs/documento_final.md seccion 3) y una figura del embudo.

DATOS  datos/tablas_dashboard/embudo_datos.csv (tabla escrita a mano, agregada; esta en el repositorio).
"""
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import AZUL, TENUE, antes_despues, bloque, cifra, estilo, grafico, hecho, lamina, leer, mensaje, metodo, miles, pagina, portada  # noqa: E402

dash.register_page(__name__, path="/datos", name="Datos y calidad", title="Datos y calidad - HUN", order=11)

PASOS = ["Etapas en la base", "Etapas de urgencias y hospitalización, cerradas", "Sin copias ni duplicados", "Episodios de atención finales"]
CORREGIDO = [
    ("30 %", "Visitas copia", "3 de cada 10 visitas repetían a otra, con las mismas etapas al segundo. Se conserva una sola."),
    ("41 %", "Hospitalizaciones en dos pacientes", "La misma estancia aparecía en dos personas. Se cuenta una vez, con la persona real, "
                                                   "que se identificó en el 97,6 % de los casos."),
    ("36–42 %", "Etapas sin hora de salida", "No se tratan como atenciones de 0 horas: se marcan sin duración y se analizan con métodos "
                                             "de supervivencia."),
    ("2 días", "Caída total del registro", "El 28 y el 29 de marzo de 2026 casi no hay registros. Se excluyen, igual que las etapas que "
                                           "seguían abiertas al extraer los datos."),
]
HOSPITAL = [
    ("106", "Camas de hospitalización", "88 de adultos y 18 de niños y neonatos."),
    ("58", "Camillas de urgencias", "Observación de adultos y pediátrica."),
    ("Al asignar la cama", "Se registra la hospitalización", "Por eso la espera se mide desde la llegada hasta la asignación de la cama."),
]


def layout():
    return pagina(
        portada("Contexto · Datos y calidad", "Antes de medir hubo que limpiar: 3 de cada 10 visitas eran copias",
                "La base traía visitas repetidas, hospitalizaciones contadas en dos pacientes y etapas sin hora de salida. "
                "Corregirlo cambió todas las cifras del hospital.",
                [cifra("30 %", "de las visitas eran copias de otra"), cifra("41 %", "de las hospitalizaciones estaba en dos pacientes"),
                 cifra("38 meses", "de datos confiables: feb-2023 a 9-abr-2026")]),
        lamina(1, "De 3,3 millones de etapas quedan 337 mil episodios de atención",
               "Cada paso de la limpieza quita registros que no son atenciones reales: citas administrativas, copias y duplicados.",
               grafico("dat-embudo", alto=270), dato=("337 mil", "episodios de atención analizados")),
        bloque("Qué se corrigió", "Cuatro problemas de calidad y la regla con que se resolvió cada uno"),
        html.Div(className="hechos", children=[hecho(*c) for c in CORREGIDO]),
        html.Div(className="hechos hechos--2", children=[
            html.Div(className="hecho", children=[
                html.Div("Sin la limpieza, el hospital parecía más lleno de lo que está", className="hecho__titulo"),
                antes_despues("146", "100", "camas ocupadas en promedio"), antes_despues("27,7", "20", "ingresos a cama por día")]),
            html.Div(className="hecho", children=[
                html.Div("Por qué el análisis llega solo hasta el 9 de abril de 2026", className="hecho__titulo"),
                antes_despues("65 %", "30 %", "de las visitas de urgencias con su etapa de llegada registrada, desde abril de 2026"),
                html.P("Las visitas no bajan: se registra menos detalle. No es menos demanda, y por eso esos meses no se usan.",
                       className="hecho__txt")]),
        ]),
        bloque("Lo que confirmó el hospital", "Sesión con el HUN del 29 de octubre de 2026"),
        html.Div(className="hechos", children=[hecho(*h) for h in HOSPITAL]),
        mensaje("**Todas las cifras del dashboard usan los datos limpios.** La limpieza es parte del resultado: sin ella, la ocupación y "
                "los ingresos salían inflados cerca de 40 %.", titulo="Por qué importa"),
        metodo(
            "Reglas documentadas en `src/analisis_etapas.py` y `src/preparar_variables.py`, verificadas con una auditoría de solo lectura "
            "en la base (2-nov-2026) y reproduciendo el proceso en una copia limpia. La base sigue el modelo OMOP y va de enero de 2023 a "
            "julio de 2026.",
            "La persona real de las estancias duplicadas se deduce de los datos; el hospital dijo que «lo más probable» es que sean "
            "duplicados, pero no confirmó cuál es. Tampoco explicó por qué cambia el registro desde abril de 2026.",
            "Fuente: datos/tablas_dashboard/embudo_datos.csv · CLAUDE.md 4.1, 4.3, 4.6, 4.9 y 4.10 · sesión con el HUN del 29-oct-2026."))


@callback(Output("dat-embudo", "figure"), Input("theme-store", "data"))
def embudo(tema):
    e = leer("embudo_datos.csv")
    fig = go.Figure()
    if e is not None:
        e = e.sort_values("orden")
        fig.add_trace(go.Bar(y=PASOS[:len(e)], x=e.etapas, orientation="h", marker_color=[TENUE] * (len(e) - 1) + [AZUL],
                             text=[miles(v) for v in e.etapas], textposition="outside", cliponaxis=False, customdata=e.nota,
                             hovertemplate="<b>%{y}</b><br>%{x:,.0f} registros<br>%{customdata}<extra></extra>"))
    estilo(fig, tema)
    fig.update_layout(margin=dict(l=10, r=90, t=6, b=6), bargap=0.5)
    fig.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    fig.update_xaxes(showticklabels=False, showline=False)
    return fig
