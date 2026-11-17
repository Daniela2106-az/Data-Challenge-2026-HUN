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
from componentes import (AZUL, PIZARRA, TENUE, aviso_datos, bloque, cifra, coma, dato, estilo, grafico, hecho, lamina, laminas_grupo, leer,  # noqa: E402
                         mensaje, metodo, pagina, portada)

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
        laminas_grupo(
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
        ),
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
            "Fuente: CLAUDE.md 6b y 4.10 · docs/HALLAZGOS.md 4.5 · docs/modelo_espera.md · espera_cubo.csv (dashboard/preparar_datos.py)."))


@callback(Output("fac-peso", "figure"), Output("fac-grupos", "figure"), Output("fac-dato", "children"), Output("fac-efectos", "figure"),
          Input("theme-store", "data"))
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
    return peso, grupos, dato(f"{coma(tipo['Urgencias'], 0)} h", "de espera mediana al entrar por urgencias"), efectos
