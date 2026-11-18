"""
dashboard/pages/inicio.py  -  pantalla de inicio del dashboard (12-nov-2026; tarjetas por seccion desde el 13-nov-2026)
Pagina de bienvenida (ruta `/`, `order=0`) que reemplaza el arranque directo en el pronostico. Muestra la portada con la marca
del hospital, un resumen de contexto y un menu de tarjetas para entrar a cada pagina, agrupadas por seccion (contexto, resultados,
prediccion y propuestas) con la misma lista de la barra lateral (`dashboard/navegacion.py`).

No carga datos ni se conecta a la base, asi que nunca falla el arranque. Las cifras del resumen son hechos ya
documentados del proyecto (CLAUDE.md, docs/HALLAZGOS.md), presentados como contexto, no como un calculo en vivo.
"""
import sys
from pathlib import Path

import dash
from dash import dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from navegacion import ICONOS, agrupar  # noqa: E402

dash.register_page(__name__, path="/", name="Inicio", title="Dashboard HUN — Inicio", order=0)

# ruta -> (titulo de la tarjeta, descripcion). Una pagina sin entrada sale con su nombre y sin descripcion.
TARJETAS = {
    "/resumen": ("Resumen",
                 "El proyecto en una pantalla: los ocho hallazgos, cada uno con su página, y lo que proponemos."),
    "/comparar": ("Comparar años",
                  "Elige dos años y mira qué cambió en la espera: en qué tramos, en qué grupos de pacientes y por dónde entran."),
    "/factores": ("Qué influye en la espera",
                  "Lo que se sabe del paciente explica solo el 16 % de su espera: qué factores pesan y cuáles no."),
    "/estancia": ("Estancias largas",
                  "Por qué subió la estancia media: unas pocas estancias de semanas ocupan un tercio de las camas."),
    "/diagnosticos": ("Diagnósticos",
                      "Qué grupos de diagnóstico esperan más cama y cuáles se quedan más tiempo hospitalizados."),
    "/alertas": ("Alertas",
                 "Las alertas del proyecto, qué tan bien aciertan y qué recomendación dispara cada una: día congestionado, ocupación alta, paciente sin cama y cola de espera."),
    "/atipicos": ("Días atípicos",
                  "Los días que se salen del patrón y lo que dicen: el problema de la espera es de todos los días."),
    "/datos": ("Datos y calidad",
               "De 3,3 millones de etapas a 337 mil episodios: qué había en la base, qué se corrigió y hasta dónde se puede confiar."),
    "/demanda": ("Demanda",
                 "¿A qué hora y qué día llegan los pacientes? Mapa por día y hora, y cómo cambian las llegadas mes a mes."),
    "/ocupacion": ("Ocupación de camas",
                   "Camas ocupadas frente a las 106 del hospital, y por qué sube la ocupación si no llegan más pacientes."),
    "/espera": ("Espera de cama",
                "El cuello de botella: cuánto se espera por una cama, quién espera más y cómo empeoran los peores casos."),
    "/altas": ("Llegada y altas",
               "A qué hora salen las altas, a qué hora se asignan las camas y cuánto espera quien llega a cada hora."),
    "/perfiles": ("Perfiles y picos",
                  "¿Qué perfiles de paciente esperan o se quedan distinto cuando el hospital está más cargado? Perfiles, trayectorias y días de alta demanda."),
    "/pronostico": ("Pronóstico de demanda",
                    "¿Cuántos pacientes ingresarán al hospital y a cama en los próximos días? Proyección diaria con su rango probable."),
    "/estacionalidad": ("Forma del año",
                        "Qué épocas del año traen más pacientes y cuánto mejora el pronóstico al saberlo."),
    "/paciente": ("Paciente en espera",
                  "Describe a un paciente y estima en qué momento del día es más probable que reciba cama, con su rango típico."),
    "/camas": ("Planeación de camas",
               "Simula «¿qué pasaría si…?»: más ingresos, menos estancia u otra mezcla de perfiles, y mira la ocupación proyectada."),
    "/simulador": ("Simulador integral",
                   "Un solo motor sigue a cada paciente simulado: demanda, cola de espera y ocupación a la vez. Saltan alertas con su recomendación y puedes aplicar la mejora y compararla."),
    "/recomendaciones": ("Recomendaciones",
                         "Siete acciones para el hospital, cada una con lo que dicen nuestros datos y lo que se encontró en otros hospitales."),
    "/documentacion": ("Documentación",
                       "El documento completo del proyecto: datos, hallazgos, modelos, recomendaciones y referencias, con descarga en PDF."),
}

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


def grupo(titulo, descripcion, paginas):
    """Una seccion del menu: su titulo, la pregunta que responde y las tarjetas de sus paginas."""
    tarjetas = []
    for p in paginas:
        nombre, texto = TARJETAS.get(p["path"], (p["name"], ""))
        tarjetas.append(tarjeta_menu(p["path"], ICONOS.get(p["path"], "ico-profiles"), nombre, texto))
    return html.Section(className="home-group", children=[
        html.Div(className="home-group__head", children=[
            html.Div(titulo, className="section-title"), html.Div(descripcion, className="home-group__sub")]),
        html.Div(className="card-grid", children=tarjetas),
    ])


def layout():
    paginas = sorted(dash.page_registry.values(), key=lambda p: (p.get("order") is None, p.get("order", 0), p["path"]))
    return html.Div(className="page-container", children=[
        html.Section(className="hero", children=[
            html.Div(className="hero__heart"),
            html.Div("Hospital Universidad del Norte · Servimos con corazón", className="hero__eyebrow"),
            html.H1("Analítica del flujo de pacientes", className="hero__title"),
            html.P("Un panel único para entender, predecir y planear la atención en el hospital: qué datos hay, cómo llegan "
                   "los pacientes, dónde se pierde el tiempo, qué se espera para los próximos meses y qué proponemos. "
                   "Elige una página o recórrelo en orden, como una presentación.", className="hero__sub"),
            dcc.Link("Empezar el recorrido", href="/resumen", className="hero__cta"),
            html.Div("Avanza con las flechas ← → del teclado. El botón de la esquina superior derecha oculta el menú para presentar.",
                     className="hero__hint"),
        ]),

        html.Div("El hospital en una mirada", className="section-title", style={"marginTop": "28px"}),
        html.Div(className="stat-row", style={"marginTop": "0"}, children=[tarjeta_resumen(n, e) for n, e in RESUMEN]),
        html.P("Cifras de contexto ya documentadas en la página de Documentación (regla de estancia única). "
               "Casi todo son asociaciones y escenarios, no causas; periodo confiable: feb-2023 a 9-abr-2026.",
               style={"fontSize": "12px", "color": "var(--muted)", "marginTop": "10px"}),

        *[grupo(*g) for g in agrupar(paginas)],
    ])
