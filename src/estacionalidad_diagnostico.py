"""
estacionalidad_diagnostico.py  -  version 1 (12-nov-2026)  ·  ficha A9, niveles 1 y 2: ¿hace falta un modelo mas complejo o una banda nueva?

1. LJUNG-BOX sobre los residuos del modelo de Poisson (periodo confiable): si quedan autocorrelaciones, la ficha sugiere probar SARIMAX o un
   modelo aditivo (nivel 1). Se compara el modelo con y sin la estacionalidad anual.
2. COBERTURA DE LA BANDA DEL 80 % FUERA DE MUESTRA: los factores de la banda se calculan con los cortes cuyo destino es anterior a jul-2025 y se mide
   que porcentaje de los dias de jul-2025 a 9-abr-2026 cae dentro, por tramo de horizonte (nivel 2: si quedara mal calibrada, migrar solo la banda).
3. ¿LA ESTACIONALIDAD TAMBIEN SIRVE PARA LAS LLEGADAS TOTALES? (en el modelo vigente solo se aplica a las llegadas con atencion).

DATOS  HUN_PROCESADOS/para_equipo/panel_diario.csv.  SALIDA  HUN_TABLAS/estacionalidad_diagnostico_*.csv
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modelo_pronostico as mp  # noqa: E402

TABLAS = Path(os.environ.get("HUN_TABLAS", Path(__file__).resolve().parent.parent / "resultados" / "tablas"))
CORTE_BANDA = "2025-07-01"
ORIGINAL = dict(mp.ESTACIONALIDAD)


def residuos(serie, con):
    mp.ESTACIONALIDAD[serie.name] = (ORIGINAL.get(serie.name) or "dengue") if con else False
    s = serie.loc[:mp.FIN_CONFIABLE]
    cal = mp.calendario(pd.date_range(s.index.min(), s.index.max()), serie.name)
    beta = mp._ajustar(s, cal, pd.Timestamp(mp.ENTRENA_HASTA))
    mu = np.exp(cal.values @ beta)
    r = (s - mu) / np.sqrt(mu)                    # residuo de Pearson
    return r.dropna()


def cobertura(bt):
    entr = bt[bt.fecha < CORTE_BANDA]
    prueba = bt[(bt.fecha >= CORTE_BANDA) & (bt.fecha < mp.INICIO_QUIEBRE)]
    out = []
    for a, b in mp.TRAMOS:
        e, t = entr[(entr.lead >= a) & (entr.lead <= b)], prueba[(prueba.lead >= a) & (prueba.lead <= b)]
        if len(e) < 30 or len(t) < 30:
            continue
        lo, hi = (e.real / e.pronostico).quantile(0.1), (e.real / e.pronostico).quantile(0.9)
        dentro = ((t.real >= t.pronostico * lo) & (t.real <= t.pronostico * hi)).mean()
        out.append({"tramo_dias": f"{a}-{b}", "n_prueba": len(t), "cobertura_80_pct": round(100 * dentro, 1),
                    "ancho_relativo_pct": round(100 * (hi - lo), 1)})
    return pd.DataFrame(out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    panel = mp.cargar_panel()
    original = dict(mp.ESTACIONALIDAD)
    lb, cob, tot = [], [], []
    for obj in ["llegadas_con_atencion", "llegadas", "ingresos_a_cama"]:
        serie = panel[obj].copy(); serie.name = obj
        for con in [False, True]:
            r = residuos(serie, con)
            q = acorr_ljungbox(r, lags=[7, 14, 28], return_df=True)
            for lag, f in q.iterrows():
                lb.append({"objetivo": obj, "estacionalidad": con, "rezago_dias": lag, "Q": round(f.lb_stat, 1), "p": f.lb_pvalue,
                           "autocorr_1": round(r.autocorr(1), 3), "autocorr_7": round(r.autocorr(7), 3)})
            mp.ESTACIONALIDAD[obj] = (ORIGINAL.get(obj) or "dengue") if con else False
            bt = mp.retroceso(serie)
            c = cobertura(bt); c.insert(0, "estacionalidad", con); c.insert(0, "objetivo", obj); cob.append(c)
            e = mp.tabla_error(bt, sin_caida=True)[["tramo_dias", "wape_pct", "sesgo_pct"]]
            e.insert(0, "estacionalidad", con); e.insert(0, "objetivo", obj); tot.append(e)
        mp.ESTACIONALIDAD[obj] = original.get(obj, False)
    lb, cob, tot = pd.DataFrame(lb), pd.concat(cob), pd.concat(tot)
    TABLAS.mkdir(parents=True, exist_ok=True)
    lb.to_csv(TABLAS / "estacionalidad_diagnostico_ljungbox.csv", index=False)
    cob.to_csv(TABLAS / "estacionalidad_diagnostico_banda.csv", index=False)
    tot.to_csv(TABLAS / "estacionalidad_diagnostico_error.csv", index=False)
    pd.set_option("display.width", 200)
    print("LJUNG-BOX (residuos de Pearson, periodo confiable)\n", lb.to_string(index=False))
    print("\nCOBERTURA DE LA BANDA DEL 80 % (factores con destinos antes de jul-2025; prueba jul-2025 a 9-abr-2026)\n", cob.to_string(index=False))
    print("\nERROR DEL BACKTEST (WAPE) CON Y SIN ESTACIONALIDAD\n", tot.pivot_table(index=["objetivo", "tramo_dias"], columns="estacionalidad", values="wape_pct").to_string())
