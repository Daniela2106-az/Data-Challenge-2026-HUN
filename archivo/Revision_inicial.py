"""
analisis_etapas.py  -  version 3 (20-oct-2026)
Analisis de duracion por ruta de etapas. Base OMOP uninorte (Data Challenge HUN 2026).

QUE CAMBIO RESPECTO A LA VERSION ANTERIOR
  1. Ya NO se filtra solo urgencias. Entran todos los tipos de visita. Las visitas que
     solo tienen etapas AMB (consultas de 0 min) desaparecen solas al quitar AMB.
  2. Ya NO se descartan los episodios de menos de 15 min. Todos los episodios quedan en
     las tablas de cobertura, con un estado (medida, minimo_dx, sin_duracion, sin_actividad).
     Solo las estadisticas de TIEMPO usan los episodios "medida", porque los demas no tienen
     hora de fin real y su duracion no se puede calcular.
     "medida" = el episodio tiene al menos una etapa TU o HOSP con fin posterior al inicio.
  3. Copias: se buscan con todos los desfases de id vistos (1.746.478 a 1.746.489 y
     1.757.760 a 1.757.769), en todos los tipos de visita, y se aceptan si coinciden
     el paciente, el fin o el inicio.
  4. Etapas repetidas en otra visita: si una etapa (mismo tipo, mismo inicio y mismo fin al
     segundo) aparece en dos visitas, se le asigna a la de menor id. Un episodio cuyas etapas
     estan TODAS en otra visita es una copia y se quita. Esto reemplaza la regla anterior de
     "episodios identicos" y prueba la hipotesis de que los fragmentos de ~16 dias antes son
     etapas copiadas de una visita anterior.
  5. Atipicos: se quito el IQR. Los errores se quitan con reglas (copias, etapas abiertas,
     corte de episodios y tope MAX_H). Lo que queda se resume con mediana y percentiles,
     que no se mueven por unos pocos casos extremos.
  6. Nuevo: espera de cama (inicio del episodio hasta la primera HOSP) y tiempo sin etapa
     justo antes de la HOSP.

ENTRADAS (misma carpeta que este script)
  visit_detail.csv      visit_detail_id, visit_occurrence_id, visit_detail_concept_id,
                        visit_detail_start_datetime, visit_detail_end_datetime
  visit_occurrence.csv  visit_occurrence_id, person_id, visit_concept_id
  dx_por_visita.csv     (opcional) visit_occurrence_id, n_dx, dx_min, dx_max
  proc_por_visita.csv   (opcional) visit_occurrence_id, n_proc

SALIDAS
  episodios.csv, bloques.csv (v3.1: tramos por episodio, para la ocupacion), resumen_por_ruta.csv, resumen_por_etapa.csv, espera_cama.csv,
  cobertura_por_ruta.csv, cobertura_por_tipo_visita.csv, resultados_finales.xlsx,
  boxplot_rutas.png, cobertura_por_ruta.png
"""
import os

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------
# Parametros (se pueden cambiar)
# ----------------------------------------------------------------------
OFFSETS_COPIA = list(range(1_746_478, 1_746_490)) + list(range(1_757_760, 1_757_770))
H_HUECO = 168        # horas sin ninguna etapa para cortar un episodio nuevo
MAX_H = 2160         # episodio medido de mas de 90 dias = error probable, fuera de las estadisticas
MAX_DX_H = 168       # un diagnostico mas de 7 dias despues del inicio no se usa para estimar duracion
MIN_DX_H = 0.25      # la duracion minima estimada por diagnosticos debe ser de al menos 15 min
MIN_EPISODIOS = 30   # rutas con menos episodios medidos se marcan como poco confiables
AMB, ER, TU, HOSP = 581479, 9203, 3045729, 9201
TIPOS = {ER: "Urgencias", TU: "Treatment urgency", HOSP: "Inpatient", AMB: "Ambulatorio"}
ESTADOS = ["medida", "minimo_dx", "sin_duracion", "sin_actividad"]

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


