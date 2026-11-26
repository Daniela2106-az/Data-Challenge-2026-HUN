"""
src/impacto_presentacion.py  -  cifras fijas de la presentacion de la final (26-nov-2026, version 2)

Corre el simulador integral 90 dias (el plazo «90 días» del simulador del dashboard) desde el ultimo dia confiable (9-abr-2026), 400 repeticiones
y semilla fija, en estos escenarios:
  hoy               operacion como en 2025
  optima            hoy + R7 (gestion de las estancias de mas de 14 dias, 15 % menos) + R4 (30 % de las altas de la tarde a la mañana)
  estancia_m5       hoy con la estancia 5 % mas corta
  alta              temporada alta: llega 10 % mas pacientes (el caso que se reproduce en vivo en la presentacion)
  alta_optima       temporada alta + la mejora que propone la propia alerta del simulador en ese caso (R7 15 % + R4 30 %)
  tu_doble          llega el doble de pacientes por «Treatment urgency»
Para cada uno: camas ocupadas en promedio, % de dias-repeticion sobre las 106 camas, cola media, camas que faltan en promedio (sobre 106),
ingresos a cama por dia y las camas que harian falta para superar la capacidad solo 1 de cada 10 dias.
dashboard/pages/presentacion.py copia estos valores en IMPACTO.

Uso:  python src/impacto_presentacion.py [salida.json]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simulador_integral as si  # noqa: E402
import simulacion_camas_montecarlo as scm  # noqa: E402

CAP = scm.CAPACIDAD["total"]
DIAS, N = 90, 400
MOD = [k for k in ("dengue", "lluvia", "ira", "eda") if k in si.MODELOS_DISPONIBLES]
RUTA = dict(si.RUTA_MARG_LLEG)
TU = [k for k in RUTA if "reatment" in k][0]
RUTA_TU = {k: (v * 2 if k == TU else v) for k, v in RUTA.items()}
RUTA_TU = {k: v / sum(RUTA_TU.values()) for k, v in RUTA_TU.items()}
OPTIMA = dict(recorte_largas_pct=15, adelanto_altas_pct=30)
ESCENARIOS = [("hoy", {}), ("optima", OPTIMA), ("estancia_m5", dict(ajuste_estancia=0.95)), ("alta", dict(ajuste_llegadas=1.10)),
              ("alta_optima", dict(ajuste_llegadas=1.10, **OPTIMA)), ("tu_doble", dict(mezcla_ruta=RUTA_TU))]


def camas_para_10(t):
    """Camas con las que se superaria la capacidad solo 1 de cada 10 dias-repeticion."""
    for c in range(96, 200):
        if (t > c).mean() <= 0.10:
            return c
    return None


res = {}
for nombre, k in ESCENARIOS:
    o = si.simular_integral(scm.ULTIMO_CONFIABLE, DIAS, n_rep=N, acoplar_estancia=True, modelos=MOD, casos={}, **k)[1]
    t = o["total"]
    res[nombre] = dict(camas=round(float(t.mean()), 1), sat=round(100 * float((t > CAP).mean()), 1), cola=round(float(o["cola"].mean()), 1),
                       faltan=round(float(np.maximum(t - CAP, 0).mean()), 2), ingresos=round(float(o["ingresos_cama"].mean()), 2), cap10=camas_para_10(t))
    print(nombre, res[nombre], flush=True)
if len(sys.argv) > 1:
    json.dump(res, open(sys.argv[1], "w"), indent=1)
