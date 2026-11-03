"""
ejecutar_consultas.py  -  version 1 (2-nov-2026)
Corre un archivo de consultas SQL (solo lectura) contra la base del reto y guarda cada resultado en un CSV. Esta pensado para correr SOLO, en segundo plano,
porque con la VPN conectada el computador pierde el internet normal (y con el la sesion de Claude Code): se lanza ANTES de conectar la VPN, espera a que el
servidor responda, corre todo, avisa con una notificacion de macOS y termina. Entonces se desconecta la VPN. Guia completa: docs/conexion_bd.md

FORMATO DEL ARCHIVO SQL
  Cada consulta empieza con una linea de nombre y termina en punto y coma:

      -- nombre: visitas_por_mes
      SELECT date_trunc('month', visit_start_datetime)::date AS mes, count(*) AS visitas
      FROM uninorte_omop.visit_occurrence GROUP BY 1 ORDER BY 1;

      -- nombre: personas_por_sexo
      SELECT gender_concept_id, count(*) FROM uninorte_omop.person GROUP BY 1;

USO
  python3 src/ejecutar_consultas.py sql/mis_consultas.sql --esperar 120          lanzar y despues conectar la VPN
  python3 src/ejecutar_consultas.py sql/mis_consultas.sql --solo-listar          solo muestra las consultas que encontro (no necesita la base)
SALIDAS   datos/crudos/consultas/<nombre>.csv y datos/crudos/consultas/consultas.log (todo fuera de git)
REGLAS    solo SELECT/WITH (la sesion es de solo lectura); limite de 15 minutos por consulta; la contrasena la lee PostgreSQL de ~/.pgpass, nunca este archivo.
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
SALIDA = RAIZ / "datos" / "crudos" / "consultas"
SALIDA.mkdir(parents=True, exist_ok=True)
LOG = SALIDA / "consultas.log"


def log(msg):
    linea = f"{datetime.datetime.now():%H:%M:%S}  {msg}"
    print(linea, flush=True)
    with open(LOG, "a") as f:
        f.write(linea + "\n")


def leer_consultas(ruta):
    """Devuelve [(nombre, sql)] a partir de las lineas '-- nombre: x' y los ';' finales."""
    texto = Path(ruta).read_text()
    bloques = re.split(r"^\s*--\s*nombre:\s*(\S+)\s*$", texto, flags=re.M)
    consultas = []
    for i in range(1, len(bloques), 2):
        nombre, sql = bloques[i], bloques[i + 1].strip().rstrip(";").strip()
        if sql:
            consultas.append((re.sub(r"[^\w\-]", "_", nombre), sql))
    return consultas


def notificar(texto):
    try:
        subprocess.run(["osascript", "-e", f'display notification "{texto}" with title "Consultas a la base" sound name "Glass"'], timeout=10)
    except Exception:
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("archivo")
    ap.add_argument("--esperar", type=float, default=0, help="minutos que espera a que el servidor responda (0 = no espera)")
    ap.add_argument("--solo-listar", action="store_true")
    a = ap.parse_args()
    consultas = leer_consultas(a.archivo)
    if not consultas:
        raise SystemExit("No se encontro ninguna consulta. Cada una debe empezar con una linea '-- nombre: algo'.")
    peligrosas = [n for n, q in consultas if not re.match(r"^\s*(with|select|explain)\b", q, flags=re.I)]
    if peligrosas:
        raise SystemExit(f"Solo se permiten consultas SELECT/WITH. Revisa: {', '.join(peligrosas)}")
    if a.solo_listar:
        for n, q in consultas:
            print(f"- {n}: {len(q)} caracteres")
        raise SystemExit(0)
    import conexion_bd as cb
    from sqlalchemy import text
    log(f"inicio: {len(consultas)} consultas de {a.archivo}")
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
    log("servidor alcanzable: empiezan las consultas")
    t_total = time.time()
    for nombre, sql in consultas:
        t0 = time.time()
        try:
            with cb.motor(timeout_min=15).connect() as con:
                df = pd.read_sql(text(sql), con)
            df.to_csv(SALIDA / f"{nombre}.csv", index=False)
            log(f"OK    {nombre}: {len(df)} filas ({time.time() - t0:.0f} s)")
        except Exception as e:
            log(f"ERROR {nombre}: {type(e).__name__}: {str(e).splitlines()[0][:220]}")
    log(f"TERMINADO en {(time.time() - t_total) / 60:.1f} min")
    notificar("Consultas terminadas. Ya puedes desconectar la VPN.")
