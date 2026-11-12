-- nombre: registros_por_visita_condition
SELECT
    COUNT(*)                            AS total_filas,
    COUNT(DISTINCT visit_occurrence_id) AS visitas_distintas,
    ROUND(COUNT(*)::numeric / COUNT(DISTINCT visit_occurrence_id), 2) AS filas_promedio_por_visita
FROM uninorte_omop.condition_occurrence;

-- nombre: registros_por_visita_procedure
SELECT
    COUNT(*)                            AS total_filas,
    COUNT(DISTINCT visit_occurrence_id) AS visitas_distintas,
    ROUND(COUNT(*)::numeric / COUNT(DISTINCT visit_occurrence_id), 2) AS filas_promedio_por_visita
FROM uninorte_omop.procedure_occurrence;

-- nombre: registros_por_visita_measurement
SELECT
    COUNT(*)                            AS total_filas,
    COUNT(DISTINCT visit_occurrence_id) AS visitas_distintas,
    ROUND(COUNT(*)::numeric / COUNT(DISTINCT visit_occurrence_id), 2) AS filas_promedio_por_visita
FROM uninorte_omop.measurement;
