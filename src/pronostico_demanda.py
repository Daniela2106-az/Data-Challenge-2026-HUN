"""
pronostico_demanda.py  -  version 1.3 (22-oct-2026)
Fase 6 del plan de cuellos de botella y ficha D.1 (Modelo A): pronostico de llegadas e ingresos a cama,
con alerta de "dia congestionado". Entrena con el pasado y prueba con el futuro (validacion temporal).

CAMBIOS DE LA v1.3 (hallados con src/dias_atipicos.py, que revisa los dias que el modelo erro mas)
  - Fin de anio: el 24 y el 31 de diciembre bajan las llegadas y el 25 de diciembre y el 1 de enero las suben; antes
    iban juntos en una sola marca y se cancelaban. La mejora SE VE TAMBIEN en la validacion de 2025-07 a 2025-12.
  - Carnaval de Barranquilla (sabado a martes antes del miercoles de ceniza): llegadas ~16 % menores. Se descubrio
    con los residuos de 2024 y 2025 (en muestra) y 2026 solo lo CONFIRMA; la validacion de 2025 no tiene carnavales,
    asi que esta marca no se pudo elegir con ella. Se asume que el HUN esta en Barranquilla (por la universidad).

CAMBIOS DE LA v1.2 (cada uno se probo antes con la validacion de 2025-07 a 2025-12 y se confirmo en 2026)
  - Calendario: festivo entre semana y festivo en fin de semana por separado (un festivo en sabado o domingo no
    baja las llegadas porque ya son bajas) y semana santa. Mejora las llegadas.
  - "Sorpresa" del ultimo dia conocido: cuanto se desvio el ultimo dia que ya se conoce de lo que se esperaba
    (los errores tienen memoria: autocorrelacion 0,35 al dia siguiente). Mejora las llegadas, no los ingresos.
  - Bandas del 80 % con los errores de los ultimos 60 dias conocidos (antes: errores fijos de la validacion).
  - Alerta con un clasificador logistico propio y corte elegido en validacion (antes: probabilidad del modelo).
  - Ingresos: ademas del diario se evalua por SEMANA, donde el ruido de conteo se promedia.
  - Probado y descartado: nivel con mediana de 28 dias (empeora) y cambiar la ventana del nivel (casi no cambia).
    No probado: modelar los ingresos como fraccion de las llegadas pronosticadas.

QUE HACE
  1. Pronostica llegadas por dia, ingresos a cama por dia (estancias unicas) y llegadas por hora.
  2. Metodos que compiten (todos se miden igual):
       - promedio del dia de la semana en el entrenamiento
       - el mismo dia de la semana anterior
       - promedio del dia de la semana ajustado al nivel reciente (ultimos 28 dias ya conocidos)
       - regresion de Poisson con calendario y, segun la variante, nivel reciente, sorpresa del ultimo dia o mes
  3. El METODO ELEGIDO es el de menor error en la validacion (2025-07 a 2025-12), sin mirar la prueba.
     Despues se entrena con todo hasta 2025-12 y se prueba en 2026-01 a 2026-04.
  4. MAYO 2026 se reporta aparte (prueba de estres): las llegadas caen de forma sostenida desde abril y puede
     ser carga de datos incompleta. No se usa para evaluar.
  5. Horizontes: 1 dia (nivel hasta ayer) y 7 dias (nivel hasta hace 7 dias, para planear la semana).
  6. Alerta: dia congestionado = llegadas por encima del percentil 90 del mismo dia de la semana en las 12
     semanas anteriores. Clasificador logistico con el pronostico, el dia, la sorpresa y el cambio de nivel.
  7. Pronostico por hora = pronostico diario elegido x forma horaria del dia de la semana.

ENTRADAS  datos/procesados/para_equipo/panel_diario.csv, datos/procesados/serie_horaria.csv
SALIDAS   resultados/tablas/pronostico_metricas.csv, pronostico_diario_test.csv, pronostico_alerta.csv,
          pronostico_horario_metricas.csv, pronostico_semanal_metricas.csv, tendencia_mensual.csv
          resultados/graficos/pronostico_demanda.png

OJO AL LEER
  - `llegadas` cuenta todos los episodios (incluye al menos 4 % de replicas, ver docs/CONTEXTO_TECNICO.md 4.6). El nivel esta algo
    inflado; la dinamica (dia de la semana, festivos, tendencia) no.
  - Los ingresos diarios son casi puro ruido de conteo (varianza = media): no hay mejora posible por el lado del modelo.
  - Es un pronostico de calendario y nivel: no anticipa brotes (dengue), eventos, cortes de sistema ni cambios de registro.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import modelo_pronostico as mp  # noqa: E402  (A9: comparte la estacionalidad con el modelo vigente)

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
for _d in (TABLAS, GRAFICOS):
    _d.mkdir(parents=True, exist_ok=True)

ENTRENA_HASTA, VALIDA_ENTRENA_HASTA, VALIDA_DESDE = "2025-12-31", "2025-06-30", "2025-07-01"
PRUEBA_DESDE, PRUEBA_HASTA = "2026-01-01", "2026-04-09"
ESTRES_DESDE, FIN_DATOS = "2026-04-10", "2026-05-31"
VENTANA_NIVEL = 28
VENTANA_BANDA = 60
HORIZONTES = [1, 7]
SEMANAS_ALERTA = 12

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


def poisson_fit(X, y, ridge=1e-4, iters=60):
    """Regresion de Poisson (enlace log) por minimos cuadrados reponderados."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    beta = np.zeros(X.shape[1])
    beta[0] = np.log(y.mean())
    for _ in range(iters):
        eta = np.clip(X @ beta, -20, 20)
        mu = np.exp(eta)
        z = eta + (y - mu) / mu
        nuevo = np.linalg.solve(X.T @ (X * mu[:, None]) + ridge * np.eye(X.shape[1]), X.T @ (mu * z))
        converge = np.abs(nuevo - beta).max() < 1e-8
        beta = nuevo
        if converge:
            break
    return beta


