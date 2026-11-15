"""
dashboard/pages/prueba_flujo.py  -  «Prueba de flujo» (15-nov-2026)
Recorrido en cadena de lo que haria el sistema para un dia futuro, con los modelos del proyecto y sin el simulador integral (plan B):
  1. Demanda esperada      pronostico de demanda (src/modelo_pronostico.py): llegadas e ingresos a cama del dia, con su rango.
  2. Camas esperadas       simulacion Monte Carlo de camas (src/simulacion_camas_montecarlo.py) hasta ese dia, con el mismo ajuste de demanda.
  3. Cola y pacientes      modelo de flujo de la cola (docs/pronostico_espera_sistema.md 1a), con las llegadas ajustadas a la demanda esperada del
                           dia, y el estimador de espera por paciente (src/estimador_tiempo_restante.py) sobre pacientes de ejemplo sorteados.
  4. Alertas               dia congestionado (con el pronostico), ocupacion alta (con la simulacion), paciente 48 h sin cama y aviso temprano.
  5. Recomendaciones       la tabla de recomendaciones ligada a cada alerta (dashboard/catalogo.py).
Un solo control, el ajuste de demanda, mueve las etapas 1 a 3, asi que las etapas son coherentes entre si. Es una PRUEBA: pacientes de ejemplo,
no tiempo real. Es independiente del simulador integral (/simulador, rama de Anthony): cuando exista uno en main, su salida puede reemplazar 1 y 2.

DATOS  datos/tablas_dashboard/flujo_*.csv (src/exportar_datos_flujo_prueba.py), alertas_tabla.csv y recomendaciones_tabla.csv.
LIMITES  La alerta de ocupacion se probo con «mañana igual que hoy»; calcularla con la simulacion no se ha probado. Las llegadas de la cola se
         escalan con la demanda esperada del dia: el modelo probado usa el promedio de esa hora de la semana, sin escalar.
"""
import sys
from pathlib import Path

import dash
import numpy as np
import pandas as pd
from dash import Input, Output, State, callback, ctx, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
import catalogo as cat  # noqa: E402
from componentes import MESES, aviso_datos, bloque, cifra, coma, hecho, leer, mensaje, metodo, pagina, portada  # noqa: E402

dash.register_page(__name__, path="/prueba-flujo", name="Prueba de flujo", title="Prueba de flujo - HUN", order=40)

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
UMBRAL_CAMAS = 108          # mediana de camas ocupadas desde la que salta la alerta (percentil 80 del entrenamiento: 107 en validacion, 109 en prueba)
CAMAS_HUN = 106
HORAS_AVISO = 48            # A3: horas desde la llegada sin cama
PROB_AVISO = 0.40           # A4: probabilidad de seguir sin cama a las 48 h
EDADES = {"0-4": (0, 4), "5-14": (5, 14), "15-29": (15, 29), "30-44": (30, 44), "45-59": (45, 59), "60-74": (60, 74), "75+": (75, 92)}
PASOS = ["Demanda esperada", "Camas esperadas", "Cola y pacientes en espera", "Alertas", "Recomendaciones"]
_CACHE = {"bt": {}, "camas": {}}


def _hoy():
    return pd.Timestamp.today().normalize()


def _fecha_txt(f):
    return f"{DIAS[f.dayofweek].lower()} {f.day} de {MESES[f.month - 1].lower()} de {f.year}"


def _tablas():
    return leer("flujo_umbrales.csv"), leer("flujo_perfiles.csv"), leer("flujo_esperas.csv"), leer("flujo_cola_horaria.csv")


