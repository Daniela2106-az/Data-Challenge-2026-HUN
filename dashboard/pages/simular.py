"""
dashboard/pages/simular.py  -  «¿Qué quieres hacer hoy?» (20-nov-2026)
Pagina a la que lleva el boton azul «Simular» del menu: una tarjeta grande por modulo interactivo, con el mismo estilo que el resto del dashboard
(menu-card, Google Sans, paleta del HUN) y una animacion al pasar el mouse. No carga datos.
"""
import dash
from dash import dcc, html

from navegacion import ICONOS

dash.register_page(__name__, path="/simular", name="Simular", title="Simular - HUN", order=0.5)

# Figuras en linea (SVG): usan las variables de color del tema, asi que siguen el modo claro/oscuro.
_V = '<svg viewBox="0 0 320 150" preserveAspectRatio="xMidYMid meet">'
FIG = {
    "pron": _V + '<defs><linearGradient id="g-pron" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--brand);stop-opacity:.35"/><stop offset="1" style="stop-color:var(--brand);stop-opacity:0"/></linearGradient></defs>'
            '<path d="M44 24V122H284" class="gd"/>'
            '<path class="a-area" d="M50 112L84 98L114 106L144 82L174 76L204 62V122H50Z" fill="url(#g-pron)"/>'
            '<path d="M204 30V122" class="gd" style="stroke-dasharray:3 5;stroke:var(--accent)"/>'
            '<polyline class="ln a-linea" points="50,112 84,98 114,106 144,82 174,76 204,62"/>'
            '<polyline class="ln-sua a-sigue" points="204,62 244,50 276,40"/>'
            '<circle cx="204" cy="62" r="12" class="fs a-halo"/><circle cx="204" cy="62" r="6" class="ft"/></svg>',
    "espera": _V + '<g transform="translate(160 75)"><circle r="54" class="gd" style="stroke-width:8"/>'
              '<circle r="54" class="a-anillo" transform="rotate(-90)" style="fill:none;stroke:var(--accent);stroke-width:8;stroke-linecap:round;stroke-dasharray:340;stroke-dashoffset:230"/>'
              '<circle r="42" style="fill:var(--surface)"/><path d="M0-36V-30M36 0H30M0 36V30M-36 0H-30" class="gd" style="stroke-width:3"/>'
              '<line class="ln" x1="0" y1="0" x2="0" y2="-18" style="stroke-width:4"/><g class="a-aguja"><line class="ln" x1="0" y1="0" x2="0" y2="-30" style="stroke-width:3"/></g>'
              '<circle r="5" class="ft"/></g></svg>',
    "cama": _V + '<rect x="40" y="62" width="240" height="30" rx="15" style="fill:var(--surface);stroke:var(--line);stroke-width:2"/>'
            '<clipPath id="c-cama"><rect x="42" y="64" width="236" height="26" rx="13"/></clipPath>'
            '<g clip-path="url(#c-cama)"><rect class="ft a-avance" x="42" y="64" width="236" height="26" style="transform-origin:42px 77px"/></g>'
            '<g class="a-cursor"><rect x="38" y="30" width="34" height="20" rx="10" style="fill:var(--brand-ink)"/><text x="55" y="44" class="tx" text-anchor="middle" style="fill:var(--surface)">Hoy</text>'
            '<circle cx="55" cy="77" r="12" class="ft" style="stroke:var(--surface);stroke-width:3"/></g>'
            '<circle cx="46" cy="116" r="4" class="ft"/><text x="56" y="120" class="tx">Ingreso</text>'
            '<text x="262" y="120" class="tx" text-anchor="end">Alta</text><circle cx="274" cy="116" r="4" style="fill:none;stroke:var(--brand);stroke-width:2"/></svg>',
    "camas": _V + '<path d="M40 120H290" class="gd"/><path d="M40 38H290" class="gd" style="stroke-dasharray:4 6;stroke:var(--accent)"/>'
             '<rect class="ft a-c1" x="62" y="70" width="28" height="50" rx="5" opacity=".5"/><rect class="ft a-c2" x="104" y="70" width="28" height="50" rx="5" opacity=".65"/>'
             '<rect class="ft a-c3" x="146" y="70" width="28" height="50" rx="5" opacity=".8"/><rect class="ft a-c4" x="188" y="70" width="28" height="50" rx="5"/>'
             '<rect class="ft a-c5" x="230" y="70" width="28" height="50" rx="5" opacity=".65"/><text x="290" y="30" class="tx" text-anchor="end">Capacidad</text></svg>',
    "sim": _V + '<path d="M60 40H260M60 75H260M60 110H260" class="gd" style="stroke-width:6"/>'
           '<path class="ln a-f1" d="M60 40H100" style="stroke-width:6"/><path class="ln a-f2" d="M60 75H190" style="stroke-width:6"/><path class="ln a-f3" d="M60 110H150" style="stroke-width:6"/>'
           '<circle class="ft a-p1" cx="100" cy="40" r="12" style="stroke:var(--surface);stroke-width:3"/><circle class="ft a-p2" cx="190" cy="75" r="12" style="stroke:var(--surface);stroke-width:3"/>'
           '<circle class="ft a-p3" cx="150" cy="110" r="12" style="stroke:var(--surface);stroke-width:3"/></svg>',
}

MODULOS = [      # orden logico: primero el simulador (junta todo) y luego el recorrido: llegadas, camas, espera y estancia del paciente
    ("/simulador", "Simulador integral", "Pon el hospital a correr en tiempo real y mueve palancas, como más ingresos o altas más temprano, para ver cómo cambian las camas, las esperas y las alertas.", "sim"),
    ("/pronostico", "Pronosticador", "Cuántos pacientes llegarán a urgencias en los próximos días, con su margen de error.", "pron"),
    ("/camas", "Planeación de camas", "Cambia un supuesto sobre el futuro y mira cuántos pacientes quedarían esperando cama y cuántas camas harían falta.", "camas"),
    ("/paciente", "Paciente en espera", "Describe a un paciente que espera cama y mira a qué hora es más probable que la reciba.", "espera"),
    ("/paciente-cama", "Paciente en cama", "Describe a un paciente hospitalizado y mira qué día es más probable que reciba el alta.", "cama"),
]


def _tarjeta(n, ruta, titulo, desc, fig):
    return dcc.Link(href=ruta, className="menu-card sim-card" + (" sim-card--primera" if n == 1 else ""), children=[
        dcc.Markdown(FIG[fig], dangerously_allow_html=True, className="sim-card__fig"),
        html.Div(className="sim-card__cuerpo", children=[
            html.Div(className="sim-card__cab", children=[html.Span(titulo, className="menu-card__title"), html.Span(f"{n:02d}", className="sim-card__num")]),
            html.Div(desc, className="menu-card__desc"),
            html.Span("Abrir módulo", className="menu-card__go")])])


def layout():
    return html.Div(className="page-container", children=[
        html.Div(className="sim-head", children=[
            html.Span(className="sim-head__chip", children=[html.Span(className="nav__ico ico-models"), "Módulos interactivos"]),
            html.H1("¿Qué quieres hacer hoy?", className="sim-head__t"),
            html.P("Elige un módulo para explorar cómo se mueven los pacientes, las camas y las esperas del hospital.", className="sim-head__sub")]),
        html.Div(className="card-grid sim-grid", children=[_tarjeta(i, *m) for i, m in enumerate(MODULOS, 1)])])
