"""
severidad_labs.py  -  version 2 (11-nov-2026)
Exploracion A8 punto 10: ¿una SEVERIDAD sacada del texto de los laboratorios de las primeras 6 h mejora lo que ya sabemos predecir?
(v2, 11-nov: CRUCE POR PERSONA REAL. La v1 (8-nov) cruzaba los valores por visita (sev_*.csv) y solo llevaba a la visita raiz las copias de la MISMA persona: en las
 estancias gemelas mezclaba los laboratorios de las dos personas y dejaba sin laboratorio al 60 % de las estancias. Ahora los valores vienen por visita Y persona
 (sevp_*.csv, sql/severidad_labs_6h_persona.sql), TODAS las copias se llevan a su visita raiz y se queda solo lo de la persona real de la estancia (persona_real de
 tabla_episodios o, si no se identifico, la del registro conservado); en los episodios sin cama, la persona del propio registro. Cobertura de las estancias del
 periodo confiable: 40 % -> 52 %. La seccion 0 compara los dos cruces; las secciones 1 a 4 son las de la v1 con el cruce nuevo.)

METODO  Valores extraidos con expresiones regulares (leucocitos, hemoglobina, creatinina, BUN, lactato, potasio, sodio, troponina I, PCR) entre la primera etapa y las
  6 h siguientes. Banderas con puntos de corte clinicos comunes (BANDERAS_LAB de comparar_estimadores.py) y una puntuacion = numero de banderas.
  1. Entre episodios con atencion y laboratorio en las primeras 6 h: ¿cuanto sube la hospitalizacion con las banderas? (logistica, entrenada hasta 2025-06 y probada desde 2025-07).
  2. Entre estancias hospitalizadas con laboratorio: ¿cuanto R2 anade la puntuacion a la espera de cama y a la estancia, sobre edad, sexo, tipo de visita, hora y ano?
  3. Prueba sencilla para A6 (gradiente con las variables basicas); la prueba dentro del estimador completo esta en src/prueba_banderas_persona.py.
  4. Efecto de cada bandera sobre la espera (esperas >= 6 h), controlando edad, sexo, tipo de visita, franja y ano.
LIMITES  Solo hay valor si le pidieron el examen (los pacientes con laboratorio no son todos); la decision de pedirlo ya informa la gravedad. Los puntos de corte son genericos (sin
  separar edad ni sexo; un clinico debe validarlos). Asociacion, no causa. Los laboratorios de las primeras 6 h no se conocen "al llegar": sirven para un estimador que se
  actualiza a las pocas horas (A6), no para la entrada.
ENTRADAS  datos/crudos/consultas/sevp_*_6h_*.csv (y sev_*_6h_*.csv, solo para la comparacion de la seccion 0), datos/procesados/tabla_episodios.parquet y copias.csv
SALIDAS   resultados/tablas/severidad_labs_*.csv y severidad_labs_resumen.txt
COMO CORRERLO  python3 src/severidad_labs.py   (1-2 min)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402

TABLAS = ce.TABLAS
nb = list(ce.BANDERAS_LAB)
LINEAS = []


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def roc_auc_score(y, p):
    r = rankdata(p)
    n1 = y.sum()
    n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def valores_por_visita_y_persona():
    """sevp_*.csv: una fila por visita y persona; las visitas copia se llevan a su raiz (todas) y se agrega por (raiz, persona)."""
    hem, qui = ce._archivos_lab("sevp")
    if hem is None:
        raise SystemExit("faltan sevp_hemograma_6h_*.csv / sevp_quimica_6h_*.csv (sql/severidad_labs_6h_persona.sql) en datos/crudos/consultas")
    s = pd.concat([pd.read_csv(f) for f in hem]).merge(pd.concat([pd.read_csv(f) for f in qui]), on=["visit_occurrence_id", "person_id"], how="outer")
    cop = pd.read_csv(ce.PROC / "copias.csv", usecols=["visit_occurrence_id", "raiz_id"])
    s["visit_occurrence_id"] = s.visit_occurrence_id.map(cop.set_index("visit_occurrence_id").raiz_id).fillna(s.visit_occurrence_id).astype("int64")
    return s.groupby(["visit_occurrence_id", "person_id"], as_index=False).agg(ce.AGG_LAB)


def con_banderas(df):
    b = ce.banderas_desde_valores(df).astype(bool)
    out = pd.concat([df, b], axis=1)
    out["puntos"] = b.sum(axis=1)
    return out


def main():
    TABLAS.mkdir(parents=True, exist_ok=True)
    T = pd.read_parquet(ce.PROC / "tabla_episodios.parquet")
    t = T[(T.ini >= "2023-02-01") & (T.ini < "2026-04-10") & (~T.hospitalizado | T.estancia_unica.fillna(False).astype(bool))]
    t = t[~((t.ruta_simple == "ER") & (t.estado == "sin_actividad"))]

    # ---- 0. los dos cruces, sobre las estancias unicas del periodo confiable
    decir("SEVERIDAD DESDE LOS LABORATORIOS DE LAS PRIMERAS 6 H (v2: cruce por persona real)")
    est = set(t[t.hospitalizado & t.estancia_id.notna()].estancia_id.astype(int))
    N = ce.valores_lab_por_estancia(T, True)
    V = ce.valores_lab_por_estancia(T, False)
    f0 = [("estancias unicas del periodo confiable", len(est), len(est))]
    if V is not None:
        sn, sv = set(N.index) & est, set(V.index) & est
        bn, bv = ce.banderas_desde_valores(N.loc[sorted(sn)]), ce.banderas_desde_valores(V.loc[sorted(sv)])
        comunes = sorted(sn & sv)
        f0 += [("con algun valor de laboratorio en las 6 h", len(sv), len(sn)), ("solo en ese cruce", len(sv - sn), len(sn - sv)),
               ("en los dos cruces", len(comunes), len(comunes)), ("en los dos cruces, con alguna bandera distinta", int((bn.loc[comunes] != bv.loc[comunes]).any(axis=1).sum()), None)]
        f0 += [(f"bandera {n}", int(bv[n].sum()), int(bn[n].sum())) for n in nb]
        decir("\n0. CRUCE VIEJO (por visita, sin persona; copias solo de la misma persona) FRENTE AL NUEVO (por visita y persona real; todas las copias a su raiz)")
    else:
        decir("\n0. (no estan los sev_*.csv viejos: no se compara el cruce)")
    t0 = pd.DataFrame(f0, columns=["medida", "cruce_viejo_sev", "cruce_nuevo_sevp"])
    decir(t0.to_string(index=False))
    t0.to_csv(TABLAS / "severidad_labs_cruce_persona.csv", index=False)

    # ---- 1. episodios con atencion y laboratorio: hospitalizacion
    s = valores_por_visita_y_persona()
    ep = t[t.episodio == 0].copy()
    ep["real"] = ep.persona_real.fillna(ep.person_id).astype("int64")
    e = ep.merge(s.rename(columns={"person_id": "persona_lab"}), on="visit_occurrence_id", how="inner")
    e = e[e.persona_lab == e.real].copy()
    e = con_banderas(e)
    e = e[e.edad.between(0, 105) & e.sexo.notna()].copy()
    e["hosp"] = e.hospitalizado.astype(int)
    e["menor15"] = (e.edad < 15).astype(int)
    decir(f"\n1. EPISODIOS con atencion y laboratorio extraido en 6 h (de la propia persona): {len(e):,}; hospitalizados {e.hosp.mean():.1%}")
    decir("cobertura (episodios con el valor): " + str({c: int(e[c].notna().sum()) for c in ["leuc_max", "hb_min", "creat_max", "bun_max", "lactato_max", "k_max", "na_min", "troponina_max", "pcr_max"]}))
    decir("\nHospitalizacion segun puntos de severidad:")
    tp = e.assign(p=e.puntos.clip(upper=3)).groupby("p").agg(n=("hosp", "size"), hosp_pct=("hosp", lambda x: 100 * x.mean())).round(1)
    decir(tp.to_string())
    tp.to_csv(TABLAS / "severidad_labs_hospitalizacion_por_puntos.csv")
    bf = pd.DataFrame({n: {"n_con_bandera": int(e[n].sum()), "hosp_pct_con": round(100 * e.loc[e[n], "hosp"].mean(), 1),
                           "hosp_pct_sin": round(100 * e.loc[~e[n], "hosp"].mean(), 1)} for n in nb}).T
    decir("\npor bandera:\n" + bf.to_string())
    bf.to_csv(TABLAS / "severidad_labs_por_bandera.csv")

    e["tipo"] = e.tipo_visita.astype(str)
    X0 = pd.get_dummies(e[["edad", "menor15", "tipo", "hora"]], columns=["tipo"], drop_first=True).astype(float)
    X0["sexo_f"] = (e.sexo.astype(str).str.upper().str[0] == "F").astype(float)
    X1 = X0.join(e[nb].astype(float))
    tr = (e.ini < "2025-07-01").values
    res = []
    for nombre, X in [("sin laboratorio (edad, sexo, tipo, hora)", X0), ("+ banderas", X1)]:
        mu, sd = X[tr].mean(), X[tr].std().replace(0, 1)
        m = sm.Logit(e.hosp[tr].values, sm.add_constant((X[tr] - mu) / sd)).fit(disp=0, method="bfgs", maxiter=500)
        pr = m.predict(sm.add_constant((X[~tr] - mu) / sd, has_constant="add"))
        res.append({"modelo": nombre, "AUC prueba (2025-07 a 2026-04)": round(roc_auc_score(e.hosp[~tr].values, np.asarray(pr)), 3)})
    r1 = pd.DataFrame(res)
    decir("\nHOSPITALIZACION (logistica):\n" + r1.to_string(index=False))
    r1.to_csv(TABLAS / "severidad_labs_auc_hospitalizacion.csv", index=False)

    # ---- 2. R2 sobre espera y estancia entre estancias hospitalizadas (valores de la persona real de la estancia)
    h = t[t.hospitalizado & t.estancia_id.notna()].copy()
    h["estancia_id"] = h.estancia_id.astype(int)
    sh = con_banderas(N.reset_index())
    h = h.merge(sh, on="estancia_id", how="inner")
    h = h[h.edad.between(0, 105) & h.sexo.notna() & h.espera_cama_h.notna() & (h.fin_hosp_est > h.ini_hosp_est)].copy()
    h["estancia_h"] = (h.fin_hosp_est - h.ini_hosp_est).dt.total_seconds() / 3600
    h = h[h.estancia_h > 0]
    h["ly_esp"], h["ly_est"] = np.log1p(h.espera_cama_h), np.log1p(h.estancia_h)
    h["pt"] = h.puntos.clip(upper=3)
    h["anio"] = h.anio.astype(int)
    h_todas = h.copy()
    decir(f"\n2. ESTANCIAS hospitalizadas con laboratorio extraido (persona real): {len(h):,}")
    base = "edad + C(sexo) + C(tipo_visita) + C(franja) + C(anio)"
    out = []
    for y, nombre in [("ly_esp", "espera de cama (solo espera >= 6 h)"), ("ly_est", "estancia en cama")]:
        h = h_todas[h_todas.espera_cama_h >= 6] if y == "ly_esp" else h_todas
        r0 = smf.ols(f"{y} ~ {base}", h).fit().rsquared
        r1_ = smf.ols(f"{y} ~ {base} + C(pt)", h).fit().rsquared
        r2 = smf.ols(f"{y} ~ {base} + " + " + ".join(nb), h).fit().rsquared
        out.append({"resultado": nombre, "R2 base": round(100 * r0, 1), "R2 + puntos": round(100 * r1_, 1), "R2 + banderas": round(100 * r2, 1)})
    r2 = pd.DataFrame(out)
    decir(r2.to_string(index=False))
    r2.to_csv(TABLAS / "severidad_labs_r2.csv", index=False)
    coef = smf.ols(f"ly_est ~ {base} + C(pt)", h_todas).fit().params.filter(like="pt")
    decir("efecto de los puntos sobre la estancia (% vs 0 puntos): " + str({k: round(100 * (np.exp(v) - 1), 1) for k, v in coef.items() if k != "Intercept"}))
    h = h_todas[h_todas.espera_cama_h >= 6]
    decir(f"estancias con espera >= 6 h: {len(h):,}")
    coef = smf.ols(f"ly_esp ~ {base} + C(pt)", h).fit().params.filter(like="pt")
    decir("efecto de los puntos sobre la espera (% vs 0 puntos): " + str({k: round(100 * (np.exp(v) - 1), 1) for k, v in coef.items() if k != "Intercept"}))

    # ---- 3. prueba sencilla para A6 (la prueba dentro del estimador completo: src/prueba_banderas_persona.py)
    a6 = h_todas[h_todas.espera_cama_h > 6].copy()
    a6["resta"] = np.log1p(a6.espera_cama_h - 6)
    a6["sexo_f"] = (a6.sexo.astype(str).str.upper().str[0] == "M").astype(float)
    base_cols = ["edad", "sexo_f", "hora", "dia_semana_num", "ocup_hosp", "llegadas_6h_previas"]
    a6["tipo_cod"] = a6.tipo_visita.astype("category").cat.codes
    base_cols.append("tipo_cod")
    tr6 = (a6.ini < "2025-07-01").values
    decir(f"\n3. PRUEBA SENCILLA PARA A6: {len(a6):,} estancias con espera > 6 h (entrenamiento {tr6.sum():,}, prueba {(~tr6).sum():,})")
    rng = np.random.default_rng(7)
    errs = {}
    for nombre, cols in [("sin laboratorio", base_cols), ("+ banderas", base_cols + nb), ("+ puntos", base_cols + ["puntos"])]:
        X = a6[cols].astype(float)
        m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=40, random_state=7).fit(X[tr6], a6.resta[tr6])
        errs[nombre] = (a6.resta[~tr6].values - m.predict(X[~tr6])) ** 2
    y = a6.resta[~tr6].values
    filas = []
    for nombre, e2 in errs.items():
        r2 = 1 - e2.sum() / ((y - a6.resta[tr6].mean()) ** 2).sum()
        dd = e2 - errs["sin laboratorio"]
        bs = [dd[rng.integers(0, len(dd), len(dd))].mean() for _ in range(1000)]
        filas.append({"modelo": nombre, "R2 en prueba (vs media del entrenamiento)": round(r2, 4), "cambio del error cuadratico medio": round(dd.mean(), 4),
                      "IC95 bajo": round(np.percentile(bs, 2.5), 4), "IC95 alto": round(np.percentile(bs, 97.5), 4)})
    r3 = pd.DataFrame(filas)
    decir(r3.to_string(index=False))
    r3.to_csv(TABLAS / "severidad_labs_prueba_a6.csv", index=False)

    # ---- 4. efecto de cada bandera sobre la espera (esperas >= 6 h)
    h = h_todas[h_todas.espera_cama_h >= 6]
    ajuste = smf.ols("ly_esp ~ " + base + " + " + " + ".join(f"{n}.astype(int)" for n in nb), h).fit(cov_type="HC1")
    ef = pd.DataFrame({"efecto_pct": [round(100 * (np.exp(ajuste.params[f"{n}.astype(int)"]) - 1), 1) for n in nb],
                       "ic95_bajo": [round(100 * (np.exp(ajuste.conf_int().loc[f"{n}.astype(int)", 0]) - 1), 1) for n in nb],
                       "ic95_alto": [round(100 * (np.exp(ajuste.conf_int().loc[f"{n}.astype(int)", 1]) - 1), 1) for n in nb],
                       "estancias_con_bandera": [int(h[n].sum()) for n in nb]}, index=nb)
    decir("\n4. EFECTO DE CADA BANDERA SOBRE LA ESPERA DE CAMA (esperas >= 6 h; % frente a no tenerla, controlando edad, sexo, tipo, franja y ano):\n" + ef.to_string())
    ef.to_csv(TABLAS / "severidad_labs_efecto_por_bandera_en_la_espera.csv")
    (TABLAS / "severidad_labs_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    main()
