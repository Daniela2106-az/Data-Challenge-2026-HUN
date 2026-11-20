"""
dashboard/pacientes_alerta.py  -  tablas de pacientes simulados para la confirmacion verde de una alerta (19-nov-2026)

Al aplicar la mejora de una alerta, antes de reanudar la simulacion, el hospital ve A QUIEN afecta la mejora:
  - Faltaran camas: las altas de la tarde que pasarian a la manana (30 %) y los pacientes de 14 dias o mas (los que ya llevan 14 dias en cama y los estimados).
  - Cola de espera: los pacientes que esperan 48 h o mas (ahora mismo y estimados) y lo mismo para 72 h.

Los pacientes salen de UNA repeticion de la simulacion (`info["pacientes"]` de src/simulador_integral.py, parametro `registrar_rep`), no del promedio de las
repeticiones: son un ejemplo, y el numero exacto cambia de una corrida a otra. Las funciones de calculo son puras (reciben el dict y el dia); `panel_confirmacion`
arma el panel con html de Dash.

Convenciones del dict `pac`:
  perfiles          lista [grupo_edad, ruta] (indice = perfil)
  nuevos            hospitalizados simulados: perf, sexo (0 mujer, 1 hombre), t_lleg_h (horas desde el dia 0), espera_h, estancia_h, dia_cama, dia_alta, cola_sembrada
  sembrados         los que ya estaban en cama el dia 0: perf, sexo, dur_dias (dia en que salen de alta)
"""
import numpy as np
from dash import html

SEMILLA = 20261119                      # el 30 % de altas adelantadas sale al azar, pero siempre igual para el mismo dia
SEXO = {0: "Mujer", 1: "Hombre"}
RUTA = {"Urgencias": "Urgencias", "Treatment urgency": "Treatment urgency", "Ambulatorio": "Ambulatorio"}
EDAD_COLORES = {"0-4": "#6ec6b2", "5-14": "#2e9b82", "15-29": "#7fb3e0", "30-44": "#4a8fd0",      # los mismos del pictograma del simulador
                "45-59": "#2a6fb0", "60-74": "#e0862a", "75+": "#c0392b"}
PIE = ("Ejemplo de una corrida simulada: el número exacto cambia de una corrida a otra. Las estancias y esperas «estimadas» son estimaciones "
       "del simulador según el perfil del paciente.")


def _a(pac, clave):
    return {k: np.asarray(v) for k, v in pac[clave].items()}


def _fila(pac, perf, sexo, valor):
    g, r = pac["perfiles"][int(perf)]
    return {"edad": f"{g} años", "sexo": SEXO.get(int(sexo), "—"), "visita": RUTA.get(r, r), "valor": float(valor)}


# ---------------------------------------------------------------- calculo
def altas_del_dia(pac, dia):
    """Pacientes cuya alta calculada (llegada + espera + estancia) cae en `dia`. Valor = estancia en cama, en dias."""
    n, s = _a(pac, "nuevos"), _a(pac, "sembrados")
    filas = []
    for i in np.nonzero(n["dia_alta"] == dia)[0]:
        filas.append(_fila(pac, n["perf"][i], n["sexo"][i], (n["dia_alta"][i] - n["dia_cama"][i])))
    for i in np.nonzero(s["dur_dias"] == dia)[0]:
        filas.append(_fila(pac, s["perf"][i], s["sexo"][i], s["dur_dias"][i]))
    return filas


def adelanto_altas(pac, dia, pct=30):
    """(todas las altas del dia, las que pasan a la manana). Se sortea el `pct` % con una semilla fija: mismo dia, mismo resultado."""
    todas = altas_del_dia(pac, dia)
    k = int(round(len(todas) * pct / 100.0)) if todas else 0
    k = max(1, k) if todas else 0
    idx = np.random.default_rng(SEMILLA + int(dia)).choice(len(todas), size=k, replace=False) if k else []
    return todas, [todas[int(i)] for i in sorted(idx)]


