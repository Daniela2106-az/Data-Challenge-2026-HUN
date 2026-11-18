"""
dashboard/pages/simulador.py  -  pagina del dashboard multipagina (14-nov-2026; rediseno del 16 y 17-nov-2026)
"Simulador integral del hospital": el hospital en operacion continua. UN SOLO motor de agentes
(src/simulador_integral.py, que extiende el Monte Carlo validado de A5 hacia atras: de la cama a la llegada)
emite tres vistas sincronizadas del MISMO paciente sintetico: la demanda que llega, la cola de espera de cama
y la ocupacion con sus altas diarias. Antes esas vistas vivian en tres herramientas separadas (/pronostico,
/paciente y /camas); esta pagina las une sobre un solo motor, sin encadenar los tres modelos en serie (eso
rompia los supuestos de cada uno - ver la ficha tecnica y docs/simulador_integral.md).

REDISEÑO 16-nov: sidebar de configuracion colapsable, reproductor en vez de metricas, radiografia con
perfiles completos y filtros, vistas todo/flujo/camas/espera, solo el boton Reproducir dispara la simulacion.

REDISEÑO 17-nov (ajustes visuales pedidos):
  - La radiografia va ANTES del grafico (orden: alerta, reproductor, radiografia, grafico).
  - El grafico NO dibuja el futuro: se recorta de verdad (server-side segun el cursor al reconstruir la
    figura, cliente vía Plotly.restyle en cada tick) en vez de un velo translucido encima.
  - El sidebar de configuracion es un boton flotante (46x46) que se EXPANDE SOBRE el contenido (position:
    absolute, no empuja los graficos/radiografia, que usan todo el ancho disponible).
  - Filtros de edad/ruta/sexo en una sola linea con separadores finos, sin titulos, y se activan tambien al
    pasar el mouse (no solo clic). (20-nov: se quito la activacion por hover, ver panel_filtros — quedaba
    un filtro pegado sin querer y la radiografia dejaba de coincidir con el grafico, que nunca se filtra.)
  - Sliders: sin "R7"/"A"/"D" en el encabezado; sin fondo azul al pasar el mouse (solo aparecen el punto y
    los numeros); agrupados en 4 secciones (Operación, Estrés, Optimización, Factores externos); los casos
    de dengue/lluvia/ira/eda son sliders siempre visibles (sin casilla ni texto alrededor, resumido en un
    solo icono de info junto al encabezado del grupo); se quito "curva suave del año".

REUTILIZA POR COMPLETO src/simulador_integral.py (simular_integral), que a su vez reutiliza el motor A5
(simulacion_camas_montecarlo.py) y el pronostico (modelo_pronostico.py). Importar es liviano: el backtest y la
proyeccion oficial solo corren al ejecutar el script directamente.
"""
import sys
from pathlib import Path

import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, clientside_callback, dcc, html
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import simulador_integral as si  # noqa: E402  (import liviano: no corre backtest ni proyeccion)
import simulacion_camas_montecarlo as scm  # noqa: E402
import tema_graficos as tg  # noqa: E402
import catalogo as _catalogo  # noqa: E402
from componentes import mensaje, metodo, secciones  # noqa: E402

dash.register_page(__name__, path="/simulador", name="Simulador integral", title="Simulador integral - HUN", order=7)

GRIS, AZUL, NARANJA, VERDE, ROJO, ROSA = "#6b6b6b", "#2a6fb0", "#eb6834", "#2e8b57", "#c0392b", "#c2185b"
N_REP_INTERACTIVO = 200
N_REP_HORARIO = 300
# Alertas del simulador. Hay dos gravedades: AVISO (media) y CRITICO (alta). Las dos frenan la simulacion, pero cada alerta (tipo y gravedad) se muestra UNA SOLA VEZ por corrida.
# Como cada alerta se muestra una sola vez por corrida, una condicion que dura casi todo el tiempo (superar las 106 camas es lo normal en esta simulacion: la probabilidad
# tiene mediana 68 %) avisa una vez y no vuelve a molestar; lo critico esta por encima de lo tipico (en un caso normal de 90 dias:
# probabilidad casi nunca mayor de 84 %, camas ocupadas mediana 111 y p90 114,5, cola mediana 25 y p99 28). Criterios de esta pagina, no cifras validadas.
UMBRAL_ALERTA_MEDIA = 50                 # saturacion: aviso cuando es mas probable que si superar la capacidad a 48 h
UMBRAL_ALERTA = 84                       # saturacion: critico (solo se alcanza en los picos de un caso normal)
UMBRAL_OCUPACION = 107                   # ocupacion: aviso (camas ocupadas, mediana de las repeticiones; alerta A2: 107 a 109 camas)
UMBRAL_OCUPACION_CRITICA = 118           # ocupacion: critico
UMBRAL_COLA = 28                         # cola: aviso (pacientes esperando cama a la vez; lo habitual son ~25)
UMBRAL_COLA_CRITICA = 33                 # cola: critico (el percentil 90 real de la cola es 33)
ARRANQUE_SIN_ALERTAS = 7                 # los primeros dias vienen de la siembra con el censo real y no generan alertas: 7 (4 si el plazo es de 2 semanas o menos, porque la siembra deja las camas por encima de 118 los primeros 3 dias; 12 h en la vista horaria)

# Escenarios con nombre: cada uno fija las palancas (el simulador mueve los controles y despues recalcula). Los factores externos no cambian.
PALANCAS_CERO = {"llegadas": 0, "estancia": 0, "espera": 0, "capacidad": 106, "estres": 0, "recorte": 0, "adelanto": 0}
ESCENARIOS = {
    "hoy": ("Hoy (sin cambios)", "", {}),
    "optimo": ("Operación óptima", "Aplica dos recomendaciones a la vez: revisar las estancias de más de 14 días (R7, 15 % menos en ellas) y adelantar a la mañana el 30 % "
                                    "de las altas de la tarde (R4). No cambia la demanda ni la estancia del resto de pacientes.", {"recorte": 15, "adelanto": 30}),
}
ETIQUETA_PALANCA = {"llegadas": "Demanda de llegadas", "estancia": "Estancia en cama", "espera": "Espera de cama", "estres": "Perfiles de estrés",
                    "recorte": "Recorte de estancias largas", "adelanto": "Adelanto de altas a la mañana"}
PLAZOS = [("3 días (hora a hora)", "72h"), ("1 semana", 7), ("30 días", 30), ("90 días", 90), ("6 meses", 182), ("1 año", 365)]
SERIES = list(si.SERIES_SALIDA)

# Factores externos (dengue, lluvia, infecciones respiratorias, diarreas) SIEMPRE entrenan su regresor
# estacional (ya no hay casilla para activarlos); el slider de cada uno elige la severidad del caso (17-nov).
# "curva suave del año" se retiro de esta pagina (seguia disponible en el motor, no se ofrece aqui).
def _recomendaciones_por_numero():
    """{numero: (titulo corto, primer paso)} de las recomendaciones (datos/tablas_dashboard/recomendaciones_tabla.csv)."""
    try:
        r = _catalogo.recomendaciones()
        return {int(f.prioridad): (f.titulo_accion, str(f.que_cambiar).split("|")[0]) for f in r.itertuples()}
    except Exception:
        return {}


def _alertas_dia(fechas, total_p50, cola_p50, probs48, capacidad, horas=False):
    """Reglas de negocio sobre las series simuladas: la alerta de cada dia (o de cada hora), o None. Cada una dice su tipo, su gravedad (media: aviso;
    alta: critica, frena la reproduccion), por que salto y la recomendacion de la que se deriva (con su primer paso).
    Saturacion de camas (probabilidad de superar la capacidad a 48 h): aviso desde 50 %, critica desde 84 % (R4 y R7). Ocupacion: aviso desde 107 camas y critica
    desde 118 (R3 y R4). Cola de espera: aviso desde 28 pacientes y critica desde 33 (R5 y R6). Si varias coinciden, gana la mas grave."""
    rec = _recomendaciones_por_numero()
    acc = lambda *ns: [f"R{n} · {rec.get(n, ('',))[0]}".rstrip(" ·") for n in ns]
    paso = lambda n: rec.get(n, ("", ""))[1]
    salida = []
    for i, f in enumerate(fechas):
        p, o, c = float(probs48[i]), float(total_p50[i]), float(cola_p50[i])
        cand = []
        if i < (12 if horas else (ARRANQUE_SIN_ALERTAS if len(fechas) > 14 else 4)):
            salida.append(None)
            continue
        if p >= UMBRAL_ALERTA_MEDIA:
            cand.append(("Alta" if p >= UMBRAL_ALERTA else "Media", 0, {
                "tipo": "saturacion", "titulo": "Riesgo de saturar las camas",
                "texto": f"{p:.0f} % de probabilidad de superar las {capacidad} camas dentro de 48 {'horas' if horas else 'horas (pasado mañana)'}.",
                "acciones": acc(4, 7), "paso": paso(4), "mejora": True, "rec": 4, "alerta": "A2"}))
        if o >= UMBRAL_OCUPACION:
            cand.append(("Alta" if o >= UMBRAL_OCUPACION_CRITICA else "Media", 1, {
                "tipo": "ocupacion", "titulo": "Ocupación alta",
                "texto": f"Se esperan unas {o:.0f} camas ocupadas, por encima de las {capacidad} del hospital.",
                "acciones": acc(3, 4), "paso": paso(3), "mejora": True, "rec": 3, "alerta": "A2"}))
        if c >= UMBRAL_COLA:
            cand.append(("Alta" if c >= UMBRAL_COLA_CRITICA else "Media", 2, {
                "tipo": "cola", "titulo": "Cola de espera larga",
                "texto": f"Unos {c:.0f} pacientes esperando cama a la vez, más de lo habitual (cerca de 26).",
                "acciones": acc(5, 6), "paso": paso(5), "mejora": False, "rec": 5, "alerta": "S1"}))
        if not cand:
            salida.append(None)
            continue
        g, _, a = sorted(cand, key=lambda x: (x[0] != "Alta", x[1]))[0]
        salida.append({**a, "gravedad": g})
    return salida


MODELOS_FIJOS = [k for k in ("dengue", "lluvia", "ira", "eda") if k in si.MODELOS_DISPONIBLES]

# Reproduccion con la granularidad natural de cada vista: hora para el horizonte de 3 dias, dia para 1
# semana/30 dias; en los horizontes largos (90/182/365 dias) el paso por defecto es semana o mes (para no
# hacer pesada la reproduccion), pero "1 dia" tambien queda disponible como opcion.
VELOCIDADES_POR_PLAZO = {
    "72h": ([{"label": "1 hora", "value": 1}, {"label": "6 horas", "value": 6}], 1),
    7:     ([{"label": "1 día", "value": 1}], 1),
    30:    ([{"label": "1 día", "value": 1}, {"label": "1 semana", "value": 7}], 1),
    90:    ([{"label": "1 día", "value": 1}, {"label": "1 semana", "value": 7}, {"label": "1 mes", "value": 30}], 7),
    182:   ([{"label": "1 día", "value": 1}, {"label": "1 semana", "value": 7}, {"label": "1 mes", "value": 30}], 7),
    365:   ([{"label": "1 día", "value": 1}, {"label": "1 semana", "value": 7}, {"label": "1 mes", "value": 30}], 30),
}
# La radiografia agrega por la MISMA unidad que el usuario elige en "simint-velocidad" (dia/semana/mes) — no
# por el plazo total. Antes seguia una tabla fija por plazo (GRANULARIDAD_RADIOGRAFIA, ya retirada) que
# ignoraba la velocidad elegida: con plazo=90 dias y velocidad "1 dia" la radiografia seguia sumando una
# semana completa (hasta ~1900 llegadas) mientras el grafico mostraba el valor de ESE dia (~260-300) al
# pasar el mouse — incongruencia reportada el 17-nov. Ahora, con velocidad "1 dia" la ventana es exactamente
# ese dia (debe coincidir con el hover del grafico); con "1 semana"/"1 mes" sigue siendo una suma, declarada
# en el titulo.
GRANULARIDAD_POR_VELOCIDAD = {1: "dia", 7: "semana", 30: "mes"}

INFO_SLIDER = {
    "llegadas": "Sube o baja TODA la demanda un % fijo: las llegadas al hospital y, a través de los agentes "
                "(cada llegada se hospitaliza según su perfil), también los ingresos a cama. Es el escenario B "
                "del plan mínimo visto desde la puerta de entrada.",
    "estancia": "Sube o baja cuánto dura cada estancia un % fijo (escenario C del plan mínimo = −5 %). Es la "
                "palanca más barata: mueve la ocupación casi tanto como +10 camas físicas.",
    "espera": "Sube o baja la espera de cama de cada paciente un % fijo. OJO: mueve la COLA (cuántos esperan a "
              "la vez), no la ocupación de camas — la cama se ocupa igual, solo que antes o después. Sirve para "
              "ver cuánta presión de sala de espera quitaría reducir la espera.",
    "recorte_largas": "R7 (recomendaciones): reduce ese % SOLO a las estancias de más de 14 días (revisión "
                      "semanal con gestión de casos). Son el 7 % de las estancias pero ocupan ~36 camas (34 % de "
                      "la ocupación, página Estancia). Recortarlas 15 % libera ~4-5 camas — comparable a bajar "
                      "TODAS las estancias 5 %, pero actuando solo sobre los largos.",
    "adelanto_altas": "Escenario A (página Altas): % de las altas de la tarde que pasan a la mañana. Efecto "
                      "INYECTADO del análisis ya medido (adelantar 30 % evita ~3 % del exceso de espera, cota "
                      "máx. 8 %): descarga la COLA, no libera camas — el motor no modela la mecánica interna "
                      "de asignación, aplica la estimación medida (límite declarado).",
    "mezcla_estres": "Escenario D (página Planeación de camas): concentra la mezcla de LLEGADAS hacia los "
                     "perfiles que históricamente más se quedan (mayores, Treatment urgency). 0 % = mezcla real "
                     "de 2025; 100 % = caso de estrés explícito, no un pronóstico.",
    "capacidad": "Capacidad hipotética total: mueve la franja del gráfico y el % de días saturados SIN volver a "
                 "simular (curva de capacidad de A5: para riesgo ≤ 10 % harían falta ~126 camas). No cambia el "
                 "tablero por grupo (88/18) ni ninguna otra cifra.",
}
INFO_FACTORES_EXTERNOS = (
    "Dengue, lluvia, infecciones respiratorias (IRA) y diarreas (EDA): formas del año tomadas de climatologías "
    "públicas (dengue y lluvia) y de SIVIGILA (IRA y EDA), siempre activas en el pronóstico de la serie que "
    "corresponde (dengue y lluvia en las llegadas; IRA y EDA en los ingresos a cama). Cada slider elige cuánto "
    "estuvo ese caso por encima o por debajo de lo normal, en la escala real de 2023 a 2025 («alto» = más alto "
    "que 3 de cada 4 semanas, «muy alto» que 9 de cada 10, «grave» que 19 de cada 20, «récord» el máximo "
    "histórico). El efecto es el medido en esas semanas, descontando calendario y forma del año, así que vale "
    "igual en cualquier mes. En «Normal» (0) el regresor sigue activo pero sin caso adicional. Es una "
    "asociación, no una causa; los datos externos llegan hasta 2025."
)

