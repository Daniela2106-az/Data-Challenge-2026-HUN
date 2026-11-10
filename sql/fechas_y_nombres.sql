-- fechas_y_nombres.sql  (10-nov-2026)  Solo lectura. Correr con:  cd src && nohup caffeinate -i python3 ejecutar_consultas.py ../sql/fechas_y_nombres.sql --esperar 120 --latido 60 > ../datos/crudos/consultas/salida.txt 2>&1 &
-- Resultados en datos/crudos/consultas/<nombre>.csv (fuera de git). Tiempo estimado total: 5 a 15 minutos.
--   ¿Que porcentaje de laboratorios, diagnosticos y procedimientos tiene fecha y hora, y cuantos conceptos distintos hay?
--   Nombre de los 9 conceptos que aun no tienen nombre (procedimientos y laboratorios mas frecuentes).

-- nombre: validez_fechas_measurement
SELECT COUNT(*) AS filas,
       COUNT(*) FILTER (WHERE measurement_datetime IS NULL) AS sin_fecha,
       COUNT(*) FILTER (WHERE measurement_datetime < TIMESTAMP '2023-01-01' OR measurement_datetime >= TIMESTAMP '2026-09-01') AS fecha_fuera_de_rango,
       COUNT(*) FILTER (WHERE measurement_concept_id = 0) AS concepto_cero,
       COUNT(DISTINCT measurement_concept_id) AS conceptos_distintos,
       MIN(measurement_datetime) AS fecha_minima, MAX(measurement_datetime) AS fecha_maxima
FROM uninorte_omop.measurement;

-- nombre: validez_fechas_condition
SELECT COUNT(*) AS filas,
       COUNT(*) FILTER (WHERE condition_start_datetime IS NULL) AS sin_fecha,
       COUNT(*) FILTER (WHERE condition_start_datetime < TIMESTAMP '2023-01-01' OR condition_start_datetime >= TIMESTAMP '2026-09-01') AS fecha_fuera_de_rango,
       COUNT(*) FILTER (WHERE condition_concept_id = 0) AS concepto_cero,
       COUNT(DISTINCT condition_concept_id) AS conceptos_distintos,
       MIN(condition_start_datetime) AS fecha_minima, MAX(condition_start_datetime) AS fecha_maxima
FROM uninorte_omop.condition_occurrence;

-- nombre: validez_fechas_procedure
SELECT COUNT(*) AS filas,
       COUNT(*) FILTER (WHERE procedure_date IS NULL) AS sin_fecha,
       COUNT(*) FILTER (WHERE procedure_concept_id = 0) AS concepto_cero,
       COUNT(DISTINCT procedure_concept_id) AS conceptos_distintos
FROM uninorte_omop.procedure_occurrence;

-- nombre: nombres_conceptos_faltantes
SELECT concept_id, concept_name, vocabulary_id, domain_id
FROM uninorte_omop.concept
WHERE concept_id IN (9713,4007805,4074649,4176561,4178483,4208414,4230543,4331286,44809202);
