"""
dashboard/pages/documentacion_cap.py  -  un capitulo del documento final por pagina (14-nov-2026)
Ruta /documentacion/<n>. Muestra el capitulo con su introduccion y cada subseccion en una tarjeta, con una fila de accesos a las
subsecciones arriba y los botones capitulo anterior / siguiente. El pie de cada pagina del dashboard enlaza aqui (con el ancla de la subseccion).
"""
import sys
from pathlib import Path

import dash
from dash import dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from documento import capitulos, render, slug, titulo_limpio  # noqa: E402

dash.register_page(__name__, path_template="/documentacion/<cap>", name="Documentación", title="Documentación - HUN")


def _md(texto):
    return dcc.Markdown(texto, className="doc-md", link_target="_blank")


def layout(cap=None, **_):
    caps = capitulos()
    try:
        n = int(cap)
    except (TypeError, ValueError):
        n = 0
    if n not in caps:
        return html.Div(className="page-container", children=[html.H2("Capítulo no encontrado"), dcc.Link("Volver a la documentación", href="/documentacion")])
    c = caps[n]
    chips = [html.A(titulo_limpio(t), href="#" + slug(t), className="doc-chip", title=t.replace("`", "")) for t, _ in c["subs"]]
    cuerpo = []
    if c["intro"]:
        cuerpo.append(html.Section(className="doc-sub doc-sub--intro", children=render(c["intro"])))
    for t, texto in c["subs"]:
        cuerpo.append(html.Section(id=slug(t), className="doc-sub", children=[html.H3(titulo_limpio(t), className="doc-sub__titulo"), *render(texto)]))

    def boton(k, d, clase):
        return dcc.Link(href=f"/documentacion/{k}", className="paso__btn " + clase, children=[
            html.Span(d, className="paso__dir"), html.Span(caps[k]["titulo"], className="paso__nombre")]) if k in caps else html.Span()

    return html.Div(className="page-container doc-cap", children=[
        html.Div(className="doc-cap__head", children=[
            dcc.Link("← Documentación", href="/documentacion", className="doc-cap__volver"),
            html.Div(f"Capítulo {n}", className="portada__eyebrow doc-cap__eyebrow"), html.H2(c["titulo"], className="doc-cap__titulo"),
            html.Div(chips, className="doc-chips") if chips else None]),
        *cuerpo,
        html.Nav(className="paso", children=[boton(n - 1, "← Capítulo anterior", "paso__btn--ant"), html.Span(),
                                              boton(n + 1, "Capítulo siguiente →", "paso__btn--sig")])])