def layout():
    if any(t is None for t in _tablas()):
        return pagina(aviso_datos("Prueba de flujo", ["flujo_umbrales.csv", "flujo_perfiles.csv", "flujo_esperas.csv", "flujo_cola_horaria.csv"]))

    def control(etiqueta, *hijos, ancho="240px"):
        return html.Div(style={"minWidth": ancho, "flex": "1 1 " + ancho}, children=[html.Div(etiqueta, className="filtro__label"), *hijos])

    return pagina(
        portada("Predicción · Prueba de flujo", "Del pronóstico a la recomendación, en cadena",
                "Elige un día futuro y avanza paso a paso: el pronóstico de demanda da las llegadas, la simulación de camas la ocupación, el modelo de la cola "
                "proyecta quién espera y el estimador calcula a cada paciente. Con eso saltan las alertas y cada una muestra lo que se recomienda.",
                [cifra("5", "pasos, de la demanda a las recomendaciones"), cifra("4", "modelos del proyecto encadenados en cada recorrido"),
                 cifra("1", "ajuste de demanda que mueve todas las etapas")]),
        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "18px 28px", "alignItems": "flex-start", "margin": "10px 0 14px"}, children=[
            control("Días a partir de hoy", html.Div(id="fl-fecha", className="enlaces__vacio", style={"marginBottom": "6px"}),
                    dcc.Slider(id="fl-dias", min=1, max=30, step=1, value=1, marks={1: "1", 7: "7", 14: "14", 21: "21", 30: "30"},
                               tooltip={"placement": "bottom", "always_visible": True})),
            control("Hora del día", dcc.Slider(id="fl-hora", min=1, max=23, step=1, value=12, marks={1: "1 h", 6: "6 h", 12: "12 h", 18: "18 h", 23: "23 h"},
                                               tooltip={"placement": "bottom", "always_visible": True}), ancho="220px"),
            control("Ajuste de la demanda (%)", dcc.Slider(id="fl-demanda", min=-30, max=30, step=5, value=0, marks={-30: "−30", 0: "0", 30: "+30"},
                                                           tooltip={"placement": "bottom", "always_visible": True}), ancho="220px"),
            control("Pacientes esperando cama ahora", dcc.Slider(id="fl-n", min=3, max=40, step=1, value=26, marks={3: "3", 26: "26 (típico)", 40: "40"},
                                                                  tooltip={"placement": "bottom", "always_visible": True}), ancho="240px"),
        ]),
        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "10px", "margin": "0 0 18px"}, children=[
            html.Button("Siguiente paso", id="fl-sig", n_clicks=0, className="btn-primary"),
            html.Button("Reiniciar", id="fl-reiniciar", n_clicks=0, className="btn-secondary"),
            html.Button("Sortear otros pacientes", id="fl-sortear", n_clicks=0, className="btn-secondary")]),
        dcc.Store(id="fl-paso", data=0), dcc.Store(id="fl-datos"),
        html.Div(id="fl-salida"),
        metodo(
            "El día se pronostica con el modelo de demanda (calendario, festivos y nivel reciente) y la ocupación con la simulación de camas, que parte del último "
            "censo confiable y suma ingresos y estancias reales por perfil. La cola de pacientes sin cama se proyecta con el modelo de flujo: la cola de ahora más las "
            "llegadas que se hospitalizan menos las camas que suelen asignarse cada hora de esa semana, con las llegadas ajustadas a la demanda esperada del día. A cada "
            "paciente de ejemplo, sorteado con la mezcla real de 2025 como una foto del momento, el estimador le calcula cuánto le falta.",
            "No es tiempo real y los pacientes son de ejemplo. Un día antes, la alerta de día congestionado detecta pocos casos (la versión fuerte es la de mediodía, con lo que "
            "ya llegó). La alerta de ocupación se probó suponiendo que mañana será igual que hoy; calcularla con la simulación no se ha probado. Ajustar las llegadas de la cola "
            "con la demanda del día tampoco se ha probado. Las cifras de acierto son las de la prueba con días de 2026.",
            "Fuente: pronóstico de demanda, simulación de camas, cola proyectada y estimador de espera.", ruta="/prueba-flujo"))


@callback(Output("fl-fecha", "children"), Input("fl-dias", "value"))
def etiqueta_fecha(dias):
    return _fecha_txt(_hoy() + pd.Timedelta(days=int(dias or 1))).capitalize()


