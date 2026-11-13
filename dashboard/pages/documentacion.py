"""
dashboard/pages/documentacion.py  -  pagina «Documentación» (13-nov-2026)
Muestra el documento final del proyecto (docs/documento_final.md) dentro del dashboard, con un indice por secciones, sus tablas y
graficos, y un boton para descargar el PDF. Lee el Markdown al abrir la pagina, asi que cualquier cambio del documento aparece solo.

Las imagenes del documento apuntan a ../resultados/graficos/; aqui se sirven desde la ruta /graficos/ y el PDF desde
/documento_final.pdf (rutas registradas en dashboard/main.py). Solo se publican graficos y el documento: nada de datos por paciente.
"""
import re
from pathlib import Path

import dash
from dash import dcc, html

dash.register_page(__name__, path="/documentacion", name="Documentación", title="Documentación del proyecto - HUN", order=6)

DOC = Path(__file__).resolve().parents[2] / "docs" / "documento_final.md"


def _slug(texto):
    t = re.sub(r"[^\w\s-]", "", texto.lower(), flags=re.UNICODE)
    return "sec-" + re.sub(r"\s+", "-", t.strip())[:60]


def _secciones():
    """Parte el documento en secciones de nivel 2 (## ...), sin el titulo, el encabezado ni el indice escrito a mano."""
    texto = DOC.read_text(encoding="utf-8")
    texto = texto.replace("](../resultados/graficos/", "](/graficos/")
    partes = re.split(r"^## ", texto, flags=re.M)
    secciones = []
    for parte in partes[1:]:
        titulo, _, cuerpo = parte.partition("\n")
        titulo = titulo.strip()
        if titulo.lower().startswith("índice") or titulo.lower().startswith("flujo de pacientes"):
            continue
        cuerpo = re.sub(r"\n---\s*$", "\n", cuerpo.strip())
        secciones.append((titulo, cuerpo))
    return secciones


def layout():
    if not DOC.exists():
        return html.Div(className="page-container", children=[
            html.H2("Documentación"), html.P("No se encontró docs/documento_final.md.", style={"color": "#c0392b"})])
    secciones = _secciones()
    indice = html.Nav(className="doc-toc card", children=[
        html.Div("Contenido", className="rec-block__label"),
        html.Ol([html.Li(html.A(re.sub(r"^\d+\.\s*", "", t), href="#" + _slug(t))) for t, _ in secciones]),
    ])
    cuerpo = [html.Section(id=_slug(t), className="doc-section", children=[
        html.H3(t),
        dcc.Markdown(c, className="doc-md", link_target="_blank"),
    ]) for t, c in secciones]
    return html.Div(className="page-container", children=[
        html.H2("¿Por qué se espera tanto por una cama?"),
        html.P("El documento completo del proyecto: los datos y su calidad, cómo fluye el paciente, el cuello de botella, los modelos de "
               "predicción y simulación, las recomendaciones, las limitaciones y las referencias.", className="rec-lead"),
        html.A("Descargar el documento en PDF", href="/documento_final.pdf", className="btn-primary doc-pdf", download="documento_final_HUN.pdf"),
        html.Div(className="doc-layout", children=[indice, html.Div(cuerpo, className="doc-body")]),
    ])
