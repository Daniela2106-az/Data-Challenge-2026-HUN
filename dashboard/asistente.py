"""
dashboard/asistente.py  -  version 1 (19-nov-2026): el asistente de preguntas del dashboard (pagina /preguntas y chat flotante)

Responde preguntas en lenguaje natural SOLO con lo que dice docs/asistente/conocimiento.md (lo arma src/armar_conocimiento.py a partir de la
documentacion del proyecto). Usa la API de Anthropic con el modelo Claude Sonnet 5.5. No envia datos de pacientes: solo ese documento, la pregunta
y, si la hay, el texto que el usuario selecciono en la pantalla.

CONFIGURACION (variables de entorno; en Render: Environment)
  ANTHROPIC_API_KEY   la clave de la API. Nunca va en el repositorio.
  ASISTENTE_HASTA     ultimo dia de servicio es el dia ANTERIOR a esta fecha (por defecto 2026-12-01, hora de Colombia): desde ese dia el
                      asistente no llama a la API y lo dice en pantalla.

COSTO  El documento (~45 mil tokens) va en el prompt del sistema con cache de 5 minutos (la escritura de la cache de 5 min cuesta menos que la de 1 hora): la primera
       pregunta tras 5 minutos sin uso paga el documento completo y las que llegan dentro de esos 5 minutos lo leen casi gratis. Ademas hay limites de uso (LIMITE_*), que se cuentan en la memoria del servidor: se
       reinician si el servidor se reinicia y, si hubiera varios procesos, cada uno lleva su cuenta. El tope de gasto real es el del workspace
       de la clave en la consola de Anthropic.
"""
import datetime as dt
import json
import os
import threading
from pathlib import Path
from zoneinfo import ZoneInfo



def _cargar_env_local():
    """En el computador de desarrollo la clave puede ir en un archivo .env en la raiz del proyecto (esta en .gitignore). En Render no hace falta:
    la variable ya existe en el entorno y no se pisa."""
    ruta = Path(__file__).resolve().parent.parent / ".env"
    try:
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except OSError:
        pass


_cargar_env_local()
MODELO = "claude-sonnet-5-5"
HASTA_POR_DEFECTO = "2026-12-01"
ZONA = ZoneInfo("America/Bogota")
LIMITE_PERSONA_DIA = 10          # preguntas por persona (navegador o IP) al dia
LIMITE_TOTAL_DIA = 60            # preguntas de todo el sitio al dia
MAX_CARACTERES = 500             # largo maximo de la pregunta
MAX_CITA = 1500                  # largo maximo del texto seleccionado que acompana la pregunta
MAX_TURNOS = 6                   # turnos anteriores de la conversacion que se reenvian
MAX_TOKENS = 2500                # largo maximo de la respuesta (el JSON de la tarjeta)

CONOCIMIENTO = Path(__file__).resolve().parent.parent / "docs" / "asistente" / "conocimiento.md"
try:
    _TEXTO = CONOCIMIENTO.read_text(encoding="utf-8")
except OSError:
    _TEXTO = ""

def _paginas():
    """{ruta: nombre} de las paginas del dashboard (de dashboard/pages/*.py): las unicas que el asistente puede senalar."""
    import re
    d = {}
    for f in sorted((Path(__file__).resolve().parent / "pages").glob("*.py")):
        m = re.search(r'register_page\([^)]*?path="([^"]+)"[^)]*?name="([^"]+)"', f.read_text(encoding="utf-8"), re.S)
        if m:
            d[m.group(1)] = m.group(2)
    return d


PAGINAS = {r: n for r, n in _paginas().items() if r != "/"}      # el asistente no se senala a si mismo (es la pagina de inicio)
ICONOS = ["reloj", "tendencia", "embudo", "gente", "sol", "cama", "calendario", "frasco", "campana", "grafico", "persona", "alerta", "hospital", "pulso"]
TONOS = ["neutro", "bueno", "malo", "info"]

