"""
explorar_bd.py  -  version 1 (2-nov-2026)
Exploracion de SOLO LECTURA de la base (esquema uninorte_omop) pensada para correr SOLA mientras la VPN esta conectada, porque con la VPN activa el
computador pierde el internet normal (y con el la sesion de Claude Code). Se lanza ANTES de conectar la VPN: espera a que el servidor responda, corre
todas las consultas, guarda los resultados en CSV, avisa con una notificacion de macOS y termina. Entonces ya se puede desconectar la VPN.

QUE BUSCA
  1. El esquema real: todas las tablas y columnas (nunca se verifico contra la base; CLAUDE.md dice que no hay servicio, sede ni cama).
  2. Si existen columnas de servicio, sede, cama u origen/destino (care_site_id, visit_detail_source_value, admitted_from_concept_id, etc.): los valores mas
     frecuentes de cada columna "categorica" de care_site, location, provider, visit_detail y visit_occurrence.
  3. El numero aproximado de filas de cada tabla.

USO       python3 src/explorar_bd.py --esperar 90            lote 1: esquema y valores de columnas (ya corrido el 2-nov: no hay servicio, sede ni cama)
          python3 src/explorar_bd.py --esperar 90 --lote 2   lote 2: tabla `cups` (catalogo de procedimientos), procedimientos mas frecuentes, codigos de
                                                              observacion/hospitalizacion por visita y diagnosticos con y sin codigo por semana
SALIDAS   datos/crudos/exploracion_bd/*.csv  y  datos/crudos/exploracion_bd/exploracion.log   (todo fuera de git)
CONEXION  src/conexion_bd.py (solo lectura, ~/.hun_db.json y ~/.pgpass). La contrasena nunca pasa por este archivo.
"""
import argparse
import datetime
import json
import socket
import subprocess
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import text

import conexion_bd as cb

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "datos" / "crudos" / "exploracion_bd"
SALIDA.mkdir(parents=True, exist_ok=True)
LOG = SALIDA / "exploracion.log"
ESQUEMA = "uninorte_omop"
TABLAS_CLAVE = ["care_site", "location", "provider", "visit_detail", "visit_occurrence", "location_history", "cdm_source"]
SALTAR = ("_id", "_datetime", "_date", "_start", "_end")      # llaves y fechas no son categoricas (los *_concept_id y *_source_concept_id si se revisan)


def log(msg):
    linea = f"{datetime.datetime.now():%H:%M:%S}  {msg}"
    print(linea, flush=True)
    with open(LOG, "a") as f:
        f.write(linea + "\n")


def esperar_servidor(minutos):
    c = json.loads(cb.CONFIG.read_text())
    limite = time.time() + minutos * 60
    avisado = False
    while True:
        try:
            socket.create_connection((c["host"], int(c.get("port", 5432))), timeout=5).close()
            return True
        except OSError:
            if time.time() > limite:
                return False
            if not avisado:
                log(f"esperando a que responda {c['host']}:{c.get('port')} (conecta la VPN)...")
                avisado = True
            time.sleep(10)


def correr(con, nombre, sql, params=None):
    t0 = time.time()
    try:
        df = pd.read_sql(text(sql), con, params=params)
        df.to_csv(SALIDA / f"{nombre}.csv", index=False)
        log(f"OK  {nombre}: {len(df)} filas ({time.time() - t0:.1f} s)")
        return df
    except Exception as e:                                       # una consulta que falla no detiene las demas
        con.rollback()
        log(f"ERROR {nombre}: {type(e).__name__}: {str(e).splitlines()[0][:200]}")
        return None


