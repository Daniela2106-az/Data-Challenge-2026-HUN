"""
dashboard/widgets_paciente.py  -  piezas de formulario y de resultado compartidas por las paginas de
estimador por paciente (19-nov-2026): dashboard/pages/paciente.py («Paciente en espera») y
dashboard/pages/paciente_cama.py («Paciente en cama»).

Se separan aqui (en vez de hacer `from paciente import ...` desde paciente_cama.py) porque Dash carga
cada pagina de `pages/` como su propio modulo top-level: un segundo `import paciente` desde otra
pagina volveria a ejecutar sus `clientside_callback(...)` de nivel de modulo (las etapas de urgencias,
ids `pac-etapas-*`), registrando esos callbacks dos veces y tumbando el arranque de la app.
"""
from pathlib import Path

import pandas as pd
from dash import Input, Output, State, clientside_callback, dcc, html

GRIS, AZUL, NARANJA, VERDE, ROSA = "#6b6b6b", "#2a6fb0", "#eb6834", "#2e9b5b", "#d6336c"

TIPOS_INFO = {"Urgencias": ("URG", "Urgencias: la ruta más común (83 % de los ingresos). El paciente pasa por la etapa de admisión (ER) y queda en atención (TU) hasta que se le asigna cama."),
              "Treatment urgency": ("TU", "Treatment urgency: nombre interno de la base para la atención en urgencias (incluye observación y espera), sin pasar por el registro de admisión."),
              "Ambulatorio": ("AMB", "Ambulatorio: evento administrativo, normalmente una cita o trámite previo, sin que eso signifique una visita de urgencias típica.")}

# bandera -> (valor del laboratorio que se le pasa al estimador, justo mas alla del punto de corte; texto para el usuario)
LABS_FUERA = {"leucocitos_alt": ("leuc_max", 13.0, "Leucocitos altos (más de 12)"), "leucopenia": ("leuc_min", 3.0, "Leucocitos bajos (menos de 4)"),
              "anemia": ("hb_min", 9.0, "Hemoglobina baja (menos de 10)"), "creatinina_alta": ("creat_max", 2.0, "Creatinina alta (más de 1,5)"),
              "bun_alto": ("bun_max", 45.0, "BUN alto (más de 40)"), "lactato_alto": ("lactato_max", 3.0, "Lactato alto (más de 2,2)"),
              "potasio_alt": ("k_max", 6.0, "Potasio alto (más de 5,5)"), "sodio_bajo": ("na_min", 125.0, "Sodio bajo (menos de 130)"),
              "sodio_alto": ("na_max", 155.0, "Sodio alto (más de 150)"), "troponina_alta": ("troponina_max", 2.0, "Troponina alta (más de 1,0)"),
              "pcr_alta": ("pcr_max", 80.0, "PCR alta (más de 50)")}


def _grupos_dx():
    """Grupos de diagnostico (datos/referencia/mapeo_dx.csv) para el diagnostico de una visita anterior."""
    try:
        d = pd.read_csv(Path(__file__).resolve().parent.parent / "datos" / "referencia" / "mapeo_dx.csv", encoding="utf-8")
        return sorted(d.categoria_dx.dropna().unique())
    except (FileNotFoundError, OSError):
        return []


GRUPOS_DX = _grupos_dx()


def info_badge(texto):
    return html.Span(className="info-badge tooltip-trigger", children=[
        "i", html.Span(texto, className="tooltip-content")])


def stepper(id_, value, minimo=0, maximo=None, label_sr=""):
    return html.Div(className="stepper", children=[
        html.Button("–", id=f"{id_}-menos", n_clicks=0, className="stepper__btn", type="button"),
        dcc.Input(id=id_, type="number", value=value, min=minimo, max=maximo, step=1, className="stepper__value"),
        html.Button("+", id=f"{id_}-mas", n_clicks=0, className="stepper__btn", type="button"),
    ])