# Mezcla de estres (mismo espiritu que el escenario D de /camas pero sobre las LLEGADAS): pesos hacia los
# perfiles de mayor estancia mediana (edad por scm.resumen_reciente; ruta por la mediana de su pool).
_mediana_ruta_e = {r: float(np.median(np.concatenate([v for (g, t), v in scm.BOOTSTRAP_PERFIL.items() if t == r])))
                   for r in scm.RUTAS_HIST.index}
_peso_edad_e = scm.resumen_reciente["mediana"].reindex(list(si.EDAD_MARG_LLEG))
_peso_edad_e = (_peso_edad_e / _peso_edad_e.sum()).to_dict()
_peso_ruta_e = pd.Series(_mediana_ruta_e)
_peso_ruta_e = (_peso_ruta_e / _peso_ruta_e.sum()).to_dict()


def mezcla_estres(intensidad):
    """intensidad 0-1: 0 = mezcla real de llegadas de 2025 (None, el default del motor); 1 = concentrada en
    los perfiles de mayor estancia. Devuelve (mezcla_edad, mezcla_ruta) para simular_integral."""
    if not intensidad:
        return None, None
    me = {g: (1 - intensidad) * si.EDAD_MARG_LLEG[g] + intensidad * _peso_edad_e.get(g, 0) for g in si.EDAD_MARG_LLEG}
    mr = {r: (1 - intensidad) * si.RUTA_MARG_LLEG[r] + intensidad * _peso_ruta_e.get(r, 0) for r in si.RUTA_MARG_LLEG}
    me = {k: v / sum(me.values()) for k, v in me.items()}
    mr = {k: v / sum(mr.values()) for k, v in mr.items()}
    return me, mr


ETAPAS_PIPELINE = [
    ("1. Pronóstico de demanda", "Las llegadas diarias salen de una distribución de Poisson alrededor del "
     "pronóstico validado de llegadas (modelo_pronostico.py, el mismo de la página Pronóstico), entrenado solo "
     "con el periodo confiable (hasta el 9-abr-2026) y con los 4 regresores estacionales de «Factores "
     "externos» siempre activos."),
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
    return html.Div(className="simint-slider-group", children=[
        html.Span(className="simint-slider-group__label", children=[etiqueta, info_badge(INFO_SLIDER[clave_info])]),
        control,
    ])


def campo_slider_simple(etiqueta, control):
    """Como campo_slider pero SIN icono de info propio — usado por los sliders de factores externos, que
    comparten un unico info_badge junto al encabezado del grupo (17-nov)."""
    return html.Div(className="simint-slider-group", children=[
        html.Span(etiqueta, className="simint-slider-group__label"),
        control,
    ])


def _marcas_visibles(marcas_dict):
    """Filtra marcas para mostrar solo 3: mínimo, centro, máximo. Mantiene todos los steps internos del slider."""
    if not marcas_dict:
        return marcas_dict
    keys_sorted = sorted(marcas_dict.keys())
    if len(keys_sorted) <= 3:
        return marcas_dict
    idx_min, idx_mid, idx_max = keys_sorted[0], keys_sorted[len(keys_sorted) // 2], keys_sorted[-1]
    return {idx_min: marcas_dict[idx_min], idx_mid: marcas_dict[idx_mid], idx_max: marcas_dict[idx_max]}


def encabezado_grupo(texto, info_texto=None):
    hijos = [texto] if not info_texto else [texto, info_badge(info_texto)]
    return html.Div(hijos, className="simint-config-group-header")


def _titulo_interp(texto, color=None):
    return html.Div(texto, style={"fontWeight": 700, "color": color or AZUL, "marginBottom": "5px"})


def _demo_escala_etapas():
    """Demo visual del criterio de escala de los pictogramas (21-nov): 1 icono NO es 1 paciente — la escala
    cambia por metrica (ETAPAS_INFO) para que las llegadas (escala 10) no se vuelvan miles de iconos."""
    filas = []
    for etapa in ("llegadas", "esperando", "ingresos_cama", "en_cama", "altas"):
        nombre_e, escala = ETAPAS_INFO[etapa]
        plural = "s" if escala != 1 else ""
        filas.append(html.Div(style={"display": "flex", "alignItems": "center", "gap": "9px"}, children=[
            html.Span(className="simint-picto__p", style={"background": AZUL, "flex": "0 0 auto"}),
            html.Span(f"= {escala} paciente{plural}", style={"fontWeight": 600}),
            html.Span(f"en la fila «{nombre_e}»", style={"color": GRIS, "fontSize": "12px"}),
        ]))
    return html.Div(filas, style={"display": "grid", "gap": "7px", "margin": "8px 0 12px"})


def _demo_color_forma():
    """Demo de que el color = grupo de edad y la forma = ruta de llegada (anillo = Treatment urgency,
    translucida = Ambulatorio, sin marca = Urgencias) — mismo criterio de pictograma()."""
    chips_edad = [html.Span(style={"display": "inline-flex", "alignItems": "center", "gap": "5px"}, children=[
                      html.Span(className="simint-radio__chip", style={"background": EDAD_COLORES[g]}),
                      f"{g} años"])
                  for g in EDAD_ORDEN]
    chips_ruta = [
        html.Span(style={"display": "inline-flex", "alignItems": "center", "gap": "6px"}, children=[
            html.Span(className="simint-picto__p", style={"background": GRIS}), "Urgencias (sin marca)"]),
        html.Span(style={"display": "inline-flex", "alignItems": "center", "gap": "6px"}, children=[
            html.Span(className="simint-picto__p simint-picto__p--tu", style={"background": GRIS}),
            "Treatment urgency (con anillo)"]),
        html.Span(style={"display": "inline-flex", "alignItems": "center", "gap": "6px"}, children=[
            html.Span(className="simint-picto__p simint-picto__p--amb", style={"background": GRIS}),
            "Ambulatorio (más clara)"]),
    ]
    return html.Div(style={"display": "grid", "gap": "8px", "margin": "8px 0 12px"}, children=[
        html.Div(chips_edad, style={"display": "flex", "flexWrap": "wrap", "gap": "6px 14px"}),
        html.Div(chips_ruta, style={"display": "flex", "flexWrap": "wrap", "gap": "6px 16px"}),
    ])


def _demo_flecha():
    """Demo de que el color de la flechita de tendencia no es fijo: depende de SUBIR_ES_BUENO por metrica."""
    return html.Div(style={"display": "grid", "gap": "5px", "margin": "8px 0 4px", "fontSize": "13px"}, children=[
        html.Div([html.Span("▲", className="simint-radio__flecha", style={"color": ROJO, "marginRight": "6px"}),
                  "roja: subió y es peor — más llegadas, más pacientes esperando cama o más camas ocupadas"]),
        html.Div([html.Span("▲", className="simint-radio__flecha", style={"color": VERDE, "marginRight": "6px"}),
                  "verde: subió y es mejor — más ingresos a cama o más altas (se desahoga la cola)"]),
    ])


def _demo_camas():
    """Demo del tablero de camas (modulo que aparece en la vista Camas) con el mismo criterio de
    _grupo_camas(): celdas azules = ocupadas, claras = libres, rojas = por encima de la capacidad."""
    celdas = ([html.Span(className="simint-bed") for _ in range(4)]
              + [html.Span(className="simint-bed simint-bed--libre") for _ in range(2)]
              + [html.Span(className="simint-bed simint-bed--sobre") for _ in range(1)])
    return html.Div(style={"margin": "8px 0 4px"}, children=[
        html.Div(celdas, className="simint-bedgrid"),
        html.Div("azul = cama ocupada · gris claro = cama libre · roja = por encima de la capacidad física",
                 style={"fontSize": "12px", "color": GRIS, "marginTop": "5px"}),
    ])


def _seccion_alertas():
    """Como funcionan las alertas, la pausa y la operacion optima (se muestra dentro de la documentacion de la pagina)."""
    return html.Div([
        _titulo_interp("Alertas y operación óptima"),
        html.Div(f"Mientras corre la simulación salta una tarjeta de alerta arriba del gráfico, siempre visible. Hay tres alertas: riesgo de saturar las camas (aviso desde {UMBRAL_ALERTA_MEDIA} % de "
                 f"probabilidad de superar la capacidad a 48 h, crítico desde {UMBRAL_ALERTA} %), ocupación alta (aviso desde {UMBRAL_OCUPACION} camas, crítico desde {UMBRAL_OCUPACION_CRITICA}) y cola de espera larga "
                 f"(aviso desde {UMBRAL_COLA} pacientes, crítico desde {UMBRAL_COLA_CRITICA}). Hay dos gravedades, aviso (amarillo) y crítico (rojo); las dos frenan la simulación, y cada alerta salta una sola vez por corrida. "
                 "La tarjeta dice qué pasó y la recomendación de la que se deriva (con su primer paso), tiene flechas para ver las alertas anteriores y botones para ir a la alerta y a la recomendación."),
        html.Div([html.B("Aplicar mejora y comparar: "), "el panel de configuración se abre, los controles se desplazan a la operación óptima (15 % menos en las estancias de más de 14 días y 30 % de las "
                  "altas de la tarde adelantadas a la mañana), el panel se cierra y la simulación se repite desde el día 1 con la mejora en color y cómo iba antes («Antes de la mejora») en gris punteado. "
                  "Las alertas anteriores siguen disponibles, marcadas como resueltas con la mejora. «Reiniciar» devuelve los controles a cero."], style={"marginTop": "8px"}),
    ])


def panel_interpretacion():
    return html.Details(className="page-section", children=[
        html.Summary("¿Cómo se interpreta?"),
        html.Div(style={"padding": "10px 4px 2px", "display": "grid", "gap": "20px", "fontSize": "13.5px", "lineHeight": "1.6"}, children=[

            html.Div([_titulo_interp("Qué estás viendo"),
                      html.Div("La operación típica proyectada del hospital, día a día, desde el último dato "
                               "confiable. A la izquierda, la «radiografía»: cuántos pacientes llegan, esperan "
                               "cama, entran a cama, están en cama y salen de alta en ese momento. A la derecha, "
                               "la misma historia como una curva en el tiempo. Son los MISMOS pacientes "
                               "simulados en las dos vistas: el que ves esperando es el mismo que después ocupa "
                               "la cama y el mismo que sale de alta.")]),

            html.Div([_titulo_interp("Cómo leer cada fila de la radiografía"),
                      html.Div("El número de cada fila (Llegan, Esperan cama, Entran a cama, En cama, Salen de "
                               "alta) es exacto. El grupo de pacientitos al lado NO es un paciente por icono: "
                               "la escala cambia según la fila, para que las llegadas (que pueden ser miles) no "
                               "se vuelvan ilegibles."),
                      _demo_escala_etapas(),
                      html.Div("El color de cada pacientito es su grupo de edad; la forma dice por dónde "
                               "llegó:"),
                      _demo_color_forma(),
                      html.Div("Pasa el mouse sobre cualquier pacientito para ver su edad, sexo y ruta exactas "
                               "(raza y etnia no se muestran: no hay una distribución real que distinga "
                               "pacientes por esas dos variables en la base). Junto al número, la flechita "
                               "▲/▼ compara con el periodo anterior — el color no es siempre el mismo, depende "
                               "de si subir es bueno o malo para esa métrica:"),
                      _demo_flecha()]),

            html.Div([_titulo_interp("Los controles: reproductor, vistas, filtros y camas"),
                      html.Div([html.B("▶ Reproducir"), " avanza la simulación paso a paso (hora, día, semana o "
                               "mes, según la velocidad elegida). Al pausar a mitad de camino aparecen "
                               "«↺ Reiniciar» y «▶ Continuar donde quedó»; la barra y la fecha debajo siempre "
                               "muestran en qué momento está parada la simulación."]),
                      html.Div([html.B("Todo / Flujo / Camas / Espera"), ", arriba de la radiografía, eligen "
                               "qué filas mostrar. En «Camas» aparece además el Tablero de camas, con una "
                               "celda por cama (grupo Adultos y grupo Niños):"]),
                      _demo_camas(),
                      html.Div([html.B("Los filtros"), " de edad, ruta y sexo (debajo de los controles de la "
                               "izquierda) resaltan solo esos pacientitos en la radiografía — el gráfico de la "
                               "derecha no se filtra, siempre muestra el total."]),
                      html.Div([html.B("Las palancas"), " del panel de Configuración (icono ⚙, arriba a la "
                               "izquierda) cambian un supuesto del escenario antes de reproducir — por ejemplo "
                               "subir la demanda o recortar las estancias largas. Cada una tiene su propio "
                               "icono \"i\" con el detalle de qué mueve y qué no."],
                               style={"marginTop": "2px"})]),

            html.Div([_titulo_interp("Cómo se calculó"),
                      html.Div("Con un motor de agentes montado sobre la simulación de Monte Carlo validada del "
                               "planeador de camas: cada llegada simulada recibe un perfil real (edad × ruta), "
                               "se hospitaliza con la probabilidad histórica de su perfil y, si va a cama, "
                               "hereda la trayectoria completa (hora de llegada, espera y estancia) de un "
                               "paciente real parecido. Se repite "
                               f"{N_REP_INTERACTIVO} veces para ver el rango (las cifras oficiales usan 1.000).")]),

            html.Div([_titulo_interp("Qué significa para el hospital"),
                      html.Div("Permite ver el efecto de una palanca sobre TODO el flujo a la vez: bajar la "
                               "estancia descarga las camas (y con ellas, con el tiempo, la espera); bajar la "
                               "espera descarga la sala de urgencias (la cola) aunque las camas sigan igual de "
                               "llenas; más demanda empuja las tres curvas. Es la base sobre la que se pueden "
                               "montar alertas operativas (fase 2) y recomendaciones (fase 3).")]),

            html.Div([_titulo_interp("Qué NO dice", NARANJA),
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
                html.Div(["Además de los agregados, se compararon DE FRENTE las distribuciones de los tiempos "
                          "que reciben los agentes contra las reales del mismo periodo (simint_distribuciones.csv): "
                          "espera de cama simulada vs real — mediana 18,9 vs 17,0 h, p75 40,3 vs 45,1, p90 74,7 vs "
                          "79,6; estancia — mediana 75,2 vs 69,6 h, p90 283,8 vs 260,6. Los percentiles casi se "
                          "calcan; la cola alta real de la espera es algo peor que el pool 2024-2025 (coherente con "
                          "que los peores casos empeoran año a año)."],
                         style={"fontSize": "12px", "color": GRIS, "marginBottom": "8px"}),
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
                    html.Li("La vista horaria (3 días) usa un motor simplificado sin perfiles por radiografía "
                            "ni factores externos; la radiografía por perfil solo está disponible desde 1 "
                            "semana en adelante."),
                    html.Li("Asociación, no causa; periodo confiable hasta el 9-abr-2026; 106 camas es la cifra "
                            "del HUN sin fecha de corte conocida."),
                ]),
                html.Div("Detalle completo: docs/simulador_integral.md (y docs/modelo_camas.md para el motor A5 de base).",
                         style={"fontSize": "11px", "color": GRIS, "marginTop": "6px"}),
            ]),
        ]),
    ])


