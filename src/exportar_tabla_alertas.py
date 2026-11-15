"""
exportar_tabla_alertas.py  -  catalogo de alertas para el dashboard (14-nov-2026)

Arma datos/tablas_dashboard/alertas_tabla.csv: una fila por alerta y por momento de aviso, con su identificador fijo, lo que
se midio y la(s) recomendacion(es) que dispara. Es la "interfaz" entre las alertas y las recomendaciones: la pagina /alertas
y la pagina /recomendaciones leen este archivo, y quien conecte un flujo despues (el modulo de predicciones en secuencia)
puede leerlo para saber que alerta existe, con que umbral y que recomendacion le corresponde.

IDENTIFICADORES (no cambiarlos: otros modulos pueden depender de ellos)
  A1  Dia congestionado           llegadas del dia por encima del percentil 90 del mismo dia de la semana (12 semanas)
  A2  Ocupacion alta de manana    ocupacion a las 12 h por encima del percentil 80 del entrenamiento (107-109 camas)
  A3  Paciente sin cama           desde su llegada lleva T horas sin cama (recomendada: 48 h)
  A4  Paciente sin cama, temprana el estimador A6 da >= 40 % de probabilidad de seguir sin cama a las 48 h, evaluado a las 12 h
  S1  Cola proyectada             SENAL, no alerta: pacientes que seguiran sin cama a 6, 12 y 24 h (no tiene umbral)
  Recomendaciones: R1 a R7 de docs/recomendaciones.md (prioridad = numero).

ENTRADAS  resultados/tablas/alertas_congestion.csv, alertas_camas.csv, alertas_paciente.csv (src/alertas.py, regla v3.8, prueba
          de enero al 9-abr-2026 con cortes elegidos en jul-dic 2025). A4 y S1 no tienen tabla local: sus cifras se copian de
          el recalculo del 14-nov con src/utilidad_estimador.py (docs/estimador_tiempos.md 3.2 trae 55,3 % y 53,5 %, de la version del 11-nov) y docs/pronostico_espera_sistema.md (1a); la fuente queda en cada fila.
SALIDA    datos/tablas_dashboard/alertas_tabla.csv  (agregado: sin datos por paciente)
COMO CORRERLO  python3 src/exportar_tabla_alertas.py   (segundos)
LIMITES   Las alertas se probaron reproduciendo dias pasados (15 dias congestionados en la prueba), no en tiempo real. La
          precision de A3 es el % de avisos que termina esperando mas de 72 h; solo cuenta a quienes luego se hospitalizan.
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "resultados" / "tablas"
SALIDA = RAIZ / "datos" / "tablas_dashboard" / "alertas_tabla.csv"
COLUMNAS = ["alerta_id", "alerta", "tipo", "momento", "orden", "recomendada", "alertas_por_dia", "precision_pct", "deteccion_pct",
            "auc", "margen_h", "medida", "recomendacion_ids", "fuente"]
fila = lambda **k: {c: k.get(c) for c in COLUMNAS}

filas = []

# ---- A1 dia congestionado (src/alertas.py, alertas_congestion.csv)
cong = pd.read_csv(TABLAS / "alertas_congestion.csv")
nombres = ["Un día antes", "A las 9 h", "A las 12 h", "A las 15 h"]
for i, r in cong.iterrows():
    filas.append(fila(alerta_id="A1", alerta="Día congestionado", tipo="alerta", momento=nombres[i], orden=i + 1, recomendada=int(i == 2),
                      alertas_por_dia=r["alertas_por_dia"], precision_pct=r["precision_%"], deteccion_pct=r["deteccion_%"], auc=r["AUC_prueba"],
                      medida=f"{int(r['alertas'])} alertas, {int(r['aciertos'])} aciertos en la prueba (15 días congestionados)",
                      recomendacion_ids="R3;R4", fuente="resultados/tablas/alertas_congestion.csv; src/alertas.py"))

# ---- A2 ocupacion alta de manana (alertas_camas.csv)
cam = pd.read_csv(TABLAS / "alertas_camas.csv")
etiquetas = {"persistencia": "«Mañana igual que hoy» (persistencia)", "proyeccion": "Proyección con altas e ingresos esperados"}
for i, r in cam.sort_values("metodo", ascending=False).reset_index(drop=True).iterrows():
    filas.append(fila(alerta_id="A2", alerta="Ocupación alta de mañana", tipo="alerta", momento=etiquetas[r["metodo"]], orden=i + 1,
                      recomendada=int(r["metodo"] == "persistencia"), alertas_por_dia=r["alertas_por_dia"], precision_pct=r["precision_%"],
                      deteccion_pct=r["deteccion_%"], auc=r["AUC_prueba"],
                      medida=f"{int(r['alertas'])} alertas, {int(r['aciertos'])} aciertos; umbral: el 20 % de ocupaciones más altas a las 12 h (107 a 109 camas)",
                      recomendacion_ids="R3;R4", fuente="resultados/tablas/alertas_camas.csv; src/alertas.py"))

# ---- A3 paciente sin cama (alertas_paciente.csv): la precision es el % que termina esperando mas de 72 h
pac = pd.read_csv(TABLAS / "alertas_paciente.csv")
pac = pac[pac["alerta_a_las_T_horas"] >= 24].reset_index(drop=True)      # la de 12 h no es parte del diseno recomendado (A4 la cubre con el estimador)
for i, r in pac.iterrows():
    t = int(r["alerta_a_las_T_horas"])
    filas.append(fila(alerta_id="A3", alerta="Paciente sin cama", tipo="alerta", momento=f"A las {t} h sin cama", orden=i + 1, recomendada=int(t == 48),
                      alertas_por_dia=r["alertas_por_dia"], precision_pct=r["pct_que_espera_mas_de_72h"], margen_h=r["horas_de_anticipacion_a_las_72h"],
                      medida=f"{r['pct_que_espera_mas_de_72h']:.0f} % de los avisos termina esperando más de 72 h; quedan {int(r['horas_de_anticipacion_a_las_72h'])} h de margen",
                      recomendacion_ids="R5", fuente="resultados/tablas/alertas_paciente.csv; src/alertas.py"))

# ---- A4 paciente sin cama, temprana, con el estimador A6 (recalculo del 14-nov con src/utilidad_estimador.py): evaluada a las 12 h de espera
for i, (corte, apd, prec, det) in enumerate([(30, 6.9, 48.2, 77.7), (40, 4.1, 54.8, 53.0), (50, 1.5, 58.8, 19.9)]):
    filas.append(fila(alerta_id="A4", alerta="Paciente sin cama (aviso temprano con el estimador)", tipo="alerta",
                      momento=f"A las 12 h, probabilidad ≥ {corte} % de seguir sin cama a las 48 h", orden=i + 1, recomendada=int(corte == 40),
                      alertas_por_dia=apd, precision_pct=prec, deteccion_pct=det, auc=0.68, margen_h=36,
                      medida="Referencia sin modelo: alertar a todos los que llevan 24 h da 8,1 alertas por día y acierta 52,9 %; con el estimador hay 12 h más de margen",
                      recomendacion_ids="R5", fuente="recalculado el 14-nov con src/utilidad_estimador.py (evaluar_alerta; modelo entrenado hasta jun-2025, prueba jul-2025 a 9-abr-2026); solo para pacientes con orden de hospitalización"))

# ---- S1 cola proyectada (senal, sin umbral): error en pacientes, modelo de flujo frente a "lo mismo que ahora"
for i, (h, persist, flujo, mejora) in enumerate([(6, 3.82, 2.58, 33), (12, 5.47, 3.48, 36), (24, 4.53, 4.11, 9)]):
    filas.append(fila(alerta_id="S1", alerta="Cola proyectada (pacientes sin cama)", tipo="senal", momento=f"A {h} h", orden=i + 1, recomendada=int(h == 12),
                      medida=f"Error de {flujo:.1f} pacientes frente a {persist:.1f} de «lo mismo que ahora» (−{mejora} %); es una señal para la reunión de camas, no una alerta con umbral".replace(".", ","),
                      recomendacion_ids="R3", fuente="docs/pronostico_espera_sistema.md 1a (prueba jul-2025 a 9-abr-2026)"))

SALIDA.parent.mkdir(parents=True, exist_ok=True)
tabla = pd.DataFrame(filas, columns=COLUMNAS)
tabla.to_csv(SALIDA, index=False, encoding="utf-8")
print(f"{SALIDA.relative_to(RAIZ)}: {len(tabla)} filas")
print(tabla[["alerta_id", "momento", "recomendada", "alertas_por_dia", "precision_pct", "deteccion_pct", "auc"]].to_string(index=False))
# comprobacion: la carga total del diseno recomendado (A1 a las 12 h + A2 persistencia + A3 a las 48 h) debe ser ~4,6 por dia
rec = tabla[(tabla.recomendada == 1) & (tabla.alerta_id.isin(["A1", "A2", "A3"]))]
print(f"\ncarga total del diseño recomendado (A1+A2+A3): {rec.alertas_por_dia.sum():.2f} alertas por día (CLAUDE.md 6b: ~4,6)")
