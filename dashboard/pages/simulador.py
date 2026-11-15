"""
dashboard/pages/simulador.py  -  pagina del dashboard multipagina (14-nov-2026)
"Simulador integral del hospital": el hospital en operacion continua. UN SOLO motor de agentes
(src/simulador_integral.py, que extiende el Monte Carlo validado de A5 hacia atras: de la cama a la llegada)
emite tres vistas sincronizadas del MISMO paciente sintetico: la demanda que llega, la cola de espera de cama
y la ocupacion con sus altas diarias. Antes esas vistas vivian en tres herramientas separadas (/pronostico,
/paciente y /camas); esta pagina las une sobre un solo motor, sin encadenar los tres modelos en serie (eso
rompia los supuestos de cada uno - ver la ficha tecnica y docs/simulador_integral.md).

REUTILIZA POR COMPLETO src/simulador_integral.py (simular_integral), que a su vez reutiliza el motor A5
(simulacion_camas_montecarlo.py) y el pronostico (modelo_pronostico.py). Importar es liviano: el backtest y la
proyeccion oficial solo corren al ejecutar el script directamente.

Mismo patron visual que pages/camas.py: panel de sliders a la izquierda, boton "Simular" (los sliders son
Input: las graficas se actualizan solas al mover cualquier control), dcc.Store intermedio, un callback corre el motor y otro redibuja con el tema. Ids con prefijo "simint-".
"""
import sys
from pathlib import Path

import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, dcc, html
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import simulador_integral as si  # noqa: E402  (import liviano: no corre backtest ni proyeccion)
import simulacion_camas_montecarlo as scm  # noqa: E402
import tema_graficos as tg  # noqa: E402

dash.register_page(__name__, path="/simulador", name="Simulador integral", title="Simulador integral - HUN", order=7)

GRIS, AZUL, NARANJA, VERDE, ROJO = "#6b6b6b", "#2a6fb0", "#eb6834", "#2e8b57", "#c0392b"
N_REP_INTERACTIVO = 200
PLAZOS = [("30 días", 30), ("90 días", 90), ("6 meses", 182)]
SERIES = list(si.SERIES_SALIDA)

INFO_SLIDER = {
    "llegadas": "Sube o baja TODA la demanda un % fijo: las llegadas al hospital y, a través de los agentes "
                "(cada llegada se hospitaliza según su perfil), también los ingresos a cama. Es el escenario B "
                "del plan mínimo visto desde la puerta de entrada.",
    "estancia": "Sube o baja cuánto dura cada estancia un % fijo (escenario C del plan mínimo = −5 %). Es la "
                "palanca más barata: mueve la ocupación casi tanto como +10 camas físicas.",
    "espera": "Sube o baja la espera de cama de cada paciente un % fijo. OJO: mueve la COLA (cuántos esperan a "
              "la vez), no la ocupación de camas — la cama se ocupa igual, solo que antes o después. Sirve para "
              "ver cuánta presión de sala de espera quitaría reducir la espera.",
}

INFO_SLIDER.update({
    "entrenamiento": "Marca los modelos de la ficha A9 con que quieres entrenar el pronóstico; puedes marcar uno, varios o ninguno "
                     "(sin modelo: solo el calendario). Cada uno entra solo en la serie donde A9 lo probó: dengue y lluvia en las "
                     "llegadas; curva del año, respiratorias y diarreas en los ingresos a cama. Mueve las tres gráficas.",
    "casos": "Aparece un deslizador por cada modelo marcado (la curva del año no tiene caso). Cada caso tiene su propia escala, "
             "sacada de lo que de verdad pasó en 2023–2025 frente a lo normal de esa época del año: «alto» es una semana más alta "
             "que 3 de cada 4, «muy alto» que 9 de cada 10, «grave» que 19 de cada 20 y «récord» la más alta que hubo. Solo "
             "aparecen los niveles que existieron en ese caso. El efecto es el medido en esas semanas, descontando el calendario, "
             "la forma del año y los otros casos, así que vale igual en cualquier mes. Es una asociación, no una causa.",
})
def texto_efecto(caso):
    """Escala del caso y cuanto cambian llegadas e ingresos en su nivel mas alto."""
    niveles = si.niveles_caso(caso)
    escala = " · ".join(f"{n} {'+' if v > 0 else '−' if v < 0 else ''}{abs(v)} %" for n, v in niveles if n != "Normal")
    nombre, tope = niveles[-1]
    ef = lambda serie: f"{'+' if si.efecto_aplicado(caso, serie, tope) >= 0 else '−'}{abs(si.efecto_aplicado(caso, serie, tope)):.1f} %".replace(".", ",")
    return [html.Div(f"Sobre lo normal: {escala}"),
            html.Div(f"En «{nombre.lower()}»: llegadas {ef('llegadas')} · ingresos {ef('ingresos')}")]


