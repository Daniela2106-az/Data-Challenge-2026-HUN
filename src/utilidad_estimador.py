"""
utilidad_estimador.py  -  version 1 (8-nov-2026)
Tarea A6: ¿que tan UTIL es el estimador? Mide tres salidas pensadas para el uso diario del hospital, con la misma prueba de siempre (modelos
entrenados con llegadas de feb-2023 a jun-2025, con mas peso en lo reciente; prueba con jul-2025 a 9-abr-2026).

1. VENTANAS DE ASIGNACION (para el paciente y su familia): probabilidad de recibir cama en cada bloque del dia (madrugada 0-7, mañana 7-14,
   tarde 14-19, noche 19-24) de hoy, mañana y pasado mañana, y despues. Se mide: si la ventana mas probable acierta, si la real esta entre las 2 mas
   probables, el puntaje de Brier (error de las probabilidades; menor es mejor) y la calibracion (cuando dice 30 %, ¿pasa el 30 % de las veces?).
   Referencia: la distribucion historica de la ventana segun la hora del reloj (lo que se diria sin modelo).
2. CENSO PARA LA REUNION DE CAMAS (para gestion): cada dia a las 7:00 y a las 13:00, entre los pacientes que esperan cama en ese momento,
   ¿cuantos la reciben en las proximas 12 y 24 horas? El estimador suma las probabilidades de cada paciente. Se compara con lo que paso y con la
   referencia historica (pacientes en espera x fraccion historica que recibe cama en ese plazo a esa hora). Ademas se calcula el PISO DE RUIDO: el
   error que tendria hasta un estimador perfecto porque el numero de camas asignadas es un conteo con azar (Poisson). La banda del 80 % se arma
   con la distribucion de Poisson del estimado (la de suma de probabilidades independientes subestimaba el ruido: acertaba solo el 64-73 % de los dias).
3. ALERTA DE ESPERA LARGA (para actuar antes): a las 12 h de espera, la probabilidad de seguir sin cama a las 48 h. Se mide el AUC y, para varios
   cortes, cuantas alertas da por dia, que parte de las alertas acierta (precision) y que parte de los que esperan mas de 48 h detecta.

OJO: el censo usa a los pacientes que luego se hospitalizan (en el hospital equivale a los que tienen orden de hospitalizacion pendiente, que se
conocen en el momento; aqui incluye tambien la atencion previa a esa orden). Todo es asociacion; los modelos no conocen el servicio ni el triage.

ENTRADAS  tabla_episodios.parquet (HUN_PROCESADOS); visit_detail.csv y procedimientos_por_estancia.csv (HUN_CRUDOS)
SALIDAS   en HUN_TABLAS: utilidad_ventanas.csv, utilidad_ventanas_calibracion.csv, utilidad_censo.csv, utilidad_censo_diario.csv, utilidad_alerta.csv
          resultados/graficos/utilidad_estimador.png
COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... HUN_CRUDOS=... python3 src/utilidad_estimador.py   (~10 min; con --solo-grafico rehace solo el grafico)
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import poisson

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402
import estimador_tiempo_restante as etr  # noqa: E402

H1 = np.timedelta64(1, "h")
HORAS_CENSO = [7, 13]
PLAZOS_CENSO = [12, 24]
ALERTA_DESDE, ALERTA_LIMITE = 12, 48


# ----------------------------------------------------------------------
# Curvas de "seguir esperando" para muchos pacientes, cada uno en su propio momento
# ----------------------------------------------------------------------
def curvas(paq, d, filas, horas):
    """Para cada paciente (fila de d) que lleva horas[i] esperando: (c, S) con S[j] = P(sigue esperando a las c + j horas | sigue ahora)."""
    sub = d.loc[filas].reset_index(drop=True)
    horas = np.asarray(horas, float)
    ahora = sub.ini_est.to_numpy() + (horas * 3600).astype("int64").astype("timedelta64[s]")
    k_zona = sub.zona.to_numpy() == "ninos"
    rej, est = curvas.rejilla, curvas.estado
    kk_ahora = np.clip(((ahora - rej[0]) // H1).astype(int), 0, len(rej) - 1)
    ocup = np.where(k_zona, est["ninos"]["ocup"][kk_ahora], est["adultos"]["ocup"][kk_ahora])
    vacio = (np.array([]), np.array([]), np.array([]))
    grupos = {}
    for i in range(len(sub)):
        m = etr.modelo_para(paq, horas[i])
        grupos.setdefault(id(m), (m, []))[1].append(i)
    out = [None] * len(sub)
    for m, idx in grupos.values():
        bloques, largos = [], []
        for i in idx:
            c = int(np.floor(horas[i]))
            k = np.arange(c, ce.MAX_H)
            reloj = pd.DatetimeIndex(ahora[i] + ((k - horas[i]) * 3600).astype("int64").astype("timedelta64[s]"))
            rec = ce.recorrido_paciente(*ce.ETAPAS.get(sub.clave[i], vacio), np.full(len(k), horas[i]), k.astype(float))
            fila = {"transcurrido": k, "hora_reloj": reloj.hour, "dia_semana": reloj.dayofweek, "ocup": ocup[i], **rec,
                    **{col: sub.at[i, col] for col in m.cols_ if col not in ("transcurrido", "hora_reloj", "dia_semana", "ocup") and col not in rec}}
            bloques.append(pd.DataFrame(fila)[m.cols_])
            largos.append(len(k))
        p = m.predict_proba(pd.concat(bloques, ignore_index=True))[:, 1]
        pos = 0
        for i, n in zip(idx, largos):
            out[i] = (int(np.floor(horas[i])), np.concatenate([[1.0], np.cumprod(1 - p[pos:pos + n])]))
            pos += n
    return out


def sigue(c, S, t):
    return np.interp(t, c + np.arange(len(S)), S, left=1.0, right=S[-1])


# ----------------------------------------------------------------------
# 1) Ventanas de asignacion
# ----------------------------------------------------------------------
def etiqueta_real(ahora, cama, dias=3):
    """Ventana (dia relativo y bloque) en que el paciente recibio cama, contando desde el dia de 'ahora'."""
    d = (pd.Timestamp(cama).normalize() - pd.Timestamp(ahora).normalize()).days
    if d >= dias:
        return "después"
    h = pd.Timestamp(cama).hour
    nombre = next(n for a, b, n in etr.BLOQUES if a <= h < b)
    return f"{etr.NOMBRES_DIA[d]}, {nombre}"


def referencia_ventanas(tr, horas_desde):
    """Distribucion historica de la ventana real segun la hora del reloj en el momento de la estimacion (entrenamiento)."""
    t = tr[tr.espera_cama_h > horas_desde]
    ahora = t.ini_est + pd.to_timedelta(horas_desde, unit="h")
    lab = [etiqueta_real(a, c) for a, c in zip(ahora, t.ini_hosp_est)]
    return pd.crosstab(ahora.dt.hour.to_numpy(), np.array(lab), normalize="index")


def evaluar_ventanas(paq, d, te, tr, horas_desde):
    sub = te[te.espera_cama_h > horas_desde]
    cur = curvas(paq, d, sub.index, np.full(len(sub), horas_desde))
    ref = referencia_ventanas(tr, horas_desde)
    filas, pares = [], []
    for (i, r), (c, S) in zip(sub.iterrows(), cur):
        ahora = r.ini_est + pd.Timedelta(hours=horas_desde)
        v = etr.ventanas_de_cama(S, c, horas_desde, ahora)
        real = etiqueta_real(ahora, r.ini_hosp_est)
        p_mod = {x["ventana"]: x["probabilidad"] for x in v}
        p_ref = ref.loc[ahora.hour].to_dict() if ahora.hour in ref.index else {}
        nombres = list(p_mod)
        orden = sorted(nombres, key=lambda n: -p_mod[n])
        orden_ref = sorted(nombres, key=lambda n: -p_ref.get(n, 0))
        con_fecha = [n for n in orden if n != "después"]                 # lo que muestra la pagina como "lo mas probable"
        con_fecha_ref = [n for n in orden_ref if n != "después"]
        filas.append({"real": real, "acierta_1": orden[0] == real, "acierta_2": real in orden[:2],
                      "acierta_1_ref": orden_ref[0] == real, "acierta_2_ref": real in orden_ref[:2],
                      "acierta_fecha": con_fecha[0] == real, "acierta_fecha_ref": con_fecha_ref[0] == real, "despues": real == "después",
                      "brier": sum((p_mod[n] - (n == real)) ** 2 for n in nombres),
                      "brier_ref": sum((p_ref.get(n, 0) - (n == real)) ** 2 for n in nombres)})
        pares += [(p_mod[n], n == real) for n in nombres]
    f = pd.DataFrame(filas)
    res = {"horas_esperando": horas_desde, "n": len(f),
           "acierta_ventana_mas_probable_pct": round(100 * f.acierta_1.mean(), 1), "referencia_mas_probable_pct": round(100 * f.acierta_1_ref.mean(), 1),
           "real_entre_las_2_mas_probables_pct": round(100 * f.acierta_2.mean(), 1), "referencia_2_mas_probables_pct": round(100 * f.acierta_2_ref.mean(), 1),
           "acierta_ventana_con_fecha_mas_probable_pct": round(100 * f.acierta_fecha.mean(), 1), "referencia_ventana_con_fecha_pct": round(100 * f.acierta_fecha_ref.mean(), 1),
           "pct_reales_despues_de_3_dias": round(100 * f.despues.mean(), 1),
           "brier": round(f.brier.mean(), 4), "brier_referencia": round(f.brier_ref.mean(), 4),
           "mejora_brier_pct": round(100 * (1 - f.brier.mean() / f.brier_ref.mean()), 1)}
    pp = pd.DataFrame(pares, columns=["prob", "paso"])
    pp["tramo"] = pd.cut(pp.prob, [-0.001, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 1.0])
    cal = pp.groupby("tramo", observed=True).agg(n=("paso", "size"), prob_media=("prob", "mean"), frecuencia_real=("paso", "mean")).reset_index()
    cal["horas_esperando"] = horas_desde
    return res, cal


# ----------------------------------------------------------------------
# 2) Censo para la reunion de camas
# ----------------------------------------------------------------------
def evaluar_censo(paq, d, tr, desde, hasta):
    momentos = [pd.Timestamp(dia) + pd.Timedelta(hours=hh) for dia in pd.date_range(desde, hasta - pd.Timedelta(days=2), freq="D") for hh in HORAS_CENSO]
    ini, cama = d.ini_est.to_numpy(), d.ini_hosp_est.to_numpy()
    # referencia historica: fraccion de los que esperan a esa hora que recibe cama en el plazo (entrenamiento, ultimos 12 meses)
    frac = {}
    for hh in HORAS_CENSO:
        for plazo in PLAZOS_CENSO:
            num = den = 0
            for dia in pd.date_range(ce.CORTE - pd.Timedelta(days=365), ce.CORTE - pd.Timedelta(days=2), freq="D"):
                t = np.datetime64(dia + pd.Timedelta(hours=hh))
                w = (ini <= t) & (cama > t)
                den += w.sum()
                num += (w & (cama <= t + np.timedelta64(plazo, "h"))).sum()
            frac[(hh, plazo)] = num / den
    filas = []
    for t in momentos:
        t64 = np.datetime64(t)
        w = np.flatnonzero((ini <= t64) & (cama > t64))
        if not len(w):
            continue
        horas = (t64 - ini[w]) / H1
        horas = np.minimum(horas, ce.MAX_H - 2)
        cur = curvas(paq, d, d.index[w], horas)
        for plazo in PLAZOS_CENSO:
            p = np.array([1 - sigue(c, S, h + plazo) for (c, S), h in zip(cur, horas)])
            real = int((cama[w] <= t64 + np.timedelta64(plazo, "h")).sum())
            filas.append({"momento": t, "hora": t.hour, "plazo_h": plazo, "en_espera": len(w), "estimado": p.sum(),
                          "banda_baja": poisson.ppf(0.1, p.sum()), "banda_alta": poisson.ppf(0.9, p.sum()),
                          "referencia": len(w) * frac[(t.hour, plazo)], "real": real})
    return pd.DataFrame(filas)


def resumir_censo(c):
    out = []
    rng = np.random.default_rng(1)
    for (hh, plazo), g in c.groupby(["hora", "plazo_h"]):
        e, r, ref = g.estimado, g.real, g.referencia
        dentro = ((r >= g.banda_baja) & (r <= g.banda_alta)).mean()
        piso = np.mean([np.abs(rng.poisson(m, 4000) - m).mean() for m in e])           # error de un estimador perfecto (solo azar)
        sem = g.set_index("momento").resample("W")[["estimado", "real"]].sum()
        out.append({"hora_del_censo": f"{hh}:00", "plazo_h": plazo, "dias": len(g), "en_espera_promedio": round(g.en_espera.mean(), 1),
                    "real_promedio": round(r.mean(), 1), "error_abs_medio": round((e - r).abs().mean(), 2), "error_pct": round(100 * (e - r).abs().sum() / r.sum(), 1),
                    "error_abs_medio_referencia": round((ref - r).abs().mean(), 2), "error_pct_referencia": round(100 * (ref - r).abs().sum() / r.sum(), 1),
                    "piso_de_ruido_error_abs": round(piso, 2), "sesgo": round((e - r).mean(), 2), "correlacion": round(np.corrcoef(e, r)[0, 1], 3),
                    "dentro_banda_80_pct": round(100 * dentro, 1), "error_pct_por_semana": round(100 * (sem.estimado - sem.real).abs().sum() / sem.real.sum(), 1)})
    return pd.DataFrame(out)


# ----------------------------------------------------------------------
# 3) Alerta de espera larga
# ----------------------------------------------------------------------
def auc(y, p):
    y, p = np.asarray(y, bool), np.asarray(p, float)
    r = pd.Series(p).rank().to_numpy()
    n1, n0 = y.sum(), (~y).sum()
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def evaluar_alerta(paq, d, te):
    sub = te[te.espera_cama_h > ALERTA_DESDE]
    cur = curvas(paq, d, sub.index, np.full(len(sub), ALERTA_DESDE))
    p = np.array([sigue(c, S, ALERTA_LIMITE) for c, S in cur])
    y = (sub.espera_cama_h > ALERTA_LIMITE).to_numpy()
    dias = (te.ini_est.max() - te.ini_est.min()).days + 1
    filas = [{"corte": "sin modelo: alertar a todos los que llevan 12 h", "alertas_por_dia": round(len(y) / dias, 2), "precision_pct": round(100 * y.mean(), 1),
              "deteccion_pct": 100.0, "auc": 0.5}]
    for corte in [0.2, 0.3, 0.4, 0.5, 0.6]:
        a = p >= corte
        filas.append({"corte": f"probabilidad >= {corte:.0%}", "alertas_por_dia": round(a.sum() / dias, 2),
                      "precision_pct": round(100 * y[a].mean(), 1) if a.any() else np.nan, "deteccion_pct": round(100 * a[y].mean(), 1), "auc": round(auc(y, p), 3)})
    # el mismo volumen de alertas que la regla de alertar a todos los que llevan 24 h (docs/CONTEXTO_TECNICO.md 6b, alerta C)
    n24 = int((sub.espera_cama_h > 24).sum())
    top = np.argsort(-p)[:n24]
    a = np.zeros(len(p), bool)
    a[top] = True
    filas.append({"corte": "las mismas alertas que 'todos los que llevan 24 h', pero a las 12 h y elegidas por el modelo", "alertas_por_dia": round(n24 / dias, 2),
                  "precision_pct": round(100 * y[a].mean(), 1), "deteccion_pct": round(100 * a[y].mean(), 1), "auc": round(auc(y, p), 3)})
    y24 = (sub.espera_cama_h[sub.espera_cama_h > 24] > ALERTA_LIMITE).to_numpy()
    filas.append({"corte": "sin modelo: alertar a todos los que llevan 24 h (12 h mas tarde)", "alertas_por_dia": round(n24 / dias, 2),
                  "precision_pct": round(100 * y24.mean(), 1), "deteccion_pct": round(100 * y24.sum() / y.sum(), 1), "auc": np.nan})
    return pd.DataFrame(filas)


def grafico(cals, censo, al):
    fig, ejes = plt.subplots(1, 3, figsize=(16, 4.6))
    c0 = cals[cals.horas_esperando == 0]
    ejes[0].plot([0, 0.5], [0, 0.5], color="#c9c8c3", lw=1)
    ejes[0].plot(c0.prob_media, c0.frecuencia_real, marker="o", color="#2a78d6")
    ejes[0].set_xlabel("probabilidad que da el estimador"); ejes[0].set_ylabel("lo que pasó"); ejes[0].set_title("Ventanas: ¿la probabilidad dice la verdad?")
    g = censo[(censo.hora == 13) & (censo.plazo_h == 24)].set_index("momento")
    s = g[["real", "estimado"]].resample("W").sum()
    ejes[1].fill_between(s.index, poisson.ppf(0.1, s.estimado), poisson.ppf(0.9, s.estimado), color="#2a78d6", alpha=0.15, lw=0,
                         label="rango del 80 % de la semana")
    ejes[1].plot(s.index, s.real, color="#52514e", lw=1.4, label="real")
    ejes[1].plot(s.index, s.estimado, color="#2a78d6", lw=1.6, label="estimado")
    ejes[1].set_title("Censo de las 13:00: cuántos tienen cama en 24 h (por semana)"); ejes[1].legend(frameon=False, fontsize=8); ejes[1].set_ylim(0)
    ejes[1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m-%Y")); ejes[1].tick_params(axis="x", labelrotation=30)
    a = al[al.corte.str.startswith("probabilidad")]
    ejes[2].plot(a.alertas_por_dia, a.precision_pct, marker="o", color="#eb6834")
    for _, r in a.iterrows():
        ejes[2].annotate(r.corte.replace("probabilidad >= ", ""), (r.alertas_por_dia, r.precision_pct), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ejes[2].axhline(al.iloc[0].precision_pct, color="#c9c8c3", ls="--", lw=1)
    ejes[2].set_xlabel("alertas por día"); ejes[2].set_ylabel("% de alertas que acierta"); ejes[2].set_title("Alerta a las 12 h: seguirá sin cama a las 48 h")
    for ax in ejes:
        ax.grid(color="#e5e4df")
    fig.text(0.01, 0.01, "Prueba con jul-2025 a 9-abr-2026 (entrenamiento feb-2023 a jun-2025). Línea gris punteada: alertar sin modelo. Fuente: src/utilidad_estimador.py",
             fontsize=8, color="#52514e")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(ce.GRAF / "utilidad_estimador.png", dpi=150)


if __name__ == "__main__":
    if "--solo-grafico" in sys.argv:                                     # rehace el grafico desde las tablas ya calculadas
        grafico(pd.read_csv(ce.TABLAS / "utilidad_ventanas_calibracion.csv"), pd.read_csv(ce.TABLAS / "utilidad_censo_diario.csv", parse_dates=["momento"]),
                pd.read_csv(ce.TABLAS / "utilidad_alerta.csv"))
        sys.exit()
    pd.set_option("display.width", 230)
    ce.TABLAS.mkdir(parents=True, exist_ok=True)
    d, h, rejilla, estado = ce.preparar()
    curvas.rejilla, curvas.estado = rejilla, estado
    paq = etr.entrenar_paquete(d, rejilla, estado, hasta=ce.CORTE)             # solo con el entrenamiento
    tr, te = d[d.ini_est < ce.CORTE], d[d.ini_est >= ce.CORTE]

    res_v, cals = [], []
    for hd in [0, 6]:
        r, cal = evaluar_ventanas(paq, d, te, tr, hd)
        res_v.append(r); cals.append(cal)
        print(r, flush=True)
    res_v, cals = pd.DataFrame(res_v), pd.concat(cals)
    res_v.to_csv(ce.TABLAS / "utilidad_ventanas.csv", index=False)
    cals.to_csv(ce.TABLAS / "utilidad_ventanas_calibracion.csv", index=False)
    print("\nCALIBRACION DE LAS VENTANAS\n" + cals.round(3).to_string(index=False), flush=True)

    censo = evaluar_censo(paq, d, tr, ce.CORTE, ce.HASTA)
    censo.to_csv(ce.TABLAS / "utilidad_censo_diario.csv", index=False)
    rc = resumir_censo(censo)
    rc.to_csv(ce.TABLAS / "utilidad_censo.csv", index=False)
    print("\nCENSO PARA LA REUNION DE CAMAS\n" + rc.to_string(index=False), flush=True)

    al = evaluar_alerta(paq, d, te)
    al.to_csv(ce.TABLAS / "utilidad_alerta.csv", index=False)
    print("\nALERTA DE ESPERA LARGA (a las 12 h, seguir sin cama a las 48 h)\n" + al.to_string(index=False), flush=True)

    grafico(cals, censo, al)
