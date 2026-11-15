"""
dashboard/pages/espera.py  -  pagina «Espera de cama» (13-nov-2026; pagina 2.3 de docs/estructura_dashboard.md; formato de presentacion)
El cuello de botella: cuanto se espera por una cama y quien espera mas. Controles (tres): año, tipo de visita y grupo de edad.
Graficas: distribucion de la espera por tramos y tendencia mensual (mediana y percentil 90).

DATOS  espera_cubo.csv y espera_por_mes.csv (dashboard/preparar_datos.py). Estancias unicas del periodo confiable; los grupos con
       menos de 30 estancias no se muestran.
"""
import sys
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tema_graficos as tg  # noqa: E402
from componentes import (AZUL, PIZARRA, TENUE, aviso_datos, bloque, cifra, coma, dato, eje_fechas, estilo, etiqueta_final, fecha_es, filtro,  # noqa: E402
                         grafico, hecho, lamina, leer, mensaje, metodo, miles, pagina, portada)

dash.register_page(__name__, path="/espera", name="Espera de cama", title="Espera de cama - HUN", order=23)

TITULO = "La mitad de los pacientes espera más de 18 horas por una cama, y los peores casos empeoran"
EDADES = ["Niños (< 15)", "Adultos (15–59)", "Mayores (60+)"]
TIPOS = ["Urgencias", "Ambulatorio", "Treatment urgency"]
ULTIMO_MES = "2026-03"                                      # ultimo mes completo del periodo confiable (abril llega solo hasta el dia 9)
# Donde se va el tiempo (CLAUDE.md 6b, 4.11 y 4.12): cifras ya publicadas
TIEMPO = [
    ("98 %", "De la espera ocurre en urgencias", "Antes de que se asigne la cama. El tiempo sin ningún registro es apenas el 1 %."),
    ("83 %", "De las horas de espera", "Vienen de pacientes que esperan más de un día; el 57 %, de quienes esperan más de dos."),
    ("26", "Pacientes esperando cama", "Es el promedio a cualquier hora. La cola nunca llega a cero, ni de madrugada."),
    ("+38 %", "De exceso de espera por paciente", "De 17 horas en 2023 a 24 en 2025, frente a cuando el hospital funciona bien."),
]
TRAMOS = ["0–6 h", "6–12 h", "12–24 h", "24–48 h", "48–72 h", "72–120 h", "> 120 h"]


REFERENCIAS = {"a10": "Espera de los días más tranquilos (10 %)", "a20": "Espera de los días más tranquilos (20 %)",
               "b10": "Espera del 10 % que menos espera", "b25": "Espera del 25 % que menos espera"}


def _exceso():
    """Exceso de espera de cama por año (datos/tablas_dashboard/exceso_por_anio.csv), o None. 2026 es de enero al 9 de abril."""
    t = leer("exceso_por_anio.csv")
    return None if t is None or t.empty else t.sort_values("anio")


def _reparto():
    """Horas de exceso en urgencias antes de la cama y en huecos sin etapa, con cada referencia (datos/tablas_dashboard/ranking_cuellos.csv)."""
    t = leer("ranking_cuellos.csv")
    return None if t is None or t.empty else t


