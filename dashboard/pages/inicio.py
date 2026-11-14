"""
dashboard/pages/inicio.py  -  pantalla de inicio del dashboard (12-nov-2026)
Pagina de bienvenida (ruta `/`, `order=0`) que reemplaza el arranque directo en el pronostico. Muestra un
menu de tarjetas para entrar a cada seccion, siguiendo el flujo estandar de una app web de analitica de datos:
una portada con la marca del hospital, un resumen de contexto y accesos claros a cada herramienta.

No carga datos ni se conecta a la base, asi que nunca falla el arranque. Las cifras del resumen son hechos ya
documentados del proyecto (CLAUDE.md, docs/HALLAZGOS.md), presentados como contexto, no como un calculo en vivo.
"""
import dash
from dash import dcc, html

dash.register_page(__name__, path="/", name="Inicio", title="Dashboard HUN — Inicio", order=0)

# (ruta, clase de icono, titulo, descripcion)
SECCIONES = [
    ("/pronostico", "ico-forecast", "Pronóstico de demanda",
     "¿Cuántos pacientes ingresarán al hospital y a cama en los próximos días? Proyección diaria con su rango probable."),
    ("/paciente", "ico-patient", "Paciente en espera",
     "Describe a un paciente y estima en qué momento del día es más probable que reciba cama, con su rango típico."),
    ("/camas", "ico-bed", "Planeación de camas",
     "Simula «¿qué pasaría si…?»: más ingresos, menos estancia u otra mezcla de perfiles, y mira la ocupación proyectada."),
]

RESUMEN = [
    ("18,6 h", "Espera mediana por una cama de hospitalización"),
    ("106", "Camas de hospitalización en el HUN"),
    ("~20", "Ingresos a cama por día (promedio)"),
    ("~94–105", "Camas ocupadas en promedio (2023 → 2025)"),
]


def tarjeta_menu(ruta, icono, titulo, descripcion):
    return dcc.Link(href=ruta, className="menu-card", children=[
        html.Div(className="menu-card__ico", children=html.Span(className="nav__ico " + icono)),
        html.Div(titulo, className="menu-card__title"),
        html.Div(descripcion, className="menu-card__desc"),
        html.Span("Abrir", className="menu-card__go"),
    ])


def tarjeta_resumen(numero, etiqueta):
    return html.Div(className="stat", children=[
        html.Div(numero, className="stat__num"),
        html.Div(etiqueta, className="stat__lbl"),
    ])


def layout():
    return html.Div(className="page-container", children=[
        html.Section(className="hero", children=[
            html.Div(className="hero__heart"),
            html.Div("Hospital Universidad del Norte · Servimos con corazón", className="hero__eyebrow"),
            html.H1("Analítica del flujo de pacientes", className="hero__title"),
            html.P("Un panel único para entender, predecir y planear la atención en el hospital: pronóstico de "
                   "demanda, estimación de espera por cama y planeación de capacidad. "
                   "Elige una sección para empezar.", className="hero__sub"),
        ]),

        html.Div("Secciones", className="section-title"),
        html.Div(className="card-grid", children=[tarjeta_menu(*s) for s in SECCIONES]),

        html.Div("El hospital en una mirada", className="section-title", style={"marginTop": "32px"}),
        html.Div(className="stat-row", children=[tarjeta_resumen(n, e) for n, e in RESUMEN]),
        html.P("Cifras de contexto ya documentadas (regla de estancia única v3.8, CLAUDE.md / docs/HALLAZGOS.md). "
               "Casi todo son asociaciones y escenarios, no causas; periodo confiable: feb-2023 a 9-abr-2026.",
               style={"fontSize": "12px", "color": "var(--muted)", "marginTop": "14px"}),
    ])
