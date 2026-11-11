"""
dashboard/main.py  -  version 1 (10-nov-2026)
Punto de entrada UNICO del dashboard (reemplaza las 5 apps sueltas: app.py, estimador.py, camas.py,
perfiles.py y menu.py, retiradas el 10-nov-2026). Un solo proceso Dash, un solo puerto, con el patron
multipagina de Dash (`use_pages=True`): cada pieza vive en `dashboard/pages/*.py` y se registra con
`dash.register_page()`. La barra de navegacion se arma sola a partir de `dash.page_registry`, asi que agregar
una pagina nueva solo exige crear el archivo en `pages/` con su `register_page` -- no hay que tocar este archivo.

PAGINAS (ver docstring de cada una en dashboard/pages/):
  /          pronostico.py  Pronostico de demanda (Daniela/Samuel)
  /paciente  paciente.py    Paciente en espera (A6, Samuel)
  /camas     camas.py       Planeacion de camas (A5, Anthony)
  /perfiles  perfiles.py    Perfiles y picos (Anthony)

COMO CORRERLO  python3 dashboard/main.py   y abrir http://127.0.0.1:8050
  La primera vez que se visita /paciente, el modelo de A6 se entrena si no existe (~1 min). Las demas paginas
  cargan sus datos al arrancar el proceso (no al visitarlas), por eso el arranque tarda unos segundos.
"""
import dash
from dash import Dash, dcc, html

GRIS, AZUL = "#6b6b6b", "#2a6fb0"

app = Dash(__name__, use_pages=True, pages_folder="pages", title="Dashboard HUN")
server = app.server


def barra_navegacion():
    enlaces = [dcc.Link(pg["name"], href=pg["path"], style={
        "padding": "8px 14px", "borderRadius": "6px", "textDecoration": "none", "color": "#fff",
        "fontWeight": 600, "fontSize": "14px"}) for pg in dash.page_registry.values()]
    return html.Div(enlaces, style={"display": "flex", "gap": "6px", "backgroundColor": AZUL,
                                    "padding": "10px 16px", "flexWrap": "wrap"})


app.layout = html.Div([
    barra_navegacion(),
    html.Div(dash.page_container, style={"padding": "0"}),
], style={"fontFamily": "system-ui, sans-serif", "backgroundColor": "#f7f7f5", "minHeight": "100vh"})


if __name__ == "__main__":
    app.run(debug=False, port=8050)
