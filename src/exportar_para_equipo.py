"""
exportar_para_equipo.py  -  tablas listas para el equipo (21-oct-2026)
Corre DESPUES de analisis_etapas.py y preparar_variables.py. Deja en datos/procesados/para_equipo/ las tablas
que usan los modelos y Power BI. Esa carpeta NO se sube a git: se comparte por el drive privado del equipo.

SALIDAS
  estancias_hospitalizacion.csv  una fila por episodio hospitalizado: ingreso a cama, alta, horas en cama,
                                 y las variables del paciente (insumo del modelo de camas y la simulacion)
  panel_diario.csv               una fila por dia: llegadas, hospitalizados, ingresos a cama, altas, ocupacion,
                                 espera de cama y calendario (insumo del Modelo A y de la deteccion de dias atipicos)
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
SALIDA = PROC / "para_equipo"
SALIDA.mkdir(parents=True, exist_ok=True)
OCUP_DESDE, OCUP_HASTA = "2023-02-01", "2026-06-01"   # mismo rango confiable de preparar_variables.py
K = ["visit_occurrence_id", "episodio"]

ep = pd.read_parquet(PROC / "tabla_episodios.parquet")
bl = pd.read_csv(PROC / "bloques.csv", parse_dates=["ini", "fin"])
hosp = bl[bl.etapa == "HOSP"]

# ---- estancias en cama -------------------------------------------------------------------------
est = hosp.groupby(K).agg(ingreso_cama=("ini", "min"), alta=("fin", "max"),
                          horas_hosp=("horas", "sum"), n_bloques_hosp=("etapa", "size")).reset_index()
est["alta_completa"] = est.alta < pd.Timestamp(OCUP_HASTA)   # las altas posteriores quedan cortadas por la extraccion
cols = ["ini", "hora", "dia_semana_num", "mes", "festivo", "edad", "grupo_edad", "sexo", "tipo_visita",
        "categoria_dx", "n_lab_6h", "espera_cama_h", "espera_mas_24h", "ocup_hosp", "llegadas_6h_previas",
        "ocupacion_confiable"]
est = est.merge(ep[K + cols].rename(columns={"ini": "llegada", "hora": "hora_llegada"}), on=K, how="left")
est.to_csv(SALIDA / "estancias_hospitalizacion.csv", index=False)

# ---- panel diario ------------------------------------------------------------------------------
dias = pd.date_range(OCUP_DESDE, pd.Timestamp(OCUP_HASTA) - pd.Timedelta(days=1))
sd = pd.read_csv(PROC / "serie_diaria.csv", parse_dates=["fecha"]).set_index("fecha")
completas = est[est.alta_completa]
d = pd.DataFrame(index=dias)
d.index.name = "fecha"
d["llegadas"] = sd.llegadas
d["hospitalizados"] = sd.llegadas_que_se_hospitalizan
d["ingresos_a_cama"] = est.ingreso_cama.dt.normalize().value_counts().reindex(dias, fill_value=0)
d["altas"] = completas.alta.dt.normalize().value_counts().reindex(dias, fill_value=0)
d["altas_antes_mediodia"] = completas[completas.alta.dt.hour < 12].alta.dt.normalize().value_counts().reindex(dias, fill_value=0)
d["ocup_hosp_media"] = sd.ocup_hosp_media
d["ocup_hosp_max"] = sd.ocup_hosp_max
d["espera_cama_mediana_h"] = sd.espera_cama_mediana_h
d["n_espera"] = sd.n_espera
d["dia_semana_num"] = d.index.dayofweek
d["mes"] = d.index.month
try:
    import holidays
    fest = holidays.Colombia(years=range(d.index.min().year, d.index.max().year + 1))
    d["festivo"] = d.index.date.astype(object)
    d["festivo"] = [x in fest for x in d.festivo]
except ImportError:
    d["festivo"] = np.nan
d["dia_no_habil"] = (d.dia_semana_num >= 5) | (d.festivo == True)  # noqa: E712
d.round(2).to_csv(SALIDA / "panel_diario.csv")

print(f"estancias_hospitalizacion.csv: {len(est)} filas | con alta completa: {int(est.alta_completa.sum())}")
print(f"panel_diario.csv: {len(d)} dias ({d.index.min().date()} a {d.index.max().date()})")
print(d[["llegadas", "hospitalizados", "ingresos_a_cama", "altas", "altas_antes_mediodia"]].describe().round(1).to_string())
