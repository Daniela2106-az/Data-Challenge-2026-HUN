"""
revision_estimador.py  -  version 1 (9-nov-2026)
Tarea A6: revision del estimador de tiempo restante (docs/estimador_tiempos.md, seccion 7). Prueba con datos los problemas que encontro la revision del
codigo y que la v2 no habia medido. Usa la misma prueba que comparar_estimadores.py (entrenamiento feb-2023 a jun-2025, prueba jul-2025 a 9-abr-2026).

QUE PRUEBA
  1. EL MODELO QUE SE USA, HORA POR HORA. La v2 se probo con modelos por momento entrenados justo en 0, 3 y 6 h, pero el que se consulta tiene modelos en
     0, 2, 4, 6 y 9 h y para otras horas usa el mas cercano por debajo. Aqui se evalua ese esquema en cada hora de 0 a 11 y se compara con un modelo
     entrenado justo en esa hora. Si en alguna hora el esquema usado pierde mucho, hay que agregar modelos.
  2. ¿EL RECORRIDO EN URGENCIAS ES UNA FUGA? Sospecha: quien tiene varias etapas abiertas recibe cama pronto porque esas etapas se abren en el tramite de
     hospitalizacion (el modelo veria que ya se pidio la cama, no lo predeciria). Dos pruebas:
     a) descriptiva: cuanto antes de la cama empieza la ultima etapa de urgencias, y en cuantas estancias empieza en la hora previa;
     b) con retraso: se vuelve a entrenar el modelo de 3 y de 6 h viendo el recorrido solo hasta 1, 2 y 3 h antes. Si la mejora se cae al retrasar,
        el recorrido trae sobre todo el tramite (fuga); si se mantiene, trae informacion real del paciente.
  3. ¿CUANTO PESABA LA FUGA DEL DIAGNOSTICO PREVIO? Modelo al llegar con el diagnostico previo fechado al inicio de su episodio (v2, con fuga) y al fin (v3).
  4. ESTABILIDAD: el resultado del esquema usado en jul-dic 2025 y en ene-9 abr 2026 por separado. Ojo: no hay un periodo que nadie haya mirado; el corte
     de 12 h y la vida media de 6 meses se eligieron con esta misma prueba, asi que estas cifras siguen siendo algo optimistas.
  5. ZONA: en cuantas estancias la zona (adultos o ninos) cambia al usar la edad corregida de la persona real.

ENTRADAS  las de comparar_estimadores.py: tabla_episodios.parquet (HUN_PROCESADOS), visit_detail.csv y procedimientos_por_estancia.csv (HUN_CRUDOS)
SALIDAS   en HUN_TABLAS: revision_estimador_por_hora.csv, revision_estimador_fuga_recorrido.csv, revision_estimador_ultima_etapa.csv,
          revision_estimador_dx_previo.csv, revision_estimador_por_periodo.csv, revision_estimador_resumen.txt
COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... HUN_CRUDOS=... python3 src/revision_estimador.py   (unos 15-25 min; RAPIDO=1 omite la prueba 1 hora por hora)
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402
import estimador_tiempo_restante as etr  # noqa: E402

RAPIDO = os.environ.get("RAPIDO", "0") == "1"
HORAS = list(range(0, ce.HORAS_RECORRIDO))       # 0 a 11 h: donde se usan los modelos por momento
RETRASOS = [0, 1, 2, 3]
LINEAS = []


def decir(texto=""):
    print(texto, flush=True)
    LINEAS.append(texto)


def landmark_usado(h):
    return max(L for L in etr.LANDMARKS if L <= h)


def evaluar(tr, sub, preds, desde):
    """Mejora frente al rango general (con IC 95 % por semanas) y calibracion de cada prediccion."""
    y = np.minimum(sub.espera_cama_h.to_numpy() - desde, ce.MAX_H)
    general, _ = ce.referencias(tr, sub, desde)
    lg = ce.perdida_por_caso(y, general)
    semana = sub.ini_est.dt.to_period("W").astype(str).to_numpy()
    filas = []
    for nombre, p in preds.items():
        lp = ce.perdida_por_caso(y, p)
        lo, hi = ce.intervalo_mejora(semana, lp, lg)
        filas.append({"horas_esperando": desde, "modelo": nombre, "n": len(y), "mejora_vs_general_pct": round(100 * (1 - lp.mean() / lg.mean()), 1),
                      "ic95_bajo": round(lo, 1), "ic95_alto": round(hi, 1), "error_abs_mediana_h": round(float(np.mean(np.abs(y - p[:, 1]))), 1),
                      **{f"pct_debajo_p{int(q * 100)}": round(100 * float(np.mean(y <= p[:, j])), 1) for j, q in enumerate(ce.Q)}})
    return filas, y, semana


def diferencia(y, semana, p_a, p_b):
    """Cuanto mejor es a que b (positivo = a mejor), con IC 95 %."""
    la, lb = ce.perdida_por_caso(y, p_a), ce.perdida_por_caso(y, p_b)
    lo, hi = ce.intervalo_mejora(semana, la, lb)
    return round(100 * (1 - la.mean() / lb.mean()), 1), round(lo, 1), round(hi, 1)


# ----------------------------------------------------------------------
# 1) Esquema usado, hora por hora
# ----------------------------------------------------------------------
def prueba_por_hora(tr, te, rejilla, estado):
    decir("\n1) MODELO QUE SE USA, HORA POR HORA (0 a 11 h de espera)")
    usados = {L: ce.entrenar_landmark(tr, rejilla, estado, L) for L in etr.LANDMARKS}
    filas = []
    for h in HORAS:
        sub = te[te.espera_cama_h > h].reset_index(drop=True)
        L = landmark_usado(h)
        p_usado = ce.predecir_m1(usados[L], sub, rejilla, estado, h)
        p_justo = p_usado if L == h else ce.predecir_m1(ce.entrenar_landmark(tr, rejilla, estado, h), sub, rejilla, estado, h)
        f, y, sem = evaluar(tr, sub, {f"usado (modelo de {L} h)": p_usado, "entrenado justo en esa hora": p_justo}, h)
        dif = diferencia(y, sem, p_justo, p_usado) if L != h else (0.0, 0.0, 0.0)
        for fila in f:
            fila.update(landmark_usado=L, justo_mejor_que_usado_pct=dif[0], ic95_dif_bajo=dif[1], ic95_dif_alto=dif[2])
        filas += f
        decir(f"  {h:>2} h (usa el de {L} h): usado {f[0]['mejora_vs_general_pct']:+.1f} %  |  justo en la hora {f[1]['mejora_vs_general_pct']:+.1f} %  |  "
              f"diferencia {dif[0]:+.1f} (IC {dif[1]:+.1f} a {dif[2]:+.1f})")
    r = pd.DataFrame(filas)
    r.to_csv(ce.TABLAS / "revision_estimador_por_hora.csv", index=False)
    malas = r[(r.justo_mejor_que_usado_pct > 0) & (r.ic95_dif_bajo > 0)].horas_esperando.unique()
    decir(f"  Horas en que un modelo propio seria claramente mejor (IC sin el 0): {list(map(int, malas)) or 'ninguna'}")
    return r


# ----------------------------------------------------------------------
# 2) ¿Fuga del recorrido?
# ----------------------------------------------------------------------
def ultima_etapa(d):
    """Horas entre el inicio de la ultima etapa de urgencias antes de la cama y la cama, por estancia."""
    filas = []
    for clave, espera in zip(d.clave, d.espera_cama_h):
        s, e, er = ce.ETAPAS.get(clave, (np.array([]), np.array([]), np.array([])))
        if not len(s):
            continue
        abiertas6 = int(((s < 6) & (np.isnan(e) | (e > 6))).sum()) if espera > 6 else np.nan
        filas.append({"clave": clave, "espera_h": espera, "horas_ultima_etapa_a_cama": espera - s.max(), "n_etapas": len(s), "abiertas_a_las_6h": abiertas6})
    return pd.DataFrame(filas)


def prueba_fuga_recorrido(d, tr, te, rejilla, estado):
    decir("\n2) ¿EL RECORRIDO EN URGENCIAS ES UNA FUGA DEL TRAMITE DE HOSPITALIZACION?")
    u = ultima_etapa(d)
    u["grupo"] = np.where(u.abiertas_a_las_6h >= 2, "2+ etapas abiertas a las 6 h", np.where(u.abiertas_a_las_6h.notna(), "0-1 abiertas a las 6 h", "espera de 6 h o menos"))
    res = u.groupby("grupo").agg(n=("clave", "size"), mediana_h_ultima_etapa_a_cama=("horas_ultima_etapa_a_cama", "median"),
                                 pct_ultima_etapa_en_la_hora_previa=("horas_ultima_etapa_a_cama", lambda x: 100 * (x <= 1).mean()),
                                 espera_mediana_h=("espera_h", "median")).round(2).reset_index()
    tot = {"grupo": "todas", "n": len(u), "mediana_h_ultima_etapa_a_cama": round(u.horas_ultima_etapa_a_cama.median(), 2),
           "pct_ultima_etapa_en_la_hora_previa": round(100 * (u.horas_ultima_etapa_a_cama <= 1).mean(), 2), "espera_mediana_h": round(u.espera_h.median(), 2)}
    res = pd.concat([res, pd.DataFrame([tot])], ignore_index=True)
    res.to_csv(ce.TABLAS / "revision_estimador_ultima_etapa.csv", index=False)
    decir("  a) Cuanto antes de la cama empieza la ultima etapa de urgencias:")
    decir("     " + res.to_string(index=False).replace("\n", "\n     "))

    decir("  b) Mejora del modelo viendo el recorrido con retraso (si se cae al retrasar, era el tramite):")
    filas = []
    for desde in [3, 6]:
        sub = te[te.espera_cama_h > desde].reset_index(drop=True)
        preds = {f"recorrido con {r} h de retraso": ce.predecir_m1(ce.entrenar_landmark(tr, rejilla, estado, desde, retraso_h=r), sub, rejilla, estado, desde)
                 for r in RETRASOS}
        preds["sin recorrido (solo historial)"] = ce.predecir_m1(ce.entrenar_landmark(tr, rejilla, estado, desde, cols=ce.COLS_M1_BASE + ce.HIST),
                                                                 sub, rejilla, estado, desde)
        f, y, sem = evaluar(tr, sub, preds, desde)
        sin = preds["sin recorrido (solo historial)"]
        for fila in f:
            fila["aporte_del_recorrido_pct"] = diferencia(y, sem, preds[fila["modelo"]], sin)[0] if fila["modelo"] in preds and "retraso" in fila["modelo"] else 0.0
        filas += f
        decir(f"     {desde} h: " + " | ".join(f"{x['modelo']}: {x['mejora_vs_general_pct']:+.1f} %" for x in f))
    r = pd.DataFrame(filas)
    r.to_csv(ce.TABLAS / "revision_estimador_fuga_recorrido.csv", index=False)
    for desde in [3, 6]:
        g = r[r.horas_esperando == desde].set_index("modelo").aporte_del_recorrido_pct
        a0, a2 = g.get("recorrido con 0 h de retraso", np.nan), g.get("recorrido con 2 h de retraso", np.nan)
        conserva = 100 * a2 / a0 if a0 > 0 else np.nan
        decir(f"     {desde} h: el recorrido aporta {a0:+.1f} puntos sin retraso y {a2:+.1f} con 2 h de retraso"
              + (f" (conserva el {conserva:.0f} %)" if np.isfinite(conserva) else ""))
    decir("     Lectura: si conserva menos de la mitad, el aporte del recorrido es sobre todo el tramite de hospitalizacion y no debe venderse como prediccion.")
    return r


# ----------------------------------------------------------------------
# 3) Fuga del diagnostico previo
# ----------------------------------------------------------------------
def prueba_dx_previo(t, d, rejilla, estado):
    decir("\n3) DIAGNOSTICO PREVIO: FECHADO AL INICIO (v2, con fuga) O AL FIN (v3) DEL EPISODIO ANTERIOR")
    base = d.drop(columns=ce.HIST)
    ce.DX_PREVIO_AL_INICIO = True
    d_v2 = ce.historial(t, base.copy())
    ce.DX_PREVIO_AL_INICIO = False
    d_v3 = ce.historial(t, base.copy())
    cambia = (d_v2.dx_previo_cod.fillna(-1) != d_v3.dx_previo_cod.fillna(-1)).mean()
    decir(f"  Estancias cuyo diagnostico previo cambia: {100 * cambia:.1f} %")
    filas = []
    for nombre, dd in [("v2: al inicio (con fuga)", d_v2), ("v3: al fin", d_v3)]:
        tr, te = dd[dd.ini_est < ce.CORTE].reset_index(drop=True), dd[dd.ini_est >= ce.CORTE].reset_index(drop=True)
        p = ce.predecir_m1(ce.entrenar_landmark(tr, rejilla, estado, 0), te, rejilla, estado, 0)
        f, _, _ = evaluar(tr, te, {nombre: p}, 0)
        filas += f
        decir(f"  {nombre}: mejora al llegar {f[0]['mejora_vs_general_pct']:+.1f} % (IC {f[0]['ic95_bajo']:+.1f} a {f[0]['ic95_alto']:+.1f})")
    r = pd.DataFrame(filas).assign(pct_estancias_que_cambian=round(100 * cambia, 1))
    r.to_csv(ce.TABLAS / "revision_estimador_dx_previo.csv", index=False)
    return r


# ----------------------------------------------------------------------
# 4) Estabilidad por periodo
# ----------------------------------------------------------------------
def prueba_periodos(tr, te, rejilla, estado):
    decir("\n4) ESTABILIDAD: ESQUEMA USADO EN JUL-DIC 2025 Y EN ENE-9 ABR 2026")
    usados = {L: ce.entrenar_landmark(tr, rejilla, estado, L) for L in etr.LANDMARKS}
    m12 = ce.entrenar_m1(tr, rejilla, estado, ce.COLS_M1_BASE + ce.HIST)
    filas = []
    for desde in [0, 3, 6, 12, 24]:
        sub = te[te.espera_cama_h > desde].reset_index(drop=True)
        m = m12 if desde >= ce.HORAS_RECORRIDO else usados[landmark_usado(desde)]
        p = ce.predecir_m1(m, sub, rejilla, estado, desde)
        for periodo, mask in [("jul-dic 2025", sub.ini_est < "2026-01-01"), ("ene-9 abr 2026", sub.ini_est >= "2026-01-01")]:
            mask = mask.to_numpy()
            f, _, _ = evaluar(tr, sub[mask].reset_index(drop=True), {"esquema usado": p[mask]}, desde)
            f[0]["periodo"] = periodo
            filas += f
        decir(f"  {desde:>2} h: jul-dic 2025 {filas[-2]['mejora_vs_general_pct']:+.1f} % | ene-abr 2026 {filas[-1]['mejora_vs_general_pct']:+.1f} %"
              f" (p90 cubre {filas[-2]['pct_debajo_p90']:.0f} % y {filas[-1]['pct_debajo_p90']:.0f} %)")
    r = pd.DataFrame(filas)
    r.to_csv(ce.TABLAS / "revision_estimador_por_periodo.csv", index=False)
    return r


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    ce.TABLAS.mkdir(parents=True, exist_ok=True)
    t = pd.read_parquet(ce.PROC / "tabla_episodios.parquet")
    d, h, rejilla, estado = ce.preparar()
    tr, te = d[d.ini_est < ce.CORTE].reset_index(drop=True), d[d.ini_est >= ce.CORTE].reset_index(drop=True)
    decir(f"REVISION DEL ESTIMADOR A6 | entrenamiento {len(tr):,} estancias | prueba {len(te):,}")

    zona_sin = np.where(d.edad < 15, "ninos", "adultos")
    decir(f"\n5) ZONA: estancias en que cambia al usar la edad corregida: {100 * (zona_sin != d.zona.to_numpy()).mean():.2f} %")

    if not RAPIDO:
        prueba_por_hora(tr, te, rejilla, estado)
    prueba_fuga_recorrido(d, tr, te, rejilla, estado)
    prueba_dx_previo(t, d, rejilla, estado)
    prueba_periodos(tr, te, rejilla, estado)
    (ce.TABLAS / "revision_estimador_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")
    decir(f"\nListo. Resumen en {ce.TABLAS / 'revision_estimador_resumen.txt'}")
