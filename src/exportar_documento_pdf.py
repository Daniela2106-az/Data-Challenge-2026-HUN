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
LOGO = RAIZ / "dashboard" / "assets" / "logo_hun.png"
FECHA = "17 de noviembre de 2026"
EQUIPO = [("Daniela Amaya", "Coordinación, datos y análisis"), ("Samuel Amador", "Estimador de tiempos, recomendaciones y dashboard"), ("Anthony Amaya", "Modelo explicativo y simulación de camas")]
CSS = ("@page{size:A4;margin:18mm 16mm 20mm 16mm;@bottom-right{content:'Página ' counter(page) ' de ' counter(pages);font:8.5pt Helvetica,Arial,sans-serif;color:#6b7785}"
       "@bottom-left{content:'Data Challenge HUN 2026 · Documentación del proyecto';font:8.5pt Helvetica,Arial,sans-serif;color:#6b7785}}"
       "@page:first{margin:0;@bottom-right{content:none}@bottom-left{content:none}}"
       "html,body{margin:0}body{font-family:Helvetica,Arial,sans-serif;font-size:10.5pt;line-height:1.5;color:#1a1d21}h2#indice{page-break-before:auto}"
       "h1,h2,h3{color:#0a4f8f;page-break-after:avoid}h2{font-size:19pt;border-bottom:2px solid #0071bc;padding-bottom:4px;margin-top:0;page-break-before:always}"
       "h3{font-size:13pt;margin-top:18px}table{border-collapse:collapse;width:100%;font-size:9pt;margin:8px 0}tr{page-break-inside:avoid}"
       "th,td{border:1px solid #c9d3de;padding:4px 6px;vertical-align:top}th{background:#eaf3fb}img{max-width:100%}code{font-size:9pt;background:#f1f4f8;padding:0 3px}"
       "blockquote{border-left:4px solid #0071bc;margin:8px 0;padding:2px 12px;background:#f4f8fc}"
       # portada
       ".portada{height:297mm;box-sizing:border-box;padding:22mm 24mm 26mm;display:flex;flex-direction:column;justify-content:space-between;page-break-after:always;"
       "background:linear-gradient(180deg,#0071bc 0,#0071bc 52%,#fff 52%)}.portada .logo{background:#fff;display:inline-block;padding:10px 16px;border-radius:8px}.portada .logo img{height:46px;display:block}"
       ".portada .tema{color:#fff;margin-top:22mm}.portada .kicker{font-size:11pt;letter-spacing:.2em;font-weight:700;opacity:.9}.portada .tipo{font-size:30pt;font-weight:800;margin:6px 0 14px;line-height:1.1}"
       ".portada .titulo{font-size:17pt;font-weight:600;line-height:1.3;max-width:150mm}.portada .sub{font-size:11.5pt;opacity:.92;margin-top:8px;max-width:150mm}"
       ".portada .bloque{color:#1a1d21}.portada h4{color:#0a4f8f;font-size:10pt;letter-spacing:.12em;text-transform:uppercase;margin:0 0 6px;border-bottom:1px solid #c9d3de;padding-bottom:4px}"
       ".portada table{border:none;font-size:11pt}.portada td{border:none;border-bottom:1px solid #eef1f5;padding:6px 4px}.portada td:first-child{font-weight:700;width:30%}"
       ".portada .pie{font-size:10pt;color:#44505e;display:flex;justify-content:space-between;margin-top:6mm}")


def portada():
    filas = "".join(f"<tr><td>{n}</td><td>{r}</td></tr>" for n, r in EQUIPO)
    logo = f"<div class='logo'><img src='{LOGO.as_uri()}'></div>" if LOGO.exists() else ""
    return (f"<section class='portada'><div>{logo}<div class='tema'><div class='kicker'>DATA CHALLENGE HUN 2026</div><div class='tipo'>Documentación del proyecto</div>"
            "<div class='titulo'>¿Por qué se espera tanto por una cama?</div>"
            "<div class='sub'>Flujo de pacientes, cuellos de botella y anticipación en el Hospital Universidad del Norte</div></div></div>"
            f"<div class='bloque'><h4>Equipo</h4><table>{filas}</table>"
            f"<div class='pie'><span>Hospital Universidad del Norte · Pregrado de Ciencia de Datos, Universidad del Norte</span><span>Versión del {FECHA}</span></div></div></section>")


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


texto = (RAIZ / "docs" / "documento_final.md").read_text(encoding="utf-8")
texto = lista_con_espacio(texto)
texto = texto[texto.index("> **Cómo leer este documento.**"):]       # la portada reemplaza el titulo y la lista de equipo del encabezado
texto = re.sub(r"\]\(\.\./(resultados/[^)]+)\)", lambda m: f"](file://{RAIZ}/{m.group(1)})", texto)       # las figuras se leen con su ruta completa
html = markdown.markdown(texto, extensions=["tables", "fenced_code", "toc", "sane_lists"])
with tempfile.TemporaryDirectory() as tmp:
    pagina = Path(tmp) / "documento.html"
    pagina.write_text(f"<!doctype html><meta charset='utf-8'><style>{CSS}</style>{portada()}{html}", encoding="utf-8")
    salida = RAIZ / "docs" / "documento_final.pdf"
    subprocess.run([CHROME.get(sys.platform, "google-chrome"), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={salida}", pagina.as_uri()], check=True)
print(f"{salida.relative_to(RAIZ)}: {salida.stat().st_size // 1024} KB")