def deslizador_caso(caso):
    niveles = si.niveles_caso(caso)
    cero = [n for n, _ in niveles].index("Normal")
    marcas = {i - cero: n for i, (n, _) in enumerate(niveles)}
    return html.Div([html.Div(si.CASOS[caso], style={"fontSize": "13px", "fontWeight": 600, "marginBottom": "2px"}),
                     dcc.Slider(id={"type": "simint-caso", "caso": caso}, min=min(marcas), max=max(marcas), step=1, value=0, marks=marcas),
                     html.Div(texto_efecto(caso), style={"fontSize": "11px", "color": GRIS, "marginTop": "2px"})])


def error_modelo(m):
    serie = si.MODELOS_A9[m][1]
    con, sin = si.ERROR_MODELOS.get((serie, m)), si.ERROR_MODELOS.get((serie, "ninguno"))
    if not con or not sin:
        return ""
    f = lambda x: f"{x:.1f} %".replace(".", ",")
    return f" Error en la prueba (ene–abr 2026): {f(con[1])}, sin modelo {f(sin[1])}; en la validación: {f(con[0])} y {f(sin[0])}."


ETAPAS_PIPELINE = [
    ("1. Pronóstico de demanda", "Las llegadas diarias salen de una distribución de Poisson alrededor del "
     "pronóstico validado de llegadas (modelo_pronostico.py, el mismo de la página Pronóstico), entrenado solo "
     "con el periodo confiable (hasta el 9-abr-2026)."),
    ("2. Perfil de cada llegada", "Cada llegada recibe un perfil (grupo de edad × ruta: Urgencias / Treatment "
     "urgency / Ambulatorio) sorteado de la mezcla real de 2025 — el mismo criterio de perfiles del motor de "
     "camas (A5)."),
    ("3. ¿Va a cama?", "Cada llegada se hospitaliza con la probabilidad histórica de su perfil (P(cama|perfil), "
     "de tabla_episodios con estancias únicas), calibrada con un factor global (kappa) para que el nivel "
     "esperado coincida con el pronóstico validado de ingresos a cama. Los ingresos EMERGEN de los agentes: no "
     "se fuerza una cuota diaria con un ranking (el orden de llegada casi no predice el orden de cama: 53 % de "
     "pares en orden, azar 50 %)."),
    ("4. Trayectoria real sorteada", "A cada futuro hospitalizado se le sortea la trayectoria completa de un "
     "paciente REAL de su mismo perfil (hora de llegada, espera de cama y estancia del MISMO paciente "
     "histórico, 2024-2025), suavizada con ruido de Silverman — muestreo, no predicción puntual: asignar la "
     "predicción del estimador comprimiría la varianza y daría bandas falsamente angostas."),
    ("5. El día a día", "cama = llegada + espera; alta = cama + estancia. La ocupación se acumula por día "
     "(misma convención validada de A5) y la cola de espera por HORA (como la cola real observada). Se siembra "
     "el día 0 con el censo real en cama y la cola real del corte."),
    ("Opcional: modelos y casos", "Se pueden marcar modelos de la ficha A9 (forma del año) para entrenar el pronóstico, cada uno en "
     "la serie donde A9 lo probó, y para cada modelo marcado decir cuánto está su caso por encima o por debajo de lo normal. El "
     "caso multiplica las llegadas y los ingresos a cama por su efecto propio medido en 2023–2025 (src/medir_casos.py). Sin nada marcado, el "
     "motor es el de siempre."),
    ("6. Puerta de validación", "El simulador integrado re-pasó el backtest de ocupación del motor A5 "
     "(ene a 9-abr-2026 entrenado hasta dic-2025) y además reprodujo la cola real y las altas diarias — las "
     "cifras están en la tabla de abajo."),
]

