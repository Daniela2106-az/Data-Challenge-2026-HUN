"""
exportar_para_equipo.py  -  tablas listas para el equipo (v2, 22-oct-2026)
Corre DESPUES de analisis_etapas.py y preparar_variables.py. Deja en datos/procesados/para_equipo/ las tablas
que usan los modelos y Power BI. Esa carpeta NO se sube a git: se comparte por el drive privado del equipo.

QUE CAMBIO EN v2 (22-oct): ESTANCIAS GEMELAS
  El 41 % de los episodios hospitalizados tiene otro episodio con exactamente el mismo inicio y fin de cama:
  es la misma estancia replicada entre dos personas distintas. Contarlas todas inflaba los ingresos por dia
  (27,7 en vez de ~22), la ocupacion (~146 en vez de ~113 camas) y la espera de cama (mediana 22,4 h en vez de 18 h).
  Ahora estancias_hospitalizacion.csv trae UNA fila por estancia (se queda el episodio de menor
  visit_occurrence_id) y n_registros indica cuantos registros tenia esa estancia. El panel diario cuenta
  ingresos, altas, hospitalizados, espera y ocupacion con esas estancias unicas.
  OJO: la columna `llegadas` sigue contando todos los episodios (puede incluir replicas de otras personas
  que no tienen cama; ver docs/CONTEXTO_TECNICO.md, seccion 4.6).

SALIDAS
  estancias_hospitalizacion.csv  una fila por ESTANCIA en cama: ingreso, alta, horas en cama, n_registros
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
OCUP_DESDE, OCUP_HASTA = "2023-02-01", "2026-04-10"   # mismo rango confiable de preparar_variables.py
K = ["visit_occurrence_id", "episodio"]
LLAVE_ESTANCIA = ["ingreso_cama", "alta"]

ep = pd.read_parquet(PROC / "tabla_episodios.parquet")
bl = pd.read_csv(PROC / "bloques.csv", parse_dates=["ini", "fin"])
hosp = bl[bl.etapa == "HOSP"]

# ---- estancias en cama -------------------------------------------------------------------------
est = hosp.groupby(K).agg(ingreso_cama=("ini", "min"), alta=("fin", "max"),
                          horas_hosp=("horas", "sum"), n_bloques_hosp=("etapa", "size")).reset_index()
# v2.3: el inicio y el fin de cama de cada estancia son los de TODA la estancia (minimo y maximo entre sus registros gemelos, analisis_etapas.py v3.8)
est = est.merge(ep[K + ["ini_hosp_est", "fin_hosp_est", "n_registros_estancia"]], on=K, how="left")
est["ingreso_cama"] = est.ini_hosp_est.fillna(est.ingreso_cama)
est["alta"] = est.fin_hosp_est.fillna(est.alta)
est = est.drop(columns=["ini_hosp_est", "fin_hosp_est"])
est["alta_completa"] = est.alta < pd.Timestamp(OCUP_HASTA)   # las altas posteriores quedan cortadas por la extraccion
cols = ["ini", "hora", "dia_semana_num", "mes", "festivo", "edad", "grupo_edad", "sexo", "tipo_visita",
        "categoria_dx", "n_lab_6h", "espera_cama_h", "espera_mas_24h", "ocup_hosp", "llegadas_6h_previas",
        "ocupacion_confiable", "estancia_unica"]
est = est.merge(ep[K + cols].rename(columns={"ini": "llegada", "hora": "hora_llegada"}), on=K, how="left")

# estancias gemelas: mismo inicio y fin de cama en otro episodio -> se cuenta una vez
est = est.sort_values(K).reset_index(drop=True)
est["n_registros"] = est.n_registros_estancia
est = est.drop(columns="n_registros_estancia")
n_antes = len(est)
est = est[est.estancia_unica].reset_index(drop=True)   # v2.1: el registro conservado por preparar_variables.py (el de mas informacion)
est.to_csv(SALIDA / "estancias_hospitalizacion.csv", index=False)

# ---- panel diario ------------------------------------------------------------------------------
dias = pd.date_range(OCUP_DESDE, pd.Timestamp(OCUP_HASTA) - pd.Timedelta(days=1))
sd = pd.read_csv(PROC / "serie_diaria.csv", parse_dates=["fecha"]).set_index("fecha")
completas = est[est.alta_completa]

# ocupacion con estancias unicas: pacientes en cama al final de cada hora (los ingresados antes de
# OCUP_DESDE entran por sus eventos, asi que el arranque no queda en cero)
horas = pd.date_range(est.ingreso_cama.min().floor("h"), est.alta.max().floor("h"), freq="h")
delta = (est.ingreso_cama.dt.floor("h").value_counts()
         .sub(est.alta.dt.floor("h").value_counts(), fill_value=0)
         .reindex(horas, fill_value=0))
ocup_h = delta.cumsum()
ocup_d = ocup_h.groupby(ocup_h.index.normalize()).agg(["mean", "max"])

d = pd.DataFrame(index=dias)
d.index.name = "fecha"
d["llegadas"] = sd.llegadas
# llegadas con atencion: episodios que tienen TU u hospitalizacion (todos menos los que solo tienen la etapa ER de admision). El 29-abr-2026
# cambia el registro de la etapa ER y esta serie depende menos de ella (docs/CONTEXTO_TECNICO.md 4.7)
_con_at = ep[ep.ruta != "ER"].ini.dt.normalize().value_counts()
d["llegadas_con_atencion"] = _con_at.reindex(dias, fill_value=0)
d["hospitalizados"] = est.llegada.dt.normalize().value_counts().reindex(dias, fill_value=0)
d["ingresos_a_cama"] = est.ingreso_cama.dt.normalize().value_counts().reindex(dias, fill_value=0)
d["altas"] = completas.alta.dt.normalize().value_counts().reindex(dias, fill_value=0)
d["altas_antes_mediodia"] = completas[completas.alta.dt.hour < 12].alta.dt.normalize().value_counts().reindex(dias, fill_value=0)
d["ocup_hosp_media"] = ocup_d["mean"].reindex(dias)
d["ocup_hosp_max"] = ocup_d["max"].reindex(dias)
esp = est.dropna(subset=["espera_cama_h"]).assign(fecha=lambda x: x.llegada.dt.normalize())
d["espera_cama_mediana_h"] = esp.groupby("fecha").espera_cama_h.median().reindex(dias)
d["n_espera"] = esp.groupby("fecha").size().reindex(dias, fill_value=0)
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

print(f"estancias_hospitalizacion.csv: {len(est)} estancias unicas ({n_antes - len(est)} registros gemelos quitados de {n_antes}) "
      f"| con alta completa: {int(est.alta_completa.sum())}")
print(f"panel_diario.csv: {len(d)} dias ({d.index.min().date()} a {d.index.max().date()})")
print(d[["llegadas", "hospitalizados", "ingresos_a_cama", "altas", "altas_antes_mediodia",
         "ocup_hosp_media", "espera_cama_mediana_h"]].describe().round(1).to_string())
