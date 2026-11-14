"""
dashboard/pages/alertas.py  -  pagina «Alertas» (13-nov-2026; pagina 3.2 de docs/estructura_dashboard.md; formato de presentacion)
Las tres alertas del proyecto: dia congestionado, paciente sin cama y camas de mañana. Para cada una, cuando avisar y que tan bien acierta.

DATOS  Cifras ya publicadas (CLAUDE.md 6b, docs/HALLAZGOS.md y docs/documento_final.md seccion 6), escritas aqui como constantes: prueba
       de enero al 9 de abril de 2026 reproduciendo los dias, con los cortes elegidos en julio a diciembre de 2025 (src/alertas.py).
       No lee ninguna tabla.
"""
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import AZUL, PIZARRA, TENUE, bloque, cifra, coma, estilo, grafico, hecho, lamina, mensaje, metodo, pagina, portada  # noqa: E402

dash.register_page(__name__, path="/alertas", name="Alertas", title="Alertas - HUN", order=33)

# (momento del aviso, deteccion %, precision %, detalle) - alerta de dia congestionado, 15 dias congestionados en la prueba
DIA = [("Un día antes", 20, 43, "7 alertas, 3 aciertos"), ("A las 9 h", 27, 57, "7 alertas, 4 aciertos"),
       ("A las 12 h", 87, 52, "25 alertas, 13 aciertos"), ("A las 15 h", 60, 75, "12 alertas, 9 aciertos")]
# (horas que lleva sin cama, avisos por dia, % que termina esperando mas de 72 h) - alerta de paciente sin cama
PACIENTE = [(24, 8.6, 24), (36, 5.3, 39), (48, 4.0, 52), (60, 2.6, 80)]
CAMAS = [
    ("3,2 camas", "Error de «mañana igual que hoy»", "Suponer que mañana habrá las mismas camas ocupadas que hoy se equivoca menos que "
                                                     "proyectar altas e ingresos (3,7 camas)."),
    ("76 %", "De los días de ocupación alta, avisados", "Con esa regla simple, y casi la mitad de los avisos acierta (48 %): 0,4 avisos por día."),
    ("~20", "Camas que se liberan cada día", "Las altas esperadas sirven como orden de magnitud, no para afinar la alerta."),
]


def layout():
    return pagina(
        portada("Predicción · Alertas", "Tres alertas para actuar a tiempo: a mediodía ya se sabe si el día será congestionado",
                "Cada alerta responde a una pregunta distinta del hospital y se probó reproduciendo, día por día, los primeros meses de 2026.",
                [cifra("87 %", "de los días congestionados se detecta a las 12 h (13 de 15)"),
                 cifra("4 por día", "pacientes cumplen 48 horas sin cama; la mitad terminará esperando más de 72"),
                 cifra("4,6", "alertas por día en total con el diseño recomendado")]),
        lamina(1, "Día congestionado: el aviso sirve a mediodía, no un día antes",
               "Con lo que ha llegado hasta las 12 h, el modelo detecta casi todos los días congestionados. **Un día antes solo detecta "
               "1 de cada 5**; a las 15 h acierta más, pero ya queda poco margen para reaccionar.",
               grafico("ale-dia", alto=350), dato=("12 h", "el mejor momento para avisar: detecta el 87 % y acierta 1 de cada 2 avisos")),
        lamina(2, "Paciente sin cama: avisar a las 48 horas es el mejor equilibrio",
               "Avisar antes genera muchas alertas que no terminan en una espera larga; avisar después deja poco tiempo. **A las 48 horas, "
               "la mitad de los avisos termina esperando más de 72 horas** y quedan 24 horas para actuar.",
               grafico("ale-paciente", alto=350), dato=("4 avisos", "por día a las 48 horas: una lista corta para la reunión de camas"),
               invertida=True),
        bloque("Camas de mañana", "Para saber si mañana habrá ocupación alta, lo simple le gana a lo complejo"),
        html.Div(className="hechos", children=[hecho(*c) for c in CAMAS]),
        mensaje("Con las tres alertas el hospital recibiría **unas 4,6 alertas por día**, casi todas de pacientes que llevan 48 horas sin "
                "cama: una lista corta y accionable, no una alarma constante."),
        metodo(
            "Prueba de enero al 9 de abril de 2026 reproduciendo cada día con lo que se sabía en ese momento; los cortes se eligieron con "
            "julio a diciembre de 2025. Día congestionado: llegadas por encima del percentil 90 del mismo día de la semana en las últimas "
            "12 semanas. Ocupación alta: por encima del percentil 80 de las 12 h.",
            "No se probaron en tiempo real. En la prueba solo hubo **15 días congestionados**, así que los porcentajes pueden moverse. La "
            "alerta de paciente sin cama solo cuenta a quienes después se hospitalizan: la carga real es mayor.",
            "Fuente: src/alertas.py · CLAUDE.md 6b · docs/HALLAZGOS.md · docs/documento_final.md, sección 6."))


@callback(Output("ale-dia", "figure"), Output("ale-paciente", "figure"), Input("theme-store", "data"))
def figuras(tema):
    x = [m for m, *_ in DIA]
    dia = go.Figure()
    dia.add_trace(go.Bar(x=x, y=[d for _, d, _, _ in DIA], name="Detección: días congestionados que avisa", marker_color=AZUL,
                         text=[f"{d} %" for _, d, _, _ in DIA], textposition="outside", cliponaxis=False, customdata=[n for *_, n in DIA],
                         hovertemplate="%{x}: detecta el %{y} % de los días congestionados (%{customdata})<extra></extra>"))
    dia.add_trace(go.Bar(x=x, y=[p for _, _, p, _ in DIA], name="Precisión: avisos que aciertan", marker_color=PIZARRA,
                         hovertemplate="%{x}: acierta el %{y} % de los avisos<extra></extra>"))
    estilo(dia, tema, leyenda=True).update_yaxes(ticksuffix=" %", range=[0, 105])
    dia.update_layout(barmode="group", bargap=0.34, bargroupgap=0.08)

    pac = go.Figure(go.Bar(x=[f"A las {h} h<br>{coma(n)} avisos por día" for h, n, _ in PACIENTE], y=[p for *_, p in PACIENTE],
                           marker_color=[AZUL if h == 48 else TENUE for h, *_ in PACIENTE], text=[f"{p} %" for *_, p in PACIENTE],
                           textposition="outside", cliponaxis=False,
                           hovertemplate="%{y} % de los avisos termina esperando más de 72 horas<extra></extra>"))
    estilo(pac, tema).update_yaxes(ticksuffix=" %", range=[0, 95], title_text="termina esperando más de 72 h")
    pac.update_layout(margin=dict(l=64, b=58), bargap=0.4)
    return dia, pac
