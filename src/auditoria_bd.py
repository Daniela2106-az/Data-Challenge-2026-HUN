"""
auditoria_bd.py  -  version 1 (2-nov-2026)
AUDITORIA de SOLO LECTURA contra la base (esquema uninorte_omop) para comprobar con la fuente original lo que hemos concluido a partir de los CSV exportados.
Se lanza SOLA antes de conectar la VPN (con la VPN activa el computador pierde el internet normal y la sesion de Claude Code): espera a que el servidor responda,
corre las consultas de la mas barata a la mas pesada, guarda cada resultado en CSV, anota el avance en un log y avisa con una notificacion de macOS al terminar.

QUE COMPRUEBA (cada bloque responde una duda concreta)
  A. Fechas y cortes: ultimo dato de cada tabla, fechas futuras, filas por mes (la base esta completa? el recorte de mayo de 2026 es real?).
  B. Estructura del registro: etapas ER, TU y HOSP por mes y por dia alrededor del 29-abr-2026; visitas con solo la etapa ER (el cambio de registro).
  C. Camas (la pregunta de por que la ocupacion media es casi igual al total de camas):
       - calidad de las etapas HOSP (sin fin, sin duracion, con milisegundos, de mas de 30 dias, por anio);
       - cuanto se repite cada intervalo (filas, intervalos por visita, intervalos distintos);
       - intervalos HOSP de la MISMA persona que se solapan (la misma persona en dos camas a la vez);
       - estancia por estancia, el ultimo laboratorio dentro de la estancia (para ver si el alta se registra mucho despues de la ultima actividad);
       - horas redondas en inicio y fin (marcas administrativas en vez de horas reales);
       - hora del dia de ingresos y altas por estancia distinta (valida el 62 % de altas de 14 a 19 h sin pasar por nuestro pipeline).
  D. Cifras clave recalculadas directo de la base: espera de cama (mediana, p75, p90) y estancias distintas por mes (ingresos por dia).
  E. Llegadas: visitas contra personas distintas por dia (cuantas replicas hay), copias por desfase de id (validacion de CLAUDE.md 4.1), llegadas por hora.
  F. Diagnosticos: filas con y sin codigo por mes (2023 a 2026), fechas futuras y hora del diagnostico frente a la visita (muestra).
  G. Personas: anios de nacimiento imposibles y sexo.

          python3 src/auditoria_bd.py --esperar 120 --lote 3 (lote 3: actividad por estancia: dias con laboratorio, UCI y nutricion hospitalaria)
          python3 src/auditoria_bd.py --esperar 120 --lote 4 (lote 4: persona real de cada visita con hospitalizacion segun diagnosticos, laboratorios y procedimientos)
USO       python3 src/auditoria_bd.py --esperar 120          (lote 1, ya corrido el 2-nov: 23 consultas, 4,7 min)
          python3 src/auditoria_bd.py --esperar 120 --lote 2 (lote 2: visitas con y sin etapas, personas, espera con episodios, laboratorios y diagnosticos por estancia)
          python3 src/auditoria_bd.py --probar-local         (prueba la sintaxis de las consultas con DuckDB y tablas vacias; no usa la base)
SALIDAS   datos/crudos/auditoria_bd/*.csv y auditoria.log (todo fuera de git)
"""
import argparse
import datetime
import json
import re
import socket
import subprocess
import time
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "datos" / "crudos" / "auditoria_bd"
SALIDA.mkdir(parents=True, exist_ok=True)
LOG = SALIDA / "auditoria.log"
S = "uninorte_omop"

# visita-etapa: conceptos 9203 (ER), 3045729 (TU), 9201 (HOSP), 581479 (AMB)
HOSP_CERRADA = (f"vd.visit_detail_concept_id = 9201 AND vd.visit_detail_end_datetime > vd.visit_detail_start_datetime "
                f"AND vd.visit_detail_end_datetime = date_trunc('second', vd.visit_detail_end_datetime)")

