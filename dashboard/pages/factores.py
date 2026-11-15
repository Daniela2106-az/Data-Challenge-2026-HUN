"""
dashboard/pages/factores.py  -  pagina «Qué influye en la espera» (13-nov-2026; pagina 2.5 de docs/estructura_dashboard.md; formato de presentacion)
Cuanto de la espera de cama se explica con lo que se sabe del paciente (poco) y que factores pesan.

DATOS  Peso de cada factor y demas cifras: ya publicadas (CLAUDE.md 6b y 4.10, docs/HALLAZGOS.md 4.5, docs/modelo_espera.md), escritas aqui
       como constantes. La grafica por tipo de visita y edad lee espera_cubo.csv (dashboard/preparar_datos.py).
"""
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import (AZUL, PIZARRA, TENUE, aviso_datos, bloque, cifra, coma, dato, estilo, grafico, hecho, lamina, leer, mensaje, metodo,  # noqa: E402
                         pagina, portada)

dash.register_page(__name__, path="/factores", name="Factores de la espera", title="Qué influye en la espera - HUN", order=25)

TITULO = "Lo que se sabe del paciente explica solo el 16 % de su espera"
# (factor, puntos de R2 que aporta) - modelo sobre el logaritmo de la espera, R2 total = 16 %
FACTORES = [("Diagnóstico", 7.2), ("Edad y sexo", 4.1), ("Tipo de visita", 2.0), ("Hora de llegada", 0.6),
            ("Laboratorios de las primeras 6 h", 0.2), ("Año", 0.1), ("Carga del momento", 0.1), ("Día de la semana y festivos", 0.0)]
OTROS = [
    ("14 → 26 h", "La carga del momento sí se nota", "Espera mediana cuando llegan pocos pacientes en las 6 horas previas frente a cuando "
                                                     "llegan muchos. Pero explica poco de las diferencias entre pacientes."),
    ("+27 %", "Las mujeres esperan más", "A igual edad, tipo de visita, hora y año. No se explica por obstetricia ni por la saturación: "
                                         "es un hallazgo abierto."),
    ("~0", "El calendario no cambia la espera", "Día de la semana y festivos casi no pesan: reforzar personal por día no la resolvería."),
    ("4 de cada 10", "Falsas alarmas al predecir por paciente", "Un modelo que avise al llegar quién esperará más de un día marcaría al "
                                                               "44 % de los pacientes."),
]
# (comparacion, cambio en la espera con todo lo demas igual, en %) - efectos del modelo (CLAUDE.md 6b y 4.10)
EFECTOS = [("Mujer, frente a hombre", 27), ("Cada escalón más de carga al llegar", 2.5), ("Visita ambulatoria, frente a urgencias", -31),
           ("«Treatment urgency», frente a urgencias", -39)]
TIPOS = ["Urgencias", "Ambulatorio", "Treatment urgency"]
EDADES = ["Niños (< 15)", "Adultos (15–59)", "Mayores (60+)"]


def _carga():
    """Espera de cama por decil de llegadas en las 6 horas previas (datos/tablas_dashboard/carga_por_decil.csv), o None."""
    t = leer("carga_por_decil.csv")
    return None if t is None else t[(t.segmento == "espera_cama") & (t.carga == "llegadas_6h_previas")].sort_values("decil")


def _lamina_carga():
    t = _carga()
    if t is None or t.empty:
        return []
    p1, p10, q1, q10 = t.p50.iloc[0], t.p50.iloc[-1], t.pct_mas_24h.iloc[0], t.pct_mas_24h.iloc[-1]
    return [lamina(4, "Cuando llegan más pacientes en las horas previas, la espera sube",
                   f"Los pacientes se ordenan en 10 grupos según cuántos llegaron en las 6 horas previas. La espera mediana pasa de **{coma(p1, 0)} h** "
                   f"con pocas llegadas a **{coma(p10, 0)} h** con muchas, y los que esperan más de un día pasan de **{coma(q1, 0)} %** a **{coma(q10, 0)} %**. "
                   "Es una asociación: la carga del momento explica poco de las diferencias entre pacientes.",
                   grafico("fac-carga", alto=320), dato=(f"{coma(p1, 0)} → {coma(p10, 0)} h", "espera mediana con pocas llegadas frente a muchas"),
                   invertida=True)]


def _or():
    """Efectos del modelo explicativo con su intervalo de confianza del 95 % (datos/tablas_dashboard/efectos_espera_or.csv, de docs/modelo_espera.md), o None."""
    t = leer("efectos_espera_or.csv")
    return None if t is None or t.empty else t


