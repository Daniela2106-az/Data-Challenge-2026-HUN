"""
dashboard/documento.py  -  lectura del documento final por capitulos y subsecciones (14-nov-2026)
Parte docs/documento_final.md en capitulos (## N. ...) y cada capitulo en subsecciones (### ...). Las usan pages/documentacion.py (indice)
y pages/documentacion_cap.py (un capitulo por pagina, con sus capitulos en el menu lateral).
"""
import re
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "documento_final.md"


def slug(texto):
    t = re.sub(r"[^\w\s-]", "", texto.lower(), flags=re.UNICODE)
    return "sec-" + re.sub(r"\s+", "-", t.strip())[:60]


def capitulos():
    """{numero: {"titulo", "intro", "subs": [(titulo, cuerpo)]}} del documento final."""
    if not DOC.exists():
        return {}
    texto = DOC.read_text(encoding="utf-8").replace("](../resultados/graficos/", "](/graficos/")
    salida = {}
    for parte in re.split(r"^## ", texto, flags=re.M)[1:]:
        titulo, _, cuerpo = parte.partition("\n")
        m = re.match(r"(\d+)\.\s*(.+)", titulo.strip())
        if not m:
            continue
        cuerpo = re.sub(r"\n---\s*$", "\n", cuerpo.strip())
        partes = re.split(r"^### ", cuerpo, flags=re.M)
        subs = []
        for p in partes[1:]:
            t, _, c = p.partition("\n")
            subs.append((t.strip(), re.sub(r"\n---\s*$", "\n", c.strip())))
        salida[int(m.group(1))] = {"titulo": m.group(2).strip(), "intro": partes[0].strip(), "subs": subs}
    return salida


def referencias(caps):
    n = 0
    for t, c in caps.get(11, {}).get("subs", []):
        if t.startswith("11.4"):
            n = len(re.findall(r"^\d+\. ", c, flags=re.M))
    return n


def titulo_limpio(titulo):
    """Titulo de subseccion sin el numero, sin el codigo entre comillas y sin los archivos entre parentesis: «6.1 Pronóstico de demanda (`src/...`)» -> «Pronóstico de demanda»."""
    t = re.sub(r"^\d+(\.\d+)*\.?\s+", "", titulo.replace("`", ""))
    return re.sub(r"\s*\(.*$", "", t).strip() or titulo


# ---------------------------------------------------------------- formato de cada subseccion
def _bloques(texto):
    """Parte el Markdown de una subseccion en bloques tipados: parrafo, lista, numerada, tabla, imagen, nota."""
    salida, actual, tipo = [], [], None

    def cerrar():
        nonlocal actual, tipo
        if actual:
            salida.append((tipo, "\n".join(actual)))
        actual, tipo = [], None

    for linea in texto.split("\n"):
        s = linea.strip()
        if not s:
            if tipo not in ("lista",):
                cerrar()
            else:
                actual.append("")                   # una lista puede tener lineas en blanco entre sus items
            continue
        nuevo = ("tabla" if s.startswith("|") else "imagen" if s.startswith("![") else "nota" if s.startswith(">") else
                 "lista" if s.startswith("- ") else "numerada" if re.match(r"\d+\.\s", s) else None)
        sangrada = linea.startswith(" ") and tipo in ("lista", "numerada")
        if nuevo and nuevo != tipo and not sangrada:
            cerrar()
            tipo = nuevo
        elif tipo is None:
            tipo = "parrafo"
        elif tipo in ("tabla", "imagen") and nuevo != tipo:
            cerrar()
            tipo = "parrafo"
        actual.append(linea)
    cerrar()
    # una lista que quedo con lineas en blanco al final se limpia
    return [(t, c.strip("\n")) for t, c in salida]


def _items_lista(bloque):
    items, cur = [], []
    for l in bloque.split("\n"):
        if l.startswith("- "):
            if cur:
                items.append(" ".join(x.strip() for x in cur if x.strip()))
            cur = [l[2:]]
        elif l.strip():
            cur.append(l)
    if cur:
        items.append(" ".join(x.strip() for x in cur if x.strip()))
    return items


def render(texto, con_lead=True):
    """Subseccion del documento con formato: la primera frase destacada, las listas con titulo en negrita como tarjetas, las tablas y
    figuras en su marco y las notas como recuadro. El resto va como Markdown normal."""
    from dash import dcc, html
    md = lambda t, cls="doc-md": dcc.Markdown(t, className=cls, link_target="_blank")    # noqa: E731
    hijos, lead_puesto = [], not con_lead
    bloques = _bloques(texto)
    i = 0
    while i < len(bloques):
        tipo, cuerpo = bloques[i]
        if tipo == "parrafo":
            hijos.append(md(cuerpo, "doc-md doc-lead") if not lead_puesto and len(cuerpo) < 700 else md(cuerpo))
            lead_puesto = True
        elif tipo == "lista":
            items = _items_lista(cuerpo)
            partes = [re.match(r"\*\*(.+?)\*\*\s*(.*)", it, flags=re.S) for it in items]
            if len(items) >= 2 and all(partes):
                tarjetas = []
                for m in partes:
                    titulo, resto = m.group(1).rstrip(":. "), m.group(2).lstrip(":. ")
                    tarjetas.append(html.Div(className="doc-hallazgo", children=[html.Div(titulo, className="doc-hallazgo__titulo"), md(resto, "doc-md doc-hallazgo__txt")]))
                hijos.append(html.Div(tarjetas, className="doc-hallazgos"))
            else:
                hijos.append(md(cuerpo))
        elif tipo == "numerada":
            items, cur = [], []
            for l in cuerpo.split("\n"):
                if re.match(r"\d+\.\s", l):
                    if cur:
                        items.append(" ".join(x.strip() for x in cur if x.strip()))
                    cur = [re.sub(r"^\d+\.\s*", "", l)]
                elif l.strip():
                    cur.append(l)
            if cur:
                items.append(" ".join(x.strip() for x in cur if x.strip()))
            partes = [re.match(r"\*\*(.+?)\*\*\s*(.*)", it, flags=re.S) for it in items]
            if len(items) >= 3 and all(partes):
                hijos.append(html.Div(className="doc-pasos", children=[html.Div(className="doc-paso", children=[
                    html.Div(str(k), className="doc-paso__num"),
                    html.Div([html.Div(m.group(1).rstrip(":. "), className="doc-paso__titulo"), md(m.group(2).lstrip(":. "), "doc-md doc-paso__txt")])])
                    for k, m in enumerate(partes, 1)]))
            else:
                hijos.append(md(cuerpo))
        elif tipo == "tabla":
            hijos.append(html.Div(md(cuerpo), className="doc-tabla"))
        elif tipo == "imagen":
            hijos.append(html.Div(md(cuerpo), className="doc-figura"))
        elif tipo == "nota":
            hijos.append(html.Div(md(re.sub(r"^>\s?", "", cuerpo, flags=re.M)), className="doc-nota"))
        else:
            hijos.append(md(cuerpo))
        i += 1
    return hijos
