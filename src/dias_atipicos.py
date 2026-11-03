"""
dias_atipicos.py  -  version 1 (22-oct-2026)
Ficha D.2 del plan (lo pide el instructivo: "identificar patrones atipicos en el flujo hospitalario").

QUE HACE
  Marca los dias que se salieron del patron comparando lo observado con lo que esperaba el modelo de demanda
  (pronostico a 1 dia de src/pronostico_demanda.py):
    - LLEGADAS: z = (log(real / esperado) - mediana) / desviacion robusta, con mediana y desviacion (1,4826 x MAD)
      calculadas en 2023-03 a 2025-12.
    - INGRESOS A CAMA: residuo de Pearson (real - esperado) / sqrt(esperado), estandarizado igual.
    - ESPERA DE CAMA: mediana de la espera de los pacientes que llegaron ese dia, frente a la mediana de los 56
      dias anteriores (solo dias con 8 o mas pacientes), estandarizado igual.
  Atipico = |z| > 3. Despues se describe cada dia con una causa de calendario si la tiene (festivo, semana santa,
  fin de anio, vispera o dia despues de un festivo) o "sin causa de calendario aparente".

ENTRADAS  datos/procesados/para_equipo/panel_diario.csv, resultados/tablas/pronostico_diario_completo.csv
SALIDAS   resultados/tablas/dias_atipicos.csv (un dia por fila), dias_atipicos_resumen.csv
          resultados/graficos/dias_atipicos.png

OJO AL LEER
  - Hasta 2025-12 los esperados son "en muestra" (el modelo vio esos dias), asi que los residuos son algo mas chicos que
    en la realidad; desde 2026-01 son fuera de muestra.
  - Desde 2026-05 las llegadas caen de forma sostenida (posible carga incompleta, pregunta 14): esos dias se marcan
    aparte como "periodo de caida de datos" y no se interpretan como dias atipicos individuales.
  - Con |z| > 3 y datos normales se esperarian ~0,3 % de dias (3 de 1.188); las colas son mas pesadas, por eso hay mas.
  - No hay causa probada: la categoria de calendario solo dice que el dia coincide con un festivo u otra fecha especial.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
for _d in (TABLAS, GRAFICOS):
    _d.mkdir(parents=True, exist_ok=True)

ENTRENA_HASTA = "2025-12-31"
CAIDA_DESDE = "2026-04-10"
UMBRAL_Z = 3.0
VENTANA_ESPERA = 56
MIN_PACIENTES_ESPERA = 8

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


def z_robusto(x, base):
    """(x - mediana) / (1,4826 x MAD), con mediana y MAD de la serie base."""
    mediana = base.median()
    escala = 1.4826 * (base - mediana).abs().median()
    return (x - mediana) / escala


# ----------------------------------------------------------------------
# 1) Carga y residuos estandarizados
# ----------------------------------------------------------------------
titulo("1. RESIDUOS ESTANDARIZADOS")
d = pd.read_csv(PROC / "para_equipo" / "panel_diario.csv", parse_dates=["fecha"]).set_index("fecha")
c = pd.read_csv(TABLAS / "pronostico_diario_completo.csv", parse_dates=["fecha"]).set_index("fecha")
d = d.join(c[["llegadas_pronostico_h1", "ingresos_a_cama_pronostico_h1"]], how="inner")
ent = d.index <= ENTRENA_HASTA

r_ll = np.log(d.llegadas / d.llegadas_pronostico_h1)
d["z_llegadas"] = z_robusto(r_ll, r_ll[ent])
p_in = (d.ingresos_a_cama - d.ingresos_a_cama_pronostico_h1) / np.sqrt(d.ingresos_a_cama_pronostico_h1)
d["z_ingresos"] = z_robusto(p_in, p_in[ent])
esp = d.espera_cama_mediana_h.where(d.n_espera >= MIN_PACIENTES_ESPERA)
base_esp = esp.rolling(VENTANA_ESPERA, min_periods=30).median().shift(1)
r_es = np.log(esp / base_esp)
d["z_espera"] = z_robusto(r_es, r_es[ent])
print(d[["z_llegadas", "z_ingresos", "z_espera"]].describe().round(2).T.to_string())

# ----------------------------------------------------------------------
# 2) Calendario especial
# ----------------------------------------------------------------------
d["festivo"] = d.festivo.astype(bool)
d["dow"] = d.index.dayofweek
semana_santa = pd.Series(False, index=d.index)
for a in range(d.index.min().year, d.index.max().year + 1):
    e = pd.Timestamp(easter(a))
    semana_santa[(d.index >= e - pd.Timedelta(days=7)) & (d.index <= e)] = True
fin_anio = pd.Series(((d.index.month == 12) & d.index.day.isin([24, 25, 31])) |
                     ((d.index.month == 1) & (d.index.day == 1)), index=d.index)
vispera_o_despues = d.festivo.shift(-1, fill_value=False) | d.festivo.shift(1, fill_value=False)


def causa(fecha):
    if fecha >= pd.Timestamp(CAIDA_DESDE):
        return "periodo de caida de datos (desde mayo 2026)"
    if d.festivo[fecha]:
        return "festivo"
    if semana_santa[fecha]:
        return "semana santa"
    if fin_anio[fecha]:
        return "fin de anio"
    if vispera_o_despues[fecha]:
        return "vispera o dia despues de un festivo"
    return "sin causa de calendario aparente"


d["causa_calendario"] = [causa(f) for f in d.index]
d["calendario_especial"] = d.causa_calendario.isin(["festivo", "semana santa", "fin de anio", "vispera o dia despues de un festivo"])

# ----------------------------------------------------------------------
# 3) Dias atipicos
# ----------------------------------------------------------------------
titulo(f"2. DIAS ATIPICOS (|z| > {UMBRAL_Z:g})")
filas = []
for var, col, esperado, real in [("llegadas", "z_llegadas", "llegadas_pronostico_h1", "llegadas"),
                                 ("ingresos a cama", "z_ingresos", "ingresos_a_cama_pronostico_h1", "ingresos_a_cama"),
                                 ("espera de cama (mediana del dia)", "z_espera", None, "espera_cama_mediana_h")]:
    z = d[col].dropna()
    marcados = z[z.abs() > UMBRAL_Z].index
    for f in marcados:
        filas.append({"fecha": f.date(), "dia_semana": ["lun", "mar", "mie", "jue", "vie", "sab", "dom"][d.dow[f]],
                      "variable": var, "real": round(float(d[real][f]), 1),
                      "esperado": round(float(d[esperado][f]), 1) if esperado else round(float(base_esp[f]), 1),
                      "z": round(float(z[f]), 1), "sentido": "mas de lo esperado" if z[f] > 0 else "menos de lo esperado",
                      "causa_calendario": d.causa_calendario[f]})
at = pd.DataFrame(filas).sort_values(["variable", "z"], key=lambda s: s.abs() if s.name == "z" else s,
                                     ascending=[True, False])
at.to_csv(TABLAS / "dias_atipicos.csv", index=False)

resumen = []
for var, g in at.groupby("variable"):
    n_dias = int(d[{"llegadas": "z_llegadas", "ingresos a cama": "z_ingresos",
                    "espera de cama (mediana del dia)": "z_espera"}[var]].notna().sum())
    antes = g[g.causa_calendario != "periodo de caida de datos (desde mayo 2026)"]
    resumen.append({"variable": var, "dias_evaluados": n_dias, "dias_atipicos": len(g),
                    "pct_de_los_dias": round(100 * len(g) / n_dias, 1),
                    "mas_de_lo_esperado": int((g.z > 0).sum()), "menos_de_lo_esperado": int((g.z < 0).sum()),
                    "con_causa_de_calendario": int(antes.causa_calendario.isin(
                        ["festivo", "semana santa", "fin de anio", "vispera o dia despues de un festivo"]).sum()),
                    "sin_causa_aparente": int((antes.causa_calendario == "sin causa de calendario aparente").sum()),
                    "en_la_caida_de_datos": int((g.causa_calendario == "periodo de caida de datos (desde mayo 2026)").sum())})
res = pd.DataFrame(resumen)
res.to_csv(TABLAS / "dias_atipicos_resumen.csv", index=False)
print(res.to_string(index=False))
print(f"\nCon datos normales se esperarian ~{0.0027 * d.z_llegadas.notna().sum():.0f} dias con |z| > 3 por variable.")
base_cal = d[~(d.index >= CAIDA_DESDE)].calendario_especial.mean()
ll = at[at.variable == "llegadas"]
ll = ll[ll.causa_calendario != "periodo de caida de datos (desde mayo 2026)"]
print(f"Dias con calendario especial: {100 * base_cal:.1f} % de todos los dias; entre los atipicos de llegadas: "
      f"{100 * ll.causa_calendario.isin(['festivo', 'semana santa', 'fin de anio', 'vispera o dia despues de un festivo']).mean():.1f} %")

print("\nLLEGADAS: los 15 dias mas atipicos (sin contar la caida de datos de mayo 2026)")
print(ll.reindex(ll.z.abs().sort_values(ascending=False).index).head(15).drop(columns="variable").to_string(index=False))

print("\nDias atipicos en MAS DE UNA variable:")
multiples = at.groupby("fecha").variable.agg(list)
multiples = multiples[multiples.map(len) > 1]
print(multiples.to_string() if len(multiples) else "ninguno")
dias_ll_in = at[at.variable.isin(["llegadas", "ingresos a cama"])].groupby("fecha").variable.nunique()
print(f"dias atipicos a la vez en llegadas e ingresos: {int((dias_ll_in == 2).sum())}")

# ----------------------------------------------------------------------
# 4) Grafico
# ----------------------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("\nmatplotlib no esta instalado: se omite el grafico")
else:
    SUPERFICIE, TINTA, TINTA2, REJILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e5e4df"
    AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
    fig, axs = plt.subplots(1, 2, figsize=(14.5, 4.9), facecolor=SUPERFICIE, gridspec_kw={"width_ratios": [1.7, 1]})

    def estilo(ax):
        ax.set_facecolor(SUPERFICIE)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(REJILLA)
        ax.tick_params(colors=TINTA2, labelsize=9)
        ax.grid(axis="y", color=REJILLA, linewidth=.8)
        ax.set_axisbelow(True)

    ax = axs[0]
    z = d.z_llegadas.dropna()
    ax.plot(z.index, z, color=REJILLA, linewidth=1)
    ax.axvspan(pd.Timestamp(CAIDA_DESDE), z.index.max(), color=REJILLA, alpha=.5, linewidth=0)
    ax.axhline(UMBRAL_Z, color=TINTA2, linewidth=1, linestyle=(0, (4, 3)))
    ax.axhline(-UMBRAL_Z, color=TINTA2, linewidth=1, linestyle=(0, (4, 3)))
    grupos = [("calendario especial", d.calendario_especial, AZUL), ("sin causa de calendario aparente",
              d.causa_calendario == "sin causa de calendario aparente", NARANJA)]
    for nombre, m, color in grupos:
        s = z[(z.abs() > UMBRAL_Z) & m.reindex(z.index)]
        ax.scatter(s.index, s, s=34, color=color, edgecolor=SUPERFICIE, linewidth=1.2, zorder=3, label=f"{nombre} ({len(s)})")
    s = z[(z.abs() > UMBRAL_Z) & (z.index >= CAIDA_DESDE)]
    ax.scatter(s.index, s, s=34, color=TINTA2, edgecolor=SUPERFICIE, linewidth=1.2, zorder=3,
               label=f"caida de datos desde mayo 2026 ({len(s)})")
    ax.set_ylabel("z de las llegadas (desviaciones robustas)", color=TINTA2, fontsize=9)
    ax.set_title("Llegadas: dias que se salieron de lo esperado", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, labelcolor=TINTA2, loc="lower left")
    estilo(ax)

    ax = axs[1]
    etiquetas = ["llegadas", "ingresos a cama", "espera de cama (mediana del dia)"]
    cortos = ["llegadas", "ingresos\na cama", "espera de\ncama"]
    r_ = res.set_index("variable").loc[etiquetas]
    x_ = np.arange(len(etiquetas))
    base = np.zeros(len(etiquetas))
    for col, color, et in [("con_causa_de_calendario", AZUL, "calendario especial"),
                           ("sin_causa_aparente", NARANJA, "sin causa de calendario aparente"),
                           ("en_la_caida_de_datos", TINTA2, "caida de datos desde mayo 2026")]:
        ax.bar(x_, r_[col], bottom=base, width=.55, color=color, label=et, edgecolor=SUPERFICIE, linewidth=1.5)
        base += r_[col].values
    for i, t_ in enumerate(base):
        ax.text(i, t_ + .4, f"{int(t_)}", ha="center", fontsize=9, color=TINTA)
    ax.axhline(0.0027 * 1188, color=TINTA2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(-0.45, 0.0027 * 1188 + .3, "esperados con datos normales", ha="left", fontsize=8, color=TINTA2)
    ax.set_xticks(x_)
    ax.set_xticklabels(cortos, fontsize=9)
    ax.set_ylabel("dias atipicos", color=TINTA2, fontsize=9)
    ax.set_title("Cuantos y de que tipo", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, labelcolor=TINTA2, loc="upper right")
    estilo(ax)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.text(.01, .01, "Atipico = mas de 3 desviaciones robustas respecto al pronostico a 1 dia. Hasta 2025-12 el pronostico es en muestra. "
             "Una causa de calendario es una coincidencia, no una causa probada.", color=TINTA2, fontsize=8)
    fig.savefig(GRAFICOS / "dias_atipicos.png", dpi=150, facecolor=SUPERFICIE)
    print("\nguardado: resultados/graficos/dias_atipicos.png")
