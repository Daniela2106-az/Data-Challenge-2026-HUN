"""
estacionalidad_extra.py  -  version 1 (12-nov-2026)  ·  ficha A9, segunda ronda: datos que faltaban, banda y SARIMAX

1. CALENDARIO ESCOLAR (colegios oficiales de Barranquilla, 2023-2026; fechas de prensa que citan a la Secretaria de Educacion, ver
   <datos>/externos/calendario_escolar/): vacaciones de mitad de año, semana de receso de octubre y vacaciones de fin de año. Para años sin dato
   (2027 en adelante) se usa la regla tipica: clases desde el ultimo lunes de enero, mitad de año 3 semanas desde el lunes siguiente al 20 de junio,
   receso la semana del primer lunes de octubre, fin de clases el primer domingo de diciembre.
2. EL NIÑO (indice ONI de NOAA, mensual). Para no hacer trampa, en cada corte del backtest el ONI del futuro es el ULTIMO VALOR CONOCIDO
   (persistencia, con 1 mes de retraso de publicacion).
3. RECALIBRAR LA BANDA DEL 80 %: se elige el nivel de los percentiles (q, 1-q) para que cubra 80 % en una validacion (destinos de ene-jun 2025, factores
   con destinos anteriores) y se mide la cobertura en la prueba (jul-2025 a 9-abr-2026) con factores de todos los destinos anteriores a jul-2025.
4. SARIMAX (nivel 1 de la ficha, indicado por Ljung-Box): log(llegadas) con el mismo calendario como regresores y errores ARMA, en el mismo backtest.

Seleccion de variables: igual que src/estacionalidad_anual.py (validacion jul-dic 2025, 1-6 meses; regla: no empeorar 1-7 dias).
DATOS  HUN_PROCESADOS/para_equipo/panel_diario.csv, HUN_EXTERNOS/{calendario_escolar,noaa_oni}.  SALIDA HUN_TABLAS/estacionalidad_extra_*.csv
"""
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estacionalidad_anual as ea  # noqa: E402
import modelo_pronostico as mp  # noqa: E402

warnings.filterwarnings("ignore")
EXT, TABLAS = ea.EXT, ea.TABLAS
VAL, PRUEBA = ea.VAL, ea.PRUEBA


# ---------------------------------------------------------------- 1. calendario escolar
def _lunes_desde(fecha):
    f = pd.Timestamp(fecha)
    return f + pd.Timedelta(days=(7 - f.dayofweek) % 7)


def fechas_escolares():
    t = pd.read_csv(EXT / "calendario_escolar" / "calendario_escolar_barranquilla.csv", parse_dates=[
        "inicio_clases", "vac_mitad_inicio", "vac_mitad_fin", "receso_oct_inicio", "receso_oct_fin", "fin_clases"])
    return {int(f.anio): f for _, f in t.iterrows()}


def _regla(anio):
    ene = pd.Timestamp(f"{anio}-01-31")
    inicio = ene - pd.Timedelta(days=(ene.dayofweek - 0) % 7)
    mitad = _lunes_desde(f"{anio}-06-20")
    receso = _lunes_desde(f"{anio}-10-01")
    fin = pd.Timestamp(f"{anio}-12-01") + pd.Timedelta(days=(6 - pd.Timestamp(f"{anio}-12-01").dayofweek) % 7)
    return pd.Series({"inicio_clases": inicio, "vac_mitad_inicio": mitad, "vac_mitad_fin": mitad + pd.Timedelta(days=20),
                      "receso_oct_inicio": receso, "receso_oct_fin": receso + pd.Timedelta(days=6), "fin_clases": fin})


