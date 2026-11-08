"""
comparar_estimadores.py  -  version 1 (7-nov-2026)
Tarea A6, tercera parte: tres maneras de estimar la espera de cama, comparadas en la misma prueba.

LOS TRES METODOS
  M1. TIEMPO RESTANTE (supervivencia por hora): para cada hora de espera se estima la probabilidad de recibir cama en la hora siguiente, segun cuanto lleva
      esperando, la hora del reloj, el dia de la semana, la cola y la ocupacion de su zona en ese momento, la edad, el sexo y el tipo de visita (arboles de
      gradiente). Multiplicando hora por hora sale la distribucion completa del tiempo que falta, y se puede recalcular en cualquier momento de la espera.
  M2. AL LLEGAR CON MAS VARIABLES (regresion por cuantiles): un modelo por percentil (25, 50, 75, 90) con lo que se sabe al llegar mas el estado del
      hospital en ese momento: hora, dia, mes, edad, sexo, tipo de visita, cola y ocupacion de su zona, llegadas de las 6 h previas.
  M3. COLA: las camas se asignan a la tasa historica de su zona en cada hora del dia y dia de la semana. Dos versiones:
      M3a orden aleatorio: cada hora, la probabilidad de recibir cama es camas asignadas / pacientes en cola;
      M3b en orden de llegada: recibe cama cuando se han asignado tantas camas como pacientes tenia delante (Poisson).
  Referencias: el rango general (el mismo para todos) y la tabla de perfiles de estimador_tiempos.py (hora, edad, tipo de visita y sexo).

LA PRUEBA
  Entrenamiento con llegadas de feb-2023 a jun-2025; prueba con jul-2025 a 9-abr-2026 (estancias unicas con espera medida).
  1. Al llegar: cada metodo da los percentiles 25, 50, 75 y 90. Se mide la perdida de cuantiles (menor es mejor), la mejora frente al rango general y si
     los percentiles aciertan (cuantos casos quedan por debajo de cada uno).
  2. Durante la espera (despues de 6, 12, 24 y 48 h sin cama): el tiempo que le falta a quien sigue esperando. M2 no aplica (solo estima al llegar).

COLA Y OCUPACION
  Por hora y por zona (adultos de 15 anos o mas, ninos), con estancias unicas: ocupacion = pacientes en cama; cola = pacientes que ya llegaron, se
  hospitalizaran y aun no tienen cama. OJO: la cola usa saber quien se hospitalizara despues; en el hospital equivale a los pacientes con orden de
  hospitalizacion pendiente, que si se conocen en el momento, pero aqui incluye tambien la atencion clinica previa a esa orden.
  Para estimar hacia adelante, la cola y la ocupacion se dejan fijas en el ultimo valor conocido (persistencia, que fue lo mejor para camas, CLAUDE.md 6b).

ENTRADA  tabla_episodios.parquet en HUN_PROCESADOS ; SALIDAS en HUN_TABLAS: comparacion_estimadores_al_llegar.csv, comparacion_estimadores_en_espera.csv,
         m1_probabilidad_por_hora_reloj.csv ; resultados/graficos/comparacion_estimadores.png
COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... python3 src/comparar_estimadores.py   (unos minutos)
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
import estimador_tiempos as et  # noqa: E402

PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
GRAF = RAIZ / "resultados" / "graficos"
DESDE, HASTA, CORTE = et.DESDE, et.HASTA, et.CORTE
Q = et.CUANTILES
MAX_H = 240                                   # horizonte de la supervivencia (10 dias); mas alla se toma como 240 h
CONTROLES = [6, 12, 24, 48]                   # horas de espera en que se vuelve a estimar
SEMILLA = 7
# Ago-sep 2025: sobredemanda porque hospitales cercanos fueron intervenidos por el Estado y el HUN quedo como la unica opcion de la zona (dato del
# equipo, 7-nov). En los datos se ve poco: +6-7 % de llegadas frente a ago-sep 2024 y ingresos y espera mediana normales. Se evaluan aparte.
MESES_SOBREDEMANDA = ["2025-08", "2025-09"]
H1 = np.timedelta64(1, "h")


# ----------------------------------------------------------------------
# 1) Estancias, cola y ocupacion por hora y zona
# ----------------------------------------------------------------------
def preparar():
    t = pd.read_parquet(PROC / "tabla_episodios.parquet")
    h = t[t.hospitalizado & t.estancia_unica & t.edad.notna() & (t.ini_est <= t.ini_hosp_est)].copy()
    h["zona"] = np.where(h.edad < 15, "ninos", "adultos")
    rejilla = pd.date_range(h.ini_est.min().floor("h"), h.fin_hosp_est.max().ceil("h"), freq="h").to_numpy()
    estado = {}
    for zona, g in h.groupby("zona"):
        def contar(a, b):
            return np.searchsorted(np.sort(a), rejilla, side="right") - np.searchsorted(np.sort(b), rejilla, side="right")
        estado[zona] = {"cola": contar(g.ini_est.to_numpy(), g.ini_hosp_est.to_numpy()),
                        "ocup": contar(g.ini_hosp_est.to_numpy(), g.fin_hosp_est.to_numpy())}
    d = h[(h.ini_est >= DESDE) & (h.ini_est < HASTA) & h.espera_cama_h.notna() & h.sexo.isin(["Mujer", "Hombre"]) & h.tipo_visita.isin(et.TIPOS)].copy()
    d["grupo_edad"] = d.grupo_edad.astype(str)
    d["bloque_hora"] = pd.Series(et.BLOQUES)[d.hora.to_numpy() // 3].to_numpy()
    d["edad_cod"] = d.grupo_edad.map({e: i for i, e in enumerate(et.EDADES)})
    d["tipo_cod"] = d.tipo_visita.map({v: i for i, v in enumerate(et.TIPOS)})
    d["sexo_cod"] = (d.sexo == "Mujer").astype(int)
    d["zona_cod"] = (d.zona == "ninos").astype(int)
    d["llegadas_6h"] = d.get("llegadas_6h_previas", pd.Series(np.nan, index=d.index))
    d = d.reset_index(drop=True)
    return d, h, rejilla, estado


def estado_en(d, rejilla, estado, horas_despues):
    """Cola y ocupacion de la zona de cada paciente, horas_despues de su llegada (arreglo o escalar)."""
    x = d.ini_est.to_numpy() + np.asarray(horas_despues) * H1
    k = np.clip(((x - rejilla[0]) // H1).astype(int), 0, len(rejilla) - 1)
    ninos = d.zona.to_numpy() == "ninos"
    cola = np.where(ninos, estado["ninos"]["cola"][k], estado["adultos"]["cola"][k])
    ocup = np.where(ninos, estado["ninos"]["ocup"][k], estado["adultos"]["ocup"][k])
    return cola, ocup


# ----------------------------------------------------------------------
# 2) Utilidades de evaluacion
# ----------------------------------------------------------------------
def perdida(y, pred):
    """Suma de las perdidas de cuantiles de los 4 percentiles (pred: matriz n x 4)."""
    e = y[:, None] - pred
    return np.nanmean(np.maximum(np.array(Q) * e, (np.array(Q) - 1) * e), axis=0).sum()


def cuantiles_de_supervivencia(S):
    """S: matriz n x (H+1) con S[:, k] = P(T > k horas). Devuelve n x 4 percentiles en horas (interpolados)."""
    F = 1 - S
    out = np.full((len(S), len(Q)), float(S.shape[1] - 1))
    for j, q in enumerate(Q):
        llega = F >= q
        k = np.where(llega.any(axis=1), llega.argmax(axis=1), -1)
        ok = k > 0
        f0, f1 = F[ok, k[ok] - 1], F[ok, k[ok]]
        out[ok, j] = (k[ok] - 1) + (q - f0) / np.maximum(f1 - f0, 1e-9)
        out[k == 0, j] = 0.0
    return out


# ----------------------------------------------------------------------
# 3) M1: supervivencia por hora (tiempo restante)
# ----------------------------------------------------------------------
DINAMICAS = ["transcurrido", "hora_reloj", "dia_semana", "cola", "ocup"]
COLS_M1 = DINAMICAS + ["edad_cod", "tipo_cod", "sexo_cod", "zona_cod"]
CATEGORICAS = ["hora_reloj", "dia_semana", "tipo_cod", "dx_cod"]


def filas_persona_hora(d, rejilla, estado, desde=0, fijar_estado=False, cols=COLS_M1):
    """Una fila por paciente y hora de espera desde 'desde' hasta MAX_H (o hasta recibir cama si se entrena)."""
    n = len(d)
    k = np.arange(desde, MAX_H)
    idx = np.repeat(np.arange(n), len(k))
    kk = np.tile(k, n)
    t = d.ini_est.to_numpy()[idx] + kk * H1
    reloj = pd.DatetimeIndex(t)
    if fijar_estado:
        cola0, ocup0 = estado_en(d, rejilla, estado, desde)
        cola, ocup = cola0[idx], ocup0[idx]
    else:
        cola, ocup = estado_en(d.iloc[idx].reset_index(drop=True), rejilla, estado, kk)
    X = pd.DataFrame({"transcurrido": kk, "hora_reloj": reloj.hour, "dia_semana": reloj.dayofweek, "cola": cola, "ocup": ocup,
                      **{c: d[c].to_numpy()[idx] for c in cols if c not in DINAMICAS}})
    return X, idx, kk


def entrenar_m1(tr, rejilla, estado, cols=COLS_M1):
    X, idx, kk = filas_persona_hora(tr, rejilla, estado, cols=cols)
    e = tr.espera_cama_h.to_numpy()[idx]
    vivo = kk <= np.floor(e)                                # en riesgo en la hora kk
    y = (kk == np.floor(e)).astype(int)
    X, y = X[vivo], y[vivo]
    print(f"M1: {len(X):,} filas paciente-hora para entrenar, {y.mean():.3f} de probabilidad media por hora")
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=63, min_samples_leaf=200,
                                       categorical_features=[cols.index(c) for c in CATEGORICAS if c in cols], random_state=SEMILLA)
    m.fit(X[cols], y)
    m.cols_ = cols
    return m


def predecir_m1(m, d, rejilla, estado, desde=0):
    X, idx, kk = filas_persona_hora(d, rejilla, estado, desde=desde, fijar_estado=True, cols=m.cols_)
    p = m.predict_proba(X[m.cols_])[:, 1].reshape(len(d), MAX_H - desde)
    S = np.hstack([np.ones((len(d), 1)), np.cumprod(1 - p, axis=1)])
    return cuantiles_de_supervivencia(S)                    # horas que faltan desde 'desde'


# ----------------------------------------------------------------------
# 4) M2: cuantiles al llegar
# ----------------------------------------------------------------------
COLS_M2 = ["hora", "dia_semana_num", "mes", "edad_cod", "tipo_cod", "sexo_cod", "zona_cod", "cola0", "ocup0", "llegadas_6h"]


def matriz_m2(d, rejilla, estado):
    cola0, ocup0 = estado_en(d, rejilla, estado, 0)
    return d.assign(cola0=cola0, ocup0=ocup0, mes=d.ini_est.dt.month, dia_semana_num=d.ini_est.dt.dayofweek)[COLS_M2]


def m2(tr, te, rejilla, estado):
    Xtr, Xte = matriz_m2(tr, rejilla, estado), matriz_m2(te, rejilla, estado)
    ytr = np.log1p(tr.espera_cama_h.to_numpy())
    pred = np.column_stack([np.expm1(HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=300, learning_rate=0.05,
                                                                   max_leaf_nodes=31, min_samples_leaf=100, random_state=SEMILLA).fit(Xtr, ytr).predict(Xte))
                            for q in Q])
    return np.maximum.accumulate(np.clip(pred, 0, None), axis=1)


# ----------------------------------------------------------------------
# 5) M3: modelo de cola
# ----------------------------------------------------------------------
def tasas_asignacion(h):
    """Camas asignadas por hora, por zona, hora del dia y dia de la semana (promedio del entrenamiento)."""
    a = h[(h.ini_hosp_est >= DESDE) & (h.ini_hosp_est < CORTE)]
    slots = pd.date_range(DESDE, CORTE, freq="h", inclusive="left")
    n_slots = pd.Series(1, index=slots).groupby([slots.dayofweek, slots.hour]).sum()
    tasa = {}
    for zona, g in a.groupby("zona"):
        c = g.groupby([g.ini_hosp_est.dt.dayofweek, g.ini_hosp_est.dt.hour]).size()
        tasa[zona] = (c.reindex(n_slots.index, fill_value=0) / n_slots).to_numpy().reshape(7, 24)
    return tasa


def m3(d, rejilla, estado, tasa, desde=0, fifo=False):
    cola, _ = estado_en(d, rejilla, estado, desde)
    k = np.arange(desde, MAX_H)
    t = d.ini_est.to_numpy()[:, None] + k[None, :] * H1
    reloj = pd.DatetimeIndex(t.ravel())
    ninos = (d.zona.to_numpy() == "ninos")[:, None]
    lam = np.where(ninos, tasa["ninos"][reloj.dayofweek, reloj.hour].reshape(t.shape), tasa["adultos"][reloj.dayofweek, reloj.hour].reshape(t.shape))
    if fifo:
        delante = np.maximum(cola - 1, 0)                   # la cola ya incluye al paciente
        Lam = np.cumsum(lam, axis=1)
        S = np.hstack([np.ones((len(d), 1)), poisson.cdf(delante[:, None], Lam)])   # P(menos de 'delante'+1 camas asignadas)
    else:
        p = np.minimum(1, lam / np.maximum(cola, 1)[:, None])
        S = np.hstack([np.ones((len(d), 1)), np.cumprod(1 - p, axis=1)])
    return cuantiles_de_supervivencia(S)


# ----------------------------------------------------------------------
# 6) Referencias: rango general y tabla de perfiles (tambien condicionadas a seguir esperando)
# ----------------------------------------------------------------------
def referencias(tr, te, desde=0):
    trc = tr[tr.espera_cama_h > desde].assign(valor=lambda x: x.espera_cama_h - desde)
    res = et.tabla_por_nivel(trc, "espera_cama_h")
    general = np.tile(res[res.nivel == 0][[f"p{int(q * 100)}" for q in Q]].to_numpy(), (len(te), 1))
    perfil = et.asignar(te, res, len(et.DIMS))[[f"p{int(q * 100)}" for q in Q]].to_numpy()
    return general, perfil


def puntuar(nombre, y, pred, base, desde):
    fila = {"horas_esperando": desde, "metodo": nombre, "n_prueba": len(y), "perdida_cuantiles": round(perdida(y, pred), 3),
            "mejora_vs_general_pct": round(100 * (1 - perdida(y, pred) / base), 1),
            "error_abs_mediana_h": round(np.nanmean(np.abs(y - pred[:, 1])), 2)}
    for j, q in enumerate(Q):
        fila[f"pct_debajo_p{int(q * 100)}"] = round(100 * np.nanmean(y <= pred[:, j]), 1)
    fila["pct_dentro_p25_p75"] = round(100 * np.nanmean((y > pred[:, 0]) & (y <= pred[:, 2])), 1)
    return fila


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    TABLAS.mkdir(parents=True, exist_ok=True)
    d, h, rejilla, estado = preparar()
    tr, te = d[d.ini_est < CORTE].reset_index(drop=True), d[d.ini_est >= CORTE].reset_index(drop=True)
    print(f"entrenamiento {len(tr):,} estancias | prueba {len(te):,}")
    m1 = entrenar_m1(tr, rejilla, estado)
    tasa = tasas_asignacion(h)

    filas = []
    for desde in [0] + CONTROLES:
        sub = te[te.espera_cama_h > desde].reset_index(drop=True)
        y = np.minimum(sub.espera_cama_h.to_numpy() - desde, MAX_H)
        general, perfil = referencias(tr, sub, desde)
        base = perdida(y, general)
        preds = {"rango general (referencia)": general, "tabla de perfiles (A6 actual)": perfil,
                 "M1 tiempo restante": predecir_m1(m1, sub, rejilla, estado, desde),
                 "M3a cola, orden aleatorio": m3(sub, rejilla, estado, tasa, desde),
                 "M3b cola, orden de llegada": m3(sub, rejilla, estado, tasa, desde, fifo=True)}
        if desde == 0:
            preds["M2 al llegar con mas variables"] = m2(tr, sub, rejilla, estado)
        sobre = sub.ini_est.dt.to_period("M").astype(str).isin(MESES_SOBREDEMANDA).to_numpy()
        for periodo, m in [("toda la prueba", np.ones(len(sub), bool)), ("sin ago-sep 2025", ~sobre), ("solo ago-sep 2025", sobre)]:
            base_p = perdida(y[m], general[m])
            for nombre, pred in preds.items():
                filas.append({"periodo": periodo, **puntuar(nombre, y[m], pred[m], base_p, desde)})
        print(f"listo: {desde} h esperando ({len(sub):,} casos)")
    todo = pd.DataFrame(filas)
    todo[todo.horas_esperando == 0].to_csv(TABLAS / "comparacion_estimadores_al_llegar.csv", index=False)
    todo.to_csv(TABLAS / "comparacion_estimadores_en_espera.csv", index=False)
    res = todo[todo.periodo == "toda la prueba"]
    print("\nCOMPARACION (prueba jul-2025 a 9-abr-2026; perdida menor = mejor; lo ideal debajo de cada percentil es 25 / 50 / 75 / 90 %)")
    print(res.drop(columns="periodo").to_string(index=False))
    print("\nAL LLEGAR, SEPARANDO AGO-SEP 2025 (sobredemanda)")
    print(todo[(todo.horas_esperando == 0) & (todo.periodo != "toda la prueba")][["periodo", "metodo", "n_prueba", "mejora_vs_general_pct",
          "error_abs_mediana_h", "pct_debajo_p25", "pct_debajo_p50", "pct_debajo_p75", "pct_debajo_p90"]].to_string(index=False))

    # Lectura de M1: probabilidad media de recibir cama en la hora siguiente segun la hora del reloj (con todo lo demas como en la prueba)
    X, _, _ = filas_persona_hora(te.sample(min(1500, len(te)), random_state=SEMILLA).reset_index(drop=True), rejilla, estado)
    X = X[X.transcurrido < 72]
    reloj = pd.DataFrame({"hora_reloj": range(24), "prob_cama_siguiente_hora": [m1.predict_proba(X.assign(hora_reloj=hh)[COLS_M1])[:, 1].mean() for hh in range(24)]})
    reloj.round(4).to_csv(TABLAS / "m1_probabilidad_por_hora_reloj.csv", index=False)
    print("\nM1: probabilidad media de recibir cama en la hora siguiente, por hora del reloj\n" + reloj.round(3).T.to_string())

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6))
    orden = ["rango general (referencia)", "tabla de perfiles (A6 actual)", "M2 al llegar con mas variables", "M1 tiempo restante",
             "M3a cola, orden aleatorio", "M3b cola, orden de llegada"]
    colores = {"rango general (referencia)": "#c9c8c3", "tabla de perfiles (A6 actual)": "#8a8984", "M2 al llegar con mas variables": "#1baf7a",
               "M1 tiempo restante": "#2a78d6", "M3a cola, orden aleatorio": "#eb6834", "M3b cola, orden de llegada": "#f2a37f"}
    for nombre in orden:
        g = res[res.metodo == nombre]
        a1.plot(g.horas_esperando, g.mejora_vs_general_pct, marker="o", color=colores[nombre], label=nombre)
    a1.axhline(0, color="#52514e", lw=0.8)
    a1.set_xlabel("horas que el paciente ya lleva esperando")
    a1.set_ylabel("mejora frente al rango general (%)")
    a1.set_title("¿Qué método estima mejor el tiempo que falta?")
    a1.legend(frameon=False, fontsize=8)
    a1.grid(axis="y", color="#e5e4df")
    a2.bar(reloj.hora_reloj, 100 * reloj.prob_cama_siguiente_hora, color="#2a78d6")
    a2.set_xlabel("hora del reloj")
    a2.set_ylabel("% que recibe cama en la hora siguiente")
    a2.set_title("M1: la hora del día manda (paciente que sigue esperando)")
    a2.grid(axis="y", color="#e5e4df")
    fig.text(0.01, 0.01, "Prueba con jul-2025 a 9-abr-2026 (entrenamiento feb-2023 a jun-2025). Fuente: src/comparar_estimadores.py", fontsize=8, color="#52514e")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(GRAF / "comparacion_estimadores.png", dpi=150)
