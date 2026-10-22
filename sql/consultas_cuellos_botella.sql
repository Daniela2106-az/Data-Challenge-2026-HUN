-- consultas_cuellos_botella.sql  (21-oct-2026)
-- Consultas para el plan de cuellos de botella (docs/plan_de_accion.md, seccion 0).
-- Cada consulta se corre sola en DBeaver y se exporta con: clic derecho en el resultado >
-- Exportar datos > CSV, separador coma, con encabezado. Guardar en datos/crudos/ con el nombre indicado.
-- Todas son de solo lectura (usan WITH, no tablas temporales).
--
-- OJO: estas consultas aplican una version SIMPLIFICADA de la limpieza de analisis_etapas.py
-- (sin AMB, sin etapas abiertas, sin copias de la misma persona, sin duplicados exactos, sin episodios
-- cuyas etapas ya estan en otra visita). Sirven para verificar el pipeline contra la base, no para
-- reemplazarlo. Cada una trae un "valor esperado": si no coincide, hay que entender por que antes de seguir.

SET statement_timeout = 0;   -- sin limite de tiempo solo para esta sesion

-- =====================================================================
-- Q0) q0_reconciliacion.csv   (rapida, ~1-3 min, 10 filas)
--     Cuadra los conteos basicos de la base con lo que dice CLAUDE.md.
--     Probada con los CSV locales (DuckDB): todo coincide salvo "copias de la misma persona",
--     que da 238.632 y no 238.674 (la diferencia de 42 viene de las cadenas de copias con
--     desfase 11.280-11.286, que esta consulta no usa). Esa diferencia es aceptable.
-- =====================================================================
WITH offs(k) AS (
    VALUES (1746478),(1757764),(1746479),(1746480),(1746481),(1746482),
           (1746483),(1746484),(1746485),(1746486),(1746487),(1746488),(1746489)
),
copias AS (
    SELECT DISTINCT vo.visit_occurrence_id
    FROM uninorte_omop.visit_occurrence vo
    JOIN offs o ON TRUE
    JOIN uninorte_omop.visit_occurrence w
      ON w.visit_occurrence_id = vo.visit_occurrence_id - o.k
     AND w.person_id = vo.person_id
)
SELECT 'visitas (visit_occurrence)' AS metrica,
       COUNT(*)::bigint AS valor, 1706001::bigint AS esperado
FROM uninorte_omop.visit_occurrence
UNION ALL
SELECT 'etapas (visit_detail)', COUNT(*), 3281613
FROM uninorte_omop.visit_detail
UNION ALL
SELECT 'etapas AMB (581479)', COUNT(*), 1539340
FROM uninorte_omop.visit_detail WHERE visit_detail_concept_id = 581479
UNION ALL
SELECT 'etapas abiertas no AMB (fin con milisegundos o vacio)', COUNT(*), 2053
FROM uninorte_omop.visit_detail
WHERE visit_detail_concept_id <> 581479
  AND (visit_detail_end_datetime IS NULL
       OR visit_detail_end_datetime <> date_trunc('second', visit_detail_end_datetime))
UNION ALL
SELECT 'etapas que quedan (ER, TU, HOSP cerradas por segundo)', COUNT(*), 1740220
FROM uninorte_omop.visit_detail
WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
  AND visit_detail_end_datetime IS NOT NULL
  AND visit_detail_end_datetime = date_trunc('second', visit_detail_end_datetime)
UNION ALL
SELECT 'etapas ER (9203)', COUNT(*), 481481
FROM uninorte_omop.visit_detail WHERE visit_detail_concept_id = 9203
UNION ALL
SELECT 'etapas TU (3045729)', COUNT(*), 1152191
FROM uninorte_omop.visit_detail WHERE visit_detail_concept_id = 3045729
UNION ALL
SELECT 'etapas HOSP (9201)', COUNT(*), 108601
FROM uninorte_omop.visit_detail WHERE visit_detail_concept_id = 9201
UNION ALL
SELECT 'visitas copia de la misma persona', COUNT(*), 238674
FROM copias
UNION ALL
SELECT 'primera etapa desde 2020 (aaaamm)',
       (EXTRACT(YEAR FROM MIN(visit_detail_start_datetime)) * 100
        + EXTRACT(MONTH FROM MIN(visit_detail_start_datetime)))::bigint, 202301
