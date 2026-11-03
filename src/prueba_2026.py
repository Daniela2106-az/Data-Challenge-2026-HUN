"""
prueba_2026.py  -  version 1 (1-nov-2026)
Pronostica 2026 hasta el 9 de abril (fin del periodo confiable) desde el 31 de diciembre de 2025, usando solo lo que se sabia ese dia, y pone encima lo que
paso de verdad. Sirve para ver donde el dato real sale de la banda, y que el modelo no puede anticipar la degradacion del registro desde el 10-abr-2026.

  - Linea azul: pronostico con el nivel "historico" (12 meses hasta diciembre de 2025).
  - Zona azul clara: banda del 80 %, armada solo con errores de dias ya conocidos al 31-dic-2025.
  - Linea punteada naranja: pronostico con el nivel "reciente" (ultimos 28 dias de 2025).
  - Linea gris y puntos: lo real SIN limpiar. Puntos oscuros dentro de la banda, rojos fuera.
  - Panel de abajo: promedio de 7 dias del real contra los dos pronosticos.

SALIDAS  resultados/graficos/prueba_2026_llegadas.png, prueba_2026_ingresos.png; resultados/tablas/prueba_2026.csv (resumen) y prueba_2026_diario.csv (un dia por fila: real, pronosticos y banda; con esto se rehacen los graficos)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import modelo_pronostico as mp

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
CORTE = pd.Timestamp("2025-12-31")
FIN = pd.Timestamp(mp.FIN_CONFIABLE)
DIAS = (FIN - CORTE).days

real = mp.cargar_panel(limpiar=False)
limpio = mp.cargar_panel()
filas, DIARIO = [], []
for obj, nombre, archivo in [("llegadas_con_atencion", "Llegadas con atención por día", "llegadas_con_atencion"), ("llegadas", "Llegadas por día", "llegadas"), ("ingresos_a_cama", "Ingresos a cama por día", "ingresos")]:
    serie = limpio[obj]
    bt = mp.retroceso(serie)
    cal = mp.calendario(pd.date_range(serie.index.min(), serie.index.max() + pd.Timedelta(days=400)))
    hist = serie.loc[:CORTE]
    ph = mp.pronosticar_desde(hist, cal, CORTE, DIAS, "historico")
    pr = mp.pronosticar_desde(hist, cal, CORTE, DIAS, "reciente")
    fb = mp.factores_banda(bt[bt.fecha <= CORTE], excluir_caida=False)
    lead = np.arange(1, DIAS + 1)
    lo_f, hi_f = np.empty(DIAS), np.empty(DIAS)
    for (a, b), (l, h) in fb.items():
        m = (lead >= a) & (lead <= b)
        lo_f[m], hi_f[m] = l, h
    lo, hi = pd.Series(ph.values * lo_f, ph.index), pd.Series(ph.values * hi_f, ph.index)
    y = real[obj].reindex(ph.index)
    dentro = (y >= lo) & (y <= hi)
    DIARIO.append(pd.DataFrame({"fecha": ph.index.strftime("%Y-%m-%d"), "serie": obj, "real": y.values, "pronostico_historico": ph.values.round(1),
                                "pronostico_reciente": pr.values.round(1), "banda_baja": lo.values.round(1), "banda_alta": hi.values.round(1),
                                "real_dentro_de_la_banda": dentro.values.astype(int), "dias_adelante": lead}))
    for nombre_p, mask in [("1 ene - 9 abr", ph.index <= FIN)]:
        yy, pp = y[mask], ph[mask]
        filas.append(dict(serie=obj, periodo=nombre_p, dias=int(mask.sum()), dentro_banda_pct=round(100 * dentro[mask].mean()),
                          real_promedio=round(yy.mean(), 1), pronostico_historico=round(pp.mean(), 1),
                          pronostico_reciente=round(pr[mask].mean(), 1), diferencia_real_vs_historico_pct=round(100 * (yy.mean() / pp.mean() - 1), 1),
                          wape_historico_pct=round(100 * (yy - pp).abs().sum() / yy.sum(), 1)))

    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={"height_ratios": [2.2, 1.2]}, sharex=True)
    ax.fill_between(ph.index, lo, hi, color="#2a6fb0", alpha=0.15, label="banda 80 % (con lo que se sabía al 31-dic-2025)")
    ax.plot(ph.index, ph.values, color="#2a6fb0", lw=2, label="pronóstico, nivel histórico")
    ax.plot(pr.index, pr.values, color="#d9730d", lw=1.2, ls=":", label="pronóstico, nivel reciente (fin de 2025)")
    ax.plot(y.index, y.values, color="#444", lw=0.9, alpha=0.6, label="real")
    ax.scatter(y.index[dentro.values], y.values[dentro.values], color="#222", s=16, zorder=3, label="real dentro de la banda")
    ax.scatter(y.index[~dentro.values], y.values[~dentro.values], color="#c0392b", s=26, zorder=3, label="real fuera de la banda")
    for a_ in (ax, ax2):
        a_.grid(alpha=0.25)
    d_ant = dentro.mean()
    ax.set_title(f"{nombre} en 2026 hasta el 9-abr, pronosticado desde el 31-dic-2025: {100 * d_ant:.0f} % de los días reales dentro de la banda", fontsize=11)
    ax.set_ylabel(nombre)
    ax.legend(fontsize=8, ncol=2, loc="lower left")
    y7, ph7, pr7 = y.rolling(7).mean(), ph.rolling(7).mean(), pr.rolling(7).mean()
    ax2.plot(y7.index, y7.values, color="#222", lw=1.8, label="real (promedio 7 días)")
    ax2.plot(ph7.index, ph7.values, color="#2a6fb0", lw=1.8, label="pronóstico histórico (7 días)")
    ax2.plot(pr7.index, pr7.values, color="#d9730d", lw=1.2, ls=":", label="pronóstico reciente (7 días)")
    ax2.legend(fontsize=8)
    ax2.set_ylabel("promedio de 7 días")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m"))
    fig.tight_layout()
    fig.savefig(GRAFICOS / f"prueba_2026_{archivo}.png", dpi=110)
    plt.close(fig)

t = pd.DataFrame(filas)
t.to_csv(TABLAS / "prueba_2026.csv", index=False)
pd.concat(DIARIO).to_csv(TABLAS / "prueba_2026_diario.csv", index=False)
print(t.to_string(index=False))
