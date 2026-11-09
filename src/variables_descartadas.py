"""
variables_descartadas.py  -  version 1 (8-nov-2026)
Tarea A6: ¿mejoran el estimador los datos que aun no usa? Se prueban tres grupos que se conocen en el momento, sin trampa, sobre el estimador final
(un modelo por momento antes de 12 h, solo historial despues, con mas peso en lo reciente), con la misma prueba (entrenamiento hasta jun-2025, prueba
jul-2025 a 9-abr-2026) y diferencia pareada con intervalo del 95 % (bootstrap por semanas):
  - visitas previas a urgencias (no solo hospitalizaciones): cuantas, hace cuantos dias, reingreso a 72 h y 30 dias, ruta y estado de la anterior;
  - congestion de urgencias al llegar: llegadas de las 6 y 24 h previas, pacientes en atencion en urgencias;
  - calendario: festivo, dia no habil, mes.
Se descarto antes de probar la hora del primer diagnostico (dx_por_visita.csv): coincide con la llegada en la mitad de los casos y en el 10 % es semanas
antes (visitas copia), asi que no marca un momento real.
RESULTADO (8-nov): ninguno ayuda (de -0,3 a +0,5 puntos, ningun intervalo excluye el 0). No se agregan al estimador.
ENTRADAS  tabla_episodios.parquet (HUN_PROCESADOS); visit_detail.csv y procedimientos_por_estancia.csv (HUN_CRUDOS)
SALIDA    HUN_TABLAS/variables_descartadas.csv
COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... HUN_CRUDOS=... python3 src/variables_descartadas.py   (~5 min)
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce

d, h, rejilla, estado = ce.preparar()
RUTAS = {"TU": 0, "TU > HOSP": 1, "ER": 2}
d["anterior_ruta_cod"] = np.where(d.anterior_ruta.isna(), np.nan, d.anterior_ruta.map(RUTAS).fillna(3))
d["anterior_medida"] = np.where(d.anterior_estado.isna(), np.nan, (d.anterior_estado == "medida").astype(float))
for c in ["reingreso_72h", "reingreso_30d", "tras_registro_vacio", "festivo", "dia_no_habil"]:
    d[c] = d[c].astype(float)
GRUPOS = {
    "visitas previas a urgencias": ["n_episodios_previos", "dias_desde_anterior", "reingreso_72h", "reingreso_30d", "anterior_ruta_cod", "anterior_medida", "tras_registro_vacio"],
    "congestion de urgencias al llegar": ["llegadas_6h_previas", "llegadas_24h_previas", "ocup_tu"],
    "calendario (festivo, dia no habil, mes)": ["festivo", "dia_no_habil", "mes"],
}
GRUPOS["los tres juntos"] = sum(GRUPOS.values(), [])
ce.CATEGORICAS.append("anterior_ruta_cod")


def modelo(tr, desde, extra):
    if desde < ce.HORAS_RECORRIDO:
        return ce.entrenar_landmark(tr, rejilla, estado, desde, ce.COLS_M1_FINAL + extra, vida_media_dias=182)
    return ce.entrenar_m1(tr, rejilla, estado, ce.COLS_M1_BASE + ce.HIST + extra, vida_media_dias=182)


tr, te = d[d.ini_est < ce.CORTE].reset_index(drop=True), d[d.ini_est >= ce.CORTE].reset_index(drop=True)
filas = []
for desde in [0, 3, 6, 12, 24]:
    sub = te[te.espera_cama_h > desde].reset_index(drop=True)
    y = np.minimum(sub.espera_cama_h.to_numpy() - desde, ce.MAX_H)
    sem = sub.ini_est.dt.to_period("W").astype(str).to_numpy()
    lg = ce.perdida_por_caso(y, ce.referencias(tr, sub, desde)[0])
    lb = ce.perdida_por_caso(y, ce.predecir_m1(modelo(tr, desde, []), sub, rejilla, estado, desde))
    filas.append({"H": desde, "variante": "estimador actual", "mejora_pct": round(100 * (1 - lb.mean() / lg.mean()), 1)})
    for nombre, cols in GRUPOS.items():
        p = ce.predecir_m1(modelo(tr, desde, cols), sub, rejilla, estado, desde)
        lp = ce.perdida_por_caso(y, p)
        lo, hi = ce.intervalo_mejora(sem, lp, lb)
        filas.append({"H": desde, "variante": "+ " + nombre, "mejora_pct": round(100 * (1 - lp.mean() / lg.mean()), 1),
                      "vs_actual_pct": round(100 * (1 - lp.mean() / lb.mean()), 1), "ic95": f"{lo:.1f} a {hi:.1f}",
                      "debajo_p90": round(100 * np.mean(y <= p[:, 3]), 1)})
    print(pd.DataFrame([f for f in filas if f["H"] == desde]).to_string(index=False), flush=True)
pd.DataFrame(filas).to_csv(ce.TABLAS / "variables_descartadas.csv", index=False)
