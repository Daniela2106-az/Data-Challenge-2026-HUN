"""
espera_con_labs.py  -  version 1 (8-nov-2026)
Exploracion A8 punto 6: ¿QUE PASA DURANTE LA ESPERA DE CAMA? Laboratorios tomados entre la llegada y la asignacion de cama.

IDEA  Si el paciente recibe atencion durante la espera, se deberian ver tomas de laboratorio; si no hay ninguna en muchas horas, la espera es mas pasiva.
METODO  Consulta `espera_labs_por_visita` de sql/espera_labs_y_texto.sql (por visita: tomas distintas, horas con toma, primera y ultima toma entre la primera etapa
  y la primera HOSP). Se une a las estancias unicas del periodo confiable (max entre los registros de la estancia, porque los laboratorios cuelgan sobre todo de la persona real).
LIMITES  Un laboratorio ausente NO prueba que no haya atencion (medicamentos, vigilancia y valoraciones no dejan huella en la base). Solo el 65 % de las estancias tiene
  algun laboratorio en toda la hospitalizacion. Asociacion, no causa.
ENTRADAS  datos/crudos/consultas/espera_labs_por_visita.csv, datos/procesados/tabla_episodios.parquet
SALIDAS   resultados/tablas/espera_con_labs_por_banda.csv ; datos/procesados/espera_con_labs_por_estancia.csv (por estancia, fuera de git)
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
l = pd.read_csv(RAIZ / "datos/crudos/consultas/espera_labs_por_visita.csv", parse_dates=["t0", "th", "primera_toma", "ultima_toma"])
t = pd.read_parquet(RAIZ / "datos/procesados/tabla_episodios.parquet",
                    columns=["visit_occurrence_id", "estancia_id", "hospitalizado", "ini_est", "ini_hosp_est", "espera_cama_h", "ini"])
t = t[t.hospitalizado & t.estancia_id.notna() & (t.ini >= "2023-02-01") & (t.ini < "2026-04-10")]
m = t.merge(l, on="visit_occurrence_id", how="left")
m["tiene"] = m.n_tomas.notna()
g = m.groupby("estancia_id").agg(espera=("espera_cama_h", "max"), tiene=("tiene", "max"), n_tomas=("n_tomas", "max"),
                                 n_horas=("n_horas_con_toma", "max"), prim=("primera_toma", "min"), ult=("ultima_toma", "max"),
                                 t0=("ini_est", "min"), th=("ini_hosp_est", "max")).reset_index()
g = g[g.espera.notna() & (g.espera > 0)].copy()
g["tiene"] = g.tiene.astype(bool)
g["prim_h"] = (g.prim - g.t0).dt.total_seconds() / 3600
g["ult_antes_h"] = (g.th - g.ult).dt.total_seconds() / 3600
g["tomas_x24h"] = g.n_tomas.fillna(0) / (g.espera / 24)
g["frac_horas"] = (g.n_horas.fillna(0) / np.ceil(g.espera)).clip(upper=1)
g["banda"] = pd.cut(g.espera, [0, 6, 12, 24, 48, 72, 1e9], labels=["<6h", "6-12h", "12-24h", "24-48h", "48-72h", ">72h"])
r = g.groupby("banda", observed=True).apply(lambda d: pd.Series({
    "estancias": len(d), "con_algun_lab_pct": 100 * d.tiene.mean(), "tomas_por_24h_media": d.tomas_x24h.mean(),
    "horas_con_toma_pct_de_la_espera": 100 * d.frac_horas.mean(), "primera_toma_mediana_h": d.prim_h.median(),
    "ultima_toma_antes_de_cama_mediana_h": d.ult_antes_h.median(), "horas_espera": d.espera.sum()}), include_groups=False).round(1)
print(r.to_string())
print(f"\nglobal: {len(g):,} estancias, {g.tiene.mean():.1%} con algun laboratorio durante la espera, {g.espera.sum():,.0f} horas de espera")
x = g[(g.espera > 24) & g.tiene]
print(f"espera > 24 h con laboratorio: la ultima toma fue > 12 h antes de la cama en {(x.ult_antes_h > 12).mean():.0%} y > 24 h antes en {(x.ult_antes_h > 24).mean():.0%}")
r.to_csv(RAIZ / "resultados/tablas/espera_con_labs_por_banda.csv")
g.to_csv(RAIZ / "datos/procesados/espera_con_labs_por_estancia.csv", index=False)
