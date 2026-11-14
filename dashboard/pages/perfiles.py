"""
dashboard/pages/perfiles.py  -  pagina «Perfiles y picos» (14-nov-2026; formato de presentacion; antes una tabla sin controles)
Cruza el perfil del paciente (grupo de edad x sexo x tipo de visita, 42 perfiles) con el momento de carga en que llego, que ni A1 (perfil sin
mirar la carga) ni los analisis de saturacion (carga sin desagregar por perfil) hacian. Dice: la carga alarga la espera en los perfiles de
Urgencias mas comunes (30 a 70 %), pero no cambia quien llega ni cuanto se queda en cama; y los dias de alta demanda no son dias de cuello de botella.

DATOS  resultados/tablas/perfiles_en_picos_llegadas.csv, perfiles_en_picos_ocupacion.csv y dias_alta_demanda.csv (src/perfiles_en_picos.py; correrlo
       antes si no existen). Documento: docs/perfiles_en_picos.md. Periodo confiable 1-feb-2023 a 9-abr-2026.
"""
import os
import sys
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dash_table, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import AZUL, TENUE, bloque, cifra, estilo, grafico, hecho, lamina, mensaje, metodo, pagina, portada  # noqa: E402

dash.register_page(__name__, path="/perfiles", name="Perfiles y picos", title="Perfiles y picos de demanda - HUN", order=4)

RAIZ = Path(__file__).resolve().parent.parent.parent
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
NARANJA = "#eb6834"
try:
    LLEG = pd.read_csv(TABLAS / "perfiles_en_picos_llegadas.csv")
    OCUP = pd.read_csv(TABLAS / "perfiles_en_picos_ocupacion.csv")
    DIAS = pd.read_csv(TABLAS / "dias_alta_demanda.csv")
    DATOS_OK = True
except (FileNotFoundError, OSError):
    DATOS_OK = False


def grandes(df, col="espera_contraste"):
    return df[df[col].astype(str).str.startswith("GRANDE")].copy()


def etiqueta(r):
    return f"{r.grupo_edad} años, {r.sexo.lower()}, {r.tipo_visita}"