# ----------------------------------------------------------------------
# Radiografia: composicion por perfil de cada etapa del flujo, con filtros (edad/ruta/sexo, clic O hover),
# 4 vistas (todo/flujo/camas/espera) y titulo con la granularidad de la vista (dia/semana/mes). Pictogramas:
# 1 figura = N pacientes; color = grupo de edad; anillo = Treatment urgency; translucida = Ambulatorio.
# Es la MEZCLA TIPICA simulada (promedio de las repeticiones), no un censo nominal.
# ----------------------------------------------------------------------
EDAD_ORDEN = ["0-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+"]
EDAD_COLORES = {"0-4": "#6ec6b2", "5-14": "#2e9b82", "15-29": "#7fb3e0", "30-44": "#4a8fd0",
                "45-59": "#2a6fb0", "60-74": "#e0862a", "75+": "#c0392b"}
RUTA_ORDEN = ["Urgencias", "Treatment urgency", "Ambulatorio"]
RUTA_CORTA = {"Urgencias": "urgencias", "Treatment urgency": "treatment urg.", "Ambulatorio": "ambulatorio"}
RUTA_ABREV = {"Urgencias": "URG", "Treatment urgency": "TU", "Ambulatorio": "AMB"}
ETAPAS_INFO = {"llegadas": ("Llegan al hospital", 10), "esperando": ("Esperando cama", 1),
               "ingresos_cama": ("Entran a cama", 1), "en_cama": ("En cama", 5), "altas": ("Salen de alta", 1)}
VISTA_ETAPAS = {"todo": ["llegadas", "esperando", "ingresos_cama", "en_cama", "altas"],
                "flujo": ["llegadas", "ingresos_cama", "altas"], "camas": ["en_cama"], "espera": ["esperando"]}
# La radiografia siempre muestra las 5 metricas base (filtradas por vista) + filtros; el Tablero de camas es
# un MODULO adicional, colapsado, que solo aparece en la vista "Camas" (18-nov) — ver modulo_tablero_camas().
AGREGACION = {"llegadas": "suma", "ingresos_cama": "suma", "altas": "suma", "en_cama": "media", "esperando": "media"}
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
            "octubre", "noviembre", "diciembre"]
INFO_RADIOGRAFIA = ("Composición típica simulada (promedio de las repeticiones) de los pacientes en cada "
                    "etapa del flujo — no un censo nominal, no dice quiénes estarán ese día/semana/mes. Edad, "
                    "sexo y ruta de llegada son reales (del mismo paciente histórico) o su proporción "
                    "histórica. La cola («esperando cama») solo cuenta a quienes terminarán hospitalizados — "
                    "cota inferior de la presión real de urgencias. Raza y etnia NO se muestran por paciente: "
                    "en la base la raza está sin dato en el 95 % de las personas y la etnia es casi siempre "
                    "«Hispanic or Latino» en toda la base, así que no hay una distribución real que diferencie "
                    "pacientes por esas dos variables.")


def _orden_perfiles(perfiles):
    return sorted(range(len(perfiles)),
                  key=lambda i: (EDAD_ORDEN.index(perfiles[i][0]) if perfiles[i][0] in EDAD_ORDEN else 99,
                                 RUTA_ORDEN.index(perfiles[i][1]) if perfiles[i][1] in RUTA_ORDEN else 99))


def _reparto_figuras(counts, escala):
    """Cuantas figuras por celda para que el total sea round(suma/escala) (restos mayores primero)."""
    total = int(round(sum(counts) / escala))
    if total <= 0:
        return [0] * len(counts)
    brutos = np.array(counts, dtype=float) / escala
    base = np.floor(brutos).astype(int)
    for i in np.argsort(base - brutos)[:max(total - int(base.sum()), 0)]:
        base[i] += 1
    return base.tolist()


def pictograma(comp_perfil_sexo, perfiles, escala, filtro):
    """comp_perfil_sexo: lista (21, 2) [perfil][sexo] ya agregada en el tiempo. Aplica el filtro (edad/ruta/
    sexo) y devuelve (pictograma, total_filtrado). Cada figura lleva en su title (tooltip nativo) edad, sexo,
    ruta, raza y etnia del perfil que representa — raza/etnia son la nota general (sin dato / Hispanic-Latino),
    no una variable que distinga pacientes."""
    arr = np.asarray(comp_perfil_sexo, dtype=float)
    filtro = filtro or {}
    edad_f, ruta_f, sexo_f = filtro.get("edad"), filtro.get("ruta"), filtro.get("sexo")
    celdas = []
    for i in _orden_perfiles(perfiles):
        g, r = perfiles[i]
        if edad_f and g != edad_f:
            continue
        if ruta_f and r != ruta_f:
            continue
        for sx, nombre_sx in ((0, "Mujer"), (1, "Hombre")):
            if sexo_f and nombre_sx != sexo_f:
                continue
            celdas.append((g, r, nombre_sx, float(arr[i, sx])))
    counts = [c for *_, c in celdas]
    reparto = _reparto_figuras(counts, escala)
    figs = []
    for (g, r, sx, _c), n in zip(celdas, reparto):
        if n <= 0:
            continue
        clase = "simint-picto__p" + (" simint-picto__p--tu" if r == "Treatment urgency" else "") \
                + (" simint-picto__p--amb" if r == "Ambulatorio" else "")
        titulo = (f"{g} años · {sx} · {RUTA_CORTA.get(r, r)} · raza: sin dato en la base · "
                 f"etnia: Hispanic/Latino (predominante en toda la base)")
        figs += [html.Span(className=clase, style={"background": EDAD_COLORES.get(g, "#888")}, title=titulo)] * n
    return html.Div(figs, className="simint-picto"), sum(counts)


# Flecha de tendencia (20-nov, estilo bolsa de valores): compara el total de la ventana actual contra la
# ventana anterior del MISMO ancho (dia vs dia anterior, semana vs semana anterior, etc.). La direccion de
# la flecha siempre refleja el cambio real (subio/bajo); el COLOR es relativo a la etapa: para llegadas,
# esperando cama y en cama (metricas de presion/ocupacion) subir es peor (rojo); para ingresos a cama y
# altas (metricas de flujo: cuanto se desahoga la cola / cuantas camas se liberan) subir es mejor (verde).
SUBIR_ES_BUENO = {"llegadas": False, "esperando": False, "ingresos_cama": True, "en_cama": False, "altas": True}


def flecha_tendencia(etapa, actual, anterior):
    """None si no hay ventana anterior (idx=0) o no cambio; si no, una flecha minimalista ▲/▼ coloreada
    segun SUBIR_ES_BUENO, con el detalle en el tooltip nativo (title)."""
    if anterior is None or round(actual, 1) == round(anterior, 1):
        return None
    sube = actual > anterior
    color = VERDE if (sube == SUBIR_ES_BUENO[etapa]) else ROJO
    return html.Span("▲" if sube else "▼", className="simint-radio__flecha", style={"color": color},
                     title=f"{'Subió' if sube else 'Bajó'} frente al periodo anterior ({anterior:.0f} → {actual:.0f})")


def fila_metrica(nombre_e, texto_num, escala, pictograma_div, flecha=None):
    """Una FILA de las 5 metricas principales (19-nov): etiqueta + numero a la izquierda en una columna
    angosta fija, y el pictograma a la derecha ocupando TODO el ancho libre hasta el borde de la tarjeta
    (antes eran columnas lado a lado, apretadas en el panel angosto de la izquierda). `flecha` (20-nov) es
    la flechita de tendencia, justo al lado del numero — ver flecha_tendencia()."""
    num_hijos = [texto_num, flecha] if flecha is not None else texto_num
    return html.Div(className="simint-radio__fila", children=[
        html.Div(className="simint-radio__fila-izq", children=[
            html.Div(nombre_e, className="simint-radio__cap"),
            html.Div(num_hijos, className="simint-radio__num"),
        ]),
        html.Div(pictograma_div, className="simint-radio__fila-der"),
    ])


def _grupo_camas(titulo_g, ocupadas, cap):
    """Un grupo del tablero de camas: `cap` celdas azules/libres y, si el censo supera la capacidad, celdas
    ROJAS adicionales — la sobreocupacion se ve crecer, no se lee en una nota."""
    n_oc = int(round(ocupadas))
    dentro, sobre = min(n_oc, cap), max(n_oc - cap, 0)
    celdas = ([html.Span(className="simint-bed") for _ in range(dentro)]
              + [html.Span(className="simint-bed simint-bed--libre") for _ in range(cap - dentro)]
              + [html.Span(className="simint-bed simint-bed--sobre") for _ in range(sobre)])
    etiqueta = [f"{titulo_g}: {n_oc} de {cap}"]
    if sobre:
        etiqueta.append(html.Span(f"  +{sobre} sobre capacidad", style={"color": ROJO, "fontWeight": 700}))
    return html.Div(style={"flex": "1 1 260px"}, children=[
        html.Div(etiqueta, className="simint-radio__cap"), html.Div(celdas, className="simint-bedgrid")])


def modulo_tablero_camas(ocup_adultos, ocup_ninos):
    """Modulo de la vista "Camas" (18-nov, visible sin desplegable desde el 20-nov): informacion ADICIONAL
    a las 5 metricas base de la radiografia, siempre a la vista debajo de la metrica "En cama". Es el primero
    de varios "modulos por vista" que se iran agregando (p.ej. mas adelante, otros graficos especificos de
    Camas u otras vistas) — el patron a seguir es el mismo: un html.Div por modulo, agregado solo cuando la
    vista correspondiente esta activa."""
    return html.Div(className="simint-radio__modulo", children=[
        html.Div("Tablero de camas", className="simint-radio__modulo-titulo"),
        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "18px", "marginTop": "10px"}, children=[
            _grupo_camas("Adultos", ocup_adultos, scm.CAPACIDAD["adultos"]),
            _grupo_camas("Niños", ocup_ninos, scm.CAPACIDAD["ninos"]),
        ]),
    ])


def _agregar(etapa, comp_etapa, ini, fin):
    """Suma (conteos: llegadas/ingresos/altas) o promedia (stock: en_cama/esperando) la composicion por
    perfil x sexo en la ventana [ini, fin) de dias — la ventana depende de la granularidad (dia/semana/mes)."""
    ventana = np.asarray(comp_etapa[ini:fin], dtype=float)
    if ventana.shape[0] == 0:
        return np.zeros((len(comp_etapa[0]) if comp_etapa else 21, 2)).tolist()
    return (ventana.sum(axis=0) if AGREGACION[etapa] == "suma" else ventana.mean(axis=0)).tolist()


def ventana_radiografia(idx, fechas, velocidad):
    """(ini, fin, fecha_representativa, granularidad) para agregar la composicion alrededor de `idx`. La
    granularidad sigue la velocidad de reproduccion elegida (1/7/30 dias -> dia/semana/mes, GRANULARIDAD_POR_
    VELOCIDAD), NO el plazo total — asi coincide con lo que el usuario pidio ver y con lo que avanza el
    cursor en pantalla.
    El ULTIMO tramo del horizonte (cuando `dias` no es multiplo de 7, o el mes final queda a medias) nunca
    se deja mas corto que un periodo completo: en vez de sumar un tramo de 2-3 dias como si fuera una semana
    completa (lo que hacia caer la cifra en picada en el ultimo tick de la reproduccion, bug del 17-nov), la
    ventana se corre hacia atras para cubrir siempre 7 dias / el mes completo, igual que las demas ventanas."""
    gran = GRANULARIDAD_POR_VELOCIDAD.get(velocidad, "dia")
    fecha = pd.Timestamp(fechas[idx])
    n = len(fechas)
    if gran == "dia":
        return idx, idx + 1, fecha, gran
    if gran == "semana":
        ini = max(0, idx - fecha.dayofweek)
        fin = min(n, ini + 7)
        if fin - ini < 7:
            ini = max(0, fin - 7)
        return ini, fin, pd.Timestamp(fechas[ini]), gran
    ini = max(0, idx - (fecha.day - 1))
    dias_mes = pd.Period(fecha, freq="M").days_in_month
    fin = min(n, ini + dias_mes)
    if fin - ini < dias_mes:
        ini = max(0, fin - dias_mes)
    return ini, fin, pd.Timestamp(fechas[ini]), gran


def ventanas_del_grafico(fechas, velocidad):
    """(ini, fin) por dia para TODA la serie, con la misma ventana real (semana/mes de calendario) que usa la
    radiografia — para que el hover del grafico, con velocidad "semana"/"mes", muestre el total/promedio de
    esa ventana en vez del valor suelto de ese dia (reportado el 20-nov: solo la radiografia agregaba, el
    grafico seguia mostrando el dato diario al pasar el mouse)."""
    n = len(fechas)
    inis, fins = [0] * n, [0] * n
    for i in range(n):
        ini, fin, _, _ = ventana_radiografia(i, fechas, velocidad)
        inis[i], fins[i] = ini, fin
    return inis, fins


def serie_agregada_por_ventana(serie, inis, fins, modo):
    """`serie` (un valor por dia) agregada ventana a ventana (ver ventanas_del_grafico): cada dia se reemplaza
    por la suma o el promedio de su ventana, segun `modo` ("suma" o "media", igual que AGREGACION)."""
    arr = np.asarray(serie, dtype=float)
    out = np.empty(len(arr))
    for i in range(len(arr)):
        tramo = arr[inis[i]:fins[i]]
        out[i] = tramo.sum() if modo == "suma" else tramo.mean()
    return out.tolist()


def customdata_ventana(agregado, fechas_dt, inis, fins):
    """customdata por punto para el hovertemplate del grafico: [valor agregado, 'dd Mon' de inicio, 'dd Mon'
    de fin] de la ventana (semana o mes) a la que pertenece ese dia."""
    def corta(ts):
        return f"{ts.day} {MESES_ES[ts.month - 1][:3]}"
    return [[agregado[i], corta(fechas_dt[inis[i]]), corta(fechas_dt[fins[i] - 1])] for i in range(len(agregado))]


