"""
dashboard/pages/recomendaciones.py  -  «Recomendaciones» (17-nov-2026; pagina 4.1 de docs/estructura_dashboard.md; formato de presentacion)
Las 7 recomendaciones del proyecto con lo que dicen nuestros datos, la evidencia externa verificada, su firmeza, su limite y como medirla, y las
acciones que sugiere el diagnostico de cada periodo (antes en «Diagnostico por periodo»), ordenadas por gravedad y tipo y con la recomendacion
de la que se derivan.

DATOS  datos/tablas_dashboard/recomendaciones_tabla.csv (tabla escrita a mano a partir de docs/recomendaciones.md; sin datos por paciente) y
       datos/tablas_dashboard/cuello_botella_reportes.csv (src/exportar_reportes_periodo.py) para las acciones de cada periodo.
       Si falta alguna, la pagina muestra un aviso en vez de tumbar el arranque del dashboard.
UBICACION  Es informativa: el usuario elige un periodo o un filtro, pero no modifica ningun supuesto (a diferencia de las alertas, que van en Prediccion).
"""
import re
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from catalogo import enlaces_alertas, enlaces_paginas, recomendaciones  # noqa: E402
import tema_graficos as tg  # noqa: E402
from componentes import (AZUL, PIZARRA, TENUE, bloque as titulo_bloque, cifra, coma, estilo, filtro, frase, grafico, lamina, leer,  # noqa: E402
                         mensaje, portada, tarjetas)

dash.register_page(__name__, path="/recomendaciones", name="Recomendaciones", title="Recomendaciones - HUN", order=5)

RECS = recomendaciones()
DATOS_OK = RECS is not None and not RECS.empty

TIPO = {1: "Registro", 2: "Seguimiento", 3: "Proceso", 4: "Proceso", 5: "Alerta", 6: "Proceso", 7: "Revisión"}      # de que clase es cada recomendacion
TIPOS = ["Registro", "Seguimiento", "Proceso", "Alerta", "Revisión"]
TITULO_CORTO = {1: "Registrar mejor la información", 2: "Seguir seis indicadores cada mes", 3: "Reunión diaria de camas, con alertas", 4: "Meta de altas antes del mediodía",
                5: "Alerta por paciente con 48 h sin cama", 6: "Pedir antes la cama de quien llega por la tarde", 7: "Revisar cada semana las estancias largas"}
SIEMPRE = {1: "Aplica en cualquier periodo: es la base para medir bien lo demás.", 2: "Aplica en cualquier periodo: la línea base para ver si algo mejora."}
NO_RECOMENDAMOS = [
    ("Reforzar personal según el día", "El día de la semana y los festivos casi no cambian la espera."),
    ("Ordenar la fila por riesgo al llegar", "El mejor modelo marcaría al 44 % de los pacientes, con 4 de cada 10 falsas alarmas."),
    ("Un centro de comando solo", "El estudio mejor diseñado (Bradford, Reino Unido) no encontró efecto."),
    ("Calcular cuántas camas más", "Los datos no lo permiten con certeza: antes de pensar en camas nuevas, atacar la estancia y la asignación."),
]

# ---------------------------------------------------------------- acciones que sugiere el diagnostico de un periodo
PERIODOS = [("todo", "Todo el periodo"), ("2023", "2023"), ("2024", "2024"), ("2025", "2025"), ("2026", "2026 (hasta el 9 de abril)"),
            ("2023s1", "Feb a jun 2023"), ("2023s2", "Jul a dic 2023"), ("2024s1", "Ene a jun 2024"), ("2024s2", "Jul a dic 2024"),
            ("2025s1", "Ene a jun 2025"), ("2025s2", "Jul a dic 2025")]
NOMBRE = dict(PERIODOS)
# regla -> (palabra que la identifica en el texto del reporte, tipo, accion derivada, recomendaciones de las que sale, alertas que la apoyan,
#           que mide, umbral con el que se activa en src/diagnostico_cuello_botella.py)
REGLAS = {
    "asignar": ("dentro de urgencias", "Proceso", "Asignar la cama enseguida y avisar antes", [4, 5, 6], "A3;A4", "% del exceso de espera que está en urgencias", None),
    "altas": ("adelantar altas", "Proceso", "Adelantar las altas a la mañana", [4], "A2", "% de las altas entre las 14 y las 19 h", 50),
    "cola": ("revisar pacientes con espera", "Alerta", "Revisar uno por uno a quien lleva más de 48 h sin cama", [5], "A3;A4", "% de las horas en exceso que vienen de esperas de más de 48 h", 50),
    "camas": ("planear camas", "Planeación", "Planear las camas con el pronóstico semanal", [3, 7], "A1;A2;S1", "% de las horas con más de 106 camas ocupadas", 10),
    "flujo": ("sobrerrepresentadas", "Revisión", "Mirar aparte el flujo de ese tipo de visita", [7], "", "veces más frecuente entre las esperas largas", None),
}
FACTOR_GRAVEDAD = 1.5          # una regla es de gravedad alta si su cifra supera en mas de la mitad el umbral que la activa


