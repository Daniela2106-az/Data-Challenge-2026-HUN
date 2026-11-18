"""
exportar_documento_pdf.py  -  genera docs/documento_final.pdf desde docs/documento_final.md (17-nov-2026)

El boton «Descargar el documento en PDF» de la pagina de Documentacion del dashboard entrega este archivo. Hay que volver a correr este script
cada vez que cambie docs/documento_final.md.
COMO CORRERLO  python3 src/exportar_documento_pdf.py      (necesita `pip install markdown` y Google Chrome instalado)
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

RAIZ = Path(__file__).resolve().parent.parent
CHROME = {"darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "linux": "google-chrome", "win32": r"C:\Program Files\Google\Chrome\Application\chrome.exe"}
CSS = ("@page{size:A4;margin:16mm}body{font-family:Helvetica,Arial,sans-serif;font-size:10.5pt;line-height:1.45;color:#1a1d21}h1,h2,h3{color:#0a4f8f;page-break-after:avoid}"
       "h2{border-bottom:2px solid #0071bc;padding-bottom:3px;margin-top:22px}table{border-collapse:collapse;width:100%;font-size:9pt;margin:8px 0}tr{page-break-inside:avoid}"
       "th,td{border:1px solid #c9d3de;padding:4px 6px;vertical-align:top}th{background:#eaf3fb}img{max-width:100%}code{font-size:9pt;background:#f1f4f8;padding:0 3px}"
       "blockquote{border-left:4px solid #0071bc;margin:8px 0;padding:2px 12px;background:#f4f8fc}")

texto = (RAIZ / "docs" / "documento_final.md").read_text(encoding="utf-8")
def lista_con_espacio(t):
    """Markdown exige una linea en blanco antes de una lista; el documento no siempre la deja (el dashboard si la lee bien), asi que aqui se agrega."""
    salida, prev = [], ""
    for ln in t.split("\n"):
        es_item = bool(re.match(r"\s*(?:[-*]|\d+\.)\s", ln))
        if es_item and prev.strip() and not re.match(r"\s*(?:[-*]|\d+\.)\s", prev) and not prev.startswith(("|", " ", "\t")) and not prev.lstrip().startswith(">"):
            salida.append("")
        salida.append(ln)
        prev = ln
    return "\n".join(salida)


texto = lista_con_espacio(texto)
texto = re.sub(r"\]\(\.\./(resultados/[^)]+)\)", lambda m: f"](file://{RAIZ}/{m.group(1)})", texto)       # las figuras se leen con su ruta completa
html = markdown.markdown(texto, extensions=["tables", "fenced_code", "toc", "sane_lists"])
with tempfile.TemporaryDirectory() as tmp:
    pagina = Path(tmp) / "documento.html"
    pagina.write_text(f"<!doctype html><meta charset='utf-8'><style>{CSS}</style>{html}", encoding="utf-8")
    salida = RAIZ / "docs" / "documento_final.pdf"
    subprocess.run([CHROME.get(sys.platform, "google-chrome"), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={salida}", pagina.as_uri()], check=True)
print(f"{salida.relative_to(RAIZ)}: {salida.stat().st_size // 1024} KB")
