-- exportaciones_base.sql  (23-oct-2026)
-- Las 4 exportaciones de la base que NO estaban en sql/consultas_semana1.sql. Junto con las consultas 1 a 4 de ese archivo
-- (person, diagnosticos_por_visita, procedimientos_por_visita, laboratorios_por_visita) dan los 8 CSV que necesita todo el
-- proyecto en datos/crudos/ (ver README.md, "Como reproducirlo").
-- Exportar cada resultado completo a CSV desde DBeaver (Exportar datos > CSV, coma, con encabezado), con el nombre indicado.
-- OJO: las dos primeras son tablas completas (3,3 M y 1,7 M de filas). Las dos ultimas recorren tablas de 38 M y 47 M de filas:
-- pueden tardar 5-15 min cada una.
--
-- ESTADO: visit_detail.csv y visit_occurrence.csv son los SELECT de columnas que dice CLAUDE.md (seccion 7). Las consultas de
-- dx_por_visita.csv y proc_por_visita.csv se RECONSTRUYERON a partir de los CSV que ya existen (n_dx y n_proc son conteos de
-- FILAS, no de conceptos distintos: maximos de 823.429 y 370.712 por visita) y NO se han probado contra la base. Despues de
-- correrlas, comprobar que dan 566.004 filas (dx) y 662.783 filas (proc), una de ellas con visit_occurrence_id vacio, y que
-- los totales coinciden con los CSV viejos; si no coinciden, corregir aqui.

SET statement_timeout = 0;

-- 1) visit_detail.csv  (3,28 M filas)
SELECT visit_detail_id,
       visit_occurrence_id,
       visit_detail_concept_id,
       visit_detail_start_datetime,
       visit_detail_end_datetime
FROM uninorte_omop.visit_detail;

-- 2) visit_occurrence.csv  (1,7 M filas)
SELECT visit_occurrence_id,
       person_id,
       visit_concept_id
FROM uninorte_omop.visit_occurrence;

-- 3) dx_por_visita.csv  (~566 mil filas; conteo y primera/ultima hora de diagnostico por visita)
SELECT visit_occurrence_id,
       COUNT(*)                         AS n_dx,
       MIN(condition_start_datetime)    AS dx_min,
       MAX(condition_start_datetime)    AS dx_max
FROM uninorte_omop.condition_occurrence
GROUP BY visit_occurrence_id;

-- 4) proc_por_visita.csv  (~663 mil filas; conteo de procedimientos por visita)
SELECT visit_occurrence_id,
       COUNT(*) AS n_proc
FROM uninorte_omop.procedure_occurrence
GROUP BY visit_occurrence_id;
