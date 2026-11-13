"""
dashboard/main.py  -  version 2 (12-nov-2026)
Punto de entrada UNICO del dashboard (patron multipagina de Dash, `use_pages=True`). Cada pieza vive en
`dashboard/pages/*.py` y se registra con `dash.register_page()`; la navegacion se arma sola a partir de
`dash.page_registry`, asi que agregar una pagina nueva solo exige crear el archivo en `pages/` con su
`register_page` -- no hay que tocar este archivo.

DISENO (12-nov-2026): rediseno completo con estetica tipo Google (Material 3 / Gemini): barra lateral con el
logo del HUN y navegacion en pildoras, barra superior con el titulo de la pagina activa, y una PANTALLA DE
INICIO (`pages/inicio.py`, ruta `/`) con un menu de tarjetas en vez de abrir directo en el pronostico. Todo el
estilo esta en `dashboard/assets/theme.css` (Dash lo carga solo). La paleta viene del logo del hospital.

PAGINAS (ver docstring de cada una en dashboard/pages/):
  /            inicio.py      Pantalla de inicio con el menu de secciones
  /pronostico  pronostico.py  Pronostico de demanda (Daniela/Samuel)
  /paciente    paciente.py    Paciente en espera (A6, Samuel)
  /camas       camas.py       Planeacion de camas (A5, Anthony)
  /perfiles    perfiles.py    Perfiles y picos (Anthony)
  /datos           datos.py            Datos y calidad: de la base a los episodios analizados (Samuel)
  /demanda         demanda.py          Cuando llegan los pacientes (Samuel)
  /ocupacion       ocupacion.py        Camas ocupadas frente a las 106 del hospital (Samuel)
  /espera          espera.py           Espera de cama: el cuello de botella (Samuel)
  /altas           altas.py            Hora de llegada, altas y asignacion de camas (Samuel)
  /estacionalidad  estacionalidad.py   La forma del año del pronostico (A9, Samuel)
  /recomendaciones recomendaciones.py  Las 7 recomendaciones con su evidencia (Samuel)
  /documentacion   documentacion.py    El documento final completo con descarga en PDF (Samuel)

MENU (13-nov-2026): la barra lateral agrupa las paginas por seccion (contexto, resultados, prediccion y propuestas) con la
lista de `dashboard/navegacion.py`, la misma que usa el inicio. Una pagina que no este en esa lista aparece al final, bajo "Más".
Al pie de cada pagina hay botones «anterior» y «siguiente» en ese mismo orden: el dashboard se puede recorrer como una presentacion.

COMO CORRERLO  python dashboard/main.py   y abrir http://127.0.0.1:8050
  La primera vez que se visita /paciente, el modelo de A6 se entrena si no existe (~1 min). Las demas paginas
  cargan sus datos al arrancar el proceso, por eso el arranque tarda unos segundos.
"""
import sys
from pathlib import Path

import dash
from dash import Dash, Input, Output, State, callback, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent))
from navegacion import ICONOS, agrupar, recorrido  # noqa: E402

app = Dash(__name__, use_pages=True, pages_folder="pages", title="Dashboard HUN",
           update_title="Actualizando…")
server = app.server

# Archivos del documento final para la pagina /documentacion: graficos de resultados/graficos/ y el PDF (solo graficos y el documento;
# nada de datos por paciente).
from pathlib import Path as _Path  # noqa: E402
from flask import abort, send_from_directory  # noqa: E402

_RAIZ = _Path(__file__).resolve().parent.parent


@server.route("/graficos/<path:archivo>")
def _grafico(archivo):
    if not archivo.lower().endswith((".png", ".jpg", ".jpeg", ".svg")):
        abort(404)
    return send_from_directory(_RAIZ / "resultados" / "graficos", archivo)


@server.route("/documento_final.pdf")
def _documento_pdf():
    return send_from_directory(_RAIZ / "docs", "documento_final.pdf")

# Los iconos (ICONOS) y las secciones del menu viven en dashboard/navegacion.py, que tambien usa la pantalla de inicio.


def _paginas_ordenadas():
    """Las paginas registradas, ordenadas por su `order` (inicio primero)."""
    return sorted(dash.page_registry.values(), key=lambda p: (p.get("order") is None, p.get("order", 0), p["path"]))


def enlace_nav(pagina, ruta_activa):
    ico = ICONOS.get(pagina["path"], "ico-profiles")
    activo = " is-active" if pagina["path"] == ruta_activa else ""
    return dcc.Link(href=pagina["path"], className="nav__item" + activo, children=[
        html.Span(className="nav__ico " + ico),
        html.Span(pagina["name"]),
    ])


def enlaces_nav(ruta_activa):
    """Enlaces del menu: el inicio y luego cada seccion con su titulo (las secciones estan en navegacion.py)."""
    paginas = _paginas_ordenadas()
    hijos = [enlace_nav(p, ruta_activa) for p in paginas if p["path"] == "/"]
    for titulo, _descripcion, grupo in agrupar(paginas):
        hijos.append(html.Div(titulo, className="nav__label"))
        hijos += [enlace_nav(p, ruta_activa) for p in grupo]
    return hijos


