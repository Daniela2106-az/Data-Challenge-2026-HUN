"""
dashboard/pages/ocupacion.py  -  pagina «Ocupación de camas» (13-nov-2026; pagina 2.2 de docs/estructura_dashboard.md; formato de presentacion)
Camas ocupadas frente a las 106 que informo el hospital, e ingresos a cama por dia. Control: vista (promedio por mes o dia por dia).

DATOS  panel_diario.csv (ya agregado por dia; dashboard/preparar_datos.py). Solo el periodo confiable (1-feb-2023 a 9-abr-2026).
       La estancia media por año es la cifra documentada en CLAUDE.md 4.8 (el panel diario no la trae).
"""
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import (AZUL, NARANJA, TENUE, aviso_datos, bloque, cifra, coma, eje_fechas, estilo, etiqueta_final, fecha_es, filtro, grafico, lamina,  # noqa: E402
                         hecho, leer, mensaje, metodo, pagina, por_mes, portada)

dash.register_page(__name__, path="/ocupacion", name="Ocupación de camas", title="Ocupación de camas - HUN", order=22)

TITULO = "La ocupación roza las 106 camas porque los pacientes se quedan más, no porque lleguen más"
CAMAS = 106
# Donde esta el exceso (CLAUDE.md 4.11 y la revision final de la ocupacion): cifras ya publicadas
EXCESO = [
    ("100 %", "Camas de adultos, en 2025", "88 camas de adultos y 88 ocupadas en promedio: los adultos operan al tope, y más de la mitad "
                                           "de las horas, por encima."),
    ("83–99 %", "Camas de niños y neonatos", "Las 18 camas pediátricas y neonatales no están saturadas: el exceso es de adultos."),
    ("36 camas", "Estancias de más de 14 días", "Un tercio de la ocupación de 2025. Es lo que más creció; ver la página de Estancias largas."),
    ("6 camas", "Con poca actividad clínica", "Entre 6 % y 8 % de los días-cama, sin crecer: el aumento es de pacientes activos, no de "
                                           "camas ocupadas sin motivo."),
]


def _panel():
    p = leer("panel_diario.csv", parse_dates=["fecha"])
    return None if p is None else p[(p.fecha >= "2023-02-01") & (p.fecha < "2026-04-10") & p.ocup_hosp_media.notna()]


def layout():
    p = _panel()
    if p is None:
        return aviso_datos(TITULO, ["panel_diario.csv"])
    a = p.groupby(p.fecha.dt.year).agg(ocup=("ocup_hosp_media", "mean"), ing=("ingresos_a_cama", "mean"))
    o23, o25 = a.ocup.get(2023, float("nan")), a.ocup.get(2025, float("nan"))
    sobre = 100 * (p[p.fecha.dt.year == 2025].ocup_hosp_media > CAMAS).mean()
    return pagina(
        portada("Resultados · Ocupación de camas", TITULO,
                "El hospital trabaja pegado a su capacidad. No es que entren más pacientes: cada uno ocupa la cama más días.",
                [cifra(coma(o25, 0), f"camas ocupadas en promedio en 2025 (en 2023: {coma(o23, 0)})"),
                 cifra(f"{coma(sobre, 0)} %", "de los días de 2025 por encima de las 106 camas"),
                 cifra("5,3 días", "de estancia media en 2025 (en 2023: 4,6 días)")]),
        lamina(1, f"En dos años la ocupación subió de {coma(o23, 0)} a {coma(o25, 0)} camas",
               "La línea naranja son las **106 camas** que informó el hospital. Desde 2024 la ocupación se mueve pegada a ese techo, y "
               "muchos días lo supera.",
               grafico("ocu-camas", alto=340), dato=(f"+{coma(o25 - o23, 0)} camas", "ocupadas en promedio, de 2023 a 2025"),
               controles=filtro("ocu-vista", "Vista", [("mes", "Promedio por mes"), ("dia", "Día por día")], "mes")),
        lamina(2, f"Pero entran los mismos pacientes: unos {coma(p.ingresos_a_cama.mean(), 0)} ingresos a cama por día",
               "Lo que creció no es la demanda sino la **estancia**: cada paciente se queda en promedio 5,3 días, frente a 4,6 en 2023.",
               grafico("ocu-flujo", alto=320), dato=("+16 %", "de estancia media entre 2023 y 2025"), invertida=True),
        lamina(3, f"En 2023 casi ningún día superó las 106 camas; en 2025, el {coma(sobre, 0)} %",
               "Porcentaje de los días de cada año con más camas ocupadas, en promedio, que las 106 del hospital. **El exceso es "
               "reciente**: aparece en 2024 y se duplica en 2025.",
               grafico("ocu-sobre", alto=320), dato=(f"{coma(p.ocup_hosp_max.max(), 0)} camas", "ocupadas en el momento de mayor ocupación")),
        lamina(4, "Las camas están igual de llenas todos los días de la semana",
               "Camas ocupadas en promedio según el día de la semana. Aunque el fin de semana llegan menos pacientes y se dan menos "
               "altas, **la ocupación no baja**: el hospital no tiene un día para ponerse al día.",
               grafico("ocu-semana", alto=300), dato=("100 camas", "ocupadas en promedio cualquier día de la semana"), invertida=True),
        bloque("Dónde está el exceso", "No todas las camas están igual de llenas"),
        html.Div(className="hechos", children=[hecho(*e) for e in EXCESO]),
        mensaje("**Bajar la estancia libera camas.** Volver a la estancia de 2023 equivale a unas 15 camas; la página de Planeación de "
                "camas simula cuánto cambia el riesgo de saturación."),
        metodo(
            "Panel diario con estancias únicas: una cama cuenta como ocupada desde que se asigna hasta el alta. Periodo confiable: "
            "1-feb-2023 a 9-abr-2026; las gráficas por mes solo muestran meses completos. La estancia media viene de las estancias con "
            "alta completa.",
            "Pasar de 106 no es un error de los datos: puede ser sobreocupación con camas adicionales o una capacidad real mayor, y los "
            "datos no las distinguen. La base no separa piso, UCI ni servicio.",
            "Fuente: panel_diario.csv (src/exportar_para_equipo.py) · capacidad: sesión con el HUN del 29-oct-2026 · "
            "docs/HALLAZGOS.md 4.6 · CLAUDE.md 4.8."))


