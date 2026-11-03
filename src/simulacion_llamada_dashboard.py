"""
simulacion_llamada_dashboard.py  -  version 1 (1-nov-2026)

PARA QUE SIRVE
  Simula lo que pasaria si el usuario del dashboard elige un horizonte ("proxima semana", "mes", "6 meses", "ano") y el
  pronostico se pidiera en ese momento. Mide cuanto tarda cada paso, con dos formas de obtener los datos:

    --fuente bd       conecta a la base con SQLAlchemy, cuenta las llegadas por dia (etapa 9203) y pronostica.
    --fuente archivo  lee panel_diario.csv (ya calculado) y pronostica.   [no necesita VPN]
    --fuente tabla    solo lee una tabla de pronosticos ya hecha (la forma recomendada para el dashboard)

  La idea es comparar los tiempos y decidir la arquitectura. El dashboard publicado NO se puede conectar a la base del
  hospital (VPN, solo lectura, datos clinicos), asi que lo realista es "tabla": el pronostico se calcula antes y el
  dashboard solo filtra por el horizonte elegido.

COMO USARLO
  Conexion (la contrasena NUNCA se escribe en archivos ni en el chat: se pide al correr o se toma de la variable PGPASSWORD):
      export HUN_DB_HOST=...      export HUN_DB_NAME=...      export HUN_DB_USER=...      (HUN_DB_PORT=5432 por defecto)
      python3 src/simulacion_llamada_dashboard.py --fuente bd --horizonte mes
  Sin base:
      python3 src/simulacion_llamada_dashboard.py --fuente archivo --horizonte anio
  Horizontes: semana (7 dias), mes (30), 6meses (182), anio (365). Para probar todos: --horizonte todos

QUE PRONOSTICA (version simple, solo para la simulacion; NO es el modelo final)
  nivel = promedio de los ultimos 28 dias x factor del dia de la semana x ajuste de festivo (festivos de Colombia). Es la
  referencia "dia de la semana x nivel reciente" de pronostico_demanda.py (error de 9,9 % a 1 dia y 10,5 % a 7 dias). La banda del
  80 % sale de los errores historicos de esa misma regla a cada horizonte (retrocediendo en el pasado), y crece con el horizonte.
  A 6 meses o un ano solo da tendencia: el modelo no conoce estacionalidad anual ni la causa de la caida de abril de 2026.

SALIDAS  resultados/tablas/simulacion_llamada_dashboard.csv  (una fila por corrida: fuente, horizonte, segundos por paso)
"""
import argparse
import getpass
import os
import time
from pathlib import Path

import holidays
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
HORIZONTES = {"semana": 7, "mes": 30, "6meses": 182, "anio": 365}
VENTANA_NIVEL = 28
FEST = holidays.Colombia(years=range(2023, 2028))

# Llegadas por dia desde la base: visitas distintas con etapa 9203 (llegada a urgencias) segun su fecha de inicio. Es una
# aproximacion rapida de "llegadas": no aplica nuestra limpieza (copias, episodios, estancias gemelas).
SQL_LLEGADAS = """
SELECT date_trunc('day', visit_detail_start_datetime)::date AS fecha,
       COUNT(DISTINCT visit_occurrence_id)                  AS llegadas
FROM uninorte_omop.visit_detail
WHERE visit_detail_concept_id = 9203
  AND visit_detail_start_datetime >= :desde
  AND visit_detail_start_datetime <  :hasta
GROUP BY 1
ORDER BY 1
"""


