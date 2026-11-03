"""
pruebas_ruido_pronostico.py  -  version 1 (1-nov-2026)
Ocho pruebas para saber cuanto del error del pronostico es ruido de conteo (que ningun modelo baja) y cuanto es estructura que falta modelar.
Usa el modelo de src/modelo_pronostico.py (calendario + nivel reciente de 28 dias en el retroceso) sobre las series 'llegadas' e 'ingresos_a_cama'.

  1. Piso de ruido 1/raiz(media) frente al error del retroceso.
  2. Indice de dispersion (varianza / media) por dia de la semana y trimestre, sin festivos.
  3. Coeficiente de variacion al agregar (diario, semanal, mensual), sin el patron por dia de la semana.
  4. Error frente a la referencia simple (mismo dia de la semana anterior y promedio de las 4 semanas anteriores).
  5. Descomposicion STL: parte de la varianza que queda en el residuo.
  6. Residuos del modelo (un dia hacia adelante): error absoluto por mes y autocorrelacion (ACF).
  7. Banda con y sin los meses posteriores a abril de 2026.
  8. Cobertura de la banda del 80 % en el retroceso (dentro de muestra y con la banda calculada solo con el pasado).

ENTRADAS  datos/procesados/para_equipo/panel_diario.csv, resultados/tablas/dias_atipicos.csv
SALIDAS   resultados/tablas/pruebas_pronostico_resumen.csv (una fila por prueba, serie y metrica) y un informe impreso.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

import modelo_pronostico as mp

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "resultados" / "tablas"
SERIES = ["llegadas_con_atencion", "llegadas", "ingresos_a_cama"]
FILAS = []


def reg(prueba, serie, metrica, valor):
    FILAS.append(dict(prueba=prueba, serie=serie, metrica=metrica, valor=round(float(valor), 4)))


def titulo(t):
    print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


crudo = pd.read_csv(mp.PANEL, parse_dates=["fecha"]).set_index("fecha")
panel = mp.cargar_panel()                                   # limpio: sin atipicos sin causa ni el corte de marzo
ANTES = panel.loc[:mp.FIN_CONFIABLE]                            # antes de la caida de datos
BT = {s: mp.retroceso(panel[s]) for s in SERIES}

# ---------------------------------------------------------------- 1. piso de ruido
titulo("1. PISO DE RUIDO (Poisson puro)")
for s in SERIES:
    mu = ANTES[s].loc["2025-05-01":].mean()                  # los 12 meses antes de la caida
    cv = 1 / np.sqrt(mu)
    wape_piso = np.sqrt(2 / np.pi) / np.sqrt(mu)             # E|X - mu| = 0,798 sigma para Poisson
    b = BT[s][BT[s].fecha < mp.INICIO_QUIEBRE]
    wape = {t: 100 * (g.real - g.pronostico).abs().sum() / g.real.sum() for t, g in
            [("1-7", b[b.lead <= 7]), ("8-30", b[(b.lead > 7) & (b.lead <= 30)]), ("183-365", b[b.lead > 182])]}
    print(f"{s}: media {mu:.1f}/dia | ruido relativo 1/raiz(media) = {100 * cv:.1f} % | piso de WAPE = {100 * wape_piso:.1f} % | "
          f"WAPE del modelo: 1-7 d {wape['1-7']:.1f} %, 8-30 d {wape['8-30']:.1f} %, 183-365 d {wape['183-365']:.1f} %")
    reg("1 piso de ruido", s, "ruido_relativo_pct", 100 * cv)
    reg("1 piso de ruido", s, "wape_piso_pct", 100 * wape_piso)
    for k, v in wape.items():
        reg("1 piso de ruido", s, f"wape_modelo_{k}_pct", v)
    reg("1 piso de ruido", s, "wape_modelo_1_7_sobre_piso", wape["1-7"] / (100 * wape_piso))

# ---------------------------------------------------------------- 2. indice de dispersion
titulo("2. INDICE DE DISPERSION (varianza / media por dia de la semana y trimestre, sin festivos)")
for s in SERIES:
    d = crudo[(~crudo.festivo.astype(bool))].copy()
    d["trim"] = d.index.to_period("Q")
    g = d.groupby(["dia_semana_num", "trim"])[s]
    disp = (g.var() / g.mean()).rename("disp").reset_index()
    print(f"\n{s}: indice de dispersion (n = {len(disp)} grupos de ~12 dias)")
    print(disp.disp.describe().round(2).to_string())
    por_trim = disp.groupby("trim").disp.median().round(2)
    print("mediana por trimestre:", por_trim.to_dict())
    reg("2 dispersion", s, "mediana", disp.disp.median())
    reg("2 dispersion", s, "p90", disp.disp.quantile(0.9))
    reg("2 dispersion", s, "mediana_2026Q1", por_trim.get(pd.Period("2026Q1"), np.nan))
    reg("2 dispersion", s, "mediana_2026Q2", por_trim.get(pd.Period("2026Q2"), np.nan))
    reg("2 dispersion", s, "mediana_2025", por_trim[[p for p in por_trim.index if p.year == 2025]].median())

# ---------------------------------------------------------------- 3. agregacion
titulo("3. COEFICIENTE DE VARIACION AL AGREGAR (sin el patron por dia de la semana)")
for s in SERIES:
    y = panel[s].loc[:mp.FIN_CONFIABLE]
    fd = y.groupby(y.index.dayofweek).transform("mean") / y.mean()
    z = (y / fd)                                              # serie sin el efecto del dia de la semana
    for nombre, zz in [("con el nivel de largo plazo", z), ("sin el nivel de largo plazo (media movil de 91 dias)", z / z.rolling(91, center=True, min_periods=45).mean())]:
        zz = zz.dropna()
        diario = zz.std() / zz.mean()
        semanal = zz.resample("W").mean().iloc[1:-1]
        mensual = zz.resample("MS").mean().iloc[1:-1]
        cvs = [diario, semanal.std() / semanal.mean(), mensual.std() / mensual.mean()]
        print(f"{s} [{nombre}]: CV diario {100 * cvs[0]:.1f} % | semanal {100 * cvs[1]:.1f} % (baja x{cvs[0] / cvs[1]:.1f}; esperado x2,6 si es ruido) | "
              f"mensual {100 * cvs[2]:.1f} % (x{cvs[0] / cvs[2]:.1f}; esperado x5,5)")
        k = "nivel_largo" if nombre.startswith("con") else "sin_nivel_largo"
        reg("3 agregacion", s, f"cv_diario_{k}_pct", 100 * cvs[0])
        reg("3 agregacion", s, f"reduccion_semanal_{k}", cvs[0] / cvs[1])
        reg("3 agregacion", s, f"reduccion_mensual_{k}", cvs[0] / cvs[2])

# ---------------------------------------------------------------- 4. referencia simple
titulo("4. ERROR FRENTE A LA REFERENCIA SIMPLE (mismos dias, 1 a 7 dias hacia adelante, antes de mayo de 2026)")
for s in SERIES:
    b = BT[s][(BT[s].lead <= 7) & (BT[s].fecha < mp.INICIO_QUIEBRE)].copy()
    ser = panel[s]
    b["semana_ant"] = ser.reindex(b.fecha - pd.Timedelta(days=7)).values
    b["prom4"] = np.nanmean(np.vstack([ser.reindex(b.fecha - pd.Timedelta(days=7 * k)).values for k in (1, 2, 3, 4)]), axis=0)
    b = b.dropna(subset=["semana_ant", "prom4", "real"])
    w = lambda p: 100 * (b.real - p).abs().sum() / b.real.sum()
    wm, w1, w4 = w(b.pronostico), w(b.semana_ant), w(b.prom4)
    print(f"{s}: WAPE modelo {wm:.1f} % | mismo dia semana anterior {w1:.1f} % (el modelo mejora {100 * (1 - wm / w1):.0f} %) | "
          f"promedio de 4 semanas {w4:.1f} % (mejora {100 * (1 - wm / w4):.0f} %) | n = {len(b)}")
    reg("4 referencia", s, "wape_modelo", wm)
    reg("4 referencia", s, "wape_semana_anterior", w1)
    reg("4 referencia", s, "wape_prom_4_semanas", w4)
    reg("4 referencia", s, "mejora_vs_semana_anterior_pct", 100 * (1 - wm / w1))
    reg("4 referencia", s, "mejora_vs_prom_4_semanas_pct", 100 * (1 - wm / w4))

# ---------------------------------------------------------------- 5. STL
titulo("5. DESCOMPOSICION STL (parte de la varianza que queda en el residuo)")
for s in SERIES:
    y = panel[s].loc[:mp.FIN_CONFIABLE].interpolate()
    for nombre, serie, per in [("diaria (periodo 7)", y, 7), ("semanal (periodo 52)", y.resample("W").mean().iloc[1:-1], 52)]:
        r = STL(serie, period=per, robust=True).fit()
        tot = serie.var()
        res = r.resid.var() / tot
        print(f"{s} {nombre}: residuo {100 * res:.0f} % de la varianza | tendencia {100 * r.trend.var() / tot:.0f} % | estacional {100 * r.seasonal.var() / tot:.0f} %")
        reg("5 STL", s, f"residuo_{nombre.split()[0]}_pct_varianza", 100 * res)

# ---------------------------------------------------------------- 6. residuos
titulo("6. RESIDUOS DEL MODELO A UN DIA (nivel de los ultimos 28 dias)")
for s in SERIES:
    ser = panel[s]
    cal = mp.calendario(pd.date_range(ser.index.min(), ser.index.max() + pd.Timedelta(days=2)))
    res = {}
    for pos in range(400, len(ser) - 1):
        corte = ser.index[pos]
        f = mp.pronosticar_desde(ser.iloc[:pos + 1], cal, corte, 1, "reciente")
        real = ser.iloc[pos + 1]
        if not np.isnan(real):
            res[f.index[0]] = (real - f.iloc[0]) / f.iloc[0]
    r = pd.Series(res)
    mensual = r.abs().groupby(r.index.to_period("M")).mean() * 100
    print(f"\n{s}: error absoluto relativo medio por mes (%):")
    print(mensual.tail(14).round(1).to_string())
    antes, despues = r.loc[:mp.FIN_CONFIABLE].abs().mean() * 100, r.loc[mp.INICIO_QUIEBRE:].abs().mean() * 100
    print(f"  antes de mayo de 2026: {antes:.1f} % | desde mayo de 2026: {despues:.1f} %")
    reg("6 residuos", s, "error_abs_antes_mayo26_pct", antes)
    reg("6 residuos", s, "error_abs_desde_mayo26_pct", despues)
    rr = r.loc[:mp.FIN_CONFIABLE]
    rr = rr - rr.mean()
    n = len(rr)
    acf = [float((rr.iloc[k:].values * rr.iloc[:n - k].values).sum() / (rr ** 2).sum()) for k in range(1, 15)]
    umbral = 1.96 / np.sqrt(n)
    print("  ACF de los residuos (lags 1 a 14):", [round(a, 2) for a in acf], f"| umbral 95 % = +-{umbral:.2f}",
          "| lags fuera del umbral:", [k + 1 for k, a in enumerate(acf) if abs(a) > umbral])
    reg("6 residuos", s, "acf_lag1", acf[0])
    reg("6 residuos", s, "acf_lag7", acf[6])
    reg("6 residuos", s, "n_lags_fuera_umbral_de_14", sum(abs(a) > umbral for a in acf))

# ---------------------------------------------------------------- 7. efecto del quiebre en la banda
titulo("7. BANDA DEL 80 % CON Y SIN LOS MESES POSTERIORES A ABRIL DE 2026")
for s in SERIES:
    bt = BT[s]
    print(f"\n{s}: percentiles 10 y 90 de real / pronostico (ancho = p90 - p10)")
    for ex, nombre in [(False, "con la caida"), (True, "sin destinos desde mayo de 2026")]:
        fb = mp.factores_banda(bt, ex)
        txt = " | ".join(f"{a}-{b} d: {lo:.2f}-{hi:.2f}" for (a, b), (lo, hi) in fb.items())
        print(f"  {nombre:36s} {txt}")
        for (a, b), (lo, hi) in fb.items():
            reg("7 quiebre", s, f"ancho_banda_{a}_{b}_{'sin' if ex else 'con'}_caida", hi - lo)
    ancho = lambda ex, t: np.subtract(*mp.factores_banda(bt, ex)[t][::-1])
    print(f"  la banda de 183-365 dias se angosta {100 * (1 - ancho(True, (183, 365)) / ancho(False, (183, 365))):.0f} % al quitar la caida")

# ---------------------------------------------------------------- 8. cobertura
titulo("8. COBERTURA DE LA BANDA DEL 80 % EN EL RETROCESO")
for s in SERIES:
    bt = BT[s].copy()
    bt["r"] = bt.real / bt.pronostico
    print(f"\n{s}:")
    filas = []
    for a, b in mp.TRAMOS:
        t = bt[(bt.lead >= a) & (bt.lead <= b)]
        te = t[t.fecha < mp.INICIO_QUIEBRE]
        lo, hi = te.r.quantile(0.1), te.r.quantile(0.9)
        dentro = ((te.r >= lo) & (te.r <= hi)).mean()                       # dentro de muestra (sin la caida)
        entr, prueba = te[te.corte < "2025-07-01"], te[te.corte >= "2025-07-01"]   # banda con el pasado, probada en el futuro
        lo2, hi2 = entr.r.quantile(0.1), entr.r.quantile(0.9)
        fuera = ((prueba.r >= lo2) & (prueba.r <= hi2)).mean() if len(prueba) > 30 else np.nan
        con_caida = ((t.r >= lo) & (t.r <= hi)).mean()                      # la banda sin la caida, aplicada a todos los destinos
        filas.append((f"{a}-{b}", len(te), dentro, fuera, con_caida))
        reg("8 cobertura", s, f"cobertura_dentro_{a}_{b}_pct", 100 * dentro)
        reg("8 cobertura", s, f"cobertura_fuera_muestra_{a}_{b}_pct", 100 * fuera)
        reg("8 cobertura", s, f"cobertura_con_caida_{a}_{b}_pct", 100 * con_caida)
    print(pd.DataFrame(filas, columns=["tramo_dias", "n", "dentro_de_muestra", "banda_con_pasado_probada_despues", "incluyendo_destinos_de_la_caida"])
          .assign(**{c: lambda x, c=c: (100 * x[c]).round(0) for c in ["dentro_de_muestra", "banda_con_pasado_probada_despues", "incluyendo_destinos_de_la_caida"]})
          .to_string(index=False))

pd.DataFrame(FILAS).to_csv(TABLAS / "pruebas_pronostico_resumen.csv", index=False)
print("\nguardado: resultados/tablas/pruebas_pronostico_resumen.csv")
