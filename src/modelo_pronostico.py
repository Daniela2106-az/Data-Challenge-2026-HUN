"""
modelo_pronostico.py  -  version 1 (1-nov-2026)
Modelo de serie de tiempo como LIBRERIA (se importa; no imprime ni escribe nada). Lo usan:
  - src/pronostico_futuro.py            genera las tablas de pronostico a 365 dias y el error por horizonte
  - dashboard/app.py                    el dashboard en Dash: el modelo corre cuando el usuario elige el horizonte
  - src/simulacion_llamada_dashboard.py (simulacion de tiempos)

QUE HACE
  Regresion de Poisson (enlace log) sobre el CALENDARIO: dia de la semana, festivos de Colombia (entre semana y en fin de semana
  por separado), vispera y dia despues de festivo, 24/31 de diciembre, 25 de diciembre y 1 de enero, semana santa y Carnaval de
  Barranquilla. Es el mismo calendario de pronostico_demanda.py v1.3. Se entrena SOLO con los dias antes de la caida de datos
  (por defecto, hasta 2026-04-30).
  El NIVEL (cuantos pacientes llegan "en general") no lo da el calendario: se fija con un ESCENARIO que el usuario elige:
    - "historico":  (por defecto) el nivel de los 12 meses antes de la caida (hasta 2026-04-30). Trata la caida sin explicar como
                    un posible problema de datos y NO la usa.
    - "reciente":   el nivel de los ultimos 28 dias con datos (ya incluye la caida de mayo de 2026, que puede ser carga incompleta).
    - ajuste_pct:   un porcentaje adicional sobre el nivel elegido (por ejemplo -10 o +5), para probar hipotesis.
  Pronostico del dia = nivel x efecto de calendario de ese dia.

DIAS ATIPICOS Y CAIDA SIN EXPLICAR (decision del 1-nov-2026)
  Los dias atipicos sin causa de calendario (src/dias_atipicos.py) no entran al ajuste, al nivel ni a la medicion del error, y el
  ancho de la banda no cuenta los dias destino desde mayo de 2026. Si la caida es real y no un problema de datos, este pronostico
  sobrestima: por eso el escenario "reciente" sigue disponible.

BANDA DEL 80 %
  Sale de un RETROCESO (backtest): se pronostica desde muchos cortes del pasado (cada 14 dias) con la regla "reciente" y se mide
  real / pronostico segun cuantos dias hacia adelante se pronostica. La banda usa los percentiles 10 y 90 de esas razones por tramo
  (1-7, 8-30, 31-91, 92-182, 183-365 dias), asi que se ensancha con el horizonte. Es empirica y aproximada: hay pocos cortes para
  los tramos largos.

LIMITES (decirlos siempre junto al grafico)
  - A mas de unas semanas solo hay calendario y nivel supuesto: NO sabe de brotes, cortes de sistema, estacionalidad anual ni de por
    que las llegadas caen desde abril de 2026. El escenario elegido decide casi todo el nivel.
  - Las llegadas incluyen al menos 4 % de replicas (CLAUDE.md 4.6). Los ingresos diarios son casi ruido de conteo.
"""
from pathlib import Path

import os

import holidays
import numpy as np
import pandas as pd
from dateutil.easter import easter

