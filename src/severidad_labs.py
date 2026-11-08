"""
severidad_labs.py  -  version 1 (8-nov-2026)
Exploracion A8 punto 10: ¿una SEVERIDAD sacada del texto de los laboratorios de las primeras 6 h mejora lo que ya sabemos predecir?

METODO  Valores extraidos con expresiones regulares (sql/severidad_labs_6h.sql: leucocitos, hemoglobina, creatinina, BUN, lactato, potasio, sodio, troponina I, PCR)
  entre la primera etapa y las 6 h siguientes. Banderas con puntos de corte clinicos comunes (ver BANDERAS) y una puntuacion = numero de banderas.
  1. Entre episodios con atencion y laboratorio en las primeras 6 h: ¿cuanto sube la hospitalizacion con las banderas? (logistica, entrenada hasta 2025-06 y probada desde 2025-07).
  2. Entre estancias hospitalizadas con laboratorio: ¿cuanto R2 anade la puntuacion a la espera de cama y a la estancia, sobre edad, sexo, tipo de visita, hora y ano?
LIMITES  Solo hay valor si le pidieron el examen (los pacientes con laboratorio no son todos); la decision de pedirlo ya informa la gravedad. Los puntos de corte son genericos (sin
  separar edad ni sexo; un clinico debe validarlos). En estancias gemelas se toma el maximo de los registros de la estancia (los laboratorios pueden ser de la otra persona del par).
  Asociacion, no causa. Los laboratorios de las primeras 6 h no se conocen "al llegar": sirven para un estimador que se actualiza a las pocas horas (A6), no para la entrada.
ENTRADAS  datos/crudos/consultas/sev_*_6h_*.csv, datos/procesados/tabla_episodios.parquet     SALIDAS  resultados/tablas/severidad_labs_*.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm
from scipy.stats import rankdata

def roc_auc_score(y, p):
    r = rankdata(p); n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


RAIZ = Path(__file__).resolve().parent.parent
CONSULTAS, TABLAS = RAIZ / "datos/crudos/consultas", RAIZ / "resultados/tablas"
BANDERAS = {   # nombre: (columna, funcion de anormalidad)
    "leucocitos_alt": ("leuc_max", lambda s: s > 12), "leucopenia": ("leuc_min", lambda s: s < 4), "anemia": ("hb_min", lambda s: s < 10),
    "creatinina_alta": ("creat_max", lambda s: s > 1.5), "bun_alto": ("bun_max", lambda s: s > 40), "lactato_alto": ("lactato_max", lambda s: s > 2.2),
    "potasio_alt": ("k_max", lambda s: s > 5.5), "sodio_bajo": ("na_min", lambda s: s < 130), "sodio_alto": ("na_max", lambda s: s > 150),
    "troponina_alta": ("troponina_max", lambda s: s > 1.0), "pcr_alta": ("pcr_max", lambda s: s > 50)}
hem = pd.concat([pd.read_csv(f) for f in sorted(CONSULTAS.glob("sev_hemograma_6h_*.csv"))])
qui = pd.concat([pd.read_csv(f) for f in sorted(CONSULTAS.glob("sev_quimica_6h_*.csv"))])
s = hem.merge(qui, on="visit_occurrence_id", how="outer")
# el 81 % de las visitas con laboratorio son copias: sus valores se pasan a la visita original solo si la copia es de la MISMA persona (igual que preparar_variables.py)
cop = pd.read_csv(RAIZ / "datos/procesados/copias.csv", usecols=["visit_occurrence_id", "raiz_id", "misma_persona"])
cop = cop[cop.misma_persona]
s["visit_occurrence_id"] = s.visit_occurrence_id.map(cop.set_index("visit_occurrence_id").raiz_id).fillna(s.visit_occurrence_id).astype("int64")
AGG = {"leuc_max": "max", "leuc_min": "min", "hb_min": "min", "creat_max": "max", "bun_max": "max", "lactato_max": "max", "k_max": "max", "k_min": "min",
       "na_max": "max", "na_min": "min", "troponina_max": "max", "pcr_max": "max"}
s = s.groupby("visit_occurrence_id").agg(AGG).reset_index()
for n, (col, f) in BANDERAS.items():
    s[n] = f(s[col]).fillna(False) & s[col].notna()
nb = list(BANDERAS)
s["puntos"] = s[nb].sum(axis=1)
print(f"visitas con algun valor extraido: {len(s):,}")
print("cobertura (visitas con el valor):", {c: int(s[c].notna().sum()) for c in ["leuc_max", "hb_min", "creat_max", "bun_max", "lactato_max", "k_max", "na_min", "troponina_max", "pcr_max"]})

t = pd.read_parquet(RAIZ / "datos/procesados/tabla_episodios.parquet")
t = t[(t.ini >= "2023-02-01") & (t.ini < "2026-04-10") & (~t.hospitalizado | t.estancia_unica.fillna(False).astype(bool))]
t = t[~((t.ruta_simple == "ER") & (t.estado == "sin_actividad"))]
e = t[t.episodio == 0].merge(s, on="visit_occurrence_id", how="inner")
e = e[e.edad.between(0, 105) & e.sexo.notna()].copy()
e["hosp"] = e.hospitalizado.astype(int)
e["menor15"] = (e.edad < 15).astype(int)
print(f"\nEPISODIOS con atencion y laboratorio extraido en 6 h: {len(e):,}; hospitalizados {e.hosp.mean():.1%}")
print("\nHospitalizacion segun puntos de severidad:")
tp = e.assign(p=e.puntos.clip(upper=3)).groupby("p").agg(n=("hosp", "size"), hosp_pct=("hosp", lambda x: 100 * x.mean())).round(1)
print(tp.to_string()); tp.to_csv(TABLAS / "severidad_labs_hospitalizacion_por_puntos.csv")
bf = pd.DataFrame({n: {"n_con_bandera": int(e[n].sum()), "hosp_pct_con": round(100 * e.loc[e[n], "hosp"].mean(), 1),
                       "hosp_pct_sin": round(100 * e.loc[~e[n], "hosp"].mean(), 1)} for n in nb}).T
print("\npor bandera:\n" + bf.to_string()); bf.to_csv(TABLAS / "severidad_labs_por_bandera.csv")

# 1) logistica: hospitalizacion con y sin banderas (corte temporal)
e["tipo"] = e.tipo_visita.astype(str)
X0 = pd.get_dummies(e[["edad", "menor15", "tipo", "hora"]], columns=["tipo"], drop_first=True).astype(float)
X0["sexo_f"] = (e.sexo.astype(str).str.upper().str[0] == "F").astype(float)
X1 = X0.join(e[nb].astype(float))
X2 = X1.assign(puntos=e.puntos.astype(float))
tr = (e.ini < "2025-07-01").values
res = []
for nombre, X in [("sin laboratorio (edad, sexo, tipo, hora)", X0), ("+ banderas", X1)]:
    mu, sd = X[tr].mean(), X[tr].std().replace(0, 1)
    m = sm.Logit(e.hosp[tr].values, sm.add_constant((X[tr] - mu) / sd)).fit(disp=0, method="bfgs", maxiter=500)
    pr = m.predict(sm.add_constant((X[~tr] - mu) / sd, has_constant="add"))
    res.append({"modelo": nombre, "AUC prueba (2025-07 a 2026-04)": round(roc_auc_score(e.hosp[~tr].values, np.asarray(pr)), 3)})
r1 = pd.DataFrame(res); print("\nHOSPITALIZACION (logistica):\n" + r1.to_string(index=False)); r1.to_csv(TABLAS / "severidad_labs_auc_hospitalizacion.csv", index=False)

# 2) R2 sobre espera y estancia entre hospitalizadas
h = t[t.hospitalizado & t.estancia_id.notna()]
sh = s.merge(t[["visit_occurrence_id", "estancia_id"]].drop_duplicates(), on="visit_occurrence_id")
sh = sh.groupby("estancia_id")[nb + ["puntos"]].max().reset_index() if True else sh
sh["puntos"] = sh[nb].sum(axis=1)
h = h.merge(sh, on="estancia_id", how="inner")
h = h[h.edad.between(0, 105) & h.sexo.notna() & h.espera_cama_h.notna() & (h.fin_hosp_est > h.ini_hosp_est)].copy()
h["estancia_h"] = (h.fin_hosp_est - h.ini_hosp_est).dt.total_seconds() / 3600
h = h[h.estancia_h > 0]
h["ly_esp"], h["ly_est"] = np.log1p(h.espera_cama_h), np.log1p(h.estancia_h)
h["pt"] = h.puntos.clip(upper=3)
h["anio"] = h.anio.astype(int)
h_todas = h.copy()
print(f"\nESTANCIAS hospitalizadas con laboratorio extraido: {len(h):,}")
base = "edad + C(sexo) + C(tipo_visita) + C(franja) + C(anio)"
out = []
for y, nombre in [("ly_esp", "espera de cama (solo espera >= 6 h)"), ("ly_est", "estancia en cama")]:
    h = h_todas[h_todas.espera_cama_h >= 6] if y == "ly_esp" else h_todas
    r0 = smf.ols(f"{y} ~ {base}", h).fit().rsquared
    r1_ = smf.ols(f"{y} ~ {base} + C(pt)", h).fit().rsquared
    r2 = smf.ols(f"{y} ~ {base} + " + " + ".join(nb), h).fit().rsquared
    out.append({"resultado": nombre, "R2 base": round(100 * r0, 1), "R2 + puntos": round(100 * r1_, 1), "R2 + banderas": round(100 * r2, 1)})
r2 = pd.DataFrame(out); print(r2.to_string(index=False)); r2.to_csv(TABLAS / "severidad_labs_r2.csv", index=False)
coef = smf.ols(f"ly_est ~ {base} + C(pt)", h).fit().params.filter(like="pt")
h = h_todas
print("efecto de los puntos sobre la estancia (% vs 0 puntos):", {k: round(100 * (np.exp(v) - 1), 1) for k, v in coef.items() if k != "Intercept"})
h = h_todas[h_todas.espera_cama_h >= 6]
print(f"estancias con espera >= 6 h: {len(h):,}")
coef = smf.ols(f"ly_esp ~ {base} + C(pt)", h).fit().params.filter(like="pt")
print("efecto de los puntos sobre la espera (% vs 0 puntos):", {k: round(100 * (np.exp(v) - 1), 1) for k, v in coef.items() if k != "Intercept"})

# 3) Prueba para el estimador A6: entre quienes ya llevan 6 h esperando, ¿predice mejor lo que les falta (log de horas restantes) con las banderas?
#    Modelo de gradiente (como A6), entrenado hasta 2025-06 y probado desde 2025-07 (mismo corte que A6); diferencia de error con intervalo por bootstrap.
from sklearn.ensemble import HistGradientBoostingRegressor
a6 = h_todas[h_todas.espera_cama_h > 6].copy()
a6["resta"] = np.log1p(a6.espera_cama_h - 6)
a6["sexo_f"] = (a6.sexo.astype(str).str.upper().str[0] == "M").astype(float)
base_cols = ["edad", "sexo_f", "hora", "dia_semana_num", "ocup_hosp", "llegadas_6h_previas"]
a6["tipo_cod"] = a6.tipo_visita.astype("category").cat.codes
base_cols.append("tipo_cod")
tr6 = (a6.ini < "2025-07-01").values
print(f"\nPRUEBA A6: {len(a6):,} estancias con espera > 6 h (entrenamiento {tr6.sum():,}, prueba {(~tr6).sum():,})")
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
    d = e2 - errs["sin laboratorio"]
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)]
    filas.append({"modelo": nombre, "R2 en prueba (vs media del entrenamiento)": round(r2, 4), "cambio del error cuadratico medio": round(d.mean(), 4),
                  "IC95 bajo": round(np.percentile(bs, 2.5), 4), "IC95 alto": round(np.percentile(bs, 97.5), 4)})
r3 = pd.DataFrame(filas); print(r3.to_string(index=False)); r3.to_csv(TABLAS / "severidad_labs_prueba_a6.csv", index=False)

# 4) Efecto de cada bandera sobre la espera (esperas >= 6 h), en % frente a no tenerla, controlando edad, sexo, tipo de visita, franja y ano
h = h_todas[h_todas.espera_cama_h >= 6]
ajuste = smf.ols("ly_esp ~ " + base + " + " + " + ".join(f"{n}.astype(int)" for n in nb), h).fit(cov_type="HC1")
ef = pd.DataFrame({"efecto_pct": [round(100 * (np.exp(ajuste.params[f"{n}.astype(int)"]) - 1), 1) for n in nb],
                   "ic95_bajo": [round(100 * (np.exp(ajuste.conf_int().loc[f"{n}.astype(int)", 0]) - 1), 1) for n in nb],
                   "ic95_alto": [round(100 * (np.exp(ajuste.conf_int().loc[f"{n}.astype(int)", 1]) - 1), 1) for n in nb],
                   "estancias_con_bandera": [int(h[n].sum()) for n in nb]}, index=nb)
print("\nEFECTO DE CADA BANDERA SOBRE LA ESPERA DE CAMA (esperas >= 6 h):\n" + ef.to_string())
ef.to_csv(TABLAS / "severidad_labs_efecto_por_bandera_en_la_espera.csv")
