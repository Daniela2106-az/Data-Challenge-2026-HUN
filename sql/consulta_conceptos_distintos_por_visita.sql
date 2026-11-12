-- nombre: conceptos_distintos_condition
WITH por_visita AS (
    SELECT visit_occurrence_id,
           COUNT(DISTINCT condition_concept_id)                                              AS n_dist,
           COUNT(DISTINCT condition_concept_id) FILTER (WHERE condition_concept_id <> 0)      AS n_dist_real
    FROM uninorte_omop.condition_occurrence
    GROUP BY visit_occurrence_id
)
SELECT COUNT(*)                     AS visitas_con_registros,
       ROUND(AVG(n_dist), 2)        AS prom_conceptos_distintos,
       ROUND(AVG(n_dist_real), 2)   AS prom_conceptos_distintos_reales
FROM por_visita;

-- nombre: conceptos_distintos_procedure
WITH por_visita AS (
    SELECT visit_occurrence_id,
           COUNT(DISTINCT procedure_concept_id)                                              AS n_dist,
           COUNT(DISTINCT procedure_concept_id) FILTER (WHERE procedure_concept_id <> 0)      AS n_dist_real
    FROM uninorte_omop.procedure_occurrence
    GROUP BY visit_occurrence_id
)
SELECT COUNT(*)                     AS visitas_con_registros,
       ROUND(AVG(n_dist), 2)        AS prom_conceptos_distintos,
       ROUND(AVG(n_dist_real), 2)   AS prom_conceptos_distintos_reales
FROM por_visita;

-- nombre: conceptos_distintos_measurement
WITH por_visita AS (
    SELECT visit_occurrence_id,
           COUNT(DISTINCT measurement_concept_id)                                              AS n_dist,
           COUNT(DISTINCT measurement_concept_id) FILTER (WHERE measurement_concept_id <> 0)    AS n_dist_real
    FROM uninorte_omop.measurement
    GROUP BY visit_occurrence_id
)
SELECT COUNT(*)                     AS visitas_con_registros,
       ROUND(AVG(n_dist), 2)        AS prom_conceptos_distintos,
       ROUND(AVG(n_dist_real), 2)   AS prom_conceptos_distintos_reales
FROM por_visita;