def estancias_14(pac, dia):
    """(ya llevan 14+ dias en cama, estimados de 14+ dias). Solo pacientes que siguen en cama en `dia`.
    Valor de «ya llevan» = dias en cama; de «estimados» = estancia estimada total, en dias."""
    n, s = _a(pac, "nuevos"), _a(pac, "sembrados")
    ya, est = [], []
    en_cama = (n["dia_cama"] <= dia) & (n["dia_alta"] > dia)
    for i in np.nonzero(en_cama)[0]:
        llevan = dia - n["dia_cama"][i]
        if llevan >= 14:
            ya.append(_fila(pac, n["perf"][i], n["sexo"][i], llevan))
        elif n["estancia_h"][i] / 24.0 >= 14:
            est.append(_fila(pac, n["perf"][i], n["sexo"][i], n["estancia_h"][i] / 24.0))
    for i in np.nonzero((s["dur_dias"] > dia) & (s["dur_dias"] >= 14))[0]:
        est.append(_fila(pac, s["perf"][i], s["sexo"][i], s["dur_dias"][i]))      # ya estaban en cama el dia 0: se quedan al menos hasta su alta
    return ya, est


def colas(pac, dia, umbral_h):
    """(esperando `umbral_h` o mas ahora, estimados de `umbral_h` o mas). «Ahora» = cierre del dia. Valor = espera actual / espera estimada, en horas."""
    n = _a(pac, "nuevos")
    ahora_h = (dia + 1) * 24.0
    t_cama = n["t_lleg_h"] + n["espera_h"]
    espera_ahora = (n["t_lleg_h"] <= ahora_h) & (t_cama > ahora_h)
    transcurrida = ahora_h - n["t_lleg_h"]
    ya, est = [], []
    for i in np.nonzero(espera_ahora)[0]:
        if transcurrida[i] >= umbral_h:
            ya.append(_fila(pac, n["perf"][i], n["sexo"][i], transcurrida[i]))
        elif n["espera_h"][i] >= umbral_h:
            est.append(_fila(pac, n["perf"][i], n["sexo"][i], n["espera_h"][i]))
    return ya, est


RIESGO_LARGA = lambda g, r: g in ("60-74", "75+") or r == "Treatment urgency"      # 2 a 3 veces mas riesgo de pasar de 14 dias (pagina Estancias largas)


def _ref(pac):
    return np.asarray(pac.get("ref_p90") or [14.0] * len(pac["perfiles"]), dtype=float)


def series_alertas(pac, n_dias, umbral_espera_h=72):
    """Conteos diarios de las alertas por paciente (20-nov-2026), sobre los pacientes de la repeticion registrada:
    sobre_perfil (en cama con mas dias que el p90 de su perfil), sobre_corto (de ellos, con menos de 14 dias), mas30 (en cama con 30 dias o mas),
    espera_ext (esperando `umbral_espera_h` o mas ahora), espera_prox (esperando desde hace 12 h o mas que llegaran a ese umbral), may_urg y manana
    (de los de espera extrema: mayores de 60 por urgencias / llegados entre las 6 y las 12 h), pct_riesgo y n_riesgo (ingresos de los ultimos 7 dias de perfil de riesgo)
    y riesgo_14 (de ellos, con estancia estimada de 14 dias o mas)."""
    n = _a(pac, "nuevos")
    ref = _ref(pac)
    perf = n["perf"].astype(int)
    p90 = ref[perf]
    riesgo = np.array([RIESGO_LARGA(g, r) for g, r in pac["perfiles"]])[perf]
    may_urg = np.array([g in ("60-74", "75+") and r == "Urgencias" for g, r in pac["perfiles"]])[perf]
    manana = (np.mod(n["t_lleg_h"], 24) >= 6) & (np.mod(n["t_lleg_h"], 24) < 12)
    t_cama = n["t_lleg_h"] + n["espera_h"]
    out = {k: [] for k in ("sobre_perfil", "sobre_corto", "mas30", "espera_ext", "espera_prox", "may_urg", "manana", "pct_riesgo", "n_riesgo", "riesgo_14")}
    for d in range(n_dias):
        en = (n["dia_cama"] <= d) & (n["dia_alta"] > d)
        llev = d - n["dia_cama"]
        sob = en & (llev > p90)
        out["sobre_perfil"].append(int(sob.sum()))
        out["sobre_corto"].append(int((sob & (llev < 14)).sum()))
        out["mas30"].append(int((en & (llev >= 30)).sum()))
        ahora = (d + 1) * 24.0
        esp = (n["t_lleg_h"] <= ahora) & (t_cama > ahora)
        tr = ahora - n["t_lleg_h"]
        ext = esp & (tr >= umbral_espera_h)
        out["espera_ext"].append(int(ext.sum()))
        out["espera_prox"].append(int((esp & (tr >= 12) & (tr < umbral_espera_h) & (n["espera_h"] >= umbral_espera_h)).sum()))
        out["may_urg"].append(int((ext & may_urg).sum()))
        out["manana"].append(int((ext & manana).sum()))
        ing = (n["dia_cama"] > d - 7) & (n["dia_cama"] <= d)
        k = int(ing.sum())
        out["n_riesgo"].append(int((ing & riesgo).sum()))
        out["pct_riesgo"].append(round(100.0 * (ing & riesgo).sum() / k, 1) if k else 0.0)
        out["riesgo_14"].append(int((ing & riesgo & (n["estancia_h"] >= 14 * 24)).sum()))
    return out


