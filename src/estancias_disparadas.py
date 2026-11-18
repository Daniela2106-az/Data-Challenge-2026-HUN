"""
estancias_disparadas.py  -  version 1 (3-nov-2026)
Tarea A2b (docs/pendientes_y_reparto.md, idea de Anthony): ¿cuando se "disparan" las estancias y que comparten las que se disparan?

DEFINICION: estancia LARGA = mas de 14 dias en cama (6,5 % de las estancias); MUY LARGA = mas de 30 dias (1,2 %). Se comparan con las demas.

PARTES
  1. CUANDO: por mes de ingreso (feb-2023 a 9-abr-2026): estancia mediana, p90, % de estancias largas y muy largas, y cuantas camas ocupan. ¿Se concentran en ciertos meses o es parejo?
  2. QUIEN: perfil de las largas frente a las demas (edad, sexo, tipo de visita, diagnostico, espera, hora de llegada) con razones de probabilidades ajustadas (regresion logistica) -> tabla de A2.
  3. QUE LES PASA (opcional, necesita la consulta del lote 5 de src/auditoria_bd.py): procedimientos y laboratorios de las PRIMERAS 48 HORAS de cada estancia (laboratorios con fecha; los
     procedimientos no tienen fecha, se marcan como "durante la estancia" y pueden ser consecuencia de ella), solo de las filas de la persona real (docs/CONTEXTO_TECNICO.md 4.10).

REGLAS: periodo confiable (hasta el 9-abr-2026), una fila por estancia (`estancia_id`), edad y sexo de la persona real, alta registrada antes del 10-abr.

ENTRADAS  datos/procesados/tabla_episodios.parquet, para_equipo/estancias_hospitalizacion.csv, y (parte 3) datos/crudos/auditoria_bd/Q*.csv
SALIDAS   resultados/tablas/disparadas_por_mes.csv, disparadas_perfil.csv, disparadas_odds.csv, disparadas_conceptos.csv (parte 3)
          resultados/graficos/estancias_disparadas.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
CRUDOS = RAIZ / "datos" / "crudos"
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
DESDE, HASTA, HASTA_DX = "2023-02-01", "2026-04-10", "2026-05-01"
LARGA_D, MUY_LARGA_D = 14, 30

t = pd.read_parquet(PROC / "tabla_episodios.parquet")
t = t[t.estancia_unica & t.hospitalizado & (t.ini >= DESDE) & (t.ini < HASTA) & t.sexo.isin(["Mujer", "Hombre"]) & t.grupo_edad.notna()].copy()
est = pd.read_csv(PROC / "para_equipo" / "estancias_hospitalizacion.csv", usecols=["visit_occurrence_id", "episodio", "ingreso_cama", "alta", "alta_completa"], parse_dates=["ingreso_cama", "alta"])
e = t.merge(est, on=["visit_occurrence_id", "episodio"], how="inner")
e = e[e.alta_completa == True].copy()      # noqa: E712
e["los_d"] = (e.alta - e.ingreso_cama).dt.total_seconds() / 86400
e = e[e.los_d > 0].copy()
e["larga"], e["muy_larga"] = e.los_d > LARGA_D, e.los_d > MUY_LARGA_D
e["mes"] = e.ingreso_cama.dt.to_period("M").dt.to_timestamp()
e["franja"] = pd.cut(e.ini.dt.hour, [-1, 5, 11, 17, 23], labels=["madrugada", "mañana", "tarde", "noche"])
e["tipo"] = e.tipo_visita.where(e.tipo_visita.isin(["Urgencias", "Treatment urgency", "Ambulatorio"]), "Otro")
e["con_dx"] = (e.n_dx_distintos > 0) & (e.ini < HASTA_DX) & (e.categoria_dx != "Sin diagnostico")
print(f"estancias: {len(e)} | largas (>{LARGA_D} d): {int(e.larga.sum())} ({100 * e.larga.mean():.1f} %) | muy largas (>{MUY_LARGA_D} d): {int(e.muy_larga.sum())} ({100 * e.muy_larga.mean():.1f} %)")

# ---------------------------------------------------------------- 1. cuando
m = e.groupby("mes").agg(estancias=("los_d", "size"), mediana_d=("los_d", "median"), p90_d=("los_d", lambda x: x.quantile(.9)), pct_largas=("larga", lambda x: 100 * x.mean()),
                         pct_muy_largas=("muy_larga", lambda x: 100 * x.mean()), largas=("larga", "sum"), muy_largas=("muy_larga", "sum"))
m["dias_cama_de_largas_por_dia"] = e[e.larga].groupby("mes").los_d.sum().reindex(m.index).fillna(0) / m.index.to_series().dt.days_in_month
m = m.round(2)
m.to_csv(TABLAS / "disparadas_por_mes.csv")
m_ok = m.iloc[1:-1]                                   # primer y ultimo mes incompletos
print("\nPOR MES (estancias que empiezan ese mes)")
print(m_ok[["estancias", "mediana_d", "p90_d", "pct_largas", "pct_muy_largas"]].describe().loc[["mean", "std", "min", "max"]].round(2).to_string())
# estacionalidad por mes del anio y tendencia
e["mes_anio"] = e.ingreso_cama.dt.month
est_mes = e.groupby("mes_anio").agg(estancias=("los_d", "size"), pct_largas=("larga", lambda x: 100 * x.mean())).round(2)
print("\n% de largas por mes del anio (todos los anios):", est_mes.pct_largas.to_dict())
tri = e.groupby(e.ingreso_cama.dt.to_period("Q")).agg(estancias=("los_d", "size"), pct_largas=("larga", lambda x: round(100 * x.mean(), 1)), pct_muy=("muy_larga", lambda x: round(100 * x.mean(), 2)), mediana_d=("los_d", lambda x: round(x.median(), 2)))
print("\nPOR TRIMESTRE\n", tri.to_string())
# regresion simple de la tendencia (% largas por mes ~ tiempo)
x = np.arange(len(m_ok)); y = m_ok.pct_largas.values
b = np.polyfit(x, y, 1)
resid = y - np.polyval(b, x)
se = np.sqrt((resid @ resid) / (len(x) - 2) / ((x - x.mean()) @ (x - x.mean())))
print(f"\ntendencia del % de largas: {b[0]:+.3f} puntos por mes (IC95 {b[0] - 1.96 * se:+.3f} a {b[0] + 1.96 * se:+.3f}); de {np.polyval(b, 0):.1f} % a {np.polyval(b, len(x) - 1):.1f} %")
# concentracion: que parte de los meses tiene % largas por encima de lo esperado por azar
p0 = e.larga.mean()
z = (m_ok.largas - p0 * m_ok.estancias) / np.sqrt(p0 * (1 - p0) * m_ok.estancias)
print(f"meses con % de largas mas alto de lo esperado por azar (z > 2): {int((z > 2).sum())} de {len(z)}; z < -2: {int((z < -2).sum())}")

# ---------------------------------------------------------------- 2. quien
def comparar(col, etiqueta):
    g = e.groupby(col, observed=True).agg(estancias=("los_d", "size"), largas=("larga", "sum"), muy_largas=("muy_larga", "sum"))
    g["pct_largas"] = (100 * g.largas / g.estancias).round(1)
    g["pct_de_todas_las_largas"] = (100 * g.largas / g.largas.sum()).round(1)
    g["pct_de_todas_las_estancias"] = (100 * g.estancias / g.estancias.sum()).round(1)
    g.insert(0, "factor", etiqueta)
    g.index.name = "nivel"
    return g.reset_index()


perfil = pd.concat([comparar("grupo_edad", "edad"), comparar("sexo", "sexo"), comparar("tipo", "tipo de visita"), comparar("franja", "franja de llegada"),
                    comparar(e.ingreso_cama.dt.year.rename("anio"), "año de ingreso"), comparar(e.categoria_dx.where(e.con_dx, "sin diagnóstico").rename("dx"), "diagnóstico (o sin él)")])
perfil.to_csv(TABLAS / "disparadas_perfil.csv", index=False)
print("\nPERFIL DE LAS LARGAS (>14 d)")
print(perfil[perfil.factor.isin(["edad", "tipo de visita", "sexo"])].to_string(index=False))


def logit(X, y, it=60):
    A = X.values.astype(float)
    b = np.zeros(A.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-np.clip(A @ b, -30, 30)))
        H = A.T @ (A * (p * (1 - p))[:, None]) + 1e-6 * np.eye(A.shape[1])
        nuevo = b + np.linalg.solve(H, A.T @ (y - p))
        if np.abs(nuevo - b).max() < 1e-8:
            b = nuevo
            break
        b = nuevo
    p = 1 / (1 + np.exp(-np.clip(A @ b, -30, 30)))
    H = A.T @ (A * (p * (1 - p))[:, None]) + 1e-6 * np.eye(A.shape[1])
    return pd.Series(b, index=X.columns), pd.Series(np.sqrt(np.diag(np.linalg.inv(H))), index=X.columns), p


def dummies(df, cols):
    X = pd.concat([pd.get_dummies(df[c].astype(str), prefix=c, dtype=float).drop(columns=f"{c}_{df[c].astype(str).value_counts().index[0]}") for c in cols], axis=1)
    X.insert(0, "const", 1.0)
    return X


e["anio_c"] = e.ingreso_cama.dt.year.astype(str)
e["espera_est"] = ((e.espera_cama_h.fillna(e.espera_cama_h.median()) - e.espera_cama_h.mean()) / e.espera_cama_h.std())
filas = []
for etiqueta, df, cols, extra in [("todas las estancias", e, ["grupo_edad", "sexo", "tipo", "franja", "anio_c"], ["espera_est"]),
                                  ("solo con diagnóstico", e[e.con_dx], ["grupo_edad", "sexo", "tipo", "franja", "anio_c", "categoria_dx"], ["espera_est"])]:
    for objetivo, col in [("larga (>14 d)", "larga"), ("muy larga (>30 d)", "muy_larga")]:
        X = pd.concat([dummies(df, cols), df[extra].astype(float)], axis=1)
        bb, se, p = logit(X, df[col].astype(float).values)
        pos, neg = df[col].values, ~df[col].values
        rank = pd.Series(p).rank().values
        auc = (rank[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * neg.sum())
        for v in X.columns[1:]:
            filas.append(dict(modelo=etiqueta, objetivo=objetivo, variable=v, odds_ratio=round(float(np.exp(bb[v])), 2), ic_bajo=round(float(np.exp(bb[v] - 1.96 * se[v])), 2),
                              ic_alto=round(float(np.exp(bb[v] + 1.96 * se[v])), 2), auc_modelo=round(auc, 3), n=len(df), casos=int(pos.sum())))
odds = pd.DataFrame(filas)
odds.to_csv(TABLAS / "disparadas_odds.csv", index=False)
print("\nRAZONES DE PROBABILIDADES (todas las estancias; larga >14 d)")
o = odds[(odds.modelo == "todas las estancias") & (odds.objetivo.str.startswith("larga"))]
print(o[["variable", "odds_ratio", "ic_bajo", "ic_alto"]].to_string(index=False), "\nAUC:", o.auc_modelo.iloc[0])
print("\nmuy larga (>30 d), variables mas fuertes:")
o2 = odds[(odds.modelo == "todas las estancias") & (odds.objetivo.str.startswith("muy"))].sort_values("odds_ratio", ascending=False)
print(o2.head(6)[["variable", "odds_ratio", "ic_bajo", "ic_alto"]].to_string(index=False), "\nAUC:", o2.auc_modelo.iloc[0])
dxo = odds[(odds.modelo == "solo con diagnóstico") & (odds.objetivo.str.startswith("larga")) & odds.variable.str.startswith("categoria_dx")].sort_values("odds_ratio", ascending=False)
print("\ndiagnostico (solo con diagnostico, larga):")
print(dxo[["variable", "odds_ratio", "ic_bajo", "ic_alto"]].head(5).to_string(index=False), "\n ...\n", dxo[["variable", "odds_ratio", "ic_bajo", "ic_alto"]].tail(3).to_string(index=False))

# ---------------------------------------------------------------- 3. que les pasa (si esta el lote 5)
q_proc, q_lab = CRUDOS / "auditoria_bd" / "Q01_procedimientos_por_estancia.csv", CRUDOS / "auditoria_bd" / "Q02_laboratorios_primeras_48h_por_estancia.csv"
if q_proc.exists() and q_lab.exists():
    print("\n--- PARTE 3: procedimientos y laboratorios ---")
    # cada visita (incluidas las copias que el pipeline no conserva) se lleva a su raiz y de ahi a su estancia
    cop = pd.read_csv(PROC / "copias.csv", usecols=["visit_occurrence_id", "raiz_id"])
    epi = pd.read_csv(PROC / "episodios.csv", usecols=["visit_occurrence_id", "estancia_id"]).drop_duplicates("visit_occurrence_id")
    todos = cop.merge(epi.rename(columns={"visit_occurrence_id": "raiz_id"}), on="raiz_id")[["visit_occurrence_id", "estancia_id"]]
    todos = pd.concat([todos, epi]).drop_duplicates("visit_occurrence_id")
    real = e[["estancia_id", "persona_real", "larga", "muy_larga"]].drop_duplicates("estancia_id")
    nombres = {}
    for ruta, tipo in [(q_proc, "procedimiento"), (q_lab, "laboratorio_48h")]:
        dfx = pd.read_csv(ruta)
        dfx = dfx.merge(todos, on="visit_occurrence_id").merge(real, on="estancia_id")
        propia = dfx.person_id == dfx.persona_real
        dfx = dfx[propia | dfx.persona_real.isna()]              # solo las filas de la persona real (o todas si no se identifico)
        pres = dfx.groupby(["estancia_id", "concepto"]).size().reset_index()[["estancia_id", "concepto"]]
        pres = pres.merge(real[["estancia_id", "larga", "muy_larga"]], on="estancia_id")
        n_l, n_o = int(real.larga.sum()), int((~real.larga).sum())
        r = pres.groupby("concepto").agg(estancias=("estancia_id", "nunique"), en_largas=("larga", "sum"))
        r["en_otras"] = r.estancias - r.en_largas
        r["pct_largas"], r["pct_otras"] = 100 * r.en_largas / n_l, 100 * r.en_otras / n_o
        r["razon"] = (r.pct_largas / r.pct_otras.replace(0, np.nan)).round(2)
        r["tipo"] = tipo
        r = r[r.estancias >= 100].reset_index()
        nom_ruta = CRUDOS / "auditoria_bd" / "Q03_nombres_de_conceptos.csv"
        if nom_ruta.exists():
            r = r.merge(pd.read_csv(nom_ruta).rename(columns={"concept_id": "concepto", "concept_name": "nombre"})[["concepto", "nombre"]], on="concepto", how="left")
        nombres[tipo] = r.sort_values("razon", ascending=False)
        print(tipo, "- conceptos con >=100 estancias:", len(r))
        print(nombres[tipo].head(10)[[c for c in ["concepto", "nombre", "estancias", "pct_largas", "pct_otras", "razon"] if c in nombres[tipo].columns]].round(1).to_string(index=False))
    pd.concat(nombres.values()).to_csv(TABLAS / "disparadas_conceptos.csv", index=False)
else:
    print("\n(Parte 3 pendiente: faltan los CSV del lote 5 de src/auditoria_bd.py)")

# ---------------------------------------------------------------- grafico
fig, ejes = plt.subplots(1, 3, figsize=(17, 4.8))
ejes[0].plot(m_ok.index, m_ok.pct_largas, color="#2a6fb0", lw=1.4, label="% de estancias largas (>14 d)")
ejes[0].plot(m_ok.index, np.polyval(b, x), color="#c0392b", ls="--", lw=1.1, label="tendencia")
ejes[0].plot(m_ok.index, m_ok.pct_muy_largas, color="#d9730d", lw=1.2, label="% de muy largas (>30 d)")
ejes[0].set_title("Cuándo: estancias largas por mes de ingreso", fontsize=10)
ejes[0].legend(fontsize=8)
ejes[0].xaxis.set_major_formatter(mdates.DateFormatter("%m-%Y"))
ejes[0].tick_params(axis="x", labelrotation=30)
pe = perfil[perfil.factor == "edad"]
ejes[1].bar(pe.nivel, pe.pct_largas, color="#2a6fb0")
ejes[1].set_title("Quién: % de estancias largas por edad", fontsize=10)
pt = perfil[perfil.factor == "tipo de visita"]
ejes[2].bar(pt.nivel, pt.pct_largas, color="#d9730d")
ejes[2].set_title("Quién: % de estancias largas por tipo de visita", fontsize=10)
for ax in ejes:
    ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(GRAFICOS / "estancias_disparadas.png", dpi=120)
print("\nguardado: disparadas_*.csv y estancias_disparadas.png")
