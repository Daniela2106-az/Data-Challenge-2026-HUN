"""
ventana_entrenamiento.py  -  version 1 (7-nov-2026)
Tarea A6: ¿estimar la espera de ahora con datos de 2023 a 2025 es un problema? El hospital cambio (la ocupacion de adultos paso del 88 % al 101 % y el
percentil 90 de la espera de 61 a 81 h), asi que un modelo entrenado sobre todo con lo antiguo puede quedarse atras.

QUE COMPARA (misma prueba que comparar_estimadores.py: jul-2025 a 9-abr-2026; al llegar y despues de 3, 6, 12 y 24 h; estimador final)
  1. La espera por semestre de llegada (cuanto cambio).
  2. Formas de entrenar: todo feb-2023 a jun-2025 (la actual); solo los ultimos 12 o 6 meses; todo con mas peso a lo reciente (la mitad del peso cada 6 o
     12 meses hacia atras); y REENTRENAR CADA MES con todo lo conocido hasta ese mes (sin y con peso a lo reciente). En el reentrenamiento mensual solo
     entran las estancias que ya tenian cama antes de empezar el mes y que llegaron al menos 14 dias antes (lo que de verdad se sabria en ese momento).
  3. Diferencia pareada entre el reentrenamiento mensual con peso a lo reciente y el modelo fijo, con intervalo del 95 % (bootstrap por semanas).

ENTRADAS  tabla_episodios.parquet (HUN_PROCESADOS); visit_detail.csv y procedimientos_por_estancia.csv (HUN_CRUDOS)
SALIDAS   en HUN_TABLAS: ventana_entrenamiento_espera_por_semestre.csv, ventana_entrenamiento.csv, ventana_entrenamiento_pareado.csv
COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... HUN_CRUDOS=... python3 src/ventana_entrenamiento.py   (~10 min)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402

VIDA_MEDIA_DIAS = 182          # la usada por el estimador final (estimador_tiempo_restante.py)
DIAS_SIN_USAR = 14             # en el reentrenamiento mensual, las llegadas de los ultimos 14 dias aun no tienen su espera completa


def modelo(d, rejilla, estado, tr, desde, vida=None):
    if desde < ce.HORAS_RECORRIDO:
        return ce.entrenar_landmark(tr, rejilla, estado, desde, vida_media_dias=vida)
    return ce.entrenar_m1(tr, rejilla, estado, ce.cols_finales(desde), vida_media_dias=vida)


def reentreno_mensual(d, rejilla, estado, sub, desde, vida):
    p = np.full((len(sub), 4), np.nan)
    for mes in sorted(sub.ini_est.dt.to_period("M").unique()):
        ini_mes = mes.to_timestamp()
        m_ = (sub.ini_est.dt.to_period("M") == mes).to_numpy()
        tr = d[(d.ini_est < ini_mes - pd.Timedelta(days=DIAS_SIN_USAR)) & (d.ini_hosp_est < ini_mes)].reset_index(drop=True)
        p[m_] = ce.predecir_m1(modelo(d, rejilla, estado, tr, desde, vida), sub[m_].reset_index(drop=True), rejilla, estado, desde)
    return p


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    d, h, rejilla, estado = ce.preparar()
    sem_ = d.ini_est.dt.year.astype(str) + "-S" + ((d.ini_est.dt.month > 6) + 1).astype(str)
    por_sem = d.groupby(sem_).espera_cama_h.describe(percentiles=[.25, .5, .75, .9])[["count", "25%", "50%", "75%", "90%"]].round(1)
    por_sem.to_csv(ce.TABLAS / "ventana_entrenamiento_espera_por_semestre.csv", index_label="semestre")
    print("ESPERA POR SEMESTRE DE LLEGADA\n" + por_sem.to_string())

    estrategias = {"todo feb-2023 a jun-2025 (modelo fijo)": ("2023-02-01", None), "ultimos 12 meses": ("2024-07-01", None),
                   "ultimos 6 meses": ("2025-01-01", None), "todo, peso a lo reciente (vida media 6 meses)": ("2023-02-01", 182),
                   "todo, peso a lo reciente (vida media 12 meses)": ("2023-02-01", 365)}
    te_all = d[d.ini_est >= ce.CORTE].reset_index(drop=True)
    tr_full = d[d.ini_est < ce.CORTE].reset_index(drop=True)
    filas, pares = [], []
    for desde in [0, 3, 6, 12, 24]:
        sub = te_all[te_all.espera_cama_h > desde].reset_index(drop=True)
        y = np.minimum(sub.espera_cama_h.to_numpy() - desde, ce.MAX_H)
        sem = sub.ini_est.dt.to_period("W").astype(str).to_numpy()
        lg = ce.perdida_por_caso(y, ce.referencias(tr_full, sub, desde)[0])
        preds = {}
        for nombre, (desde_tr, vida) in estrategias.items():
            tr = d[(d.ini_est >= desde_tr) & (d.ini_est < ce.CORTE)].reset_index(drop=True)
            preds[nombre] = ce.predecir_m1(modelo(d, rejilla, estado, tr, desde, vida), sub, rejilla, estado, desde)
        preds["reentreno mensual, todo lo anterior"] = reentreno_mensual(d, rejilla, estado, sub, desde, None)
        preds["reentreno mensual, peso a lo reciente (6 meses)"] = reentreno_mensual(d, rejilla, estado, sub, desde, VIDA_MEDIA_DIAS)
        for nombre, p in preds.items():
            lp = ce.perdida_por_caso(y, p)
            lo, hi = ce.intervalo_mejora(sem, lp, lg)
            filas.append({"horas_esperando": desde, "estrategia": nombre, "mejora_vs_general_pct": round(100 * (1 - lp.mean() / lg.mean()), 1),
                          "ic95_bajo": round(lo, 1), "ic95_alto": round(hi, 1), "error_abs_mediana_h": round(np.mean(np.abs(y - p[:, 1])), 1),
                          **{f"pct_debajo_p{int(q * 100)}": round(100 * np.mean(y <= p[:, j]), 1) for j, q in enumerate(ce.Q)}})
        lf = ce.perdida_por_caso(y, preds["todo feb-2023 a jun-2025 (modelo fijo)"])
        lm = ce.perdida_por_caso(y, preds["reentreno mensual, peso a lo reciente (6 meses)"])
        lo, hi = ce.intervalo_mejora(sem, lm, lf)
        pares.append({"horas_esperando": desde, "mejora_del_mensual_sobre_el_fijo_pct": round(100 * (1 - lm.mean() / lf.mean()), 1),
                      "ic95_bajo": round(lo, 1), "ic95_alto": round(hi, 1)})
        print(pd.DataFrame([f for f in filas if f["horas_esperando"] == desde]).to_string(index=False), "\n", pares[-1], flush=True)
    pd.DataFrame(filas).to_csv(ce.TABLAS / "ventana_entrenamiento.csv", index=False)
    pd.DataFrame(pares).to_csv(ce.TABLAS / "ventana_entrenamiento_pareado.csv", index=False)
