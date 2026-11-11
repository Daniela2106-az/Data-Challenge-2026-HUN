"""
perfiles_en_picos.py  -  version 1 (10-nov-2026)
Punto 2 del plan de dashboard de Anthony (no tiene ficha A# propia: es una ampliacion de A1 que cruza perfil
con momento de carga). Pregunta: dentro de cada perfil de paciente (igual definicion que A1: grupo de edad x
sexo x tipo de visita), ¿cambia la espera o la estancia cuando el paciente llega en un momento de alta carga?

POR QUE SE ESPERA UN RESULTADO DEBIL (declarar esto en el documento, no ocultarlo)
  Tres analisis independientes del proyecto ya apuntan a que el momento importa poco frente a quien es el
  paciente: docs/estimador_tiempos.md 1.1 (el dia de llegada explica 0,1% de la espera individual mas alla del
  azar), docs/pronostico_espera_sistema.md "camino 3" (la saturacion real al llegar suma 3,7 puntos de R^2,
  frente a 7,0 de edad+sexo+tipo de visita) y docs/saturacion_y_espera.md (en adultos la cola de espera NUNCA
  esta vacia: 0,0% de las horas) -- el sistema esta saturado casi siempre, asi que el contraste "pico vs no
  pico" tiene poco contraste real con el que comparar. Si esta tabla sale con diferencias chicas para casi
  todos los perfiles, ESO es el hallazgo (una cuarta confirmacion, a nivel de perfil): el problema concentra en
  quien llega, no en cuando. No se fuerza un resultado distinto.

REGLAS (las mismas de A1, src/perfiles_pacientes.py, para que las dos tablas se puedan leer juntas)
  - Periodo confiable: llegadas del 2023-02-01 al 2026-04-09.
  - Perfil = grupo_edad x sexo x tipo_visita (42 perfiles). Espera y estancia: una fila por estancia
    (estancia_unica). "Con atencion" = ruta != "ER".
  - Minimos: celdas con menos de 100 episodios con atencion o 30 estancias no se interpretan (MIN_EPISODIOS,
    MIN_ESTANCIAS, igual que A1). La clasificacion GRANDE/pequena/ruido usa el mismo criterio de A1
    (`clasificar`): el intervalo de confianza del 95% de la diferencia no incluye 0 y la diferencia relativa es
    de al menos 20%.

DOS CRITERIOS DE CARGA, SE REPORTAN LOS DOS (igual que src/dependencia_carga.py, mismo metodo: pd.qcut decil)
  - Llegadas en las 6 h previas (llegadas_6h_previas, ya en tabla_episodios.parquet): decil 10 = "pico" de
    demanda reciente, decil 1-9 = "resto".
  - Ocupacion del hospital al llegar (ocup_hosp, solo donde ocupacion_confiable es True): decil 10 = "pico" de
    ocupacion, decil 1-9 = "resto".

ENTRADAS  datos/procesados/tabla_episodios.parquet, datos/procesados/para_equipo/estancias_hospitalizacion.csv
SALIDAS   resultados/tablas/perfiles_en_picos_llegadas.csv, perfiles_en_picos_ocupacion.csv
          resultados/tablas/dias_alta_demanda.csv (lista para la pagina del dashboard, con la advertencia de
          docs/dias_atipicos.md al lado: NO se interpreta como dia de cuello de botella, solo de mas llegadas)
          docs/perfiles_en_picos.md (de forma manual, con estos resultados)
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
DESDE, HASTA = "2023-02-01", "2026-04-10"
MIN_EPISODIOS, MIN_ESTANCIAS = 100, 30
EDADES = ["0-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+"]
rng = np.random.default_rng(7)

t = pd.read_parquet(PROC / "tabla_episodios.parquet")
t = t[(t.ini >= DESDE) & (t.ini < HASTA) & t.grupo_edad.notna() & t.sexo.isin(["Mujer", "Hombre"])
      & t.tipo_visita.isin(["Urgencias", "Treatment urgency", "Ambulatorio"])].copy()
t["con_atencion"] = t.ruta != "ER"
t["hosp"] = t.hospitalizado & t.estancia_unica                       # una vez por estancia, igual que A1

est = pd.read_csv(PROC / "para_equipo" / "estancias_hospitalizacion.csv",
                   usecols=["visit_occurrence_id", "episodio", "ingreso_cama", "alta", "alta_completa"],
                   parse_dates=["ingreso_cama", "alta"])
h_base = t[t.hosp].merge(est, on=["visit_occurrence_id", "episodio"], how="left")
h_base["estancia_h"] = ((h_base.alta - h_base.ingreso_cama).dt.total_seconds() / 3600).where(h_base.alta_completa == True)  # noqa: E712

a_base = t[t.con_atencion].copy()

print(f"periodo {DESDE} a {HASTA}: {len(t)} episodios | {len(a_base)} con atencion | {len(h_base)} estancias unicas")


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - m, c + m


def ic_mediana(x, B=400):
    x = np.asarray(pd.Series(x).dropna(), float)
    if len(x) < MIN_ESTANCIAS:
        return np.nan, np.nan
    med = np.median(rng.choice(x, size=(B, len(x)), replace=True), axis=1)
    return np.percentile(med, 2.5), np.percentile(med, 97.5)


def ic_diferencia_medianas(x_alta, x_resto, B=400):
    """IC 95% de (mediana_alta - mediana_resto) por bootstrap pareado; np.nan si alguno de los dos no alcanza MIN_ESTANCIAS."""
    x_alta, x_resto = np.asarray(pd.Series(x_alta).dropna(), float), np.asarray(pd.Series(x_resto).dropna(), float)
    if len(x_alta) < MIN_ESTANCIAS or len(x_resto) < MIN_ESTANCIAS:
        return np.nan, np.nan, np.nan
    d_obs = np.median(x_alta) - np.median(x_resto)
    d_boot = (np.median(rng.choice(x_alta, size=(B, len(x_alta)), replace=True), axis=1)
              - np.median(rng.choice(x_resto, size=(B, len(x_resto)), replace=True), axis=1))
    return d_obs, np.percentile(d_boot, 2.5), np.percentile(d_boot, 97.5)


def clasificar_contraste(d_obs, lo, hi, ref_resto):
    """GRANDE si el IC de la diferencia no incluye 0 y la diferencia es de al menos 20% de la mediana del resto; en otro caso, pequena/ruido."""
    if np.isnan(d_obs) or ref_resto in (0, np.nan) or np.isnan(ref_resto):
        return "sin datos suficientes"
    fuera_de_cero = (lo > 0) or (hi < 0)
    if fuera_de_cero and abs(d_obs / ref_resto) >= 0.20:
        return "GRANDE (más alto en pico)" if d_obs > 0 else "GRANDE (más bajo en pico)"
    return "ruido" if not fuera_de_cero else "pequeña"


def tabla_por_carga(nombre_carga, col_carga, filtro_extra=None):
    """Para cada perfil (edad x sexo x tipo), compara espera y estancia entre decil 10 (pico) de `col_carga` y el resto."""
    a, h = a_base.copy(), h_base.copy()
    if filtro_extra is not None:
        a, h = a[filtro_extra(a)], h[filtro_extra(h)]
    # el corte de "pico" (decil 10) se calcula UNA vez sobre `a` (todos los atendidos) y se aplica igual a `h`
    # (los hospitalizados son un subconjunto de los atendidos): asi "pico" significa lo mismo en las dos tablas,
    # en vez de recalcular un decil 10 propio solo entre hospitalizados (una poblacion distinta y mas chica).
    _, bordes = pd.qcut(a[col_carga], 10, duplicates="drop", retbins=True)
    bordes = bordes.copy(); bordes[0], bordes[-1] = -np.inf, np.inf
    a["pico"] = pd.cut(a[col_carga], bordes, labels=False) == len(bordes) - 2
    h["pico"] = pd.cut(h[col_carga], bordes, labels=False) == len(bordes) - 2
    filas = []
    for (edad, sexo, tipo), g_a in a.groupby(["grupo_edad", "sexo", "tipo_visita"], observed=True):
        g_h = h[(h.grupo_edad == edad) & (h.sexo == sexo) & (h.tipo_visita == tipo)]
        n_at_total = len(g_a)
        comp_pico = 100 * (g_a.pico.sum() / max(a.pico.sum(), 1))
        comp_resto = 100 * ((~g_a.pico).sum() / max((~a.pico).sum(), 1))
        fila = dict(grupo_edad=edad, sexo=sexo, tipo_visita=tipo, episodios_con_atencion=n_at_total,
                    pct_de_los_picos=round(comp_pico, 2), pct_del_resto=round(comp_resto, 2),
                    sobrerrepresentado_en_picos=comp_pico > comp_resto * 1.2)
        for medida, serie_col in [("espera", "espera_cama_h"), ("estancia", "estancia_h")]:
            x_pico, x_resto = g_h.loc[g_h.pico, serie_col], g_h.loc[~g_h.pico, serie_col]
            med_pico, med_resto = x_pico.median(), x_resto.median()
            d_obs, lo, hi = ic_diferencia_medianas(x_pico, x_resto)
            fila[f"n_estancias_pico_{medida}"] = int(x_pico.notna().sum())
            fila[f"n_estancias_resto_{medida}"] = int(x_resto.notna().sum())
            fila[f"{medida}_mediana_pico_h"] = round(med_pico, 1) if pd.notna(med_pico) else np.nan
            fila[f"{medida}_mediana_resto_h"] = round(med_resto, 1) if pd.notna(med_resto) else np.nan
            fila[f"{medida}_contraste"] = clasificar_contraste(d_obs, lo, hi, med_resto)
        filas.append(fila)
    out = pd.DataFrame(filas)
    out["_o"] = out.grupo_edad.map({e: i for i, e in enumerate(EDADES)})
    return out.sort_values(["espera_mediana_resto_h"], ascending=False).drop(columns="_o").reset_index(drop=True)


# ----------------------------------------------------------------------
# 1) Criterio de carga 1: llegadas en las 6 h previas (congestion reciente)
# ----------------------------------------------------------------------
tab_llegadas = tabla_por_carga("llegadas_6h_previas", "llegadas_6h_previas")
tab_llegadas.to_csv(TABLAS / "perfiles_en_picos_llegadas.csv", index=False)
n_grande = (tab_llegadas.espera_contraste.str.startswith("GRANDE", na=False)).sum()
print(f"\ncriterio 1 (llegadas 6h previas, decil 10 vs resto): {n_grande} de {len(tab_llegadas)} perfiles con contraste GRANDE en espera")
print(tab_llegadas[["grupo_edad", "sexo", "tipo_visita", "espera_mediana_pico_h", "espera_mediana_resto_h", "espera_contraste"]].head(10).to_string(index=False))

# ----------------------------------------------------------------------
# 2) Criterio de carga 2: ocupacion del hospital al llegar
# ----------------------------------------------------------------------
tab_ocup = tabla_por_carga("ocup_hosp", "ocup_hosp", filtro_extra=lambda d: d.ocupacion_confiable)
tab_ocup.to_csv(TABLAS / "perfiles_en_picos_ocupacion.csv", index=False)
n_grande_o = (tab_ocup.espera_contraste.str.startswith("GRANDE", na=False)).sum()
print(f"\ncriterio 2 (ocupacion al llegar, decil 10 vs resto): {n_grande_o} de {len(tab_ocup)} perfiles con contraste GRANDE en espera")

# ----------------------------------------------------------------------
# 3) Lista de dias de alta demanda (para la pagina del dashboard, NO como "cuello de botella")
#    Reutiliza la definicion de A (alertas.py): llegadas > percentil 90 del mismo dia de la semana en las
#    12 semanas anteriores. Aqui solo se calcula desde tabla_episodios.parquet (no depende de panel_diario.csv).
# ----------------------------------------------------------------------
llegadas_dia = t.groupby(t.ini.dt.normalize()).size().rename("llegadas").to_frame()
llegadas_dia["dow"] = llegadas_dia.index.dayofweek
umbral = pd.concat([llegadas_dia.llegadas.shift(7 * k) for k in range(1, 13)], axis=1).quantile(.9, axis=1)
llegadas_dia["umbral_p90_mismo_dia_semana"] = umbral
llegadas_dia["alta_demanda"] = llegadas_dia.llegadas > umbral
dias_alta = llegadas_dia[llegadas_dia.alta_demanda].reset_index().rename(columns={"ini": "fecha"})
dias_alta["pct_sobre_umbral"] = round(100 * (dias_alta.llegadas / dias_alta.umbral_p90_mismo_dia_semana - 1), 1)
dias_alta[["fecha", "llegadas", "umbral_p90_mismo_dia_semana", "pct_sobre_umbral"]].round(1).to_csv(TABLAS / "dias_alta_demanda.csv", index=False)
print(f"\ndias de alta demanda (llegadas > percentil 90 del mismo dia de semana, 12 semanas previas): {len(dias_alta)} de {len(llegadas_dia)} dias")
print("ADVERTENCIA para la pagina del dashboard: docs/dias_atipicos.md ya probo que ningun dia tuvo espera mas alta de lo esperado -- "
      "esta lista es solo de mas llegadas, nunca se debe mostrar como 'cuello de botella' o 'dia problematico'.")