FROM uninorte_omop.visit_detail
WHERE visit_detail_start_datetime >= DATE '2020-01-01';

-- =====================================================================
-- Q1) q1_huecos_por_par.csv   (~3-8 min, unas 60 filas)
--     Hueco entre una etapa y la siguiente de la misma visita, por par de tipos.
--     Responde: las etapas van pegadas? en que par esta el tiempo muerto?
--     Valor esperado: la gran mayoria de los pares cae en "0 (pegadas, <=1 s)";
--     TU > HOSP: ~25 % de los PARES con mas de 1 h (esta consulta no separa replicas). Medido por
--     EPISODIO hospitalizado, el hueco antes de la cama es > 1 h en ~19 % (Q3b, control 14).
--     Probada con los CSV locales: ER > TU 99 % pegadas; TU > HOSP 74 % pegadas y ~25 % con
--     mas de 1 h; y TU > TU tiene ~11 mil huecos de 1 a 24 h (candidato a segmento nuevo).
-- =====================================================================
WITH offs(k) AS (
    VALUES (1746478),(1757764),(1746479),(1746480),(1746481),(1746482),
           (1746483),(1746484),(1746485),(1746486),(1746487),(1746488),(1746489)
),
copias AS (
    SELECT DISTINCT vo.visit_occurrence_id
    FROM uninorte_omop.visit_occurrence vo
    JOIN offs o ON TRUE
    JOIN uninorte_omop.visit_occurrence w
      ON w.visit_occurrence_id = vo.visit_occurrence_id - o.k
     AND w.person_id = vo.person_id
),
et AS (
    SELECT DISTINCT
           vd.visit_occurrence_id,
           CASE vd.visit_detail_concept_id WHEN 9203 THEN 'ER'
                                           WHEN 3045729 THEN 'TU'
                                           ELSE 'HOSP' END AS etapa,
           vd.visit_detail_start_datetime AS ini,
           vd.visit_detail_end_datetime   AS fin
    FROM uninorte_omop.visit_detail vd
    WHERE vd.visit_detail_concept_id IN (9203, 3045729, 9201)
      AND vd.visit_detail_end_datetime IS NOT NULL
      AND vd.visit_detail_end_datetime = date_trunc('second', vd.visit_detail_end_datetime)
      AND NOT EXISTS (SELECT 1 FROM copias c WHERE c.visit_occurrence_id = vd.visit_occurrence_id)
),
con_prev AS (
    SELECT visit_occurrence_id, etapa, ini,
           LAG(etapa) OVER w AS etapa_prev,
           MAX(fin)   OVER (PARTITION BY visit_occurrence_id ORDER BY ini, fin
                            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS fin_prev
    FROM et
    WINDOW w AS (PARTITION BY visit_occurrence_id ORDER BY ini, fin)
),
h AS (
    SELECT etapa_prev || ' > ' || etapa AS par,
           EXTRACT(EPOCH FROM (ini - fin_prev)) / 3600.0 AS hueco_h
    FROM con_prev
    WHERE fin_prev IS NOT NULL
)
SELECT par,
       CASE WHEN hueco_h <= 1.0/3600 THEN '1) pegadas (<= 1 s o solape)'
            WHEN hueco_h <= 1.0/60   THEN '2) hasta 1 min'
            WHEN hueco_h <= 1        THEN '3) 1 min a 1 h'
            WHEN hueco_h <= 6        THEN '4) 1 a 6 h'
            WHEN hueco_h <= 24       THEN '5) 6 a 24 h'
            WHEN hueco_h <= 168      THEN '6) 1 a 7 d'
            ELSE                          '7) mas de 7 d (corte de episodio)' END AS tramo,
       COUNT(*) AS n
FROM h
GROUP BY 1, 2
ORDER BY 1, 2;

-- =====================================================================
-- Q2) q2_duraciones_por_tipo_anio.csv   (~2-5 min, ~16 filas)
--     Por tipo de etapa y anio: cuantas, cuantas tienen inicio = fin, y percentiles de las que si
--     tienen duracion. Valor esperado: TU con inicio = fin: 2023 41,6 %, 2024 38,4 %, 2025 35,8 %,
--     2026 36,6 %; HOSP mediana ~46 h. La mediana de TU aqui (~3,3 h) es solo de las etapas que
--     SI tienen duracion; la de 1,2 h de CLAUDE.md incluye las de duracion cero.
--     Probada con los CSV locales: coincide (TU 41,6 / 38,4 / 35,8 / 36,8 %).
-- =====================================================================
SELECT CASE vd.visit_detail_concept_id WHEN 9203 THEN 'ER'
                                       WHEN 3045729 THEN 'TU'
                                       ELSE 'HOSP' END AS etapa,
       EXTRACT(YEAR FROM vd.visit_detail_start_datetime)::int AS anio,
       COUNT(*) AS n,
       COUNT(*) FILTER (WHERE vd.visit_detail_end_datetime <= vd.visit_detail_start_datetime) AS n_inicio_igual_fin,
       ROUND(100.0 * COUNT(*) FILTER (WHERE vd.visit_detail_end_datetime <= vd.visit_detail_start_datetime)
             / COUNT(*), 1) AS pct_inicio_igual_fin,
       ROUND((percentile_cont(0.25) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (vd.visit_detail_end_datetime - vd.visit_detail_start_datetime)) / 3600.0)
              FILTER (WHERE vd.visit_detail_end_datetime > vd.visit_detail_start_datetime))::numeric, 2) AS p25_h,
       ROUND((percentile_cont(0.50) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (vd.visit_detail_end_datetime - vd.visit_detail_start_datetime)) / 3600.0)
              FILTER (WHERE vd.visit_detail_end_datetime > vd.visit_detail_start_datetime))::numeric, 2) AS mediana_h,
       ROUND((percentile_cont(0.75) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (vd.visit_detail_end_datetime - vd.visit_detail_start_datetime)) / 3600.0)
              FILTER (WHERE vd.visit_detail_end_datetime > vd.visit_detail_start_datetime))::numeric, 2) AS p75_h,
       ROUND((percentile_cont(0.90) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (vd.visit_detail_end_datetime - vd.visit_detail_start_datetime)) / 3600.0)
              FILTER (WHERE vd.visit_detail_end_datetime > vd.visit_detail_start_datetime))::numeric, 2) AS p90_h
