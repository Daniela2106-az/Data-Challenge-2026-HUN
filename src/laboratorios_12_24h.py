"""
laboratorios_12_24h.py  -  version 1 (8-nov-2026)

Pregunta: para quien lleva 12 o 24 h esperando cama, ¿ayudan los laboratorios tomados hasta ESE momento (no solo los de las primeras 6 h)?

Datos: sev_hemograma_24h_*.csv y sev_quimica_24h_*.csv en HUN_CRUDOS (consultas de sql/severidad_labs_12_24h.sql). Traen los valores acumulados
hasta las 12 h (columnas _12h) y hasta las 24 h (_24h) desde la primera etapa de la visita. Mismos cortes que src/severidad_labs.py
(comparar_estimadores.BANDERAS_LAB) y misma regla de copias (solo copias de la misma persona) y de estancia (lo mas extremo entre sus registros).

Prueba (sin fuga de informacion): a las H horas solo se usan laboratorios tomados antes de H. Para eso se entrena un modelo por momento ("landmark",
features fijadas en H) y se compara en la misma prueba (entrena hasta jun-2025, prueba jul-2025 a 9-abr-2026, con peso a lo reciente):
  - estimador actual: el modelo final de comparar_estimadores (banderas de 6 h);
  - landmark con banderas de 6 h (mismo tipo de modelo, para separar el efecto del modelo del de los laboratorios);
  - landmark con banderas hasta H (12 h a las 12 h; 24 h a las 24 h; a las 48 h, las de 24 h).
Intervalos del 95 % de la diferencia con bootstrap por semanas (ce.intervalo_mejora).

Salida: HUN_TABLAS/laboratorios_12_24h.csv. Correr: python3 src/laboratorios_12_24h.py (~5 min).
"""
import sys
import warnings

import numpy as np
import pandas as pd

import comparar_estimadores as ce

warnings.filterwarnings("ignore")
VIDA = 182
VALORES = ["leuc_max", "leuc_min", "hb_min", "creat_max", "bun_max", "lactato_max", "k_max", "na_max", "na_min", "troponina_max", "pcr_max"]
AGG = {c: ("min" if c.endswith("_min") else "max") for c in VALORES}


