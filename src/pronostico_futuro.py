"""
pronostico_futuro.py  -  version 1 (1-nov-2026)
Genera las tablas del pronostico HACIA ADELANTE (365 dias desde manana) y el error por horizonte, con el modelo de src/modelo_pronostico.py.
Sirven para el dashboard (Dash lee el panel y corre el modelo en vivo; Power BI, si se usa, lee estas tablas ya calculadas).

ENTRADAS  datos/procesados/para_equipo/panel_diario.csv
SALIDAS   resultados/tablas/pronostico_futuro.csv            un dia por fila: objetivo, escenario, fecha, pronostico, banda_baja, banda_alta, dias_adelante
          resultados/tablas/pronostico_error_por_horizonte.csv   WAPE, sesgo y factores de banda por tramo de horizonte (con y sin la caida de datos)
          resultados/graficos/pronostico_futuro.png

LECTURA
  - Escenario "reciente": el nivel de los ultimos 28 dias (incluye la caida de mayo de 2026). "historico": el nivel de los 12 meses
    antes de la caida. Que escenario es el real no se sabe (pregunta 14 al HUN, sin respuesta): se muestran los dos.
  - El error crece con el horizonte; mas alla de ~3 meses es una tendencia con banda ancha, no una prediccion fina.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import modelo_pronostico as mp

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
for d in (TABLAS, GRAFICOS):
    d.mkdir(parents=True, exist_ok=True)

panel = mp.cargar_panel()
DESDE = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)      # el pronostico parte de manana, con el nivel y el calendario del periodo confiable (hasta 9-abr-2026)
filas, errores = [], []
fig, ejes = plt.subplots(1, 3, figsize=(19, 4.5))
for ax, (obj, nombre) in zip(ejes, mp.OBJETIVOS.items()):
    serie = panel[obj]
    bt = mp.retroceso(serie)
    for sin_caida, etiqueta in [(False, "todos los cortes"), (True, "periodo confiable (destino antes del 10-abr-2026)")]:
        e = mp.tabla_error(bt, sin_caida)
        e.insert(0, "objetivo", obj)
        e.insert(1, "evaluacion", etiqueta)
        errores.append(e)
    real = mp.cargar_panel(limpiar=False)[obj]
    ax.plot(real.index, real.rolling(7).mean(), color="#444", lw=1.2, label="histórico (promedio 7 días)")
    for esc, color in [("reciente", "#c0392b"), ("historico", "#2471a3")]:
        f = mp.pronostico_con_banda(serie, bt, 365, esc, 0.0, True, False, DESDE)
        f.insert(0, "escenario", esc)
        f.insert(0, "objetivo", obj)
        filas.append(f)
        ax.plot(f.fecha, f.pronostico.rolling(7, min_periods=1).mean(), color=color, lw=1.5, label=f"pronóstico, nivel {esc}")
        ax.fill_between(f.fecha, f.banda_baja.rolling(7, min_periods=1).mean(), f.banda_alta.rolling(7, min_periods=1).mean(),
                        color=color, alpha=0.12)
    ax.set_title(nombre + " (promedio móvil de 7 días; banda del 80 % de los días)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(GRAFICOS / "pronostico_futuro.png", dpi=130)

fut = pd.concat(filas, ignore_index=True)
fut["fecha"] = fut.fecha.dt.strftime("%Y-%m-%d")
for c in ["pronostico", "banda_baja", "banda_alta"]:
    fut[c] = fut[c].round(1)
fut.to_csv(TABLAS / "pronostico_futuro.csv", index=False)
err = pd.concat(errores, ignore_index=True)
err.to_csv(TABLAS / "pronostico_error_por_horizonte.csv", index=False)

print("ultimo dia con datos:", panel.dropna().index.max().date())
print(err.to_string(index=False))
print("\npromedio pronosticado por dia (primeros 30 dias / 365 dias):")
print(fut.groupby(["objetivo", "escenario"]).apply(lambda g: pd.Series({"30 dias": g.pronostico.iloc[:30].mean().round(1),
                                                                        "365 dias": g.pronostico.mean().round(1)})).to_string())
print("guardado: pronostico_futuro.csv, pronostico_error_por_horizonte.csv, pronostico_futuro.png")
