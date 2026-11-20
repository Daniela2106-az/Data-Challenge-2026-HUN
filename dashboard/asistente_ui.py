"""
dashboard/asistente_ui.py  -  version 1 (19-nov-2026): piezas de pantalla del asistente de preguntas (dashboard/asistente.py)

  chat_flotante()   el boton de la esquina inferior derecha y el chat pequeno que abre (va en el layout de main.py, en todas las paginas)
  enviar()          la llamada al asistente que usan el chat pequeno y la pagina /preguntas; guarda la conversacion en el Store
                    `asis-hist` (de la sesion del navegador), que comparten los dos: la misma conversacion se ve en ambos lados.

Lo que pasa en el navegador (pintar la conversacion, el boton «Preguntar sobre esto» al seleccionar texto, Enter para enviar) vive en
dashboard/assets/asistente.js. La conversacion se pinta con JavaScript y no con callbacks de Dash porque la pagina /preguntas no siempre
esta en pantalla.
"""
import json

import dash
import flask
from dash import Input, Output, State, callback, clientside_callback, dcc, html

import asistente

SUGERENCIAS = [
    ("reloj", "¿Cuánto esperan por una cama?"), ("tendencia", "¿Ha empeorado con los años?"), ("embudo", "¿Dónde se pierde más tiempo?"),
    ("gente", "¿Influye que esté lleno?"), ("sol", "¿A qué hora dan de alta?"), ("cama", "¿Qué tan llenas están las camas?"),
    ("calendario", "¿Se quedan más días?"), ("frasco", "¿Y si damos más altas en la mañana?"), ("campana", "¿Qué alertas hay?"),
    ("grafico", "¿Se puede pronosticar la demanda?"), ("persona", "¿Quién espera más?"), ("alerta", "¿Qué dice el proyecto que no se sabe?"),
]


def _persona(uid):
    ip = (flask.request.headers.get("X-Forwarded-For") or flask.request.remote_addr or "").split(",")[0].strip()
    return f"{uid or 'sin-id'}|{ip}"


def enviar(pregunta, hist, uid, cita=None):
    """Hace la pregunta y devuelve (conversacion nueva, preguntas restantes hoy)."""
    hist = list(hist or [])
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return hist, None
    persona = _persona(uid)
    datos, ok = asistente.responder(pregunta, hist, cita, persona)
    hist += [{"rol": "usuario", "texto": pregunta, "cita": cita}, {"rol": "asistente", "datos": datos, "ok": ok}]
    return hist[-40:], asistente.restantes(persona)


def chat_flotante():
    ok, motivo = asistente.estado()
    datos = {"data-ok": "1" if ok else "0", "data-motivo": motivo, "data-sug": json.dumps(SUGERENCIAS, ensure_ascii=False)}
    return html.Div(id="asis-raiz", className="asis-raiz", **datos, children=[
        dcc.Store(id="asis-hist", storage_type="session"),
        dcc.Store(id="asis-uid", storage_type="local"),
        dcc.Store(id="asis-cita", storage_type="memory"),
        dcc.Store(id="asis-directa", storage_type="memory"),
        dcc.Store(id="asis-restantes", storage_type="session"),
        html.Div(id="asis-dummy", style={"display": "none"}),
        html.Button(id="asis-fab", className="asis-fab", title="Asistente de flujo HUN", **{"aria-label": "Abrir el asistente"},
                    children=html.Span(className="asis-i-slot", **{"data-ico": "pulso"})),
        html.Div(id="asis-panel", className="asis-panel asis-scope", **{"aria-hidden": "true"}, children=[
            html.Div(className="asis-panel__cab", children=[
                html.Span(className="asis-logo asis-logo--mini asis-i-slot", **{"data-ico": "pulso"}),
                html.B("Asistente de flujo HUN"),
                html.A("Abrir en página", href="/preguntas", className="asis-panel__link"),
                html.Button("✕", id="asis-cerrar", className="asis-panel__cerrar", title="Cerrar", **{"aria-label": "Cerrar"})]),
            html.Div(id="asis-log-mini", className="asis-log asis-log--mini"),
            html.Div(className="asis-pie asis-pie--mini", children=[
                html.Div(id="asis-cita-mini", className="asis-cita"),
                html.Div(className="asis-composer", children=[
                    dcc.Textarea(id="asis-input-mini", className="asis-input", placeholder="Escribe tu pregunta…", maxLength=asistente.MAX_CARACTERES, rows=1),
                    html.Button(id="asis-enviar-mini", className="asis-enviar", n_clicks=0, title="Enviar", **{"aria-label": "Enviar"},
                                children=html.Span(className="asis-i-slot", **{"data-ico": "enviar"}))]),
                html.Span(id="asis-restan-mini", className="asis-restan"),
            ]),
        ]),
        html.Button("Preguntar sobre esto", id="asis-sel", className="asis-sel", type="button"),
    ])


@callback(Output("asis-hist", "data", allow_duplicate=True), Output("asis-restantes", "data", allow_duplicate=True),
          Input("asis-directa", "data"), State("asis-hist", "data"), State("asis-uid", "data"), prevent_initial_call=True)
def enviar_directa(d, hist, uid):
    """Una pregunta que sale de una sugerencia o de una pregunta de seguimiento (las pinta JavaScript, por eso entran por este Store)."""
    if not d or not d.get("q"):
        return dash.no_update, dash.no_update
    return enviar(d["q"], hist, uid, d.get("cita"))


@callback(Output("asis-hist", "data", allow_duplicate=True), Output("asis-input-mini", "value"), Output("asis-cita", "data", allow_duplicate=True),
          Output("asis-restantes", "data", allow_duplicate=True),
          Input("asis-enviar-mini", "n_clicks"), State("asis-input-mini", "value"), State("asis-hist", "data"), State("asis-uid", "data"),
          State("asis-cita", "data"), prevent_initial_call=True)
def enviar_mini(_n, pregunta, hist, uid, cita):
    nuevo, quedan = enviar(pregunta, hist, uid, cita)
    return nuevo, "", None, quedan


# Pintar la conversacion y la cita (JavaScript, dashboard/assets/asistente.js): en el chat pequeno y, si esta en pantalla, en /preguntas.
clientside_callback(
    """function(hist, cita, quedan) { if (window.asisPintar) { window.asisPintar(hist || [], cita, quedan); } return ''; }""",
    Output("asis-dummy", "children"), Input("asis-hist", "data"), Input("asis-cita", "data"), Input("asis-restantes", "data"))