TABLA_DECISIONES = [
    ("Encadenar los 3 módulos en serie (pronóstico → estimador de espera → Monte Carlo)", "No entra",
     "Cada módulo se construyó para una población distinta: el estimador de espera solo vio pacientes que "
     "recibieron cama (no sabe decir \"este no necesita cama\") y el ~87 % de las llegadas atendidas se va de "
     "alta desde urgencias. Encadenarlos rompía los supuestos de cada uno."),
    ("Llenar la cuota diaria de camas con un ranking de probabilidad", "No entra",
     "Reinventa una fila de prioridad que los datos rechazan: el orden de llegada casi no predice el orden de "
     "cama (53 % de pares consecutivos en orden; el azar da 50 %) y la espera es individual, no del momento "
     "(el día de llegada explica el 0,1 % de la espera)."),
    ("\"Pacientes sin cama\" = llegadas − ingresos a cama", "No entra",
     "Esa resta no es la cola: es sobre todo gente que nunca iba a necesitar cama. La cola simulada se "
     "construye agente por agente (entre su llegada y su cama) y se validó contra la cola real observada."),
    ("Usar el estimador de espera (A6) como predictor dentro del motor", "No entra",
     "Asignar a cada agente la predicción puntual comprime la varianza y daña las bandas. La espera se SORTEA "
     "de trayectorias reales del perfil; A6 sigue siendo la consulta para pacientes reales (página Paciente)."),
    ("Ingresos a cama emergentes de los agentes, calibrados (kappa)", "Entra",
     "Los conteos emergen de llegadas × P(cama|perfil) × espera sorteada, y un factor global los calibra "
     "contra el pronóstico validado de ingresos — coherente con un modelo de agentes y verificado en el "
     "backtest."),
    ("Trayectoria conjunta (espera y estancia del MISMO paciente real)", "Entra",
     "Conserva la correlación real espera-estancia (+9 % de estancia por desviación de espera, "
     "docs/factores_estancia.md) que se perdería sorteando cada tiempo por separado."),
]


def info_badge(texto):
    return html.Span(className="info-badge tooltip-trigger", children=[
        "i", html.Span(texto, className="tooltip-content")])


def campo_slider(etiqueta, clave_info, control):
    return html.Div(className="camas-slider-group", children=[
        html.Span(className="camas-slider-group__label", children=[etiqueta, info_badge(INFO_SLIDER[clave_info])]),
        control,
    ])


def tarjeta(id_valor, caption):
    return html.Div(className="metric-card", style={"flex": "1 1 150px", "textAlign": "center", "padding": "12px 10px"},
                    children=[
                        html.Div(id=id_valor, style={"fontSize": "24px", "fontWeight": 700}),
                        html.Div(caption, style={"fontSize": "11.5px", "color": GRIS, "marginTop": "2px"}),
                    ])