RAIZ = Path(__file__).resolve().parent.parent
# Donde buscar panel_diario.csv (9-nov), en este orden: HUN_PANEL (ruta exacta); el "Secret File" de Render (/etc/secrets/panel_diario.csv, asi el
# archivo no pasa por GitHub); HUN_PROCESADOS/para_equipo (datos fuera del proyecto); datos/procesados/para_equipo del proyecto.
_CANDIDATOS = [os.environ.get("HUN_PANEL"), "/etc/secrets/panel_diario.csv",
               Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados")) / "para_equipo" / "panel_diario.csv"]
PANEL = next((Path(c) for c in _CANDIDATOS if c and Path(c).exists()), RAIZ / "datos" / "procesados" / "para_equipo" / "panel_diario.csv")
OBJETIVOS = {"llegadas_con_atencion": "Llegadas con atención por día (TU u hospitalización)", "llegadas": "Llegadas por día (todas)",
             "ingresos_a_cama": "Ingresos a cama por día"}
# Auditoria en la base (CLAUDE.md 4.9, 2-nov-2026): el registro de las etapas es confiable hasta el 9-abr-2026. Desde el 10-abr aparecen visitas de mas sin etapas
# y baja la proporcion de visitas con etapa ER (65 % -> 52 %); desde el 29-abr cae a ~30 %. Esos dias NO se usan para estimar nivel, calendario ni error.
FIN_CONFIABLE = "2026-04-09"
INICIO_QUIEBRE = "2026-04-10"
ENTRENA_HASTA = FIN_CONFIABLE
VENTANA_RECIENTE = 28
# Correccion de corto plazo ("sorpresa"): si los ultimos 7 dias vinieron mas altos o bajos que el nivel de 28 dias, esa desviacion se
# arrastra a los primeros dias del pronostico y se desvanece como exp(-dias_adelante / tau). tau = 0 la apaga. Se elige por serie con
# src/elegir_tau.py usando solo la validacion (hasta 2025-12) y se confirma en 2026-01 a 2026-04.
TAU = {"llegadas": 14.0, "llegadas_con_atencion": 0.0, "ingresos_a_cama": 0.0}   # elegido con elegir_tau.py; ingresos: la correccion no ayuda
VENTANA_CORTA = 7
TRAMOS = [(1, 7), (8, 30), (31, 91), (92, 182), (183, 365)]
COLUMNAS = ["const", "dow_1", "dow_2", "dow_3", "dow_4", "dow_5", "dow_6", "fest_habil", "fest_finde", "vispera", "despues",
            "bajo_fin", "alto_fin", "semana_santa", "carnaval"]


ATIPICOS = RAIZ / "resultados" / "tablas" / "dias_atipicos.csv"
NOMBRE_ATIPICO = {"llegadas": "llegadas", "llegadas_con_atencion": "llegadas", "ingresos_a_cama": "ingresos a cama"}


# Rangos que se quitan a mano porque no tienen explicacion real (decision del 1-nov-2026). 28 y 29 de marzo de 2026: corte de registro
# (88 y 123 llegadas con ~1 ingreso a cama). La semana santa (2 al 5 de abril de 2026) NO se quita: el calendario la explica.
EXCLUIR_RANGOS = [("2026-03-28", "2026-03-29")]


def cargar_panel(ruta=PANEL, limpiar=True, excluir_rangos=None):
    """Panel diario. Con limpiar=True los dias atipicos SIN causa de calendario (cortes de sistema, caidas puntuales; src/dias_atipicos.py)
    quedan vacios: no entran al ajuste, al nivel ni a la medicion del error. Los festivos y demas dias que el calendario explica se quedan."""
    d = pd.read_csv(ruta, parse_dates=["fecha"]).set_index("fecha").asfreq("D")[list(OBJETIVOS)]
    if limpiar:
        d.loc[INICIO_QUIEBRE:, :] = np.nan                       # el registro de etapas se degrada desde el 10-abr-2026
    if limpiar and ATIPICOS.exists():
        a = pd.read_csv(ATIPICOS, parse_dates=["fecha"])
        a = a[a.causa_calendario.str.contains("sin causa", na=False)]
        for col, nombre in NOMBRE_ATIPICO.items():
            d.loc[d.index.isin(a.loc[a.variable == nombre, "fecha"]), col] = np.nan
    for ini, fin in (EXCLUIR_RANGOS if excluir_rangos is None else excluir_rangos) if limpiar else []:
        d.loc[ini:fin, :] = np.nan
    return d


def calendario(idx):
    """Variables de calendario para cualquier rango de fechas (pasado o futuro)."""
    idx = pd.DatetimeIndex(idx)
    fest = holidays.Colombia(years=range(idx.min().year - 1, idx.max().year + 2))
    es_fest = pd.Series([d.date() in fest for d in idx], index=idx)
    dow = pd.Series(idx.dayofweek, index=idx)
    c = pd.DataFrame(index=idx)
    c["const"] = 1.0
    for k in range(1, 7):
        c[f"dow_{k}"] = (dow == k).astype(float)
    c["fest_habil"] = (es_fest & (dow < 5)).astype(float)
    c["fest_finde"] = (es_fest & (dow >= 5)).astype(float)
    c["vispera"] = es_fest.shift(-1, fill_value=False).astype(float)
    c["despues"] = es_fest.shift(1, fill_value=False).astype(float)
    c["bajo_fin"] = ((idx.month == 12) & np.isin(idx.day, [24, 31])).astype(float)
    c["alto_fin"] = (((idx.month == 12) & (idx.day == 25)) | ((idx.month == 1) & (idx.day == 1))).astype(float)
    c["semana_santa"] = 0.0
    c["carnaval"] = 0.0
    for a in range(idx.min().year, idx.max().year + 1):
        e = pd.Timestamp(easter(a))
        c.loc[(idx >= e - pd.Timedelta(days=7)) & (idx <= e), "semana_santa"] = 1.0
        c.loc[(idx >= e - pd.Timedelta(days=50)) & (idx <= e - pd.Timedelta(days=47)), "carnaval"] = 1.0
    return c[COLUMNAS]


def poisson_fit(X, y, ridge=1e-4, iters=60):
    """Regresion de Poisson (enlace log) por minimos cuadrados reponderados (igual que pronostico_demanda.py)."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    beta = np.zeros(X.shape[1])
    beta[0] = np.log(y.mean())
    for _ in range(iters):
        eta = np.clip(X @ beta, -20, 20)
        mu = np.exp(eta)
        z = eta + (y - mu) / mu
        nuevo = np.linalg.solve(X.T @ (X * mu[:, None]) + ridge * np.eye(X.shape[1]), X.T @ (mu * z))
        converge = np.abs(nuevo - beta).max() < 1e-8
        beta = nuevo
        if converge:
            break
    return beta


def _ajustar(serie, cal, corte):
    """Entrena con los dias <= corte. Devuelve los coeficientes."""
    m = (serie.index <= corte) & serie.notna().values
    return poisson_fit(cal.reindex(serie.index).loc[m].values, serie[m].values)


def _nivel_ventana(serie, cal, beta, ultimo, dias):
    """Factor de nivel con una ventana de `dias` dias que termina en `ultimo`."""
    ini = ultimo - pd.Timedelta(days=dias - 1)
    m = (serie.index >= ini) & (serie.index <= ultimo) & serie.notna().values
    return serie[m].sum() / np.exp(cal.loc[m].values @ beta).sum()


def _nivel(serie, cal, beta, escenario, ultimo):
    """Factor que lleva el efecto de calendario al nivel del escenario: suma real / suma ajustada en la ventana de referencia."""
    if escenario == "historico":
        fin = min(pd.Timestamp(ENTRENA_HASTA), ultimo)
        ini = fin - pd.Timedelta(days=364)
    else:
        fin = ultimo
        ini = fin - pd.Timedelta(days=VENTANA_RECIENTE - 1)
    m = (serie.index >= ini) & (serie.index <= fin) & serie.notna().values
    ajustado = np.exp(cal.loc[m].values @ beta)
    return serie[m].sum() / ajustado.sum()


def pronosticar_desde(serie, cal, corte, dias, escenario="reciente", ajuste_pct=0.0, beta=None):
    """Pronostico de los `dias` siguientes a `corte` usando solo datos hasta `corte`."""
    hist = serie[serie.index <= corte]
    if beta is None:
        beta = _ajustar(serie, cal, min(pd.Timestamp(corte), pd.Timestamp(ENTRENA_HASTA)))
    nivel = _nivel(hist, cal.loc[hist.index], beta, escenario, hist.dropna().index.max())
    fut = pd.date_range(pd.Timestamp(corte) + pd.Timedelta(days=1), periods=dias)
    mu = nivel * np.exp(cal.loc[fut].values @ beta) * (1 + ajuste_pct / 100.0)
    tau = TAU.get(getattr(serie, "name", None), 0.0)
    if tau > 0:
        ult = hist.dropna().index.max()
        ch = cal.loc[hist.index]
        c = np.clip(_nivel_ventana(hist, ch, beta, ult, VENTANA_CORTA) / _nivel_ventana(hist, ch, beta, ult, VENTANA_RECIENTE), 0.8, 1.25)
        mu = mu * c ** np.exp(-np.arange(1, dias + 1) / tau)
    return pd.Series(mu, index=fut)


def retroceso(serie, paso=14, minimo_dias=400):
    """Backtest: pronostica 365 dias desde muchos cortes del pasado con la regla 'reciente' y guarda (dia hacia adelante, real, pronostico)."""
    cal = calendario(pd.date_range(serie.index.min(), serie.index.max() + pd.Timedelta(days=366)))
    filas = []
    n_valido = serie.index.get_loc(serie.dropna().index.max()) + 1     # los dias sin dato confiable no son destino ni corte
    for pos in range(minimo_dias, n_valido - 7, paso):
        corte = serie.index[pos]
        f = pronosticar_desde(serie.iloc[:pos + 1], cal, corte, 365, "reciente")
        real = serie.reindex(f.index)
        ok = real.notna().values
        lead = np.arange(1, len(f) + 1)[ok]
        filas.append(pd.DataFrame({"corte": corte, "lead": lead, "fecha": f.index[ok], "real": real.values[ok],
                                   "pronostico": f.values[ok]}))
    return pd.concat(filas, ignore_index=True)


def tabla_error(bt, sin_caida=False):
    """Error por tramo de horizonte: WAPE diario (suma |real - pron| / suma real), sesgo y cobertura de la banda del 80 %."""
    if sin_caida:
        bt = bt[bt.fecha < INICIO_QUIEBRE]
    out = []
    for a, b in TRAMOS:
        t = bt[(bt.lead >= a) & (bt.lead <= b)]
        if len(t) < 30:
            continue
        r = t.real / t.pronostico
        lo, hi = r.quantile(0.1), r.quantile(0.9)
        out.append(dict(tramo_dias=f"{a}-{b}", n=len(t), wape_pct=round(100 * (t.real - t.pronostico).abs().sum() / t.real.sum(), 1),
                        sesgo_pct=round(100 * (t.pronostico.sum() / t.real.sum() - 1), 1), factor_banda_baja=round(lo, 3),
                        factor_banda_alta=round(hi, 3)))
    return pd.DataFrame(out)


def factores_banda(bt, excluir_caida=True):
    """(tramo -> (percentil 10, percentil 90)) de real / pronostico, para armar la banda del 80 %.
    Con excluir_caida=True los dias destino desde mayo de 2026 (caida de datos sin explicar) no cuentan para el ancho de la banda."""
    if excluir_caida:
        bt = bt[bt.fecha < INICIO_QUIEBRE]
    res = {}
    for a, b in TRAMOS:
        t = bt[(bt.lead >= a) & (bt.lead <= b)]
        r = (t.real / t.pronostico) if len(t) >= 30 else pd.Series([0.8, 1.2])
        res[(a, b)] = (float(r.quantile(0.1)), float(r.quantile(0.9)))
    return res


def factores_banda_semanal(bt, excluir_caida=True):
    """Igual que factores_banda pero para el TOTAL (o promedio) de una semana de 7 dias: percentiles 10 y 90 de
    (suma real de la semana) / (suma pronosticada de la semana), por tramo de dias hacia adelante. Es mas angosta que la diaria porque
    el ruido de dias sueltos se compensa dentro de la semana."""
    if excluir_caida:
        bt = bt[bt.fecha < INICIO_QUIEBRE]
    b = bt.assign(sem=(bt.lead - 1) // 7)
    u = b.groupby(["corte", "sem"]).agg(real=("real", "sum"), pron=("pronostico", "sum"), n=("real", "size"))
    u = u[u.n == 7].reset_index()
    u["lead_med"] = u["sem"] * 7 + 4
    u["r"] = u.real / u.pron
    res = {}
    for a, z in TRAMOS:
        t = u[(u.lead_med >= a) & (u.lead_med <= z)]
        res[(a, z)] = (float(t.r.quantile(0.1)), float(t.r.quantile(0.9))) if len(t) >= 30 else (0.9, 1.1)
    return res


def pronostico_con_banda(serie, bt, dias, escenario="historico", ajuste_pct=0.0, excluir_caida=True, semanal=False, desde=None):
    """Pronostico diario desde el ultimo dia con datos, con banda del 80 % que se ensancha con el horizonte.
    Con semanal=True devuelve el PROMEDIO MOVIL DE 7 DIAS del pronostico con la banda propia de un promedio semanal (mas angosta).
    `desde`: primer dia a pronosticar (por defecto, el dia siguiente al ultimo dato confiable). Si es posterior, el pronostico usa el nivel y el calendario
    del ultimo dato confiable y los `dias_adelante` cuentan desde ese ultimo dato (la banda es la de ese plazo, mas ancha)."""
    ultimo = serie.dropna().index.max()
    d0 = pd.Timestamp(desde) if desde is not None else ultimo + pd.Timedelta(days=1)
    total = (d0 - ultimo).days + dias - 1
    cal = calendario(pd.date_range(serie.index.min(), ultimo + pd.Timedelta(days=total + 1)))
    f = pronosticar_desde(serie, cal, ultimo, total, escenario, ajuste_pct)
    fb = factores_banda_semanal(bt, excluir_caida) if semanal else factores_banda(bt, excluir_caida)
    if semanal:
        f = pd.Series(f.rolling(7, min_periods=1).mean().values, index=f.index)
    lead = np.arange(1, total + 1)
    ultimo_tramo = fb[TRAMOS[-1]]
    lo, hi = np.full(total, ultimo_tramo[0]), np.full(total, ultimo_tramo[1])      # mas alla de 365 dias se usa el ultimo tramo
    for (a, b), (l, h) in fb.items():
        m = (lead >= a) & (lead <= b)
        lo[m], hi[m] = l, h
    out = pd.DataFrame({"fecha": f.index, "pronostico": f.values, "banda_baja": f.values * lo, "banda_alta": f.values * hi,
                        "dias_adelante": lead})
    return out[out.fecha >= d0].reset_index(drop=True)
