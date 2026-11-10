-- ids_procedimientos.sql  (10-nov-2026)  Solo lectura. Correr con:  cd src && nohup caffeinate -i python3 ejecutar_consultas.py ../sql/ids_procedimientos.sql --esperar 120 --latido 60 > ../datos/crudos/consultas/salida.txt 2>&1 &
-- Resultados en datos/crudos/consultas/<nombre>.csv (fuera de git: son datos clinicos). Log: datos/crudos/consultas/consultas.log
-- Para que: los procedimientos no tienen fecha (procedure_date vacia). ¿El ORDEN de procedure_occurrence_id sigue el orden en que se registraron? Si si, los procedimientos se pueden
--           ordenar entre si y, con las ordenes de laboratorio como ancla (misma prueba, con hora de toma), ubicarlos entre dos anclas, o sea, en una etapa TU aproximada.
-- Que se saca, por ano de t0 (primera etapa) de las visitas con hospitalizacion, como espera_labs_dx_con_hora.sql:
--   proc_ids_<ano>: por (visita, persona, procedimiento): primer y ultimo procedure_occurrence_id y cuantas filas.
--   labs_ids_<ano>: por (visita, persona, hora de toma, examen): primer measurement_id, dentro de la ventana de espera [t0, th). Sirve para comprobar si el id sigue la hora en laboratorios.
-- Tiempo estimado total: 10 a 25 minutos.

-- nombre: proc_ids_2023
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, p.person_id, p.procedure_concept_id AS concepto,
       MIN(p.procedure_occurrence_id) AS id_min, MAX(p.procedure_occurrence_id) AS id_max, COUNT(*) AS filas
FROM v
JOIN uninorte_omop.procedure_occurrence p ON p.visit_occurrence_id = v.visit_occurrence_id
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2023-02-01' AND v.t0 < TIMESTAMP '2024-01-01'
GROUP BY v.visit_occurrence_id, p.person_id, p.procedure_concept_id;

-- nombre: proc_ids_2024
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, p.person_id, p.procedure_concept_id AS concepto,
       MIN(p.procedure_occurrence_id) AS id_min, MAX(p.procedure_occurrence_id) AS id_max, COUNT(*) AS filas
FROM v
JOIN uninorte_omop.procedure_occurrence p ON p.visit_occurrence_id = v.visit_occurrence_id
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2024-01-01' AND v.t0 < TIMESTAMP '2025-01-01'
GROUP BY v.visit_occurrence_id, p.person_id, p.procedure_concept_id;

-- nombre: proc_ids_2025
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, p.person_id, p.procedure_concept_id AS concepto,
       MIN(p.procedure_occurrence_id) AS id_min, MAX(p.procedure_occurrence_id) AS id_max, COUNT(*) AS filas
FROM v
JOIN uninorte_omop.procedure_occurrence p ON p.visit_occurrence_id = v.visit_occurrence_id
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2025-01-01' AND v.t0 < TIMESTAMP '2026-01-01'
GROUP BY v.visit_occurrence_id, p.person_id, p.procedure_concept_id;

-- nombre: proc_ids_2026
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, p.person_id, p.procedure_concept_id AS concepto,
       MIN(p.procedure_occurrence_id) AS id_min, MAX(p.procedure_occurrence_id) AS id_max, COUNT(*) AS filas
FROM v
JOIN uninorte_omop.procedure_occurrence p ON p.visit_occurrence_id = v.visit_occurrence_id
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2026-01-01' AND v.t0 < TIMESTAMP '2026-04-10'
GROUP BY v.visit_occurrence_id, p.person_id, p.procedure_concept_id;

-- nombre: labs_ids_2023
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, m.person_id, m.measurement_datetime, m.measurement_concept_id AS concepto, MIN(m.measurement_id) AS id_min
FROM v
JOIN uninorte_omop.measurement m
  ON m.visit_occurrence_id = v.visit_occurrence_id
 AND m.measurement_datetime >= v.t0
 AND m.measurement_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2023-02-01' AND v.t0 < TIMESTAMP '2024-01-01'
GROUP BY v.visit_occurrence_id, m.person_id, m.measurement_datetime, m.measurement_concept_id;

-- nombre: labs_ids_2024
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, m.person_id, m.measurement_datetime, m.measurement_concept_id AS concepto, MIN(m.measurement_id) AS id_min
FROM v
JOIN uninorte_omop.measurement m
  ON m.visit_occurrence_id = v.visit_occurrence_id
 AND m.measurement_datetime >= v.t0
 AND m.measurement_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2024-01-01' AND v.t0 < TIMESTAMP '2025-01-01'
GROUP BY v.visit_occurrence_id, m.person_id, m.measurement_datetime, m.measurement_concept_id;

-- nombre: labs_ids_2025
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, m.person_id, m.measurement_datetime, m.measurement_concept_id AS concepto, MIN(m.measurement_id) AS id_min
FROM v
JOIN uninorte_omop.measurement m
  ON m.visit_occurrence_id = v.visit_occurrence_id
 AND m.measurement_datetime >= v.t0
 AND m.measurement_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2025-01-01' AND v.t0 < TIMESTAMP '2026-01-01'
GROUP BY v.visit_occurrence_id, m.person_id, m.measurement_datetime, m.measurement_concept_id;

-- nombre: labs_ids_2026
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, m.person_id, m.measurement_datetime, m.measurement_concept_id AS concepto, MIN(m.measurement_id) AS id_min
FROM v
JOIN uninorte_omop.measurement m
  ON m.visit_occurrence_id = v.visit_occurrence_id
 AND m.measurement_datetime >= v.t0
 AND m.measurement_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2026-01-01' AND v.t0 < TIMESTAMP '2026-04-10'
GROUP BY v.visit_occurrence_id, m.person_id, m.measurement_datetime, m.measurement_concept_id;
