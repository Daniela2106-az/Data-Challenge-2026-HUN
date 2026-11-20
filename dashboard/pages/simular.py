"""
dashboard/pages/simular.py  -  «¿Qué quieres hacer hoy?» (20-nov-2026)
Pagina a la que lleva el boton azul «Simular» del menu: cuatro tarjetas grandes, una por modulo interactivo, con una animacion al pasar el mouse.
No carga datos.
"""
import dash
from dash import dcc, html

dash.register_page(__name__, path="/simular", name="Simular", title="Simular - HUN", order=0.5)


# Las animaciones son SVG en linea (dash no trae SVG): se inyectan como HTML dentro de un iframe-less Div con dangerously_allow_html no existe,
# asi que se arman con dcc.Markdown(dangerously_allow_html=True).
ANIM = {
    "pron": '<svg viewBox="0 0 200 120"><line class="gr" x1="20" y1="100" x2="185" y2="100"/><line class="gr" x1="20" y1="20" x2="20" y2="100"/>'
            '<polyline class="st a-linea" points="25,92 55,78 80,84 110,56 140,48 175,22"/><circle class="fl a-punta" cx="175" cy="22" r="6"/></svg>',
    "espera": '<svg viewBox="0 0 200 120"><circle class="st" cx="100" cy="60" r="44"/><line class="st" x1="100" y1="60" x2="100" y2="34" style="opacity:.45"/>'
              '<line class="st a-aguja" x1="100" y1="60" x2="100" y2="26"/><circle class="fl" cx="100" cy="60" r="5"/></svg>',
    "cama": '<svg viewBox="0 0 200 120"><rect class="gr" x="30" y="30" width="140" height="22" rx="11" style="fill:none"/>'
            '<rect class="fl a-barra" x="30" y="30" width="140" height="22" rx="11" style="transform-origin:30px 41px"/>'
            '<text x="30" y="80" font-size="13" fill="currentColor" opacity=".7">Ingreso</text><text x="170" y="80" font-size="13" fill="currentColor" opacity=".7" text-anchor="end">Alta</text></svg>',
    "sim": '<svg viewBox="0 0 200 120"><line class="gr" x1="30" y1="30" x2="170" y2="30"/><line class="gr" x1="30" y1="60" x2="170" y2="60"/><line class="gr" x1="30" y1="90" x2="170" y2="90"/>'
           '<circle class="fl a-p1" cx="50" cy="30" r="9"/><circle class="fl a-p2" cx="150" cy="60" r="9"/><circle class="fl a-p3" cx="70" cy="90" r="9"/></svg>',
}

MODULOS = [
    ("/pronostico", "Pronosticador", "Cuántos pacientes llegarán en los próximos días.", "pron"),
    ("/paciente", "Paciente en espera", "Cuándo recibirá cama un paciente que espera.", "espera"),
    ("/paciente-cama", "Paciente en cama", "Cuánto le falta de estancia a un paciente hospitalizado.", "cama"),
    ("/simulador", "Simulador integral", "Mueve las palancas y mira qué pasa con camas y esperas.", "sim"),
]


def _tarjeta(ruta, titulo, desc, anim):
    return dcc.Link(href=ruta, className="sim-card", children=[
        dcc.Markdown(ANIM[anim], dangerously_allow_html=True, className="sim-card__anim"),
        html.H3(titulo, className="sim-card__t"),
        html.P(desc, className="sim-card__d")])


def layout():
    return html.Div(className="sim-pag", children=[
        html.H1("¿Qué quieres hacer hoy?", className="sim-pag__titulo"),
        html.P("Elige un módulo interactivo.", className="sim-pag__sub"),
        html.Div(className="sim-grid", children=[_tarjeta(*m) for m in MODULOS])])
