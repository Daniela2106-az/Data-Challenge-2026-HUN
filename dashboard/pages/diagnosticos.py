"""
dashboard/pages/diagnosticos.py  -  pagina «Diagnósticos» (13-nov-2026; pagina 2.8 de docs/estructura_dashboard.md; formato de presentacion)
Espera de cama y estancia por grupo de diagnostico (tarea A3). Control: que medir.

DATOS  Tabla ya publicada en docs/diagnosticos_y_tiempos.md (seccion 3), escrita aqui como constante: 11 grupos, todos con mas de 250
       hospitalizados con espera medida. No lee ninguna tabla. El agrupamiento es propio y no tiene validacion clinica.
"""
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import AZUL, PIZARRA, TENUE, cifra, coma, dato, estilo, filtro, grafico, lamina, laminas_grupo, leer, mensaje, metodo, miles, pagina, portada  # noqa: E402

from componentes import frase, tarjetas  # noqa: E402

dash.register_page(__name__, path="/diagnosticos", name="Diagnósticos", title="Diagnósticos y tiempos - HUN", order=27)

# (grupo, hospitalizados con espera medida, espera mediana h, espera p90 h, estancia mediana h)
GRUPOS = [("Musculoesquelético y dolor", 423, 38.9, 108.0, 116.3), ("Renal y urinario", 1622, 34.8, 94.5, 69.4),
          ("Cáncer y tumores", 263, 31.6, 107.1, 114.4), ("Digestivo", 2391, 29.1, 77.2, 88.9), ("Trauma y lesiones", 1643, 23.8, 72.1, 51.0),
          ("Infecciosas", 1080, 18.2, 106.8, 98.2), ("Embarazo, parto y ginecología", 1952, 16.9, 38.2, 46.2),
          ("Neurológico", 689, 12.6, 61.6, 90.0), ("Salud mental", 478, 10.3, 76.4, 71.0), ("Respiratorio", 1312, 8.8, 60.5, 70.0),
          ("Cardiovascular", 2454, 8.6, 56.8, 84.0)]
# indicador -> (posicion en la tupla, que es, se divide entre 24 para pasar a dias)
INDICADORES = {"espera": (2, "espera mediana por una cama", False), "p90": (3, "espera de los peores casos (percentil 90)", False),
               "estancia": (4, "estancia mediana en cama", True)}
LENTOS = {"Musculoesquelético y dolor", "Renal y urinario", "Cáncer y tumores", "Digestivo"}


ACENTOS = {"Embarazo, parto y ginecologia": "Embarazo, parto y ginecología", "Neurologico": "Neurológico", "Endocrino y metabolico": "Endocrino y metabólico",
           "Musculoesqueletico y dolor": "Musculoesquelético y dolor", "Dolor y sintomas generales": "Dolor y síntomas generales", "Cancer y tumores": "Cáncer y tumores",
           "Sangre e inmunologia": "Sangre e inmunología", "Recien nacido": "Recién nacido", "Ojo, oido, boca y dientes": "Ojo, oído, boca y dientes"}


def _laminas_pacientes():
    """Cuantos pacientes hay detras de cada grupo (datos/tablas_dashboard/tiempos_por_dx.csv) y la cobertura del diagnostico."""
    t = leer("tiempos_por_dx.csv")
    if t is None or t.empty:
        return []
    c = leer("cobertura_dx_por_ruta.csv")
    cob = ""
    if c is not None and not c.empty:
        d = c.set_index("ruta_simple").pct_con_dx
        if {"TU", "TU > HOSP"} <= set(d.index):
            cob = (f" Solo el {coma(d['TU'], 0)} % de quienes se atienden en urgencias y se van de alta tiene un diagnóstico registrado, frente al {coma(d['TU > HOSP'], 0)} % de quienes se hospitalizan: "
                   "los grupos reflejan sobre todo a los hospitalizados.")
    mayor = t.sort_values("hospitalizados", ascending=False).iloc[0]
    return [lamina(3, "Cuántos pacientes hay detrás de cada grupo",
                   "Cada barra es el número de hospitalizados de un grupo de diagnóstico. Pasa el cursor para ver qué porcentaje de sus pacientes se hospitaliza. "
                   "**En azul, los grupos con espera medida en suficientes casos**; en gris, los de pocos casos." + cob,
                   grafico("dx-pacientes", alto=520), dato=(miles(mayor.hospitalizados), f"hospitalizados en {ACENTOS.get(mayor.categoria_dx, mayor.categoria_dx).lower()}, el grupo más grande"))]


