-- nombre: procedure_fechas
SELECT
    COUNT(*)                                            AS total_filas,
    COUNT(procedure_date)                               AS con_fecha,
    COUNT(*) - COUNT(procedure_date)                    AS sin_fecha,
    ROUND(100.0 * COUNT(procedure_date) / COUNT(*), 4)   AS pct_con_fecha
FROM uninorte_omop.procedure_occurrence;
