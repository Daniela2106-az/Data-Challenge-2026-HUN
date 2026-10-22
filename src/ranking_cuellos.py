"""
ranking_cuellos.py  -  version 1 (21-oct-2026)
Fase 3 del plan de cuellos de botella (docs/plan_de_accion.md, seccion 0).

QUE HACE
  1. Calcula la referencia de "cuando funciona bien" de cada segmento candidato, por estrato (nino/adulto).
       a20 = mediana del segmento cuando la carga es baja (llegadas de las 6 h previas en el 20 % mas bajo)
       a10 = lo mismo con el 10 % mas bajo
       b25 = percentil 25 del segmento
       b10 = percentil 10 del segmento
     (la meta del HUN seria la referencia c: se agrega cuando respondan).
  2. Exceso de cada episodio = max(0, horas - referencia). Impacto = suma de excesos (horas-paciente).
  3. Ranking de segmentos con cada referencia, y si el orden entre componentes se mantiene.
  4. Descomposicion de la espera de cama (cuanto es urgencias y cuanto es hueco sin etapa).
  5. Exceso por anio y por franja horaria de llegada (las referencias son fijas para todo el periodo).
  6. Grafico del impacto.

ENTRADA
  datos/procesados/segmentos.csv   (src/construir_segmentos.py)

SALIDAS
  resultados/tablas/referencias_usadas.csv, ranking_cuellos.csv, descomposicion_espera.csv,
  exceso_por_anio.csv, exceso_por_franja.csv
  resultados/graficos/ranking_cuellos.png

OJO AL LEER EL RANKING
  espera_cama = urgencias_antes_cama + hueco_antes_cama. La espera de cama siempre tiene el mayor exceso
  porque es la suma; el orden que informa es el de los DOS COMPONENTES. Los excesos no se suman entre filas.
  Una referencia es una eleccion, no una verdad: por eso se prueban cuatro y se mira si el orden se mantiene.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

SUFIJO = os.environ.get("SUFIJO", "")   # ver construir_segmentos.py
RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
for _d in (TABLAS, GRAFICOS):
    _d.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# Parametros
# ----------------------------------------------------------------------
CANDIDATOS = ["espera_cama", "urgencias_antes_cama", "hueco_antes_cama"]
COMPONENTES = ["urgencias_antes_cama", "hueco_antes_cama"]
REFS = {"a20": ("a", .20), "a10": ("a", .10), "b25": ("b", .25), "b10": ("b", .10)}
MIN_ESTRATO = 30     # un estrato con menos casos usa la referencia de todo el segmento
K = ["visit_occurrence_id", "episodio"]

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


# ----------------------------------------------------------------------
# 1) Carga
# ----------------------------------------------------------------------
titulo("1. CARGA")
seg = pd.read_csv(PROC / f"segmentos{SUFIJO}.csv")
d = seg[seg.segmento.isin(CANDIDATOS) & seg.en_estadisticas].copy()
d["grupo"] = np.where(d.edad.isna(), "sin dato", np.where(d.edad < 15, "nino", "adulto"))
print(d.groupby("segmento").size().rename("filas").to_string())
print(d.drop_duplicates(K).grupo.value_counts().rename("episodios por grupo").to_string())

# umbral de "carga baja": percentil de llegadas_6h_previas sobre los episodios con espera de cama
ep_cama = d[d.segmento == "espera_cama"].drop_duplicates(K)
UMBRALES = {p: ep_cama.llegadas_6h_previas.quantile(p) for _, (t, p) in REFS.items() if t == "a"}
for p, u in UMBRALES.items():
    print(f"carga baja ({int(p * 100)} % mas bajo): llegadas_6h_previas <= {u:.0f}")

# ----------------------------------------------------------------------
# 2) Referencias
# ----------------------------------------------------------------------
titulo("2. REFERENCIAS (horas)")


def valor_ref(g, tipo, p):
    if tipo == "a":
        base = g[g.llegadas_6h_previas <= UMBRALES[p]]
        return (base.horas.median() if len(base) else np.nan), len(base)
    return g.horas.quantile(p), len(g)


filas = []
for nombre, (tipo, p) in REFS.items():
    for sg, g in d.groupby("segmento"):
        glob, n_glob = valor_ref(g, tipo, p)
        filas.append(dict(referencia=nombre, segmento=sg, grupo="todos", n_base=n_glob, ref_h=glob))
        for gr, gg in g.groupby("grupo"):
            v, n = valor_ref(gg, tipo, p)
            usa_global = n < MIN_ESTRATO or np.isnan(v)
            filas.append(dict(referencia=nombre, segmento=sg, grupo=gr, n_base=n,
                              ref_h=glob if usa_global else v))
refs = pd.DataFrame(filas).round(2)
print(refs.pivot_table(index=["segmento", "grupo"], columns="referencia", values="ref_h").round(1).to_string())
refs.to_csv(TABLAS / f"referencias_usadas{SUFIJO}.csv", index=False)

# ----------------------------------------------------------------------
# 3) Exceso, impacto y ranking
# ----------------------------------------------------------------------
titulo("3. EXCESO E IMPACTO (horas-paciente perdidas sobre la referencia)")
res = d.merge(refs[refs.grupo != "todos"][["referencia", "segmento", "grupo", "ref_h"]],
              on=["segmento", "grupo"])
res["exceso"] = (res.horas - res.ref_h).clip(lower=0)

rk = (res.groupby(["referencia", "segmento"])
         .agg(n=("horas", "size"), horas_totales=("horas", "sum"), exceso_total_h=("exceso", "sum"),
              exceso_medio_h=("exceso", "mean"),
              pct_exceso_mas_6h=("exceso", lambda s: 100 * (s > 6).mean()),
              pct_exceso_mas_24h=("exceso", lambda s: 100 * (s > 24).mean()))
         .round(1).reset_index())
rk = rk.merge(refs[refs.grupo == "todos"][["referencia", "segmento", "ref_h"]]
              .rename(columns={"ref_h": "ref_todo_h"}), on=["referencia", "segmento"])
rk["orden_componentes"] = (rk[rk.segmento.isin(COMPONENTES)]
                           .groupby("referencia").exceso_total_h.rank(ascending=False).astype("Int64"))
rk = rk.sort_values(["referencia", "exceso_total_h"], ascending=[True, False])
print(rk.to_string(index=False))
rk.to_csv(TABLAS / f"ranking_cuellos{SUFIJO}.csv", index=False)

print("\nORDEN ENTRE COMPONENTES (1 = el que mas horas pierde) con cada referencia:")
orden = rk[rk.segmento.isin(COMPONENTES)].pivot(index="segmento", columns="referencia", values="orden_componentes")
print(orden.to_string())
lider = rk[rk.segmento.isin(COMPONENTES)].sort_values("exceso_total_h", ascending=False).groupby("referencia").segmento.first()
print("lider por referencia:", lider.to_dict())
print("ORDEN ROBUSTO" if lider.nunique() == 1 else "ORDEN SENSIBLE A LA REFERENCIA: reportarlo asi")

# ----------------------------------------------------------------------
# 4) Descomposicion de la espera de cama
# ----------------------------------------------------------------------
titulo("4. DESCOMPOSICION DE LA ESPERA DE CAMA")
w = d.pivot_table(index=K, columns="segmento", values="horas").dropna()
tot = w.sum()
desc = pd.DataFrame({"horas_totales": tot.round(0), "pct_de_espera_cama": (100 * tot / tot["espera_cama"]).round(1)})
print(f"episodios con los tres segmentos: {len(w)}")
print(desc.to_string())
desc.to_csv(TABLAS / f"descomposicion_espera{SUFIJO}.csv")

# ----------------------------------------------------------------------
# 5) Exceso por anio y por franja de llegada (referencia fija para todo el periodo)
# ----------------------------------------------------------------------
titulo("5. EXCESO POR ANIO Y POR FRANJA DE LLEGADA (referencias a20 y b25)")
sub = res[res.referencia.isin(["a20", "b25"])]


def tabla(por):
    t = (sub.groupby(["referencia", "segmento", por], observed=True)
            .agg(n=("horas", "size"), mediana_h=("horas", "median"), exceso_medio_h=("exceso", "mean"),
                 pct_exceso_mas_24h=("exceso", lambda s: 100 * (s > 24).mean()))
            .round(1).reset_index())
    return t


por_anio = tabla("anio")
por_franja = tabla("franja")
por_anio.to_csv(TABLAS / f"exceso_por_anio{SUFIJO}.csv", index=False)
por_franja.to_csv(TABLAS / f"exceso_por_franja{SUFIJO}.csv", index=False)
print("espera_cama por anio:")
print(por_anio[por_anio.segmento == "espera_cama"].to_string(index=False))
print("\nespera_cama por franja de llegada:")
print(por_franja[por_franja.segmento == "espera_cama"].to_string(index=False))
print("\n(2026 es medio anio. El exceso medio por episodio es comparable entre anios; el total no.)")

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
    AZUL, NARANJA = "#2a78d6", "#eb6834"      # paleta de referencia de la guia de visualizacion
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.8), facecolor=SUPERFICIE,
                                   gridspec_kw={"width_ratios": [1.25, 1]})
    for ax in (ax1, ax2):
        ax.set_facecolor(SUPERFICIE)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(REJILLA)
        ax.tick_params(colors=TINTA2, labelsize=9)
        ax.grid(axis="x" if ax is ax1 else "y", color=REJILLA, linewidth=.8)
        ax.set_axisbelow(True)

    nombres = {"espera_cama": "Espera de cama\n(total)", "urgencias_antes_cama": "Urgencias\nantes de la cama",
               "hueco_antes_cama": "Hueco sin etapa\nantes de la cama"}
    orden_seg = ["hueco_antes_cama", "urgencias_antes_cama", "espera_cama"]
    y = np.arange(len(orden_seg))
    for k, (ref, color, etiqueta) in enumerate([("a20", AZUL, "referencia: carga baja"),
                                                ("b25", NARANJA, "referencia: percentil 25")]):
        v = [rk[(rk.referencia == ref) & (rk.segmento == s)].exceso_total_h.iloc[0] / 1000 for s in orden_seg]
        pos = y + (k - .5) * .34
        ax1.barh(pos, v, height=.3, color=color, label=etiqueta)
        for p_, val in zip(pos, v):
            ax1.text(val + max(v) * .01, p_, f"{val:,.0f} mil h", va="center", fontsize=8.5, color=TINTA)
    ax1.set_yticks(y)
    ax1.set_yticklabels([nombres[s] for s in orden_seg], color=TINTA, fontsize=9.5)
    ax1.set_xlabel("horas-paciente perdidas sobre la referencia (miles)", color=TINTA2, fontsize=9)
    ax1.set_xlim(0, ax1.get_xlim()[1] * 1.18)
    ax1.legend(frameon=False, fontsize=8.5, labelcolor=TINTA2, loc="lower right")
    ax1.set_title("Impacto por segmento", loc="left", color=TINTA, fontsize=11.5, fontweight="bold")

    a = por_anio[(por_anio.segmento == "espera_cama") & (por_anio.referencia == "a20")]
    ax2.plot(a.anio, a.exceso_medio_h, color=AZUL, linewidth=2, marker="o", markersize=7,
             markeredgecolor=SUPERFICIE, markeredgewidth=2)
    for x_, y_ in zip(a.anio, a.exceso_medio_h):
        ax2.text(x_, y_ + .6, f"{y_:.1f} h", ha="center", fontsize=9, color=TINTA)
    ax2.set_xticks(a.anio)
    ax2.set_xticklabels([str(int(x_)) if x_ != 2026 else "2026\n(medio anio)" for x_ in a.anio])
    ax2.set_ylim(0, a.exceso_medio_h.max() * 1.25)
    ax2.set_ylabel("exceso medio por episodio (h)", color=TINTA2, fontsize=9)
    ax2.set_title("Espera de cama: exceso medio por anio", loc="left", color=TINTA, fontsize=11.5,
                  fontweight="bold")
    fig.tight_layout()
    fig.savefig(GRAFICOS / f"ranking_cuellos{SUFIJO}.png", dpi=150, facecolor=SUPERFICIE)
    print("\nguardado: resultados/graficos/ranking_cuellos.png")
