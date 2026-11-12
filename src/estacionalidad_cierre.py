"""
estacionalidad_cierre.py  -  version 1 (12-nov-2026)  ·  ficha A9, lo que quedaba por probar con datos disponibles

1. POBLACION (DANE, proyecciones municipales 2018-2042, version de ago-2025): area metropolitana de Barranquilla (Barranquilla, Soledad, Malambo,
   Puerto Colombia y Galapa). Prioridad 2 de la ficha: solo tendencia de nivel, no forma del año. Se aplica como ajuste del pronostico:
   pronostico x poblacion(fecha destino) / poblacion(fecha del corte), interpolando en log entre años. La proyeccion del DANE se conoce de antemano.
2. GAM (nivel 1 de la ficha, alternativa al SARIMAX): una curva ciclica suave del dia del año (spline ciclico de patsy, cc) dentro del mismo Poisson,
   con 4, 6 u 8 grados de libertad, en lugar de la climatologia del dengue.

Misma seleccion que src/estacionalidad_anual.py: validacion jul-dic 2025 (1-6 meses), regla de no empeorar 1-7 dias; prueba ene-9 abr 2026 aparte.
DATOS  HUN_PROCESADOS/para_equipo/panel_diario.csv, HUN_EXTERNOS/dane_poblacion/PPED-AreaMun-2018-2042_VP.xlsx
SALIDA HUN_TABLAS/estacionalidad_cierre.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from patsy import dmatrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estacionalidad_anual as ea  # noqa: E402
import modelo_pronostico as mp  # noqa: E402

warnings.filterwarnings("ignore")
AREA_METRO = ["08001", "08758", "08433", "08573", "08296"]


def poblacion_diaria(fechas):
    x = pd.read_excel(ea.EXT / "dane_poblacion" / "PPED-AreaMun-2018-2042_VP.xlsx", sheet_name=2, header=None, skiprows=9, dtype={2: str})
    x = x[x[2].isin(AREA_METRO) & (x[5].astype(str).str.strip() == "Total")]
    anual = x.groupby(4)[6].sum().astype(float)
    puntos = pd.Series(np.log(anual.values), index=pd.to_datetime([f"{int(a)}-07-01" for a in anual.index]))
    d = puntos.reindex(puntos.index.union(fechas)).interpolate("time").reindex(fechas)
    return np.exp(d), anual


def retroceso_poblacion(serie, calf, pob, paso=14, minimo_dias=400):
    bt = ea.retroceso(serie, calf, paso, minimo_dias)
    bt["pronostico"] = bt.pronostico * pob.reindex(bt.fecha).values / pob.reindex(bt.corte).values
    return bt


def calendario_gam(df):
    def cal(idx):
        c = mp.calendario(idx)
        b = dmatrix(f"cc(x, df={df}) - 1", {"x": pd.DatetimeIndex(idx).dayofyear.to_numpy()}, return_type="dataframe")
        b.index = c.index
        b.columns = [f"gam_{i}" for i in range(b.shape[1])]
        return pd.concat([c, (b - b.mean()) / b.std(ddof=0)], axis=1)
    return cal


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 220)
    panel = mp.cargar_panel()
    cd, _ = ea.clima_dengue(); cn, _ = ea.clima_nasa()
    pob, anual = poblacion_diaria(pd.date_range("2018-07-01", "2028-12-31"))
    print("poblacion del area metropolitana (DANE):", {int(k): int(v) for k, v in anual.loc[2022:2028].items()})
    filas = []
    for obj in ["llegadas_con_atencion", "ingresos_a_cama"]:
        serie = panel[obj].copy(); serie.name = obj
        dengue = ea.calendario_con("dengue_2", cd, cn)
        variantes = {"sin estacionalidad": (lambda i: mp.calendario(i), False),
                     "dengue (modelo actual)": (dengue, False),
                     "dengue + poblacion DANE": (dengue, True),
                     "sin estacionalidad + poblacion DANE": (lambda i: mp.calendario(i), True)}
        for df in [4, 6, 8]:
            variantes[f"GAM ciclico ({df} gl)"] = (calendario_gam(df), False)
        for nombre, (calf, con_pob) in variantes.items():
            bt = retroceso_poblacion(serie, calf, pob) if con_pob else ea.retroceso(serie, calf)
            f = {"objetivo": obj, "variante": nombre, "val_1_7": ea.wape(bt, 1, 7, *ea.VAL), "val_31_182": ea.wape(bt, 31, 182, *ea.VAL),
                 "prueba_1_7": ea.wape(bt, 1, 7, *ea.PRUEBA), "prueba_31_182": ea.wape(bt, 31, 182, *ea.PRUEBA)}
            for a, b in ea.TRAMOS:
                f[f"todo_{a}_{b}"] = ea.wape(bt, a, b)
            filas.append(f)
            print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in f.items()}, flush=True)
    res = pd.DataFrame(filas).round(2)
    ea.TABLAS.mkdir(parents=True, exist_ok=True)
    res.to_csv(ea.TABLAS / "estacionalidad_cierre.csv", index=False)
    print(res[["objetivo", "variante", "val_1_7", "val_31_182", "prueba_1_7", "prueba_31_182", "todo_31_91", "todo_92_182", "todo_183_365"]].to_string(index=False))