def panel_interpretacion():
    return html.Details(className="page-section", children=[
        html.Summary("¿Cómo se interpreta?"),
        html.Div(style={"padding": "10px 4px 2px", "display": "grid", "gap": "14px", "fontSize": "13.5px", "lineHeight": "1.6"}, children=[
            html.Div([html.Div("Qué estás viendo", style={"fontWeight": 700, "color": AZUL, "marginBottom": "3px"}),
                      html.Div("La operación típica proyectada del hospital, día a día, desde el último dato "
                               "confiable: cuántos pacientes llegan, cuántos entran a cama y cuántos salen "
                               "(arriba), cuántas camas quedan ocupadas frente a las 106 reales (centro) y "
                               "cuántos pacientes están esperando cama a la vez (abajo). Las tres vistas salen "
                               "de los MISMOS pacientes simulados: el que ves esperando es el mismo que después "
                               "ocupa la cama y el mismo que sale de alta.")]),
            html.Div([html.Div("Cómo se calculó", style={"fontWeight": 700, "color": AZUL, "marginBottom": "3px"}),
                      html.Div("Con un motor de agentes montado sobre la simulación de Monte Carlo validada del "
                               "planeador de camas: cada llegada simulada recibe un perfil real (edad × ruta), "
                               "se hospitaliza con la probabilidad histórica de su perfil y, si va a cama, "
                               "hereda la trayectoria completa (hora de llegada, espera y estancia) de un "
                               "paciente real parecido. Se repite "
                               f"{N_REP_INTERACTIVO} veces para ver el rango (las cifras oficiales usan 1.000).")]),
            html.Div([html.Div("Qué significa para el hospital", style={"fontWeight": 700, "color": AZUL, "marginBottom": "3px"}),
                      html.Div("Permite ver el efecto de una palanca sobre TODO el flujo a la vez: bajar la "
                               "estancia descarga las camas (y con ellas, con el tiempo, la espera); bajar la "
                               "espera descarga la sala de urgencias (la cola) aunque las camas sigan igual de "
                               "llenas; más demanda empuja las tres curvas. Es la base sobre la que se pueden "
                               "montar alertas operativas (fase 2) y recomendaciones (fase 3).")]),
            html.Div([html.Div("Qué NO dice", style={"fontWeight": 700, "color": NARANJA, "marginBottom": "3px"}),
                      html.Div("No predice un día concreto ni un paciente concreto: reproduce patrones "
                               "(fidelidad estadística), no el futuro exacto. La cola solo cuenta a quienes "
                               "terminarán hospitalizados — es una COTA INFERIOR de la presión real de "
                               "urgencias, que no se puede simular con estos datos (36-42 % de las etapas de "
                               "urgencias no tiene hora de fin). Y es asociación proyectada sobre el patrón "
                               "histórico, no una garantía de que ese patrón se mantenga.")]),
        ]),
    ])


