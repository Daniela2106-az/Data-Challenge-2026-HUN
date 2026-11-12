"""
dashboard/tema_graficos.py  -  tema compartido para los graficos Plotly del dashboard (12-nov-2026)
Hace que las figuras combinen con el diseno del dashboard y con el modo claro/oscuro:
  - fondo TRANSPARENTE (paper y plot), asi el grafico toma el color del contenedor detras (claro u oscuro)
    sin tener que redibujarlo;
  - tipografia Google Sans y colores de texto, titulo y rejilla segun el tema.
SOLO cambia estilos de layout: NO toca la interactividad (zoom, paneo, hover, barra de herramientas, seleccion),
que depende del parametro `config` de dcc.Graph, no de estos colores.
"""
FUENTE = "Google Sans, Roboto, 'Segoe UI', system-ui, sans-serif"

CLARO = dict(texto="#1a1d21", titulo="#0a2540", rejilla="#e6ecf3", linea="#d7dfe8")
OSCURO = dict(texto="#e6edf3", titulo="#e8eef4", rejilla="#27313c", linea="#3a4653")


def es_oscuro(tema):
    """`tema` es el dict guardado en dcc.Store(theme-store): {'theme': 'dark'|'light'} o None."""
    return bool(tema and tema.get("theme") == "dark")


def aplicar(fig, dark=False):
    """Aplica el tema del dashboard a una figura ya construida y la devuelve."""
    c = OSCURO if dark else CLARO
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FUENTE, color=c["texto"], size=13),
        title_font=dict(family=FUENTE, color=c["titulo"]),
        legend=dict(font=dict(color=c["texto"])),
        hoverlabel=dict(font=dict(family=FUENTE)),
    )
    fig.update_xaxes(gridcolor=c["rejilla"], linecolor=c["linea"], zerolinecolor=c["rejilla"])
    fig.update_yaxes(gridcolor=c["rejilla"], linecolor=c["linea"], zerolinecolor=c["rejilla"])
    return fig