CONSULTAS_1 = [
    # ---------------------------------------------------------------- A. fechas y cortes
    ("A01_fechas_visitas_etapas", f"""
        SELECT 'visit_occurrence' AS tabla, min(visit_start_datetime) AS primera, max(visit_start_datetime) AS ultima,
               count(*) FILTER (WHERE visit_start_datetime > now()) AS futuras, count(*) AS n FROM {S}.visit_occurrence
        UNION ALL
        SELECT 'visit_detail', min(visit_detail_start_datetime), max(visit_detail_start_datetime),
               count(*) FILTER (WHERE visit_detail_start_datetime > now()), count(*) FROM {S}.visit_detail"""),
    ("A02_visitas_por_mes_tipo", f"""
        SELECT date_trunc('month', visit_start_datetime)::date AS mes, visit_concept_id, count(*) AS visitas, count(DISTINCT person_id) AS personas
        FROM {S}.visit_occurrence GROUP BY 1, 2 ORDER BY 1, 2"""),
    ("A03_conceptos_nombres", f"""
        SELECT concept_id, concept_name, domain_id, vocabulary_id FROM {S}.concept WHERE concept_id IN (9203, 3045729, 9201, 581479, 9202, 0)"""),
    # ---------------------------------------------------------------- B. estructura del registro
    ("B01_etapas_por_mes_concepto", f"""
        SELECT date_trunc('month', visit_detail_start_datetime)::date AS mes, visit_detail_concept_id AS concepto, count(*) AS etapas,
               count(*) FILTER (WHERE visit_detail_end_datetime > visit_detail_start_datetime) AS con_fin, count(DISTINCT visit_occurrence_id) AS visitas
        FROM {S}.visit_detail GROUP BY 1, 2 ORDER BY 1, 2"""),
    ("B02_etapas_diarias_alrededor_del_quiebre", f"""
        SELECT visit_detail_start_datetime::date AS dia, visit_detail_concept_id AS concepto, count(*) AS etapas, count(DISTINCT visit_occurrence_id) AS visitas
        FROM {S}.visit_detail WHERE visit_detail_start_datetime >= '2026-04-10' AND visit_detail_start_datetime < '2026-05-25'
        GROUP BY 1, 2 ORDER BY 1, 2"""),
    ("B03_visitas_solo_ER_por_mes", f"""
        WITH v AS (SELECT visit_occurrence_id, min(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9203) AS ini_er,
                          bool_or(visit_detail_concept_id IN (3045729, 9201)) AS tiene_atencion
                   FROM {S}.visit_detail GROUP BY 1 HAVING bool_or(visit_detail_concept_id = 9203))
        SELECT date_trunc('month', ini_er)::date AS mes, count(*) AS visitas_con_ER, count(*) FILTER (WHERE NOT tiene_atencion) AS solo_ER FROM v GROUP BY 1 ORDER BY 1"""),
    ("B04_visitas_solo_ER_diario_quiebre", f"""
        WITH v AS (SELECT visit_occurrence_id, min(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9203) AS ini_er,
                          bool_or(visit_detail_concept_id IN (3045729, 9201)) AS tiene_atencion
                   FROM {S}.visit_detail GROUP BY 1 HAVING bool_or(visit_detail_concept_id = 9203))
        SELECT ini_er::date AS dia, count(*) AS visitas_con_ER, count(*) FILTER (WHERE NOT tiene_atencion) AS solo_ER FROM v
        WHERE ini_er >= '2026-04-10' AND ini_er < '2026-05-25' GROUP BY 1 ORDER BY 1"""),
    # ---------------------------------------------------------------- C. camas
    ("C01_hosp_calidad_por_anio", f"""
        SELECT extract(year FROM visit_detail_start_datetime)::int AS anio, count(*) AS etapas,
               count(*) FILTER (WHERE visit_detail_end_datetime IS NULL) AS fin_nulo,
               count(*) FILTER (WHERE visit_detail_end_datetime <= visit_detail_start_datetime) AS sin_duracion,
               count(*) FILTER (WHERE visit_detail_end_datetime <> date_trunc('second', visit_detail_end_datetime)) AS fin_con_milisegundos,
               count(*) FILTER (WHERE visit_detail_end_datetime > visit_detail_start_datetime + interval '30 days') AS mas_de_30_dias,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM (visit_detail_end_datetime - visit_detail_start_datetime)) / 3600) AS mediana_h
        FROM {S}.visit_detail WHERE visit_detail_concept_id = 9201 GROUP BY 1 ORDER BY 1"""),
    ("C02_hosp_repeticion_de_intervalos", f"""
        SELECT count(*) AS filas, count(DISTINCT visit_occurrence_id) AS visitas,
               (SELECT count(*) FROM (SELECT DISTINCT visit_occurrence_id, visit_detail_start_datetime, visit_detail_end_datetime FROM {S}.visit_detail vd WHERE {HOSP_CERRADA}) a) AS intervalos_por_visita,
               (SELECT count(*) FROM (SELECT DISTINCT visit_detail_start_datetime, visit_detail_end_datetime FROM {S}.visit_detail vd WHERE {HOSP_CERRADA}) b) AS intervalos_distintos
        FROM {S}.visit_detail WHERE visit_detail_concept_id = 9201"""),
    ("C03_tu_repeticion_de_intervalos", f"""
        SELECT (SELECT count(*) FROM {S}.visit_detail WHERE visit_detail_concept_id = 3045729 AND visit_detail_end_datetime > visit_detail_start_datetime) AS filas_cerradas,
               (SELECT count(*) FROM (SELECT DISTINCT visit_occurrence_id, visit_detail_start_datetime, visit_detail_end_datetime FROM {S}.visit_detail
                  WHERE visit_detail_concept_id = 3045729 AND visit_detail_end_datetime > visit_detail_start_datetime) a) AS intervalos_por_visita,
               (SELECT count(*) FROM (SELECT DISTINCT visit_detail_start_datetime, visit_detail_end_datetime FROM {S}.visit_detail
                  WHERE visit_detail_concept_id = 3045729 AND visit_detail_end_datetime > visit_detail_start_datetime) b) AS intervalos_distintos"""),
    ("C04_hosp_solapes_misma_persona", f"""
        WITH h AS (SELECT DISTINCT vo.person_id, vd.visit_detail_start_datetime AS ini, vd.visit_detail_end_datetime AS fin
                   FROM {S}.visit_detail vd JOIN {S}.visit_occurrence vo ON vo.visit_occurrence_id = vd.visit_occurrence_id WHERE {HOSP_CERRADA}),
             o AS (SELECT person_id, ini, fin, max(fin) OVER (PARTITION BY person_id ORDER BY ini, fin ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS fin_prev FROM h)
        SELECT extract(year FROM ini)::int AS anio, count(*) AS intervalos, count(*) FILTER (WHERE fin_prev > ini) AS solapan,
               sum(extract(epoch FROM (least(fin, fin_prev) - ini)) / 3600) FILTER (WHERE fin_prev > ini) AS horas_solapadas
        FROM o GROUP BY 1 ORDER BY 1"""),
    ("C05_hosp_horas_redondas", f"""
        SELECT count(*) AS etapas,
               count(*) FILTER (WHERE extract(minute FROM visit_detail_start_datetime) = 0 AND extract(second FROM visit_detail_start_datetime) = 0) AS inicio_en_punto,
               count(*) FILTER (WHERE extract(minute FROM visit_detail_end_datetime) = 0 AND extract(second FROM visit_detail_end_datetime) = 0) AS fin_en_punto,
               count(*) FILTER (WHERE extract(hour FROM visit_detail_end_datetime) = 0 AND extract(minute FROM visit_detail_end_datetime) = 0 AND extract(second FROM visit_detail_end_datetime) = 0) AS fin_a_medianoche
        FROM {S}.visit_detail vd WHERE {HOSP_CERRADA}"""),
    ("C06_ingresos_y_altas_por_hora_estancia_distinta", f"""
        WITH v AS (SELECT visit_occurrence_id, min(visit_detail_start_datetime) AS ini0, max(visit_detail_end_datetime) AS fin1
                   FROM {S}.visit_detail vd WHERE {HOSP_CERRADA} GROUP BY 1),
             d AS (SELECT DISTINCT ini0, fin1 FROM v WHERE fin1 < '2026-06-01')
        SELECT 'ingreso' AS tipo, extract(hour FROM ini0)::int AS hora, count(*) AS n FROM d GROUP BY 1, 2
        UNION ALL SELECT 'alta', extract(hour FROM fin1)::int, count(*) FROM d GROUP BY 1, 2 ORDER BY 1, 2"""),
    # ---------------------------------------------------------------- D. cifras clave directas
    ("D01_espera_de_cama_por_anio", f"""
        WITH s AS (SELECT visit_occurrence_id,
                          min(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id IN (9203, 3045729, 9201)) AS ini_vis,
                          min(visit_detail_start_datetime) FILTER (WHERE visit_detail_concept_id = 9201) AS ini_hosp,
                          max(visit_detail_end_datetime) FILTER (WHERE visit_detail_concept_id = 9201 AND visit_detail_end_datetime > visit_detail_start_datetime) AS fin_hosp
                   FROM {S}.visit_detail GROUP BY 1 HAVING bool_or(visit_detail_concept_id = 9201)),
             d AS (SELECT ini_hosp, fin_hosp, min(ini_vis) AS ini_vis FROM s GROUP BY ini_hosp, fin_hosp),
             e AS (SELECT extract(year FROM ini_hosp)::int AS anio, greatest(extract(epoch FROM (ini_hosp - ini_vis)) / 3600, 0) AS espera_h FROM d)
        SELECT anio, count(*) AS estancias,
               percentile_cont(0.25) WITHIN GROUP (ORDER BY espera_h) AS p25, percentile_cont(0.5) WITHIN GROUP (ORDER BY espera_h) AS p50,
               percentile_cont(0.75) WITHIN GROUP (ORDER BY espera_h) AS p75, percentile_cont(0.9) WITHIN GROUP (ORDER BY espera_h) AS p90,
               avg((espera_h > 24)::int) AS prop_mas_24h
        FROM e GROUP BY ROLLUP(anio) ORDER BY anio"""),
    ("D02_estancias_distintas_por_mes", f"""
        WITH s AS (SELECT visit_occurrence_id, min(visit_detail_start_datetime) AS ini_hosp,
                          max(visit_detail_end_datetime) FILTER (WHERE visit_detail_end_datetime > visit_detail_start_datetime) AS fin_hosp
                   FROM {S}.visit_detail WHERE visit_detail_concept_id = 9201 GROUP BY 1),
             d AS (SELECT DISTINCT ini_hosp, fin_hosp FROM s)
        SELECT date_trunc('month', ini_hosp)::date AS mes, count(*) AS estancias,
               avg(extract(epoch FROM (fin_hosp - ini_hosp)) / 86400) AS estancia_media_dias
        FROM d GROUP BY 1 ORDER BY 1"""),
    # ---------------------------------------------------------------- E. llegadas
    ("E01_llegadas_visitas_vs_personas_por_dia", f"""
        SELECT vd.visit_detail_start_datetime::date AS dia, count(DISTINCT vd.visit_occurrence_id) AS visitas, count(DISTINCT vo.person_id) AS personas
        FROM {S}.visit_detail vd JOIN {S}.visit_occurrence vo ON vo.visit_occurrence_id = vd.visit_occurrence_id
        WHERE vd.visit_detail_concept_id IN (9203, 3045729) GROUP BY 1 ORDER BY 1"""),
    ("E02_copias_por_desfase_de_id", f"""
        SELECT o.off AS desfase, count(*) AS pares, count(*) FILTER (WHERE a.person_id = b.person_id) AS misma_persona,
               count(*) FILTER (WHERE a.visit_start_datetime = b.visit_start_datetime) AS mismo_inicio
        FROM (VALUES (1746478), (1746479), (1746480), (1746481), (1746482), (1746483), (1746484), (1746485), (1746486), (1746487), (1746488), (1746489), (1757764)) AS o(off)
        JOIN {S}.visit_occurrence a ON a.visit_occurrence_id >= o.off
        JOIN {S}.visit_occurrence b ON b.visit_occurrence_id = a.visit_occurrence_id - o.off
        GROUP BY 1 ORDER BY 1"""),
    ("E03_llegadas_por_hora_2025", f"""
        WITH v AS (SELECT visit_occurrence_id, min(visit_detail_start_datetime) AS ini FROM {S}.visit_detail
                   WHERE visit_detail_concept_id IN (9203, 3045729) GROUP BY 1)
        SELECT extract(hour FROM ini)::int AS hora, extract(isodow FROM ini)::int AS dia_semana, count(*) AS visitas
        FROM v WHERE ini >= '2025-01-01' AND ini < '2026-01-01' GROUP BY 1, 2 ORDER BY 2, 1"""),
    # ---------------------------------------------------------------- G. personas
    ("G01_personas_anio_nacimiento_y_sexo", f"""
        SELECT gender_concept_id, count(*) AS personas, count(*) FILTER (WHERE year_of_birth < 1900 OR year_of_birth > 2026) AS anio_imposible,
               count(*) FILTER (WHERE year_of_birth < 1916) AS mas_de_110, min(year_of_birth) AS min_anio, max(year_of_birth) AS max_anio
        FROM {S}.person GROUP BY 1 ORDER BY 1"""),
    # ---------------------------------------------------------------- C07 y F: las pesadas, al final
    ("C07_ultimo_laboratorio_dentro_de_cada_estancia", f"""
        WITH v AS (SELECT visit_occurrence_id, min(visit_detail_start_datetime) AS ini, max(visit_detail_end_datetime) AS fin
                   FROM {S}.visit_detail vd WHERE {HOSP_CERRADA} GROUP BY 1),
             st AS (SELECT DISTINCT ON (ini, fin) visit_occurrence_id, ini, fin FROM v ORDER BY ini, fin, visit_occurrence_id)
        SELECT st.visit_occurrence_id, st.ini, st.fin, count(m.measurement_id) AS n_lab, min(m.measurement_datetime) AS primer_lab, max(m.measurement_datetime) AS ultimo_lab
        FROM st LEFT JOIN {S}.measurement m ON m.visit_occurrence_id = st.visit_occurrence_id AND m.measurement_datetime BETWEEN st.ini AND st.fin
        GROUP BY 1, 2, 3"""),
    ("F01_diagnosticos_con_y_sin_codigo_por_mes", f"""
        SELECT date_trunc('month', condition_start_datetime)::date AS mes, count(*) AS filas, count(*) FILTER (WHERE condition_concept_id = 0) AS sin_codigo,
               count(DISTINCT visit_occurrence_id) AS visitas, count(*) FILTER (WHERE condition_start_datetime > now()) AS futuras
        FROM {S}.condition_occurrence GROUP BY 1 ORDER BY 1"""),
    ("F02_hora_del_diagnostico_frente_a_la_visita", f"""
        SELECT count(*) AS filas, avg((c.condition_start_datetime < v.visit_start_datetime + interval '2 hours')::int) AS prop_en_primeras_2h,
               avg((c.condition_start_datetime < v.visit_start_datetime)::int) AS prop_antes_de_la_visita,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM (c.condition_start_datetime - v.visit_start_datetime)) / 3600) AS mediana_h_desde_inicio_visita
        FROM {S}.condition_occurrence c TABLESAMPLE SYSTEM (1) JOIN {S}.visit_occurrence v ON v.visit_occurrence_id = c.visit_occurrence_id"""),
    ("A04_laboratorios_por_mes", f"""
        SELECT date_trunc('month', measurement_datetime)::date AS mes, count(*) AS filas, count(DISTINCT visit_occurrence_id) AS visitas
        FROM {S}.measurement GROUP BY 1 ORDER BY 1"""),
]


