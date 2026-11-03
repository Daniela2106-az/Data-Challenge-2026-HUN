"""
altas_y_factores.py  -  version 1 (22-oct-2026)
Fase 5 del plan de cuellos de botella (docs/plan_de_accion.md, seccion 0).

PREGUNTAS
  A. Las altas se dan tarde? (perfil por hora del dia de altas, ingresos a cama y llegadas)
  B. Quien llega despues del mediodia espera hasta el dia siguiente? (hora en que se asigna la cama segun
     la hora de llegada; % que recibe la cama el mismo dia)
  C. Los ingresos a cama siguen a las altas dentro del mismo dia? (correlacion cruzada por hora, sin el
     patron horario)
  D. Puerta 3: se sostiene la hipotesis de las altas tardias? (criterios impresos al final)
  E. Factores de la espera de cama: cuanto explica cada grupo (hora, calendario, anio, edad y sexo, tipo de
     visita, diagnostico, laboratorios de las primeras 6 h, carga) con un modelo sobre log(espera + 1).

ENTRADA  datos/procesados/para_equipo/estancias_hospitalizacion.csv (exportar_para_equipo.py v2: una fila por
         estancia en cama, sin estancias gemelas)
SALIDAS  resultados/tablas/altas_ingresos_llegadas_por_hora.csv, asignacion_cama_por_hora_llegada.csv,
         correlacion_altas_ingresos.csv, coeficientes_espera_cama.csv, importancia_factores.csv
         resultados/graficos/altas_y_factores.png

OJO AL LEER
  - Son asociaciones, no causas. Que las altas se concentren en la tarde y las camas se asignen en la tarde es
    compatible con la hipotesis, pero no prueba que adelantar las altas reduzca la espera: eso se estima con
    la simulacion de camas (Fase 6).
  - Los diagnosticos se registran tarde (88 % despues de las primeras 2 h) y el 62 % de las estancias no tiene
    diagnostico traducido; sirven para explicar, no para predecir al llegar. mapeo_dx.csv esta pendiente: el
    diagnostico se usa como "tiene diagnostico" y los mas frecuentes.
  - La ventana confiable es feb-2023 a may-2026 (las altas posteriores quedan cortadas por la extraccion).
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
for _d in (TABLAS, GRAFICOS):
    _d.mkdir(parents=True, exist_ok=True)

DESDE, HASTA = "2023-02-01", "2026-04-10"
MAX_H = 2160
MIN_DX = 150          # un diagnostico entra al modelo si tiene al menos estos casos; el resto va a "otros"
# criterios de la Puerta 3 (de criterio, se pueden discutir)
MAX_ALTAS_ANTES_MEDIODIA = 25.0     # % de altas antes de las 12 h
MAX_RANGO_HORA_ASIGNACION = 3       # horas de diferencia entre las horas medianas de asignacion de cama
MIN_SALTO_DIA_SIGUIENTE = 20.0      # puntos entre el % que recibe cama el dia siguiente al llegar a las 8 h y a las 16 h
MIN_CORR_CRUZADA = 0.05

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


def ols(y, X):
    X = np.asarray(X, dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    ss_tot = ((y - y.mean()) ** 2).sum()
    return beta, 1 - (res @ res) / ss_tot


# ----------------------------------------------------------------------
# 1) Carga
# ----------------------------------------------------------------------
titulo("1. CARGA")
e = pd.read_csv(PROC / "para_equipo" / "estancias_hospitalizacion.csv",
                parse_dates=["ingreso_cama", "alta", "llegada"])
w = e[(e.ingreso_cama >= DESDE) & (e.ingreso_cama < HASTA)].copy()
c = w[w.alta_completa].copy()
print(f"estancias unicas en la ventana: {len(w)} | con alta completa: {len(c)}")

# ----------------------------------------------------------------------
# 2) A. Perfil por hora del dia
# ----------------------------------------------------------------------
titulo("2. A. PERFIL POR HORA DEL DIA (% del total de cada serie)")
perfil = pd.DataFrame({
    "altas_pct": 100 * c.alta.dt.hour.value_counts(normalize=True),
    "ingresos_cama_pct": 100 * w.ingreso_cama.dt.hour.value_counts(normalize=True),
    "llegadas_pct": 100 * w.llegada.dt.hour.value_counts(normalize=True)}).sort_index().round(1)
perfil.index.name = "hora"
perfil.to_csv(TABLAS / "altas_ingresos_llegadas_por_hora.csv")
print(perfil.T.to_string())
antes_med = 100 * (c.alta.dt.hour < 12).mean()
print(f"\naltas antes del mediodia: {antes_med:.1f} % | de 12 a 17: {100 * c.alta.dt.hour.between(12, 17).mean():.1f} % "
      f"| de 18 en adelante: {100 * (c.alta.dt.hour >= 18).mean():.1f} %")
print(f"altas entre las 14 y las 18:59: {100 * c.alta.dt.hour.between(14, 18).mean():.1f} %")
c["fin_de_semana"] = c.alta.dt.dayofweek >= 5
c["anio"] = c.alta.dt.year
print("altas antes del mediodia (%) por tipo de dia:",
      (100 * c.groupby("fin_de_semana").apply(lambda g: (g.alta.dt.hour < 12).mean(), include_groups=False)).round(1)
      .rename({False: "entre semana", True: "fin de semana"}).to_dict())
print("altas antes del mediodia (%) por anio:",
      (100 * c.groupby("anio").apply(lambda g: (g.alta.dt.hour < 12).mean(), include_groups=False)).round(1).to_dict())

# ----------------------------------------------------------------------
# 3) B. Hora en que se asigna la cama segun la hora de llegada
# ----------------------------------------------------------------------
titulo("3. B. HORA DE ASIGNACION DE CAMA SEGUN LA HORA DE LLEGADA (pacientes que esperaron)")
x = w[w.espera_cama_h > 0].copy()
x["hora_llegada"] = x.llegada.dt.hour
x["dias_hasta_cama"] = (x.ingreso_cama.dt.normalize() - x.llegada.dt.normalize()).dt.days
asig = (x.groupby("hora_llegada")
          .agg(n=("dias_hasta_cama", "size"),
               pct_cama_el_mismo_dia=("dias_hasta_cama", lambda s: 100 * (s == 0).mean()),
               pct_cama_dia_siguiente_o_mas=("dias_hasta_cama", lambda s: 100 * (s >= 1).mean()),
               espera_p50_h=("espera_cama_h", "median"),
               hora_asignacion_mediana=("ingreso_cama", lambda s: s.dt.hour.median()))
          .round(1).reset_index())
asig.to_csv(TABLAS / "asignacion_cama_por_hora_llegada.csv", index=False)
print(asig.to_string(index=False))
asig_dia = asig[asig.hora_llegada.between(7, 21)]
rango_asig = asig_dia.hora_asignacion_mediana.max() - asig_dia.hora_asignacion_mediana.min()
print(f"\nllegadas de 7 a 21 h: hora mediana de asignacion entre {asig_dia.hora_asignacion_mediana.min():.0f} y "
      f"{asig_dia.hora_asignacion_mediana.max():.0f} h (rango {rango_asig:.0f} h)")
print(f"ingresos a cama entre las 15 y las 18:59: {100 * w.ingreso_cama.dt.hour.between(15, 18).mean():.1f} % | "
      f"entre las 20 y las 23:59: {100 * w.ingreso_cama.dt.hour.between(20, 23).mean():.1f} %")

# ----------------------------------------------------------------------
# 4) C. Correlacion cruzada por hora entre altas e ingresos a cama
# ----------------------------------------------------------------------
titulo("4. C. LOS INGRESOS A CAMA SIGUEN A LAS ALTAS? (correlacion cruzada por hora)")
grilla = pd.date_range(DESDE, HASTA, freq="h", inclusive="left")
alt_h = c.alta.dt.floor("h").value_counts().reindex(grilla, fill_value=0).astype(float)
ing_h = w.ingreso_cama.dt.floor("h").value_counts().reindex(grilla, fill_value=0).astype(float)
# se quita el patron de cada hora del dia y dia de la semana para no medir solo "ambos pasan en la tarde"
llave = [grilla.dayofweek, grilla.hour]
alt_r = alt_h - alt_h.groupby(llave).transform("mean")
ing_r = ing_h - ing_h.groupby(llave).transform("mean")
filas = []
for lag in range(-3, 7):
    filas.append({"retraso_h": lag, "correlacion": round(alt_r.corr(ing_r.shift(-lag)), 3)})
cc = pd.DataFrame(filas)
cc.to_csv(TABLAS / "correlacion_altas_ingresos.csv", index=False)
print("correlacion entre las altas de una hora y los ingresos a cama `retraso` horas despues")
print("(sin el patron de hora y dia de la semana; retraso 0 = la misma hora):")
print(cc.to_string(index=False))
max_corr = cc[cc.retraso_h.between(0, 3)].correlacion.max()

# ----------------------------------------------------------------------
# 5) D. Puerta 3
# ----------------------------------------------------------------------
titulo("5. D. PUERTA 3: SE SOSTIENE LA HIPOTESIS DE LAS ALTAS TARDIAS?")
p8 = asig.loc[asig.hora_llegada == 8, "pct_cama_dia_siguiente_o_mas"].iloc[0]
p16 = asig.loc[asig.hora_llegada == 16, "pct_cama_dia_siguiente_o_mas"].iloc[0]
criterios = [
    (f"altas antes del mediodia {antes_med:.1f} % (< {MAX_ALTAS_ANTES_MEDIODIA:.0f} %)", antes_med < MAX_ALTAS_ANTES_MEDIODIA),
    (f"hora de asignacion de cama casi igual para quien llega de 7 a 21 h (rango {rango_asig:.0f} h <= {MAX_RANGO_HORA_ASIGNACION} h)",
     rango_asig <= MAX_RANGO_HORA_ASIGNACION),
    (f"% con cama el dia siguiente sube de {p8:.0f} % (llega a las 8 h) a {p16:.0f} % (llega a las 16 h): "
     f"+{p16 - p8:.0f} puntos (>= {MIN_SALTO_DIA_SIGUIENTE:.0f})", p16 - p8 >= MIN_SALTO_DIA_SIGUIENTE),
    (f"los ingresos a cama siguen a las altas en las 0-3 h siguientes (correlacion maxima {max_corr:.3f} >= {MIN_CORR_CRUZADA})",
     max_corr >= MIN_CORR_CRUZADA)]
for texto, ok in criterios:
    print(("  [cumple]    " if ok else "  [NO cumple] ") + texto)
n_ok = sum(ok for _, ok in criterios)
print(f"\ncriterios que se cumplen: {n_ok} de {len(criterios)} -> " +
      ("HIPOTESIS SOSTENIDA (descriptivamente)" if n_ok >= 3 else "HIPOTESIS NO SOSTENIDA con estos datos"))

# ----------------------------------------------------------------------
# 6) E. Factores de la espera de cama
# ----------------------------------------------------------------------
titulo("6. E. FACTORES DE LA ESPERA DE CAMA (modelo sobre log(espera + 1); explicar, no predecir)")
m = w[(w.espera_cama_h > 0) & (w.espera_cama_h <= MAX_H)].copy()
m["anio"] = m.llegada.dt.year.astype(str)
m["franja"] = pd.cut(m.hora_llegada, [-1, 5, 11, 17, 23],
                     labels=["madrugada 0-5", "manana 6-11", "tarde 12-17", "noche 18-23"]).astype(str)
m["dia_semana"] = m.dia_semana_num.astype(int).astype(str)
m["festivo"] = m.festivo.astype(str)
m["grupo_edad"] = m.grupo_edad.astype(str)
m["sexo"] = m.sexo.fillna("sin dato").astype(str)
m["tipo_visita"] = m.tipo_visita.astype(str)
frec = m.categoria_dx.value_counts()
top = [d for d in frec[frec >= MIN_DX].index if d not in ("Sin diagnostico", "Otros")]
m["dx"] = np.where(m.categoria_dx.isin(top), m.categoria_dx, np.where(m.categoria_dx == "Sin diagnostico",
                                                                       "sin diagnostico", "otros"))
m["lab6"] = np.log1p(m.n_lab_6h.fillna(0))
m["carga"] = m.llegadas_6h_previas.fillna(m.llegadas_6h_previas.median()) / 10
y = np.log1p(m.espera_cama_h.values)

GRUPOS = {"hora de llegada": ["franja"], "calendario (dia, festivo)": ["dia_semana", "festivo"],
          "anio": ["anio"], "edad y sexo": ["grupo_edad", "sexo"], "tipo de visita": ["tipo_visita"],
          "diagnostico": ["dx"], "laboratorios (6 h)": ["lab6"], "carga (llegadas 6 h)": ["carga"]}
NUMERICAS = {"lab6", "carga"}
# categoria de referencia de cada factor: la mas frecuente, salvo estas (asi los % se leen contra algo claro)
REFERENCIA_FIJA = {"franja": "madrugada 0-5", "anio": "2023", "dia_semana": "0", "festivo": "False",
                   "sexo": "Hombre", "dx": "sin diagnostico"}
REFS_USADAS = {}


def diseno(cols):
    partes = [pd.Series(1.0, index=m.index, name="const")]
    for col in cols:
        if col in NUMERICAS:
            partes.append(m[[col]].astype(float))
            continue
        ref = REFERENCIA_FIJA.get(col, m[col].value_counts().index[0])
        REFS_USADAS[col] = ref
        d_ = pd.get_dummies(m[col], prefix=col, dtype=float)
        partes.append(d_.drop(columns=f"{col}_{ref}"))
    return pd.concat(partes, axis=1)


todas = [c_ for g in GRUPOS.values() for c_ in g]
Xf = diseno(todas)
beta_f, r2_full = ols(y, Xf.values)
print(f"estancias en el modelo: {len(m)} | R2 con todos los factores: {r2_full:.3f}")
filas = []
for nombre, cols in GRUPOS.items():
    _, r2_solo = ols(y, diseno(cols).values)
    _, r2_sin = ols(y, diseno([c_ for c_ in todas if c_ not in cols]).values)
    filas.append({"factor": nombre, "r2_solo": round(r2_solo, 4), "perdida_r2_si_se_quita": round(r2_full - r2_sin, 4)})
imp = pd.DataFrame(filas).sort_values("perdida_r2_si_se_quita", ascending=False)
imp.to_csv(TABLAS / "importancia_factores.csv", index=False)
print("\nque tanto explica cada grupo de factores (R2 = proporcion de la variacion de log(espera) que explica):")
print(imp.to_string(index=False))

coef = pd.DataFrame({"variable": Xf.columns, "pct_cambio": (100 * (np.exp(beta_f) - 1)).round(1)})
coef = coef[coef.variable != "const"].copy()
coef["referencia"] = [REFS_USADAS.get(next((c_ for c_ in todas if v == c_ or v.startswith(c_ + "_")), ""), "") for v in coef.variable]
coef.to_csv(TABLAS / "coeficientes_espera_cama.csv", index=False)   # no se llama factores_espera_cama.csv: ese nombre es de preparar_variables.py
print("\nefecto de cada nivel (% de cambio de la espera frente a la categoria de referencia de su factor; "
      "lab6 y carga: por cada unidad, es decir por cada x2,7 en laboratorios o cada 10 llegadas):")
print(coef.to_string(index=False))
print("\nOJO: el diagnostico se registra despues de la llegada; quien espera mas tiene mas tiempo para que se le "
      "registre uno. Esa relacion puede ser en parte inversa (la espera causa el diagnostico, no al reves).")

# ----------------------------------------------------------------------
# 7) Grafico
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
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8), facecolor=SUPERFICIE, gridspec_kw={"width_ratios": [1.2, 1, 1]})
    ax = axs[0]
    for col, color, et in [("llegadas_pct", AQUA, "llegadas"), ("altas_pct", NARANJA, "altas"),
                           ("ingresos_cama_pct", AZUL, "ingresos a cama")]:
        ax.plot(perfil.index, perfil[col], color=color, linewidth=2, marker="o", markersize=5,
                markeredgecolor=SUPERFICIE, markeredgewidth=1.2, label=et)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("hora del dia", color=TINTA2, fontsize=9)
    ax.set_ylabel("% del total de cada serie", color=TINTA2, fontsize=9)
    ax.set_title("Altas, ingresos a cama y llegadas por hora", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=TINTA2, loc="upper left")
    ax = axs[1]
    ax.plot(asig.hora_llegada, asig.pct_cama_dia_siguiente_o_mas, color=AZUL, linewidth=2, marker="o", markersize=5,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.2)
    ax.set_xticks(range(0, 24, 3))
    ax.set_ylim(0, 100)
    ax.set_xlabel("hora de llegada", color=TINTA2, fontsize=9)
    ax.set_ylabel("% que recibe cama al dia siguiente o despues", color=TINTA2, fontsize=9)
    ax.set_title("Quien llega tarde espera hasta manana", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    ax = axs[2]
    t = imp.sort_values("perdida_r2_si_se_quita")
    ax.barh(t.factor, 100 * t.perdida_r2_si_se_quita, height=.5, color=AZUL)
    for i, v in enumerate(100 * t.perdida_r2_si_se_quita):
        ax.text(v + .1, i, f"{v:.1f} %", va="center", fontsize=8.5, color=TINTA)
    ax.set_xlabel("% de la variacion que se pierde si se quita el factor", color=TINTA2, fontsize=9)
    ax.set_title(f"Que explica la espera (R2 total {100 * r2_full:.0f} %)", loc="left", color=TINTA, fontsize=10.5,
                 fontweight="bold")
    ax.set_xlim(0, max(100 * t.perdida_r2_si_se_quita) * 1.25)
    for ax in axs:
        ax.set_facecolor(SUPERFICIE)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(REJILLA)
        ax.tick_params(colors=TINTA2, labelsize=9)
        ax.grid(axis="x" if ax is axs[2] else "y", color=REJILLA, linewidth=.8)
        ax.set_axisbelow(True)
    axs[2].tick_params(axis="y", colors=TINTA)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.text(.01, .01, "Cada estancia en cama se cuenta una vez. Son asociaciones, no causas. Ventana feb-2023 a may-2026.",
             color=TINTA2, fontsize=8)
    fig.savefig(GRAFICOS / "altas_y_factores.png", dpi=150, facecolor=SUPERFICIE)
    print("\nguardado: resultados/graficos/altas_y_factores.png")
