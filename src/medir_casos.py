"""
src/medir_casos.py  -  version 5 (15-nov-2026)  ·  efecto de los casos y error de cada modelo del simulador integral

QUE MIDE
  1. Efecto PROPIO de cada caso (dengue, infecciones respiratorias, diarreas, lluvias) en la demanda del hospital, en porcentaje y
     valido en cualquier mes del año: cuanto cambian las llegadas y los ingresos a cama cuando el caso esta X % por encima (o por
     debajo) de lo normal PARA ESA SEMANA DEL AÑO.
     - «Lo normal» de cada caso en cada semana epidemiologica = media de esa semana en los años previos a la evaluacion (dengue, IRA y
       EDA de Barranquilla 2016-2022; lluvia 2005-2022), suavizada 3 semanas. Asi un brote en julio cuenta como brote aunque julio no
       sea temporada de dengue, y la temporada de diciembre no se confunde con el dengue.
     - La demanda de cada semana se compara contra lo que espera un modelo con el calendario (dia de la semana, festivos, Semana Santa,
       Carnaval), el nivel de cada año y las formas del año de esa serie (llegadas: dengue y lluvia; ingresos: curva del año, IRA y EDA).
     - Regresion con TODAS las semanas de feb-2023 a dic-2025 (151 semanas epidemiologicas, domingo a sabado como SIVIGILA):
       log(real / esperado) = a + b_dengue·log(dengue / normal) + b_ira·log(IRA / normal) + b_eda·log(EDA / normal) + b_lluvia·log(lluvia / normal).
       Los cuatro casos van juntos, asi el efecto de cada uno es neto de los otros. b es una elasticidad: un caso X % por encima de lo
       normal cambia la demanda en (1 + X/100)^b - 1. Intervalo del 95 % con bootstrap de semanas (2.000 repeticiones).
  2. Error de cada modelo de la ficha A9 en la serie donde A9 lo valido (dengue y lluvia en las llegadas; curva, IRA y EDA en los
     ingresos a cama): entrenado hasta el 30-jun-2025, pronostico diario de jul-dic 2025 (validacion) y de ene a 9-abr-2026 (prueba),
     WAPE frente al real, comparado con «sin modelo».

ENTRADAS  HUN_PROCESADOS/dashboard/panel_diario.csv y HUN_PROCESADOS/tablas/estacionalidad_climatologias.csv (agregados), y HUN_EXTERNOS
          (SIVIGILA y NASA POWER).
SALIDAS   HUN_PROCESADOS/dashboard/casos_efecto.csv, casos_escala.csv y modelos_error.csv (agregadas, sin pacientes). El simulador las lee; si no
          estan, usa los valores escritos en src/simulador_integral.py (los de la ultima corrida).
CORRER    HUN_PROCESADOS=... HUN_EXTERNOS=... python src/medir_casos.py   (~1 min)
LIMITES   Asociacion, no causa. Los datos externos llegan a 2025. Para cambios muy grandes (un brote del triple de lo normal) el efecto
          se extrapola con la misma elasticidad.
"""
import contextlib
import io
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))
E = Path(os.environ.get("HUN_EXTERNOS", RAIZ / "datos" / "externos"))
SALIDA = PROC / "dashboard"
sys.path.insert(0, str(RAIZ / "src"))
with contextlib.redirect_stdout(io.StringIO()):
    import modelo_pronostico as mp  # noqa: E402

SERIES = {"llegadas": "llegadas", "ingresos": "ingresos_a_cama"}
BASES_SERIE = {"llegadas": ("dengue", "lluvia"), "ingresos": ("curva", "ira", "eda")}   # donde A9 probo cada forma del año
CASOS = ("dengue", "ira", "eda", "lluvia")
EXCLUIR = pd.to_datetime(["2026-03-28", "2026-03-29"])


