"""
comparacion_banda_caida.py  -  version 1 (1-nov-2026)
Compara el ANCHO de la banda del 80 % del pronostico segun si el modelo vio o no la caida de 2026. Mismo modelo, mismas tres series, mismo
periodo pronosticado (1-jul-2026 a 30-abr-2027); cambia solo lo que el modelo conocia:

  A  "sin caida":  datos hasta 2025-12-31. La banda sale solo de errores de antes de 2026.
  B  "con caida":  datos hasta 2026-05-31. El calendario se ajusta con todo, el nivel historico incluye los meses de la caida y la banda
                   cuenta tambien los errores de dias destino de mayo de 2026 en adelante.
  C  "foto del dash": datos hasta 2026-05-31, pero como esta hoy el dashboard: el calendario y el nivel historico se calculan hasta 2026-04-30
                   y la banda NO cuenta los dias destino desde mayo de 2026 (ver modelo_pronostico.ENTRENA_HASTA y factores_banda).

ANCHO RELATIVO = (banda_alta - banda_baja) / pronostico.
  - En este modelo el ancho relativo depende solo de cuantos dias hacia adelante se pronostica (tramos de la banda), no del nivel ni de la serie
    graficada. Se compara de dos formas: (1) a los mismos dias hacia adelante (30, 90, 180, 300) contando desde el ultimo dato de cada corrida,
    y (2) en las mismas fechas de calendario (julio 2026 a abril 2027), que para A son plazos mas largos (181 a 485 dias).

SALIDAS  resultados/tablas/comparacion_banda_caida_diario.csv  (un dia por fila, por serie y corrida)
         resultados/tablas/comparacion_banda_caida_resumen.csv (ancho relativo por plazo y por mes)
"""
from pathlib import Path

import numpy as np
import pandas as pd

import modelo_pronostico as mp

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "resultados" / "tablas"
DESDE, HASTA = pd.Timestamp("2026-07-01"), pd.Timestamp("2027-04-30")
CORRIDAS = {"A sin caída (hasta 2025-12)": dict(corte="2025-12-31", entrena="2026-04-30", excluir_caida=False),
            "B con caída (hasta 2026-05)": dict(corte="2026-05-31", entrena="2026-05-31", excluir_caida=False),
            "C foto del dash (hasta 2026-05, nivel y banda sin la caída)": dict(corte="2026-05-31", entrena="2026-04-30", excluir_caida=True)}
ENTRENA_ORIGINAL = mp.ENTRENA_HASTA

panel = mp.cargar_panel()
diario = []
for obj in mp.OBJETIVOS:
    for nombre, c in CORRIDAS.items():
        mp.ENTRENA_HASTA = c["entrena"]
        serie = panel[obj].loc[:c["corte"]]
        dias = (HASTA - pd.Timestamp(c["corte"])).days
        bt = mp.retroceso(serie)
        f = mp.pronostico_con_banda(serie, bt, dias, "historico", 0.0, c["excluir_caida"])
        f["ancho_relativo"] = (f.banda_alta - f.banda_baja) / f.pronostico
        f.insert(0, "corrida", nombre)
        f.insert(0, "serie", obj)
        diario.append(f)
mp.ENTRENA_HASTA = ENTRENA_ORIGINAL

d = pd.concat(diario, ignore_index=True)
for c in ["pronostico", "banda_baja", "banda_alta"]:
    d[c] = d[c].round(1)
d["ancho_relativo"] = d.ancho_relativo.round(3)
d["fecha"] = d.fecha.dt.strftime("%Y-%m-%d")
d_jul = d[(d.fecha >= "2026-07-01") & (d.fecha <= "2027-04-30")]
d_jul.to_csv(TABLAS / "comparacion_banda_caida_diario.csv", index=False)

# (1) mismos dias hacia adelante
filas = []
for (s, c), g in d.groupby(["serie", "corrida"]):
    fila = {"serie": s, "corrida": c}
    for k in (30, 90, 180, 300):
        fila[f"ancho_a_{k}_dias_%"] = round(100 * g.loc[g.dias_adelante == k, "ancho_relativo"].iloc[0], 1)
    # (2) mismas fechas
    j = g[(g.fecha >= "2026-07-01") & (g.fecha <= "2027-04-30")]
    fila["ancho_jul26_abr27_%"] = round(100 * j.ancho_relativo.mean(), 1)
    fila["pronostico_prom_jul26_abr27"] = round(j.pronostico.mean(), 1)
    fila["plazo_en_jul26_abr27"] = f"{int(j.dias_adelante.min())}-{int(j.dias_adelante.max())}"
    filas.append(fila)
res = pd.DataFrame(filas)
res.to_csv(TABLAS / "comparacion_banda_caida_resumen.csv", index=False)
pd.set_option("display.width", 250)
print(res.to_string(index=False))
print("\nancho relativo medio por mes (%), llegadas con atención:")
m = d_jul[d_jul.serie == "llegadas_con_atencion"].assign(mes=lambda x: x.fecha.str[:7]).pivot_table(index="mes", columns="corrida", values="ancho_relativo") * 100
print(m.round(1).to_string())