def layout():
    if not DATOS_OK:
        return pagina(html.H2("Perfiles y picos de demanda"), html.Div(className="card aviso", children=[
            "Faltan las tablas de esta página (perfiles_en_picos_*.csv y dias_alta_demanda.csv). Se generan con ",
            html.Code("python3 src/perfiles_en_picos.py"), " (necesita los datos procesados, que viven fuera del repositorio)."]))
    g1, g2 = grandes(LLEG), grandes(OCUP)
    n = len(LLEG)
    sobre = int(g1.sobrerrepresentado_en_picos.sum())
    pct = (g1.espera_mediana_pico_h / g1.espera_mediana_resto_h - 1) * 100
    est = len(grandes(LLEG, "estancia_contraste"))
    return pagina(
        portada("Resultados · Perfiles y picos", "La carga alarga la espera en los perfiles de urgencias más comunes, pero no cambia quién llega ni cuánto se queda",
                "Se cruzó el perfil de cada paciente con lo lleno que estaba el hospital cuando llegó. El efecto existe, pero se concentra en pocos perfiles.",
                [cifra(f"{len(g1)} de {n}", "perfiles esperan mucho más cuando llegan en un pico de llegadas"),
                 cifra(f"+{pct.min():.0f} a +{pct.max():.0f} %", "más espera en esos perfiles, todos de urgencias"),
                 cifra(f"{est} de {n}", "perfiles cambia su estancia con la carga")]),
        lamina(1, f"Con muchas llegadas seguidas, {len(g1)} perfiles esperan entre {pct.min():.0f} y {pct.max():.0f} % más",
               "Espera mediana en horas, comparando a quienes llegaron cuando entraron más pacientes en las 6 horas previas (el 10 % más cargado) con "
               "el resto. **Son los perfiles de urgencias más numerosos**: adultos y niños escolares.",
               grafico("perf-g1", alto=330), dato=(f"{len(g1)} de {n}", "perfiles con un aumento grande (14 %)")),
        lamina(2, f"Con el hospital casi lleno al llegar, {len(g2)} perfiles esperan más",
               "Mismo cruce, pero tomando la ocupación de camas al llegar (el 10 % más alto). Aparece el mismo patrón: adultos y niños de urgencias.",
               grafico("perf-g2", alto=300), dato=(f"{len(g2)} de {n}", "perfiles con un aumento grande"), invertida=True),
        bloque("Lo que la tabla permite concluir", "Cuatro lecturas, de la más específica a la más general"),
        html.Div(className="hechos", children=[
            hecho(f"{sobre} de {len(g1)}", "Ninguno llega más seguido en los picos" if sobre == 0 else "Pocos llegan más seguido en los picos",
                  "Los perfiles que más sufren no son los que provocan el pico: simplemente les va peor cuando coincide con uno. Por eso esta tabla "
                  "no sirve para repartir cuántos pacientes de cada tipo llegan en un pico."),
            hecho(f"{est} de {n}", "La estancia casi no cambia",
                  "Cuánto se queda alguien hospitalizado depende de su cuadro clínico, no de qué tan lleno estaba el hospital cuando llegó."),
            hecho("14 %", "Un efecto real, pero no generalizado",
                  "Solo 6 de 42 perfiles muestran un salto grande, todos de urgencias. En «Treatment urgency» y ambulatoria casi no hay datos "
                  "suficientes para decidir."),
            hecho("3,7 puntos", "Por qué se esperaba poco",
                  "Saber la saturación real al llegar mejora la explicación de la espera individual apenas 3,7 puntos, frente a 7,0 de la edad, el sexo "
                  "y el tipo de visita. Además, en adultos la cola nunca está vacía: hay poco contraste entre «pico» y «no pico»."),
        ]),
        bloque("Días de alta demanda", "Días en que llegaron más pacientes de lo normal para ese día de la semana"),
        html.Div(className="card aviso", children=[
            html.B(f"{len(DIAS)} de 1.164 días ({100 * len(DIAS) / 1164:.0f} %), más o menos 1 de cada 6: no es un evento raro. "),
            "Una advertencia que no es letra pequeña: ya se probó que ", html.B("ningún día tuvo una espera más alta de lo esperado"),
            ". El problema de la espera es crónico y de cola larga, no de días puntuales. Esta lista dice únicamente que ese día llegó más gente; "
            "no es un «día de cuello de botella»."]),
        html.Div(className="card", style={"marginTop": "12px"}, children=[dash_table.DataTable(
            id="perf-tabla-dias", data=DIAS.sort_values("fecha", ascending=False).to_dict("records"),
            columns=[{"name": nombre, "id": c} for c, nombre in [("fecha", "Fecha"), ("llegadas", "Llegadas"),
                     ("umbral_p90_mismo_dia_semana", "Umbral (percentil 90)"), ("pct_sobre_umbral", "% sobre el umbral")]],
            sort_action="native", page_size=12, style_table={"overflowX": "auto"},
            style_cell={"fontSize": "13px", "padding": "6px", "textAlign": "center", "backgroundColor": "transparent", "color": "inherit"},
            style_header={"fontWeight": 700, "backgroundColor": "transparent"})]),
        mensaje("**La carga alarga la espera en los perfiles de urgencias más comunes, entre 30 y 70 %, pero no cambia quién llega ni cuánto se queda "
                "en cama.** Los picos no se resuelven con más personal un día puntual: la espera larga es crónica, y por eso valen todos los días las "
                "acciones de fondo (asignar rápido la cama que se libera, adelantar altas, pedir antes la cama de quien llega por la tarde)."),
        metodo("Se cruzan los 42 perfiles (7 grupos de edad, sexo y 3 tipos de visita) con el momento de carga en que llegó cada paciente, de dos "
               "maneras: las llegadas de las 6 horas previas o la ocupación del hospital al llegar, tomando el 10 % más alto como «pico». Para cada "
               "perfil se compara la mediana de espera y de estancia en el pico frente al resto. La diferencia es **grande** si es al menos de 20 % y "
               "su intervalo de confianza del 95 % no incluye el cero; **pequeña** o **ruido** en otro caso; y **sin datos suficientes** si el pico o "
               "el resto tienen menos de 30 estancias. Los días de alta demanda reutilizan la alerta del día congestionado: llegadas por encima del "
               "percentil 90 del mismo día de la semana en las 12 semanas anteriores.",
               "Es una asociación, no una causa: que un perfil espere más en los picos no prueba que espere por el pico. No distingue qué parte "
               "de la espera es atención clínica y cuál es espera pura. Treatment urgency y ambulatoria casi nunca tienen veredicto por falta de "
               "datos. Periodo confiable: 1-feb-2023 a 9-abr-2026.",
               "Fuente: src/perfiles_en_picos.py · docs/perfiles_en_picos.md y docs/perfiles_pacientes.md."))


def _barras(df, tema):
    if not DATOS_OK or df.empty:
        return go.Figure()
    d = df.assign(et=df.apply(etiqueta, axis=1), ratio=df.espera_mediana_pico_h / df.espera_mediana_resto_h).sort_values("ratio")
    fig = go.Figure([
        go.Bar(y=d.et, x=d.espera_mediana_resto_h, orientation="h", name="Resto del tiempo", marker_color=TENUE,
               hovertemplate="%{y}<br>Resto: %{x:.1f} h<extra></extra>"),
        go.Bar(y=d.et, x=d.espera_mediana_pico_h, orientation="h", name="Con el hospital en pico", marker_color=NARANJA,
               text=[f"+{(r - 1) * 100:.0f} %" for r in d.ratio], textposition="outside", cliponaxis=False,
               hovertemplate="%{y}<br>En pico: %{x:.1f} h<extra></extra>")])
    estilo(fig, tema, leyenda=True)
    fig.update_layout(barmode="group", bargap=0.35, margin=dict(l=10, r=60, t=34, b=36))
    fig.update_xaxes(title="Espera mediana (horas)", showgrid=True)
    fig.update_yaxes(showgrid=False, automargin=True)
    return fig


@callback(Output("perf-g1", "figure"), Input("theme-store", "data"))
def g1(tema):
    return _barras(grandes(LLEG) if DATOS_OK else pd.DataFrame(), tema)


@callback(Output("perf-g2", "figure"), Input("theme-store", "data"))
def g2(tema):
    return _barras(grandes(OCUP) if DATOS_OK else pd.DataFrame(), tema)