FROM uninorte_omop.visit_detail vd
WHERE vd.visit_detail_concept_id IN (9203, 3045729, 9201)
  AND vd.visit_detail_end_datetime IS NOT NULL
  AND vd.visit_detail_end_datetime = date_trunc('second', vd.visit_detail_end_datetime)
GROUP BY 1, 2
ORDER BY 1, 2;

-- =====================================================================
-- Q3) q3_episodios.csv   (la central; ~5-15 min; ~340 mil filas, ~40 MB)
--     Una fila por episodio con lo necesario para segmentos, referencias, carga y camas.
--     Lo que hace, en orden: quita copias de la misma persona (sus etapas pasan a la raiz),
--     quita duplicados exactos y etapas de duracion cero repetidas, corta episodios con huecos
--     de mas de 168 h, quita episodios cuyas etapas ya estan en una visita de id menor,
--     y calcula llegadas de las 6 y 24 h previas.
--     Valor esperado: ~337 mil episodios; mediana de (ini_hosp - ini) ~22 h en los que tienen HOSP.
--     Probada con los CSV locales: 336.844 episodios (pipeline: 337.194), 35.322 con HOSP,
--     espera mediana 21,4 h (pipeline: 22,4 h con n = 34.537). Diferencias pequenas por la
--     limpieza simplificada.
--     No trae diagnosticos ni laboratorios: esos ya estan en datos/crudos (consultas_semana1.sql).
-- =====================================================================
WITH offs(k) AS (
    VALUES (1746478),(1757764),(1746479),(1746480),(1746481),(1746482),
           (1746483),(1746484),(1746485),(1746486),(1746487),(1746488),(1746489)
),
-- copia -> original (misma persona). Si hay varias, se queda la de mayor desfase menor id.
mapa1 AS (
    SELECT vo.visit_occurrence_id AS copia,
           MIN(vo.visit_occurrence_id - o.k) AS orig
    FROM uninorte_omop.visit_occurrence vo
    JOIN offs o ON TRUE
    JOIN uninorte_omop.visit_occurrence w
      ON w.visit_occurrence_id = vo.visit_occurrence_id - o.k
     AND w.person_id = vo.person_id
    GROUP BY vo.visit_occurrence_id
),
-- se sigue la cadena copia de copia hasta 3 niveles
mapa AS (
    SELECT m1.copia,
           COALESCE(m3.orig, m2.orig, m1.orig) AS raiz
    FROM mapa1 m1
    LEFT JOIN mapa1 m2 ON m2.copia = m1.orig
    LEFT JOIN mapa1 m3 ON m3.copia = m2.orig
),
et0 AS (
    SELECT COALESCE(m.raiz, vd.visit_occurrence_id) AS visita,
           vd.visit_detail_id,
           vd.visit_detail_concept_id AS concepto,
           CASE vd.visit_detail_concept_id WHEN 9203 THEN 'ER'
                                           WHEN 3045729 THEN 'TU'
                                           ELSE 'HOSP' END AS etapa,
           vd.visit_detail_start_datetime AS ini,
           vd.visit_detail_end_datetime   AS fin
    FROM uninorte_omop.visit_detail vd
    LEFT JOIN mapa m ON m.copia = vd.visit_occurrence_id
    WHERE vd.visit_detail_concept_id IN (9203, 3045729, 9201)
      AND vd.visit_detail_end_datetime IS NOT NULL
      AND vd.visit_detail_end_datetime = date_trunc('second', vd.visit_detail_end_datetime)
),
-- duplicados exactos (misma visita, tipo, inicio y fin) y etapas de duracion cero cuando la misma
-- etapa (mismo tipo e inicio) tiene una version cerrada
et1 AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY visita, concepto, ini, fin ORDER BY visit_detail_id) AS rn,
           BOOL_OR(fin > ini) OVER (PARTITION BY visita, concepto, ini) AS hay_cerrada
    FROM et0
),
et2 AS (
    SELECT visita, visit_detail_id, concepto, etapa, ini, fin
    FROM et1
    WHERE rn = 1 AND NOT (fin <= ini AND hay_cerrada)
),
-- episodios: corte cuando pasan mas de 168 h sin ninguna etapa
et3 AS (
    SELECT *,
           MAX(fin) OVER (PARTITION BY visita ORDER BY ini, visit_detail_id
                          ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS fin_prev
    FROM et2
),
et4 AS (
    SELECT *,
           SUM(CASE WHEN ini - fin_prev > INTERVAL '168 hours' THEN 1 ELSE 0 END)
               OVER (PARTITION BY visita ORDER BY ini, visit_detail_id ROWS UNBOUNDED PRECEDING) AS episodio,
           -- dueno de la etapa: la visita de menor id que tiene la misma etapa exacta
           MIN(visita) OVER (PARTITION BY concepto, ini, fin) AS dueno
    FROM et3
),
ep AS (
    SELECT visita, episodio,
           MIN(ini) AS ini,
           MAX(fin) AS fin_max,
           MIN(ini) FILTER (WHERE etapa = 'HOSP') AS ini_hosp,
           MAX(fin) FILTER (WHERE etapa = 'HOSP') AS fin_hosp,
           -- fin mas tardio de las etapas que empiezan antes de la primera HOSP
           MAX(fin) FILTER (WHERE etapa <> 'HOSP') AS fin_no_hosp,
           COUNT(*) FILTER (WHERE etapa = 'ER')   AS n_er,
           COUNT(*) FILTER (WHERE etapa = 'TU')   AS n_tu,
           COUNT(*) FILTER (WHERE etapa = 'HOSP') AS n_hosp,
           BOOL_OR(etapa <> 'ER' AND fin > ini)   AS con_tiempo,
           (ARRAY_AGG(fin > ini ORDER BY ini DESC, visit_detail_id DESC)
                FILTER (WHERE etapa <> 'ER'))[1]  AS ultima_cerrada,
           -- episodio redundante: todas sus etapas (o todas las TU/HOSP) ya estan en otra visita
           (BOOL_AND(visita <> dueno)
            OR (BOOL_OR(etapa <> 'ER')
                AND BOOL_AND(visita <> dueno OR etapa = 'ER'))) AS todas_repetidas
    FROM et4
    GROUP BY visita, episodio
),
ep_ok AS (
    SELECT * FROM ep WHERE NOT todas_repetidas
),
-- primera hospitalizacion: fin de lo que estaba antes (para medir el hueco previo)
hueco AS (
    SELECT e.visita, e.episodio,
           MAX(x.fin) AS fin_previo_hosp
    FROM ep_ok e
    JOIN et4 x ON x.visita = e.visita AND x.episodio = e.episodio
              AND e.ini_hosp IS NOT NULL AND x.ini < e.ini_hosp
    GROUP BY e.visita, e.episodio
),
base AS (
    SELECT e.visita AS visit_occurrence_id,
           e.episodio,
           vo.person_id,
           vo.visit_concept_id,
           e.ini, e.fin_max, e.ini_hosp, e.fin_hosp, h.fin_previo_hosp,
           e.n_er, e.n_tu, e.n_hosp, e.con_tiempo, e.ultima_cerrada,
           p.year_of_birth, p.gender_concept_id
    FROM ep_ok e
    JOIN uninorte_omop.visit_occurrence vo ON vo.visit_occurrence_id = e.visita
    LEFT JOIN uninorte_omop.person p ON p.person_id = vo.person_id
    LEFT JOIN hueco h ON h.visita = e.visita AND h.episodio = e.episodio
)
SELECT b.*,
       COUNT(*) OVER (ORDER BY b.ini
                      RANGE BETWEEN INTERVAL '6 hours'  PRECEDING AND INTERVAL '1 second' PRECEDING) AS llegadas_6h_previas,
       COUNT(*) OVER (ORDER BY b.ini
                      RANGE BETWEEN INTERVAL '24 hours' PRECEDING AND INTERVAL '1 second' PRECEDING) AS llegadas_24h_previas
FROM base b
ORDER BY b.ini;

-- =====================================================================
-- Q4) q4_ocupacion_por_hora.csv   (~2-5 min; ~30 mil filas)
--     Pacientes en cama (HOSP) y en TU con duracion, al FINAL de cada hora.
--     Para "ocupacion al llegar" a la hora H usar la fila de la hora H-1.
--     Se cuentan intervalos distintos (inicio, fin) para no contar dos veces un registro replicado.
--     Valor esperado: media ~100 (cuartiles de ocupacion 59-117 en CLAUDE.md), feb-2023 a may-2026;
--     antes de feb-2023 es menor porque los ingresados en 2022 no estan en la base.
--     ALERTA (probada con los CSV locales): sin quitar intervalos repetidos la media seria ~280;
--     con ellos ~100. La ocupacion del pipeline (~146) y la ley de Little (27,7 ingresos/dia x 5,2 dias
--     = ~144) cuentan dos veces las estancias replicadas entre dos personas (el 41 % de los episodios
--     hospitalizados tiene un "gemelo" con el mismo inicio y fin de cama). Contando cada estancia una
--     sola vez salen ~113 camas y ~22 ingresos/dia. El nivel absoluto (100-113) depende del metodo;
--     para comparar contra la carga sirve la variacion, no el nivel.
-- =====================================================================
WITH iv AS (
    SELECT DISTINCT vd.visit_detail_concept_id AS concepto,
           vd.visit_detail_start_datetime AS ini,
           vd.visit_detail_end_datetime   AS fin
    FROM uninorte_omop.visit_detail vd
    WHERE vd.visit_detail_concept_id IN (3045729, 9201)
      AND vd.visit_detail_end_datetime IS NOT NULL
      AND vd.visit_detail_end_datetime = date_trunc('second', vd.visit_detail_end_datetime)
      AND vd.visit_detail_end_datetime > vd.visit_detail_start_datetime
),
ev AS (
    SELECT date_trunc('hour', ini) AS hora, concepto,  1 AS d FROM iv
    UNION ALL
    SELECT date_trunc('hour', fin) AS hora, concepto, -1 AS d FROM iv
),
ev_h AS (
    SELECT hora,
           SUM(d) FILTER (WHERE concepto = 9201)    AS delta_hosp,
           SUM(d) FILTER (WHERE concepto = 3045729) AS delta_tu
    FROM ev
    GROUP BY hora
),
grid AS (
    SELECT g.hora
    FROM generate_series(TIMESTAMP '2023-01-01 00:00:00',
                         TIMESTAMP '2026-07-31 23:00:00',
                         INTERVAL '1 hour') AS g(hora)
)
SELECT g.hora,
       SUM(COALESCE(e.delta_hosp, 0)) OVER (ORDER BY g.hora) AS ocup_hosp_fin_hora,
       SUM(COALESCE(e.delta_tu, 0))   OVER (ORDER BY g.hora) AS ocup_tu_fin_hora
