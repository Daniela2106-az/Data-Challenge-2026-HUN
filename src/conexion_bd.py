"""
conexion_bd.py  -  version 1 (2-nov-2026)
Conexion de SOLO LECTURA a la base del reto (PostgreSQL, esquema uninorte_omop) con SQLAlchemy, sin que la contrasena aparezca en el chat, en el codigo
ni en ningun archivo del proyecto.

COMO FUNCIONA
  - Host, puerto, nombre de la base y usuario (no son secretos) se leen de ~/.hun_db.json, un archivo en tu carpeta personal, FUERA del proyecto:
        {"host": "...", "port": 5432, "database": "...", "user": "..."}
  - La contrasena la lee la propia libreria de PostgreSQL desde ~/.pgpass (tambien fuera del proyecto, con permisos 600). Una linea:
        host:puerto:base:usuario:contrasena
    Este modulo nunca abre ni lee ~/.pgpass.
  - Hay que estar conectada a la VPN del hospital.
  - La sesion se abre en modo solo lectura y con statement_timeout de 10 min (cambiable con el parametro `timeout_min`).

USO
    from conexion_bd import consultar
    df = consultar("SELECT count(*) AS n FROM uninorte_omop.visit_occurrence")
"""
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

CONFIG = Path.home() / ".hun_db.json"


def motor(timeout_min=10):
    if not CONFIG.exists():
        raise SystemExit(f"Falta {CONFIG}. Crealo fuera del proyecto con host, port, database y user (ver el encabezado de src/conexion_bd.py).")
    c = json.loads(CONFIG.read_text())
    url = URL.create("postgresql+psycopg", username=c["user"], host=c["host"], port=int(c.get("port", 5432)), database=c["database"])
    opciones = f"-c default_transaction_read_only=on -c statement_timeout={int(timeout_min * 60_000)}"
    return create_engine(url, connect_args={"options": opciones, "connect_timeout": 15})


def consultar(sql, params=None, timeout_min=10):
    """Corre una consulta de solo lectura y devuelve un DataFrame."""
    with motor(timeout_min).connect() as con:
        return pd.read_sql(text(sql), con, params=params)