def escolar(idx):
    idx = pd.DatetimeIndex(idx)
    tab = fechas_escolares()
    out = pd.DataFrame(0.0, index=idx, columns=["vac_mitad", "receso_oct", "vac_fin_ano"])
    for a in range(idx.min().year - 1, idx.max().year + 1):
        f, g = tab.get(a, _regla(a)), tab.get(a + 1, _regla(a + 1))
        out.loc[(idx >= f.vac_mitad_inicio) & (idx <= f.vac_mitad_fin), "vac_mitad"] = 1.0
        out.loc[(idx >= f.receso_oct_inicio) & (idx <= f.receso_oct_fin), "receso_oct"] = 1.0
        out.loc[(idx > f.fin_clases) & (idx < g.inicio_clases), "vac_fin_ano"] = 1.0
    return out


# ---------------------------------------------------------------- 2. ONI con persistencia
def oni_mensual():
    t = pd.read_csv(EXT / "noaa_oni" / "oni.ascii.txt", sep=r"\s+")
    centro = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6, "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}
    t["mes"] = pd.to_datetime(dict(year=t.YR, month=t.SEAS.map(centro), day=1))
    return t.set_index("mes").ANOM.sort_index()


def retroceso_oni(serie, base_cal, oni, paso=14, minimo_dias=400):
    """Backtest con ONI: en cada corte el ONI del futuro es el ultimo conocido (publicado con ~1 mes de retraso)."""
    fechas = pd.date_range(serie.index.min(), serie.index.max() + pd.Timedelta(days=366))
    cal0 = base_cal(fechas)
    o_hist = oni.reindex(pd.date_range(oni.index.min(), fechas.max(), freq="D")).ffill().reindex(fechas)
    mu, sd = o_hist.loc[:mp.FIN_CONFIABLE].mean(), o_hist.loc[:mp.FIN_CONFIABLE].std()
    filas = []
    n_valido = serie.index.get_loc(serie.dropna().index.max()) + 1
    for pos in range(minimo_dias, n_valido - 7, paso):
        corte = serie.index[pos]
        conocido = o_hist.loc[:corte - pd.Timedelta(days=45)].iloc[-1]
        o = o_hist.copy(); o[o.index > corte - pd.Timedelta(days=45)] = conocido
        cal = cal0.assign(oni=((o - mu) / sd).values)
        f = mp.pronosticar_desde(serie.iloc[:pos + 1], cal, corte, 365, "reciente")
        real = serie.reindex(f.index); ok = real.notna().values
        filas.append(pd.DataFrame({"corte": corte, "lead": np.arange(1, len(f) + 1)[ok], "fecha": f.index[ok], "real": real.values[ok],
                                   "pronostico": f.values[ok]}))
    return pd.concat(filas, ignore_index=True)


def fila(obj, v, bt):
    r = {"objetivo": obj, "variante": v, "val_1_7": ea.wape(bt, 1, 7, *VAL), "val_31_182": ea.wape(bt, 31, 182, *VAL),
         "prueba_1_7": ea.wape(bt, 1, 7, *PRUEBA), "prueba_31_182": ea.wape(bt, 31, 182, *PRUEBA)}
    for a, b in ea.TRAMOS:
        r[f"todo_{a}_{b}"] = ea.wape(bt, a, b)
    return r


# ---------------------------------------------------------------- 3. banda
def cobertura(bt, q, entr_hasta, ev_desde, ev_hasta):
    out = {}
    for a, b in mp.TRAMOS:
        e = bt[(bt.lead >= a) & (bt.lead <= b) & (bt.fecha < entr_hasta)]
        t = bt[(bt.lead >= a) & (bt.lead <= b) & (bt.fecha >= ev_desde) & (bt.fecha <= ev_hasta)]
        if len(e) < 30 or len(t) < 30:
            continue
        r = e.real / e.pronostico
        lo, hi = r.quantile(q), r.quantile(1 - q)
        out[f"{a}-{b}"] = 100 * ((t.real >= t.pronostico * lo) & (t.real <= t.pronostico * hi)).mean()
    return out