@callback(Output("ocu-camas", "figure"), Output("ocu-flujo", "figure"), Output("ocu-sobre", "figure"), Output("ocu-semana", "figure"),
          Input("ocu-vista", "value"), Input("theme-store", "data"))
def actualizar(vista, tema):
    p = _panel()
    s = p.set_index("fecha").ocup_hosp_media
    s = por_mes(s) if vista == "mes" else s
    camas = go.Figure(go.Scatter(x=s.index, y=s.values, mode="lines", line=dict(color=AZUL, width=2 if vista == "mes" else 1.2),
                                 customdata=[fecha_es(f, dia=vista == "dia") for f in s.index],
                                 hovertemplate="%{customdata}: %{y:.0f} camas<extra></extra>"))
    camas.add_hline(y=CAMAS, line=dict(color=NARANJA, width=1.5))
    estilo(camas, tema).update_yaxes(range=[60, 126])
    etiqueta_final(eje_fechas(camas, s.index), s.index[-1], CAMAS, "106 camas")

    m = por_mes(p.set_index("fecha").ingresos_a_cama)
    flujo = go.Figure(go.Scatter(x=m.index, y=m.values, mode="lines", line=dict(color=AZUL, width=2),
                                 customdata=[fecha_es(f) for f in m.index],
                                 hovertemplate="%{customdata}: %{y:.1f} ingresos a cama por día<extra></extra>"))
    estilo(flujo, tema).update_yaxes(rangemode="tozero")
    etiqueta_final(eje_fechas(flujo, m.index), m.index[-1], m.values[-1], coma(m.values[-1], 0))

    pct = 100 * (p.ocup_hosp_media > CAMAS).groupby(p.fecha.dt.year).mean()
    sobre = go.Figure(go.Bar(x=[str(a) if a != 2026 else "2026 (ene–abr)" for a in pct.index], y=pct.values,
                             marker_color=[AZUL if a == 2025 else TENUE for a in pct.index], text=[f"{coma(v, 0)} %" for v in pct.values],
                             textposition="outside", cliponaxis=False,
                             hovertemplate="%{x}: %{y:.1f} % de los días por encima de 106 camas<extra></extra>"))
    estilo(sobre, tema).update_yaxes(ticksuffix=" %", range=[0, max(pct.max() * 1.2, 10)])
    sobre.update_xaxes(type="category")
    sobre.update_layout(bargap=0.45)

    d = p.groupby("dia_semana_num").ocup_hosp_media.mean().reindex(range(7))
    semana = go.Figure(go.Bar(x=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"], y=d.values,
                              marker_color=[AZUL] * 5 + [TENUE] * 2, text=[coma(v, 0) for v in d.values], textposition="outside",
                              cliponaxis=False, hovertemplate="%{x}: %{y:.1f} camas ocupadas<extra></extra>"))
    semana.add_hline(y=CAMAS, line=dict(color=NARANJA, width=1.5))
    estilo(semana, tema).update_yaxes(range=[0, 125])
    semana.update_layout(bargap=0.4)
    return camas, flujo, sobre, semana