def titulo_radiografia(ini_fecha, fin_fecha, gran):
    """Titulo con el rango REAL que se esta agregando (ini_fecha a fin_fecha, ambas incluidas) — ya no asume
    que la semana empieza en lunes ni que el mes es completo, porque la ultima ventana del horizonte puede
    estar corrida hacia atras (ver ventana_radiografia)."""
    if gran == "dia":
        return ini_fecha.strftime("%b %d, %Y")   # mismo formato que la cabecera del hover del grafico (x unified)
    if gran == "semana":
        if ini_fecha.month == fin_fecha.month:
            return f"Semana del {ini_fecha.day} al {fin_fecha.day} de {MESES_ES[fin_fecha.month - 1]} de {fin_fecha.year}"
        return (f"Semana del {ini_fecha.day} de {MESES_ES[ini_fecha.month - 1]} al {fin_fecha.day} de "
                f"{MESES_ES[fin_fecha.month - 1]} de {fin_fecha.year}")
    if ini_fecha.day == 1 and ini_fecha.month == fin_fecha.month:
        return f"{MESES_ES[fin_fecha.month - 1].capitalize()} de {fin_fecha.year}"
    return (f"Del {ini_fecha.day} de {MESES_ES[ini_fecha.month - 1]} al {fin_fecha.day} de "
            f"{MESES_ES[fin_fecha.month - 1]} de {fin_fecha.year}")


def chip_edad(g, activo):
    if g == "todas":
        return html.Div(id={"type": "simint-chip-edad", "edad": g}, n_clicks=0,
                        className="simint-chip" + (" is-active" if activo else ""), children="Todos")
    return html.Div(id={"type": "simint-chip-edad", "edad": g}, n_clicks=0,
                    className="simint-chip" + (" is-active" if activo else ""), children=[
                        html.Span(className="simint-chip__swatch", style={"background": EDAD_COLORES[g]}), g])


def chip_ruta(valor, activo):
    etiqueta = "Todas" if valor == "todas" else RUTA_ABREV[valor]
    return html.Div(id={"type": "simint-chip-ruta", "ruta": valor}, n_clicks=0,
                    className="simint-chip" + (" is-active" if activo else ""), children=etiqueta)


def chip_sexo(sx, contenido, color, activo):
    if sx == "todas":
        hijo = contenido
        clase = "simint-chip"
    else:
        hijo = html.Span(contenido, style={"color": color, "fontWeight": 700, "fontSize": "14px"})
        clase = "simint-chip simint-chip--icon"
    return html.Div(id={"type": "simint-chip-sexo", "sexo": sx}, n_clicks=0,
                    className=clase + (" is-active" if activo else ""), children=hijo)


def panel_filtros(filtro):
    """3 filas, una por grupo de filtro (Edad/Ruta/Sexo), cada una con su etiqueta y apiladas una encima de
    la otra (20-nov). Cada grupo trae su opcion "Todos"/"Todas" como PRIMER chip de izquierda a derecha, y
    esa es la que esta activa por defecto (filtro vacio). Los chips se activan SOLO con clic explicito — se
    quito la activacion por hover porque un simple paso del mouse dejaba un filtro pegado sin que el usuario
    se diera cuenta, mostrando un subgrupo en la radiografia mientras el grafico seguia sin filtrar (la
    "incongruencia" reportada ese dia)."""
    filtro = filtro or {}
    chips_edad = [chip_edad("todas", not filtro.get("edad"))] + \
                 [chip_edad(g, filtro.get("edad") == g) for g in EDAD_ORDEN]
    chips_ruta = [chip_ruta("todas", not filtro.get("ruta"))] + \
                 [chip_ruta(r, filtro.get("ruta") == r) for r in RUTA_ORDEN]
    chips_sexo = [chip_sexo("todas", "Todos", GRIS, not filtro.get("sexo")),
                  chip_sexo("Mujer", "♀", ROSA, filtro.get("sexo") == "Mujer"),
                  chip_sexo("Hombre", "♂", AZUL, filtro.get("sexo") == "Hombre")]
    return html.Div(className="simint-radio__filtros-col", children=[
        html.Div(className="simint-radio__filtro-fila", children=[
            html.Span("Edad", className="simint-radio__filtro-etiqueta"),
            html.Div(chips_edad, className="simint-radio__filtro-grupo"),
        ]),
        html.Div(className="simint-radio__filtro-fila", children=[
            html.Span("Ruta", className="simint-radio__filtro-etiqueta"),
            html.Div(chips_ruta, className="simint-radio__filtro-grupo"),
        ]),
        html.Div(className="simint-radio__filtro-fila", children=[
            html.Span("Sexo", className="simint-radio__filtro-etiqueta"),
            html.Div(chips_sexo, className="simint-radio__filtro-grupo"),
        ]),
    ])


def _descripcion_escenario(clave, dia=None):
    """Que se aplico y como leer el grafico, solo despues de aplicar la mejora desde una alerta."""
    if clave != "optimo":
        return []
    texto_palanca = {"recorte": lambda v: f"estancias de más de 14 días {v} % más cortas (R7)", "adelanto": lambda v: f"{v} % de las altas de la tarde adelantadas a la mañana (R4)"}
    lista = [texto_palanca[k](v) for k, v in ESCENARIOS["optimo"][2].items()]
    return [html.Div("Operación óptima aplicada desde el día 1", className="simint-escenario__titulo"),
            html.Div([html.Span("Qué cambió", className="simint-escenario__rotulo"), html.Span(" y ".join(lista))], className="simint-escenario__palancas"),
            html.Div([html.Span("Cómo leer el gráfico", className="simint-escenario__rotulo"),
                      html.Span("la simulación se repite desde el día 1: las líneas de color son la operación óptima y las grises punteadas, cómo iba antes de aplicarla.")],
                     className="simint-escenario__palancas")]


def layout():
    return html.Div(className="page-container", children=[
        html.Div(className="page-head", children=[
            html.H2("Simulador integral: el hospital en operación continua"),
            html.P("Como la recepción de un hotel que nunca cierra: cada paciente simulado llega, espera cama, "
                   "se queda y sale de alta — y lo ves correr en tiempo real. Ajusta una palanca y presiona "
                   "Reproducir.",
                   className="page-head__sub"),
        ]),

        html.Div(className="control-row", children=[
            html.Div(className="control-group", children=[
                html.Span("¿Hasta cuándo quieres ver?", className="control-group__label"),
                dcc.RadioItems(id="simint-plazo", className="pill-switch",
                               options=[{"label": n, "value": d} for n, d in PLAZOS], value=90)]),
        ]),
        html.Div(id="simint-escenario-desc", className="simint-escenario", style={"display": "none"}),
        dcc.Checklist(id="simint-comparar", value=["si"], className="simint-comparar simint-comparar--visible",
                      options=[{"label": "Al aplicar una mejora, mostrar en gris punteado cómo iba antes, junto a la simulación nueva en color", "value": "si"}]),
        # El boton de configuracion vive EN LA FILA del reproductor (a la izquierda de "Reproducir", con el
        # margen del propio gap de .simint-player) — no flota sobre la pagina; solo el PANEL que emerge al
        # pasar el mouse es absolute y SI se superpone sobre el contenido de abajo (eso si es lo esperado).
        # El resto del contenido (alerta/radiografia/grafico) usa todo el ancho disponible.
        html.Div(children=[
            html.Div(id="simint-alerta", className="alert-inline simint-alerta simint-alerta--idle", style={"display": "flex"}, children=[
                html.Div(className="simint-alerta__espera", children=[
                    html.Span(className="nav__ico ico-alert simint-alerta__espera-ico"),
                    html.Div(className="simint-alerta__espera-texto", children=[
                        html.Div("Vigilando la simulación: sin alertas por ahora", className="simint-alerta__espera-titulo"),
                        html.P("Una alerta aparecerá aquí en cuanto se detecte un riesgo. La simulación se detiene para que la revises, puedas ver qué hacer y aplicar la mejora; "
                               "la tarjeta se queda a la vista todo el tiempo.", className="simint-alerta__espera-p"),
                        html.Div(className="simint-alerta__vigila", children=[
                            html.Span([html.I(), f"Riesgo de saturar las camas · aviso desde {UMBRAL_ALERTA_MEDIA} %, crítico desde {UMBRAL_ALERTA} %"], className="simint-alerta__vigila-item"),
                            html.Span([html.I(), f"Ocupación alta · aviso desde {UMBRAL_OCUPACION} camas, crítico desde {UMBRAL_OCUPACION_CRITICA}"], className="simint-alerta__vigila-item"),
                            html.Span([html.I(), f"Cola de espera larga · aviso desde {UMBRAL_COLA} pacientes, crítico desde {UMBRAL_COLA_CRITICA}"], className="simint-alerta__vigila-item")])])]),
                html.Div(className="simint-alerta__cuerpo", children=[
                    html.Div(className="simint-alerta__cab", children=[
                        html.Span("ALERTA", className="simint-alerta__etiqueta"),
                        html.Span(id="simint-alerta-grav", className="rec-chip"), html.Span("Sin alertas por ahora", id="simint-alerta-titulo", className="simint-alerta__titulo"),
                        html.Span(className="simint-alerta__hist", children=[
                            html.Button(html.Span(className="chev chev--izq"), id="simint-alerta-prev", n_clicks=0, className="simint-alerta__flecha", title="Alerta anterior"),
                            html.Span(id="simint-alerta-pos", className="simint-alerta__pos"),
                            html.Button(html.Span(className="chev chev--der"), id="simint-alerta-next", n_clicks=0, className="simint-alerta__flecha", title="Alerta siguiente")])]),
                    html.Div(className="simint-alerta__bloque", children=[html.Span("Qué pasó", className="simint-alerta__rotulo"), html.Span("Las alertas saltarán aquí mientras corre la simulación, y la tarjeta se queda a la vista.", id="simint-alerta-detalle")]),
                    html.Div(className="simint-alerta__bloque", children=[html.Span("Recomendación", className="simint-alerta__rotulo"),
                                                                           html.Span(id="simint-alerta-acciones"), html.Span(id="simint-alerta-paso", className="simint-alerta__paso")]),
                    html.Span(id="simint-alerta-texto", style={"display": "none"}),
                ]),
                html.Div(className="simint-alerta__botones", children=[
                    html.Button("Continuar", id="simint-continuar", n_clicks=0, className="btn-primary simint-alerta__btn"),
                    html.Button("Aplicar mejora y comparar", id="simint-aplicar", n_clicks=0, className="btn-primary simint-alerta__btn simint-alerta__btn--mejora",
                                title="Aplica la operación óptima: los controles se mueven y se vuelve a simular desde el día 1, comparando con cómo iba antes"),
                    dcc.Link("Ver más sobre esta alerta", id="simint-alerta-link-alerta", href="/alertas", refresh=True, className="simint-alerta__btn simint-alerta__link"),
                    dcc.Link("Ver recomendación", id="simint-alerta-link-rec", href="/recomendaciones", refresh=True, className="simint-alerta__btn simint-alerta__link"),
                    html.Span(id="simint-alerta-nota", className="simint-alerta__nota"),
                ]),
            ]),
            html.Div(className="simint-player", children=[
                html.Div(id="simint-config", className="simint-config-sidebar", children=[
                    html.Div(html.Span(className="nav__ico ico-settings"), className="simint-config-tab"),
                    html.Div(className="simint-config-inner", children=[
                    html.Div("Configuración", className="simint-config-title", style={"gridColumn": "1 / -1"}),

                    # Sección 1: Operación
                    html.Div(className="simint-config-section", children=[
                        encabezado_grupo("Operación"),
                        campo_slider("Demanda de llegadas (%)", "llegadas",
                                     dcc.Slider(id="simint-ajuste_llegadas", min=-30, max=30, step=5, value=0,
                                               marks={-30: "-30", 0: "0", 30: "30"})),
                        campo_slider("Estancia en cama (%)", "estancia",
                                     dcc.Slider(id="simint-ajuste_estancia", min=-20, max=20, step=5, value=0,
                                               marks={-20: "-20", 0: "0", 20: "20"})),
                        campo_slider("Espera de cama (%)", "espera",
                                     dcc.Slider(id="simint-ajuste_espera", min=-30, max=30, step=5, value=0,
                                               marks={-30: "-30", 0: "0", 30: "30"})),
                        campo_slider("Capacidad hipotética (camas)", "capacidad",
                                     dcc.Slider(id="simint-capacidad", min=96, max=130, step=2, value=106,
                                                marks={96: "96", 106: "106", 116: "116", 126: "126"})),
                    ]),

                    # Sección 2: Estrés
                    html.Div(className="simint-config-section", children=[
                        encabezado_grupo("Estrés"),
                        campo_slider("Perfiles de estrés (%)", "mezcla_estres",
                                     dcc.Slider(id="simint-mezcla_estres", min=0, max=100, step=10, value=0,
                                               marks={0: "0", 50: "50", 100: "100"})),
                    ]),

                    # Sección 3: Optimización
                    html.Div(className="simint-config-section", children=[
                        encabezado_grupo("Optimización"),
                        campo_slider("Recortar estancias largas (%)", "recorte_largas",
                                     dcc.Slider(id="simint-recorte_largas", min=0, max=50, step=5, value=0,
                                               marks={0: "0", 25: "25", 50: "50"})),
                        campo_slider("Adelantar altas a la mañana (%)", "adelanto_altas",
                                     dcc.Slider(id="simint-adelanto_altas", min=0, max=100, step=10, value=0,
                                               marks={0: "0", 50: "50", 100: "100"})),
                    ]),

                    # Sección 4: Factores externos
                    html.Div(className="simint-config-section", children=[
                        encabezado_grupo("Factores externos", INFO_FACTORES_EXTERNOS),
                        *([campo_slider_simple(si.CASOS[k], dcc.Slider(
                            id={"type": "simint-caso", "caso": k}, min=min(m), max=max(m), step=1, value=0,
                            marks=_marcas_visibles(m)))
                           for k in MODELOS_FIJOS
                           for m in [{i - [n for n, _ in si.niveles_caso(k)].index("Normal"): n
                                     for i, (n, _) in enumerate(si.niveles_caso(k))}]]),
                    ]),

                    html.Div(id="simint-nota", style={"fontSize": "12px", "marginTop": "10px", "gridColumn": "1 / -1"}),
                ]),
                ]),
                html.Button("▶ Reproducir", id="simint-play", n_clicks=0, className="btn-primary simint-player__btn"),
                # Boton partido (20-nov): aparece SOLO al pausar manualmente a mitad de la reproduccion (en vez
                # de volver a mostrar "Reproducir", que reiniciaba todo desde cero sin avisar). "Continuar"
                # reanuda el mismo cursor; "Reiniciar" solo borra los datos/el progreso y vuelve a mostrar el
                # boton unico, SIN recalcular hasta que el usuario presione Reproducir de nuevo.
                html.Div(id="simint-play-split", className="simint-player__split", style={"display": "none"}, children=[
                    html.Button("▶ Continuar", id="simint-play-continuar", n_clicks=0,
                                className="simint-player__split-btn", title="Continuar donde se pausó"),
                    html.Button("↺ Reiniciar", id="simint-play-reiniciar", n_clicks=0,
                                className="simint-player__split-btn", title="Reiniciar la simulación desde el comienzo"),
                ]),
                dcc.RadioItems(id="simint-velocidad", className="pill-switch",
                               options=[{"label": "1 día", "value": 1}, {"label": "1 semana", "value": 7},
                                       {"label": "1 mes", "value": 30}], value=7),
                html.Div(className="simint-player__track",
                         children=html.Div(id="simint-player-fill", className="simint-player__fill")),
                html.Div(id="simint-player-pct", className="simint-player__pct"),
                html.Div(id="simint-player-fecha", className="simint-player__fecha"),
            ]),

            # Dos columnas (18-nov): la radiografia queda como panel fijo a la IZQUIERDA; el grafico a la
            # DERECHA. Asi, en las vistas que solo muestran 1 fila de grafico (flujo/camas/espera, mas angostas
            # que "todo"), el espacio que antes quedaba vacio ahora lo ocupa naturalmente la columna izquierda
            # (que puede crecer con los modulos de la vista, p.ej. el tablero de camas) en vez de alargar el
            # grafico de forma artificial.
            html.Div(className="simint-layout-dos-col", children=[
                html.Div(className="simint-radio-panel", children=[
                    html.Div(className="metric-card simint-radio", children=[
                        html.Div(className="simint-radio__header", children=[
                            html.Div([html.Span(id="simint-radiografia-titulo", className="simint-radio__titulo"),
                                     info_badge(INFO_RADIOGRAFIA)], style={"display": "flex", "alignItems": "center", "gap": "8px"}),
                            dcc.RadioItems(id="simint-vista-radio", className="pill-switch pill-switch--compact", value="todo",
                                          options=[{"label": "Todo", "value": "todo"}, {"label": "Flujo", "value": "flujo"},
                                                   {"label": "Camas", "value": "camas"}, {"label": "Espera", "value": "espera"}]),
                        ]),
                        html.Div(id="simint-radiografia-body", style={"marginTop": "20px"}),
                    ]),
                ]),
                html.Div(className="simint-grafico-panel", children=[
                    # 720px (antes 640px, 17-nov): la leyenda horizontal de abajo se quito (ahora vive una
                    # mini leyenda por fila, dentro de cada grafico) y ese espacio libre pasa a las 3 filas,
                    # que crecen proporcionalmente (mismas fracciones de alto en `alturas`, mas pixeles).
                    dcc.Graph(id="simint-grafico", config={"displaylogo": False}, style={"height": "720px"}),
                ]),
            ]),
        ]),

        # 18-nov: el intervalo "real" de avance sigue siendo ~350ms (SIMINT_SUBFRAMES x 50ms), pero el tick
        # dispara cada 50ms para poder dibujar SUBFRAMES intermedios interpolados entre un punto real y el
        # siguiente — eso es lo que hace que el trazo crezca fluido en vez de a saltos (ver clientside abajo).
        dcc.Interval(id="simint-tick", interval=50, disabled=True),
        dcc.Store(id="simint-escenario", data={"clave": "hoy", "n": 0}),
        dcc.Store(id="simint-pendiente"),
        html.Div(id="simint-dummy-cfg", style={"display": "none"}),
        dcc.Store(id="simint-cursor"),
        dcc.Store(id="simint-datos"),
        dcc.Store(id="simint-filtro", data={}),
        dcc.Store(id="simint-sync-hover"),   # salida de callbacks cliente "silenciosos" (no se usa su valor)
        mensaje("**Sirve para ver el efecto de una decisión sobre todo el flujo a la vez, no para adivinar un día.** Bajar la estancia descarga las camas; bajar la espera descarga "
                "la sala de urgencias aunque las camas sigan igual de llenas; más demanda empuja las tres curvas. Cuando salta una alerta, el simulador dice qué hacer y permite "
                "aplicar la operación óptima y compararla con cómo iba antes."),
        metodo(
            "Un motor de agentes montado sobre la simulación de Monte Carlo validada del planeador de camas: cada llegada simulada recibe un perfil real (edad × ruta), se hospitaliza "
            f"con la probabilidad histórica de su perfil y, si va a cama, hereda la trayectoria completa (hora de llegada, espera y estancia) de un paciente real parecido. Se repite {N_REP_INTERACTIVO} "
            "veces para ver el rango (las cifras oficiales usan 1.000). Parte del último dato confiable (9-abr-2026) con el censo y la cola reales de ese día.",
            "No predice un día concreto ni un paciente concreto: reproduce patrones. La cola solo cuenta a quienes terminarán hospitalizados, así que es una **cota inferior** de la "
            "presión real de urgencias. Las alertas y sus umbrales son criterios de esta página, no resultados validados. Es asociación proyectada sobre el patrón histórico, no una "
            "garantía de que ese patrón se mantenga.",
            "Fuente: src/simulador_integral.py y docs/simulador_integral.md.", ruta="/simulador",
            antes=secciones(panel_interpretacion(), solo=("Qué estás viendo", "Cómo leer cada fila", "Los controles")) + [_seccion_alertas()],
            despues=secciones(panel_tecnico()), pasos=False, modelo=False),
    ])


