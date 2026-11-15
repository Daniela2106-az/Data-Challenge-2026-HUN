"""
dashboard/pages/atipicos.py  -  pagina «Días atípicos» (13-nov-2026; pagina 3.3 de docs/estructura_dashboard.md; formato de presentacion)
Los dias que se salen del patron frente al pronostico (llegadas, ingresos a cama y espera) y que dicen del problema de la espera.

DATOS  Tablas ya publicadas en docs/dias_atipicos.md, escritas aqui como constantes (son dias, no pacientes). No lee ninguna tabla.
       Un dia es atipico si se aparta mas de 3 desviaciones de lo que esperaba el pronostico.
"""
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import AZUL, MESES, PIZARRA, TENUE, bloque, cifra, coma, estilo, filtro, grafico, hecho, lamina, leer, ficha_de, interpretacion_de, mensaje, metodo, pagina, portada  # noqa: E402

dash.register_page(__name__, path="/atipicos", name="Días atípicos", title="Días atípicos - HUN", order=34)

# (fecha, llegadas reales, llegadas esperadas, observacion) - los 14 dias atipicos de llegadas
DIAS = [("2023-07-03", 181, 240, "lunes festivo"), ("2023-12-05", 221, 305, "grupo del 5 al 7 de diciembre, sin causa aparente"),
        ("2023-12-06", 200, 269, "grupo del 5 al 7 de diciembre, sin causa aparente"), ("2023-12-07", 188, 247, "víspera del festivo del 8 de diciembre"),
        ("2024-02-12", 192, 254, "lunes de Carnaval"), ("2024-06-15", 111, 250, "solo 8 ingresos a cama: posible corte del sistema"),
        ("2024-09-22", 158, 204, "sin causa aparente"), ("2025-03-01", 128, 174, "sábado de Carnaval"),
        ("2025-11-01", 168, 223, "sábado de fin de semana largo"), ("2025-12-25", 212, 161, "Navidad: más de lo esperado"),
        ("2026-02-02", 229, 301, "sin causa aparente"), ("2026-03-28", 88, 221, "un solo ingreso a cama: posible corte del sistema"),
        ("2026-04-29", 173, 268, "inicio del registro incompleto"), ("2026-05-09", 126, 186, "periodo de registro incompleto")]
VARIABLES = [("llegadas", "Llegadas"), ("ingresos a cama", "Ingresos a cama"), ("espera de cama (mediana del dia)", "Espera de cama")]
CORTES = {"2024-06-15", "2026-03-28"}
# (variable, dias con mas de lo esperado, dias con menos de lo esperado)
RESUMEN = [("Llegadas", 1, 13), ("Ingresos a cama", 3, 6), ("Espera de cama", 0, 7)]
CALENDARIO = [
    ("−16 %", "Carnaval de Barranquilla", "El sábado y el lunes de Carnaval llegan menos pacientes. Se descubrió revisando estos días y "
                                          "ahora el pronóstico lo incluye."),
    ("−37 %", "24 y 31 de diciembre", "Bajan mucho las llegadas; el 25 de diciembre y el 1 de enero se comportan como un festivo normal."),
    ("3 días", "Del 5 al 7 de diciembre de 2023", "Entre 24 % y 28 % menos llegadas de lo esperado, sin causa conocida. El hospital "
                                                  "podría saber qué pasó."),
]


def _fecha(f):
    a, m, d = f.split("-")
    return f"{int(d)} {MESES[int(m) - 1]} {a}"


