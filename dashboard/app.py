"""
dashboard/app.py  -  version 5 (9-nov-2026)
Dashboard del Data Challenge HUN 2026 en Dash (los organizadores aceptaron Dash). Es una app MULTIPAGINA con un menu lateral en el orden de
docs/estructura_dashboard.md (0 Inicio, 1 Contexto, 2 Resultados, 3 Prediccion y anticipacion, 4 Recomendaciones, 5 Anexos).
Cada pagina vive en dashboard/pages/ y se registra sola (dash.page_registry). Las paginas que aun no existen aparecen en gris en el menu como
«pendiente», para que se vea el plan completo sin inventar contenido.

PAGINAS HECHAS
  3.1 Pronostico de demanda        dashboard/pages/pronostico.py   (antes dashboard/app.py v4)
  3.7 ¿Cuando recibira cama?       dashboard/pages/estimador.py    (antes dashboard/estimador.py, A6)

COMO CORRERLO
  python3 dashboard/app.py    y abrir http://127.0.0.1:8050
  La pagina 3.7 necesita ademas HUN_PROCESADOS, HUN_TABLAS y HUN_CRUDOS (el modelo del estimador sale de datos clinicos y no se publica);
  sin ellas muestra un aviso y el resto del dashboard funciona igual.

DATOS  Solo tablas agregadas (sin ids ni datos de pacientes). NO se conecta a la base del hospital.
"""
import dash
from dash import Dash, dcc, html

from componentes import GRIS

# Menu completo de docs/estructura_dashboard.md. Las paginas hechas se enlazan por su ruta; las demas se muestran como pendientes.
MENU = [
    ("0. Inicio", ["0.1 Portada"]),
    ("1. Contexto", ["1.1 El reto y el alcance", "1.2 La base de datos", "1.3 Calidad de los datos", "1.4 Las variables",
                     "1.5 Las tablas del dashboard", "1.6 Metodología"]),
    ("2. Resultados", ["2.1 Demanda", "2.2 Ocupación de camas", "2.3 Espera de cama", "2.4 Hora de llegada y altas", "2.5 Qué influye en la espera",
                       "2.6 Perfiles de pacientes", "2.7 La estancia", "2.8 Diagnósticos"]),
    ("3. Predicción y anticipación", ["3.1 Pronóstico de demanda", "3.2 Alertas", "3.3 Días atípicos", "3.4 Simulador de camas",
                                      "3.5 Diagnóstico de cuello de botella", "3.6 Cómo se eligieron los modelos", "3.7 ¿Cuándo recibirá cama?"]),
    ("4. Recomendaciones", ["4.1 Qué hacemos con esto"]),
    ("5. Anexos", ["5.1 Limitaciones", "5.2 Glosario", "5.3 Repositorio"]),
]

app = Dash(__name__, use_pages=True, title="Data Challenge HUN 2026", suppress_callback_exceptions=True)
server = app.server


def menu():
    hechas = {p["name"]: p["relative_path"] for p in dash.page_registry.values()}
    bloques = []
    for parte, paginas in MENU:
        items = []
        for nombre in paginas:
            if nombre in hechas:
                items.append(dcc.Link(nombre, href=hechas[nombre], style={"display": "block", "padding": "3px 0", "color": "#1f4e79"}))
            else:
                items.append(html.Div(f"{nombre} · pendiente", style={"padding": "3px 0", "color": "#aaa"}))
        bloques.append(html.Div([html.Div(parte, style={"fontWeight": 700, "marginTop": "12px"}), *items]))
    return html.Nav(bloques, style={"flex": "0 0 230px", "fontSize": "13px", "borderRight": "1px solid #ddd", "paddingRight": "14px"})


app.layout = html.Div(style={"fontFamily": "system-ui, sans-serif", "maxWidth": "1400px", "margin": "0 auto", "padding": "16px"}, children=[
    html.Div("Data Challenge HUN 2026 · flujo de pacientes", style={"fontSize": "13px", "color": GRIS, "marginBottom": "6px"}),
    html.Div(style={"display": "flex", "gap": "24px", "alignItems": "flex-start"}, children=[
        menu(),
        html.Main(dash.page_container, style={"flex": "1 1 auto", "minWidth": 0}),
    ]),
])


if __name__ == "__main__":
    app.run(debug=False, port=8050)
