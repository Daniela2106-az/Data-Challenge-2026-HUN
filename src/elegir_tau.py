"""
elegir_tau.py  -  version 1 (1-nov-2026)
Elige por serie el parametro tau de la correccion de corto plazo (modelo_pronostico.TAU) con la validacion (destinos hasta 2025-12-31)
y lo confirma en la prueba (2026-01-01 a 2026-04-30), que no se usa para elegir. tau = 0 es "sin correccion".
"""
import pandas as pd

import modelo_pronostico as mp

panel = mp.cargar_panel()
for obj in mp.OBJETIVOS:
    print(f"\n{obj}: WAPE (%) segun tau; validacion = destinos hasta 2025-12-31, prueba = 2026-01 a 9-abr-2026")
    filas = []
    for tau in [0, 2, 4, 7, 14, 30]:
        mp.TAU = {obj: float(tau)}
        bt = mp.retroceso(panel[obj])
        fila = {"tau": tau}
        for nombre, f in [("validacion", (bt.fecha <= "2025-12-31")), ("prueba", (bt.fecha >= "2026-01-01") & (bt.fecha < mp.INICIO_QUIEBRE))]:
            for a, b in [(1, 7), (8, 30)]:
                t = bt[f & (bt.lead >= a) & (bt.lead <= b)]
                fila[f"{nombre} {a}-{b} d"] = round(100 * (t.real - t.pronostico).abs().sum() / t.real.sum(), 2)
        filas.append(fila)
    d = pd.DataFrame(filas)
    print(d.to_string(index=False))
    mejor = d.loc[(d["validacion 1-7 d"] + d["validacion 8-30 d"]).idxmin(), "tau"]
    print(f"-> tau elegido en validacion: {mejor}")