def barra_lateral(ruta_activa="/"):
    return html.Aside(className="sidebar", children=[
        dcc.Link(href="/", className="sidebar__brand", children=html.Img(
            src=dash.get_asset_url("logo_hun.png"), alt="Hospital Universidad del Norte")),
        html.Div("Analítica de flujo", className="nav__label"),
        html.Nav(id="nav-principal", className="nav",
                 children=enlaces_nav(ruta_activa)),
        html.Div(className="sidebar__foot", children=[
            html.Div("Data Challenge HUN 2026"),
            html.Div("Flujo de pacientes · Uninorte", style={"marginTop": "2px"}),
        ]),
    ])


def pasos(ruta):
    """Botones «anterior» y «siguiente» al pie de cada pagina: el dashboard se recorre en orden, como una presentacion."""
    orden = recorrido(_paginas_ordenadas())
    rutas = [p["path"] for p in orden]
    if ruta not in rutas:
        return []
    i = rutas.index(ruta)

    def boton(j, direccion, clase):
        if not 0 <= j < len(orden):
            return html.Span()
        return dcc.Link(href=orden[j]["path"], className="paso__btn " + clase, children=[
            html.Span(direccion, className="paso__dir"), html.Span(orden[j]["name"], className="paso__nombre")])

    return [boton(i - 1, "← Anterior", "paso__btn--ant"), html.Span(f"{i + 1} de {len(orden)}", className="paso__pos"),
            boton(i + 1, "Siguiente →", "paso__btn--sig")]


def barra_superior():
    return html.Header(className="topbar", children=[
        html.Div("Inicio", id="topbar-titulo", className="topbar__title"),
        html.Div(className="topbar__right", children=[
            html.Span("Datos confiables hasta 9-abr-2026", className="topbar__chip"),
            html.Button("☾", id="theme-toggle", className="theme-toggle", n_clicks=0,
                        title="Cambiar entre modo claro y oscuro"),
        ]),
    ])


def servir_layout():
    return html.Div(className="app-shell", children=[
        dcc.Location(id="url"),
        dcc.Store(id="theme-store", storage_type="local"),   # recuerda el tema entre visitas
        html.Div(id="grafico-tema-dummy", style={"display": "none"}),
        barra_lateral(),
        html.Div(className="main", children=[
            barra_superior(),
            html.Main(className="content", children=[dash.page_container, html.Nav(id="paso-nav", className="paso")]),
        ]),
    ])


app.layout = servir_layout


@callback(Output("nav-principal", "children"), Output("topbar-titulo", "children"), Output("paso-nav", "children"),
          Input("url", "pathname"))
def sincronizar_navegacion(ruta):
    """Resalta el enlace activo en la barra lateral, pone el nombre de la pagina en la barra superior y arma los botones del pie."""
    ruta = ruta or "/"
    enlaces = enlaces_nav(ruta)
    actual = next((p["name"] for p in dash.page_registry.values() if p["path"] == ruta), "Inicio")
    return enlaces, actual, pasos(ruta)


# Modo claro/oscuro: todo del lado del cliente para que sea instantaneo y no necesite al servidor.
# Al cargar (n_clicks inicial) aplica el tema guardado; al pulsar el boton lo alterna y lo persiste.
app.clientside_callback(
    """
    function(n_clicks, data) {
        var cur = (data && data.theme) ? data.theme : 'light';
        var ctx = dash_clientside.callback_context;
        var porClick = ctx && ctx.triggered && ctx.triggered.length &&
                       ctx.triggered[0].prop_id.indexOf('theme-toggle') === 0;
        var tema = porClick ? (cur === 'dark' ? 'light' : 'dark') : cur;
        document.documentElement.setAttribute('data-theme', tema);
        var icono = (tema === 'dark') ? '\\u2600' : '\\u263E';   // sol en oscuro, luna en claro
        return [{theme: tema}, icono];
    }
    """,
    Output("theme-store", "data"),
    Output("theme-toggle", "children"),
    Input("theme-toggle", "n_clicks"),
    State("theme-store", "data"),
)

# Retematiza AL INSTANTE los graficos que ya estan dibujados cuando cambia el tema, sin volver a pedirlos al
# servidor y SIN perder el estado interactivo (zoom, paneo). Solo cambia colores de layout via Plotly.relayout;
# el fondo es transparente, asi que el grafico ya toma el color claro/oscuro del contenedor.
app.clientside_callback(
    """
    function(data) {
        if (!window.Plotly) { return ''; }
        var dark = (data && data.theme === 'dark');
        var c = dark ? {t:'#e6edf3', ti:'#e8eef4', g:'#27313c', l:'#3a4653'}
                     : {t:'#1a1d21', ti:'#0a2540', g:'#e6ecf3', l:'#d7dfe8'};
        document.querySelectorAll('.js-plotly-plot').forEach(function(gd){
            try {
                Plotly.relayout(gd, {
                    'font.color': c.t, 'title.font.color': c.ti, 'legend.font.color': c.t,
                    'xaxis.gridcolor': c.g, 'yaxis.gridcolor': c.g,
                    'xaxis.linecolor': c.l, 'yaxis.linecolor': c.l,
                    'xaxis.zerolinecolor': c.g, 'yaxis.zerolinecolor': c.g,
                    'paper_bgcolor': 'rgba(0,0,0,0)', 'plot_bgcolor': 'rgba(0,0,0,0)'
                });
            } catch (e) {}
        });
        return '';
    }
    """,
    Output("grafico-tema-dummy", "children"),
    Input("theme-store", "data"),
)


if __name__ == "__main__":
    app.run(debug=False, port=8050)
