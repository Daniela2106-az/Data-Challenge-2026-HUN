"""
dashboard/pages/comparar.py  -  pagina «Comparar años» (14-nov-2026; version por año de la pagina 3.5 de docs/estructura_dashboard.md)
Diagnostico del cuello de botella periodo por periodo: se eligen dos años y se ve que cambio en la espera de cama (cuanto, en que
tramos, en que grupos de pacientes y por donde entran). Es la version publicable del diagnostico repetible del proyecto
(src/diagnostico_cuello_botella.py), que con las tablas por paciente permite elegir cualquier rango de fechas.

DATOS  espera_cubo.csv (dashboard/preparar_datos.py): agregada por año x tipo de visita x grupo de edad; los grupos con menos de 30
       estancias no se muestran. 2026 llega solo hasta el 9 de abril.
"""
import sys
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import (AZUL, PIZARRA, TENUE, aviso_datos, cifra, coma, dato, estilo, filtro, grafico, lamina, laminas_grupo,  # noqa: E402
                         leer, mensaje, metodo, pagina, portada)

from componentes import frase, tarjetas  # noqa: E402

dash.register_page(__name__, path="/comparar", name="Comparar años", title="Comparar años - HUN", order=23.5)

TITULO = "El cuello de botella es el mismo cada año, pero castiga cada vez más a los que más esperan"
ANIOS = ["2023", "2024", "2025", ("2026", "2026 (ene–abr)")]
TRAMOS = ["0–6 h", "6–12 h", "12–24 h", "24–48 h", "48–72 h", "72–120 h", "> 120 h"]


GRUPO_GRANDE = 200                                         # el titular nombra un grupo con al menos estas hospitalizaciones por año


def _signo(x, decimales=1, unidad=" h"):
    """Cambio con su signo («+18 h», «−1,9 h»); si redondea a cero no lleva signo."""
    if round(abs(x), decimales) == 0:
        return f"0{unidad}"
    return f"{'+' if x >= 0 else '−'}{coma(abs(x), decimales)}{unidad}"


def layout():
    if leer("espera_cubo.csv") is None:
        return aviso_datos(TITULO, ["espera_cubo.csv"])
    return pagina(
        portada("Resultados · Comparar años", TITULO,
                "Elige dos años y mira qué cambió: cuánto se espera, en qué tramos, en qué grupos de pacientes y por dónde entran.",
                id_cifras="com-cifras"),
        html.Div(className="filtros", children=[filtro("com-anio", "Año", ANIOS, "2025"), filtro("com-ref", "Comparar con", ANIOS, "2023")]),
        frase("El cuello de botella es el mismo cada año, pero castiga cada vez más a los pacientes que más esperan."),
        laminas_grupo(
            lamina(1, html.Span(id="com-titular-1"),
                   "Porcentaje de las hospitalizaciones en cada tramo de espera, en los dos años. **Si las barras azules crecen a la derecha, "
                   "hay más esperas largas.**",
                   grafico("com-tramos", alto=340), id_dato="com-dato-1"),
            lamina(2, html.Span(id="com-titular-2"),
                   "Cambio en la espera de los peores casos (percentil 90) de cada grupo de pacientes. **En azul, los grupos que empeoraron.** "
                   "Solo aparecen los grupos con al menos 30 hospitalizaciones en los dos años.",
                   grafico("com-grupos", alto=360), id_dato="com-dato-2", invertida=True),
            lamina(3, html.Span(id="com-titular-3"),
                   "Reparto de las hospitalizaciones según el tipo de visita por el que entró el paciente. Un cambio aquí significa que "
                   "cambió **quién llega**, no solo cuánto espera.",
                   grafico("com-mezcla", alto=320), id_dato="com-dato-3"),
            lamina(4, "Año por año: la espera típica no se mueve, los peores casos sí",
                   "Espera mediana y espera de los peores casos (percentil 90) en cada año, sin importar los dos que elijas arriba. "
                   "**La barra gris casi no cambia; la azul sube cada año.**",
                   grafico("com-anios", alto=320), id_dato="com-dato-4", invertida=True),
        ),
        tarjetas("Qué cambia y qué no entre años", "Cuatro ideas para leer la comparación",
                 ("Urgencias", "El cuello de botella no cambia de sitio", "Es la espera en urgencias antes de que se asigne la cama, año tras año."),
                 ("17 a 20 h", "La espera típica casi no se mueve", "La mediana se mantiene en ese rango de 2023 a 2026."),
                 ("61 → 81 h", "Los peores casos sí empeoran", "El 10 % que más espera pasó de 61 a 81 horas."),
                 ("Mayores", "Quién paga el costo", "Cada año, más pacientes mayores que entran por urgencias esperan varios días.")),
        mensaje("El cuello de botella no cambia de sitio: es la espera en urgencias antes de la cama. Lo que cambia es **quién paga el "
                "costo**: cada año, más pacientes esperan varios días, sobre todo los mayores que entran por urgencias."),
        metodo(
            "Estancias únicas del periodo confiable, por año de llegada. Espera desde la llegada hasta la asignación de la cama. El "
            "percentil 90 es la espera que supera 1 de cada 10 pacientes. Es la versión por año del diagnóstico repetible del proyecto "
            "(`src/diagnostico_cuello_botella.py`), que con los datos por paciente permite elegir cualquier rango de fechas.",
            "2026 solo llega hasta el 9 de abril, así que no es un año completo. Las diferencias son **asociaciones**: un grupo puede "
            "empeorar porque cambiaron sus pacientes y no el proceso. «Treatment urgency» es una etiqueta de la base, no un servicio "
            "confirmado por el hospital.",
            "Fuente: espera_cubo.csv (dashboard/preparar_datos.py) · docs/diagnostico_cuello_botella.md · docs/HALLAZGOS.md 4.2.", ruta="/comparar"))


