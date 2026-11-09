-- espera_labs_dx_con_hora.sql  (9-nov-2026)  Solo lectura. Correr con:  cd src && nohup caffeinate -i python3 ejecutar_consultas.py ../sql/espera_labs_dx_con_hora.sql --esperar 120 --omitir-hechas --latido 60 > ../datos/crudos/consultas/salida.txt 2>&1 &
-- Resultados en datos/crudos/consultas/<nombre>.csv (fuera de git: son datos clinicos). Log: datos/crudos/consultas/consultas.log
-- Para qué: caracterizar la espera de cama (de la primera etapa a la primera HOSP) con cada laboratorio y cada diagnostico CON SU HORA, por persona de la fila
--           (para elegir la persona real en las estancias gemelas) y por visita. Comparar quienes reciben cama pronto, a las 12-48 h y despues de 72 h.
-- Ventana de cada visita: de t0 (primera etapa ER/TU/HOSP) a th (primera HOSP), solo visitas con HOSP y t0 entre 2023-02-01 y 2026-04-10, como espera_labs_por_visita.
-- Laboratorios: una fila por (visita, persona, hora de toma, examen). Diagnosticos: una fila por (visita, persona, diagnostico) con su primera y ultima hora y cuantas filas tiene.
-- Procedimientos NO van: procedure_date esta vacia en toda la tabla, no tienen hora.
-- Dividido por ano de t0 para que ninguna consulta pase de los 15 minutos. Tiempo estimado total: 15 a 40 minutos.

-- nombre: espera_labs_2023
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT DISTINCT v.visit_occurrence_id, m.person_id, v.t0, v.th, m.measurement_datetime, m.measurement_concept_id
FROM v
JOIN uninorte_omop.measurement m
  ON m.visit_occurrence_id = v.visit_occurrence_id
 AND m.measurement_datetime >= v.t0
 AND m.measurement_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2023-02-01' AND v.t0 < TIMESTAMP '2024-01-01';

-- nombre: espera_labs_2024
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT DISTINCT v.visit_occurrence_id, m.person_id, v.t0, v.th, m.measurement_datetime, m.measurement_concept_id
FROM v
JOIN uninorte_omop.measurement m
  ON m.visit_occurrence_id = v.visit_occurrence_id
 AND m.measurement_datetime >= v.t0
 AND m.measurement_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2024-01-01' AND v.t0 < TIMESTAMP '2025-01-01';

-- nombre: espera_labs_2025
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT DISTINCT v.visit_occurrence_id, m.person_id, v.t0, v.th, m.measurement_datetime, m.measurement_concept_id
FROM v
JOIN uninorte_omop.measurement m
  ON m.visit_occurrence_id = v.visit_occurrence_id
 AND m.measurement_datetime >= v.t0
 AND m.measurement_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2025-01-01' AND v.t0 < TIMESTAMP '2026-01-01';

-- nombre: espera_labs_2026
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT DISTINCT v.visit_occurrence_id, m.person_id, v.t0, v.th, m.measurement_datetime, m.measurement_concept_id
FROM v
JOIN uninorte_omop.measurement m
  ON m.visit_occurrence_id = v.visit_occurrence_id
 AND m.measurement_datetime >= v.t0
 AND m.measurement_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2026-01-01' AND v.t0 < TIMESTAMP '2026-04-10';

-- nombre: espera_dx_2023
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, c.person_id, v.t0, v.th, c.condition_concept_id,
       MIN(c.condition_start_datetime) AS primera, MAX(c.condition_start_datetime) AS ultima, COUNT(*) AS filas
FROM v
JOIN uninorte_omop.condition_occurrence c
  ON c.visit_occurrence_id = v.visit_occurrence_id
 AND c.condition_start_datetime >= v.t0
 AND c.condition_start_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2023-02-01' AND v.t0 < TIMESTAMP '2024-01-01'
GROUP BY v.visit_occurrence_id, c.person_id, v.t0, v.th, c.condition_concept_id;

-- nombre: espera_dx_2024
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, c.person_id, v.t0, v.th, c.condition_concept_id,
       MIN(c.condition_start_datetime) AS primera, MAX(c.condition_start_datetime) AS ultima, COUNT(*) AS filas
FROM v
JOIN uninorte_omop.condition_occurrence c
  ON c.visit_occurrence_id = v.visit_occurrence_id
 AND c.condition_start_datetime >= v.t0
 AND c.condition_start_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2024-01-01' AND v.t0 < TIMESTAMP '2025-01-01'
GROUP BY v.visit_occurrence_id, c.person_id, v.t0, v.th, c.condition_concept_id;

-- nombre: espera_dx_2025
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, c.person_id, v.t0, v.th, c.condition_concept_id,
       MIN(c.condition_start_datetime) AS primera, MAX(c.condition_start_datetime) AS ultima, COUNT(*) AS filas
FROM v
JOIN uninorte_omop.condition_occurrence c
  ON c.visit_occurrence_id = v.visit_occurrence_id
 AND c.condition_start_datetime >= v.t0
 AND c.condition_start_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2025-01-01' AND v.t0 < TIMESTAMP '2026-01-01'
GROUP BY v.visit_occurrence_id, c.person_id, v.t0, v.th, c.condition_concept_id;

-- nombre: espera_dx_2026
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, c.person_id, v.t0, v.th, c.condition_concept_id,
       MIN(c.condition_start_datetime) AS primera, MAX(c.condition_start_datetime) AS ultima, COUNT(*) AS filas
FROM v
JOIN uninorte_omop.condition_occurrence c
  ON c.visit_occurrence_id = v.visit_occurrence_id
 AND c.condition_start_datetime >= v.t0
 AND c.condition_start_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2026-01-01' AND v.t0 < TIMESTAMP '2026-04-10'
GROUP BY v.visit_occurrence_id, c.person_id, v.t0, v.th, c.condition_concept_id;
