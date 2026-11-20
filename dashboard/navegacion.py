"""
dashboard/navegacion.py  -  secciones del menu del dashboard (13-nov-2026)
Una sola lista para la barra lateral (main.py) y para las tarjetas del inicio (pages/inicio.py), en el orden de
docs/estructura_dashboard.md: contexto, resultados, prediccion y propuestas.

Una pagina nueva que no este en SECCIONES aparece sola al final, bajo "Más": para agregarla basta con crear su archivo en pages/.
"""
import re

# Icono (clase CSS de theme.css) de cada ruta. Una ruta sin entrada usa el icono generico de perfiles.
ICONOS = {"/": "ico-home", "/pronostico": "ico-forecast", "/paciente": "ico-patient", "/camas": "ico-bed", "/simulador": "ico-models",
          "/perfiles": "ico-profiles", "/recomendaciones": "ico-recs", "/documentacion": "ico-docs", "/datos": "ico-data",
          "/demanda": "ico-demand", "/ocupacion": "ico-occup", "/espera": "ico-wait", "/altas": "ico-clock",
          "/estacionalidad": "ico-season", "/alertas": "ico-alert", "/preguntas": "ico-chat", "/factores": "ico-factors", "/estancia": "ico-stay",
          "/diagnosticos": "ico-dx", "/atipicos": "ico-outlier", "/resumen": "ico-summary", "/comparar": "ico-compare", "/periodo": "ico-period"}

# (titulo de la seccion, que responde, rutas en orden)
SECCIONES = [
    ("Contexto", "El proyecto en una pantalla, y qué datos hay detrás", ["/resumen", "/datos"]),
    ("Resultados", "Qué pasa hoy en el hospital y dónde se pierde el tiempo",
     ["/demanda", "/estacionalidad", "/ocupacion", "/espera", "/comparar", "/periodo", "/altas", "/factores", "/estancia", "/diagnosticos", "/perfiles", "/atipicos", "/alertas"]),
    ("Predicción", "Qué se espera y qué pasaría si algo cambia",
     ["/pronostico", "/paciente", "/camas", "/simulador"]),
    ("Propuestas", "Qué hacer con lo que se encontró", ["/recomendaciones", "/preguntas", "/documentacion"]),
]


# Paginas que no van en el menu principal porque viven dentro de la Documentacion (se abren desde su submenu y desde cada componente)
DENTRO_DE_DOCUMENTACION = {}


def agrupar(paginas):
    """Reparte las paginas registradas (dicts de dash.page_registry, ya ordenadas) en las secciones.
    Devuelve [(titulo, descripcion, [paginas])]; el inicio queda fuera y lo que no este en SECCIONES va a "Más"."""
    paginas = [p for p in paginas if "<" not in p["path"] and not p.get("path_template")]      # las rutas con plantilla (/documentacion/<cap>) no van en el menu
    por_ruta = {p["path"]: p for p in paginas}
    grupos, usadas = [], {"/"}
    for titulo, descripcion, rutas in SECCIONES:
        presentes = [por_ruta[r] for r in rutas if r in por_ruta]
        if presentes:
            grupos.append((titulo, descripcion, presentes))
        usadas.update(rutas)
    usadas.update(DENTRO_DE_DOCUMENTACION)
    resto = [p for p in paginas if p["path"] not in usadas]
    if resto:
        grupos.append(("Más", "", resto))
    return grupos


def recorrido(paginas):
    """Las paginas en el orden en que se recorre el dashboard, como una presentacion: el inicio y luego cada seccion."""
    inicio = [p for p in paginas if p["path"] == "/"]
    return inicio + [p for _titulo, _descripcion, grupo in agrupar(paginas) for p in grupo]


# ---------------------------------------------------------------- documentacion que respalda cada pagina (14-nov-2026)
# Cada pagina del dashboard es la version resumida, para el hospital, de una parte de docs/documento_final.md (la pagina
# /documentacion lo muestra completo). main.py pone al pie de cada pagina el enlace a su seccion.
CAPITULOS = {1: "Resumen ejecutivo", 2: "El reto y qué abordamos", 3: "Los datos y su calidad", 4: "Cómo fluye el paciente (componente 1)",
             5: "El cuello de botella y sus factores (componente 2)", 6: "Modelos, predicción y simulación (componente 3)",
             7: "Recomendaciones (componente 4)", 8: "El dashboard", 9: "Limitaciones", 10: "Trabajo en curso y futuro", 11: "Anexos"}
