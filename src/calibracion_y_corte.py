"""
calibracion_y_corte.py  -  version 1 (9-nov-2026)
Tarea A6: dos arreglos del estimador de tiempo restante que pidio la revision (docs/estimador_tiempos.md, seccion 7):
  1. EL CORTE DE 12 H SE ELIGIO MIRANDO LA PRUEBA. Aqui se elige con un periodo de validacion aparte.
  2. EL PERCENTIL 90 SE QUEDA CORTO (cubre 87-88 % en vez de 90 %). Aqui se calibra con el mismo periodo de validacion.

COMO SE EVITA MIRAR LA PRUEBA
  entrenamiento A : feb-2023 a dic-2024
  validacion      : ene-2025 a jun-2025   (aqui se elige el corte y se calibra el p90)
  prueba          : jul-2025 a 9-abr-2026 (NO se usa para elegir nada; solo se mide al final con lo ya decidido)
  Para medir la prueba se vuelven a entrenar los modelos con A + validacion (todo antes de jul-2025), como en comparar_estimadores.py y en el modelo
  que se consulta; el nivel calibrado sale de la validacion y se aplica tal cual.

QUE HACE
  Paso 1 (corte). Para cada corte candidato (6, 9, 12, 18, 24 h) compara, en la validacion, el modelo por momento (con el recorrido en urgencias) contra
  el modelo unico con solo el historial, en esa hora de espera. Se elige el corte mas bajo en el que el modelo por momento ya NO es mejor de forma clara
  (el limite inferior del intervalo de 95 % de su ventaja, por bootstrap de semanas, no supera 0).
  Paso 2 (p90). Con el corte elegido, en la validacion se busca el nivel mas bajo (0,90, 0,91, ...) cuyo percentil deja por debajo al menos el 90 % de los
  casos, juntando las horas de espera 0, 3, 6, 12, 24 y 48. Ese nivel se usa para el p90 que se muestra.
  Paso 3 (prueba). Con el corte y el nivel ya elegidos se mide la prueba: mejora frente al rango general y porcentaje por debajo de cada percentil,
  con el p90 sin calibrar y calibrado.

SALIDAS (HUN_TABLAS): calibracion_corte_paso1.csv, calibracion_corte_paso2.csv, calibracion_corte_paso3.csv, calibracion_corte_resumen.txt
COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... HUN_CRUDOS=... python3 src/calibracion_y_corte.py   (unos 20-30 min)
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402

INI_VALIDACION = pd.Timestamp("2025-01-01")
CANDIDATOS = [int(x) for x in os.environ.get("CANDIDATOS", "6,9,12,18,24").split(",")]
SOLO_PASO1 = os.environ.get("SOLO_PASO1", "0") == "1"      # 1 = solo elegir el corte (para probar candidatos mas altos)
HORAS_P90 = [0, 3, 6, 12, 24, 48]
NIVELES = np.round(np.arange(0.90, 0.9801, 0.01), 2)
VIDA_MEDIA_DIAS = 182
LINEAS = []


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def supervivencia(m, d, rejilla, estado, desde):
    """S[:, k] = probabilidad de seguir esperando k horas despues de 'desde' (igual que predecir_m1, pero devuelve la supervivencia)."""
    X, _, _ = ce.filas_persona_hora(d, rejilla, estado, desde=desde, fijar_estado=True, cols=m.cols_, retraso_h=getattr(m, "retraso_h_", 0.0))
    p = m.predict_proba(X[m.cols_])[:, 1].reshape(len(d), ce.MAX_H - desde)
    return np.hstack([np.ones((len(d), 1)), np.cumprod(1 - p, axis=1)])


def cols_unico():
    return ce.COLS_M1_BASE + ce.HIST + (ce.LAB if ce.HAY_LAB else [])


def cols_momento(h):
    return ce.COLS_M1_FINAL + (ce.LAB if ce.HAY_LAB and h >= ce.HORAS_LAB else [])


def casos(d, desde):
    sub = d[d.espera_cama_h > desde].reset_index(drop=True)
    return sub, np.minimum(sub.espera_cama_h.to_numpy() - desde, ce.MAX_H)


def paso1(tr, va, rejilla, estado):
    decir("PASO 1. ¿Desde que hora el recorrido en urgencias ya no suma? (validacion ene-jun 2025, modelos entrenados hasta dic-2024)")
    unico = ce.entrenar_m1(tr, rejilla, estado, cols_unico(), vida_media_dias=VIDA_MEDIA_DIAS)
    filas = []
    for h in CANDIDATOS:
        momento = ce.entrenar_landmark(tr, rejilla, estado, h, cols=cols_momento(h), vida_media_dias=VIDA_MEDIA_DIAS)
        sub, y = casos(va, h)
        l_mom = ce.perdida_por_caso(y, ce.cuantiles_de_supervivencia(supervivencia(momento, sub, rejilla, estado, h)))
        l_uni = ce.perdida_por_caso(y, ce.cuantiles_de_supervivencia(supervivencia(unico, sub, rejilla, estado, h)))
        semana = sub.ini_est.dt.to_period("W").astype(str).to_numpy()
        lo, hi = ce.intervalo_mejora(semana, l_mom, l_uni)          # ventaja del modelo por momento sobre el unico (positiva = por momento mejor)
        filas.append({"hora": h, "n_validacion": len(sub), "ventaja_por_momento_pct": round(100 * (1 - l_mom.mean() / l_uni.mean()), 2),
                      "ic95_bajo": round(lo, 2), "ic95_alto": round(hi, 2), "por_momento_mejor_claro": bool(lo > 0)})
        decir(f"  {h:>2} h: ventaja del modelo por momento {filas[-1]['ventaja_por_momento_pct']:+.2f} % (IC95 {lo:+.2f} a {hi:+.2f}), n={len(sub):,}")
    tabla = pd.DataFrame(filas)
    sin_ventaja = tabla[~tabla.por_momento_mejor_claro]
    corte = int(sin_ventaja.hora.min()) if len(sin_ventaja) else None
    decir(f"  -> corte elegido en validacion: {corte} h" if corte else "  -> el modelo por momento gana en todos los candidatos: no hay corte en esta lista")
    return tabla, corte, unico


def modelos_por_hora(tr, rejilla, estado, corte, unico):
    """Modelo que se usaria en cada hora de HORAS_P90 con el corte elegido."""
    out = {}
    for h in HORAS_P90:
        out[h] = unico if h >= corte else ce.entrenar_landmark(tr, rejilla, estado, h, cols=cols_momento(h), vida_media_dias=VIDA_MEDIA_DIAS)
    return out


def cobertura_por_nivel(modelos, d, rejilla, estado):
    """Para cada hora y nivel: porcentaje de casos con lo que falta por debajo del percentil de ese nivel."""
    filas = []
    for h, m in modelos.items():
        sub, y = casos(d, h)
        S = supervivencia(m, sub, rejilla, estado, h)
        for nivel in NIVELES:
            pred = ce.cuantiles_de_supervivencia(S, niveles=[nivel])[:, 0]
            filas.append({"hora": h, "nivel": nivel, "n": len(sub), "pct_debajo": 100 * np.mean(y <= pred)})
    return pd.DataFrame(filas)


def paso2(tr, va, rejilla, estado, corte, unico):
    decir("\nPASO 2. Calibrar el p90 con la validacion")
    modelos = modelos_por_hora(tr, rejilla, estado, corte, unico)
    cob = cobertura_por_nivel(modelos, va, rejilla, estado)
    junto = cob.assign(peso=cob.n).groupby("nivel").apply(lambda g: np.average(g.pct_debajo, weights=g.peso), include_groups=False).rename("pct_debajo_junto")
    for nivel, v in junto.items():
        decir(f"  nivel {nivel:.2f}: deja por debajo al {v:.1f} % de los casos (horas juntas)")
    ok = junto[junto >= 90.0]
    nivel = float(ok.index.min()) if len(ok) else float(NIVELES[-1])
    decir(f"  -> nivel elegido para el p90: {nivel:.2f}")
    cob = cob.merge(junto.reset_index(), on="nivel")
    return cob, nivel


def paso3(tr, te, rejilla, estado, corte, nivel):
    decir("\nPASO 3. Prueba (jul-2025 a 9-abr-2026), modelos entrenados con todo lo anterior; corte y nivel ya decididos")
    unico = ce.entrenar_m1(tr, rejilla, estado, cols_unico(), vida_media_dias=VIDA_MEDIA_DIAS)
    modelos = modelos_por_hora(tr, rejilla, estado, corte, unico)
    filas = []
    for h, m in modelos.items():
        sub, y = casos(te, h)
        S = supervivencia(m, sub, rejilla, estado, h)
        general, _ = ce.referencias(tr, sub, h)
        base = ce.perdida(y, general)
        pred = ce.cuantiles_de_supervivencia(S)
        pred_cal = pred.copy()
        pred_cal[:, 3] = ce.cuantiles_de_supervivencia(S, niveles=[nivel])[:, 0]
        for nombre, p in (("p90 sin calibrar", pred), (f"p90 calibrado (nivel {nivel:.2f})", pred_cal)):
            fila = {"hora": h, "p90": nombre, "n": len(sub), "mejora_vs_general_pct": round(100 * (1 - ce.perdida(y, p) / base), 1)}
            for j, q in enumerate(ce.Q):
                fila[f"pct_debajo_p{int(q * 100)}"] = round(100 * np.mean(y <= p[:, j]), 1)
            filas.append(fila)
    tabla = pd.DataFrame(filas)
    decir(tabla.to_string(index=False))
    return tabla


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    ce.TABLAS.mkdir(parents=True, exist_ok=True)
    d, h_, rejilla, estado = ce.preparar()
    a = d[d.ini_est < INI_VALIDACION].reset_index(drop=True)
    va = d[(d.ini_est >= INI_VALIDACION) & (d.ini_est < ce.CORTE)].reset_index(drop=True)
    tr = d[d.ini_est < ce.CORTE].reset_index(drop=True)
    te = d[d.ini_est >= ce.CORTE].reset_index(drop=True)
    decir(f"entrenamiento A {len(a):,} | validacion {len(va):,} | entrenamiento para la prueba {len(tr):,} | prueba {len(te):,}")
    t1, corte, unico_a = paso1(a, va, rejilla, estado)
    if SOLO_PASO1:
        sys.exit(0)
    t1.to_csv(ce.TABLAS / "calibracion_corte_paso1.csv", index=False)
    if corte is None:
        corte = ce.HORAS_RECORRIDO
        decir(f"  (se deja el corte actual de {corte} h)")
    ce.HORAS_RECORRIDO = corte
    t2, nivel = paso2(a, va, rejilla, estado, corte, unico_a)
    t2.to_csv(ce.TABLAS / "calibracion_corte_paso2.csv", index=False)
    t3 = paso3(tr, te, rejilla, estado, corte, nivel)
    t3.to_csv(ce.TABLAS / "calibracion_corte_paso3.csv", index=False)
    decir(f"\nRESULTADO: corte = {corte} h (antes 12 h, elegido con la prueba); nivel del p90 = {nivel:.2f}")
    (ce.TABLAS / "calibracion_corte_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")
