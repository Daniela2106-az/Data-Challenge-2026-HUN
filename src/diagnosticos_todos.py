"""
diagnosticos_todos.py  -  version 1 (10-nov-2026)
Espera de cama y estancia en cama para CADA diagnostico (concepto SNOMED) que aparece en las estancias, sin dejar ninguno por fuera, y por grupo de diagnostico.
(Antes solo se miraban los 16 grupos de mapeo_dx.csv y el diagnostico principal: docs/diagnosticos_y_tiempos.md.)

COMO SE ARMA
  - Estancias unicas hospitalizadas del periodo confiable (1-feb-2023 a 9-abr-2026), edad y sexo de la persona real. Espera = llegada a asignacion de cama.
    Estancia = de la asignacion de cama al alta (fin_hosp_est), solo estancias con alta registrada antes del 10-abr-2026.
  - Cada estancia "tiene" un diagnostico si lo trae alguna de sus visitas (los registros gemelos se unen, regla de docs/CONTEXTO_TECNICO.md 4.7) Y la persona dominante de los diagnosticos
    de esa visita (P02 de auditoria_bd) es la persona real de la estancia: asi se descartan los diagnosticos que son de la otra persona del par. Se cuentan TODOS los
    diagnosticos distintos de la estancia, no solo el principal. Los diagnosticos se registran en cualquier momento de la visita (no solo durante la espera).
  - Por diagnostico: n, espera (p25, mediana, p75, p90), estancia (p25, mediana, p75, p90), % de estancias de mas de 14 dias y el EFECTO AJUSTADO (porcentaje de cambio de la
    espera y de la estancia frente a las demas estancias, con edad, sexo, tipo de visita y ano en el modelo; log(espera + 1) y log(estancia)). Valor p con correccion de
    Benjamini-Hochberg sobre todos los diagnosticos con n >= 30. n < 30: se muestra el dato pero se marca "no interpretable".

SALIDAS (HUN_TABLAS): dx_todos_espera_estancia.csv (todos los diagnosticos), dx_grupos_espera_estancia.csv (por grupo de mapeo_dx), dx_todos_resumen.txt
ENTRADAS tabla_episodios.parquet, episodios.csv (HUN_PROCESADOS); diagnosticos_por_visita.csv y auditoria_bd/P02_persona_de_los_diagnosticos.csv (HUN_CRUDOS)
COMO CORRERLO  python3 src/diagnosticos_todos.py   (1-2 min)
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parent.parent
PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
CRUDOS = Path(os.environ.get("HUN_CRUDOS", RAIZ / "datos" / "crudos"))
DESDE, HASTA = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10")
LINEAS = []


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def estancias():
    t = pd.read_parquet(PROC / "tabla_episodios.parquet")
    h = t[t.hospitalizado & t.estancia_unica & (t.ini_est >= DESDE) & (t.ini_est < HASTA) & t.edad.notna() & t.sexo.isin(["Mujer", "Hombre"])].copy()
    h["real"] = h.persona_real.fillna(h.person_id).astype(int)
    h["estancia_h"] = (h.fin_hosp_est - h.ini_hosp_est).dt.total_seconds() / 3600
    h.loc[(h.fin_hosp_est >= HASTA) | h.fin_hosp_est.isna() | (h.estancia_h <= 0), "estancia_h"] = np.nan
    h["anio"] = h.ini_est.dt.year.astype(str)
    return h.reset_index(drop=True)


def diagnosticos_de_la_estancia(h):
    e = pd.read_csv(PROC / "episodios.csv", usecols=["visit_occurrence_id", "estancia_id", "hospitalizado"])
    vis = e[e.hospitalizado & e.estancia_id.notna()][["visit_occurrence_id", "estancia_id"]].drop_duplicates()
    vis["estancia_id"] = vis.estancia_id.astype(int)
    # los diagnosticos tambien cuelgan de visitas COPIA (copias.csv: copia -> visita raiz); se llevan a la estancia de su raiz y despues se filtran por persona (P02)
    cop = pd.read_csv(PROC / "copias.csv", usecols=["visit_occurrence_id", "raiz_id"])
    cop = cop.merge(vis.rename(columns={"visit_occurrence_id": "raiz_id"}), on="raiz_id")[["visit_occurrence_id", "estancia_id"]]
    vis = pd.concat([vis, cop], ignore_index=True).drop_duplicates()
    d = pd.read_csv(CRUDOS / "diagnosticos_por_visita.csv", usecols=["visit_occurrence_id", "dx_concept_id", "dx_nombre"])
    p2 = pd.read_csv(CRUDOS / "auditoria_bd" / "P02_persona_de_los_diagnosticos.csv").sort_values("filas", ascending=False).drop_duplicates("visit_occurrence_id")
    d = d.merge(p2[["visit_occurrence_id", "person_id"]], on="visit_occurrence_id", how="left").merge(vis, on="visit_occurrence_id")
    d = d.merge(h[["estancia_id", "real"]], on="estancia_id")
    n0 = d.estancia_id.nunique()
    d = d[d.person_id == d.real]
    decir(f"  Estancias con algun diagnostico antes del filtro de persona: {n0:,}; despues: {d.estancia_id.nunique():,} de {len(h):,}")
    return d.drop_duplicates(["estancia_id", "dx_concept_id"])


def ajustado(y, X_ctrl, ind):
    """Efecto de 'ind' (0/1) sobre log(y) controlando X_ctrl (OLS con errores robustos HC1). Devuelve coeficiente, IC95 y valor p."""
    X = np.column_stack([np.ones(len(y)), ind, X_ctrl])
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ X.T @ y
    r = y - X @ b
    meat = (X * r[:, None]).T @ (X * r[:, None]) * len(y) / (len(y) - X.shape[1])
    cov = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(cov[1, 1])
    z = b[1] / se if se > 0 else 0.0
    return b[1], b[1] - 1.96 * se, b[1] + 1.96 * se, 2 * (1 - stats.norm.cdf(abs(z)))


def pct(b):
    return 100 * (np.exp(b) - 1)


def main():
    TABLAS.mkdir(parents=True, exist_ok=True)
    h = estancias()
    decir(f"DIAGNOSTICOS FRENTE A ESPERA Y ESTANCIA | {len(h):,} estancias unicas hospitalizadas (periodo confiable); con espera medida {int(h.espera_cama_h.notna().sum()):,}; con alta registrada {int(h.estancia_h.notna().sum()):,}")
    d = diagnosticos_de_la_estancia(h)
    h = h.set_index("estancia_id")
    ctrl = pd.get_dummies(h[["grupo_edad", "sexo", "tipo_visita", "anio"]].astype(str), drop_first=True).astype(float)
    y_esp = np.log1p(h.espera_cama_h.to_numpy())
    y_est = np.log(h.estancia_h.to_numpy())
    ok_e, ok_s = ~np.isnan(y_esp), ~np.isnan(y_est)
    ref_e, ref_s = h.espera_cama_h.median(), h.estancia_h.median()
    decir(f"  Referencia (todas las estancias): espera mediana {ref_e:.1f} h, estancia mediana {ref_s:.1f} h")
    idx_pos = {e: i for i, e in enumerate(h.index)}
    filas = []
    for (cid, nombre), g in d.groupby(["dx_concept_id", "dx_nombre"]):
        pos = np.array([idx_pos[e] for e in g.estancia_id])
        ind = np.zeros(len(h))
        ind[pos] = 1
        es, st = h.espera_cama_h.to_numpy()[pos], h.estancia_h.to_numpy()[pos]
        es, st = es[~np.isnan(es)], st[~np.isnan(st)]
        fila = {"dx_concept_id": cid, "diagnostico": nombre, "n_estancias": len(pos), "n_con_espera": len(es), "n_con_estancia": len(st), "interpretable_n_30": len(pos) >= 30}
        for nombre_m, v in [("espera", es), ("estancia", st)]:
            if len(v):
                for q, etq in [(.25, "p25"), (.5, "mediana"), (.75, "p75"), (.9, "p90")]:
                    fila[f"{nombre_m}_{etq}_h"] = round(float(np.quantile(v, q)), 1)
        if len(st):
            fila["pct_estancia_mas_14d"] = round(100 * float((st > 14 * 24).mean()), 1)
        if len(pos) >= 30:
            for nombre_m, y, ok in [("espera", y_esp, ok_e), ("estancia", y_est, ok_s)]:
                m = ok & ((ind == 1) | (ind == 0))
                if ind[m].sum() >= 20:
                    b, lo, hi, pv = ajustado(y[m], ctrl.to_numpy()[m], ind[m])
                    fila.update({f"{nombre_m}_efecto_ajustado_pct": round(pct(b), 1), f"{nombre_m}_ic95_bajo": round(pct(lo), 1), f"{nombre_m}_ic95_alto": round(pct(hi), 1), f"{nombre_m}_p": pv})
        filas.append(fila)
    t = pd.DataFrame(filas)
    for nombre_m in ("espera", "estancia"):
        col = f"{nombre_m}_p"
        v = t[col].dropna().sort_values()
        m = len(v)
        bh = (v * m / np.arange(1, m + 1))[::-1].cummin()[::-1].clip(upper=1)
        t.loc[bh.index, f"{nombre_m}_p_ajustado_BH"] = bh.round(5)
        t[f"{nombre_m}_significativo_BH05"] = t[f"{nombre_m}_p_ajustado_BH"] < 0.05
        t = t.drop(columns=col)
    mapeo = pd.read_csv(RAIZ / "datos" / "referencia" / "mapeo_dx.csv")
    t = t.merge(mapeo.rename(columns={"dx_nombre": "diagnostico", "categoria_dx": "grupo"}).drop_duplicates("diagnostico")[["diagnostico", "grupo"]], on="diagnostico", how="left")
    t = t.sort_values("n_estancias", ascending=False)
    t.to_csv(TABLAS / "dx_todos_espera_estancia.csv", index=False)
    decir(f"\n  Diagnosticos distintos: {len(t):,} (con n >= 30: {int(t.interpretable_n_30.sum()):,}; con 1 sola estancia: {int((t.n_estancias == 1).sum()):,})")

    # ---- por grupo de diagnostico (cada estancia cuenta en cada grupo que tenga)
    dg = d.merge(mapeo.rename(columns={"dx_nombre": "dx_nombre", "categoria_dx": "grupo"}).drop_duplicates("dx_nombre")[["dx_nombre", "grupo"]], on="dx_nombre", how="left").dropna(subset=["grupo"]).drop_duplicates(["estancia_id", "grupo"])
    filas = []
    for grupo, g in dg.groupby("grupo"):
        pos = np.array([idx_pos[e] for e in g.estancia_id])
        es, st = h.espera_cama_h.to_numpy()[pos], h.estancia_h.to_numpy()[pos]
        es, st = es[~np.isnan(es)], st[~np.isnan(st)]
        fila = {"grupo": grupo, "n_estancias": len(pos), "espera_mediana_h": round(float(np.median(es)), 1), "espera_p90_h": round(float(np.quantile(es, .9)), 1), "estancia_mediana_h": round(float(np.median(st)), 1),
                "estancia_p90_h": round(float(np.quantile(st, .9)), 1), "pct_estancia_mas_14d": round(100 * float((st > 336).mean()), 1)}
        ind = np.zeros(len(h))
        ind[pos] = 1
        for nombre_m, y, ok in [("espera", y_esp, ok_e), ("estancia", y_est, ok_s)]:
            b, lo, hi, pv = ajustado(y[ok], ctrl.to_numpy()[ok], ind[ok])
            fila.update({f"{nombre_m}_efecto_ajustado_pct": round(pct(b), 1), f"{nombre_m}_ic95": f"{pct(lo):+.0f} a {pct(hi):+.0f}"})
        filas.append(fila)
    tg = pd.DataFrame(filas).sort_values("espera_mediana_h", ascending=False)
    tg.to_csv(TABLAS / "dx_grupos_espera_estancia.csv", index=False)
    decir("\nPOR GRUPO DE DIAGNOSTICO (una estancia cuenta en cada grupo que tenga; efecto ajustado frente a las demas estancias, con edad, sexo, tipo de visita y ano)")
    decir(tg.to_string(index=False))

    ti = t[t.interpretable_n_30]
    decir(f"\nDIAGNOSTICOS CON n >= 30: {len(ti):,}. Significativos tras la correccion BH al 5 %: espera {int(ti.espera_significativo_BH05.sum())}, estancia {int(ti.estancia_significativo_BH05.sum())}")
    for col, etiqueta in [("espera_efecto_ajustado_pct", "ESPERA MAS LARGA"), ("estancia_efecto_ajustado_pct", "ESTANCIA MAS LARGA")]:
        sig = ti[ti[col.replace("efecto_ajustado_pct", "significativo_BH05")]]
        decir(f"\n{etiqueta} (efecto ajustado, solo significativos BH):")
        decir(sig.sort_values(col, ascending=False).head(15)[["diagnostico", "grupo", "n_estancias", col, "espera_mediana_h", "estancia_mediana_h"]].to_string(index=False))
        decir(f"{etiqueta.replace('MAS LARGA', 'MAS CORTA')}:")
        decir(sig.sort_values(col).head(15)[["diagnostico", "grupo", "n_estancias", col, "espera_mediana_h", "estancia_mediana_h"]].to_string(index=False))
    decir("\nLos 25 diagnosticos mas frecuentes:")
    decir(t.head(25)[["diagnostico", "grupo", "n_estancias", "espera_mediana_h", "espera_p90_h", "estancia_mediana_h", "estancia_p90_h", "pct_estancia_mas_14d"]].to_string(index=False))
    (TABLAS / "dx_todos_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    main()
