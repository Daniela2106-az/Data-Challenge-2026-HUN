"""
dashboard/pages/periodo.py  -  «Diagnóstico por periodo» (17-nov-2026; pagina 3.5 de docs/estructura_dashboard.md; formato de presentacion)
El reporte de cinco pasos del diagnostico de cuello de botella para el periodo que se elija, comparado con una referencia. Se presenta como las
demas paginas de Resultados: una tarjeta numerada por resultado, con su titular, una frase, un dato y la grafica que lo muestra.

TARJETAS  1 dónde está el cuello de botella · 2 cuánto cambió frente a la referencia (solo si se compara con otro periodo) · 3 qué se dispara
          (cola larga) · 4 qué estancias esperan muchísimo · 5 qué tienen en común · 6 camas y altas del periodo, y las cuatro tarjetas de las camas del periodo.
          Las acciones que sugiere cada periodo («Qué hacer») ya no se muestran aqui: viven en la pagina de Recomendaciones.
DATOS     datos/tablas_dashboard/cuello_botella_reportes.csv (src/exportar_reportes_periodo.py, que corre src/diagnostico_cuello_botella.py de antemano
          para cada periodo y referencia; el diagnostico parte de tablas por episodio que no se publican). Cada reporte guarda sus tablas como texto:
          aqui se leen y se dibujan, asi que no hay cifras escritas a mano. Se ofrecen años y semestres, no un rango libre.
          Si se agrega un periodo en el exportador, agregarlo también en PERIODOS de este archivo.
"""
import re
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import AZUL, PIZARRA, TENUE, aviso_datos, cifra, coma, estilo, filtro, lamina, laminas_grupo, leer, mensaje, metodo, pagina, portada, tarjetas  # noqa: E402

dash.register_page(__name__, path="/periodo", name="Diagnóstico por periodo", title="Diagnóstico por periodo - HUN", order=9)

PERIODOS = [("todo", "Todo el periodo"), ("2023", "2023"), ("2024", "2024"), ("2025", "2025"), ("2026", "2026 (hasta el 9 de abril)"),
            ("2023s1", "Feb a jun 2023"), ("2023s2", "Jul a dic 2023"), ("2024s1", "Ene a jun 2024"), ("2024s2", "Jul a dic 2024"),
            ("2025s1", "Ene a jun 2025"), ("2025s2", "Jul a dic 2025")]
NOMBRE = dict(PERIODOS)
TITULO = "El cuello de botella de cada periodo, paso a paso"
CAMAS_HUN = 106
# los nombres de grupo vienen sin tildes de las tablas del diagnostico
ACENTOS = {"Cancer y tumores": "Cáncer y tumores", "Endocrino y metabolico": "Endocrino y metabólico", "Musculoesqueletico y dolor": "Musculoesquelético y dolor",
           "Sin diagnostico": "Sin diagnóstico", "manana 6-11": "mañana 6–11", "tarde 12-17": "tarde 12–17"}


def _reportes():
    return leer("cuello_botella_reportes.csv", dtype={"periodo": str, "referencia": str})


def layout():
    if _reportes() is None:
        return pagina(aviso_datos("Diagnóstico por periodo", ["cuello_botella_reportes.csv"]))
    return pagina(
        portada("Resultados · Diagnóstico por periodo", TITULO,
                "Elige un periodo y con cuál compararlo. Verás dónde se pierde el tiempo, qué se dispara, qué estancias esperan muchísimo y qué tienen en común, "
                "y si el cuello de botella cambió frente a la referencia.", id_cifras="per-cifras"),
        html.Div(className="filtros", children=[filtro("per-periodo", "Periodo", PERIODOS, "2025"), filtro("per-ref", "Comparar con", PERIODOS, "2023")]),
        html.Div(id="per-reporte"),
        metodo(
            "Cada reporte se calculó de antemano con el diagnóstico repetible del proyecto. Mide cuánto espera cada estancia por encima de «lo normal»: la espera de los "
            "momentos en que llegaban menos pacientes. Esa referencia se calcula con el periodo con el que se compara, así que cambiarlo cambia el exceso.",
            "Se ofrecen años y semestres, no un rango libre de fechas. Todo son asociaciones, no causas: el diagnóstico se registra tarde y puede ser de otro paciente del par "
            "duplicado. El periodo termina el 9 de abril de 2026 porque después el registro está incompleto.",
            "Fuente: diagnóstico del cuello de botella · documentación, sección 6.7.", ruta="/periodo"))


