"""
exportar_para_powerbi.py  -  version 1 (23-oct-2026)
Arma el PAQUETE DE DATOS para el dashboard de Power BI (powerbi/roadmap_powerbi.md) en datos/procesados/powerbi/ y su zip
datos/procesados/powerbi.zip, para pasarlo por el drive privado del equipo. Esa carpeta NO se sube a git.

QUE HACE
  1. Crea tablas nuevas pensadas para Power BI:
       bi_estancias.csv            una estancia en cama por fila, SIN ids ni fechas exactas (solo anio y mes)
       bi_llegadas.csv             llegadas agregadas por anio, dia de la semana, hora, tipo de visita y edad (sin mes)
       bi_calendario.csv           una fecha por fila con festivos, semana santa, Carnaval y fin de anio
       bi_escenario_altas.csv      rejilla de 0 a 100 % (cada 5 puntos) para el deslizador de altas adelantadas
       bi_escenario_camas_hora.csv camas libres adicionales por hora si se adelanta el 100 % de las altas de la tarde
       dim_hora, dim_dia_semana, dim_edad, dim_tipo_visita   dimensiones pequenas para ordenar y filtrar
  2. Copia las tablas ya calculadas (panel diario, serie horaria y los resultados de resultados/tablas/) con los
     nombres de columna LIMPIOS (sin %, parentesis ni espacios: "WAPE_%" pasa a "wape_pct").
  3. Calcula las CIFRAS DE CONTROL (cifras_de_control.csv) que el dashboard debe reproducir y avisa si alguna se sale
     de lo esperado.
  4. Escribe LEEME.txt con la lista de archivos, filas y columnas.

ENTRADAS  datos/procesados/para_equipo/estancias_hospitalizacion.csv, panel_diario.csv, datos/procesados/espera_cama.csv,
          tabla_episodios.parquet, serie_horaria.csv y las tablas de resultados/tablas/ (correr antes todos los scripts de src/)
SALIDAS   datos/procesados/powerbi/*.csv, LEEME.txt, cifras_de_control.csv ; datos/procesados/powerbi.zip

PRIVACIDAD
  bi_estancias.csv no trae ids ni fechas exactas, pero sigue siendo una fila por estancia: usarla solo si los organizadores
  autorizan datos por fila (docs/hun/sesion_de_preguntas.md, D2 y D3). Para publicar solo agregados, quitarla y usar las
  tablas de resultados.
"""
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
SALIDA = PROC / "powerbi"
SALIDA.mkdir(parents=True, exist_ok=True)
for f in SALIDA.glob("*"):
    f.unlink()                                   # el paquete se arma desde cero cada vez
K = ["visit_occurrence_id", "episodio"]
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
EDADES = ["0-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+", "sin dato"]   # "sin dato": 21 episodios con edad imposible
TIPOS = ["Urgencias", "Treatment urgency", "Ambulatorio", "Inpatient"]
CAIDA_DESDE = pd.Timestamp("2026-05-01")
FECHA_INI, FECHA_FIN = "2023-01-01", "2026-07-31"


def limpiar(nombre):
    n = nombre.strip().lower().replace("%", "pct").replace("/", "_sobre_")
    n = re.sub(r"[()]", "", n)
    n = re.sub(r"[^a-z0-9_]+", "_", n)
    return n.strip("_")


def franja(h):
    return pd.cut(h, [-1, 5, 11, 17, 23], labels=["madrugada 0-5", "manana 6-11", "tarde 12-17", "noche 18-23"]).astype(str)


def guardar(df, nombre, descripcion):
    df = df.copy()
    df.columns = [limpiar(c) for c in df.columns]
    df.to_csv(SALIDA / nombre, index=False)
    CATALOGO.append((nombre, len(df), ", ".join(df.columns), descripcion))


CATALOGO = []

# ----------------------------------------------------------------------
# 1) Tablas nuevas
# ----------------------------------------------------------------------
est = pd.read_csv(PROC / "para_equipo" / "estancias_hospitalizacion.csv", parse_dates=["ingreso_cama", "alta", "llegada"])
esp = pd.read_csv(PROC / "espera_cama.csv")[K + ["hueco_antes_hosp_h"]]
est = est.merge(esp, on=K, how="left")