FROM grid g
LEFT JOIN ev_h e ON e.hora = g.hora
ORDER BY g.hora;

-- =====================================================================
-- Q3b) q3b_resumen.csv   (misma carga que Q3, ~5-15 min, pero devuelve ~23 filas)
--      Version de Q3 que NO exporta los 337 mil episodios: devuelve solo controles
--      agregados. Sirve para comprobar que Q3 es creible cuando la exportacion completa falla.
--      "esperado" sale de la prueba local con los CSV (puede variar ~1-2 %).
-- =====================================================================
SET statement_timeout = 0;

WITH offs(k) AS (
    VALUES (1746478),(1757764),(1746479),(1746480),(1746481),(1746482),
           (1746483),(1746484),(1746485),(1746486),(1746487),(1746488),(1746489)
),

mapa1 AS (
    SELECT vo.visit_occurrence_id AS copia,
           MIN(vo.visit_occurrence_id - o.k) AS orig
    FROM uninorte_omop.visit_occurrence vo
    JOIN offs o ON TRUE
    JOIN uninorte_omop.visit_occurrence w
      ON w.visit_occurrence_id = vo.visit_occurrence_id - o.k
     AND w.person_id = vo.person_id
    GROUP BY vo.visit_occurrence_id
),

mapa AS (
    SELECT m1.copia,
           COALESCE(m3.orig, m2.orig, m1.orig) AS raiz
    FROM mapa1 m1
    LEFT JOIN mapa1 m2 ON m2.copia = m1.orig
    LEFT JOIN mapa1 m3 ON m3.copia = m2.orig
),
et0 AS (
    SELECT COALESCE(m.raiz, vd.visit_occurrence_id) AS visita,
           vd.visit_detail_id,
           vd.visit_detail_concept_id AS concepto,
           CASE vd.visit_detail_concept_id WHEN 9203 THEN 'ER'
                                           WHEN 3045729 THEN 'TU'
                                           ELSE 'HOSP' END AS etapa,
           vd.visit_detail_start_datetime AS ini,
           vd.visit_detail_end_datetime   AS fin
    FROM uninorte_omop.visit_detail vd
    LEFT JOIN mapa m ON m.copia = vd.visit_occurrence_id
    WHERE vd.visit_detail_concept_id IN (9203, 3045729, 9201)
      AND vd.visit_detail_end_datetime IS NOT NULL
      AND vd.visit_detail_end_datetime = date_trunc('second', vd.visit_detail_end_datetime)
),