# ---------------------------------------------------------------- leer el texto del reporte
def _num(s):
    """'43,7 %' -> 43.7;  '6973' -> 6973.0"""
    return float(s.replace("%", "").replace("h", "").strip().replace(".", "").replace(",", ".")) if re.search(r"\d", s) else float("nan")


def _tabla(texto):
    """Primera tabla del texto -> (encabezados, filas de texto)."""
    filas = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in texto.splitlines()
             if ln.strip().startswith("|") and not set(ln.replace("|", "").strip()) <= set("-: ")]
    return (filas[0], filas[1:]) if filas else ([], [])


def _cursiva(texto, empieza):
    """Texto de la linea en cursiva que empieza con `empieza`, sin los asteriscos."""
    for ln in texto.splitlines():
        if ln.strip().startswith("*" + empieza):
            return ln.strip().strip("*")
    return ""


def _grafica(fig, alto):
    return dcc.Graph(figure=fig, config={"displaylogo": False, "displayModeBar": False, "responsive": True}, style={"height": f"{alto}px"})


def _pct(v):
    return f"{coma(v, 0 if abs(v - round(v)) < 0.05 else 1)} %"


# ---------------------------------------------------------------- una figura por tarjeta
def _fig_cuello(filas, cuello, tema):
    """Exceso medio por estancia en cada tramo; el cuello de botella en azul."""
    nombres = [f[0] for f in filas]
    v = [_num(f[6]) for f in filas]
    fig = go.Figure(go.Bar(y=nombres, x=v, orientation="h", marker_color=[AZUL if n == cuello else TENUE for n in nombres],
                           text=[f"{coma(x, 1)} h" for x in v], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:.1f} h en exceso por estancia<extra></extra>"))
    estilo(fig, tema).update_xaxes(ticksuffix=" h", rangemode="tozero", range=[0, max(v) * 1.2])
    fig.update_layout(bargap=0.4, margin=dict(l=10, r=40, t=10, b=36))
    fig.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    fig.update_xaxes(showgrid=True)
    return fig


def _fig_cambio(ref, per, a, b, tema):
    fig = go.Figure(go.Bar(x=[ref, per], y=[a, b], marker_color=[TENUE, AZUL], text=[f"{coma(a, 1)} h", f"{coma(b, 1)} h"], textposition="outside",
                           cliponaxis=False, hovertemplate="%{x}: %{y:.1f} h de exceso medio por estancia<extra></extra>"))
    estilo(fig, tema).update_yaxes(ticksuffix=" h", rangemode="tozero", range=[0, max(a, b) * 1.25])
    fig.update_layout(bargap=0.55)
    return fig


def _fig_cola(filas, tema):
    """% de pacientes frente a % de las horas en exceso, para esperas de más de 24, 48 y 72 horas."""
    x = [f"Más de {f[0].split()[-2]} h" for f in filas]
    pac, hor = [_num(f[1]) for f in filas], [_num(f[2]) for f in filas]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=pac, name="% de los pacientes", marker_color=TENUE, text=[_pct(v) for v in pac], textposition="outside", cliponaxis=False,
                         hovertemplate="%{x}: %{y:.1f} % de los pacientes<extra></extra>"))
    fig.add_trace(go.Bar(x=x, y=hor, name="% de las horas en exceso", marker_color=AZUL, text=[_pct(v) for v in hor], textposition="outside",
                         cliponaxis=False, hovertemplate="%{x}: %{y:.1f} % de las horas en exceso<extra></extra>"))
    estilo(fig, tema, leyenda=True).update_yaxes(ticksuffix=" %", range=[0, 118], rangemode="tozero")
    fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08)
    return fig


