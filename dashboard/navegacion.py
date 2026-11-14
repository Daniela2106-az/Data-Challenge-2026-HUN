"""
dashboard/navegacion.py  -  secciones del menu del dashboard (13-nov-2026)
Una sola lista para la barra lateral (main.py) y para las tarjetas del inicio (pages/inicio.py), en el orden de
docs/estructura_dashboard.md: contexto, resultados, prediccion y propuestas.

Una pagina nueva que no este en SECCIONES aparece sola al final, bajo "Más": para agregarla basta con crear su archivo en pages/.
"""
# Icono (clase CSS de theme.css) de cada ruta. Una ruta sin entrada usa el icono generico de perfiles.
ICONOS = {"/": "ico-home", "/pronostico": "ico-forecast", "/paciente": "ico-patient", "/camas": "ico-bed",
          "/perfiles": "ico-profiles", "/recomendaciones": "ico-recs", "/documentacion": "ico-docs", "/datos": "ico-data",
          "/demanda": "ico-demand", "/ocupacion": "ico-occup", "/espera": "ico-wait", "/altas": "ico-clock",
          "/estacionalidad": "ico-season", "/alertas": "ico-alert", "/factores": "ico-factors", "/estancia": "ico-stay",
          "/diagnosticos": "ico-dx", "/atipicos": "ico-outlier", "/modelos": "ico-models", "/resumen": "ico-summary", "/comparar": "ico-compare"}

# (titulo de la seccion, que responde, rutas en orden)
SECCIONES = [
    ("Contexto", "El proyecto en una pantalla, y qué datos hay detrás", ["/resumen", "/datos"]),
    ("Resultados", "Qué pasa hoy en el hospital y dónde se pierde el tiempo",
     ["/demanda", "/ocupacion", "/espera", "/comparar", "/altas", "/factores", "/estancia", "/diagnosticos", "/perfiles"]),
    ("Predicción", "Qué se espera y qué pasaría si algo cambia",
     ["/pronostico", "/estacionalidad", "/alertas", "/atipicos", "/paciente", "/camas", "/modelos"]),
    ("Propuestas", "Qué hacer con lo que se encontró", ["/recomendaciones", "/documentacion"]),
]


def agrupar(paginas):
    """Reparte las paginas registradas (dicts de dash.page_registry, ya ordenadas) en las secciones.
    Devuelve [(titulo, descripcion, [paginas])]; el inicio queda fuera y lo que no este en SECCIONES va a "Más"."""
    por_ruta = {p["path"]: p for p in paginas}
    grupos, usadas = [], {"/"}
    for titulo, descripcion, rutas in SECCIONES:
        presentes = [por_ruta[r] for r in rutas if r in por_ruta]
        if presentes:
            grupos.append((titulo, descripcion, presentes))
        usadas.update(rutas)
    resto = [p for p in paginas if p["path"] not in usadas]
    if resto:
        grupos.append(("Más", "", resto))
    return grupos


def recorrido(paginas):
    """Las paginas en el orden en que se recorre el dashboard, como una presentacion: el inicio y luego cada seccion."""
    inicio = [p for p in paginas if p["path"] == "/"]
    return inicio + [p for _titulo, _descripcion, grupo in agrupar(paginas) for p in grupo]