def _laminas_exceso():
    e, r = _exceso(), _reparto()
    out = []
    if e is not None:
        a, z = e.exceso_medio_h.iloc[0], e.exceso_medio_h.iloc[-1]
        out.append(lamina(4, "Cada paciente pierde cada vez más horas por encima de lo normal",
                          f"El exceso es cuánto espera un paciente por encima de lo que se espera cuando el hospital está tranquilo. Pasó de **{coma(a, 1)} h** en "
                          f"{int(e.anio.iloc[0])} a **{coma(z, 1)} h** en {int(e.anio.iloc[-1])} (enero a abril), un {coma(100 * (z / a - 1), 0)} % más.",
                          grafico("esp-exceso", alto=320), dato=(f"+{coma(z - a, 1)} h", "de exceso medio por paciente, de 2023 a 2026"), invertida=True))
    if r is not None:
        u = r[r.segmento == "urgencias_antes_cama"].set_index("referencia").exceso_total_h
        h = r[r.segmento == "hueco_antes_cama"].set_index("referencia").exceso_total_h
        pct = 100 * u / (u + h)
        out.append(lamina(5, "Casi todas las horas perdidas son en urgencias, esperando que se asigne la cama",
                          f"Se compararon cuatro maneras de definir «lo normal». Con todas, entre el **{coma(pct.min(), 0)} %** y el **{coma(pct.max(), 0)} %** de las horas de "
                          "exceso ocurre en urgencias antes de que se asigne la cama; el tiempo sin ninguna etapa registrada es mínimo. "
                          "Incluye hasta julio de 2026: desde abril el registro está incompleto y ese tiempo sin etapa pesa algo más de lo real.",
                          grafico("esp-reparto", alto=300), dato=(f"{coma(pct.mean(), 0)} %", "de las horas perdidas, en urgencias antes de la cama")))
    return out


def layout():
    if leer("espera_cubo.csv") is None or leer("espera_por_mes.csv") is None:
        return aviso_datos(TITULO, ["espera_cubo.csv", "espera_por_mes.csv"])
    return pagina(
        portada("Resultados · Espera de cama", TITULO,
                "Es el cuello de botella del hospital: casi toda esa espera (el 98 %) ocurre en urgencias, antes de que se asigne la cama.",
                id_cifras="esp-cifras"),
        html.Div(className="filtros", children=[
            filtro("esp-anio", "Año de llegada", ["Todos", "2023", "2024", "2025", ("2026", "2026 (ene–abr)")], "Todos"),
            filtro("esp-tipo", "Tipo de visita", ["Todos", "Urgencias", "Ambulatorio", "Treatment urgency"], "Todos"),
            filtro("esp-grupo", "Grupo de edad", ["Todos", "Niños (< 15)", "Adultos (15–59)", "Mayores (60+)"], "Todos")]),
        lamina(1, html.Span(id="esp-titular"),
               "Cada barra es un tramo de espera, desde la llegada hasta que se asigna la cama. **En azul, quienes esperan más de "
               "24 horas.** Cambia con los filtros de arriba.",
               grafico("esp-hist", alto=340), id_dato="esp-dato"),
        lamina(2, "La espera típica no cambia, pero los peores casos pasan de 61 a 81 horas",
               "La mediana se mantiene entre 17 y 20 horas. El **percentil 90**, el paciente que espera más que 9 de cada 10, sube año "
               "tras año. Esta gráfica muestra a todos los pacientes: no cambia con los filtros.",
               grafico("esp-mes", alto=340), dato=("+20 h", "en la espera de los peores casos, de 2023 a 2026"), invertida=True),
        lamina(3, html.Span(id="esp-titular-quien"),
               "Espera mediana de cada grupo de edad según el tipo de visita por el que entró: entre más intenso el azul, más espera. "
               "**Cambia con el año de arriba**, no con los otros dos filtros. Los grupos con menos de 30 casos quedan en blanco.",
               grafico("esp-matriz", alto=300), id_dato="esp-dato-quien"),
        *_laminas_exceso(),
        bloque("Dónde se va el tiempo", "Cuatro cifras que explican por qué la espera es el cuello de botella"),
        html.Div(className="hechos", children=[hecho(*t) for t in TIEMPO]),
        mensaje("El problema no es la espera típica sino **las esperas de varios días**: el 83 % de las horas de espera viene de "
                "pacientes que esperan más de un día. Ahí apuntan las alertas y las recomendaciones."),
        metodo(
            "Espera desde que el paciente llega hasta que **se le asigna una cama**, para quienes se hospitalizan. Estancias únicas del "
            "periodo confiable (1-feb-2023 a 9-abr-2026): cada hospitalización se cuenta una vez, con la persona real. Los grupos con "
            "menos de 30 estancias no se muestran, y la tendencia solo usa meses completos. Aquí la mediana es 18,5 h porque solo cuenta "
            "el periodo confiable; el documento final cita 18,6 h, con todas las estancias medidas.",
            "No separa la atención clínica en urgencias de la espera pura por una cama, porque la base no registra la hora de la orden "
            "de hospitalización. Los filtros muestran **asociaciones**, no causas.",
            "Fuente: espera_cubo.csv y espera_por_mes.csv (dashboard/preparar_datos.py) · docs/HALLAZGOS.md 4.2 y 4.3 · asociación, no causa.", ruta="/espera"))