def resumen_horas(s):
    """Estadisticas robustas de una serie de horas."""
    s = s.dropna()
    if s.empty:
        return pd.Series({"n": 0})
    lo, hi = s.quantile([.05, .95])
    return pd.Series({
        "n": len(s),
        "p25_h": s.quantile(.25),
        "mediana_h": s.median(),
        "p75_h": s.quantile(.75),
        "p90_h": s.quantile(.90),
        "media_h": s.mean(),
        "media_recortada_5_95_h": s[(s >= lo) & (s <= hi)].mean(),
    })


# ----------------------------------------------------------------------
# 1) Carga
# ----------------------------------------------------------------------
vd = pd.read_csv("visit_detail.csv",
                 parse_dates=["visit_detail_start_datetime", "visit_detail_end_datetime"])
vo = pd.read_csv("visit_occurrence.csv")
vo["tipo_visita"] = vo.visit_concept_id.map(TIPOS).fillna("Otro")
vd_raw = vd.copy()   # etapas sin filtrar, solo para mostrar ejemplos

titulo("1. CARGA")
print("visitas:", len(vo), "| etapas:", len(vd))
print("visitas por tipo:\n" + vo.tipo_visita.value_counts().to_string())

# ----------------------------------------------------------------------
# 2) Limpieza de etapas: sin AMB, sin etapas abiertas (fin con milisegundos o vacio)
# ----------------------------------------------------------------------
fin = vd.visit_detail_end_datetime
abierta = fin.isna() | (fin.dt.microsecond != 0)
es_amb = vd.visit_detail_concept_id == AMB
titulo("2. LIMPIEZA DE ETAPAS")
print("etapas AMB quitadas:", int(es_amb.sum()))
print("etapas abiertas quitadas (fin con milisegundos o vacio):", int((abierta & ~es_amb).sum()))
vd = vd[~es_amb & ~abierta].copy()
vd["etapa"] = vd.visit_detail_concept_id.map({ER: "ER", TU: "TU", HOSP: "HOSP"})
otras = vd.etapa.isna().sum()
if otras:
    print("etapas de otro tipo quitadas:", int(otras))
vd = vd.dropna(subset=["etapa"])
print("etapas que quedan:", len(vd), "| visitas con alguna etapa:", vd.visit_occurrence_id.nunique())

# ----------------------------------------------------------------------
# 3) Copias de visitas: id - desfase existe y (mismo paciente, mismo fin o mismo inicio)
# ----------------------------------------------------------------------
iv = vd.groupby("visit_occurrence_id").agg(ini=("visit_detail_start_datetime", "min"),
                                          fin=("visit_detail_end_datetime", "max"))
vo = vo.merge(iv, left_on="visit_occurrence_id", right_index=True, how="left")
ref = vo.set_index("visit_occurrence_id")[["person_id", "ini", "fin"]]

es_copia = pd.Series(False, index=vo.index)
desfase = pd.Series(np.nan, index=vo.index)
motivo = pd.Series("", index=vo.index, dtype=object)
for k in OFFSETS_COPIA:
    cand = vo.visit_occurrence_id - k
    existe = cand.isin(ref.index)
    if not existe.any():
        continue
    pac = existe & (cand.map(ref.person_id) == vo.person_id)
    mfin = existe & vo.fin.notna() & (cand.map(ref.fin) == vo.fin)
    mini = existe & vo.ini.notna() & (cand.map(ref.ini) == vo.ini)
    nueva = (pac | mfin | mini) & ~es_copia
    desfase[nueva] = k
    motivo[nueva & pac] = "misma persona"
    motivo[nueva & ~pac & mfin] = "mismo fin"
    motivo[nueva & ~pac & ~mfin & mini] = "solo mismo inicio"
    es_copia |= nueva

titulo("3. COPIAS DE VISITAS")
print("copias quitadas:", int(es_copia.sum()), "de", len(vo))
print("por motivo:\n" + motivo[es_copia].value_counts().to_string())
print("por desfase (los 8 mas frecuentes):\n" +
      desfase[es_copia].astype(int).value_counts().head(8).to_string())
