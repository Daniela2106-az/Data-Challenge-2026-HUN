"""
dashboard/pages/periodo.py  -  «Diagnóstico por periodo» (15-nov-2026; pagina 3.5 de docs/estructura_dashboard.md; formato de presentacion)
El reporte de cinco pasos del diagnostico de cuello de botella para el periodo que se elija, comparado con una referencia: dónde está el
cuello, qué se dispara, qué estancias tienen esperas muy largas, qué tienen en común y qué hacer. Dice también si el cuello de botella cambió.

DATOS  datos/tablas_dashboard/cuello_botella_reportes.csv (src/exportar_reportes_periodo.py, que corre src/diagnostico_cuello_botella.py de antemano
       para cada periodo y referencia; el diagnostico parte de tablas por episodio que no se publican). Se ofrecen años y semestres, no un rango libre.
       Si se agrega un periodo en el exportador, agregarlo también en PERIODOS de este archivo.
"""
import sys
from pathlib import Path

import dash
from dash import Input, Output, dcc, html, callback

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import aviso_datos, bloque, filtro, leer, mensaje, metodo, pagina, portada  # noqa: E402

dash.register_page(__name__, path="/periodo", name="Diagnóstico por periodo", title="Diagnóstico por periodo - HUN", order=9)

PERIODOS = [("todo", "Todo el periodo"), ("2023", "2023"), ("2024", "2024"), ("2025", "2025"), ("2026", "2026 (hasta el 9 de abril)"),
            ("2023s1", "Feb a jun 2023"), ("2023s2", "Jul a dic 2023"), ("2024s1", "Ene a jun 2024"), ("2024s2", "Jul a dic 2024"),
            ("2025s1", "Ene a jun 2025"), ("2025s2", "Jul a dic 2025")]
NOMBRE = dict(PERIODOS)


def _reportes():
    return leer("cuello_botella_reportes.csv", dtype={"periodo": str, "referencia": str})


def layout():
    if _reportes() is None:
        return pagina(aviso_datos("Diagnóstico por periodo", ["cuello_botella_reportes.csv"]))
    return pagina(
        portada("Resultados · Diagnóstico por periodo", "El cuello de botella de cada periodo, en cinco pasos",
                "Elige un periodo y con cuál compararlo. Verás dónde se pierde el tiempo, qué se dispara, qué estancias esperan muchísimo, qué tienen en común y qué hacer, "
                "y si el cuello de botella cambió frente a la referencia."),
        html.Div(className="filtros", children=[filtro("per-periodo", "Periodo", PERIODOS, "2025"), filtro("per-ref", "Comparar con", PERIODOS, "2023")]),
        html.Div(id="per-reporte"),
        metodo(
            "Cada reporte se calculó de antemano con el diagnóstico repetible del proyecto. Mide cuánto espera cada estancia por encima de «lo normal»: la espera de los "
            "momentos en que llegaban menos pacientes. Esa referencia se calcula con el periodo con el que se compara, así que cambiarlo cambia el exceso.",
            "Se ofrecen años y semestres, no un rango libre de fechas. Todo son asociaciones, no causas: el diagnóstico se registra tarde y puede ser de otro paciente del par "
            "duplicado. El periodo termina el 9 de abril de 2026 porque después el registro está incompleto.",
            "Fuente: diagnóstico del cuello de botella · documentación, sección 6.7.", ruta="/periodo"))


# ---------------------------------------------------------------- del texto del reporte a componentes
def _tabla(lineas):
    filas = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lineas if not set(ln.replace("|", "").strip()) <= set("-: ")]
    cab, cuerpo = filas[0], filas[1:]
    return html.Div(className="tech-table-wrap", children=[html.Table(className="tech-table", children=[
        html.Thead(html.Tr([html.Th(c) for c in cab])), html.Tbody([html.Tr([html.Td(f"{int(c):,}".replace(",", ".") if c.isdigit() and len(c) > 3 else c) for c in f]) for f in cuerpo])])])


def _componentes(texto):
    """Markdown del reporte -> tablas HTML y parrafos (dcc.Markdown solo para el texto, que no lleva tablas)."""
    salida, bloque_, tabla = [], [], []
    for ln in texto.splitlines():
        if ln.strip().startswith("|"):
            if bloque_:
                salida.append(dcc.Markdown("\n".join(bloque_))); bloque_ = []
            tabla.append(ln)
        else:
            if tabla:
                salida.append(_tabla(tabla)); tabla = []
            bloque_.append(ln)
    if tabla:
        salida.append(_tabla(tabla))
    if bloque_ and "".join(bloque_).strip():
        salida.append(dcc.Markdown("\n".join(bloque_)))
    return salida


@callback(Output("per-reporte", "children"), Input("per-periodo", "value"), Input("per-ref", "value"))
def reporte(periodo, referencia):
    t = _reportes()
    if t is None:
        return []
    r = t[(t.periodo == periodo) & (t.referencia == referencia)].sort_values("paso")
    if r.empty:
        return [mensaje("No hay un reporte para esa combinación.", titulo="Sin reporte")]
    p1 = r.iloc[0]
    per, ref = (NOMBRE[x] if x != "todo" else "todo el periodo" for x in (periodo, referencia))
    if int(p1.mismo):
        titular = f"**El periodo y la referencia son el mismo ({per}):** no hay comparación, solo el diagnóstico del periodo."
    else:
        titular = f"**Frente a {ref}, {p1.cambio}**" if isinstance(p1.cambio, str) and p1.cambio else "Sin comparación disponible."
    salida = [mensaje(f"**Cuello de botella de {per}: {p1.cuello}.** {titular}", titulo="En una frase")]
    for f in r.itertuples():
        salida += [bloque(f"{f.paso}. {f.titulo}"), *_componentes(f.texto)]
    return salida