@callback(Output("esp-cifras", "children"), Output("esp-hist", "figure"), Output("esp-titular", "children"), Output("esp-dato", "children"),
          Output("esp-mes", "figure"), Output("esp-titular-quien", "children"), Output("esp-matriz", "figure"),
          Output("esp-dato-quien", "children"),
          Input("esp-anio", "value"), Input("esp-tipo", "value"), Input("esp-grupo", "value"), Input("theme-store", "data"))
def actualizar(anio, tipo, grupo, tema):
    c, m = leer("espera_cubo.csv", dtype={"anio": str}), leer("espera_por_mes.csv")
    f = c[(c.anio == anio) & (c.tipo_visita == tipo) & (c.grupo_edad == grupo)].iloc[0]
    mes = figura_mes(m, tema)
    quien = figura_quien(c, anio, tema)
    if f.n < 30 or pd.isna(f.mediana):
        aviso = cifra("—", f"Con esos filtros solo hay {int(f.n)} estancias: son menos de 30 y no se muestran")
        return [aviso], estilo(go.Figure(), tema), "No hay datos suficientes para esta combinación", [], mes, *quien
    cifras = [cifra(f"{coma(f.mediana)} h", f"de espera mediana ({miles(f.n)} estancias)"),
              cifra(f"{coma(f.p90, 0)} h", "o más espera 1 de cada 10 pacientes"),
              cifra(f"{coma(f.pct_24, 0)} %", "espera más de un día")]
    v = [f[f"tramo_{i}"] for i in range(7)]
    hist = go.Figure(go.Bar(x=TRAMOS, y=v, marker_color=[TENUE] * 3 + [AZUL] * 4, text=[f"{coma(x, 0)} %" for x in v],
                            textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:.1f} % de las estancias<extra></extra>"))
    estilo(hist, tema).update_yaxes(ticksuffix=" %", rangemode="tozero", range=[0, max(v) * 1.18])
    titular = f"El {coma(f.pct_24, 0)} % espera más de un día por una cama"
    return cifras, hist, titular, dato(f"{coma(f.pct_48, 0)} %", "espera más de dos días"), mes, *quien


def figura_quien(c, anio, tema):
    """Espera mediana por grupo de edad y tipo de visita, del año elegido: titular, figura y dato."""
    m = c[(c.anio == anio) & (c.tipo_visita != "Todos") & (c.grupo_edad != "Todos") & (c.n >= 30)]
    m = m.pivot_table(index="grupo_edad", columns="tipo_visita", values="mediana").reindex(index=EDADES, columns=TIPOS)
    oscuro = tg.es_oscuro(tema)
    escala = [[0, "#22384c"], [1, "#1f7fc0"]] if oscuro else [[0, "#eaf3fb"], [1, "#0a4f8f"]]
    fig = go.Figure(go.Heatmap(z=m.values, x=TIPOS, y=EDADES, colorscale=escala, xgap=5, ygap=5, showscale=False,
                               text=[[f"{coma(v, 0)} h" if pd.notna(v) else "" for v in fila] for fila in m.values],
                               texttemplate="%{text}", textfont=dict(size=16, **({"color": "#ffffff"} if oscuro else {})),
                               hovertemplate="%{y}, %{x}: espera mediana de %{z:.1f} h<extra></extra>"))
    estilo(fig, tema)
    fig.update_layout(margin=dict(l=110, r=10, t=10, b=36))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showline=False)
    plano = m.stack()
    if plano.empty:
        return "No hay grupos con suficientes casos en este año", fig, []
    (e1, t1), (e2, t2) = plano.idxmax(), plano.idxmin()
    titular = f"Quienes más esperan: {e1.lower()} que entran por {t1.lower()}, {coma(plano.max(), 0)} h"
    return titular, fig, dato(f"{coma(plano.min(), 0)} h", f"esperan {e2.lower()} por {t2.lower()}, el grupo que menos")


