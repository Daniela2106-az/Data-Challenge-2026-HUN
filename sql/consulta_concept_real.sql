-- nombre: concept_real_condition
SELECT
    COUNT(*) AS total_filas,
    COUNT(*) FILTER (WHERE condition_concept_id IS NOT NULL AND condition_concept_id <> 0) AS con_concepto_real,
    COUNT(*) FILTER (WHERE condition_concept_id IS NULL OR condition_concept_id = 0)        AS sin_concepto,
    ROUND(100.0 * COUNT(*) FILTER (WHERE condition_concept_id IS NOT NULL AND condition_concept_id <> 0) / COUNT(*), 4) AS pct_con_concepto
FROM uninorte_omop.condition_occurrence;

-- nombre: concept_real_procedure
SELECT
    COUNT(*) AS total_filas,
    COUNT(*) FILTER (WHERE procedure_concept_id IS NOT NULL AND procedure_concept_id <> 0) AS con_concepto_real,
    COUNT(*) FILTER (WHERE procedure_concept_id IS NULL OR procedure_concept_id = 0)        AS sin_concepto,
    ROUND(100.0 * COUNT(*) FILTER (WHERE procedure_concept_id IS NOT NULL AND procedure_concept_id <> 0) / COUNT(*), 4) AS pct_con_concepto
FROM uninorte_omop.procedure_occurrence;

-- nombre: concept_real_measurement
SELECT
    COUNT(*) AS total_filas,
    COUNT(*) FILTER (WHERE measurement_concept_id IS NOT NULL AND measurement_concept_id <> 0) AS con_concepto_real,
    COUNT(*) FILTER (WHERE measurement_concept_id IS NULL OR measurement_concept_id = 0)        AS sin_concepto,
    ROUND(100.0 * COUNT(*) FILTER (WHERE measurement_concept_id IS NOT NULL AND measurement_concept_id <> 0) / COUNT(*), 4) AS pct_con_concepto
FROM uninorte_omop.measurement;