print("por tipo de visita de la copia:\n" + vo.loc[es_copia, "tipo_visita"].value_counts().to_string())
vo = vo[~es_copia]
vd = vd[vd.visit_occurrence_id.isin(vo.visit_occurrence_id)]
vd = vd.sort_values(["visit_occurrence_id", "visit_detail_start_datetime", "visit_detail_id"]).reset_index(drop=True)
print("visitas que quedan:", len(vo), "| con alguna etapa:", vd.visit_occurrence_id.nunique())

# ----------------------------------------------------------------------
# 4) Episodios: se corta la visita cuando pasan mas de H_HUECO horas sin ninguna etapa
# ----------------------------------------------------------------------
v = vd.visit_occurrence_id
prev_fin = vd.groupby(v).visit_detail_end_datetime.cummax().groupby(v).shift()
hueco_h = (vd.visit_detail_start_datetime - prev_fin).dt.total_seconds() / 3600
vd["episodio"] = (hueco_h > H_HUECO).astype(int).groupby(v).cumsum()
K = ["visit_occurrence_id", "episodio"]

titulo("4. HUECOS ENTRE ETAPAS DE UNA MISMA VISITA")
bins = [-np.inf, 0, 1, 6, 24, 72, 168, 336, 720, np.inf]
etq = ["solapa (<=0)", "0-1 h", "1-6 h", "6-24 h", "1-3 d", "3-7 d", "7-14 d", "14-30 d", ">30 d"]
print(pd.cut(hueco_h.dropna(), bins=bins, labels=etq).value_counts().reindex(etq).to_string())
for h in [72, 168, 336]:
    print(f"  cortes si el umbral fuera {h} h: {int((hueco_h > h).sum())}")
print(f"(umbral usado: {H_HUECO} h)")
print("mediana del hueco en los cortes (dias):", round(hueco_h[hueco_h > H_HUECO].median() / 24, 1))

# ----------------------------------------------------------------------
# 5) Etapas repetidas en otra visita (prueba de la hipotesis de los ~16 dias)
# ----------------------------------------------------------------------
llave = ["visit_detail_concept_id", "visit_detail_start_datetime", "visit_detail_end_datetime"]
vd["dueno"] = vd.groupby(llave).visit_occurrence_id.transform("min")
vd["repetida"] = vd.visit_occurrence_id != vd.dueno

# Una copia puede traer una ER inicial de mas: por eso basta con que esten repetidas
# todas las etapas TU/HOSP (si el episodio tiene alguna) o todas las etapas (si solo tiene ER).
vd["no_er"] = vd.etapa != "ER"
vd["rep_no_er"] = vd.repetida | ~vd.no_er
vd["n_ep"] = vd.groupby(v).episodio.transform("max") + 1
ep_rep = vd.groupby(K).agg(rep_todas=("repetida", "all"),
                           rep_no_er=("rep_no_er", "all"),
                           tiene_no_er=("no_er", "any"),
                           alguna_repetida=("repetida", "any"),
                           n_ep=("n_ep", "first"))
ep_rep["todas_repetidas"] = ep_rep.rep_todas | (ep_rep.tiene_no_er & ep_rep.rep_no_er)
ep_rep["ultimo"] = ep_rep.index.get_level_values(1) == ep_rep.n_ep - 1
ep_rep["tipo"] = np.where(ep_rep.n_ep == 1, "visita de 1 episodio",
                          np.where(ep_rep.ultimo, "ultimo episodio de visita partida",
                                   "fragmento anterior de visita partida"))

titulo("5. EPISODIOS CUYAS ETAPAS YA ESTAN EN OTRA VISITA")
tab = ep_rep.groupby("tipo").agg(episodios=("todas_repetidas", "size"),
                                 todas_repetidas=("todas_repetidas", "sum"),
                                 alguna_repetida=("alguna_repetida", "sum"))
tab["pct_todas_repetidas"] = (100 * tab.todas_repetidas / tab.episodios).round(1)
print(tab.to_string())
print("Lectura: si los 'fragmentos anteriores' tienen un % alto de etapas repetidas, el desfase de")
print("~16 dias es una etapa copiada de otra visita. Si es bajo, son atenciones previas reales.")

