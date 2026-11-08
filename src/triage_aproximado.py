"""
triage_aproximado.py  -  version 1 (7-nov-2026)
Tarea A6, cuarta parte: ¿cuanto mejoraria la estimacion de la espera de cama si se conociera la gravedad del paciente (el triage)?

POR QUE
  En urgencias la prioridad se define con el triage (I inmediata, II muy alta, III media, IV baja, V muy baja). La base NO trae el nivel de triage
  (CLAUDE.md secciones 3 y 4.8; la etapa 9203 solo trae la hora). Se prueban dos aproximaciones dentro del modelo de tiempo restante (M1 de
  comparar_estimadores.py), sabiendo que ninguna es el triage:
    + laboratorios de las primeras 6 h (n_lab_6h): pedir examenes temprano indica urgencia o complejidad. Se conoce a las 6 h, asi que solo es valido
      para estimar desde las 6 h de espera en adelante.
    + grupo de diagnostico: es lo mas parecido a la gravedad que hay, pero el 88 % se registra despues de las 2 primeras horas y puede venir del registro
      gemelo. Se usa como ESCENARIO: "si el HUN registrara la gravedad al llegar". Es una cota optimista, no un modelo utilizable hoy.

LA PRUEBA  la misma de comparar_estimadores.py (entrenamiento feb-2023 a jun-2025, prueba jul-2025 a 9-abr-2026), al llegar y despues de 6, 12, 24 y 48 h.
ENTRADA  tabla_episodios.parquet en HUN_PROCESADOS ; SALIDA en HUN_TABLAS: triage_aproximado.csv
COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... python3 src/triage_aproximado.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402

VARIANTES = {
    "M1 sin gravedad": ce.COLS_M1,
    "M1 + laboratorios de 6 h": ce.COLS_M1 + ["n_lab_6h"],
    "M1 + grupo de diagnostico (escenario)": ce.COLS_M1 + ["dx_cod"],
    "M1 + ambos (escenario)": ce.COLS_M1 + ["n_lab_6h", "dx_cod"],
}

if __name__ == "__main__":
    pd.set_option("display.width", 220)
    d, h, rejilla, estado = ce.preparar()
    grupos = sorted(d.categoria_dx.dropna().unique())
    d["dx_cod"] = d.categoria_dx.map({g: i for i, g in enumerate(grupos)})          # sin diagnostico = vacio (el modelo lo trata aparte)
    d["n_lab_6h"] = d.n_lab_6h.fillna(0)
    tr, te = d[d.ini_est < ce.CORTE].reset_index(drop=True), d[d.ini_est >= ce.CORTE].reset_index(drop=True)
    print(f"con grupo de diagnostico: {d.dx_cod.notna().mean():.0%} de las estancias | con algun laboratorio en 6 h: {(d.n_lab_6h > 0).mean():.0%}")
    modelos = {nombre: ce.entrenar_m1(tr, rejilla, estado, cols) for nombre, cols in VARIANTES.items()}

    filas = []
    for desde in [0] + ce.CONTROLES:
        sub = te[te.espera_cama_h > desde].reset_index(drop=True)
        y = np.minimum(sub.espera_cama_h.to_numpy() - desde, ce.MAX_H)
        general, _ = ce.referencias(tr, sub, desde)
        base = ce.perdida(y, general)
        for nombre, m in modelos.items():
            fila = ce.puntuar(nombre, y, ce.predecir_m1(m, sub, rejilla, estado, desde), base, desde)
            fila["valido_hoy"] = "no (escenario)" if "diagnostico" in nombre or "ambos" in nombre else ("solo desde 6 h" if "laboratorios" in nombre and desde < 6 else "si")
            filas.append(fila)
    res = pd.DataFrame(filas)
    res.to_csv(ce.TABLAS / "triage_aproximado.csv", index=False)
    print(res[["horas_esperando", "metodo", "valido_hoy", "n_prueba", "mejora_vs_general_pct", "error_abs_mediana_h", "pct_debajo_p25",
               "pct_debajo_p50", "pct_debajo_p75", "pct_debajo_p90"]].to_string(index=False))
