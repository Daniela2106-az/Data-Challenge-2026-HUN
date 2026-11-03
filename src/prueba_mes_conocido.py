"""
prueba_mes_conocido.py  -  version 1 (1-nov-2026)
Prueba con meses que YA tienen datos reales: se pronostica el mes entero desde el dia anterior a que empiece, usando solo lo que se sabia
hasta ese dia (modelo, nivel de los ultimos 28 dias y banda del 80 % armada solo con errores de dias ya conocidos), y despues se
pone el dato real encima. Asi se ve si los puntos reales caen dentro de la banda y cuanto de su ancho es ruido de conteo.

Cada grafico dibuja: la linea real, el pronostico, la banda del 80 % del modelo (azul claro) y, como comparacion, la banda que daria
un ruido de conteo puro (Poisson: pronostico +- 1,28 x raiz del pronostico, linea punteada). Puntos reales dentro de la banda del
modelo: oscuros; fuera: rojos. Los datos reales se dibujan SIN limpiar (se ve el corte del 28 de marzo de 2026); el modelo usa la serie limpia.

SALIDAS  resultados/graficos/prueba_mes_conocido_llegadas.png, prueba_mes_conocido_ingresos.png
         resultados/tablas/prueba_mes_conocido.csv (por mes: dentro de la banda, dentro de la banda de ruido puro, WAPE, sesgo)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import modelo_pronostico as mp

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
MESES = ["2025-03", "2025-06", "2025-09", "2025-12", "2026-01", "2026-02", "2026-03"]      # abril de 2026 ya tiene el registro degradado
Z80 = 1.2816

real = mp.cargar_panel(limpiar=False)
limpio = mp.cargar_panel()
filas = []
for obj, nombre, archivo in [("llegadas_con_atencion", "Llegadas con atención por día", "llegadas_con_atencion"), ("llegadas", "Llegadas por día", "llegadas"), ("ingresos_a_cama", "Ingresos a cama por día", "ingresos")]:
    serie = limpio[obj]
    bt = mp.retroceso(serie)
    cal = mp.calendario(pd.date_range(serie.index.min(), serie.index.max() + pd.Timedelta(days=400)))
    fig, ejes = plt.subplots(4, 2, figsize=(14, 15))
    ejes = ejes.ravel()
    for ax, mes in zip(ejes, MESES):
        ini = pd.Timestamp(mes + "-01")
        fin = ini + pd.offsets.MonthEnd(0)
        corte = ini - pd.Timedelta(days=1)
        dias = (fin - ini).days + 1
        f = mp.pronosticar_desde(serie.loc[:corte], cal, corte, dias, "reciente")
        # banda armada solo con errores de dias ya conocidos al momento del corte
        fb = mp.factores_banda(bt[bt.fecha <= corte], excluir_caida=False)
        lead = np.arange(1, dias + 1)
        lo_f, hi_f = np.empty(dias), np.empty(dias)
        for (a, b), (l, h) in fb.items():
            m = (lead >= a) & (lead <= b)
            lo_f[m], hi_f[m] = l, h
        lo, hi = f.values * lo_f, f.values * hi_f
        plo, phi = f.values - Z80 * np.sqrt(f.values), f.values + Z80 * np.sqrt(f.values)
        y = real[obj].reindex(f.index)
        dentro = (y >= lo) & (y <= hi)
        dentro_p = (y >= plo) & (y <= phi)
        wape = 100 * (y - f).abs().sum() / y.sum()
        sesgo = 100 * (f.sum() / y.sum() - 1)
        filas.append(dict(serie=obj, mes=mes, dias=dias, dentro_banda_modelo_pct=round(100 * dentro.mean()),
                          dentro_banda_ruido_puro_pct=round(100 * dentro_p.mean()), wape_pct=round(wape, 1), sesgo_pct=round(sesgo, 1),
                          ancho_banda_modelo_pct_del_pron=round(100 * ((hi - lo) / f.values).mean()),
                          ancho_banda_ruido_puro_pct_del_pron=round(100 * ((phi - plo) / f.values).mean())))
        hist = real[obj].loc[corte - pd.Timedelta(days=20):corte]
        ax.plot(hist.index, hist.values, color="#999", lw=1)
        ax.fill_between(f.index, lo, hi, color="#2a6fb0", alpha=0.15, label="banda 80 % del modelo")
        ax.plot(f.index, plo, color="#d9730d", lw=0.9, ls=":", label="banda de ruido puro (Poisson)")
        ax.plot(f.index, phi, color="#d9730d", lw=0.9, ls=":")
        ax.plot(f.index, f.values, color="#2a6fb0", lw=2, label="pronóstico")
        ax.plot(y.index, y.values, color="#444", lw=1, alpha=0.6, label="real")
        ax.scatter(y.index[dentro.values], y.values[dentro.values], color="#222", s=22, zorder=3)
        ax.scatter(y.index[~dentro.values], y.values[~dentro.values], color="#c0392b", s=34, zorder=3, label="real fuera de la banda")
        ax.axvline(corte, color="#999", ls="--", lw=0.8)
        ax.set_title(f"{mes}: {100 * dentro.mean():.0f} % dentro de la banda · error {wape:.0f} % · "
                     f"ruido puro cubriría {100 * dentro_p.mean():.0f} %", fontsize=10)
        ax.grid(alpha=0.25)
        ax.tick_params(axis="x", labelrotation=30, labelsize=8)
    ejes[-1].axis("off")
    h, l = ejes[0].get_legend_handles_labels()
    ejes[-1].legend(h, l, loc="center", fontsize=10)
    fig.suptitle(f"{nombre}: mes pronosticado desde el día anterior, con lo que se sabía entonces", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(GRAFICOS / f"prueba_mes_conocido_{archivo}.png", dpi=110)
    plt.close(fig)

t = pd.DataFrame(filas)
t.to_csv(TABLAS / "prueba_mes_conocido.csv", index=False)
print(t.to_string(index=False))
for s, g in t.groupby("serie"):
    print(f"\n{s}: promedio de los {len(g)} meses -> dentro de la banda del modelo {g.dentro_banda_modelo_pct.mean():.0f} %, "
          f"dentro de la banda de ruido puro {g.dentro_banda_ruido_puro_pct.mean():.0f} %, ancho del modelo {g.ancho_banda_modelo_pct_del_pron.mean():.0f} % "
          f"vs ruido puro {g.ancho_banda_ruido_puro_pct_del_pron.mean():.0f} % del pronostico")