# ---------------------------------------------------------------------------------------------------------------------------------------------
# LOTE 2 (2-nov-2026): preguntas que dejo el lote 1. El lote 1 mostro que las VISITAS (visit_occurrence) de urgencias NO bajaron en mayo de 2026
# (+2 % frente a mayo de 2025) mientras que las ETAPAS (visit_detail) de ER bajaron 64 %: el quiebre estaria en el detalle, no en los pacientes.
# ---------------------------------------------------------------------------------------------------------------------------------------------
CONSULTAS_2 = [
    ("R01_visitas_diarias_con_y_sin_etapas", f"""
        WITH d AS (SELECT visit_occurrence_id, count(*) AS n, count(*) FILTER (WHERE visit_detail_concept_id = 9203) AS n_er,
                          count(*) FILTER (WHERE visit_detail_concept_id = 3045729) AS n_tu, count(*) FILTER (WHERE visit_detail_concept_id = 9201) AS n_hosp
                   FROM {S}.visit_detail GROUP BY 1)
        SELECT vo.visit_start_datetime::date AS dia, vo.visit_concept_id, count(*) AS visitas,
               count(*) FILTER (WHERE d.n IS NULL) AS sin_ninguna_etapa, count(*) FILTER (WHERE d.n_er > 0) AS con_etapa_er,
               count(*) FILTER (WHERE d.n_tu > 0) AS con_etapa_tu, count(*) FILTER (WHERE d.n_hosp > 0) AS con_etapa_hosp
        FROM {S}.visit_occurrence vo LEFT JOIN d ON d.visit_occurrence_id = vo.visit_occurrence_id
        WHERE vo.visit_start_datetime >= '2025-01-01' GROUP BY 1, 2 ORDER BY 1, 2"""),
    ("R02_visitas_por_persona_por_mes", f"""
        WITH x AS (SELECT date_trunc('month', visit_start_datetime)::date AS mes, person_id, count(*) AS v
                   FROM {S}.visit_occurrence WHERE visit_start_datetime >= '2025-01-01' GROUP BY 1, 2)
        SELECT mes, count(*) AS personas, sum(v) AS visitas, max(v) AS max_visitas_de_una_persona,
               count(*) FILTER (WHERE v >= 20) AS personas_con_20_o_mas_visitas, sum(v) FILTER (WHERE v >= 20) AS visitas_de_esas_personas
        FROM x GROUP BY 1 ORDER BY 1"""),
    ("R03_personas_nuevas_por_mes", f"""
        SELECT date_trunc('month', primera)::date AS mes, count(*) AS personas_nuevas
        FROM (SELECT person_id, min(visit_start_datetime) AS primera FROM {S}.visit_occurrence GROUP BY 1) x GROUP BY 1 ORDER BY 1"""),
    ("R04_espera_de_cama_con_episodios", f"""
        WITH s AS (SELECT visit_occurrence_id, visit_detail_concept_id AS c, visit_detail_start_datetime AS ini, visit_detail_end_datetime AS fin
                   FROM {S}.visit_detail WHERE visit_detail_concept_id IN (9203, 3045729, 9201)
                     AND visit_detail_end_datetime = date_trunc('second', visit_detail_end_datetime)),
             o AS (SELECT *, max(fin) OVER (PARTITION BY visit_occurrence_id ORDER BY ini, fin ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS fin_prev FROM s),
             e AS (SELECT *, sum((fin_prev IS NULL OR ini > fin_prev + interval '168 hours')::int) OVER (PARTITION BY visit_occurrence_id ORDER BY ini, fin) AS ep FROM o),
             p AS (SELECT visit_occurrence_id, ep, min(ini) AS ini_ep, min(ini) FILTER (WHERE c = 9201) AS ini_hosp,
                          max(fin) FILTER (WHERE c = 9201 AND fin > ini) AS fin_hosp
                   FROM e GROUP BY 1, 2 HAVING bool_or(c = 9201)),
             d AS (SELECT ini_hosp, fin_hosp, min(ini_ep) AS ini_ep FROM p GROUP BY 1, 2),
             w AS (SELECT extract(year FROM ini_hosp)::int AS anio, greatest(extract(epoch FROM (ini_hosp - ini_ep)) / 3600, 0) AS espera_h FROM d)
        SELECT anio, count(*) AS estancias, percentile_cont(0.25) WITHIN GROUP (ORDER BY espera_h) AS p25, percentile_cont(0.5) WITHIN GROUP (ORDER BY espera_h) AS p50,
               percentile_cont(0.75) WITHIN GROUP (ORDER BY espera_h) AS p75, percentile_cont(0.9) WITHIN GROUP (ORDER BY espera_h) AS p90,
               avg((espera_h > 24)::int) AS prop_mas_24h
        FROM w GROUP BY ROLLUP(anio) ORDER BY anio"""),
    ("R05_laboratorios_por_estancia_con_gemelos", f"""
        WITH v AS (SELECT visit_occurrence_id, min(visit_detail_start_datetime) AS ini, max(visit_detail_end_datetime) AS fin
                   FROM {S}.visit_detail vd WHERE {HOSP_CERRADA} GROUP BY 1),
             vv AS (SELECT visit_occurrence_id, ini, fin, dense_rank() OVER (ORDER BY ini, fin) AS sid FROM v WHERE fin < '2026-06-01')
        SELECT vv.sid, min(vv.ini) AS ini, min(vv.fin) AS fin, count(DISTINCT vv.visit_occurrence_id) AS visitas_gemelas,
               count(m.measurement_id) AS n_lab, min(m.measurement_datetime) AS primer_lab, max(m.measurement_datetime) AS ultimo_lab
        FROM vv LEFT JOIN {S}.measurement m ON m.visit_occurrence_id = vv.visit_occurrence_id AND m.measurement_datetime BETWEEN vv.ini AND vv.fin
        GROUP BY vv.sid"""),
    ("R06_ultimo_diagnostico_por_estancia_con_gemelos", f"""
        WITH v AS (SELECT visit_occurrence_id, min(visit_detail_start_datetime) AS ini, max(visit_detail_end_datetime) AS fin
                   FROM {S}.visit_detail vd WHERE {HOSP_CERRADA} GROUP BY 1),
             vv AS (SELECT visit_occurrence_id, ini, fin, dense_rank() OVER (ORDER BY ini, fin) AS sid FROM v WHERE fin < '2026-06-01')
        SELECT vv.sid, count(c.condition_occurrence_id) AS n_dx, min(c.condition_start_datetime) AS primer_dx, max(c.condition_start_datetime) AS ultimo_dx
        FROM vv LEFT JOIN {S}.condition_occurrence c ON c.visit_occurrence_id = vv.visit_occurrence_id AND c.condition_start_datetime BETWEEN vv.ini AND vv.fin
        GROUP BY vv.sid"""),
]