def estancias_sobre_perfil(pac, dia):
    """(14 dias o mas, menos de 14 dias): pacientes en cama que ya superan el p90 de estancia de su perfil. Valor = dias que llevan en cama."""
    n = _a(pac, "nuevos")
    ref = _ref(pac)
    largos, cortos = [], []
    en = (n["dia_cama"] <= dia) & (n["dia_alta"] > dia)
    for i in np.nonzero(en)[0]:
        llevan = dia - n["dia_cama"][i]
        if llevan > ref[int(n["perf"][i])]:
            (largos if llevan >= 14 else cortos).append(_fila(pac, n["perf"][i], n["sexo"][i], llevan))
    return largos, cortos


def ingresos_riesgo(pac, dia):
    """(ingresos de los ultimos 7 dias de perfil de riesgo, de ellos con estancia estimada de 14 dias o mas). Valor = dias en cama / estancia estimada."""
    n = _a(pac, "nuevos")
    todos, largos = [], []
    for i in np.nonzero((n["dia_cama"] > dia - 7) & (n["dia_cama"] <= dia))[0]:
        g, r = pac["perfiles"][int(n["perf"][i])]
        if RIESGO_LARGA(g, r):
            todos.append(_fila(pac, n["perf"][i], n["sexo"][i], dia - n["dia_cama"][i]))
            if n["estancia_h"][i] >= 14 * 24:
                largos.append(_fila(pac, n["perf"][i], n["sexo"][i], n["estancia_h"][i] / 24.0))
    return todos, largos


def agrupar(filas):
    """Perfiles distintos con su cantidad y el valor medio, del mas frecuente al menos."""
    g = {}
    for f in filas:
        g.setdefault((f["edad"], f["sexo"], f["visita"]), []).append(f["valor"])
    return sorted(([*k, len(v), float(np.mean(v))] for k, v in g.items()), key=lambda r: (-r[3], r[0], r[1]))


# ---------------------------------------------------------------- panel
def _icono(edad, visita, sexo):
    """El mismo pacientito del pictograma: color por grupo de edad; borde si es Treatment urgency, tenue si es ambulatorio."""
    g = edad.replace(" años", "")
    clase = "simint-picto__p" + (" simint-picto__p--tu" if visita == "Treatment urgency" else "") + (" simint-picto__p--amb" if visita == "Ambulatorio" else "")
    return html.Span(className=clase, style={"background": EDAD_COLORES.get(g, "#888")}, title=f"{edad} · {sexo} · {visita}")


def _tabla(titulo, filas, rotulo_valor, unidad, nota=None):
    grupos = agrupar(filas)
    cuerpo = [html.Tr([html.Td(_icono(e, v, sx), className="ico"), html.Td(e), html.Td(sx), html.Td(v), html.Td(str(c), className="num"), html.Td(f"{m:.1f}".replace(".", ",") + f" {unidad}", className="num")])
              for e, sx, v, c, m in grupos]
    if not cuerpo:
        cuerpo = [html.Tr(html.Td("Ninguno en este momento de la simulación", colSpan=6, className="vacio"))]
    return html.Div(className="simint-conf__tabla", children=[
        html.Div([html.Span(titulo), html.B(f"{len(filas)}", className="simint-conf__total")], className="simint-conf__tabla-titulo"),
        html.Div(nota, className="simint-conf__nota") if nota else None,
        html.Div(className="simint-conf__scroll", children=html.Table(children=[
            html.Thead(html.Tr([html.Th(""), html.Th("Edad"), html.Th("Sexo"), html.Th("Visita"), html.Th("Pacientes", className="num"), html.Th(rotulo_valor, className="num")])),
            html.Tbody(cuerpo)]))])


