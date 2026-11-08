"""
estimador_tiempos.py  -  version 1 (7-nov-2026)
Tarea A6 (componente 3): estimar tiempos de atencion. Cuando llega un paciente, ¿que tan probable es que se hospitalice, cuanto esperaria cama,
cuanto se quedaria en cama y cuanto duraria en urgencias si no se hospitaliza?

POR QUE ASI
  Predecir el tiempo de UN paciente no funciona con lo que se sabe al llegar (esperar mas de 24 h: AUC 0,60; estancia: R2 cercano a 0; CLAUDE.md 6b).
  Por eso el estimador da un RANGO TIPICO de pacientes parecidos (percentiles 25, 50, 75 y 90) y una probabilidad, no un numero exacto
  (opcion 1 de A6 en docs/pendientes_y_reparto.md, con la opcion 3 sumada: probabilidad de hospitalizarse al llegar).

QUE HACE
  1. PERFIL = solo lo que se sabe al llegar: bloque de 3 horas de la llegada, grupo de edad, tipo de visita y sexo.
     Si un perfil tiene menos de MIN_CASOS casos, se usa el perfil mas general que si los tenga (se quita primero el sexo, luego el tipo de visita, luego la edad).
  2. Cuatro medidas por perfil:
       - prob. de hospitalizarse: entre los episodios con atencion (no solo admision), contando cada estancia una vez.
       - espera de cama (si se hospitaliza): de la llegada a la asignacion de cama; 100 % medida en hospitalizados.
       - estancia en cama: de la asignacion de cama al alta; solo estancias con alta registrada antes del 10-abr-2026.
       - urgencias sin hospitalizar: Kaplan-Meier (los episodios con 'minimo_conocido' cuentan como censurados), porque solo una parte tiene hora de salida.
  3. VALIDACION TEMPORAL: se arma la tabla con feb-2023 a jun-2025 y se prueba con jul-2025 a 9-abr-2026 (la estancia, hasta el 9-ene-2026 para que las
     estancias largas alcancen a terminar). Se mide cuanto mejora cada variable frente al rango general (perdida de cuantiles) y si los rangos aciertan
     (cuantos casos nuevos caen por debajo de cada percentil: 25 / 50 / 75 / 90 % es lo ideal).
  4. Tabla final con todo el periodo confiable (feb-2023 a 9-abr-2026) y la funcion estimar() para el dashboard.

ENTRADA  datos/procesados/tabla_episodios.parquet (src/analisis_etapas.py y src/preparar_variables.py)
SALIDAS  resultados/tablas/estimador_tiempos.csv           una fila por perfil de llegada (agregada, solo celdas con MIN_CASOS o mas)
         resultados/tablas/estimador_validacion.csv        resultado de la prueba temporal por medida y nivel de detalle
         resultados/graficos/estimador_tiempos.png

LIMITES
  - Son asociaciones de pacientes parecidos, no predicciones individuales: el rango sirve para planear y comunicar, no para prometerle un tiempo a una persona.
  - Urgencias: la mitad de los episodios no tiene ningun tiempo registrado y ningun metodo lo recupera (docs/supervivencia_urgencias.md); Kaplan-Meier
    supone que la falta de cierre no depende de la duracion.
  - Edad y sexo de las estancias gemelas: si faltan los CSV del lote 4 de auditoria_bd.py, preparar_variables.py conserva el registro con mas informacion,
    que es el de la persona real en ~81-85 % de las gemelas (CLAUDE.md 4.10).
  - Las llegadas incluyen >= 4 % de registros replica (CLAUDE.md 4.6), que pesan en la probabilidad de hospitalizarse.

COMO CORRERLO  python3 src/estimador_tiempos.py
"""
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))   # los datos pueden vivir fuera del proyecto
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
GRAF = RAIZ / "resultados" / "graficos"
DESDE, HASTA = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10")   # periodo confiable (CLAUDE.md 4.9)
CORTE = pd.Timestamp("2025-07-01")                                     # entrenar antes, probar despues
HASTA_ESTANCIA_PRUEBA = pd.Timestamp("2026-01-10")                     # 90 dias antes del fin, para que las estancias largas terminen
MIN_CASOS = 30
CUANTILES = [0.25, 0.5, 0.75, 0.9]
EDADES = ["0-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+"]
TIPOS = ["Urgencias", "Treatment urgency", "Ambulatorio"]
BLOQUES = ["00-02", "03-05", "06-08", "09-11", "12-14", "15-17", "18-20", "21-23"]
DIMS = ["bloque_hora", "grupo_edad", "tipo_visita", "sexo"]            # de la mas general a la mas fina; se quitan desde el final
NIVELES = {0: "general", 1: "hora", 2: "hora + edad", 3: "hora + edad + tipo de visita", 4: "hora + edad + tipo de visita + sexo"}