redundantes = ep_rep.index[ep_rep.todas_repetidas]
print("episodios quitados por estar completos en otra visita:", len(redundantes))
vd = vd.set_index(K)
vd = vd[~vd.index.isin(redundantes)].reset_index()

# ----------------------------------------------------------------------
# 6) Bloques (etapas seguidas iguales se juntan) y tabla de episodios
# ----------------------------------------------------------------------
vd["con_tiempo"] = (vd.etapa != "ER") & (vd.visit_detail_end_datetime > vd.visit_detail_start_datetime)
vd["bloque"] = (vd.etapa != vd.groupby(K).etapa.shift()).cumsum()

bloques = (vd.groupby(K + ["bloque"])
             .agg(etapa=("etapa", "first"),
                  ini=("visit_detail_start_datetime", "min"),
                  fin=("visit_detail_end_datetime", "max"),
                  n_etapas=("etapa", "size"))
             .reset_index())
bloques["horas"] = (bloques.fin - bloques.ini).dt.total_seconds() / 3600
bloques["pos"] = bloques.groupby(K).cumcount() + 1

ep = bloques.groupby(K).agg(ruta=("etapa", " > ".join),
                            ini=("ini", "min"), fin=("fin", "max"),
                            n_etapas=("n_etapas", "sum"))
ep["con_tiempo"] = vd.groupby(K).con_tiempo.any()
ep["horas_total"] = (ep.fin - ep.ini).dt.total_seconds() / 3600
ep = ep.reset_index()
ep["ruta_simple"] = ep.ruta.str.replace(r"^ER > ", "", regex=True)
ep["hospitalizado"] = ep.ruta.str.contains("HOSP")
ep["n_ep_visita"] = ep.groupby("visit_occurrence_id").episodio.transform("size")
ep = ep.merge(vo[["visit_occurrence_id", "person_id", "tipo_visita"]], on="visit_occurrence_id", how="left")

titulo("6. EPISODIOS")
print("episodios:", len(ep), "| visitas:", ep.visit_occurrence_id.nunique())
dup = ep.duplicated(["ini", "fin", "ruta"], keep=False)
print(f"episodios que aun son identicos a otro (inicio, fin y ruta): {int(dup.sum())} ({dup.mean():.1%})")
print("  (si es alto, quedan copias sin detectar; si es bajo, son coincidencias de cierres a la misma hora)")

# ----------------------------------------------------------------------
# 7) Estado de cada episodio
# ----------------------------------------------------------------------
ep["horas_dx"] = np.nan
hay_dx = os.path.exists("dx_por_visita.csv")
hay_proc = os.path.exists("proc_por_visita.csv")
if hay_dx:
    dx = pd.read_csv("dx_por_visita.csv", parse_dates=["dx_min", "dx_max"])[["visit_occurrence_id", "n_dx", "dx_max"]]
    ep = ep.merge(dx, on="visit_occurrence_id", how="left")
    h = (ep.dx_max - ep.ini).dt.total_seconds() / 3600
    ep["horas_dx"] = h.where((ep.n_ep_visita == 1) & h.between(0, MAX_DX_H))
else:
    ep["n_dx"] = np.nan
if hay_proc:
    pr = pd.read_csv("proc_por_visita.csv")[["visit_occurrence_id", "n_proc"]]
    ep = ep.merge(pr, on="visit_occurrence_id", how="left")
else:
    ep["n_proc"] = np.nan
ep["n_dx"] = ep.n_dx.fillna(0)
ep["n_proc"] = ep.n_proc.fillna(0)
actividad = (ep.n_dx > 0) | (ep.n_proc > 0)

ep["estado"] = np.select(
    [ep.con_tiempo, ep.horas_dx >= MIN_DX_H, actividad],
    ["medida", "minimo_dx", "sin_duracion"], "sin_actividad")
if not (hay_dx and hay_proc):
    print("\nAVISO: faltan dx_por_visita.csv o proc_por_visita.csv; 'sin_actividad' no es confiable.")

