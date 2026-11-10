"""
estimador_desde_cero.py  -  version 1 (8-nov-2026)
Tarea A6: un estimador de la espera de cama construido DESDE CERO, independiente del estimador actual (tiempo restante por hora,
estimador_tiempo_restante.py), para comprobar si otro camino llega mas lejos. Solo comparte con el actual la limpieza de los datos (tabla de episodios).

QUE CAMBIA FRENTE AL ACTUAL
  - Otra familia de modelos: en vez de estimar la probabilidad hora por hora, se estima directamente la espera que falta:
      A. LightGBM con regresion por cuantiles (un modelo por percentil 25, 50, 75 y 90 sobre el logaritmo de la espera).
      B. XGBoost con un modelo de tiempo de falla acelerado (AFT): el logaritmo de la espera sigue una distribucion normal cuya media depende del paciente.
      C. La combinacion de A y B (promedio de los percentiles en escala logaritmica).
  - Otras variables: la EDAD EN AÑOS (no en grupos), y todo lo que se conoce en ese momento: sexo, tipo de visita, hora del reloj, dia de la semana, mes,
    festivo, camas ocupadas de su zona, pacientes en urgencias y llegadas de las 6 y 24 h previas al llegar, historial de hospitalizaciones y de visitas a
    urgencias, y el recorrido en urgencias de esta visita hasta ese momento.
  - Ajustes elegidos con una validacion temporal propia: entrenar con feb-2023 a dic-2024 y validar con ene a jun-2025 (sin mirar la prueba).
LA PRUEBA  la misma de siempre: modelos finales entrenados con feb-2023 a jun-2025 y probados con jul-2025 a 9-abr-2026, al llegar y a las 6 y 12 h de espera.
  Se compara con el estimador actual entrenado con el mismo periodo (diferencia pareada con intervalo del 95 %, bootstrap por semanas).

ENTRADAS  tabla_episodios.parquet (HUN_PROCESADOS); visit_detail.csv y procedimientos_por_estancia.csv (HUN_CRUDOS)
SALIDAS   HUN_TABLAS/estimador_desde_cero.csv
COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... HUN_CRUDOS=... python3 src/estimador_desde_cero.py   (~10 min)
"""
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402

Q = ce.Q
Z = norm.ppf(Q)
VALIDACION_DESDE = pd.Timestamp("2025-01-01")
H1 = np.timedelta64(1, "h")
CATEGORICAS = ["tipo_cod", "dia_semana", "dx_previo_cod", "anterior_ruta_cod"]


