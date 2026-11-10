-- severidad_labs_6h_persona.sql  (10-nov-2026)  Solo lectura. Correr con:  cd src && nohup caffeinate -i python3 ejecutar_consultas.py ../sql/severidad_labs_6h_persona.sql --esperar 120 --latido 60 > ../datos/crudos/consultas/salida.txt 2>&1 &
-- Igual que severidad_labs_6h.sql (valores de laboratorio de las primeras 6 h desde la primera etapa, por visita, extraidos del texto), pero AGRUPADO POR VISITA Y PERSONA (person_id de cada fila de
-- laboratorio). Motivo (10-nov): las banderas de la version sin persona mezclaban los laboratorios de las dos personas de una estancia gemela y dejaban 40 % de estancias con bandera cuando
-- el 61,5 % tiene una toma propia en las 6 h. Con la persona se queda solo lo de la persona real de la estancia. Resultados: datos/crudos/consultas/sevp_*.csv (fuera de git).
-- Tiempo estimado: 2 a 5 minutos en total (8 consultas, ~20 a 50 segundos cada una).

-- nombre: sevp_hemograma_6h_2023
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2023-02-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2024-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.person_id,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id, person_id, MAX(leuc) AS leuc_max, MIN(leuc) AS leuc_min, MIN(hb) AS hb_min, COUNT(*) AS n_hemogramas
FROM r GROUP BY visit_occurrence_id, person_id;

-- nombre: sevp_hemograma_6h_2024
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2024-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2025-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.person_id,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id, person_id, MAX(leuc) AS leuc_max, MIN(leuc) AS leuc_min, MIN(hb) AS hb_min, COUNT(*) AS n_hemogramas
FROM r GROUP BY visit_occurrence_id, person_id;

-- nombre: sevp_hemograma_6h_2025
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2025-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.person_id,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id, person_id, MAX(leuc) AS leuc_max, MIN(leuc) AS leuc_min, MIN(hb) AS hb_min, COUNT(*) AS n_hemogramas
FROM r GROUP BY visit_occurrence_id, person_id;

-- nombre: sevp_hemograma_6h_2026
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2026-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-04-10'
), r AS (
  SELECT v.visit_occurrence_id, m.person_id,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id, person_id, MAX(leuc) AS leuc_max, MIN(leuc) AS leuc_min, MIN(hb) AS hb_min, COUNT(*) AS n_hemogramas
FROM r GROUP BY visit_occurrence_id, person_id;

-- nombre: sevp_quimica_6h_2023
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2023-02-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2024-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.person_id, m.measurement_source_value_extended AS x
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id, person_id,
  MAX((regexp_match(x, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS creat_max,
  MAX((regexp_match(x, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric) AS bun_max,
  MAX((regexp_match(x, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)                   AS lactato_max,
  MAX((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_max,
  MIN((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_min,
  MAX((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_max,
  MIN((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_min,
  MAX((regexp_match(x, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)               AS troponina_max,
  MAX((regexp_match(x, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS pcr_max
FROM r GROUP BY visit_occurrence_id, person_id;

-- nombre: sevp_quimica_6h_2024
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2024-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2025-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.person_id, m.measurement_source_value_extended AS x
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id, person_id,
  MAX((regexp_match(x, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS creat_max,
  MAX((regexp_match(x, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric) AS bun_max,
  MAX((regexp_match(x, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)                   AS lactato_max,
  MAX((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_max,
  MIN((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_min,
  MAX((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_max,
  MIN((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_min,
  MAX((regexp_match(x, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)               AS troponina_max,
  MAX((regexp_match(x, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS pcr_max
FROM r GROUP BY visit_occurrence_id, person_id;

-- nombre: sevp_quimica_6h_2025
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2025-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.person_id, m.measurement_source_value_extended AS x
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id, person_id,
  MAX((regexp_match(x, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS creat_max,
  MAX((regexp_match(x, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric) AS bun_max,
  MAX((regexp_match(x, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)                   AS lactato_max,
  MAX((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_max,
  MIN((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_min,
  MAX((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_max,
  MIN((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_min,
  MAX((regexp_match(x, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)               AS troponina_max,
  MAX((regexp_match(x, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS pcr_max
FROM r GROUP BY visit_occurrence_id, person_id;

-- nombre: sevp_quimica_6h_2026
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2026-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-04-10'
), r AS (
  SELECT v.visit_occurrence_id, m.person_id, m.measurement_source_value_extended AS x
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id, person_id,
  MAX((regexp_match(x, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS creat_max,
  MAX((regexp_match(x, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric) AS bun_max,
  MAX((regexp_match(x, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)                   AS lactato_max,
  MAX((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_max,
  MIN((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_min,
  MAX((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_max,
  MIN((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_min,
  MAX((regexp_match(x, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)               AS troponina_max,
  MAX((regexp_match(x, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS pcr_max
FROM r GROUP BY visit_occurrence_id, person_id;

