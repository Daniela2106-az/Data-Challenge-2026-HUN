"""
efecto_fin_de_semana.py  -  version 1 (4-nov-2026)
Exploracion 4: EFECTO DEL FIN DE SEMANA Y DE LOS FESTIVOS en altas, ingresos a cama, espera y estancia.

PREGUNTAS
  1. ¿Se dan menos altas en fin de semana y festivos? (altas por dia, y por cada 100 camas ocupadas)
  2. ¿Se asignan menos camas en esos dias?
  3. ¿Esperan mas quienes llegan en esos dias?
  4. ¿Se quedan mas los que ingresan a cama en viernes o sabado? (modelo sobre log(estancia), con edad, tipo de visita y ano)
  5. Orden de magnitud: ¿cuantas camas equivalentes ocupa el retraso de altas del fin de semana al lunes?

LIMITES
  - Altas = fin de la estancia registrada (el HUN confirmo que hay horarios y costumbres de alta, sin detalle).
  - El orden de magnitud del punto 5 supone que cada alta que no ocurre en sabado o domingo se traslada al lunes: es un supuesto, no una medicion.
  - Asociacion, no causa. Periodo: 1-feb-2023 a 9-abr-2026 sin el 28 y 29 de marzo de 2026 (caida del sistema).

ENTRADAS  datos/procesados/para_equipo/panel_diario.csv, datos/procesados/tabla_episodios.parquet
SALIDAS   resultados/tablas/fin_de_semana_*.csv ; resultados/graficos/efecto_fin_de_semana.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

RAIZ = Path(__file__).resolve().parent.parent
TABLAS, GRAF = RAIZ / "resultados" / "tablas", RAIZ / "resultados" / "graficos"
INI, FIN = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10")
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
pd.set_option("display.width", 200)

p = pd.read_csv(RAIZ / "datos/procesados/para_equipo/panel_diario.csv", parse_dates=["fecha"])
p = p[(p.fecha >= INI) & (p.fecha < FIN) & ~p.fecha.isin(pd.to_datetime(["2026-03-28", "2026-03-29"]))].copy()
p["dow"] = p.fecha.dt.dayofweek
p["tipo"] = np.where(p.festivo.astype(bool) & (p.dow < 5), "festivo entre semana", np.where(p.dow >= 5, "fin de semana", "dia habil"))
p["altas_x100"] = 100 * p.altas / p.ocup_hosp_media

# ---------------------------------------------------------------- 1 y 2. altas e ingresos a cama por dia
print("1-2. ALTAS E INGRESOS A CAMA POR DIA DE LA SEMANA (promedio por dia)")
g = p.groupby("dow").agg(dias=("altas", "size"), altas=("altas", "mean"), altas_por_100_camas=("altas_x100", "mean"), ingresos_a_cama=("ingresos_a_cama", "mean"),
                          llegadas_que_se_hospitalizan=("hospitalizados", "mean"), ocupacion=("ocup_hosp_media", "mean")).round(1)
g.index = DIAS
print(g.to_string())
g.to_csv(TABLAS / "fin_de_semana_por_dia.csv")
h = p.groupby("tipo").agg(dias=("altas", "size"), altas=("altas", "mean"), altas_por_100_camas=("altas_x100", "mean"), ingresos_a_cama=("ingresos_a_cama", "mean")).round(1)
print("\nPor tipo de dia:")
print(h.to_string())
h.to_csv(TABLAS / "fin_de_semana_por_tipo_de_dia.csv")
# comparacion con un dia habil, mismo ano, controlando el lunes a viernes
hab = h.loc["dia habil"]
fs = h.loc["fin de semana"]
fe = h.loc["festivo entre semana"]
print(f"\nAltas por 100 camas: dia habil {hab.altas_por_100_camas}, festivo entre semana {fe.altas_por_100_camas} ({100 * (fe.altas_por_100_camas / hab.altas_por_100_camas - 1):+.0f} %), "
      f"fin de semana {fs.altas_por_100_camas} ({100 * (fs.altas_por_100_camas / hab.altas_por_100_camas - 1):+.0f} %)")
print(f"Ingresos a cama por dia: habil {hab.ingresos_a_cama}, festivo {fe.ingresos_a_cama} ({100 * (fe.ingresos_a_cama / hab.ingresos_a_cama - 1):+.0f} %), fin de semana {fs.ingresos_a_cama} ({100 * (fs.ingresos_a_cama / hab.ingresos_a_cama - 1):+.0f} %)")

# ---------------------------------------------------------------- 3. espera segun el dia de llegada
t = pd.read_parquet(RAIZ / "datos/procesados/tabla_episodios.parquet",
                    columns=["estancia_unica", "hospitalizado", "ini", "espera_cama_h", "ini_hosp_est", "fin_hosp_est", "edad", "tipo_visita", "festivo", "sexo"])
e = t[t.estancia_unica & t.hospitalizado & (t.ini >= INI) & (t.ini < FIN)].copy()
e["dow_llegada"] = e.ini.dt.dayofweek
print("\n3. ESPERA DE CAMA SEGUN EL DIA DE LLEGADA (mediana, p90, n)")
w = e.dropna(subset=["espera_cama_h"]).groupby("dow_llegada").espera_cama_h.agg(["median", lambda s: s.quantile(.9), "size"]).round(1)
w.columns = ["mediana_h", "p90_h", "n"]
w.index = DIAS
print(w.to_string())
w.to_csv(TABLAS / "fin_de_semana_espera_por_dia_llegada.csv")

# ---------------------------------------------------------------- 4. estancia segun el dia del ingreso a cama
c = e[e.fin_hosp_est.notna() & (e.fin_hosp_est < FIN)].copy()
c["estancia_h"] = (c.fin_hosp_est - c.ini_hosp_est).dt.total_seconds() / 3600
c = c[c.estancia_h > 0]
c["dow_cama"] = c.ini_hosp_est.dt.dayofweek
c["dia_cama"] = c.dow_cama.map(dict(enumerate(DIAS)))
c["anio"] = c.ini_hosp_est.dt.year.astype(str)
c["ledad"] = c.edad.fillna(c.edad.median())
c["log_est"] = np.log(c.estancia_h)
print("\n4. ESTANCIA SEGUN EL DIA DE INGRESO A CAMA")
q = c.groupby("dia_cama").estancia_h.agg(["median", "mean", "size"]).reindex(DIAS).round(1)
print(q.to_string())
m = smf.ols("log_est ~ C(dia_cama, Treatment('martes')) + C(tipo_visita) + C(anio) + ledad + I(ledad**2)", data=c).fit(cov_type="HC1")
ef = pd.DataFrame({"efecto_pct": 100 * (np.exp(m.params) - 1), "ic_bajo": 100 * (np.exp(m.conf_int()[0]) - 1), "ic_alto": 100 * (np.exp(m.conf_int()[1]) - 1)}).round(1)
ef = ef[ef.index.str.contains("dia_cama")]
ef.index = ef.index.str.extract(r"\[T\.(.*)\]")[0].values
print("\nefecto sobre la estancia frente al martes (controlando tipo de visita, ano y edad):")
print(ef.to_string())
ef.to_csv(TABLAS / "fin_de_semana_efecto_estancia.csv")
# la mediana de la estancia mas alta o mas baja segun el momento del dia no se mezcla con los dias
c["tarde_o_noche"] = c.ini_hosp_est.dt.hour >= 14

# ---------------------------------------------------------------- 5. orden de magnitud
dr = g.altas_por_100_camas
tasa_h = hab.altas_por_100_camas
faltan_sab = max(tasa_h - dr["sabado"], 0) / 100 * g.ocupacion["sabado"]
faltan_dom = max(tasa_h - dr["domingo"], 0) / 100 * g.ocupacion["domingo"]
dias_cama_extra = 2 * faltan_sab + 1 * faltan_dom       # sabado->lunes: 2 dias; domingo->lunes: 1 dia
print(f"\n5. ORDEN DE MAGNITUD (supuesto: lo que falta de altas en sabado y domingo se traslada al lunes)")
print(f"altas que 'faltan' por sabado: {faltan_sab:.1f}; por domingo: {faltan_dom:.1f}; dias-cama extra por semana: {dias_cama_extra:.0f}; camas equivalentes: {dias_cama_extra / 7:.1f}")
pd.DataFrame([dict(altas_faltan_sabado=round(faltan_sab, 1), altas_faltan_domingo=round(faltan_dom, 1), dias_cama_extra_por_semana=round(dias_cama_extra),
                   camas_equivalentes=round(dias_cama_extra / 7, 1))]).to_csv(TABLAS / "fin_de_semana_orden_de_magnitud.csv", index=False)

fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
cols = ["#2a6fb0"] * 5 + ["#d9730d"] * 2
ax[0].bar(DIAS, g.altas_por_100_camas, color=cols)
ax[0].set_title("Altas por cada 100 camas ocupadas", fontsize=10)
ax[1].bar(DIAS, g.ingresos_a_cama, color=cols)
ax[1].set_title("Ingresos a cama por dia", fontsize=10)
ax[2].bar(DIAS, w.mediana_h.values, color=cols)
ax[2].set_title("Espera mediana de cama segun el dia de llegada (h)", fontsize=10)
for a in ax:
    a.tick_params(axis="x", rotation=35)
plt.tight_layout()
plt.savefig(GRAF / "efecto_fin_de_semana.png", dpi=130)
print("\nguardado: fin_de_semana_*.csv y efecto_fin_de_semana.png")
