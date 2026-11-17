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
from componentes import AZUL, MESES, PIZARRA, TENUE, cifra, estilo, filtro, grafico, lamina, leer, mensaje, metodo, pagina, portada  # noqa: E402

from componentes import frase, tarjetas, tarjeta_grafica  # noqa: E402,F401

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


def layout():
    return pagina(
        portada("Resultados · Días atípicos", "Ningún día tuvo una espera más alta de lo esperado: el problema es de todos los días",
                "En más de tres años, los días raros son casi todos de menos actividad. La espera larga no aparece en días récord, sino "
                "como algo constante.",
                [cifra("14", "días atípicos de llegadas entre 2023 y 2026"), cifra("13 de 14", "fueron días con menos llegadas de lo esperado"),
                 cifra("0", "días con espera más alta de lo esperado")]),
        frase("Ningún día tuvo una espera más alta de lo esperado: el problema de la espera es de todos los días, no de días puntuales."),
        lamina(1, "Los dos días más extremos parecen cortes del sistema, no menos pacientes",
               "Cada barra es un día atípico: cuánto se apartaron las llegadas de lo que esperaba el pronóstico. **En azul, los dos días "
               "en que también cayeron los ingresos a cama**, algo que apunta a una falla de registro. Pasa el cursor para ver cada día.",
               grafico("ati-dias", alto=360), dato=("−60 %", "de llegadas el 28 de marzo de 2026, con un solo ingreso a cama")),
        lamina(2, "La espera larga no produce días récord",
               "Días con más y con menos de lo esperado en cada serie. **Los 7 días atípicos de espera son de espera más corta**, casi "
               "todos domingos, festivos o Semana Santa.",
               grafico("ati-resumen", alto=320), dato=("0 días", "con una espera más alta de lo esperado"), invertida=True),
        lamina(3, "Los 14 días, uno por uno: lo que llegó frente a lo que se esperaba",
               "Cada par de barras es un día atípico de llegadas: **en gris lo que esperaba el pronóstico y en azul lo que llegó de verdad**. "
               "Los dos posibles cortes del sistema se marcan con un asterisco. Pasa el cursor para ver la causa de cada día.",
               grafico("ati-dias-real", alto=380), dato=("14 días", "con llegadas fuera de lo esperado, 13 de ellos con menos pacientes")),
        lamina(4, "Los días atípicos de cada serie, uno por uno",
               "Elige qué mirar. Cada par de barras es un día: **lo que se esperaba (gris) frente a lo que ocurrió (azul)**. Pasa el cursor para ver "
               "cuánto se apartó y qué lo explica.",
               grafico("ati-var-grafico", alto=380), id_dato="ati-var-dato", invertida=True,
               controles=filtro("ati-var", "Qué mirar", VARIABLES, "llegadas")),
        tarjetas("Lo que explica el calendario", "Revisar los días raros sirvió para mejorar el pronóstico",
                 *CALENDARIO, ("Sin causa", "Días que el calendario no explica", "Solo 3 de los 14 días de llegadas tienen causa de calendario; el resto sigue sin explicación conocida.")),
        mensaje("**El problema de la espera es crónico, no de días malos.** Reaccionar a los picos no lo resuelve: hay que cambiar el "
                "proceso diario de altas y de asignación de camas."),
        metodo(
            "Un día es atípico si se aparta más de 3 desviaciones de lo que esperaba el pronóstico, que ya conoce el día de la semana, los "
            "festivos y el Carnaval. Con ese umbral se esperan unos 3 días por azar en cada serie.",
            "Que dos días parezcan cortes del sistema es una **hipótesis sin comprobar**: los datos no dicen qué pasó. La caída desde "
            "abril de 2026 no es un día atípico sino un cambio del registro, y se trata aparte. Se asume que el hospital está en Barranquilla.",
            "Fuente: docs/dias_atipicos.md · src/dias_atipicos.py.", ruta="/atipicos", modelo=False),
    )


@callback(Output("ati-dias", "figure"), Output("ati-resumen", "figure"), Output("ati-dias-real", "figure"), Input("theme-store", "data"))
def figuras(tema):
    desvio = [100 * (r / e - 1) for _, r, e, _ in DIAS]
    dias = go.Figure(go.Bar(x=[_fecha(f) for f, *_ in DIAS], y=desvio, marker_color=[AZUL if f in CORTES else TENUE for f, *_ in DIAS],
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
    return dias, resumen, _real_esperado([_fecha(f) + (" *" if f in CORTES else "") for f, *_ in DIAS], [r for _, r, _, _ in DIAS], [e for _, _, e, _ in DIAS],
                                         [o.capitalize() for *_, o in DIAS], "", tema)


def _real_esperado(fechas, real, esperado, causa, unidad, tema):
    """Pares de barras por dia: lo que se esperaba (gris) y lo que ocurrio (azul)."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=fechas, y=esperado, name="Se esperaba", marker_color=TENUE, hovertemplate="<b>%{x}</b><br>Se esperaba %{y}" + unidad + "<extra></extra>"))
    fig.add_trace(go.Bar(x=fechas, y=real, name="Ocurrió", marker_color=AZUL, customdata=list(zip(causa, [100 * (r / e - 1) for r, e in zip(real, esperado)])),
                         hovertemplate="<b>%{x}</b><br>Ocurrió %{y}" + unidad + " (%{customdata[1]:+.0f} %)<br>%{customdata[0]}<extra></extra>"))
    estilo(fig, tema, leyenda=True).update_yaxes(rangemode="tozero", ticksuffix=unidad)
    fig.update_xaxes(type="category", tickangle=-45)
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05, margin_b=78)
    return fig


@callback(Output("ati-var-grafico", "figure"), Output("ati-var-dato", "children"), Input("ati-var", "value"), Input("theme-store", "data"))
def por_variable(var, tema):
    t = leer("dias_atipicos.csv")
    if t is None:
        return go.Figure(), []
    t = t[t.variable == var].sort_values("fecha")
    unidad = " h" if var.startswith("espera") else ""
    desv = 100 * (t.real / t.esperado - 1)
    mas = int(t.sentido.str.startswith("mas").sum())
    fig = _real_esperado([_fecha(f) for f in t.fecha], [round(x, 1) for x in t.real], [round(x, 1) for x in t.esperado], [str(c).capitalize() for c in t.causa_calendario], unidad, tema)
    peor = t.iloc[int(desv.abs().values.argmax())]
    return fig, [html.B(f"{len(t)} días"), html.Span(f"atípicos: {mas} con más de lo esperado y {len(t) - mas} con menos; el más lejano, el {_fecha(peor.fecha)}")]
