"""
procedimientos_escenario.py  -  version 1 (7-nov-2026)
Tarea A6: recalcula los modelos con la informacion de los procedimientos (procedimientos_por_estancia.csv, extraido por Daniela para A2b).

QUE MIDE
  1. Descripcion: espera de cama segun el servicio que atendio al paciente y segun las marcas de gravedad (comparar_estimadores.procedimientos()).
  2. Escenario: ¿cuanto mejoraria la estimacion si al llegar se supiera la gravedad y el servicio? Se recalculan los modelos que usan datos del paciente:
       - el estimador final (tiempo restante: un modelo por momento antes de 12 h, solo historial despues),
       - el modelo de cuantiles al llegar (M2),
       - la tabla de perfiles (agregando el servicio como primera dimension),
     con gravedad, con servicio, con ambos, con el grupo de diagnostico y con todo junto.
     Los modelos de cola y las dos series no usan datos del paciente: los procedimientos no les cambian nada.

OJO: los procedimientos NO tienen fecha. Una cesarea, una transfusion o el ingreso a UCI pueden ocurrir despues de recibir la cama, asi que el escenario es
     una cota OPTIMISTA de lo que daria conocer la gravedad y el servicio al llegar, no un modelo que se pueda usar hoy. El 45 % de las estancias no tiene
     ninguno de los 157 procedimientos del archivo (solo trae los que aparecen en 100 estancias o mas, y algunos menos frecuentes).

LA PRUEBA  la misma de comparar_estimadores.py (entrenamiento feb-2023 a jun-2025, prueba jul-2025 a 9-abr-2026), al llegar y despues de 3, 6, 12 y 24 h.
ENTRADAS  tabla_episodios.parquet (HUN_PROCESADOS); visit_detail.csv y procedimientos_por_estancia.csv (HUN_CRUDOS)
SALIDAS   en HUN_TABLAS: procedimientos_espera_por_grupo.csv, procedimientos_escenario.csv
COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... HUN_CRUDOS=... python3 src/procedimientos_escenario.py   (~5 min)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402
import estimador_tiempos as et  # noqa: E402

NOMBRES_SERV = list(ce.SERVICIOS) + ["ninguno de esos servicios"]


def describir(d):
    filas = []
    base = d.espera_cama_h
    filas.append({"grupo": "todas las estancias", "estancias": len(d), "pct": 100.0, "espera_mediana_h": round(base.median(), 1), "espera_p90_h": round(base.quantile(.9), 1)})
    for i, s in enumerate(NOMBRES_SERV):
        g = d.loc[d.servicio_cod == i, "espera_cama_h"]
        filas.append({"grupo": f"servicio: {s}", "estancias": len(g), "pct": round(100 * len(g) / len(d), 1), "espera_mediana_h": round(g.median(), 1), "espera_p90_h": round(g.quantile(.9), 1)})
    for g_ in list(ce.GRAVEDAD):
        g = d.loc[d[g_] == 1, "espera_cama_h"]
        filas.append({"grupo": f"gravedad: {g_}", "estancias": len(g), "pct": round(100 * len(g) / len(d), 1), "espera_mediana_h": round(g.median(), 1), "espera_p90_h": round(g.quantile(.9), 1)})
    for k in [0, 1, 2]:
        g = d.loc[d.n_marcas_gravedad.clip(upper=2) == k, "espera_cama_h"]
        filas.append({"grupo": f"marcas de gravedad: {k}{'+' if k == 2 else ''}", "estancias": len(g), "pct": round(100 * len(g) / len(d), 1),
                      "espera_mediana_h": round(g.median(), 1), "espera_p90_h": round(g.quantile(.9), 1)})
    return pd.DataFrame(filas)


def perfiles_con_servicio(tr, te, desde):
    dims = et.DIMS
    try:
        et.DIMS = ["servicio", "bloque_hora", "grupo_edad", "tipo_visita"]     # el servicio va primero: es lo ultimo que se quita si faltan casos
        return ce.referencias(tr, te, desde)[1]
    finally:
        et.DIMS = dims


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    d, h, rejilla, estado = ce.preparar()
    if "servicio_cod" not in d:
        sys.exit("Falta procedimientos_por_estancia.csv en HUN_CRUDOS")
    grupos = sorted(d.categoria_dx.dropna().unique())
    d["dx_cod"] = d.categoria_dx.map({g: i for i, g in enumerate(grupos)})
    d["servicio"] = pd.Series(NOMBRES_SERV)[d.servicio_cod.to_numpy()].to_numpy()

    desc = describir(d)
    desc.to_csv(ce.TABLAS / "procedimientos_espera_por_grupo.csv", index=False)
    print("ESPERA DE CAMA POR SERVICIO Y GRAVEDAD (procedimientos sin fecha: descripcion, no causa)\n" + desc.to_string(index=False))

    extras = {"sin procedimientos (estimador final)": [], "+ gravedad": ce.PROC_GRAV, "+ servicio": ce.PROC_SERV,
              "+ gravedad y servicio": ce.PROC_GRAV + ce.PROC_SERV, "+ grupo de diagnostico": ["dx_cod"],
              "+ todo (gravedad, servicio y diagnostico)": ce.PROC_GRAV + ce.PROC_SERV + ["dx_cod"]}
    tr, te = d[d.ini_est < ce.CORTE].reset_index(drop=True), d[d.ini_est >= ce.CORTE].reset_index(drop=True)
    filas = []
    for desde in [0, 3, 6, 12, 24]:
        sub = te[te.espera_cama_h > desde].reset_index(drop=True)
        y = np.minimum(sub.espera_cama_h.to_numpy() - desde, ce.MAX_H)
        general, perfil = ce.referencias(tr, sub, desde)
        lg = ce.perdida_por_caso(y, general)
        sem = sub.ini_est.dt.to_period("W").astype(str).to_numpy()
        preds = {"tabla de perfiles": perfil, "tabla de perfiles + servicio": perfiles_con_servicio(tr, sub, desde)}
        for nombre, extra in extras.items():
            if desde < ce.HORAS_RECORRIDO:
                m = ce.entrenar_landmark(tr, rejilla, estado, desde, ce.COLS_M1_FINAL + extra)
            else:
                m = ce.entrenar_m1(tr, rejilla, estado, ce.COLS_M1_BASE + ce.HIST + extra)
            preds[f"estimador final {nombre}"] = ce.predecir_m1(m, sub, rejilla, estado, desde)
        if desde == 0:
            for nombre, extra in [("M2 al llegar", []), ("M2 al llegar + gravedad y servicio", ce.PROC_GRAV + ce.PROC_SERV)]:
                cols = [c for c in ce.COLS_M2 if c != "cola0"] + extra
                Xtr = ce.matriz_m2(tr, rejilla, estado).join(tr[extra]) if extra else ce.matriz_m2(tr, rejilla, estado)
                Xte = ce.matriz_m2(sub, rejilla, estado).join(sub[extra]) if extra else ce.matriz_m2(sub, rejilla, estado)
                ytr = np.log1p(tr.espera_cama_h.to_numpy())
                pred = np.column_stack([np.expm1(ce.HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                                                                   min_samples_leaf=100, random_state=ce.SEMILLA).fit(Xtr[cols], ytr).predict(Xte[cols]))
                                        for q in ce.Q])
                preds[nombre] = np.maximum.accumulate(np.clip(pred, 0, None), axis=1)
        for nombre, p in preds.items():
            lp = ce.perdida_por_caso(y, p)
            lo, hi = ce.intervalo_mejora(sem, lp, lg)
            filas.append({"horas_esperando": desde, "metodo": nombre, "n_prueba": len(y), "mejora_vs_general_pct": round(100 * (1 - lp.mean() / lg.mean()), 1),
                          "ic95_bajo": round(lo, 1), "ic95_alto": round(hi, 1), "error_abs_mediana_h": round(np.mean(np.abs(y - p[:, 1])), 1),
                          **{f"pct_debajo_p{int(q * 100)}": round(100 * np.mean(y <= p[:, j]), 1) for j, q in enumerate(ce.Q)}})
        print(pd.DataFrame([f for f in filas if f["horas_esperando"] == desde]).to_string(index=False), flush=True)
    pd.DataFrame(filas).to_csv(ce.TABLAS / "procedimientos_escenario.csv", index=False)