def _lamina_efecto():
    """Efecto del grupo de diagnostico sobre la espera, con edad, tipo de visita, franja y año iguales (datos/tablas_dashboard/efecto_dx_espera.csv)."""
    t = leer("efecto_dx_espera.csv")
    if t is None or t.empty:
        return []
    top = t.sort_values("efecto_pct_vs_digestivo", ascending=False).iloc[0]
    return [lamina(4, "Con lo demás igual, el diagnóstico sigue marcando cuánto se espera",
                   "Cuánto más o menos espera cada grupo que Digestivo, con tipo de visita, franja, año y edad iguales. **La línea fina es el intervalo de confianza del 95 %**: "
                   "si cruza el cero, la diferencia puede ser azar.",
                   grafico("dx-efecto", alto=480), dato=(f"+{coma(top.efecto_pct_vs_digestivo, 0)} %", f"de espera en {top.categoria_dx.lower()} frente a Digestivo"), invertida=True)]


def layout():
    return pagina(
        portada("Resultados · Diagnósticos", "Lo urgente consigue cama rápido; lo quirúrgico y lo urológico espera cuatro veces más",
                "Un infarto o una neumonía reciben cama en horas. Los pacientes estables que esperan cirugía, urología u ortopedia son "
                "los que hacen la cola larga.",
                [cifra("39 h", "de espera mediana en musculoesquelético y dolor"), cifra("9 h", "en cardiovascular y respiratorio"),
                 cifra("65 %", "de las hospitalizaciones tiene un diagnóstico que se puede agrupar")]),
        frase("Lo urgente consigue cama rápido; lo quirúrgico y lo urológico espera cuatro veces más."),
        laminas_grupo(
            lamina(1, html.Span(id="dx-titular"),
                   "Cada barra es un grupo de diagnóstico, ordenado de mayor a menor. **En azul, los cuatro grupos que más esperan cama.** "
                   "Pasa el cursor por una barra para ver cuántos pacientes tiene.",
                   grafico("dx-barras", alto=430), id_dato="dx-dato",
                   controles=filtro("dx-indicador", "Qué medir", [("espera", "Espera de cama"), ("p90", "Peores casos"), ("estancia", "Estancia")],
                                    "espera")),
            lamina(2, "Musculoesquelético y cáncer esperan mucho y además se quedan más tiempo",
                   "Cada punto es un grupo de diagnóstico: hacia la derecha, más espera por una cama; hacia arriba, más días "
                   "hospitalizado. **Renal y urinario espera mucho pero se queda poco**: su problema es conseguir la cama, no ocuparla.",
                   grafico("dx-dispersion", alto=400), dato=("4,8 días", "de estancia mediana en musculoesquelético y en cáncer, los que más se quedan"),
                   invertida=True),
            *_laminas_pacientes(),
            *_lamina_efecto(),
        ),
        tarjetas("Lo que dicen los diagnósticos", "Cuatro lecturas de las gráficas de arriba",
                 ("39 h", "La espera más larga", "Es la de musculoesquelético y dolor, el grupo que más espera por una cama."),
                 ("9 h", "La más corta", "Cardiovascular y respiratorio reciben cama en horas: lo urgente no hace cola."),
                 ("Renal", "Espera mucho, se queda poco", "Su problema es conseguir la cama, no ocuparla."),
                 ("65 %", "De las hospitalizaciones se puede agrupar", "El resto no tiene un diagnóstico que se pueda traducir al llegar a la cama.")),
        mensaje("La cola larga está en **cirugía, urología y ortopedia**: pacientes estables que esperan turno o una cama especializada. "
                "Vale la pena revisar ese flujo aparte, porque no compite con las urgencias vitales."),
        metodo(
            "Hospitalizados con espera medida y con diagnóstico traducido (65 % de las estancias), agrupados a mano en 11 grupos a partir "
            "del primer diagnóstico registrado. Estancias únicas, con la persona real de cada estancia.",
            "**El agrupamiento no tiene validación clínica.** El diagnóstico es un dato administrativo: se registra tarde, no se conoce al "
            "llegar y puede venir del registro duplicado. Que la cola esté en cirugía y urología es una **hipótesis sin comprobar**. El "
            "accidente cerebrovascular está agrupado en Cardiovascular.",
            "Fuente: docs/diagnosticos_y_tiempos.md, sección 3 · docs/revision_mapeo_dx.md · asociación, no causa.", ruta="/diagnosticos"))


@callback(Output("dx-dispersion", "figure"), Input("theme-store", "data"))
def dispersion(tema):
    lado = {"Musculoesquelético y dolor": "top center", "Cáncer y tumores": "middle left", "Renal y urinario": "bottom center",
            "Digestivo": "bottom center", "Trauma y lesiones": "middle right", "Infecciosas": "top center",
            "Embarazo, parto y ginecología": "bottom center", "Neurológico": "top center", "Salud mental": "middle right",
            "Respiratorio": "bottom center", "Cardiovascular": "middle left"}
    fig = go.Figure(go.Scatter(
        x=[g[2] for g in GRUPOS], y=[g[4] / 24 for g in GRUPOS], mode="markers+text", text=[g[0] for g in GRUPOS],
        textposition=[lado[g[0]] for g in GRUPOS], textfont=dict(size=11),
        marker=dict(size=13, color=[AZUL if g[0] in LENTOS else PIZARRA for g in GRUPOS], line=dict(width=2, color="rgba(255,255,255,0.7)")),
        customdata=[miles(g[1]) for g in GRUPOS], cliponaxis=False,
        hovertemplate="<b>%{text}</b><br>espera mediana: %{x:.1f} h<br>estancia mediana: %{y:.1f} días<br>%{customdata} hospitalizados<extra></extra>"))
    estilo(fig, tema)
    fig.update_xaxes(title_text="espera mediana por una cama (horas)", range=[-3, 46], showgrid=True, gridwidth=1)
    fig.update_yaxes(title_text="estancia mediana (días)", range=[1.2, 5.6])
    fig.update_layout(margin=dict(l=56, r=20, t=10, b=52))
    return fig


