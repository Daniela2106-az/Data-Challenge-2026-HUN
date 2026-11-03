"""
simulacion_altas.py  -  version 1 (22-oct-2026)
Fase 6 del plan de cuellos de botella (docs/plan_de_accion.md, seccion 0): ocupacion de camas y el escenario
"mas altas antes del mediodia", con cotas honestas en vez de una promesa.

POR QUE NO UNA FILA ("primero en llegar, primero en cama")
  Solo ~53 % de los pares de llegadas consecutivas conserva el mismo orden al recibir cama (azar = 50 %): el orden
  de llegada casi no predice el orden de cama. Un modelo de fila FIFO no esta respaldado por los datos. Se usa un
  argumento de CONSERVACION que no depende de como se asignan las camas:
    - una cama liberada X horas antes puede acortar la espera de un paciente, como maximo, X horas;
    - si la cama no era la limitante (habia camas libres), no cambia nada.
  Por eso el efecto sobre la espera esta entre 0 y las "horas-cama liberadas antes". Entre medias se da una
  estimacion con el acople observado entre altas e ingresos a cama (cuantos ingresos siguen a una alta extra).

QUE HACE
  1. Ocupacion (estancias unicas): perfil por hora del dia, por anio, y descomposicion en ingresos x estancia.
  2. Acople altas -> ingresos a cama (pendiente de la relacion por hora, sin el patron horario).
  3. Escenario A: una proporcion de las altas de la tarde pasa a las 9-12 h del mismo dia. Se reportan las
     camas libres adicionales por hora del dia, las horas-cama liberadas por dia y la cota superior y la
     estimacion de horas-paciente de espera que se evitarian (frente al exceso de espera de la Fase 3).
  4. Grafico.

ENTRADA  datos/procesados/para_equipo/estancias_hospitalizacion.csv (una fila por estancia unica)
         resultados/tablas/ranking_cuellos.csv (para comparar con el exceso de espera, referencia a20)
SALIDAS  resultados/tablas/ocupacion_por_anio.csv, acople_altas_ingresos.csv, escenario_altas_antes.csv,
         escenario_camas_por_hora.csv ; resultados/graficos/simulacion_altas.png

SUPUESTOS DEL ESCENARIO A (escribirlos siempre junto al resultado)
  - Se mueve una proporcion de las altas posteriores a las 12 h a una hora al azar entre las 9 y las 12 h del
    mismo dia. No se mueve un alta si el paciente aun no estaba en cama a esa hora.
  - La hora de ingreso a cama de los demas pacientes se mantiene: es una cota, no una prediccion.
  - La "cota superior" vale si el momento del alta de los demas pacientes NO cambia (el alta depende del curso
    clinico desde la llegada, no de cuando se asigna la cama). Si una cama mas temprana adelantara tambien el
    alta de quien la ocupa, habria un efecto en cadena y el efecto real podria superar la cota.
  - La capacidad total de camas se desconoce (pregunta 9 al HUN): no se calculan "dias saturados".
  - Lo operativo (que el hospital logre adelantar altas) no esta en los datos.
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

DESDE, HASTA = pd.Timestamp("2023-03-01"), pd.Timestamp("2026-04-10")   # ventana estable de ocupacion (periodo confiable hasta el 9-abr-2026)
HORA_TOPE_MANANA, HORA_MIN_MANANA = 12, 9
PROPORCIONES = [0.10, 0.20, 0.30, 0.50, 1.00]
REPETICIONES = 200
SEMILLA = 42
REF_EXCESO = "a20"       # referencia de la Fase 3 con la que se compara el exceso de espera

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)
rng = np.random.default_rng(SEMILLA)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


# ----------------------------------------------------------------------
# 1) Carga y ocupacion
# ----------------------------------------------------------------------
titulo("1. OCUPACION (estancias unicas)")
e = pd.read_csv(PROC / "para_equipo" / "estancias_hospitalizacion.csv",
                parse_dates=["ingreso_cama", "alta", "llegada"])
horas = pd.date_range(e.ingreso_cama.min().floor("h"), e.alta.max().floor("h"), freq="h")
delta = (e.ingreso_cama.dt.floor("h").value_counts().sub(e.alta.dt.floor("h").value_counts(), fill_value=0)
         .reindex(horas, fill_value=0))
ocup = delta.cumsum()[DESDE:HASTA - pd.Timedelta(hours=1)]
print(f"ocupacion horaria: media {ocup.mean():.1f} | p5 {ocup.quantile(.05):.0f} | mediana {ocup.median():.0f} | "
      f"p95 {ocup.quantile(.95):.0f} | maximo {ocup.max():.0f}")
perfil_h = ocup.groupby(ocup.index.hour).mean()
print("ocupacion media por hora del dia (la caida de la tarde son las altas):")
print(perfil_h.round(0).astype(int).to_dict())

# por anio: ocupacion = ingresos por dia x estancia media (ley de Little)
v = e[(e.ingreso_cama >= DESDE) & (e.ingreso_cama < HASTA)].copy()
v["anio"] = v.ingreso_cama.dt.year
dias_anio = {a: ((min(pd.Timestamp(f"{a + 1}-01-01"), HASTA) - max(pd.Timestamp(f"{a}-01-01"), DESDE)).days)
             for a in sorted(v.anio.unique())}
v["estancia_h"] = (v.alta - v.ingreso_cama).dt.total_seconds() / 3600
filas = []
for a, g in v.groupby("anio"):
    o = ocup[ocup.index.year == a]
    completas = g[g.alta_completa]
    filas.append({"anio": a, "dias": dias_anio[a], "ingresos_por_dia": round(len(g) / dias_anio[a], 1),
                  "estancia_media_dias": round(completas.estancia_h.mean() / 24, 2) if a < 2026 else np.nan,
                  "ocupacion_media": round(o.mean(), 1)})
anio = pd.DataFrame(filas)
base = anio.iloc[0]
anio["indice_ingresos"] = (100 * anio.ingresos_por_dia / base.ingresos_por_dia).round(0)
anio["indice_estancia"] = (100 * anio.estancia_media_dias / base.estancia_media_dias).round(0)
anio["indice_ocupacion"] = (100 * anio.ocupacion_media / base.ocupacion_media).round(0)
print("\nocupacion por anio (2023 = marzo a diciembre; 2026 = enero a abril; la estancia de 2026 queda fuera: "
      "las altas posteriores estan cortadas por la extraccion):")
print(anio.to_string(index=False))
anio.to_csv(TABLAS / "ocupacion_por_anio.csv", index=False)

# ----------------------------------------------------------------------
# 2) Acople altas -> ingresos a cama
# ----------------------------------------------------------------------
titulo("2. ACOPLE ALTAS -> INGRESOS A CAMA (por hora, sin el patron de hora y dia de la semana)")
grilla = pd.date_range(DESDE, HASTA, freq="h", inclusive="left")
c = e[e.alta_completa]
alt_h = c.alta.dt.floor("h").value_counts().reindex(grilla, fill_value=0).astype(float)
ing_h = e.ingreso_cama.dt.floor("h").value_counts().reindex(grilla, fill_value=0).astype(float)
llave = [grilla.dayofweek, grilla.hour]
alt_r = alt_h - alt_h.groupby(llave).transform("mean")
ing_r = ing_h - ing_h.groupby(llave).transform("mean")
filas = []
for lag in range(0, 7):
    pend = np.cov(alt_r.values[:len(alt_r) - lag], ing_r.values[lag:])[0, 1] / alt_r.var()
    filas.append({"retraso_h": lag, "ingresos_extra_por_alta_extra": round(pend, 3)})
ac = pd.DataFrame(filas)
ac["acumulado"] = ac.ingresos_extra_por_alta_extra.cumsum().round(3)
ac.to_csv(TABLAS / "acople_altas_ingresos.csv", index=False)
print(ac.to_string(index=False))
PHI = float(np.clip(ac.acumulado.iloc[-1], 0, 1))
print(f"\nacople acumulado en 6 h: {ac.acumulado.iloc[-1]:.2f} ingresos extra por cada alta extra -> se usa phi = {PHI:.2f}")
print("(lectura: de cada cama liberada de mas, ~phi se vuelve a ocupar en las 6 h siguientes. Es una estimacion "
      "gruesa: la relacion tambien recoge dias ocupados en general.)")

# ----------------------------------------------------------------------
# 3) Escenario A: altas de la tarde pasan a las 9-12 h
# ----------------------------------------------------------------------
titulo("3. ESCENARIO A: UNA PROPORCION DE LAS ALTAS DE LA TARDE PASA A LAS 9-12 H DEL MISMO DIA")
a = c[(c.alta >= DESDE) & (c.alta < HASTA)].reset_index(drop=True)
tarde = (a.alta.dt.hour >= HORA_TOPE_MANANA).values
dia = a.alta.dt.normalize().values
alta_h = (a.alta - a.alta.dt.normalize()).dt.total_seconds().values / 3600       # hora decimal de la alta
ing_h_dec = np.where(a.ingreso_cama.dt.normalize().values == dia,
                     (a.ingreso_cama - a.ingreso_cama.dt.normalize()).dt.total_seconds().values / 3600, -1.0)
n_dias = (HASTA - DESDE).days
print(f"altas completas en la ventana: {len(a)} | despues del mediodia: {tarde.sum()} ({100 * tarde.mean():.1f} %)")

# lo que se compara: horas-paciente de espera y su exceso (Fase 3)
rk = pd.read_csv(TABLAS / "ranking_cuellos.csv")
esp = rk[(rk.referencia == REF_EXCESO) & (rk.segmento == "espera_cama")].iloc[0]
espera_dia = esp.horas_totales / n_dias
exceso_dia = esp.exceso_total_h / n_dias
print(f"espera de cama: {espera_dia:.0f} horas-paciente por dia, de las cuales {exceso_dia:.0f} son exceso (referencia {REF_EXCESO})")


def mover(prop):
    """Una repeticion: devuelve (movidas, nueva hora decimal de cada alta movida)."""
    elegida = tarde & (rng.random(len(a)) < prop)
    nueva = rng.uniform(HORA_MIN_MANANA, HORA_TOPE_MANANA, len(a))
    # no se mueve si el paciente aun no estaba en cama a esa hora del mismo dia
    elegida &= ~(ing_h_dec >= nueva)
    return elegida, nueva


filas = []
for prop in PROPORCIONES:
    libres = []
    for _ in range(REPETICIONES if prop < 1 else 20):
        mov, nueva = mover(prop)
        libres.append((alta_h[mov] - nueva[mov]).sum() / n_dias)         # horas-cama liberadas por dia
    h = float(np.mean(libres))
    filas.append({"proporcion_movida": prop, "altas_movidas_por_dia": round(prop * tarde.sum() / n_dias, 1),
                  "horas_cama_liberadas_por_dia": round(h, 1),
                  "cota_superior_h_paciente_por_dia": round(h, 1),
                  "estimacion_h_paciente_por_dia": round(PHI * h, 1),
                  "cota_superior_pct_del_exceso": round(100 * h / exceso_dia, 1),
                  "estimacion_pct_del_exceso": round(100 * PHI * h / exceso_dia, 1),
                  "estimacion_pct_de_la_espera": round(100 * PHI * h / espera_dia, 1)})
esc = pd.DataFrame(filas)
esc.to_csv(TABLAS / "escenario_altas_antes.csv", index=False)
print("\nHoras-cama liberadas y efecto sobre la espera, por proporcion de altas de la tarde que se adelanta:")
print(esc.to_string(index=False))

# camas libres adicionales por hora del dia (escenario del 30 %)
P30 = 0.30
acum = np.zeros(24)
for _ in range(REPETICIONES):
    mov, nueva = mover(P30)
    for hh in range(24):
        solapa = np.clip(np.minimum(alta_h[mov], hh + 1) - np.maximum(nueva[mov], hh), 0, 1)
        acum[hh] += solapa.sum() / n_dias
camas_h = pd.DataFrame({"hora": range(24), "ocupacion_base": perfil_h.round(1).values,
                        "camas_libres_adicionales": (acum / REPETICIONES).round(2)})
camas_h["ocupacion_escenario"] = (camas_h.ocupacion_base - camas_h.camas_libres_adicionales).round(1)
camas_h.to_csv(TABLAS / "escenario_camas_por_hora.csv", index=False)
print("\ncamas libres adicionales por hora del dia con el 30 % de las altas de la tarde adelantadas:")
print(camas_h.set_index("hora").T.to_string())
pico = camas_h.loc[camas_h.camas_libres_adicionales.idxmax()]
print(f"\nmaximo: {pico.camas_libres_adicionales:.1f} camas libres adicionales a las {int(pico.hora)} h "
      f"(de ~{pico.ocupacion_base:.0f} ocupadas)")

# ----------------------------------------------------------------------
# 3b) Comparacion sencilla con la ley de Little (camas = ingresos por dia x estancia media), base 2025
# ----------------------------------------------------------------------
titulo("3b. COMPARACION CON LA LEY DE LITTLE (base: 2025, ultimo anio completo)")
b25 = anio[anio.anio == 2025].iloc[0]
b23 = anio[anio.anio == 2023].iloc[0]
casos = [("hoy (2025)", 1.0, 1.0),
         ("ingresos +10 %", 1.10, 1.0),
         ("estancia -5 %", 1.0, 0.95),
         ("estancia como en 2023", 1.0, b23.estancia_media_dias / b25.estancia_media_dias),
         ("ingresos como en 2023", b23.ingresos_por_dia / b25.ingresos_por_dia, 1.0)]
fl = [{"caso": n, "ingresos_por_dia": round(b25.ingresos_por_dia * i, 1),
       "estancia_media_dias": round(b25.estancia_media_dias * s, 2),
       "camas_ocupadas": round(b25.ocupacion_media * i * s, 1),
       "diferencia_camas": round(b25.ocupacion_media * (i * s - 1), 1)} for n, i, s in casos]
lit = pd.DataFrame(fl)
lit.to_csv(TABLAS / "escenarios_little.csv", index=False)
print(lit.to_string(index=False))
print("Lectura: la ocupacion de 2025 es mas alta que la de 2023 por la ESTANCIA, no por mas ingresos. Comparar con el "
      f"maximo de {pico.camas_libres_adicionales:.1f} camas libres de adelantar el 30 % de las altas.")

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
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8), facecolor=SUPERFICIE)

    def estilo(ax, ygrid=True):
        ax.set_facecolor(SUPERFICIE)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(REJILLA)
        ax.tick_params(colors=TINTA2, labelsize=9)
        ax.grid(axis="y", color=REJILLA, linewidth=.8)
        ax.set_axisbelow(True)

    ax = axs[0]
    ax.plot(camas_h.hora, camas_h.ocupacion_base, color=AZUL, linewidth=2, marker="o", markersize=5,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.2, label="hoy")
    ax.plot(camas_h.hora, camas_h.ocupacion_escenario, color=NARANJA, linewidth=2, marker="o", markersize=5,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.2, label="30 % de las altas de la tarde antes del mediodia")
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("hora del dia", color=TINTA2, fontsize=9)
    ax.set_ylabel("camas ocupadas, promedio (el eje no empieza en 0)", color=TINTA2, fontsize=9)
    ax.set_title("Camas ocupadas segun la hora", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, labelcolor=TINTA2, loc="lower left")
    estilo(ax)

    ax = axs[1]
    x_ = 100 * esc.proporcion_movida
    ax.plot(x_, esc.cota_superior_h_paciente_por_dia, color=NARANJA, linewidth=2, marker="o", markersize=6,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.2, label="cota superior")
    ax.plot(x_, esc.estimacion_h_paciente_por_dia, color=AZUL, linewidth=2, marker="o", markersize=6,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.2, label=f"estimacion (phi = {PHI:.2f})")
    ax.axhline(exceso_dia, color=TINTA2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(x_.iloc[0], exceso_dia * 0.94, f"exceso de espera hoy: {exceso_dia:.0f} h-paciente por dia",
            fontsize=8.5, color=TINTA2, va="top")
    ax.set_xlabel("% de las altas de la tarde que pasan a la manana", color=TINTA2, fontsize=9)
    ax.set_ylabel("horas-paciente de espera evitadas por dia", color=TINTA2, fontsize=9)
    ax.set_ylim(0, exceso_dia * 1.05)
    ax.set_title("Cuanta espera se evitaria como maximo", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=TINTA2, loc="center right")
    estilo(ax)

    ax = axs[2]
    for col, color, et in [("indice_ingresos", AQUA, "ingresos por dia"), ("indice_ocupacion", AZUL, "camas ocupadas")]:
        ax.plot(anio.anio, anio[col], color=color, linewidth=2, marker="o", markersize=6,
                markeredgecolor=SUPERFICIE, markeredgewidth=1.2, label=et)
    ax.plot(anio.anio[anio.indice_estancia.notna()], anio.indice_estancia.dropna(), color=NARANJA, linewidth=2,
            marker="o", markersize=6, markeredgecolor=SUPERFICIE, markeredgewidth=1.2, label="estancia media")
    ax.axhline(100, color=TINTA2, linewidth=1, linestyle=(0, (4, 3)))
    ax.set_xticks(anio.anio)
    ax.set_ylabel("indice (2023 = 100)", color=TINTA2, fontsize=9)
    ax.set_title("Camas ocupadas = ingresos x estancia", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=TINTA2, loc="upper left")
    estilo(ax)

    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.text(.01, .01, "Cada estancia en cama se cuenta una vez. Cota y estimacion con supuestos escritos en el script: "
             "es un escenario, no una prediccion. 2026 = enero a abril.", color=TINTA2, fontsize=8)
    fig.savefig(GRAFICOS / "simulacion_altas.png", dpi=150, facecolor=SUPERFICIE)
    print("\nguardado: resultados/graficos/simulacion_altas.png")