ep["error_probable"] = (ep.estado == "medida") & (ep.horas_total > MAX_H)

titulo("7. ESTADO DE LOS EPISODIOS")
print("medida = alguna etapa TU o HOSP con fin posterior al inicio")
print("minimo_dx = sin fin real, pero con un diagnostico que da una duracion minima")
print("sin_duracion = sin fin real y sin estimacion, pero con diagnosticos o procedimientos")
print("sin_actividad = sin fin real y sin ningun diagnostico ni procedimiento")
print("\n% del total:\n" + (100 * ep.estado.value_counts(normalize=True)).reindex(ESTADOS).fillna(0).round(1).to_string())
med = ep[ep.estado == "medida"]
print(f"\nepisodios medidos de menos de 15 min: {int((med.horas_total < 0.25).sum())} de {len(med)}")
print(f"episodios medidos de mas de {MAX_H} h (error probable, fuera de estadisticas): {int(ep.error_probable.sum())}")

titulo("7b. EJEMPLOS CRUDOS DE EPISODIOS NO MEDIDOS (todas las etapas de la visita, sin filtrar)")
rng = np.random.default_rng(1)
for r in ["TU", "ER > TU", "ER"]:
    ids = ep.loc[(ep.estado != "medida") & (ep.ruta == r), "visit_occurrence_id"].unique()
    if len(ids):
        pick = rng.choice(ids, size=min(3, len(ids)), replace=False)
        ej = vd_raw[vd_raw.visit_occurrence_id.isin(pick)].sort_values(
            ["visit_occurrence_id", "visit_detail_start_datetime"])
        print(f"\nruta '{r}':")
        print(ej[["visit_occurrence_id", "visit_detail_concept_id",
                  "visit_detail_start_datetime", "visit_detail_end_datetime"]].to_string(index=False))

# ----------------------------------------------------------------------
# 8) Cobertura por ruta y por tipo de visita
# ----------------------------------------------------------------------
def cobertura(df, col):
    c = df.groupby(col).estado.value_counts().unstack(fill_value=0).reindex(columns=ESTADOS, fill_value=0)
    c["total"] = c.sum(axis=1)
    for e in ESTADOS:
        c["pct_" + e] = (100 * c[e] / c.total).round(1)
    return c.sort_values("total", ascending=False)

cob_ruta = cobertura(ep, "ruta_simple")
cob_tipo = cobertura(ep, "tipo_visita")
glob = (100 * ep.estado.value_counts(normalize=True)).reindex(ESTADOS).fillna(0).round(1).rename("pct")
glob_act = (100 * ep[ep.estado != "sin_actividad"].estado.value_counts(normalize=True)) \
    .reindex(ESTADOS[:3]).fillna(0).round(1).rename("pct")

titulo("8. COBERTURA")
print("por ruta (las 10 mas frecuentes):\n" + cob_ruta.head(10).to_string())
print("\npor tipo de visita:\n" + cob_tipo.to_string())
print("\nsobre episodios con actividad clinica (sin contar sin_actividad):\n" + glob_act.to_string())

# ----------------------------------------------------------------------
# 9) Tiempos (solo episodios medidos y sin error probable)
# ----------------------------------------------------------------------
ok = ep[(ep.estado == "medida") & ~ep.error_probable]
tot = ok.groupby("ruta_simple").horas_total.apply(resumen_horas).unstack()
tot = tot.sort_values("n", ascending=False)
tot["confiable"] = tot.n >= MIN_EPISODIOS

tot_tipo = ok.groupby(["tipo_visita", "hospitalizado"]).horas_total.apply(resumen_horas).unstack()

b = bloques.merge(ok[K + ["ruta", "ruta_simple"]], on=K)
er_ini = (b.pos == 1) & (b.etapa == "ER") & b.ruta.str.startswith("ER > ")
b = b[~er_ini].copy()
b["pos"] = b.groupby(K).cumcount() + 1
por_etapa = b.groupby(["ruta_simple", "pos", "etapa"]).horas.apply(resumen_horas).unstack().reset_index()
orden = tot.index.to_list()
por_etapa["_o"] = por_etapa.ruta_simple.map({r: i for i, r in enumerate(orden)})
por_etapa = por_etapa.sort_values(["_o", "pos"]).drop(columns="_o")

