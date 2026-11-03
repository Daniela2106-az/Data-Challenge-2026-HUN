-- Ejemplo para src/ejecutar_consultas.py (ver docs/conexion_bd.md). Cada consulta empieza con "-- nombre: algo" y termina en ";".

-- nombre: visitas_por_mes
SELECT date_trunc('month', visit_start_datetime)::date AS mes, visit_concept_id, count(*) AS visitas
FROM uninorte_omop.visit_occurrence
GROUP BY 1, 2
ORDER BY 1, 2;

-- nombre: personas_por_sexo
SELECT gender_concept_id, count(*) AS personas
FROM uninorte_omop.person
GROUP BY 1
ORDER BY 1;
