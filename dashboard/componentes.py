"""
dashboard/componentes.py  -  version 1 (9-nov-2026)
Piezas que se repiten en todas las paginas del dashboard (docs/estructura_dashboard.md, seccion 4): colores, tarjeta de cifra y formato de numeros.
"""
from dash import html

GRIS, AZUL, ROJO, NARANJA = "#6b6b6b", "#2a6fb0", "#c0392b", "#eb6834"


def tarjeta(titulo, valor, detalle=""):
    """Cuadro con una cifra grande, su titulo y una linea de detalle."""
    return html.Div([html.Div(titulo, style={"fontSize": "12px", "color": GRIS}),
                     html.Div(valor, style={"fontSize": "24px", "fontWeight": 700}),
                     html.Div(detalle, style={"fontSize": "12px", "color": GRIS})],
                    style={"border": "1px solid #ddd", "borderRadius": "8px", "padding": "10px 14px", "minWidth": "190px"})


def coma(x, decimales=1):
    """Numero con coma decimal, como se escribe en Colombia."""
    return f"{x:.{decimales}f}".replace(".", ",")
