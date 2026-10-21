"""
preparar_variables.py  -  semana 1, version 2 (20-oct-2026)
Toma los episodios limpios de analisis_etapas.py y les agrega las variables para los
componentes 2 (factores de retraso) y 3 (modelos): calendario, paciente, diagnostico,
complejidad, ocupacion del hospital al llegar y reingresos.

CAMBIOS v2
  - Los diagnosticos, procedimientos y laboratorios de una visita copia pasan a su visita
    original (en v1 se perdian: el 97 % de los episodios quedaba sin diagnostico).
  - Guarda dx_frecuencias.csv para armar mapeo_dx.csv (SNOMED no trae capitulos).
  - Laboratorios de las primeras 6 h como factor (el total de la visita crece con la espera).
  - Reingresos sin contar los registros solo-ER sin actividad.
  - Nueva seccion 7b: hora de ingreso a cama frente a hora de alta.

ORDEN
  1. Corre analisis_etapas.py (v3.2). Deja episodios.csv, bloques.csv, espera_cama.csv y copias.csv.
  2. Exporta desde DBeaver las consultas del archivo consultas_semana1.sql:
       person.csv                       (obligatorio)
       diagnosticos_por_visita.csv      (obligatorio)
       procedimientos_por_visita.csv    (opcional)
       laboratorios_por_visita.csv      (opcional)
  3. Corre este script en la misma carpeta.

SALIDAS
  tabla_episodios.csv (y .parquet si tienes pyarrow)  una fila por episodio, todas las variables
  serie_horaria.csv       llegadas y ocupacion por hora   (modelo de saturacion, Power BI)
  serie_diaria.csv        lo mismo por dia
  mapa_calor_llegadas.csv llegadas promedio por dia de la semana y hora
  factores_espera_cama.csv  espera de cama segun cada variable (componente 2)
  factores_duracion_tu.csv  duracion de los episodios de alta desde urgencias segun cada variable
  altas_ingresos_por_hora.csv  % de altas, ingresos a cama y llegadas por hora del dia
  dx_frecuencias.csv      diagnosticos por frecuencia (para mapeo_dx.csv)
  variables_semana1.xlsx  todo lo anterior + diccionario de variables
  mapa_calor_llegadas.png, espera_vs_ocupacion.png, serie_diaria.png, altas_ingresos_por_hora.png
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

# Carpetas del proyecto (el script puede correrse desde cualquier lugar)
RAIZ = Path(__file__).resolve().parent.parent
CRUDOS = RAIZ / "datos" / "crudos"            # CSV exportados de la base (DBeaver)
PROC = RAIZ / "datos" / "procesados"          # tablas que producen los scripts
REF = RAIZ / "datos" / "referencia"           # archivos hechos a mano (mapeo_dx.csv)
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
EXCEL = RAIZ / "resultados" / "excel"
for _d in (PROC, TABLAS, GRAFICOS, EXCEL):
    _d.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# Parametros
# ----------------------------------------------------------------------
# La ocupacion se subestima al principio (estancias que empezaron antes de 2023 no estan)
# y al final (las etapas abiertas a la fecha de extraccion se quitaron). Fuera de este
# rango la ocupacion se marca como poco confiable.
OCUP_DESDE = "2023-02-01"
OCUP_HASTA = "2026-06-01"
UMBRAL_ESPERA_H = 24
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


def requerido(nombre):
    if not os.path.exists(nombre):
        raise SystemExit(f"Falta {nombre}. Revisa el paso ORDEN al inicio del script.")


for f in [PROC / "episodios.csv", PROC / "bloques.csv", PROC / "espera_cama.csv", PROC / "copias.csv", CRUDOS / "person.csv",
          CRUDOS / "diagnosticos_por_visita.csv"]:
    requerido(f)

# copia -> visita original que se quedo (sale de analisis_etapas.py v3.2)
_cop = pd.read_csv(PROC / "copias.csv")
if "misma_persona" in _cop:    # solo se pasan datos de copias de la misma persona
    _cop = _cop[_cop.misma_persona]
RAIZ = _cop.set_index("visit_occurrence_id").raiz_id


def a_raiz(df, nombre):
    """Pasa las filas de una copia a su visita original e informa cuantas estaban en copias."""
    df = df.dropna(subset=["visit_occurrence_id"]).copy()   # por si algun CSV trae una fila sin visita
    df["en_copia"] = df.visit_occurrence_id.isin(RAIZ.index)
    df["visit_occurrence_id"] = df.visit_occurrence_id.map(RAIZ).fillna(df.visit_occurrence_id).astype("int64")
    print(f"{Path(nombre).name}: {len(df)} visitas en el archivo, {df.en_copia.mean():.1%} colgadas de una copia")
    return df

# ----------------------------------------------------------------------
# 1) Episodios
# ----------------------------------------------------------------------
ep = pd.read_csv(PROC / "episodios.csv", parse_dates=["ini", "fin"])
ep = ep.drop(columns=[c for c in ["n_proc", "n_dx", "dx_max"] if c in ep.columns])
K = ["visit_occurrence_id", "episodio"]
n0 = len(ep)
titulo("1. EPISODIOS")
print("episodios:", n0, "| pacientes:", ep.person_id.nunique())

# variable objetivo de duracion: solo episodios con fin real y sin error probable
ep["horas_validas"] = ep.horas_total.where((ep.estado == "medida") & ~ep.error_probable)

esp = pd.read_csv(PROC / "espera_cama.csv")[K + ["espera_cama_h", "hueco_antes_hosp_h"]]
ep = ep.merge(esp, on=K, how="left")
ep[f"espera_mas_{UMBRAL_ESPERA_H}h"] = np.where(ep.espera_cama_h.notna(),
                                                (ep.espera_cama_h > UMBRAL_ESPERA_H).astype(float), np.nan)
print("episodios con espera de cama medida:", int(ep.espera_cama_h.notna().sum()))

# ----------------------------------------------------------------------
# 2) Calendario de la llegada (inicio de la primera etapa del episodio)
# ----------------------------------------------------------------------
t = ep.ini
ep["fecha"] = t.dt.normalize()
ep["anio"] = t.dt.year
ep["mes"] = t.dt.month
ep["anio_mes"] = t.dt.to_period("M").astype(str)
ep["dia_semana_num"] = t.dt.dayofweek
ep["dia_semana"] = pd.Categorical(ep.dia_semana_num.map(dict(enumerate(DIAS))), categories=DIAS, ordered=True)
ep["hora"] = t.dt.hour
ep["franja"] = pd.cut(ep.hora, [-1, 5, 11, 17, 23],
                      labels=["madrugada 0-5", "manana 6-11", "tarde 12-17", "noche 18-23"])
ep["fin_de_semana"] = ep.dia_semana_num >= 5
try:
    import holidays
    fest = holidays.Colombia(years=range(ep.anio.min(), ep.anio.max() + 1))
    ep["festivo"] = ep.fecha.dt.date.isin(list(fest.keys()))
    ep["dia_no_habil"] = ep.fin_de_semana | ep.festivo
except ImportError:
    ep["festivo"] = np.nan
    ep["dia_no_habil"] = ep.fin_de_semana
    print("\nAVISO: instala 'holidays' (pip3 install holidays) para marcar festivos de Colombia.")

# ----------------------------------------------------------------------
# 3) Paciente: edad y sexo
# ----------------------------------------------------------------------
pe = pd.read_csv(CRUDOS / "person.csv")
ep = ep.merge(pe[["person_id", "year_of_birth", "sexo"]], on="person_id", how="left")
ep["edad"] = (ep.anio - ep.year_of_birth).where(lambda s: s.between(0, 110))
ep["grupo_edad"] = pd.cut(ep.edad, [-1, 4, 14, 29, 44, 59, 74, 200],
                          labels=["0-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+"])
s = ep.sexo.fillna("").str.upper()
ep["sexo"] = np.select([s.str.startswith("FEMALE"), s.str.startswith("MALE")], ["Mujer", "Hombre"], "Otro/desconocido")

titulo("3. PACIENTE")
print("episodios con paciente encontrado en person.csv:", f"{ep.year_of_birth.notna().mean():.1%}")
print("edad valida (0-110):", f"{ep.edad.notna().mean():.1%}")
print(ep.sexo.value_counts().to_string())
print(ep.grupo_edad.value_counts(sort=False).to_string())

# ----------------------------------------------------------------------
# 4) Diagnostico principal (primer diagnostico mapeado de la visita) y complejidad
# ----------------------------------------------------------------------
CAP_CIE10 = [("A", "B", "Infecciosas"), ("C", "C", "Tumores"), ("D0", "D4", "Tumores"),
             ("D5", "D8", "Sangre e inmunidad"), ("E", "E", "Endocrinas y metabolicas"),
             ("F", "F", "Salud mental"), ("G", "G", "Sistema nervioso"), ("H0", "H5", "Ojo"),
             ("H6", "H9", "Oido"), ("I", "I", "Circulatorio"), ("J", "J", "Respiratorio"),
             ("K", "K", "Digestivo"), ("L", "L", "Piel"), ("M", "M", "Musculoesqueletico"),
             ("N", "N", "Genitourinario"), ("O", "O", "Embarazo y parto"), ("P", "P", "Perinatal"),
             ("Q", "Q", "Congenitas"), ("R", "R", "Sintomas y signos sin diagnostico"),
             ("S", "T", "Traumatismos e intoxicaciones"), ("V", "Y", "Causas externas"),
             ("Z", "Z", "Factores de salud y contacto con servicios")]


def capitulo(cod):
    if not isinstance(cod, str) or not cod:
        return np.nan
    c = cod.upper()
    for a, b, nombre in CAP_CIE10:
        if a <= c[:len(a)] <= b:
            return nombre
    return np.nan


titulo("4. DIAGNOSTICO PRINCIPAL Y COMPLEJIDAD")
dx = a_raiz(pd.read_csv(CRUDOS / "diagnosticos_por_visita.csv"), CRUDOS / "diagnosticos_por_visita.csv")
# si el original y su copia tienen diagnostico, gana el del original; n_dx_distintos = el mayor
dx = dx.sort_values(["visit_occurrence_id", "en_copia"])
n_dx = dx.groupby("visit_occurrence_id").n_dx_distintos.max()
dx = dx.drop_duplicates("visit_occurrence_id").drop(columns=["en_copia", "n_dx_distintos"])
dx["n_dx_distintos"] = dx.visit_occurrence_id.map(n_dx)
ep = ep.merge(dx, on="visit_occurrence_id", how="left")
print(f"episodios con diagnostico principal: {ep.dx_nombre.notna().mean():.1%}")
print("vocabularios:\n" + ep.dx_vocabulario.value_counts(dropna=False).head(6).to_string())

# frecuencia de diagnosticos: con este archivo se arma mapeo_dx.csv (dx_nombre -> categoria_dx)
frec = ep.dx_nombre.value_counts().rename("episodios").to_frame()
frec["pct_acumulado"] = (100 * frec.episodios.cumsum() / frec.episodios.sum()).round(1)
frec.to_csv(TABLAS / "dx_frecuencias.csv", index_label="dx_nombre")
print(f"diagnosticos distintos: {len(frec)} | los 300 mas frecuentes cubren "
      f"{frec.pct_acumulado.iloc[min(299, len(frec) - 1)] if len(frec) else 0} % de los episodios con diagnostico")

if os.path.exists(REF / "mapeo_dx.csv"):
    mp = pd.read_csv(REF / "mapeo_dx.csv").drop_duplicates("dx_nombre").set_index("dx_nombre").categoria_dx
    ep["categoria_dx"] = ep.dx_nombre.map(mp)
    ep.loc[ep.dx_nombre.notna() & ep.categoria_dx.isna(), "categoria_dx"] = "Otros"
    print("agrupacion: mapeo_dx.csv")
elif "dx_codigo" in ep and ep.dx_vocabulario.fillna("").str.upper().str.startswith("ICD10").mean() > 0.5:
    ep["categoria_dx"] = ep.dx_codigo.map(capitulo)
    print("agrupacion: capitulos CIE-10")
else:
    top = ep.dx_nombre.value_counts().head(14).index
    ep["categoria_dx"] = ep.dx_nombre.where(ep.dx_nombre.isin(top), "Otros").where(ep.dx_nombre.notna())
    print("agrupacion provisional: 14 diagnosticos mas frecuentes + 'Otros' (falta mapeo_dx.csv)")
ep["categoria_dx"] = ep.categoria_dx.fillna("Sin diagnostico")
ep["n_dx_distintos"] = ep.n_dx_distintos.fillna(0)
print("\n" + ep.categoria_dx.value_counts().head(16).to_string())
print("OJO: el 88 % de los diagnosticos se registra despues de las primeras 2 h; no usar en un")
print("modelo que diga predecir 'al llegar'. Sirve para describir y para factores de retraso.")


def por_visita_max(nombre, cols):
    """Lee un conteo por visita, pasa copias al original y toma el mayor (sumar contaria doble)."""
    if not os.path.exists(nombre):
        print(f"AVISO: falta {nombre}; {', '.join(cols)} quedan vacios.")
        return pd.DataFrame(columns=["visit_occurrence_id"] + cols)
    d = a_raiz(pd.read_csv(nombre), nombre)
    cols = [c for c in cols if c in d.columns]
    return d.groupby("visit_occurrence_id")[cols].max().reset_index()


print()
ep = ep.merge(por_visita_max(CRUDOS / "procedimientos_por_visita.csv", ["n_proc_distintos"]), on="visit_occurrence_id", how="left")
ep = ep.merge(por_visita_max(CRUDOS / "laboratorios_por_visita.csv",
                             ["n_lab", "n_lab_distintos", "n_lab_6h", "n_lab_antes_hosp"]),
              on="visit_occurrence_id", how="left")
for c in ["n_proc_distintos", "n_lab", "n_lab_distintos", "n_lab_6h", "n_lab_antes_hosp"]:
    if c not in ep:
        ep[c] = np.nan
    ep[c] = pd.to_numeric(ep[c], errors="coerce")
    if ep[c].notna().any():
        ep[c] = ep[c].fillna(0)
ep.loc[~ep.hospitalizado, "n_lab_antes_hosp"] = np.nan
print(f"episodios con algun laboratorio: {(ep.n_lab > 0).mean():.1%}")
if ep.n_lab_6h.isna().all():
    print("AVISO: laboratorios_por_visita.csv no trae n_lab_6h; corre la consulta 4 nueva de consultas_semana1.sql.")

# ----------------------------------------------------------------------
# 5) Ocupacion del hospital en el momento de la llegada
# ----------------------------------------------------------------------
bl = pd.read_csv(PROC / "bloques.csv", parse_dates=["ini", "fin"])
hosp = bl[bl.etapa == "HOSP"]
tu = bl[(bl.etapa == "TU") & (bl.fin > bl.ini)]


def abiertos(ini, fin, momentos):
    """Cuantos tramos [ini, fin) estan abiertos en cada momento (sin contar los que empiezan justo ahi)."""
    a = np.sort(ini.values.astype("datetime64[ns]"))
    b = np.sort(fin.values.astype("datetime64[ns]"))
    m = momentos.values.astype("datetime64[ns]")
    return np.searchsorted(a, m, side="left") - np.searchsorted(b, m, side="right")


def llegadas_previas(llegadas, momentos, horas):
    a = np.sort(llegadas.values.astype("datetime64[ns]"))
    m = momentos.values.astype("datetime64[ns]")
    return np.searchsorted(a, m, side="left") - np.searchsorted(a, m - np.timedelta64(horas, "h"), side="left")


ep["ocup_hosp"] = abiertos(hosp.ini, hosp.fin, ep.ini)
ep["ocup_tu"] = abiertos(tu.ini, tu.fin, ep.ini)
ep["llegadas_6h_previas"] = llegadas_previas(ep.ini, ep.ini, 6)
ep["llegadas_24h_previas"] = llegadas_previas(ep.ini, ep.ini, 24)
ep["ocupacion_confiable"] = ep.ini.between(pd.Timestamp(OCUP_DESDE), pd.Timestamp(OCUP_HASTA), inclusive="left")

titulo("5. OCUPACION AL LLEGAR")
print("ocup_hosp = pacientes en cama (etapa HOSP abierta) en el momento de la llegada")
print("ocup_tu   = pacientes en atencion de urgencias con duracion registrada (TU abierta)")
print("OJO: ocup_tu se queda corta, porque el 55 % de los TU no tiene hora de fin y no se puede contar.")
print(ep.loc[ep.ocupacion_confiable, ["ocup_hosp", "ocup_tu", "llegadas_6h_previas", "llegadas_24h_previas"]]
      .describe(percentiles=[.1, .5, .9]).round(1).to_string())

# ----------------------------------------------------------------------
# 6) Reingresos del mismo paciente
# ----------------------------------------------------------------------
ep = ep.sort_values(["person_id", "ini"]).reset_index(drop=True)
g = ep.groupby("person_id")
ep["n_episodios_previos"] = g.cumcount()
ep["dias_desde_anterior"] = (ep.ini - g.fin.shift()).dt.total_seconds() / 86400
ep["dias_hasta_siguiente"] = (g.ini.shift(-1) - ep.fin).dt.total_seconds() / 86400
ep["anterior_ruta"] = g.ruta_simple.shift()
ep["anterior_estado"] = g.estado.shift()
# un episodio anterior que es solo admision (ER) sin ninguna actividad clinica no cuenta como
# atencion: lo mas probable es un registro doble del mismo ingreso, no un reingreso
ant_vacio = (ep.anterior_ruta == "ER") & (ep.anterior_estado == "sin_actividad")
ep["tras_registro_vacio"] = ant_vacio & (ep.dias_desde_anterior <= 3)
ep["reingreso_72h"] = (ep.dias_desde_anterior <= 3) & ~ant_vacio
ep["reingreso_30d"] = (ep.dias_desde_anterior <= 30) & ~ant_vacio
sig_vacio = (g.ruta_simple.shift(-1) == "ER") & (g.estado.shift(-1) == "sin_actividad")
ep["vuelve_en_30d"] = (ep.dias_hasta_siguiente <= 30) & ~sig_vacio

titulo("6. REINGRESOS")
print("reingreso_72h = llego dentro de las 72 h siguientes a la salida de un episodio anterior con atencion")
print(f"episodios que son reingreso en 72 h: {ep.reingreso_72h.mean():.1%} | en 30 dias: {ep.reingreso_30d.mean():.1%}")
print(f"episodios que llegan <=72 h despues de un registro solo-ER sin actividad (no cuentan): "
      f"{ep.tras_registro_vacio.mean():.1%}")
r72 = ep[ep.dias_desde_anterior <= 3]
print("\nllegadas <=72 h tras otro episodio, segun que fue el anterior (las 8 combinaciones mas frecuentes):")
print((r72.anterior_ruta + " / " + r72.anterior_estado).value_counts().head(8).to_string())
print("\nhoras entre un episodio y el siguiente cuando son <=72 h:")
print(pd.cut(r72.dias_desde_anterior * 24, [-np.inf, 1, 6, 24, 72],
             labels=["<1 h", "1-6 h", "6-24 h", "24-72 h"]).value_counts(sort=False).to_string())
print("OJO: los datos empiezan en enero 2023; en los primeros meses no se ven los episodios anteriores.")

# ----------------------------------------------------------------------
# 7) Series por hora y por dia (llegadas y ocupacion)
# ----------------------------------------------------------------------
horas = pd.date_range(ep.ini.min().floor("h"), ep.ini.max().ceil("h"), freq="h")
sh = pd.DataFrame({"hora_inicio": horas})
cnt = ep.groupby(ep.ini.dt.floor("h")).size()
cnt_h = ep[ep.hospitalizado].groupby(ep.ini.dt.floor("h")).size()
sh["llegadas"] = sh.hora_inicio.map(cnt).fillna(0).astype(int)
sh["llegadas_que_se_hospitalizan"] = sh.hora_inicio.map(cnt_h).fillna(0).astype(int)
sh["ocup_hosp"] = abiertos(hosp.ini, hosp.fin, sh.hora_inicio)
sh["ocup_tu"] = abiertos(tu.ini, tu.fin, sh.hora_inicio)
sh["ocupacion_confiable"] = sh.hora_inicio.between(pd.Timestamp(OCUP_DESDE), pd.Timestamp(OCUP_HASTA), inclusive="left")

sd = sh.groupby(sh.hora_inicio.dt.normalize()).agg(
    llegadas=("llegadas", "sum"), llegadas_que_se_hospitalizan=("llegadas_que_se_hospitalizan", "sum"),
    ocup_hosp_media=("ocup_hosp", "mean"), ocup_hosp_max=("ocup_hosp", "max"),
    ocup_tu_media=("ocup_tu", "mean"), ocupacion_confiable=("ocupacion_confiable", "all"))
sd.index.name = "fecha"
esp_dia = ep.groupby("fecha").espera_cama_h.agg(espera_cama_mediana_h="median", n_espera="count")
sd = sd.join(esp_dia)
sd["dia_semana"] = sd.index.dayofweek.map(dict(enumerate(DIAS)))

mapa = (ep.groupby(["dia_semana_num", "hora"]).size() /
        ep.groupby("dia_semana_num").fecha.nunique()).unstack().round(2)
mapa.index = [DIAS[i] for i in mapa.index]

titulo("7. LLEGADAS")
print(f"llegadas por dia: mediana {sd.llegadas.median():.0f}, p10 {sd.llegadas.quantile(.1):.0f}, "
      f"p90 {sd.llegadas.quantile(.9):.0f}")
print("ultimo dia con datos:", sd.index.max().date(), "(julio 2026 esta incompleto)")
print("\nllegadas promedio por dia de la semana y hora (cada 3 horas):")
print(mapa.iloc[:, ::3].to_string())

# ----------------------------------------------------------------------
# 7b) A que hora se asignan camas y a que hora se liberan (hipotesis: las altas tardias frenan la cama)
# ----------------------------------------------------------------------
hb = hosp.groupby(K).agg(ingreso_cama=("ini", "min"), alta=("fin", "max")).reset_index()
hb = hb[hb.alta < pd.Timestamp(OCUP_HASTA)]
ah = pd.DataFrame({
    "pct_ingresos_a_cama": 100 * hb.ingreso_cama.dt.hour.value_counts(normalize=True),
    "pct_altas": 100 * hb.alta.dt.hour.value_counts(normalize=True),
    "pct_llegadas_que_se_hospitalizan": 100 * ep[ep.hospitalizado].hora.value_counts(normalize=True),
}).reindex(range(24)).fillna(0)
ah["mediana_espera_cama_h_segun_hora_llegada"] = \
    ep[ep.espera_cama_h.notna()].groupby("hora").espera_cama_h.median().reindex(range(24))
ah.index.name = "hora"

titulo("7b. HORA DE INGRESO A CAMA FRENTE A HORA DE ALTA (pacientes hospitalizados)")
print("ingreso a cama = inicio de la primera HOSP | alta = fin de la ultima HOSP del episodio")
print(ah.round(1).to_string())
print(f"\naltas antes del mediodia: {100 * (hb.alta.dt.hour < 12).mean():.1f} % | "
      f"ingresos a cama antes del mediodia: {100 * (hb.ingreso_cama.dt.hour < 12).mean():.1f} %")
print("Lectura: si las altas se concentran en la tarde y los ingresos a cama siguen a las altas,")
print("la cama se libera tarde y quien llega en la tarde espera hasta el dia siguiente.")

# ----------------------------------------------------------------------
# 8) Factores de retraso (componente 2)
# ----------------------------------------------------------------------
ep["quintil_ocup_hosp"] = pd.qcut(ep.ocup_hosp.where(ep.ocupacion_confiable), 5, duplicates="drop")
ep["quintil_llegadas_6h"] = pd.qcut(ep.llegadas_6h_previas.where(ep.ocupacion_confiable), 5, duplicates="drop")
# laboratorios en las primeras 6 h: misma ventana para todos, asi una espera larga no "fabrica"
# mas laboratorios (con el total de la visita la relacion va al reves)
ep["n_lab_6h_grupo"] = pd.cut(ep.n_lab_6h, [-1, 0, 5, 20, np.inf], labels=["0", "1-5", "6-20", "mas de 20"]) \
    if ep.n_lab_6h.notna().any() else np.nan

VARS = ["franja", "dia_semana", "dia_no_habil", "festivo", "mes", "anio", "grupo_edad", "sexo",
        "categoria_dx", "quintil_ocup_hosp", "quintil_llegadas_6h", "tipo_visita",
        "reingreso_30d", "n_lab_6h_grupo"]


def factores(df, y, umbral):
    filas = []
    base = df[y].median()
    for c in VARS:
        if c not in df or df[c].isna().all():
            continue
        g = df.groupby(c, observed=True)[y]
        r = pd.DataFrame({"n": g.size(), "mediana_h": g.median(), "p75_h": g.quantile(.75),
                          f"pct_mas_{umbral}h": g.apply(lambda s: 100 * (s > umbral).mean())})
        r = r[r.n >= 30]
        if r.empty:
            continue
        r["dif_vs_mediana_global_h"] = r.mediana_h - base
        r.insert(0, "valor", r.index.astype(str))
        r.insert(0, "variable", c)
        r["rango_de_la_variable_h"] = r.mediana_h.max() - r.mediana_h.min()
        filas.append(r.reset_index(drop=True))
    return pd.concat(filas, ignore_index=True)


hosp_ep = ep[ep.espera_cama_h.notna()]
fac_esp = factores(hosp_ep, "espera_cama_h", UMBRAL_ESPERA_H)
alta_tu = ep[(ep.ruta_simple == "TU") & ep.horas_validas.notna()]
fac_tu = factores(alta_tu, "horas_validas", 24)

titulo("8. FACTORES DE LA ESPERA DE CAMA (episodios hospitalizados)")
print(f"mediana global: {hosp_ep.espera_cama_h.median():.1f} h | "
      f"% mas de {UMBRAL_ESPERA_H} h: {100 * (hosp_ep.espera_cama_h > UMBRAL_ESPERA_H).mean():.1f}")
print("\nvariables ordenadas por cuanto cambia la mediana entre su mejor y su peor valor:")
print(fac_esp.groupby("variable").rango_de_la_variable_h.first().sort_values(ascending=False).round(1).to_string())
for c in ["franja", "quintil_llegadas_6h", "quintil_ocup_hosp", "dia_semana", "grupo_edad",
          "tipo_visita", "n_lab_6h_grupo", "categoria_dx"]:
    t_ = fac_esp[fac_esp.variable == c].drop(columns=["variable", "rango_de_la_variable_h"])
    if not t_.empty:
        print(f"\n[{c}]\n" + t_.round(1).to_string(index=False))
print("\nLectura: esto muestra asociaciones, no causas. La ocupacion y la hora se cruzan entre si;")
print("el modelo de la semana 3 separa el efecto de cada una.")

titulo("8b. FACTORES DE LA DURACION DE LOS EPISODIOS DE ALTA DESDE URGENCIAS (ruta TU, medidos)")
print("OJO: solo el 45 % de estos episodios tiene hora de fin; puede haber sesgo.")
print(fac_tu.groupby("variable").rango_de_la_variable_h.first().sort_values(ascending=False).round(1).to_string())

# ----------------------------------------------------------------------
# 9) Diccionario y salidas
# ----------------------------------------------------------------------
DICC = {
    "visit_occurrence_id, episodio": "llave del episodio (una visita puede tener varios episodios)",
    "ruta / ruta_simple": "orden de etapas; ruta_simple quita la ER inicial",
    "ini / fin": "inicio de la primera etapa y fin de la ultima etapa del episodio",
    "estado": "medida / minimo_dx / sin_duracion / sin_actividad (ver analisis_etapas.py)",
    "horas_validas": "duracion total, solo si estado = medida y no es error probable",
    "espera_cama_h": "inicio del episodio hasta la primera HOSP (solo hospitalizados)",
    "hueco_antes_hosp_h": "tiempo sin ninguna etapa justo antes de la HOSP",
    f"espera_mas_{UMBRAL_ESPERA_H}h": "1 si espera_cama_h > umbral (objetivo del modelo B)",
    "fecha, anio, mes, dia_semana, hora, franja": "calendario de la llegada",
    "dia_no_habil / festivo": "fin de semana o festivo de Colombia",
    "edad, grupo_edad, sexo": "de person (anio de llegada - year_of_birth)",
    "dx_concept_id, dx_nombre, categoria_dx": "primer diagnostico mapeado de la visita y su grupo",
    "n_dx_distintos, n_proc_distintos, n_lab": "complejidad: diagnosticos y procedimientos distintos, laboratorios (incluye los de sus copias)",
    "n_lab_6h": "laboratorios tomados en las primeras 6 h de la visita (sirve como factor)",
    "n_lab_antes_hosp": "laboratorios tomados antes de la primera HOSP (solo hospitalizados)",
    "tras_registro_vacio": "llego <=72 h despues de un episodio solo-ER sin actividad (probable registro doble)",
    "ocup_hosp": "pacientes en cama en el momento de la llegada",
    "ocup_tu": "pacientes en urgencias con TU medida en el momento de la llegada (se queda corta)",
    "llegadas_6h_previas / 24h": "llegadas en las 6 / 24 horas anteriores",
    "ocupacion_confiable": f"llegada entre {OCUP_DESDE} y {OCUP_HASTA}",
    "n_episodios_previos, dias_desde_anterior": "historia del paciente en la base",
    "reingreso_72h / reingreso_30d": "llego dentro de 72 h / 30 dias tras un episodio anterior con atencion",
    "vuelve_en_30d": "vuelve dentro de 30 dias despues de este episodio",
}
dicc = pd.DataFrame(list(DICC.items()), columns=["variable", "descripcion"])

cols_fuera = ["year_of_birth", "quintil_ocup_hosp", "quintil_llegadas_6h", "n_lab_6h_grupo"]
salida = ep.drop(columns=[c for c in cols_fuera if c in ep.columns])
salida.to_csv(PROC / "tabla_episodios.csv", index=False)
try:
    salida.to_parquet(PROC / "tabla_episodios.parquet", index=False)
    print("\ntabla_episodios.parquet guardada")
except ImportError:
    print("\n(para .parquet instala pyarrow: pip3 install pyarrow)")
sh.to_csv(PROC / "serie_horaria.csv", index=False)
sd.to_csv(PROC / "serie_diaria.csv")
mapa.to_csv(TABLAS / "mapa_calor_llegadas.csv")
fac_esp.round(2).to_csv(TABLAS / "factores_espera_cama.csv", index=False)
fac_tu.round(2).to_csv(TABLAS / "factores_duracion_tu.csv", index=False)
ah.round(2).to_csv(TABLAS / "altas_ingresos_por_hora.csv")

try:
    with pd.ExcelWriter(EXCEL / "variables_semana1.xlsx") as xw:
        dicc.to_excel(xw, sheet_name="diccionario", index=False)
        fac_esp.round(2).to_excel(xw, sheet_name="factores_espera_cama", index=False)
        fac_tu.round(2).to_excel(xw, sheet_name="factores_duracion_tu", index=False)
        mapa.to_excel(xw, sheet_name="mapa_calor_llegadas")
        ah.round(2).to_excel(xw, sheet_name="altas_ingresos_por_hora")
        frec.head(500).to_excel(xw, sheet_name="dx_frecuencias")
        sd.reset_index().assign(fecha=lambda d: d.fecha.dt.date).round(2) \
          .to_excel(xw, sheet_name="serie_diaria", index=False)
    print("Excel guardado: variables_semana1.xlsx")
except ImportError:
    print("(para el Excel instala openpyxl: pip3 install openpyxl)")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 3.8))
    im = ax.imshow(mapa.values, aspect="auto", cmap="Blues")
    ax.set_yticks(range(7))
    ax.set_yticklabels(mapa.index)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels(range(0, 24, 2))
    ax.set_xlabel("hora de llegada")
    ax.set_title("Llegadas promedio por dia de la semana y hora")
    fig.colorbar(im, ax=ax, label="episodios por hora")
    plt.tight_layout()
    plt.savefig(GRAFICOS / "mapa_calor_llegadas.png", dpi=150)
    plt.close()

    q = fac_esp[fac_esp.variable == "quintil_ocup_hosp"]
    if not q.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(q.valor, q.mediana_h, color="#3b6fb6")
        ax.set_xlabel("pacientes en cama al llegar (quintiles)")
        ax.set_ylabel("mediana de la espera de cama (h)")
        ax.set_title("Espera de cama segun la ocupacion del hospital")
        plt.xticks(rotation=15)
        plt.tight_layout()
        plt.savefig(GRAFICOS / "espera_vs_ocupacion.png", dpi=150)
        plt.close()

    fig, ax = plt.subplots(figsize=(11, 4))
    sdc = sd[sd.ocupacion_confiable]
    ax.plot(sdc.index, sdc.llegadas.rolling(7).mean(), label="llegadas por dia (media 7 dias)")
    ax.plot(sdc.index, sdc.ocup_hosp_media.rolling(7).mean(), label="pacientes en cama (media 7 dias)")
    ax.legend()
    ax.set_title("Llegadas y ocupacion por dia")
    plt.tight_layout()
    plt.savefig(GRAFICOS / "serie_diaria.png", dpi=150)
    plt.close()

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(ah.index, ah.pct_altas, marker="o", label="altas (fin de HOSP)")
    ax.plot(ah.index, ah.pct_ingresos_a_cama, marker="o", label="ingresos a cama (inicio de HOSP)")
    ax.plot(ah.index, ah.pct_llegadas_que_se_hospitalizan, ls="--", label="llegada de quienes se hospitalizan")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("hora del dia")
    ax.set_ylabel("% del total")
    ax.set_title("A que hora llegan, entran a cama y salen los pacientes hospitalizados")
    ax.legend()
    plt.tight_layout()
    plt.savefig(GRAFICOS / "altas_ingresos_por_hora.png", dpi=150)
    plt.close()
    print("Graficos guardados: mapa_calor_llegadas.png, espera_vs_ocupacion.png, serie_diaria.png, "
          "altas_ingresos_por_hora.png")
except ImportError:
    print("(matplotlib no instalado: se omiten los graficos)")

titulo("RESUMEN")
print("episodios en la tabla final:", len(salida), "(entraron", n0, ")")
print("columnas:", len(salida.columns))
