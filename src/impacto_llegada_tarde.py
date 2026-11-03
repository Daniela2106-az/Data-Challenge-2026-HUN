"""
impacto_llegada_tarde.py  -  version 1 (25-oct-2026)
Respalda la recomendacion R6 de docs/recomendaciones.md: cuanta espera de cama se evitaria si quien llega por la tarde
esperara lo mismo que quien llega por la manana.

QUE HACE
  Con las estancias unicas con espera medida (segmentos.csv, segmento espera_cama, en_estadisticas) compara la espera de
  quienes llegan entre 13:00 y 18:59 con la de quienes llegan entre 6:00 y 11:59, y calcula las horas-paciente por dia
  que se evitarian si la espera de la tarde igualara a la de la manana, con medianas y con promedios.

ENTRADAS  datos/procesados/segmentos.csv
SALIDAS   resultados/tablas/impacto_llegada_tarde.csv

OJO AL LEER
  - Dias = del 2023-02-01 al 2026-04-10 (misma ventana que simulacion_altas.py; mayo 2026 en adelante tiene caida de datos).
  - Con medianas el ahorro es grande; con promedios es chico porque la cola larga domina. Por eso R6 es de confianza baja.
  - Es una asociacion por hora de llegada, no una causa.
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "resultados" / "tablas"
TABLAS.mkdir(parents=True, exist_ok=True)

DESDE, HASTA = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10")
TARDE, MANANA = (13, 18), (6, 11)

s = pd.read_csv(RAIZ / "datos" / "procesados" / "segmentos.csv", parse_dates=["ini"])
e = s[(s.segmento == "espera_cama") & s.en_estadisticas & (s.ini >= DESDE) & (s.ini < HASTA)]
dias = (HASTA - DESDE).days
exceso_total = e.horas.sum() / dias  # solo informativo

t = e[e.hora.between(*TARDE)]
m = e[e.hora.between(*MANANA)]
fila = {
    "dias": dias,
    "llegadas_tarde_por_dia": round(len(t) / dias, 2),
    "mediana_tarde_h": round(t.horas.median(), 1), "mediana_manana_h": round(m.horas.median(), 1),
    "media_tarde_h": round(t.horas.mean(), 1), "media_manana_h": round(m.horas.mean(), 1),
    "ahorro_h_por_dia_con_medianas": round(len(t) * (t.horas.median() - m.horas.median()) / dias, 1),
    "ahorro_h_por_dia_con_promedios": round(len(t) * (t.horas.mean() - m.horas.mean()) / dias, 1),
    "horas_espera_totales_por_dia": round(exceso_total, 1),
}
pd.DataFrame([fila]).to_csv(TABLAS / "impacto_llegada_tarde.csv", index=False)
for k, v in fila.items():
    print(f"{k}: {v}")
