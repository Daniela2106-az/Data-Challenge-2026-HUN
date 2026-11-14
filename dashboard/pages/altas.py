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
from componentes import (AZUL, NARANJA, TENUE, aviso_datos, bloque, cifra, coma, dato, estilo, filtro, grafico, hecho, horas_eje, lamina, leer, mensaje,  # noqa: E402
                         metodo, pagina, portada)

dash.register_page(__name__, path="/altas", name="Llegada y altas", title="Hora de llegada y altas - HUN", order=24)

TITULO = "Las altas salen por la tarde, y quien llega en la mañana espera hasta entonces"
OLAS = set(range(15, 18)) | set(range(20, 24))            # 15-17 h y 20-23 h
# Que pasaria si se adelantan las altas (CLAUDE.md 6b, simulacion de altas): cifras ya publicadas
ESCENARIO = [
    ("5 camas", "Libres al mediodía", "Si el 30 % de las altas de la tarde saliera entre las 9 y las 12 h."),
    ("3 a 8 %", "Menos exceso de espera", "Estimación y tope máximo. Ayuda, pero no resuelve las esperas de varios días."),
    ("1,8 h", "Tarda en reasignarse una cama", "La que se libera en la mañana. Hay que asignar enseguida, no solo dar de alta antes."),
    ("72 %", "Recibe la cama al día siguiente", "De quienes llegan a las 16 h. De quienes llegan a las 8 h, la mitad."),
]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
TARDE = set(range(13, 19))                                  # llegadas de 13:00 a 18:59 (recomendacion 6)


def _panel(anio):
    """Panel diario del periodo confiable, de un año o de todos."""
    p = leer("panel_diario.csv", parse_dates=["fecha"])
    p = p[(p.fecha >= "2023-02-01") & (p.fecha < "2026-04-10")]
    return p if anio == "Todos" else p[p.fecha.dt.year == int(anio)]


def layout():
    if leer("camas_por_hora.csv") is None or leer("espera_por_hora.csv") is None or leer("panel_diario.csv") is None:
        return aviso_datos(TITULO, ["camas_por_hora.csv", "espera_por_hora.csv", "panel_diario.csv"])
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
        lamina(3, html.Span(id="alt-titular-semana"),
               "Altas promedio por día de la semana; en gris, el fin de semana. **Menos altas el domingo son menos camas libres el "
               "lunes**, que es justo el día en que llegan más pacientes.",
               grafico("alt-semana", alto=320), id_dato="alt-dato-semana"),
        bloque("Qué pasaría si se adelantan las altas", "Un escenario con supuestos escritos, no una predicción"),
        html.Div(className="hechos", children=[hecho(*e) for e in ESCENARIO]),
        mensaje("**Adelantar altas a la mañana** pone camas libres cuando más se necesitan. Y hay un límite de proceso, no solo de "
                "camas: una cama que se libera en la mañana tarda una mediana de 1,8 horas en volver a asignarse."),
        metodo(
            "Estancias únicas del periodo confiable (1-feb-2023 a 9-abr-2026): hora de inicio y de fin de la cama de cada estancia, como "
            "porcentaje del total del día. La espera es la mediana por hora de llegada; las horas con menos de 30 estancias no se muestran.",
            "Es una **asociación**: la hora de llegada también cambia el tipo de paciente y la carga del momento, que explica unos dos "
            "quintos del efecto. Parte de la ola de la noche podría ser la hora en que se registra en el sistema.",
            "Fuente: camas_por_hora.csv y espera_por_hora.csv (dashboard/preparar_datos.py) · docs/saturacion_y_espera.md 3 y 4 · "
            "docs/HALLAZGOS.md 4.4 · asociación, no causa.", ruta="/altas"))


@callback(Output("alt-cifras", "children"), Output("alt-camas", "figure"), Output("alt-dato-olas", "children"),
          Output("alt-espera", "figure"), Output("alt-dato-peor", "children"), Output("alt-titular-semana", "children"),
          Output("alt-semana", "figure"), Output("alt-dato-semana", "children"), Input("alt-anio", "value"), Input("theme-store", "data"))
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

    p = _panel(anio)
    s = p.groupby("dia_semana_num").altas.mean().reindex(range(7))
    semana = go.Figure(go.Bar(x=DIAS, y=s.values, marker_color=[AZUL] * 5 + [TENUE] * 2, text=[coma(v) for v in s.values],
                              textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:.1f} altas por día<extra></extra>"))
    estilo(semana, tema).update_yaxes(rangemode="tozero", range=[0, s.max() * 1.15])
    semana.update_layout(bargap=0.4)
    menos = abs(100 * (s[6] / s[:5].mean() - 1))
    f = p.groupby(p.festivo.astype(bool)).altas.mean()
    festivo = dato(f"−{coma(abs(100 * (f[True] / f[False] - 1)), 0)} %", "de altas en festivo frente a un día normal") if True in f.index else []
    return (cifras, camas, dato(f"{coma(olas, 0)} %", "de las camas del día se asigna en esas dos olas"),
            espera, dato(f"{coma(peor.mediana)} h", f"de espera mediana para quien llega a las {int(peor.hora)}:00, la peor hora"),
            f"El domingo se dan {coma(menos, 0)} % menos altas que entre semana", semana, festivo)