def panel_tecnico():
    pasos = [html.Div(className="pipeline__step tooltip-trigger", children=[
                html.Div(className="pipeline__dot"), html.Div(t, className="pipeline__label"),
                html.Span(d, className="tooltip-content")])
             for t, d in ETAPAS_PIPELINE]
    filas_decision = [html.Tr([html.Th("Qué se consideró"), html.Th("Resultado"), html.Th("Por qué")])] + [
        html.Tr([html.Td(v), html.Td(r, style={"fontWeight": 700, "color": VERDE if r == "Entra" else GRIS}), html.Td(pq)])
        for v, r, pq in TABLA_DECISIONES]
    return html.Details(className="page-section", children=[
        html.Summary("Ficha técnica del simulador integral"),
        html.Div(style={"padding": "14px 4px 4px", "display": "grid", "gap": "22px"}, children=[
            html.Div([
                html.Div("Etapas del motor (pasa el mouse sobre cada una)", style={"fontWeight": 700, "marginBottom": "4px"}),
                html.Div(className="pipeline", children=pasos),
            ]),
            html.Div([
                html.Div("Backtest integrado (puerta de validación): enero a 9-abr-2026, entrenado solo hasta dic-2025",
                         style={"fontWeight": 700, "marginBottom": "4px"}),
                html.Table(className="tech-table", children=[
                    html.Thead(html.Tr([html.Th("Serie"), html.Th("MAE"), html.Th("Cobertura banda 10-90 %"), html.Th("Referencia")])),
                    html.Tbody([
                        html.Tr([html.Td("Ocupación (camas)"), html.Td("9,3 camas"), html.Td(html.B("74,7 %")),
                                 html.Td("motor A5: 8,6 camas y 78,8 % — dentro de la tolerancia (hasta 1 cama "
                                         "peor) y de la meta 70-90 %")]),
                        html.Tr([html.Td("Cola de espera"), html.Td("4,3 pacientes"), html.Td("70,7 %"),
                                 html.Td("cola real media del periodo: 27,4 (histórica ~26) — la reproduce")]),
                        html.Tr([html.Td("Ingresos a cama/día (emergentes)"), html.Td("4,0"), html.Td("79,8 %"),
                                 html.Td("sesgo +0,7: los ingresos que emergen de los agentes cuadran con los reales")]),
                        html.Tr([html.Td("Altas/día"), html.Td("4,7"), html.Td("68,7 %"), html.Td("sesgo +0,5")]),
                        html.Tr([html.Td("Llegadas/día"), html.Td("18,8"), html.Td("58,8 %"),
                                 html.Td("banda angosta: solo lleva el ruido de Poisson, no el error del "
                                         "pronóstico (límite heredado de A5, declarado)")]),
                    ]),
                ], style={"width": "100%", "marginBottom": "6px"}),
                html.Div("La puerta era no empeorar el backtest de ocupación del motor A5 (MAE 8,6 camas, "
                         "cobertura 78,8 %) y además reproducir la cola real (~26 pacientes en promedio, "
                         "docs/capacidad_efectiva.md) y las altas diarias. Las cifras de la tabla salen de "
                         "resultados/tablas/simint_backtest.csv (1.000 repeticiones).",
                         style={"fontSize": "12px", "color": GRIS}),
            ], className="tech-table-wrap"),
            html.Div([
                html.Div("Decisiones de diseño (qué se descartó y por qué)", style={"fontWeight": 700, "marginBottom": "6px"}),
                html.Table(filas_decision, style={"width": "100%", "fontSize": "12.5px", "borderCollapse": "collapse"}),
            ]),
            html.Div([
                html.Div("Límites", style={"fontWeight": 700, "color": NARANJA, "marginBottom": "4px"}),
                html.Ul(style={"fontSize": "12.5px", "color": GRIS, "lineHeight": "1.6", "paddingLeft": "18px"}, children=[
                    html.Li("La cola simulada solo contiene futuros hospitalizados (cota inferior de la presión "
                            "real); la congestión completa de urgencias no se puede simular con estos datos."),
                    html.Li("P(cama|perfil) es constante por día y la calibración (kappa) es global por corrida, "
                            "no por día de la semana."),
                    html.Li("Los pacientes sembrados (ya en cama / ya esperando el día de corte) reciben tiempos "
                            "completos del bootstrap, sin corregir el sesgo de selección — solo afecta los "
                            "primeros días."),
                    html.Li("Las llegadas incluyen ~4 % de réplicas conocidas (cota, CLAUDE.md 4.13); el nivel "
                            "absoluto de llegadas es ligeramente alto, su variación no."),
                    html.Li("Asociación, no causa; periodo confiable hasta el 9-abr-2026; 106 camas es la cifra "
                            "del HUN sin fecha de corte conocida."),
                ]),
                html.Div("Detalle completo: docs/simulador_integral.md (y docs/modelo_camas.md para el motor A5 de base).",
                         style={"fontSize": "11px", "color": GRIS, "marginTop": "6px"}),
            ]),
        ]),
    ])


