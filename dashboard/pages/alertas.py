"""
dashboard/pages/alertas.py  -  pagina «Alertas» (14-nov-2026; pagina 3.2 de docs/estructura_dashboard.md; formato de presentacion)
Las alertas del proyecto, con los dos controles del plan (tipo de alerta y momento del aviso) y, para cada una, lo que se midio y la
recomendacion que dispara.

DATOS  datos/tablas_dashboard/alertas_tabla.csv (src/exportar_tabla_alertas.py, a partir de resultados/tablas/alertas_*.csv): una fila por
       alerta y momento de aviso, con identificador fijo (A1 a A4; la cola proyectada S1 es una senal, no una alerta). La relacion con las
       recomendaciones sale de datos/tablas_dashboard/recomendaciones_tabla.csv (columna alerta_ids) mediante dashboard/catalogo.py.
       Se puede abrir una alerta desde otra pagina con /alertas?alerta=A3.
CONTROLES  Tipo de alerta (A1 dia congestionado, A2 ocupacion alta de manana, A3 paciente sin cama, A4 aviso temprano con el estimador);
           Momento del aviso (cambia segun el tipo: hora del dia, horas sin cama o umbral de probabilidad).
Prueba: enero al 9-abr-2026 reproduciendo los dias, con los cortes elegidos en jul-dic 2025 (src/alertas.py); no es tiempo real.
"""
import re
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import (AZUL, PIZARRA, TENUE, aviso_datos, bloque, cifra, coma, estilo, ficha_de, filtro, grafico, hecho,  # noqa: E402
                         interpretacion_de, mensaje, metodo, pagina, portada)
import catalogo as cat  # noqa: E402

dash.register_page(__name__, path="/alertas", name="Alertas", title="Alertas - HUN", order=33)

TIPOS = [("A1", "Día congestionado"), ("A2", "Ocupación alta de mañana"), ("A3", "Paciente sin cama"), ("A4", "Aviso temprano con el estimador")]
DESCRIPCION = {
    "A1": "Un día es congestionado cuando llegan más pacientes de lo habitual para ese día de la semana (entre el 10 % más alto de las últimas 12 semanas). "
          "El aviso se da a media jornada, con lo que ya llegó, no con un día de margen.",
    "A2": "Avisa cuando la ocupación de camas al mediodía está entre el 20 % más alto (107 a 109 camas). Funciona mejor suponer que mañana será igual que hoy "
          "que proyectar altas e ingresos.",
    "A3": "Avisa de un paciente que lleva las horas elegidas desde su llegada sin cama. Avisar antes da más alertas y menos precisión; avisar después "
          "deja menos margen para actuar.",
    "A4": "A las 12 h de espera, el estimador calcula la probabilidad de que el paciente siga sin cama a las 48 h. Sirve solo para pacientes con orden de hospitalización.",
}
CAMAS = [
    ("3,2 camas", "Error de «mañana igual que hoy»", "Suponer que mañana habrá las mismas camas ocupadas que hoy se equivoca menos que "
                                                     "proyectar altas e ingresos (3,7 camas)."),
    ("~20", "Camas que se liberan cada día", "Las altas esperadas sirven como orden de magnitud, no para afinar la alerta."),
]


def _corto(f):
    """Etiqueta corta del momento de aviso para el eje y los botones."""
    if f.alerta_id == "A4":
        m = re.search(r"≥ (\d+) %", f.momento)
        return f"≥ {m.group(1)} %" if m else f.momento
    if f.alerta_id == "A2":
        return "Mañana = hoy" if "persistencia" in f.momento else "Proyección"
    return f.momento


def _fmt(x, dec=0):
    return coma(x, dec) if dec else f"{x:.0f}"


def _filas(tabla, tipo):
    return tabla[tabla.alerta_id == tipo].sort_values("orden")