def _lamina_or():
    t = _or()
    if t is None:
        return []
    m = t[t.variable.str.startswith("Mujer")]
    dato_ = (f"{coma(m.razon.iloc[0], 2)}", "veces más probable esperar más de un día si es mujer") if len(m) else ("", "")
    return [lamina(5, "Con lo demás igual, esperar más de un día es más probable por la mañana, entre los mayores y entre las mujeres",
                   "Cada punto dice cuántas veces más (o menos) probable es esperar más de un día frente al grupo de referencia, con lo demás igual. La línea fina es el intervalo de "
                   "confianza del 95 %. **A la derecha del 1, más espera; a la izquierda, menos.** Los niños y las visitas ambulatorias esperan mucho menos.",
                   grafico("fac-or", alto=420), dato=dato_)]


def layout():
    if leer("espera_cubo.csv") is None:
        return aviso_datos(TITULO, ["espera_cubo.csv"])
    return pagina(
        portada("Resultados · Qué influye en la espera", TITULO,
                "La hora, la edad, el tipo de visita y el diagnóstico pesan poco. El resto depende de lo que la base no registra: el "
                "servicio, el tipo de cama y la gravedad.",
                [cifra("16 %", "de las diferencias de espera se explica con lo observado"),
                 cifra("84 %", "depende de lo que la base no registra"),
                 cifra("0", "peso del día de la semana y los festivos")]),
        lamina(1, "El diagnóstico y la edad pesan algo; el calendario, nada",
               "Cada barra es cuánto de la espera explica un factor, de un total de 16 puntos. **Ninguno domina**, y el que más pesa (el "
               "diagnóstico) se registra tarde y no se conoce al llegar.",
               grafico("fac-peso", alto=350), dato=("7,2 de 16", "puntos los aporta el diagnóstico, un dato que se conoce después")),
        lamina(2, "Quien entra por urgencias y quien es mayor espera más",
               "Espera mediana por tipo de visita y por grupo de edad. Las visitas ambulatorias y las de «treatment urgency» consiguen "
               "cama antes, y los niños esperan menos de la mitad que los mayores de 60. Son **asociaciones**: cada grupo trae pacientes distintos.",
               grafico("fac-grupos", alto=350), id_dato="fac-dato", invertida=True),
        lamina(3, "Con todo lo demás igual, ser mujer y entrar por urgencias suma espera",
               "Cuánto cambia la espera por cada característica cuando las demás se mantienen iguales (edad, hora, año y tipo de "
               "visita). **En azul, lo que alarga la espera; en gris, lo que la acorta.**",
               grafico("fac-efectos", alto=300), dato=("+27 %", "esperan las mujeres frente a los hombres, sin causa conocida")),
        *_lamina_carga(),
        *_lamina_or(),
        bloque("Lo demás que se probó", "Cuatro resultados que cambian qué vale la pena hacer"),
        html.Div(className="hechos", children=[hecho(*o) for o in OTROS]),
        mensaje("**La espera depende del sistema, no del paciente.** No hay un tipo de paciente al que culpar: lo que decide la espera es "
                "cuándo se liberan y se asignan las camas. Por eso las recomendaciones atacan el proceso y no proponen ordenar la fila "
                "por riesgo."),
        metodo(
            "Modelo sobre el logaritmo de la espera de cama, con estancias únicas del periodo confiable y la persona real de cada "
            "estancia. El peso de cada factor es lo que baja la explicación (R²) al quitarlo. La gráfica por grupos usa la espera mediana "
            "de `espera_cubo.csv`.",
            "Que un factor pese no significa que cause la espera. El **diagnóstico es un dato administrativo**, se registra tarde y puede "
            "venir del registro duplicado. El grupo «treatment urgency» es una etiqueta de la base, no un servicio confirmado por el hospital.",
            "Fuente: CLAUDE.md 6b y 4.10 · docs/HALLAZGOS.md 4.5 · docs/modelo_espera.md · espera_cubo.csv (dashboard/preparar_datos.py).", ruta="/factores"))


@callback(Output("fac-peso", "figure"), Output("fac-grupos", "figure"), Output("fac-dato", "children"), Output("fac-efectos", "figure"),
          Output("fac-carga", "figure"), Output("fac-or", "figure"), Input("theme-store", "data"))