# Forma de cada respuesta: la interfaz la dibuja como una tarjeta (titulo, cifras destacadas, barras, texto, fuente y preguntas de seguimiento).
ESQUEMA = {
    "type": "object",
    "properties": {
        "en_alcance": {"type": "boolean", "description": "false si la pregunta no se puede responder con la base de conocimiento"},
        "titulo": {"type": "string", "description": "La respuesta en una frase corta y afirmativa, con la cifra clave si la hay"},
        "resaltado": {"type": "string", "description": "Un fragmento EXACTO del titulo para destacar en azul, o cadena vacia"},
        "icono": {"type": "string", "enum": ICONOS},
        "tarjetas": {"type": "array", "description": "0 a 3 cifras destacadas, tomadas tal cual de la base de conocimiento",
                     "items": {"type": "object", "properties": {
                         "valor": {"type": "string", "description": "La cifra con su unidad, por ejemplo '18,6 h' o '62,7 %'"},
                         "etiqueta": {"type": "string", "description": "Que significa la cifra, con su periodo, en pocas palabras"},
                         "tono": {"type": "string", "enum": TONOS}, "icono": {"type": "string", "enum": ICONOS}},
                         "required": ["valor", "etiqueta", "tono", "icono"], "additionalProperties": False}},
        "barras_titulo": {"type": "string", "description": "Titulo de la comparacion en barras, o cadena vacia si no hay"},
        "barras": {"type": "array", "description": "0 a 4 filas para comparar valores de la misma unidad (por ejemplo dos anios); vacio si no hay comparacion",
                   "items": {"type": "object", "properties": {
                       "etiqueta": {"type": "string"}, "valor": {"type": "number", "description": "El numero de la fila, sin unidad"},
                       "texto": {"type": "string", "description": "El valor con su unidad, por ejemplo '61,6 h'"}, "tono": {"type": "string", "enum": TONOS}},
                       "required": ["etiqueta", "valor", "texto", "tono"], "additionalProperties": False}},
        "texto": {"type": "string", "description": "Explicacion breve en Markdown (1 a 4 frases) con el matiz que acompana a la cifra; puede ser vacia"},
        "nota": {"type": "string", "description": "Una advertencia corta (maximo 15 palabras) si la cifra es una asociacion, un escenario, esta pendiente de validar o tiene un limite importante; si no, cadena vacia"},
        "paginas": {"type": "array", "description": "De 0 a 3 paginas del dashboard donde se ve lo que respondes, de la mas relevante a la menos; vacio si no aplica",
                    "items": {"type": "string", "enum": sorted(PAGINAS)}},
        "seguimiento": {"type": "array", "description": "Exactamente 2 preguntas cortas que el usuario podria hacer a continuacion, respondibles con la base de conocimiento",
                        "items": {"type": "string"}},
    },
    "required": ["en_alcance", "titulo", "resaltado", "icono", "tarjetas", "barras_titulo", "barras", "texto", "nota", "paginas", "seguimiento"],
    "additionalProperties": False,
}