# ---------------------------------------------------------------- los modelos, uno por etapa
def demanda(fecha, ajuste):
    """Pronostico de llegadas e ingresos a cama del dia, con su rango del 80 %, ajustado por el escenario de demanda."""
    import modelo_pronostico as mp
    panel = mp.cargar_panel()
    k, salida = 1 + ajuste / 100, {}
    for obj in ("llegadas", "ingresos_a_cama"):
        if obj not in _CACHE["bt"]:
            _CACHE["bt"][obj] = mp.retroceso(panel[obj], paso=7, escenario="historico")
        f = mp.pronostico_con_banda(panel[obj], _CACHE["bt"][obj], 1, "historico", 0.0, True, False, fecha).iloc[0]
        salida[obj] = {"esperado": float(f.pronostico) * k, "bajo": float(f.banda_baja) * k, "alto": float(f.banda_alta) * k}
    return salida


def camas(fecha, ajuste):
    """Ocupacion del dia segun la simulacion Monte Carlo, que parte del ultimo censo confiable (9-abr-2026)."""
    import simulacion_camas_montecarlo as scm
    clave = (str(fecha.date()), ajuste)
    if clave not in _CACHE["camas"]:
        previos = max((fecha - pd.Timestamp(scm.ULTIMO_CONFIABLE)).days - 1, 0)
        _f, c = scm.simular(scm.serie_ingresos, scm.ULTIMO_CONFIABLE, previos + 1, ajuste_ingresos=1 + ajuste / 100, n_rep=300)
        x = c["total"][:, -1]
        _CACHE["camas"][clave] = {"p10": float(np.percentile(x, 10)), "p50": float(np.percentile(x, 50)), "p90": float(np.percentile(x, 90)),
                                  "prob_sobre": float((x > CAMAS_HUN).mean())}
    return _CACHE["camas"][clave]


def cola_proyectada(fecha, hora, n, ratio):
    """Modelo de flujo: cola de ahora + llegadas que se hospitalizan - camas asignadas, por hora de la semana (llegadas escaladas por `ratio`)."""
    t = leer("flujo_cola_horaria.csv")
    lam, mu = t.llegan_y_se_hospitalizan_por_hora.to_numpy(), t.camas_asignadas_por_hora.to_numpy()
    base = fecha.dayofweek * 24 + hora

    def a(h):
        return float(max(0.0, n + sum(lam[(base + k) % 168] * ratio - mu[(base + k) % 168] for k in range(1, h + 1))))
    return {"ahora": float(n), "h6": a(6), "h12": a(12)}


def sortear(n, semilla, fecha, hora):
    """n pacientes de ejemplo con la mezcla real de 2025 y su estimacion de espera; las horas se sortean como una foto del momento."""
    import estimador_tiempo_restante as etr
    _u, perf, esp, _c = _tablas()
    rng = np.random.default_rng(int(semilla))
    idx = rng.choice(len(perf), size=int(n), p=(perf.peso / perf.peso.sum()).to_numpy())
    espera = esp.espera_h.to_numpy()[:99]                                              # percentiles 1 a 99: el maximo (768 h) es un caso unico que distorsiona la foto
    peso = np.clip(espera, 0.5, None)                                                   # quien espera mas tiempo tiene mas chance de estar en la fila ahora
    total = rng.choice(espera, size=int(n), p=peso / peso.sum())
    horas = np.minimum(rng.uniform(0, total), 150.0)
    ahora = f"{fecha:%Y-%m-%d} {int(hora):02d}:00"
    filas = []
    for i, (k, h) in enumerate(zip(idx, horas), start=1):
        f = perf.iloc[k]
        a, b = EDADES[str(f.grupo_edad)]
        edad = int(rng.integers(a, b + 1))
        r = etr.estimar_tiempo_restante(float(edad), f.sexo, f.tipo_visita, float(h), ahora)
        p25, p50, p75, p90 = (r[f"faltan_p{q}_h"] for q in (25, 50, 75, 90))
        falta = HORAS_AVISO - h
        sin_cama_48 = 1.0 if falta <= 0 else float(1 - np.interp(falta, [0, p25, p50, p75, p90], [0, .25, .5, .75, .9]))
        filas.append({"n": i, "edad": edad, "sexo": f.sexo, "tipo": f.tipo_visita, "horas": round(float(h), 1), "mitad_h": p50,
                      "sin_cama_48": round(sin_cama_48, 3), "momento": r["ventana_mas_probable"]})
    return sorted(filas, key=lambda x: -x["horas"])


