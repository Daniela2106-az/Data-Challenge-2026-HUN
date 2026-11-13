"""
estacionalidad_ira_eda.py  -  version 1 (12-nov-2026)  ·  ficha A9, cuarta ronda: IRA, EDA y demanda total de Barranquilla (SIVIGILA) y calendario escolar oficial

QUE SE PRUEBA (encima del modelo VIGENTE: llegadas con atencion = calendario + dengue; ingresos a cama = calendario + curva GAM)
  Climatologias semanales de Barranquilla tomadas de los microdatos SIVIGILA del INS (eventos 995 y 998, notificacion colectiva, municipio
  de notificacion), con la misma construccion que el dengue de A9: casos de la semana / promedio semanal de su año, promediado entre años, en log.
    ira_cext        consultas externas y urgencias por IRA
    ira_hosp        hospitalizaciones por IRA grave en sala general
    eda             casos de EDA
    consultas_todas consultas externas y urgencias por TODAS las causas (lo reportan las mismas instituciones en la ficha de IRA)
    hosp_todas      hospitalizaciones por todas las causas
  Cada una con rezago de 0 o 2 semanas. Años usados: 2016-2019 (antes de la pandemia y SIN solaparse con el periodo de evaluacion, que es 2023-2026;
  asi la forma del año no "ve" la validacion ni la prueba).
  Ademas: el calendario escolar OFICIAL (resoluciones 06040/2022, 06182/2023, 07036/2024 y 07248/2025, corregido el 12-nov) encima del modelo vigente.

COMO SE DECIDE (igual que src/estacionalidad_anual.py y la ficha A9)
  Backtest cada 14 dias a 365 dias. Validacion: destinos jul-dic 2025, horizonte 31-182 dias (1-6 meses). Se acepta si mejora la validacion a 1-6 meses
  y no empeora 1-7 dias en mas de 0,05 puntos. Prueba (destinos ene-9 abr 2026) solo se reporta. Con la mejor variable aceptada se prueba ademas una
  segunda (la mejor de las restantes) encima, con la misma regla.

DATOS  HUN_PROCESADOS/para_equipo/panel_diario.csv; HUN_EXTERNOS/sivigila/ira_eda_atlantico_semanal.csv (armado desde los microdatos, ver el README de
       esa carpeta); HUN_EXTERNOS/calendario_escolar/calendario_escolar_barranquilla.csv.  Nada de esto se sube a git.
SALIDA HUN_TABLAS/estacionalidad_ira_eda.csv
COMO CORRERLO  HUN_PROCESADOS=... HUN_EXTERNOS=... HUN_TABLAS=... python src/estacionalidad_ira_eda.py   (~15 min)
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
ANIOS_CLIMA = [2016, 2017, 2018, 2019]
VARIABLES = {"ira_cext": ("IRA", "casos"), "ira_hosp": ("IRA", "hospitalizados"), "eda": ("EDA", "casos"),
             "consultas_todas": ("IRA", "consultas_todas_causas"), "hosp_todas": ("IRA", "hospitalizaciones_todas_causas")}
REZAGOS = [0, 2]
TOLERANCIA_1_7 = 0.05


def climatologias():
    t = pd.read_csv(ea.EXT / "sivigila" / "ira_eda_atlantico_semanal.csv")
    t = t[(t.territorio == "Barranquilla") & t.anio.isin(ANIOS_CLIMA)]
    out = {}
    for nombre, (evento, col) in VARIABLES.items():
        c = t[t.evento == evento].pivot_table(index="anio", columns="semana_epi", values=col, aggfunc="sum").reindex(columns=range(1, 54))
        c = c.where(c.notna(), np.nan)
        rel = c.div(c.loc[:, 1:52].mean(axis=1), axis=0)
        s = np.log(rel.loc[:, 1:52].mean(axis=0))
        s[53] = s[52]
        out[nombre] = s.sort_index()
    return pd.DataFrame(out)


def calendario_extra(obj, cl, partes):
    """Calendario vigente del objetivo (con su estacionalidad) + las columnas pedidas, estandarizadas. partes: ['ira_cext_0', 'escolar', ...]."""
    def cal(idx):
        c = mp.calendario(idx, obj)
        cols = []
        for p in partes:
            if p == "escolar":
                cols.append(ex.escolar(idx))
                continue
            nombre, rez = p.rsplit("_", 1)
            v = cl[nombre].reindex(ea.semana(pd.DatetimeIndex(idx) - pd.Timedelta(weeks=int(rez)))).to_numpy()
            cols.append(pd.DataFrame({p: (v - np.nanmean(cl[nombre])) / np.nanstd(cl[nombre])}, index=c.index))
        return pd.concat([c] + [x.set_axis(c.index) for x in cols], axis=1) if cols else c
    return cal


def evaluar(obj, serie, cl, partes):
    bt = ea.retroceso(serie, calendario_extra(obj, cl, partes))
    return {**ex.fila(obj, "+".join(partes) or "vigente", bt)}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 220)
    cl = climatologias()
    print("Climatologias (log de la forma relativa), semanas de pico y valle:")
    print(pd.DataFrame({"pico": cl.idxmax(), "valle": cl.idxmin(), "rango_log": (cl.max() - cl.min()).round(2)}).to_string())
    print("Correlacion con el dengue vigente:", cl.corrwith(pd.Series(mp.CLIMA_DENGUE, index=range(1, 54))).round(2).to_dict())
    panel = mp.cargar_panel()
    filas = []
    for obj in ["llegadas_con_atencion", "ingresos_a_cama"]:
        serie = panel[obj].copy(); serie.name = obj
        base = evaluar(obj, serie, cl, []); filas.append(base)
        candidatas = [f"{v}_{r}" for v in VARIABLES for r in REZAGOS] + ["escolar"]
        res = []
        for p in candidatas:
            f = evaluar(obj, serie, cl, [p]); filas.append(f); res.append(f)
            print(obj, p, {k: round(v, 2) for k, v in f.items() if isinstance(v, float)}, flush=True)
        r = pd.DataFrame(res)
        r["mejora"] = base["val_31_182"] - r.val_31_182
        r["acepta"] = (r.mejora > 0) & (r.val_1_7 - base["val_1_7"] <= TOLERANCIA_1_7)
        if r.acepta.any():
            mejor = r[r.acepta].sort_values("val_31_182").variante.iloc[0]
            usadas = {mejor.rsplit("_", 1)[0]}
            resto = r[r.acepta & ~r.variante.str.rsplit("_", n=1).str[0].isin(usadas)].sort_values("val_31_182")
            if len(resto):
                f = evaluar(obj, serie, cl, [mejor, resto.variante.iloc[0]]); filas.append(f)
                print(obj, f["variante"], {k: round(v, 2) for k, v in f.items() if isinstance(v, float)}, flush=True)
    t = pd.DataFrame(filas).round(2)
    b = t[t.variante == "vigente"].set_index("objetivo")
    t["mejora_val_31_182"] = t.apply(lambda f: round(b.loc[f.objetivo, "val_31_182"] - f.val_31_182, 2), axis=1)
    t["cambio_val_1_7"] = t.apply(lambda f: round(f.val_1_7 - b.loc[f.objetivo, "val_1_7"], 2), axis=1)
    t["cambio_prueba_31_182"] = t.apply(lambda f: round(f.prueba_31_182 - b.loc[f.objetivo, "prueba_31_182"], 2), axis=1)
    t["acepta"] = (t.mejora_val_31_182 > 0) & (t.cambio_val_1_7 <= TOLERANCIA_1_7) & (t.variante != "vigente")
    ea.TABLAS.mkdir(parents=True, exist_ok=True)
    t.to_csv(ea.TABLAS / "estacionalidad_ira_eda.csv", index=False)
    print(t[["objetivo", "variante", "val_1_7", "val_31_182", "prueba_1_7", "prueba_31_182", "mejora_val_31_182", "cambio_val_1_7",
             "cambio_prueba_31_182", "acepta"]].to_string(index=False))