# ---------------------------------------------------------------------------------------------------------------------------------------------
# LOTE 3 (2-nov-2026): ¿las estancias largas y las de visitas "Treatment urgency" son pacientes con actividad de hospitalizacion cada dia?
# (la ocupacion supera las 106 camas desde 2024 y el exceso viene de estancias de mas de 14 dias y de las visitas Treatment urgency, que pasaron de 269 a 958
#  estancias por anio entre 2023 y 2025). Por estancia: dias con laboratorio, procedimientos de UCI y de nutricion hospitalaria, tipo de visita y persona.
# ---------------------------------------------------------------------------------------------------------------------------------------------
CONSULTAS_3 = [
    ("S01_actividad_por_estancia", f"""
        WITH v AS (SELECT visit_occurrence_id, min(visit_detail_start_datetime) AS ini, max(visit_detail_end_datetime) AS fin
                   FROM {S}.visit_detail vd WHERE {HOSP_CERRADA} GROUP BY 1),
             vv AS (SELECT v.visit_occurrence_id, v.ini, v.fin, vo.visit_concept_id, vo.person_id, dense_rank() OVER (ORDER BY v.ini, v.fin) AS sid
                    FROM v JOIN {S}.visit_occurrence vo ON vo.visit_occurrence_id = v.visit_occurrence_id
                    WHERE v.fin < '2026-04-10' AND v.ini >= '2023-02-01'),
             lab AS (SELECT vv.sid, count(*) AS n_lab, count(DISTINCT m.measurement_datetime::date) AS dias_con_lab
                     FROM vv JOIN {S}.measurement m ON m.visit_occurrence_id = vv.visit_occurrence_id AND m.measurement_datetime BETWEEN vv.ini AND vv.fin
                     GROUP BY 1),
             pr AS (SELECT vv.sid, count(*) FILTER (WHERE p.procedure_concept_id = 4137917) AS n_uci, count(*) FILTER (WHERE p.procedure_concept_id = 4138350) AS n_nutricion
                    FROM vv JOIN {S}.procedure_occurrence p ON p.visit_occurrence_id = vv.visit_occurrence_id WHERE p.procedure_concept_id IN (4137917, 4138350) GROUP BY 1)
        SELECT vv.sid, min(vv.ini) AS ini, min(vv.fin) AS fin, count(*) AS visitas_gemelas, min(vv.visit_concept_id) AS tipo_visita_min, max(vv.visit_concept_id) AS tipo_visita_max,
               min(vv.person_id) AS persona, coalesce(max(lab.n_lab), 0) AS n_lab, coalesce(max(lab.dias_con_lab), 0) AS dias_con_lab,
               coalesce(max(pr.n_uci), 0) AS n_uci, coalesce(max(pr.n_nutricion), 0) AS n_nutricion
        FROM vv LEFT JOIN lab ON lab.sid = vv.sid LEFT JOIN pr ON pr.sid = vv.sid GROUP BY vv.sid"""),
]