et1 AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY visita, concepto, ini, fin ORDER BY visit_detail_id) AS rn,
           BOOL_OR(fin > ini) OVER (PARTITION BY visita, concepto, ini) AS hay_cerrada
    FROM et0
),
et2 AS (
    SELECT visita, visit_detail_id, concepto, etapa, ini, fin
    FROM et1
    WHERE rn = 1 AND NOT (fin <= ini AND hay_cerrada)
),

et3 AS (
    SELECT *,
           MAX(fin) OVER (PARTITION BY visita ORDER BY ini, visit_detail_id
                          ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS fin_prev
    FROM et2
),
et4 AS (
    SELECT *,
           SUM(CASE WHEN ini - fin_prev > INTERVAL '168 hours' THEN 1 ELSE 0 END)
               OVER (PARTITION BY visita ORDER BY ini, visit_detail_id ROWS UNBOUNDED PRECEDING) AS episodio,
           
           MIN(visita) OVER (PARTITION BY concepto, ini, fin) AS dueno
    FROM et3
),
ep AS (
    SELECT visita, episodio,
           MIN(ini) AS ini,
           MAX(fin) AS fin_max,
           MIN(ini) FILTER (WHERE etapa = 'HOSP') AS ini_hosp,
           MAX(fin) FILTER (WHERE etapa = 'HOSP') AS fin_hosp,
           
           MAX(fin) FILTER (WHERE etapa <> 'HOSP') AS fin_no_hosp,
           COUNT(*) FILTER (WHERE etapa = 'ER')   AS n_er,
           COUNT(*) FILTER (WHERE etapa = 'TU')   AS n_tu,
           COUNT(*) FILTER (WHERE etapa = 'HOSP') AS n_hosp,
           BOOL_OR(etapa <> 'ER' AND fin > ini)   AS con_tiempo,
           (ARRAY_AGG(fin > ini ORDER BY ini DESC, visit_detail_id DESC)
                FILTER (WHERE etapa <> 'ER'))[1]  AS ultima_cerrada,
           
           (BOOL_AND(visita <> dueno)
            OR (BOOL_OR(etapa <> 'ER')
                AND BOOL_AND(visita <> dueno OR etapa = 'ER'))) AS todas_repetidas
    FROM et4
    GROUP BY visita, episodio
),
ep_ok AS (
    SELECT * FROM ep WHERE NOT todas_repetidas
),

hueco AS (
    SELECT e.visita, e.episodio,
           MAX(x.fin) AS fin_previo_hosp
    FROM ep_ok e
    JOIN et4 x ON x.visita = e.visita AND x.episodio = e.episodio
              AND e.ini_hosp IS NOT NULL AND x.ini < e.ini_hosp
    GROUP BY e.visita, e.episodio
),
base AS (
    SELECT e.visita AS visit_occurrence_id,
           e.episodio,
           vo.person_id,
           vo.visit_concept_id,
           e.ini, e.fin_max, e.ini_hosp, e.fin_hosp, h.fin_previo_hosp,
           e.n_er, e.n_tu, e.n_hosp, e.con_tiempo, e.ultima_cerrada,
           p.year_of_birth, p.gender_concept_id
    FROM ep_ok e
    JOIN uninorte_omop.visit_occurrence vo ON vo.visit_occurrence_id = e.visita
    LEFT JOIN uninorte_omop.person p ON p.person_id = vo.person_id
    LEFT JOIN hueco h ON h.visita = e.visita AND h.episodio = e.episodio
),
q3 AS (
    SELECT b.*,
           COUNT(*) OVER (ORDER BY b.ini
                          RANGE BETWEEN INTERVAL '6 hours'  PRECEDING AND INTERVAL '1 second' PRECEDING) AS llegadas_6h_previas
    FROM base b
),
x AS (
    SELECT q3.*,
           EXTRACT(EPOCH FROM (ini_hosp - ini)) / 3600.0 AS espera_h,
           EXTRACT(EPOCH FROM (ini_hosp - fin_previo_hosp)) / 3600.0 AS hueco_h
    FROM q3
)
SELECT '01 episodios (filas)' AS control, COUNT(*)::numeric AS valor, 336844::numeric AS esperado FROM x
UNION ALL SELECT '02 visitas distintas', COUNT(DISTINCT visit_occurrence_id), NULL FROM x
UNION ALL SELECT '03 episodios repetidos (visita, episodio): debe ser 0',
       COUNT(*) - COUNT(DISTINCT (visit_occurrence_id, episodio)), 0 FROM x
UNION ALL SELECT '04 visitas partidas (con mas de un episodio restante)',
       COUNT(*), 575 FROM (SELECT visit_occurrence_id FROM x GROUP BY 1 HAVING COUNT(*) > 1) t
UNION ALL SELECT '05 episodios con hospitalizacion', COUNT(*) FILTER (WHERE ini_hosp IS NOT NULL), 35322 FROM x
UNION ALL SELECT '06 espera de cama p50 (h)', ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY espera_h))::numeric, 1), 21.4 FROM x WHERE ini_hosp IS NOT NULL
UNION ALL SELECT '07 espera de cama p75 (h)', ROUND((percentile_cont(0.75) WITHIN GROUP (ORDER BY espera_h))::numeric, 1), 41.2 FROM x WHERE ini_hosp IS NOT NULL
UNION ALL SELECT '08 espera de cama p90 (h)', ROUND((percentile_cont(0.9) WITHIN GROUP (ORDER BY espera_h))::numeric, 1), 76.8 FROM x WHERE ini_hosp IS NOT NULL
UNION ALL SELECT '09 esperas negativas: debe ser 0', COUNT(*) FILTER (WHERE espera_h < 0), 0 FROM x
UNION ALL SELECT '10 fin_hosp antes que ini_hosp: debe ser 0', COUNT(*) FILTER (WHERE fin_hosp < ini_hosp), 0 FROM x
UNION ALL SELECT '11 etapas previas que terminan despues de ini_hosp (hueco < 0)', COUNT(*) FILTER (WHERE hueco_h < 0), NULL FROM x
UNION ALL SELECT '12 esperas de cama de mas de 168 h', COUNT(*) FILTER (WHERE espera_h > 168), 492 FROM x
UNION ALL SELECT '13 esperas de cama de mas de 2160 h', COUNT(*) FILTER (WHERE espera_h > 2160), NULL FROM x
UNION ALL SELECT '14 hospitalizados con hueco antes de cama > 1 h (%)',
       ROUND((100.0 * COUNT(*) FILTER (WHERE hueco_h > 1) / COUNT(*))::numeric, 1), 19.0 FROM x WHERE ini_hosp IS NOT NULL