def campo_stepper_clientside(id_, minimo=0, maximo=None):
    """+/- de un stepper simple (edad, horas): clientside, sin ir al servidor."""
    clientside_callback(
        f"""
        function(nMenos, nMas, val) {{
            var ctx = dash_clientside.callback_context;
            if (!ctx.triggered.length) {{ return val; }}
            var id = ctx.triggered[0].prop_id;
            var v = (val === null || val === undefined) ? 0 : val;
            v = v + (id.indexOf('menos') !== -1 ? -1 : 1);
            var lo = {minimo if minimo is not None else 'null'}, hi = {maximo if maximo is not None else 'null'};
            if (lo !== null && v < lo) v = lo;
            if (hi !== null && v > hi) v = hi;
            return v;
        }}
        """,
        Output(id_, "value"),
        Input(f"{id_}-menos", "n_clicks"), Input(f"{id_}-mas", "n_clicks"),
        State(id_, "value"),
    )


def tabla_html(encabezados, filas, resaltar_fila=None):
    cuerpo_filas = []
    for i, fila in enumerate(filas):
        estilo = {"fontWeight": 700, "color": AZUL} if i == resaltar_fila else {}
        cuerpo_filas.append(html.Tr([html.Td(celda, style=estilo) for celda in fila]))
    tabla = html.Table(className="tech-table", children=[
        html.Thead(html.Tr([html.Th(h) for h in encabezados])),
        html.Tbody(cuerpo_filas),
    ])
    return html.Div(tabla, className="tech-table-wrap")


def tarjeta(titulo, valor, detalle="", destacada=False):
    clases = "metric-card" + (" metric-card--lead" if destacada else "")
    return html.Div(className=clases, children=[
        html.Div(titulo, style={"fontSize": "12px"}),
        html.Div(valor, className="value-pop", key=f"{titulo}-{valor}", style={"fontSize": "24px", "fontWeight": 700}),
        html.Div(detalle, style={"fontSize": "12px", "color": GRIS})])


def _pos(v, lo, hi):
    return max(0.0, min(100.0, (v - lo) / (hi - lo) * 100))


def rango_widget(p25, p50, p75, p90):
    """Rango tipico (p25-p75, fuerte) con la cola del p90 (peor caso, mas clara) y la mediana marcada."""
    ancho = max(p90 - p25, max(p50 * 0.05, 1.0))
    esc_lo, esc_hi = max(0.0, p25 - ancho * 0.15), p90 + ancho * 0.15
    esc_hi = max(esc_hi, esc_lo + 1.0)
    pos = lambda v: _pos(v, esc_lo, esc_hi)  # noqa: E731
    p_25, p_50, p_75, p_90 = pos(p25), pos(p50), pos(p75), pos(p90)
    return html.Div(className="range-metric", children=[
        html.Div("Lo que le falta: rango típico, con el peor caso (p90) en la cola clara", className="range-metric__title"),
        html.Div(className="range-metric__line", children=[
            html.Div(className="range-metric__track"),
            html.Div(className="range-metric__fill--tail", style={"left": f"{p_75}%", "width": f"{p_90 - p_75}%"}),
            html.Div(className="range-metric__fill", style={"left": f"{p_25}%", "width": f"{p_75 - p_25}%"}),
            html.Div(f"{p25:.0f}", className="range-metric__endlabel", style={"left": f"{p_25}%"}),
            html.Div(f"{p75:.0f}", className="range-metric__endlabel", style={"left": f"{p_75}%"}),
            html.Div(f"{p90:.0f} h (peor caso)", className="range-metric__endlabel range-metric__endlabel--tail", style={"left": f"{p_90}%"}),
            html.Div(className="range-metric__marker", style={"left": f"{p_50}%"}, children=[
                html.Div(f"{p50:.0f} h", className="range-metric__marker-value value-pop", key=f"marker-{p50:.0f}"),
                html.Div(className="range-metric__marker-dot"),
            ]),
        ]),
        html.Div("El punto azul es la mediana (la mitad de los pacientes parecidos ya tendría cama); el tramo "
                 "claro de la derecha es el 10 % que más tarda.", className="range-metric__caption"),
    ])
