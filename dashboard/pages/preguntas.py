"""
dashboard/pages/preguntas.py  -  version 2 (19-nov-2026): pagina del Asistente de flujo HUN

Un chat continuo: al inicio, un mosaico de preguntas sugeridas; despues, cada respuesta es una tarjeta (titular, cifras destacadas, barras, nota, fuente y
preguntas de seguimiento). Comparte la conversacion con el chat flotante de la esquina (Store `asis-hist`). La logica esta en dashboard/asistente.py y
dashboard/asistente_ui.py; la conversacion y las tarjetas las pinta dashboard/assets/asistente.js.
"""
import datetime as dt

import dash
from dash import Input, Output, State, callback, dcc, html

import asistente
from asistente_ui import enviar

dash.register_page(__name__, path="/preguntas", name="Asistente HUN", title="Asistente de flujo HUN", order=40)


def layout():
    ok, motivo = asistente.estado()
    ultimo = asistente.vence() - dt.timedelta(days=1)
    return html.Div(className="asis-pagina asis-scope", children=[
        html.Div(className="asis-top", children=[
            html.Span(className="asis-logo asis-i-slot", **{"data-ico": "pulso"}),
            html.B("Asistente de flujo HUN"),
            html.Span(className="asis-vivo" + ("" if ok else " asis-vivo--off"), children=[html.I(), "En línea" if ok else "No disponible"])]),
        html.Div(id="asis-log", className="asis-log asis-log--pagina"),
        html.Div(className="asis-pie", children=[
            html.Div(className="asis-composer", children=[
                dcc.Textarea(id="asis-input", className="asis-input", placeholder="Escribe tu pregunta…", maxLength=asistente.MAX_CARACTERES, rows=1, disabled=not ok),
                html.Button(id="asis-enviar", className="asis-enviar", n_clicks=0, title="Enviar", disabled=not ok, **{"aria-label": "Enviar"},
                            children=html.Span(className="asis-i-slot", **{"data-ico": "enviar"}))]),
            html.P([html.Span(className="asis-i-slot asis-aviso__ico", **{"data-ico": "ojo"}), "Cifras del análisis, no datos en vivo"], className="asis-aviso"),
            html.P(f"Asistente con inteligencia artificial (Claude): puede equivocarse, verifica en la página que cita. Hasta {asistente.LIMITE_PERSONA_DIA} preguntas por persona al día · "
                   f"disponible hasta el {ultimo.day} de {asistente._MESES[ultimo.month - 1]}. Solo recibe la documentación del proyecto, nunca datos de pacientes.",
                   className="asis-nota"),
        ]),
    ])


@callback(Output("asis-hist", "data", allow_duplicate=True), Output("asis-input", "value"), Output("asis-restantes", "data", allow_duplicate=True),
          Input("asis-enviar", "n_clicks"), State("asis-input", "value"), State("asis-hist", "data"), State("asis-uid", "data"), prevent_initial_call=True)
def enviar_pagina(_n, pregunta, hist, uid):
    nuevo, quedan = enviar(pregunta, hist, uid)
    return nuevo, "", quedan
