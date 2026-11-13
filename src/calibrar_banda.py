"""
calibrar_banda.py  -  version 1 (12-nov-2026)  ·  ficha A9, tercera ronda: ¿hay que recalibrar la banda del 80 % con el guardarrail de Anthony?

POR QUE: NIVEL_BANDA (A9, src/estacionalidad_extra.py) se eligio con el retroceso 'reciente' cada 14 dias y SIN el guardarrail de no-angostamiento
(rama pronostico-banda-estacionalidad, `_ensanchar_monotona`). Al juntar las dos cosas, la cobertura medida SOBRE LOS MISMOS CORTES con que se arma
la banda (tabla_error) llegaba a 88 % en los tramos largos. Este script mira si eso es real fuera de muestra y si otra calibracion lo hace mejor.

COMO: para cada objetivo y escenario ('reciente', 'historico'), retroceso cada 7 dias con el escenario del pronostico (como pronostico_futuro.py),
y la banda SIEMPRE con el guardarrail. Se comparan tres reglas para el percentil q de cada tramo:
  - "q=0,10 fijo": percentiles 10 y 90 en todos los tramos (lo que habia antes de A9).
  - "NIVEL_BANDA A9": los niveles vigentes.
  - "recalibrado": en la validacion (factores con destinos antes del 1-ene-2025, cobertura en destinos ene-jun 2025) se recorren los tramos de corto a
    largo y en cada uno se elige el q MAS GRANDE (banda mas angosta) de REJILLA cuya cobertura, con el guardarrail ya aplicado a los tramos anteriores,
    sea >= 80 %. La rejilla va de 0,03 a 0,20, para poder angostar y no solo ensanchar.
  Prueba (no se usa para elegir): factores con destinos antes del 1-jul-2025, cobertura en jul-2025 a 9-abr-2026.

RESULTADO (12-nov-2026; distancia media a 80 % en la prueba, promedio de 6 combinaciones objetivo x escenario / peor tramo):
  NIVEL_BANDA A9  4,7 puntos / 77,8 %   <- se queda (empata en distancia con q=0,10, pero su peor tramo es mucho mejor)
  q=0,10 fijo     4,7 puntos / 72,2 %
  recalibrado     6,8 puntos / 66,0 %
  - Llegadas con atencion (la serie principal): con A9 la prueba cubre 79-82 % ('reciente') y 78-82 % ('historico'). La validacion decia lo contrario
    (A9 cubria 84-88 % ahi y pedia angostar hasta q = 0,20), y al hacerle caso la prueba cae a 66 %: ene-jun 2025 fue un semestre mas tranquilo que
    jul-2025 a abr-2026 (las etapas TU ya bajaban desde ene-2026, CLAUDE.md 4.9). Recalibrar sobre ese semestre es sobreajustar.
  - Ingresos a cama: con A9 la banda cubre 85-93 % en la prueba (sobra ancho). Ninguna regla elegida SOLO con la validacion lo arregla sin
    romper las llegadas con atencion, y elegir una regla por serie mirando la prueba seria hacer trampa. Se acepta: la banda de ingresos es
    conservadora, lo que para planear camas es el error menos grave.
  - Llegadas (todas): A9 no tiene niveles propios (q = 0,10): 79-87 % en la prueba.
Conclusion: NIVEL_BANDA no cambia. El guardarrail y los niveles de A9 conviven bien fuera de muestra; el 88 % de tabla_error es en muestra.

DATOS  HUN_PROCESADOS/para_equipo/panel_diario.csv.  SALIDA HUN_TABLAS/calibrar_banda.csv (una fila por objetivo, escenario, regla y tramo).
COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... python src/calibrar_banda.py   (~2 min)
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modelo_pronostico as mp  # noqa: E402

TABLAS = Path(os.environ.get("HUN_TABLAS", mp.RAIZ / "resultados" / "tablas"))
VAL = ("2025-01-01", "2025-01-01", "2025-06-30")             # factores con destinos antes de / evaluar desde / hasta
PRUEBA = ("2025-07-01", "2025-07-01", mp.FIN_CONFIABLE)
REJILLA = [0.20, 0.18, 0.16, 0.15, 0.14, 0.13, 0.12, 0.11, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03]   # de angosta a ancha
META = 80.0


def _razones(bt, hasta):
    """real / pronostico por tramo, solo con destinos anteriores a `hasta`."""
    out = {}
    for a, b in mp.TRAMOS:
        e = bt[(bt.lead >= a) & (bt.lead <= b) & (bt.fecha < hasta)]
        out[(a, b)] = e.real / e.pronostico
    return out


def _cobertura(bt, factores, desde, hasta):
    """% de dias destino entre `desde` y `hasta` que caen dentro de la banda, por tramo."""
    out = {}
    for (a, b), (lo, hi) in factores.items():
        t = bt[(bt.lead >= a) & (bt.lead <= b) & (bt.fecha >= desde) & (bt.fecha <= hasta)]
        out[(a, b)] = 100 * ((t.real >= t.pronostico * lo) & (t.real <= t.pronostico * hi)).mean() if len(t) >= 30 else float("nan")
    return out


def factores(razones, qs):
    """Igual que mp.factores_banda: percentiles q y 1-q por tramo y luego el guardarrail monotono."""
    res = {k: ((float(r.quantile(qs[k])), float(r.quantile(1 - qs[k]))) if len(r) >= 30 else (0.8, 1.2)) for k, r in razones.items()}
    return mp._ensanchar_monotona(res)


def calibrar(bt):
    """q por tramo, de corto a largo: el mas grande (banda mas angosta) que cubre >= META en la validacion con el guardarrail puesto."""
    rv = _razones(bt, VAL[0])
    qs = {}
    for k in mp.TRAMOS:
        elegido = REJILLA[-1]
        for q in REJILLA:
            prueba = {**qs, k: q, **{j: 0.10 for j in mp.TRAMOS if j not in qs and j != k}}
            if _cobertura(bt, factores(rv, prueba), *VAL[1:])[k] >= META:
                elegido = q
                break
        qs[k] = elegido
    return qs


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    panel = mp.cargar_panel()
    filas = []
    for obj in mp.OBJETIVOS:
        serie = panel[obj].copy(); serie.name = obj
        for esc in ("reciente", "historico"):
            bt = mp.retroceso(serie, paso=7, escenario=esc)
            reglas = {"q=0,10 fijo": {k: 0.10 for k in mp.TRAMOS},
                      "NIVEL_BANDA A9": {k: mp.NIVEL_BANDA.get(obj, {}).get(k, 0.10) for k in mp.TRAMOS},
                      "recalibrado": calibrar(bt)}
            for nombre, q in reglas.items():
                cv = _cobertura(bt, factores(_razones(bt, VAL[0]), q), *VAL[1:])
                fp = factores(_razones(bt, PRUEBA[0]), q)
                cp = _cobertura(bt, fp, *PRUEBA[1:])
                for k in mp.TRAMOS:
                    filas.append(dict(objetivo=obj, escenario=esc, regla=nombre, tramo_dias=f"{k[0]}-{k[1]}", q=q[k],
                                      cobertura_validacion=round(cv[k], 1), cobertura_prueba=round(cp[k], 1),
                                      ancho_relativo=round(fp[k][1] - fp[k][0], 3)))
            print(obj, esc, "q recalibrado:", list(reglas["recalibrado"].values()), flush=True)
    res = pd.DataFrame(filas)
    TABLAS.mkdir(parents=True, exist_ok=True)
    res.to_csv(TABLAS / "calibrar_banda.csv", index=False)
    print(res.pivot_table(index=["objetivo", "escenario", "tramo_dias"], columns="regla", values="cobertura_prueba").round(1).to_string())
    res["dist"] = (res.cobertura_prueba - META).abs()
    g = res.groupby(["regla", "objetivo", "escenario"]).agg(dist=("dist", "mean"), peor=("cobertura_prueba", "min")).groupby("regla")
    print("\nResumen en la prueba (distancia media a 80 % y peor tramo):")
    print(pd.DataFrame({"distancia_media": g.dist.mean().round(1), "peor_tramo": g.peor.min().round(1)}).to_string())