def notificar(texto):
    try:
        subprocess.run(["osascript", "-e", f'display notification "{texto}" with title "Exploracion de la base" sound name "Glass"'], timeout=10)
    except Exception:
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--esperar", type=float, default=0, help="minutos que espera a que el servidor responda (0 = no espera)")
    ap.add_argument("--lote", type=int, default=1)
    a = ap.parse_args()
    log("inicio")
    if not esperar_servidor(max(a.esperar, 0.1)):
        log("el servidor no respondio: revisa la VPN")
        notificar("El servidor no respondio. Revisa la VPN.")
        raise SystemExit(1)
    log("servidor alcanzable: empiezan las consultas")
    if a.lote == 2:
        with cb.motor(timeout_min=20).connect() as con:
            correr(con, "20_cups_columnas_y_muestra", f"SELECT * FROM {ESQUEMA}.cups ORDER BY codigo LIMIT 60")
            correr(con, "21_cups_periodos", f"SELECT periodo, count(*) AS n FROM {ESQUEMA}.cups GROUP BY 1 ORDER BY 1")
            palabras = ["%observ%", "%hospitaliz%", "%estancia%", "%cama%", "%cuidado intensivo%", "%cuidado intermedio%", "%unidad de cuidado%",
                        "%urgencia%", "%habitaci%", "%internaci%", "%neonat%"]
            claves = correr(con, "22_cups_palabras_clave", f"SELECT codigo, descripcion, periodo FROM {ESQUEMA}.cups WHERE descripcion ILIKE ANY(:p) ORDER BY codigo",
                            {"p": palabras})
            top = correr(con, "23_procedimientos_top200", f"""WITH t AS (SELECT procedure_concept_id, count(*) AS filas, count(DISTINCT visit_occurrence_id) AS visitas
                                                               FROM {ESQUEMA}.procedure_occurrence GROUP BY 1 ORDER BY 2 DESC LIMIT 200)
                                                             SELECT t.*, c.concept_name, c.vocabulary_id, c.domain_id, u.descripcion AS cups_descripcion
                                                             FROM t LEFT JOIN {ESQUEMA}.concept c ON c.concept_id = t.procedure_concept_id
                                                             LEFT JOIN {ESQUEMA}.cups u ON u.codigo = t.procedure_concept_id::text ORDER BY t.filas DESC""")
            if claves is not None and len(claves):
                cods = [str(c) for c in claves.codigo.unique()][:400]
                correr(con, "24_visitas_con_codigos_clave", f"""SELECT procedure_concept_id::text AS codigo, count(*) AS filas, count(DISTINCT visit_occurrence_id) AS visitas
                                                                FROM {ESQUEMA}.procedure_occurrence WHERE procedure_concept_id::text = ANY(:c) GROUP BY 1 ORDER BY 3 DESC""",
                       {"c": cods})
            correr(con, "25_dx_con_y_sin_codigo_por_semana", f"""SELECT date_trunc('week', condition_start_datetime)::date AS semana,
                                                                 count(*) FILTER (WHERE condition_concept_id = 0) AS filas_sin_codigo,
                                                                 count(*) FILTER (WHERE condition_concept_id <> 0) AS filas_con_codigo,
                                                                 count(DISTINCT visit_occurrence_id) AS visitas
                                                                 FROM {ESQUEMA}.condition_occurrence WHERE condition_start_datetime >= '2026-02-01' AND condition_start_datetime < '2026-08-01'
                                                                 GROUP BY 1 ORDER BY 1""")
        log("TERMINADO (lote 2)")
        notificar("Lote 2 terminado. Ya puedes desconectar la VPN.")
        raise SystemExit(0)
    with cb.motor(timeout_min=10).connect() as con:
        correr(con, "00_conexion", "select current_database() as base, current_user as usuario, now() as hora, version() as version")
        cols = correr(con, "01_esquema_columnas", f"""SELECT table_name, ordinal_position, column_name, data_type
                                                      FROM information_schema.columns WHERE table_schema = '{ESQUEMA}'
                                                      ORDER BY table_name, ordinal_position""")
        correr(con, "02_tablas_filas_aprox", f"""SELECT c.relname AS tabla, c.reltuples::bigint AS filas_aprox, pg_size_pretty(pg_total_relation_size(c.oid)) AS tamano
                                                 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                                                 WHERE n.nspname = '{ESQUEMA}' AND c.relkind = 'r' ORDER BY c.reltuples DESC""")
        if cols is not None:
            existentes = set(cols.table_name)
            log("tablas del esquema: " + ", ".join(sorted(existentes)))
            for tabla in [t for t in TABLAS_CLAVE if t in existentes]:
                columnas = cols[cols.table_name == tabla]
                resumen = []
                for _, r in columnas.iterrows():
                    col = r.column_name
                    if col.endswith(SALTAR) and not col.endswith("concept_id"):
                        continue
                    if col in ("person_id", tabla + "_id"):
                        continue
                    df = correr(con, f"10_valores_{tabla}__{col}",
                                f'SELECT "{col}" AS valor, count(*) AS n FROM {ESQUEMA}.{tabla} GROUP BY 1 ORDER BY 2 DESC LIMIT 40')
                    if df is not None:
                        resumen.append(dict(tabla=tabla, columna=col, valores_distintos_en_top40=len(df), valor_mas_frecuente=str(df.valor.iloc[0]) if len(df) else None,
                                            n_mas_frecuente=int(df.n.iloc[0]) if len(df) else None))
                pd.DataFrame(resumen).to_csv(SALIDA / f"11_resumen_{tabla}.csv", index=False)
    log("TERMINADO")
    notificar("Terminó. Ya puedes desconectar la VPN.")
