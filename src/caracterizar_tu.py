"""
caracterizar_tu.py  -  version 1 (9-nov-2026)
Pregunta (Daniela, 9-nov): la espera de cama es casi toda tiempo en urgencias (etapas TU) antes de que se asigne la cama. ¿Quienes esperan mucho HACEN algo
distinto en urgencias (mas laboratorios, mas diagnosticos, mas bloques de atencion) o simplemente esperan mas tiempo en el mismo estado ("espera pura")?

COMO SE MIDE
  - Las etapas TU no traen diagnostico ni laboratorio propios: esa informacion cuelga de la visita. Se caracteriza entonces la VENTANA DE ESPERA de cada
    estancia (de la llegada, ini_est, a la asignacion de cama, ini_hosp_est), que es casi toda TU.
  - Laboratorios (hora de toma, medida confiable) y diagnosticos (hora de registro, poco confiable: se registra tarde) con su hora, de la consulta
    sql/espera_labs_dx_con_hora.sql. Se usan SOLO las filas de la persona real de la estancia (persona_real de tabla_episodios, o la del registro conservado si no se
    pudo identificar) y SOLO las que caen dentro de la ventana de la estancia. Los procedimientos no tienen hora y no entran.
  - Grupos por espera de cama (periodo confiable, estancias unicas, sin el 28 y 29 de marzo de 2026): A menos de 6 h; B de 12 a 48 h; C mas de 72 h (y 6-12 y 48-72 como apoyo).
  - CUIDADO CON EL TAMANO DE LA VENTANA: una espera larga tiene mas tiempo para acumular tomas, asi que se comparan TASAS (por dia de espera) y lo que pasa en las
    PRIMERAS 6 Y 12 H, que es la misma ventana para todos los que siguen esperando. La medida central es el tiempo SIN laboratorios antes de la cama (horas desde la
    ultima toma hasta la asignacion de cama) y la intensidad de laboratorios por tramo de la espera. El diagnostico no mide inactividad: se registra casi siempre justo
    antes de la cama.

SALIDAS (HUN_TABLAS): tu_grupos_resumen.csv, tu_grupos_actividad.csv, tu_primeras_horas.csv, tu_sin_actividad.csv, tu_intensidad_por_tramo.csv, tu_espera_segun_cantidad.csv, tu_por_diagnostico.csv, tu_resumen.txt
ENTRADAS tabla_episodios.parquet, episodios.csv, bloques.csv (HUN_PROCESADOS) y espera_labs_{2023..2026}.csv, espera_dx_{2023..2026}.csv (HUN_CRUDOS/consultas)
COMO CORRERLO  python3 src/caracterizar_tu.py   (1-2 min)
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
CONS = Path(os.environ.get("HUN_CRUDOS", RAIZ / "datos" / "crudos")) / "consultas"
DESDE, HASTA = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10")
DIAS_CORTE = [pd.Timestamp("2026-03-28").date(), pd.Timestamp("2026-03-29").date()]
GRUPOS = [("A  < 6 h", 0, 6), ("6-12 h", 6, 12), ("B  12-48 h", 12, 48), ("48-72 h", 48, 72), ("C  > 72 h", 72, 1e9)]
LINEAS = []


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def cohorte():
    t = pd.read_parquet(PROC / "tabla_episodios.parquet")
    h = t[t.hospitalizado & t.estancia_unica & t.espera_cama_h.notna() & (t.ini_est >= DESDE) & (t.ini_est < HASTA) & (t.ini_est <= t.ini_hosp_est)].copy()
    h = h[~h.ini_est.dt.date.isin(DIAS_CORTE)]
    h["real"] = h.persona_real.fillna(h.person_id).astype(int)
    h["grupo"] = pd.cut(h.espera_cama_h, [g[1] for g in GRUPOS] + [GRUPOS[-1][2]], labels=[g[0] for g in GRUPOS], right=False)
    return h.reset_index(drop=True)


def visitas_de_estancia():
    e = pd.read_csv(PROC / "episodios.csv", usecols=["visit_occurrence_id", "estancia_id", "hospitalizado"])
    e = e[e.hospitalizado & e.estancia_id.notna()][["visit_occurrence_id", "estancia_id"]].drop_duplicates()
    e["estancia_id"] = e.estancia_id.astype(int)
    # la informacion clinica tambien cuelga de las visitas COPIA (copias.csv: copia -> visita raiz): se lleva a la estancia de su raiz; despues se filtra por persona.
    # (v1 omitia las copias: perdia ~80 % de las filas de laboratorio con concepto traducido y subestimaba la cobertura; corregido el 10-nov)
    cop = pd.read_csv(PROC / "copias.csv", usecols=["visit_occurrence_id", "raiz_id"])
    cop = cop.merge(e.rename(columns={"visit_occurrence_id": "raiz_id"}), on="raiz_id")[["visit_occurrence_id", "estancia_id"]]
    return pd.concat([e, cop], ignore_index=True).drop_duplicates()


def filas_en_ventana(nombre, c, vis, col_hora, extra):
    """Filas (laboratorio o diagnostico) de la persona real que caen dentro de la ventana de espera de su estancia."""
    partes = [pd.read_csv(CONS / f"{nombre}_{a}.csv", parse_dates=[col_hora] + (["primera", "ultima"] if "primera" in extra else [])) for a in range(2023, 2027)]
    d = pd.concat(partes, ignore_index=True)
    d = d.merge(vis, on="visit_occurrence_id").merge(c[["estancia_id", "real", "ini_est", "ini_hosp_est"]], on="estancia_id")
    d = d[d.person_id == d.real]
    return d


def main():
    TABLAS.mkdir(parents=True, exist_ok=True)
    c = cohorte()
    vis = visitas_de_estancia()
    decir(f"CARACTERIZACION DE LA ESPERA EN URGENCIAS | {len(c):,} estancias unicas con espera medida (periodo confiable)")
    decir("  " + "  ".join(f"{g[0]}: {int((c.grupo == g[0]).sum()):,}" for g in GRUPOS))

    # ---- laboratorios dentro de la ventana de la estancia
    L = pd.concat([pd.read_csv(CONS / f"espera_labs_{a}.csv", parse_dates=["measurement_datetime"]) for a in range(2023, 2027)], ignore_index=True)
    L = L.merge(vis, on="visit_occurrence_id").merge(c[["estancia_id", "real", "ini_est", "ini_hosp_est"]], on="estancia_id")
    L = L[(L.person_id == L.real) & (L.measurement_datetime >= L.ini_est) & (L.measurement_datetime < L.ini_hosp_est)]
    L = L.drop_duplicates(["estancia_id", "measurement_datetime", "measurement_concept_id"])
    L["h"] = (L.measurement_datetime - L.ini_est).dt.total_seconds() / 3600
    toma = L.drop_duplicates(["estancia_id", "measurement_datetime"])
    lab = toma.groupby("estancia_id").agg(n_tomas=("h", "size"), h_primera_toma=("h", "min"), h_ultima_toma=("h", "max"))
    lab["n_examenes"] = L[L.measurement_concept_id != 0].groupby("estancia_id").measurement_concept_id.nunique()
    lab["n_examenes"] = lab.n_examenes.fillna(0)

    # ---- diagnosticos dentro de la ventana
    D = pd.concat([pd.read_csv(CONS / f"espera_dx_{a}.csv", parse_dates=["primera", "ultima"]) for a in range(2023, 2027)], ignore_index=True)
    D = D.merge(vis, on="visit_occurrence_id").merge(c[["estancia_id", "real", "ini_est", "ini_hosp_est"]], on="estancia_id")
    D = D[(D.person_id == D.real) & (D.primera >= D.ini_est) & (D.primera < D.ini_hosp_est)]
    D["h_primero"] = (D.primera - D.ini_est).dt.total_seconds() / 3600
    D["h_ultimo"] = (D.ultima.where(D.ultima < D.ini_hosp_est, D.ini_hosp_est) - D.ini_est).dt.total_seconds() / 3600
    dx = D.groupby("estancia_id").agg(n_dx_filas=("filas", "sum"), n_dx_conceptos=("condition_concept_id", lambda s: int((s != 0).sum())), h_primer_dx=("h_primero", "min"), h_ultimo_dx=("h_ultimo", "max"))

    # ---- bloques TU y ER antes de la cama (del registro conservado)
    B = pd.read_csv(PROC / "bloques.csv", parse_dates=["ini", "fin"])
    B = B.merge(c[["visit_occurrence_id", "episodio", "estancia_id", "ini_hosp_est"]], on=["visit_occurrence_id", "episodio"])
    B = B[(B.ini < B.ini_hosp_est) & (B.etapa != "HOSP")]
    bl = B.groupby("estancia_id").agg(n_bloques_tu=("etapa", lambda s: int((s == "TU").sum())), n_bloques_er=("etapa", lambda s: int((s == "ER").sum())))

    x = c.set_index("estancia_id").join([lab, dx, bl])
    for col in ["n_tomas", "n_examenes", "n_dx_filas", "n_dx_conceptos", "n_bloques_tu", "n_bloques_er"]:
        x[col] = x[col].fillna(0)
    x["con_lab"] = x.n_tomas > 0
    x["con_dx"] = x.n_dx_conceptos > 0
    x["con_actividad"] = x.con_lab | x.con_dx
    x["dias"] = x.espera_cama_h / 24
    x["ult_actividad_h"] = x[["h_ultima_toma", "h_ultimo_dx"]].max(axis=1)
    x["sin_actividad_h"] = x.espera_cama_h - x.ult_actividad_h                     # horas desde la ultima toma o dx hasta la cama (NaN si no hubo ninguna)
    x["pct_espera_sin_actividad"] = 100 * x.sin_actividad_h / x.espera_cama_h
    x["tomas_por_dia"] = x.n_tomas / x.dias

    nombres = [g[0] for g in GRUPOS]
    # ---- 1. resumen por grupo
    decir("\n1. RESUMEN POR GRUPO DE ESPERA")
    r = x.groupby("grupo", observed=True).agg(n=("espera_cama_h", "size"), espera_mediana_h=("espera_cama_h", "median"), edad_mediana=("edad", "median"),
                                              pct_con_lab=("con_lab", lambda s: 100 * s.mean()), pct_con_dx=("con_dx", lambda s: 100 * s.mean()),
                                              pct_con_alguna_actividad=("con_actividad", lambda s: 100 * s.mean()),
                                              bloques_tu_media=("n_bloques_tu", "mean"), bloques_er_media=("n_bloques_er", "mean")).reindex(nombres).round(1)
    decir(r.to_string())
    r.to_csv(TABLAS / "tu_grupos_resumen.csv")

    # ---- 2. actividad (solo quienes tienen actividad), en tasas
    decir("\n2. ACTIVIDAD CLINICA DENTRO DE LA ESPERA (tasas por dia de espera; entre quienes tienen al menos un laboratorio)")
    a = x[x.con_lab].groupby("grupo", observed=True).agg(n=("n_tomas", "size"), tomas_mediana=("n_tomas", "median"), tomas_por_dia_mediana=("tomas_por_dia", "median"),
                                                          examenes_distintos_mediana=("n_examenes", "median"), h_primera_toma_mediana=("h_primera_toma", "median"),
                                                          h_ultima_toma_mediana=("h_ultima_toma", "median")).reindex(nombres).round(2)
    decir(a.to_string())
    a.to_csv(TABLAS / "tu_grupos_actividad.csv")

    # ---- 3. mismas primeras horas para todos los que siguen esperando
    decir("\n3. LAS PRIMERAS 6 Y 12 H (misma ventana para todos los que siguen esperando a esas horas)")
    filas = []
    toma_h = toma.set_index("estancia_id")
    for ventana in (6, 12):
        s = x[x.espera_cama_h > ventana]
        tt = toma[toma.estancia_id.isin(s.index) & (toma.h < ventana)].groupby("estancia_id").size().reindex(s.index).fillna(0)
        dd = D[D.estancia_id.isin(s.index) & (D.h_primero < ventana)].groupby("estancia_id").condition_concept_id.apply(lambda v: int((v != 0).sum())).reindex(s.index).fillna(0)
        t2 = pd.DataFrame({"grupo": s.grupo, "tomas": tt, "con_lab": tt > 0, "dx": dd, "con_dx": dd > 0})
        g = t2.groupby("grupo", observed=True).agg(n=("tomas", "size"), pct_con_lab=("con_lab", lambda v: 100 * v.mean()), tomas_media=("tomas", "mean"),
                                                   pct_con_dx=("con_dx", lambda v: 100 * v.mean()), dx_conceptos_media=("dx", "mean")).reindex([n for n in nombres if n in set(t2.grupo)]).round(2)
        g.insert(0, "ventana_h", ventana)
        filas.append(g.reset_index())
        decir(f"  primeras {ventana} h (solo los que siguen esperando a las {ventana} h):")
        decir(g.drop(columns="ventana_h").to_string())
    pd.concat(filas).to_csv(TABLAS / "tu_primeras_horas.csv", index=False)

    # ---- 4. tiempo sin actividad antes de la cama (solo laboratorios: el diagnostico se registra justo antes de la cama y no mide inactividad)
    decir("\n4. TIEMPO SIN LABORATORIOS ANTES DE LA CAMA (horas desde la ultima toma hasta la asignacion; solo estancias con al menos una toma)")
    x["sin_lab_h"] = x.espera_cama_h - x.h_ultima_toma
    x["pct_espera_sin_lab"] = 100 * x.sin_lab_h / x.espera_cama_h
    s4 = x[x.con_lab].groupby("grupo", observed=True).agg(n=("sin_lab_h", "size"), espera_mediana_h=("espera_cama_h", "median"), sin_lab_mediana_h=("sin_lab_h", "median"),
                                                          sin_lab_p75_h=("sin_lab_h", lambda v: v.quantile(.75)), pct_de_la_espera_sin_lab_mediana=("pct_espera_sin_lab", "median"),
                                                          pct_con_mas_de_12h_sin_lab=("sin_lab_h", lambda v: 100 * (v > 12).mean()),
                                                          pct_con_mas_de_24h_sin_lab=("sin_lab_h", lambda v: 100 * (v > 24).mean())).reindex(nombres).round(1)
    decir(s4.to_string())
    s4.to_csv(TABLAS / "tu_sin_actividad.csv")
    sin = x[~x.con_lab].groupby("grupo", observed=True).size().reindex(nombres)
    decir("  Estancias SIN ninguna toma de laboratorio en la espera: " + ", ".join(f"{k}: {int(v)}" for k, v in sin.items()))
    dx_t = x[x.con_dx].groupby("grupo", observed=True).agg(n=("h_primer_dx", "size"), h_primer_dx_mediana=("h_primer_dx", "median"), h_ultimo_dx_antes_de_la_cama_mediana=("h_ultimo_dx", lambda v: np.nan))
    dx_t["h_ultimo_dx_antes_de_la_cama_mediana"] = (x[x.con_dx].espera_cama_h - x[x.con_dx].h_ultimo_dx).groupby(x[x.con_dx].grupo, observed=True).median()
    decir("  Diagnosticos: hora del primero desde la llegada y horas entre el ultimo y la cama (se registran cerca de la cama):")
    decir(dx_t.reindex(nombres).round(2).to_string())

    # ---- 6. intensidad de laboratorios por tramo de la espera
    decir("\n6. INTENSIDAD DE LABORATORIOS SEGUN EL TRAMO DE LA ESPERA (tomas por 10 horas-paciente, entre todas las estancias que siguen esperando en ese tramo)")
    tramos = [(0, 6), (6, 12), (12, 24), (24, 48), (48, 72), (72, 120)]
    f6 = []
    for nombre in nombres:
        g = x[x.grupo == nombre]
        for a, b in tramos:
            sub = g[g.espera_cama_h > a]
            if len(sub) < 100:
                continue
            expo = (np.minimum(sub.espera_cama_h, b) - a).sum()
            n_t = toma[toma.estancia_id.isin(sub.index) & (toma.h >= a) & (toma.h < b) & (toma.h < toma.estancia_id.map(sub.espera_cama_h).fillna(0))].shape[0]
            pct = 100 * toma[toma.estancia_id.isin(sub.index) & (toma.h >= a) & (toma.h < b)].estancia_id.nunique() / len(sub)
            f6.append({"grupo": nombre, "tramo_h": f"{a}-{b}", "n_estancias": len(sub), "tomas_por_10h_paciente": round(10 * n_t / expo, 2), "pct_con_alguna_toma_en_el_tramo": round(pct, 1)})
    t6 = pd.DataFrame(f6)
    decir(t6.pivot(index="tramo_h", columns="grupo", values="tomas_por_10h_paciente").reindex([f"{a}-{b}" for a, b in tramos]).to_string())
    decir("  % de las estancias que siguen esperando con alguna toma en el tramo:")
    decir(t6.pivot(index="tramo_h", columns="grupo", values="pct_con_alguna_toma_en_el_tramo").reindex([f"{a}-{b}" for a, b in tramos]).to_string())
    t6.to_csv(TABLAS / "tu_intensidad_por_tramo.csv", index=False)

    # ---- 5. dentro de un mismo diagnostico
    decir("\n5. DENTRO DEL MISMO GRUPO DE DIAGNOSTICO: B (12-48 h) frente a C (> 72 h)")
    top = x.categoria_dx.value_counts().head(8).index
    f5 = []
    for cat in top:
        g = x[(x.categoria_dx == cat) & x.grupo.isin(["B  12-48 h", "C  > 72 h"])]
        for nombre, gg in g.groupby("grupo", observed=True):
            f5.append({"categoria_dx": cat, "grupo": nombre, "n": len(gg), "pct_con_lab": round(100 * gg.con_lab.mean(), 1), "tomas_por_dia_mediana": round(gg[gg.con_lab].tomas_por_dia.median(), 2) if gg.con_lab.any() else np.nan,
                       "sin_lab_mediana_h": round(gg[gg.con_lab].sin_lab_h.median(), 1) if gg.con_lab.any() else np.nan, "bloques_tu_media": round(gg.n_bloques_tu.mean(), 2)})
    t5 = pd.DataFrame(f5)
    decir(t5.to_string(index=False))
    t5.to_csv(TABLAS / "tu_por_diagnostico.csv", index=False)

    # ---- 7. espera segun la CANTIDAD de actividad (TU como un bloque)
    decir("\n7. ESPERA RESTANTE SEGUN LA CANTIDAD DE ACTIVIDAD EN LAS PRIMERAS 6 H (TU como un bloque; solo estancias que siguen esperando a las 6 h)")
    dd6 = D[D.h_primero < 6].groupby("estancia_id").condition_concept_id.apply(lambda v: int((v != 0).sum()))
    tt6 = toma[toma.h < 6].groupby("estancia_id").size()
    z = x[x.espera_cama_h > 6].copy()
    z["tomas_6h"], z["dx_6h"] = tt6.reindex(z.index).fillna(0), dd6.reindex(z.index).fillna(0)
    z["restante_h"] = z.espera_cama_h - 6
    z["f_tomas"] = pd.cut(z.tomas_6h, [-1, 0, 2, 5, 1e9], labels=["0", "1-2", "3-5", "6 o mas"])
    z["f_dx"] = pd.cut(z.dx_6h, [-1, 0, 1, 1e9], labels=["0", "1", "2 o mas"])
    z["f_proc"] = pd.cut(z.n_proc_distintos, [-1, 5, 9, 14, 1e9], labels=["0-5", "6-9", "10-14", "15 o mas"])
    filas7 = []
    for col, nombre, nota in [("f_tomas", "tomas de laboratorio en las primeras 6 h", ""), ("f_dx", "diagnosticos distintos registrados en las primeras 6 h", ""),
                              ("f_proc", "procedimientos distintos de la visita (toda la visita, no solo la espera)", " - cuentan tambien los de la hospitalizacion")]:
        r = z.groupby(col, observed=True).agg(n=("restante_h", "size"), restante_mediana_h=("restante_h", "median"), restante_p75_h=("restante_h", lambda v: v.quantile(.75)),
                                              restante_p90_h=("restante_h", lambda v: v.quantile(.9)), pct_mas_24h=("restante_h", lambda v: 100 * (v > 24).mean()),
                                              edad_mediana=("edad", "median")).round(1)
        decir(f"  segun {nombre}{nota}:")
        decir(r.to_string())
        filas7.append(r.reset_index().rename(columns={col: "franja"}).assign(medida=nombre))
    pd.concat(filas7).to_csv(TABLAS / "tu_espera_segun_cantidad.csv", index=False)
    import statsmodels.formula.api as smf
    z["log_rest"] = np.log1p(z.restante_h)
    z["tomas_c"], z["dx_c"] = np.minimum(z.tomas_6h, 10), np.minimum(z.dx_6h, 5)
    z["proc_c"] = np.minimum(z.n_proc_distintos, 30) / 5
    z["hora_ll"] = z.ini_est.dt.hour
    z["tipo"] = z.tipo_visita
    z["gedad"] = z.grupo_edad.astype(str)
    z["mes"] = z.ini_est.dt.to_period("M").astype(str)
    m = smf.ols("log_rest ~ tomas_c + dx_c + C(gedad) + C(tipo) + C(hora_ll) + C(mes)", data=z).fit(cov_type="HC1")
    decir("  Efecto sobre la espera restante, controlando edad, tipo de visita, hora de llegada y mes: " + "; ".join(
        f"{n} {100 * (np.exp(m.params[v]) - 1):+.1f} % ({100 * (np.exp(m.conf_int().loc[v, 0]) - 1):+.1f} a {100 * (np.exp(m.conf_int().loc[v, 1]) - 1):+.1f})" for v, n in [("tomas_c", "por cada toma en las 6 h"), ("dx_c", "por cada diagnostico en las 6 h")]))
    (TABLAS / "tu_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")
    x.reset_index().to_parquet(PROC / "tu_por_estancia.parquet")


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    main()
