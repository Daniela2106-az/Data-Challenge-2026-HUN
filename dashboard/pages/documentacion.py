"""
dashboard/pages/documentacion.py  -  portada de «Documentación» (14-nov-2026)
Indice del documento final (docs/documento_final.md): una tarjeta por capitulo con sus subsecciones. Cada capitulo se abre en su propia
pagina (pages/documentacion_cap.py, ruta /documentacion/<n>) y los capitulos aparecen en el menu lateral, asi el indice no ocupa
espacio de la pantalla. Boton para descargar el PDF. La pagina lee el Markdown al abrirse: cualquier cambio del documento aparece solo.
"""
import sys
from pathlib import Path

import dash
from dash import dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import cifra, portada  # noqa: E402
from documento import DOC, capitulos, referencias, titulo_limpio  # noqa: E402

dash.register_page(__name__, path="/documentacion", name="Documentación", title="Documentación del proyecto - HUN", order=6)


def layout():
    if not DOC.exists():
        return html.Div(className="page-container", children=[html.H2("Documentación"), html.P("No se encontró docs/documento_final.md.")])
    caps = capitulos()
    tarjetas = []
    for n, c in sorted(caps.items()):
        subs = html.Ul([html.Li(titulo_limpio(t)) for t, _ in c["subs"]], className="doc-card__subs") if c["subs"] else None
        tarjetas.append(dcc.Link(href=f"/documentacion/{n}", className="doc-card", children=[
            html.Div(f"{n:02d}", className="doc-card__num"), html.Div(c["titulo"], className="doc-card__titulo"),
            subs, html.Div("Abrir capítulo →", className="doc-card__ir")]))
    return html.Div(className="page-container", children=[
        portada("Conclusiones · Documentación", "¿Por qué se espera tanto por una cama?",
                "El documento completo del proyecto, por capítulos: los datos y su calidad, cómo fluye el paciente, el cuello de botella, los modelos "
                "de predicción y simulación, las recomendaciones, las limitaciones y las referencias. Los capítulos también están en el menú de la izquierda.",
                [cifra(str(len(caps)), "capítulos, del reto a los anexos"), cifra("7", "recomendaciones para el hospital"),
                 cifra(str(referencias(caps)), "referencias, listadas en los anexos")],
                accion=html.A("Descargar el documento en PDF", href="/documento_final.pdf", className="doc-pdf", download="Documentacion_Data_Challenge_HUN_2026.pdf")),
        html.Div(className="doc-cards", children=tarjetas)])