def layout():
    return html.Div(className="page-container", children=[
        html.Div(className="page-head", children=[
            html.H2("Simulador integral: el hospital en operación continua"),
            html.P("Un solo motor de agentes sigue a cada paciente simulado por todo su recorrido — llega, "
                   "espera cama, la ocupa y sale de alta — y muestra las tres vistas sincronizadas: demanda, "
                   "cola de espera y ocupación. Cambia una palanca y ve cómo reacciona el flujo completo.",
                   className="page-head__sub"),
        ]),

        html.Div(className="control-row", children=[
            html.Div(className="control-group", children=[
                html.Span("¿Hasta cuándo quieres ver?", className="control-group__label"),
                dcc.RadioItems(id="simint-plazo", className="pill-switch",
                               options=[{"label": n, "value": d} for n, d in PLAZOS], value=90)]),
        ]),

        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "32px", "alignItems": "stretch"}, children=[
            html.Div(className="form-panel", style={"flex": "0 0 320px", "display": "flex", "flexDirection": "column"}, children=[
                html.Div(style={"display": "flex", "flexDirection": "column", "justifyContent": "space-evenly",
                                "flex": "1 1 auto", "gap": "26px"}, children=[
                    campo_slider("Demanda (llegadas)", "llegadas", dcc.Slider(id="simint-ajuste_llegadas", min=-30, max=30, step=5, value=0)),
                    campo_slider("Estancia en cama", "estancia", dcc.Slider(id="simint-ajuste_estancia", min=-20, max=20, step=5, value=0)),
                    campo_slider("Espera de cama", "espera", dcc.Slider(id="simint-ajuste_espera", min=-30, max=30, step=5, value=0)),
                    campo_slider("Entrenar el pronóstico con (ficha A9)", "entrenamiento", dcc.Checklist(
                        id="simint-entrenamiento", value=[], labelStyle={"display": "block", "margin": "3px 0"},
                        inputStyle={"marginRight": "8px"},
                        options=[{"label": si.MODELOS_A9[k][0], "value": k} for k in si.MODELOS_DISPONIBLES])),
                    html.Div(id="simint-entrenamiento-texto", style={"fontSize": "12px", "color": GRIS, "marginTop": "-18px"}),
                    html.Div(id="simint-casos-bloque", style={"display": "none"}, children=[
                        campo_slider("Casos de los modelos marcados", "casos", html.Div()),
                        html.Div(id="simint-casos", style={"display": "flex", "flexDirection": "column", "gap": "14px"}),
                    ]),
                ]),
                html.Div(style={"marginTop": "18px"}, children=[
                    html.Button("Simular", id="simint-simular", n_clicks=0, className="btn-primary", style={"width": "100%"}),
                    html.Div(id="simint-nota", style={"fontSize": "12px", "marginTop": "10px"}),
                ]),
            ]),
            html.Div(style={"flex": "1 1 600px"}, children=[
                html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "12px", "marginBottom": "10px"}, children=[
                    tarjeta("simint-m_llegadas", "llegadas al hospital / día"),
                    tarjeta("simint-m_ingresos", "entran a cama / día"),
                    tarjeta("simint-m_ocupacion", "camas ocupadas (media)"),
                    tarjeta("simint-m_cola", "esperando cama a la vez"),
                ]),
                dcc.Graph(id="simint-grafico", config={"displaylogo": False}, style={"height": "640px"}),
            ]),
        ]),

        dcc.Store(id="simint-datos"),
        html.P("Los tres paneles salen de los mismos pacientes simulados (un solo motor). La cola solo cuenta "
               "futuros hospitalizados (cota inferior). Operación típica proyectada, no una predicción de días "
               "concretos. Asociación, no causa.", style={"fontSize": "11px", "color": GRIS, "marginTop": "10px"}),
        panel_interpretacion(),
        panel_tecnico(),
    ])


@callback(Output("simint-datos", "data"), Output("simint-nota", "children"),
          Input("simint-simular", "n_clicks"),
          Input("simint-ajuste_llegadas", "value"), Input("simint-ajuste_estancia", "value"),
          Input("simint-ajuste_espera", "value"), Input("simint-plazo", "value"), Input("simint-entrenamiento", "value"),
          Input({"type": "simint-caso", "caso": ALL}, "value"), State({"type": "simint-caso", "caso": ALL}, "id"))
