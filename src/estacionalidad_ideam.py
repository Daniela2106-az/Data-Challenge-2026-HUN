"""
estacionalidad_ideam.py  -  version 1 (12-nov-2026)  ·  ficha A9, cuarta ronda: lluvia del IDEAM (la fuente que nombra la ficha) en vez de NASA POWER

DATOS  Precipitacion del IDEAM en datos.gov.co (conjunto s54a-sgyg), estacion automatica 0029004520 "ESCUELA NAVAL BARRANQUILLA - AUT", sumada por dia
       (valores cada 10 minutos, en mm). Se guarda en HUN_EXTERNOS/ideam/lluvia_diaria_0029004520.csv (fuera del repositorio).
       Climatologia semanal: lluvia promedio de cada semana ISO con los años completos ANTES de 2023 (sin solaparse con la evaluacion), suavizada
       con media movil de 3 semanas como la de NASA en src/estacionalidad_anual.py, estandarizada.
PRUEBA Encima del modelo VIGENTE (dengue en llegadas; GAM + IRA + EDA en ingresos), rezagos 0, 2, 4, 6 y 8 semanas, con la regla de la ficha A9
       (validacion jul-dic 2025 a 1-6 meses, sin empeorar 1-7 dias; prueba ene-9 abr 2026 solo se reporta).
SALIDA HUN_TABLAS/estacionalidad_ideam.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estacionalidad_anual as ea  # noqa: E402
import estacionalidad_extra as ex  # noqa: E402
import modelo_pronostico as mp  # noqa: E402

warnings.filterwarnings("ignore")
RUTA = ea.EXT / "ideam" / "lluvia_diaria_0029004520.csv"
REZAGOS = [0, 2, 4, 6, 8]


def climatologia_ideam():
    d = pd.read_csv(RUTA, parse_dates=["dia"])
    d = d[d.n >= 100]                                   # dias con al menos ~70 % de las 144 lecturas de 10 minutos
    d["anio"], d["sem"] = d.dia.dt.year, ea.semana(d.dia)
    cobertura = d.groupby("anio").size()
    anios = [a for a, n in cobertura.items() if a < 2023 and n >= 300]
    s = d[d.anio.isin(anios)].groupby("sem").lluvia_mm.mean().reindex(range(1, 54)).ffill()
    s = s.rolling(3, center=True, min_periods=1).mean()
    return (s - s.mean()) / s.std(ddof=0), anios, cobertura


def calendario_lluvia(obj, clim, rez):
    def cal(idx):
        c = mp.calendario(idx, obj)
        c[f"lluvia_ideam_{rez}"] = clim.reindex(ea.semana(pd.DatetimeIndex(idx) - pd.Timedelta(weeks=rez))).to_numpy()
        return c
    return cal


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 220)
    clim, anios, cob = climatologia_ideam()
    nasa, _ = ea.clima_nasa()
    print("Años con dato (dias validos):", cob.to_dict(), "| usados:", anios)
    print("Correlacion con la lluvia de NASA POWER:", round(float(np.corrcoef(clim, nasa.lluvia.reindex(range(1, 54)))[0, 1]), 2),
          "| semana mas lluviosa:", int(clim.idxmax()), "| mas seca:", int(clim.idxmin()))
    panel = mp.cargar_panel()
    filas = []
    for obj in ["llegadas_con_atencion", "ingresos_a_cama"]:
        serie = panel[obj].copy(); serie.name = obj
        filas.append(ex.fila(obj, "vigente", ea.retroceso(serie, lambda i, o=obj: mp.calendario(i, o))))
        for r in REZAGOS:
            filas.append(ex.fila(obj, f"lluvia_ideam_{r}", ea.retroceso(serie, calendario_lluvia(obj, clim, r))))
            print(obj, r, round(filas[-1]["val_31_182"], 2), flush=True)
    t = pd.DataFrame(filas).round(2)
    b = t[t.variante == "vigente"].set_index("objetivo")
    t["mejora_val_31_182"] = t.apply(lambda f: round(b.loc[f.objetivo, "val_31_182"] - f.val_31_182, 2), axis=1)
    t["cambio_val_1_7"] = t.apply(lambda f: round(f.val_1_7 - b.loc[f.objetivo, "val_1_7"], 2), axis=1)
    t["acepta"] = (t.mejora_val_31_182 > 0) & (t.cambio_val_1_7 <= 0.05) & (t.variante != "vigente")
    ea.TABLAS.mkdir(parents=True, exist_ok=True)
    t.to_csv(ea.TABLAS / "estacionalidad_ideam.csv", index=False)
    print(t[["objetivo", "variante", "val_1_7", "val_31_182", "prueba_1_7", "prueba_31_182", "mejora_val_31_182", "cambio_val_1_7", "acepta"]]
          .to_string(index=False))
