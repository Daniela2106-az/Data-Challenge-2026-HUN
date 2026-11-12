-- severidad_labs_12_24h.sql  (8-nov-2026)  Solo lectura. Para el estimador de tiempo restante (A6, docs/estimador_tiempos.md 3.3).
-- Igual que sql/severidad_labs_6h.sql (mismas expresiones regulares sobre measurement_source_value_extended), pero con los valores
-- ACUMULADOS hasta las 12 h (columnas _12h) y hasta las 24 h (columnas _24h) desde la primera etapa de la visita.
-- El estimador usa los de 12 h para quien lleva 12 h esperando y los de 24 h para quien lleva 24 h (asi no usa nada que aun no se sabe).
-- Partida por anio (8 consultas, una por bloque "-- nombre:") para que una caida de la VPN no pierda todo.
-- Tiempo estimado: 2 a 8 minutos cada una (lee hasta 24 h de laboratorios por visita, ~4 veces la ventana de 6 h).
-- Guardar cada resultado como CSV con el nombre del bloque (p. ej. sev_hemograma_24h_2023.csv) en D:\Descargas D\Datos (fuera de git).
-- Antes de correr: SET statement_timeout = 0;

-- nombre: sev_hemograma_24h_2023
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2023-02-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2024-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_datetime < v.t0 + INTERVAL '12 hours' AS en12,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '24 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id,
  MAX(leuc) FILTER (WHERE en12) AS leuc_max_12h, MIN(leuc) FILTER (WHERE en12) AS leuc_min_12h, MIN(hb) FILTER (WHERE en12) AS hb_min_12h,
  MAX(leuc) AS leuc_max_24h, MIN(leuc) AS leuc_min_24h, MIN(hb) AS hb_min_24h
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_hemograma_24h_2024
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2024-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2025-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_datetime < v.t0 + INTERVAL '12 hours' AS en12,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '24 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id,
  MAX(leuc) FILTER (WHERE en12) AS leuc_max_12h, MIN(leuc) FILTER (WHERE en12) AS leuc_min_12h, MIN(hb) FILTER (WHERE en12) AS hb_min_12h,
  MAX(leuc) AS leuc_max_24h, MIN(leuc) AS leuc_min_24h, MIN(hb) AS hb_min_24h
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_hemograma_24h_2025
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2025-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_datetime < v.t0 + INTERVAL '12 hours' AS en12,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '24 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id,
  MAX(leuc) FILTER (WHERE en12) AS leuc_max_12h, MIN(leuc) FILTER (WHERE en12) AS leuc_min_12h, MIN(hb) FILTER (WHERE en12) AS hb_min_12h,
  MAX(leuc) AS leuc_max_24h, MIN(leuc) AS leuc_min_24h, MIN(hb) AS hb_min_24h
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_hemograma_24h_2026
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2026-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-04-10'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_datetime < v.t0 + INTERVAL '12 hours' AS en12,
         (regexp_match(m.measurement_source_value_extended, 'Recuento de Globulos Blancos :([0-9]+\.?[0-9]*)'))[1]::numeric AS leuc,
         (regexp_match(m.measurement_source_value_extended, 'Hemoglobina :([0-9]+\.?[0-9]*)'))[1]::numeric AS hb
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '24 hours'
  WHERE m.measurement_source_value_extended LIKE '%Recuento de Globulos Blancos :%'
)
SELECT visit_occurrence_id,
  MAX(leuc) FILTER (WHERE en12) AS leuc_max_12h, MIN(leuc) FILTER (WHERE en12) AS leuc_min_12h, MIN(hb) FILTER (WHERE en12) AS hb_min_12h,
  MAX(leuc) AS leuc_max_24h, MIN(leuc) AS leuc_min_24h, MIN(hb) AS hb_min_24h
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_quimica_24h_2023
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2023-02-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2024-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_datetime < v.t0 + INTERVAL '12 hours' AS en12,
         (regexp_match(m.measurement_source_value_extended, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric AS creat,
         (regexp_match(m.measurement_source_value_extended, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS bun,
         (regexp_match(m.measurement_source_value_extended, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS lactato,
         (regexp_match(m.measurement_source_value_extended, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS k,
         (regexp_match(m.measurement_source_value_extended, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS na,
         (regexp_match(m.measurement_source_value_extended, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS troponina,
         (regexp_match(m.measurement_source_value_extended, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS pcr
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '24 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id,
  MAX(creat) FILTER (WHERE en12) AS creat_max_12h,
  MAX(bun) FILTER (WHERE en12) AS bun_max_12h,
  MAX(lactato) FILTER (WHERE en12) AS lactato_max_12h,
  MAX(k) FILTER (WHERE en12) AS k_max_12h,
  MAX(na) FILTER (WHERE en12) AS na_max_12h,
  MIN(na) FILTER (WHERE en12) AS na_min_12h,
  MAX(troponina) FILTER (WHERE en12) AS troponina_max_12h,
  MAX(pcr) FILTER (WHERE en12) AS pcr_max_12h,
  MAX(creat) AS creat_max_24h,
  MAX(bun) AS bun_max_24h,
  MAX(lactato) AS lactato_max_24h,
  MAX(k) AS k_max_24h,
  MAX(na) AS na_max_24h,
  MIN(na) AS na_min_24h,
  MAX(troponina) AS troponina_max_24h,
  MAX(pcr) AS pcr_max_24h
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_quimica_24h_2024
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2024-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2025-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_datetime < v.t0 + INTERVAL '12 hours' AS en12,
         (regexp_match(m.measurement_source_value_extended, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric AS creat,
         (regexp_match(m.measurement_source_value_extended, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS bun,
         (regexp_match(m.measurement_source_value_extended, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS lactato,
         (regexp_match(m.measurement_source_value_extended, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS k,
         (regexp_match(m.measurement_source_value_extended, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS na,
         (regexp_match(m.measurement_source_value_extended, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS troponina,
         (regexp_match(m.measurement_source_value_extended, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS pcr
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '24 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id,
  MAX(creat) FILTER (WHERE en12) AS creat_max_12h,
  MAX(bun) FILTER (WHERE en12) AS bun_max_12h,
  MAX(lactato) FILTER (WHERE en12) AS lactato_max_12h,
  MAX(k) FILTER (WHERE en12) AS k_max_12h,
  MAX(na) FILTER (WHERE en12) AS na_max_12h,
  MIN(na) FILTER (WHERE en12) AS na_min_12h,
  MAX(troponina) FILTER (WHERE en12) AS troponina_max_12h,
  MAX(pcr) FILTER (WHERE en12) AS pcr_max_12h,
  MAX(creat) AS creat_max_24h,
  MAX(bun) AS bun_max_24h,
  MAX(lactato) AS lactato_max_24h,
  MAX(k) AS k_max_24h,
  MAX(na) AS na_max_24h,
  MIN(na) AS na_min_24h,
  MAX(troponina) AS troponina_max_24h,
  MAX(pcr) AS pcr_max_24h
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_quimica_24h_2025
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2025-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-01-01'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_datetime < v.t0 + INTERVAL '12 hours' AS en12,
         (regexp_match(m.measurement_source_value_extended, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric AS creat,
         (regexp_match(m.measurement_source_value_extended, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS bun,
         (regexp_match(m.measurement_source_value_extended, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS lactato,
         (regexp_match(m.measurement_source_value_extended, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS k,
         (regexp_match(m.measurement_source_value_extended, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS na,
         (regexp_match(m.measurement_source_value_extended, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS troponina,
         (regexp_match(m.measurement_source_value_extended, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS pcr
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '24 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id,
  MAX(creat) FILTER (WHERE en12) AS creat_max_12h,
  MAX(bun) FILTER (WHERE en12) AS bun_max_12h,
  MAX(lactato) FILTER (WHERE en12) AS lactato_max_12h,
  MAX(k) FILTER (WHERE en12) AS k_max_12h,
  MAX(na) FILTER (WHERE en12) AS na_max_12h,
  MIN(na) FILTER (WHERE en12) AS na_min_12h,
  MAX(troponina) FILTER (WHERE en12) AS troponina_max_12h,
  MAX(pcr) FILTER (WHERE en12) AS pcr_max_12h,
  MAX(creat) AS creat_max_24h,
  MAX(bun) AS bun_max_24h,
  MAX(lactato) AS lactato_max_24h,
  MAX(k) AS k_max_24h,
  MAX(na) AS na_max_24h,
  MIN(na) AS na_min_24h,
  MAX(troponina) AS troponina_max_24h,
  MAX(pcr) AS pcr_max_24h
FROM r GROUP BY visit_occurrence_id;

-- nombre: sev_quimica_24h_2026
WITH v AS (
  SELECT visit_occurrence_id, MIN(visit_detail_start_datetime) AS t0
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
  HAVING MIN(visit_detail_start_datetime) >= TIMESTAMP '2026-01-01' AND MIN(visit_detail_start_datetime) < TIMESTAMP '2026-04-10'
), r AS (
  SELECT v.visit_occurrence_id, m.measurement_datetime < v.t0 + INTERVAL '12 hours' AS en12,
         (regexp_match(m.measurement_source_value_extended, 'CREATININA EN SUERO: :([0-9]+\.?[0-9]*)'))[1]::numeric AS creat,
         (regexp_match(m.measurement_source_value_extended, 'Bun \[Nitrogeno Ureico\]\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS bun,
         (regexp_match(m.measurement_source_value_extended, 'Lactato\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS lactato,
         (regexp_match(m.measurement_source_value_extended, 'Potasio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS k,
         (regexp_match(m.measurement_source_value_extended, 'Sodio en Sangre\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS na,
         (regexp_match(m.measurement_source_value_extended, 'Troponina I\.*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS troponina,
         (regexp_match(m.measurement_source_value_extended, 'PCR Cuantitativa[^:]*: :([0-9]+\.?[0-9]*)'))[1]::numeric AS pcr
  FROM v JOIN uninorte_omop.measurement m ON m.visit_occurrence_id = v.visit_occurrence_id
   AND m.measurement_datetime >= v.t0 AND m.measurement_datetime < v.t0 + INTERVAL '24 hours'
  WHERE m.measurement_source_value_extended ~ '(CREATININA EN SUERO|Bun \[|Lactato|Potasio en Sangre|Sodio en Sangre|Troponina I|PCR Cuantitativa)'
)
SELECT visit_occurrence_id,
  MAX(creat) FILTER (WHERE en12) AS creat_max_12h,
  MAX(bun) FILTER (WHERE en12) AS bun_max_12h,
  MAX(lactato) FILTER (WHERE en12) AS lactato_max_12h,
  MAX(k) FILTER (WHERE en12) AS k_max_12h,
  MAX(na) FILTER (WHERE en12) AS na_max_12h,
  MIN(na) FILTER (WHERE en12) AS na_min_12h,
  MAX(troponina) FILTER (WHERE en12) AS troponina_max_12h,
  MAX(pcr) FILTER (WHERE en12) AS pcr_max_12h,
  MAX(creat) AS creat_max_24h,
  MAX(bun) AS bun_max_24h,
  MAX(lactato) AS lactato_max_24h,
  MAX(k) AS k_max_24h,
  MAX(na) AS na_max_24h,
  MIN(na) AS na_min_24h,
  MAX(troponina) AS troponina_max_24h,
  MAX(pcr) AS pcr_max_24h
FROM r GROUP BY visit_occurrence_id;
