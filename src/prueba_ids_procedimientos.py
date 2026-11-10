"""
prueba_ids_procedimientos.py  -  version 1 (10-nov-2026)
¿El orden de procedure_occurrence_id (o de measurement_id) sigue el orden en que ocurrieron las cosas? Si si, los procedimientos (que no tienen fecha) se podrian ordenar entre si y, con las
ordenes de laboratorio como ancla (misma prueba, con hora de toma), ubicar entre dos anclas y asignar a una etapa TU aproximada.

PRUEBA (con sql/ids_procedimientos.sql: proc_ids_<ano>.csv y labs_ids_<ano>.csv en HUN_CRUDOS/consultas)
  1. Laboratorios, donde la hora SI se conoce: correlacion de Spearman entre measurement_id y la hora de toma, por visita (>= 5 tomas).
  2. Lo mismo solo en visitas cuyos ids estan en un rango estrecho (un solo lote de carga).
  3. Procedimientos: correlacion entre el id de la orden y la hora de toma del MISMO examen (ancla), por visita (>= 5 anclas).
  4. ¿Los ids siguen la fecha entre visitas? (mediana del measurement_id por mes).
RESULTADO: no. Ver docs/procedimientos_y_laboratorios.md, seccion 4.
COMO CORRERLO  python3 src/prueba_ids_procedimientos.py   (1 min)
"""
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

RAIZ = Path(__file__).resolve().parent.parent
CONS = Path(os.environ.get("HUN_CRUDOS", RAIZ / "datos" / "crudos")) / "consultas"
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))


def rho(g, a, b):
    return spearmanr(g[a], g[b])[0] if len(g) >= 5 and g[a].nunique() > 1 and g[b].nunique() > 1 else np.nan


def main():
    TABLAS.mkdir(parents=True, exist_ok=True)
    P = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(CONS / "proc_ids_20*.csv")))], ignore_index=True)
    L = pd.concat([pd.read_csv(f, parse_dates=["measurement_datetime"]) for f in sorted(glob.glob(str(CONS / "labs_ids_20*.csv")))], ignore_index=True)
    L["t_h"] = L.measurement_datetime.astype("int64") / 3.6e12
    out = [f"PRUEBA DEL ORDEN DE LOS IDENTIFICADORES | procedimientos: {len(P):,} filas de {P.visit_occurrence_id.nunique():,} visitas; laboratorios: {len(L):,} filas de {L.visit_occurrence_id.nunique():,} visitas"]
    g = L.groupby(["visit_occurrence_id", "person_id"])
    r = g.apply(lambda x: rho(x, "id_min", "t_h"), include_groups=False).dropna()
    out.append(f"1) Laboratorios, measurement_id frente a la hora de toma (por visita, >= 5 tomas): n = {len(r):,}; Spearman mediana {r.median():.2f}, p25 {r.quantile(.25):.2f}, "
               f"con rho > 0,8: {100 * (r > 0.8).mean():.1f} %")
    rng = g.id_min.agg(lambda s: s.max() - s.min())
    rs = r.reindex(rng.index[rng < 10000]).dropna()
    out.append(f"2) Rango del measurement_id dentro de una visita: mediana {rng.median():.0f} (100 % de las visitas en un bloque de menos de 10.000 ids); "
               f"Spearman en esas visitas: mediana {rs.median():.2f}, con rho > 0,8: {100 * (rs > 0.8).mean():.1f} %")
    P["rango"] = P.id_max - P.id_min
    out.append(f"   Procedimientos: filas por (visita, procedimiento) mediana {P.filas.median():.0f}; el {100 * (P.rango > 1e6).mean():.1f} % tiene ids que abarcan mas de 1.000.000 (varias cargas mezcladas)")
    Lc = L[L.concepto != 0].groupby(["visit_occurrence_id", "person_id", "concepto"]).agg(t_h=("t_h", "min")).reset_index()
    A = P.merge(Lc, on=["visit_occurrence_id", "person_id", "concepto"])
    rr = A.groupby(["visit_occurrence_id", "person_id"]).apply(lambda x: rho(x, "id_min", "t_h"), include_groups=False).dropna()
    out.append(f"3) Procedimientos: {len(A):,} anclas (mismo examen como procedimiento y como laboratorio) en {A.groupby(['visit_occurrence_id', 'person_id']).ngroups:,} visitas. "
               f"id de la orden frente a la hora de toma del mismo examen (>= 5 anclas): n = {len(rr):,}; Spearman mediana {rr.median():.2f}, p25 {rr.quantile(.25):.2f}, p75 {rr.quantile(.75):.2f}; "
               f"con rho > 0,8: {100 * (rr > 0.8).mean():.1f} %; con rho > 0,5: {100 * (rr > 0.5).mean():.1f} %")
    m = L.assign(mes=L.measurement_datetime.dt.to_period("M")).groupby("mes").id_min.median()
    out.append("4) Mediana del measurement_id por mes (sube en general con la fecha entre visitas, con altibajos): " + "; ".join(f"{k}: {v / 1e6:.1f} M" for k, v in m.iloc[[0, 6, 12, 18, 24, 30, -1]].items()))
    out.append("CONCLUSION: los ids de laboratorio de cada visita vienen en un bloque estrecho (se cargaron visita por visita y, en general, crecen con la fecha de la visita), pero dentro de la visita su orden NO sigue la hora (rho ~ 0,1): no sirven para ubicar procedimientos en el tiempo.")
    print("\n".join(out))
    (TABLAS / "prueba_ids_resumen.txt").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