def _ejecutar(dias, pct_lleg, pct_est, pct_esp, recorte, adelanto, estres, comparar, valores_casos, ids_casos):
    """Cuerpo de la simulacion (compartido por el boton Reproducir y por Intervenir, para que Intervenir no
    dependa de leer los sliders como State justo despues de que otro callback los acaba de cambiar — evita la
    condicion de carrera de Dash entre dos callbacks disparados por el mismo click). Los 4 factores externos
    (dengue/lluvia/ira/eda) estan SIEMPRE activos (MODELOS_FIJOS); sus sliders solo eligen la severidad."""
    casos, nombres = {}, {}
    for i, v in zip(ids_casos or [], valores_casos or []):
        if v and i["caso"] in MODELOS_FIJOS:
            niveles = si.niveles_caso(i["caso"])
            nombre, pct = niveles[[n for n, _ in niveles].index("Normal") + v]
            casos[i["caso"]], nombres[i["caso"]] = pct, nombre
    es_horario = isinstance(dias, str) and dias.endswith("h")

    if es_horario:
        # Vista horaria: motor simplificado, sin factores externos/R7/adelanto/mezcla ni composicion por perfil.
        horas = int(dias[:-1])
        fechas, out, info = si.simular_horario(scm.ULTIMO_CONFIABLE, horas=horas, n_rep=N_REP_HORARIO,
                                               ajuste_estancia=1 + pct_est / 100, ajuste_espera=1 + pct_esp / 100)
        series_h = ("ingresos_cama", "altas", "cola", "total")
        data = {"fechas": [f.isoformat() for f in fechas], "es_horario": True}
        for s in series_h:
            for p in (10, 50, 90):
                data[f"{s}_p{p}"] = np.percentile(out[s], p, axis=0).tolist()
        data["medias"] = {s: float(out[s].mean()) for s in series_h}
        data["pct_sat"] = round(100 * float((out["total"] > scm.CAPACIDAD["total"]).mean()), 1)
        probs = 100 * (out["total"] > scm.CAPACIDAD["total"]).mean(axis=0)
        idx48 = np.minimum(np.arange(len(fechas)) + 48, len(fechas) - 1)     # 48 h = 48 pasos (la unidad es la hora)
        data["prob_sat_48h"] = np.round(probs[idx48], 1).tolist()
        data["umbral_alerta"] = UMBRAL_ALERTA
        data["alertas_dia"] = _alertas_dia(data["fechas"], data["total_p50"], data["cola_p50"], data["prob_sat_48h"], scm.CAPACIDAD["total"], horas=True)
        data["sat_por_capacidad"] = {str(c): round(100 * float((out["total"] > c).mean()), 1) for c in range(96, 131, 2)}
        nota_casos = html.Div([html.B("Vista horaria: "), "motor simplificado (sin factores externos, R7, "
                               "adelanto de altas, perfiles de estrés ni radiografía por perfil) — pensada "
                               "para ver EN VIVO el patrón de horas de asignación de cama (dos olas: 15-17 h "
                               "y 20-23 h)."], style={"marginBottom": "8px"})
        return data, nota_casos

    me, mr = mezcla_estres((estres or 0) / 100)
    fechas, out, info = si.simular_integral(scm.ULTIMO_CONFIABLE, dias,
                                            ajuste_llegadas=1 + pct_lleg / 100, ajuste_estancia=1 + pct_est / 100,
                                            ajuste_espera=1 + pct_esp / 100, n_rep=N_REP_INTERACTIVO,
                                            modelos=MODELOS_FIJOS, casos=casos, con_composicion=True,
                                            recorte_largas_pct=recorte or 0, adelanto_altas_pct=adelanto or 0,
                                            mezcla_edad=me, mezcla_ruta=mr)
    data = {"fechas": [str(f.date()) for f in fechas], "es_horario": False}
    for s in SERIES:
        for p in (10, 50, 90):
            data[f"{s}_p{p}"] = np.percentile(out[s], p, axis=0).tolist()
    data["medias"] = {s: float(out[s].mean()) for s in SERIES}
    data["pct_sat"] = round(100 * float((out["total"] > scm.CAPACIDAD["total"]).mean()), 1)
    data["perfiles"] = info["perfiles"]
    data["composicion"] = info["composicion"]
    probs = 100 * (out["total"] > scm.CAPACIDAD["total"]).mean(axis=0)
    idx48 = np.minimum(np.arange(len(fechas)) + 2, len(fechas) - 1)
    data["prob_sat_48h"] = np.round(probs[idx48], 1).tolist()
    data["umbral_alerta"] = UMBRAL_ALERTA
    data["alertas_dia"] = _alertas_dia(data["fechas"], data["total_p50"], data["cola_p50"], data["prob_sat_48h"], scm.CAPACIDAD["total"])
    data["sat_por_capacidad"] = {str(c): round(100 * float((out["total"] > c).mean()), 1) for c in range(96, 131, 2)}
    hay_palancas = any([pct_lleg, pct_est, pct_esp, recorte, adelanto, estres, casos])
    if comparar and "si" in comparar and hay_palancas:
        _, out_b, _ = si.simular_integral(scm.ULTIMO_CONFIABLE, dias, n_rep=N_REP_INTERACTIVO)
        for s in ("ingresos_cama", "total", "cola"):
            data[f"base_{s}_p50"] = np.percentile(out_b[s], 50, axis=0).tolist()

    resumen = []
    if casos:
        detalle = ", ".join(f"{si.CASOS[k].lower()} {nombres[k].lower()} ({'+' if v > 0 else '−'}{abs(v)} % sobre lo normal)"
                            for k, v in casos.items())
        cl, ci = 100 * (info["factor_llegadas"] - 1), 100 * (info["factor_ingresos"] - 1)
        signo = lambda x: f"{'+' if x >= 0 else '−'}{abs(x):.1f} %".replace(".", ",")
        resumen = [html.B("Casos: "), f"{detalle} → llegadas {signo(cl)}, ingresos a cama {signo(ci)}."]
    nota_casos = html.Div(resumen, style={"marginBottom": "8px"}) if resumen else ""
    nota = ""
    if pct_esp < 0:
        nota = html.Div([html.B("Ojo: "), "reducir la espera descarga la cola (sala de urgencias), pero NO libera "
                         "camas: la cama se ocupa igual, solo que antes. Para liberar camas, la palanca es la "
                         "estancia."], style={"border": f"1px solid {NARANJA}", "borderRadius": "6px", "padding": "6px 10px"})
    elif pct_est < 0:
        nota = html.Div([html.B("R7 (recomendaciones): "), "bajar la estancia 5 % libera ~5 camas (ley de Little y "
                         "simulación A5); la palanca más barata antes de ampliar capacidad."],
                        style={"border": f"1px solid {VERDE}", "borderRadius": "6px", "padding": "6px 10px"})
    elif recorte:
        nota = html.Div([html.B("R7 en acción: "), "estás recortando solo las estancias de más de 14 días (el 7 % "
                         "de las estancias que ocupa ~34 % de las camas) — gestión de casos, no un recorte parejo. "
                         "Adelantar altas, en cambio, descarga la cola pero no libera camas: suaviza el pico, no "
                         "baja el nivel."],
                        style={"border": f"1px solid {VERDE}", "borderRadius": "6px", "padding": "6px 10px"})
    return data, (html.Div([nota_casos, nota]) if (nota_casos != "" and nota != "") else (nota_casos or nota))


@callback(Output("simint-datos", "data"), Output("simint-nota", "children"),
          Input("simint-play", "n_clicks"),
          State("simint-tick", "disabled"),
          State("simint-ajuste_llegadas", "value"), State("simint-ajuste_estancia", "value"),
          State("simint-ajuste_espera", "value"), State("simint-plazo", "value"),
          State("simint-recorte_largas", "value"), State("simint-adelanto_altas", "value"),
          State("simint-mezcla_estres", "value"), State("simint-comparar", "value"),
          State({"type": "simint-caso", "caso": ALL}, "value"), State({"type": "simint-caso", "caso": ALL}, "id"),
          prevent_initial_call=True)
def correr_simulacion(_, tick_disabled, pct_lleg, pct_est, pct_esp, dias, recorte, adelanto, estres,
                      comparar, valores_casos, ids_casos):
    if tick_disabled is False:
        raise dash.exceptions.PreventUpdate      # el click fue para PAUSAR: no se vuelve a simular
    return _ejecutar(dias, pct_lleg, pct_est, pct_esp, recorte, adelanto, estres, comparar,
                     valores_casos, ids_casos)


@callback(Output("simint-velocidad", "options"), Output("simint-velocidad", "value"), Input("simint-plazo", "value"))
def velocidad_segun_plazo(plazo):
    """La reproduccion avanza en la unidad natural de cada vista: hora (3 dias), dia (semana/30 dias),
    o dia/semana/mes a elegir en los horizontes largos (90/182/365 dias, con semana o mes como paso por
    defecto para no hacer pesada la reproduccion, pero dejando "1 dia" disponible) — VELOCIDADES_POR_PLAZO."""
    opciones, valor = VELOCIDADES_POR_PLAZO.get(plazo, ([{"label": "1 día", "value": 1}], 1))
    return opciones, valor


SLIDERS_ESCENARIO = [("llegadas", "simint-ajuste_llegadas"), ("estancia", "simint-ajuste_estancia"), ("espera", "simint-ajuste_espera"),
                     ("capacidad", "simint-capacidad"), ("estres", "simint-mezcla_estres"), ("recorte", "simint-recorte_largas"), ("adelanto", "simint-adelanto_altas")]


def _palancas(clave):
    return {**PALANCAS_CERO, **ESCENARIOS[clave][2]}


@callback(Output("simint-pendiente", "data"), Output("simint-comparar", "value"),
          Output("simint-escenario-desc", "children"), Output("simint-escenario-desc", "style"),
          Input("simint-aplicar", "n_clicks"), State("simint-pendiente", "data"), prevent_initial_call=True)
