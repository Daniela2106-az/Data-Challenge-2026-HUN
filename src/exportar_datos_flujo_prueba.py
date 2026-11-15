"""
exportar_datos_flujo_prueba.py  -  tablas agregadas para la pagina «Prueba de flujo» del dashboard (15-nov-2026)

La pagina simula un recorrido paso a paso: estado del hospital -> pacientes esperando cama -> alertas -> recomendaciones. Para eso
necesita, sin datos por paciente:
  flujo_umbrales.csv   por dia de la semana: limite de llegadas de un dia congestionado (percentil 90 de ese dia en las 12 semanas
                       anteriores al 9-abr-2026, sin los dias 28 y 29 de marzo, que son un corte del sistema) y la fraccion tipica del
                       dia que ya llego antes de cada hora (columnas h1 a h23).
  flujo_perfiles.csv   mezcla real de los pacientes hospitalizados de 2025 por edad, tipo de visita y sexo (para sortear pacientes).
  flujo_esperas.csv    los 100 percentiles de la espera de cama de 2025 (para sortear cuanto lleva esperando cada paciente).
  flujo_cola_horaria.csv  por hora de la semana: pacientes que llegan y se hospitalizan, y camas asignadas (modelo de flujo de la cola proyectada).
ENTRADAS  datos/procesados/dashboard/panel_diario.csv y llegadas_calor.csv; datos/procesados/tabla_episodios.parquet (locales)
SALIDA    datos/tablas_dashboard/flujo_*.csv
COMO CORRERLO  python3 src/exportar_datos_flujo_prueba.py   (segundos)
LIMITES   Es una version simplificada de la alerta de dia congestionado: la original (src/alertas.py) mezcla ademas el pronostico.
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DASH, SAL = RAIZ / "datos" / "procesados" / "dashboard", RAIZ / "datos" / "tablas_dashboard"
FIN, SEMANAS = pd.Timestamp("2026-04-09"), 12
CORTE_SISTEMA = [pd.Timestamp("2026-03-28"), pd.Timestamp("2026-03-29")]

# --- umbrales de llegadas por dia de la semana (percentil 90 de las ultimas 12 semanas) y fraccion acumulada por hora
p = pd.read_csv(DASH / "panel_diario.csv", parse_dates=["fecha"])
p = p[(p.fecha > FIN - pd.Timedelta(weeks=SEMANAS)) & (p.fecha <= FIN) & ~p.fecha.isin(CORTE_SISTEMA)]
umbral = p.groupby(p.fecha.dt.dayofweek).llegadas.apply(lambda s: float(np.percentile(s, 90)))
calor = pd.read_csv(DASH / "llegadas_calor.csv")                       # llegadas medias por hora; una fila por dia (lunes a domingo)
horas = [str(h) for h in range(24)]
cum = calor[horas].cumsum(axis=1).div(calor[horas].sum(axis=1), axis=0)  # fraccion del dia que ya llego al terminar cada hora
tipica = p.groupby(p.fecha.dt.dayofweek).llegadas.mean()
umb = pd.DataFrame({"dia": range(7), "dia_nombre": calor["dia"].values, "umbral_llegadas": umbral.reindex(range(7)).round(0).values,
                    "llegadas_tipicas": tipica.reindex(range(7)).round(1).values})
for h in range(1, 24):
    umb[f"h{h}"] = cum[str(h - 1)].round(4).values                        # lo que llego antes de las h:00
umb.to_csv(SAL / "flujo_umbrales.csv", index=False, encoding="utf-8")

# --- mezcla de pacientes hospitalizados de 2025 y distribucion de la espera de cama
t = pd.read_parquet(RAIZ / "datos" / "procesados" / "tabla_episodios.parquet", columns=["hospitalizado", "estancia_unica", "anio", "grupo_edad", "tipo_visita", "sexo", "espera_cama_h"])
h = t[t.hospitalizado & t.estancia_unica & (t.anio == 2025) & t.espera_cama_h.notna() & t.sexo.isin(["Mujer", "Hombre"])]
mezcla = h.groupby(["grupo_edad", "tipo_visita", "sexo"], observed=True).size().rename("n").reset_index()
mezcla["peso"] = (mezcla.n / mezcla.n.sum()).round(5)
mezcla[["grupo_edad", "tipo_visita", "sexo", "peso"]].to_csv(SAL / "flujo_perfiles.csv", index=False, encoding="utf-8")
esp = pd.DataFrame({"percentil": range(1, 101), "espera_h": np.percentile(h.espera_cama_h, range(1, 101)).round(2)})
esp.to_csv(SAL / "flujo_esperas.csv", index=False, encoding="utf-8")

# --- cola proyectada: modelo de flujo (docs/pronostico_espera_sistema.md 1a): cola de ahora + llegadas que se hospitalizan - camas asignadas, por hora de la semana
t2 = pd.read_parquet(RAIZ / "datos" / "procesados" / "tabla_episodios.parquet", columns=["hospitalizado", "estancia_unica", "ini_est", "ini_hosp_est"])
u2 = t2[t2.hospitalizado & t2.estancia_unica & t2.ini_est.notna() & t2.ini_hosp_est.notna()]
horas_rango = pd.date_range("2023-02-01", "2025-06-30 23:00", freq="h")                 # mismo entrenamiento que la prueba del modelo (hasta jun-2025)
llegan = pd.Series(1, index=u2.ini_est.dt.floor("h")).groupby(level=0).sum().reindex(horas_rango, fill_value=0)
asignan = pd.Series(1, index=u2.ini_hosp_est.dt.floor("h")).groupby(level=0).sum().reindex(horas_rango, fill_value=0)
how = (horas_rango.dayofweek * 24 + horas_rango.hour).to_numpy()
cola = pd.DataFrame({"hora_de_la_semana": range(168),
                     "llegan_y_se_hospitalizan_por_hora": pd.Series(llegan.to_numpy()).groupby(how).mean().reindex(range(168)).round(4).values,
                     "camas_asignadas_por_hora": pd.Series(asignan.to_numpy()).groupby(how).mean().reindex(range(168)).round(4).values})
cola.to_csv(SAL / "flujo_cola_horaria.csv", index=False, encoding="utf-8")
print(f"cola: llegan {cola.llegan_y_se_hospitalizan_por_hora.mean():.2f} y se asignan {cola.camas_asignadas_por_hora.mean():.2f} por hora en promedio")

print("umbrales de llegadas por dia:", dict(zip(umb.dia_nombre, umb.umbral_llegadas)))
print(f"a las 12 h ya llegó, en promedio, el {100 * umb['h12'].mean():.0f} % del día")
print(f"perfiles: {len(mezcla)} combinaciones de {len(h)} estancias de 2025 | esperas: mediana {esp.espera_h.iloc[49]:.1f} h, p90 {esp.espera_h.iloc[89]:.1f} h")
print("grupos de edad:", sorted(h.grupo_edad.astype(str).unique()))
