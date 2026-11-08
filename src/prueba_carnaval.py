"""
prueba_carnaval.py  -  version 1 (8-nov-2026)
C4 opcional: ¿el Carnaval de Barranquilla afecta distinto cada dia (sabado, domingo, lunes, martes)? El modelo vigente usa UNA variable para los 4 dias.

METODO  (1) Regresion de Poisson (statsmodels) con el calendario de modelo_pronostico.py, cambiando la variable `carnaval` por una por dia: efecto y IC 95 % de cada dia.
        (2) Retroceso (backtest) de modelo_pronostico.py con una variable unica frente a variables por dia: error WAPE en los dias de Carnaval y en todos los dias.
LIMITES  Solo hay 4 Carnavales en el periodo confiable (2023 a 2026), asi que cada coeficiente por dia sale de 4 observaciones: los IC son anchos y separar por dia puede
  ajustar ruido. El lunes y el martes de Carnaval no son festivos nacionales (el calendario de `holidays` Colombia no los incluye).
ENTRADAS  datos/procesados/para_equipo/panel_diario.csv      SALIDAS  resultados/tablas/prueba_carnaval.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dateutil.easter import easter

import modelo_pronostico as mp

RAIZ = Path(__file__).resolve().parent.parent
cal0 = mp.calendario
NOMBRES = ["sab", "dom", "lun", "mar"]


def dias_carnaval(idx):
    """Devuelve una tabla con una columna por dia de Carnaval (sabado, domingo, lunes, martes = Pascua -50, -49, -48, -47)."""
    idx = pd.DatetimeIndex(idx)
    c = pd.DataFrame(0.0, index=idx, columns=[f"carnaval_{n}" for n in NOMBRES])
    for a in range(idx.min().year, idx.max().year + 1):
        e = pd.Timestamp(easter(a))
        for k, n in zip([50, 49, 48, 47], NOMBRES):
            d = e - pd.Timedelta(days=k)
            if d in c.index:
                c.loc[d, f"carnaval_{n}"] = 1.0
    return c


def cal_por_dia(idx):
    c = cal0(idx).drop(columns="carnaval")
    return c.join(dias_carnaval(c.index))


panel = mp.cargar_panel()
filas = []
for obj in mp.OBJETIVOS:
    s = panel[obj].dropna()
    s = s[s.index < mp.INICIO_QUIEBRE]
    X = cal_por_dia(s.index)
    r = sm.GLM(s.values, X.values, family=sm.families.Poisson()).fit(cov_type="HC0")
    for i, n in enumerate(X.columns):
        if n.startswith("carnaval_"):
            b, se = r.params[i], r.bse[i]
            filas.append({"serie": obj, "variable": n, "efecto_pct": round(100 * (np.exp(b) - 1), 1),
                          "ic95_bajo": round(100 * (np.exp(b - 1.96 * se) - 1), 1), "ic95_alto": round(100 * (np.exp(b + 1.96 * se) - 1), 1)})
coef = pd.DataFrame(filas)
print("EFECTO DEL CARNAVAL POR DIA (% sobre lo esperado por calendario y nivel):")
print(coef.to_string(index=False))


def wape(t):
    return round(100 * (t.real - t.pronostico).abs().sum() / t.real.sum(), 2) if len(t) else np.nan


res = []
for obj in mp.OBJETIVOS:
    for nombre, f in [("una variable (vigente)", cal0), ("una por dia", cal_por_dia)]:
        mp.calendario = f
        bt = mp.retroceso(panel[obj])
        bt = bt[bt.fecha < mp.INICIO_QUIEBRE]
        cv = dias_carnaval(bt.fecha.drop_duplicates()).sum(axis=1)
        es_carn = bt.fecha.isin(cv[cv > 0].index)
        c1 = bt[bt.lead.between(1, 30)]
        res.append({"serie": obj, "calendario": nombre, "WAPE dias de Carnaval 1-30 d": wape(c1[c1.fecha.isin(cv[cv > 0].index)]),
                    "WAPE todos los dias 1-30 d": wape(c1), "WAPE todos 92-365 d": wape(bt[bt.lead >= 92])})
mp.calendario = cal0
r = pd.DataFrame(res)
print("\nRETROCESO:")
print(r.to_string(index=False))
pd.concat([coef.assign(tipo="coeficientes"), r.assign(tipo="retroceso")]).to_csv(RAIZ / "resultados" / "tablas" / "prueba_carnaval.csv", index=False)