# ----------------------------------------------------------------------
# 1) Variables: una fila por paciente, con lo que se sabe a las 'desde' horas de espera
# ----------------------------------------------------------------------
def variables(s, rejilla, estado, desde):
    t = s.ini_est.to_numpy() + desde * H1
    reloj = pd.DatetimeIndex(t)
    k = np.clip(((t - rejilla[0]) // H1).astype(int), 0, len(rejilla) - 1)
    ninos = s.zona.to_numpy() == "ninos"
    X = pd.DataFrame({
        "edad": s.edad.to_numpy(float), "sexo_cod": s.sexo_cod.to_numpy(), "tipo_cod": s.tipo_cod.to_numpy(),
        "hora_reloj": reloj.hour + reloj.minute / 60, "hora_llegada": s.ini_est.dt.hour.to_numpy() + s.ini_est.dt.minute.to_numpy() / 60,
        "dia_semana": reloj.dayofweek, "mes": reloj.month, "festivo": s.festivo.astype(float).to_numpy(), "dia_no_habil": s.dia_no_habil.astype(float).to_numpy(),
        "ocup_zona": np.where(ninos, estado["ninos"]["ocup"][k], estado["adultos"]["ocup"][k]), "zona_ninos": ninos.astype(int),
        "ocup_urgencias_llegada": s.ocup_tu.to_numpy(float), "llegadas_6h": s.llegadas_6h_previas.to_numpy(float), "llegadas_24h": s.llegadas_24h_previas.to_numpy(float),
        "espera_prev_h": s.espera_prev_h.to_numpy(float), "estancia_prev_h": s.estancia_prev_h.to_numpy(float), "n_hosp_previas": s.n_hosp_previas.to_numpy(float),
        "dias_desde_hosp": s.dias_desde_hosp.to_numpy(float), "dx_previo_cod": s.dx_previo_cod.to_numpy(float),
        "n_episodios_previos": s.n_episodios_previos.to_numpy(float), "dias_desde_anterior": s.dias_desde_anterior.to_numpy(float),
        "reingreso_72h": s.reingreso_72h.astype(float).to_numpy(),
        "anterior_ruta_cod": s.anterior_ruta.map({"TU": 0, "TU > HOSP": 1, "ER": 2}).where(s.anterior_ruta.isna() | s.anterior_ruta.isin(["TU", "TU > HOSP", "ER"]), 3).to_numpy(float),
    })
    vacio = (np.array([]), np.array([]), np.array([]))
    rec = [ce.recorrido_paciente(*ce.ETAPAS.get(c, vacio), np.array([float(desde)]), np.array([float(desde)])) for c in s.clave]
    for c in ce.REC:
        X[c] = [r[c][0] for r in rec]
    return X


def objetivo(s, desde):
    return np.log1p(np.minimum(s.espera_cama_h.to_numpy() - desde, ce.MAX_H))


# ----------------------------------------------------------------------
# 2) Modelos
# ----------------------------------------------------------------------
def lgb_cuantiles(Xa, ya, Xv=None, yv=None, hojas=31, rondas=None):
    """Un modelo por percentil. Si hay validacion, devuelve tambien el numero de rondas elegido por parada temprana."""
    modelos, mejores = [], []
    for j, q in enumerate(Q):
        params = dict(objective="quantile", alpha=q, learning_rate=0.03, num_leaves=hojas, min_data_in_leaf=60, feature_fraction=0.8,
                      bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, verbose=-1, seed=ce.SEMILLA)
        da = lgb.Dataset(Xa, ya, categorical_feature=[c for c in CATEGORICAS if c in Xa.columns], free_raw_data=False)
        if Xv is not None:
            dv = lgb.Dataset(Xv, yv, reference=da)
            m = lgb.train(params, da, num_boost_round=3000, valid_sets=[dv], callbacks=[lgb.early_stopping(150, verbose=False)])
            mejores.append(m.best_iteration)
        else:
            m = lgb.train(params, da, num_boost_round=rondas[j])
        modelos.append(m)
    return modelos, mejores


def lgb_predecir(modelos, X):
    p = np.column_stack([m.predict(X, num_iteration=m.best_iteration or None) for m in modelos])
    return np.sort(p, axis=1)                                            # percentiles ordenados (log)


def xgb_aft(Xa, ya, Xv=None, yv=None, sigma=1.0, prof=5, rondas=None):
    params = dict(objective="survival:aft", eval_metric="aft-nloglik", aft_loss_distribution="normal", aft_loss_distribution_scale=sigma,
                  learning_rate=0.03, max_depth=prof, min_child_weight=20, subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, seed=ce.SEMILLA,
                  tree_method="hist")
    def dm(X, y):
        d = xgb.DMatrix(X)
        d.set_float_info("label_lower_bound", np.exp(y))                # sin censura: la espera se conoce
        d.set_float_info("label_upper_bound", np.exp(y))
        return d
    da = dm(Xa, ya)
    if Xv is not None:
        dv = dm(Xv, yv)
        m = xgb.train(params, da, num_boost_round=3000, evals=[(dv, "v")], early_stopping_rounds=150, verbose_eval=False)
        return m, m.best_iteration + 1
    return xgb.train(params, da, num_boost_round=rondas), rondas


def xgb_predecir(m, X, sigma):
    mu = np.log(m.predict(xgb.DMatrix(X)))                              # la prediccion es exp(mu)
    return mu[:, None] + sigma * Z[None, :]                             # percentiles (log) de la normal


def perdida_log(y_h, pred_log):
    """Perdida de cuantiles en horas (para elegir ajustes en la validacion)."""
    return ce.perdida(y_h, np.expm1(pred_log))


# ----------------------------------------------------------------------
# 3) Ajuste con validacion temporal propia, entrenamiento final y prueba
# ----------------------------------------------------------------------
def ajustar_y_predecir(tr, te, rejilla, estado, desde):
    a = tr[(tr.espera_cama_h > desde) & (tr.ini_est < VALIDACION_DESDE)].reset_index(drop=True)
    v = tr[(tr.espera_cama_h > desde) & (tr.ini_est >= VALIDACION_DESDE)].reset_index(drop=True)
    f = tr[tr.espera_cama_h > desde].reset_index(drop=True)
    Xa, Xv, Xf, Xt = (variables(s, rejilla, estado, desde) for s in (a, v, f, te))
    ya, yv, yf = objetivo(a, desde), objetivo(v, desde), objetivo(f, desde)
    yv_h = np.expm1(yv)
    # A. LightGBM: tamaño de hoja
    mejor_lgb = None
    for hojas in [15, 31, 63]:
        mods, rondas = lgb_cuantiles(Xa, ya, Xv, yv, hojas=hojas)
        perd = perdida_log(yv_h, lgb_predecir(mods, Xv))
        if mejor_lgb is None or perd < mejor_lgb[0]:
            mejor_lgb = (perd, hojas, rondas)
    # B. XGBoost AFT: escala de la normal y profundidad
    mejor_xgb = None
    for sigma in [0.8, 1.0, 1.2, 1.4]:
        for prof in [4, 6]:
            m, r = xgb_aft(Xa, ya, Xv, yv, sigma=sigma, prof=prof)
            perd = perdida_log(yv_h, xgb_predecir(m, Xv, sigma))
            if mejor_xgb is None or perd < mejor_xgb[0]:
                mejor_xgb = (perd, sigma, prof, r)
    print(f"  {desde} h | LightGBM: hojas {mejor_lgb[1]}, rondas {mejor_lgb[2]} | XGBoost AFT: sigma {mejor_xgb[1]}, profundidad {mejor_xgb[2]}, rondas {mejor_xgb[3]}", flush=True)
    # modelos finales con todo el entrenamiento y los ajustes elegidos (rondas escaladas al tamaño)
    escala = len(f) / len(a)
    mods, _ = lgb_cuantiles(Xf, yf, hojas=mejor_lgb[1], rondas=[max(50, int(r * escala)) for r in mejor_lgb[2]])
    pa = lgb_predecir(mods, Xt)
    mx, _ = xgb_aft(Xf, yf, sigma=mejor_xgb[1], prof=mejor_xgb[2], rondas=max(50, int(mejor_xgb[3] * escala)))
    pb = xgb_predecir(mx, Xt, mejor_xgb[1])
    return {"A. LightGBM por cuantiles": np.expm1(pa), "B. XGBoost AFT": np.expm1(pb), "C. combinacion A + B": np.expm1((pa + pb) / 2)}


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    d, h, rejilla, estado = ce.preparar()
    tr, te = d[d.ini_est < ce.CORTE].reset_index(drop=True), d[d.ini_est >= ce.CORTE].reset_index(drop=True)
    filas = []
    for desde in [0, 6, 12]:
        sub = te[te.espera_cama_h > desde].reset_index(drop=True)
        y = np.minimum(sub.espera_cama_h.to_numpy() - desde, ce.MAX_H)
        sem = sub.ini_est.dt.to_period("W").astype(str).to_numpy()
        lg = ce.perdida_por_caso(y, ce.referencias(tr, sub, desde)[0])
        actual = (ce.entrenar_landmark(tr, rejilla, estado, desde, vida_media_dias=182) if desde < ce.HORAS_RECORRIDO
                  else ce.entrenar_m1(tr, rejilla, estado, ce.COLS_M1_BASE + ce.HIST, vida_media_dias=182))
        preds = {"estimador actual (tiempo restante)": ce.predecir_m1(actual, sub, rejilla, estado, desde), **ajustar_y_predecir(tr, sub, rejilla, estado, desde)}
        l_act = ce.perdida_por_caso(y, preds["estimador actual (tiempo restante)"])
        for nombre, p in preds.items():
            lp = ce.perdida_por_caso(y, p)
            lo, hi = ce.intervalo_mejora(sem, lp, lg)
            fila = {"horas_esperando": desde, "metodo": nombre, "mejora_vs_general_pct": round(100 * (1 - lp.mean() / lg.mean()), 1), "ic95": f"{lo:.1f} a {hi:.1f}",
                    "error_promedio_mediana_h": round(np.abs(y - p[:, 1]).mean(), 1), "error_tipico_mediana_h": round(np.median(np.abs(y - p[:, 1])), 1),
                    **{f"debajo_p{int(q * 100)}": round(100 * np.mean(y <= p[:, j]), 1) for j, q in enumerate(Q)}}
            if not nombre.startswith("estimador actual"):
                dlo, dhi = ce.intervalo_mejora(sem, lp, l_act)
                fila["vs_actual_pct"] = round(100 * (1 - lp.mean() / l_act.mean()), 1)
                fila["vs_actual_ic95"] = f"{dlo:.1f} a {dhi:.1f}"
            filas.append(fila)
        print(pd.DataFrame([f for f in filas if f["horas_esperando"] == desde]).to_string(index=False), flush=True)
    pd.DataFrame(filas).to_csv(ce.TABLAS / "estimador_desde_cero.csv", index=False)
