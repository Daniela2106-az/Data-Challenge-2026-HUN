"""
dashboard/preparar_datos.py  -  version 2 (13-nov-2026)
Arma las TABLAS AGREGADAS que leen las paginas de Contexto y Resultados del dashboard (demanda, ocupacion, espera de cama, llegada y
altas, forma del año). Ninguna tiene una fila por paciente, y los grupos con menos de 30 casos se ocultan (regla 2 de
docs/estructura_dashboard.md). Lee los datos procesados de HUN_PROCESADOS (por defecto datos/procesados, fuera de git) y escribe en
HUN_PROCESADOS/dashboard/. Esas tablas NO se suben a GitHub: para publicar el dashboard se suben aparte (por ejemplo, como archivos
secretos del servicio donde se despliegue).

Periodo confiable de las etapas: 1-feb-2023 a 9-abr-2026 (docs/CONTEXTO_TECNICO.md 4.9). Espera de cama: estancias unicas (una vez cada una, regla
v3.8), de la llegada a la asignacion de cama, con la persona real (v4.0).

SALIDAS (HUN_PROCESADOS/dashboard/)
  espera_cubo.csv            por año x tipo de visita x grupo de edad (y "Todos"): n, mediana, p25, p75, p90, % > 24 h, % > 48 h y tramos
  espera_por_mes.csv         por mes de llegada: n, mediana, p90
  espera_por_hora.csv        por año x hora de llegada: n, mediana, p90
  camas_por_hora.csv         por año x hora: % de las camas asignadas y % de las altas
  llegadas_calor.csv         llegadas promedio por dia de la semana x hora
  panel_diario.csv           copia del panel diario (ya agregado por dia)
  estacionalidad_efecto.csv  por dia de un año tipico y serie: cuanto sube o baja el pronostico por la epoca del año (%)
  estacionalidad_error.csv   por serie y horizonte: error del backtest (WAPE) sin y con la forma del año

CORRER  HUN_PROCESADOS=... python dashboard/preparar_datos.py   (~2 min; la parte de la forma del año repite cuatro backtests)
"""
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))
SALIDA = PROC / "dashboard"
SALIDA.mkdir(parents=True, exist_ok=True)
DESDE, HASTA = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10")
MIN_N = 30
TRAMOS = [0, 6, 12, 24, 48, 72, 120, np.inf]
ETQ_TRAMOS = ["0–6 h", "6–12 h", "12–24 h", "24–48 h", "48–72 h", "72–120 h", "> 120 h"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def grupo(edad):
    return np.select([edad < 15, edad < 60], ["Niños (< 15)", "Adultos (15–59)"], "Mayores (60+)")


def resumen(e):
    n = len(e)
    if n < MIN_N:
        return None
    h = pd.cut(e, TRAMOS, right=False, labels=ETQ_TRAMOS).value_counts(normalize=True).reindex(ETQ_TRAMOS).fillna(0) * 100
    return {"n": n, "mediana": e.median(), "p25": e.quantile(.25), "p75": e.quantile(.75), "p90": e.quantile(.9),
            "pct_24": 100 * (e > 24).mean(), "pct_48": 100 * (e > 48).mean(), **{f"tramo_{i}": v for i, v in enumerate(h)}}


# ---------------------------------------------------------------- espera de cama, camas por hora y llegadas (tabla_episodios)
t = pd.read_parquet(PROC / "tabla_episodios.parquet")
est = t[t.estancia_unica & t.hospitalizado & t.espera_cama_h.notna() & (t.ini_est >= DESDE) & (t.ini_est < HASTA)].copy()
est["anio_s"] = est.ini_est.dt.year.astype(str)
est["grupo"] = grupo(est.edad.to_numpy())
est["tipo"] = est.tipo_visita.where(est.tipo_visita.isin(["Urgencias", "Ambulatorio", "Treatment urgency"]), "Otro")
print(f"estancias unicas con espera, periodo confiable: {len(est):,}; mediana {est.espera_cama_h.median():.1f} h")

filas = []
for a in ["Todos"] + sorted(est.anio_s.unique()):
    for tv in ["Todos", "Urgencias", "Ambulatorio", "Treatment urgency"]:
        for g in ["Todos", "Niños (< 15)", "Adultos (15–59)", "Mayores (60+)"]:
            s = est
            if a != "Todos":
                s = s[s.anio_s == a]
            if tv != "Todos":
                s = s[s.tipo == tv]
            if g != "Todos":
                s = s[s.grupo == g]
            r = resumen(s.espera_cama_h)
            filas.append({"anio": a, "tipo_visita": tv, "grupo_edad": g, **(r or {"n": len(s)})})
pd.DataFrame(filas).round(2).to_csv(SALIDA / "espera_cubo.csv", index=False)

m = est.groupby(est.ini_est.dt.to_period("M")).espera_cama_h.agg(n="size", mediana="median", p90=lambda s: s.quantile(.9))
m = m[m.n >= MIN_N]
m.index = m.index.astype(str)
m.round(2).to_csv(SALIDA / "espera_por_mes.csv", index_label="mes")

hh = []
for a in ["Todos"] + sorted(est.anio_s.unique()):
    s = est if a == "Todos" else est[est.anio_s == a]
    g = s.groupby(s.ini_est.dt.hour).espera_cama_h.agg(n="size", mediana="median", p90=lambda v: v.quantile(.9)).reset_index(names="hora")
    hh.append(g[g.n >= MIN_N].assign(anio=a))
pd.concat(hh).round(2).to_csv(SALIDA / "espera_por_hora.csv", index=False)

cama = t[t.estancia_unica & t.hospitalizado & t.ini_hosp_est.notna() & (t.ini_hosp_est >= DESDE) & (t.ini_hosp_est < HASTA)]
ch = []
for a in ["Todos", "2023", "2024", "2025", "2026"]:
    s = cama if a == "Todos" else cama[cama.ini_hosp_est.dt.year.astype(str) == a]
    alt = cama[cama.fin_hosp_est.notna() & (cama.fin_hosp_est < HASTA)]
    alt = alt if a == "Todos" else alt[alt.fin_hosp_est.dt.year.astype(str) == a]
    if len(s) < MIN_N or len(alt) < MIN_N:
        continue
    ing = s.ini_hosp_est.dt.hour.value_counts(normalize=True).reindex(range(24), fill_value=0) * 100
    al = alt.fin_hosp_est.dt.hour.value_counts(normalize=True).reindex(range(24), fill_value=0) * 100
    ch.append(pd.DataFrame({"anio": a, "hora": range(24), "pct_ingresos_a_cama": ing.values, "pct_altas": al.values,
                            "n_ingresos": len(s), "n_altas": len(alt)}))
pd.concat(ch).round(2).to_csv(SALIDA / "camas_por_hora.csv", index=False)

lle = t[(t.ini >= DESDE) & (t.ini < HASTA)]
semanas = lle.ini.dt.normalize().nunique() / 7
cal = lle.groupby([lle.ini.dt.day_of_week, lle.ini.dt.hour]).size().unstack(fill_value=0) / semanas
cal.index = DIAS
cal.round(2).to_csv(SALIDA / "llegadas_calor.csv", index_label="dia")

shutil.copy(PROC / "para_equipo" / "panel_diario.csv", SALIDA / "panel_diario.csv")

# ---------------------------------------------------------------- forma del año del pronostico (src/modelo_pronostico.py)
sys.path.insert(0, str(RAIZ / "src"))
os.environ.setdefault("HUN_PROCESADOS", str(PROC))
import modelo_pronostico as mp  # noqa: E402

panel = mp.cargar_panel()
SERIES = {"llegadas_con_atencion": "Llegadas con atención", "ingresos_a_cama": "Ingresos a cama"}
dias = pd.date_range("2027-01-01", "2027-12-31")              # un año completo cualquiera: la forma del año no depende del año
efecto, errores = [], []
for obj in SERIES:
    serie = panel[obj].copy()
    serie.name = obj
    cal_o = mp.calendario(pd.date_range(serie.index.min(), dias.max()), obj)
    beta = mp._ajustar(serie, cal_o, pd.Timestamp(mp.ENTRENA_HASTA))
    cols = [i for i, c in enumerate(cal_o.columns) if c not in mp.COLUMNAS]
    e = np.exp(cal_o.loc[dias].values[:, cols] @ beta[cols])
    efecto.append(pd.DataFrame({"objetivo": obj, "dia_del_anio": dias.day_of_year, "mes": dias.month, "dia": dias.day,
                                "efecto_pct": 100 * (e / e.mean() - 1)}))
    sin = serie.copy()
    sin.name = None                                             # sin nombre, calendario() no suma la forma del año
    for etiqueta, s in [("sin", sin), ("con", serie)]:
        te = mp.tabla_error(mp.retroceso(s), sin_caida=True)
        errores.append(te[["tramo_dias", "n", "wape_pct"]].assign(objetivo=obj, forma_del_anio=etiqueta))
pd.concat(efecto).round(2).to_csv(SALIDA / "estacionalidad_efecto.csv", index=False)
err = pd.concat(errores).pivot_table(index=["objetivo", "tramo_dias"], columns="forma_del_anio", values="wape_pct").reset_index()
orden = {f"{a}-{b}": i for i, (a, b) in enumerate(mp.TRAMOS)}
err = err.assign(orden=err.tramo_dias.map(orden)).sort_values(["objetivo", "orden"]).rename(columns={"sin": "wape_sin", "con": "wape_con"})
err.to_csv(SALIDA / "estacionalidad_error.csv", index=False)
print(err.to_string(index=False))
print("tablas en", SALIDA, ":", sorted(p.name for p in SALIDA.glob("*.csv")))