# ----------------------------------------------------------------------
# 1) Datos
# ----------------------------------------------------------------------
def cargar():
    t = pd.read_parquet(PROC / "tabla_episodios.parquet")
    t = t[(t.ini >= DESDE) & (t.ini < HASTA) & t.grupo_edad.notna() & t.sexo.isin(["Mujer", "Hombre"]) & t.tipo_visita.isin(TIPOS)].copy()
    t["grupo_edad"] = t.grupo_edad.astype(str)
    t["bloque_hora"] = pd.Series(BLOQUES)[t.hora.to_numpy() // 3].to_numpy()
    t["con_atencion"] = t.ruta != "ER"
    t["hosp"] = t.hospitalizado & t.estancia_unica
    t["estancia_h"] = ((t.fin_hosp_est - t.ini_hosp_est).dt.total_seconds() / 3600).where(t.hosp & (t.fin_hosp_est < HASTA))
    return t


def medidas(t):
    """Una tabla por medida, con las columnas del perfil, el valor y (si aplica) si el valor es un evento observado."""
    at = t[t.con_atencion & (~t.hospitalizado | t.estancia_unica)]          # cada estancia una vez en el denominador
    h = t[t.hosp]
    u = t[~t.hospitalizado & t.ruta_simple.fillna("").str.contains("TU")]
    u = u[u.estado.isin(["medida", "minimo_conocido"]) & u.horas_total.le(24 * 90)]
    return {
        "prob_hospitalizarse": at.assign(valor=at.hosp.astype(float))[DIMS + ["ini", "valor"]],
        "espera_cama_h": h[h.espera_cama_h.notna()].assign(valor=lambda d: d.espera_cama_h)[DIMS + ["ini", "valor"]],
        "estancia_cama_h": h[h.estancia_h.notna()].assign(valor=lambda d: d.estancia_h)[DIMS + ["ini", "valor"]],
        "urgencias_sin_hosp_h": u.assign(valor=u.horas_total, evento=u.estado.eq("medida"))[DIMS + ["ini", "valor", "evento"]],
    }


# ----------------------------------------------------------------------
# 2) Estimadores
# ----------------------------------------------------------------------
def kaplan_meier(tiempo, evento):
    """Devuelve los tiempos con evento y la supervivencia S(t) justo despues de cada uno."""
    tiempo, evento = np.asarray(tiempo, float), np.asarray(evento, bool)
    ut, idx = np.unique(tiempo, return_inverse=True)
    d = np.bincount(idx, weights=evento.astype(float))
    c = np.bincount(idx)
    en_riesgo = len(tiempo) - np.cumsum(c) + c
    return ut, np.cumprod(1 - d / en_riesgo)


def km_cuantil(tiempo, evento, q):
    ut, s = kaplan_meier(tiempo, evento)
    k = np.flatnonzero(s <= 1 - q)
    return ut[k[0]] if len(k) else np.nan                                  # nan: el percentil queda por encima del ultimo dato observado


def resumir(g, medida):
    """Resumen de un grupo: n y percentiles (o la proporcion)."""
    out = {"n": len(g)}
    if medida == "prob_hospitalizarse":
        out["valor"] = g.valor.mean()
    elif medida == "urgencias_sin_hosp_h":
        for q in CUANTILES:
            out[f"p{int(q * 100)}"] = km_cuantil(g.valor, g.evento, q)
        out["pct_con_hora_salida"] = g.evento.mean()
    else:
        for q in CUANTILES:
            out[f"p{int(q * 100)}"] = g.valor.quantile(q)
    return out


def tabla_por_nivel(d, medida):
    """Resumen de cada perfil en cada nivel de detalle (0 = general ... 4 = todas las variables)."""
    filas = []
    for nivel in NIVELES:
        cols = DIMS[:nivel]
        grupos = [((), d)] if not cols else d.groupby(cols, observed=True)
        for clave, g in grupos:
            clave = clave if isinstance(clave, tuple) else (clave,)
            filas.append({"nivel": nivel, **dict(zip(cols, clave)), **resumir(g, medida)})
    return pd.DataFrame(filas)


def asignar(d, resumen, nivel_max):
    """A cada caso le toca el perfil mas fino (hasta nivel_max) con MIN_CASOS o mas; devuelve las columnas del resumen y el nivel usado."""
    pendiente = pd.Series(True, index=d.index)
    partes = []
    for nivel in range(nivel_max, -1, -1):
        idx = pendiente.index[pendiente]
        if not len(idx):
            break
        cols = DIMS[:nivel]
        r = resumen[(resumen.nivel == nivel) & (resumen.n >= MIN_CASOS)].drop(columns=[c for c in DIMS if c not in cols])
        if cols:
            m = d.loc[idx, cols].assign(_i=idx).merge(r, on=cols, how="left").set_index("_i").drop(columns=cols)
        else:
            m = pd.DataFrame([r.iloc[0].to_dict()] * len(idx), index=idx)
        m = m[m.n.notna()]
        partes.append(m)
        pendiente[m.index] = False
    return pd.concat(partes).reindex(d.index)


# ----------------------------------------------------------------------
# 3) Validacion temporal
# ----------------------------------------------------------------------
def perdida_cuantil(y, pred, q):
    e = y - pred
    return np.mean(np.maximum(q * e, (q - 1) * e))


def auc(y, p):
    y, p = np.asarray(y, bool), np.asarray(p, float)
    r = pd.Series(p).rank().to_numpy()
    n1, n0 = y.sum(), (~y).sum()
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def validar(med):
    filas = []
    for medida, d in med.items():
        fin_prueba = HASTA_ESTANCIA_PRUEBA if medida == "estancia_cama_h" else HASTA
        tr, te = d[d.ini < CORTE], d[(d.ini >= CORTE) & (d.ini < fin_prueba)]
        res = tabla_por_nivel(tr, medida)
        base = None
        for nivel in NIVELES:
            a = asignar(te, res, nivel)
            fila = {"medida": medida, "nivel": nivel, "detalle": NIVELES[nivel], "n_prueba": len(te),
                    "pct_casos_con_su_perfil_completo": round(100 * (a.nivel == nivel).mean(), 1) if nivel else 100.0}
            if medida == "prob_hospitalizarse":
                y, p = te.valor.to_numpy(), a.valor.to_numpy()
                fila.update(auc=round(auc(y, p), 3) if nivel else 0.5, brier=round(np.mean((p - y) ** 2), 4),
                            prob_media_estimada=round(p.mean(), 4), prob_real_prueba=round(y.mean(), 4))
            elif medida == "urgencias_sin_hosp_h":
                for q in CUANTILES:                                                   # KM del cociente tiempo / percentil del perfil, evaluado en 1
                    k = f"p{int(q * 100)}"
                    ok = a[k].notna()
                    ut, s = kaplan_meier(te.valor[ok] / a[k][ok], te.evento[ok])
                    s1 = s[ut <= 1][-1] if (ut <= 1).any() else 1.0
                    fila[f"pct_debajo_{k}"] = round(100 * (1 - s1), 1)
            else:
                perd = sum(perdida_cuantil(te.valor.to_numpy(), a[f"p{int(q * 100)}"].to_numpy(), q) for q in CUANTILES)
                base = perd if nivel == 0 else base
                fila["mejora_vs_general_pct"] = round(100 * (1 - perd / base), 1)
                for q in CUANTILES:
                    k = f"p{int(q * 100)}"
                    fila[f"pct_debajo_{k}"] = round(100 * (te.valor.to_numpy() <= a[k].to_numpy()).mean(), 1)
            filas.append(fila)
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------
# 4) Tabla final y consulta
# ----------------------------------------------------------------------
def tabla_final(med):
    """Una fila por perfil completo de llegada; cada medida usa el perfil mas fino con MIN_CASOS o mas."""
    rejilla = pd.MultiIndex.from_product([BLOQUES, EDADES, TIPOS, ["Mujer", "Hombre"]], names=DIMS).to_frame(index=False)
    partes = [rejilla]
    for medida, d in med.items():
        a = asignar(rejilla, tabla_por_nivel(d, medida), len(DIMS))
        a = a.rename(columns={"valor": medida, "n": f"{medida}_n", "nivel": f"{medida}_nivel",
                              **{f"p{int(q * 100)}": f"{medida}_p{int(q * 100)}" for q in CUANTILES},
                              "pct_con_hora_salida": f"{medida}_pct_con_hora_salida"})
        partes.append(a)
    t = pd.concat(partes, axis=1)
    for c in t.columns:
        if c.endswith("_nivel") or c.endswith("_n"):
            t[c] = t[c].astype("Int64")
    return t


def estimar(hora, grupo_edad, tipo_visita, sexo, tabla=None):
    """Rango tipico para una llegada. Ej.: estimar(15, '60-74', 'Urgencias', 'Mujer'). Lee la tabla guardada si no se pasa."""
    tabla = pd.read_csv(TABLAS / "estimador_tiempos.csv") if tabla is None else tabla
    fila = tabla[(tabla.bloque_hora == BLOQUES[int(hora) // 3]) & (tabla.grupo_edad == grupo_edad) & (tabla.tipo_visita == tipo_visita) & (tabla.sexo == sexo)]
    return fila.iloc[0].to_dict() if len(fila) else None


# ----------------------------------------------------------------------
# 5) Grafico
# ----------------------------------------------------------------------
def grafico(t):
    fig, ejes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=False)
    sel = t[(t.tipo_visita == "Urgencias") & (t.sexo == "Mujer")]
    x = np.arange(len(BLOQUES))
    for ax, edad, color in [(ejes[0], "30-44", "#2a78d6"), (ejes[1], "75+", "#eb6834")]:
        s = sel[sel.grupo_edad == edad].set_index("bloque_hora").loc[BLOQUES]
        ax.fill_between(x, s.espera_cama_h_p25, s.espera_cama_h_p75, color=color, alpha=0.25, label="p25 a p75")
        ax.plot(x, s.espera_cama_h_p50, color=color, lw=2, label="mediana")
        ax.plot(x, s.espera_cama_h_p90, color=color, lw=1, ls="--", label="p90")
        ax.set_xticks(x, BLOQUES)
        ax.set_title(f"Espera de cama, urgencias, mujeres de {edad} años")
        ax.set_xlabel("hora de llegada")
        ax.set_ylim(0)
        ax.grid(axis="y", color="#e5e4df")
        ax.legend(frameon=False)
    ejes[0].set_ylabel("horas")
    fig.text(0.01, 0.01, "Rango típico de pacientes parecidos (feb-2023 a 9-abr-2026), no una predicción individual. Fuente: src/estimador_tiempos.py",
             fontsize=8, color="#52514e")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(GRAF / "estimador_tiempos.png", dpi=150)


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    TABLAS.mkdir(parents=True, exist_ok=True)
    GRAF.mkdir(parents=True, exist_ok=True)
    med = medidas(cargar())
    for k, d in med.items():
        print(f"{k}: {len(d):,} casos")

    val = validar(med)
    val.to_csv(TABLAS / "estimador_validacion.csv", index=False)
    print("\nVALIDACION TEMPORAL (tabla con feb-2023 a jun-2025, prueba con jul-2025 a 9-abr-2026)")
    print(val.to_string(index=False))

    tf = tabla_final(med)
    tf.round(3).to_csv(TABLAS / "estimador_tiempos.csv", index=False)
    grafico(tf)
    print(f"\nestimador_tiempos.csv: {len(tf)} perfiles")
    for ej in [(9, "30-44", "Urgencias", "Mujer"), (15, "30-44", "Urgencias", "Mujer"), (15, "75+", "Urgencias", "Hombre")]:
        e = estimar(*ej, tabla=tf)
        print(ej, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in e.items() if k.startswith(("prob", "espera", "estancia"))})
