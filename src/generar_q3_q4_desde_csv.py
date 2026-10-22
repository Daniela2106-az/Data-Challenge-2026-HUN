"""
generar_q3_q4_desde_csv.py  -  version 1 (22-oct-2026)
Genera q3_episodios.csv y q4_ocupacion_por_hora.csv (consultas Q3 y Q4 de sql/consultas_cuellos_botella.sql)
corriendo esas MISMAS consultas sobre los CSV de datos/crudos con DuckDB, para quien no pueda exportarlas
desde DBeaver (la exportacion completa de Q3, ~337 mil filas, fallo en la base).

POR QUE ES EQUIVALENTE
  Las consultas son SQL estandar compatible con PostgreSQL y DuckDB. El 22-oct-2026 se corrio Q3b (la version
  resumida de Q3) en la base real y dio EXACTAMENTE los mismos 23 controles que sobre estos CSV (336.844
  episodios, 35.322 con hospitalizacion, espera mediana 21,4 h, etc.). Q1 y Q2 tambien coincidieron fila por fila.

ENTRADAS (datos/crudos/)  visit_detail.csv, visit_occurrence.csv, person.csv
SALIDAS  (datos/crudos/)  q3_episodios.csv, q4_ocupacion_por_hora.csv
         con --umbral H: q3_episodios_uH.csv (episodios cortados con huecos de mas de H horas, para la prueba de
         sensibilidad: SUFIJO=_uH python3 src/construir_segmentos.py)

USO
  pip install duckdb
  python3 src/generar_q3_q4_desde_csv.py            # Q3 y Q4 con el corte de 168 h
  python3 src/generar_q3_q4_desde_csv.py --umbral 72
"""
import argparse
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CRUDOS = RAIZ / "datos" / "crudos"
SQL = RAIZ / "sql" / "consultas_cuellos_botella.sql"
N_ESPERADO = 336_844      # filas de Q3 con el corte de 168 h (referencia, no es una regla)


def consulta(texto, marca_a, marca_b=None):
    """Devuelve la primera consulta del archivo que contiene las marcas (los comentarios se quitan antes)."""
    sin_comentarios = re.sub(r"--[^\n]*", "", texto)
    for s in sin_comentarios.split(";"):
        if marca_a in s and (marca_b is None or marca_b in s) and "SET statement_timeout" not in s:
            return s.strip()
    raise SystemExit(f"no se encontro la consulta con la marca {marca_a!r} en {SQL.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--umbral", type=int, default=168, help="horas sin etapas para cortar un episodio (por defecto 168)")
    args = ap.parse_args()
    try:
        import duckdb
    except ImportError:
        raise SystemExit("falta duckdb: pip install duckdb")
    for nombre in ["visit_detail.csv", "visit_occurrence.csv", "person.csv"]:
        if not (CRUDOS / nombre).exists():
            raise SystemExit(f"falta {CRUDOS / nombre}")

    con = duckdb.connect()
    con.execute("CREATE SCHEMA uninorte_omop")
    for t in ["visit_detail", "visit_occurrence"]:
        con.execute(f"CREATE TABLE uninorte_omop.{t} AS SELECT * FROM read_csv_auto('{CRUDOS / (t + '.csv')}')")
    # person.csv trae el sexo como texto; Q3 usa el codigo estandar OMOP (8507 hombre, 8532 mujer)
    con.execute(f"""CREATE TABLE uninorte_omop.person AS
                    SELECT person_id, year_of_birth,
                           CASE upper(sexo) WHEN 'MALE' THEN 8507 WHEN 'FEMALE' THEN 8532 ELSE 0 END AS gender_concept_id
                    FROM read_csv_auto('{CRUDOS / 'person.csv'}')""")

    texto = SQL.read_text(encoding="utf-8")
    q3 = consulta(texto, "ep_ok", "llegadas_24h_previas").replace("'168 hours'", f"'{args.umbral} hours'")
    q4 = consulta(texto, "ocup_hosp_fin_hora")
    sufijo = "" if args.umbral == 168 else f"_u{args.umbral}"

    df = con.execute(q3).df()
    df["episodio"] = df.episodio.astype(int)
    df.to_csv(CRUDOS / f"q3_episodios{sufijo}.csv", index=False)
    print(f"q3_episodios{sufijo}.csv: {len(df)} episodios, {int(df.ini_hosp.notna().sum())} con hospitalizacion")
    if args.umbral == 168 and abs(len(df) - N_ESPERADO) / N_ESPERADO > 0.02:
        print(f"  AVISO: se esperaban ~{N_ESPERADO} episodios (diferencia mayor al 2 %): revisar los CSV de entrada")
    if args.umbral == 168:
        o = con.execute(q4).df()
        o.to_csv(CRUDOS / "q4_ocupacion_por_hora.csv", index=False)
        print(f"q4_ocupacion_por_hora.csv: {len(o)} horas")


if __name__ == "__main__":
    main()