def _tabla():
    """Los 14 dias atipicos de llegadas, uno por uno (los dos posibles cortes del sistema, resaltados)."""
    cabecera = html.Thead(html.Tr([html.Th("Fecha"), html.Th("Llegadas", className="num"), html.Th("Se esperaban", className="num"),
                                   html.Th("Diferencia", className="num"), html.Th("Observación")]))
    filas = [html.Tr(className="destacada" if f in CORTES else None, children=[
        html.Td(_fecha(f)), html.Td(str(r), className="num"), html.Td(str(e), className="num"),
        html.Td(f"{'+' if r > e else '−'}{abs(round(100 * (r / e - 1)))} %", className="num"), html.Td(o.capitalize())])
        for f, r, e, o in DIAS]
    return html.Div(className="card tabla-wrap", children=html.Table(className="tabla", children=[cabecera, html.Tbody(filas)]))


def layout():
    return pagina(
        portada("Resultados · Días atípicos", "Ningún día tuvo una espera más alta de lo esperado: el problema es de todos los días",
                "En más de tres años, los días raros son casi todos de menos actividad. La espera larga no aparece en días récord, sino "
                "como algo constante.",
                [cifra("14", "días atípicos de llegadas entre 2023 y 2026"), cifra("13 de 14", "fueron días con menos llegadas de lo esperado"),
                 cifra("0", "días con espera más alta de lo esperado")]),
        lamina(1, "Los dos días más extremos parecen cortes del sistema, no menos pacientes",
               "Cada barra es un día atípico: cuánto se apartaron las llegadas de lo que esperaba el pronóstico. **En azul, los dos días "
               "en que también cayeron los ingresos a cama**, algo que apunta a una falla de registro. Pasa el cursor para ver cada día.",
               grafico("ati-dias", alto=360), dato=("−60 %", "de llegadas el 28 de marzo de 2026, con un solo ingreso a cama")),
        lamina(2, "La espera larga no produce días récord",
               "Días con más y con menos de lo esperado en cada serie. **Los 7 días atípicos de espera son de espera más corta**, casi "
               "todos domingos, festivos o Semana Santa.",
               grafico("ati-resumen", alto=320), dato=("0 días", "con una espera más alta de lo esperado"), invertida=True),
        bloque("Los 14 días, uno por uno", "Llegadas reales frente a las que esperaba el pronóstico; resaltados, los dos posibles cortes del sistema"),
        _tabla(),
        bloque("Los días atípicos de cada serie", "Elige qué mirar: cuánto se apartó cada día de lo esperado y qué lo explica"),
        html.Div(className="filtros", children=[filtro("ati-var", "Qué mirar", VARIABLES, "llegadas")]),
        grafico("ati-var-grafico", alto=340),
        html.Div(id="ati-var-tabla"),
        bloque("Lo que explica el calendario", "Revisar los días raros sirvió para mejorar el pronóstico"),
        html.Div(className="hechos", children=[hecho(*c) for c in CALENDARIO]),
        mensaje("**El problema de la espera es crónico, no de días malos.** Reaccionar a los picos no lo resuelve: hay que cambiar el "
                "proceso diario de altas y de asignación de camas."),
        interpretacion_de("/atipicos"),
        metodo(
            "Un día es atípico si se aparta más de 3 desviaciones de lo que esperaba el pronóstico, que ya conoce el día de la semana, los "
            "festivos y el Carnaval. Con ese umbral se esperan unos 3 días por azar en cada serie.",
            "Que dos días parezcan cortes del sistema es una **hipótesis sin comprobar**: los datos no dicen qué pasó. La caída desde "
            "abril de 2026 no es un día atípico sino un cambio del registro, y se trata aparte. Se asume que el hospital está en Barranquilla.",
            "Fuente: docs/dias_atipicos.md · src/dias_atipicos.py.", ruta="/atipicos"),
        ficha_de("/atipicos"),
    )


