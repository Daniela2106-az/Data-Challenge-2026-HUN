"""
dashboard/pages/demanda.py  -  pagina «Demanda» (13-nov-2026; pagina 2.1 de docs/estructura_dashboard.md; formato de presentacion)
Cuando llega la gente: mapa de calor por dia de la semana y hora, y llegadas (o ingresos a cama) por dia, mes a mes.
Control: que contar (todas las llegadas o los ingresos a cama).

DATOS  llegadas_calor.csv y panel_diario.csv (dashboard/preparar_datos.py). Solo el periodo confiable (1-feb-2023 a 9-abr-2026).
"""
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tema_graficos as tg  # noqa: E402
from componentes import (AZUL, PIZARRA, TENUE, aviso_datos, cifra, coma, dato, eje_fechas, estilo, etiqueta_final, fecha_es, filtro, grafico,  # noqa: E402
                         horas_eje, lamina, leer, mensaje, metodo, pagina, por_mes, portada)

dash.register_page(__name__, path="/demanda", name="Demanda", title="Demanda - HUN", order=21)

TITULO = "Los pacientes llegan de día y entre semana, y la demanda no crece"
ETIQUETA = {"llegadas": "llegadas", "ingresos_a_cama": "ingresos a cama"}
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
NO_CRECEN = {"llegadas": "Las llegadas no crecen", "ingresos_a_cama": "Los ingresos a cama no crecen"}


def _panel():
    p = leer("panel_diario.csv", parse_dates=["fecha"])
    return None if p is None else p[(p.fecha >= "2023-02-01") & (p.fecha < "2026-04-10")]


def layout():
    if leer("llegadas_calor.csv") is None or _panel() is None:
        return aviso_datos(TITULO, ["llegadas_calor.csv", "panel_diario.csv"])
    return pagina(
        portada("Resultados · Demanda", TITULO,
                "El pico es a media mañana y el lunes es el día más cargado. De un año a otro no llega más gente: la presión sobre "
                "las camas no viene de ahí.", id_cifras="dem-cifras"),
        html.Div(className="filtros", children=[
            filtro("dem-serie", "Qué contar", [("llegadas", "Todas las llegadas"), ("ingresos_a_cama", "Ingresos a cama")], "llegadas")]),
        lamina(1, "El pico es de 9 a 11 de la mañana, y el lunes es el día más cargado",
               "Cada cuadro es una hora de un día de la semana: entre más intenso el azul, más llegadas. De noche y en fin de semana el "
               "hospital recibe mucho menos.",
               grafico("dem-calor", alto=330), dato=("9 a 11 a. m.", "la franja con más llegadas, todos los días")),
        lamina(2, html.Span(id="dem-titular"),
               "Promedio por día de cada mes completo, de febrero de 2023 a marzo de 2026. **Si la demanda no crece, la saturación "
               "hay que buscarla dentro del hospital.**",
               grafico("dem-mes", alto=330), id_dato="dem-dato", invertida=True),
        lamina(3, html.Span(id="dem-titular-semana"),
               "Promedio por día de la semana; en gris, el fin de semana. **El ritmo del hospital baja sábado y domingo**, y con él "
               "las altas y los ingresos a cama.",
               grafico("dem-semana", alto=320), id_dato="dem-dato-semana"),
        lamina(4, html.Span(id="dem-titular-festivo"),
               "Un festivo se parece a un domingo: llegan menos pacientes y se hospitalizan menos. El pronóstico ya lo tiene en "
               "cuenta, junto con la Semana Santa y el Carnaval.",
               grafico("dem-festivo", alto=300), id_dato="dem-dato-festivo", invertida=True),
        lamina(5, "El fin de semana llega la misma curva del día, con menos gente",
               "Llegadas promedio en cada hora, entre semana y en fin de semana. **La forma es la misma: sube desde las 6, tiene su "
               "pico a media mañana y cae en la noche.** Esta gráfica cuenta todas las llegadas.",
               grafico("dem-horas", alto=320), id_dato="dem-dato-horas"),
        mensaje("La presión sobre las camas **no viene de más pacientes**. Hay que mirar cuánto se quedan y cómo se liberan las "
                "camas: es lo que muestran las páginas siguientes."),
        metodo(
            "Episodios de atención del periodo confiable (1-feb-2023 a 9-abr-2026). Las llegadas incluyen cerca de 4 % de réplicas de "
            "registro, una proporción estable en el tiempo que no cambia la forma de las curvas. El mapa de calor cuenta todas las "
            "llegadas.",
            "No anticipa brotes ni cortes del sistema. Para ver lo que se espera hacia adelante está la página de Pronóstico.",
            "Fuente: llegadas_calor.csv y panel_diario.csv (dashboard/preparar_datos.py) · docs/HALLAZGOS.md 3 · CLAUDE.md 4.13.", ruta="/demanda"))


@callback(Output("dem-cifras", "children"), Output("dem-calor", "figure"), Output("dem-titular", "children"), Output("dem-dato", "children"),
          Output("dem-mes", "figure"), Output("dem-titular-semana", "children"), Output("dem-semana", "figure"),
          Output("dem-dato-semana", "children"), Output("dem-titular-festivo", "children"), Output("dem-festivo", "figure"),
          Output("dem-dato-festivo", "children"), Output("dem-horas", "figure"), Output("dem-dato-horas", "children"),
          Input("dem-serie", "value"), Input("theme-store", "data"))
