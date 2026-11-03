"""
construir_segmentos.py  -  version 1 (21-oct-2026)
Fase 2 del plan de cuellos de botella (docs/plan_de_accion.md, seccion 0).

QUE HACE
  1. Carga q3_episodios.csv (consulta Q3 de sql/consultas_cuellos_botella.sql) y corre controles.
  2. Construye los SEGMENTOS de cada episodio (espera de cama, urgencias antes de la cama, hueco antes
     de la cama, estancia en cama, urgencias sin hospitalizar) y los guarda en formato largo.
  3. Inventario por segmento: n, % medido, percentiles, % de casos > 6 h y > 24 h (total y por anio).
  4. Prueba de sesgo de medicion de TU: quien tiene duracion medida y quien no.
  5. Tiempo en urgencias antes de la cama por anio (la cola de TU sube: es real o es de registro?).

ENTRADA
  datos/crudos/q3_episodios.csv   (una fila por episodio; ver Q3)

SALIDAS
  datos/procesados/segmentos.csv
  resultados/tablas/inventario_segmentos.csv
  resultados/tablas/inventario_segmentos_por_anio.csv
  resultados/tablas/sesgo_medicion_urgencias.csv
  resultados/tablas/urgencias_antes_cama_por_anio.csv

REGLAS
  - (v1.1, 22-oct) ESTANCIAS GEMELAS: si dos episodios tienen exactamente el mismo inicio y fin de HOSP, es la misma
    estancia replicada entre dos personas (41 % de los episodios hospitalizados). Los segmentos de hospitalizacion
    (espera de cama, urgencias antes de la cama, hueco, estancia en cama) cuentan cada estancia UNA vez: se queda
    el episodio de menor visit_occurrence_id. Con DEDUP=0 se desactiva (solo para comparar).
  - Los segmentos se calculan para TODOS los episodios (el corte de 168 h solo decide como se forman).
  - La numeracion de "episodio" viene de antes de quitar episodios replicados: un 1 no significa que
    la visita este partida. Para eso se cuentan las filas por visita.
  - Espera de cama = inicio de la primera HOSP - inicio del episodio. Se excluye la hospitalizacion
    directa (la primera etapa ya es HOSP): no hay espera que medir.
  - Edades imposibles (anio de nacimiento < 1900 o mas de 110 anios) quedan en blanco, el episodio se queda.
  - Las llegadas previas de las primeras 6 / 24 h de la base quedan en blanco (no hay historia anterior).
  - Tope MAX_H: un segmento de mas de 90 dias queda fuera de las estadisticas.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

# SUFIJO (variable de entorno, vacio por defecto): permite correr el mismo script con otra version de Q3,
# por ejemplo SUFIJO=_u72 lee q3_episodios_u72.csv y guarda segmentos_u72.csv (prueba de sensibilidad).
SUFIJO = os.environ.get("SUFIJO", "")
RAIZ = Path(__file__).resolve().parent.parent
CRUDOS = RAIZ / "datos" / "crudos"
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
for _d in (PROC, TABLAS):
    _d.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# Parametros
# ----------------------------------------------------------------------
MAX_H = 2160                 # igual que analisis_etapas.py
DEDUP_ESTANCIAS = os.environ.get("DEDUP", "1") != "0"   # True: cada estancia en cama se cuenta una vez
K = ["visit_occurrence_id", "episodio"]
N_ESPERADO = 336_844         # filas de Q3 en la prueba (referencia, no es una regla)
TIPOS = {9203: "Urgencias", 3045729: "Treatment urgency", 9201: "Inpatient", 581479: "Ambulatorio"}
SEXOS = {8507: "Hombre", 8532: "Mujer"}
# clase de cada segmento (espera = candidato a cuello de botella; servicio = atencion clinica)
CLASES = {"espera_cama": "espera",
          "urgencias_antes_cama": "espera (mezcla atencion)",
          "hueco_antes_cama": "espera (sin etapa registrada)",
          "estancia_cama": "servicio",
          "urgencias_sin_hospitalizar": "descriptivo"}

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


def a_bool(s):
    """true/false (o vacio) -> booleano con vacios."""
    return s.astype("string").str.lower().map({"true": True, "false": False}).astype("boolean")


def horas(a, b):
    return (b - a).dt.total_seconds() / 3600


def pcts(s):
    return pd.Series({"p10": s.quantile(.10), "p25": s.quantile(.25), "p50": s.median(),
                      "p75": s.quantile(.75), "p90": s.quantile(.90),
                      "pct_mas_6h": 100 * (s > 6).mean(), "pct_mas_24h": 100 * (s > 24).mean()})


# ----------------------------------------------------------------------
# 1) Carga y controles
# ----------------------------------------------------------------------
titulo("1. CARGA Y CONTROLES")
ep = pd.read_csv(CRUDOS / f"q3_episodios{SUFIJO}.csv",
                 parse_dates=["ini", "fin_max", "ini_hosp", "fin_hosp", "fin_previo_hosp"])
ep["episodio"] = ep.episodio.astype(int)
for c in ["con_tiempo", "ultima_cerrada"]:
    ep[c] = a_bool(ep[c])
print("episodios:", len(ep), "| visitas:", ep.visit_occurrence_id.nunique())
if abs(len(ep) - N_ESPERADO) / N_ESPERADO > 0.02:
    print(f"  AVISO: se esperaban ~{N_ESPERADO} episodios (diferencia mayor al 2 %)")

# v1.2: llegada y cama a nivel de ESTANCIA (el minimo entre los registros gemelos del pipeline), asi la espera no depende de cual registro se conserve
_pip = PROC / "episodios.csv"
if _pip.exists() and "ini_est" in pd.read_csv(_pip, nrows=1).columns:
    _p = pd.read_csv(_pip, usecols=K + ["estancia_unica", "estancia_gemela", "ini_est", "ini_hosp_est"], parse_dates=["ini_est", "ini_hosp_est"])
    _p = _p.rename(columns={"estancia_unica": "_u", "estancia_gemela": "_g", "ini_est": "_ie", "ini_hosp_est": "_ihe"})
    ep = ep.merge(_p, on=K, how="left")
    _m = ep._ie.notna() & ep._ihe.notna() & ep.ini_hosp.notna()
    ep.loc[_m, "ini"] = ep.loc[_m, "_ie"]
    ep.loc[_m, "ini_hosp"] = ep.loc[_m, "_ihe"]
    ep = ep.drop(columns=["_ie", "_ihe"])

dup = ep.duplicated(["visit_occurrence_id", "episodio"]).sum()
print("episodios repetidos (visita, episodio):", dup, "(debe ser 0)")
assert dup == 0, "hay episodios repetidos: revisar Q3"

n_por_visita = ep.groupby("visit_occurrence_id").size()
print("visitas con mas de un episodio:", int((n_por_visita > 1).sum()),
      "| filas con episodio >= 1:", int((ep.episodio >= 1).sum()),
      "(un 1 no significa visita partida: el 0 pudo ser un episodio replicado y quitarse)")

ep["hospitalizado"] = ep.ini_hosp.notna()
ep["espera_h"] = horas(ep.ini, ep.ini_hosp)
print("esperas negativas:", int((ep.espera_h < 0).sum()), "(debe ser 0)")
print("fin_hosp antes que ini_hosp:", int((ep.fin_hosp < ep.ini_hosp).sum()), "(debe ser 0)")
ep["hosp_directa"] = ep.hospitalizado & (ep.espera_h <= 0)
print(f"hospitalizacion directa (primera etapa ya es HOSP): {int(ep.hosp_directa.sum())} -> sin espera de cama")
print("hueco < 0 (alguna etapa previa termina despues de ini_hosp):",
      int((horas(ep.fin_previo_hosp, ep.ini_hosp) < 0).sum()), "-> se recorta a 0")

# estancias gemelas (v1.1, 22-oct): la misma estancia en cama registrada en dos personas distintas
# (mismo inicio y mismo fin de HOSP). Se cuenta UNA vez: se queda el episodio de menor visit_occurrence_id.
_hh = ep.hospitalizado & ep.fin_hosp.notna()
_h = ep[_hh].sort_values(K)
ep["estancia_gemela"] = False
ep.loc[_h.index, "estancia_gemela"] = _h.duplicated(["ini_hosp", "fin_hosp"], keep=False).values
ep["estancia_unica"] = True
ep.loc[_h.index[_h.duplicated(["ini_hosp", "fin_hosp"], keep="first").values], "estancia_unica"] = False
print(f"estancias gemelas: {int(ep.estancia_gemela.sum())} episodios hospitalizados ({100 * ep.estancia_gemela.sum() / _hh.sum():.1f} %) "
      f"comparten inicio y fin de cama con otro | estancias unicas: {int((_hh & ep.estancia_unica).sum())} de {int(_hh.sum())}")
print(f"DEDUP_ESTANCIAS = {DEDUP_ESTANCIAS}: " + ("los segmentos de hospitalizacion cuentan cada estancia una vez"
                                                  if DEDUP_ESTANCIAS else "NO se deduplica (solo para comparar)"))
# v1.2 (1-nov-2026): la estancia unica y las gemelas salen del pipeline (analisis_etapas.py v3.8, CLAUDE.md 4.8) cuando esta episodios.csv: ademas de
# "mismo inicio y fin de cama" detecta las gemelas que comparten algun intervalo HOSP identico. Los episodios que no estan en el pipeline conservan la regla propia.
if "_u" in ep.columns:
    _n_cambia = int((ep._u.notna() & (ep._u != ep.estancia_unica)).sum())
    ep["estancia_unica"] = ep._u.fillna(ep.estancia_unica).astype(bool)
    ep["estancia_gemela"] = ep._g.fillna(ep.estancia_gemela).astype(bool)
    ep = ep.drop(columns=["_u", "_g"])
    print(f"estancia unica tomada del pipeline (v3.8): {_n_cambia} episodios cambian frente a la regla propia | "
          f"estancias unicas hospitalizadas: {int((_hh & ep.estancia_unica).sum())}")
USO = ep.estancia_unica if DEDUP_ESTANCIAS else pd.Series(True, index=ep.index)

# contexto de cada episodio
ep["edad"] = ep.ini.dt.year - ep.year_of_birth
mala_edad = (ep.year_of_birth < 1900) | (ep.edad > 110) | (ep.edad < 0)
print("edades imposibles (quedan en blanco):", int(mala_edad.sum()))
ep.loc[mala_edad, "edad"] = np.nan
ep["grupo_edad"] = pd.cut(ep.edad, [-1, 14, 44, 64, 200], labels=["0-14", "15-44", "45-64", "65+"])
ep["sexo"] = ep.gender_concept_id.map(SEXOS)
ep["tipo_visita"] = ep.visit_concept_id.map(TIPOS).fillna("Otro")
ep["anio"] = ep.ini.dt.year
ep["mes"] = ep.ini.dt.month
ep["hora"] = ep.ini.dt.hour
ep["dia_semana"] = ep.ini.dt.dayofweek
ep["fin_de_semana"] = ep.dia_semana >= 5
ep["franja"] = pd.cut(ep.hora, [-1, 5, 11, 17, 23],
                      labels=["madrugada 0-5", "manana 6-11", "tarde 12-17", "noche 18-23"])
# llegadas previas: las primeras 6 / 24 h de la base no tienen historia anterior
t0 = ep.ini.min()
ep.loc[ep.ini < t0 + pd.Timedelta(hours=6), "llegadas_6h_previas"] = np.nan
ep.loc[ep.ini < t0 + pd.Timedelta(hours=24), "llegadas_24h_previas"] = np.nan
print("primera llegada de la base:", t0)

CONTEXTO = ["ini", "anio", "mes", "hora", "dia_semana", "franja", "fin_de_semana", "edad", "grupo_edad", "sexo",
            "tipo_visita", "llegadas_6h_previas", "llegadas_24h_previas", "estancia_gemela"]
K = ["visit_occurrence_id", "episodio"]

# ----------------------------------------------------------------------
# 2) Segmentos (formato largo: una fila por episodio y segmento)
# ----------------------------------------------------------------------
titulo("2. SEGMENTOS")
piezas = []


def agregar(nombre, mask, h, medido):
    d = ep.loc[mask, K + CONTEXTO].copy()
    d["segmento"] = nombre
    d["clase"] = CLASES[nombre]
    d["horas"] = h[mask].values
    d["medido"] = medido[mask].astype(bool).values
    piezas.append(d)


con_cama = ep.hospitalizado & ~ep.hosp_directa & USO
todos = pd.Series(True, index=ep.index)
agregar("espera_cama", con_cama, ep.espera_h, todos)
agregar("urgencias_antes_cama", con_cama & ep.fin_previo_hosp.notna(),
        horas(ep.ini, ep.fin_previo_hosp).clip(lower=0), todos)
agregar("hueco_antes_cama", con_cama & ep.fin_previo_hosp.notna(),
        horas(ep.fin_previo_hosp, ep.ini_hosp).clip(lower=0), todos)
agregar("estancia_cama", ep.hospitalizado & USO, horas(ep.ini_hosp, ep.fin_hosp), ep.ultima_cerrada.fillna(False))
sin_hosp = (ep.n_hosp == 0) & (ep.n_tu > 0)
agregar("urgencias_sin_hospitalizar", sin_hosp, horas(ep.ini, ep.fin_max),
        (ep.con_tiempo.fillna(False)) & (ep.ultima_cerrada.fillna(False)))

seg = pd.concat(piezas, ignore_index=True)
# entra a las estadisticas: medido, no negativo y dentro del tope
seg["en_estadisticas"] = seg.medido & seg.horas.between(0, MAX_H)
print("segmentos:", len(seg), "| fuera de estadisticas por tope o negativos:",
      int((seg.medido & ~seg.horas.between(0, MAX_H)).sum()))
seg.to_csv(PROC / f"segmentos{SUFIJO}.csv", index=False)
print(f"guardado: datos/procesados/segmentos{SUFIJO}.csv")

# ----------------------------------------------------------------------
# 2b) Efecto de contar cada estancia una vez
# ----------------------------------------------------------------------
titulo("2b. EFECTO DE CONTAR CADA ESTANCIA UNA VEZ (antes y despues)")
DIAS = (pd.Timestamp("2026-07-01") - pd.Timestamp("2023-01-01")).days   # enero 2023 a junio 2026
V0, V1 = pd.Timestamp("2023-03-01"), pd.Timestamp("2026-04-10")          # ventana confiable para camas


def camas_little(g):
    """Camas ocupadas en promedio: horas de cama de la ventana / horas de la ventana."""
    s, e = g.ini_hosp.clip(lower=V0), g.fin_hosp.clip(upper=V1)
    return (e - s)[e > s].dt.total_seconds().sum() / 3600 / ((V1 - V0).total_seconds() / 3600)


hosp_ok = ep[_hh]
filas = []
for nombre, g_all in [("sin deduplicar", hosp_ok), ("una vez por estancia", hosp_ok[hosp_ok.estancia_unica])]:
    g = g_all[~g_all.hosp_directa]
    s = g.espera_h
    filas.append({"version": nombre, "estancias": len(g_all), "ingresos_por_dia": round(len(g_all) / DIAS, 1),
                  "camas_medias": round(camas_little(g_all), 1), "n_espera": len(s),
                  "espera_p25": round(s.quantile(.25), 1), "espera_p50": round(s.median(), 1),
                  "espera_p75": round(s.quantile(.75), 1), "espera_p90": round(s.quantile(.90), 1),
                  "pct_espera_mas_24h": round(100 * (s > 24).mean(), 1)})
comp = pd.DataFrame(filas)
print(comp.to_string(index=False))
comp.to_csv(TABLAS / f"comparacion_dedup{SUFIJO}.csv", index=False)

# ----------------------------------------------------------------------
# 3) Inventario por segmento
# ----------------------------------------------------------------------
titulo("3. INVENTARIO DE SEGMENTOS (horas)")


def inventario(df, por):
    filas = []
    for clave, g in df.groupby(por, observed=True):
        s = g.loc[g.en_estadisticas, "horas"]
        base = {"n_total": len(g), "n_medido": int(g.medido.sum()),
                "pct_medido": round(100 * g.medido.mean(), 1)}
        if len(s):
            base.update(pcts(s).round(1).to_dict())
        clave = clave if isinstance(clave, tuple) else (clave,)
        filas.append(dict(zip(por, clave)) | base)
    return pd.DataFrame(filas)


inv = inventario(seg, ["segmento", "clase"])
# fila extra: el hueco solo en los episodios que SI tienen hueco (casi todos son 0)
h_pos = seg[(seg.segmento == "hueco_antes_cama") & (seg.horas > 0)].assign(segmento="hueco_antes_cama (solo hueco > 0)")
inv = pd.concat([inv, inventario(h_pos, ["segmento", "clase"])], ignore_index=True)
print(inv.to_string(index=False))
inv.to_csv(TABLAS / f"inventario_segmentos{SUFIJO}.csv", index=False)

inv_anio = inventario(seg, ["segmento", "anio"])
inv_anio.to_csv(TABLAS / f"inventario_segmentos_por_anio{SUFIJO}.csv", index=False)
print("\nguardado: inventario_segmentos.csv e inventario_segmentos_por_anio.csv")

# ----------------------------------------------------------------------
# 4) Sesgo de medicion en urgencias sin hospitalizar
# ----------------------------------------------------------------------
titulo("4. SESGO DE MEDICION: urgencias sin hospitalizar (quien tiene duracion y quien no)")
u = seg[seg.segmento == "urgencias_sin_hospitalizar"].copy()
print(f"episodios con TU y sin HOSP: {len(u)} | con duracion medida: {int(u.medido.sum())} "
      f"({100 * u.medido.mean():.1f} %)")
u["carga"] = pd.qcut(u.llegadas_6h_previas, 3, labels=["baja", "media", "alta"], duplicates="drop")
u["fin_de_semana"] = u.fin_de_semana.map({True: "fin de semana", False: "entre semana"})
filas = []
for var in ["grupo_edad", "sexo", "tipo_visita", "anio", "franja", "fin_de_semana", "carga"]:
    t = u.groupby(var, observed=True).medido.agg(["size", "mean"])
    for nivel, r in t.iterrows():
        filas.append({"variable": var, "nivel": str(nivel), "n": int(r["size"]),
                      "pct_medido": round(100 * r["mean"], 1)})
sesgo = pd.DataFrame(filas)
rango = (sesgo.groupby("variable").pct_medido.agg(lambda s: s.max() - s.min())
         .round(1).sort_values(ascending=False).rename("rango_puntos"))
print(sesgo.to_string(index=False))
print("\nRango (maximo - minimo) del % medido entre niveles de cada variable. Mientras mas alto,")
print("mas se relaciona esa variable con quien tiene duracion medida:")
print(rango.to_string())
sesgo.to_csv(TABLAS / f"sesgo_medicion_urgencias{SUFIJO}.csv", index=False)

# ----------------------------------------------------------------------
# 5) Urgencias antes de la cama por anio (hospitalizados: medido al 100 %)
# ----------------------------------------------------------------------
titulo("5. URGENCIAS ANTES DE LA CAMA POR ANIO (la cola de TU: real o de registro?)")
filas = []
for nombre in ["urgencias_antes_cama", "espera_cama"]:
    d = seg[(seg.segmento == nombre) & seg.en_estadisticas]
    for anio, g in d.groupby("anio"):
        filas.append({"segmento": nombre, "anio": int(anio), "n": len(g),
                      "p50": round(g.horas.median(), 1), "p75": round(g.horas.quantile(.75), 1),
                      "p90": round(g.horas.quantile(.90), 1)})
por_anio = pd.DataFrame(filas)
print(por_anio.to_string(index=False))
por_anio.to_csv(TABLAS / f"urgencias_antes_cama_por_anio{SUFIJO}.csv", index=False)
print("\nLectura: si p75 y p90 suben de 2023 a 2026 en hospitalizados (100 % medidos), el empeoramiento es real.")
print("Si se quedan planos, la cola creciente de TU en Q2 es un efecto de que se registran mas salidas.")
print("(2026 es medio anio.)")
