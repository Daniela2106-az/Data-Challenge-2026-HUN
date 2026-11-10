"""
etapas_tu_por_examen.py  -  version 1 (10-nov-2026)
Continuacion de caracterizar_etapas_tu.py. A cada etapa TU cruda (antes de la cama) se le asignan los laboratorios de la persona real cuya hora de toma cae dentro de su
intervalo, y se etiqueta la etapa por el TIPO de examen. Pregunta de Daniela: ¿que tipo de etapa TU dura mas?

LO QUE SE PUEDE Y NO SE PUEDE
  - Laboratorio: tiene hora (measurement_datetime) y sirve. PERO el 46,5 % de las filas de laboratorio en la espera viene con concepto 0 (sin traducir): de esas solo
    se sabe que hubo una toma, no que examen fue. Entre las traducidas hay 71 conceptos (hemograma, creatinina, gases, troponina, cultivos...), que se agrupan en categorias.
  - Diagnostico: se pudo asignar a la etapa TU por la hora del PRIMER registro de cada diagnostico (caracterizar_etapas_tu.py): casi todos caen en la primera etapa.
  - Procedimiento: NO tiene hora (procedure_date vacia): no se puede asignar a ninguna etapa.

CATEGORIAS DE EXAMEN (por concepto; ver CATEGORIAS) y ETIQUETA DE LA ETAPA (la primera que aplique, en este orden de prioridad):
  inestabilidad (gases, lactato) > cardiaco (troponina, BNP, CK) > infeccion (cultivos, PCR, antibiograma, serologias) > coagulacion > higado y pancreas > metabolico y endocrino
  > orina y embarazo > rutina (hemograma, urea, creatinina, electrolitos, glucosa) > solo tomas sin traducir > sin toma.

SALIDAS (HUN_TABLAS): etapas_examen_categorias.csv, etapas_examen_por_posicion.csv, etapas_examen_duracion.csv, etapas_examen_primera_vs_espera.csv, etapas_examen_duracion_2h.csv, etapas_examen_resumen.txt
ENTRADAS las de caracterizar_etapas_tu.py (espera_labs_*.csv de la consulta sql/espera_labs_dx_con_hora.sql, visit_detail.csv, tabla_episodios.parquet, episodios.csv)
COMO CORRERLO  python3 src/etapas_tu_por_examen.py   (1-2 min)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caracterizar_tu as ct  # noqa: E402
import caracterizar_etapas_tu as cet  # noqa: E402

TABLAS = ct.TABLAS
LINEAS = []

CATEGORIAS = {
    "inestabilidad": {4239236: "gases arteriales", 36309462: "gases arteriales", 4267144: "gases venosos", 4213582: "lactato", 3014111: "lactato"},
    "cardiaco": {3033745: "troponina", 4007805: "troponina", 44812010: "BNP", 3007220: "creatina quinasa"},
    "infeccion": {4252846: "hemocultivo aerobio", 4252847: "hemocultivo anaerobio", 4267650: "cultivo LCR", 46272908: "PCR", 40547237: "antibiograma", 4032801: "antibiograma",
                  42529218: "VIH", 37172372: "hepatitis B", 4178483: "toxoplasma", 3027529: "toxoplasma", 4058393: "sifilis (RPR)", 4198581: "dengue"},
    "coagulacion": {4245261: "tiempo de protrombina", 3034426: "tiempo de protrombina", 44809202: "TPT", 4175016: "TPT", 46287143: "dimero D"},
    "higado y pancreas": {3045524: "bilirrubina", 4230543: "bilirrubina", 4146380: "ALT", 4263457: "AST", 4230636: "fosfatasa alcalina", 3016771: "amilasa", 3024561: "albumina",
                          4012918: "LDH", 4119650: "proteina total", 4288601: "albumina/globulina"},
    "metabolico y endocrino": {4184637: "HbA1c", 4246879: "TSH", 3008486: "T4 libre", 4008265: "colesterol", 4032789: "trigliceridos", 4176561: "ferritina", 3001122: "ferritina"},
    "orina y embarazo": {4099313: "uroanalisis", 4150621: "creatinina en orina", 3020876: "proteina 24 h", 37398200: "beta-hCG"},
    "rutina": {4016928: "hemograma", 4153000: "hemoglobina", 4151358: "hematocrito", 4324383: "creatinina", 4074649: "urea", 3024641: "urea", 4245152: "potasio", 4154489: "potasio",
               3019550: "sodio", 4097430: "sodio", 4019545: "cloro", 3014576: "cloro", 4331286: "glucosa", 3013826: "glucosa", 4144235: "glucosa", 4243005: "magnesio",
               4216722: "calcio", 3021347: "calcio ionizado"},
    "otros (sangre y transfusion)": {4263581: "reticulocitos", 3002529: "grupo sanguineo", 4267525: "grupo sanguineo"},
}
PRIORIDAD = ["inestabilidad", "cardiaco", "infeccion", "coagulacion", "higado y pancreas", "metabolico y endocrino", "orina y embarazo", "rutina", "otros (sangre y transfusion)"]
CONCEPTO_A_CAT = {cid: cat for cat, d in CATEGORIAS.items() for cid in d}


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def etiqueta(cats, hay_toma):
    if not hay_toma:
        return "sin toma"
    for c in PRIORIDAD:
        if c in cats:
            return c
    return "solo tomas sin traducir"


def main():
    TABLAS.mkdir(parents=True, exist_ok=True)
    c = ct.cohorte()
    vis = ct.visitas_de_estancia()
    E = cet.etapas_tu(c)
    L = pd.concat([pd.read_csv(ct.CONS / f"espera_labs_{a}.csv", parse_dates=["measurement_datetime"]) for a in range(2023, 2027)], ignore_index=True)
    L = L.merge(vis, on="visit_occurrence_id").merge(c[["estancia_id", "real", "ini_est", "ini_hosp_est"]], on="estancia_id")
    L = L[(L.person_id == L.real) & (L.measurement_datetime >= L.ini_est) & (L.measurement_datetime < L.ini_hosp_est)]
    L = L.drop_duplicates(["estancia_id", "measurement_datetime", "measurement_concept_id"])
    L["categoria"] = L.measurement_concept_id.map(CONCEPTO_A_CAT)
    decir(f"ETAPAS TU POR TIPO DE EXAMEN | {len(E):,} etapas de {E.estancia_id.nunique():,} estancias; {len(L):,} filas de laboratorio dentro de la ventana de espera (persona real)")
    decir(f"  Filas con concepto traducido: {100 * L.categoria.notna().mean():.1f} %; concepto 0 (sin traducir): {100 * (L.measurement_concept_id == 0).mean():.1f} %; "
          f"traducidas fuera de las categorias: {100 * ((L.measurement_concept_id != 0) & L.categoria.isna()).mean():.1f} %")

    # ---- laboratorios dentro de cada etapa
    j = E[["estancia_id", "k", "K", "posicion", "grupo", "ini", "fin_efectivo", "dur_h", "espera_cama_h"]].merge(
        L[["estancia_id", "measurement_datetime", "measurement_concept_id", "categoria"]], on="estancia_id", how="left")
    j = j[(j.measurement_datetime >= j.ini) & (j.measurement_datetime < j.fin_efectivo)]
    cats = j.dropna(subset=["categoria"]).groupby(["estancia_id", "k"]).categoria.agg(lambda s: set(s))
    hay = j.groupby(["estancia_id", "k"]).size()
    EE = E.set_index(["estancia_id", "k"]).copy()
    EE["hay_toma"] = EE.index.isin(hay.index)
    EE["cats"] = [cats.get(i, set()) for i in EE.index]
    EE["etiqueta"] = [etiqueta(cs, hy) for cs, hy in zip(EE.cats, EE.hay_toma)]
    con = EE[EE.index.get_level_values(0).isin(L.estancia_id.unique())]                      # estancias con alguna toma en la espera
    decir(f"  Estancias con alguna toma en la espera: {con.index.get_level_values(0).nunique():,} de {E.estancia_id.nunique():,}")

    # ---- 1. categorias presentes por posicion de la etapa
    decir("\n1. CATEGORIAS DE EXAMEN PRESENTES, POR POSICION DE LA ETAPA (% de las etapas que tienen al menos un examen de esa categoria; estancias con alguna toma)")
    f1 = []
    for pos in ["unica", "primera", "intermedia", "ultima"]:
        s = con[con.posicion == pos]
        fila = {"posicion": pos, "n_etapas": len(s), "con_alguna_toma": round(100 * s.hay_toma.mean(), 1)}
        for cat in PRIORIDAD:
            fila[cat] = round(100 * s.cats.map(lambda x: cat in x).mean(), 1)
        f1.append(fila)
    t1 = pd.DataFrame(f1)
    decir(t1.to_string(index=False))
    t1.to_csv(TABLAS / "etapas_examen_por_posicion.csv", index=False)
    pd.DataFrame([{"categoria": cat, "concepto": cid, "examen": nom} for cat, d in CATEGORIAS.items() for cid, nom in d.items()]).to_csv(TABLAS / "etapas_examen_categorias.csv", index=False)

    # ---- 2. duracion por etiqueta
    decir("\n2. DURACION DE LA ETAPA SEGUN SU ETIQUETA (horas; mediana, p75 y % de etapas de mas de 24 h), por posicion")
    f2 = []
    orden = PRIORIDAD + ["solo tomas sin traducir", "sin toma"]
    for pos in ["primera", "intermedia", "ultima"]:
        s = con[con.posicion == pos]
        for et in orden:
            g = s[s.etiqueta == et]
            if len(g) >= 30:
                f2.append({"posicion": pos, "etiqueta": et, "n_etapas": len(g), "dur_mediana_h": round(g.dur_h.median(), 1), "dur_p75_h": round(g.dur_h.quantile(.75), 1),
                           "pct_mas_24h": round(100 * (g.dur_h > 24).mean(), 1), "pct_de_la_espera_mediana": round(100 * (g.dur_h / g.espera_cama_h).median(), 1)})
    t2 = pd.DataFrame(f2)
    for pos in ["primera", "intermedia", "ultima"]:
        decir(f"  etapa {pos}:")
        decir(t2[t2.posicion == pos].drop(columns="posicion").to_string(index=False))
    t2.to_csv(TABLAS / "etapas_examen_duracion.csv", index=False)

    # ---- 3. la etiqueta de la primera etapa frente a la espera total
    decir("\n3. LO QUE SE PIDE EN LA PRIMERA ETAPA FRENTE A LA ESPERA TOTAL DE LA ESTANCIA (estancias con 2 o mas etapas)")
    p = con[(con.posicion == "primera")].reset_index()
    f3 = []
    for et in orden:
        g = p[p.etiqueta == et]
        if len(g) >= 30:
            f3.append({"etiqueta_primera_etapa": et, "n_estancias": len(g), "espera_total_mediana_h": round(g.espera_cama_h.median(), 1), "espera_total_p90_h": round(g.espera_cama_h.quantile(.9), 1),
                       "pct_espera_mas_24h": round(100 * (g.espera_cama_h > 24).mean(), 1), "edad_mediana": round(float(g.edad.median()), 0)})
    t3 = pd.DataFrame(f3)
    decir(t3.to_string(index=False))
    t3.to_csv(TABLAS / "etapas_examen_primera_vs_espera.csv", index=False)

    # ---- 4. etiqueta por lo que se pide en las PRIMERAS 2 H de cada etapa (misma exposicion para todas; evita el sesgo de que una etapa larga tiene mas tiempo para tener cualquier examen)
    decir("\n4. DURACION SEGUN LO QUE SE PIDE EN LAS PRIMERAS 2 H DE LA ETAPA (solo etapas que duran mas de 2 h y estancias con alguna toma; misma ventana para todas)")
    j2 = j.copy()
    j2 = j2[(j2.measurement_datetime - j2.ini) < pd.Timedelta(hours=2)]
    cats2 = j2.dropna(subset=["categoria"]).groupby(["estancia_id", "k"]).categoria.agg(lambda s: set(s))
    hay2 = j2.groupby(["estancia_id", "k"]).size()
    EE["hay_toma_2h"] = EE.index.isin(hay2.index)
    EE["cats_2h"] = [cats2.get(i, set()) for i in EE.index]
    EE["etiqueta_2h"] = [etiqueta(cs, hy) for cs, hy in zip(EE.cats_2h, EE.hay_toma_2h)]
    c2 = EE[(EE.dur_h > 2) & EE.index.get_level_values(0).isin(L.estancia_id.unique())]
    f4 = []
    for pos in ["primera", "intermedia", "ultima"]:
        for et in orden:
            g = c2[(c2.posicion == pos) & (c2.etiqueta_2h == et)]
            if len(g) >= 30:
                f4.append({"posicion": pos, "etiqueta_primeras_2h": et, "n_etapas": len(g), "dur_mediana_h": round(g.dur_h.median(), 1), "dur_p75_h": round(g.dur_h.quantile(.75), 1),
                           "pct_mas_24h": round(100 * (g.dur_h > 24).mean(), 1)})
    t4 = pd.DataFrame(f4)
    for pos in ["primera", "intermedia", "ultima"]:
        decir(f"  etapa {pos}:")
        decir(t4[t4.posicion == pos].drop(columns="posicion").to_string(index=False))
    t4.to_csv(TABLAS / "etapas_examen_duracion_2h.csv", index=False)
    (TABLAS / "etapas_examen_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    main()
