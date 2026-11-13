"""
dashboard/pages/altas.py  -  pagina «Llegada y altas» (13-nov-2026; pagina 2.4 de docs/estructura_dashboard.md; formato de presentacion)
A que hora salen las altas, a que hora se asignan las camas y cuanto espera quien llega a cada hora. Control: año.

DATOS  camas_por_hora.csv y espera_por_hora.csv (dashboard/preparar_datos.py). Estancias unicas del periodo confiable; las horas con
       menos de 30 estancias no se muestran.
"""
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import (AZUL, NARANJA, TENUE, aviso_datos, cifra, coma, dato, estilo, filtro, grafico, horas_eje, lamina, leer, mensaje,  # noqa: E402
                         metodo, pagina, portada)

dash.register_page(__name__, path="/altas", name="Llegada y altas", title="Hora de llegada y altas - HUN", order=24)

TITULO = "Las altas salen por la tarde, y quien llega en la mañana espera hasta entonces"
OLAS = set(range(15, 18)) | set(range(20, 24))            # 15-17 h y 20-23 h
TARDE = set(range(13, 19))                                  # llegadas de 13:00 a 18:59 (recomendacion 6)


def layout():
    if leer("camas_por_hora.csv") is None or leer("espera_por_hora.csv") is None:
        return aviso_datos(TITULO, ["camas_por_hora.csv", "espera_por_hora.csv"])
    return pagina(
        portada("Resultados · Llegada y altas", TITULO,
                "Las camas se liberan en bloque después del mediodía. Hasta ese momento casi nadie recibe cama, sin importar a qué hora "
                "llegó.", id_cifras="alt-cifras"),
        html.Div(className="filtros", children=[
            filtro("alt-anio", "Año", ["Todos", "2023", "2024", "2025", ("2026", "2026 (ene–abr)")], "Todos")]),
        lamina(1, "Las camas se asignan en dos olas: de 15 a 17 h y de 20 a 23 h",
               "Las **altas** (línea naranja) se concentran en la tarde y las camas se asignan justo después. En la mañana casi no se "
               "libera ninguna.",
               grafico("alt-camas", alto=350), id_dato="alt-dato-olas"),
        lamina(2, "Quien llega después del mediodía espera cerca de un día",
               "Llegar entre las 13 y las 19 h (en azul) es haber perdido la ola de la tarde: la cama llega al día siguiente. Es una "
               "asociación: a esa hora también cambian el tipo de paciente y la carga.",
               grafico("alt-espera", alto=350), id_dato="alt-dato-peor", invertida=True),
        mensaje("**Adelantar altas a la mañana** pone camas libres cuando más se necesitan. Y hay un límite de proceso, no solo de "
                "camas: una cama que se libera en la mañana tarda una mediana de 1,8 horas en volver a asignarse."),
        metodo(
            "Estancias únicas del periodo confiable (1-feb-2023 a 9-abr-2026): hora de inicio y de fin de la cama de cada estancia, como "
            "porcentaje del total del día. La espera es la mediana por hora de llegada; las horas con menos de 30 estancias no se muestran.",
            "Es una **asociación**: la hora de llegada también cambia el tipo de paciente y la carga del momento, que explica unos dos "
            "quintos del efecto. Parte de la ola de la noche podría ser la hora en que se registra en el sistema.",
            "Fuente: camas_por_hora.csv y espera_por_hora.csv (dashboard/preparar_datos.py) · docs/saturacion_y_espera.md 3 y 4 · "
            "docs/HALLAZGOS.md 4.4 · asociación, no causa."))


@callback(Output("alt-cifras", "children"), Output("alt-camas", "figure"), Output("alt-dato-olas", "children"),
          Output("alt-espera", "figure"), Output("alt-dato-peor", "children"), Input("alt-anio", "value"), Input("theme-store", "data"))
def actualizar(anio, tema):
    c, e = leer("camas_por_hora.csv", dtype={"anio": str}), leer("espera_por_hora.csv", dtype={"anio": str})
    c, e = c[c.anio == anio], e[e.anio == anio]
    olas = c[c.hora.isin(OLAS)].pct_ingresos_a_cama.sum()
    tarde = c[c.hora.between(14, 18)].pct_altas.sum()
    manana = c[c.hora < 12].pct_altas.sum()
    peor = e.loc[e.mediana.idxmax()]
    cifras = [cifra(f"{coma(tarde, 0)} %", "de las altas sale entre las 14 y las 19 h"),
              cifra(f"{coma(manana, 0)} %", "sale antes del mediodía"),
              cifra(f"{coma(olas, 0)} %", "de las camas se asigna en dos olas, tarde y noche")]

    camas = go.Figure()
    for nombre, color, en_ola in [("Camas: las dos olas", AZUL, True), ("Camas: resto del día", TENUE, False)]:
        d = c[c.hora.isin(OLAS) == en_ola]
        camas.add_trace(go.Bar(x=d.hora, y=d.pct_ingresos_a_cama, name=nombre, marker_color=color,
                               hovertemplate="%{x}:00 · %{y:.1f} % de las camas del día<extra></extra>"))
    camas.add_trace(go.Scatter(x=c.hora, y=c.pct_altas, name="Altas", mode="lines+markers", line=dict(color=NARANJA, width=2),
                               marker=dict(size=7, line=dict(width=0)), hovertemplate="%{x}:00 · %{y:.1f} % de las altas del día<extra></extra>"))
    estilo(camas, tema, leyenda=True).update_yaxes(ticksuffix=" %", rangemode="tozero")
    horas_eje(camas).update_layout(bargap=0.35, barmode="overlay")

    espera = go.Figure(go.Bar(x=e.hora, y=e.mediana, marker_color=[AZUL if h in TARDE else TENUE for h in e.hora], customdata=e.n,
                              hovertemplate="Llega a las %{x}:00 · espera mediana de %{y:.1f} h · n = %{customdata}<extra></extra>"))
    espera.add_annotation(x=peor.hora, y=peor.mediana, text=f"{coma(peor.mediana, 0)} h", showarrow=False, yshift=12)
    estilo(espera, tema).update_yaxes(ticksuffix=" h", rangemode="tozero")
    horas_eje(espera).update_layout(bargap=0.35)
    return (cifras, camas, dato(f"{coma(olas, 0)} %", "de las camas del día se asigna en esas dos olas"),
            espera, dato(f"{coma(peor.mediana)} h", f"de espera mediana para quien llega a las {int(peor.hora)}:00, la peor hora"))