def _num(s):
    return float(s.replace("%", "").strip().replace(".", "").replace(",", "."))


def _metricas(periodo):
    """Acciones del reporte del periodo (consigo mismo como referencia): [(regla, cifra, gravedad, texto de la accion)]."""
    t = leer("cuello_botella_reportes.csv", dtype={"periodo": str, "referencia": str})
    if t is None:
        return [], {}
    r = t[(t.periodo == periodo) & (t.referencia == periodo)].sort_values("paso")
    if r.empty:
        return [], {}
    textos = {int(f.paso): f.texto for f in r.itertuples()}
    parte = re.search(r"\(([\d,]+) % del exceso", textos[1])
    tarde = re.search(r"el ([\d,]+) % ocurre entre las 14:00", textos[2])
    sobre = re.search(r"el ([\d,]+) % de las horas supera", textos[2])
    fila48 = next((ln for ln in textos[2].splitlines() if ln.startswith("| 48")), None)
    cola = _num(fila48.strip("|").split("|")[2]) if fila48 else None
    cifras = {"asignar": _num(parte.group(1)) if parte else 100.0, "altas": _num(tarde.group(1)) if tarde else None, "cola": cola,
              "camas": _num(sobre.group(1)) if sobre else None, "flujo": None}
    salida = []
    for ln in textos[5].splitlines():
        if not ln.startswith("- "):
            continue
        txt = ln[2:].strip().replace("**", "")
        clave = next((k for k, v in REGLAS.items() if v[0] in txt.lower()), None)
        if clave is None:
            continue
        valor, umbral = cifras[clave], REGLAS[clave][6]
        if clave == "flujo":
            m = re.search(r"razón ([\d,.]+)", txt)
            valor = _num(m.group(1)) if m else None
        grave = "Alta" if (umbral is None and clave == "asignar") or (valor is not None and umbral and valor >= FACTOR_GRAVEDAD * umbral) else "Media"
        salida.append((clave, valor, grave, txt))
    salida.sort(key=lambda a: (a[2] != "Alta", -(a[1] or 0) / (REGLAS[a[0]][6] or 100)))
    return salida, cifras


# ---------------------------------------------------------------- las siete recomendaciones, ordenadas por firmeza
def chip(firmeza):
    return html.Span(f"Firmeza {firmeza.lower()}", className=f"rec-chip rec-chip--{firmeza.lower()}")


def _primera(texto):
    return re.split(r"(?<=[.;])\s", str(texto).strip())[0].rstrip(".;") + "."


def carta(r):
    """Una recomendacion como tarjeta operativa: que cambiar (tres pasos), la meta con la que se sabe que funciono y por que importa."""
    n = int(r.prioridad)
    pasos = [x for x in str(r.que_cambiar).split("|") if x]
    return html.Div(id=f"rec-R{n}", className="hecho rec-corta", children=[
        html.Div(className="rec-corta__cab", children=[html.Div(f"R{n}", className="hecho__num"),
                                                       html.Div([html.Span(TIPO.get(n, ""), className="rec-chip"), chip(r.firmeza)], className="rec-corta__chips")]),
        html.Div(r.titulo_accion, className="hecho__titulo"),
        html.Div("Qué cambiar", className="rec-corta__rotulo"),
        html.Ol([html.Li(x) for x in pasos], className="rec-corta__pasos"),
        html.Div(className="rec-corta__meta", children=[html.Span("Meta", className="rec-corta__rotulo"), html.Span(r.meta)]),
        html.P(r.por_que, className="hecho__txt"),
        html.Div(className="enlaces", children=[html.Span("Se ve en", className="enlaces__rotulo"), *enlaces_paginas(r.paginas_respaldo), *enlaces_alertas(r.alerta_ids)])
        if (r.paginas_respaldo or r.alerta_ids) else None])


def lista_por_firmeza():
    """Las siete, primero las de firmeza alta y luego las de media (dentro de cada grupo, por prioridad)."""
    salida = []
    for firmeza, sub in (("Alta", "Los datos del HUN muestran el problema, varios estudios coinciden y la acción es de bajo costo"),
                         ("Media", "Les falta una de esas tres condiciones")):
        filas = RECS[RECS.firmeza == firmeza].sort_values("prioridad")
        if len(filas):
            salida += [titulo_bloque(f"Firmeza {firmeza.lower()}", sub), html.Div(className="hechos hechos--2", children=[carta(r) for r in filas.itertuples()])]
    return salida