b = pd.DataFrame({
    "anio": est.llegada.dt.year,
    "mes": est.llegada.dt.month,
    "anio_mes": est.llegada.dt.strftime("%Y-%m"),
    "dia_semana_num": est.llegada.dt.dayofweek,
    "dia_semana": est.llegada.dt.dayofweek.map(dict(enumerate(DIAS))),
    "hora_llegada": est.llegada.dt.hour,
    "franja": franja(est.llegada.dt.hour),
    "grupo_edad": est.grupo_edad.astype(str).fillna("sin dato").replace("nan", "sin dato"),
    "sexo": est.sexo.fillna("sin dato"),
    "tipo_visita": est.tipo_visita,
    "espera_h": est.espera_cama_h,
    "hueco_h": est.hueco_antes_hosp_h,
})
b["urgencias_antes_h"] = (b.espera_h - b.hueco_h).clip(lower=0)
b["estancia_h"] = ((est.alta - est.ingreso_cama).dt.total_seconds() / 3600).where(est.alta_completa)
b["hora_ingreso_cama"] = est.ingreso_cama.dt.hour
b["hora_alta"] = est.alta.dt.hour.where(est.alta_completa)
b["espera_mas_24h"] = np.where(b.espera_h.notna(), (b.espera_h > 24).astype(int), np.nan)
b["espera_mas_48h"] = np.where(b.espera_h.notna(), (b.espera_h > 48).astype(int), np.nan)
b["sin_espera_medida"] = b.espera_h.isna().astype(int)         # hospitalizacion directa u otros sin etapa previa
b["periodo_caida_de_datos"] = (est.llegada >= CAIDA_DESDE).astype(int)   # desde mayo 2026: posible carga incompleta
b = b.sample(frac=1, random_state=7).reset_index(drop=True)    # se mezcla el orden: no sigue el orden de llegada
guardar(b.round(3), "bi_estancias.csv", "Una estancia en cama por fila, sin ids ni fechas exactas (sensible: ver PRIVACIDAD)")

ep = pd.read_parquet(PROC / "tabla_episodios.parquet", columns=["anio", "dia_semana_num", "hora", "tipo_visita", "grupo_edad",
                                                                "ruta_simple", "hospitalizado", "estancia_unica"])
ep["llegadas_con_atencion"] = (ep.ruta_simple != "ER").astype(int)
ep["hospitalizados_unicos"] = (ep.hospitalizado & ep.estancia_unica).astype(int)
ll = (ep.assign(llegadas=1, grupo_edad=ep.grupo_edad.astype(str).fillna("sin dato").replace("nan", "sin dato"))
        .groupby(["anio", "dia_semana_num", "hora", "tipo_visita", "grupo_edad"], observed=True)
        [["llegadas", "llegadas_con_atencion", "hospitalizados_unicos"]].sum().reset_index())
ll["dia_semana"] = ll.dia_semana_num.map(dict(enumerate(DIAS)))
guardar(ll[["anio", "dia_semana_num", "dia_semana", "hora", "tipo_visita", "grupo_edad", "llegadas", "llegadas_con_atencion",
            "hospitalizados_unicos"]], "bi_llegadas.csv", "Llegadas (episodios) agregadas por anio, dia, hora, tipo de visita y edad")

# calendario con festivos, semana santa, carnaval y fin de anio
fechas = pd.date_range(FECHA_INI, FECHA_FIN)
cal = pd.DataFrame({"fecha": fechas})
cal["anio"], cal["mes"] = cal.fecha.dt.year, cal.fecha.dt.month
cal["nombre_mes"] = cal.mes.map(dict(enumerate(MESES, 1)))
cal["anio_mes"] = cal.fecha.dt.strftime("%Y-%m")
cal["dia_semana_num"] = cal.fecha.dt.dayofweek
cal["dia_semana"] = cal.dia_semana_num.map(dict(enumerate(DIAS)))
cal["es_fin_de_semana"] = (cal.dia_semana_num >= 5).astype(int)
try:
    import holidays
    fest = holidays.Colombia(years=range(2023, 2027))
    cal["festivo"] = [int(f.date() in fest) for f in cal.fecha]
