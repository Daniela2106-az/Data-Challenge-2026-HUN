-- severidad_labs_6h.sql  (8-nov-2026)  Solo lectura. A8 punto 10: valores de laboratorio de las primeras 6 h desde la primera etapa, por visita.
-- Se extraen con expresiones regulares del texto (measurement_source_value_extended). Resultados en datos/crudos/consultas/ (fuera de git).
-- Partida por anio (8 consultas) para que una caida de la VPN no pierda todo. Tiempo estimado: 1 a 4 minutos cada una.

-- nombre: sev_hemograma_6h_2023
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2023-02-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2024-01-01'
), r AS (
  SELECT v.visit_occurrence_id,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id, MAX(leuc) AS leuc_max, MIN(leuc) AS leuc_min, MIN(hb) AS hb_min, COUNT(*) AS n_hemogramas
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_hemograma_6h_2024
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2024-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2025-01-01'
), r AS (
  SELECT v.visit_occurrence_id,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id, MAX(leuc) AS leuc_max, MIN(leuc) AS leuc_min, MIN(hb) AS hb_min, COUNT(*) AS n_hemogramas
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_hemograma_6h_2025
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2025-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-01-01'
), r AS (
  SELECT v.visit_occurrence_id,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id, MAX(leuc) AS leuc_max, MIN(leuc) AS leuc_min, MIN(hb) AS hb_min, COUNT(*) AS n_hemogramas
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_hemograma_6h_2026
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2026-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-04-10'
), r AS (
  SELECT v.visit_occurrence_id,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id, MAX(leuc) AS leuc_max, MIN(leuc) AS leuc_min, MIN(hb) AS hb_min, COUNT(*) AS n_hemogramas
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_quimica_6h_2023
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2023-02-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2024-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_source_value_extended AS x
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id,
  MAX((regexp_match(x, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS creat_max,
  MAX((regexp_match(x, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric) AS bun_max,
  MAX((regexp_match(x, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)                   AS lactato_max,
  MAX((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_max,
  MIN((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_min,
  MAX((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_max,
  MIN((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_min,
  MAX((regexp_match(x, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)               AS troponina_max,
  MAX((regexp_match(x, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS pcr_max
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_quimica_6h_2024
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2024-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2025-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_source_value_extended AS x
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id,
  MAX((regexp_match(x, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS creat_max,
  MAX((regexp_match(x, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric) AS bun_max,
  MAX((regexp_match(x, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)                   AS lactato_max,
  MAX((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_max,
  MIN((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_min,
  MAX((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_max,
  MIN((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_min,
  MAX((regexp_match(x, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)               AS troponina_max,
  MAX((regexp_match(x, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS pcr_max
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_quimica_6h_2025
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2025-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_source_value_extended AS x
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id,
  MAX((regexp_match(x, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS creat_max,
  MAX((regexp_match(x, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric) AS bun_max,
  MAX((regexp_match(x, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)                   AS lactato_max,
  MAX((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_max,
  MIN((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_min,
  MAX((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_max,
  MIN((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_min,
  MAX((regexp_match(x, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)               AS troponina_max,
  MAX((regexp_match(x, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS pcr_max
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_quimica_6h_2026
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2026-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-04-10'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_source_value_extended AS x
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '6 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id,
  MAX((regexp_match(x, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS creat_max,
  MAX((regexp_match(x, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric) AS bun_max,
  MAX((regexp_match(x, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)                   AS lactato_max,
  MAX((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_max,
  MIN((regexp_match(x, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)         AS k_min,
  MAX((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_max,
  MIN((regexp_match(x, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)           AS na_min,
  MAX((regexp_match(x, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric)               AS troponina_max,
  MAX((regexp_match(x, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric)        AS pcr_max
FROM r GROUP BY visit_occurrence_id;