@callback(Output("ati-dias", "figure"), Output("ati-resumen", "figure"), Input("theme-store", "data"))
def figuras(tema):
    def fecha(f):
        a, m, d = f.split("-")
        return f"{int(d)} {MESES[int(m) - 1]} {a}"

    desvio = [100 * (r / e - 1) for _, r, e, _ in DIAS]
    dias = go.Figure(go.Bar(x=[fecha(f) for f, *_ in DIAS], y=desvio, marker_color=[AZUL if f in CORTES else TENUE for f, *_ in DIAS],
                            customdata=[[r, e, o] for _, r, e, o in DIAS],
                            hovertemplate="<b>%{x}</b><br>%{customdata[0]} llegadas; se esperaban %{customdata[1]} (%{y:+.0f} %)"
                                          "<br>%{customdata[2]}<extra></extra>"))
    estilo(dias, tema).update_yaxes(ticksuffix=" %", zeroline=True, zerolinewidth=1, range=[-70, 40])
    dias.update_xaxes(type="category", tickangle=-45)
    dias.update_layout(margin_b=78, bargap=0.3)

    nombres = [n for n, *_ in RESUMEN]
    resumen = go.Figure()
    resumen.add_trace(go.Bar(x=nombres, y=[m for _, m, _ in RESUMEN], name="Más de lo esperado", marker_color=AZUL,
                             text=[str(m) for _, m, _ in RESUMEN], textposition="outside", cliponaxis=False,
                             hovertemplate="%{x}: %{y} días con más de lo esperado<extra></extra>"))
    resumen.add_trace(go.Bar(x=nombres, y=[m for *_, m in RESUMEN], name="Menos de lo esperado", marker_color=PIZARRA,
                             text=[str(m) for *_, m in RESUMEN], textposition="outside", cliponaxis=False,
                             hovertemplate="%{x}: %{y} días con menos de lo esperado<extra></extra>"))
    estilo(resumen, tema, leyenda=True).update_yaxes(range=[0, 15.5], title_text="días atípicos")
    resumen.update_layout(barmode="group", bargap=0.36, bargroupgap=0.08, margin_l=60)
    return dias, resumen


@callback(Output("ati-var-grafico", "figure"), Output("ati-var-tabla", "children"), Input("ati-var", "value"), Input("theme-store", "data"))
def por_variable(var, tema):
    t = leer("dias_atipicos.csv")
    if t is None:
        return go.Figure(), html.P("No se encontró dias_atipicos.csv.")
    t = t[t.variable == var].sort_values("fecha")
    unidad = " h" if var.startswith("espera") else ""
    desv = 100 * (t.real / t.esperado - 1)
    mas = t.sentido.str.startswith("mas")
    fig = go.Figure(go.Bar(x=[_fecha(f) for f in t.fecha], y=desv, marker_color=[AZUL if m else TENUE for m in mas],
                           customdata=list(zip(t.real, t.esperado, t.causa_calendario.str.capitalize())),
                           hovertemplate="<b>%{x}</b><br>Real: %{customdata[0]}" + unidad + "; se esperaba %{customdata[1]}" + unidad + " (%{y:+.0f} %)<br>%{customdata[2]}<extra></extra>"))
    estilo(fig, tema).update_yaxes(ticksuffix=" %", zeroline=True, zerolinewidth=1)
    fig.update_xaxes(type="category", tickangle=-45)
    fig.update_layout(margin_b=78, bargap=0.3)
    cab = html.Thead(html.Tr([html.Th("Fecha"), html.Th("Real", className="num"), html.Th("Se esperaba", className="num"), html.Th("Diferencia", className="num"),
                              html.Th("Qué lo explica")]))
    filas = [html.Tr([html.Td(_fecha(f.fecha)), html.Td(f"{coma(f.real, 0 if f.real >= 20 else 1)}{unidad}", className="num"),
                      html.Td(f"{coma(f.esperado, 0 if f.esperado >= 20 else 1)}{unidad}", className="num"),
                      html.Td(f"{'+' if f.real > f.esperado else '−'}{abs(round(100 * (f.real / f.esperado - 1)))} %", className="num"),
                      html.Td(f.causa_calendario.capitalize())]) for f in t.itertuples()]
    return fig, html.Div(className="card tabla-wrap", children=html.Table(className="tabla", children=[cab, html.Tbody(filas)]))