INSTRUCCIONES = """Eres el Asistente de flujo HUN, del dashboard del Data Challenge HUN 2026: un análisis del flujo de pacientes, la espera de cama y la ocupación del Hospital Universidad del Norte (Barranquilla), hecho por estudiantes de Ciencia de Datos de la Universidad del Norte.

El dashboard se abre en tu página: tú eres la página de inicio. Si preguntan cómo usar el dashboard o qué mirar primero, oriéntalos con la guía de la base de conocimiento.

Responde SOLO con lo que dice la base de conocimiento que sigue. Reglas:
- Si la respuesta no está en la base de conocimiento: en_alcance false, titulo «Eso no está en el análisis del proyecto», en texto explica en una o dos frases qué sí se sabe de algo cercano, y deja tarjetas y barras vacías. No completes con conocimiento general, no inventes cifras y no hagas cálculos nuevos que el proyecto no hizo.
- Usa las cifras tal como aparecen, con sus unidades y su periodo. Si el proyecto dice que algo es una asociación o un escenario, no lo presentes como causa o predicción, y dilo en texto.
- titulo: la respuesta en una frase corta y afirmativa («El caso típico igual, pero la cola larga creció»). resaltado: el fragmento del título que más importa, copiado exacto, o vacío.
- tarjetas: de 0 a 3 cifras clave, en español con coma decimal. Tono: «malo» para lo que empeora o preocupa, «bueno» para lo que mejora o es favorable, «info» o «neutro» para el resto. Si la respuesta no tiene cifras, no pongas tarjetas.
- barras: solo cuando comparas valores de la misma unidad (años, grupos, franjas); si no, vacío. valor es solo el número; texto es el valor con su unidad.
- texto: Markdown breve, solo lo que añade (matiz, qué significa). No repitas las tarjetas. Puedes dejarlo vacío.
- nota: una advertencia corta (máximo 15 palabras) cuando la cifra es una asociación, un escenario, algo pendiente de validar o tiene un límite importante; si no hay nada que advertir, vacía.
- paginas: de 0 a 3 páginas del dashboard donde el usuario puede ver lo que respondes (la ruta exacta de la lista de páginas de la base de conocimiento), de la más relevante a la menos. No pongas la sección del documento ni la ruta en el texto: la interfaz muestra la página como un botón. Si no hay una página que lo muestre, déjala vacía.
- seguimiento: exactamente 2 preguntas cortas y distintas que se puedan responder con la base de conocimiento.
- Escribe en español claro, sin jerga técnica: quien pregunta puede ser personal del hospital o un jurado.
- No des información de pacientes individuales: el proyecto solo publica cifras agregadas.
- Si piden algo que no es sobre este proyecto (otros temas, código, tareas), en_alcance false y explica amablemente que solo respondes sobre este análisis.
- Si el usuario cita un texto de la pantalla, responde sobre ese texto usando la base de conocimiento.
Responde únicamente con el objeto JSON de la respuesta."""

_lock = threading.Lock()
_conteo = {"dia": None, "total": 0, "persona": {}}
_cliente = None


def _hoy():
    return dt.datetime.now(ZONA).date()


def vence():
    """Fecha (date) desde la que el asistente deja de funcionar."""
    try:
        return dt.date.fromisoformat(os.environ.get("ASISTENTE_HASTA", HASTA_POR_DEFECTO).strip())
    except ValueError:
        return dt.date.fromisoformat(HASTA_POR_DEFECTO)


def estado():
    """(disponible, mensaje para el usuario si no lo esta)."""
    if _hoy() >= vence():
        ultimo = vence() - dt.timedelta(days=1)
        return False, f"El asistente estuvo disponible hasta el {ultimo.day} de {_MESES[ultimo.month - 1]} de {ultimo.year}."
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False, "El asistente no está configurado en este servidor (falta la clave de la API)."
    if not _TEXTO:
        return False, "El asistente no encuentra su base de conocimiento (docs/asistente/conocimiento.md)."
    return True, ""


_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def restantes(persona):
    """Preguntas que le quedan hoy a esta persona (y al sitio)."""
    with _lock:
        _al_dia()
        usadas = _conteo["persona"].get(persona, 0)
        return max(0, min(LIMITE_PERSONA_DIA - usadas, LIMITE_TOTAL_DIA - _conteo["total"]))


def _al_dia():
    if _conteo["dia"] != _hoy():
        _conteo.update(dia=_hoy(), total=0, persona={})


def _reservar(persona):
    with _lock:
        _al_dia()
        if _conteo["total"] >= LIMITE_TOTAL_DIA:
            return "Hoy ya se respondieron todas las preguntas disponibles para el sitio. Vuelve mañana."
        if _conteo["persona"].get(persona, 0) >= LIMITE_PERSONA_DIA:
            return f"Ya hiciste las {LIMITE_PERSONA_DIA} preguntas disponibles por hoy. Vuelve mañana."
        _conteo["total"] += 1
        _conteo["persona"][persona] = _conteo["persona"].get(persona, 0) + 1
        return None