def semana_epi(fechas):
    """(año, semana) epidemiologica de cada fecha: semanas de domingo a sabado; la semana 1 contiene el 4 de enero."""
    f = pd.DatetimeIndex(fechas)
    inicio = f - pd.to_timedelta((f.dayofweek + 1) % 7, unit="D")
    anio = (inicio + pd.Timedelta(days=3)).year
    ene4 = pd.to_datetime([f"{a}-01-04" for a in anio])
    primero = ene4 - pd.to_timedelta((ene4.dayofweek + 1) % 7, unit="D")
    return np.asarray(anio), np.asarray((inicio - primero).days // 7 + 1)


def clima_lluvia():
    c = pd.read_csv(PROC / "tablas" / "estacionalidad_climatologias.csv")
    v = c.set_index("semana")["lluvia_mm_dia"].reindex(range(1, 54)).ffill().rolling(3, center=True, min_periods=1).mean()
    return ((v - v.mean()) / v.std()).to_numpy()


CLIMA_LLUVIA = clima_lluvia()


def columnas(idx, bases):
    idx = pd.DatetimeIndex(idx)
    out = pd.DataFrame(index=idx)
    for b in bases:
        if b == "dengue":
            out[b] = mp.regresor_estacional(idx, mp.CLIMA_DENGUE, mp.REZAGO_DENGUE_SEMANAS).to_numpy()
        elif b == "ira":
            out[b] = mp.regresor_estacional(idx, mp.CLIMA_IRA, 0).to_numpy()
        elif b == "eda":
            out[b] = mp.regresor_estacional(idx, mp.CLIMA_EDA, 0).to_numpy()
        elif b == "lluvia":
            out[b] = mp.regresor_estacional(idx, CLIMA_LLUVIA, 0).to_numpy()
        elif b == "curva":
            g = mp._base_gam(idx.dayofyear)
            for i in range(g.shape[1]):
                out[f"curva_{i}"] = g[:, i]
    return out


panel = pd.read_csv(PROC / "dashboard" / "panel_diario.csv", parse_dates=["fecha"]).set_index("fecha").asfreq("D")
panel = panel.loc["2023-02-01":"2026-04-09"]
panel.loc[panel.index.isin(EXCLUIR), ["llegadas", "ingresos_a_cama"]] = np.nan

# ----------------------------------------------------------------------------------------------------------------------
# 1. EFECTO PROPIO DE LOS CASOS
# ----------------------------------------------------------------------------------------------------------------------
d = pd.read_csv(E / "sivigila" / "dengue_barranquilla_2016_2026.csv").rename(columns={"semana_epi": "semana"})
i = pd.read_csv(E / "sivigila" / "ira_eda_atlantico_semanal.csv").rename(columns={"semana_epi": "semana"})
i = i[i.territorio == "Barranquilla"]
lineas = open(E / "nasa_power" / "barranquilla_diario_2005_2025.csv", encoding="utf-8", errors="ignore").read().splitlines()
n = pd.read_csv(E / "nasa_power" / "barranquilla_diario_2005_2025.csv", skiprows=next(k for k, t in enumerate(lineas) if "END HEADER" in t) + 1)
n["fecha"] = pd.to_datetime(dict(year=n.YEAR, month=n.MO, day=n.DY))
na, ns = semana_epi(n.fecha)
historia = {"dengue": d.set_index(["anio", "semana"]).casos_dengue,
            "ira": i[i.evento == "IRA"].set_index(["anio", "semana"]).casos,
            "eda": i[i.evento == "EDA"].set_index(["anio", "semana"]).casos,
            "lluvia": n.assign(anio=na, semana=ns).groupby(["anio", "semana"]).PRECTOTCORR.sum()}

desvio = {}            # log(valor / lo normal de esa semana) para cada caso y semana
for c, s in historia.items():
    s = s.sort_index()
    t = s[s.index.get_level_values("anio") <= 2022].groupby(level="semana").mean().reindex(range(1, 54)).ffill().bfill()
    t = pd.concat([t.iloc[-1:], t, t.iloc[:1]]).rolling(3, center=True).mean().iloc[1:-1]
    ref = s.index.get_level_values("semana").map(t).to_numpy(float)
    desvio[c] = pd.Series(np.log((s.to_numpy(float) + 1) / (ref + 1)), index=s.index)
desvio = pd.DataFrame(desvio)

p = panel.loc[:"2025-12-31"]
anio, semana = semana_epi(p.index)
rng = np.random.default_rng(7)
filas = []
for serie, col in SERIES.items():
    cal = pd.concat([mp.calendario(p.index), columnas(p.index, BASES_SERIE[serie])], axis=1)
    for a in (2024, 2025):
        cal[f"anio_{a}"] = (p.index.year == a).astype(float)
    y = p[col].astype(float)
    m = y.notna().values
    beta = mp.poisson_fit(cal.values[m], y.values[m])
    esp = np.exp(cal.values @ beta)
    sem = pd.DataFrame({"anio": anio, "semana": semana, "real": y.values, "esp": np.where(m, esp, np.nan), "dias": m.astype(int)})
    sem = sem.groupby(["anio", "semana"]).sum(min_count=1)
    sem = sem[sem.dias == 7].join(desvio, how="inner").dropna()
    lr = np.log(sem.real / sem.esp).to_numpy()
    X = np.column_stack([np.ones(len(sem))] + [sem[c].to_numpy() for c in CASOS])
    coef = np.linalg.lstsq(X, lr, rcond=None)[0]
    boot = np.array([np.linalg.lstsq(X[k], lr[k], rcond=None)[0] for k in (rng.integers(0, len(lr), len(lr)) for _ in range(2000))])
    for j, c in enumerate(CASOS, start=1):
        lo, hi = np.percentile(boot[:, j], [2.5, 97.5])
        filas.append(dict(caso=c, serie=serie, elasticidad=round(coef[j], 4), ic_bajo=round(lo, 4), ic_alto=round(hi, 4),
                          efecto_30_pct=round(100 * (1.3 ** coef[j] - 1), 2), semanas=len(sem), claro=bool(lo > 0 or hi < 0)))
efectos = pd.DataFrame(filas)

# Escala de niveles de cada caso: cuanto estuvo por encima o por debajo de lo normal en las semanas reales de 2023 a 2025. Cada nivel es
# un percentil de esas semanas, asi «grave» significa lo mismo en todos los casos (una semana excepcional pero que si paso) y ningun
# nivel se sale de los datos. Solo se dejan los niveles bajos que de verdad quedaron por debajo de lo normal (menos de −5 %) y los altos
# que quedaron por encima (mas de +5 %).
NIVELES = [("Muy bajo", 0.05), ("Bajo", 0.25), ("Alto", 0.75), ("Muy alto", 0.90), ("Grave", 0.95), ("Récord", 1.0)]
obs = 100 * (np.exp(desvio[(desvio.index.get_level_values("anio") >= 2023) & (desvio.index.get_level_values("anio") <= 2025)]) - 1)
filas = []
for c in CASOS:
    for nombre, q in NIVELES:
        v = float(obs[c].dropna().quantile(q))
        if (q < 0.5 and v < -5) or (q > 0.5 and v > 5):
            filas.append(dict(caso=c, nivel=nombre, percentil=q, pct_sobre_normal=round(v)))
escala = pd.DataFrame(filas)

# ----------------------------------------------------------------------------------------------------------------------
# 2. ERROR DE CADA MODELO EN LA SERIE DONDE A9 LO VALIDO
# ----------------------------------------------------------------------------------------------------------------------
CORTE = pd.Timestamp("2025-06-30")
dias = (panel.index.max() - CORTE).days
filas = []
for serie, col in SERIES.items():
    y = panel[col].astype(float)
    for modelo in ("ninguno",) + BASES_SERIE[serie]:
        bases = () if modelo == "ninguno" else (modelo,)
        idx = pd.date_range(y.index.min(), CORTE + pd.Timedelta(days=dias + 2))
        cal = pd.concat([mp.calendario(idx), columnas(idx, bases)], axis=1)
        beta = mp._ajustar(y, cal, CORTE)
        pron = mp.pronosticar_desde(y, cal, CORTE, dias, "historico", beta=beta)
        real = y.reindex(pron.index)
        ok = real.notna()
        wape = lambda desde, hasta: round(100 * (real[ok].loc[desde:hasta] - pron[ok].loc[desde:hasta]).abs().sum()
                                          / real[ok].loc[desde:hasta].sum(), 2)
        filas.append(dict(serie=serie, modelo=modelo, wape_validacion=wape("2025-07-01", "2025-12-31"),
                          wape_prueba=wape("2026-01-01", "2026-04-09")))
errores = pd.DataFrame(filas)

if __name__ == "__main__":
    SALIDA.mkdir(parents=True, exist_ok=True)
    efectos.to_csv(SALIDA / "casos_efecto.csv", index=False)
    errores.to_csv(SALIDA / "modelos_error.csv", index=False)
    escala.to_csv(SALIDA / "casos_escala.csv", index=False)
    print(efectos.to_string(index=False))
    print()
    print(escala.to_string(index=False))
    print()
    print(errores.to_string(index=False))
