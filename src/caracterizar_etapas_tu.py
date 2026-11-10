"""
caracterizar_etapas_tu.py  -  version 1 (9-nov-2026)
Continuacion de caracterizar_tu.py. Alli se junto toda la espera en un bloque; eso lo hicimos nosotros: en la base cada estancia tiene VARIAS etapas TU
(visit_detail), pegadas una tras otra (el fin de una es el inicio de la siguiente). Aqui se miran las etapas CRUDAS antes de la cama, una por una, y se
caracteriza cada una por lo que cae dentro de su intervalo: laboratorios (hora de toma) y diagnosticos (hora del primer registro). Los procedimientos no
tienen hora y no se pueden asociar a una etapa.

QUE SE MIDE
  1. Cuantas etapas TU tiene cada estancia antes de la cama, por grupo de espera (A < 6 h, B 12-48 h, C > 72 h) y cuanto dura cada una segun su posicion
     (primera, intermedias, ultima). Cuanto de la espera esta en la ultima etapa.
  2. A que hora del dia empiezan las etapas (el cambio de etapa, ¿coincide con cambios de turno?).
  3. Laboratorios por etapa: cuantos caen en cada posicion y si cada etapa nueva "dispara" una toma (tomas en la hora siguiente al inicio de la etapa frente a
     el resto de la etapa).
  4. Diagnosticos por etapa: en que posicion se registra el primer registro de cada diagnostico.
  5. Lo que distingue las etapas del grupo C de las del B.
  6. Cuando empieza la ultima etapa (horas desde la llegada y hora del dia).

SALIDAS (HUN_TABLAS): tu_etapas_por_grupo.csv, tu_etapas_duracion_por_posicion.csv, tu_etapas_hora_de_inicio.csv, tu_etapas_laboratorios.csv, tu_etapas_diagnosticos.csv, tu_etapas_inicio_ultima.csv, tu_etapas_hora_inicio_ultima.csv, tu_etapas_resumen.txt
ENTRADAS visit_detail.csv (HUN_CRUDOS) mas las de caracterizar_tu.py
COMO CORRERLO  python3 src/caracterizar_etapas_tu.py   (1-2 min)
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caracterizar_tu as ct  # noqa: E402

RAIZ = ct.RAIZ
CRUDOS = Path(os.environ.get("HUN_CRUDOS", RAIZ / "datos" / "crudos"))
TABLAS = ct.TABLAS
LINEAS = []


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def etapas_tu(c):
    vd = pd.read_csv(CRUDOS / "visit_detail.csv", parse_dates=["visit_detail_start_datetime", "visit_detail_end_datetime"])
    vd = vd[vd.visit_detail_concept_id == 3045729]
    m = vd.merge(c[["visit_occurrence_id", "estancia_id", "ini_est", "ini_hosp_est", "grupo", "espera_cama_h", "edad", "categoria_dx"]], on="visit_occurrence_id")
    m = m[(m.visit_detail_start_datetime >= m.ini_est - pd.Timedelta(seconds=1)) & (m.visit_detail_start_datetime < m.ini_hosp_est)].copy()
    m = m.rename(columns={"visit_detail_start_datetime": "ini", "visit_detail_end_datetime": "fin"})
    m = m.sort_values(["estancia_id", "ini", "fin"]).reset_index(drop=True)
    m["k"] = m.groupby("estancia_id").cumcount() + 1
    m["K"] = m.groupby("estancia_id").k.transform("max")
    m["posicion"] = np.where(m.K == 1, "unica", np.where(m.k == 1, "primera", np.where(m.k == m.K, "ultima", "intermedia")))
    m["fin_efectivo"] = m.fin.where(m.fin > m.ini, m.ini_hosp_est)                              # etapa sin hora de fin: se toma hasta la cama
    m["fin_efectivo"] = m[["fin_efectivo", "ini_hosp_est"]].min(axis=1)
    m["dur_h"] = (m.fin_efectivo - m.ini).dt.total_seconds() / 3600
    m["h_ini"] = (m.ini - m.ini_est).dt.total_seconds() / 3600
    m["hora_reloj"] = m.ini.dt.hour
    return m


def main():
    TABLAS.mkdir(parents=True, exist_ok=True)
    c = ct.cohorte()
    vis = ct.visitas_de_estancia()
    E = etapas_tu(c)
    nombres = [g[0] for g in ct.GRUPOS]
    decir(f"ETAPAS TU CRUDAS ANTES DE LA CAMA | {E.estancia_id.nunique():,} estancias, {len(E):,} etapas")

    # ---- 1. numero de etapas y duracion por posicion
    decir("\n1. ETAPAS TU POR ESTANCIA (crudas, sin juntar)")
    K = E.drop_duplicates("estancia_id").groupby("grupo", observed=True).K.agg(estancias="size", media="mean", mediana="median", p90=lambda s: s.quantile(.9)).reindex(nombres).round(2)
    esp = c.groupby("grupo", observed=True).espera_cama_h.median().reindex(nombres).round(1)
    K["espera_mediana_h"] = esp
    K["etapas_por_dia_de_espera"] = (E.drop_duplicates("estancia_id").assign(d=lambda x: x.espera_cama_h / 24).groupby("grupo", observed=True).apply(lambda g: (g.K / g.d).median(), include_groups=False)).reindex(nombres).round(2)
    decir(K.to_string())
    K.to_csv(TABLAS / "tu_etapas_por_grupo.csv")

    decir("\n   Duracion de cada etapa segun su posicion (horas; mediana y p75), por grupo de espera:")
    f = []
    for gname in nombres:
        for pos in ["unica", "primera", "intermedia", "ultima"]:
            s = E[(E.grupo == gname) & (E.posicion == pos)]
            if len(s) >= 50:
                f.append({"grupo": gname, "posicion": pos, "n_etapas": len(s), "dur_mediana_h": round(s.dur_h.median(), 2), "dur_p75_h": round(s.dur_h.quantile(.75), 2),
                          "pct_de_la_espera_mediana": round(100 * (s.dur_h / s.espera_cama_h).median(), 1)})
    t1 = pd.DataFrame(f)
    decir(t1.to_string(index=False))
    t1.to_csv(TABLAS / "tu_etapas_duracion_por_posicion.csv", index=False)

    ult = E[E.posicion == "ultima"].groupby("grupo", observed=True).apply(lambda g: 100 * (g.dur_h / g.espera_cama_h).median(), include_groups=False).reindex(nombres).round(1)
    decir("\n   % de la espera que ocupa la ULTIMA etapa (mediana, estancias con 2 o mas etapas): " + ", ".join(f"{k}: {v}" for k, v in ult.items()))

    # ---- 2. hora de inicio de las etapas
    decir("\n2. HORA DEL DIA EN QUE EMPIEZAN LAS ETAPAS (la primera etapa frente a las siguientes)")
    h2 = pd.DataFrame({"primeras_etapas_pct": E[E.k == 1].hora_reloj.value_counts(normalize=True).sort_index() * 100,
                       "cambios_de_etapa_pct": E[E.k >= 2].hora_reloj.value_counts(normalize=True).sort_index() * 100}).round(1)
    h2.to_csv(TABLAS / "tu_etapas_hora_de_inicio.csv")
    decir("   hora:  " + " ".join(f"{h:>4d}" for h in h2.index))
    decir("   1ra:   " + " ".join(f"{v:>4.1f}" for v in h2.primeras_etapas_pct))
    decir("   cambio:" + " ".join(f"{v:>4.1f}" for v in h2.cambios_de_etapa_pct))
    top = h2.cambios_de_etapa_pct.sort_values(ascending=False).head(6)
    decir("   Horas con mas cambios de etapa: " + ", ".join(f"{int(h)} h ({v:.1f} %)" for h, v in top.items()))

    # ---- laboratorios y diagnosticos de la persona real, con la hora
    L = pd.concat([pd.read_csv(ct.CONS / f"espera_labs_{a}.csv", parse_dates=["measurement_datetime"]) for a in range(2023, 2027)], ignore_index=True)
    L = L.merge(vis, on="visit_occurrence_id").merge(c[["estancia_id", "real", "ini_est", "ini_hosp_est"]], on="estancia_id")
    L = L[(L.person_id == L.real) & (L.measurement_datetime >= L.ini_est) & (L.measurement_datetime < L.ini_hosp_est)]
    toma = L.drop_duplicates(["estancia_id", "measurement_datetime"])[["estancia_id", "measurement_datetime"]]
    D = pd.concat([pd.read_csv(ct.CONS / f"espera_dx_{a}.csv", parse_dates=["primera", "ultima"]) for a in range(2023, 2027)], ignore_index=True)
    D = D.merge(vis, on="visit_occurrence_id").merge(c[["estancia_id", "real", "ini_est", "ini_hosp_est"]], on="estancia_id")
    D = D[(D.person_id == D.real) & (D.primera >= D.ini_est) & (D.primera < D.ini_hosp_est) & (D.condition_concept_id != 0)]
    dxc = D.drop_duplicates(["estancia_id", "condition_concept_id"])[["estancia_id", "condition_concept_id", "primera"]]

    # ---- 3. laboratorios por etapa
    decir("\n3. LABORATORIOS DENTRO DE CADA ETAPA TU")
    tt = E[["estancia_id", "k", "K", "posicion", "grupo", "ini", "fin_efectivo", "dur_h"]].merge(toma, on="estancia_id")
    tt = tt[(tt.measurement_datetime >= tt.ini) & (tt.measurement_datetime < tt.fin_efectivo)]
    tt["min_desde_ini"] = (tt.measurement_datetime - tt.ini).dt.total_seconds() / 60
    por_etapa = tt.groupby(["estancia_id", "k"]).agg(n_tomas=("min_desde_ini", "size"), en_primera_hora=("min_desde_ini", lambda v: int((v < 60).sum()))).reset_index()
    EE = E.merge(por_etapa, on=["estancia_id", "k"], how="left").fillna({"n_tomas": 0, "en_primera_hora": 0})
    con = EE[EE.estancia_id.isin(toma.estancia_id.unique())]                           # solo estancias con alguna toma (si no, no sabemos si faltan registros)
    f3 = []
    for pos in ["unica", "primera", "intermedia", "ultima"]:
        s = con[con.posicion == pos]
        if len(s):
            horas = s.dur_h.sum()
            f3.append({"posicion": pos, "n_etapas": len(s), "pct_etapas_con_toma": round(100 * (s.n_tomas > 0).mean(), 1), "tomas_por_10h": round(10 * s.n_tomas.sum() / horas, 2),
                       "tomas_primera_hora_por_etapa": round(s.en_primera_hora.mean(), 2), "dur_mediana_h": round(s.dur_h.median(), 2)})
    t3 = pd.DataFrame(f3)
    decir("   (solo estancias con al menos una toma de laboratorio en la espera)")
    decir(t3.to_string(index=False))
    # ¿cada etapa nueva dispara una toma? tomas en la primera hora de la etapa frente a la tasa del resto de la etapa
    s = con[(con.k >= 2) & (con.dur_h > 2)]
    primera_h = s.en_primera_hora.sum() / len(s)
    resto = (s.n_tomas.sum() - s.en_primera_hora.sum()) / (s.dur_h.sum() - len(s))
    decir(f"   Etapas intermedias o ultimas de mas de 2 h (n = {len(s):,}): {primera_h:.3f} tomas en la primera hora de la etapa frente a {resto:.3f} por hora en el resto de la etapa "
          f"({primera_h / resto:.1f} veces)")
    s1 = con[(con.k == 1) & (con.dur_h > 2)]
    decir(f"   Primera etapa de mas de 2 h (n = {len(s1):,}): {s1.en_primera_hora.sum() / len(s1):.3f} tomas en la primera hora frente a "
          f"{(s1.n_tomas.sum() - s1.en_primera_hora.sum()) / (s1.dur_h.sum() - len(s1)):.3f} por hora en el resto")
    por_grupo = con.groupby(["grupo", "posicion"], observed=True).apply(lambda g: pd.Series({"n_etapas": len(g), "tomas_por_10h": round(10 * g.n_tomas.sum() / g.dur_h.sum(), 2)}), include_groups=False).reset_index()
    decir("   Tomas por 10 horas de etapa, segun el grupo de espera y la posicion de la etapa:")
    decir(por_grupo[por_grupo.n_etapas >= 50].pivot(index="posicion", columns="grupo", values="tomas_por_10h").reindex(["unica", "primera", "intermedia", "ultima"]).to_string())
    t3.to_csv(TABLAS / "tu_etapas_laboratorios.csv", index=False)

    # ---- 4. diagnosticos por etapa
    decir("\n4. EN QUE ETAPA SE REGISTRA CADA DIAGNOSTICO (primer registro de cada diagnostico distinto)")
    dd = E[["estancia_id", "k", "K", "posicion", "ini", "fin_efectivo"]].merge(dxc, on="estancia_id")
    dd = dd[(dd.primera >= dd.ini) & (dd.primera < dd.fin_efectivo)]
    d4 = dd.groupby("posicion").size()
    tot = d4.sum()
    decir("   % de los diagnosticos segun la posicion de la etapa en que se registran: " + ", ".join(f"{p}: {100 * d4.get(p, 0) / tot:.1f} %" for p in ["unica", "primera", "intermedia", "ultima"]))
    base = E.groupby("posicion").dur_h.sum()
    decir("   % de las horas de TU segun la posicion de la etapa: " + ", ".join(f"{p}: {100 * base.get(p, 0) / base.sum():.1f} %" for p in ["unica", "primera", "intermedia", "ultima"]))
    pd.DataFrame({"pct_diagnosticos": 100 * d4 / tot, "pct_horas": 100 * base / base.sum()}).round(1).to_csv(TABLAS / "tu_etapas_diagnosticos.csv")

    # ---- 5. grupo C frente a B
    decir("\n5. ¿QUE DISTINGUE A LAS ESTANCIAS LARGAS? (B 12-48 h frente a C > 72 h)")
    for gname in ["B  12-48 h", "C  > 72 h"]:
        g = E[E.grupo == gname]
        e = g.drop_duplicates("estancia_id")
        un = g[g.K >= 2]
        decir(f"   {gname}: {e.K.mean():.2f} etapas por estancia; primera etapa {g[g.k == 1].dur_h.median():.1f} h; ultima etapa {g[(g.posicion == 'ultima')].dur_h.median():.1f} h; "
              f"% de la espera en la ultima etapa {100 * (un[un.posicion == 'ultima'].dur_h / un[un.posicion == 'ultima'].espera_cama_h).median():.0f} %")

    # ---- 6. cuando empieza la ultima etapa
    decir("\n6. ¿CUANDO EMPIEZA LA ULTIMA ETAPA? (estancias con 2 o mas etapas; horas desde la llegada hasta que empieza la ultima)")
    u = E[(E.posicion == "ultima")]
    t6 = u.groupby("grupo", observed=True).agg(n=("h_ini", "size"), h_inicio_ultima_p25=("h_ini", lambda v: v.quantile(.25)), h_inicio_ultima_mediana=("h_ini", "median"),
                                               h_inicio_ultima_p75=("h_ini", lambda v: v.quantile(.75)), dur_ultima_mediana_h=("dur_h", "median")).reindex(nombres).round(1)
    decir(t6.to_string())
    t6.to_csv(TABLAS / "tu_etapas_inicio_ultima.csv")
    hh = pd.DataFrame({"ultima_etapa_pct": u.hora_reloj.value_counts(normalize=True).sort_index() * 100,
                       "intermedias_pct": E[E.posicion == "intermedia"].hora_reloj.value_counts(normalize=True).sort_index() * 100}).round(1)
    decir("   hora:      " + " ".join(f"{h:>4d}" for h in hh.index))
    decir("   ultima:    " + " ".join(f"{v:>4.1f}" for v in hh.ultima_etapa_pct))
    decir("   intermedia:" + " ".join(f"{v:>4.1f}" for v in hh.intermedias_pct))
    hh.to_csv(TABLAS / "tu_etapas_hora_inicio_ultima.csv")
    (TABLAS / "tu_etapas_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")
    E.to_parquet(ct.PROC / "tu_etapas_por_estancia.parquet")


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    main()