def layout(alerta=None, **_):
    tabla = cat.alertas()
    if tabla is None:
        return pagina(aviso_datos("Alertas", ["alertas_tabla.csv"]))
    tipo = alerta if alerta in dict(TIPOS) else "A1"
    rec = tabla[(tabla.recomendada == 1) & tabla.alerta_id.isin(["A1", "A2", "A3"])]
    a1 = tabla[(tabla.alerta_id == "A1") & (tabla.recomendada == 1)].iloc[0]
    a3 = tabla[(tabla.alerta_id == "A3") & (tabla.recomendada == 1)].iloc[0]
    total = rec.alertas_por_dia.sum()
    senal = _filas(tabla, "S1")
    return pagina(
        portada("Predicción · Alertas", "Las alertas avisan a tiempo y cada una apunta a la recomendación que dispara",
                "Elige una alerta y el momento en que avisa: verás qué tan bien acierta, cuántos avisos genera por día y qué recomendación le corresponde. "
                "Se probó reproduciendo, día por día, los primeros meses de 2026.",
                [cifra(f"{a1.deteccion_pct:.0f} %", "de los días congestionados se detecta a las 12 h (13 de 15)"),
                 cifra(f"{a3.alertas_por_dia:.0f} por día", "pacientes cumplen 48 horas sin cama; la mitad terminará esperando más de 72"),
                 cifra(coma(total, 1), "alertas por día en total con el diseño recomendado")]),
        html.Div(className="filtros", children=[
            filtro("ale-tipo", "Tipo de alerta", TIPOS, tipo),
            html.Div(className="filtro", children=[html.Div("Momento del aviso", className="filtro__label"),
                                                   dcc.RadioItems(id="ale-momento", options=[], className="pildoras", inline=True)])]),
        html.Div(className="ale-panel", children=[
            html.P(id="ale-descripcion", className="prose"),
            grafico("ale-grafico", alto=340),
            html.Div(id="ale-tarjetas", className="hechos"),
            html.Div(id="ale-recos"),
        ]),
        bloque("Cola proyectada", "Una señal para la reunión de camas, no una alerta con umbral"),
        html.Div(className="hechos", children=[
            hecho(re.search(r"Error de ([\d,]+) pacientes", f.medida).group(1) + " pacientes", f"Error de la cola {f.momento.lower()}",
                  f.medida.split("; es una señal")[0] + ".") for f in senal.itertuples()]),
        bloque("Camas de mañana", "Para saber si mañana habrá ocupación alta, lo simple le gana a lo complejo"),
        html.Div(className="hechos", children=[hecho(*c) for c in CAMAS]),
        mensaje(f"Con las tres alertas del diseño recomendado (día congestionado a las 12 h, ocupación alta de mañana y paciente a las 48 h sin cama) el "
                f"hospital recibiría **unas {coma(total, 1)} alertas por día**, casi todas de pacientes que llevan 48 horas sin cama: una lista corta y "
                "accionable, no una alarma constante."),
        interpretacion_de("/alertas"),
        metodo(
            "Prueba de enero al 9 de abril de 2026 reproduciendo cada día con lo que se sabía en ese momento; los cortes se eligieron con "
            "julio a diciembre de 2025. Día congestionado: llegadas por encima del percentil 90 del mismo día de la semana en las últimas "
            "12 semanas. Ocupación alta: por encima del percentil 80 de las 12 h.",
            "No se probaron en tiempo real. En la prueba solo hubo **15 días congestionados**, así que los porcentajes pueden moverse. La "
            "alerta de paciente sin cama solo cuenta a quienes después se hospitalizan: la carga real es mayor. La alerta por zona (niños y adultos "
            "por separado) no se probó.",
            "Fuente: src/alertas.py · documentación, sección 6.2.", ruta="/alertas"),
        ficha_de("/alertas"),
    )


@callback(Output("ale-momento", "options"), Output("ale-momento", "value"), Input("ale-tipo", "value"))
def momentos(tipo):
    tabla = cat.alertas()
    filas = _filas(tabla, tipo)
    ops = [{"label": _corto(f) + (" ✓" if f.recomendada else ""), "value": int(f.orden)} for f in filas.itertuples()]
    rec = filas[filas.recomendada == 1]
    return ops, int(rec.orden.iloc[0]) if len(rec) else int(filas.orden.iloc[0])


