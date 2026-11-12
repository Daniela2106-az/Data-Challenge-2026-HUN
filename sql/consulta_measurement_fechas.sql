-- nombre: measurement_fechas
SELECT
    COUNT(*)                                                AS total_filas,
    COUNT(measurement_datetime)                             AS con_fecha,
    COUNT(*) - COUNT(measurement_datetime)                  AS sin_fecha,
    ROUND(100.0 * COUNT(measurement_datetime) / COUNT(*), 4) AS pct_con_fecha
FROM uninorte_omop.measurement;