def correr_simulacion(_, pct_lleg, pct_est, pct_esp, dias, modelos, valores_casos, ids_casos):
    casos, nombres = {}, {}
    for i, v in zip(ids_casos or [], valores_casos or []):
        if v and i["caso"] in (modelos or []):
            niveles = si.niveles_caso(i["caso"])
            nombre, pct = niveles[[n for n, _ in niveles].index("Normal") + v]
            casos[i["caso"]], nombres[i["caso"]] = pct, nombre
    fechas, out, info = si.simular_integral(scm.ULTIMO_CONFIABLE, dias,
                                            ajuste_llegadas=1 + pct_lleg / 100, ajuste_estancia=1 + pct_est / 100,
                                            ajuste_espera=1 + pct_esp / 100, n_rep=N_REP_INTERACTIVO,
                                            modelos=modelos or [], casos=casos)
    data = {"fechas": [str(f.date()) for f in fechas]}
    for s in SERIES:
        for p in (10, 50, 90):
            data[f"{s}_p{p}"] = np.percentile(out[s], p, axis=0).tolist()
    data["medias"] = {s: float(out[s].mean()) for s in SERIES}
    data["pct_sat"] = round(100 * float((out["total"] > scm.CAPACIDAD["total"]).mean()), 1)
    elegidos = ", ".join(si.MODELOS_A9[m][0].lower() for m in (modelos or [])) or "sin modelo (solo el calendario)"
    resumen = [html.B("Entrenado con: "), elegidos[0].upper() + elegidos[1:], "."]
    if casos:
        detalle = ", ".join(f"{si.CASOS[k].lower()} {nombres[k].lower()} ({'+' if v > 0 else '−'}{abs(v)} % sobre lo normal)"
                            for k, v in casos.items())
        cl, ci = 100 * (info["factor_llegadas"] - 1), 100 * (info["factor_ingresos"] - 1)
        signo = lambda x: f"{'+' if x >= 0 else '−'}{abs(x):.1f} %".replace(".", ",")
        resumen += [" ", html.B("Casos: "), f"{detalle} → llegadas {signo(cl)}, ingresos a cama {signo(ci)}."]
    nota_casos = html.Div(resumen, style={"marginBottom": "8px"})
    nota = ""
    if pct_esp < 0:
        nota = html.Div([html.B("Ojo: "), "reducir la espera descarga la cola (sala de urgencias), pero NO libera "
                         "camas: la cama se ocupa igual, solo que antes. Para liberar camas, la palanca es la "
                         "estancia."], style={"border": f"1px solid {NARANJA}", "borderRadius": "6px", "padding": "6px 10px"})
    elif pct_est < 0:
        nota = html.Div([html.B("R7 (recomendaciones): "), "bajar la estancia 5 % libera ~5 camas (ley de Little y "
                         "simulación A5); la palanca más barata antes de ampliar capacidad."],
                        style={"border": f"1px solid {VERDE}", "borderRadius": "6px", "padding": "6px 10px"})
    return data, html.Div([nota_casos, nota]) if nota else nota_casos


@callback(Output("simint-entrenamiento-texto", "children"), Input("simint-entrenamiento", "value"))
def explicar_entrenamiento(modelos):
    if not modelos:
        return "Sin modelo: solo el calendario (día de la semana, festivos, Semana Santa y Carnaval)."
    return html.Ul([html.Li(si.MODELOS_A9[m][2] + error_modelo(m)) for m in modelos], style={"margin": "0", "paddingLeft": "18px"})


@callback(Output("simint-casos", "children"), Output("simint-casos-bloque", "style"), Input("simint-entrenamiento", "value"))
def armar_casos(modelos):
    con_caso = [m for m in (modelos or []) if m in si.CASOS]
    return [deslizador_caso(m) for m in con_caso], ({"display": "block"} if con_caso else {"display": "none"})