except ImportError:
    panel_ = pd.read_csv(PROC / "para_equipo" / "panel_diario.csv", parse_dates=["fecha"]).set_index("fecha")
    cal["festivo"] = cal.fecha.map(panel_.festivo.astype(int)).fillna(0).astype(int)
cal["semana_santa"] = 0
cal["carnaval"] = 0
for a in range(2023, 2027):
    e = pd.Timestamp(easter(a))
    cal.loc[(cal.fecha >= e - pd.Timedelta(days=7)) & (cal.fecha <= e), "semana_santa"] = 1
    cal.loc[(cal.fecha >= e - pd.Timedelta(days=50)) & (cal.fecha <= e - pd.Timedelta(days=47)), "carnaval"] = 1
cal["fin_anio_24_31_dic"] = (((cal.mes == 12) & cal.fecha.dt.day.isin([24, 31]))).astype(int)
cal["fin_anio_25_dic_1_ene"] = ((((cal.mes == 12) & (cal.fecha.dt.day == 25)) | ((cal.mes == 1) & (cal.fecha.dt.day == 1)))).astype(int)
cal["periodo_caida_de_datos"] = (cal.fecha >= CAIDA_DESDE).astype(int)
guardar(cal, "bi_calendario.csv", "Una fecha por fila (2023-01-01 a 2026-07-31) con festivos, semana santa, Carnaval y fin de anio")

# escenarios: el efecto de adelantar altas es LINEAL en el valor esperado (cada alta se mueve con probabilidad p)
ea = pd.read_csv(TABLAS / "escenario_altas_antes.csv")
cien = ea[ea.proporcion_movida == 1.0].iloc[0]
rej = pd.DataFrame({"proporcion_pct": np.arange(0, 101, 5)})
p = rej.proporcion_pct / 100
rej["altas_movidas_por_dia"] = p * cien.altas_movidas_por_dia
rej["horas_cama_liberadas_por_dia"] = p * cien.horas_cama_liberadas_por_dia
rej["cota_pct_del_exceso"] = p * cien.cota_superior_pct_del_exceso
rej["estimacion_pct_del_exceso"] = p * cien.estimacion_pct_del_exceso
rej["estimacion_pct_de_la_espera"] = p * cien.estimacion_pct_de_la_espera
guardar(rej.round(2), "bi_escenario_altas.csv", "Rejilla 0-100 % de altas adelantadas (lineal en el valor esperado; coincide con escenario_altas_antes.csv)")
ch = pd.read_csv(TABLAS / "escenario_camas_por_hora.csv")
ch["camas_libres_100pct"] = (ch.camas_libres_adicionales / 0.30).round(3)
guardar(ch[["hora", "ocupacion_base", "camas_libres_100pct"]], "bi_escenario_camas_hora.csv",
        "Por hora: ocupacion base y camas libres adicionales si se adelanta el 100 % de las altas (multiplicar por la proporcion elegida)")

# dimensiones
guardar(pd.DataFrame({"hora": range(24), "etiqueta": [f"{h:02d}:00" for h in range(24)], "franja": franja(pd.Series(range(24)))})
        .assign(orden_franja=lambda d: d.franja.map({"madrugada 0-5": 1, "manana 6-11": 2, "tarde 12-17": 3, "noche 18-23": 4})),
        "dim_hora.csv", "Hora del dia, franja y su orden")
guardar(pd.DataFrame({"dia_semana_num": range(7), "dia_semana": DIAS, "tipo_dia": ["entre semana"] * 5 + ["fin de semana"] * 2}),
        "dim_dia_semana.csv", "Dia de la semana (0 = lunes) y tipo de dia")
guardar(pd.DataFrame({"grupo_edad": EDADES, "orden": range(1, 9)}), "dim_edad.csv", "Grupos de edad y su orden")
guardar(pd.DataFrame({"tipo_visita": TIPOS, "orden": range(1, 5)}), "dim_tipo_visita.csv", "Tipos de visita y su orden")