def _devolver(persona):
    """Si la llamada fallo, la pregunta no cuenta."""
    with _lock:
        _conteo["total"] = max(0, _conteo["total"] - 1)
        if _conteo["persona"].get(persona):
            _conteo["persona"][persona] -= 1


def _client():
    global _cliente
    if _cliente is None:
        import anthropic
        _cliente = anthropic.Anthropic(max_retries=2, timeout=90.0)
    return _cliente


def _contenido_usuario(pregunta, cita):
    if cita:
        return f"Texto que seleccioné en la pantalla del dashboard:\n«{cita}»\n\nMi pregunta: {pregunta}"
    return pregunta


def _json_de_texto(t):
    """Saca el objeto JSON de un texto (por si el modelo lo envolvio en algo mas)."""
    t = (t or "").strip()
    try:
        return json.loads(t)
    except ValueError:
        i, j = t.find("{"), t.rfind("}")
        if 0 <= i < j:
            try:
                return json.loads(t[i:j + 1])
            except ValueError:
                return None
    return None


def _limpiar(d):
    """Deja la respuesta del modelo en la forma segura que dibuja la interfaz (tipos, largos e iconos validos)."""
    def cad(x, n=400):
        return str(x or "").strip()[:n]
    def ico(x):
        return x if x in ICONOS else "pulso"
    def tono(x):
        return x if x in TONOS else "neutro"
    out = {"en_alcance": bool(d.get("en_alcance", True)), "titulo": cad(d.get("titulo"), 200), "resaltado": cad(d.get("resaltado"), 200), "icono": ico(d.get("icono")),
           "tarjetas": [], "barras_titulo": cad(d.get("barras_titulo"), 120), "barras": [], "texto": cad(d.get("texto"), 1800), "nota": cad(d.get("nota"), 160), "paginas": [], "seguimiento": []}
    for r in (d.get("paginas") or [])[:3]:
        if r in PAGINAS and r not in out["paginas"]:
            out["paginas"].append(r)
    for t in (d.get("tarjetas") or [])[:3]:
        if isinstance(t, dict) and t.get("valor"):
            out["tarjetas"].append({"valor": cad(t.get("valor"), 30), "etiqueta": cad(t.get("etiqueta"), 120), "tono": tono(t.get("tono")), "icono": ico(t.get("icono"))})
    for b in (d.get("barras") or [])[:4]:
        try:
            out["barras"].append({"etiqueta": cad(b.get("etiqueta"), 40), "valor": max(0.0, float(b.get("valor"))), "texto": cad(b.get("texto"), 30), "tono": tono(b.get("tono"))})
        except (TypeError, ValueError, AttributeError):
            pass
    out["seguimiento"] = [cad(q, 90) for q in (d.get("seguimiento") or [])[:2] if q]
    if not out["titulo"]:
        out["titulo"] = "Respuesta"
    return out


def _error(texto):
    return {"en_alcance": False, "titulo": "", "resaltado": "", "icono": "alerta", "tarjetas": [], "barras_titulo": "", "barras": [], "texto": texto, "nota": "", "paginas": [], "seguimiento": [], "error": True}


def _a_texto_de_historial(turno):
    d = turno.get("datos") or {}
    return json.dumps({k: d.get(k) for k in ("en_alcance", "titulo", "resaltado", "icono", "tarjetas", "barras_titulo", "barras", "texto", "nota", "paginas", "seguimiento")}, ensure_ascii=False)