# ---------------------------------------------------------------------------------------------------------------------------------------------
# LOTE 4 (2-nov-2026): ¿cual de las dos personas de una estancia gemela es la real? En A1 se vio que los dos registros de una estancia gemela coinciden en el sexo solo
# el 51,7 % de las veces (el azar daria 51 %) y en la edad (dentro de 2 anios) el 6,3 %: son dos personas sin relacion. El person_id de las filas de diagnosticos,
# laboratorios y procedimientos de cada visita puede delatar a la persona real. Por visita con hospitalizacion: las personas que aparecen en esas filas.
# ---------------------------------------------------------------------------------------------------------------------------------------------
_V_HOSP = f"SELECT DISTINCT visit_occurrence_id FROM {S}.visit_detail WHERE visit_detail_concept_id = 9201"
CONSULTAS_4 = [
    ("P01_persona_de_la_visita", f"SELECT visit_occurrence_id, person_id FROM {S}.visit_occurrence WHERE visit_occurrence_id IN ({_V_HOSP})"),
    ("P02_persona_de_los_diagnosticos", f"SELECT visit_occurrence_id, person_id, count(*) AS filas FROM {S}.condition_occurrence WHERE visit_occurrence_id IN ({_V_HOSP}) GROUP BY 1, 2"),
    ("P03_persona_de_los_laboratorios", f"SELECT visit_occurrence_id, person_id, count(*) AS filas FROM {S}.measurement WHERE visit_occurrence_id IN ({_V_HOSP}) GROUP BY 1, 2"),
    ("P04_persona_de_los_procedimientos", f"SELECT visit_occurrence_id, person_id, count(*) AS filas FROM {S}.procedure_occurrence WHERE visit_occurrence_id IN ({_V_HOSP}) GROUP BY 1, 2"),
]
CONSULTAS = CONSULTAS_1