def _seccion(titulo, bajada, *tablas):
    return html.Div(className="simint-conf__seccion", children=[
        html.Div(titulo, className="simint-conf__seccion-titulo"), html.P(bajada, className="simint-conf__bajada") if bajada else None,
        html.Div(list(tablas), className="simint-conf__tablas")])


def panel_confirmacion(tipo, titulo, fecha, pac, dia, pct_altas=30):
    """Contenido del panel verde (sin el boton Continuar, que vive fijo en el layout). `pac` = info["pacientes"]; None si la vista no lo trae."""
    cab = html.Div(className="simint-conf__cab", children=[
        html.Span("Mejora aplicada", className="rec-chip simint-conf__chip"), html.Span(titulo or "", className="simint-alerta__titulo"),
        html.Span(f"Día {fecha}" if fecha else "", className="simint-alerta__fecha")])
    if not pac or dia is None:
        return [cab, html.P("En esta vista no hay pacientes de ejemplo. Los controles ya se movieron; pulsa «Continuar con la mejora» para seguir.", className="simint-conf__bajada")]
    secciones = []
    if tipo == "saturacion":
        todas, mover = adelanto_altas(pac, dia, pct_altas)
        secciones.append(_seccion(
            f"Adelanto de altas ({pct_altas} %)",
            f"De los {len(todas)} pacientes que se darían de alta hoy en la tarde, {len(mover)} pasarían a la mañana (selección al azar, para el ejemplo).",
            _tabla("Pasan al alta de la mañana", mover, "Estancia (media)", "días")))
        ya, est = estancias_14(pac, dia)
        secciones.append(_seccion(
            f"Estancias de 14 días o más ({len(ya) + len(est)} pacientes)", "Son a quienes se les coordina el plan de salida.",
            _tabla("Ya llevan 14 días o más en cama", ya, "Días en cama (media)", "días"),
            _tabla("Estimador: 14 días o más", est, "Estancia estimada (media)", "días")))
    elif tipo == "estancia_perfil":
        largos, cortos = estancias_sobre_perfil(pac, dia)
        secciones.append(_seccion(
            f"Estancias más largas de lo normal para su perfil ({len(largos) + len(cortos)} pacientes)",
            "Ya llevan más días en cama que 9 de cada 10 pacientes de su misma edad y tipo de visita.",
            _tabla("Aún no cumplen 14 días (la revisión de estancias largas no los ve)", cortos, "Días en cama (media)", "días"),
            _tabla("Con 14 días o más", largos, "Días en cama (media)", "días")))
    elif tipo == "ingresos_riesgo":
        todos, largos = ingresos_riesgo(pac, dia)
        secciones.append(_seccion(
            f"Ingresos de la última semana con riesgo de estancia larga ({len(todos)} pacientes)",
            "Mayores de 60 o visitas «treatment urgency»: a quienes conviene fijarles el plan de alta desde el ingreso.",
            _tabla("Ingresaron en los últimos 7 días", todos, "Días en cama (media)", "días"),
            _tabla("Estimador: 14 días o más", largos, "Estancia estimada (media)", "días")))
    elif tipo == "espera_extrema":
        ya, est = colas(pac, dia, 72)
        secciones.append(_seccion(
            f"Esperas de 72 horas o más ({len(ya) + len(est)} pacientes)", "Los peores casos de espera: revisar uno por uno qué bloquea la cama.",
            _tabla("Esperando 72 h o más ahora mismo", ya, "Espera actual (media)", "h"),
            _tabla("Estimador: 72 h o más", est, "Espera estimada (media)", "h")))
    else:
        for h in (48, 72):
            ya, est = colas(pac, dia, h)
            secciones.append(_seccion(
                f"Esperas de {h} horas o más ({len(ya) + len(est)} pacientes)", None,
                _tabla(f"Esperando {h} h o más ahora mismo", ya, "Espera actual (media)", "h"),
                _tabla(f"Estimador: {h} h o más", est, "Espera estimada (media)", "h")))
    return [cab, *secciones]
