-- consultas_semana1.sql  (version 2, 20-oct-2026)
-- Exportar cada resultado completo a CSV desde DBeaver: clic derecho en el resultado >
-- Exportar datos > CSV, separador coma, con encabezado. Nombre del archivo indicado en cada una.
-- Guardar los CSV en la misma carpeta que preparar_variables.py.
-- Las consultas 2, 3 y 4 recorren tablas grandes: pueden tardar 10-30 min cada una.
--
-- QUE CAMBIO EN v2: solo la consulta 4 (laboratorios). Ahora tambien cuenta los laboratorios
-- de las primeras 6 h y los tomados antes de la primera hospitalizacion.
-- Las consultas 1, 2 y 3 no cambian: si ya tienes esos CSV, NO hace falta repetirlas.

SET statement_timeout = 0;   -- sin limite de tiempo solo para esta sesion

-- ---------------------------------------------------------------------
-- 1) person.csv  (obligatoria, ~912 mil filas, rapida)
-- ---------------------------------------------------------------------
SELECT p.person_id,
       p.year_of_birth,
       c.concept_name AS sexo
FROM uninorte_omop.person p
LEFT JOIN uninorte_omop.concept c ON c.concept_id = p.gender_concept_id;

-- ---------------------------------------------------------------------
-- 2) diagnosticos_por_visita.csv  (obligatoria, una fila por visita)
--    dx principal = primer diagnostico con concepto mapeado (distinto de 0) de la visita
-- ---------------------------------------------------------------------
WITH primero AS (
    SELECT DISTINCT ON (co.visit_occurrence_id)
           co.visit_occurrence_id,
           co.condition_concept_id
    FROM uninorte_omop.condition_occurrence co
    WHERE co.condition_concept_id <> 0
    ORDER BY co.visit_occurrence_id, co.condition_start_datetime, co.condition_occurrence_id
),
conteo AS (
    SELECT co.visit_occurrence_id,
           COUNT(DISTINCT co.condition_concept_id) AS n_dx_distintos
    FROM uninorte_omop.condition_occurrence co
    WHERE co.condition_concept_id <> 0
    GROUP BY co.visit_occurrence_id
)
SELECT p.visit_occurrence_id,
       p.condition_concept_id AS dx_concept_id,
       c.concept_name         AS dx_nombre,
       c.vocabulary_id        AS dx_vocabulario,
       n.n_dx_distintos
FROM primero p
JOIN conteo n ON n.visit_occurrence_id = p.visit_occurrence_id
LEFT JOIN uninorte_omop.concept c ON c.concept_id = p.condition_concept_id;

-- ---------------------------------------------------------------------
-- 3) procedimientos_por_visita.csv  (opcional)
-- ---------------------------------------------------------------------
SELECT po.visit_occurrence_id,
       COUNT(DISTINCT po.procedure_concept_id) AS n_proc_distintos
FROM uninorte_omop.procedure_occurrence po
GROUP BY po.visit_occurrence_id;

-- ---------------------------------------------------------------------
-- 4) laboratorios_por_visita.csv  (REEMPLAZA el archivo anterior; la mas pesada)
--    n_lab_6h         = laboratorios en las primeras 6 h desde la primera etapa (sin AMB)
--    n_lab_antes_hosp = laboratorios tomados antes de la primera etapa de hospitalizacion (9201)
-- ---------------------------------------------------------------------
WITH etapas AS (
    SELECT vd.visit_occurrence_id,
           MIN(vd.visit_detail_start_datetime) AS ini,
           MIN(vd.visit_detail_start_datetime) FILTER (WHERE vd.visit_detail_concept_id = 9201) AS ini_hosp
    FROM uninorte_omop.visit_detail vd
    WHERE vd.visit_detail_concept_id <> 581479
    GROUP BY vd.visit_occurrence_id
)
SELECT m.visit_occurrence_id,
       COUNT(*)                                  AS n_lab,
       COUNT(DISTINCT m.measurement_concept_id)  AS n_lab_distintos,
       COUNT(*) FILTER (WHERE m.measurement_datetime <  e.ini + INTERVAL '6 hours') AS n_lab_6h,
       COUNT(*) FILTER (WHERE m.measurement_datetime <  e.ini_hosp)                AS n_lab_antes_hosp
FROM uninorte_omop.measurement m
LEFT JOIN etapas e ON e.visit_occurrence_id = m.visit_occurrence_id
GROUP BY m.visit_occurrence_id;