def logistic_fit(X, y, ridge=1e-2, iters=60):
    """Regresion logistica por minimos cuadrados reponderados."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))
        W = np.clip(p * (1 - p), 1e-6, None)
        z = X @ beta + (y - p) / W
        nuevo = np.linalg.solve(X.T @ (X * W[:, None]) + ridge * np.eye(X.shape[1]), X.T @ (W * z))
        converge = np.abs(nuevo - beta).max() < 1e-8
        beta = nuevo
        if converge:
            break
    return beta


def predice(beta, X):
    return np.exp(np.clip(np.asarray(X, float) @ beta, -20, 20))


def prob(beta, X):
    return 1 / (1 + np.exp(-np.clip(np.asarray(X, float) @ beta, -30, 30)))


def metricas(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {"MAE": np.abs(y - p).mean(), "WAPE_%": 100 * np.abs(y - p).sum() / y.sum(),
            "sesgo_%": 100 * (p - y).sum() / y.sum()}


def auc(y, score):
    """AUC por rangos (probabilidad de que un positivo tenga mayor puntaje que un negativo)."""
    y, s = np.asarray(y, bool), pd.Series(np.asarray(score, float)).rank().values
    n1, n0 = y.sum(), (~y).sum()
    return np.nan if n1 == 0 or n0 == 0 else (s[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


# ----------------------------------------------------------------------
# 1) Carga y calendario
# ----------------------------------------------------------------------
titulo("1. CARGA Y TENDENCIA")
d = pd.read_csv(PROC / "para_equipo" / "panel_diario.csv", parse_dates=["fecha"]).set_index("fecha")
d["festivo"] = d.festivo.astype(bool)
d["dow"] = d.index.dayofweek
d["fest_habil"] = d.festivo & (d.dow < 5)          # un festivo en sabado o domingo no baja las llegadas
d["fest_finde"] = d.festivo & (d.dow >= 5)
d["vispera"] = d.festivo.shift(-1, fill_value=False)
d["despues"] = d.festivo.shift(1, fill_value=False)
# fin de anio: el 24 y el 31 de diciembre bajan las llegadas y el 25 de diciembre y el 1 de enero las suben (efectos opuestos)
d["bajo_fin"] = (d.index.month == 12) & d.index.day.isin([24, 31])
d["alto_fin"] = ((d.index.month == 12) & (d.index.day == 25)) | ((d.index.month == 1) & (d.index.day == 1))
d["semana_santa"] = False
d["carnaval"] = False        # Carnaval de Barranquilla: sabado a martes antes del miercoles de ceniza (pascua - 50 a - 47 dias)
for _a in range(d.index.min().year, d.index.max().year + 1):
    _e = pd.Timestamp(easter(_a))
    d.loc[(d.index >= _e - pd.Timedelta(days=7)) & (d.index <= _e), "semana_santa"] = True
    d.loc[(d.index >= _e - pd.Timedelta(days=50)) & (d.index <= _e - pd.Timedelta(days=47)), "carnaval"] = True
d["mes"] = d.index.month
print(f"{len(d)} dias ({d.index.min().date()} a {d.index.max().date()})")
tend = d.groupby(d.index.to_period("M"))[["llegadas", "ingresos_a_cama"]].mean().round(1)
tend.index = tend.index.astype(str)
tend.to_csv(TABLAS / "tendencia_mensual.csv")
print("promedio por dia segun el anio:")
print(d.groupby(d.index.year)[["llegadas", "ingresos_a_cama"]].mean().round(1).to_string())
print("ultimos 8 meses (promedio por dia):")
print(tend.tail(8).T.to_string())
print("ATENCION: mayo 2026 cae ~25 % frente a abril y la caida sigue en junio y julio (serie_diaria). Se trata como "
      "posible carga incompleta (pregunta 14 para el HUN) y no se usa para evaluar.")

OBJETIVOS = {"llegadas": "llegadas por dia", "ingresos_a_cama": "ingresos a cama por dia"}
DOW = pd.get_dummies(d.dow, prefix="dow", dtype=float).drop(columns="dow_0")
# variante -> (nivel reciente, mes, sorpresa del ultimo dia conocido)
VARIANTES = {"calendario": (False, False, False), "calendario + nivel reciente": (True, False, False),
             "calendario + nivel + sorpresa": (True, False, True), "calendario + nivel + mes": (True, True, False)}
REFERENCIAS = ["promedio del dia de la semana", "mismo dia de la semana anterior", "dia de la semana x nivel reciente"]


def nivel_h(col, h):
    return d[col].rolling(VENTANA_NIVEL).mean().shift(h)


def sorpresa(col, h, entr_fin):
    """log(real / esperado) del ultimo dia conocido; el esperado usa el factor del dia de la semana del entrenamiento."""
    y, L1 = d[col], nivel_h(col, 1)
    m = (d.index <= entr_fin) & L1.notna()
    fd = (y[m] / L1[m]).groupby(d.dow[m]).mean()
    return np.log(y / (d.dow.map(fd) * L1)).shift(h).clip(-0.8, 0.8)


def diseno(col, h, variante, entr_fin):
    nv, ms, so = VARIANTES[variante]
    X = pd.concat([pd.Series(1.0, index=d.index, name="const"), DOW,
                   d[["fest_habil", "fest_finde", "vispera", "despues", "bajo_fin", "alto_fin", "semana_santa",
                      "carnaval"]].astype(float)], axis=1)
    if nv:
        X["log_nivel"] = np.log(nivel_h(col, h))
    if so:
        X["sorpresa"] = sorpresa(col, h, entr_fin)
    if ms:
        X = pd.concat([X, pd.get_dummies(d.mes, prefix="mes", dtype=float).drop(columns="mes_1")], axis=1)
    est = mp.columnas_estacionales(d.index, col)    # A9 (12-nov): mismas columnas, mismo orden que src/modelo_pronostico.calendario()
    for c in est.columns:
        X[c] = est[c].to_numpy()
    return X


def predicciones(col, h, entr_fin, ev0, ev1):
    """Pronostica los dias valid entre ev0 y ev1 con todos los metodos, entrenando solo con dias hasta entr_fin."""
    y = d[col]
    L = nivel_h(col, h)
    valido = L.notna() & sorpresa(col, h, entr_fin).notna() & y.shift(7).notna()
    entr = valido & (d.index <= entr_fin)
    evalu = valido & (d.index >= ev0) & (d.index <= ev1)
    fact = (y[entr] / L[entr]).groupby(d.dow[entr]).mean()
    salida = {REFERENCIAS[0]: d.dow[evalu].map(y[entr].groupby(d.dow[entr]).mean()),
              REFERENCIAS[1]: y.shift(7)[evalu],
              REFERENCIAS[2]: d.dow[evalu].map(fact) * L[evalu]}
    for v in VARIANTES:
        X = diseno(col, h, v, entr_fin)
        b = poisson_fit(X[entr].values, y[entr].values)
        salida[f"Poisson: {v}"] = pd.Series(predice(b, X[evalu].values), index=d.index[evalu])
    return salida


# ----------------------------------------------------------------------
# 2) Seleccion en validacion y prueba
# ----------------------------------------------------------------------
titulo("2. PRONOSTICO DIARIO: seleccion en validacion (2025-07 a 2025-12) y prueba (2026-01 a 2026-04)")
filas, elegido, pred_val, pred_all = [], {}, {}, {}
for col, nombre in OBJETIVOS.items():
    y = d[col]
    for h in HORIZONTES:
        pv = predicciones(col, h, VALIDA_ENTRENA_HASTA, "2023-01-01", ENTRENA_HASTA)
        en_val = lambda s: s[s.index >= VALIDA_DESDE]
        wape_val = {m: metricas(y[en_val(p).index], en_val(p).values)["WAPE_%"] for m, p in pv.items()}
        mejor = min(wape_val, key=wape_val.get)
        elegido[(col, h)] = mejor
        pred_val[(col, h)] = pv[mejor]
        pa = predicciones(col, h, ENTRENA_HASTA, "2023-01-01", FIN_DATOS)
        pred_all[(col, h)] = pa
        prueba = pa[mejor].index[(pa[mejor].index >= PRUEBA_DESDE) & (pa[mejor].index <= PRUEBA_HASTA)]
        for m, p in pa.items():
            filas.append({"objetivo": nombre, "horizonte_dias": h, "metodo": m,
                          "WAPE_validacion_%": round(wape_val[m], 1), "elegido_en_validacion": m == mejor,
                          **metricas(y[prueba], p.reindex(prueba).values)})
        print(f"{nombre}, horizonte {h} d -> elegido en validacion: {mejor} (WAPE {wape_val[mejor]:.1f} %)")
met = pd.DataFrame(filas)
met["MAE"] = met.MAE.round(2)
met["WAPE_%"] = met["WAPE_%"].round(1)
met["sesgo_%"] = met["sesgo_%"].round(1)
met["orden_en_prueba"] = met.groupby(["objetivo", "horizonte_dias"]).MAE.rank().astype(int)
met.to_csv(TABLAS / "pronostico_metricas.csv", index=False)
print("\nMETRICAS EN LA PRUEBA (2026-01 a 2026-04). MAE = error medio en personas por dia; WAPE = error relativo; "
      "sesgo = tendencia a sobre (+) o subestimar (-):")
for (obj, h), g in met.groupby(["objetivo", "horizonte_dias"], sort=False):
    print(f"\n{obj}, horizonte {h} d")
    print(g.drop(columns=["objetivo", "horizonte_dias"]).to_string(index=False))

print("\nPRUEBA DE ESTRES: MAYO 2026 (no usada para evaluar)")
filas = []
for col, nombre in OBJETIVOS.items():
    for h in HORIZONTES:
        p = pred_all[(col, h)][elegido[(col, h)]]
        mayo = p.index[p.index >= ESTRES_DESDE]
        real = d[col].reindex(mayo)
        filas.append({"objetivo": nombre, "horizonte_dias": h, "metodo_elegido": elegido[(col, h)],
                      "real_promedio": round(real.mean(), 1), "pronostico_promedio": round(p.reindex(mayo).mean(), 1),
                      "sesgo_%": round(100 * (p.reindex(mayo).sum() - real.sum()) / real.sum(), 1)})
print(pd.DataFrame(filas).to_string(index=False))

# bandas del 80 % con los errores de los ultimos 60 dias CONOCIDOS al momento de pronosticar
filas = []
sal = pd.DataFrame(index=d.index[(d.index >= PRUEBA_DESDE) & (d.index <= FIN_DATOS)])
for col, nombre in OBJETIVOS.items():
    y = d[col]
    for h in HORIZONTES:
        p_all = pred_all[(col, h)][elegido[(col, h)]]
        razon = (y / p_all).dropna()
        lo, hi = [], []
        for t in sal.index:
            if t not in p_all.index:
                lo.append(np.nan); hi.append(np.nan); continue
            q = np.quantile(razon[:t - pd.Timedelta(days=h)].iloc[-VENTANA_BANDA:], [.10, .90])
            lo.append(q[0] * p_all[t]); hi.append(q[1] * p_all[t])
        sal[f"{col}_real"] = y.reindex(sal.index)
        sal[f"{col}_pronostico_h{h}"] = p_all.reindex(sal.index).round(1)
        sal[f"{col}_banda_baja_h{h}"] = np.round(lo, 1)
        sal[f"{col}_banda_alta_h{h}"] = np.round(hi, 1)
        for etiqueta, a, b in [("prueba ene-abr", PRUEBA_DESDE, PRUEBA_HASTA), ("mayo (estres)", ESTRES_DESDE, FIN_DATOS)]:
            s = sal[(sal.index >= a) & (sal.index <= b)]
            dentro = ((s[f"{col}_real"] >= s[f"{col}_banda_baja_h{h}"]) & (s[f"{col}_real"] <= s[f"{col}_banda_alta_h{h}"]))
            filas.append({"objetivo": nombre, "horizonte_dias": h, "periodo": etiqueta,
                          "cobertura_banda_80%": round(100 * dentro.mean(), 1)})
print("\nCOBERTURA de la banda del 80 % (lo ideal es cerca de 80):")
print(pd.DataFrame(filas).to_string(index=False))
sal.to_csv(TABLAS / "pronostico_diario_test.csv")

# pronostico a 1 dia de TODOS los dias con el metodo elegido (hasta 2025-12 es en muestra; desde 2026-01 es fuera de muestra).
# Lo usa src/dias_atipicos.py.
completo = pd.DataFrame({f"{c}_real": d[c] for c in OBJETIVOS})
for c in OBJETIVOS:
    completo[f"{c}_pronostico_h1"] = pred_all[(c, 1)][elegido[(c, 1)]]
completo.dropna().round(2).to_csv(TABLAS / "pronostico_diario_completo.csv")

# ----------------------------------------------------------------------
# 2b) Ingresos y llegadas por SEMANA
# ----------------------------------------------------------------------
titulo("2b. PRONOSTICO SEMANAL (suma de los pronosticos diarios a 7 dias, semanas completas lunes a domingo)")
filas = []
for col, nombre in OBJETIVOS.items():
    y = d[col]
    p = pred_all[(col, 7)][elegido[(col, 7)]]
    p = p[(p.index >= PRUEBA_DESDE) & (p.index <= PRUEBA_HASTA)]
    df = pd.DataFrame({"pron": p, "real": y.reindex(p.index)})
    df["semana"] = df.index.to_period("W-SUN")
    g = df.groupby("semana").agg(pron=("pron", "sum"), real=("real", "sum"), n=("pron", "size"))
    g = g[g.n == 7]
    ref = y.rolling(7).sum().shift(7).reindex([w.end_time.normalize() for w in g.index]).values
    filas.append({"objetivo": nombre, "semanas": len(g), "real_semanal_medio": round(g.real.mean(), 1),
                  "MAE_semanal": round((g.pron - g.real).abs().mean(), 1),
                  "WAPE_semanal_%": round(100 * (g.pron - g.real).abs().sum() / g.real.sum(), 1),
                  "WAPE_diario_%": round(metricas(df.real, df.pron)["WAPE_%"], 1),
                  "WAPE_semanal_semana_anterior_%": round(100 * np.abs(ref - g.real.values).sum() / g.real.sum(), 1)})
sem = pd.DataFrame(filas)
sem.to_csv(TABLAS / "pronostico_semanal_metricas.csv", index=False)
print(sem.to_string(index=False))
print("Lectura: el error diario de los ingresos es casi todo ruido de conteo; sumado por semana baja a la mitad o menos.")

# ----------------------------------------------------------------------
# 3) Alerta de dia congestionado (clasificador logistico)
# ----------------------------------------------------------------------
titulo("3. ALERTA: DIA CONGESTIONADO (llegadas > percentil 90 del mismo dia de la semana en las ultimas 12 semanas)")
y = d.llegadas
umbral = pd.concat([y.shift(7 * k) for k in range(1, SEMANAS_ALERTA + 1)], axis=1).quantile(.9, axis=1)
etiqueta_all = (y > umbral)
test_idx = d.index[(d.index >= PRUEBA_DESDE) & (d.index <= PRUEBA_HASTA)]
print(f"dias de prueba: {len(test_idx)} | dias congestionados segun la definicion: {int(etiqueta_all[test_idx].sum())} "
      f"({100 * etiqueta_all[test_idx].mean():.1f} %)")


def rasgos_alerta(pred, h, entr_fin):
    F = pd.concat([pd.Series(1.0, index=d.index, name="const"), DOW, d[["fest_habil"]].astype(float)], axis=1).reindex(pred.index)
    F["log_pron_sobre_umbral"] = np.log(pred / umbral.reindex(pred.index))
    F["sorpresa"] = sorpresa("llegadas", h, entr_fin).reindex(pred.index)
    F["cambio_de_nivel"] = np.log(y.rolling(7).mean().shift(h) / y.rolling(28).mean().shift(h)).reindex(pred.index)
    return F.dropna()


filas = []
for h in HORIZONTES:
    # validacion: clasificador entrenado antes de 2025-07; el corte maximiza F1 en 2025-07 a 2025-12
    pv = predicciones("llegadas", h, VALIDA_ENTRENA_HASTA, "2023-01-01", ENTRENA_HASTA)[elegido[("llegadas", h)]]
    Fv = rasgos_alerta(pv, h, VALIDA_ENTRENA_HASTA)
    iv = Fv.index.intersection(umbral.dropna().index)
    ent_v, val_v = iv[iv < VALIDA_DESDE], iv[iv >= VALIDA_DESDE]
    bv = logistic_fit(Fv.loc[ent_v].values, etiqueta_all[ent_v].values)
    pr_v = pd.Series(prob(bv, Fv.loc[val_v].values), index=val_v)
    mejor_f1, corte = -1, 0.3
    for c in np.arange(.15, .70, .05):
        a = pr_v >= c
        tp = (a & etiqueta_all[val_v]).sum()
        den = a.sum() + etiqueta_all[val_v].sum()
        f1 = 2 * tp / den if den else 0
        if f1 > mejor_f1:
            mejor_f1, corte = f1, round(c, 2)
    # prueba: clasificador entrenado hasta 2025-12
    pa = pred_all[("llegadas", h)][elegido[("llegadas", h)]]
    Fa = rasgos_alerta(pa, h, ENTRENA_HASTA)
    ia = Fa.index.intersection(umbral.dropna().index)
    bt = logistic_fit(Fa.loc[ia[ia <= ENTRENA_HASTA]].values, etiqueta_all[ia[ia <= ENTRENA_HASTA]].values)
    ti = ia[(ia >= PRUEBA_DESDE) & (ia <= PRUEBA_HASTA)]
    p_t = pd.Series(prob(bt, Fa.loc[ti].values), index=ti)
    etq = etiqueta_all[ti]
    base = (y.shift(7) / umbral).reindex(ti)
    filas.append({"horizonte_dias": h, "metodo": "clasificador logistico", "AUC": round(auc(etq, p_t), 3)})
    filas.append({"horizonte_dias": h, "metodo": "referencia: mismo dia de la semana anterior", "AUC": round(auc(etq, base), 3)})
    a = p_t >= corte
    tp = int((a & etq).sum())
    filas.append({"horizonte_dias": h, "metodo": f"alerta si probabilidad >= {corte} (corte elegido en validacion)",
                  "alertas": int(a.sum()), "aciertos": tp, "precision_%": round(100 * tp / max(a.sum(), 1), 1),
                  "deteccion_%": round(100 * tp / max(etq.sum(), 1), 1), "falsas_alarmas": int(a.sum()) - tp})
al = pd.DataFrame(filas)
al.to_csv(TABLAS / "pronostico_alerta.csv", index=False)
print(al.to_string(index=False))
print("(AUC: 0,5 = azar, 1 = perfecto. Precision = de las alertas, cuantas eran dias congestionados; "
      "deteccion = de los dias congestionados, cuantos se anticiparon.)")

# ----------------------------------------------------------------------
# 4) Pronostico por hora
# ----------------------------------------------------------------------
titulo("4. PRONOSTICO POR HORA (llegadas): pronostico diario elegido x forma horaria del dia de la semana")
hh = pd.read_csv(PROC / "serie_horaria.csv", parse_dates=["hora_inicio"]).set_index("hora_inicio").llegadas
hh = hh[(hh.index >= d.index.min()) & (hh.index < d.index.max() + pd.Timedelta(days=1))]
df_h = pd.DataFrame({"y": hh})
df_h["fecha"] = df_h.index.normalize()
df_h["dow"] = df_h.index.dayofweek
df_h["hora"] = df_h.index.hour
ent = df_h[df_h.fecha <= ENTRENA_HASTA]
forma = ent.assign(parte=ent.y / ent.groupby("fecha").y.transform("sum")).groupby(["dow", "hora"]).parte.mean()
pru = df_h[(df_h.fecha >= PRUEBA_DESDE) & (df_h.fecha <= PRUEBA_HASTA)].copy()
llave = pd.MultiIndex.from_frame(pru[["dow", "hora"]])
for h in HORIZONTES:
    dia_p = pred_all[("llegadas", h)][elegido[("llegadas", h)]]
    pru[f"modelo_h{h}"] = pru.fecha.map(dia_p) * llave.map(forma).values
pru["prom_dow_hora"] = llave.map(ent.groupby(["dow", "hora"]).y.mean()).values
pru["misma_hora_semana_anterior"] = df_h.y.shift(24 * 7).reindex(pru.index)
filas = [{"metodo": n, **metricas(pru.y, pru[c])} for n, c in
         [("promedio de dia x hora", "prom_dow_hora"), ("misma hora, semana anterior", "misma_hora_semana_anterior"),
          ("elegido x forma horaria, horizonte 1 d", "modelo_h1"), ("elegido x forma horaria, horizonte 7 d", "modelo_h7")]]
hor = pd.DataFrame(filas).round(2)
hor.to_csv(TABLAS / "pronostico_horario_metricas.csv", index=False)
print(f"horas de prueba: {len(pru)} | llegadas por hora: media {pru.y.mean():.1f}")
print(hor.to_string(index=False))

# ----------------------------------------------------------------------
# 5) Grafico
# ----------------------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("\nmatplotlib no esta instalado: se omite el grafico")
else:
    SUPERFICIE, TINTA, TINTA2, REJILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e5e4df"
    AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
    fig, axs = plt.subplots(1, 3, figsize=(15.5, 4.9), facecolor=SUPERFICIE, gridspec_kw={"width_ratios": [1.5, 1, 1]})

    def estilo(ax):
        ax.set_facecolor(SUPERFICIE)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(REJILLA)
        ax.tick_params(colors=TINTA2, labelsize=9)
        ax.grid(axis="y", color=REJILLA, linewidth=.8)
        ax.set_axisbelow(True)

    ax = axs[0]
    s = sal.dropna(subset=["llegadas_pronostico_h1"])
    ax.axvspan(pd.Timestamp(ESTRES_DESDE), s.index.max(), color=REJILLA, alpha=.6, linewidth=0)
    ax.text(pd.Timestamp(ESTRES_DESDE) + pd.Timedelta(days=1), 20, "mayo:\ncaida no\nanticipada", fontsize=8, color=TINTA2)
    ax.fill_between(s.index, s.llegadas_banda_baja_h1, s.llegadas_banda_alta_h1, color=AZUL, alpha=.15, linewidth=0,
                    label="banda del 80 %")
    ax.plot(s.llegadas_real, color=TINTA2, linewidth=1.2, label="real")
    ax.plot(s.llegadas_pronostico_h1, color=AZUL, linewidth=2, label="pronostico a 1 dia")
    ax.set_title("Llegadas por dia en 2026", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    ax.set_ylabel("llegadas por dia", color=TINTA2, fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=TINTA2, loc="lower left", ncol=3)
    ax.set_ylim(0, None)
    estilo(ax)

    ax = axs[1]
    g = met[met.horizonte_dias == 1]
    cortos = {"promedio del dia de la semana": "promedio\ndia sem.", "mismo dia de la semana anterior": "semana\nanterior",
              "dia de la semana x nivel reciente": "dia sem. x\nnivel", "Poisson: calendario + nivel + sorpresa": "Poisson\n+ sorpresa"}
    metodos = list(cortos)
    colores = {m_: c_ for m_, c_ in zip(metodos, [REJILLA, TINTA2, AQUA, AZUL])}
    ancho = .38
    for k, obj in enumerate(["llegadas por dia", "ingresos a cama por dia"]):
        gg = g[g.objetivo == obj].set_index("metodo").loc[metodos]
        v = gg["WAPE_%"].values
        pos = np.arange(len(metodos)) + (k - .5) * ancho
        ax.bar(pos, v, width=ancho * .9, color=[colores[m_] for m_ in metodos], alpha=1.0 if k == 0 else .55)
        for p_, val in zip(pos, v):
            ax.text(p_, val + .4, f"{val:.0f}", ha="center", fontsize=8, color=TINTA)
    ax.set_xticks(np.arange(len(metodos)))
    ax.set_xticklabels([cortos[m_] for m_ in metodos], fontsize=8)
    ax.set_ylabel("error relativo, WAPE % (menos es mejor)", color=TINTA2, fontsize=9)
    ax.set_title("Error a 1 dia: llegadas (oscuro), ingresos (claro)", loc="left", color=TINTA, fontsize=10,
                 fontweight="bold")
    estilo(ax)

    ax = axs[2]
    base_ = tend.iloc[:6].mean()
    idx = pd.to_datetime(tend.index)
    for col, color, et in [("llegadas", AZUL, "llegadas"), ("ingresos_a_cama", AQUA, "ingresos a cama")]:
        ax.plot(idx, 100 * tend[col] / base_[col], color=color, linewidth=2, label=et)
    ax.axhline(100, color=TINTA2, linewidth=1, linestyle=(0, (4, 3)))
    ax.set_xticks([pd.Timestamp(f"{a}-01-01") for a in range(2023, 2027)])
    ax.set_xticklabels(["2023", "2024", "2025", "2026"])
    ax.set_ylabel("indice (primeros 6 meses = 100)", color=TINTA2, fontsize=9)
    ax.set_title("Tendencia mensual", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=TINTA2, loc="lower left")
    estilo(ax)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.text(.01, .01, "Validacion temporal: entrenado hasta 2025-12, probado en 2026-01 a 2026-04; mayo se reporta aparte. "
             "Las llegadas incluyen algunas replicas (>= 4 %). Es un pronostico de calendario y nivel.",
             color=TINTA2, fontsize=8)
    fig.savefig(GRAFICOS / "pronostico_demanda.png", dpi=150, facecolor=SUPERFICIE)
    print("\nguardado: resultados/graficos/pronostico_demanda.png")