def responder(pregunta, historial=None, cita=None, persona="anonimo"):
    """Responde una pregunta. `historial` = turnos anteriores: {"rol": "usuario", "texto", "cita"} y {"rol": "asistente", "datos": <respuesta>, "ok"}.
    Devuelve (respuesta como dict, ok). Si no se pudo responder, ok es False y la respuesta trae "error": True con el motivo en `texto`."""
    ok, motivo = estado()
    if not ok:
        return _error(motivo), False
    pregunta = (pregunta or "").strip()
    cita = (cita or "").strip()[:MAX_CITA] or None
    if not pregunta:
        return _error("Escribe una pregunta."), False
    if len(pregunta) > MAX_CARACTERES:
        return _error(f"La pregunta es muy larga: máximo {MAX_CARACTERES} caracteres."), False
    bloqueo = _reservar(persona)
    if bloqueo:
        return _error(bloqueo), False

    mensajes = []
    for t in (historial or [])[-2 * MAX_TURNOS:]:
        if t.get("rol") == "usuario":
            mensajes.append({"role": "user", "content": _contenido_usuario(t.get("texto", ""), t.get("cita"))})
        elif t.get("rol") == "asistente" and t.get("ok") and t.get("datos") and mensajes and mensajes[-1]["role"] == "user":
            mensajes.append({"role": "assistant", "content": _a_texto_de_historial(t)})
    if mensajes and mensajes[-1]["role"] == "user":       # un turno sin respuesta: se descarta para que los roles alternen
        mensajes.pop()
    mensajes.append({"role": "user", "content": _contenido_usuario(pregunta, cita)})

    import anthropic
    sistema = [{"type": "text", "text": INSTRUCCIONES},
               {"type": "text", "text": "<base_de_conocimiento>\n" + _TEXTO + "\n</base_de_conocimiento>", "cache_control": {"type": "ephemeral"}}]
    try:
        try:
            r = _client().messages.create(model=MODELO, max_tokens=MAX_TOKENS, system=sistema, messages=mensajes,
                                          output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA}})
        except anthropic.BadRequestError as e:
            if "schema" not in str(e).lower() and "format" not in str(e).lower():
                raise
            print(f"[asistente] la API rechazo el esquema, se reintenta sin el: {e}", flush=True)           # el modelo igual recibe las instrucciones de la forma
            r = _client().messages.create(model=MODELO, max_tokens=MAX_TOKENS, system=sistema, messages=mensajes, output_config={"effort": "low"})
    except anthropic.RateLimitError:
        _devolver(persona)
        return _error("El asistente está recibiendo muchas preguntas en este momento. Intenta de nuevo en un minuto."), False
    except anthropic.AuthenticationError:
        _devolver(persona)
        return _error("La clave de la API no es válida o ya fue revocada."), False
    except anthropic.APIStatusError as e:
        _devolver(persona)
        print(f"[asistente] error de la API: {e}", flush=True)
        if e.status_code in (402, 403) or "credit" in str(e).lower() or "limit" in str(e).lower():
            return _error("El asistente alcanzó su límite de uso y ya no puede responder."), False
        return _error("El asistente no pudo responder en este momento. Intenta de nuevo más tarde."), False
    except anthropic.APIConnectionError:
        _devolver(persona)
        return _error("No hay conexión con el servicio del asistente. Intenta de nuevo más tarde."), False

    _registrar_uso(r)
    if r.stop_reason == "refusal":
        return _error("No puedo responder esa pregunta. Pregunta sobre el análisis del flujo de pacientes del HUN."), False
    texto = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
    d = _json_de_texto(texto) if r.stop_reason != "max_tokens" else None
    if isinstance(d, dict):
        return _limpiar(d), True
    if texto:                                              # el modelo no devolvio la forma esperada: se muestra como texto simple
        return _limpiar({"en_alcance": True, "titulo": "Respuesta", "texto": texto + ("\n\n*(La respuesta quedó cortada.)*" if r.stop_reason == "max_tokens" else "")}), True
    return _error("No obtuve una respuesta. Intenta reformular la pregunta."), False


def _registrar_uso(r):
    """Deja en el log del servidor los tokens de cada respuesta (para vigilar el costo)."""
    try:
        u = r.usage
        print(f"[asistente] entrada {u.input_tokens} · caché leída {u.cache_read_input_tokens} · caché escrita {u.cache_creation_input_tokens} · salida {u.output_tokens}", flush=True)
    except Exception:
        pass
