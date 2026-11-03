"""
factores_estancia.py  -  version 1 (3-nov-2026)
Tarea A2 (docs/pendientes_y_reparto.md): factores asociados a las estancias hospitalarias (instructivo, componente 2) y respuesta a una pregunta concreta:
la estancia media subio de 4,57 a 5,31 dias entre 2023 y 2025 (+16 %): ¿porque cambio el TIPO de pacientes o porque cada tipo se quedo mas tiempo?

QUE HACE
  1. Describe la estancia en cama (mediana, p90, estancias de mas de 14 y de 30 dias) por anio.
  2. Modelo EXPLICATIVO (no predictivo) sobre log(estancia en horas): cuanto explica cada grupo de factores (R2 propio y perdida de R2 al quitarlo) y el efecto de cada nivel
     (% de cambio de la estancia), con intervalos de confianza. Un segundo modelo, solo entre quienes tienen diagnostico (65 % de las estancias, hasta el 30-abr-2026), suma el grupo de diagnostico.
  3. Regresion logistica de "estancia de mas de 14 dias" con razones de probabilidades (odds ratios) e intervalo.
  4. DESCOMPOSICION del cambio de la estancia media 2023 -> 2025 en: composicion (cambio en el peso de cada tipo de paciente) y dentro de cada tipo (el mismo tipo se queda mas), con
     varias definiciones de "tipo": edad, edad x tipo de visita, edad x sexo x tipo de visita, y edad x tipo de visita x diagnostico (si lo hay). Ademas: cuanto del cambio viene de las estancias de mas de 30 dias.

REGLAS
  - Periodo confiable: estancias que empiezan entre 2023-02-01 y 2026-04-09 y con alta registrada antes del 10-abr-2026 (`alta_completa`). Una fila por estancia (registro conservado, `estancia_id`).
  - Edad y sexo son los de la persona real (CLAUDE.md 4.10).
  - Factores permitidos: lo que se sabe al ingresar o poco despues (edad, sexo, tipo de visita, franja y anio de llegada, espera de cama, laboratorios de las primeras 6 h, ocupacion al llegar) y,
    en el segundo modelo, el grupo de diagnostico (se registra durante la estancia: reverse causality parcial; no es causa). NO se usan los conteos totales de diagnosticos, procedimientos ni laboratorios
    (crecen con la estancia: causalidad inversa).
  - Se reporta el R2 sin esconderlo: el objetivo es EXPLICAR, no predecir (la prueba del 21-oct dio R2 cercano a 0 al predecir la estancia por paciente).

ENTRADAS  datos/procesados/tabla_episodios.parquet, datos/procesados/para_equipo/estancias_hospitalizacion.csv
SALIDAS   resultados/tablas/factores_estancia_por_anio.csv, factores_estancia_importancia.csv, factores_estancia_efectos.csv, factores_estancia_logit_14d.csv, factores_estancia_descomposicion.csv
          resultados/graficos/factores_estancia.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
DESDE, HASTA, HASTA_DX = "2023-02-01", "2026-04-10", "2026-05-01"

# ---------------------------------------------------------------- datos
t = pd.read_parquet(PROC / "tabla_episodios.parquet")
t = t[t.estancia_unica & t.hospitalizado & (t.ini >= DESDE) & (t.ini < HASTA) & t.sexo.isin(["Mujer", "Hombre"]) & t.grupo_edad.notna()].copy()
est = pd.read_csv(PROC / "para_equipo" / "estancias_hospitalizacion.csv", usecols=["visit_occurrence_id", "episodio", "ingreso_cama", "alta", "alta_completa"], parse_dates=["ingreso_cama", "alta"])
e = t.merge(est, on=["visit_occurrence_id", "episodio"], how="inner")
e = e[e.alta_completa == True].copy()      # noqa: E712
e["los_h"] = (e.alta - e.ingreso_cama).dt.total_seconds() / 3600
e = e[e.los_h > 0].copy()
e["los_d"] = e.los_h / 24
e["anio"] = e.ini.dt.year
e["anio_c"] = e.anio.astype(str)
e["franja"] = pd.cut(e.ini.dt.hour, [-1, 5, 11, 17, 23], labels=["madrugada", "manana", "tarde", "noche"])
e["tipo"] = e.tipo_visita.where(e.tipo_visita.isin(["Urgencias", "Treatment urgency", "Ambulatorio"]), "Otro")
e["espera_h"] = e.espera_cama_h.fillna(e.espera_cama_h.median())
e["sin_espera"] = e.espera_cama_h.isna().astype(int)
e["lab6"] = np.log1p(e.n_lab_6h.fillna(0))
e["ocup"] = e.ocup_hosp.fillna(e.ocup_hosp.median())
e["con_dx"] = (e.n_dx_distintos > 0) & (e.ini < HASTA_DX) & (e.categoria_dx != "Sin diagnostico")
print(f"estancias del periodo confiable con alta registrada: {len(e)} | estancia media {e.los_d.mean():.2f} d, mediana {e.los_h.median():.1f} h, p90 {e.los_h.quantile(.9):.0f} h | con diagnostico: {100 * e.con_dx.mean():.1f} %")

# ---------------------------------------------------------------- 1) descripcion por anio
pa = e.groupby("anio").agg(estancias=("los_d", "size"), media_dias=("los_d", "mean"), mediana_h=("los_h", "median"), p90_h=("los_h", lambda x: x.quantile(.9)),
                           pct_mas_14d=("los_d", lambda x: 100 * (x > 14).mean()), pct_mas_30d=("los_d", lambda x: 100 * (x > 30).mean())).round(2)
pa["media_dias_sin_las_de_mas_de_30d"] = e[e.los_d <= 30].groupby("anio").los_d.mean().round(2)
pa.to_csv(TABLAS / "factores_estancia_por_anio.csv")
print("\nESTANCIA POR ANIO (estancias que empiezan ese anio; 2026 = hasta el 9-abr)\n", pa.to_string())


# ---------------------------------------------------------------- 2) modelo explicativo sobre log(estancia)
def disenio(df, bloques):
    partes, nombres = [pd.Series(1.0, index=df.index, name="const")], {}
    for nombre, cols in bloques.items():
        piezas = []
        for c in cols:
            if df[c].dtype.kind in "fi" and df[c].nunique() > 2:
                piezas.append(((df[c] - df[c].mean()) / df[c].std()).rename(c))
            elif df[c].dtype.kind in "fi":
                piezas.append(df[c].astype(float).rename(c))
            else:
                piezas.append(pd.get_dummies(df[c].astype(str), prefix=c, dtype=float))
        X = pd.concat(piezas, axis=1)
        # quitar una categoria de referencia por variable categorica
        for c in cols:
            if df[c].dtype.kind not in "fi":
                ref = df[c].astype(str).value_counts().index[0]
                X = X.drop(columns=f"{c}_{ref}")
        nombres[nombre] = list(X.columns)
        partes.append(X)
    return pd.concat(partes, axis=1), nombres


def ajustar(X, y):
    A = X.values
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    n, k = A.shape
    s2 = (r @ r) / (n - k)
    cov = s2 * np.linalg.inv(A.T @ A)
    r2 = 1 - (r @ r) / ((y - y.mean()) @ (y - y.mean()))
    return pd.Series(b, index=X.columns), pd.Series(np.sqrt(np.diag(cov)), index=X.columns), r2


BLOQUES = {"edad y sexo": ["grupo_edad", "sexo"], "tipo de visita": ["tipo"], "hora y año de llegada": ["franja", "anio_c"],
           "espera de cama": ["espera_h", "sin_espera"], "laboratorios (6 h)": ["lab6"], "ocupación al llegar": ["ocup"]}
resultados_imp, resultados_efec = [], []
for modelo, df, bloques in [("A: todas las estancias", e, BLOQUES), ("B: solo con diagnóstico", e[e.con_dx], {**BLOQUES, "grupo de diagnóstico": ["categoria_dx"]})]:
    df = df.copy()
    y = np.log(df.los_h.values)
    X, nom = disenio(df, bloques)
    b, se, r2 = ajustar(X, y)
    print(f"\nMODELO {modelo}: n = {len(df)}, R2 con todos los factores = {r2:.3f}")
    for nombre, cols in nom.items():
        solo = X[["const"] + cols]
        _, _, r2s = ajustar(solo, y)
        sin = X.drop(columns=cols)
        _, _, r2m = ajustar(sin, y)
        resultados_imp.append(dict(modelo=modelo, factor=nombre, r2_solo=round(r2s, 4), perdida_r2_si_se_quita=round(r2 - r2m, 4), r2_total=round(r2, 4), n=len(df)))
    for c in X.columns[1:]:
        resultados_efec.append(dict(modelo=modelo, variable=c, pct_cambio_estancia=round(100 * (np.exp(b[c]) - 1), 1), ic_bajo=round(100 * (np.exp(b[c] - 1.96 * se[c]) - 1), 1),
                                    ic_alto=round(100 * (np.exp(b[c] + 1.96 * se[c]) - 1), 1)))
imp = pd.DataFrame(resultados_imp)
imp.to_csv(TABLAS / "factores_estancia_importancia.csv", index=False)
efe = pd.DataFrame(resultados_efec)
efe.to_csv(TABLAS / "factores_estancia_efectos.csv", index=False)
print(imp.to_string(index=False))
print("\nEFECTOS destacados (modelo A; % de cambio de la estancia frente a la categoria de referencia)")
print(efe[(efe.modelo.str.startswith("A")) & efe.variable.str.contains("grupo_edad|sexo|tipo_|franja|anio_c")].to_string(index=False))


# ---------------------------------------------------------------- 3) logistica: estancia de mas de 14 dias
def logit(X, y, it=50):
    A = X.values.astype(float)
    b = np.zeros(A.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-np.clip(A @ b, -30, 30)))
        W = p * (1 - p)
        H = A.T @ (A * W[:, None]) + 1e-6 * np.eye(A.shape[1])
        nuevo = b + np.linalg.solve(H, A.T @ (y - p))
        if np.abs(nuevo - b).max() < 1e-8:
            b = nuevo
            break
        b = nuevo
    p = 1 / (1 + np.exp(-np.clip(A @ b, -30, 30)))
    H = A.T @ (A * (p * (1 - p))[:, None]) + 1e-6 * np.eye(A.shape[1])
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return pd.Series(b, index=X.columns), pd.Series(se, index=X.columns), p


Xl, _ = disenio(e, BLOQUES)
yl = (e.los_d > 14).astype(float).values
bl, sel, pl = logit(Xl, yl)
rank = pd.Series(pl).rank().values
pos, neg = yl == 1, yl == 0
auc = (rank[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum())
lg = pd.DataFrame({"variable": Xl.columns[1:], "odds_ratio": np.exp(bl[1:]).round(2), "ic_bajo": np.exp(bl[1:] - 1.96 * sel[1:]).round(2), "ic_alto": np.exp(bl[1:] + 1.96 * sel[1:]).round(2)})
lg.to_csv(TABLAS / "factores_estancia_logit_14d.csv", index=False)
print(f"\nLOGISTICA estancia de mas de 14 dias: {int(yl.sum())} de {len(yl)} ({100 * yl.mean():.1f} %), AUC = {auc:.3f}")
print(lg[lg.variable.str.contains("grupo_edad|sexo|tipo_|anio_c|espera")].to_string(index=False))


# ---------------------------------------------------------------- 4) descomposicion 2023 -> 2025
def descomponer(df, grupos, y0=2023, y1=2025):
    d0, d1 = df[df.anio == y0], df[df.anio == y1]
    g0 = d0.groupby(grupos, observed=True).los_d.agg(["size", "mean"]).rename(columns={"size": "n0", "mean": "m0"})
    g1 = d1.groupby(grupos, observed=True).los_d.agg(["size", "mean"]).rename(columns={"size": "n1", "mean": "m1"})
    g = g0.join(g1, how="outer").fillna({"n0": 0, "n1": 0})
    g["w0"], g["w1"] = g.n0 / g.n0.sum(), g.n1 / g.n1.sum()
    comunes = g.dropna(subset=["m0", "m1"])
    solo_1 = g[g.m0.isna()]
    media0, media1 = d0.los_d.mean(), d1.los_d.mean()
    # composicion: cambio de pesos valorado con la estancia de 2023; dentro: cambio de estancia con los pesos de 2025 (celdas que existen en ambos anios)
    comp = ((comunes.w1 - comunes.w0) * comunes.m0).sum()
    dentro = (comunes.w1 * (comunes.m1 - comunes.m0)).sum()
    resto = media1 - media0 - comp - dentro          # celdas que no existen en los dos anios
    return dict(media_2023=round(media0, 3), media_2025=round(media1, 3), cambio_dias=round(media1 - media0, 3), cambio_pct=round(100 * (media1 / media0 - 1), 1),
                composicion_dias=round(comp, 3), dentro_dias=round(dentro, 3), celdas_sin_comparacion_dias=round(resto, 3), n_celdas=len(g), celdas_comunes=len(comunes))


e["dx_g"] = np.where(e.con_dx, e.categoria_dx, "sin diagnóstico")
filas = []
for nombre, grupos in [("edad", ["grupo_edad"]), ("edad x tipo de visita", ["grupo_edad", "tipo"]), ("edad x sexo x tipo de visita", ["grupo_edad", "sexo", "tipo"]),
                       ("edad x tipo de visita x diagnóstico (o sin él)", ["grupo_edad", "tipo", "dx_g"])]:
    r = descomponer(e, grupos)
    r["definicion_de_tipo"] = nombre
    filas.append(r)
# sin las estancias de mas de 30 dias
r = descomponer(e[e.los_d <= 30], ["grupo_edad", "tipo"])
r["definicion_de_tipo"] = "edad x tipo de visita, SIN las estancias de más de 30 días"
filas.append(r)
dec = pd.DataFrame(filas)[["definicion_de_tipo", "media_2023", "media_2025", "cambio_dias", "cambio_pct", "composicion_dias", "dentro_dias", "celdas_sin_comparacion_dias", "n_celdas", "celdas_comunes"]]
dec.to_csv(TABLAS / "factores_estancia_descomposicion.csv", index=False)
print("\nDESCOMPOSICION del cambio de la estancia media 2023 -> 2025 (dias)\n", dec.to_string(index=False))
# aporte de las estancias largas y de Treatment urgency
for y in (2023, 2025):
    d = e[e.anio == y]
    print(f"{y}: estancias {len(d)} | media {d.los_d.mean():.2f} d | >30 d: {int((d.los_d > 30).sum())} estancias, aportan {d[d.los_d > 30].los_d.sum() / len(d):.2f} d de la media | Treatment urgency: {100 * (d.tipo == 'Treatment urgency').mean():.1f} % de las estancias, media {d[d.tipo == 'Treatment urgency'].los_d.mean():.2f} d")
tmp = e.assign(grupo=np.where(e.los_d > 30, "más de 30 d", np.where(e.los_d > 14, "14 a 30 d", np.where(e.los_d > 7, "7 a 14 d", "hasta 7 d"))))
aporte = tmp.groupby(["anio", "grupo"]).los_d.sum().unstack() / tmp.groupby("anio").size().values[:, None]
print("\naporte de cada tramo de duracion a la estancia media (dias):\n", aporte.loc[[2023, 2024, 2025]].round(2).to_string())

# ---------------------------------------------------------------- grafico
fig, ejes = plt.subplots(1, 3, figsize=(17, 4.8))
ia = imp[imp.modelo.str.startswith("A")].sort_values("perdida_r2_si_se_quita")
ejes[0].barh(ia.factor, 100 * ia.perdida_r2_si_se_quita, color="#2a6fb0")
ejes[0].set_title(f"Qué explica la estancia (modelo A, R² total {100 * ia.r2_total.iloc[0]:.1f} %)", fontsize=10)
ejes[0].set_xlabel("puntos de R² que se pierden al quitar el factor")
ejes[1].bar(pa.index.astype(str), pa.media_dias, color=["#999", "#2a6fb0", "#2a6fb0", "#999"][:len(pa)])
ejes[1].set_title("Estancia media por año de ingreso (días)", fontsize=10)
for i, v in enumerate(pa.media_dias):
    ejes[1].text(i, v + 0.05, f"{v:.2f}".replace(".", ","), ha="center", fontsize=9)
d0 = dec.iloc[1]
ejes[2].bar(["composición\n(tipo de pacientes)", "dentro de cada tipo\n(se quedan más)", "sin comparar"], [d0.composicion_dias, d0.dentro_dias, d0.celdas_sin_comparacion_dias], color=["#d9730d", "#2a6fb0", "#999"])
ejes[2].axhline(0, color="#444", lw=0.8)
ejes[2].set_title(f"Cambio 2023→2025 ({d0.cambio_dias:+.2f} días), tipo = edad × tipo de visita".replace(".", ","), fontsize=10)
ejes[2].set_ylabel("días")
fig.tight_layout()
fig.savefig(GRAFICOS / "factores_estancia.png", dpi=120)
print("\nguardado: factores_estancia_*.csv y factores_estancia.png")