def aplicar_mejora(_n, anterior):
    """Unica accion de la alerta: aplicar la operacion optima. Solo prepara el aviso y activa la comparacion; lo que se ve (el panel que se abre, los controles
    que se desplazan a sus valores y despues el calculo) lo hace `animar_mejora` en el navegador, en ese orden."""
    return {"n": (anterior or {}).get("n", 0) + 1, "palancas": _palancas("optimo")}, ["si"], _descripcion_escenario("optimo"), {"display": "block"}


clientside_callback(
    """
    function(p) {
        // En vivo y en orden: 1) se frena la reproduccion y se abre el panel, 2) cada control se desliza hasta su valor optimo (uno tras otro),
        // 3) cuando ya se vieron moverse, se vuelve a simular desde el dia 1.
        if (!p || !p.n) { return ''; }
        var ns = window.dash_clientside, set = ns.set_props;
        var el = document.getElementById('simint-config');
        set('simint-tick', {disabled: true});
        if (el) { el.classList.add('simint-config--abierto'); }
        clearTimeout(window._simintCfgT);
        var ids = {recorte: 'simint-recorte_largas', adelanto: 'simint-adelanto_altas', llegadas: 'simint-ajuste_llegadas', estancia: 'simint-ajuste_estancia',
                   espera: 'simint-ajuste_espera', estres: 'simint-mezcla_estres', capacidad: 'simint-capacidad'};
        var orden = ['recorte', 'adelanto'], espera = 1000, DESLIZA = 1100;           // se mueven uno por uno; cada uno tarda ~1 s en deslizarse
        var mover = document.getElementById(ids.recorte);
        if (mover && mover.scrollIntoView) { setTimeout(function() { mover.scrollIntoView({block: 'center', behavior: 'smooth'}); }, 450); }   // enfoca las palancas que cambian
        orden.forEach(function(k) {
            if (p.palancas[k] === undefined) { return; }
            setTimeout(function() { set(ids[k], {value: p.palancas[k]}); }, espera);
            espera += DESLIZA + 300;
        });
        var fin = espera + 300;                                                        // todos ya terminaron de moverse
        setTimeout(function() {                                                        // cierra solo el panel y lleva la vista al grafico que se va a volver a ejecutar
            if (el) { el.classList.remove('simint-config--abierto'); if (document.activeElement) { document.activeElement.blur(); } }
            var g = document.getElementById('simint-grafico');
            if (g && g.scrollIntoView) { g.scrollIntoView({behavior: 'smooth', block: 'start'}); }
        }, fin);
        setTimeout(function() { set('simint-escenario', {data: {clave: 'optimo', n: p.n}}); }, fin + 700);
        return '';
    }
    """,
    Output("simint-dummy-cfg", "children"), Input("simint-pendiente", "data"), prevent_initial_call=True)


@callback(*[Output(i, "value", allow_duplicate=True) for _, i in SLIDERS_ESCENARIO], Output("simint-escenario-desc", "children", allow_duplicate=True),
          Output("simint-escenario-desc", "style", allow_duplicate=True), Input("simint-play-reiniciar", "n_clicks"), prevent_initial_call=True)
def volver_a_hoy(_n):
    """«Reiniciar» deja todo como al principio: los controles en cero (la operacion de hoy) y sin la nota de la mejora."""
    pal = _palancas("hoy")
    return (*[pal[k] for k, _ in SLIDERS_ESCENARIO], [], {"display": "none"})


@callback(Output("simint-datos", "data", allow_duplicate=True), Output("simint-nota", "children", allow_duplicate=True),
          Input("simint-escenario", "data"), State("simint-plazo", "value"),
          State({"type": "simint-caso", "caso": ALL}, "value"), State({"type": "simint-caso", "caso": ALL}, "id"),
          prevent_initial_call=True)
def aplicar_escenario(estado, dias, valores_casos, ids_casos):
    """Vuelve a simular desde el dia 1 con la operacion optima (usa sus valores directamente), con el estado anterior en gris punteado y la mejora en color."""
    p = _palancas(estado["clave"])
    data, nota = _ejecutar(dias, p["llegadas"], p["estancia"], p["espera"], p["recorte"], p["adelanto"], p["estres"], ["si"], valores_casos, ids_casos)
    data["conserva_historial"] = True          # las alertas de la corrida anterior siguen a la vista (marcadas como resueltas con la mejora)
    return data, nota


@callback(Output("simint-filtro", "data"),
          Input({"type": "simint-chip-edad", "edad": ALL}, "n_clicks"),
          Input({"type": "simint-chip-sexo", "sexo": ALL}, "n_clicks"),
          Input({"type": "simint-chip-ruta", "ruta": ALL}, "n_clicks"),
          State("simint-filtro", "data"), prevent_initial_call=True)
def actualizar_filtro(_n_edad, _n_sexo, _n_ruta, filtro):
    """Un clic explicito en un chip de edad/ruta/sexo filtra la radiografia a esa categoria; el chip "Todos"/
    "Todas" (primera opcion de cada grupo, activa por defecto) vuelve a quitar el filtro de ese grupo."""
    filtro = dict(filtro or {})
    disparo = dash.ctx.triggered_id
    if isinstance(disparo, dict):
        tipo = disparo["type"]
        if tipo == "simint-chip-edad":
            filtro["edad"] = None if disparo["edad"] == "todas" else disparo["edad"]
        elif tipo == "simint-chip-sexo":
            filtro["sexo"] = None if disparo["sexo"] == "todas" else disparo["sexo"]
        elif tipo == "simint-chip-ruta":
            filtro["ruta"] = None if disparo["ruta"] == "todas" else disparo["ruta"]
    return filtro


FILAS_VISTA_GRAFICO = {"todo": ["flujo", "camas", "espera"], "flujo": ["flujo"], "camas": ["camas"], "espera": ["espera"]}
TITULO_FILA = {"flujo": "Flujo: llegan, entran a cama, salen de alta", "camas": "Camas ocupadas", "espera": "Pacientes esperando cama a la vez (cota inferior)"}


def _hover_tpl(etiqueta, gran, modo="suma"):
    """hovertemplate del grafico: el valor crudo del dia para "dia"; con velocidad "semana"/"mes" usa el
    total (`modo="suma"`: llegadas, entran a cama, altas) o el promedio (`modo="media"`: camas ocupadas,
    esperando cama) de la ventana (customdata, ver customdata_ventana) y declara el rango de fechas en vez de
    un solo dia, para no confundirlo con el valor suelto de ese dia (reportado el 20-nov: el panel de la
    radiografia ya agregaba por semana/mes pero el grafico seguia mostrando el dato de un solo dia al pasar
    el mouse). Se muestra el mismo valor sin importar en que dia de la semana/mes caiga el mouse (no solo en
    el ultimo): obligar a acertarle al dia exacto de corte seria mas dificil de usar sin ganar nada."""
    if gran == "dia":
        return "%{x|%d-%m}<br>%{y:.0f} " + etiqueta + "<extra></extra>"
    art = "la" if gran == "semana" else "el"
    cola = f"en {art} {gran} (promedio diario)" if modo == "media" else f"en {art} {gran} (total)"
    return f"Del %{{customdata[1]}} al %{{customdata[2]}}<br>%{{customdata[0]:.0f}} {etiqueta} {cola}<extra></extra>"


@callback(Output("simint-grafico", "figure"),
          Input("simint-datos", "data"), Input("simint-capacidad", "value"), Input("simint-vista-radio", "value"),
          Input("simint-velocidad", "value"), State("simint-cursor", "data"), State("theme-store", "data"))
def mostrar(data, capacidad, vista, velocidad, cursor, tema):
    """Construye la figura YA RECORTADA segun el cursor actual (no dibuja el "futuro": ni siquiera existe en
    el trace, no es un velo encima). Cada trace recortable lleva su serie COMPLETA en `meta.fullY` (y la
    fecha completa en `layout.meta.fullX`) para que el clientside de reproduccion solo tenga que extenderla
    tick a tick con Plotly.restyle, sin volver a pedirle nada al servidor. El eje x queda FIJO al rango
    completo para que el recorte no encoja el eje."""
    if not data:
        fig = go.Figure()
        fig.add_annotation(text="Presiona ▶ Reproducir para simular", showarrow=False,
                           font=dict(size=14, color=GRIS), xref="paper", yref="paper", x=0.5, y=0.5)
        tg.aplicar(fig, tg.es_oscuro(tema))      # el estado vacio tambien debe adaptarse a claro/oscuro
        return fig
    fechas = pd.to_datetime(data["fechas"])
    cap = int(capacidad or scm.CAPACIDAD["total"])
    es_horario = data.get("es_horario", False)
    unidad = "hora" if es_horario else "día"
    upto = (cursor + 1) if isinstance(cursor, int) else len(fechas)
    upto = max(1, min(upto, len(fechas)))
    fechas_vis = fechas[:upto]

    # Ventana del hover (20-nov): con velocidad "semana"/"mes" cada serie de flujo/nivel se agrega por la
    # MISMA ventana real de calendario que usa la radiografia (ventanas_del_grafico), para que el hover del
    # grafico y el de la radiografia digan lo mismo. En "1 dia" (o la vista horaria) no se toca nada.
    gran = "dia" if es_horario else GRANULARIDAD_POR_VELOCIDAD.get(velocidad, "dia")
    customdatas = {}
    if gran != "dia":
        inis, fins = ventanas_del_grafico(fechas, velocidad)
        for clave, modo in (("llegadas_p50", "suma"), ("ingresos_cama_p50", "suma"), ("altas_p50", "suma"),
                            ("total_p50", "media"), ("cola_p50", "media")):
            if clave in data:
                agregado = serie_agregada_por_ventana(data[clave], inis, fins, modo)
                customdatas[clave] = customdata_ventana(agregado, fechas, inis, fins)

    filas = FILAS_VISTA_GRAFICO.get(vista or "todo", FILAS_VISTA_GRAFICO["todo"])
    n = len(filas)
    titulos = []
    for clave in filas:
        if clave == "flujo":
            titulos.append("Flujo por hora: entran a cama, salen de alta" if es_horario else TITULO_FILA["flujo"])
        elif clave == "camas":
            titulos.append(f"Camas ocupadas (capacidad: {cap})")
        else:
            titulos.append(f"Pacientes esperando cama a la vez (cota inferior, por {unidad})")
    alturas = {1: [1.0], 2: [0.45, 0.55], 3: [0.28, 0.42, 0.30]}[n]

    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=alturas,
                        subplot_titles=tuple(titulos))

    def recorte(serie_completa):
        return serie_completa[:upto]

    # Leyenda POR fila (17-nov): antes era una sola leyenda horizontal debajo de los 3 graficos, mezclando
    # lineas de filas distintas y empujando el espacio de dibujo hacia arriba. Plotly >= 5.15 permite varias
    # leyendas (legend/legend2/legend3, una por fila via el atributo `legend` de cada trace); cada una se
    # ubica en la esquina superior derecha de SU fila (ver legend_layout abajo), chica y semitransparente
    # para no tapar la curva, y el espacio que libera abajo pasa al alto real del grafico (dcc.Graph mas
    # alto + margen inferior minimo).
    LEGEND_IDS = ["legend", "legend2", "legend3"]

    for r, clave in enumerate(filas, start=1):
        legend_id = LEGEND_IDS[r - 1]
        if clave == "flujo":
            if not es_horario:
                fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["llegadas_p50"]), mode="lines",
                                         line=dict(color=GRIS, width=1.6), name="Llegadas al hospital", legend=legend_id,
                                         meta={"fullY": data["llegadas_p50"]}, customdata=customdatas.get("llegadas_p50"),
                                         hovertemplate=_hover_tpl("llegadas", gran)), row=r, col=1)
            fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["ingresos_cama_p50"]), mode="lines",
                                     line=dict(color=VERDE, width=1.8), name="Entran a cama", legend=legend_id,
                                     meta={"fullY": data["ingresos_cama_p50"]}, customdata=customdatas.get("ingresos_cama_p50"),
                                     hovertemplate=_hover_tpl("entran a cama", gran)), row=r, col=1)
            fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["altas_p50"]), mode="lines",
                                     line=dict(color=NARANJA, width=1.8), name="Salen de alta", legend=legend_id,
                                     meta={"fullY": data["altas_p50"]}, customdata=customdatas.get("altas_p50"),
                                     hovertemplate=_hover_tpl("altas", gran)), row=r, col=1)
            if "base_ingresos_cama_p50" in data:
                fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["base_ingresos_cama_p50"]), mode="lines",
                                         line=dict(color=GRIS, width=1.4, dash="dot"), name="Antes de la mejora",
                                         legend=legend_id, meta={"fullY": data["base_ingresos_cama_p50"]},
                                         legendgroup="base", showlegend=True, hoverinfo="skip"), row=r, col=1)
        elif clave == "camas":
            fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["total_p90"]), mode="lines", line=dict(width=0),
                                     showlegend=False, meta={"fullY": data["total_p90"]}, hoverinfo="skip"), row=r, col=1)
            fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["total_p10"]), mode="lines", line=dict(width=0),
                                     fill="tonexty", fillcolor="rgba(42,111,176,0.15)", name="Banda 10-90 %",
                                     legend=legend_id, meta={"fullY": data["total_p10"]}, hoverinfo="skip"), row=r, col=1)
            fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["total_p50"]), mode="lines", line=dict(color=AZUL, width=2),
                                     name="Camas ocupadas (mediana)", legend=legend_id, meta={"fullY": data["total_p50"]},
                                     customdata=customdatas.get("total_p50"),
                                     hovertemplate=_hover_tpl("camas ocupadas", gran, "media")), row=r, col=1)
            fig.add_trace(go.Scatter(x=fechas, y=[cap] * len(fechas), mode="lines",   # linea constante: SIN recortar
                                     line=dict(color=NARANJA, dash="dash"), name=f"Capacidad HUN ({cap})", legend=legend_id,
                                     hoverinfo="skip"), row=r, col=1)
            if "base_total_p50" in data:
                fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["base_total_p50"]), mode="lines",
                                         line=dict(color=GRIS, width=1.4, dash="dot"), name="Antes de la mejora",
                                         legend=legend_id, meta={"fullY": data["base_total_p50"]},
                                         legendgroup="base", showlegend=True, hoverinfo="skip"), row=r, col=1)
        else:  # espera
            fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["cola_p90"]), mode="lines", line=dict(width=0),
                                     showlegend=False, meta={"fullY": data["cola_p90"]}, hoverinfo="skip"), row=r, col=1)
            fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["cola_p10"]), mode="lines", line=dict(width=0),
                                     fill="tonexty", fillcolor="rgba(192,57,43,0.13)", showlegend=False,
                                     meta={"fullY": data["cola_p10"]}, hoverinfo="skip"), row=r, col=1)
            fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["cola_p50"]), mode="lines", line=dict(color=ROJO, width=2),
                                     name="Esperando cama (mediana)", legend=legend_id, meta={"fullY": data["cola_p50"]},
                                     customdata=customdatas.get("cola_p50"),
                                     hovertemplate=_hover_tpl("esperando cama", gran, "media")), row=r, col=1)
            if "base_cola_p50" in data:
                fig.add_trace(go.Scatter(x=fechas_vis, y=recorte(data["base_cola_p50"]), mode="lines",
                                         line=dict(color=GRIS, width=1.4, dash="dot"), name="Antes de la mejora",
                                         legend=legend_id, meta={"fullY": data["base_cola_p50"]},
                                         legendgroup="base", showlegend=True, hoverinfo="skip"), row=r, col=1)

    dark = tg.es_oscuro(tema)
    texto_legenda = tg.OSCURO["texto"] if dark else tg.CLARO["texto"]
    fondo_legenda = "rgba(23,33,43,0.72)" if dark else "rgba(255,255,255,0.78)"
    borde_legenda = "rgba(255,255,255,0.14)" if dark else "rgba(10,37,64,0.10)"
    legend_layout = {}
    for r, legend_id in enumerate(LEGEND_IDS[:n], start=1):
        eje = "yaxis" if r == 1 else f"yaxis{r}"
        top = fig.layout[eje].domain[1]
        legend_layout[legend_id] = dict(
            x=0.995, xanchor="right", y=top - 0.012, yanchor="top",
            font=dict(size=10, color=texto_legenda), bgcolor=fondo_legenda, bordercolor=borde_legenda,
            borderwidth=1, itemsizing="constant", tracegroupgap=0,
        )

    fig.update_layout(template="simple_white", margin=dict(l=40, r=20, t=40, b=16), hovermode="x unified",
                      meta={"fullX": [str(f) for f in fechas]}, **legend_layout)
    for ann in fig.layout.annotations:
        ann.font = dict(size=12)
        ann.x = 0.0
        ann.xanchor = "left"

    fig.update_xaxes(range=[fechas[0], fechas[-1]], autorange=False, showspikes=True, spikemode="across",
                     spikesnap="cursor", spikethickness=1, spikedash="dot", spikecolor=GRIS)
    tg.aplicar(fig, dark)
    return fig


