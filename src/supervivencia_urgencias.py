"""
supervivencia_urgencias.py  -  version 1 (4-nov-2026)
Exploracion 5: duracion de la atencion en urgencias (pacientes que NO se hospitalizan) con metodos de supervivencia.

PROBLEMA
  Solo ~30 % de estos episodios tiene hora de salida (estado 'medida'). El resto es:
    minimo_conocido : hay etapas con tiempo pero la ultima no tiene fin -> la duracion es AL MENOS lo observado (censura por la derecha, con informacion)
    minimo_dx, sin_duracion, sin_actividad : sin tiempo en urgencias (la etapa tiene inicio = fin) -> no hay informacion de duracion
  Mirar solo los 'medida' sesga hacia abajo: deja fuera a los que seguian en urgencias al cierre del registro.

QUE HACE
  1. Estimador de Kaplan-Meier con los 'medida' (evento) y los 'minimo_conocido' (censurados en lo observado). Corrige la truncacion.
  2. Prueba si tener informacion de duracion depende de lo que sabemos (hora, dia, edad, sexo, tipo de visita, ano, diagnostico, laboratorios,
     procedimientos, carga): modelo logistico y AUC. Si depende, se PONDERA (inverso de la probabilidad de tener informacion).
  3. Compara: mediana ingenua (solo 'medida'), Kaplan-Meier, Kaplan-Meier ponderado y COTAS extremas (que pasa si todos los episodios
     sin informacion fueran de 0 h o de 24 h).

LIMITES (los mas importantes)
  - Los episodios sin tiempo en urgencias (la mayoria) NO aportan informacion de duracion: ningun metodo la inventa. La ponderacion solo corrige las
    diferencias que se ven en las variables observadas; si faltar depende de la duracion misma, el sesgo sigue. Por eso se reportan cotas.
  - El diagnostico y los laboratorios se usan solo para ponderar (no es un modelo "al llegar").
  - Solo episodios de urgencias sin hospitalizacion, con alguna etapa TU; se excluyen los que son solo admision (ER). Periodo: 1-feb-2023 a 9-abr-2026.

ENTRADA datos/procesados/tabla_episodios.parquet ; SALIDAS resultados/tablas/supervivencia_urgencias_*.csv ; resultados/graficos/supervivencia_urgencias.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parent.parent
TABLAS, GRAF = RAIZ / "resultados" / "tablas", RAIZ / "resultados" / "graficos"
INI, FIN = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10")
pd.set_option("display.width", 200)

t = pd.read_parquet(RAIZ / "datos/procesados/tabla_episodios.parquet")
c = t[(~t.hospitalizado) & (t.ini >= INI) & (t.ini < FIN) & t.ruta_simple.str.contains("TU")].copy()
c["info"] = c.estado.isin(["medida", "minimo_conocido"])
c["evento"] = c.estado.eq("medida")
c["tiempo"] = np.where(c.info, c.horas_total, 0.0)
c = c[c.tiempo.le(24 * 90)]
print(f"episodios de urgencias sin hospitalizacion: {len(c)}")
print(c.estado.value_counts().to_string())
print(f"con informacion de duracion: {100 * c['info'].mean():.1f} % (medida {100 * c.evento.mean():.1f} %, minimo conocido {100 * (c.estado == 'minimo_conocido').mean():.1f} %)")


def km(tiempo, evento, peso=None):
    """Kaplan-Meier (con pesos opcionales); devuelve tiempos y supervivencia S(t)."""
    peso = np.ones(len(tiempo)) if peso is None else np.asarray(peso, float)
    o = np.argsort(tiempo, kind="stable")
    tt, ee, ww = np.asarray(tiempo)[o], np.asarray(evento)[o].astype(bool), peso[o]
    en_riesgo = ww[::-1].cumsum()[::-1]
    u, idx = np.unique(tt, return_index=True)
    S, s = [], 1.0
    for i, ti in enumerate(u):
        m = tt == ti
        d = ww[m & ee].sum()
        n = en_riesgo[idx[i]]
        s *= 1 - d / n if n > 0 else 1
        S.append(s)
    return u, np.array(S)


def cuantil(u, S, q):
    """Menor tiempo con S(t) <= 1-q; NaN si la curva no llega ahi (censura larga)."""
    k = np.where(S <= 1 - q)[0]
    return float(u[k[0]]) if len(k) else np.nan


# ---------------------------------------------------------------- 2. ¿depende tener informacion de lo observado?
c["hora_llegada"] = c.hora
c["dx_presente"] = c.dx_nombre.notna().astype(int)
X = pd.concat([pd.get_dummies(c[["grupo_edad", "tipo_visita", "franja", "sexo"]].astype(str), drop_first=True, dtype=float),
               pd.get_dummies(c.anio.astype(str), prefix="anio", drop_first=True, dtype=float),
               pd.get_dummies(c.dia_semana_num.astype(str), prefix="dow", drop_first=True, dtype=float),
               c[["dx_presente"]].astype(float), (c.n_lab.fillna(0) > 0).astype(float).rename("tiene_lab"), (c.n_proc_distintos.fillna(0) > 0).astype(float).rename("tiene_proc"),
               c.llegadas_6h_previas.fillna(c.llegadas_6h_previas.median()).rename("carga_6h")], axis=1)
X = sm.add_constant(X)
mod = sm.Logit(c["info"].astype(float), X).fit(disp=0, maxiter=200)
p = mod.predict(X).clip(0.02, 0.98)
# AUC por rangos (sin sklearn)
r = pd.Series(p).rank().values
n1, n0 = c["info"].sum(), (~c["info"]).sum()
auc = (r[c["info"].values].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
print(f"\nModelo de 'tener informacion de duracion': AUC = {auc:.3f} (0,5 = no depende de lo observado)")
coef = pd.DataFrame({"odds_ratio": np.exp(mod.params), "p": mod.pvalues}).drop(index="const").round(3)
print("variables con mayor efecto (razon de probabilidades):")
print(coef.assign(dist=lambda d: (np.log(d.odds_ratio)).abs()).sort_values("dist", ascending=False).head(8).drop(columns="dist").to_string())
tasa = c.groupby("anio")["info"].mean().round(3)
print("\n% con informacion por ano:", tasa.to_dict())
print("% con informacion por tipo de visita:", c.groupby("tipo_visita")["info"].mean().round(3).to_dict())
print("% con informacion por franja:", c.groupby("franja")["info"].mean().round(3).to_dict())
print("% con informacion segun tenga laboratorio:", c.groupby(c.n_lab.fillna(0) > 0)["info"].mean().round(3).to_dict())

# ---------------------------------------------------------------- 1 y 3. estimadores
w = (1 / p[c["info"].values]).values
ci = c[c["info"]]
res = []
naive = c[c.evento].tiempo
res.append(("ingenua: solo 'medida'", naive.quantile(.25), naive.median(), naive.quantile(.75), naive.quantile(.9), len(naive)))
u, S = km(ci.tiempo.values, ci.evento.values)
res.append(("Kaplan-Meier (medida + minimo conocido)", cuantil(u, S, .25), cuantil(u, S, .5), cuantil(u, S, .75), cuantil(u, S, .9), len(ci)))
uw, Sw = km(ci.tiempo.values, ci.evento.values, w)
res.append(("Kaplan-Meier ponderado por la prob. de tener informacion", cuantil(uw, Sw, .25), cuantil(uw, Sw, .5), cuantil(uw, Sw, .75), cuantil(uw, Sw, .9), len(ci)))
# cotas: los episodios sin informacion duran 0 h (cota baja) o 24 h (cota alta)
for etiqueta, d0 in [("cota baja: los sin informacion duraron 0 h", 0.0), ("cota alta: los sin informacion duraron 24 h", 24.0)]:
    ti = np.concatenate([ci.tiempo.values, np.full((~c["info"]).sum(), d0)])
    ei = np.concatenate([ci.evento.values, np.ones((~c["info"]).sum(), bool)])
    uu, SS = km(ti, ei)
    res.append((etiqueta, cuantil(uu, SS, .25), cuantil(uu, SS, .5), cuantil(uu, SS, .75), cuantil(uu, SS, .9), len(ti)))
R = pd.DataFrame(res, columns=["estimador", "p25_h", "mediana_h", "p75_h", "p90_h", "n"]).round(1)
print("\nDURACION EN URGENCIAS (horas) SEGUN EL METODO")
print(R.to_string(index=False))
R.to_csv(TABLAS / "supervivencia_urgencias_estimadores.csv", index=False)

# por tipo de visita y franja (Kaplan-Meier, con n)
filas = []
for f in ["tipo_visita", "grupo_edad", "franja"]:
    for nivel, d in ci.groupby(f):
        if len(d) < 200:
            continue
        uu, SS = km(d.tiempo.values, d.evento.values)
        nv = c[c[f] == nivel]
        filas.append(dict(factor=f, nivel=nivel, n_con_info=len(d), pct_con_info=round(100 * len(d) / len(nv), 1), mediana_km_h=round(cuantil(uu, SS, .5), 1),
                          mediana_ingenua_h=round(nv[nv.evento].tiempo.median(), 1)))
G = pd.DataFrame(filas)
print("\nPOR GRUPO (Kaplan-Meier frente a la mediana ingenua)")
print(G.to_string(index=False))
G.to_csv(TABLAS / "supervivencia_urgencias_por_grupo.csv", index=False)

fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
un = np.sort(naive.values)
ax[0].step(un, 1 - np.arange(1, len(un) + 1) / len(un), where="post", color="#bdbdbd", label="ingenua (solo 'medida')")
ax[0].step(u, S, where="post", color="#2a6fb0", label="Kaplan-Meier")
ax[0].step(uw, Sw, where="post", color="#d9730d", ls="--", label="K-M ponderado")
ax[0].set_xlim(0, 72)
ax[0].set_xlabel("horas en urgencias")
ax[0].set_ylabel("proporcion que sigue en urgencias")
ax[0].legend(fontsize=8)
ax[0].set_title("Duracion en urgencias (sin hospitalizacion)", fontsize=10)
g2 = c.groupby("anio")["info"].mean() * 100
ax[1].bar(g2.index.astype(str), g2.values, color="#2a6fb0")
ax[1].set_ylabel("% de episodios con informacion de duracion")
ax[1].set_title("Cobertura por ano", fontsize=10)
plt.tight_layout()
plt.savefig(GRAF / "supervivencia_urgencias.png", dpi=130)
print("\nguardado: supervivencia_urgencias_*.csv y supervivencia_urgencias.png")
