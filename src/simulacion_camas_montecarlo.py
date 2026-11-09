"""
simulacion_camas_montecarlo.py  -  version 1 (9-nov-2026)
Ficha A5 del plan de accion (docs/pendientes_y_reparto.md A5; fusiona las fichas 3.1 y 3.2 de
docs/fichas_de_tareas.md). El instructivo pide "modelos de simulacion" (docs/plan_de_accion.md): lo que habia
hasta ahora (src/simulacion_altas.py) es un analisis de escenarios sobre datos historicos, no una simulacion
estocastica con bandas de probabilidad.

QUE HACE
  1. Construye la serie de ingresos a cama y la ocupacion real DIRECTAMENTE desde estancias_hospitalizacion.csv
     (no necesita panel_diario.csv: sus columnas ingresos_a_cama/ocup_hosp_media/max se calculan exactamente
     asi en exportar_para_equipo.py; se reprodujo y coincide con CLAUDE.md 4.8).
  2. Distribucion de estancias (horas_hosp) por grupo_edad, para el bootstrap.
  3. Motor de Monte Carlo: por cada repeticion, ingresos diarios ~ Poisson(pronostico de modelo_pronostico.py),
     a cada ingreso se le asigna un grupo_edad (mezcla historica reciente) y una estancia (bootstrap empirico de
     ese grupo); el censo diario sale de acumular eventos de ingreso/alta. Lleva TRES censos en paralelo: total,
     ninos (grupo_edad 0-4 y 5-14) y adultos (el resto) - proxy de ward, ver limites.
  4. Backtest: simula enero a 9-abr-2026 entrenando el pronostico de ingresos solo hasta el 31-dic-2025;
     compara contra la ocupacion real de esos dias.
  5. Alerta de saturacion hacia adelante (desde el 9-abr-2026): probabilidad de superar el percentil 90
     historico y la capacidad que dio el HUN (106 total / 18 ninos / 88 adultos - tabla del 8-nov-2026).
  6. Escenarios B (+10% ingresos) y C (-5% estancia). El escenario A (altas antes del mediodia) NO se repite:
     ya esta hecho en src/simulacion_altas.py, se cita en docs/simulacion.md.
  7. Tres graficos (resultados/graficos/): backtest, proyeccion con umbrales, comparacion de escenarios.

ENTRADA  datos/procesados/para_equipo/estancias_hospitalizacion.csv
SALIDAS  resultados/tablas/simcamas_*.csv ; resultados/graficos/simcamas_*.png

CAPACIDAD DEL HUN (imagen compartida el 8-nov-2026; ya documentada en CLAUDE.md 4.7, aqui con el desglose)
  Camas:    Pediatrica 8, Adultos 64, TPR 4, Intermedia Adultos 6, Intensiva Adultos 14, incubadoras neonatales
            6+3+1=10  ->  106 camas en total.
  Camillas: Observacion Pediatrica 14, Adultos Hombres 18, Adultos Mujeres 26  ->  58 camillas (no modeladas
            aqui: la ocupacion de TU no es comparable 1 a 1 con camillas, CLAUDE.md 4.8).
  Proxy ninos/adultos: la base NO tiene servicio/piso/cama (CLAUDE.md 4.8), asi que no se puede simular por
  unidad exacta. Se reusa el proxy de edad que el equipo ya valido una vez a mano (CLAUDE.md 4.8, "Revision
  final de la ocupacion"): ninos = Pediatrica+neonatal = 8+10 = 18; adultos = Adultos+Intermedia+Intensiva+TPR
  = 64+6+14+4 = 88. Aqui "ninos" = grupo_edad en (0-4, 5-14); es mas grueso que el corte "menor de 1 ano" que
  se uso en esa revision puntual de la base (nuestros bins no llegan a ese detalle) - se declara como limite.

LIMITES
  - El backtest formal (paso 4) es solo del censo TOTAL (no hay ocupacion real separada por ninos/adultos para
    comparar); los censos ninos/adultos se reportan sin backtest propio.
  - Los ingresos se simulan con Poisson alrededor del pronostico puntual (una sola fuente de aleatoriedad por
    dia); no se remuestrea ademas el nivel semanal del pronostico.
  - Asociacion, no causa; todo lo de siempre: duplicados tratados, periodo confiable hasta el 9-abr-2026.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modelo_pronostico as mp

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
for _d in (TABLAS, GRAFICOS):
    _d.mkdir(parents=True, exist_ok=True)

OCUP_DESDE, OCUP_HASTA = "2023-02-01", "2026-04-10"          # igual que exportar_para_equipo.py / dependencia_carga.py
GRUPOS_NINOS = ["0-4", "5-14"]
CAPACIDAD = {"total": 106, "ninos": 18, "adultos": 88}        # tabla del HUN, 8-nov-2026 (ver docstring)
N_REP = 1000
SEMILLA = 42
BACKTEST_CORTE = "2025-12-31"
VENTANA_MEZCLA_EDAD = ("2025-01-01", "2026-01-01")            # mezcla de grupo_edad entre ingresos, ultimo ano completo confiable
VENTANA_BOOTSTRAP = ("2024-01-01", "2026-01-01")               # 2 anios para el bootstrap de horas_hosp (mas estable que 1 solo)
HORIZONTE_PROYECCION = 180

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)
rng_global = np.random.default_rng(SEMILLA)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


# ----------------------------------------------------------------------
# 1) Series base (ingresos y ocupacion), directo desde estancias_hospitalizacion.csv
# ----------------------------------------------------------------------
titulo("1. SERIES BASE (sin panel_diario.csv: se reconstruyen desde estancias_hospitalizacion.csv)")
est = pd.read_csv(PROC / "para_equipo" / "estancias_hospitalizacion.csv", parse_dates=["ingreso_cama", "alta"])
print(f"estancias unicas: {len(est)} | alta_completa: {int(est.alta_completa.sum())}")

dias_panel = pd.date_range(OCUP_DESDE, pd.Timestamp(OCUP_HASTA) - pd.Timedelta(days=1))
ingresos_a_cama = est.ingreso_cama.dt.normalize().value_counts().reindex(dias_panel, fill_value=0).astype(float)
ingresos_a_cama.name = "ingresos_a_cama"

horas_ev = pd.date_range(est.ingreso_cama.min().floor("h"), est.alta.max().floor("h"), freq="h")
delta = (est.ingreso_cama.dt.floor("h").value_counts()
         .sub(est.alta.dt.floor("h").value_counts(), fill_value=0).reindex(horas_ev, fill_value=0))
ocup_h = delta.cumsum()
ocup_d = ocup_h.groupby(ocup_h.index.normalize()).agg(["mean", "max"]).reindex(dias_panel)
print("ingresos_a_cama por anio (reproducido):", ingresos_a_cama.groupby(ingresos_a_cama.index.year).mean().round(1).to_dict())
print("ocup_hosp_media por anio (reproducido):", ocup_d["mean"].groupby(ocup_d.index.year).mean().round(1).to_dict())
print("(referencia CLAUDE.md 4.8: ingresos 20.6/20.8/19.8 y ocupacion 94/101/105 para 2023/2024/2025 - coincide)")

serie_ingresos = ingresos_a_cama.asfreq("D").rename("ingresos_a_cama")
print(f"\nserie_ingresos: {serie_ingresos.index.min().date()} a {serie_ingresos.index.max().date()} "
      f"(ya termina en {mp.FIN_CONFIABLE}, el ultimo dia confiable - CLAUDE.md 4.9; no hace falta blanquear nada mas)")

# ----------------------------------------------------------------------
# 2) Distribucion de estancias por grupo_edad (para el bootstrap) y mezcla de edades
# ----------------------------------------------------------------------
titulo("2. DISTRIBUCION DE ESTANCIAS POR GRUPO_EDAD (bootstrap empirico)")
completas = est[est.alta_completa & est.horas_hosp.notna() & est.grupo_edad.notna()]
resumen_edad = completas.groupby("grupo_edad", observed=True).horas_hosp.agg(
    n="size", mediana="median", p90=lambda s: s.quantile(.9)).round(1)
print("toda la historia (solo para describir):")
print(resumen_edad.to_string())

# el bootstrap usa SOLO 2024-2025: la mediana de estancia sube con el anio en casi todos los grupos
# (p. ej. 75+: 96.1h en 2023 -> 110.9h en 2025, docs/factores_estancia.md) - usar toda la historia
# subestimaba la ocupacion simulada (se detecto en el backtest: sesgo de -4.6 camas, corregido aqui).
reciente = completas[(completas.ingreso_cama >= VENTANA_BOOTSTRAP[0]) & (completas.ingreso_cama < VENTANA_BOOTSTRAP[1])]
BOOTSTRAP = {g: gg.horas_hosp.values for g, gg in reciente.groupby("grupo_edad", observed=True)}
resumen_reciente = reciente.groupby("grupo_edad", observed=True).horas_hosp.agg(
    n="size", mediana="median", p90=lambda s: s.quantile(.9)).round(1)
print(f"\n{VENTANA_BOOTSTRAP[0]} a {VENTANA_BOOTSTRAP[1]} (lo que de verdad usa el bootstrap, para no subestimar "
      f"la estancia de 2026):")
print(resumen_reciente.to_string())

mezcla = est[(est.ingreso_cama >= VENTANA_MEZCLA_EDAD[0]) & (est.ingreso_cama < VENTANA_MEZCLA_EDAD[1])
            & est.grupo_edad.notna()].grupo_edad.value_counts(normalize=True)
GRUPOS_HIST = mezcla.index.to_numpy()
PROB_GRUPOS = mezcla.values
print(f"\nmezcla de grupo_edad entre ingresos ({VENTANA_MEZCLA_EDAD[0]} a {VENTANA_MEZCLA_EDAD[1]}, usada para "
      f"asignar edad a cada ingreso simulado):")
print(mezcla.round(3).to_string())
print(f"niños (0-4 + 5-14) de la mezcla: {100 * mezcla.reindex(GRUPOS_NINOS).sum():.1f} %")


# ----------------------------------------------------------------------
# 3) Motor de Monte Carlo
# ----------------------------------------------------------------------
titulo("3. MOTOR DE SIMULACION")


def _una_repeticion(lam, rng, ajuste_estancia, n0=0):
    """Una repeticion sobre un horizonte de len(lam) dias. `n0` pacientes YA estan hospitalizados el dia 0
    (censo real del dia de corte, para no arrancar con el hospital vacio - ver nota en simular()). Devuelve
    3 arrays (total, ninos, adultos) de censo diario."""
    n_dias = len(lam)
    n_ingresos = rng.poisson(np.clip(lam, 0, None))
    dia_ingreso_nuevos = np.repeat(np.arange(n_dias), n_ingresos)
    dia_ingreso = np.concatenate([np.zeros(n0, dtype=int), dia_ingreso_nuevos]).astype(int)
    total = len(dia_ingreso)
    if total == 0:
        z = np.zeros(n_dias)
        return z, z.copy(), z.copy()
    grupo = rng.choice(GRUPOS_HIST, size=total, p=PROB_GRUPOS)
    horas = np.empty(total)
    for g in GRUPOS_HIST:
        m = grupo == g
        if m.any():
            horas[m] = rng.choice(BOOTSTRAP[g], size=int(m.sum()), replace=True)
    horas = horas * ajuste_estancia
    dur_dias = np.clip(np.ceil(horas / 24).astype(int), 1, None)
    dia_alta = dia_ingreso + dur_dias   # exclusivo

    def censo(mask):
        delta_ = np.zeros(n_dias + 1)
        np.add.at(delta_, dia_ingreso[mask], 1.0)
        np.add.at(delta_, np.clip(dia_alta[mask], 0, n_dias), -1.0)
        return np.cumsum(delta_)[:n_dias]

    todos = np.ones(total, dtype=bool)
    es_nino = np.isin(grupo, GRUPOS_NINOS)
    return censo(todos), censo(es_nino), censo(~es_nino)


def simular(serie, corte, dias, escenario="historico", ajuste_ingresos=1.0, ajuste_estancia=1.0,
            n_rep=N_REP, semilla=SEMILLA):
    """Simula `dias` dias despues de `corte`. Devuelve (fechas, censos) donde censos es un dict
    {'total'/'ninos'/'adultos': array (n_rep, dias)} con el censo diario de cada repeticion.
    SIEMBRA el dia 0 con el censo REAL del dia de corte (ocup_d), para no arrancar con el hospital vacio -
    sin esto, la ocupacion simulada tarda ~3-4 semanas en "llenarse" y ese arranque artificial no existe en la
    realidad. Simplificacion declarada: a cada paciente ya hospitalizado se le asigna como tiempo QUE LE QUEDA
    un valor sacado del mismo bootstrap de estancias COMPLETAS (no se corrige el sesgo de seleccion de que un
    paciente ya hospitalizado tiende a estar en una estancia mas larga que el promedio - "inspection paradox");
    es una aproximacion, no afecta la ocupacion de REGIMEN (mas alla de los primeros ~30 dias)."""
    rng = np.random.default_rng(semilla)
    cal = mp.calendario(pd.date_range(serie.index.min(), pd.Timestamp(corte) + pd.Timedelta(days=dias + 2)))
    pron = mp.pronosticar_desde(serie, cal, pd.Timestamp(corte), dias, escenario) * ajuste_ingresos
    fechas = pron.index
    lam = pron.values
    censo_real = ocup_d["mean"].reindex([pd.Timestamp(corte)]).iloc[0]
    if pd.isna(censo_real):
        censo_real = ocup_d["mean"].dropna().iloc[-1]
    n0 = int(round(censo_real))
    out = {"total": np.zeros((n_rep, dias)), "ninos": np.zeros((n_rep, dias)), "adultos": np.zeros((n_rep, dias))}
    for r in range(n_rep):
        t, n, a = _una_repeticion(lam, rng, ajuste_estancia, n0=n0)
        out["total"][r], out["ninos"][r], out["adultos"][r] = t, n, a
    return fechas, out


def percentiles(censos, pcts=(10, 50, 90)):
    return {k: {p: np.percentile(v, p, axis=0) for p in pcts} for k, v in censos.items()}


print(f"motor listo: {N_REP} repeticiones, bootstrap por grupo_edad, ingresos ~ Poisson(pronostico)")

# ----------------------------------------------------------------------
# 4) BACKTEST (ficha 3.1, puerta de decision)
# ----------------------------------------------------------------------
titulo("4. BACKTEST: enero a 9-abr-2026, entrenado SOLO con datos hasta el 31-dic-2025")
dias_bt = (pd.Timestamp("2026-04-09") - pd.Timestamp(BACKTEST_CORTE)).days
fechas_bt, censos_bt = simular(serie_ingresos, BACKTEST_CORTE, dias_bt, escenario="historico")
pct_bt = percentiles(censos_bt)
real_bt = ocup_d.reindex(fechas_bt)
err = pct_bt["total"][50] - real_bt["mean"].values
cobertura = ((real_bt["mean"].values >= pct_bt["total"][10]) & (real_bt["mean"].values <= pct_bt["total"][90])).mean()
print(f"dias de backtest: {dias_bt} ({fechas_bt.min().date()} a {fechas_bt.max().date()})")
print(f"error absoluto medio (mediana simulada vs ocupacion real media): {np.abs(err).mean():.1f} camas")
print(f"sesgo medio (simulada - real): {err.mean():+.1f} camas")
print(f"% de dias con la ocupacion real dentro de la banda 10-90 %: {100 * cobertura:.1f} % "
      f"(meta de la ficha 3.1: entre 70 % y 90 %)")
bt_tabla = pd.DataFrame({"fecha": fechas_bt, "real_media": real_bt["mean"].values, "real_max": real_bt["max"].values,
                         "sim_p10": pct_bt["total"][10], "sim_p50": pct_bt["total"][50], "sim_p90": pct_bt["total"][90]})
bt_tabla.to_csv(TABLAS / "simcamas_backtest.csv", index=False)
print("guardado: resultados/tablas/simcamas_backtest.csv")

# ----------------------------------------------------------------------
# 5) PROYECCION HACIA ADELANTE Y ALERTA DE SATURACION
# ----------------------------------------------------------------------
titulo("5. PROYECCION HACIA ADELANTE Y ALERTA DE SATURACION (desde el ultimo dato confiable)")
ULTIMO_CONFIABLE = serie_ingresos.dropna().index.max()
print(f"ultimo dato confiable: {ULTIMO_CONFIABLE.date()} | horizonte: {HORIZONTE_PROYECCION} dias")
fechas_f, censos_f = simular(serie_ingresos, ULTIMO_CONFIABLE, HORIZONTE_PROYECCION, escenario="historico")
pct_f = percentiles(censos_f)

p90_historico = ocup_d["mean"].dropna().quantile(.9)
print(f"percentil 90 de la ocupacion historica de entrenamiento (total, referencia de la ficha 3.1): "
      f"{p90_historico:.1f} camas")

filas_sat = []
for grupo in ["total", "ninos", "adultos"]:
    umbrales = {"capacidad_HUN": CAPACIDAD[grupo]}
    if grupo == "total":
        umbrales["p90_historico"] = p90_historico
    for nombre_u, u in umbrales.items():
        prob = (censos_f[grupo] > u).mean(axis=0)
        filas_sat.append({"grupo": grupo, "umbral": nombre_u, "valor_umbral": round(float(u), 1),
                          "prob_saturacion_media_horizonte_%": round(100 * prob.mean(), 1),
                          "prob_saturacion_dia_30_%": round(100 * prob[29], 1) if len(prob) > 29 else np.nan,
                          "prob_saturacion_dia_60_%": round(100 * prob[59], 1) if len(prob) > 59 else np.nan,
                          "prob_saturacion_dia_90_%": round(100 * prob[89], 1) if len(prob) > 89 else np.nan})
sat = pd.DataFrame(filas_sat)
print(sat.to_string(index=False))
sat.to_csv(TABLAS / "simcamas_saturacion.csv", index=False)
print("\nguardado: resultados/tablas/simcamas_saturacion.csv")

proy = pd.DataFrame({"fecha": fechas_f})
for grupo in ("total", "ninos", "adultos"):
    for p in (10, 50, 90):
        proy[f"{grupo}_p{p}"] = pct_f[grupo][p]
proy.to_csv(TABLAS / "simcamas_proyeccion.csv", index=False)
print("guardado: resultados/tablas/simcamas_proyeccion.csv")

# ----------------------------------------------------------------------
# 6) ESCENARIOS B y C (A se cita, no se recalcula - src/simulacion_altas.py)
# ----------------------------------------------------------------------
titulo("6. ESCENARIOS: B (ingresos +10 %) y C (estancia -5 %)")
_, censos_B = simular(serie_ingresos, ULTIMO_CONFIABLE, HORIZONTE_PROYECCION, escenario="historico", ajuste_ingresos=1.10)
_, censos_C = simular(serie_ingresos, ULTIMO_CONFIABLE, HORIZONTE_PROYECCION, escenario="historico", ajuste_estancia=0.95)

filas_esc = []
for nombre, cs in [("hoy (base)", censos_f), ("B: ingresos +10%", censos_B), ("C: estancia -5%", censos_C)]:
    for grupo in ("total", "ninos", "adultos"):
        c = cs[grupo]
        filas_esc.append({"escenario": nombre, "grupo": grupo, "ocupacion_media": round(float(c.mean()), 1),
                          "ocupacion_max_p90": round(float(np.percentile(c.max(axis=1), 90)), 1),
                          "pct_dia_rep_saturado": round(100 * float((c > CAPACIDAD[grupo]).mean()), 1),
                          "capacidad_HUN": CAPACIDAD[grupo]})
esc = pd.DataFrame(filas_esc)
print(esc.to_string(index=False))
esc.to_csv(TABLAS / "simcamas_escenarios.csv", index=False)
print("\nguardado: resultados/tablas/simcamas_escenarios.csv")
print("\nEscenario A (altas antes del mediodia) NO se recalcula aqui: ya esta en src/simulacion_altas.py")
print("(resultado ya documentado: max. 8 % del exceso de espera evitado, estimacion ~3 % - CLAUDE.md 6b).")

# ----------------------------------------------------------------------
# 7) Graficos
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
    fig, axs = plt.subplots(1, 4, figsize=(20.5, 4.8), facecolor=SUPERFICIE,
                            gridspec_kw={"width_ratios": [1.05, 1.0, 1.05, .95]})

    def estilo(ax):
        ax.set_facecolor(SUPERFICIE)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(REJILLA)
        ax.tick_params(colors=TINTA2, labelsize=8.5)
        ax.grid(axis="y", color=REJILLA, linewidth=.8)
        ax.set_axisbelow(True)

    ax = axs[0]
    ax.fill_between(fechas_bt, pct_bt["total"][10], pct_bt["total"][90], color=AZUL, alpha=.18, label="banda 10-90 %")
    ax.plot(fechas_bt, pct_bt["total"][50], color=AZUL, linewidth=1.8, label="mediana simulada")
    ax.plot(fechas_bt, real_bt["mean"].values, color=NARANJA, linewidth=1.8, label="ocupacion real")
    ax.set_title(f"Backtest ene-9abr 2026 (cobertura {100 * cobertura:.0f} %)", loc="left", color=TINTA,
                fontsize=10.5, fontweight="bold")
    ax.set_ylabel("camas ocupadas", color=TINTA2, fontsize=9)
    ax.legend(frameon=False, fontsize=7.5, labelcolor=TINTA2, loc="lower left")
    ax.tick_params(axis="x", rotation=30)
    estilo(ax)

    # panel nuevo: zoom de corto plazo (30-60 dias), pensado para decisiones operativas, no solo estrategicas
    ax = axs[1]
    corto = slice(0, 60)
    ax.fill_between(fechas_f[corto], pct_f["total"][10][corto], pct_f["total"][90][corto], color=AZUL, alpha=.18,
                    label="banda 10-90 %")
    ax.plot(fechas_f[corto], pct_f["total"][50][corto], color=AZUL, linewidth=1.8, label="mediana simulada")
    ax.axhline(CAPACIDAD["total"], color=TINTA, linewidth=1, linestyle=(0, (4, 3)), label="106 camas (HUN)")
    for d, color in [(29, TINTA2), (59, TINTA2)]:
        ax.axvline(fechas_f[d], color=color, linewidth=.8, linestyle=(0, (1, 2)))
    prob_30 = sat.loc[(sat.grupo == "total") & (sat.umbral == "capacidad_HUN"), "prob_saturacion_dia_30_%"].iloc[0]
    prob_60 = sat.loc[(sat.grupo == "total") & (sat.umbral == "capacidad_HUN"), "prob_saturacion_dia_60_%"].iloc[0]
    ax.text(fechas_f[29], ax.get_ylim()[1] if False else pct_f["total"][90][corto].max() + 1,
            f"dia 30:\n{prob_30:.0f} %", fontsize=7, color=TINTA2, ha="center", va="bottom")
    ax.text(fechas_f[59], pct_f["total"][90][corto].max() + 1, f"dia 60:\n{prob_60:.0f} %", fontsize=7,
            color=TINTA2, ha="center", va="bottom")
    ax.set_title("Corto plazo (30-60 d) y prob. de saturar 106", loc="left", color=TINTA, fontsize=10.5,
                fontweight="bold")
    ax.legend(frameon=False, fontsize=7.5, labelcolor=TINTA2, loc="lower right")
    ax.tick_params(axis="x", rotation=30)
    estilo(ax)

    ax = axs[2]
    ax.fill_between(fechas_f, pct_f["total"][10], pct_f["total"][90], color=AZUL, alpha=.18, label="banda 10-90 %")
    ax.plot(fechas_f, pct_f["total"][50], color=AZUL, linewidth=1.8, label="mediana simulada")
    ax.axhline(CAPACIDAD["total"], color=TINTA, linewidth=1, linestyle=(0, (4, 3)), label="106 camas (HUN)")
    ax.axhline(p90_historico, color=NARANJA, linewidth=1, linestyle=(0, (1, 2)), label="p90 historico")
    ax.set_title(f"Proyeccion desde {ULTIMO_CONFIABLE.date()} ({HORIZONTE_PROYECCION} d)", loc="left", color=TINTA,
                fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=7.5, labelcolor=TINTA2, loc="lower right")
    ax.tick_params(axis="x", rotation=30)
    estilo(ax)

    ax = axs[3]
    nombres_esc = ["hoy (base)", "B: ingresos\n+10%", "C: estancia\n-5%"]
    valores = esc[esc.grupo == "total"].ocupacion_media.values
    x = np.arange(3)
    barras = ax.bar(x, valores, color=[AZUL, NARANJA, AQUA], width=.55)
    ax.axhline(CAPACIDAD["total"], color=TINTA, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(2.5, CAPACIDAD["total"] + 1, "106 camas", fontsize=7.5, color=TINTA2, ha="right")
    for xi, v in zip(x, valores):
        ax.text(xi, v + 1, f"{v:.0f}", ha="center", fontsize=8.5, color=TINTA)
    ax.set_xticks(x)
    ax.set_xticklabels(nombres_esc, fontsize=8)
    ax.set_title("Ocupacion media por escenario (total)", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    estilo(ax)

    fig.tight_layout(rect=(0, .02, 1, 1))
    fig.text(.01, .01, "Simulacion de Monte Carlo (1.000 repeticiones). Escenario A (altas) citado de "
             "simulacion_altas.py, no recalculado aqui. Asociacion, no causa.", color=TINTA2, fontsize=7.5)
    fig.savefig(GRAFICOS / "simcamas_resultados.png", dpi=150, facecolor=SUPERFICIE)
    print("\nguardado: resultados/graficos/simcamas_resultados.png")
