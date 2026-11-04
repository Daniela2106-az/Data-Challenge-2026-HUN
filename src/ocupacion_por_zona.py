"""
ocupacion_por_zona.py  -  version 1 (4-nov-2026)
Exploracion 1 de "otras cosas para explorar": ocupacion por ZONA frente a las capacidades que dio el HUN (29-oct-2026).

PREGUNTA
  Comparar toda la ocupacion contra las 106 camas mezcla zonas. El HUN dio el desglose:
    camas de hospitalizacion: adultos 88 (piso 64 + intermedio 6 + intensiva 14 + TPR 4), ninos 18 (pediatrica 8 + neonatal 10).
    camillas de urgencias:    observacion pediatrica 14, adultos hombres 18, adultos mujeres 26.
  Con edad y sexo de la persona real (CLAUDE.md 4.10) se puede ver en QUE zona se supera la capacidad y si el sexo
  ayuda a entender por que las mujeres esperan mas cama (hallazgo abierto de A1).

QUE HACE
  A. Camas de hospitalizacion ocupadas por hora, por grupo (menores de 1 ano, 1-14, adultos hombres, adultos mujeres), frente a la capacidad
     de cada zona. Estancias unicas, intervalo completo de la estancia.
  B. Pacientes en atencion de urgencias (TU con hora de fin registrada) por hora y grupo (menores de 15, hombres 15+, mujeres 15+), frente
     a las camillas. Cada intervalo distinto se cuenta una vez. OJO: solo el ~38 % de los TU tiene hora de fin, asi que es una COTA INFERIOR.
  C. Espera de cama por grupo y su relacion con la saturacion de urgencias de ese grupo al llegar, para ver si la brecha por sexo cambia.

LIMITES (declararlos siempre)
  - Los grupos son aproximaciones por edad y sexo: no hay servicio, piso ni cama en la base. Un adulto puede estar en UCI o en intermedio, un
    nino de 12 anos puede estar en adultos, un lactante puede estar en pediatria y no en neonatal, y las camas no se reparten por sexo
    (el HUN solo dio el sexo para las camillas de urgencias).
  - La lista de camas del HUN no trae fecha: puede no corresponder a 2023-2025.
  - Asociacion, no causa.

ENTRADAS  datos/procesados/tabla_episodios.parquet, datos/procesados/bloques.csv
SALIDAS   resultados/tablas/ocupacion_zona_hospitalizacion.csv, ocupacion_zona_urgencias.csv, ocupacion_zona_espera.csv
          resultados/graficos/ocupacion_por_zona.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC, TABLAS, GRAF = RAIZ / "datos" / "procesados", RAIZ / "resultados" / "tablas", RAIZ / "resultados" / "graficos"
FIN = pd.Timestamp("2026-04-10")         # el registro de etapas se degrada desde el 10-abr-2026
INI = pd.Timestamp("2023-02-01")
CAP_CAMAS = {"menores de 1": 10, "1 a 14": 8, "adultos hombres": np.nan, "adultos mujeres": np.nan}   # neonatal 10, pediatrica 8; adultos 88 en total
CAP_ADULTOS, CAP_NINOS = 88, 18
CAP_CAMILLAS = {"menores de 15": 14, "hombres 15+": 18, "mujeres 15+": 26}
PERIODOS = [("2023", "2023-02-01", "2024-01-01"), ("2024", "2024-01-01", "2025-01-01"), ("2025", "2025-01-01", "2026-01-01"), ("2026 (hasta 9-abr)", "2026-01-01", "2026-04-10")]

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)

t = pd.read_parquet(PROC / "tabla_episodios.parquet", columns=["visit_occurrence_id", "episodio", "ini", "sexo", "edad", "estancia_unica", "hospitalizado",
                                                                  "ini_hosp_est", "fin_hosp_est", "espera_cama_h", "llegadas_6h_previas"])


def grupo_cama(df):
    g = np.where(df.edad < 1, "menores de 1", np.where(df.edad < 15, "1 a 14", np.where(df.sexo == "Hombre", "adultos hombres", np.where(df.sexo == "Mujer", "adultos mujeres", "sin dato"))))
    return pd.Series(g, index=df.index)


def abiertos(ini, fin, momentos):
    a, b = np.sort(ini.values.astype("datetime64[ns]")), np.sort(fin.values.astype("datetime64[ns]"))
    m = momentos.values.astype("datetime64[ns]")
    return np.searchsorted(a, m, side="left") - np.searchsorted(b, m, side="right")


horas = pd.Series(pd.date_range(INI, FIN, freq="h", inclusive="left"))

# ------------------------------------------------------------------ A. camas de hospitalizacion
est = t[t.estancia_unica & t.hospitalizado & t.ini_hosp_est.notna()].copy()
est["fin_hosp_est"] = est.fin_hosp_est.fillna(pd.Timestamp("2100-01-01"))
est["grupo"] = grupo_cama(est)
print("estancias unicas:", len(est), "| sin dato de sexo/edad:", int((est.grupo == "sin dato").sum()))
oc = pd.DataFrame({"hora": horas})
for g, d in est.groupby("grupo"):
    oc[g] = abiertos(d.ini_hosp_est, d.fin_hosp_est, horas)
oc["ninos (<15)"] = oc["menores de 1"] + oc["1 a 14"]
oc["adultos"] = oc["adultos hombres"] + oc["adultos mujeres"]
oc["total"] = oc["ninos (<15)"] + oc["adultos"] + oc.get("sin dato", 0)
CAP = {"menores de 1": 10, "1 a 14": 8, "ninos (<15)": CAP_NINOS, "adultos": CAP_ADULTOS, "total": 106}
filas = []
for nombre, d, h in PERIODOS:
    s = oc[(oc.hora >= d) & (oc.hora < h)]
    for z, cap in CAP.items():
        v = s[z]
        filas.append(dict(periodo=nombre, zona=z, capacidad_HUN=cap, media=round(v.mean(), 1), p95=round(v.quantile(.95)), maximo=int(v.max()),
                          pct_media_sobre_capacidad=round(100 * v.mean() / cap, 1), pct_horas_sobre_capacidad=round(100 * (v > cap).mean(), 1)))
    for z in ["adultos hombres", "adultos mujeres"]:
        v = s[z]
        filas.append(dict(periodo=nombre, zona=z, capacidad_HUN=np.nan, media=round(v.mean(), 1), p95=round(v.quantile(.95)), maximo=int(v.max()),
                          pct_media_sobre_capacidad=np.nan, pct_horas_sobre_capacidad=np.nan))
A = pd.DataFrame(filas)
A.to_csv(TABLAS / "ocupacion_zona_hospitalizacion.csv", index=False)
print("\nA. CAMAS DE HOSPITALIZACION POR ZONA (capacidad del HUN, 29-oct-2026)")
print(A[A.zona.isin(["adultos", "ninos (<15)", "menores de 1", "1 a 14", "total"])].to_string(index=False))
print("\nadultos por sexo (media de camas):")
print(A[A.zona.isin(["adultos hombres", "adultos mujeres"])].pivot(index="periodo", columns="zona", values="media").to_string())

# ------------------------------------------------------------------ B. camillas de urgencias
bl = pd.read_csv(PROC / "bloques.csv", parse_dates=["ini", "fin"])
tu = bl[(bl.etapa == "TU") & (bl.fin > bl.ini)].merge(t[["visit_occurrence_id", "episodio", "sexo", "edad"]], on=["visit_occurrence_id", "episodio"], how="left")
tu["zona"] = np.where(tu.edad < 15, "menores de 15", np.where(tu.sexo == "Hombre", "hombres 15+", np.where(tu.sexo == "Mujer", "mujeres 15+", "sin dato")))
tu = tu.drop_duplicates(["ini", "fin", "zona"])          # el mismo intervalo registrado en gemelos se cuenta una vez
ocu = pd.DataFrame({"hora": horas})
for z in CAP_CAMILLAS:
    d = tu[tu.zona == z]
    ocu[z] = abiertos(d.ini, d.fin, horas)
filas = []
for nombre, d, h in PERIODOS:
    s = ocu[(ocu.hora >= d) & (ocu.hora < h)]
    for z, cap in CAP_CAMILLAS.items():
        v = s[z]
        filas.append(dict(periodo=nombre, zona=z, camillas_HUN=cap, media=round(v.mean(), 1), p95=round(v.quantile(.95)), maximo=int(v.max()),
                          razon_media_camillas=round(v.mean() / cap, 2), pct_horas_sobre_camillas=round(100 * (v > cap).mean(), 1)))
B = pd.DataFrame(filas)
B.to_csv(TABLAS / "ocupacion_zona_urgencias.csv", index=False)
print("\nB. PACIENTES EN URGENCIAS (TU con hora de fin) POR ZONA FRENTE A LAS CAMILLAS (cota inferior: solo ~38 % tiene hora de fin)")
print(B.to_string(index=False))

# ------------------------------------------------------------------ C. espera de cama y saturacion de urgencias del grupo
e = t[t.estancia_unica & t.hospitalizado & t.espera_cama_h.notna() & (t.ini >= INI) & (t.ini < FIN)].copy()
e["zona"] = np.where(e.edad < 15, "menores de 15", np.where(e.sexo == "Hombre", "hombres 15+", np.where(e.sexo == "Mujer", "mujeres 15+", "sin dato")))
e = e[e.zona != "sin dato"]
for z in CAP_CAMILLAS:
    m = e.zona == z
    e.loc[m, "razon_tu_llegada"] = abiertos(tu[tu.zona == z].ini, tu[tu.zona == z].fin, e.loc[m, "ini"]) / CAP_CAMILLAS[z]
filasC = []
for z, d in e.groupby("zona"):
    rho = d[["razon_tu_llegada", "espera_cama_h"]].corr(method="spearman").iloc[0, 1]
    filasC.append(dict(zona=z, estancias=len(d), espera_mediana_h=round(d.espera_cama_h.median(), 1), espera_p90_h=round(d.espera_cama_h.quantile(.9), 1),
                       pct_espera_mas_24h=round(100 * (d.espera_cama_h > 24).mean(), 1), razon_tu_llegada_media=round(d.razon_tu_llegada.mean(), 2),
                       spearman_razon_vs_espera=round(rho, 3)))
C = pd.DataFrame(filasC)
C.to_csv(TABLAS / "ocupacion_zona_espera.csv", index=False)
print("\nC. ESPERA DE CAMA POR ZONA Y SATURACION DE URGENCIAS DE ESA ZONA AL LLEGAR")
print(C.to_string(index=False))
ad = e[e.zona.isin(["hombres 15+", "mujeres 15+"])].copy()
ad["tercil"] = pd.qcut(ad.razon_tu_llegada, 3, labels=["baja", "media", "alta"], duplicates="drop")
print("\nBrecha por sexo (adultos 15+) segun la saturacion de urgencias de su grupo al llegar (mediana de espera, h):")
print(ad.groupby(["tercil", "zona"], observed=True).espera_cama_h.agg(["median", "size"]).round(1).unstack().to_string())

# ------------------------------------------------------------------ grafico
fig, ax = plt.subplots(1, 2, figsize=(14, 4.8))
x = np.arange(len(PERIODOS))
for z, col in [("adultos", "#2a6fb0"), ("ninos (<15)", "#d9730d")]:
    r = A[A.zona == z].set_index("periodo").loc[[p[0] for p in PERIODOS]]
    ax[0].plot(x, 100 * r["media"] / CAP[z], marker="o", color=col, label=f"{z} (capacidad {CAP[z]})")
ax[0].axhline(100, color="grey", ls="--", lw=1)
ax[0].set_xticks(x, [p[0] for p in PERIODOS])
ax[0].set_ylabel("% de la capacidad (media de camas ocupadas)")
ax[0].set_title("Hospitalizacion: ocupacion media frente a las camas del HUN", fontsize=10)
ax[0].legend(fontsize=8)
for z, col in [("menores de 15", "#d9730d"), ("hombres 15+", "#2a6fb0"), ("mujeres 15+", "#7a3e9d")]:
    r = B[B.zona == z].set_index("periodo").loc[[p[0] for p in PERIODOS]]
    ax[1].plot(x, r.razon_media_camillas, marker="o", color=col, label=f"{z} ({CAP_CAMILLAS[z]} camillas)")
ax[1].axhline(1, color="grey", ls="--", lw=1)
ax[1].set_xticks(x, [p[0] for p in PERIODOS])
ax[1].set_ylabel("pacientes en urgencias con hora de fin / camillas")
ax[1].set_title("Urgencias (cota inferior): pacientes por camilla", fontsize=10)
ax[1].legend(fontsize=8)
plt.tight_layout()
plt.savefig(GRAF / "ocupacion_por_zona.png", dpi=130)
print("\nguardado: ocupacion_zona_*.csv y ocupacion_por_zona.png")
