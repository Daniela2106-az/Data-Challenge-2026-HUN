"""
pronostico_espera_sistema.py  -  version 1 (9-nov-2026)
Daniela (9-nov): ya predecimos la saturacion de camas y los ingresos, pero NO el tiempo de espera. ¿Se puede predecir la espera con lo que sabemos del hospital?

CAMINO 3 - ¿cuanto de la espera se predice con la HORA y el DIA en que llega el paciente, y cuanto suma saber la saturacion?
  Se entrenan modelos de percentiles (25, 50, 75 y 90) de la espera de cama con las llegadas de feb-2023 a jun-2025 y se prueban con jul-2025 a 9-abr-2026
  (la prueba no se usa para elegir nada: hiperparametros fijos). Se compara con "el mismo rango para todos" (referencia general):
    F1 calendario            : hora de llegada, dia de la semana, festivo
    F2 + saturacion al llegar: ocupacion y cola de su zona en la hora de llegada (el valor REAL; si se pronosticara seria peor, asi que es un techo)
    F3 + paciente            : edad, sexo y tipo de visita (equivale a "al llegar" del estimador A6 sin historial ni recorrido)

CAMINO 1 - la cola y la espera del sistema
  a) Pronostico de la COLA (pacientes que ya llegaron y aun no tienen cama; solo los que luego se hospitalizan) a 6, 12 y 24 h con un modelo de flujo
     (cola ahora + llegadas esperadas - camas asignadas esperadas, por hora de la semana) frente a "lo mismo que ahora" (persistencia) y a un modelo lineal.
  b) Espera esperada por la ley de Little: espera media = cola / llegadas por hora.
  c) Semanal: ¿la ocupacion o la cola de la semana explican la espera mediana de la semana? (R2 y correlacion, con el efecto del ano aparte).

SALIDAS (HUN_TABLAS): espera_camino3.csv, espera_camino1_cola.csv, espera_camino1_semanal.csv, espera_sistema_resumen.txt
ENTRADAS tabla_episodios.parquet (HUN_PROCESADOS); usa saturacion_y_espera.py para la cola y la ocupacion hora por hora.
COMO CORRERLO  python3 src/pronostico_espera_sistema.py   (1-3 min)
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import saturacion_y_espera as se  # noqa: E402
import comparar_estimadores as ce  # noqa: E402

CORTE = pd.Timestamp("2025-07-01")
Q = [0.25, 0.5, 0.75, 0.9]
LINEAS = []


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def modelo_q(q):
    return HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200, random_state=7)


def camino3(p):
    decir("CAMINO 3. ¿CUANTO DE LA ESPERA SE PREDICE AL LLEGAR? (entrenamiento feb-2023 a jun-2025; prueba jul-2025 a 9-abr-2026)")
    p = p.copy()
    p["festivo_n"] = p.festivo.astype(int)
    p["zona_n"] = (p.zona == "ninos").astype(int)
    p["sexo_n"] = (p.sexo == "Mujer").astype(int)
    p["tipo_n"] = p.tipo_visita.astype("category").cat.codes
    p["edad_n"] = p.edad
    conj = {"F1 calendario": ["hora_llegada", "dia_semana", "festivo_n"],
            "F2 + saturacion al llegar": ["hora_llegada", "dia_semana", "festivo_n", "zona_n", "ocup_zona_llegada", "cola_zona_llegada"],
            "F3 + paciente": ["hora_llegada", "dia_semana", "festivo_n", "zona_n", "ocup_zona_llegada", "cola_zona_llegada", "edad_n", "sexo_n", "tipo_n"]}
    tr, te = p[p.ini_est < CORTE], p[p.ini_est >= CORTE]
    y = te.espera_cama_h.to_numpy()
    general = np.tile(np.quantile(tr.espera_cama_h, Q), (len(te), 1))
    l_gen = ce.perdida_por_caso(y, general)
    semana = te.ini_est.dt.to_period("W").astype(str).to_numpy()
    decir(f"  entrenamiento {len(tr):,} estancias | prueba {len(te):,}")
    filas = []
    for nombre, cols in conj.items():
        pred = np.column_stack([modelo_q(q).fit(tr[cols], tr.espera_cama_h).predict(te[cols]) for q in Q])
        pred = np.maximum.accumulate(np.maximum(pred, 0), axis=1)                    # que los percentiles no se crucen
        l = ce.perdida_por_caso(y, pred)
        lo, hi = ce.intervalo_mejora(semana, l, l_gen)
        fila = {"modelo": nombre, "n_prueba": len(te), "mejora_vs_general_pct": round(100 * (1 - l.mean() / l_gen.mean()), 1), "ic95_bajo": round(lo, 1), "ic95_alto": round(hi, 1),
                "error_abs_mediana_h": round(float(np.mean(np.abs(y - pred[:, 1]))), 1)}
        for j, q in enumerate(Q):
            fila[f"pct_debajo_p{int(q * 100)}"] = round(100 * float(np.mean(y <= pred[:, j])), 1)
        filas.append(fila)
    filas.insert(0, {"modelo": "referencia: el mismo rango para todos", "n_prueba": len(te), "mejora_vs_general_pct": 0.0, "ic95_bajo": 0.0, "ic95_alto": 0.0,
                     "error_abs_mediana_h": round(float(np.mean(np.abs(y - general[:, 1]))), 1), **{f"pct_debajo_p{int(q * 100)}": round(100 * float(np.mean(y <= general[:, j])), 1) for j, q in enumerate(Q)}})
    t = pd.DataFrame(filas)
    decir(t.to_string(index=False))
    t.to_csv(se.TABLAS / "espera_camino3.csv", index=False)
    decir("  Referencia del estimador A6 (docs/estimador_tiempos.md): al llegar mejora 8,6-9,2 %, con historial y recorrido en urgencias.")
    return t


def camino1_cola(h, est):
    decir("\nCAMINO 1a. PRONOSTICO DE LA COLA (pacientes que ya llegaron y aun no tienen cama) A 6, 12 Y 24 H")
    r = est.index
    cola = est.cola_total
    llegan = pd.Series(1, index=h.ini_est.dt.floor("h")).groupby(level=0).sum().reindex(r, fill_value=0)
    ingresan = pd.Series(1, index=h.ini_hosp_est.dt.floor("h")).groupby(level=0).sum().reindex(r, fill_value=0)
    how = (r.dayofweek * 24 + r.hour).to_numpy()
    entren = r < CORTE
    media_ll = pd.Series(llegan.to_numpy()[entren]).groupby(how[entren]).mean().reindex(range(168)).to_numpy()
    media_in = pd.Series(ingresan.to_numpy()[entren]).groupby(how[entren]).mean().reindex(range(168)).to_numpy()
    media_cola = pd.Series(cola.to_numpy()[entren]).groupby(how[entren]).mean().reindex(range(168)).to_numpy()
    c = cola.to_numpy().astype(float)
    filas = []
    for hor in (6, 12, 24):
        t0 = np.arange(len(r) - hor)
        ok = ~entren[t0 + hor] & (est.index[t0] >= CORTE)
        t0 = t0[ok]
        real = c[t0 + hor]
        flujo = np.array([c[t] + sum(media_ll[(how[t] + k) % 168] - media_in[(how[t] + k) % 168] for k in range(1, hor + 1)) for t in t0]).clip(min=0)
        pers = c[t0]
        # lineal entrenado con el pasado: cola(t+h) ~ cola(t) + cola tipica de la hora destino
        ti = np.arange(len(r) - hor)
        ti = ti[entren[ti + hor]]
        X = np.column_stack([np.ones(len(ti)), c[ti], media_cola[(how[ti] + hor) % 168]])
        beta = np.linalg.lstsq(X, c[ti + hor], rcond=None)[0]
        lin = np.column_stack([np.ones(len(t0)), c[t0], media_cola[(how[t0] + hor) % 168]]) @ beta
        tipica = media_cola[(how[t0] + hor) % 168]
        for nombre, pr in [("persistencia (lo mismo que ahora)", pers), ("cola tipica de esa hora de la semana", tipica), ("modelo de flujo (llegadas - camas asignadas)", flujo), ("lineal: cola actual y cola tipica", lin)]:
            filas.append({"horizonte_h": hor, "metodo": nombre, "n": len(t0), "mae_pacientes": round(float(np.mean(np.abs(real - pr))), 2), "sesgo": round(float(np.mean(pr - real)), 2)})
    t = pd.DataFrame(filas)
    base = t[t.metodo.str.startswith("persistencia")].set_index("horizonte_h").mae_pacientes
    t["mejora_vs_persistencia_pct"] = [round(100 * (1 - m / base[hh]), 1) for hh, m in zip(t.horizonte_h, t.mae_pacientes)]
    decir(f"  cola media en la prueba: {float(np.mean(c[est.index >= CORTE])):.1f} pacientes (desviacion {float(np.std(c[est.index >= CORTE])):.1f})")
    decir(t.to_string(index=False))
    t.to_csv(se.TABLAS / "espera_camino1_cola.csv", index=False)
    lam = float(media_ll.mean())
    decir(f"\nCAMINO 1b. LEY DE LITTLE: llegadas que se hospitalizan {lam:.2f} por hora; cola media {float(c.mean()):.1f} -> espera MEDIA esperada {c.mean() / lam:.1f} h "
          f"(la espera media real del periodo: {float(h[(h.ini_est >= se.DESDE) & (h.ini_est < se.HASTA)].espera_cama_h.mean()):.1f} h; la mediana es menor por la cola larga)")
    return t


def camino1_semanal(p, est):
    decir("\nCAMINO 1c. SEMANAL: ¿LA OCUPACION O LA COLA DE LA SEMANA EXPLICAN LA ESPERA DE LA SEMANA?")
    sem = est.groupby(est.index.to_period("W")).agg(ocup=("ocup_total", "mean"), cola=("cola_total", "mean"))
    w = p.groupby(p.ini_est.dt.to_period("W")).agg(n=("espera_cama_h", "size"), mediana=("espera_cama_h", "median"), media=("espera_cama_h", "mean"), p90=("espera_cama_h", lambda v: v.quantile(.9))).join(sem).dropna()
    w = w[w.n >= 60]
    w["anio"] = [str(x.start_time.year) for x in w.index]
    decir(f"  {len(w)} semanas con al menos 60 estancias")
    filas = []
    for medida in ["mediana", "media", "p90"]:
        for x in ["ocup", "cola"]:
            rho = float(w[[x, medida]].corr(method="spearman").iloc[0, 1])
            d = w[[x, medida]] - w.groupby("anio")[[x, medida]].transform("mean")                   # sin el efecto del ano
            rho_d = float(d.corr(method="spearman").iloc[0, 1])
            r2 = float(np.corrcoef(w[x], w[medida])[0, 1] ** 2)
            filas.append({"espera": medida, "saturacion_de_la_semana": x, "spearman": round(rho, 2), "spearman_sin_efecto_ano": round(rho_d, 2), "r2": round(r2, 2)})
    t = pd.DataFrame(filas)
    decir(t.to_string(index=False))
    t.to_csv(se.TABLAS / "espera_camino1_semanal.csv", index=False)
    return t


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    se.TABLAS.mkdir(parents=True, exist_ok=True)
    h = se.cargar()
    est = se.estado_por_hora(h)
    p = se.pacientes(h, est)
    decir(f"PRONOSTICO DE LA ESPERA | {len(p):,} estancias con espera medida")
    camino3(p)
    camino1_cola(h, est)
    camino1_semanal(p, est)
    (se.TABLAS / "espera_sistema_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")
