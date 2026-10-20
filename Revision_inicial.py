import pandas as pd
import numpy as np

# 1. Carga de datos
vd = pd.read_csv("visit_detail.csv", parse_dates=["visit_detail_start_datetime", "visit_detail_end_datetime"])
vo = pd.read_csv("visit_occurrence.csv")

OFFSET = 1_746_478

# 2. Filtrar solo visitas de urgencias
vo = vo[vo.visit_concept_id == 9203]

# 3. Identificación y eliminación de copias (comparando original vs copia)
ini = (vd[vd.visit_detail_concept_id != 581479]
         .groupby("visit_occurrence_id").visit_detail_start_datetime.min().rename("ini"))
vo = vo.merge(ini, left_on="visit_occurrence_id", right_index=True, how="left")

orig = vo.set_index("visit_occurrence_id")[["person_id", "ini"]]
cand = vo.visit_occurrence_id - OFFSET
mismo_pac = cand.map(orig.person_id) == vo.person_id
mismo_ini = cand.map(orig.ini) == vo.ini
es_copia = cand.isin(orig.index) & (mismo_pac | mismo_ini)

print("copias removidas:", es_copia.sum(), "de", len(vo))
vo = vo[~es_copia]

vd = vd[vd.visit_occurrence_id.isin(vo.visit_occurrence_id)]

# 4. Quitar AMB y etapas abiertas (fin con milisegundos = fecha de extracción)
vd = vd[vd.visit_detail_concept_id != 581479]
vd = vd[vd.visit_detail_end_datetime.notna() & 
        (vd.visit_detail_end_datetime.dt.microsecond == 0)]

# 5. Asignar nombre de etapa y ordenar cronológicamente
etapa = {9203: "ER", 3045729: "TU", 9201: "HOSP"}
vd["etapa"] = vd.visit_detail_concept_id.map(etapa)
vd = vd.dropna(subset=["etapa"])

# 6. Agrupamiento por episodios (H = 168 horas) y bloques de etapas
H = 168
vd = vd.sort_values(["visit_occurrence_id", "visit_detail_start_datetime"])
v = vd.visit_occurrence_id

# Hueco contra el fin más tardío de las etapas anteriores
fin_max = vd.groupby(v).visit_detail_end_datetime.cummax()
prev_fin = fin_max.groupby(v).shift()
hueco_h = (vd.visit_detail_start_datetime - prev_fin).dt.total_seconds() / 3600
vd["episodio"] = (hueco_h > H).groupby(v).cumsum()

K = ["visit_occurrence_id", "episodio"]
g = vd.groupby(K)
vd["bloque"] = ((vd.etapa != g.etapa.shift()) | (vd.episodio != vd.groupby(v).episodio.shift())).cumsum()

bloques = (vd.groupby(K + ["bloque"])
             .agg(etapa=("etapa", "first"),
                  ini=("visit_detail_start_datetime", "min"),
                  fin=("visit_detail_end_datetime", "max"))
             .reset_index())
bloques["horas"] = (bloques.fin - bloques.ini).dt.total_seconds() / 3600
bloques["pos"] = bloques.groupby(K).cumcount() + 1

# 7. Ruta y duración total por episodio de visita
rutas = bloques.groupby(K).agg(
    ruta=("etapa", " > ".join),
    ini=("ini", "min"),
    fin=("fin", "max")
)
rutas["horas_total"] = (rutas.fin - rutas.ini).dt.total_seconds() / 3600
rutas = rutas[rutas.horas_total >= 0.25]  # >= 15 min

bloques = bloques.merge(rutas[["ruta"]], left_on=K, right_index=True)

# 8. Atípicos por ruta (IQR)
def fuera(s):
    q1, q3 = s.quantile([.25, .75]); i = q3 - q1
    return (s < q1 - 1.5*i) | (s > q3 + 1.5*i)

rutas["atipica"] = rutas.groupby("ruta").horas_total.transform(fuera)
bloques["atipica"] = bloques.groupby(["ruta", "pos"]).horas.transform(fuera)

# 9. Resultados y resúmenes
# --- Total por ruta ---
tot = rutas.groupby("ruta").agg(
    visitas=("horas_total", "size"),
    mediana_h=("horas_total", "median"),
    media_h=("horas_total", "mean"),
    media_sin_atipicas_h=("horas_total", lambda s: s[~rutas.loc[s.index, "atipica"]].mean()),
    atipicas=("atipica", "sum"),
).sort_values("visitas", ascending=False)

# --- Por etapa dentro de cada ruta ---
por_etapa = (bloques.groupby(["ruta", "pos", "etapa"])
    .apply(lambda d: pd.Series({
        "n": len(d),
        "mediana_h": d.horas.median(),
        "media_sin_atipicas_h": d.loc[~d.atipica, "horas"].mean(),
        "atipicas": d.atipica.sum(),
    }))
    .reset_index())

# Imprimir resultados
print(tot.head(15))
print(por_etapa[por_etapa.ruta == "ER > TU > HOSP"])