titulo("9. TIEMPOS POR RUTA (episodios medidos, sin error probable)")
print(tot.head(12).round(2).to_string())
print("\npor tipo de visita y hospitalizacion:\n" + tot_tipo.round(2).to_string())
print("\npor etapa, 4 rutas principales:")
print(por_etapa[por_etapa.ruta_simple.isin(orden[:4])].round(2).to_string(index=False))

# ----------------------------------------------------------------------
# 10) Espera de cama: del inicio del episodio a la primera HOSP
# ----------------------------------------------------------------------
bh = bloques.merge(ok[K + ["ini", "ruta_simple", "tipo_visita"]].rename(columns={"ini": "ini_ep"}), on=K)
ini_hosp = bh[bh.etapa == "HOSP"].groupby(K).ini.min().rename("ini_hosp")
bh = bh.merge(ini_hosp, left_on=K, right_index=True)
antes = bh[bh.ini < bh.ini_hosp]
fin_previo = antes.groupby(K).fin.max().rename("fin_previo")
esp = (bh.groupby(K).agg(ini_ep=("ini_ep", "first"), ini_hosp=("ini_hosp", "first"),
                         ruta_simple=("ruta_simple", "first"), tipo_visita=("tipo_visita", "first"))
         .join(fin_previo, how="inner"))
esp["espera_cama_h"] = (esp.ini_hosp - esp.ini_ep).dt.total_seconds() / 3600
esp["hueco_antes_hosp_h"] = ((esp.ini_hosp - esp.fin_previo).dt.total_seconds() / 3600).clip(lower=0)

def resumen_espera(df):
    r = resumen_horas(df.espera_cama_h)
    r["pct_mas_6h"] = round(100 * (df.espera_cama_h > 6).mean(), 1)
    r["pct_mas_24h"] = round(100 * (df.espera_cama_h > 24).mean(), 1)
    r["mediana_hueco_sin_etapa_h"] = df.hueco_antes_hosp_h.median()
    r["pct_con_hueco_mas_1h"] = round(100 * (df.hueco_antes_hosp_h > 1).mean(), 1)
    return r

esp_total = resumen_espera(esp).to_frame("todos").T
esp_tipo = esp.groupby("tipo_visita").apply(resumen_espera)
esp_ruta = esp.groupby("ruta_simple").apply(resumen_espera)
esp_ruta = esp_ruta[esp_ruta.n >= MIN_EPISODIOS].sort_values("n", ascending=False)

titulo("10. ESPERA DE CAMA (episodios medidos con alguna etapa antes de la primera HOSP)")
print("espera_cama = inicio del episodio hasta el inicio de la primera HOSP")
print("hueco_sin_etapa = tiempo sin ninguna etapa registrada justo antes de la HOSP\n")
print(esp_total.round(2).to_string())
print("\npor tipo de visita:\n" + esp_tipo.round(2).to_string())
print("\npor ruta:\n" + esp_ruta.round(2).to_string())

# ----------------------------------------------------------------------
# 11) Extremos y validacion de la estimacion por diagnosticos
# ----------------------------------------------------------------------
titulo("11. EXTREMOS (episodios medidos)")
ext = med.groupby("ruta_simple").horas_total.agg(
    episodios="size", p99=lambda x: x.quantile(.99), maximo="max",
    mas_de_30_dias=lambda x: (x > 720).sum(), mas_de_90_dias=lambda x: (x > MAX_H).sum())
print(ext.sort_values("episodios", ascending=False).head(8).round(1).to_string())
print("\nlos 10 episodios medidos mas largos:")
print(med.nlargest(10, "horas_total")[["visit_occurrence_id", "person_id", "tipo_visita", "ruta",
                                       "ini", "fin", "horas_total"]].round({"horas_total": 1}).to_string(index=False))

