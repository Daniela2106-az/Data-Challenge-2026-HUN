"""
prueba_quincenas.py  -  version 1 (8-nov-2026)
Exploracion A8 (datos externos, parte de calendario): ¿mejora el pronostico de demanda si se agregan las QUINCENAS (dias de pago)?

METODO  Mismo retroceso (backtest) que elegir_tau.py, con y sin variables de quincena sobre el calendario de modelo_pronostico.py.
  - quincena:   15, 16, 30, 31 y 1 de cada mes (pago de quincena y dia despues)
  - fin_mes:    dias 29 a 31 (menos los de arriba no se separan; es una alternativa)
  Se compara el error (WAPE) en validacion (destinos hasta 2025-12-31) y prueba (2026-01-01 a 9-abr-2026). Sin elegir con la prueba.
LIMITES  Los residuos por dia del mes son de ±2–3 % con ~40 observaciones por dia (ruido esperable). No se prueba el 'pago de prima' (junio, diciembre).
ENTRADAS  datos/procesados/para_equipo/panel_diario.csv      SALIDAS  resultados/tablas/prueba_quincenas.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

import modelo_pronostico as mp

RAIZ = Path(__file__).resolve().parent.parent
cal0, cols0 = mp.calendario, list(mp.COLUMNAS)


def con_extra(nombre):
    def cal(idx):
        c = cal0(idx)                               # cal0 devuelve solo las columnas originales
        d = pd.DatetimeIndex(idx).day
        if nombre == "quincena":
            c["quincena"] = np.isin(d, [15, 16, 30, 31, 1]).astype(float)
        if nombre == "fin_mes":
            c["fin_mes"] = (d >= 29).astype(float)
        return c
    return cal


def wape(bt, f, a, b):
    t = bt[f & (bt.lead >= a) & (bt.lead <= b)]
    return round(100 * (t.real - t.pronostico).abs().sum() / t.real.sum(), 2)


panel = mp.cargar_panel()
filas = []
for obj in mp.OBJETIVOS:
    for nombre in ["base", "quincena", "fin_mes"]:
        mp.calendario = cal0 if nombre == "base" else con_extra(nombre)
        bt = mp.retroceso(panel[obj])
        val, pru = bt.fecha <= "2025-12-31", (bt.fecha >= "2026-01-01") & (bt.fecha < mp.INICIO_QUIEBRE)
        filas.append({"serie": obj, "calendario": nombre, "val 1-7 d": wape(bt, val, 1, 7), "val 8-30 d": wape(bt, val, 8, 30),
                      "val 92-365 d": wape(bt, val, 92, 365), "prueba 1-7 d": wape(bt, pru, 1, 7), "prueba 8-30 d": wape(bt, pru, 8, 30)})
d = pd.DataFrame(filas)
print(d.to_string(index=False))
d.to_csv(RAIZ / "resultados" / "tablas" / "prueba_quincenas.csv", index=False)