@callback(Output("simint-radiografia-titulo", "children"), Output("simint-radiografia-body", "children"),
          Input("simint-grafico", "hoverData"), Input("simint-cursor", "data"), Input("simint-datos", "data"),
          Input("simint-vista-radio", "value"), Input("simint-filtro", "data"), Input("simint-velocidad", "value"))
def radiografia(hoverData, cursor, data, vista, filtro, velocidad):
    vista = vista or "todo"
    if not data or "composicion" not in data:
        # Estado cero (antes de reproducir, o vista horaria sin perfiles): la MISMA ventana con metricas en
        # 0 en vez de quedar en blanco — asi se ve la forma del panel desde el primer momento.
        etapas_mostrar = VISTA_ETAPAS.get(vista, VISTA_ETAPAS["todo"])
        filas_metricas = [fila_metrica(nombre_e, "0", escala, html.Div(className="simint-picto"))
                          for etapa in etapas_mostrar for nombre_e, escala in [ETAPAS_INFO[etapa]]]
        cuerpo = [html.Div(filas_metricas, className="simint-radio__filas")]
        if vista == "camas":
            cuerpo.append(modulo_tablero_camas(0, 0))
        cuerpo.append(panel_filtros(filtro))
        return "Presiona ▶ Reproducir para simular", cuerpo
    fechas = data["fechas"]
    idx = 0
    try:
        disparo = dash.ctx.triggered_id
    except Exception:
        disparo = None
    if disparo == "simint-cursor" and isinstance(cursor, int):
        idx = max(0, min(cursor, len(fechas) - 1))
    elif disparo == "simint-grafico" and hoverData and hoverData.get("points"):
        p = hoverData["points"][0]
        i = p.get("pointNumber", p.get("pointIndex"))
        if isinstance(i, int):
            idx = max(0, min(i, len(fechas) - 1))
    elif isinstance(cursor, int):
        idx = max(0, min(cursor, len(fechas) - 1))
    elif hoverData and hoverData.get("points"):
        p = hoverData["points"][0]
        i = p.get("pointNumber", p.get("pointIndex"))
        if isinstance(i, int):
            idx = max(0, min(i, len(fechas) - 1))

    perfiles = data["perfiles"]
    ini, fin, fecha_rep, gran = ventana_radiografia(idx, fechas, velocidad)
    titulo_txt = titulo_radiografia(fecha_rep, pd.Timestamp(fechas[fin - 1]), gran)

    ancho = fin - ini
    ini_prev, fin_prev = ini - ancho, ini
    hay_prev = ini_prev >= 0

    vista = vista or "todo"
    etapas_mostrar = VISTA_ETAPAS.get(vista, VISTA_ETAPAS["todo"])
    # Escala del pictograma segun el ANCHO de la ventana (20-nov): con velocidad "semana"/"mes" las metricas
    # de conteo (AGREGACION "suma": llegadas, ingresos a cama, altas) suman varios dias y disparaban cientos
    # de figuras (la ventana del pictograma crecia sin limite). Las de nivel ("media": esperando, en_cama) no
    # crecen con la ventana (son un promedio), asi que su escala se deja igual. Multiplicar la escala base por
    # los dias de la ventana mantiene el numero de figuras mas o menos constante (~20-30) en dia/semana/mes.
    dias_ventana = max(fin - ini, 1)
    filas_metricas = []
    for etapa in etapas_mostrar:
        nombre_e, escala = ETAPAS_INFO[etapa]
        escala_efectiva = escala * dias_ventana if AGREGACION[etapa] == "suma" else escala
        agregado = _agregar(etapa, data["composicion"][etapa], ini, fin)
        pic, total = pictograma(agregado, perfiles, escala_efectiva, filtro)
        flecha = None
        if hay_prev:
            agregado_prev = _agregar(etapa, data["composicion"][etapa], ini_prev, fin_prev)
            _, total_prev = pictograma(agregado_prev, perfiles, escala_efectiva, filtro)
            flecha = flecha_tendencia(etapa, total, total_prev)
        filas_metricas.append(fila_metrica(nombre_e, f"{total:.0f}", escala_efectiva, pic, flecha))

    cuerpo = [html.Div(filas_metricas, className="simint-radio__filas")]
    if vista == "camas":
        ventana_n = max(fin - ini, 1)
        ad = float(np.mean(data["adultos_p50"][ini:fin])) if ventana_n > 1 else data["adultos_p50"][idx]
        ni = float(np.mean(data["ninos_p50"][ini:fin])) if ventana_n > 1 else data["ninos_p50"][idx]
        cuerpo.append(modulo_tablero_camas(ad, ni))
    cuerpo.append(panel_filtros(filtro))
    return titulo_txt, cuerpo


# ----------------------------------------------------------------------
# Cinta de reproduccion: el simulador "corriendo". Todo clientside — los datos ya estan completos en el
# Store; reproducir solo mueve un cursor y EXTIENDE las trazas con Plotly.restyle (usa meta.fullY/fullX ya
# puestos por mostrar() al construir la figura) — no se dibuja el futuro, no hay velo. La radiografia sigue
# el cursor con su callback de servidor. Unico disparador de la simulacion: "Reproducir"; pausar NO recalcula.
# ----------------------------------------------------------------------
clientside_callback(
    """
    function(n, disabled) {
        var ns = window.dash_clientside;
        if (disabled) {
            // estaba en reposo (inicio o terminada): este click dispara TAMBIEN el callback de Python (mismo
            // Input) que (re)simula desde cero; mientras tanto mostramos "Cargando..." y el tick arranca
            // cuando lleguen datos nuevos. El boton partido ya esta oculto en este estado (no_update).
            return [true, "Cargando…", 0, ns.no_update, ns.no_update];
        }
        // estaba reproduciendo -> pausa instantanea, sin recalcular Y sin tocar el cursor: en vez de volver a
        // mostrar "Reproducir" (que reiniciaba todo al presionarlo), se oculta el boton unico y aparece el
        // boton partido Continuar/Reiniciar (20-nov).
        return [true, ns.no_update, ns.no_update, {display: "none"}, {display: "flex"}];
    }
    """,
    Output("simint-tick", "disabled", allow_duplicate=True), Output("simint-play", "children", allow_duplicate=True),
    Output("simint-cursor", "data", allow_duplicate=True),
    Output("simint-play", "style", allow_duplicate=True), Output("simint-play-split", "style", allow_duplicate=True),
    Input("simint-play", "n_clicks"), State("simint-tick", "disabled"),
    prevent_initial_call=True,
)

clientside_callback(
    """
    function(n) {           // mitad "Continuar" del boton partido: reanuda el MISMO cursor, sin recalcular
        return [false, {display: "flex", alignItems: "center"}, {display: "none"}, "\\u23F8 Pausa"];
    }
    """,
    Output("simint-tick", "disabled", allow_duplicate=True),
    Output("simint-play", "style", allow_duplicate=True),
    Output("simint-play-split", "style", allow_duplicate=True),
    Output("simint-play", "children", allow_duplicate=True),
    Input("simint-play-continuar", "n_clicks"),
    prevent_initial_call=True,
)

clientside_callback(
    """
    function(n) {           // mitad "Reiniciar": borra los datos y el progreso y vuelve a mostrar el boton
                             // "Reproducir" solo — NO vuelve a simular hasta que el usuario lo presione.
        window._simintUltAlerta = null; window._simintUltTipo = {}; window._simintPausados = {}; window._simintHist = []; window._simintVista = -1;
        window.dash_clientside.set_props('simint-alerta-texto', {children: JSON.stringify({idle: true, n: Date.now()})});
        return [null, null, true, window.dash_clientside.no_update, {display: "flex", alignItems: "center"}, {display: "none"},
                "▶ Reproducir", {width: "0%"}, "0 %", ""];
    }
    """,
    Output("simint-datos", "data", allow_duplicate=True),
    Output("simint-cursor", "data", allow_duplicate=True),
    Output("simint-tick", "disabled", allow_duplicate=True),
    Output("simint-alerta", "style", allow_duplicate=True),
    Output("simint-play", "style", allow_duplicate=True),
    Output("simint-play-split", "style", allow_duplicate=True),
    Output("simint-play", "children", allow_duplicate=True),
    Output("simint-player-fill", "style", allow_duplicate=True),
    Output("simint-player-pct", "children", allow_duplicate=True),
    Output("simint-player-fecha", "children", allow_duplicate=True),
    Input("simint-play-reiniciar", "n_clicks"),
    prevent_initial_call=True,
)

clientside_callback(
    r"""
    function(n, cursorReal, vel, data) {
        var ns = window.dash_clientside;
        var NO8 = [ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update];
        if (!data || !data.fechas || cursorReal === null || cursorReal === undefined) { return NO8; }
        var SUB = 7;                              // 7 subframes x 50ms = ~350ms por paso real (mismo ritmo de antes)
        var max = data.fechas.length - 1;
        var nextCursor = Math.min(cursorReal + (vel || 1), max);
        var sub = (window._simintSub || 0);
        var pasos = Math.max(nextCursor - cursorReal, 1);        // dias reales que cubre este paso (1, 7 o 30)
        var avance = Math.min(sub / SUB, 1) * pasos;             // dias reales recorridos dentro del paso (0..pasos)
        var diaEntero = Math.min(cursorReal + Math.floor(avance), nextCursor);
        var fracDia = avance - Math.floor(avance);

        // 1) Dibuja el recorte revelando los DIAS REALES intermedios a medida que avanzan los subframes, en
        //    vez de solo una linea recta interpolada entre el dia de hoy y el de dentro de una semana/mes
        //    (eso escondia el zigzag real de los dias intermedios y los hacia aparecer de golpe al terminar
        //    el paso — "se dibuja por tramos", reportado el 20-nov). Con velocidad "1 dia" (pasos=1) esto es
        //    identico a antes: un solo punto interpolado hacia el siguiente dia.
        var cont = document.getElementById('simint-grafico');
        var gd = cont && (cont.querySelector('.js-plotly-plot') || cont);
        if (gd && gd.data && gd.layout && gd.layout.meta && gd.layout.meta.fullX) {
            try {
                var fx = gd.layout.meta.fullX;
                var idxs = [], xs = [], ys = [];
                for (var k = 0; k < gd.data.length; k++) {
                    var tr = gd.data[k];
                    if (tr.meta && tr.meta.fullY) {
                        var baseY = tr.meta.fullY.slice(0, diaEntero + 1);
                        var baseX = fx.slice(0, diaEntero + 1);
                        if (fracDia > 0 && tr.meta.fullY[diaEntero + 1] !== undefined) {
                            var y0 = tr.meta.fullY[diaEntero], y1 = tr.meta.fullY[diaEntero + 1];
                            var t0 = new Date(fx[diaEntero]).getTime(), t1 = new Date(fx[diaEntero + 1]).getTime();
                            baseY = baseY.concat([y0 + (y1 - y0) * fracDia]);
                            baseX = baseX.concat([new Date(t0 + (t1 - t0) * fracDia).toISOString()]);
                        }
                        idxs.push(k); xs.push(baseX); ys.push(baseY);
                    }
                }
                if (idxs.length) { Plotly.restyle(gd, {x: xs, y: ys}, idxs); }
            } catch (e) {}
        }

        // 2) Barra de progreso, % y fecha — avanzan con el mismo "avance" en dias reales (antes usaban una
        //    fraccion 0..1 del paso completo, que con semana/mes las dejaba casi quietas y saltando de golpe
        //    al terminar el paso: el mismo bug "por tramos" de arriba).
        var posFrac = Math.min(cursorReal + avance, max);
        var pct = (max > 0) ? 100 * posFrac / max : 100;
        var fillStyle = {width: pct + '%'};
        var pctTxt = Math.round(pct) + ' %';
        var fechaOut = data.fechas[Math.min(diaEntero, max)];

        // 3) Avanza el subframe; solo al llegar al limite (cada SUB ticks) se da el paso REAL (cursor, alerta,
        //    fin de reproduccion) — la logica de alerta/fin es la MISMA que antes, solo que ahora corre menos
        //    seguido (una vez por paso real, no una vez por cada tick rapido de 50ms).
        window._simintSub = (sub + 1) % SUB;
        if (window._simintSub !== 0 || nextCursor === cursorReal) {
            return [ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, fillStyle, pctTxt, fechaOut];
        }
        var c = nextCursor;
        var al = data.alertas_dia || [];
        if (al.length > c && al[c]) {
            var a = al[c], aPrev = (cursorReal < al.length) ? al[cursorReal] : null;
            var ult = window._simintUltTipo = window._simintUltTipo || {};
            var pausados = window._simintPausados = window._simintPausados || {};
            var clave = a.tipo + '|' + a.gravedad;                               // cada alerta (tipo y gravedad) se muestra UNA sola vez por corrida: despues queda como procesada
            var nueva = ult[clave] === undefined;
            if (nueva && window._simintUltAlerta !== c) {
                window._simintUltAlerta = c;
                ult[clave] = c;
                var ob = {tipo: a.tipo, gravedad: a.gravedad, titulo: a.titulo, texto: a.texto, fecha: data.fechas[c],
                          acciones: a.acciones, paso: a.paso, mejora: a.mejora, rec: a.rec, alerta: a.alerta, pausada: false};
                var hist = window._simintHist = window._simintHist || [];
                ob.pausada = true;                                                     // toda alerta nueva (aviso o critica) frena la simulacion para poder revisarla y mejorar
                if (a.gravedad === 'Alta') { pausados[a.tipo] = true; }
                hist.push(ob); window._simintVista = hist.length - 1;
                var o1 = Object.assign({}, ob, {pos: hist.length + ' de ' + hist.length, ultima: true});
                return [c, true, "▶ Reproducir", {display: "flex", alignItems: "center"}, JSON.stringify(o1), fillStyle, pctTxt, fechaOut];
            }
        }
        if (c >= max) { return [c, true, "▶ Reproducir", ns.no_update, ns.no_update, fillStyle, pctTxt, fechaOut]; }
        return [c, ns.no_update, ns.no_update, ns.no_update, ns.no_update, fillStyle, pctTxt, fechaOut];
    }
    """,
    Output("simint-cursor", "data", allow_duplicate=True),
    Output("simint-tick", "disabled", allow_duplicate=True),
    Output("simint-play", "children", allow_duplicate=True),
    Output("simint-alerta", "style", allow_duplicate=True),
    Output("simint-alerta-texto", "children", allow_duplicate=True),
    Output("simint-player-fill", "style", allow_duplicate=True),
    Output("simint-player-pct", "children", allow_duplicate=True),
    Output("simint-player-fecha", "children", allow_duplicate=True),
    Input("simint-tick", "n_intervals"),
    State("simint-cursor", "data"), State("simint-velocidad", "value"), State("simint-datos", "data"),
    prevent_initial_call=True,
)

