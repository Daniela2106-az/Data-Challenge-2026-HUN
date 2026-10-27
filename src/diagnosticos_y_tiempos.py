"""
diagnosticos_y_tiempos.py  -  version 1 (26-oct-2026)
Tarea A3 (parte analitica). El instructivo pide analizar "diagnosticos y procedimientos asociados a los tiempos de atencion y la
complejidad clinica de las visitas". Este script lo hace por grupo de diagnostico (datos/referencia/mapeo_dx.csv).

QUE HACE
  Por categoria_dx (diagnostico principal = primer diagnostico traducido del episodio), con estancias unicas:
    - cobertura: cuantos episodios tienen diagnostico y como cambia segun la ruta (sesgo de registro),
    - % que se hospitaliza y reingreso a 72 h,
    - espera de cama (mediana, p90) y estancia en cama (mediana, p90) de los hospitalizados,
    - duracion de urgencias de quienes NO se hospitalizan (solo episodios con hora de salida: sesgada, ver OJO),
    - complejidad: diagnosticos, procedimientos y laboratorios de las primeras 6 h (medianas),
    - razon frente a todos los hospitalizados con diagnostico (espera del grupo / espera de ese conjunto) y bandera de n < 30.
  Tambien el detalle de los 25 diagnosticos concretos con mas hospitalizados.

ENTRADA   datos/procesados/tabla_episodios.parquet (src/preparar_variables.py), datos/referencia/mapeo_dx.csv
SALIDAS   resultados/tablas/tiempos_por_dx.csv, tiempos_por_dx_detalle.csv, cobertura_dx_por_ruta.csv,
          dx_registrado_segun_espera.csv (sesgo de registro), efecto_dx_espera.csv (efecto del grupo con controles)
          resultados/graficos/tiempos_por_dx.png

OJO AL LEER
  - El diagnostico se registra tarde (88 % despues de las 2 primeras h) y solo ~50 % de los hospitalizados y ~20 % de los demas
    tiene uno traducido: los grupos NO representan a todos los pacientes, y quien tiene diagnostico puede ser distinto
    (p. ej. quien se queda mas tiempo tiene mas oportunidad de que se registre). Es asociacion, no causa, y no sirve para
    predecir al llegar.
  - SESGO DE REGISTRO (medido aqui): entre los hospitalizados, tiene diagnostico traducido el ~60 % de quienes reciben cama en 6 h o
    menos y solo el ~27 % de quienes esperan mas de 24 h. Comparar con y sin diagnostico exagera la diferencia, y las comparaciones
    entre grupos valen solo "dentro de quienes tienen diagnostico". Pregunta nueva al HUN: cuando se registra el diagnostico.
  - Complejidad (n_dx, n_proc, laboratorios) crece con la estancia (causalidad inversa): se reporta como descripcion.
  - La duracion de urgencias sin hospitalizar solo existe en ~38 % de los episodios (hora de salida faltante) y esta sesgada.
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC, TABLAS, GRAF = RAIZ / "datos" / "procesados", RAIZ / "resultados" / "tablas", RAIZ / "resultados" / "graficos"
MIN_N = 30
MAX_H = 2160

t = pd.read_parquet(PROC / "tabla_episodios.parquet")
t = t[t.estancia_unica].copy()
t["con_dx"] = t.categoria_dx != "Sin diagnostico"
t["estancia_cama_h"] = (pd.to_datetime(t.fin_hosp) - pd.to_datetime(t.ini_hosp)).dt.total_seconds() / 3600
t.loc[~t.estancia_cama_h.between(0.01, MAX_H), "estancia_cama_h"] = np.nan
t["tu_alta_h"] = t.horas_validas.where((~t.hospitalizado) & (t.estado == "medida") & (t.horas_validas <= MAX_H))
t["espera"] = t.espera_cama_h.where(t.hospitalizado)

# cobertura del diagnostico por ruta (sesgo de registro)
cob = t.groupby("ruta_simple").agg(episodios=("con_dx", "size"), pct_con_dx=("con_dx", "mean")).reset_index()
cob["pct_con_dx"] = (100 * cob.pct_con_dx).round(1)
cob.sort_values("episodios", ascending=False).head(15).to_csv(TABLAS / "cobertura_dx_por_ruta.csv", index=False)
print("cobertura del diagnostico: hospitalizados %.1f %% | no hospitalizados %.1f %%" % (
    100 * t[t.hospitalizado].con_dx.mean(), 100 * t[~t.hospitalizado].con_dx.mean()))


def q(s, p):
    return s.quantile(p) if s.notna().sum() else np.nan


def resumen(g):
    h = g[g.hospitalizado]
    return pd.Series({
        "episodios": len(g), "hospitalizados": len(h),
        "pct_hospitaliza": 100 * g.hospitalizado.mean(),
        "espera_n": h.espera.notna().sum(), "espera_mediana_h": q(h.espera, .5), "espera_p90_h": q(h.espera, .9),
        "pct_espera_mas_24h": 100 * (h.espera.dropna() > 24).mean() if h.espera.notna().any() else np.nan,
        "estancia_n": h.estancia_cama_h.notna().sum(), "estancia_mediana_h": q(h.estancia_cama_h, .5),
        "estancia_p90_h": q(h.estancia_cama_h, .9),
        "urgencias_sin_hosp_n": g.tu_alta_h.notna().sum(), "urgencias_sin_hosp_mediana_h": q(g.tu_alta_h, .5),
        "n_dx_mediana": g.n_dx_distintos.median(), "n_proc_mediana": g.n_proc_distintos.median(),
        "n_lab_6h_mediana": g.n_lab_6h.median(),
        "reingreso_72h_pct": 100 * g.reingreso_72h.mean(),
    })


tot_todos = resumen(t)
tot = resumen(t[t.con_dx])   # referencia = hospitalizados CON diagnostico (el mismo universo de los grupos)
print(f"TODOS: espera mediana {tot_todos.espera_mediana_h:.1f} h, estancia mediana {tot_todos.estancia_mediana_h:.1f} h | "
      f"CON diagnostico: espera {tot.espera_mediana_h:.1f} h, estancia {tot.estancia_mediana_h:.1f} h")
res = t[t.con_dx].groupby("categoria_dx").apply(resumen, include_groups=False).reset_index()
res["razon_espera_vs_con_dx"] = res.espera_mediana_h / tot.espera_mediana_h
res["razon_estancia_vs_con_dx"] = res.estancia_mediana_h / tot.estancia_mediana_h
res["n_insuficiente"] = (res.espera_n < MIN_N) | (res.estancia_n < MIN_N)
res = res.sort_values("hospitalizados", ascending=False)
res.round(2).to_csv(TABLAS / "tiempos_por_dx.csv", index=False)
cols = ["categoria_dx", "episodios", "pct_hospitaliza", "espera_n", "espera_mediana_h", "espera_p90_h", "estancia_mediana_h",
        "estancia_p90_h", "n_dx_mediana", "n_proc_mediana", "n_insuficiente"]
print(res[cols].round(1).to_string(index=False))

det = t[t.con_dx & t.hospitalizado].groupby("dx_nombre").apply(resumen, include_groups=False).reset_index()
det = det.merge(t.drop_duplicates("dx_nombre")[["dx_nombre", "categoria_dx"]], on="dx_nombre")
det = det.sort_values("hospitalizados", ascending=False).head(25)
det.round(2).to_csv(TABLAS / "tiempos_por_dx_detalle.csv", index=False)
print("\nTOP 25 diagnosticos con mas hospitalizados:")
print(det[["dx_nombre", "hospitalizados", "espera_mediana_h", "estancia_mediana_h", "estancia_p90_h"]].round(1).to_string(index=False))

# sesgo de registro: que parte de los hospitalizados tiene diagnostico segun cuanto esperaron
h = t[t.hospitalizado & t.espera.notna()].copy()
h["tramo_espera_h"] = pd.cut(h.espera, [-1, 3, 6, 12, 24, 48, 72, 5000],
                             labels=["0-3", "3-6", "6-12", "12-24", "24-48", "48-72", "mas de 72"])
sesgo = h.groupby("tramo_espera_h", observed=True).con_dx.agg(hospitalizados="size", pct_con_dx="mean").reset_index()
sesgo["pct_con_dx"] = (100 * sesgo.pct_con_dx).round(1)
sesgo.to_csv(TABLAS / "dx_registrado_segun_espera.csv", index=False)
print("\nSESGO DE REGISTRO (% de hospitalizados con diagnostico segun su espera de cama):")
print(sesgo.to_string(index=False))
print("espera mediana con diagnostico %.1f h | sin diagnostico %.1f h" % (h[h.con_dx].espera.median(), h[~h.con_dx].espera.median()))

# efecto del grupo de diagnostico sobre log(espera + 1), con controles (solo hospitalizados CON diagnostico); referencia = Digestivo
d = h[h.con_dx].copy()
d["y"] = np.log1p(d.espera)
d["grupo_dx"] = d.categoria_dx.replace({"Recien nacido": "Otros / sin clasificar"})
dum = lambda cols: pd.get_dummies(d[cols].astype(str)).astype(float)
ctrl = dum(["tipo_visita", "franja", "anio", "grupo_edad"])
ctrl = ctrl.drop(columns=[c for c in ("tipo_visita_Urgencias", "franja_madrugada 0-5", "anio_2023", "grupo_edad_15-44") if c in ctrl])


def mco(X):
    X = X.copy()
    X.insert(0, "const", 1.0)
    A, y = X.values, d.y.values
    b = np.linalg.lstsq(A, y, rcond=None)[0]
    r = y - A @ b
    s2 = r @ r / (len(y) - A.shape[1])
    se = np.sqrt(np.diag(s2 * np.linalg.pinv(A.T @ A)))
    return pd.Series(b, X.columns), pd.Series(se, X.columns), 1 - r @ r / ((y - y.mean()) ** 2).sum()


_, _, r2_ctrl = mco(ctrl)
Xg = pd.concat([ctrl, dum(["grupo_dx"]).drop(columns="grupo_dx_Digestivo")], axis=1)
b, se, r2_full = mco(Xg)
c = b.filter(like="grupo_dx_")
ef = pd.DataFrame({"categoria_dx": [i.replace("grupo_dx_", "") for i in c.index],
                   "efecto_pct_vs_digestivo": ((np.exp(c.values) - 1) * 100).round(0),
                   "ic95_bajo": ((np.exp(c.values - 1.96 * se[c.index].values) - 1) * 100).round(0),
                   "ic95_alto": ((np.exp(c.values + 1.96 * se[c.index].values) - 1) * 100).round(0)})
ef = ef.merge(res[["categoria_dx", "espera_n"]], on="categoria_dx").sort_values("efecto_pct_vs_digestivo")
ef.to_csv(TABLAS / "efecto_dx_espera.csv", index=False)
print(f"\nEFECTO DEL GRUPO DE DIAGNOSTICO EN LA ESPERA (controlando tipo de visita, franja, anio y edad; R2 solo controles {r2_ctrl:.3f}, con grupo {r2_full:.3f}):")
print(ef.to_string(index=False))

# grafico
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AZUL, NARANJA, GRIS = "#2a78d6", "#eb6834", "#52514e"
g = res[~res.n_insuficiente].sort_values("estancia_mediana_h")
fig, axs = plt.subplots(1, 2, figsize=(12, 6), sharey=True, facecolor="#fcfcfb")
for ax, col, ref, color, tit in [(axs[0], "espera_mediana_h", tot.espera_mediana_h, AZUL, "Espera de cama, mediana (h)"),
                                (axs[1], "estancia_mediana_h", tot.estancia_mediana_h, NARANJA, "Estancia en cama, mediana (h)")]:
    ax.set_facecolor("#fcfcfb")
    ax.barh(g.categoria_dx, g[col], color=color, height=0.65)
    ax.axvline(ref, color=GRIS, linestyle="--", linewidth=1)
    ax.text(ref, len(g) - 0.4, f" con dx: {ref:.0f} h", color=GRIS, fontsize=8, va="bottom")
    for y, (v, n) in enumerate(zip(g[col], g.hospitalizados)):
        ax.text(v, y, f" {v:.0f} (n={int(n)})", va="center", fontsize=8, color=GRIS)
    ax.set_title(tit, fontsize=11, loc="left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlim(0, g[col].max() * 1.3)
fig.suptitle("Tiempos de los hospitalizados por grupo de diagnostico (solo con diagnostico traducido; asociacion, no causa)", fontsize=11, x=0.01, ha="left")
fig.tight_layout()
fig.savefig(GRAF / "tiempos_por_dx.png", dpi=150)
print("\ngrafico: resultados/graficos/tiempos_por_dx.png")
