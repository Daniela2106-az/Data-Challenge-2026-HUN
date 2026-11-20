"""
dashboard/pages/datos.py  -  pagina «Datos y calidad» (13-nov-2026; pagina 1.3 de docs/estructura_dashboard.md; formato de presentacion)
De 3,3 millones de etapas a 337 mil episodios: que habia en la base, que se corrigio y por que solo se usa hasta el 9-abr-2026.
Pagina de contexto: cifras ya documentadas (docs/CONTEXTO_TECNICO.md 4.1 a 4.10, docs/documento_final.md seccion 3) y una figura del embudo.

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
# Que hay en la base y que no (docs/CONTEXTO_TECNICO.md secciones 2 y 3): cifras ya publicadas
BASE = [
    ("1,7 M", "Visitas", "De enero de 2023 a julio de 2026, de unos 304 mil pacientes."),
    ("3,3 M", "Etapas del recorrido", "Llegada, atención en urgencias y hospitalización. De aquí salen todos los tiempos."),
    ("38,6 M", "Diagnósticos", "El 37 % sin traducir, y se registran tarde: sirven para explicar, no para predecir al llegar."),
    ("16,6 M", "Laboratorios", "La única tabla clínica con una hora útil: la de la toma de la muestra."),
]
FALTA = [
    ("Servicio y cama", "No se sabe en qué piso está el paciente", "No se puede separar piso, cuidados intensivos ni camillas."),
    ("Gravedad", "No hay triage ni signos vitales", "Con la gravedad al llegar, el estimador de espera mejoraría el doble."),
    ("Orden de hospitalizar", "No se registra su hora", "Por eso no se separa la atención clínica de la espera pura por una cama."),
    ("Hora de salida", "Falta en 4 de cada 10 etapas de urgencias", "Quien se va de alta desde urgencias casi nunca tiene hora de fin."),
]
# (año, % de las etapas de atencion en urgencias sin hora de salida) - conteo directo en la base (docs/CONTEXTO_TECNICO.md 4.3)
SIN_FIN = [("2023", 41.6), ("2024", 38.4), ("2025", 35.8), ("2026", 36.6)]
# (mes de 2026, % de las visitas de urgencias con su etapa de llegada registrada) - auditoria en la base (docs/CONTEXTO_TECNICO.md 4.9, lote 2)
REGISTRO = [("Enero", 65.7), ("Febrero", 64.7), ("Marzo", 64.6), ("Abril", 54.0), ("Mayo", 28.4), ("Junio", 29.6)]
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
        lamina(2, "4 de cada 10 etapas de urgencias no tienen hora de salida",
               "Porcentaje de etapas de atención en urgencias que no registran cuándo terminaron, por año. **No son atenciones "
               "cortas: falta el dato.** Mejora un poco cada año, pero sigue siendo el mayor vacío de la base.",
               grafico("dat-sinfin", alto=300), dato=("100 %", "de las hospitalizaciones sí tiene sus tiempos completos"), invertida=True),
        lamina(3, "En abril de 2026 el registro se rompe: la etapa de llegada cae de 65 % a 30 %",
               "Porcentaje de las visitas de urgencias de 2026 que tienen registrada su etapa de llegada. **Las visitas no bajan; lo "
               "que baja es el detalle.** Por eso todo el análisis usa los datos hasta el 9 de abril: en gris, los meses que no se usan.",
               grafico("dat-registro", alto=300), dato=("+2 %", "de visitas de urgencias en mayo de 2026 frente a mayo de 2025: no es menos demanda")),
        bloque("Qué hay en la base", "Una base clínica en formato OMOP, de solo lectura"),
        html.Div(className="hechos", children=[hecho(*b) for b in BASE]),
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
        bloque("Lo que la base no registra", "Cuatro vacíos que limitan lo que se puede concluir, y que proponemos empezar a registrar"),
        html.Div(className="hechos", children=[hecho(*f) for f in FALTA]),
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
            "Fuente: datos/tablas_dashboard/embudo_datos.csv · docs/CONTEXTO_TECNICO.md 4.1, 4.3, 4.6, 4.9 y 4.10 · sesión con el HUN del 29-oct-2026.", ruta="/datos"))


@callback(Output("dat-registro", "figure"), Input("theme-store", "data"))
def registro(tema):
    fig = go.Figure(go.Bar(x=[m for m, _ in REGISTRO], y=[v for _, v in REGISTRO], marker_color=[AZUL] * 3 + [TENUE] * 3,
                           text=[f"{v:.0f} %" for _, v in REGISTRO], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x} de 2026: %{y:.1f} % de las visitas con etapa de llegada<extra></extra>"))
    estilo(fig, tema).update_yaxes(ticksuffix=" %", range=[0, 78])
    fig.update_layout(bargap=0.4)
    return fig


@callback(Output("dat-sinfin", "figure"), Input("theme-store", "data"))
def sin_fin(tema):
    fig = go.Figure(go.Bar(x=[a for a, _ in SIN_FIN], y=[v for _, v in SIN_FIN], marker_color=[AZUL] + [TENUE] * 3,
                           text=[f"{v:.1f} %".replace(".", ",") for _, v in SIN_FIN], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{y:.1f} % de las etapas de urgencias sin hora de salida<extra></extra>"))
    estilo(fig, tema).update_yaxes(ticksuffix=" %", range=[0, 50])
    fig.update_xaxes(type="category")
    fig.update_layout(bargap=0.45)
    return fig


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
