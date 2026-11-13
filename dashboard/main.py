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
  /recomendaciones recomendaciones.py  Las 7 recomendaciones con su evidencia (Samuel)

COMO CORRERLO  python dashboard/main.py   y abrir http://127.0.0.1:8050
  La primera vez que se visita /paciente, el modelo de A6 se entrena si no existe (~1 min). Las demas paginas
  cargan sus datos al arrancar el proceso, por eso el arranque tarda unos segundos.
"""
import dash
from dash import Dash, Input, Output, State, callback, dcc, html

app = Dash(__name__, use_pages=True, pages_folder="pages", title="Dashboard HUN",
           update_title="Actualizando…")
server = app.server

# Icono (clase CSS de theme.css) para cada ruta. Una ruta sin entrada cae en el icono generico de perfiles.
ICONOS = {"/": "ico-home", "/pronostico": "ico-forecast", "/paciente": "ico-patient",
          "/camas": "ico-bed", "/perfiles": "ico-profiles", "/recomendaciones": "ico-recs"}


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


def barra_lateral(ruta_activa="/"):
    return html.Aside(className="sidebar", children=[
        dcc.Link(href="/", className="sidebar__brand", children=html.Img(
            src=dash.get_asset_url("logo_hun.png"), alt="Hospital Universidad del Norte")),
        html.Div("Analítica de flujo", className="nav__label"),
        html.Nav(id="nav-principal", className="nav",
                 children=[enlace_nav(p, ruta_activa) for p in _paginas_ordenadas()]),
        html.Div(className="sidebar__foot", children=[
            html.Div("Data Challenge HUN 2026"),
            html.Div("Flujo de pacientes · Uninorte", style={"marginTop": "2px"}),
        ]),
    ])


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
            html.Main(className="content", children=dash.page_container),
        ]),
    ])


app.layout = servir_layout


@callback(Output("nav-principal", "children"), Output("topbar-titulo", "children"),
          Input("url", "pathname"))
def sincronizar_navegacion(ruta):
    """Resalta el enlace activo en la barra lateral y pone el nombre de la pagina en la barra superior."""
    ruta = ruta or "/"
    enlaces = [enlace_nav(p, ruta) for p in _paginas_ordenadas()]
    actual = next((p["name"] for p in dash.page_registry.values() if p["path"] == ruta), "Inicio")
    return enlaces, actual


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
