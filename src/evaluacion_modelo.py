"""
evaluacion_modelo.py  -  version 1 (1-nov-2026)
UNA sola evaluacion del modelo de serie de tiempo (src/modelo_pronostico.py) contra los datos reales que ya tenemos. Reemplaza mirar las pruebas
sueltas: con esta tabla se responde "que tan bien pronostica?" para cada serie y cada plazo.

COMO SE MIDE (retroceso, o "backtest")
  Se vuelve al pasado muchas veces (cada 14 dias, desde el dia 400 de la serie), se pronostican los 365 dias siguientes usando solo lo que se
  sabia ese dia y se compara con lo que paso. Es la misma situacion de uso real. Los resultados se separan en:
    - PRUEBA NORMAL: dias destino hasta el 9-abr-2026 (periodo confiable; el registro se degrada desde el 10-abr-2026, docs/CONTEXTO_TECNICO.md 4.9).
    - DESDE EL 10-ABR-2026: aparte, como prueba de estres (esos datos ya no son confiables). Con el corte nuevo la serie limpia termina el 9-abr, asi que casi no hay destinos ahi.

METRICAS (por serie y por plazo = cuantos dias antes se pronostico)
  WAPE_pct        error absoluto total / total real. "El pronostico se equivoca un X % en promedio". Menor es mejor.
  MAE             error absoluto medio en pacientes por dia.
  sesgo_pct       si el pronostico queda en promedio alto (+) o bajo (-).
  piso_ruido_pct  error minimo posible si los datos fueran ruido de conteo puro (Poisson); el WAPE no baja de ahi.
  WAPE_ref_pct    error de la referencia simple: promedio del mismo dia de la semana de las ultimas 4 semanas conocidas.
  mejora_pct      cuanto mejora el modelo a esa referencia.
  cobertura_80_pct  % de dias reales dentro de la banda del 80 %, con la banda armada solo con cortes anteriores a 2025-07 y probada despues
                    (deberia estar cerca de 80).
  WAPE_semanal_pct  error al sumar por semana (solo plazos de 1 a 4 semanas).

SALIDA  resultados/tablas/evaluacion_modelo.csv  (una fila por serie, periodo y plazo)
"""
from pathlib import Path

import numpy as np
import pandas as pd

import modelo_pronostico as mp

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "resultados" / "tablas"
PLAZOS = [("1-7 días", 1, 7), ("8-30 días", 8, 30), ("31-91 días", 31, 91), ("92-182 días", 92, 182), ("183-365 días", 183, 365)]
panel = mp.cargar_panel()
filas = []


def referencia(serie, bt):
    """Promedio del mismo dia de la semana de las 4 ultimas semanas conocidas al momento del corte."""
    k0 = np.ceil((bt.fecha - bt.corte).dt.days.values / 7).astype(int)
    vals = np.vstack([serie.reindex(bt.fecha - pd.to_timedelta(7 * (k0 + j), unit="D")).values for j in range(4)])
    return np.nanmean(vals, axis=0)


for obj, nombre in mp.OBJETIVOS.items():
    serie = panel[obj]
    bt = mp.retroceso(serie)
    bt["ref"] = referencia(serie, bt)
    bt = bt.dropna(subset=["real", "pronostico", "ref"])
    bt["r"] = bt.real / bt.pronostico
    mu = serie.loc["2025-04-10":mp.FIN_CONFIABLE].mean()
    piso = 100 * np.sqrt(2 / np.pi) / np.sqrt(mu)
    for periodo, filtro in [("prueba normal (hasta 9-abr-2026)", bt.fecha < mp.INICIO_QUIEBRE), ("desde el 10-abr-2026 (registro degradado)", bt.fecha >= mp.INICIO_QUIEBRE)]:
        b = bt[filtro]
        for etiqueta, a, z in PLAZOS:
            t = b[(b.lead >= a) & (b.lead <= z)]
            if len(t) < 30:
                continue
            wape = 100 * (t.real - t.pronostico).abs().sum() / t.real.sum()
            wref = 100 * (t.real - t.ref).abs().sum() / t.real.sum()
            # cobertura fuera de muestra: banda con cortes < 2025-07, probada con cortes >= 2025-07
            entr = bt[(bt.corte < "2025-07-01") & (bt.lead >= a) & (bt.lead <= z) & (bt.fecha < mp.INICIO_QUIEBRE)]
            prueba = t[t.corte >= "2025-07-01"]
            cob = np.nan
            if len(entr) > 30 and len(prueba) > 30:
                lo, hi = entr.r.quantile(0.1), entr.r.quantile(0.9)
                cob = 100 * ((prueba.r >= lo) & (prueba.r <= hi)).mean()
            wsem = np.nan
            if z <= 30:
                u = t.assign(sem=(t.lead - 1) // 7).groupby(["corte", "sem"]).agg(real=("real", "sum"), pron=("pronostico", "sum"), n=("real", "size"))
                u = u[u.n == 7]
                if len(u) > 10:
                    wsem = 100 * (u.real - u.pron).abs().sum() / u.real.sum()
            filas.append(dict(serie=obj, periodo=periodo, plazo=etiqueta, n=len(t), WAPE_pct=round(wape, 1),
                              MAE=round((t.real - t.pronostico).abs().mean(), 1), sesgo_pct=round(100 * (t.pronostico.sum() / t.real.sum() - 1), 1),
                              piso_ruido_pct=round(piso, 1), WAPE_ref_pct=round(wref, 1), mejora_pct=round(100 * (1 - wape / wref)),
                              cobertura_80_pct=round(cob) if not np.isnan(cob) else np.nan,
                              WAPE_semanal_pct=round(wsem, 1) if not np.isnan(wsem) else np.nan))

t = pd.DataFrame(filas)
t.to_csv(TABLAS / "evaluacion_modelo.csv", index=False)
pd.set_option("display.width", 250)
print(t[t.periodo.str.startswith("prueba")].drop(columns="periodo").to_string(index=False))
print("\nDESDE EL 10-ABR-2026 (registro degradado; prueba de estrés):")
print(t[t.periodo.str.startswith("desde")][["serie", "plazo", "n", "WAPE_pct", "sesgo_pct", "WAPE_ref_pct"]].to_string(index=False))
