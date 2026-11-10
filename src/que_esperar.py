"""
que_esperar.py  -  version 1 (10-nov-2026)
"Que esperar segun el paciente": dado un perfil (edad, sexo, tipo de visita y, si se conoce, el grupo de diagnostico), la espera de cama y la estancia en cama de pacientes
parecidos, como RANGOS (percentiles 25, 50, 75 y 90), nunca como un valor unico. Las tablas son para el dashboard; la funcion `que_esperar()` es la consulta.

COMO FUNCIONA
  - Base: estancias unicas hospitalizadas del periodo confiable (1-feb-2023 a 9-abr-2026), edad y sexo de la persona real (CLAUDE.md 4.10). Espera = llegada a asignacion de cama.
    Estancia = de la asignacion de cama al alta (solo estancias con alta registrada antes del 10-abr-2026).
  - Rango del perfil: percentiles de las estancias del mismo grupo de edad, sexo y tipo de visita (y del mismo grupo de diagnostico si se da). Si el grupo tiene menos de 30
    estancias se sube un nivel (se quita primero el sexo, luego el tipo de visita, luego el diagnostico, luego la edad) y se dice con cuanto detalle se calculo.
  - "Raza" y "etnicidad" NO se usan: en PERSON el 95 % de la raza esta sin dato y la etnicidad es casi toda "Hispanic or Latino" (CLAUDE.md seccion 3). El perfil queda en edad, sexo y tipo de visita.
  - Procedimientos y laboratorios NO entran al perfil: los procedimientos no tienen hora y su cantidad crece con la estancia (causalidad inversa); los laboratorios solo se conocen despues de llegar
    (su aporte a la espera esta en docs/prueba_ultima_etapa.md).

CUANTO VALE ESTE PERFIL (prueba temporal: se calculan los rangos con las llegadas hasta jun-2025 y se aplican a jul-2025 a 9-abr-2026)
  Mejora frente a dar a todos el mismo rango (perdida de cuantiles, IC 95 % por bootstrap de semanas), para: edad x sexo x tipo de visita; + grupo de diagnostico principal.

SALIDAS (HUN_TABLAS): que_esperar_perfiles.csv (edad x sexo x tipo), que_esperar_dx.csv (grupo de diagnostico x edad), que_esperar_evaluacion.csv, que_esperar_resumen.txt
COMO CORRERLO  python3 src/que_esperar.py   (1 min). Consulta: from que_esperar import que_esperar; que_esperar(67, "Mujer", "Urgencias", "Digestivo")
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
DESDE, HASTA, CORTE = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10"), pd.Timestamp("2025-07-01")
Q = [0.25, 0.5, 0.75, 0.9]
MIN_N = 30
EDADES = ["0-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+"]
LINEAS = []


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def cargar():
    t = pd.read_parquet(PROC / "tabla_episodios.parquet")
    h = t[t.hospitalizado & t.estancia_unica & (t.ini_est >= DESDE) & (t.ini_est < HASTA) & t.edad.notna() & t.sexo.isin(["Mujer", "Hombre"]) & t.espera_cama_h.notna()].copy()
    h["estancia_h"] = (h.fin_hosp_est - h.ini_hosp_est).dt.total_seconds() / 3600
    h.loc[(h.fin_hosp_est >= HASTA) | h.fin_hosp_est.isna() | (h.estancia_h <= 0), "estancia_h"] = np.nan
    h["grupo_edad"] = h.grupo_edad.astype(str)
    h["dx"] = h.categoria_dx.fillna("sin diagnostico")
    return h.reset_index(drop=True)


NIVELES = [("edad + sexo + tipo de visita + diagnostico", ["grupo_edad", "sexo", "tipo_visita", "dx"]), ("edad + tipo de visita + diagnostico", ["grupo_edad", "tipo_visita", "dx"]),
           ("edad + diagnostico", ["grupo_edad", "dx"]), ("edad + sexo + tipo de visita", ["grupo_edad", "sexo", "tipo_visita"]), ("edad + tipo de visita", ["grupo_edad", "tipo_visita"]),
           ("edad", ["grupo_edad"]), ("todos", [])]


def rangos(g, col, nombre):
    v = g[col].dropna().to_numpy()
    return {f"{nombre}_p{int(q * 100)}_h": round(float(np.quantile(v, q)), 1) for q in Q} | {f"n_{nombre}": len(v)}


def rango_para(base, perfil, con_dx):
    """Primer nivel (de mas a menos detalle) con al menos MIN_N estancias con espera y con estancia."""
    for nombre, cols in NIVELES:
        if not con_dx and "dx" in cols:
            continue
        m = np.ones(len(base), bool)
        for c in cols:
            m &= (base[c] == perfil[c]).to_numpy()
        g = base[m]
        if g.estancia_h.notna().sum() >= MIN_N and len(g) >= MIN_N:
            return nombre, g
    return "todos", base


def perdida_por_caso(y, pred):
    e = y[:, None] - pred
    return np.maximum(np.array(Q) * e, (np.array(Q) - 1) * e).sum(axis=1)


def evaluar(h):
    decir("\nCUANTO VALE EL PERFIL (rangos con llegadas hasta jun-2025, aplicados a jul-2025 a 9-abr-2026)")
    tr, te = h[h.ini_est < CORTE], h[h.ini_est >= CORTE]
    filas = []
    for variable, col, etiqueta in [("espera", "espera_cama_h", "espera de cama"), ("estancia", "estancia_h", "estancia en cama")]:
        tr_v, te_v = tr[tr[col].notna()], te[te[col].notna()]
        y = te_v[col].to_numpy()
        general = np.tile(np.quantile(tr_v[col], Q), (len(te_v), 1))
        l_gen = perdida_por_caso(y, general)
        semana = te_v.ini_est.dt.to_period("W").astype(str).to_numpy()
        for nombre, cols in [("edad", ["grupo_edad"]), ("edad + sexo + tipo de visita", ["grupo_edad", "sexo", "tipo_visita"]), ("edad + sexo + tipo de visita + diagnostico", ["grupo_edad", "sexo", "tipo_visita", "dx"])]:
            claves = tr_v.groupby(cols)[col].apply(lambda s: np.quantile(s, Q) if len(s) >= MIN_N else None).dropna()
            pred = np.array([claves.get(tuple(r) if len(cols) > 1 else r[0], general[0]) for r in te_v[cols].itertuples(index=False, name=None)])
            l = perdida_por_caso(y, pred)
            rng = np.random.default_rng(7)
            u = np.unique(semana)
            idx = {s: np.where(semana == s)[0] for s in u}
            mej = []
            for _ in range(500):
                ss = rng.choice(u, len(u))
                ii = np.concatenate([idx[s] for s in ss])
                mej.append(100 * (1 - l[ii].mean() / l_gen[ii].mean()))
            fila = {"variable": etiqueta, "perfil": nombre, "n_prueba": len(te_v), "mejora_vs_mismo_rango_pct": round(100 * (1 - l.mean() / l_gen.mean()), 1),
                    "ic95_bajo": round(float(np.percentile(mej, 2.5)), 1), "ic95_alto": round(float(np.percentile(mej, 97.5)), 1)}
            for j, q in enumerate(Q):
                fila[f"pct_debajo_p{int(q * 100)}"] = round(100 * float(np.mean(y <= pred[:, j])), 1)
            filas.append(fila)
    t = pd.DataFrame(filas)
    decir(t.to_string(index=False))
    t.to_csv(TABLAS / "que_esperar_evaluacion.csv", index=False)


def main():
    TABLAS.mkdir(parents=True, exist_ok=True)
    h = cargar()
    decir(f"QUE ESPERAR SEGUN EL PACIENTE | {len(h):,} estancias unicas hospitalizadas con espera medida; con estancia medida {int(h.estancia_h.notna().sum()):,}")
    decir(f"  Referencia: espera mediana {h.espera_cama_h.median():.1f} h (p90 {h.espera_cama_h.quantile(.9):.1f}); estancia mediana {h.estancia_h.median():.1f} h (p90 {h.estancia_h.quantile(.9):.1f})")
    # ---- tabla de perfiles edad x sexo x tipo
    filas = []
    for (e, s, t_), g in h.groupby(["grupo_edad", "sexo", "tipo_visita"]):
        filas.append({"grupo_edad": e, "sexo": s, "tipo_visita": t_, "n_estancias": len(g), "interpretable": len(g) >= MIN_N, **rangos(g, "espera_cama_h", "espera"), **rangos(g, "estancia_h", "estancia")})
    t1 = pd.DataFrame(filas)
    t1.to_csv(TABLAS / "que_esperar_perfiles.csv", index=False)
    decir(f"\n  Perfiles edad x sexo x tipo de visita: {len(t1)}; interpretables (n >= {MIN_N}): {int(t1.interpretable.sum())}")
    # ---- grupo de diagnostico x edad
    filas = []
    for (d, e), g in h.groupby(["dx", "grupo_edad"]):
        filas.append({"grupo_diagnostico": d, "grupo_edad": e, "n_estancias": len(g), "interpretable": len(g) >= MIN_N, **rangos(g, "espera_cama_h", "espera"), **rangos(g, "estancia_h", "estancia")})
    t2 = pd.DataFrame(filas)
    t2.to_csv(TABLAS / "que_esperar_dx.csv", index=False)
    decir(f"  Grupo de diagnostico x edad: {len(t2)}; interpretables: {int(t2.interpretable.sum())}")
    evaluar(h)
    # ---- ejemplos
    decir("\nEJEMPLOS de consulta (rangos de pacientes parecidos; espera de cama y estancia en cama, horas)")
    ejemplos = [(67, "Mujer", "Urgencias", None), (67, "Mujer", "Urgencias", "Digestivo"), (67, "Hombre", "Urgencias", "Cardiovascular"), (8, "Hombre", "Urgencias", "Respiratorio"),
                (30, "Mujer", "Urgencias", "Embarazo, parto y ginecologia"), (80, "Hombre", "Treatment urgency", None)]
    for ed, sx, tv, dx in ejemplos:
        r = que_esperar(ed, sx, tv, dx, base=h)
        decir(f"  {ed} anos, {sx}, {tv}" + (f", {dx}" if dx else "") + f": espera {r['espera_p25_h']:.0f} / {r['espera_p50_h']:.0f} / {r['espera_p75_h']:.0f} / {r['espera_p90_h']:.0f} h; "
              f"estancia {r['estancia_p25_h']:.0f} / {r['estancia_p50_h']:.0f} / {r['estancia_p75_h']:.0f} / {r['estancia_p90_h']:.0f} h (n = {r['n_estancias']}; detalle: {r['nivel_de_detalle']})")
    (TABLAS / "que_esperar_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")


_BASE = {}


def que_esperar(edad, sexo, tipo_visita, grupo_diagnostico=None, base=None):
    """Rango de espera de cama y de estancia en cama de pacientes parecidos (percentiles 25, 50, 75 y 90, en horas).
    sexo: 'Mujer' u 'Hombre'; tipo_visita: 'Urgencias', 'Treatment urgency' o 'Ambulatorio'; grupo_diagnostico: uno de datos/referencia/mapeo_dx.csv (opcional)."""
    if base is None:
        if "h" not in _BASE:
            _BASE["h"] = cargar()
        base = _BASE["h"]
    ge = str(pd.cut([edad], [-1, 4, 14, 29, 44, 59, 74, 200], labels=EDADES)[0])
    perfil = {"grupo_edad": ge, "sexo": sexo, "tipo_visita": tipo_visita, "dx": grupo_diagnostico or "sin diagnostico"}
    nivel, g = rango_para(base, perfil, con_dx=grupo_diagnostico is not None)
    return {**rangos(g, "espera_cama_h", "espera"), **rangos(g, "estancia_h", "estancia"), "n_estancias": len(g), "nivel_de_detalle": nivel,
            "aviso": "Rango de pacientes parecidos, no una promesa individual. Solo para pacientes con orden de hospitalizacion. La estancia se describe, no se predice."}


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    main()
