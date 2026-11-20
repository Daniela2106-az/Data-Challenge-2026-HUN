"""
dashboard/pages/inicio.py  -  version 2 (20-nov-2026): la pagina de inicio ES el asistente de flujo HUN

Quien abre el enlace cae directamente en el asistente: un titulo, preguntas sugeridas y la caja para escribir. Debajo, mientras no haya conversacion, una
guia corta para explorar sin preguntar: cuatro cifras del hospital, una fila por categoria del menu con sus paginas como botones, y el recorrido guiado.
(Antes eran ~24 tarjetas con parrafos; las descripciones largas de cada pagina siguen en la base de conocimiento del asistente.)

La conversacion se comparte con el chat flotante de la esquina (Store `asis-hist`, dashboard/asistente_ui.py) y la dibuja dashboard/assets/asistente.js.
No carga datos ni se conecta a la base. Las cifras son hechos ya documentados del proyecto (docs/HALLAZGOS.md), no un calculo en vivo.
"""
import datetime as dt
import sys
from pathlib import Path

import dash
from dash import Input, Output, State, callback, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import asistente  # noqa: E402
from asistente_ui import enviar  # noqa: E402
from navegacion import ICONOS, agrupar  # noqa: E402

dash.register_page(__name__, path="/", name="Inicio", title="Asistente de flujo HUN", order=0)

RESUMEN = [
    ("18,6 h", "espera mediana por una cama"),
    ("106", "camas de hospitalización"),
    ("~20", "ingresos a cama por día"),
    ("94 → 105", "camas ocupadas, 2023 → 2025"),
]


def _explorar():
    """Una fila por categoria del menu: su nombre y sus paginas como botones (sin descripciones: esas las responde el asistente)."""
    paginas = sorted(dash.page_registry.values(), key=lambda p: (p.get("order") is None, p.get("order", 0), p["path"]))
    filas = []
    for titulo, _desc, grupo in agrupar(paginas):
        if not titulo:
            continue
        filas.append(html.Div(className="asis-cat", children=[
            html.Span(titulo, className="asis-cat__nombre"),
            html.Div(className="asis-cat__paginas", children=[
                dcc.Link(href=p["path"], className="asis-pill", children=[html.Span(className="nav__ico " + ICONOS.get(p["path"], "ico-profiles")), p["name"]])
                for p in grupo])]))
    return html.Div(id="asis-explorar", className="asis-explorar", children=[
        html.Div(className="asis-cifras-home", children=[
            html.Div(className="asis-cifra-home", children=[html.B(n), html.Span(e)]) for n, e in RESUMEN]),
        html.Div("O explora por tema", className="asis-explorar__titulo"),
        *filas,
        dcc.Link("Empezar el recorrido guiado →", href="/resumen", className="asis-recorrido"),
        html.P("Cifras ya documentadas (regla de estancia única, feb-2023 a 9-abr-2026). Casi todo son asociaciones y escenarios, no causas.", className="asis-explorar__nota"),
    ])


def layout():
    ok, _motivo = asistente.estado()
    ultimo = asistente.vence() - dt.timedelta(days=1)
    return html.Div(className="asis-pagina asis-scope", children=[
        html.Div(className="asis-top", children=[
            html.Span(className="asis-logo asis-i-slot", **{"data-ico": "pulso"}),
            html.B("Asistente de flujo HUN"),
            html.Span(className="asis-vivo" + ("" if ok else " asis-vivo--off"), children=[html.I(), "En línea" if ok else "No disponible"])]),
        html.Div(id="asis-log", className="asis-log asis-log--pagina"),
        _explorar(),
        html.Div(className="asis-pie", children=[
            html.Div(className="asis-composer", children=[
                dcc.Textarea(id="asis-input", className="asis-input", placeholder="Escribe tu pregunta…", maxLength=asistente.MAX_CARACTERES, rows=1, disabled=not ok),
                html.Button(id="asis-enviar", className="asis-enviar", n_clicks=0, title="Enviar", disabled=not ok, **{"aria-label": "Enviar"},
                            children=html.Span(className="asis-i-slot", **{"data-ico": "enviar"}))]),
            html.P([html.Span(className="asis-i-slot asis-aviso__ico", **{"data-ico": "ojo"}), "Cifras del análisis, no datos en vivo"], className="asis-aviso"),
            html.P(f"Asistente con inteligencia artificial (Claude): puede equivocarse, verifica en la página que señala. Hasta {asistente.LIMITE_PERSONA_DIA} preguntas por persona al día · "
                   f"disponible hasta el {ultimo.day} de {asistente._MESES[ultimo.month - 1]}. Solo recibe la documentación del proyecto, nunca datos de pacientes.",
                   className="asis-nota"),
        ]),
    ])


@callback(Output("asis-hist", "data", allow_duplicate=True), Output("asis-input", "value"), Output("asis-restantes", "data", allow_duplicate=True),
          Input("asis-enviar", "n_clicks"), State("asis-input", "value"), State("asis-hist", "data"), State("asis-uid", "data"), prevent_initial_call=True)
def enviar_pagina(_n, pregunta, hist, uid):
    nuevo, quedan = enviar(pregunta, hist, uid)
    return nuevo, "", quedan
