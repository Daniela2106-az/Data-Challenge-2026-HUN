"""
dashboard/menu.py  -  version 1 (10-nov-2026)
Menu minimo del dashboard (Etapa 4 del plan de Anthony). Hoy el dashboard son 4 apps Dash sueltas, cada una en
su propio puerto, sin un menu compartido. Esta pagina es solo un INDICE con enlaces -- no fusiona las apps en
una sola (eso, si se quiere de verdad integrado en un solo proceso con rutas compartidas, es alcance de B1,
tarea de Samuel). Sirve para que cualquiera abra las 4 piezas desde un solo lugar mientras B1 no este lista.

PAGINAS (deben estar corriendo cada una en su puerto para que el enlace funcione):
  8050  dashboard/app.py        Pronostico de demanda (Daniela/Samuel)
  8051  dashboard/estimador.py  Paciente en espera (A6, Samuel)
  8052  dashboard/camas.py      Planeacion de camas (A5, Anthony)
  8054  dashboard/perfiles.py   Perfiles y picos (Anthony)

COMO CORRERLO  python3 dashboard/menu.py   y abrir http://127.0.0.1:8055
"""
from dash import Dash, html

GRIS, AZUL, NARANJA, VERDE, MORADO = "#6b6b6b", "#2a6fb0", "#eb6834", "#2e8b57", "#7a4fb5"

app = Dash(__name__, title="Dashboard HUN - Menú")
server = app.server

PAGINAS = [
    {"nombre": "Pronóstico de demanda", "puerto": 8050, "color": AZUL,
     "descripcion": "¿Cuántos pacientes van a llegar? Serie histórica y pronóstico por día."},
    {"nombre": "Paciente en espera", "puerto": 8051, "color": NARANJA,
     "descripcion": "Para UN paciente concreto que ya está esperando cama: rango de horas que le faltan (A6)."},
    {"nombre": "Planeación de camas", "puerto": 8052, "color": VERDE,
     "descripcion": "«¿Qué pasaría si...?» del hospital completo: más ingresos, menos estancia, otra mezcla de perfiles (A5)."},
    {"nombre": "Perfiles y picos", "puerto": 8054, "color": MORADO,
     "descripcion": "Tabla histórica: qué perfiles de paciente esperan o se quedan más, y si cambia en los momentos de más carga."},
]


def tarjeta(p):
    url = f"http://127.0.0.1:{p['puerto']}/"
    return html.A(href=url, target="_blank", style={"textDecoration": "none"}, children=html.Div([
        html.Div(p["nombre"], style={"fontSize": "18px", "fontWeight": 700, "color": p["color"]}),
        html.Div(p["descripcion"], style={"fontSize": "13px", "color": GRIS, "marginTop": "6px"}),
        html.Div(f"puerto {p['puerto']}", style={"fontSize": "11px", "color": GRIS, "marginTop": "10px", "fontFamily": "monospace"}),
    ], style={"border": f"1px solid {p['color']}33", "borderLeft": f"4px solid {p['color']}", "borderRadius": "8px",
              "padding": "16px 18px", "minHeight": "110px", "backgroundColor": "#fff", "cursor": "pointer"}))


app.layout = html.Div(style={"fontFamily": "system-ui, sans-serif", "maxWidth": "900px", "margin": "0 auto",
                             "padding": "24px", "backgroundColor": "#f7f7f5", "minHeight": "100vh"}, children=[
    html.H2("Dashboard HUN — Data Challenge 2026"),
    html.P("Cuatro piezas, cada una para una audiencia distinta (paciente concreto / perfiles históricos / "
           "hospital completo a futuro / demanda del sistema). Cada tarjeta abre su página en una pestaña "
           "nueva — hay que tener corriendo cada script por separado.",
           style={"color": GRIS, "marginBottom": "20px"}),
    html.Div(style={"display": "grid", "gridTemplateColumns": "repeat(2, 1fr)", "gap": "14px"},
             children=[tarjeta(p) for p in PAGINAS]),
    html.P("Menú provisional (Etapa 4, 10-nov-2026): es solo un índice con enlaces, no integra las apps en un "
           "único proceso. La integración real en un solo dashboard con rutas compartidas es alcance de B1 "
           "(Samuel).", style={"fontSize": "11px", "color": GRIS, "marginTop": "24px"}),
])

if __name__ == "__main__":
    app.run(debug=False, port=8055)
