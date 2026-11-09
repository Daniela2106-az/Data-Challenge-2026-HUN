-- espera_labs_y_texto.sql  (8-nov-2026)  Solo lectura. Correr con:  cd src && nohup caffeinate -i python3 ejecutar_consultas.py ../sql/espera_labs_y_texto.sql --esperar 120 > ../datos/crudos/consultas/salida.txt 2>&1 &
-- Resultados en datos/crudos/consultas/<nombre>.csv (fuera de git). Tiempo estimado total: 10 a 25 minutos.
--   C2: comprueba que las consultas de sql/exportaciones_base.sql dan 566.004 y 662.783 filas.
--   A8 punto 6: laboratorios dentro de la espera de cama (de la primera etapa a la primera HOSP) por visita.
--   A8 punto 10: muestra del texto de los laboratorios y los conceptos mas frecuentes (para decidir si se puede sacar una severidad).

-- nombre: c2_filas_dx
SELECT COUNT(*) AS filas, SUM(n_dx) AS suma_n_dx, COUNT(*) FILTER (WHERE visit_occurrence_id IS NULL) AS filas_visita_vacia
FROM (SELECT visit_occurrence_id, COUNT(*) AS n_dx FROM uninorte_omop.condition_occurrence GROUP BY visit_occurrence_id) x;

-- nombre: c2_filas_proc
SELECT COUNT(*) AS filas, SUM(n_proc) AS suma_n_proc, COUNT(*) FILTER (WHERE visit_occurrence_id IS NULL) AS filas_visita_vacia
FROM (SELECT visit_occurrence_id, COUNT(*) AS n_proc FROM uninorte_omop.procedure_occurrence GROUP BY visit_occurrence_id) x;

-- nombre: espera_labs_por_visita
WITH v AS (
  SELECT visit_occurrence_id,
         MIN(visit_detail_start_datetime) AS t0,
         MIN(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS th
  FROM uninorte_omop.visit_detail
  WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  GROUP BY visit_occurrence_id
)
SELECT v.visit_occurrence_id, v.t0, v.th,
       COUNT(DISTINCT m.measurement_datetime)                          AS n_tomas,
       COUNT(DISTINCT date_trunc('hour', m.measurement_datetime))      AS n_horas_con_toma,
       COUNT(DISTINCT m.measurement_concept_id)                        AS n_examenes_distintos,
       MIN(m.measurement_datetime)                                     AS primera_toma,
       MAX(m.measurement_datetime)                                     AS ultima_toma
FROM v
JOIN uninorte_omop.measurement m
  ON m.visit_occurrence_id = v.visit_occurrence_id
 AND m.measurement_datetime >= v.t0
 AND m.measurement_datetime <  v.th
WHERE v.th IS NOT NULL AND v.t0 >= TIMESTAMP '2023-02-01' AND v.t0 < TIMESTAMP '2026-04-10'
GROUP BY v.visit_occurrence_id, v.t0, v.th;

-- nombre: labs_conceptos_frecuentes
WITH top AS (
  SELECT measurement_concept_id, COUNT(*) AS filas,
         AVG(length(measurement_source_value_extended))::int AS largo_medio_texto,
         AVG((value_as_number <> 0)::int) AS pct_con_valor_numerico
  FROM uninorte_omop.measurement
  GROUP BY measurement_concept_id
  ORDER BY COUNT(*) DESC
  LIMIT 80
)
SELECT t.*, c.concept_name, c.vocabulary_id
FROM top t LEFT JOIN uninorte_omop.concept c ON c.concept_id = t.measurement_concept_id
ORDER BY t.filas DESC;

-- nombre: labs_muestra_texto
SELECT measurement_concept_id, value_as_number, left(measurement_source_value_extended, 400) AS texto
FROM uninorte_omop.measurement TABLESAMPLE SYSTEM (0.05)
WHERE measurement_source_value_extended IS NOT NULL
LIMIT 400;
