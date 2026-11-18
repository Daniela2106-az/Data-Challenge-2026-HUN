"""
procedimientos_y_laboratorios.py  -  version 1 (10-nov-2026)
Daniela (10-nov): los procedimientos no tienen hora, pero los laboratorios si. ¿Que procedimientos se asocian con que laboratorios? ¿Hay procedimiento sin laboratorio, o laboratorio sin procedimiento?

HALLAZGO DE PARTIDA: muchos procedimientos son LAS MISMAS ORDENES que luego aparecen como laboratorio (hemograma, creatinina, urea, glucosa, tiempo de protrombina...): comparten el
mismo codigo de concepto en procedure_occurrence y en measurement. Entonces se puede cruzar por concepto: "orden" (procedimiento) frente a "resultado" (laboratorio).

COMO SE ARMA
  - Estancias unicas hospitalizadas del periodo confiable, de la persona real, con estancia en cama de 48 h o menos y alta registrada: la ventana de laboratorios (espera de cama +
    primeras 48 h de cama, que son las que se extrajeron con hora) cubre ENTERA su visita, asi que no se pierde nada por truncamiento.
  - Procedimientos: Q01 (auditoria_bd; todos los procedimientos de las visitas con hospitalizacion, sin fecha; union de las visitas de la estancia, SIN filtrar por persona). Laboratorios: los de la espera (espera_labs_*.csv) y las primeras 48 h de cama
    (Q02). Se llevan las filas de las visitas copia a la estancia de su visita raiz y se queda solo lo de la persona real.
  - "Resultado traducido" = hay una fila de laboratorio con el concepto; las tomas con concepto 0 (sin traducir) no se pueden cruzar.

SALIDAS (HUN_TABLAS): proc_lab_orden_vs_resultado.csv, proc_lab_estancias.csv, proc_lab_no_laboratorio_asociacion.csv, proc_lab_resumen.txt
COMO CORRERLO  python3 src/procedimientos_y_laboratorios.py   (1 min)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caracterizar_tu as ct  # noqa: E402

AUD = Path(ct.CONS).parent / "auditoria_bd"
TABLAS = ct.TABLAS
LINEAS = []


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def main():
    TABLAS.mkdir(parents=True, exist_ok=True)
    c = ct.cohorte()
    t = pd.read_parquet(ct.PROC / "tabla_episodios.parquet", columns=["estancia_id", "estancia_unica", "fin_hosp_est", "ini_hosp_est"])
    t = t[t.estancia_unica].drop_duplicates("estancia_id")
    c = c.merge(t[["estancia_id", "fin_hosp_est", "ini_hosp_est"]].rename(columns={"fin_hosp_est": "fin_h", "ini_hosp_est": "ini_h"}), on="estancia_id", how="left")
    c["estancia_h"] = (c.fin_h - c.ini_h).dt.total_seconds() / 3600
    cc = c[(c.estancia_h > 0) & (c.estancia_h <= 48) & (c.fin_h < ct.HASTA)]
    decir(f"PROCEDIMIENTOS Y LABORATORIOS | estancias con estancia en cama de 48 h o menos y alta registrada: {len(cc):,} de {len(c):,}")
    vis = ct.visitas_de_estancia()
    nombres = pd.read_csv(AUD / "Q03_nombres_de_conceptos.csv").drop_duplicates("concept_id").set_index("concept_id").concept_name

    # procedimientos (sin hora), de la persona real
    P = pd.read_csv(AUD / "Q01_procedimientos_por_estancia.csv").merge(vis, on="visit_occurrence_id").merge(cc[["estancia_id", "real"]], on="estancia_id")
    # los procedimientos de una estancia gemela cuelgan sobre todo del OTRO registro (docs/CONTEXTO_TECNICO.md 4.10: el 88 % no es el conservado): no se filtra por persona,
    # se une lo de todas las visitas de la estancia (igual que n_proc_distintos del pipeline). Los laboratorios si se filtran por persona real.
    P = P[["estancia_id", "concepto"]].drop_duplicates()

    # laboratorios (con hora): espera + primeras 48 h de cama, de la persona real
    W = pd.concat([pd.read_csv(ct.CONS / f"espera_labs_{a}.csv", usecols=["visit_occurrence_id", "person_id", "measurement_concept_id"]) for a in range(2023, 2027)], ignore_index=True)
    W = W.rename(columns={"measurement_concept_id": "concepto"})
    Q2 = pd.read_csv(AUD / "Q02_laboratorios_primeras_48h_por_estancia.csv")[["visit_occurrence_id", "person_id", "concepto"]]
    Lb = pd.concat([W, Q2], ignore_index=True).merge(vis, on="visit_occurrence_id").merge(cc[["estancia_id", "real"]], on="estancia_id")
    Lb = Lb[Lb.person_id == Lb.real][["estancia_id", "concepto"]].drop_duplicates()
    Lt = Lb[Lb.concepto != 0]
    conceptos_lab = set(Lt.concepto)
    decir(f"  Procedimientos distintos: {P.concepto.nunique()}; conceptos de laboratorio traducidos: {len(conceptos_lab)}; "
          f"conceptos presentes en las dos tablas (la misma orden y su resultado): {len(conceptos_lab & set(P.concepto))}")

    # ---- 1. estancia por estancia: ¿procedimiento sin laboratorio y laboratorio sin procedimiento?
    n = len(cc)
    sp = set(P.estancia_id)
    sl_any = set(Lb.estancia_id)
    sl_tr = set(Lt.estancia_id)
    # procedimientos que son "ordenes de laboratorio" (mismo concepto que algun laboratorio)
    orden_lab = set(P[P.concepto.isin(conceptos_lab)].estancia_id)
    otro_proc = set(P[~P.concepto.isin(conceptos_lab)].estancia_id)
    filas = [("con algun procedimiento", len(sp)), ("con alguna toma de laboratorio (traducida o no)", len(sl_any)), ("con laboratorio traducido", len(sl_tr)),
             ("con una orden de examen (procedimiento que tambien es laboratorio)", len(orden_lab)), ("con otro procedimiento (imagen, consulta, cirugia...)", len(otro_proc)),
             ("procedimiento SIN ninguna toma de laboratorio", len(sp - sl_any)), ("toma de laboratorio SIN ningun procedimiento", len(sl_any - sp)),
             ("orden de examen SIN ningun laboratorio traducido", len(orden_lab - sl_tr)), ("laboratorio traducido SIN ninguna orden de examen", len(sl_tr - orden_lab)),
             ("ni procedimiento ni laboratorio", n - len(sp | sl_any))]
    t1 = pd.DataFrame([{"estancias": k, "n": v, "pct": round(100 * v / n, 1)} for k, v in filas])
    decir("\n1. ESTANCIA POR ESTANCIA")
    decir(t1.to_string(index=False))
    t1.to_csv(TABLAS / "proc_lab_estancias.csv", index=False)

    # ---- 2. orden frente a resultado, por concepto
    decir("\n2. LA MISMA PRUEBA: ORDEN (procedimiento) FRENTE A RESULTADO (laboratorio), por concepto")
    f2 = []
    for cid in sorted(conceptos_lab & set(P.concepto)):
        o = set(P[P.concepto == cid].estancia_id)
        r = set(Lt[Lt.concepto == cid].estancia_id)
        f2.append({"concepto": cid, "examen": nombres.get(cid, ""), "estancias_con_orden": len(o), "estancias_con_resultado": len(r), "con_ambos": len(o & r),
                   "pct_ordenes_con_resultado": round(100 * len(o & r) / len(o), 1) if o else np.nan, "pct_resultados_con_orden": round(100 * len(o & r) / len(r), 1) if r else np.nan})
    t2 = pd.DataFrame(f2).sort_values("estancias_con_orden", ascending=False)
    decir(t2.head(30).to_string(index=False, max_colwidth=60))
    t2.to_csv(TABLAS / "proc_lab_orden_vs_resultado.csv", index=False)
    pond = (t2.con_ambos.sum() / t2.estancias_con_orden.sum()) * 100
    decir(f"  En conjunto: de cada 100 ordenes de examen, {pond:.0f} tienen su resultado traducido en la base; el resto no (resultado sin traducir o no registrado).")

    # ---- 3. los procedimientos que NO son laboratorio: ¿que laboratorios los acompanan?
    decir("\n3. PROCEDIMIENTOS QUE NO SON EXAMENES: ¿QUE LABORATORIOS LOS ACOMPANAN? (mayor aumento de probabilidad frente a las estancias sin ese procedimiento; n >= 100 estancias)")
    base = Lt.groupby("concepto").estancia_id.nunique() / n
    por_proc = P[~P.concepto.isin(conceptos_lab)].groupby("concepto").estancia_id.apply(set)
    f3 = []
    for pid, est in por_proc.items():
        if len(est) < 100:
            continue
        lab_con = Lt[Lt.estancia_id.isin(est)].groupby("concepto").estancia_id.nunique() / len(est)
        lab_sin = Lt[~Lt.estancia_id.isin(est)].groupby("concepto").estancia_id.nunique() / (n - len(est))
        lift = (lab_con / lab_sin.reindex(lab_con.index)).replace([np.inf], np.nan).dropna()
        top = lift[(lab_con.reindex(lift.index) >= 0.05)].sort_values(ascending=False).head(3)
        for cid, v in top.items():
            f3.append({"procedimiento": nombres.get(pid, pid), "n_estancias": len(est), "laboratorio": nombres.get(cid, cid), "pct_con_ese_lab_si_hay_procedimiento": round(100 * lab_con[cid], 1),
                       "pct_con_ese_lab_si_no_hay": round(100 * lab_sin.get(cid, 0), 1), "aumento_veces": round(float(v), 1)})
        f3.append({"procedimiento": nombres.get(pid, pid), "n_estancias": len(est), "laboratorio": "(cualquier laboratorio traducido)", "pct_con_ese_lab_si_hay_procedimiento": round(100 * len(sl_tr & est) / len(est), 1),
                   "pct_con_ese_lab_si_no_hay": round(100 * len(sl_tr - est) / (n - len(est)), 1), "aumento_veces": np.nan})
    t3 = pd.DataFrame(f3)
    t3.to_csv(TABLAS / "proc_lab_no_laboratorio_asociacion.csv", index=False)
    top_proc = por_proc.map(len).sort_values(ascending=False).head(14).index
    decir(t3[t3.procedimiento.isin([nombres.get(x, x) for x in top_proc])].to_string(index=False, max_colwidth=55))
    (TABLAS / "proc_lab_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    main()