def figuras(tema):
    nombres, puntos = [f for f, _ in FACTORES], [p for _, p in FACTORES]
    peso = go.Figure(go.Bar(y=nombres, x=puntos, orientation="h", marker_color=[AZUL] * 3 + [TENUE] * 5,
                            text=[coma(p) for p in puntos], textposition="outside", cliponaxis=False,
                            hovertemplate="<b>%{y}</b><br>%{x:.1f} de los 16 puntos que se explican<extra></extra>"))
    estilo(peso, tema)
    peso.update_layout(margin=dict(l=10, r=40, t=6, b=6), bargap=0.4)
    peso.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    peso.update_xaxes(showticklabels=False, showline=False)

    c = leer("espera_cubo.csv", dtype={"anio": str})
    c = c[c.anio == "Todos"]
    tipo = c[(c.grupo_edad == "Todos") & c.tipo_visita.isin(TIPOS)].set_index("tipo_visita").mediana.reindex(TIPOS)
    edad = c[(c.tipo_visita == "Todos") & c.grupo_edad.isin(EDADES)].set_index("grupo_edad").mediana.reindex(EDADES)
    grupos = go.Figure()
    for nombre, serie, color in [("Tipo de visita", tipo, AZUL), ("Grupo de edad", edad, PIZARRA)]:
        grupos.add_trace(go.Bar(x=[n.replace(" (", "<br>(").replace("Treatment urgency", "Treatment<br>urgency") for n in serie.index],
                                y=serie.values, name=nombre, marker_color=color, text=[f"{coma(v, 0)} h" for v in serie],
                                textposition="outside", cliponaxis=False, hovertemplate="%{x}: espera mediana de %{y:.1f} h<extra></extra>"))
    estilo(grupos, tema, leyenda=True).update_yaxes(ticksuffix=" h", rangemode="tozero", range=[0, max(tipo.max(), edad.max()) * 1.2])
    grupos.update_layout(bargap=0.4, barmode="overlay", margin_b=54)
    grupos.update_xaxes(tickangle=0)

    valores = [v for _, v in EFECTOS]
    efectos = go.Figure(go.Bar(y=[n for n, _ in EFECTOS], x=valores, orientation="h", marker_color=[AZUL if v > 0 else TENUE for v in valores],
                               text=[("+" if v > 0 else "−") + coma(abs(v), 0 if abs(v) >= 10 else 1) + " %" for v in valores],
                               textposition="outside", cliponaxis=False,
                               hovertemplate="<b>%{y}</b><br>%{x:+.1f} % de espera, con lo demás igual<extra></extra>"))
    estilo(efectos, tema)
    efectos.update_layout(margin=dict(l=10, r=30, t=6, b=6), bargap=0.4)
    efectos.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    efectos.update_xaxes(showticklabels=False, showline=False, range=[-55, 45], zeroline=True, zerolinewidth=1)
    carga = go.Figure()
    t = _carga()
    if t is not None and not t.empty:
        x = [str(d) for d in t.decil]
        carga.add_trace(go.Bar(x=x, y=t.p50, name="Espera mediana", marker_color=AZUL, text=[f"{coma(v, 0)} h" for v in t.p50], textposition="outside",
                               cliponaxis=False, hovertemplate="Grupo %{x}: espera mediana de %{y:.1f} h<extra></extra>"))
        carga.add_trace(go.Bar(x=x, y=t.p90, name="Los que más esperan (1 de cada 10)", marker_color=PIZARRA,
                               hovertemplate="Grupo %{x}: el 10 % que más espera pasa de %{y:.0f} h<extra></extra>"))
        estilo(carga, tema, leyenda=True).update_yaxes(ticksuffix=" h", range=[0, t.p90.max() * 1.2])
        carga.update_layout(barmode="group", bargap=0.3, bargroupgap=0.06)
        carga.update_xaxes(title_text="Pacientes que llegaron en las 6 horas previas (de menos a más)")
    orf, o = go.Figure(), _or()
    if o is not None:
        o = o.sort_values("razon")
        orf.add_trace(go.Scatter(x=o.razon, y=o.variable, mode="markers", marker=dict(size=9, color=[AZUL if v > 1 else TENUE for v in o.razon]),
                                 error_x=dict(type="data", symmetric=False, array=o.ic_alto - o.razon, arrayminus=o.razon - o.ic_bajo, thickness=1.5, width=4, color="#8a97a6"),
                                 customdata=list(zip(o.ic_bajo, o.ic_alto)),
                                 hovertemplate="<b>%{y}</b><br>%{x:.2f} veces (intervalo %{customdata[0]:.2f} a %{customdata[1]:.2f})<extra></extra>"))
        orf.add_vline(x=1, line_dash="dash", line_color=TENUE)
        estilo(orf, tema).update_xaxes(type="log", tickvals=[0.15, 0.25, 0.5, 1, 1.5, 2], ticktext=["0,15", "0,25", "0,5", "1", "1,5", "2"], title_text="Veces más (o menos) probable esperar más de un día")
        orf.update_yaxes(automargin=True)
        orf.update_layout(margin=dict(l=10, r=20, t=10, b=44))
    return peso, grupos, dato(f"{coma(tipo['Urgencias'], 0)} h", "de espera mediana al entrar por urgencias"), efectos, carga, orf
