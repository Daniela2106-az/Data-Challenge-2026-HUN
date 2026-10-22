"""
alertas.py  -  version 1 (22-oct-2026)
Fase 7 del plan de cuellos de botella (docs/plan_de_accion.md, seccion 0): alertas de sistema y de paciente,
probadas REPRODUCIENDO dias pasados (validacion 2025-07 a 2025-12 para elegir cortes; prueba 2026-01 a 2026-04).

TRES ALERTAS
  A. DIA CONGESTIONADO (sistema, tiempo real): a las 9, 12 o 15 h se estima el total de llegadas del dia con lo
     que ya llego (llegadas hasta esa hora / parte tipica del dia que ya paso) mezclado con el pronostico del dia
     (dia de la semana x nivel reciente). Congestionado = llegadas > percentil 90 del mismo dia de la semana en
     las 12 semanas anteriores. El corte lo elige la validacion (maximo F1).
  B. CAMAS A 24 H (sistema): a las 12 h, camas ocupadas dentro de 24 h = camas ocupadas ahora
        - altas esperadas de quienes estan en cama (probabilidad de alta en 24 h dado el tiempo que llevan,
          de la distribucion real de estancias del entrenamiento)
        + ingresos esperados (dia de la semana x nivel reciente).
     Alerta si la proyeccion supera el percentil PERCENTIL_OCUP de la ocupacion de las 12 h en el entrenamiento
     (la capacidad real se desconoce: es un nivel de "ocupacion alta", no de saturacion). Tambien entrega las
     altas esperadas (camas que se liberan) en las proximas 24 h.
  C. PACIENTE (espera de cama larga): el paciente lleva T horas desde su llegada sin cama. Para cada T se
     reporta cuantas alertas por dia genera, que porcentaje termina esperando mas de 72 h (percentil 90 de la
     espera) y con cuantas horas de anticipacion. Solo se evalua con los pacientes que despues se hospitalizan
     (los unicos con espera de cama medida): es una cota inferior de la carga real de alertas, porque en
     tiempo real tambien alertaria por quienes al final no se hospitalizan.

ENTRADAS  datos/procesados/para_equipo/panel_diario.csv, datos/procesados/serie_horaria.csv,
          datos/procesados/para_equipo/estancias_hospitalizacion.csv, datos/procesados/segmentos.csv
SALIDAS   resultados/tablas/alertas_congestion.csv, alertas_camas.csv, alertas_camas_dias.csv,
          alertas_paciente.csv, alertas_carga_diaria.csv ; resultados/graficos/alertas.png

RESULTADO CLAVE DE B (22-oct): la proyeccion de camas a 24 h NO mejora a la persistencia ("lo mismo que ahora"): el
  balance diario entre ingresos y altas es casi todo azar y las altas esperadas tienen sesgo. Para la alerta de camas se
  recomienda la persistencia; las altas esperadas se reportan solo como orden de magnitud.

OJO AL LEER
  - Los cortes de A y B se eligen con 2025-07 a 2025-12 y la prueba (2026-01 a 2026-04) se mira una vez. La
    prueba tiene pocos dias positivos: las precisiones pueden moverse bastante.
  - "Reproducir" usa solo lo que se sabia en ese momento (llegadas hasta la hora, camas ocupadas, esperas de
    quienes ya habian llegado). Los pacientes sin hora de fin quedan fuera de C (no se pueden seguir).
  - Mayo 2026 no se usa (caida de llegadas por posible carga incompleta; pregunta 14 al HUN).
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

ENTRENA_HASTA, VALIDA_ENTRENA_HASTA, VALIDA_DESDE = "2025-12-31", "2025-06-30", "2025-07-01"
PRUEBA_DESDE, PRUEBA_HASTA = "2026-01-01", "2026-04-30"
HORAS_CORTE = [9, 12, 15]
SEMANAS_UMBRAL = 12
PERCENTIL_OCUP = 0.80       # "ocupacion alta" = percentil 80 de la ocupacion de las 12 h en el entrenamiento
HORAS_T = [12, 24, 36, 48, 60]
ESPERA_LARGA_H = 72

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


def auc(y, score):
    y, s = np.asarray(y, bool), pd.Series(np.asarray(score, float)).rank().values
    n1, n0 = y.sum(), (~y).sum()
    return np.nan if n1 == 0 or n0 == 0 else (s[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def mejor_corte(score, etiqueta, grilla):
    """Corte que maximiza F1; si hay empate se queda con el mas alto (menos alertas)."""
    mejor, corte = -1, grilla[0]
    for c in grilla:
        a = score >= c
        tp = (a & etiqueta).sum()
        den = a.sum() + etiqueta.sum()
        f1 = 2 * tp / den if den else 0
        if f1 >= mejor:
            mejor, corte = f1, c
    return float(corte), float(mejor)


def resumen_alerta(a, etiqueta):
    tp = int((a & etiqueta).sum())
    return {"alertas": int(a.sum()), "aciertos": tp, "precision_%": round(100 * tp / max(a.sum(), 1), 1),
            "deteccion_%": round(100 * tp / max(etiqueta.sum(), 1), 1), "falsas_alarmas": int(a.sum()) - tp}


# ----------------------------------------------------------------------
# A. Dia congestionado en tiempo real
# ----------------------------------------------------------------------
titulo("A. ALERTA DE DIA CONGESTIONADO (llegadas > percentil 90 del mismo dia de la semana en 12 semanas)")
d = pd.read_csv(PROC / "para_equipo" / "panel_diario.csv", parse_dates=["fecha"]).set_index("fecha")
d["dow"] = d.index.dayofweek
y = d.llegadas
umbral = pd.concat([y.shift(7 * k) for k in range(1, SEMANAS_UMBRAL + 1)], axis=1).quantile(.9, axis=1)
etiqueta = y > umbral

hh = pd.read_csv(PROC / "serie_horaria.csv", parse_dates=["hora_inicio"]).set_index("hora_inicio").llegadas
hh = hh[(hh.index >= d.index.min()) & (hh.index < d.index.max() + pd.Timedelta(days=1))]
H = hh.to_frame("y")
H["fecha"], H["hora"] = H.index.normalize(), H.index.hour
tabla = H.pivot_table(index="fecha", columns="hora", values="y", aggfunc="sum").reindex(d.index).fillna(0)
total_dia = tabla.sum(axis=1)


def previo(col, entr_fin):
    """Pronostico del dia = factor del dia de la semana x promedio de los 28 dias anteriores."""
    s = d[col]
    nivel = s.rolling(28).mean().shift(1)
    m = (d.index <= entr_fin) & nivel.notna()
    fact = (s[m] / nivel[m]).groupby(d.dow[m]).mean()
    return d.dow.map(fact) * nivel


def puntaje(k, entr_fin):
    ent = d.index <= entr_fin
    acum = tabla.iloc[:, :k].sum(axis=1)
    parte = (acum[ent] / total_dia[ent]).groupby(d.dow[ent]).mean()
    ahora = acum / d.dow.map(parte)
    return (ahora * k / 24 + previo("llegadas", entr_fin) * (24 - k) / 24) / umbral


val_idx = d.index[(d.index >= VALIDA_DESDE) & (d.index <= ENTRENA_HASTA) & umbral.notna()]
test_idx = d.index[(d.index >= PRUEBA_DESDE) & (d.index <= PRUEBA_HASTA)]
print(f"dias de validacion: {len(val_idx)} (congestionados: {int(etiqueta[val_idx].sum())}) | "
      f"dias de prueba: {len(test_idx)} (congestionados: {int(etiqueta[test_idx].sum())})")
GRILLA = np.arange(0.80, 1.16, 0.01)
filas = []
sc_prev_v = (previo("llegadas", VALIDA_ENTRENA_HASTA) / umbral)
sc_prev_t = (previo("llegadas", ENTRENA_HASTA) / umbral)
for nombre, sv, st, quien in [("un dia antes (solo el pronostico)", sc_prev_v, sc_prev_t, "dia anterior")] + \
        [(f"a las {k} h", puntaje(k, VALIDA_ENTRENA_HASTA), puntaje(k, ENTRENA_HASTA), f"{k} h") for k in HORAS_CORTE]:
    c, f1 = mejor_corte(sv[val_idx], etiqueta[val_idx], GRILLA)
    a = st[test_idx] >= c
    filas.append({"momento": nombre, "corte_(puntaje/umbral)": round(c, 2), "F1_validacion": round(f1, 2),
                  "AUC_prueba": round(auc(etiqueta[test_idx], st[test_idx]), 3), **resumen_alerta(a, etiqueta[test_idx])})
al_a = pd.DataFrame(filas)
al_a["alertas_por_dia"] = (al_a.alertas / len(test_idx)).round(2)
al_a.to_csv(TABLAS / "alertas_congestion.csv", index=False)
print(al_a.to_string(index=False))
print("(el corte es el puntaje estimado del dia dividido entre el umbral de congestion; 1,0 = justo en el umbral)")

# ----------------------------------------------------------------------
# B. Camas a 24 h
# ----------------------------------------------------------------------
titulo("B. CAMAS OCUPADAS DENTRO DE 24 H, DESDE LAS 12 H (estancias unicas)")
est = pd.read_csv(PROC / "para_equipo" / "estancias_hospitalizacion.csv", parse_dates=["ingreso_cama", "alta"])
ing, alta = est.ingreso_cama.values, est.alta.values


def ocupacion(t):
    t = np.datetime64(t)
    return int(((ing <= t) & (alta > t)).sum())


def distribucion_estancias(entr_fin):
    m = est.alta_completa & (est.ingreso_cama <= pd.Timestamp(entr_fin))
    return np.sort(((est.alta - est.ingreso_cama).dt.total_seconds() / 3600)[m].values)


def prob_alta_24h(e, los):
    """P(alta en las proximas 24 h | lleva e horas) = 1 - S(e+24)/S(e), con S de la distribucion empirica."""
    n = len(los)
    s0 = 1 - np.searchsorted(los, e, side="right") / n
    s24 = 1 - np.searchsorted(los, e + 24, side="right") / n
    return np.where(s0 > 1e-3, 1 - s24 / np.maximum(s0, 1e-3), 1.0)


def proyeccion(dias, entr_fin):
    los = distribucion_estancias(entr_fin)
    pre = previo("ingresos_a_cama", entr_fin)
    ent = d.index <= entr_fin
    nivel = d.ingresos_a_cama.rolling(28).mean().shift(1)
    fact = (d.ingresos_a_cama[ent & nivel.notna()] / nivel[ent & nivel.notna()]).groupby(d.dow[ent & nivel.notna()]).mean()
    filas = []
    for dia in dias:
        t = dia + pd.Timedelta(hours=12)
        en_cama = (ing <= np.datetime64(t)) & (alta > np.datetime64(t))
        e_h = (np.datetime64(t) - ing[en_cama]) / np.timedelta64(1, "h")
        altas = float(prob_alta_24h(e_h.astype(float), los).sum())
        sig = (dia + pd.Timedelta(days=1)).dayofweek
        ingresos = 0.5 * (fact[dia.dayofweek] + fact[sig]) * nivel[dia]
        altas_reales = int((alta[en_cama] <= np.datetime64(t + pd.Timedelta(hours=24))).sum())
        filas.append({"fecha": dia, "ocupacion_ahora": int(en_cama.sum()), "altas_esperadas_24h": altas,
                      "altas_reales_24h": altas_reales,
                      "ingresos_esperados_24h": ingresos, "proyeccion_24h": en_cama.sum() - altas + ingresos,
                      "ocupacion_real_24h": ocupacion(t + pd.Timedelta(hours=24))})
    return pd.DataFrame(filas).set_index("fecha")


val_dias = pd.date_range(VALIDA_DESDE, ENTRENA_HASTA)
test_dias = pd.date_range(PRUEBA_DESDE, PRUEBA_HASTA)
pv = proyeccion(val_dias, VALIDA_ENTRENA_HASTA)
pt = proyeccion(test_dias, ENTRENA_HASTA)
pt["persistencia"] = pt.ocupacion_ahora
pv["persistencia"] = pv.ocupacion_ahora
print("ERROR de la ocupacion dentro de 24 h (camas):")
filas = []
for nombre, p in [("validacion 2025-07 a 2025-12", pv), ("prueba 2026-01 a 2026-04", pt)]:
    for metodo, col in [("proyeccion (altas esperadas + ingresos esperados)", "proyeccion_24h"),
                        ("persistencia (lo mismo que ahora)", "persistencia")]:
        err = p[col] - p.ocupacion_real_24h
        filas.append({"periodo": nombre, "metodo": metodo, "MAE_camas": round(err.abs().mean(), 2),
                      "sesgo_camas": round(err.mean(), 2), "ocupacion_real_media": round(p.ocupacion_real_24h.mean(), 1)})
err_b = pd.DataFrame(filas)
print(err_b.to_string(index=False))
print("\nCALIBRACION DE LAS ALTAS ESPERADAS (de quienes estan en cama a las 12 h, cuantos se van en 24 h):")
fila_cal = []
for nombre, p in [("validacion", pv), ("prueba", pt)]:
    e_ = p.altas_esperadas_24h - p.altas_reales_24h
    cte = p.altas_reales_24h.mean() - p.altas_reales_24h          # referencia: siempre el promedio del periodo
    fila_cal.append({"periodo": nombre, "altas_reales_media": round(p.altas_reales_24h.mean(), 1),
                     "altas_esperadas_media": round(p.altas_esperadas_24h.mean(), 1), "sesgo": round(e_.mean(), 2),
                     "MAE_modelo": round(e_.abs().mean(), 2), "MAE_si_se_usa_el_promedio": round(cte.abs().mean(), 2),
                     "correlacion": round(p.altas_esperadas_24h.corr(p.altas_reales_24h), 2)})
print(pd.DataFrame(fila_cal).to_string(index=False))
print("Lectura: las altas esperadas sobrestiman (sesgo positivo) y casi no siguen el dia a dia (correlacion baja); no "
      "mejoran a usar el promedio. Una causa posible, sin comprobar: las estancias del entrenamiento son mas cortas que las "
      "de 2026 (la estancia media subio ~16 % desde 2023). Por eso la proyeccion no mejora a la persistencia.")

# alerta de ocupacion alta
oc_ent = pd.Series([ocupacion(dia + pd.Timedelta(hours=12)) for dia in pd.date_range("2023-03-01", ENTRENA_HASTA)])
oc_ent_v = oc_ent.iloc[:len(pd.date_range("2023-03-01", VALIDA_ENTRENA_HASTA))]
umbral_v, umbral_t = oc_ent_v.quantile(PERCENTIL_OCUP), oc_ent.quantile(PERCENTIL_OCUP)
et_v, et_t = pv.ocupacion_real_24h >= umbral_v, pt.ocupacion_real_24h >= umbral_t
print(f"\nocupacion alta = percentil {int(PERCENTIL_OCUP * 100)} de las 12 h del entrenamiento: {umbral_v:.0f} camas (validacion), "
      f"{umbral_t:.0f} (prueba) | dias con ocupacion alta a 24 h: validacion {int(et_v.sum())}, prueba {int(et_t.sum())}")
GRILLA_B = np.arange(-8, 9, 1.0)
cb, f1b = mejor_corte(pv.proyeccion_24h - umbral_v, et_v, GRILLA_B)
filas = []
for nombre, col in [("proyeccion", "proyeccion_24h"), ("persistencia", "persistencia")]:
    cc, f1 = mejor_corte(pv[col] - umbral_v, et_v, GRILLA_B)
    a = (pt[col] - umbral_t) >= cc
    filas.append({"metodo": nombre, "corte_(camas sobre el umbral)": cc, "F1_validacion": round(f1, 2),
                  "AUC_prueba": round(auc(et_t, pt[col]), 3), **resumen_alerta(a, et_t)})
al_b = pd.DataFrame(filas)
al_b["alertas_por_dia"] = (al_b.alertas / len(test_dias)).round(2)
al_b.to_csv(TABLAS / "alertas_camas.csv", index=False)
print(al_b.to_string(index=False))
pt.round(1).to_csv(TABLAS / "alertas_camas_dias.csv")

# ----------------------------------------------------------------------
# C. Paciente: lleva T horas sin cama
# ----------------------------------------------------------------------
titulo("C. ALERTA POR PACIENTE: LLEVA T HORAS DESDE QUE LLEGO Y AUN NO TIENE CAMA")
seg = pd.read_csv(PROC / "segmentos.csv", usecols=["segmento", "horas", "ini", "franja", "en_estadisticas"], parse_dates=["ini"])
e = seg[(seg.segmento == "espera_cama") & seg.en_estadisticas & (seg.ini >= "2023-02-01") & (seg.ini < "2026-05-01")].copy()
dias_e = (pd.Timestamp("2026-05-01") - pd.Timestamp("2023-02-01")).days
print(f"estancias con espera de cama medida: {len(e)} en {dias_e} dias ({len(e) / dias_e:.1f} por dia)")
filas = []
for T in HORAS_T:
    al = e[e.horas > T]
    filas.append({"alerta_a_las_T_horas": T, "alertas_por_dia": round(len(al) / dias_e, 2),
                  "pct_que_espera_mas_de_72h": round(100 * (al.horas > ESPERA_LARGA_H).mean(), 1),
                  "horas_de_anticipacion_a_las_72h": max(ESPERA_LARGA_H - T, 0),
                  "horas_que_les_faltan_p50": round((al.horas - T).median(), 1)})
al_c = pd.DataFrame(filas)
al_c.to_csv(TABLAS / "alertas_paciente.csv", index=False)
print(al_c.to_string(index=False))
print("Lectura: alertar antes da mas tiempo de reaccion pero con menos precision y mas alertas por dia.")

# ----------------------------------------------------------------------
# Carga total de alertas por dia (con el diseno recomendado)
# ----------------------------------------------------------------------
titulo("CARGA TOTAL DE ALERTAS POR DIA (diseno recomendado)")
rec_a = al_a[al_a.momento == "a las 12 h"].iloc[0]
rec_b = al_b[al_b.metodo == "persistencia"].iloc[0]       # la proyeccion no mejora a la persistencia (ver B)
rec_c = al_c[al_c.alerta_a_las_T_horas == 48].iloc[0]
carga = pd.DataFrame([
    {"alerta": "A. dia congestionado (a las 12 h)", "alertas_por_dia": rec_a.alertas_por_dia, "precision_%": rec_a["precision_%"]},
    {"alerta": "B. camas altas a 24 h (desde las 12 h)", "alertas_por_dia": rec_b.alertas_por_dia, "precision_%": rec_b["precision_%"]},
    {"alerta": "C. paciente con 48 h sin cama (solo los que se hospitalizan)", "alertas_por_dia": rec_c.alertas_por_dia,
     "precision_%": rec_c.pct_que_espera_mas_de_72h}])
carga.loc[len(carga)] = {"alerta": "TOTAL", "alertas_por_dia": round(carga.alertas_por_dia.sum(), 2), "precision_%": np.nan}
carga.to_csv(TABLAS / "alertas_carga_diaria.csv", index=False)
print(carga.to_string(index=False))

# ----------------------------------------------------------------------
# Grafico
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
    fig, axs = plt.subplots(1, 3, figsize=(15.5, 4.9), facecolor=SUPERFICIE)

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
    x_ = np.arange(len(al_a))
    ax.bar(x_ - .2, al_a["precision_%"], width=.38, color=AZUL, label="precision (de las alertas, cuantas acertaron)")
    ax.bar(x_ + .2, al_a["deteccion_%"], width=.38, color=NARANJA, label="deteccion (de los dias congestionados, cuantos avisaron)")
    for i, r in al_a.iterrows():
        ax.text(i - .2, r["precision_%"] + 1.5, f"{r['precision_%']:.0f}", ha="center", fontsize=8.5, color=TINTA)
        ax.text(i + .2, r["deteccion_%"] + 1.5, f"{r['deteccion_%']:.0f}", ha="center", fontsize=8.5, color=TINTA)
    ax.set_xticks(x_)
    ax.set_xticklabels(["un dia\nantes", "9 h", "12 h", "15 h"], fontsize=9)
    ax.set_ylim(0, 112)
    ax.set_ylabel("%", color=TINTA2, fontsize=9)
    ax.set_title("A. Dia congestionado: avisar a media jornada", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=7.5, labelcolor=TINTA2, loc="upper left")
    estilo(ax)

    ax = axs[1]
    ax.plot(pt.index, pt.ocupacion_real_24h, color=TINTA2, linewidth=1.3, label="real a 24 h")
    ax.plot(pt.index, pt.proyeccion_24h, color=AZUL, linewidth=2, label="proyeccion desde las 12 h")
    ax.plot(pt.index, pt.persistencia, color=NARANJA, linewidth=1.3, linestyle=(0, (4, 3)), label="persistencia (ocupacion de ahora)")
    ax.axhline(umbral_t, color=TINTA2, linewidth=1, linestyle=":", label=f"ocupacion alta ({umbral_t:.0f} camas)")
    ax.set_xticks([pd.Timestamp(f"2026-{m:02d}-01") for m in range(1, 5)])
    ax.set_xticklabels(["ene", "feb", "mar", "abr"])
    ax.set_ylabel("camas ocupadas", color=TINTA2, fontsize=9)
    ax.set_title("B. Camas dentro de 24 h (2026)", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, labelcolor=TINTA2, loc="lower left", ncol=1)
    estilo(ax)

    ax = axs[2]
    ax.bar(np.arange(len(al_c)), al_c.pct_que_espera_mas_de_72h, width=.55, color=AQUA)
    for i, r in al_c.iterrows():
        ax.text(i, r.pct_que_espera_mas_de_72h + 1.5, f"{r.pct_que_espera_mas_de_72h:.0f} %\n{r.alertas_por_dia:.1f}/dia",
                ha="center", fontsize=8.5, color=TINTA)
    ax.set_xticks(np.arange(len(al_c)))
    ax.set_xticklabels([f"{t} h" for t in al_c.alerta_a_las_T_horas], fontsize=9)
    ax.set_xlabel("alerta cuando lleva T horas sin cama (anticipacion = 72 - T)", color=TINTA2, fontsize=9)
    ax.set_ylabel("% que termina esperando mas de 72 h", color=TINTA2, fontsize=9)
    ax.set_ylim(0, max(al_c.pct_que_espera_mas_de_72h) * 1.3)
    ax.set_title("C. Paciente: precision y alertas por dia", loc="left", color=TINTA, fontsize=10.5, fontweight="bold")
    estilo(ax)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.text(.01, .01, "Cortes elegidos con 2025-07 a 2025-12; prueba 2026-01 a 2026-04 (pocos dias positivos: las cifras se mueven). "
             "C solo cuenta pacientes que luego se hospitalizan.", color=TINTA2, fontsize=8)
    fig.savefig(GRAFICOS / "alertas.png", dpi=150, facecolor=SUPERFICIE)
    print("\nguardado: resultados/graficos/alertas.png")
