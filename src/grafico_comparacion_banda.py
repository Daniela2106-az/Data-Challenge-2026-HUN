"""
grafico_comparacion_banda.py  -  version 1 (1-nov-2026)
Grafica, para la serie 'llegadas' (todas), las tres corridas de src/comparacion_banda_caida.py con la misma escala, para comparar a simple vista
el sombreado azul claro (banda del 80 %). Mismo estilo que el dashboard: promedio de 7 dias del pronostico y de la banda.

  A  datos hasta 2025-12-31 (sin la caida)           B  datos hasta 2026-05-31 (con la caida)        C  la foto del dash (nivel y banda sin la caida)
Gris: lo real (promedio de 7 dias); en A, lo real posterior a su corte se dibuja mas claro porque la corrida no lo conocia.

SALIDA  resultados/graficos/comparacion_banda_caida_llegadas.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import modelo_pronostico as mp

RAIZ = Path(__file__).resolve().parent.parent
GRAFICOS = RAIZ / "resultados" / "graficos"
HASTA = pd.Timestamp("2027-04-30")
OBJ = "llegadas"
CORRIDAS = [("A · datos hasta 2025-12 (sin la caída)", dict(corte="2025-12-31", entrena="2026-04-30", excl=False)),
            ("B · datos hasta 2026-05 (con la caída en el modelo y en la banda)", dict(corte="2026-05-31", entrena="2026-05-31", excl=False)),
            ("C · foto del dash (hasta 2026-05; nivel y banda sin la caída)", dict(corte="2026-05-31", entrena="2026-04-30", excl=True))]

panel = mp.cargar_panel()
real = mp.cargar_panel(limpiar=False)[OBJ]
real7 = real.rolling(7).mean()
orig = mp.ENTRENA_HASTA
res = []
for nombre, c in CORRIDAS:
    mp.ENTRENA_HASTA = c["entrena"]
    serie = panel[OBJ].loc[:c["corte"]]
    bt = mp.retroceso(serie)
    f = mp.pronostico_con_banda(serie, bt, (HASTA - pd.Timestamp(c["corte"])).days, "historico", 0.0, c["excl"])
    for col in ("pronostico", "banda_baja", "banda_alta"):
        f[col + "_7"] = f[col].rolling(7, min_periods=1).mean()
    res.append((nombre, c, f))
mp.ENTRENA_HASTA = orig

X0 = pd.Timestamp("2026-01-01")
ylim = (130, 360)
fig, ejes = plt.subplots(4, 1, figsize=(14, 15), sharex=True)
for ax, (nombre, c, f) in zip(ejes, res):
    corte = pd.Timestamp(c["corte"])
    r = real7.loc[X0:"2026-05-31"]
    ax.plot(r.loc[:corte].index, r.loc[:corte].values, color="#555", lw=1.6, label="real (promedio 7 días), conocido por la corrida")
    if corte < pd.Timestamp("2026-05-31"):
        ax.plot(r.loc[corte:].index, r.loc[corte:].values, color="#aaa", lw=1.6, label="real que la corrida no conocía")
    g = f[f.fecha >= X0]
    ax.fill_between(g.fecha, g.banda_baja_7, g.banda_alta_7, color="#2a6fb0", alpha=0.18, label="banda 80 % (promedio 7 días)")
    ax.plot(g.fecha, g.pronostico_7, color="#2a6fb0", lw=2, label="pronóstico (promedio 7 días)")
    ax.axvline(corte, color="#c0392b", ls="--", lw=0.9)
    ax.axvspan(pd.Timestamp("2026-07-01"), HASTA, color="#000", alpha=0.03)
    j = f[(f.fecha >= "2026-07-01") & (f.fecha <= HASTA)]
    ancho = 100 * ((j.banda_alta - j.banda_baja) / j.pronostico).mean()
    ax.set_title(f"{nombre}: ancho relativo medio de la banda jul-2026 a abr-2027 = {ancho:.1f} %", fontsize=10.5)
    ax.set_ylim(*ylim)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="lower left", ncol=2)
    ax.set_ylabel("llegadas por día")

ax = ejes[3]
colores = ["#7f8c8d", "#c0392b", "#2a6fb0"]
for (nombre, c, f), col in zip(res, colores):
    j = f[(f.fecha >= "2026-07-01") & (f.fecha <= HASTA)]
    ax.plot(j.fecha, j.banda_alta_7, color=col, lw=1.4)
    ax.plot(j.fecha, j.banda_baja_7, color=col, lw=1.4, label=nombre.split("·")[0].strip() + " (bordes de la banda)")
ax.set_ylim(*ylim)
ax.set_title("Los tres bordes de banda superpuestos (julio 2026 a abril 2027)", fontsize=10.5)
ax.grid(alpha=0.25)
ax.legend(fontsize=8, loc="lower left", ncol=3)
ax.set_ylabel("llegadas por día")
fig.tight_layout()
fig.savefig(GRAFICOS / "comparacion_banda_caida_llegadas.png", dpi=110)
print("guardado: resultados/graficos/comparacion_banda_caida_llegadas.png")
