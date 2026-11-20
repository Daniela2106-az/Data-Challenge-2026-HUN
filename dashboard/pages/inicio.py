"""
dashboard/pages/inicio.py  -  version 2 (20-nov-2026): la pagina de inicio ES el asistente de flujo HUN

Quien abre el enlace cae directamente en el asistente: un titulo, preguntas sugeridas y la caja para escribir. Sobre la caja de texto, un panel plegable
para explorar sin preguntar: una fila por categoria del menu con sus paginas como botones y el recorrido guiado. Va abierto antes de preguntar y plegado despues.
(Antes eran ~24 tarjetas con parrafos; las descripciones largas de cada pagina siguen en la base de conocimiento del asistente.)

La conversacion se comparte con el chat flotante de la esquina (Store `asis-hist`, dashboard/asistente_ui.py) y la dibuja dashboard/assets/asistente.js.
No carga datos ni se conecta a la base.
"""
import datetime as dt
import sys
from pathlib import Path

import dash
from dash import dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import asistente  # noqa: E402
from navegacion import ICONOS, agrupar  # noqa: E402

dash.register_page(__name__, path="/", name="Asistente de flujo HUN", title="Asistente de flujo HUN", order=0)

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
    # Panel plegable sobre la caja: abierto antes de preguntar y plegado a una linea despues (assets/asistente.js), pero siempre se puede volver a abrir.
    return html.Div(id="asis-explorar", className="asis-explorar", children=[
        html.Button(id="asis-explorar-b", className="asis-explorar__b", type="button", **{"aria-expanded": "true"}, children=[
            html.Span(className="asis-i-slot", **{"data-ico": "grafico"}), "Explorar el dashboard", html.Span("▲", className="asis-explorar__fl")]),
        html.Div(id="asis-explorar-c", className="asis-explorar__c", children=[
            *filas,
            dcc.Link("Empezar el recorrido guiado →", href="/resumen", className="asis-recorrido")]),
    ])


def layout():
    ok, _motivo = asistente.estado()
    ultimo = asistente.vence() - dt.timedelta(days=1)
    return html.Div(className="asis-pagina asis-scope", children=[
        html.Div(className="asis-top", children=[
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
