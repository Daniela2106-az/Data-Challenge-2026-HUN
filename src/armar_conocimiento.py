"""
armar_conocimiento.py  -  version 1 (19-nov-2026)
Arma docs/asistente/conocimiento.md: el UNICO documento que lee el asistente de preguntas del dashboard (dashboard/asistente.py).
Junta, sin reescribir nada y quitando lo que repite otro documento o sobra para responder preguntas (ver FUENTES), las partes de la documentacion del proyecto que responden preguntas:
  - docs/documento_final.md completo (el documento de punta a punta)
  - docs/HALLAZGOS.md: glosario, lo que no sabemos y preguntas frecuentes
  - docs/recomendaciones.md: lo que los datos NO respaldan y lo que quedo sin respuesta del HUN
  - docs/simulador_integral.md y docs/alertas_por_paciente.md completos (el simulador y sus alertas)
  - la lista de paginas del dashboard (de dashboard/pages/*.py), para que el asistente pueda decir donde ver cada cosa
Asi el asistente responde solo con lo que esta documentado, y cuando cambia el analisis basta con correr este script otra vez.

COMO CORRERLO  python src/armar_conocimiento.py
No lee datos de la base: solo documentos del repositorio.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
SALIDA = DOCS / "asistente" / "conocimiento.md"

# (archivo, secciones de nivel 2 que se toman o None para todo el archivo, encabezados que se QUITAN con todo lo que tienen debajo)
# Se quita lo que repite otro documento (el simulador esta completo en simulador_integral.md), lo que es de quien reproduce el trabajo y no de quien pregunta
# (columnas, variables, referencias, mapa de archivos) y la historia de como se construyo. Objetivo: unos 40 mil tokens, para que cada pregunta cueste poco.
FUENTES = [
    ("documento_final.md", None, ["## Índice", "### 3.2 ", "### 3.3 ", "### 3.7 ", "### 3.8 ", "### 6.9 ", "## 8. El dashboard", "## 10. Trabajo en curso", "### 11.2 ", "### 11.3 ", "### 11.4 "]),
    ("HALLAZGOS.md", ["1. Glosario", "7. Lo que no sabemos", "8. Preguntas frecuentes"], []),
    ("recomendaciones.md", ["4. Lo que los datos NO respaldan", "5. Qué quedó sin respuesta del HUN"], []),
    ("simulador_integral.md", None, ["## Evolución del 16-nov", "## Decisiones de diseño", "## Fases siguientes", "## Entregables", "## Alertas comprimidas y alertas por paciente"]),
    ("alertas_por_paciente.md", None, []),
]


def quitar(texto, titulos):
    """Quita los bloques que empiezan en un encabezado (cualquier nivel) que comienza por alguno de `titulos`, hasta el siguiente encabezado del mismo nivel o mayor."""
    if not titulos:
        return texto
    salida, nivel_saltado = [], None
    for linea in texto.split("\n"):
        m = re.match(r"^(#{1,6}) ", linea)
        if m:
            nivel = len(m.group(1))
            if nivel_saltado is not None and nivel <= nivel_saltado:
                nivel_saltado = None
            if nivel_saltado is None and any(linea.startswith(t) for t in titulos):
                nivel_saltado = nivel
        if nivel_saltado is None:
            salida.append(linea)
    return "\n".join(salida)


def secciones(texto, titulos):
    """Las secciones de nivel 2 ('## ...') cuyo titulo empieza por alguno de `titulos`, con todo lo que tienen debajo."""
    partes = re.split(r"(?m)^(?=## )", texto)
    return [p.rstrip() for p in partes if any(p.startswith("## " + t) for t in titulos)]


def bajar_niveles(texto):
    """Baja un nivel todos los encabezados, para que cada fuente quede debajo de su propio titulo de nivel 1."""
    return re.sub(r"(?m)^(#{1,5}) ", lambda m: "#" + m.group(1) + " ", texto)


def paginas():
    filas = []
    for p in sorted((RAIZ / "dashboard" / "pages").glob("*.py")):
        t = p.read_text(encoding="utf-8")
        m = re.search(r'register_page\([^)]*?path="([^"]+)"[^)]*?name="([^"]+)"', t, re.S)
        if m:
            filas.append(f"- **{m.group(2)}**: `{m.group(1)}`")
    return "\n".join(filas)


def guia():
    """Como esta organizado el dashboard (categorias del menu y sus paginas): para responder «como uso este dashboard» y «que miro primero»."""
    import sys
    sys.path.insert(0, str(RAIZ / "dashboard"))
    from navegacion import SECCIONES, SECCIONES_FUERA_DEL_MENU
    nombres = {}
    for linea in paginas().splitlines():
        m = re.match(r"- \*\*(.+?)\*\*: `(.+?)`", linea)
        if m:
            nombres[m.group(2)] = m.group(1)
    filas = ["## Cómo está organizado el dashboard",
             "El dashboard se abre en el asistente (la página de inicio), donde se pregunta en lenguaje natural; debajo hay una guía para explorar por categorías y un recorrido guiado que "
             "empieza en Resumen. Arriba del menú lateral hay un botón azul «Simular» (`/simular`, «¿Qué quieres hacer hoy?») que abre los módulos interactivos, "
             "cada uno con una breve descripción de lo que permite hacer. El menú lateral tiene estas categorías:"]
    for titulo, desc, rutas in SECCIONES:
        if titulo in SECCIONES_FUERA_DEL_MENU:
            filas.append(f"- **{titulo}** (no están en el menú: se abren con el botón «Simular»; {desc}): " + ", ".join(f"{nombres.get(r, r)} (`{r}`)" for r in rutas))
            continue
        filas.append(f"- **{titulo}** ({desc}): " + ", ".join(f"{nombres.get(r, r)} (`{r}`)" for r in rutas))
    filas.append("Para empezar: Resumen (el proyecto en una pantalla), luego Espera de cama y Ocupación de camas (el problema), Recomendaciones (qué hacer) y, para probar escenarios, el Simulador integral.")
    return "\n".join(filas)


def main():
    bloques = ["# Base de conocimiento del asistente (dashboard HUN)",
               "Este documento se arma solo con `src/armar_conocimiento.py` a partir de la documentación del proyecto. "
               "Es la única fuente del asistente de preguntas: lo que no esté aquí, el proyecto no lo sabe.",
               "## Páginas del dashboard\n" + paginas(), guia()]
    for archivo, titulos, quitados in FUENTES:
        texto = (DOCS / archivo).read_text(encoding="utf-8")
        cuerpo = texto if titulos is None else "\n\n".join(secciones(texto, titulos))
        if titulos is not None and len(secciones(texto, titulos)) != len(titulos):
            raise SystemExit(f"{archivo}: no se encontraron todas las secciones {titulos}")
        for q in quitados:
            if not re.search(r"(?m)^" + re.escape(q), cuerpo):
                raise SystemExit(f"{archivo}: no existe el encabezado que se iba a quitar: {q!r}")
        bloques.append(f"# Fuente: docs/{archivo}\n\n" + bajar_niveles(quitar(cuerpo, quitados)))
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text("\n\n".join(bloques) + "\n", encoding="utf-8")
    print(f"{SALIDA.relative_to(RAIZ)}: {SALIDA.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