@callback(Output("ale-grafico", "figure"), Output("ale-descripcion", "children"), Output("ale-tarjetas", "children"), Output("ale-recos", "children"),
          Input("ale-tipo", "value"), Input("ale-momento", "value"), State("theme-store", "data"))
def mostrar(tipo, momento, tema):
    tabla = cat.alertas()
    filas = _filas(tabla, tipo)
    if momento not in set(filas.orden.astype(int)):          # el momento guardado es de otro tipo: tomar el recomendado
        momento = int(filas[filas.recomendada == 1].orden.iloc[0])
    x = [_corto(f) + (" ✓" if f.recomendada else "") for f in filas.itertuples()]
    sel = [int(f.orden) == momento for f in filas.itertuples()]
    opac = [1.0 if s else 0.4 for s in sel]
    fig = go.Figure()
    if tipo == "A3":
        fig.add_trace(go.Bar(x=[f"{xx}<br>{coma(a, 1)} avisos por día" for xx, a in zip(x, filas.alertas_por_dia)], y=filas.precision_pct,
                             marker_color=[AZUL if s else TENUE for s in sel], text=[f"{p:.0f} %" for p in filas.precision_pct], textposition="outside",
                             cliponaxis=False, name="Termina esperando más de 72 h",
                             hovertemplate="%{y} % de los avisos termina esperando más de 72 horas<extra></extra>"))
        estilo(fig, tema).update_yaxes(ticksuffix=" %", range=[0, 95], title_text="termina esperando más de 72 h")
        fig.update_layout(margin=dict(l=64, b=58), bargap=0.4)
    else:
        fig.add_trace(go.Bar(x=x, y=filas.deteccion_pct, name="Detección: casos que avisa", marker_color=AZUL, marker_opacity=opac,
                             text=[f"{d:.0f} %" for d in filas.deteccion_pct], textposition="outside", cliponaxis=False,
                             hovertemplate="%{x}: detecta el %{y} % de los casos<extra></extra>"))
        fig.add_trace(go.Bar(x=x, y=filas.precision_pct, name="Precisión: avisos que aciertan", marker_color=PIZARRA, marker_opacity=opac,
                             hovertemplate="%{x}: acierta el %{y} % de los avisos<extra></extra>"))
        estilo(fig, tema, leyenda=True).update_yaxes(ticksuffix=" %", range=[0, 105])
        fig.update_layout(barmode="group", bargap=0.34, bargroupgap=0.08)

    f = filas[filas.orden.astype(int) == momento].iloc[0]
    tarjetas = [hecho(coma(f.alertas_por_dia, 2) if f.alertas_por_dia < 1 else coma(f.alertas_por_dia, 1), "Avisos por día", "Cuántas veces sonaría esta alerta en un día típico.")]
    if f.alerta_id == "A3":
        tarjetas.append(hecho(f"{f.precision_pct:.0f} %", "Termina esperando más de 72 h", "De los pacientes avisados, los que de verdad esperan más de tres días."))
    else:
        tarjetas.append(hecho(f"{f.precision_pct:.0f} %", "Acierta", "De los avisos que da, los que corresponden a un caso real."))
    if f.deteccion_pct == f.deteccion_pct:
        tarjetas.append(hecho(f"{f.deteccion_pct:.0f} %", "Casos que detecta", "De todos los casos reales, los que avisa a tiempo."))
    if f.auc == f.auc:
        tarjetas.append(hecho(coma(f.auc, 2), "AUC", "Qué tan bien separa los casos de los que no lo son (0,5 es azar, 1 es perfecto)."))
    if f.margen_h == f.margen_h:
        tarjetas.append(hecho(f"{f.margen_h:.0f} h", "De margen", "Tiempo que queda para actuar antes de que se cumpla la espera larga."))

    recos = [html.Div(className="ale-reco", children=[
                html.Div("Qué hacer cuando suena", className="enlaces__rotulo"),
                html.Div(texto, className="ale-reco__titulo"),
                dcc.Link("Ver la recomendación completa", href="/recomendaciones", className="enlace-chip")])
             for _prio, texto in cat.recomendaciones_de(tipo)]
    return fig, DESCRIPCION[tipo] + f"  {f.medida}.", tarjetas, recos
