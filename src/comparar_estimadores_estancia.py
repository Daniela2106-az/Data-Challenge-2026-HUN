"""
comparar_estimadores_estancia.py  -  version 1 (19-nov-2026)
Tarea A6b: estimador de la ESTANCIA restante (tiempo hasta el alta) de un paciente YA hospitalizado,
con la misma arquitectura de supervivencia por "landmarks" que ya funciona para la espera de cama
(comparar_estimadores.py, M1: ~8-10 % de mejora frente al rango general). Los dos intentos anteriores
de predecir la estancia entrenaban UN SOLO modelo al momento del INGRESO para la estancia TOTAL:
  - prueba rapida del 21-oct (sin script en src/, solo en docs): R2 = 0,00-0,02, igual que adivinar
    la mediana (47 h).
  - src/factores_estancia.py (3-nov), con mas variables (incl. diagnostico): R2 = 7,9 % (modelo A) /
    10,8 % (modelo B) -- declarado alli mismo como "EXPLICATIVO, no predictivo".
Esto es distinto: un modelo por cada hora YA PASADA en cama ("landmark"), reestimando el riesgo de
alta con lo que se sabe en ESE momento (no solo al ingresar) -- nunca se probo asi para la estancia.

QUE USA (todo se conoce en el momento de la consulta)
  - El paciente: edad, sexo, tipo de visita y cuantas horas lleva en cama.
  - El hospital: hora del reloj, dia de la semana y ocupacion de su zona en ese momento.
  - Su historial (opcional): de su ultima hospitalizacion, cuanto espero, cuanto duro, hace cuantos
    dias y cuantas hospitalizaciones previas tiene; el grupo del ultimo diagnostico de una visita
    ANTERIOR. NUNCA el diagnostico de la estancia ACTUAL: comparar_estimadores.py::historial() ya
    documento que el 88 % de los diagnosticos se registra tarde (por eso el diagnostico previo se
    fecha al FIN del episodio anterior, no a su inicio); para la estancia en curso no existe una
    marca de tiempo confiable de cuando se "sabe" el diagnostico antes del propio final de la
    estancia, asi que usarlo aqui seria fuga.
  - Sus laboratorios de las primeras 6 h de la visita (opcional, mismas banderas de
    estimador_tiempo_restante.py / src/severidad_labs.py). FASE 1 (esta version): estaticos, tal
    como ya estan al llegar a la cama (la espera mediana de 18,6 h ya es mayor a la ventana de 6 h,
    asi que siempre se conocen de ante mano; no hace falta la ventana por horas que si usa el modelo
    de espera). FASE 2 (pendiente, fuera de esta version): laboratorios que varian hora por hora
    DURANTE la estancia (measurement_datetime es valido en el proyecto, a diferencia de
    procedure_occurrence que no tiene fecha en ningun lado) -- requiere una extraccion SQL nueva que
    todavia no existe.
  NO usa el recorrido en urgencias (etapas/admisiones): eso es el trayecto hacia la cama, no la
  estancia en ella.

CENSURA (mejora metodologica frente a los dos intentos anteriores y frente a que_esperar.py)
  que_esperar.py y factores_estancia.py DESCARTAN las estancias sin alta resuelta antes del corte
  (sesgo: las estancias largas son justo las que mas probablemente siguen abiertas cerca del corte).
  Aqui esas filas SIGUEN APORTANDO al entrenamiento como censuradas: una estancia que a las X horas
  aun no tenia alta resuelta (por seguir hospitalizada en la fecha de corte, o por terminar despues
  del periodo confiable, FIN_FIABLE) cuenta como "en riesgo" en cada landmark <= X, con evento = 0
  siempre (nunca se marca un alta que no se sabe si ocurrio). Solo las estancias CON alta resuelta
  pueden marcar evento = 1, en su hora exacta.

LANDMARKS
  [0, 6, 12, 24, 48] horas desde la asignacion de cama (ini_hosp_est); modelo agrupado (dinamico,
  igual que entrenar_m1 del modelo de espera) desde las 72 h. Espaciado MAS ESPARCIDO que el modelo
  de espera (0-11 h, cada hora): la estancia mediana es ~70 h (vs ~18,6 h de espera) y el alta opera
  a escala de dias (rondas medicas, resultados de laboratorio), no de horas.
  EL CORTE EN 72 H (no en 240 h, probado y descartado el 19-nov) SE ELIGIO MIDIENDO, no a priori: un
  modelo landmark propio en 72/120/168 h mejora solo 0,5/-1,4/-1,7 % frente al rango por perfil (la
  muestra de prueba ya es chica alli: 1.954/1.219/814 casos), mientras que el MISMO modelo agrupado
  dinamico que se usa desde los 72 h, evaluado en esas mismas horas, da 0,6/-0,7/-0,4 % -- mejor en
  los tres puntos. El modelo agrupado generaliza mejor donde hay menos estancias largas para entrenar
  un landmark propio. Horizonte MAX_H_ESTANCIA = 720 h (30 dias); mas alla se censura como "sigue mas
  de 30 dias" (solo el 1,2 % de las estancias llega tan lejos).

VALIDACION
  Entrenamiento con ingresos a cama (ini_hosp_est) de feb-2023 a jun-2025 (CORTE); prueba con jul-2025
  a HASTA_ESTANCIA_PRUEBA (9-ene-2026, colchon de 90 dias antes del fin del periodo confiable para que
  las estancias largas alcancen a resolverse, igual criterio que estimador_tiempos.py). La prueba solo
  puede usar estancias CON alta resuelta (no se puede medir perdida de cuantiles contra un desenlace
  que no se conoce); el entrenamiento si usa las censuradas.
  Metrica: perdida de cuantiles contra el baseline YA EN PRODUCCION (que_esperar.py, percentil por
  perfil edad x sexo x tipo de visita, documentado en 2,3-4,1 % de mejora para estancia) -- no R2 (R2
  solo se cita para los intentos anteriores, ya descartados). IC 95 % por bootstrap de semanas.

ENTRADA  tabla_episodios.parquet en HUN_PROCESADOS; CSV de laboratorio (sevp_*/sev_*) en HUN_CRUDOS
SALIDAS  HUN_TABLAS: comparacion_estimadores_estancia.csv, comparacion_estimadores_estancia_ic.csv
COMO CORRERLO  HUN_PROCESADOS=... HUN_CRUDOS=... HUN_TABLAS=... python3 src/comparar_estimadores_estancia.py
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

RAIZ = Path(__file__).resolve().parent.parent
GRAF = RAIZ / "resultados" / "graficos"
sys.path.insert(0, str(RAIZ / "src"))
import comparar_estimadores as ce  # noqa: E402
import estimador_tiempos as et  # noqa: E402
import que_esperar as qe  # noqa: E402

PROC = ce.PROC
TABLAS = ce.TABLAS
CRUDOS = ce.CRUDOS
DESDE, HASTA, CORTE = et.DESDE, et.HASTA, et.CORTE
HASTA_ESTANCIA_PRUEBA = et.HASTA_ESTANCIA_PRUEBA       # 2026-01-10, colchon de 90 dias
FIN_FIABLE = pd.Timestamp("2026-04-09")                # periodo confiable general (docs/CONTEXTO_TECNICO.md 4.9)
Q = ce.Q
H1 = ce.H1
SEMILLA = ce.SEMILLA
N_BOOT = ce.N_BOOT

LANDMARKS_ESTANCIA = [0, 6, 12, 24, 48]
UMBRAL_POOLED = 72                                     # >= 72 h: modelo agrupado dinamico (mejor medido que landmarks propios alli, ver cabecera)
MAX_H_ESTANCIA = 720                                   # 30 dias; mas alla se censura ("sigue mas de 30 dias")
CONTROLES_ESTANCIA = [6, 12, 24, 48, 72, 120, 168]

COLS_BASE_ESTANCIA = ["transcurrido", "hora_reloj", "dia_semana", "ocup", "edad_cod", "tipo_cod", "sexo_cod", "zona_cod"]
CATEGORICAS_ESTANCIA = ["hora_reloj", "dia_semana", "tipo_cod", "dx_previo_cod"]
DINAMICAS_ESTANCIA = ["transcurrido", "hora_reloj", "dia_semana", "ocup"]


# ----------------------------------------------------------------------
# 1) Datos: estancias, ocupacion, historial, censura
# ----------------------------------------------------------------------
def preparar():
    t = pd.read_parquet(PROC / "tabla_episodios.parquet")
    h = t[t.hospitalizado & t.estancia_unica & t.edad.notna() & t.ini_hosp_est.notna()].copy()
    h["zona"] = np.where(h.edad < 15, "ninos", "adultos")
    rejilla = pd.date_range(h.ini_hosp_est.min().floor("h"), h.fin_hosp_est.max().ceil("h"), freq="h").to_numpy()
    estado = ce.contar_estado(h, rejilla)                       # solo se usa "ocup" (la "cola" es del tramo urgencias->cama, no aplica aqui)
    d = h[(h.ini_hosp_est >= DESDE) & (h.ini_hosp_est < HASTA) & h.sexo.isin(["Mujer", "Hombre"]) & h.tipo_visita.isin(et.TIPOS)].copy()
    d["grupo_edad"] = d.grupo_edad.astype(str)
    d["edad_cod"] = d.grupo_edad.map({e: i for i, e in enumerate(et.EDADES)})
    d["tipo_cod"] = d.tipo_visita.map({v: i for i, v in enumerate(et.TIPOS)})
    d["sexo_cod"] = (d.sexo == "Mujer").astype(int)
    d["zona_cod"] = (d.zona == "ninos").astype(int)
    d = d.reset_index(drop=True)
    d["clave"] = np.arange(len(d))
    d = ce.laboratorios(t, d)                                   # banderas de laboratorio de ingreso (reuso: estatico por estancia_id)
    d = historial_estancia(t, d)
    d = censura(d)
    return d, h, rejilla, estado


def historial_estancia(t, d):
    """Reusa comparar_estimadores.historial(), que solo necesita una columna llamada 'ini_est' con el momento
    en que se quiere saber el historial. Aqui ese momento es la asignacion de cama (ini_hosp_est), no la
    llegada: se intercambian los nombres de columna, se llama a la funcion sin tocarla y se restituyen."""
    tmp = d.rename(columns={"ini_est": "_llegada", "ini_hosp_est": "ini_est"})
    tmp = ce.historial(t, tmp)
    return tmp.rename(columns={"ini_est": "ini_hosp_est", "_llegada": "ini_est"})


def censura(d):
    """evento=True y e_estancia=horas reales si el alta esta resuelta antes de FIN_FIABLE; si no, evento=False
    y e_estancia=horas observadas (desde la asignacion de cama hasta FIN_FIABLE) como censura por la derecha.
    A diferencia de que_esperar.py/factores_estancia.py, estas filas censuradas NO se descartan: siguen
    "en riesgo" en cada landmark <= e_estancia, aportando al entrenamiento (nunca marcan un alta que no se
    sabe si ocurrio)."""
    resuelto = d.fin_hosp_est.notna() & (d.fin_hosp_est <= FIN_FIABLE)
    estancia_h = (d.fin_hosp_est - d.ini_hosp_est).dt.total_seconds() / 3600
    censura_h = (FIN_FIABLE - d.ini_hosp_est).dt.total_seconds() / 3600
    d = d.assign(evento=resuelto.to_numpy(), e_estancia=np.where(resuelto, estancia_h, censura_h))
    return d[d.e_estancia > 0].reset_index(drop=True)


def cols_finales_estancia():
    return COLS_BASE_ESTANCIA + ce.HIST + (ce.LAB if ce.HAY_LAB else [])


def estado_en_cama(d, rejilla, estado, horas_despues):
    """Ocupacion de la zona de cada paciente, horas_despues de SU ASIGNACION DE CAMA (no de su llegada,
    a diferencia de comparar_estimadores.estado_en)."""
    x = d.ini_hosp_est.to_numpy() + np.asarray(horas_despues) * H1
    k = np.clip(((x - rejilla[0]) // H1).astype(int), 0, len(rejilla) - 1)
    ninos = d.zona.to_numpy() == "ninos"
    return np.where(ninos, estado["ninos"]["ocup"][k], estado["adultos"]["ocup"][k])


# ----------------------------------------------------------------------
# 2) Filas paciente-hora (igual idea que filas_persona_hora, ancladas en ini_hosp_est)
# ----------------------------------------------------------------------
def filas_persona_hora_estancia(d, rejilla, estado, desde=0, fijar_estado=False, cols=None):
    cols = cols_finales_estancia() if cols is None else cols
    n = len(d)
    k = np.arange(desde, MAX_H_ESTANCIA)
    idx = np.repeat(np.arange(n), len(k))
    kk = np.tile(k, n)
    t_clock = d.ini_hosp_est.to_numpy()[idx] + kk * H1
    reloj = pd.DatetimeIndex(t_clock)
    if fijar_estado:
        ocup0 = estado_en_cama(d, rejilla, estado, desde)
        ocup = ocup0[idx]
    else:
        ocup = estado_en_cama(d.iloc[idx].reset_index(drop=True), rejilla, estado, kk)
    X = pd.DataFrame({"transcurrido": kk, "hora_reloj": reloj.hour, "dia_semana": reloj.day_of_week, "ocup": ocup,
                      **{c: d[c].to_numpy()[idx] for c in cols if c not in DINAMICAS_ESTANCIA}})
    return X, idx, kk


def pesos_recientes_estancia(d, idx, vida_media_dias):
    if vida_media_dias is None:
        return None
    edad = (d.ini_hosp_est.max() - d.ini_hosp_est).dt.total_seconds().to_numpy()[idx] / 86400
    return 0.5 ** (edad / vida_media_dias)


def _entrenar(X, y, w, cols):
    cols = [c for c in cols if X[c].nunique(dropna=True) > 1]        # columnas constantes (p.ej. el recorrido no aplica aqui): se quitan
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=63, min_samples_leaf=200,
                                       categorical_features=[cols.index(c) for c in CATEGORICAS_ESTANCIA if c in cols], random_state=SEMILLA)
    m.fit(X[cols], y, sample_weight=w)
    m.cols_ = cols
    return m


def entrenar_landmark_estancia(tr, rejilla, estado, desde, cols=None, vida_media_dias=None):
    """Modelo para estimar desde 'desde' horas ya en cama: quienes seguian en riesgo (en cama o censurados
    mas alla de 'desde'), con lo que se sabia al llegar a la cama."""
    cols = cols_finales_estancia() if cols is None else cols
    sub = tr[tr.e_estancia > desde].reset_index(drop=True)
    X, idx, kk = filas_persona_hora_estancia(sub, rejilla, estado, desde=desde, fijar_estado=True, cols=cols)
    e, evento = sub.e_estancia.to_numpy()[idx], sub.evento.to_numpy()[idx]
    vivo = kk <= np.floor(e)
    y = (evento & (kk == np.floor(e))).astype(int)
    w = pesos_recientes_estancia(sub, idx, vida_media_dias)
    m = _entrenar(X[vivo], y[vivo], None if w is None else w[vivo], cols)
    m.desde_ = desde
    return m


def entrenar_m1_estancia(tr, rejilla, estado, cols=None, vida_media_dias=None):
    """Modelo unico (dinamico, igual idea que entrenar_m1 del modelo de espera) para las estancias que llegan
    a UMBRAL_POOLED horas o mas: 'transcurrido' varia libremente como variable numerica, en vez de un modelo
    por landmark (generaliza mejor que un landmark propio donde hay pocas estancias largas, ver cabecera)."""
    cols = cols_finales_estancia() if cols is None else cols
    X, idx, kk = filas_persona_hora_estancia(tr, rejilla, estado, desde=0, fijar_estado=False, cols=cols)
    e, evento = tr.e_estancia.to_numpy()[idx], tr.evento.to_numpy()[idx]
    vivo = kk <= np.floor(e)
    y = (evento & (kk == np.floor(e))).astype(int)
    w = pesos_recientes_estancia(tr, idx, vida_media_dias)
    print(f"M1 estancia (dinamico, usado desde {UMBRAL_POOLED} h): {vivo.sum():,} filas paciente-hora, {y[vivo].mean():.4f} prob. media por hora")
    return _entrenar(X[vivo], y[vivo], None if w is None else w[vivo], cols)


def modelo_para_estancia(paq, horas_en_cama):
    if horas_en_cama >= UMBRAL_POOLED:
        return paq["modelos"]["pooled"]
    return paq["modelos"][max(L for L in LANDMARKS_ESTANCIA if L <= horas_en_cama)]


def predecir_estancia(m, d, rejilla, estado, desde=0):
    X, idx, kk = filas_persona_hora_estancia(d, rejilla, estado, desde=desde, fijar_estado=True, cols=m.cols_)
    p = m.predict_proba(X[m.cols_])[:, 1].reshape(len(d), MAX_H_ESTANCIA - desde)
    S = np.hstack([np.ones((len(d), 1)), np.cumprod(1 - p, axis=1)])
    return ce.cuantiles_de_supervivencia(S)


def entrenar_paquete_estancia(d, rejilla, estado, hasta=None, vida_media_dias=182):
    tr = d if hasta is None else d[d.ini_hosp_est < pd.Timestamp(hasta)].reset_index(drop=True)
    modelos = {L: entrenar_landmark_estancia(tr, rejilla, estado, L, vida_media_dias=vida_media_dias) for L in LANDMARKS_ESTANCIA}
    modelos["pooled"] = entrenar_m1_estancia(tr, rejilla, estado, vida_media_dias=vida_media_dias)
    corte = np.datetime64(pd.Timestamp(hasta) if hasta is not None else tr.ini_hosp_est.max())
    fin = rejilla[(rejilla >= corte - np.timedelta64(90, "D")) & (rejilla < corte)]
    k = np.searchsorted(rejilla, fin)
    return {"modelos": modelos, "grupos_dx": ce.GRUPOS_DX, "ocup_tipica": {z: float(np.median(estado[z]["ocup"][k])) for z in estado},
            "entrenado_hasta": str((pd.Timestamp(corte) - pd.Timedelta(days=1)).date()), "vida_media_dias": vida_media_dias,
            "con_laboratorio": ce.HAY_LAB, "origen_laboratorio": ce.ORIGEN_LAB}


# ----------------------------------------------------------------------
# 3) Baseline a vencer: que_esperar.py (percentil por perfil), condicionado a 'desde'
# ----------------------------------------------------------------------
def baseline_perfil_estancia(tr, te, desde):
    """Mismo metodo de que_esperar.py (percentil por perfil edad x sexo x tipo de visita, con retroceso a menos
    detalle si n < 30), pero condicionado a 'desde' horas ya en cama: solo estancias resueltas que ya superaron
    'desde' horas, con el valor desplazado (estancia_h - desde) -- igual idea que referencias() en
    comparar_estimadores.py para el modelo de espera. No se usa el diagnostico (con_dx=False): el perfil de
    que_esperar.py con diagnostico usa el de la visita en curso, que aqui se evita por fuga (ver cabecera)."""
    trc = tr[tr.evento & (tr.e_estancia > desde)].copy()
    trc["estancia_h"] = trc.e_estancia - desde
    trc["dx"] = "sin diagnostico"
    perfiles = te[["grupo_edad", "sexo", "tipo_visita"]].drop_duplicates()
    tabla = {}
    for _, row in perfiles.iterrows():
        perfil = {"grupo_edad": row.grupo_edad, "sexo": row.sexo, "tipo_visita": row.tipo_visita, "dx": "sin diagnostico"}
        _, g = qe.rango_para(trc, perfil, con_dx=False)
        tabla[(row.grupo_edad, row.sexo, row.tipo_visita)] = [float(np.quantile(g.estancia_h.dropna(), q)) for q in Q]
    pred = np.array([tabla[(r.grupo_edad, r.sexo, r.tipo_visita)] for r in te[["grupo_edad", "sexo", "tipo_visita"]].itertuples(index=False)])
    return np.clip(pred, 0, None)


# ----------------------------------------------------------------------
# 4) Evaluacion: perdida de cuantiles, mejora vs. baseline, IC por bootstrap de semanas
# ----------------------------------------------------------------------
def puntuar(nombre, y, pred, base, desde):
    fila = {"horas_en_cama": desde, "metodo": nombre, "n_prueba": len(y), "perdida_cuantiles": round(ce.perdida(y, pred), 3),
            "mejora_vs_perfil_pct": round(100 * (1 - ce.perdida(y, pred) / base), 1), "error_abs_mediana_h": round(float(np.nanmean(np.abs(y - pred[:, 1]))), 2)}
    for j, q in enumerate(Q):
        fila[f"pct_debajo_p{int(q * 100)}"] = round(100 * float(np.nanmean(y <= pred[:, j])), 1)
    return fila


def comparar_coherencia_landmarks(paq, muestra, rejilla, estado):
    """Para la misma estancia, la mediana implicita de alta (ini_hosp_est + landmark + faltan_p50_h) no deberia
    saltar mucho entre landmarks vecinos (misma prueba que se uso para fijar LIMITE_ENTRENAMIENTO en el modelo
    de espera, ver v7 de estimador_tiempo_restante.py)."""
    filas = []
    for L in [0] + CONTROLES_ESTANCIA:
        sub = muestra[muestra.e_estancia > L].reset_index(drop=True)
        if not len(sub):
            continue
        pct = predecir_estancia(modelo_para_estancia(paq, L), sub, rejilla, estado, desde=L)
        alta_implicita = sub.ini_hosp_est + pd.to_timedelta(L + pct[:, 1], unit="h")
        filas.append(pd.DataFrame({"estancia_id": sub.estancia_id.to_numpy(), "landmark": L, "alta_mediana": alta_implicita}))
    t = pd.concat(filas, ignore_index=True)
    piv = t.pivot_table(index="estancia_id", columns="landmark", values="alta_mediana")
    saltos_h = piv.diff(axis=1).abs().apply(lambda s: s.dt.total_seconds() / 3600 if hasattr(s, "dt") else s)
    return saltos_h


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    TABLAS.mkdir(parents=True, exist_ok=True)
    print("Preparando datos (tabla_episodios.parquet)...")
    d, h, rejilla, estado = preparar()
    print(f"{len(d):,} estancias unicas hospitalizadas (feb-2023 a 9-abr-2026); {int(d.evento.sum()):,} con alta resuelta, {int((~d.evento).sum()):,} censuradas")

    tr_all = d[d.ini_hosp_est < CORTE].reset_index(drop=True)
    te_resueltas = d[(d.ini_hosp_est >= CORTE) & (d.ini_hosp_est < HASTA_ESTANCIA_PRUEBA) & d.evento].reset_index(drop=True)
    print(f"entrenamiento {len(tr_all):,} estancias (incl. censuradas) | prueba {len(te_resueltas):,} estancias resueltas")

    print("\nCorrelacion estancia previa vs. estancia actual (pacientes con hospitalizacion previa, Spearman):")
    rep = d[d.estancia_prev_h.notna() & d.evento]
    print(f"  n={len(rep):,}  spearman={rep.e_estancia.corr(rep.estancia_prev_h, method='spearman'):.3f}")

    print("\nEntrenando el paquete de landmarks de estancia...")
    paq = entrenar_paquete_estancia(tr_all, rejilla, estado, hasta=CORTE, vida_media_dias=182)

    filas = []
    for desde in [0] + CONTROLES_ESTANCIA:
        sub = te_resueltas[te_resueltas.e_estancia > desde].reset_index(drop=True)
        if not len(sub):
            continue
        y = np.minimum(sub.e_estancia.to_numpy() - desde, MAX_H_ESTANCIA)
        pred_perfil = baseline_perfil_estancia(tr_all, sub, desde)
        base = ce.perdida(y, pred_perfil)
        m = modelo_para_estancia(paq, desde)
        pred_m1 = predecir_estancia(m, sub, rejilla, estado, desde=desde)
        for nombre, pred in [("percentil por perfil (que_esperar.py)", pred_perfil), ("M1 estancia restante (landmarks)", pred_m1)]:
            filas.append(puntuar(nombre, y, pred, base, desde))
    t = pd.DataFrame(filas)
    print("\nRESULTADO (prueba jul-2025 a 9-ene-2026, estancias con alta resuelta)")
    print(t.to_string(index=False))
    t.to_csv(TABLAS / "comparacion_estimadores_estancia.csv", index=False)

    print("\nIC 95 % de la mejora (bootstrap de semanas, M1 vs. percentil por perfil) al landmark 0:")
    sub0 = te_resueltas.reset_index(drop=True)
    y0 = sub0.e_estancia.to_numpy()
    semana = sub0.ini_hosp_est.dt.to_period("W").astype(str).to_numpy()
    l_m1 = ce.perdida_por_caso(y0, predecir_estancia(modelo_para_estancia(paq, 0), sub0, rejilla, estado, desde=0))
    l_perfil = ce.perdida_por_caso(y0, baseline_perfil_estancia(tr_all, sub0, 0))
    ic = ce.intervalo_mejora(semana, l_m1, l_perfil)
    print(f"  mejora M1 vs. perfil: {100 * (1 - l_m1.mean() / l_perfil.mean()):.1f} %  (IC95 {ic[0]:.1f} a {ic[1]:.1f})")
    pd.DataFrame([{"landmark": 0, "mejora_pct": round(100 * (1 - l_m1.mean() / l_perfil.mean()), 1), "ic95_bajo": round(ic[0], 1), "ic95_alto": round(ic[1], 1)}]) \
        .to_csv(TABLAS / "comparacion_estimadores_estancia_ic.csv", index=False)

    print("\nCoherencia entre landmarks vecinos (saltos de la mediana de alta implicita, muestra de 500 estancias en prueba):")
    muestra = te_resueltas.sample(min(500, len(te_resueltas)), random_state=SEMILLA).reset_index(drop=True)
    saltos = comparar_coherencia_landmarks(paq, muestra, rejilla, estado)
    print(saltos.describe().T[["mean", "50%", "max"]].round(2))

    GRAF.mkdir(parents=True, exist_ok=True)
    m1 = t[t.metodo == "M1 estancia restante (landmarks)"].sort_values("horas_en_cama")
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    ax.bar(m1.horas_en_cama.astype(str), m1.mejora_vs_perfil_pct, color="#2a6fb0")
    ax.axhline(0, color="#52514e", lw=0.8)
    ax.set_xlabel("horas que el paciente ya lleva en cama")
    ax.set_ylabel("mejora vs. percentil por perfil (%)")
    ax.set_title("Mejora del estimador de estancia frente al rango por perfil (que_esperar.py)")
    ax.grid(axis="y", color="#e5e4df")
    fig.text(0.01, 0.01, "Prueba jul-2025 a 9-ene-2026 (estancias con alta resuelta que el modelo no vio). Fuente: src/comparar_estimadores_estancia.py",
             fontsize=8, color="#52514e")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(GRAF / "comparacion_estimadores_estancia.png", dpi=150)
