"""
dashboard/componentes.py  -  version 2 (13-nov-2026): piezas comunes de las paginas de Contexto y Resultados, en formato de presentacion
Cada pagina se lee como una diapositiva que cuenta una idea, no como un tablero de cifras sueltas:
  portada()   banda azul (la misma del inicio) con la seccion, la conclusion en grande, una frase y hasta tres cifras enormes
  lamina()    una idea por bloque: numero, titular (la afirmacion), una o dos frases y un dato a un lado; la grafica al otro
  hecho()     tarjeta de un dato con su explicacion, para los bloques sin grafica
  mensaje()   lo que significa para el hospital, destacado
  metodo()    como se calculo, que NO dice y la fuente, plegado al final (quien quiera el detalle lo abre)
El diseño es el del dashboard (assets/theme.css): mismos colores, tarjetas redondeadas y tipografia. No cambia las paginas que ya existian.

DATOS  Las paginas leen tablas AGREGADAS con leer(nombre). Se buscan, en orden, en: HUN_DASHBOARD (carpeta), /etc/secrets (archivos
       secretos del servicio donde se publique), HUN_PROCESADOS/dashboard (las arma dashboard/preparar_datos.py; por defecto
       datos/procesados/dashboard, fuera de git) y datos/tablas_dashboard (solo las tablas escritas a mano). Si falta una tabla, la
       pagina muestra un aviso en vez de tumbar el arranque.

COLORES  Los de las paginas que ya existian: azul = lo observado, naranja = referencia o escenario, pizarra = serie de contexto.
         Los tres se distinguen entre si con daltonismo y tienen contraste suficiente sobre el fondo claro y el oscuro.
"""
import os
import sys
from pathlib import Path

import pandas as pd
from dash import dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tema_graficos as tg  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
AZUL, NARANJA, PIZARRA = "#2a6fb0", "#eb6834", "#8a97a6"
TENUE = "rgba(127,140,155,0.38)"            # barras de contexto (lo que no es el punto de la grafica)
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