clientside_callback(
    """
    function(txt) {         // pinta la alerta (JSON): gravedad, titulo, que paso, recomendacion, posicion en el historial y los enlaces
        var ns = window.dash_clientside;
        var NO = [ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update];
        if (!txt) { return NO; }
        var a = JSON.parse(txt);
        if (a.idle) {          // sin alertas todavia (o corrida nueva): la tarjeta queda a la vista, en espera
            return ["", "Sin alertas por ahora", "Las alertas saltarán aquí mientras corre la simulación, y la tarjeta se queda a la vista.", "", "", "",
                    "alert-inline simint-alerta simint-alerta--idle", {display: 'none'}, '/alertas', '/recomendaciones', ''];
        }
        var clase = "alert-inline simint-alerta simint-alerta--" + (a.resuelta ? 'resuelta' : (a.gravedad === 'Alta' ? 'alta' : 'media'));
        var boton = {display: (a.mejora && a.ultima && !a.resuelta) ? 'block' : 'none'};
        var queDijo = a.texto + ' (' + a.fecha + ')' + (a.pausada ? ' La simulación se detuvo para que lo revises.' : '');
        return ["Gravedad " + a.gravedad.toLowerCase() + (a.gravedad === 'Alta' ? ' · crítica' : ' · aviso') + (a.resuelta ? ' · resuelta con la mejora' : ''), a.titulo, queDijo,
                (a.acciones || []).join('  ·  '), a.paso ? ('Primer paso: ' + a.paso) : '', a.pos || '', clase, boton,
                '/alertas#alerta-' + (a.alerta || 'A2'), '/recomendaciones#rec-R' + (a.rec || 4),
                (a.gravedad !== 'Alta' && a.mejora && a.ultima && !a.resuelta) ? 'Aún no es crítica: aplica la mejora ahora, antes de que escale.' : ''];
    }
    """,
    Output("simint-alerta-grav", "children"), Output("simint-alerta-titulo", "children"), Output("simint-alerta-detalle", "children"),
    Output("simint-alerta-acciones", "children"), Output("simint-alerta-paso", "children"), Output("simint-alerta-pos", "children"),
    Output("simint-alerta", "className"), Output("simint-aplicar", "style"),
    Output("simint-alerta-link-alerta", "href"), Output("simint-alerta-link-rec", "href"), Output("simint-alerta-nota", "children"),
    Input("simint-alerta-texto", "children"), prevent_initial_call=True)

clientside_callback(
    """
    function(prev, next) {       // flechas del historial: recorre las alertas anteriores sin interrumpir la reproduccion
        var ns = window.dash_clientside;
        var hist = window._simintHist || [];
        if (!hist.length) { return ns.no_update; }
        var quien = ns.callback_context.triggered.length ? ns.callback_context.triggered[0].prop_id : '';
        var i = (window._simintVista === undefined || window._simintVista < 0) ? hist.length - 1 : window._simintVista;
        if (quien.indexOf('-prev.') >= 0) { i = Math.max(0, i - 1); } else if (quien.indexOf('-next.') >= 0) { i = Math.min(hist.length - 1, i + 1); }
        window._simintVista = i;
        var ob = Object.assign({}, hist[i], {pos: (i + 1) + ' de ' + hist.length, ultima: i === hist.length - 1});
        return JSON.stringify(ob);
    }
    """,
    Output("simint-alerta-texto", "children", allow_duplicate=True),
    Input("simint-alerta-prev", "n_clicks"), Input("simint-alerta-next", "n_clicks"), prevent_initial_call=True)

clientside_callback(
    """
    function(fig) {          // la figura nueva ya esta dibujada: ahora si arranca la reproduccion desde el dia 1
        var ns = window.dash_clientside;
        if (!window._simintArrancar || !fig) { return [ns.no_update, ns.no_update]; }
        window._simintArrancar = false;
        var gr = document.getElementById('simint-grafico'); if (gr) { gr.style.opacity = '1'; }
        return [false, "\\u23F8 Pausa"];
    }
    """,
    Output("simint-tick", "disabled", allow_duplicate=True), Output("simint-play", "children", allow_duplicate=True),
    Input("simint-grafico", "figure"), prevent_initial_call=True)

clientside_callback(
    """
    function(n) {                                          // boton Continuar del banner: reanuda y lo oculta
        return [false, "\\u23F8 Pausa", window.dash_clientside.no_update];
    }
    """,
    Output("simint-tick", "disabled", allow_duplicate=True),
    Output("simint-play", "children", allow_duplicate=True),
    Output("simint-alerta", "style", allow_duplicate=True),
    Input("simint-continuar", "n_clicks"),
    prevent_initial_call=True,
)

clientside_callback(
    """
    function(cursor, data) {
        var ns = window.dash_clientside;
        if (!data || !data.fechas) { return [ns.no_update, "", ""]; }
        var fechas = data.fechas, n = fechas.length;
        var fin = (cursor === null || cursor === undefined);
        var i = fin ? n - 1 : Math.max(0, Math.min(cursor, n - 1));
        var upto = i + 1;
        var cont = document.getElementById('simint-grafico');
        var gd = cont && (cont.querySelector('.js-plotly-plot') || cont);
        if (gd && gd.data && gd.layout && gd.layout.meta && gd.layout.meta.fullX) {
            try {
                var fx = gd.layout.meta.fullX;
                var idxs = [], xs = [], ys = [];
                for (var k = 0; k < gd.data.length; k++) {
                    var tr = gd.data[k];
                    if (tr.meta && tr.meta.fullY) {
                        idxs.push(k);
                        xs.push(fx.slice(0, upto));
                        ys.push(tr.meta.fullY.slice(0, upto));
                    }
                }
                if (idxs.length) { Plotly.restyle(gd, {x: xs, y: ys}, idxs); }
            } catch (e) {}
        }
        var pct = fin ? 100 : (n > 1 ? 100 * i / (n - 1) : 100);
        return [{width: pct + '%'}, Math.round(pct) + ' %', fin ? "" : fechas[i]];
    }
    """,
    Output("simint-player-fill", "style", allow_duplicate=True), Output("simint-player-pct", "children", allow_duplicate=True),
    Output("simint-player-fecha", "children", allow_duplicate=True),
    Input("simint-cursor", "data"), State("simint-datos", "data"),
    prevent_initial_call=True,
)

clientside_callback(
    """
    function(data) {        // datos nuevos: reinicia cursor/alerta/filtro y ARRANCA la reproduccion
        var ns = window.dash_clientside;
        if (!data) {
            // lo puso en null el boton "Reiniciar" (20-nov): ese boton ya dejo todo en su estado inicial,
            // aqui no hay nada que arrancar.
            return [ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update, ns.no_update];
        }
        if (data.cursor_inicial !== undefined && data.cursor_inicial !== null) {       // viene de una alerta: sigue en el mismo dia (y recuerda que alertas ya frenaron)
            window._simintUltAlerta = data.cursor_inicial;
            if (data.pausado) {                                                         // «Mostrar operación óptima»: queda en pausa para comparar
                return [data.cursor_inicial, window.dash_clientside.no_update, true, "\\u25B6 Reproducir", {}, {display: "none"}, {display: "flex", alignItems: "center"}];
            }
            return [data.cursor_inicial, window.dash_clientside.no_update, false, "\\u23F8 Pausa", {}, {display: "flex", alignItems: "center"}, {display: "none"}];
        }
        var conserva = !!data.conserva_historial;
        window._simintUltAlerta = null; window._simintUltTipo = {}; window._simintPausados = {};
        if (conserva) {            // mejora aplicada: las alertas de la corrida anterior siguen consultables con las flechas, marcadas como resueltas
            (window._simintHist || []).forEach(function(h) { h.resuelta = true; });
        } else { window._simintHist = []; window._simintVista = -1; }
        // La reproduccion NO arranca todavia: espera a que llegue y se dibuje la figura nueva (si arrancara contra la figura vieja, el grafico parpadearia y se trabaria).
        window._simintArrancar = true;
        var gr = document.getElementById('simint-grafico'); if (gr) { gr.style.transition = 'opacity .25s ease'; gr.style.opacity = '0.35'; }
        if (!conserva) { ns.set_props('simint-alerta-texto', {children: JSON.stringify({idle: true, n: Date.now()})}); }
        return [0, ns.no_update, true, "\\u23F3 Calculando…", {}, {display: "flex", alignItems: "center"}, {display: "none"}];
    }
    """,
    Output("simint-cursor", "data", allow_duplicate=True),
    Output("simint-alerta", "style", allow_duplicate=True),
    Output("simint-tick", "disabled", allow_duplicate=True),
    Output("simint-play", "children", allow_duplicate=True),
    Output("simint-filtro", "data", allow_duplicate=True),
    Output("simint-play", "style", allow_duplicate=True),
    Output("simint-play-split", "style", allow_duplicate=True),
    Input("simint-datos", "data"),
    prevent_initial_call=True,
)

# Hover sincronizado (20-nov, version con listener nativo; corregido 17-nov: excluir la fila ya nativa):
# al pasar el mouse por cualquiera de las filas visibles del grafico, la MISMA linea vertical cruza las
# otras filas y abre sus respectivas ventanas de datos. La version anterior dependia de la prop "hoverData"
# de Dash (un viaje de ida y vuelta por cada movimiento del mouse, con el riesgo de perder eventos si llegan
# muy seguido) para despues llamar a Plotly.Fx.hover; ahora el listener se cuelga UNA SOLA VEZ directamente
# sobre el evento nativo "plotly_hover" del grafico (gd.on), sin pasar por Dash, así no hay retraso ni
# eventos que se pierdan. Se re-cuelga en cada figura nueva pero el guard gd._simintHoverBound evita
# duplicar el listener. Localiza las trazas representativas POR NOMBRE (no por indice: la vista horaria
# omite "Llegadas al hospital" y las vistas filtradas -flujo/camas/espera- cambian cuantas filas hay). El
# guard gd._simintSyncing evita el bucle: el propio Fx.hover tambien emite "plotly_hover".
# BUG (reportado 17-nov): el forzado incluia tambien el eje de la fila que el mouse YA estaba tocando, asi
# que esa fila recibia DOS cajas (la nativa del navegador + la que este codigo volvia a abrir), ademas de
# las de las otras filas. Ahora se excluyen los ejes que ya vienen en el evento nativo (ev.points) y solo
# se fuerza el hover en las filas QUE NO está tocando el mouse — la fila bajo el cursor conserva su unica
# caja original (linea de tendencia con nombre y numero); las otras siguen abriendose en sincronia.
clientside_callback(
    """
    function(figure) {
        var ns = window.dash_clientside;
        var cont = document.getElementById('simint-grafico');
        var gd = cont && (cont.querySelector('.js-plotly-plot') || cont);
        if (!gd || !gd.on || gd._simintHoverBound) { return ns.no_update; }
        gd._simintHoverBound = true;
        var nombres = ['Entran a cama', 'Camas ocupadas (mediana)', 'Esperando cama (mediana)'];
        var xyAxes = ['xy', 'x2y2', 'x3y3'];
        var yAxes = ['y', 'y2', 'y3'];
        function filasVisibles() {
            var ejePorFila = {};
            var data = gd.data || [];
            for (var k = 0; k < data.length; k++) {
                var nm = data[k].name;
                if (nombres.indexOf(nm) !== -1 && ejePorFila[nm] === undefined) { ejePorFila[nm] = k; }
            }
            return ejePorFila;
        }
        gd.on('plotly_hover', function(ev) {
            if (gd._simintSyncing || !ev || !ev.points || !ev.points.length) { return; }
            var i = ev.points[0].pointNumber;
            if (i === undefined || i === null) { return; }
            var yaNativa = {};
            for (var j = 0; j < ev.points.length; j++) {
                var ya = ev.points[j].data && ev.points[j].data.yaxis;
                if (ya) { yaNativa[ya] = true; }
            }
            var ejePorFila = filasVisibles(), pts = [], axes = [];
            for (var m = 0; m < nombres.length; m++) {
                if (ejePorFila[nombres[m]] !== undefined && !yaNativa[yAxes[m]]) {
                    pts.push({curveNumber: ejePorFila[nombres[m]], pointNumber: i});
                    axes.push(xyAxes[m]);
                }
            }
            if (pts.length < 1) { return; }   // la fila bajo el mouse ya tiene su propia caja nativa
            gd._simintSyncing = true;
            try { Plotly.Fx.hover(gd, pts, axes); } catch (e) {}
            gd._simintSyncing = false;
        });
        gd.on('plotly_unhover', function() {
            if (gd._simintSyncing) { return; }
            var ejePorFila = filasVisibles();
            var axes = [];
            for (var m = 0; m < nombres.length; m++) {
                if (ejePorFila[nombres[m]] !== undefined) { axes.push(xyAxes[m]); }
            }
            if (axes.length < 2) { return; }
            gd._simintSyncing = true;
            try { Plotly.Fx.unhover(gd, axes); } catch (e) {}
            gd._simintSyncing = false;
        });
        return ns.no_update;
    }
    """,
    Output("simint-sync-hover", "data"),
    Input("simint-grafico", "figure"),
    prevent_initial_call=True,
)