@callback(Output("fl-datos", "data"), Input("fl-sortear", "n_clicks"), Input("fl-n", "value"), Input("fl-dias", "value"), Input("fl-hora", "value"), Input("fl-demanda", "value"))
def generar(clics, n, dias, hora, ajuste):
    try:
        fecha, hora, ajuste, n = _hoy() + pd.Timedelta(days=int(dias or 1)), int(hora or 12), int(ajuste or 0), int(n or 26)
        u = _tablas()[0]
        fila = u[u.dia == fecha.dayofweek].iloc[0]
        d = demanda(fecha, ajuste)
        pac = sortear(n, clics or 0, fecha, hora)
        return {"fecha": str(fecha.date()), "hora": hora, "ajuste": ajuste, "demanda": d, "camas": camas(fecha, ajuste),
                "cola": cola_proyectada(fecha, hora, n, d["llegadas"]["esperado"] / float(fila.llegadas_tipicas)),
                "pacientes": pac, "umbral": float(fila.umbral_llegadas), "tipica": float(fila.llegadas_tipicas)}
    except Exception as err:                                                            # modelo o datos no disponibles: mostrar el motivo en vez de romper la pagina
        return {"error": str(err)}


@callback(Output("fl-paso", "data"), Input("fl-sig", "n_clicks"), Input("fl-reiniciar", "n_clicks"), State("fl-paso", "data"), prevent_initial_call=True)
def avanzar(_sig, _rei, actual):
    return 0 if ctx.triggered_id == "fl-reiniciar" else min((actual or 0) + 1, len(PASOS))


# ---------------------------------------------------------------- alertas
def evaluar(d):
    """{id de alerta: dict(salta, detalle)}; los ids son los de src/exportar_tabla_alertas.py."""
    fecha, pac, dem, cam = pd.Timestamp(d["fecha"]), d["pacientes"], d["demanda"]["llegadas"], d["camas"]
    lista3 = [p for p in pac if p["horas"] >= HORAS_AVISO]
    lista4 = [p for p in pac if 12 <= p["horas"] < HORAS_AVISO and p["sin_cama_48"] >= PROB_AVISO]
    return {
        "A1": dict(salta=dem["esperado"] > d["umbral"],
                   detalle=f"Se esperan {coma(dem['esperado'], 0)} llegadas (rango probable de {coma(dem['bajo'], 0)} a {coma(dem['alto'], 0)}). Un {DIAS[fecha.dayofweek].lower()} "
                           f"típico trae {coma(d['tipica'], 0)} y el límite de un día congestionado es {coma(d['umbral'], 0)}."),
        "A2": dict(salta=cam["p50"] >= UMBRAL_CAMAS,
                   detalle=f"La simulación espera una mediana de {coma(cam['p50'], 0)} camas ocupadas (rango de {coma(cam['p10'], 0)} a {coma(cam['p90'], 0)}) y una probabilidad de "
                           f"{coma(100 * cam['prob_sobre'], 0)} % de superar las {CAMAS_HUN} camas. La alerta salta desde {UMBRAL_CAMAS}."),
        "A3": dict(salta=bool(lista3), detalle=(f"{len(lista3)} paciente(s) llevan 48 horas o más sin cama: " + ", ".join(f"n.º {p['n']} ({coma(p['horas'], 0)} h)" for p in lista3))
                   if lista3 else "Nadie lleva 48 horas sin cama."),
        "A4": dict(salta=bool(lista4), detalle=(f"{len(lista4)} paciente(s) con entre 12 y 48 horas de espera tienen 40 % o más de probabilidad de seguir sin cama a las 48 h: "
                                                + ", ".join(f"n.º {p['n']} ({coma(100 * p['sin_cama_48'], 0)} %)" for p in lista4)) if lista4
                   else "Nadie con entre 12 y 48 horas de espera llega al 40 % de probabilidad de seguir sin cama a las 48 h."),
    }