@callback(Output("com-cifras", "children"), Output("com-titular-1", "children"), Output("com-tramos", "figure"), Output("com-dato-1", "children"),
          Output("com-titular-2", "children"), Output("com-grupos", "figure"), Output("com-dato-2", "children"),
          Output("com-titular-3", "children"), Output("com-mezcla", "figure"), Output("com-dato-3", "children"),
          Output("com-anios", "figure"), Output("com-dato-4", "children"),
          Input("com-anio", "value"), Input("com-ref", "value"), Input("theme-store", "data"))
def actualizar(anio, ref, tema):
    c = leer("espera_cubo.csv", dtype={"anio": str})
    total = c[(c.tipo_visita == "Todos") & (c.grupo_edad == "Todos")].set_index("anio")
    a, r = total.loc[anio], total.loc[ref]
    iguales = anio == ref
    cifras = [cifra(f"{coma(a.mediana)} h", f"de espera mediana en {anio} ({_signo(a.mediana - r.mediana)} frente a {ref})"),
              cifra(f"{coma(a.p90, 0)} h", f"esperan los peores casos ({_signo(a.p90 - r.p90, 0)})"),
              cifra(f"{coma(a.pct_48, 0)} %", f"espera más de dos días ({_signo(a.pct_48 - r.pct_48, 0, ' puntos')})")]

    # 1. Tramos de espera
    tramos = go.Figure()
    for nombre, fila, color in [(ref, r, PIZARRA), (anio, a, AZUL)]:
        v = [fila[f"tramo_{i}"] for i in range(7)]
        tramos.add_trace(go.Bar(x=TRAMOS, y=v, name=nombre, marker_color=color, hovertemplate=nombre + ", %{x}: %{y:.1f} %<extra></extra>"))
    estilo(tramos, tema, leyenda=True).update_yaxes(ticksuffix=" %", rangemode="tozero")
    tramos.update_layout(barmode="group", bargap=0.3, bargroupgap=0.06)
    if iguales:
        t1 = "Elige dos años distintos para ver qué cambió"
    else:
        baja, peor = a.mediana < r.mediana, a.p90 > r.p90
        t1 = (f"De {ref} a {anio} la espera típica {'bajó' if baja else 'subió'} {coma(abs(a.mediana - r.mediana))} h, "
              f"{'pero' if baja == peor else 'y'} los peores casos esperan {coma(abs(a.p90 - r.p90), 0)} h {'más' if peor else 'menos'}")
    d1 = dato(f"{coma(a.pct_48, 0)} %", f"espera más de dos días en {anio}; en {ref} era el {coma(r.pct_48, 0)} %")

    # 2. Grupos de pacientes
    g = c[(c.tipo_visita != "Todos") & (c.grupo_edad != "Todos") & c.anio.isin([anio, ref])]
    g = g[(g.n >= 30) & g.p90.notna()]
    casos = g.pivot_table(index=["grupo_edad", "tipo_visita"], columns="anio", values="n").dropna().min(axis=1)
    g = g.pivot_table(index=["grupo_edad", "tipo_visita"], columns="anio", values="p90").dropna()
    cambio = (g[anio] - g[ref]).sort_values(ascending=False)
    grandes = cambio[casos.reindex(cambio.index) >= GRUPO_GRANDE]
    lider = grandes if len(grandes) and grandes.iloc[0] >= 0.5 else cambio
    nombres = [f"{e} · {t}" for e, t in cambio.index]
    grupos = go.Figure(go.Bar(y=nombres, x=cambio.values, orientation="h", marker_color=[AZUL if v > 0 else TENUE for v in cambio.values],
                              text=[_signo(v, 0) for v in cambio.values], textposition="outside", cliponaxis=False,
                              hovertemplate="<b>%{y}</b><br>%{x:+.0f} h en los peores casos<extra></extra>"))
    estilo(grupos, tema)
    lim = max(abs(cambio.values).max() if len(cambio) else 0, 1) * 1.35
    grupos.update_layout(margin=dict(l=10, r=30, t=6, b=6), bargap=0.36)
    grupos.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    grupos.update_xaxes(showticklabels=False, showline=False, range=[-lim, lim], zeroline=True, zerolinewidth=1)
    if iguales or cambio.empty or lider.iloc[0] < 0.5:
        t2, d2 = ("Sin diferencias que mostrar" if iguales or cambio.empty else "Ningún grupo empeoró en sus peores casos"), []
    else:
        edad, tipo_lider = lider.index[0]
        inicio = "Entre los grupos grandes, el que más empeoró" if lider is grandes else "El grupo que más empeoró"
        t2 = f"{inicio}: {edad.lower()} que entran por {tipo_lider.lower()}"
        d2 = dato(_signo(lider.iloc[0], 0), f"en los peores casos de ese grupo, de {ref} a {anio}")

    # 3. Por donde entran
    m = c[(c.tipo_visita != "Todos") & (c.grupo_edad == "Todos") & c.anio.isin([anio, ref])]
    m = m.pivot_table(index="tipo_visita", columns="anio", values="n")
    m = 100 * m / m.sum()
    mezcla = go.Figure()
    for nombre, color in [(ref, PIZARRA), (anio, AZUL)]:
        mezcla.add_trace(go.Bar(x=list(m.index), y=m[nombre], name=nombre, marker_color=color, text=[f"{coma(v, 0)} %" for v in m[nombre]],
                                textposition="outside", cliponaxis=False, hovertemplate=nombre + ", %{x}: %{y:.1f} %<extra></extra>"))
    estilo(mezcla, tema, leyenda=True).update_yaxes(ticksuffix=" %", range=[0, 105])
    mezcla.update_layout(barmode="group", bargap=0.34, bargroupgap=0.06)
    dif = (m[anio] - m[ref]).abs()
    tipo = dif.idxmax()
    if iguales or pd.isna(dif.max()) or dif.max() < 1:
        t3, d3 = "Entran por las mismas puertas", []
    else:
        t3 = f"Las hospitalizaciones por «{tipo.lower()}» pasaron de {coma(m[ref][tipo], 0)} % a {coma(m[anio][tipo], 0)} %"
        d3 = dato(_signo(m[anio][tipo] - m[ref][tipo], 0, " puntos"), f"en la proporción que entra por «{tipo.lower()}»")

    # 4. Año por año
    por_anio = total.loc[[x for x in ("2023", "2024", "2025", "2026") if x in total.index]]
    etiquetas = [x if x != "2026" else "2026 (ene–abr)" for x in por_anio.index]
    anios = go.Figure()
    anios.add_trace(go.Bar(x=etiquetas, y=por_anio.mediana, name="Espera típica (mediana)", marker_color=PIZARRA,
                           text=[f"{coma(v, 0)} h" for v in por_anio.mediana], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{y:.1f} h de espera mediana<extra></extra>"))
    anios.add_trace(go.Bar(x=etiquetas, y=por_anio.p90, name="Peores casos (percentil 90)", marker_color=AZUL,
                           text=[f"{coma(v, 0)} h" for v in por_anio.p90], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{y:.1f} h en los peores casos<extra></extra>"))
    estilo(anios, tema, leyenda=True).update_yaxes(ticksuffix=" h", range=[0, por_anio.p90.max() * 1.2])
    anios.update_xaxes(type="category")
    anios.update_layout(barmode="group", bargap=0.34, bargroupgap=0.06)
    d4 = dato(f"{coma(por_anio.p90.iloc[0], 0)} → {coma(por_anio.p90.iloc[-1], 0)} h",
              f"en los peores casos, de {por_anio.index[0]} a {por_anio.index[-1]}")
    return cifras, t1, tramos, d1, t2, grupos, d2, t3, mezcla, d3, anios, d4