# ---------------------------------------------------------------- 4. SARIMAX
def retroceso_sarimax(serie, calf, orden=(1, 0, 1), paso=28, minimo_dias=400):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    fechas = pd.date_range(serie.index.min(), serie.index.max() + pd.Timedelta(days=366))
    cal = calf(fechas).drop(columns="const")
    filas = []
    n_valido = serie.index.get_loc(serie.dropna().index.max()) + 1
    for pos in range(minimo_dias, n_valido - 7, paso):
        corte = serie.index[pos]
        y = np.log(serie.iloc[:pos + 1])
        m = SARIMAX(y, exog=cal.loc[y.index], order=orden, trend="c", missing="drop").fit(disp=False, maxiter=200)
        fut = pd.date_range(corte + pd.Timedelta(days=1), periods=365)
        p = m.get_forecast(365, exog=cal.loc[fut])
        f = pd.Series(np.exp(p.predicted_mean.values + p.var_pred_mean.values / 2), index=fut)
        real = serie.reindex(fut); ok = real.notna().values
        filas.append(pd.DataFrame({"corte": corte, "lead": np.arange(1, 366)[ok], "fecha": fut[ok], "real": real.values[ok],
                                   "pronostico": f.values[ok]}))
    return pd.concat(filas, ignore_index=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 220)
    panel = mp.cargar_panel()
    cd, _ = ea.clima_dengue(); cn, _ = ea.clima_nasa()
    oni = oni_mensual()
    filas = []
    for obj in ["llegadas_con_atencion", "ingresos_a_cama"]:
        serie = panel[obj].copy(); serie.name = obj
        bases = {"sin estacionalidad": lambda i: mp.calendario(i), "dengue (modelo actual)": ea.calendario_con("dengue_2", cd, cn)}
        for nb, bf in bases.items():
            filas.append(fila(obj, nb, ea.retroceso(serie, bf)))
            filas.append(fila(obj, nb + " + escolar", ea.retroceso(serie, lambda i, bf=bf: pd.concat([bf(i), escolar(i)], axis=1))))
            filas.append(fila(obj, nb + " + ONI", retroceso_oni(serie, bf, oni)))
            print(pd.DataFrame(filas[-3:]).round(2).to_string(index=False), flush=True)
    res = pd.DataFrame(filas).round(2)
    TABLAS.mkdir(parents=True, exist_ok=True)
    res.to_csv(TABLAS / "estacionalidad_extra_variables.csv", index=False)

    # banda: con el modelo actual (dengue en llegadas)
    bandas = []
    for obj in ["llegadas_con_atencion", "ingresos_a_cama"]:
        serie = panel[obj].copy(); serie.name = obj
        bt = mp.retroceso(serie)
        for q in [0.10, 0.08, 0.07, 0.06, 0.05, 0.04]:
            v = cobertura(bt, q, "2025-01-01", "2025-01-01", "2025-06-30")
            p = cobertura(bt, q, "2025-07-01", "2025-07-01", mp.FIN_CONFIABLE)
            bandas.append({"objetivo": obj, "q": q, **{f"val_{k}": round(x, 1) for k, x in v.items()}, **{f"prueba_{k}": round(x, 1) for k, x in p.items()}})
    bandas = pd.DataFrame(bandas)
    bandas.to_csv(TABLAS / "estacionalidad_extra_banda.csv", index=False)
    print("\nBANDA\n", bandas.to_string(index=False), flush=True)

    # SARIMAX frente a Poisson, mismos cortes (cada 28 dias)
    sar = []
    for obj in ["llegadas_con_atencion"]:
        serie = panel[obj].copy(); serie.name = obj
        calf = ea.calendario_con("dengue_2", cd, cn)
        bp = ea.retroceso(serie, calf, paso=28)
        for orden in [(1, 0, 1), (2, 0, 1)]:
            bs = retroceso_sarimax(serie, calf, orden)
            sar.append(fila(obj, f"SARIMAX{orden}", bs))
        sar.append(fila(obj, "Poisson (modelo actual)", bp))
    sar = pd.DataFrame(sar).round(2)
    sar.to_csv(TABLAS / "estacionalidad_extra_sarimax.csv", index=False)
    print("\nSARIMAX\n", sar.to_string(index=False))