# ----------------------------------------------------------------------
# 2) Tablas ya calculadas, con nombres de columna limpios
# ----------------------------------------------------------------------
COPIAS = {
    ("para_equipo", "panel_diario.csv"): "Un dia por fila: llegadas, ingresos a cama, altas, ocupacion, espera, festivo",
    ("", "serie_horaria.csv"): "Una hora por fila: llegadas y ocupacion (usar ocupacion_confiable)",
    ("", "serie_diaria.csv"): "Una fecha por fila con llegadas y ocupacion (version completa hasta julio 2026)",
}
for (sub, nombre), desc in COPIAS.items():
    df = pd.read_csv(PROC / sub / nombre) if sub else pd.read_csv(PROC / nombre)
    guardar(df, nombre, desc)
RESULTADOS = {
    "ranking_cuellos": "Exceso de espera por segmento y referencia (impacto en horas-paciente)",
    "exceso_por_anio": "Exceso de espera y mediana por anio, segmento y referencia",
    "exceso_por_franja": "Exceso de espera por franja horaria de llegada",
    "inventario_segmentos": "Inventario de segmentos: n, % medido y percentiles",
    "descomposicion_espera": "Cuanto de la espera de cama es urgencias y cuanto es hueco",
    "urgencias_antes_cama_por_anio": "Percentiles de urgencias antes de la cama y de la espera por anio",
    "carga_por_decil": "Espera por decil de carga (llegadas y ocupacion)",
    "carga_efectos": "Efecto de la carga sobre la espera con y sin controles",
    "hora_efectos": "Efecto de la franja de llegada sobre la espera",
    "hora_llegada": "Espera mediana y p90 por hora de llegada",
    "asignacion_cama_por_hora_llegada": "Por hora de llegada: % que recibe cama el mismo dia o despues y hora de asignacion",
    "altas_ingresos_llegadas_por_hora": "% de altas, ingresos a cama y llegadas por hora del dia",
    "acople_altas_ingresos": "Ingresos a cama que siguen a una alta extra",
    "importancia_factores": "Cuanto explica cada grupo de factores de la espera (R2)",
    "coeficientes_espera_cama": "Efecto de cada nivel de los factores sobre la espera (%)",
    "sesgo_medicion_urgencias": "Quien tiene duracion medida en urgencias sin hospitalizar",
    "ocupacion_por_anio": "Ingresos por dia, estancia media y camas ocupadas por anio",
    "escenarios_little": "Camas ocupadas segun ingresos y estancia (ley de Little)",
    "escenario_altas_antes": "Escenario de altas adelantadas (5 puntos de la simulacion)",
    "tendencia_mensual": "Llegadas e ingresos por dia, promedio mensual",
    "pronostico_diario_test": "Real, pronostico y banda del 80 % por dia (ene-mayo 2026)",
    "pronostico_metricas": "Error de cada metodo de pronostico en la prueba",
    "pronostico_semanal_metricas": "Error del pronostico semanal",
    "pronostico_horario_metricas": "Error del pronostico por hora",
    "alertas_congestion": "Alerta de dia congestionado segun la hora de aviso",
    "alertas_camas": "Alerta de ocupacion alta a 24 h",
    "alertas_camas_dias": "Por dia: ocupacion ahora, proyeccion y ocupacion real a 24 h",
    "alertas_paciente": "Alerta por paciente segun las horas sin cama",
    "alertas_carga_diaria": "Alertas por dia del diseno recomendado",
    "dias_atipicos": "Dias atipicos con real, esperado, z y causa de calendario",
    "dias_atipicos_resumen": "Resumen de dias atipicos por variable",
    "cobertura_por_ruta": "Rutas de los episodios y % con duracion medida",
    "resumen_por_ruta": "Tiempos por ruta (percentiles) de los episodios medidos",
}
for n, desc in RESULTADOS.items():
    guardar(pd.read_csv(TABLAS / f"{n}.csv"), f"{n}.csv", desc)