def actualizar(col, tema):
    p, cal = _panel(), leer("llegadas_calor.csv", index_col=0)
    lab = ETIQUETA[col]
    dec = 0 if col == "llegadas" else 1
    sem, fds = p[p.dia_semana_num < 5][col].mean(), p[p.dia_semana_num >= 5][col].mean()
    cifras = [cifra(coma(p[col].mean(), dec), f"{lab} por día, en promedio"), cifra(coma(sem, dec), "por día entre semana"),
              cifra(coma(fds, dec), f"por día en fin de semana ({coma(100 * (fds / sem - 1), 0)} %)".replace("-", "−"))]

    escala = [[0, "#171d25"], [1, "#58c0ec"]] if tg.es_oscuro(tema) else [[0, "#f4f7fb"], [1, "#0a4f8f"]]
    calor = go.Figure(go.Heatmap(z=cal.values, x=list(range(24)), y=[d.capitalize() for d in cal.index], colorscale=escala, xgap=2, ygap=2,
                                 colorbar=dict(title=dict(text="por hora", side="right"), thickness=10, len=0.9, outlinewidth=0),
                                 hovertemplate="%{y}, %{x}:00 · %{z:.1f} llegadas por hora<extra></extra>"))
    estilo(calor, tema)
    calor.update_layout(margin=dict(l=78, r=10, t=10, b=40))
    calor.update_yaxes(autorange="reversed", showgrid=False)
    calor.update_xaxes(tickmode="array", tickvals=list(range(0, 24, 3)), ticktext=[f"{h}:00" for h in range(0, 24, 3)], showline=False)

    a = p.groupby(p.fecha.dt.year)[col].mean()
    titular = f"{NO_CRECEN[col]}: {coma(a[2023], dec)} por día en 2023 y {coma(a[2025], dec)} en 2025"
    cambio = dato(f"{coma(100 * (a[2025] / a[2023] - 1), 0)} %".replace("-", "−"), f"de {lab} por día entre 2023 y 2025")

    m = por_mes(p.set_index("fecha")[col])
    mes = go.Figure(go.Scatter(x=m.index, y=m.values, mode="lines", line=dict(color=AZUL, width=2),
                               customdata=[fecha_es(f) for f in m.index], hovertemplate="%{customdata}: %{y:.0f} por día<extra></extra>"))
    estilo(mes, tema).update_yaxes(rangemode="tozero")
    etiqueta_final(eje_fechas(mes, m.index), m.index[-1], m.values[-1], coma(m.values[-1], 0))

    s = p.groupby("dia_semana_num")[col].mean()
    alto, bajo = DIAS[s.idxmax()].lower(), DIAS[s.idxmin()].lower()
    semana = go.Figure(go.Bar(x=DIAS, y=s.values, marker_color=[AZUL] * 5 + [TENUE] * 2, text=[coma(v, dec) for v in s.values],
                              textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:.1f} por día<extra></extra>"))
    estilo(semana, tema).update_yaxes(rangemode="tozero", range=[0, s.max() * 1.15])
    semana.update_layout(bargap=0.4)
    t_semana = f"El {alto} es el día con más {lab} ({coma(s.max(), dec)}); el {bajo}, con menos ({coma(s.min(), dec)})"
    d_semana = dato(f"{coma(100 * (s.min() / s.max() - 1), 0)} %".replace("-", "−"), f"de {lab} el {bajo} frente al {alto}")

    f = p.groupby(p.festivo.astype(bool))[col].mean()
    festivo = go.Figure(go.Bar(x=["Día normal", "Festivo"], y=[f[False], f[True]], marker_color=[TENUE, AZUL],
                               text=[coma(f[False], dec), coma(f[True], dec)], textposition="outside", cliponaxis=False,
                               hovertemplate="%{x}: %{y:.1f} por día<extra></extra>"))
    estilo(festivo, tema).update_yaxes(rangemode="tozero", range=[0, f.max() * 1.15])
    festivo.update_layout(bargap=0.6)
    t_festivo = f"En festivo hay {coma(abs(100 * (f[True] / f[False] - 1)), 0)} % menos {lab}"
    d_festivo = dato(str(int(p.festivo.astype(bool).sum())), "festivos en el periodo analizado")

    entre, fin = cal.iloc[:5].mean(), cal.iloc[5:].mean()
    horas = go.Figure()
    horas.add_trace(go.Scatter(x=list(range(24)), y=entre.values, name="Entre semana", mode="lines", line=dict(color=AZUL, width=2),
                               hovertemplate="%{x}:00 · %{y:.1f} llegadas por hora entre semana<extra></extra>"))
    horas.add_trace(go.Scatter(x=list(range(24)), y=fin.values, name="Fin de semana", mode="lines", line=dict(color=PIZARRA, width=2),
                               hovertemplate="%{x}:00 · %{y:.1f} llegadas por hora en fin de semana<extra></extra>"))
    estilo(horas, tema, leyenda=True).update_yaxes(rangemode="tozero")
    horas_eje(horas)
    pico = int(entre.values.argmax())
    d_horas = dato(f"{pico}:00", f"la hora con más llegadas entre semana: {coma(entre.values.max(), 0)} por hora")
    return cifras, calor, titular, cambio, mes, t_semana, semana, d_semana, t_festivo, festivo, d_festivo, horas, d_horas