def log(msg):
    linea = f"{datetime.datetime.now():%H:%M:%S}  {msg}"
    print(linea, flush=True)
    with open(LOG, "a") as f:
        f.write(linea + "\n")


def notificar(texto):
    try:
        subprocess.run(["osascript", "-e", f'display notification "{texto}" with title "Auditoria de la base" sound name "Glass"'], timeout=10)
    except Exception:
        pass


def probar_local():
    """Valida la sintaxis con DuckDB y tablas vacias (no toca la base)."""
    import duckdb
    con = duckdb.connect()
    con.execute(f"CREATE SCHEMA {S}")
    con.execute(f"""CREATE TABLE {S}.visit_occurrence (visit_occurrence_id BIGINT, person_id BIGINT, visit_concept_id INT, visit_start_datetime TIMESTAMP, visit_end_datetime TIMESTAMP, provider_id INT);
                    CREATE TABLE {S}.visit_detail (visit_detail_id BIGINT, visit_occurrence_id BIGINT, visit_detail_concept_id INT, visit_detail_start_datetime TIMESTAMP, visit_detail_end_datetime TIMESTAMP, provider_id INT);
                    CREATE TABLE {S}.condition_occurrence (condition_occurrence_id BIGINT, person_id BIGINT, visit_occurrence_id BIGINT, condition_concept_id INT, condition_start_datetime TIMESTAMP, condition_type_concept_id INT);
                    CREATE TABLE {S}.measurement (measurement_id BIGINT, person_id BIGINT, visit_occurrence_id BIGINT, measurement_concept_id INT, measurement_datetime TIMESTAMP, value_as_number DOUBLE, measurement_source_value_extended VARCHAR);
                    CREATE TABLE {S}.procedure_occurrence (procedure_occurrence_id BIGINT, person_id BIGINT, visit_occurrence_id BIGINT, procedure_concept_id INT, procedure_date DATE);
                    CREATE TABLE {S}.person (person_id BIGINT, gender_concept_id INT, year_of_birth INT, race_concept_id INT, ethnicity_concept_id INT);
                    CREATE TABLE {S}.concept (concept_id INT, concept_name VARCHAR, domain_id VARCHAR, vocabulary_id VARCHAR);""")
    # con una fila de cada cosa para que las consultas no pasen vacias por casualidad
    con.execute(f"INSERT INTO {S}.visit_occurrence VALUES (1,1,9203,'2026-01-01 10:00',NULL,0),(1746479,2,9203,'2026-01-01 10:00',NULL,0)")
    con.execute(f"INSERT INTO {S}.visit_detail VALUES (1,1,9203,'2026-01-01 10:00','2026-01-01 10:05',0),(2,1,9201,'2026-01-01 12:00','2026-01-03 14:00',0),(3,2,9201,'2026-01-01 12:00','2026-01-03 14:00',0)")
    con.execute(f"INSERT INTO {S}.condition_occurrence VALUES (1,1,1,0,'2026-01-01 11:00',0)")
    con.execute(f"INSERT INTO {S}.measurement VALUES (1,1,1,1,'2026-01-02 11:00',0,'x')")
    con.execute(f"INSERT INTO {S}.person VALUES (1,8532,1980,0,0)")
    ok = 0
    for nombre, sql in CONSULTAS:
        q = re.sub(r"TABLESAMPLE SYSTEM \(\d+\)", "", sql)
        try:
            con.execute(q).fetchall()
            ok += 1
            print("OK   ", nombre)
        except Exception as e:
            print("ERROR", nombre, "->", str(e).splitlines()[0][:200])
    print(f"{ok} de {len(CONSULTAS)} consultas con sintaxis valida en DuckDB (PostgreSQL puede diferir en detalles)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--esperar", type=float, default=0)
    ap.add_argument("--probar-local", action="store_true")
    ap.add_argument("--lote", type=int, default=1)
    a = ap.parse_args()
    CONSULTAS = {1: CONSULTAS_1, 2: CONSULTAS_2, 3: CONSULTAS_3, 4: CONSULTAS_4}[a.lote]
    if a.probar_local:
        probar_local()
        raise SystemExit(0)
    import conexion_bd as cb
    from sqlalchemy import text
    log("inicio")
    cfg = json.loads(cb.CONFIG.read_text())
    limite, avisado = time.time() + max(a.esperar, 0.1) * 60, False
    while True:
        try:
            socket.create_connection((cfg["host"], int(cfg.get("port", 5432))), timeout=5).close()
            break
        except OSError:
            if time.time() > limite:
                log("el servidor no respondio: revisa la VPN")
                notificar("El servidor no respondio. Revisa la VPN.")
                raise SystemExit(1)
            if not avisado:
                log(f"esperando a que responda {cfg['host']}:{cfg.get('port')} (conecta la VPN)...")
                avisado = True
            time.sleep(10)
    log(f"servidor alcanzable: empieza la auditoria ({len(CONSULTAS)} consultas)")
    t_total = time.time()
    for nombre, sql in CONSULTAS:
        t0 = time.time()
        try:
            with cb.motor(timeout_min=40).connect() as con:
                df = pd.read_sql(text(sql), con)
            df.to_csv(SALIDA / f"{nombre}.csv", index=False)
            log(f"OK    {nombre}: {len(df)} filas ({time.time() - t0:.0f} s)")
        except Exception as e:
            log(f"ERROR {nombre}: {type(e).__name__}: {str(e).splitlines()[0][:220]}")
    log(f"TERMINADO en {(time.time() - t_total) / 60:.1f} min")
    notificar("Auditoria terminada. Ya puedes desconectar la VPN.")
