"""
exportar_procedimientos_por_estancia.py  -  version 1 (7-nov-2026)
Pedido de Samuel: un CSV que diga QUE procedimiento tuvo cada estancia (no cuantas veces).

Una fila por (estancia, procedimiento). Sin conteos, sin visit_occurrence_id y sin person_id: solo el id de estancia (estancia_id, anonimo), el grupo de edad y el
sexo de la persona real de la estancia (CLAUDE.md 4.10; son los mismos que corrigen P02 y P03) y el concepto con su nombre cuando se conoce.
Solo cuentan las filas de procedimientos de la PERSONA REAL de la estancia (los procedimientos suelen colgar del registro gemelo: el 88 % no es el conservado).

ENTRADAS  datos/crudos/auditoria_bd/Q01_procedimientos_por_estancia.csv, Q03_nombres_de_conceptos.csv (nombres conocidos),
          datos/procesados/copias.csv, episodios.csv, tabla_episodios.parquet
SALIDA    datos/procesados/para_equipo/procedimientos_por_estancia.csv  (NO se sube a git: es una fila por estancia; pasar solo por el drive del equipo)
          datos/procesados/para_equipo/procedimientos_conceptos.csv  (concepto, nombre, n_estancias)
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC, AUD = RAIZ / "datos" / "procesados", RAIZ / "datos" / "crudos" / "auditoria_bd"
OUT = PROC / "para_equipo"
OUT.mkdir(exist_ok=True)

q = pd.read_csv(AUD / "Q01_procedimientos_por_estancia.csv")
cop = pd.read_csv(PROC / "copias.csv", usecols=["visit_occurrence_id", "raiz_id"])
epi = pd.read_csv(PROC / "episodios.csv", usecols=["visit_occurrence_id", "estancia_id"]).drop_duplicates("visit_occurrence_id")
visita_a_estancia = pd.concat([cop.merge(epi.rename(columns={"visit_occurrence_id": "raiz_id"}), on="raiz_id")[["visit_occurrence_id", "estancia_id"]], epi]).drop_duplicates("visit_occurrence_id")
t = pd.read_parquet(PROC / "tabla_episodios.parquet", columns=["estancia_id", "estancia_unica", "hospitalizado", "persona_real", "grupo_edad", "sexo"])
real = t[t.estancia_unica & t.hospitalizado].drop_duplicates("estancia_id")[["estancia_id", "persona_real", "grupo_edad", "sexo"]]

x = q.merge(visita_a_estancia, on="visit_occurrence_id").merge(real, on="estancia_id")
x = x[(x.person_id == x.persona_real) | x.persona_real.isna()]
x = x[["estancia_id", "grupo_edad", "sexo", "concepto"]].drop_duplicates()
nom = pd.read_csv(AUD / "Q03_nombres_de_conceptos.csv").rename(columns={"concept_id": "concepto", "concept_name": "nombre"})[["concepto", "nombre"]]
x = x.merge(nom, on="concepto", how="left").sort_values(["estancia_id", "concepto"])
x.to_csv(OUT / "procedimientos_por_estancia.csv", index=False)
c = x.groupby("concepto").agg(n_estancias=("estancia_id", "nunique")).reset_index().merge(nom, on="concepto", how="left").sort_values("n_estancias", ascending=False)
c.to_csv(OUT / "procedimientos_conceptos.csv", index=False)
print(f"estancias con algun procedimiento: {x.estancia_id.nunique()} | filas (estancia, procedimiento): {len(x)} | conceptos: {x.concepto.nunique()} "
      f"| conceptos con nombre: {c.nombre.notna().sum()} | filas con nombre: {100 * x.nombre.notna().mean():.0f} %")
print("procedimientos por estancia (mediana):", x.groupby("estancia_id").size().median())