def _prueba(alerta_id):
    """Como acerto la alerta al reproducir dias de 2026 (alertas_tabla.csv), en palabras para el hospital."""
    t = cat.alertas()
    if t is None:
        return ""
    f = t[t.alerta_id == alerta_id]
    f = f[f.orden == 1] if alerta_id == "A1" else f[f.recomendada == 1]
    if f.empty:
        return ""
    f = f.iloc[0]
    det, prec = f.deteccion_pct, f.precision_pct
    if alerta_id == "A1":
        return f"Avisar con un día de margen es la versión más débil: en la prueba con días de 2026 detectó el {coma(det, 0)} % de los días congestionados y acertó el {coma(prec, 0)} % de sus avisos."
    if alerta_id == "A2":
        return f"Se probó suponiendo que mañana será igual que hoy (detectó el {coma(det, 0)} % y acertó el {coma(prec, 0)} %). Calcularla con la simulación no se ha probado."
    if alerta_id == "A3":
        return f"En la prueba con días de 2026, el {coma(prec, 0)} % de los avisos terminó esperando más de 72 horas."
    return f"En la prueba con días de 2026: detectó el {coma(det, 0)} % de los casos y acertó el {coma(prec, 0)} % de sus avisos."


@callback(Output("fl-salida", "children"), Input("fl-paso", "data"), Input("fl-datos", "data"))
def mostrar(paso, d):
    paso = paso or 0
    progreso = html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "8px", "margin": "0 0 16px"}, children=[
        html.Span(f"{i}. {t}", className="flujo-paso" + (" flujo-paso--hecho" if paso > i else " flujo-paso--actual" if paso == i else "")) for i, t in enumerate(PASOS, start=1)])
    if paso == 0:
        return [progreso, mensaje("Pulsa **Siguiente paso** para empezar. Puedes cambiar el día, la hora, el ajuste de demanda o la cola en cualquier momento.", titulo="Cómo se usa")]
    if not d or "error" in d:
        return [progreso, mensaje(f"No se pudo completar el recorrido. {d.get('error', '') if d else ''}", titulo="Modelo no disponible")]
    fecha = pd.Timestamp(d["fecha"])
    dem, ing, cam, col = d["demanda"]["llegadas"], d["demanda"]["ingresos_a_cama"], d["camas"], d["cola"]
    salida = [progreso, bloque("1. Demanda esperada", f"Pronóstico para el {_fecha_txt(fecha)}" + (f", con la demanda ajustada {d['ajuste']:+d} %" if d["ajuste"] else "")),
              html.Div(className="hechos", children=[
                  hecho(coma(dem["esperado"], 0), "Llegadas esperadas", f"Rango probable de {coma(dem['bajo'], 0)} a {coma(dem['alto'], 0)}; un {DIAS[fecha.dayofweek].lower()} típico trae {coma(d['tipica'], 0)}."),
                  hecho(coma(ing["esperado"], 0), "Ingresos a cama esperados", f"Rango probable de {coma(ing['bajo'], 0)} a {coma(ing['alto'], 0)}.")])]
    if paso >= 2:
        salida += [bloque("2. Camas esperadas", "Simulación de camas con esa demanda, desde el último censo confiable"),
                   html.Div(className="hechos", children=[
                       hecho(coma(cam["p50"], 0), "Camas ocupadas esperadas", f"Rango de {coma(cam['p10'], 0)} a {coma(cam['p90'], 0)}; el hospital informó {CAMAS_HUN}."),
                       hecho(f"{coma(100 * cam['prob_sobre'], 0)} %", "Probabilidad de superar las camas", f"Que ese día haya más de {CAMAS_HUN} pacientes en cama.")])]
    if paso >= 3:
        pac = d["pacientes"]
        cab = html.Thead(html.Tr([html.Th(c) for c in ["Paciente", "Edad", "Sexo", "Tipo de visita", "Lleva esperando", "Cama para la mitad en", "Sin cama a las 48 h", "Momento más probable"]]))
        filas = [html.Tr([html.Td(f"n.º {p['n']}"), html.Td(f"{p['edad']} años"), html.Td(p["sexo"]), html.Td(p["tipo"]), html.Td(f"{coma(p['horas'], 0)} h"),
                          html.Td(f"{coma(p['mitad_h'], 0)} h"), html.Td(f"{coma(100 * p['sin_cama_48'], 0)} %"), html.Td(p["momento"])]) for p in pac]
        salida += [bloque("3. Cola y pacientes en espera", f"A las {d['hora']} h; la cola se proyecta con las llegadas de ese día, y a cada paciente de ejemplo el estimador le calcula cuánto le falta"),
                   html.Div(className="hechos", children=[
                       hecho(coma(col["ahora"], 0), "Pacientes sin cama ahora", "Los de la lista de abajo."),
                       hecho(coma(col["h6"], 0), "Cola en 6 horas", "Cuando se probó el modelo se equivocó en promedio 2,6 pacientes."),
                       hecho(coma(col["h12"], 0), "Cola en 12 horas", "Cuando se probó, se equivocó en promedio 3,5 pacientes.")]),
                   html.Div(className="tech-table-wrap", children=[html.Table(className="tech-table", children=[cab, html.Tbody(filas)])]),
                   html.P("«Cama para la mitad en»: horas que faltan para que la mitad de los pacientes parecidos ya tenga cama. «Sin cama a las 48 h»: probabilidad de seguir sin cama cuando se cumplan 48 horas desde la llegada.",
                          style={"fontSize": "12px", "opacity": .75, "marginTop": "6px"})]
    if paso >= 4:
        res = evaluar(d)
        tarjetas = [html.Div(className="card", style={"padding": "12px 16px"}, children=[
            html.Div(html.B(("Salta: " if r["salta"] else "No salta: ") + cat.NOMBRES_ALERTA[a])), html.P(r["detalle"], style={"margin": "4px 0", "fontSize": "13.5px"}),
            html.P(_prueba(a), style={"margin": 0, "fontSize": "12px", "opacity": .75})]) for a, r in res.items()]
        salida += [bloque("4. Alertas", f"{sum(r['salta'] for r in res.values())} de {len(res)} alertas saltan con este escenario"), html.Div(style={"display": "grid", "gap": "10px"}, children=tarjetas)]
        if paso >= 5:
            por_reco = {}
            for a, r in res.items():
                if r["salta"]:
                    for prio, texto in cat.recomendaciones_de(a):
                        por_reco.setdefault((prio, texto), []).append(cat.NOMBRES_ALERTA[a])
            if por_reco:
                items = [html.Div(className="ale-reco", children=[html.Div(texto, className="ale-reco__titulo"), html.Div("Porque saltó: " + ", ".join(dict.fromkeys(cuales)), className="enlaces__vacio")])
                         for (_prio, texto), cuales in sorted(por_reco.items())]
                salida += [bloque("5. Recomendaciones", "Lo que se recomienda según las alertas que saltaron"), html.Div(style={"display": "grid", "gap": "10px"}, children=items),
                           dcc.Link("Ver todas las recomendaciones", href="/recomendaciones", className="enlace-chip")]
            else:
                salida += [bloque("5. Recomendaciones", ""), mensaje("Ninguna alerta saltó con este escenario, así que no hay recomendaciones nuevas. Prueba con otro día o sube el ajuste de demanda.", titulo="Sin recomendaciones")]
    return salida