UNION ALL SELECT '15 sin HOSP, con TU y duracion medida', COUNT(*) FILTER (WHERE n_hosp = 0 AND n_tu > 0 AND con_tiempo AND ultima_cerrada), NULL FROM x
UNION ALL SELECT '16 sin HOSP y con TU (total)', COUNT(*) FILTER (WHERE n_hosp = 0 AND n_tu > 0), NULL FROM x
UNION ALL SELECT '17 solo ER (n_tu = 0 y n_hosp = 0)', COUNT(*) FILTER (WHERE n_tu = 0 AND n_hosp = 0), NULL FROM x
UNION ALL SELECT '18 edades imposibles (anio 0, 1 o mas de 110 anios)',
       COUNT(*) FILTER (WHERE year_of_birth < 1900 OR EXTRACT(YEAR FROM ini) - year_of_birth > 110), NULL FROM x
UNION ALL SELECT '19 llegadas_6h p50', (percentile_cont(0.5) WITHIN GROUP (ORDER BY llegadas_6h_previas))::numeric, 77 FROM x
UNION ALL SELECT '20 episodios 2023', COUNT(*) FILTER (WHERE EXTRACT(YEAR FROM ini) = 2023), NULL FROM x
UNION ALL SELECT '21 episodios 2024', COUNT(*) FILTER (WHERE EXTRACT(YEAR FROM ini) = 2024), NULL FROM x
UNION ALL SELECT '22 episodios 2025', COUNT(*) FILTER (WHERE EXTRACT(YEAR FROM ini) = 2025), NULL FROM x
UNION ALL SELECT '23 episodios 2026', COUNT(*) FILTER (WHERE EXTRACT(YEAR FROM ini) = 2026), NULL FROM x
ORDER BY 1;
