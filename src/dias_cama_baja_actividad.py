"""
dias_cama_baja_actividad.py  -  version 1 (4-nov-2026)
Exploracion 3: DIAS-CAMA DE BAJA ACTIVIDAD CLINICA (posible estancia evitable).

IDEA
  Para cada estancia se mide la huella clinica registrada en la base: dias con al menos un laboratorio sobre el total de dias en cama,
  marca de UCI ("Admission to adult intensive care unit") y atencion de nutricion hospitalaria (S01_actividad_por_estancia.csv, lote 3 de la auditoria).
  Una estancia larga con muy pocos dias con laboratorio y sin UCI ni nutricion es un candidato a "cama ocupada con poca actividad aguda"
  (esperando traslado, tramites, cuidados de baja complejidad). Se convierte en camas equivalentes (dias-cama / dias del periodo).

QUE ES Y QUE NO ES
  - Es una COTA DESCRIPTIVA de camas con poca actividad clinica registrada, no un diagnostico de estancia evitable: un paciente puede recibir
    antibioticos, rehabilitacion o cuidados de enfermeria que no dejan laboratorios, y un paciente estable no necesita laboratorio diario.
  - Los laboratorios de S01 se contaron en todas las visitas gemelas de la estancia (antes de la regla de persona real): pueden incluir los de la otra persona.
  - Se une a nuestras estancias por (inicio, fin) de cama: coincide el 87 %.
  - Asociacion, no causa. Periodo: estancias que empiezan del 1-feb-2023 al 9-abr-2026 y terminan antes del 10-abr-2026.

CATEGORIAS (de menor a mayor actividad)
  sin huella      : sin laboratorio, ni UCI ni nutricion
  baja actividad  : estancia de 7 dias o mas, laboratorio en menos del 25 % de los dias, sin UCI
  activa          : el resto (estancias cortas con huella o con laboratorio frecuente)

ENTRADAS  datos/crudos/auditoria_bd/S01_actividad_por_estancia.csv, datos/procesados/tabla_episodios.parquet
SALIDAS   resultados/tablas/dias_cama_actividad_por_anio.csv, dias_cama_baja_actividad_perfil.csv ; resultados/graficos/dias_cama_baja_actividad.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
TABLAS, GRAF = RAIZ / "resultados" / "tablas", RAIZ / "resultados" / "graficos"
INI, FIN = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10")
pd.set_option("display.width", 200)

s = pd.read_csv(RAIZ / "datos/crudos/auditoria_bd/S01_actividad_por_estancia.csv", parse_dates=["ini", "fin"])
t = pd.read_parquet(RAIZ / "datos/procesados/tabla_episodios.parquet",
                    columns=["estancia_unica", "hospitalizado", "ini_hosp_est", "fin_hosp_est", "edad", "sexo", "tipo_visita", "categoria_dx", "grupo_edad"])
e = t[t.estancia_unica & t.hospitalizado]
m = s.merge(e, left_on=["ini", "fin"], right_on=["ini_hosp_est", "fin_hosp_est"], how="inner")
m = m[(m.ini >= INI) & (m.fin < FIN)].copy()
m["dias"] = (m.fin - m.ini).dt.total_seconds() / 86400
m["anio"] = m.ini.dt.year
m["cobertura_lab"] = (m.dias_con_lab / m.dias.clip(lower=1)).clip(upper=1)
m["cat"] = np.where((m.n_lab == 0) & (m.n_uci == 0) & (m.n_nutricion == 0), "sin huella",
                    np.where((m.dias >= 7) & (m.cobertura_lab < .25) & (m.n_uci == 0), "baja actividad", "activa"))
print(f"estancias analizadas: {len(m)} (de {len(s)} en S01; union por inicio y fin)  | dias-cama totales: {m.dias.sum():.0f}")

# ------------------------------------------------------------------ por ano
filas = []
for a, d in m.groupby("anio"):
    dias_periodo = {2023: (pd.Timestamp('2024-01-01') - INI).days, 2024: 366, 2025: 365}.get(a, (FIN - pd.Timestamp('2026-01-01')).days)
    for c, g in d.groupby("cat"):
        filas.append(dict(anio=a, categoria=c, estancias=len(g), pct_estancias=round(100 * len(g) / len(d), 1), dias_cama=round(g.dias.sum()),
                          pct_dias_cama=round(100 * g.dias.sum() / d.dias.sum(), 1), camas_equivalentes=round(g.dias.sum() / dias_periodo, 1)))
A = pd.DataFrame(filas)
A.to_csv(TABLAS / "dias_cama_actividad_por_anio.csv", index=False)
print("\nDIAS-CAMA POR NIVEL DE ACTIVIDAD CLINICA REGISTRADA")
print(A.pivot(index="anio", columns="categoria", values="camas_equivalentes").to_string(), "(camas equivalentes)")
print(A.pivot(index="anio", columns="categoria", values="pct_dias_cama").to_string(), "(% de los dias-cama)")

# ------------------------------------------------------------------ estancias largas (>14 dias): cuanto es de baja actividad
L = m[m.dias > 14]
print(f"\nEstancias de mas de 14 dias: {len(L)}")
r = L.groupby("anio").apply(lambda d: pd.Series(dict(estancias=len(d), pct_baja_actividad=round(100 * (d.cat == "baja actividad").mean(), 1),
                                                     dias_cama=round(d.dias.sum()), camas_baja_actividad=round(d[d.cat == "baja actividad"].dias.sum() / {2023: 334, 2024: 366, 2025: 365}.get(d.name, 99), 1),
                                                     cobertura_lab_mediana=round(d.cobertura_lab.median(), 2))), include_groups=False)
print(r.to_string())

# ------------------------------------------------------------------ perfil de la baja actividad entre las estancias de 7 dias o mas
G = m[m.dias >= 7].copy()
G["baja"] = G.cat == "baja actividad"
filas = []
for f in ["grupo_edad", "tipo_visita", "sexo", "categoria_dx"]:
    g = G[G[f].notna()].groupby(f).agg(estancias=("baja", "size"), pct_baja=("baja", lambda x: round(100 * x.mean(), 1)),
                                        camas_eq=("dias", lambda x: 0))
    g["dias_cama_baja"] = G[G.baja & G[f].notna()].groupby(f).dias.sum().round()
    g["dias_cama_baja"] = g.dias_cama_baja.fillna(0)
    g = g[g.estancias >= 30].reset_index().rename(columns={f: "nivel"}).drop(columns="camas_eq")
    g.insert(0, "factor", f)
    filas.append(g)
P = pd.concat(filas)
P.to_csv(TABLAS / "dias_cama_baja_actividad_perfil.csv", index=False)
print("\nPERFIL: % de estancias de 7+ dias con baja actividad (solo grupos con >= 30 estancias)")
for f in P.factor.unique():
    print(P[P.factor == f].sort_values("pct_baja", ascending=False).head(6).to_string(index=False))

fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
pv = A.pivot(index="anio", columns="categoria", values="camas_equivalentes")[["activa", "baja actividad", "sin huella"]]
pv.plot(kind="bar", stacked=True, ax=ax[0], color=["#2a6fb0", "#d9730d", "#bdbdbd"])
ax[0].set_ylabel("camas equivalentes (dias-cama / dias del periodo)")
ax[0].set_title("Camas por nivel de actividad clinica registrada", fontsize=10)
ax[0].tick_params(axis="x", rotation=0)
ax[1].hist(L.cobertura_lab, bins=20, color="#2a6fb0")
ax[1].axvline(.25, color="#d9730d", ls="--")
ax[1].set_xlabel("dias con laboratorio / dias de estancia (estancias de mas de 14 dias)")
ax[1].set_title("Cobertura de laboratorio en estancias largas", fontsize=10)
plt.tight_layout()
plt.savefig(GRAF / "dias_cama_baja_actividad.png", dpi=130)
print("\nguardado: dias_cama_*.csv y dias_cama_baja_actividad.png")
