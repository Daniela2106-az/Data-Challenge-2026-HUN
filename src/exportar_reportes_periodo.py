"""
exportar_reportes_periodo.py  -  reportes del diagnostico de cuello de botella para el dashboard (15-nov-2026)

Tarea A7 / pagina 3.5 del dashboard: el usuario elige un periodo y una referencia y ve el reporte de cinco pasos de
src/diagnostico_cuello_botella.py. Ese script lee tablas por episodio (locales, no se publican), asi que aqui se corre de antemano
para cada combinacion de periodo y referencia y se guarda SOLO el resultado agregado, en el lenguaje de la pagina.

PERIODOS  todo el periodo confiable, cada año (2023 desde febrero; 2026 hasta el 9-abr) y cada semestre de 2023 a 2025.
          Se puede agregar uno nuevo en PERIODOS y volver a correr; no hay un rango libre porque cada reporte se crea de antemano.
ENTRADA   datos/procesados/tabla_episodios.parquet (via src/diagnostico_cuello_botella.py, ~1 s por reporte; ~2 min en total)
SALIDA    datos/tablas_dashboard/cuello_botella_reportes.csv  (una fila por periodo, referencia y paso; sin datos por paciente)
COMO CORRERLO  python3 src/exportar_reportes_periodo.py
LIMITES   Todo son asociaciones sobre datos historicos; el periodo confiable termina el 9-abr-2026 (docs/CONTEXTO_TECNICO.md 4.9).
"""
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "src" / "diagnostico_cuello_botella.py"
TABLAS = RAIZ / "resultados" / "tablas"
SALIDA = RAIZ / "datos" / "tablas_dashboard" / "cuello_botella_reportes.csv"

# id, texto del boton, desde, hasta
PERIODOS = [("todo", "Todo el periodo", "2023-02-01", "2026-04-09"),
            ("2023", "2023", "2023-02-01", "2023-12-31"), ("2024", "2024", "2024-01-01", "2024-12-31"),
            ("2025", "2025", "2025-01-01", "2025-12-31"), ("2026", "2026 (hasta el 9 de abril)", "2026-01-01", "2026-04-09"),
            ("2023s1", "Feb a jun 2023", "2023-02-01", "2023-06-30"), ("2023s2", "Jul a dic 2023", "2023-07-01", "2023-12-31"),
            ("2024s1", "Ene a jun 2024", "2024-01-01", "2024-06-30"), ("2024s2", "Jul a dic 2024", "2024-07-01", "2024-12-31"),
            ("2025s1", "Ene a jun 2025", "2025-01-01", "2025-06-30"), ("2025s2", "Jul a dic 2025", "2025-07-01", "2025-12-31")]

# nombres de columna y de factor en lenguaje del hospital
COLUMNAS = {"segmento": "Tramo", "n": "Estancias", "mediana_h": "Mediana (h)", "p90_h": "Peores casos (h)", "horas_totales": "Horas totales",
            "exceso_horas": "Horas en exceso", "exceso_medio_h": "Exceso medio (h)", "pct_sobre_referencia": "% sobre lo normal",
            "factor": "Factor", "nivel": "Grupo", "disparadas": "Esperas largas", "pct_del_grupo_que_se_dispara": "% del grupo con espera larga",
            "razon": "Veces más frecuente"}
FACTORES = {"categoria_dx": "Diagnóstico", "grupo_edad": "Edad", "tipo_visita": "Tipo de visita", "franja": "Franja de llegada", "sexo": "Sexo"}
TITULOS = {1: "Dónde está el cuello de botella", 2: "Qué se dispara", 3: "Qué estancias tienen esperas muy largas",
           4: "Qué tienen en común", 5: "Qué hacer"}


def correr(d, h, rd, rh):
    subprocess.run([sys.executable, str(SCRIPT), "--desde", d, "--hasta", h, "--ref-desde", rd, "--ref-hasta", rh], check=True, capture_output=True)
    return (TABLAS / f"cuello_botella_{d}_{h}.md").read_text(encoding="utf-8")


def limpiar(t):
    """Lenguaje del hospital: sin nombres de archivo ni de columna, con coma decimal."""
    t = re.sub(r"\(el escenario de `simulacion_altas\.py` da una cota; no resuelve esperas de varios días\)", "(el escenario de altas da una cota y no resuelve esperas de varios días)", t)
    t = t.replace("(alerta C: paciente sin cama a las 48 h)", "(aviso de paciente sin cama a las 48 h)")
    t = re.sub(r"\s*\(reglas condicionadas por las cifras del periodo; detalle en `docs/recomendaciones\.md`\)", "", t)
    t = re.sub(r"`[^`]*`", "", t)
    for a, b in COLUMNAS.items():
        t = re.sub(rf"(?<=[| ]){re.escape(a)}(?=[| ])", b, t)
    for a, b in FACTORES.items():
        t = t.replace(f"| {a} |", f"| {b} |")
    t = re.sub(r"(?<=\d)\.(?=\d)", ",", t)                       # 17.5 -> 17,5
    t = t.replace("Ley de Little", "ley de Little")
    return t.strip()


def partir(md):
    """Divide el reporte en sus cinco pasos."""
    partes = re.split(r"\n## (\d)\. [^\n]*\n", "\n" + md)
    return {int(partes[i]): partes[i + 1] for i in range(1, len(partes) - 1, 2)}


filas = []
for pid, plab, pd_, ph_ in PERIODOS:
    for rid, rlab, rd_, rh_ in PERIODOS:
        md = correr(pd_, ph_, rd_, rh_)
        pasos = partir(md)
        p1 = pasos[1]
        cuello = re.search(r"\*\*Cuello de botella del periodo: ([^*]+)\*\*", p1)
        cambio = re.search(r"Frente a la referencia \*\*([^*]+)\*\*;? ?([^\n]*)", p1)
        mismo = "El periodo y la referencia coinciden" in p1
        exceso = re.search(r"Espera de cama \(total\) \| \d+ \| [\d.]+ \| [\d.]+ \| \d+ \| \d+ \| ([\d.]+) \|", p1)
        for k in range(1, 6):
            filas.append({"periodo": pid, "referencia": rid, "paso": k, "titulo": TITULOS[k], "texto": limpiar(pasos[k]),
                          "cuello": cuello.group(1) if cuello else "", "mismo": int(mismo),
                          "cambio": (cambio.group(1) + "; " + limpiar(cambio.group(2))).strip("; ") if cambio else "",
                          "exceso_medio_h": float(exceso.group(1)) if exceso else None})
    print(pid, "ok", flush=True)

SALIDA.parent.mkdir(parents=True, exist_ok=True)
t = pd.DataFrame(filas)
t.to_csv(SALIDA, index=False, encoding="utf-8")
print(f"\n{SALIDA.relative_to(RAIZ)}: {len(t)} filas ({len(PERIODOS)} periodos × {len(PERIODOS)} referencias × 5 pasos)")
