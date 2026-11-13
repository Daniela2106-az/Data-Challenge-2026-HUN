"""
prueba_banderas_persona.py  -  version 1 (11-nov-2026)
¿Cuanto suman las banderas de laboratorio de las primeras 6 h al estimador de tiempo restante (A6), con el cruce VIEJO (por visita, sin persona: sev_*.csv) y con el
cruce NUEVO (por visita y persona real: sevp_*.csv)? Y, de paso, ¿cuanto sumaban de verdad en este computador, donde hasta hoy no entraban?

MOTIVO (10-11 nov): el cruce viejo mezclaba los laboratorios de las dos personas de una estancia gemela y solo llevaba a la visita raiz las copias de la misma
  persona: 40 % de las estancias con algun valor, cuando con la persona real son 52 % (3.130 estancias recuperan sus propios laboratorios y 541 tenian solo los de
  la otra persona). Ademas comparar_estimadores.py buscaba los archivos solo en HUN_CRUDOS y aqui estan en HUN_CRUDOS/consultas: el modelo guardado decia
  con_laboratorio=False. Las cifras de "+1,1 puntos" de docs/estimador_tiempos.md 3.3 salieron de la corrida de Samuel (8-nov) con el cruce viejo.

COMO SE PRUEBA  Igual que comparar_estimadores.py (modelo fijo, sin peso a lo reciente) con dos origenes para ver la estabilidad: A) entrenar hasta dic-2024 y probar
  ene-jun 2025; B) entrenar hasta jun-2025 y probar jul-2025 a 9-abr-2026. Momentos 6, 12, 24 y 48 h de espera (las banderas entran desde las 6 h). Tres variantes con
  las mismas variables del estimador final: sin banderas; + banderas del cruce viejo; + banderas del cruce nuevo. A las 6 h, modelo del momento (landmark); desde las
  12 h, el modelo unico con historial (como el estimador final). Se mide la mejora frente al rango general, la diferencia pareada frente a "sin banderas" y entre los
  dos cruces (IC 95 % por bootstrap por semanas) y el % de casos debajo del p90 (calibracion). Tambien por subgrupo: estancias con y sin laboratorio segun el cruce nuevo.

SALIDAS (HUN_TABLAS): banderas_persona_estabilidad.csv (por variante), banderas_persona_nuevo_vs_viejo.csv, banderas_persona_resumen.txt
COMO CORRERLO  python3 src/prueba_banderas_persona.py   (15-25 min)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402

MOMENTOS = [6, 12, 24, 48]
ORIGENES = [("A: entrenar hasta dic-2024, probar ene-jun 2025", pd.Timestamp("2025-01-01"), pd.Timestamp("2025-07-01")),
            ("B: entrenar hasta jun-2025, probar jul-2025 a 9-abr-2026", pd.Timestamp("2025-07-01"), ce.HASTA)]
LAB_V = [c + "_viejo" for c in ce.LAB]
SIN, VIEJO, NUEVO = "sin banderas", "banderas, cruce viejo (por visita, sin persona)", "banderas, cruce nuevo (persona real)"
VARIANTES = [(SIN, []), (VIEJO, LAB_V), (NUEVO, list(ce.LAB))]
LINEAS = []


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def cols_base(c):
    """Variables del estimador final sin las banderas."""
    return list(ce.COLS_M1_FINAL) if c < ce.HORAS_RECORRIDO else list(ce.COLS_M1_BASE + ce.HIST)


def main():
    ce.TABLAS.mkdir(parents=True, exist_ok=True)
    d, h, rejilla, estado = ce.preparar()
    if not (ce.HAY_LAB and str(ce.ORIGEN_LAB).startswith("sevp")):
        raise SystemExit(f"hacen falta los sevp_*.csv (cruce por persona); origen actual: {ce.ORIGEN_LAB}")
    t = pd.read_parquet(ce.PROC / "tabla_episodios.parquet")
    V = ce.valores_lab_por_estancia(t, False)
    if V is None:
        raise SystemExit("hacen falta los sev_*.csv (cruce viejo) para comparar")
    bv = ce.banderas_desde_valores(V).assign(con_laboratorio_6h=1.0)
    bv.columns = LAB_V
    d = d.merge(bv, left_on="estancia_id", right_index=True, how="left")
    d[LAB_V] = d[LAB_V].fillna(0.0)
    decir("BANDERAS DE LABORATORIO EN EL ESTIMADOR: CRUCE VIEJO (sin persona) FRENTE AL NUEVO (persona real); modelo fijo, dos origenes")
    decir(f"estancias {len(d):,}: con algun valor en las 6 h segun el cruce viejo {d.con_laboratorio_6h_viejo.mean():.1%}, segun el nuevo {d.con_laboratorio_6h.mean():.1%}")
    filas, filas2 = [], []
    for nombre_o, ini, fin in ORIGENES:
        tr = d[d.ini_est < ini].reset_index(drop=True)
        te = d[(d.ini_est >= ini) & (d.ini_est < fin)].reset_index(drop=True)
        decir(f"\n{nombre_o}: entrenamiento {len(tr):,} | prueba {len(te):,} estancias")
        m12 = {n: ce.entrenar_m1(tr, rejilla, estado, cols_base(ce.HORAS_RECORRIDO) + extra) for n, extra in VARIANTES}
        for c in MOMENTOS:
            sub = te[te.espera_cama_h > c].reset_index(drop=True)
            y = np.minimum(sub.espera_cama_h.to_numpy() - c, ce.MAX_H)
            general, _ = ce.referencias(tr, sub, c)
            l_gen = ce.perdida_por_caso(y, general)
            semana = sub.ini_est.dt.to_period("W").astype(str).to_numpy()
            perd, p90 = {}, {}
            for n, extra in VARIANTES:
                m = ce.entrenar_landmark(tr, rejilla, estado, c, cols=cols_base(c) + extra) if c < ce.HORAS_RECORRIDO else m12[n]
                pred = ce.predecir_m1(m, sub, rejilla, estado, c)
                perd[n] = ce.perdida_por_caso(y, pred)
                p90[n] = y <= pred[:, -1]
            lab = sub.con_laboratorio_6h.to_numpy() == 1
            for g, mk in [("todas", np.ones(len(sub), bool)), ("con laboratorio (cruce nuevo)", lab), ("sin laboratorio (cruce nuevo)", ~lab)]:
                for n, _ in VARIANTES:
                    lo, hi = ce.intervalo_mejora(semana[mk], perd[n][mk], perd[SIN][mk]) if n != SIN else (0.0, 0.0)
                    filas.append({"origen": nombre_o[0], "horas_esperando": c, "grupo": g, "variante": n, "n": int(mk.sum()),
                                  "mejora_vs_general_pct": round(100 * (1 - perd[n][mk].mean() / l_gen[mk].mean()), 2),
                                  "diferencia_vs_sin_banderas_pct": round(100 * (1 - perd[n][mk].mean() / perd[SIN][mk].mean()), 2),
                                  "ic95_bajo": round(lo, 2), "ic95_alto": round(hi, 2), "pct_debajo_p90": round(100 * p90[n][mk].mean(), 1)})
                lo, hi = ce.intervalo_mejora(semana[mk], perd[NUEVO][mk], perd[VIEJO][mk])
                filas2.append({"origen": nombre_o[0], "horas_esperando": c, "grupo": g, "n": int(mk.sum()),
                               "nuevo_mejor_que_viejo_pct": round(100 * (1 - perd[NUEVO][mk].mean() / perd[VIEJO][mk].mean()), 2), "ic95_bajo": round(lo, 2), "ic95_alto": round(hi, 2)})
            f = [x for x in filas if x["origen"] == nombre_o[0] and x["horas_esperando"] == c and x["grupo"] == "todas"]
            decir(f"  {c:>2} h (n={len(sub):,}): sin banderas {f[0]['mejora_vs_general_pct']:+.2f} % | cruce viejo {f[1]['mejora_vs_general_pct']:+.2f} % "
                  f"(dif {f[1]['diferencia_vs_sin_banderas_pct']:+.2f}, IC {f[1]['ic95_bajo']:+.2f} a {f[1]['ic95_alto']:+.2f}) | cruce nuevo {f[2]['mejora_vs_general_pct']:+.2f} % "
                  f"(dif {f[2]['diferencia_vs_sin_banderas_pct']:+.2f}, IC {f[2]['ic95_bajo']:+.2f} a {f[2]['ic95_alto']:+.2f}) | debajo del p90: {f[0]['pct_debajo_p90']} / {f[1]['pct_debajo_p90']} / {f[2]['pct_debajo_p90']} %")
    t1, t2 = pd.DataFrame(filas), pd.DataFrame(filas2)
    t1.to_csv(ce.TABLAS / "banderas_persona_estabilidad.csv", index=False)
    t2.to_csv(ce.TABLAS / "banderas_persona_nuevo_vs_viejo.csv", index=False)
    decir("\nRESUMEN: puntos de mejora que suman las banderas frente a 'sin banderas' (todas las estancias)")
    decir(t1[t1.grupo == "todas"].pivot_table(index="horas_esperando", columns=["origen", "variante"], values="diferencia_vs_sin_banderas_pct").round(2).to_string())
    decir("\nRESUMEN: lo mismo, solo entre las estancias CON laboratorio segun el cruce nuevo")
    decir(t1[t1.grupo == "con laboratorio (cruce nuevo)"].pivot_table(index="horas_esperando", columns=["origen", "variante"], values="diferencia_vs_sin_banderas_pct").round(2).to_string())
    decir("\nRESUMEN: cruce nuevo frente al viejo (positivo = el nuevo estima mejor), con IC 95 %")
    decir(t2[t2.grupo == "todas"].to_string(index=False))
    (ce.TABLAS / "banderas_persona_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    main()