# ruta -> (capitulo, subseccion o tema, que se encuentra alli)
DOCUMENTACION = {
    "/resumen": (1, "Resumen ejecutivo", "los ocho hallazgos y lo que se propone, con sus cifras"),
    "/datos": (3, "3.1 a 3.8", "la base, cómo se extrajeron los datos, tabla por tabla, la exploración y la limpieza paso a paso, las variables construidas y las herramientas"),
    "/demanda": (4, "Cómo fluye el paciente", "llegadas por hora y por día, el recorrido, la estancia y los reingresos"),
    "/ocupacion": (5, "5.5 La saturación y la ocupación", "por qué sube la ocupación, la ley de Little y el exceso sobre las 106 camas"),
    "/espera": (5, "5.1 a 5.3 La espera de cama", "la definición de cuello de botella, el exceso y por qué empeoran los peores casos"),
    "/comparar": (6, "6.7 Diagnóstico repetible del cuello de botella", "cómo se compara el cuello de botella entre periodos"),
    "/altas": (5, "5.4 La hora del día", "las altas tardías, las dos olas de asignación y el límite de proceso"),
    "/factores": (5, "5.7 Factores de la espera", "cuánto explica cada factor y el modelo explicativo"),
    "/estancia": (5, "5.7 Estancia larga", "por qué subió la estancia y qué comparten las estancias largas"),
    "/diagnosticos": (5, "5.7 Diagnóstico", "espera y estancia por grupo de diagnóstico y sus límites"),
    "/perfiles": (5, "5.7 Quién es el paciente", "los perfiles, la brecha por sexo y la carga del momento"),
    "/pronostico": (6, "6.1 Pronóstico de demanda", "el modelo, su error por horizonte y la forma del año"),
    "/estacionalidad": (6, "6.1 La forma del año", "de dónde salen las curvas del año y cuánto mejoran el pronóstico"),
    "/alertas": (6, "6.2 Alertas", "las alertas, cómo se probaron, qué tanto aciertan y qué recomendación dispara cada una"),
    "/atipicos": (6, "6.3 Días atípicos", "cómo se detectan y qué dicen del problema de la espera"),
    "/paciente": (6, "6.4 Estimador de la espera de cada paciente", "qué usa, cómo se validó y sus límites"),
    "/camas": (6, "6.5 Simulación Monte Carlo de camas", "cómo funciona, su validación, los escenarios y la curva de capacidad"),
    "/periodo": (6, "6.7 Diagnóstico repetible del cuello de botella", "el diagnóstico de cualquier periodo comparado con una referencia: dónde está el cuello, qué se dispara y qué comparten las esperas largas"),
    "/simulador": (6, "6.9 Simulador integral", "el motor de agentes, su validación, las palancas, las alertas con su recomendación y la operación óptima"),
    "/recomendaciones": (7, "Recomendaciones", "las siete acciones con su evidencia, su firmeza y lo que no recomendamos"),
}


def slug_seccion(titulo):
    """El mismo ancla que pages/documentacion_cap.py da a cada subseccion del documento final."""
    t = re.sub(r"[^\w\s-]", "", titulo.lower(), flags=re.UNICODE)
    return "sec-" + re.sub(r"\s+", "-", t.strip())[:60]


def _titulos_h3():
    """Titulos de nivel 3 (### ...) del documento final, para apuntar el pie de cada pagina a su subseccion."""
    from pathlib import Path
    doc = Path(__file__).resolve().parent.parent / "docs" / "documento_final.md"
    try:
        return re.findall(r"^### (.+)$", doc.read_text(encoding="utf-8"), flags=re.M)
    except OSError:
        return []


def documentacion_de(ruta):
    """(capitulo, subseccion, descripcion, href) de la parte del documento final que respalda la pagina, o None.
    El enlace abre el capitulo (/documentacion/6) y baja a la subseccion cuyo numero empieza el texto de DOCUMENTACION (p. ej. «6.1»)."""
    if ruta not in DOCUMENTACION:
        return None
    cap, sub, desc = DOCUMENTACION[ruta]
    href = f"/documentacion/{cap}"
    m = re.match(r"(\d+\.\d+)", sub)
    if m:
        t = next((t for t in _titulos_h3() if t.startswith(m.group(1) + " ")), None)
        if t:
            href += "#" + slug_seccion(t)
    return cap, sub, desc, href


def capitulos_documento():
    """[(numero, titulo)] de los capitulos, para el menu lateral."""
    return sorted(CAPITULOS.items())