@callback(Output("dx-barras", "figure"), Output("dx-titular", "children"), Output("dx-dato", "children"),
          Input("dx-indicador", "value"), Input("theme-store", "data"))
def actualizar(indicador, tema):
    pos, que, en_dias = INDICADORES[indicador]
    filas = sorted(GRUPOS, key=lambda g: g[pos], reverse=True)
    valores = [g[pos] / 24 if en_dias else g[pos] for g in filas]
    unidad = "días" if en_dias else "h"
    fig = go.Figure(go.Bar(y=[g[0] for g in filas], x=valores, orientation="h", marker_color=[AZUL if g[0] in LENTOS else TENUE for g in filas],
                           text=[f"{coma(v, 1 if en_dias else 0)} {unidad}" for v in valores], textposition="outside", cliponaxis=False,
                           customdata=[miles(g[1]) for g in filas],
                           hovertemplate="<b>%{y}</b><br>%{x:.1f} " + unidad + " de " + que + "<br>%{customdata} hospitalizados<extra></extra>"))
    estilo(fig, tema)
    fig.update_layout(margin=dict(l=10, r=64, t=6, b=6), bargap=0.36)
    fig.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    fig.update_xaxes(showticklabels=False, showline=False)
    primero, ultimo = filas[0], filas[-1]
    veces = coma(valores[0] / valores[-1], 1)
    titular = f"{primero[0]} tiene la mayor {que.split(' (')[0]}: {veces} veces la de {ultimo[0].lower()}"
    return fig, titular, dato(f"{coma(valores[0], 1 if en_dias else 0)} {unidad}", f"de {que} en {primero[0].lower()}")


@callback(Output("dx-efecto", "figure"), Input("theme-store", "data"))
def figura_efecto(tema):
    t, fig = leer("efecto_dx_espera.csv"), go.Figure()
    if t is None or t.empty:
        return fig
    t = t.sort_values("efecto_pct_vs_digestivo")
    fig.add_trace(go.Bar(y=t.categoria_dx, x=t.efecto_pct_vs_digestivo, orientation="h", marker_color=[AZUL if v > 0 else TENUE for v in t.efecto_pct_vs_digestivo],
                         error_x=dict(type="data", symmetric=False, array=t.ic95_alto - t.efecto_pct_vs_digestivo, arrayminus=t.efecto_pct_vs_digestivo - t.ic95_bajo, thickness=1.4, width=4, color="#8a97a6"),
                         text=[f"{coma(v, 0)} %" for v in t.efecto_pct_vs_digestivo], textposition="outside", cliponaxis=False,
                         hovertemplate="<b>%{y}</b><br>%{x:+.0f} % de espera frente a Digestivo<extra></extra>"))
    estilo(fig, tema).update_xaxes(ticksuffix=" %", zeroline=True, zerolinewidth=1)
    fig.update_yaxes(automargin=True)
    fig.update_layout(margin=dict(l=10, r=40, t=10, b=40), bargap=0.3)
    return fig


@callback(Output("dx-pacientes", "figure"), Input("theme-store", "data"))
def figura_pacientes(tema):
    fig, t = go.Figure(), leer("tiempos_por_dx.csv")
    if t is not None and not t.empty:
        t = t.sort_values("hospitalizados")
        fig.add_trace(go.Bar(y=[ACENTOS.get(g, g) + (" *" if x else "") for g, x in zip(t.categoria_dx, t.n_insuficiente)], x=t.hospitalizados, orientation="h",
                             marker_color=[TENUE if x else AZUL for x in t.n_insuficiente],
                             text=[miles(h) for h in t.hospitalizados], textposition="outside", cliponaxis=False,
                             customdata=list(zip(t.pct_hospitaliza, t.espera_mediana_h, t.estancia_mediana_h / 24)),
                             hovertemplate="<b>%{y}</b><br>%{x:,.0f} hospitalizados (%{customdata[0]:.0f} % de sus pacientes)<br>espera mediana: %{customdata[1]:.0f} h; estancia mediana: %{customdata[2]:.1f} días<extra></extra>"))
        estilo(fig, tema).update_xaxes(showticklabels=False, showline=False, range=[0, t.hospitalizados.max() * 1.15])
        fig.update_layout(bargap=0.3, margin=dict(l=10, r=20, t=6, b=6))
        fig.update_yaxes(automargin=True, showgrid=False)
    return fig