def leer_de_bd(desde, hasta):
    """Conecta con SQLAlchemy. Pide la contrasena por teclado (no se guarda en ningun lado)."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL
    faltan = [v for v in ("HUN_DB_HOST", "HUN_DB_NAME", "HUN_DB_USER") if not os.environ.get(v)]
    if faltan:
        raise SystemExit("Faltan variables de entorno: " + ", ".join(faltan) + " (ver el encabezado del archivo)")
    clave = os.environ.get("PGPASSWORD") or getpass.getpass("Contrasena de la base (no se muestra ni se guarda): ")
    url = URL.create("postgresql+psycopg", username=os.environ["HUN_DB_USER"], password=clave,
                     host=os.environ["HUN_DB_HOST"], port=int(os.environ.get("HUN_DB_PORT", 5432)),
                     database=os.environ["HUN_DB_NAME"])
    motor = create_engine(url, connect_args={"options": "-c default_transaction_read_only=on"})
    t0 = time.perf_counter()
    with motor.connect() as con:
        t_con = time.perf_counter() - t0
        t1 = time.perf_counter()
        d = pd.read_sql(text(SQL_LLEGADAS), con, params={"desde": desde, "hasta": hasta})
    return d, t_con, time.perf_counter() - t1


def leer_de_archivo():
    t1 = time.perf_counter()
    d = pd.read_csv(PROC / "para_equipo" / "panel_diario.csv", usecols=["fecha", "llegadas"])
    return d, 0.0, time.perf_counter() - t1


def factor_dia(serie):
    """Factor de cada dia de la semana: promedio del dia / promedio general, sobre las ultimas 26 semanas."""
    s = serie.iloc[-182:]
    return (s.groupby(s.index.dayofweek).mean() / s.mean())


def pronosticar(serie, horizonte_dias):
    """Pronostico diario hacia adelante desde el ultimo dia de `serie` (indice de fechas)."""
    nivel = serie.iloc[-VENTANA_NIVEL:].mean() / factor_dia(serie).reindex(serie.iloc[-VENTANA_NIVEL:].index.dayofweek).mean()
    fd = factor_dia(serie)
    # efecto de festivo entre semana: razon entre el promedio de festivos y de dias normales del mismo dia de la semana
    hist = serie.to_frame("y")
    hist["fest"] = [d in FEST for d in hist.index]
    hist["f"] = hist.index.dayofweek.map(fd)
    adj_fest = (hist[hist.fest].y / (nivel * hist[hist.fest].f)).mean() if hist.fest.sum() > 3 else 1.0
    futuro = pd.date_range(serie.index[-1] + pd.Timedelta(days=1), periods=horizonte_dias)
    pron = np.array([nivel * fd[d.dayofweek] * (adj_fest if d in FEST else 1.0) for d in futuro])
    return pd.DataFrame({"fecha": futuro, "pronostico": pron})


def bandas(serie, horizonte_dias):
    """Banda del 80 %: percentiles 10 y 90 de la razon real/pronostico al mismo horizonte, retrocediendo en el pasado."""
    razones = []
    ultimo = len(serie) - horizonte_dias
    for corte in range(max(VENTANA_NIVEL + 182, ultimo - 360), ultimo, 14):
        pasado = serie.iloc[:corte]
        f = pronosticar(pasado, horizonte_dias)
        real = serie.reindex(f.fecha)
        ok = real.notna()
        razones += list((real[ok].values / f.pronostico.values[ok.values]))
    r = np.array(razones)
    return (np.percentile(r, 10), np.percentile(r, 90)) if len(r) > 20 else (0.8, 1.2)


def correr(fuente, nombre, dias):
    t_ini = time.perf_counter()
    if fuente == "bd":
        d, t_con, t_sql = leer_de_bd("2023-02-01", pd.Timestamp.today().normalize().strftime("%Y-%m-%d"))
    elif fuente == "archivo":
        d, t_con, t_sql = leer_de_archivo()
    else:
        t1 = time.perf_counter()
        ruta = TABLAS / "pronostico_futuro.csv"
        if not ruta.exists():
            raise SystemExit("Aun no existe resultados/tablas/pronostico_futuro.csv (lo genera src/pronostico_futuro.py).")
        t = pd.read_csv(ruta, parse_dates=["fecha"])
        f = t[t.fecha < t.fecha.min() + pd.Timedelta(days=dias)]
        seg = time.perf_counter() - t_ini
        print(f"[{nombre}] fuente=tabla  filas={len(f)}  total={seg:.3f} s")
        return dict(fuente=fuente, horizonte=nombre, dias=dias, seg_conexion=0, seg_consulta=time.perf_counter() - t1,
                    seg_modelo=0, seg_total=seg, filas=len(f))
    d["fecha"] = pd.to_datetime(d["fecha"])
    serie = d.set_index("fecha").llegadas.asfreq("D").interpolate().iloc[:-1] if fuente == "bd" else \
        d.set_index("fecha").llegadas.asfreq("D").interpolate()
    # los ultimos meses (caida de datos desde mayo de 2026) se dejan: asi se ve lo que vería el usuario
    t2 = time.perf_counter()
    f = pronosticar(serie, dias)
    lo, hi = bandas(serie, dias)
    f["banda_baja"], f["banda_alta"] = f.pronostico * lo, f.pronostico * hi
    seg_modelo = time.perf_counter() - t2
    seg = time.perf_counter() - t_ini
    print(f"[{nombre:7s}] fuente={fuente:7s} dias={dias:3d} | conexion {t_con:6.2f} s | consulta {t_sql:6.2f} s | "
          f"modelo {seg_modelo:5.2f} s | TOTAL {seg:6.2f} s | promedio pronosticado {f.pronostico.mean():5.0f}/dia "
          f"(banda 80 %: {lo:.2f} a {hi:.2f})")
    return dict(fuente=fuente, horizonte=nombre, dias=dias, seg_conexion=round(t_con, 3), seg_consulta=round(t_sql, 3),
                seg_modelo=round(seg_modelo, 3), seg_total=round(seg, 3), filas=len(f))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuente", choices=["bd", "archivo", "tabla"], default="archivo")
    ap.add_argument("--horizonte", choices=list(HORIZONTES) + ["todos"], default="todos")
    a = ap.parse_args()
    corridas = HORIZONTES if a.horizonte == "todos" else {a.horizonte: HORIZONTES[a.horizonte]}
    res = [correr(a.fuente, n, d) for n, d in corridas.items()]
    TABLAS.mkdir(parents=True, exist_ok=True)
    out = TABLAS / "simulacion_llamada_dashboard.csv"
    pd.DataFrame(res).assign(corrida=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")).to_csv(
        out, mode="a", header=not out.exists(), index=False)
    print("guardado:", out)