validacion = pd.DataFrame()
rec = pd.DataFrame()
if hay_dx:
    val = ep[(ep.estado == "medida") & ep.horas_dx.notna() & (ep.horas_total > 0)]
    razon = val.horas_dx / val.horas_total
    validacion = pd.DataFrame({"episodios_validados": [len(val)], "p25": [razon.quantile(.25)],
                               "mediana": [razon.median()], "p75": [razon.quantile(.75)]}).round(2)
    rec = (ep[ep.estado == "minimo_dx"].groupby("ruta_simple").horas_dx
           .agg(episodios="size", mediana_min_h="median").sort_values("episodios", ascending=False))
    titulo("12. ESTIMACION POR DIAGNOSTICOS")
    print("validacion en episodios medidos: estimacion / duracion real")
    print(validacion.to_string(index=False))
    print("\nduracion minima estimada (episodios minimo_dx):\n" + rec.head(6).round(2).to_string())

# ----------------------------------------------------------------------
# 12) Salidas
# ----------------------------------------------------------------------
ep.to_csv("episodios.csv", index=False)
bloques.to_csv("bloques.csv", index=False)   # tramos de cada episodio limpio; lo usa preparar_variables.py
tot.round(3).to_csv("resumen_por_ruta.csv")
por_etapa.round(3).to_csv("resumen_por_etapa.csv", index=False)
esp.reset_index().to_csv("espera_cama.csv", index=False)
cob_ruta.to_csv("cobertura_por_ruta.csv")
cob_tipo.to_csv("cobertura_por_tipo_visita.csv")

try:
    with pd.ExcelWriter("resultados_finales.xlsx") as xw:
        glob.to_frame().to_excel(xw, sheet_name="cobertura_total")
        glob_act.to_frame().to_excel(xw, sheet_name="cobertura_con_actividad")
        cob_ruta.to_excel(xw, sheet_name="cobertura_por_ruta")
        cob_tipo.to_excel(xw, sheet_name="cobertura_por_tipo")
        tot.round(2).to_excel(xw, sheet_name="tiempos_por_ruta")
        tot_tipo.round(2).to_excel(xw, sheet_name="tiempos_por_tipo")
        por_etapa.round(2).to_excel(xw, sheet_name="tiempos_por_etapa", index=False)
        pd.concat([esp_total, esp_tipo, esp_ruta], keys=["total", "tipo_visita", "ruta"]) \
          .round(2).to_excel(xw, sheet_name="espera_cama")
        ext.round(1).to_excel(xw, sheet_name="extremos")
        if hay_dx:
            rec.round(2).to_excel(xw, sheet_name="minimos_estimados")
            validacion.to_excel(xw, sheet_name="validacion_dx", index=False)
    print("\nExcel guardado: resultados_finales.xlsx")
except ImportError:
    print("\n(para el Excel instala openpyxl: pip3 install openpyxl)")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = [r for r in orden if tot.loc[r, "confiable"]][:6]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.boxplot([ok.loc[ok.ruta_simple == r, "horas_total"] for r in top], showfliers=False)
    ax.set_xticks(range(1, len(top) + 1))
    ax.set_xticklabels(top)
    ax.set_yscale("log")
    ax.set_ylabel("horas (escala log)")
    ax.set_title("Duracion del episodio por ruta (episodios medidos)")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig("boxplot_rutas.png", dpi=150)
    plt.close()

    pct = cob_ruta.head(6)[["pct_" + e for e in ESTADOS]]
    pct.columns = ["medida", "minimo (diagnosticos)", "sin duracion", "sin actividad clinica"]
    ax = pct.iloc[::-1].plot(kind="barh", stacked=True, figsize=(10, 4))
    ax.set_xlabel("% de episodios")
    ax.set_ylabel("")
    ax.set_title("Cobertura de la duracion por ruta")
    ax.legend(loc="lower right", fontsize=8)
    plt.tight_layout()
    plt.savefig("cobertura_por_ruta.png", dpi=150)
    plt.close()
    print("Graficos guardados: boxplot_rutas.png y cobertura_por_ruta.png")
except ImportError:
    print("(matplotlib no instalado: se omiten los graficos)")