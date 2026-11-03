"""
dependencia_carga.py  -  version 1 (22-oct-2026)
Fase 4 del plan de cuellos de botella (docs/plan_de_accion.md, seccion 0).

PREGUNTA: la espera empeora cuando el hospital esta mas cargado (falta capacidad), o depende de la hora
de llegada (turnos), o es larga sin importar la carga (proceso)?

QUE HACE (para cada segmento candidato: espera_cama, urgencias_antes_cama, hueco_antes_cama)
  1. Mide la carga de cada episodio al llegar: llegadas de las 6 y 24 h previas (de Q3) y pacientes en cama /
     en TU en la hora anterior (de Q4; solo feb-2023 a may-2026, antes y despues la ocupacion no es confiable).
  2. Tablas por decil de carga: media, mediana, p90, % > 24 h y razon contra el decil mas bajo.
  3. Efecto de la carga con controles (regresion sobre log(horas + 1)): sin controles, con edad y anio, y
     ademas con franja horaria. Es un % de cambio por cada decil de carga que se sube.
  4. Efecto de la hora de llegada, con y sin control de carga (separa "turnos" de "carga").
  5. Clasificacion orientativa de cada segmento y grafico.

ENTRADAS  datos/procesados/segmentos.csv (construir_segmentos.py) y datos/crudos/q4_ocupacion_por_hora.csv (Q4)
SALIDAS   resultados/tablas/carga_por_decil.csv, carga_efectos.csv, hora_efectos.csv, hora_llegada.csv
          resultados/graficos/dependencia_carga.png

OJO AL LEER
  - Son asociaciones, no causas. La carga y la hora estan mezcladas (la tarde y la manana son las horas de mas
    llegadas), por eso se estiman juntas.
  - llegadas_6h_previas cuenta llegadas (incluye algunas replicas de otras personas, >= 4 %): sirve como medida
    relativa. La ocupacion de Q4 cuenta cada estancia una vez, pero su nivel (~100) es incierto.
  - La clasificacion usa umbrales de criterio (ver CLASIFICACION): se reportan los numeros para que se discutan.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

SUFIJO = os.environ.get("SUFIJO", "")
RAIZ = Path(__file__).resolve().parent.parent
CRUDOS = RAIZ / "datos" / "crudos"
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
for _d in (TABLAS, GRAFICOS):
    _d.mkdir(parents=True, exist_ok=True)

CANDIDATOS = ["espera_cama", "urgencias_antes_cama", "hueco_antes_cama"]
CARGAS = {"llegadas_6h_previas": "llegadas 6 h previas", "llegadas_24h_previas": "llegadas 24 h previas",
          "ocup_hosp": "pacientes en cama", "ocup_tu": "pacientes en TU"}
OCUP_DESDE, OCUP_HASTA = "2023-02-01", "2026-04-10"
# criterio orientativo (se pueden discutir): una carga "importa" si subir un decil aumenta el tiempo al menos
# UMBRAL_CARGA % con controles, y la razon entre el decil alto y el bajo es de al menos RAZON_ALTA
UMBRAL_CARGA, RAZON_ALTA, UMBRAL_HORA = 1.0, 1.25, 15.0

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


def ols(y, X):
    """Minimos cuadrados con errores estandar clasicos. Devuelve coeficientes y estadistico t."""
    X = np.asarray(X, dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    s2 = res @ res / (len(y) - X.shape[1])
    se = np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))
    return beta, beta / se


def con_dummies(df, cols):
    return pd.get_dummies(df[cols], drop_first=True, dtype=float) if cols else pd.DataFrame(index=df.index)


# ----------------------------------------------------------------------
# 1) Carga
# ----------------------------------------------------------------------
titulo("1. CARGA Y CONTROLES")
seg = pd.read_csv(PROC / f"segmentos{SUFIJO}.csv", parse_dates=["ini"])
d = seg[seg.segmento.isin(CANDIDATOS) & seg.en_estadisticas].copy()
oc = pd.read_csv(CRUDOS / "q4_ocupacion_por_hora.csv", parse_dates=["hora"])
d["hora_prev"] = d.ini.dt.floor("h") - pd.Timedelta(hours=1)    # ocupacion al final de la hora anterior
d = d.merge(oc.rename(columns={"hora": "hora_prev", "ocup_hosp_fin_hora": "ocup_hosp",
                               "ocup_tu_fin_hora": "ocup_tu"}), on="hora_prev", how="left")
fuera = ~d.ini.between(OCUP_DESDE, OCUP_HASTA)
d.loc[fuera, ["ocup_hosp", "ocup_tu"]] = np.nan
d["grupo_edad"] = d.grupo_edad.fillna("sin dato").astype(str)
d["franja"] = d.franja.astype(str)
print(d.groupby("segmento").size().rename("filas").to_string())
print("rango de las cargas (episodios con espera de cama):")
print(d[d.segmento == "espera_cama"][list(CARGAS)].describe().round(1).loc[["count", "mean", "min", "50%", "max"]].to_string())

# ----------------------------------------------------------------------
# 2) Tablas por decil de carga
# ----------------------------------------------------------------------
titulo("2. TIEMPO POR DECIL DE CARGA (horas)")
filas = []
for sg in CANDIDATOS:
    g0 = d[d.segmento == sg]
    for var in CARGAS:
        g = g0.dropna(subset=[var]).copy()
        g["decil"] = pd.qcut(g[var], 10, labels=False, duplicates="drop") + 1
        t = (g.groupby("decil")
              .agg(n=("horas", "size"), carga_media=(var, "mean"), media_h=("horas", "mean"),
                   p50=("horas", "median"), p90=("horas", lambda s: s.quantile(.9)),
                   pct_mas_24h=("horas", lambda s: 100 * (s > 24).mean()))
              .reset_index())
        t["razon_vs_decil_1"] = t.media_h / t.media_h.iloc[0]
        t.insert(0, "carga", var)
        t.insert(0, "segmento", sg)
        filas.append(t)
dec = pd.concat(filas, ignore_index=True).round(2)
dec.to_csv(TABLAS / f"carga_por_decil{SUFIJO}.csv", index=False)
for var in ["llegadas_6h_previas", "ocup_hosp"]:
    print(f"\nespera_cama por decil de {var}:")
    print(dec[(dec.segmento == "espera_cama") & (dec.carga == var)]
          .drop(columns=["segmento", "carga"]).round(1).to_string(index=False))

# ----------------------------------------------------------------------
# 3) Efecto de la carga con controles
# ----------------------------------------------------------------------
titulo("3. EFECTO DE LA CARGA: % de cambio del tiempo por cada decil que se sube")
filas = []
for sg in CANDIDATOS:
    for var in CARGAS:
        g = d[(d.segmento == sg)].dropna(subset=[var]).copy()
        g["decil"] = pd.qcut(g[var], 10, labels=False, duplicates="drop") + 1
        y = np.log1p(g.horas.values)
        fila = {"segmento": sg, "carga": var, "n": len(g)}
        for nombre, ctrl in [("sin_controles", []), ("edad_y_anio", ["grupo_edad", "anio"]),
                             ("edad_anio_y_hora", ["grupo_edad", "anio", "franja"])]:
            X = pd.concat([pd.Series(1.0, index=g.index, name="const"), g[["decil"]],
                           con_dummies(g.assign(anio=g.anio.astype(str)), ctrl)], axis=1)
            b, t = ols(y, X.values)
            fila[f"pct_por_decil_{nombre}"] = round(100 * (np.exp(b[1]) - 1), 2)
            fila[f"t_{nombre}"] = round(t[1], 1)
        r = dec[(dec.segmento == sg) & (dec.carga == var)]
        fila["razon_decil_alto_vs_bajo"] = round(r.media_h.iloc[-1] / r.media_h.iloc[0], 2)
        filas.append(fila)
efe = pd.DataFrame(filas)
efe.to_csv(TABLAS / f"carga_efectos{SUFIJO}.csv", index=False)
print(efe.to_string(index=False))

# ----------------------------------------------------------------------
# 4) Efecto de la hora de llegada, con y sin control de carga
# ----------------------------------------------------------------------
titulo("4. HORA DE LLEGADA: efecto de la franja (referencia: madrugada 0-5), con y sin control de carga")
filas = []
for sg in CANDIDATOS:
    g = d[d.segmento == sg].dropna(subset=["llegadas_6h_previas"]).copy()
    g["decil_carga"] = pd.qcut(g.llegadas_6h_previas, 10, labels=False, duplicates="drop") + 1
    y = np.log1p(g.horas.values)
    base = pd.concat([pd.Series(1.0, index=g.index, name="const"),
                      con_dummies(g.assign(anio=g.anio.astype(str)), ["grupo_edad", "anio"])], axis=1)
    franjas = pd.get_dummies(g.franja, dtype=float).drop(columns="madrugada 0-5")
    for nombre, extra in [("sin_control_de_carga", [franjas]), ("con_control_de_carga", [franjas, g[["decil_carga"]]])]:
        X = pd.concat([base] + extra, axis=1)
        b, t = ols(y, X.values)
        nombres = list(X.columns)
        for f in franjas.columns:
            i = nombres.index(f)
            filas.append({"segmento": sg, "modelo": nombre, "franja": f,
                          "pct_vs_madrugada": round(100 * (np.exp(b[i]) - 1), 1), "t": round(t[i], 1)})
hora_ef = pd.DataFrame(filas)
hora_ef.to_csv(TABLAS / f"hora_efectos{SUFIJO}.csv", index=False)
print(hora_ef.pivot_table(index=["segmento", "franja"], columns="modelo", values="pct_vs_madrugada").round(1).to_string())

hl = (d[d.segmento == "espera_cama"].groupby("hora")
        .agg(n=("horas", "size"), p50=("horas", "median"), p90=("horas", lambda s: s.quantile(.9)),
             llegadas_6h_media=("llegadas_6h_previas", "mean")).round(1).reset_index())
hl.to_csv(TABLAS / f"hora_llegada{SUFIJO}.csv", index=False)

# ----------------------------------------------------------------------
# 5) Clasificacion orientativa
# ----------------------------------------------------------------------
titulo("5. CLASIFICACION ORIENTATIVA (umbrales de criterio; ver el encabezado)")
for sg in CANDIDATOS:
    e = efe[(efe.segmento == sg) & (efe.carga.isin(["llegadas_6h_previas", "ocup_hosp"]))]
    carga_ok = ((e.pct_por_decil_edad_anio_y_hora >= UMBRAL_CARGA) & (e.razon_decil_alto_vs_bajo >= RAZON_ALTA)).any()
    h = hora_ef[(hora_ef.segmento == sg) & (hora_ef.modelo == "con_control_de_carga")]
    hora_ok = h.pct_vs_madrugada.abs().max() >= UMBRAL_HORA
    if carga_ok:
        veredicto = "SUBE CON LA CARGA (compatible con falta de capacidad)"
    elif hora_ok:
        veredicto = "VARIA POR HORA pero no por carga (compatible con turnos o proceso)"
    else:
        veredicto = "PLANO frente a carga y hora (compatible con tiempo de proceso fijo)"
    print(f"{sg:24s} -> {veredicto}")
    print(e[["carga", "pct_por_decil_edad_anio_y_hora", "t_edad_anio_y_hora", "razon_decil_alto_vs_bajo"]]
          .to_string(index=False))
    print(f"   franja con mayor efecto (con control de carga): {h.loc[h.pct_vs_madrugada.abs().idxmax(), 'franja']} "
          f"({h.pct_vs_madrugada.loc[h.pct_vs_madrugada.abs().idxmax()]:+.1f} % vs madrugada)")

# ----------------------------------------------------------------------
# 6) Grafico
# ----------------------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("\nmatplotlib no esta instalado: se omite el grafico")
else:
    SUPERFICIE, TINTA, TINTA2, REJILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e5e4df"
    AZUL, NARANJA = "#2a78d6", "#eb6834"
    fig, axs = plt.subplots(1, 3, figsize=(14.5, 4.6), facecolor=SUPERFICIE, sharey=True)
    paneles = [("llegadas_6h_previas", "llegadas en las 6 h previas"), ("ocup_hosp", "pacientes en cama (hora anterior)")]
    for ax, (var, etiqueta) in zip(axs[:2], paneles):
        t = dec[(dec.segmento == "espera_cama") & (dec.carga == var)]
        ax.plot(t.carga_media, t.p50, color=AZUL, linewidth=2, marker="o", markersize=6,
                markeredgecolor=SUPERFICIE, markeredgewidth=1.5, label="mediana")
        ax.plot(t.carga_media, t.p90, color=NARANJA, linewidth=2, marker="o", markersize=6,
                markeredgecolor=SUPERFICIE, markeredgewidth=1.5, label="percentil 90")
        ax.set_xlabel(f"{etiqueta} (10 niveles)", color=TINTA2, fontsize=9)
        ax.set_title(f"Espera de cama segun {etiqueta.split(' (')[0]}", loc="left", color=TINTA,
                     fontsize=10.5, fontweight="bold")
    ax = axs[2]
    ax.plot(hl.hora, hl.p50, color=AZUL, linewidth=2, marker="o", markersize=6,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.5, label="mediana")
    ax.plot(hl.hora, hl.p90, color=NARANJA, linewidth=2, marker="o", markersize=6,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.5, label="percentil 90")
    ax.set_xlabel("hora de llegada", color=TINTA2, fontsize=9)
    ax.set_xticks(range(0, 24, 3))
    ax.set_title("Espera de cama segun la hora de llegada", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    axs[0].set_ylabel("horas", color=TINTA2, fontsize=9)
    for ax in axs:
        ax.set_facecolor(SUPERFICIE)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(REJILLA)
        ax.tick_params(colors=TINTA2, labelsize=9)
        ax.grid(axis="y", color=REJILLA, linewidth=.8)
        ax.set_axisbelow(True)
        ax.set_ylim(0, None)
    axs[0].legend(frameon=False, fontsize=8.5, labelcolor=TINTA2, loc="upper left")
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.text(.01, .01, "Cada estancia en cama se cuenta una vez. Son asociaciones, no causas: la carga y la hora "
             "de llegada estan relacionadas entre si.", color=TINTA2, fontsize=8)
    fig.savefig(GRAFICOS / f"dependencia_carga{SUFIJO}.png", dpi=150, facecolor=SUPERFICIE)
    print("\nguardado: resultados/graficos/dependencia_carga.png")
