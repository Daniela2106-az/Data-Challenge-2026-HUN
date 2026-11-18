"""
diagnostico_cuello_botella.py  -  version 1 (3-nov-2026)
Tarea A7: sistema repetible de diagnostico de cuellos de botella (idea de Anthony, 23-oct).

QUE HACE
  Recibe un PERIODO (llegadas entre --desde y --hasta) y devuelve un reporte que contesta, en el mismo orden de siempre:
    1. DONDE esta el cuello de botella: de los dos componentes de la espera de cama (urgencias antes de la cama y hueco sin etapa),
       cual acumula mas horas por encima de la referencia de "cuando funciona bien" (referencia FIJA, calculada con el periodo de
       referencia, para poder comparar periodos distintos con la misma vara).
    2. QUE SE DISPARA: que parte de las horas en exceso vienen de las esperas muy largas, cuanto se llenan las camas (frente a 106),
       cuanto se parece la ocupacion a "ingresos por dia x estancia media" (ley de Little) y como van las altas por la tarde.
    3. QUE REGISTROS SE DISPARAN: las estancias con espera mayor al percentil 90 de la referencia (y las de mas de 14 dias).
    4. QUE COMPARTEN: quien son (edad, tipo de visita, franja de llegada, grupo de diagnostico, sexo) frente al resto, con la razon
       entre ambos y el n de cada grupo (se ocultan grupos con menos de 30 casos).
    5. QUE HACER: frases condicionadas por las cifras del periodo y ligadas a docs/recomendaciones.md. Si una cifra no
       cambia lo que dice la regla, la frase no sale.
  Tambien dice si el cuello de botella CAMBIO frente al periodo de referencia.

QUE NO HACE
  - No usa datos en tiempo real: se corre sobre el periodo que se le pase (reproducir un periodo).
  - No incluye la simulacion Monte Carlo de camas (A5, Anthony): el paso 2 usa la ocupacion observada, la ley de Little y el escenario
    de altas de simulacion_altas.py. Cuando exista A5, agregarla ahi.
  - No prueba causas: todo son asociaciones (la limitacion va al lado de cada frase).

USO
  python3 src/diagnostico_cuello_botella.py                          # periodo confiable completo (2023-02-01 a 2026-04-09)
  python3 src/diagnostico_cuello_botella.py --desde 2025-01-01 --hasta 2025-12-31
  python3 src/diagnostico_cuello_botella.py --desde 2024-07-01 --hasta 2024-12-31 --ref-desde 2023-02-01 --ref-hasta 2023-12-31

ENTRADA  datos/procesados/tabla_episodios.parquet (src/preparar_variables.py)
SALIDA   resultados/tablas/cuello_botella_<desde>_<hasta>.csv (indicadores), resultados/tablas/cuello_botella_<desde>_<hasta>_perfil.csv
         resultados/tablas/cuello_botella_<desde>_<hasta>.md (el reporte en texto)
         No lleva datos de pacientes, solo agregados.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
TABLAS.mkdir(parents=True, exist_ok=True)

FIN_CONFIABLE = pd.Timestamp("2026-04-09")     # el registro de etapas se degrada desde el 10-abr-2026 (docs/CONTEXTO_TECNICO.md 4.9)
INICIO_CONFIABLE = pd.Timestamp("2023-02-01")
CAMAS_HUN = 106                                 # dato del HUN, 29-oct-2026 (sin fecha ni desglose)
MIN_N = 30                                      # grupos con menos casos no se interpretan
P_CARGA_BAJA = 0.20                             # referencia: mediana cuando las llegadas de las 6 h previas estan en el 20 % mas bajo
FACTORES = ["grupo_edad", "tipo_visita", "franja", "sexo", "categoria_dx"]

ap = argparse.ArgumentParser(description="Diagnostico repetible de cuellos de botella sobre un periodo")
ap.add_argument("--desde", default=str(INICIO_CONFIABLE.date()))
ap.add_argument("--hasta", default=str(FIN_CONFIABLE.date()))
ap.add_argument("--ref-desde", default=str(INICIO_CONFIABLE.date()), help="inicio del periodo de referencia (fija la vara de 'cuando funciona bien')")
ap.add_argument("--ref-hasta", default=str(FIN_CONFIABLE.date()), help="fin del periodo de referencia")
args = ap.parse_args()
D, H = pd.Timestamp(args.desde), pd.Timestamp(args.hasta) + pd.Timedelta(days=1)
RD, RH = pd.Timestamp(args.ref_desde), pd.Timestamp(args.ref_hasta) + pd.Timedelta(days=1)
ETIQ = f"{args.desde}_{args.hasta}"
LINEAS = []                                      # el reporte en texto


def md(df):
    """Tabla en markdown sin depender de la libreria tabulate."""
    cab = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns)
    return cab + "\n" + "\n".join("| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False))


def dice(t=""):
    print(t)
    LINEAS.append(t)


# ---------------------------------------------------------------- datos
t = pd.read_parquet(PROC / "tabla_episodios.parquet")
est = t[t.estancia_unica & t.hospitalizado & t.espera_cama_h.notna()].copy()
est["hueco_h"] = est.hueco_antes_hosp_h.fillna(0).clip(lower=0)
est["urg_h"] = (est.espera_cama_h - est.hueco_h).clip(lower=0)
est["estancia_h"] = (est.fin_hosp_est - est.ini_hosp_est).dt.total_seconds() / 3600

ventana = est[(est.ini >= D) & (est.ini < H)]
refer = est[(est.ini >= RD) & (est.ini < RH)]
if len(ventana) < 200:
    raise SystemExit(f"Solo {len(ventana)} estancias en el periodo: demasiado poco para un diagnostico.")

dice(f"# Diagnostico de cuello de botella · llegadas del {args.desde} al {args.hasta}")
dice(f"Referencia ('cuando funciona bien'): llegadas del {args.ref_desde} al {args.ref_hasta}. "
     f"Estancias en el periodo: {len(ventana)} (en la referencia: {len(refer)}). Una fila por estancia unica.")
avisos = []
if H > FIN_CONFIABLE + pd.Timedelta(days=1):
    avisos.append("El periodo incluye dias posteriores al 9-abr-2026: el registro de etapas esta degradado (docs/CONTEXTO_TECNICO.md 4.9). "
                  "Las esperas y las horas de esos dias no son confiables.")
if D < INICIO_CONFIABLE:
    avisos.append("El periodo empieza antes de feb-2023: los primeros meses no ven los episodios anteriores.")
for a in avisos:
    dice(f"> **AVISO:** {a}")
dice()

# ---------------------------------------------------------------- referencia fija por estrato (nino/adulto), como ranking_cuellos.py
def estrato(df):
    return np.where(df.edad.fillna(99) < 15, "nino", "adulto")


refer = refer.assign(estrato=estrato(refer))
ventana = ventana.assign(estrato=estrato(ventana))
corte = refer.llegadas_6h_previas.quantile(P_CARGA_BAJA)
baja = refer[refer.llegadas_6h_previas <= corte]
REF = {}
for comp in ["urg_h", "hueco_h", "espera_cama_h"]:
    glob = baja[comp].median()
    REF[comp] = {e: (baja[baja.estrato == e][comp].median() if (baja.estrato == e).sum() >= MIN_N else glob) for e in ["nino", "adulto"]}


def exceso(df, comp):
    r = df.estrato.map(REF[comp])
    return (df[comp] - r).clip(lower=0)


# ---------------------------------------------------------------- 1. donde esta el cuello de botella
dice("## 1. Dónde está el cuello de botella")
filas = []
for nombre, df in [("periodo", ventana), ("referencia", refer.assign(estrato=refer.estrato))]:
    for comp, etiq in [("urg_h", "Urgencias antes de la cama"), ("hueco_h", "Hueco sin etapa antes de la cama"), ("espera_cama_h", "Espera de cama (total)")]:
        ex = exceso(df, comp)
        filas.append(dict(periodo=nombre, segmento=etiq, n=len(df), mediana_h=round(df[comp].median(), 1), p90_h=round(df[comp].quantile(.9), 1),
                          horas_totales=round(df[comp].sum()), exceso_horas=round(ex.sum()), exceso_medio_h=round(ex.mean(), 1),
                          pct_sobre_referencia=round(100 * ex.sum() / max(df[comp].sum(), 1), 1)))
ind = pd.DataFrame(filas)
tabla1 = ind[ind.periodo == "periodo"].drop(columns="periodo")
dice(md(tabla1))
comp = tabla1[tabla1.segmento.isin(["Urgencias antes de la cama", "Hueco sin etapa antes de la cama"])].sort_values("exceso_horas", ascending=False)
cuello = comp.iloc[0].segmento
ref_comp = ind[(ind.periodo == "referencia") & ind.segmento.isin(["Urgencias antes de la cama", "Hueco sin etapa antes de la cama"])].sort_values("exceso_horas", ascending=False)
cuello_ref = ref_comp.iloc[0].segmento
dice(f"\n**Cuello de botella del periodo: {cuello}** ({100 * comp.iloc[0].exceso_horas / max(comp.exceso_horas.sum(), 1):.0f} % del exceso de los dos componentes).")
dice("*Los excesos se miden contra la mediana de cuando las llegadas de las 6 horas previas estaban en el 20 % más bajo, por niños y adultos; la referencia es una elección, no una verdad.*")
exp = tabla1[tabla1.segmento == "Espera de cama (total)"].iloc[0]
exp_ref = ind[(ind.periodo == "referencia") & (ind.segmento == "Espera de cama (total)")].iloc[0]
if (args.desde, args.hasta) == (args.ref_desde, args.ref_hasta):
    dice("El periodo y la referencia coinciden: no hay comparación de cambio.")
elif cuello == cuello_ref:
    dice(f"Frente a la referencia **el cuello de botella no cambió**; el exceso medio por estancia pasó de {exp_ref.exceso_medio_h} a {exp.exceso_medio_h} h.")
else:
    dice(f"**El cuello de botella cambió:** en la referencia era '{cuello_ref}' y ahora es '{cuello}'.")
dice()

# ---------------------------------------------------------------- 2. que se dispara
dice("## 2. Qué se dispara")
ex_total = exceso(ventana, "espera_cama_h")
disp = {}
for lim in [24, 48, 72]:
    disp[lim] = (100 * (ventana.espera_cama_h > lim).mean(), 100 * ex_total[ventana.espera_cama_h > lim].sum() / max(ex_total.sum(), 1))
dice("| Espera mayor a | % de los pacientes | % de las horas en exceso |\n|---|---|---|")
for lim, (p, e) in disp.items():
    dice(f"| {lim} h | {p:.1f} % | {e:.1f} % |")
cola = disp[48][1]
dice(f"\nLas esperas de más de 48 h son el {disp[48][0]:.0f} % de los pacientes y concentran el {cola:.0f} % de las horas en exceso: "
     + ("el problema está en la **cola larga**, no en la espera típica." if cola >= 50 else "la espera típica también pesa."))

# ocupacion de camas con estancias unicas del periodo (intervalo completo de la estancia)
ocup_est = t[t.estancia_unica & t.hospitalizado & t.ini_hosp_est.notna()]
ini_h, fin_h = ocup_est.ini_hosp_est.values.astype("datetime64[ns]"), ocup_est.fin_hosp_est.fillna(pd.Timestamp("2100-01-01")).values.astype("datetime64[ns]")
a, b = np.sort(ini_h), np.sort(fin_h)
fin_oc = min(H, FIN_CONFIABLE + pd.Timedelta(days=1))
horas = pd.date_range(D.floor("h"), fin_oc, freq="h", inclusive="left").values.astype("datetime64[ns]")
oc = np.searchsorted(a, horas, side="left") - np.searchsorted(b, horas, side="right")
pct_sobre = 100 * (oc > CAMAS_HUN).mean()
dias = max((min(H, fin_oc) - D).days, 1)
ing_dia = len(ocup_est[(ocup_est.ini_hosp_est >= D) & (ocup_est.ini_hosp_est < H)]) / dias
cerradas = ocup_est[(ocup_est.ini_hosp_est >= D) & (ocup_est.ini_hosp_est < H) & ocup_est.fin_hosp_est.notna()]
est_media_d = (cerradas.fin_hosp_est - cerradas.ini_hosp_est).dt.total_seconds().mean() / 86400
dice(f"\n**Camas ocupadas:** media {oc.mean():.0f}, máximo {oc.max()}; el {pct_sobre:.1f} % de las horas supera las {CAMAS_HUN} camas que dio el HUN "
     f"(la lista no trae fecha ni desglose). Ingresos a cama por día {ing_dia:.1f}; estancia media {est_media_d:.2f} días; Little: {ing_dia * est_media_d:.0f} camas.")
dice("*La ocupación se calcula sobre los registros de la base (puede ser sobreocupación con camas adicionales o una capacidad real mayor; los datos no lo distinguen).*")

# altas por la tarde
altas = ocup_est[(ocup_est.fin_hosp_est >= D) & (ocup_est.fin_hosp_est < H) & ocup_est.fin_hosp_est.notna()]
if len(altas) >= 100:
    h_alta = altas.fin_hosp_est.dt.hour
    tarde, manana = 100 * h_alta.between(14, 18).mean(), 100 * (h_alta < 12).mean()
    dice(f"**Altas:** el {tarde:.1f} % ocurre entre las 14:00 y las 18:59 y el {manana:.1f} % antes del mediodía.")
else:
    tarde = manana = np.nan
dice()

# ---------------------------------------------------------------- 3. registros que se disparan
dice("## 3. Qué registros se disparan")
p90_ref = refer.espera_cama_h.quantile(.9)
ventana = ventana.assign(se_dispara=ventana.espera_cama_h > p90_ref, larga=ventana.estancia_h > 14 * 24)
dice(f"Se llama 'disparada' a una estancia con espera mayor al percentil 90 de la referencia (**{p90_ref:.1f} h**): "
     f"**{int(ventana.se_dispara.sum())} de {len(ventana)}** ({100 * ventana.se_dispara.mean():.1f} %; en la referencia serían 10 %). "
     f"Estancias de más de 14 días: {int(ventana.larga.sum())} ({100 * ventana.larga.mean():.1f} %).")
dice()

# ---------------------------------------------------------------- 4. que comparten
dice("## 4. Qué comparten (frente al resto)")
dice("*Razón = % de las disparadas en ese grupo / % del resto en ese grupo. Solo grupos con al menos 30 estancias disparadas.*\n")
filas = []
n_d, n_o = ventana.se_dispara.sum(), (~ventana.se_dispara).sum()
for f in FACTORES:
    if f not in ventana or ventana[f].notna().sum() < 200:
        continue
    g = ventana[ventana[f].notna()].groupby(f).agg(disparadas=("se_dispara", "sum"), total=("se_dispara", "size"))
    g["otras"] = g.total - g.disparadas
    g["pct_disparadas"], g["pct_otras"] = 100 * g.disparadas / n_d, 100 * g.otras / n_o
    g["razon"] = (g.pct_disparadas / g.pct_otras.replace(0, np.nan)).round(2)
    g["pct_del_grupo_que_se_dispara"] = (100 * g.disparadas / g.total).round(1)
    g = g[g.disparadas >= MIN_N].reset_index().rename(columns={f: "nivel"})
    g.insert(0, "factor", f)
    filas.append(g)
perfil = pd.concat(filas).sort_values("razon", ascending=False) if filas else pd.DataFrame()
if len(perfil):
    top = perfil.head(8)[["factor", "nivel", "disparadas", "pct_del_grupo_que_se_dispara", "razon"]]
    dice(md(top))
    perfil.round(2).to_csv(TABLAS / f"cuello_botella_{ETIQ}_perfil.csv", index=False)
    dice("\n*Asociación, no causa. El diagnóstico se registra tarde, falta en una parte de los hospitalizados y puede ser de la otra persona del par duplicado.*")
dice()

# ---------------------------------------------------------------- 5. que hacer (reglas con cifras)
dice("## 5. Qué hacer (reglas condicionadas por las cifras del periodo; detalle en `docs/recomendaciones.md`)")
acciones = []
if cuello == "Urgencias antes de la cama":
    acciones.append("El tiempo se pierde **dentro de urgencias antes de que se asigne la cama**: priorizar el proceso de asignación de cama y el aviso temprano de pacientes que van a hospitalizarse (alerta C: paciente sin cama a las 48 h).")
else:
    acciones.append("El mayor exceso es el **hueco sin etapa registrada** antes de la cama: antes de actuar, aclarar con el HUN dónde está el paciente en ese tiempo y si se registra la asignación de cama (pregunta 5 de `docs/hun/sesion_de_preguntas.md`).")
if not np.isnan(tarde) and tarde >= 50 and manana <= 20:
    acciones.append(f"Las altas se concentran por la tarde ({tarde:.0f} % entre las 14 y las 19 h): probar **adelantar altas** (el escenario de `simulacion_altas.py` da una cota; no resuelve esperas de varios días).")
if cola >= 50:
    acciones.append("La mayor parte del exceso está en esperas de más de 48 h: **revisar pacientes con espera mayor a 48 h** uno por uno (la causa individual no está en la base).")
if pct_sobre >= 10:
    acciones.append(f"La ocupación supera las {CAMAS_HUN} camas el {pct_sobre:.0f} % de las horas: **planear camas con el pronóstico semanal** y revisar las estancias de más de 14 días (planificación de alta o traslado).")
if len(perfil):
    r = perfil[(perfil.factor == "tipo_visita") & (perfil.razon >= 1.5)]
    if len(r):
        acciones.append(f"Las visitas de tipo '{r.iloc[0].nivel}' están sobrerrepresentadas entre las esperas largas (razón {r.iloc[0].razon}): mirar ese flujo aparte.")
if not acciones:
    acciones.append("Ninguna regla se activó con las cifras de este periodo.")
for x in acciones:
    dice(f"- {x}")
dice("\n*Todo lo anterior son asociaciones y escenarios sobre datos históricos, no pruebas de causa. La causa de una espera individual (servicio, tipo de cama, gravedad) no está en la base.*")

# ---------------------------------------------------------------- salidas
ind.to_csv(TABLAS / f"cuello_botella_{ETIQ}.csv", index=False)
(TABLAS / f"cuello_botella_{ETIQ}.md").write_text("\n".join(LINEAS), encoding="utf-8")
print(f"\nguardado: resultados/tablas/cuello_botella_{ETIQ}.csv, _perfil.csv y .md")