def _fig_disparadas(per, p, ref_pct, tema):
    x = ["Lo esperado (referencia)", per]
    fig = go.Figure(go.Bar(x=x, y=[ref_pct, p], marker_color=[TENUE, AZUL], text=[_pct(ref_pct), _pct(p)], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{y:.1f} % de las estancias<extra></extra>"))
    estilo(fig, tema).update_yaxes(ticksuffix=" %", rangemode="tozero", range=[0, max(p, ref_pct) * 1.3])
    fig.update_layout(bargap=0.55)
    return fig


def _fig_comun(filas, general, tema):
    """% de cada grupo con espera larga; la linea marca el % de todas las estancias."""
    nombres = [f"{f[0]}: {ACENTOS.get(f[1], f[1])}" for f in filas]
    v, razon = [_num(f[3]) for f in filas], [_num(f[4]) for f in filas]
    fig = go.Figure(go.Bar(y=nombres, x=v, orientation="h", marker_color=[AZUL if r >= 2 else TENUE for r in razon],
                           text=[f"{_pct(a)} · {coma(r, 1)} veces" for a, r in zip(v, razon)], textposition="outside", cliponaxis=False,
                           customdata=razon, hovertemplate="%{y}: %{x:.1f} % con espera larga (%{customdata:.2f} veces más frecuente que en el resto)<extra></extra>"))
    estilo(fig, tema).update_xaxes(ticksuffix=" %", rangemode="tozero", range=[0, max(v) * 1.45], showgrid=True)
    fig.update_layout(bargap=0.35, margin=dict(l=10, r=20, t=26, b=36))
    fig.update_yaxes(autorange="reversed", automargin=True, showgrid=False)
    if general == general:
        fig.add_vline(x=general, line_dash="dot", line_width=2, line_color="#eb6834", layer="above", annotation_text=f"Todas las estancias: {_pct(general)}", annotation_position="top")
    return fig


def _fig_altas(antes, tarde, tema):
    resto = max(0.0, 100 - antes - tarde)
    x = ["Antes del mediodía", "Mediodía a 14 h y noche", "De 14 h a 19 h"]
    y = [antes, resto, tarde]
    fig = go.Figure(go.Bar(x=x, y=y, marker_color=[TENUE, TENUE, AZUL], text=[_pct(v) for v in y], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{y:.1f} % de las altas<extra></extra>"))
    estilo(fig, tema).update_yaxes(ticksuffix=" %", rangemode="tozero", range=[0, max(y) * 1.25])
    fig.update_layout(bargap=0.45)
    return fig


# ---------------------------------------------------------------- el reporte en tarjetas
def _cuerpo(r, per, ref, tema):
    t = {int(f.paso): f.texto for f in r.itertuples()}
    p1 = r.iloc[0]
    laminas, n = [], 0

    def nueva(*a, **k):
        nonlocal n
        n += 1
        laminas.append(lamina(n, *a, invertida=(n % 2 == 0), **k))

    # 1. dónde está el cuello de botella
    cab, filas = _tabla(t[1])
    if filas:
        total = next((f for f in filas if f[0].startswith("Espera de cama")), filas[-1])
        parte = re.search(r"\(([\d,]+) % del exceso", t[1])
        nota = _cursiva(t[1], "Los excesos")
        nueva(f"El cuello de botella de {per} es «{p1.cuello.lower()}»",
              f"Cada barra es una parte de la espera de cama: cuántas horas por encima de lo normal pierde, en promedio, cada estancia. En azul, el cuello de botella. {nota}",
              _grafica(_fig_cuello(filas, p1.cuello, tema), 250),
              dato=(_pct(_num(parte.group(1))), "del exceso de las dos partes está en el cuello de botella") if parte
              else (f"{coma(_num(total[6]), 1)} h", "de exceso medio por estancia"))

    # 2. frente a la referencia
    if not int(p1.mismo):
        cambio = re.search(r"pasó de ([\d,]+) a ([\d,]+) h", p1.cambio) if isinstance(p1.cambio, str) else None
        if cambio:
            a, b = _num(cambio.group(1)), _num(cambio.group(2))
            sube = b > a
            quedo = "el mismo" if "no cambió" in p1.cambio else "uno distinto"
            nueva(f"El exceso por paciente {'sube' if sube else 'baja'} de {coma(a, 1)} a {coma(b, 1)} horas",
                  f"Se compara **{per}** con **{ref}**. El cuello de botella es {quedo} que en la referencia. El exceso es lo que espera una estancia por encima de lo normal; "
                  "la referencia se recalcula con el periodo con el que se compara.",
                  _grafica(_fig_cambio(ref if ref != per else "Referencia", per, a, b, tema), 280),
                  dato=(f"{'+' if sube else '−'}{coma(abs(b - a), 1)} h", "de exceso medio por estancia frente a la referencia"), )

    # 3. qué se dispara
    cab, filas = _tabla(t[2])
    if filas:
        f48 = next((f for f in filas if f[0].startswith("48")), filas[-1])
        frase = next((ln for ln in t[2].splitlines() if ln.startswith("Las esperas de más de")), "")
        nueva(f"El {_pct(_num(f48[1]))} de los pacientes concentra el {_pct(_num(f48[2]))} de las horas en exceso",
              (frase + " " if frase else "") + "Cada par de barras compara a cuántos pacientes afecta una espera y cuántas horas en exceso suma.",
              _grafica(_fig_cola(filas, tema), 300), dato=(_pct(_num(f48[2])), "de las horas en exceso salen de esperas de más de 48 horas"))

    # 4. qué estancias esperan muchísimo
    d = re.search(r"\*\*([\d,]+) h\*\*\): \*\*(\d+) de (\d+)\*\* \(([\d,]+) %; en la referencia serían (\d+) %\)", t[3])
    general = float("nan")
    if d:
        p90, k, tot, pct_, ref_pct = (_num(x) for x in d.groups())
        general = pct_
        largas = re.search(r"más de (\d+) días: (\d+) \(([\d,]+) %\)", t[3])
        extra = f" Las estancias de más de {largas.group(1)} días son {_pct(_num(largas.group(3)))} ({coma(_num(largas.group(2)), 0)})." if largas else ""
        nueva(f"{_pct(pct_)} de las estancias tiene una espera muy larga ({coma(k, 0)} de {coma(tot, 0)})",
              f"Se llama «espera muy larga» a esperar más de **{coma(p90, 1)} horas**, lo que en la referencia solo pasaba al {_pct(ref_pct)} de las estancias.{extra}",
              _grafica(_fig_disparadas(per, pct_, ref_pct, tema), 280),
              dato=(f"{coma(pct_ / ref_pct, 1)} veces", "lo esperado, según la referencia"))

    # 5. qué tienen en común
    cab, filas = _tabla(t[4])
    if filas:
        top = max(filas, key=lambda f: _num(f[4]))
        asoc = _cursiva(t[4], "Asociación")
        nueva(f"Es más frecuente en {ACENTOS.get(top[1], top[1]).lower() if top[0] != 'Edad' else 'las edades de ' + top[1]}: {_pct(_num(top[3]))} de ese grupo",
              "Cada barra es el porcentaje de las estancias de ese grupo con una espera muy larga; la línea punteada es el de todas las estancias. "
              f"En azul, los grupos donde es al menos el doble de frecuente que en el resto. Solo grupos con al menos 30 casos. {asoc}",
              _grafica(_fig_comun(filas, general, tema), max(300, 34 * len(filas) + 70)),
              dato=(f"{coma(_num(top[4]), 1)} veces", f"más frecuente en {ACENTOS.get(top[1], top[1])} que en el resto"))

    # 6. camas y altas del periodo
    camas = re.search(r"media ([\d,]+), máximo ([\d,]+); el ([\d,]+) % de las horas supera", t[2])
    altas = re.search(r"el ([\d,]+) % ocurre entre las 14:00 y las 18:59 y el ([\d,]+) % antes del mediodía", t[2])
    little = re.search(r"Ingresos a cama por día ([\d,]+); estancia media ([\d,]+) días; Little: ([\d,]+) camas", t[2])
    if camas and altas:
        media, maximo, sobre = (_num(x) for x in camas.groups())
        tarde, antes = (_num(x) for x in altas.groups())
        nota = _cursiva(t[2], "La ocupación")
        nueva(f"El {_pct(tarde)} de las altas ocurre entre las 14 y las 19 horas",
              f"En {per} hubo en promedio **{coma(media, 0)} camas ocupadas** (máximo {coma(maximo, 0)}) y en el {_pct(sobre)} de las horas se superaron las {CAMAS_HUN} camas "
              f"que dio el HUN. Solo el {_pct(antes)} de las altas ocurre antes del mediodía. {nota}",
              _grafica(_fig_altas(antes, tarde, tema), 280), dato=(_pct(sobre), f"de las horas con más de {CAMAS_HUN} camas ocupadas"))
    salida = [laminas_grupo(*laminas)] if laminas else []
    if camas and little:
        ing, est, lit = (_num(x) for x in little.groups())
        salida.append(tarjetas("Las camas del periodo", f"Cuatro cifras de la ocupación de {per}",
                               (coma(media, 0), "Camas ocupadas, en promedio", f"Con un máximo de {coma(maximo, 0)}. El HUN informó {CAMAS_HUN} camas de hospitalización."),
                               (coma(ing, 1), "Ingresos a cama por día", "Pacientes que reciben cama cada día, contando cada estancia una vez."),
                               (f"{coma(est, 2)} días", "Estancia media en cama", "Lo que dura, en promedio, una hospitalización."),
                               (coma(lit, 0), "Camas que explican los ingresos", "Ingresos por día × estancia media: debe parecerse a las camas ocupadas.")))

    return salida


@callback(Output("per-cifras", "children"), Output("per-reporte", "children"), Input("per-periodo", "value"), Input("per-ref", "value"), Input("theme-store", "data"))
def reporte(periodo, referencia, tema):
    t = _reportes()
    if t is None:
        return [], []
    r = t[(t.periodo == periodo) & (t.referencia == referencia)].sort_values("paso")
    if r.empty:
        return [], [mensaje("No hay un reporte para esa combinación.", titulo="Sin reporte")]
    p1 = r.iloc[0]
    per, ref = (NOMBRE[x] if x != "todo" else "todo el periodo" for x in (periodo, referencia))
    if int(p1.mismo):
        titular = f"**El periodo y la referencia son el mismo ({per}):** no hay comparación, solo el diagnóstico del periodo."
    else:
        titular = f"**Frente a {ref}, {p1.cambio}**" if isinstance(p1.cambio, str) and p1.cambio else "Sin comparación disponible."
    textos = {int(f.paso): f.texto for f in r.itertuples()}
    cifras = []
    _, total = _tabla(textos[1])
    _, cola = _tabla(textos[2])
    if total:
        fila = next((f for f in total if f[0].startswith("Espera de cama")), total[-1])
        cifras.append(cifra(f"{coma(_num(fila[6]), 1)} h", f"de exceso medio por estancia ({coma(_num(fila[1]), 0)} estancias)"))
    if cola:
        f48 = next((f for f in cola if f[0].startswith("48")), cola[-1])
        cifras += [cifra(f"{_pct(_num(f48[1]))}", "de los pacientes espera más de 48 horas"), cifra(f"{_pct(_num(f48[2]))}", "de las horas en exceso viene de esas esperas")]
    cuerpo = _cuerpo(r, per, ref, tema)
    significa = []
    if cola:
        f48 = next((f for f in cola if f[0].startswith("48")), cola[-1])
        significa = [mensaje(f"En {per}, **el {_pct(_num(f48[1]))} de los pacientes espera más de 48 horas y suma el {_pct(_num(f48[2]))} de las horas perdidas**: el problema está en las "
                             "esperas de varios días, no en la espera típica. Las acciones que se derivan de esto están en la página de Recomendaciones.")]
    return cifras, [mensaje(f"**Cuello de botella de {per}: {p1.cuello}.** {titular}", titulo="En una frase"), *cuerpo, *significa]