def layout():
    if not DATOS_OK:
        return html.Div(className="page-container", children=[
            html.H2("Recomendaciones"),
            html.P("No se encontró datos/tablas_dashboard/recomendaciones_tabla.csv en este equipo.", style={"color": "#c0392b"}),
        ])
    n_alta = int((RECS.firmeza == "Alta").sum())
    return html.Div(className="page-container", children=[
        portada(
            "Propuestas · Recomendaciones", "Más que faltar camas, falta liberarlas, asignarlas y desocuparlas a tiempo",
            "Siete acciones para el hospital, de la más básica a la más específica, cada una respaldada por los datos del HUN y por "
            "lo que se ha encontrado en otros hospitales.",
            [cifra(str(len(RECS)), f"recomendaciones: {n_alta} con firmeza alta y {len(RECS) - n_alta} con firmeza media"),
             cifra("38", "fuentes externas, cada una leída en su versión original"),
             cifra("1 de cada 5", "pacientes espera más de 48 horas por una cama")]),
        frase("Siete acciones respaldadas por los datos del HUN y por lo que se encontró en otros hospitales: empiezan por registrar mejor y terminan en revisar cada semana las estancias largas."),
        titulo_bloque("Las siete recomendaciones", "Ordenadas por firmeza, de la más a la menos respaldada"),
        *lista_por_firmeza(),
        lamina(1, html.Span(id="rec-titular"),
               "Cada fila es una regla del diagnóstico del cuello de botella y cada columna, un año. **El número es la cifra de ese año.** "
               "En azul oscuro, gravedad alta: la cifra supera en más de la mitad el umbral que activa la regla. En azul claro, gravedad media. En gris, la regla no se activó ese año.",
               grafico("rec-reglas", alto=300), id_dato="rec-dato"),
        tarjetas("Lo que no recomendamos", "Ideas que se evaluaron y que los datos no respaldan", *[("✕", t, d) for t, d in NO_RECOMENDAMOS]),
        mensaje("Esperar mucho por una cama no es solo incómodo: en un estudio de 41.256 ingresos la mortalidad pasó de **2,5 %** en "
                "quienes esperaron menos de 2 horas a **4,5 %** en quienes esperaron 12 horas o más (Singer 2011), y una revisión de 21 "
                "estudios asocia las esperas largas con más errores de medicación y retrasos en el tratamiento (Dowling 2026). Por eso vale la pena actuar."),
    ])


ANIOS = [("2023", "2023"), ("2024", "2024"), ("2025", "2025"), ("2026", "2026 (hasta abril)")]
FILAS = {"asignar": "El tiempo se pierde en urgencias, antes de la cama", "altas": "Las altas salen por la tarde (desde 50 %)",
         "cola": "Pocos pacientes concentran la espera (desde 50 %)", "camas": "Se superan las 106 camas (desde 10 % de las horas)"}
LEYENDA = {"asignar": "del exceso de espera está en urgencias", "altas": "de las altas ocurre entre las 14 y las 19 h",
           "cola": "de las horas en exceso viene de esperas de más de 48 h", "camas": "de las horas con más de 106 camas ocupadas"}


@callback(Output("rec-titular", "children"), Output("rec-reglas", "figure"), Output("rec-dato", "children"), Input("theme-store", "data"))
def reglas(tema):
    """Mapa de reglas por año: que se activo, con que cifra y con que gravedad."""
    z, texto, hover = [], [], []
    activas = {}
    for anio, _ in ANIOS:
        a, _c = _metricas(anio)
        activas[anio] = {c: (v, g) for c, v, g, _t in a}
    claves = list(FILAS)
    for c in claves:
        fz, ft, fh = [], [], []
        for anio, _ in ANIOS:
            v, g = activas[anio].get(c, (None, None))
            fz.append({"Alta": 2, "Media": 1}.get(g, 0))
            ft.append(f"{coma(v, 0)} %" if v is not None else "—")
            fh.append(f"{FILAS[c]}<br>{anio}: " + (f"{coma(v, 0)} % {LEYENDA[c]}<br>Gravedad {g.lower()}" if v is not None else "la regla no se activó"))
        z.append(fz); texto.append(ft); hover.append(fh)
    oscuro = tg.es_oscuro(tema)
    escala = [[0, "#2b333c" if oscuro else "#e3e8ee"], [0.4999, "#2b333c" if oscuro else "#e3e8ee"], [0.5, "#6aa8dc" if oscuro else "#9cc7ea"], [0.7499, "#6aa8dc" if oscuro else "#9cc7ea"],
              [0.75, "#1f66ad" if oscuro else "#0a4f8f"], [1, "#1f66ad" if oscuro else "#0a4f8f"]]
    fig = go.Figure(go.Heatmap(z=z, x=[n for _, n in ANIOS], y=[FILAS[c] for c in claves], zmin=0, zmax=2, colorscale=escala, showscale=False, xgap=6, ygap=6,
                               text=texto, texttemplate="%{text}", textfont=dict(size=15, color="#ffffff"), customdata=hover, hovertemplate="%{customdata}<extra></extra>"))
    estilo(fig, tema)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=36))
    fig.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    fig.update_xaxes(showgrid=False, side="top")
    ult = activas["2025"]
    altas = sum(1 for _, g in ult.values() if g == "Alta")
    titular = f"En 2025 se activaron {len(ult)} de las 4 reglas, {altas} de gravedad alta"
    dato = [html.B(f"{altas} de {len(ult)}"), html.Span("reglas de gravedad alta en 2025, año completo más reciente")]
    return titular, fig, dato