def banderas_hasta(t, ventana):
    """Banderas por estancia con los laboratorios acumulados hasta 'ventana' ('12h' o '24h'); columnas <bandera>_<ventana>."""
    hem, qui = sorted(ce.CRUDOS.glob("sev_hemograma_24h_*.csv")), sorted(ce.CRUDOS.glob("sev_quimica_24h_*.csv"))
    if not hem or not qui:
        sys.exit("Faltan sev_hemograma_24h_*.csv y sev_quimica_24h_*.csv en HUN_CRUDOS (sql/severidad_labs_12_24h.sql).")
    s = pd.concat([pd.read_csv(f) for f in hem]).merge(pd.concat([pd.read_csv(f) for f in qui]), on="visit_occurrence_id", how="outer")
    s = s[["visit_occurrence_id"] + [f"{c}_{ventana}" for c in VALORES]].rename(columns={f"{c}_{ventana}": c for c in VALORES})
    s = s.dropna(subset=VALORES, how="all")
    cop = pd.read_csv(ce.PROC / "copias.csv", usecols=["visit_occurrence_id", "raiz_id", "misma_persona"])
    cop = cop[cop.misma_persona]
    s["visit_occurrence_id"] = s.visit_occurrence_id.map(cop.set_index("visit_occurrence_id").raiz_id).fillna(s.visit_occurrence_id).astype("int64")
    s = s.groupby("visit_occurrence_id").agg(AGG).reset_index()
    reg = t.loc[t.hospitalizado & (t.estancia_id >= 0) & (t.episodio == 0), ["visit_occurrence_id", "estancia_id"]]
    e = reg.merge(s, on="visit_occurrence_id").groupby("estancia_id").agg(AGG)
    e = ce.banderas_desde_valores(e).assign(con_laboratorio_6h=1.0)
    return e.rename(columns={c: f"{c}_{ventana}" for c in ce.LAB})


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 220)
    d, h, rejilla, estado = ce.preparar()
    t = pd.read_parquet(ce.PROC / "tabla_episodios.parquet", columns=["visit_occurrence_id", "episodio", "estancia_id", "hospitalizado"])
    LABV = {}
    for v in ["12h", "24h"]:
        e = banderas_hasta(t, v)
        d = d.merge(e, left_on="estancia_id", right_index=True, how="left")
        LABV[v] = list(e.columns)
        d[LABV[v]] = d[LABV[v]].fillna(0.0)
        print(f"estancias con algun laboratorio hasta las {v}: {d[f'con_laboratorio_6h_{v}'].mean():.1%} (hasta 6 h: {d.con_laboratorio_6h.mean():.1%})")
    base = ce.COLS_M1_BASE + ce.HIST
    tr, te = d[d.ini_est < ce.CORTE].reset_index(drop=True), d[d.ini_est >= ce.CORTE].reset_index(drop=True)
    filas = []
    for desde, v in [(12, "12h"), (24, "24h"), (48, "24h")]:
        sub = te[te.espera_cama_h > desde].reset_index(drop=True)
        y = np.minimum(sub.espera_cama_h.to_numpy() - desde, ce.MAX_H)
        sem = sub.ini_est.dt.to_period("W").astype(str).to_numpy()
        lg = ce.perdida_por_caso(y, ce.referencias(tr, sub, desde)[0])
        nuevo = sub[f"con_laboratorio_6h_{v}"].to_numpy() - sub.con_laboratorio_6h.to_numpy()
        variantes = {
            "estimador actual (banderas de 6 h)": ce.entrenar_m1(tr, rejilla, estado, ce.cols_finales(desde), vida_media_dias=VIDA),
            "landmark, banderas de 6 h": ce.entrenar_landmark(tr, rejilla, estado, desde, base + ce.LAB, vida_media_dias=VIDA),
            f"landmark, banderas hasta {v}": ce.entrenar_landmark(tr, rejilla, estado, desde, base + LABV[v], vida_media_dias=VIDA),
            f"landmark, banderas de 6 h y hasta {v}": ce.entrenar_landmark(tr, rejilla, estado, desde, base + ce.LAB + LABV[v], vida_media_dias=VIDA),
        }
        perdidas = {}
        for nombre, m in variantes.items():
            p = ce.predecir_m1(m, sub, rejilla, estado, desde)
            perdidas[nombre] = lp = ce.perdida_por_caso(y, p)
            fila = {"horas_esperando": desde, "variante": nombre, "n": len(sub), "con_lab_nuevo_pct": round(100 * np.mean(nuevo > 0), 1),
                    "mejora_vs_general_pct": round(100 * (1 - lp.mean() / lg.mean()), 1), "error_abs_mediana_h": round(np.mean(np.abs(y - p[:, 1])), 1),
                    **{f"pct_debajo_p{int(q * 100)}": round(100 * np.mean(y <= p[:, j]), 1) for j, q in enumerate(ce.Q)}}
            if nombre != "estimador actual (banderas de 6 h)":
                la = perdidas["estimador actual (banderas de 6 h)"]
                lo, hi = ce.intervalo_mejora(sem, lp, la)
                fila.update(vs_actual_pct=round(100 * (1 - lp.mean() / la.mean()), 1), ic95_vs_actual=f"{lo:.1f} a {hi:.1f}")
            filas.append(fila)
        print(pd.DataFrame([f for f in filas if f["horas_esperando"] == desde]).to_string(index=False), "\n", flush=True)
    pd.DataFrame(filas).to_csv(ce.TABLAS / "laboratorios_12_24h.csv", index=False)
