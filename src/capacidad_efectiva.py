"""
capacidad_efectiva.py  -  version 1 (4-nov-2026)
Exploracion 2: estimar la CAPACIDAD EFECTIVA de camas a partir de los datos, sin depender de la cifra del HUN.

IDEA
  Si hay una cola de pacientes esperando cama, las camas disponibles estan llenas. En las horas con cola, la ocupacion deberia
  acercarse a la capacidad real de operacion. Se mira, hora por hora:
    O(t) = camas ocupadas (estancias unicas, intervalo completo)
    Q(t) = pacientes que ya llegaron, se hospitalizaran y aun no tienen cama (desde el inicio del episodio hasta el inicio de la cama)
  y se estudia O dado Q (por ano) y Q dado O (para ver si hay una rodilla: un nivel de O donde Q despega).

LIMITES
  - Q solo cuenta a quienes luego se hospitalizan (cota inferior de la cola real), y su inicio es el del episodio (llegada), no el de la solicitud de cama.
  - Si la cola es casi permanente (la espera mediana es de 18 h), Q rara vez es cero y el metodo pierde contraste.
  - Asociacion, no causa. Periodo hasta el 9-abr-2026.

ENTRADA datos/procesados/tabla_episodios.parquet ; SALIDAS resultados/tablas/capacidad_efectiva_*.csv, resultados/graficos/capacidad_efectiva.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC, TABLAS, GRAF = RAIZ / "datos" / "procesados", RAIZ / "resultados" / "tablas", RAIZ / "resultados" / "graficos"
INI, FIN = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10")
pd.set_option("display.width", 200)

t = pd.read_parquet(PROC / "tabla_episodios.parquet", columns=["estancia_unica", "hospitalizado", "ini_est", "ini_hosp_est", "fin_hosp_est", "ini"])
e = t[t.estancia_unica & t.hospitalizado & t.ini_hosp_est.notna()].copy()
e["fin_hosp_est"] = e.fin_hosp_est.fillna(pd.Timestamp("2100-01-01"))
e["ini_est"] = e.ini_est.fillna(e.ini)
e = e[e.ini_est <= e.ini_hosp_est]
horas = pd.Series(pd.date_range(INI, FIN, freq="h", inclusive="left"))


def abiertos(ini, fin, m):
    a, b = np.sort(ini.values.astype("datetime64[ns]")), np.sort(fin.values.astype("datetime64[ns]"))
    m = m.values.astype("datetime64[ns]")
    return np.searchsorted(a, m, side="left") - np.searchsorted(b, m, side="right")


d = pd.DataFrame({"hora": horas})
d["O"] = abiertos(e.ini_hosp_est, e.fin_hosp_est, horas)
d["Q"] = abiertos(e.ini_est, e.ini_hosp_est, horas)
d["anio"] = d.hora.dt.year
d.loc[d.hora < "2024-01-01", "anio"] = 2023
print(f"horas: {len(d)} | Q media {d.Q.mean():.1f} | horas con Q = 0: {100 * (d.Q == 0).mean():.1f} % | Q p90 {d.Q.quantile(.9):.0f}")

print("\nO (camas ocupadas) segun el tamano de la cola Q, por ano:")
d["cola"] = pd.cut(d.Q, [-1, 5, 15, 30, 1000], labels=["cola 0-5", "cola 6-15", "cola 16-30", "cola >30"])
r = d.groupby(["anio", "cola"], observed=True).O.agg(["size", "median", lambda s: s.quantile(.9), "max"]).round(0)
r.columns = ["horas", "O_mediana", "O_p90", "O_max"]
print(r.to_string())
r.to_csv(TABLAS / "capacidad_efectiva_por_cola.csv")

print("\nQ (cola media) segun el nivel de O (rodilla?), todo el periodo y por ano:")
d["Obin"] = pd.cut(d.O, [0, 70, 80, 90, 95, 100, 105, 110, 115, 200])
q = d.groupby("Obin", observed=True).agg(horas=("Q", "size"), cola_media=("Q", "mean"), cola_p90=("Q", lambda s: s.quantile(.9))).round(1)
print(q.to_string())
q.to_csv(TABLAS / "capacidad_efectiva_cola_por_ocupacion.csv")
por_anio = d.groupby(["anio", "Obin"], observed=True).Q.mean().unstack(0).round(1)
print(por_anio.to_string())

# efecto de la ocupacion sobre la cola controlando la hora del dia (la cola tiene ciclo diario)
d["hora_dia"] = d.hora.dt.hour
b = np.polyfit(d.O, d.Q, 1)
print(f"\npendiente de la cola sobre la ocupacion (todo el periodo): {b[0]:.2f} pacientes en cola por cama ocupada adicional")
for a_ in sorted(d.anio.unique()):
    s = d[d.anio == a_]
    print(f"  {a_}: correlacion O-Q = {s[['O', 'Q']].corr().iloc[0, 1]:.2f}; O media {s.O.mean():.0f}, p99 {s.O.quantile(.99):.0f}, max {s.O.max()}")

fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
for a_, col in zip(sorted(d.anio.unique()), ["#9ecae1", "#6baed6", "#2171b5", "#08306b"]):
    s = d[d.anio == a_].groupby("Obin", observed=True).Q.mean()
    ax[0].plot([i.mid for i in s.index], s.values, marker="o", color=col, label=str(a_))
ax[0].set_xlabel("camas ocupadas (O)")
ax[0].set_ylabel("pacientes en cola por cama (Q, media)")
ax[0].set_title("Cola segun ocupacion", fontsize=10)
ax[0].legend(fontsize=8)
ax[1].hexbin(d.O, d.Q, gridsize=40, cmap="Blues", mincnt=1)
ax[1].set_xlabel("camas ocupadas (O)")
ax[1].set_ylabel("cola (Q)")
ax[1].set_title("Cada hora del periodo", fontsize=10)
ax[1].axvline(106, color="grey", ls="--", lw=1)
plt.tight_layout()
plt.savefig(GRAF / "capacidad_efectiva.png", dpi=130)
print("\nguardado: capacidad_efectiva_*.csv y capacidad_efectiva.png")