def figura_mes(m, tema):
    m = m[m.mes <= ULTIMO_MES]
    fechas = pd.to_datetime(m.mes)
    texto = [fecha_es(f) for f in fechas]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fechas, y=m.p90, name="Percentil 90 (1 de cada 10 espera más)", mode="lines", line=dict(color=AZUL, width=2),
                             customdata=texto, hovertemplate="%{customdata}: %{y:.0f} h<extra>percentil 90</extra>"))
    fig.add_trace(go.Scatter(x=fechas, y=m.mediana, name="Mediana", mode="lines", line=dict(color=PIZARRA, width=2),
                             customdata=texto, hovertemplate="%{customdata}: %{y:.0f} h<extra>mediana</extra>"))
    estilo(fig, tema, leyenda=True).update_yaxes(ticksuffix=" h", rangemode="tozero")
    eje_fechas(fig, fechas)
    for col in ("p90", "mediana"):
        etiqueta_final(fig, fechas.iloc[-1], m[col].iloc[-1], f"{coma(m[col].iloc[-1], 0)} h")
    return fig


@callback(Output("esp-exceso", "figure"), Output("esp-reparto", "figure"), Input("theme-store", "data"))
def figuras_exceso(tema):
    exc, rep = go.Figure(), go.Figure()
    e = _exceso()
    if e is not None:
        x = [str(int(a)) + (" (ene–abr)" if int(a) == int(e.anio.max()) else "") for a in e.anio]
        exc.add_trace(go.Bar(x=x, y=e.exceso_medio_h, marker_color=[TENUE] * (len(e) - 1) + [AZUL], text=[f"{coma(v, 1)} h" for v in e.exceso_medio_h],
                             textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:.1f} h de exceso medio por paciente<extra></extra>"))
        estilo(exc, tema).update_yaxes(ticksuffix=" h", range=[0, e.exceso_medio_h.max() * 1.25])
        exc.update_layout(bargap=0.45)
    r = _reparto()
    if r is not None:
        u = r[r.segmento == "urgencias_antes_cama"].set_index("referencia").exceso_total_h
        h = r[r.segmento == "hueco_antes_cama"].set_index("referencia").exceso_total_h
        pu, ph = 100 * u / (u + h), 100 * h / (u + h)
        ejes = [REFERENCIAS[k] for k in pu.index]
        rep.add_trace(go.Bar(y=ejes, x=pu.values, orientation="h", name="En urgencias antes de la cama", marker_color=AZUL,
                             text=[f"{coma(v, 0)} %" for v in pu.values], textposition="inside",
                             hovertemplate="%{y}: %{x:.1f} % de las horas perdidas<extra></extra>"))
        rep.add_trace(go.Bar(y=ejes, x=ph.values, orientation="h", name="Sin ninguna etapa registrada", marker_color=PIZARRA,
                             hovertemplate="%{y}: %{x:.1f} % de las horas perdidas<extra></extra>"))
        estilo(rep, tema, leyenda=True).update_xaxes(ticksuffix=" %", range=[0, 100])
        rep.update_layout(barmode="stack", bargap=0.4, margin_l=10)
        rep.update_yaxes(autorange="reversed", automargin=True)
    return exc, rep
