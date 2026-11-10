"""
prueba_ultima_etapa.py  -  version 1 (9-nov-2026)
Camino 3 de Daniela (9-nov): ¿mejora el estimador de tiempo restante (A6) si se le suma lo que ahora sabemos de las ETAPAS TU y los laboratorios con hora?

QUE SE SABE (docs/caracterizacion_etapas_tu.md): la espera larga esta en la ULTIMA etapa TU, que es una etapa silenciosa (casi sin laboratorios); cada etapa nueva arranca con
una rafaga de tomas. El estimador ya usa el tiempo desde el ultimo cambio de etapa (horas_desde_ultimo_inicio), el numero de etapas y la hora del reloj. Lo que NO usa:
  EXTRA = laboratorios dentro de la etapa actual y recencia de la ultima toma, todo conocido en el momento de la consulta c (horas desde la llegada):
    tomas_hasta_c         : tomas de laboratorio desde la llegada hasta c
    h_desde_ultima_toma   : horas desde la ultima toma hasta c (vacio si no hubo ninguna)
    tomas_ultimas_3h      : tomas en las 3 h anteriores a c
    tomas_etapa_actual    : tomas desde que empezo la etapa TU en la que esta el paciente en c
    dx_hasta_c            : diagnosticos distintos registrados hasta c
  OJO: no se sabe en tiempo real cual sera la ULTIMA etapa (eso solo se ve despues), por eso no se usa "estar en la ultima etapa", solo lo observable.

COMO SE PRUEBA (igual que comparar_estimadores.py), con DOS origenes para ver la estabilidad: A) entrenar hasta dic-2024 y probar ene-jun 2025; B) entrenar hasta jun-2025 y probar jul-2025 a 9-abr-2026 (y por separado jul-dic 2025 y ene-9 abr 2026), modelo por momento (landmark) en c = 3, 6, 9, 12 y 24 h,
con las mismas variables del estimador final (BASE) y con BASE + EXTRA. Mejora frente al rango general y diferencia pareada con IC 95 % (bootstrap por semanas).
Solo con laboratorios de la persona real dentro de la ventana de la estancia (consulta sql/espera_labs_dx_con_hora.sql).

SALIDAS (HUN_TABLAS): ultima_etapa_estabilidad.csv, ultima_etapa_resumen.txt
COMO CORRERLO  python3 src/prueba_ultima_etapa.py   (10-20 min)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402
import caracterizar_tu as ct  # noqa: E402
import caracterizar_etapas_tu as cet  # noqa: E402

MOMENTOS = [3, 6, 9, 12, 24]
EXTRA = ["tomas_hasta_c", "h_desde_ultima_toma", "tomas_ultimas_3h", "tomas_etapa_actual", "dx_hasta_c"]
VIDA_MEDIA_DIAS = 182
LINEAS = []


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def tablas_con_hora(d):
    """Tomas de laboratorio y diagnosticos (horas desde la llegada) y etapas TU de cada estancia de d."""
    c = ct.cohorte()
    vis = ct.visitas_de_estancia()
    L = pd.concat([pd.read_csv(ct.CONS / f"espera_labs_{a}.csv", parse_dates=["measurement_datetime"]) for a in range(2023, 2027)], ignore_index=True)
    L = L.merge(vis, on="visit_occurrence_id").merge(c[["estancia_id", "real", "ini_est", "ini_hosp_est"]], on="estancia_id")
    L = L[(L.person_id == L.real) & (L.measurement_datetime >= L.ini_est) & (L.measurement_datetime < L.ini_hosp_est)]
    toma = L.drop_duplicates(["estancia_id", "measurement_datetime"]).assign(h=lambda x: (x.measurement_datetime - x.ini_est).dt.total_seconds() / 3600)[["estancia_id", "h"]]
    D = pd.concat([pd.read_csv(ct.CONS / f"espera_dx_{a}.csv", parse_dates=["primera", "ultima"]) for a in range(2023, 2027)], ignore_index=True)
    D = D.merge(vis, on="visit_occurrence_id").merge(c[["estancia_id", "real", "ini_est", "ini_hosp_est"]], on="estancia_id")
    D = D[(D.person_id == D.real) & (D.primera >= D.ini_est) & (D.primera < D.ini_hosp_est) & (D.condition_concept_id != 0)]
    dx = D.drop_duplicates(["estancia_id", "condition_concept_id"]).assign(h=lambda x: (x.primera - x.ini_est).dt.total_seconds() / 3600)[["estancia_id", "h"]]
    E = cet.etapas_tu(c)[["estancia_id", "h_ini"]]
    return toma, dx, E


def extras_en(d, toma, dx, E, momento):
    """EXTRA de cada fila de d en el momento 'momento' (horas desde la llegada)."""
    est = d[["estancia_id"]].copy()
    t = toma[toma.h < momento]
    g = t.groupby("estancia_id").h
    est["tomas_hasta_c"] = g.size().reindex(est.estancia_id).fillna(0).to_numpy()
    est["h_desde_ultima_toma"] = (momento - g.max()).reindex(est.estancia_id).to_numpy()
    est["tomas_ultimas_3h"] = t[t.h >= momento - 3].groupby("estancia_id").size().reindex(est.estancia_id).fillna(0).to_numpy()
    ini_et = E[E.h_ini <= momento].groupby("estancia_id").h_ini.max()                         # inicio de la etapa en la que esta el paciente en 'momento'
    tt = t.merge(ini_et.rename("ini_etapa"), left_on="estancia_id", right_index=True, how="inner")
    est["tomas_etapa_actual"] = tt[tt.h >= tt.ini_etapa].groupby("estancia_id").size().reindex(est.estancia_id).fillna(0).to_numpy()
    est["dx_hasta_c"] = dx[dx.h < momento].groupby("estancia_id").size().reindex(est.estancia_id).fillna(0).to_numpy()
    return est[EXTRA]


ORIGENES = [("A: entrenar hasta dic-2024, probar ene-jun 2025", pd.Timestamp("2025-01-01"), pd.Timestamp("2025-07-01")),
            ("B: entrenar hasta jun-2025, probar jul-2025 a 9-abr-2026", pd.Timestamp("2025-07-01"), ce.HASTA)]
PERIODOS_B = [("jul-dic 2025", pd.Timestamp("2025-07-01"), pd.Timestamp("2026-01-01")), ("ene-9 abr 2026", pd.Timestamp("2026-01-01"), ce.HASTA)]


def main():
    ce.TABLAS.mkdir(parents=True, exist_ok=True)
    d, h, rejilla, estado = ce.preparar()
    toma, dx, E = tablas_con_hora(d)
    filas = []
    decir("PRUEBA DE LOS LABORATORIOS EN LA ETAPA TU ACTUAL, CON ESTABILIDAD POR PERIODO (dos origenes de entrenamiento)")
    for nombre_o, ini, fin in ORIGENES:
        tr0 = d[d.ini_est < ini].reset_index(drop=True)
        te0 = d[(d.ini_est >= ini) & (d.ini_est < fin)].reset_index(drop=True)
        decir(f"\n{nombre_o}: entrenamiento {len(tr0):,} | prueba {len(te0):,} estancias")
        for c in MOMENTOS:
            base = ce.cols_finales(c)
            tr, te = tr0.copy(), te0.copy()
            for df in (tr, te):
                ex = extras_en(df, toma, dx, E, c)
                for col in EXTRA:
                    df[col] = ex[col].to_numpy()
            sub = te[te.espera_cama_h > c].reset_index(drop=True)
            y = np.minimum(sub.espera_cama_h.to_numpy() - c, ce.MAX_H)
            general, _ = ce.referencias(tr0, sub, c)
            l_gen = ce.perdida_por_caso(y, general)
            semana = sub.ini_est.dt.to_period("W").astype(str).to_numpy()
            perd = {}
            for nombre, cols in [("base", base), ("con laboratorios en la etapa", base + EXTRA)]:
                m = ce.entrenar_landmark(tr, rejilla, estado, c, cols=cols, vida_media_dias=VIDA_MEDIA_DIAS)
                perd[nombre] = ce.perdida_por_caso(y, ce.predecir_m1(m, sub, rejilla, estado, c))
            lb, lx = perd["base"], perd["con laboratorios en la etapa"]
            mascaras = [("todo el periodo", np.ones(len(sub), bool))]
            if nombre_o.startswith("B"):
                mascaras += [(n, ((sub.ini_est >= a) & (sub.ini_est < b)).to_numpy()) for n, a, b in PERIODOS_B]
            for per, mk in mascaras:
                lo, hi = ce.intervalo_mejora(semana[mk], lx[mk], lb[mk])
                fila = {"origen": nombre_o[0], "periodo_de_prueba": per, "horas_esperando": c, "n": int(mk.sum()),
                        "mejora_base_vs_general_pct": round(100 * (1 - lb[mk].mean() / l_gen[mk].mean()), 2),
                        "mejora_con_lab_vs_general_pct": round(100 * (1 - lx[mk].mean() / l_gen[mk].mean()), 2),
                        "diferencia_pareada_pct": round(100 * (1 - lx[mk].mean() / lb[mk].mean()), 2), "ic95_bajo": round(lo, 2), "ic95_alto": round(hi, 2)}
                filas.append(fila)
                decir(f"  {per:16s} {c:>2} h (n={fila['n']:,}): base {fila['mejora_base_vs_general_pct']:+.2f} % | con lab {fila['mejora_con_lab_vs_general_pct']:+.2f} % | "
                      f"diferencia {fila['diferencia_pareada_pct']:+.2f} (IC95 {lo:+.2f} a {hi:+.2f})")
    t = pd.DataFrame(filas)
    t.to_csv(ce.TABLAS / "ultima_etapa_estabilidad.csv", index=False)
    decir("\nRESUMEN: diferencia pareada (puntos de mejora que suman los laboratorios en la etapa)")
    decir(t.pivot_table(index="horas_esperando", columns=["origen", "periodo_de_prueba"], values="diferencia_pareada_pct").round(2).to_string())
    (ce.TABLAS / "ultima_etapa_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    main()