# ---------------------------------------------------------------- datos y formato de numeros
def _carpetas():
    c = [os.environ.get("HUN_DASHBOARD"), "/etc/secrets",
         Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados")) / "dashboard", RAIZ / "datos" / "tablas_dashboard"]
    return [Path(x) for x in c if x]


def leer(nombre, **kw):
    """Tabla agregada por nombre de archivo, o None si no esta en ninguna de las carpetas."""
    for d in _carpetas():
        try:
            if (d / nombre).exists():
                return pd.read_csv(d / nombre, **kw)
        except OSError:
            continue
    return None


def coma(x, decimales=1):
    """Numero con coma decimal y punto de miles, como se escribe en Colombia."""
    s = f"{x:,.{decimales}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def miles(n):
    return f"{int(n):,}".replace(",", ".")


def fecha_es(f, dia=False):
    """Fecha en español: «mar 2025», o «14 mar 2025» con dia=True."""
    return (f"{f.day} " if dia else "") + f"{MESES[f.month - 1]} {f.year}"


def por_mes(serie, minimo_dias=25):
    """Promedio por mes de una serie diaria, solo con los meses completos: un mes con menos de `minimo_dias` dias con dato
    (abril de 2026, que llega hasta el dia 9) no se dibuja, para que el ultimo punto no sea un promedio de pocos dias."""
    g = serie.resample("MS")
    return g.mean()[g.count() >= minimo_dias]


# ---------------------------------------------------------------- piezas de la pagina
def cifra(valor, etiqueta):
    """Cifra grande de la portada: el numero y, debajo, que es."""
    return html.Div(className="cifra", children=[html.Div(valor, className="cifra__num"), html.Div(etiqueta, className="cifra__lbl")])


def portada(seccion, titulo, bajada, cifras=None, id_cifras=None, accion=None):
    """Encabezado de la pagina, como el titulo de una diapositiva. `cifras`: lista de cifra(); `id_cifras`: si las llena un callback;
    `accion`: un boton o enlace debajo de las cifras."""
    extra = {"id": id_cifras} if id_cifras else {}
    return html.Section(className="portada", children=[
        html.Div(className="hero__heart"), html.Div(seccion, className="portada__eyebrow"),
        html.H2(titulo, className="portada__title"), html.P(bajada, className="portada__lead"),
        html.Div(cifras or [], className="portada__cifras", **extra),
        html.Div(accion, className="portada__accion") if accion is not None else None])


def filtro(id_, etiqueta, opciones, valor):
    """Control de opcion unica con forma de pildoras. `opciones`: textos, o pares (valor, texto)."""
    ops = [{"label": o, "value": o} if isinstance(o, str) else {"label": o[1], "value": o[0]} for o in opciones]
    return html.Div(className="filtro", children=[
        html.Div(etiqueta, className="filtro__label"),
        dcc.RadioItems(id=id_, options=ops, value=valor, className="pildoras", inline=True)])


def grafico(id_, alto=330):
    # responsive=True (16-nov-2026): deja que Plotly se reajuste solo cuando el contenedor cambia de ancho
    # (p. ej. al expandirse una lamina del acordeon, o en modo presentacion), sin tener que forzar un resize
    # manual desde JS.
    return dcc.Graph(id=id_, config={"displaylogo": False, "displayModeBar": False, "responsive": True},
                     style={"height": f"{alto}px"})


def dato(valor, texto):
    """Contenido del dato de una lamina (lo devuelven los callbacks cuando el dato cambia con los filtros)."""
    return [html.B(valor), html.Span(texto)]


def lamina(numero, titular, texto, *grafica, dato=None, id_dato=None, invertida=False, controles=None):
    """Una idea por bloque. `titular` es la afirmacion (un texto, o un html.Span con id si cambia con los filtros); `texto`, una o
    dos frases en Markdown; `dato`, un par (cifra, que es); `id_dato`, si lo llena un callback; `controles`, un filtro de esta grafica."""
    hijos_dato = [html.B(dato[0]), html.Span(dato[1])] if dato else []
    lado = [html.Div(f"{numero:02d}", className="lamina__num"), html.H3(titular, className="lamina__titular"),
            dcc.Markdown(texto, className="lamina__p"), controles,
            html.Div(hijos_dato, className="lamina__dato", **({"id": id_dato} if id_dato else {}))]
    return html.Section(className="card lamina" + (" lamina--inv" if invertida else ""), children=[
        html.Div([x for x in lado if x is not None], className="lamina__texto"), html.Div(list(grafica), className="lamina__grafica")])


def laminas_grupo(*lams):
    """Agrupa varias lamina() en una fila horizontal tipo acordeon (16-nov-2026, dashboard/assets/acordeon.js):
    colapsadas muestran solo su numero (la "espina"); se turnan para expandirse solas cada pocos segundos, o al
    pasar el mouse por encima -- las demas se contraen para darle a la activa el mayor ancho posible. No cambia
    lamina(): aqui solo se le agrega, por fuera, la espina que se ve colapsada y la clase que activa el acordeon,
    asi lamina() sigue sirviendo igual para una pagina que no use el acordeon."""
    hijos = []
    for lam in lams:
        numero_txt = lam.children[0].children[0].children   # el primer hijo de lamina__texto es siempre lamina__num
        espina = html.Div(html.Div(numero_txt, className="lamina__espina-num"), className="lamina__espina")
        lam.children = [espina] + list(lam.children)
        lam.className = (lam.className or "") + " lamina-acordeon"
        hijos.append(lam)
    return html.Div(className="laminas-row", children=hijos)


def bloque(titulo, bajada=""):
    """Titulo de un bloque sin grafica (va seguido de una fila de hecho())."""
    return html.Div([html.Div(titulo, className="bloque-titulo"), html.P(bajada, className="bloque-bajada")])


def hecho(numero, titulo, texto):
    """Tarjeta de un dato: el numero en grande, que es y una frase que lo explica."""
    return html.Div(className="hecho", children=[
        html.Div(numero, className="hecho__num"), html.Div(titulo, className="hecho__titulo"), html.P(texto, className="hecho__txt")])


def antes_despues(antes, despues, que):
    """Una cifra que cambia: la de antes tachada, la flecha y la nueva en grande."""
    return html.Div(className="ad", children=[
        html.Span(antes, className="ad__antes"), html.Span("→", className="ad__flecha"), html.Span(despues, className="ad__despues"),
        html.Span(que, className="ad__que")])


def mensaje(texto, titulo="Qué significa para el hospital"):
    """La conclusion de la pagina para el hospital, destacada (Markdown)."""
    return html.Section(className="mensaje", children=[html.Div(titulo, className="mensaje__label"), dcc.Markdown(texto, className="mensaje__texto")])


def metodo(como, no_dice, fuente=""):
    """Detalle plegado al final: como se calculo, que NO dice y de donde sale."""
    return html.Details(className="metodo", children=[
        html.Summary("Cómo se calculó y qué no dice"),
        html.Div(className="metodo__grid", children=[
            html.Div([html.Div("Cómo se calculó", className="rec-block__label"), dcc.Markdown(como, className="ctx__text")]),
            html.Div([html.Div("Qué NO dice", className="rec-block__label"), dcc.Markdown(no_dice, className="ctx__text")])]),
        html.P(fuente, className="page-foot") if fuente else None])


def pagina(*hijos):
    return html.Div(className="page-container", children=[h for h in hijos if h is not None])


def aviso_datos(titulo, archivos):
    return html.Div(className="page-container", children=[
        html.H2(titulo),
        html.Div(className="card aviso", children=[
            html.B("Faltan las tablas agregadas de esta página: "), ", ".join(archivos), ". Se generan con ",
            html.Code("python dashboard/preparar_datos.py"), " (necesita los datos procesados, que viven fuera del repositorio)."])])


# ---------------------------------------------------------------- graficas
def estilo(fig, tema=None, leyenda=False, alto=None):
    """Tema comun de las graficas: fondo transparente, rejilla horizontal fina, barras con la punta redondeada, leyenda arriba."""
    fig.update_layout(template="simple_white", margin=dict(l=52, r=18, t=10 if not leyenda else 34, b=40), showlegend=leyenda,
                      legend=dict(orientation="h", y=1.12, x=0, xanchor="left", yanchor="bottom"), barcornerradius=4, bargap=0.45,
                      hoverlabel=dict(font_size=13), **({"height": alto} if alto else {}))
    fig.update_xaxes(showgrid=False, ticks="")
    fig.update_yaxes(showgrid=True, gridwidth=1, ticks="", showline=False, zeroline=False)
    return tg.aplicar(fig, tg.es_oscuro(tema))


def horas_eje(fig):
    """Eje de 24 horas con marcas cada 3 horas."""
    return fig.update_xaxes(tickmode="array", tickvals=list(range(0, 24, 3)), ticktext=[f"{h}:00" for h in range(0, 24, 3)])


def eje_fechas(fig, fechas):
    """Eje de tiempo con los meses en español: una marca en enero y otra en julio de cada año."""
    ini, fin = min(fechas), max(fechas)
    marcas = [m for m in pd.date_range(ini.replace(day=1), fin, freq="MS") if m.month in (1, 7)]
    return fig.update_xaxes(tickmode="array", tickvals=marcas, ticktext=[fecha_es(m) for m in marcas])


def etiqueta_final(fig, x, y, texto):
    """Etiqueta directa al final de una linea, en el margen derecho para que no tape la linea. Llamar despues de estilo()."""
    fig.add_annotation(x=x, y=y, text=texto, showarrow=False, xanchor="left", xshift=6)
    return fig.update_layout(margin_r=max(fig.layout.margin.r or 0, 18 + 7 * len(texto)))