# ----------------------------------------------------------------------
# 3) Cifras de control
# ----------------------------------------------------------------------
panel = pd.read_csv(PROC / "para_equipo" / "panel_diario.csv")
oa = pd.read_csv(TABLAS / "ocupacion_por_anio.csv").set_index("anio")
e = b.espera_h.dropna()
e_est = b[(b.periodo_caida_de_datos == 0)].espera_h.dropna()
altas = b.hora_alta.dropna()
cifras = [
    ("estancias_con_espera_medida", len(e), 27162, 0),
    ("estancias_totales", len(b), 27956, 0),
    ("espera_mediana_h", round(e.median(), 1), 18.0, 0.15),
    ("espera_p75_h", round(e.quantile(.75), 1), 37.2, 0.3),
    ("espera_p90_h", round(e.quantile(.9), 1), 71.5, 0.3),
    ("pct_espera_mas_24h", round(100 * (e > 24).mean(), 1), 42.8, 0.3),
    ("pct_espera_mas_48h", round(100 * (e > 48).mean(), 1), 19.4, 0.5),
    ("espera_mediana_h_sin_periodo_caida", round(e_est.median(), 1), 17.8, 0.15),
    ("espera_p90_h_sin_periodo_caida", round(e_est.quantile(.9), 1), 70.6, 0.3),
    ("pct_urgencias_de_las_horas_de_espera", round(100 * b.dropna(subset=["espera_h"]).urgencias_antes_h.sum() / e.sum(), 1), 76.6, 0.5),   # pipeline; el calculo con Q3 da 77,2
    ("ingresos_por_dia_panel", round(panel.ingresos_a_cama.mean(), 1), 21.8, 0.2),
    ("ocupacion_media_panel", round(panel.ocup_hosp_media.mean(), 1), 112.5, 0.5),
    ("pct_altas_14_a_18_59", round(100 * altas.between(14, 18).mean(), 1), 61.5, 0.5),
    ("pct_altas_antes_del_mediodia", round(100 * (altas < 12).mean(), 1), 15.0, 0.5),
    ("camas_ocupadas_2023", oa.loc[2023, "ocupacion_media"], 104.8, 0.2),
    ("camas_ocupadas_2025", oa.loc[2025, "ocupacion_media"], 118.6, 0.2),
    ("estancia_media_dias_2023", oa.loc[2023, "estancia_media_dias"], 4.70, 0.02),
    ("estancia_media_dias_2025", oa.loc[2025, "estancia_media_dias"], 5.46, 0.02),
    ("llegadas_por_dia_panel", round(panel.llegadas.mean(), 1), 263.6, 0.5),
    ("llegadas_total_bi_llegadas", int(ll.llegadas.sum()), 337194, 0),
]
cc = pd.DataFrame(cifras, columns=["cifra", "valor", "esperado", "tolerancia"])
cc["ok"] = [("" if pd.isna(r.esperado) else bool(abs(r.valor - r.esperado) <= r.tolerancia)) for r in cc.itertuples()]
cc.to_csv(SALIDA / "cifras_de_control.csv", index=False)
CATALOGO.append(("cifras_de_control.csv", len(cc), "cifra, valor, esperado, tolerancia, ok", "Cifras que el dashboard debe reproducir"))

# ----------------------------------------------------------------------
# 4) LEEME y zip
# ----------------------------------------------------------------------
with open(SALIDA / "LEEME.txt", "w", encoding="utf-8") as f:
    f.write("PAQUETE DE DATOS PARA POWER BI (generado por src/exportar_para_powerbi.py)\n")
    f.write("Contiene datos derivados de la base del HUN: compartir solo por el drive privado del equipo, nunca por git.\n")
    f.write("Guia completa: powerbi/CLAUDE.md, powerbi/especificacion_paginas.md y powerbi/diccionario_tablas.md del repositorio.\n")
    f.write("bi_estancias.csv es una fila por estancia (sin ids): usarla solo si se autorizan datos por fila.\n\n")
    for nombre, filas, cols, desc in CATALOGO:
        f.write(f"{nombre}  [{filas} filas]\n  {desc}\n  columnas: {cols}\n\n")
shutil.make_archive(str(PROC / "powerbi"), "zip", SALIDA)

print(f"paquete en {SALIDA} ({len(CATALOGO)} archivos) y {PROC / 'powerbi.zip'}")
print("\nCIFRAS DE CONTROL:")
print(cc.to_string(index=False))
fallan = cc[cc.ok == False]    # noqa: E712
print("\nTODAS LAS CIFRAS DE CONTROL COINCIDEN" if fallan.empty else f"\nAVISO: {len(fallan)} cifras fuera de lo esperado: {list(fallan.cifra)}")