@callback(Output("simint-grafico", "figure"),
          Output("simint-m_llegadas", "children"), Output("simint-m_ingresos", "children"),
          Output("simint-m_ocupacion", "children"), Output("simint-m_cola", "children"),
          Input("simint-datos", "data"), State("theme-store", "data"))
def mostrar(data, tema):
    if not data:
        return go.Figure(), "", "", "", ""
    fechas = pd.to_datetime(data["fechas"])
    cap = scm.CAPACIDAD["total"]

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        row_heights=[0.28, 0.42, 0.30],
                        subplot_titles=("Flujo diario: llegan, entran a cama, salen de alta",
                                        f"Camas ocupadas (capacidad: {cap})",
                                        "Pacientes esperando cama a la vez (cota inferior)"))

    fig.add_trace(go.Scatter(x=fechas, y=data["llegadas_p50"], mode="lines", line=dict(color=GRIS, width=1.6),
                             name="Llegadas al hospital",
                             hovertemplate="%{x|%d-%m}<br>%{y:.0f} llegadas<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=fechas, y=data["ingresos_cama_p50"], mode="lines", line=dict(color=VERDE, width=1.8),
                             name="Entran a cama",
                             hovertemplate="%{x|%d-%m}<br>%{y:.0f} entran a cama<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=fechas, y=data["altas_p50"], mode="lines", line=dict(color=NARANJA, width=1.8),
                             name="Salen de alta",
                             hovertemplate="%{x|%d-%m}<br>%{y:.0f} altas<extra></extra>"), row=1, col=1)

    fig.add_trace(go.Scatter(x=fechas, y=data["total_p90"], mode="lines", line=dict(width=0), showlegend=False,
                             hoverinfo="skip"), row=2, col=1)
    fig.add_trace(go.Scatter(x=fechas, y=data["total_p10"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(42,111,176,0.15)", name="Banda 10-90 %", hoverinfo="skip"), row=2, col=1)
    fig.add_trace(go.Scatter(x=fechas, y=data["total_p50"], mode="lines", line=dict(color=AZUL, width=2),
                             name="Camas ocupadas (mediana)",
                             hovertemplate="%{x|%d-%m}<br>%{y:.0f} camas ocupadas<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=fechas, y=[cap] * len(fechas), mode="lines",
                             line=dict(color=NARANJA, dash="dash"), name=f"Capacidad HUN ({cap})",
                             hoverinfo="skip"), row=2, col=1)

    fig.add_trace(go.Scatter(x=fechas, y=data["cola_p90"], mode="lines", line=dict(width=0), showlegend=False,
                             hoverinfo="skip"), row=3, col=1)
    fig.add_trace(go.Scatter(x=fechas, y=data["cola_p10"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(192,57,43,0.13)", showlegend=False, hoverinfo="skip"), row=3, col=1)
    fig.add_trace(go.Scatter(x=fechas, y=data["cola_p50"], mode="lines", line=dict(color=ROJO, width=2),
                             name="Esperando cama (mediana)",
                             hovertemplate="%{x|%d-%m}<br>%{y:.0f} esperando cama<extra></extra>"), row=3, col=1)

    fig.update_layout(template="simple_white", legend=dict(orientation="h", y=-0.08),
                      margin=dict(l=40, r=20, t=40, b=30), hovermode="x unified")
    for ann in fig.layout.annotations:
        ann.font = dict(size=12)
        ann.x = 0.0
        ann.xanchor = "left"

    m = data["medias"]
    tg.aplicar(fig, tg.es_oscuro(tema))
    return (fig,
            f"{m['llegadas']:.0f}",
            html.Span([f"{m['ingresos_cama']:.0f}", html.Span(f"  (salen {m['altas']:.0f})",
                       style={"fontSize": "13px", "color": GRIS})]),
            html.Span([f"{m['total']:.0f}", html.Span(f"  ({data['pct_sat']:.0f} % días-rep. sobre {cap})",
                       style={"fontSize": "12px", "color": ROJO if data["pct_sat"] > 50 else GRIS})]),
            f"{m['cola']:.0f}")
