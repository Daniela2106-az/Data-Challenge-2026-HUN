"""
espera_dos_series.py  -  version 1 (7-nov-2026)
Tarea A6, segunda parte: estimar la espera de cama con DOS SERIES DE TIEMPO, una para la espera que ocurre cuando no hay camas libres y otra para la
espera que ocurre cuando si las hay (demora del servicio).

COMO SE SEPARA LA ESPERA
  Para cada hora se cuentan las camas ocupadas por zona (estancias unicas): adultos (15 anos o mas) frente a 88 camas y ninos (menos de 15) frente a 18,
  las capacidades que dio el HUN el 29-oct (docs/CONTEXTO_TECNICO.md 4.7). Una hora esta "sin cama" en una zona si sus camas ocupadas llegan a la capacidad.
  La espera de cada estancia (de la llegada a la asignacion de cama) se reparte hora por hora:
    espera_sin_cama_h  = horas de espera en que la zona del paciente estaba llena
    espera_servicio_h  = horas de espera en que habia camas libres en el conteo (la demora no se explica por falta de camas)
  Las dos suman la espera total. Sensibilidad: se repite con capacidades 10 % mayores (97 y 20), por si el hospital opera con mas camas que las reportadas.

LAS DOS SERIES Y SU PRONOSTICO
  Serie diaria (por fecha de llegada) del promedio de cada parte. Pronostico con el mismo metodo para las dos: nivel de los 28 dias previos x factor del dia
  de la semana. El nivel solo usa llegadas de hace 7 dias o mas, porque la espera de quien llego ayer aun no se conoce completa (p90 ~74 h).
  Se compara contra una sola serie (la espera total con el mismo metodo) y contra el promedio historico por dia de la semana.
  Entrenamiento feb-2023 a jun-2025; prueba jul-2025 a 9-abr-2026; horizontes de 1 y 7 dias desde el ultimo dato utilizable, y por semana.

ENTRADAS  tabla_episodios.parquet en HUN_PROCESADOS (por defecto datos/procesados)
SALIDAS   en HUN_TABLAS (por defecto resultados/tablas):
            espera_dos_series_por_anio.csv, espera_dos_series_diaria.csv, espera_dos_series_pronostico.csv, espera_dos_series_por_perfil.csv
          resultados/graficos/espera_dos_series.png

LIMITES (los mas importantes)
  - "Sin cama" significa que el CONTEO de camas estaba lleno, no que el paciente esperara por eso: una cama libre puede no servirle (otro servicio, otro
    sexo, aislamiento) y una zona "llena" puede tener camas de apoyo. No se conoce la fecha de las capacidades del HUN.
  - La espera empieza en la llegada: incluye la atencion clinica en urgencias, que no se puede separar (docs/CONTEXTO_TECNICO.md 4.7).
  - docs/capacidad_efectiva.md mostro que la cola casi no cambia con la ocupacion: si casi todas las horas estan "llenas", casi toda la espera cae en
    "sin cama" por construccion. Por eso se reporta la sensibilidad y se lee la separacion como una descripcion, no como una causa.

COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... python3 src/espera_dos_series.py
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
import estimador_tiempos as et  # noqa: E402

PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
GRAF = RAIZ / "resultados" / "graficos"
DESDE, HASTA, CORTE = et.DESDE, et.HASTA, et.CORTE
CAPACIDADES = {"HUN": {"adultos": 88, "ninos": 18}, "HUN + 10 %": {"adultos": 97, "ninos": 20}}
VENTANA, RETRASO = 28, 7                                   # dias del nivel; dias de retraso hasta que la espera se conoce completa


# ----------------------------------------------------------------------
# 1) Ocupacion por hora y zona, y reparto de cada espera
# ----------------------------------------------------------------------
def estancias():
    t = pd.read_parquet(PROC / "tabla_episodios.parquet")
    h = t[t.hospitalizado & t.estancia_unica & t.edad.notna()].copy()
    h["zona"] = np.where(h.edad < 15, "ninos", "adultos")
    return t, h


def horas_llenas(h, cap):
    """Por zona: rejilla horaria y si la zona estaba llena en cada hora (conteo al inicio de la hora)."""
    rejilla = pd.date_range(h.ini_hosp_est.min().floor("h"), h.fin_hosp_est.max().ceil("h"), freq="h")
    llena = {}
    for zona, g in h.groupby("zona"):
        ini, fin = np.sort(g.ini_hosp_est.to_numpy()), np.sort(g.fin_hosp_est.to_numpy())
        ocupadas = np.searchsorted(ini, rejilla.to_numpy(), side="right") - np.searchsorted(fin, rejilla.to_numpy(), side="right")
        llena[zona] = ocupadas >= cap[zona]
    return rejilla, llena


def repartir(h, rejilla, llena):
    """Horas de espera con la zona llena: integral de la marca horaria entre la llegada y la asignacion de cama."""
    h = h.copy()
    h["espera_sin_cama_h"] = np.nan
    t0 = rejilla[0]
    for zona, marca in llena.items():
        acum = np.concatenate([[0.0], np.cumsum(marca)])
        def integral(x):
            p = (x - t0).dt.total_seconds().to_numpy() / 3600
            k = np.clip(np.floor(p).astype(int), 0, len(marca) - 1)
            return acum[k] + marca[k] * (p - k)
        m = (h.zona == zona) & h.espera_cama_h.notna()
        h.loc[m, "espera_sin_cama_h"] = np.clip(integral(h.loc[m, "ini_hosp_est"]) - integral(h.loc[m, "ini_est"]), 0, None)
    h["espera_sin_cama_h"] = np.minimum(h.espera_sin_cama_h, h.espera_cama_h)
    h["espera_servicio_h"] = h.espera_cama_h - h.espera_sin_cama_h
    return h


# ----------------------------------------------------------------------
# 2) Series diarias y pronostico
# ----------------------------------------------------------------------
def serie_diaria(h):
    d = h[(h.ini_est >= DESDE) & (h.ini_est < HASTA) & h.espera_cama_h.notna()]
    s = d.groupby(d.ini_est.dt.normalize())[["espera_sin_cama_h", "espera_servicio_h", "espera_cama_h"]].mean()
    s["n"] = d.groupby(d.ini_est.dt.normalize()).size()
    return s.asfreq("D")


def pronosticar(serie, factor, origen, destino):
    """Nivel de los VENTANA dias que terminan RETRASO dias antes del origen, por el factor del dia de la semana del destino."""
    ventana = serie.loc[origen - pd.Timedelta(days=RETRASO + VENTANA - 1): origen - pd.Timedelta(days=RETRASO)]
    nivel = (ventana / factor.reindex(ventana.index.dayofweek).to_numpy()).mean()
    return nivel * factor[destino.dayofweek]


def evaluar(s):
    tr, te = s[s.index < CORTE], s[s.index >= CORTE]
    cols = ["espera_sin_cama_h", "espera_servicio_h", "espera_cama_h"]
    factor = {c: tr[c].groupby(tr.index.dayofweek).mean() / tr[c].mean() for c in cols}
    media_dow = tr.espera_cama_h.groupby(tr.index.dayofweek).mean()
    filas = []
    for k in [1, 7]:
        for destino in te.index[te.espera_cama_h.notna()]:
            origen = destino - pd.Timedelta(days=k)
            p = {c: pronosticar(s[c], factor[c], origen, destino) for c in cols}
            filas.append({"horizonte_dias": k, "fecha": destino, "real": te.espera_cama_h[destino], "n": te.n[destino],
                          "real_sin_cama": te.espera_sin_cama_h[destino], "real_servicio": te.espera_servicio_h[destino],
                          "pred_sin_cama": p["espera_sin_cama_h"], "pred_servicio": p["espera_servicio_h"],
                          "pred_dos_series": p["espera_sin_cama_h"] + p["espera_servicio_h"], "pred_una_serie": p["espera_cama_h"],
                          "pred_historico": media_dow[destino.dayofweek]})
    return pd.DataFrame(filas)


def resumir_error(ev):
    filas = []
    for k, g in ev.groupby("horizonte_dias"):
        for metodo in ["pred_dos_series", "pred_una_serie", "pred_historico"]:
            ok = g[metodo].notna()
            gw = g[ok].set_index("fecha")
            semanal = (gw[metodo] * gw.n).resample("W").sum() / gw.n.resample("W").sum()
            real_sem = (gw.real * gw.n).resample("W").sum() / gw.n.resample("W").sum()
            filas.append({"horizonte_dias": k, "metodo": metodo.replace("pred_", ""), "dias": int(ok.sum()),
                          "error_abs_medio_diario_h": round((g.real - g[metodo])[ok].abs().mean(), 2),
                          "error_abs_medio_semanal_h": round((real_sem - semanal).abs().mean(), 2),
                          "sesgo_diario_h": round((g[metodo] - g.real)[ok].mean(), 2)})
        for parte in ["sin_cama", "servicio"]:
            filas.append({"horizonte_dias": k, "metodo": f"solo la parte {parte}", "dias": int(g[f"pred_{parte}"].notna().sum()),
                          "error_abs_medio_diario_h": round((g[f"real_{parte}"] - g[f"pred_{parte}"]).abs().mean(), 2),
                          "error_abs_medio_semanal_h": np.nan, "sesgo_diario_h": round((g[f"pred_{parte}"] - g[f"real_{parte}"]).mean(), 2)})
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------
# 3) Por perfil de llegada (mismos perfiles que estimador_tiempos.py)
# ----------------------------------------------------------------------
def por_perfil(h):
    d = h[(h.ini_est >= DESDE) & (h.ini_est < HASTA) & h.espera_cama_h.notna() & h.sexo.isin(["Mujer", "Hombre"]) & h.tipo_visita.isin(et.TIPOS)].copy()
    d["grupo_edad"] = d.grupo_edad.astype(str)
    d["bloque_hora"] = pd.Series(et.BLOQUES)[d.hora.to_numpy() // 3].to_numpy()
    rejilla = pd.MultiIndex.from_product([et.BLOQUES, et.EDADES, et.TIPOS, ["Mujer", "Hombre"]], names=et.DIMS).to_frame(index=False)
    partes = [rejilla]
    for c in ["espera_sin_cama_h", "espera_servicio_h"]:
        a = et.asignar(rejilla, et.tabla_por_nivel(d.assign(valor=d[c]), "espera_cama_h"), len(et.DIMS))
        partes.append(a.drop(columns=["n", "nivel"]).add_prefix(f"{c}_"))
    t = pd.concat(partes, axis=1)
    t["pct_sin_cama_de_la_mediana"] = 100 * t.espera_sin_cama_h_p50 / (t.espera_sin_cama_h_p50 + t.espera_servicio_h_p50)
    return t


# ----------------------------------------------------------------------
# 4) Grafico
# ----------------------------------------------------------------------
def grafico(mensual, ev):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6))
    x = mensual.index.to_timestamp()
    a1.bar(x, mensual.espera_sin_cama_h, width=25, color="#eb6834", label="con la zona llena (sin cama)")
    a1.bar(x, mensual.espera_servicio_h, width=25, bottom=mensual.espera_sin_cama_h, color="#2a78d6", label="con camas libres (demora del servicio)")
    a1.set_title("Espera de cama promedio por mes de llegada, en dos partes")
    a1.set_ylabel("horas por paciente")
    a1.legend(frameon=False, loc="upper left")
    a1.grid(axis="y", color="#e5e4df")
    g = ev[ev.horizonte_dias == 7].set_index("fecha")
    sem = lambda c: (g[c] * g.n).resample("W").sum() / g.n.resample("W").sum()
    a2.plot(sem("real").index, sem("real"), color="#52514e", lw=1.5, label="real")
    a2.plot(sem("pred_dos_series").index, sem("pred_dos_series"), color="#eb6834", lw=1.5, label="dos series")
    a2.plot(sem("pred_una_serie").index, sem("pred_una_serie"), color="#2a78d6", lw=1, ls="--", label="una serie")
    a2.set_title("Prueba: espera promedio por semana, pronóstico a 7 días")
    a2.set_ylim(0)
    a2.legend(frameon=False)
    a2.grid(axis="y", color="#e5e4df")
    fig.text(0.01, 0.01, "Capacidad del HUN por zona (adultos 88, niños 18). 'Sin cama' = el conteo de camas estaba lleno, no prueba la causa de la espera. "
             "Fuente: src/espera_dos_series.py", fontsize=8, color="#52514e")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(GRAF / "espera_dos_series.png", dpi=150)


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    TABLAS.mkdir(parents=True, exist_ok=True)
    _, h0 = estancias()
    anual, guardar = [], {}
    for nombre, cap in CAPACIDADES.items():
        rejilla, llena = horas_llenas(h0, cap)
        h = repartir(h0, rejilla, llena)
        d = h[(h.ini_est >= DESDE) & (h.ini_est < HASTA) & h.espera_cama_h.notna()]
        en_periodo = (rejilla >= DESDE) & (rejilla < HASTA)
        for anio, g in d.groupby(d.ini_est.dt.year):
            horas_anio = en_periodo & (rejilla.year == anio)
            anual.append({"capacidad": nombre, "anio": anio, "estancias": len(g),
                          "pct_horas_adultos_llena": round(100 * llena["adultos"][horas_anio].mean(), 1),
                          "pct_horas_ninos_llena": round(100 * llena["ninos"][horas_anio].mean(), 1),
                          "espera_media_h": round(g.espera_cama_h.mean(), 1), "sin_cama_media_h": round(g.espera_sin_cama_h.mean(), 1),
                          "servicio_media_h": round(g.espera_servicio_h.mean(), 1),
                          "pct_espera_sin_cama": round(100 * g.espera_sin_cama_h.sum() / g.espera_cama_h.sum(), 1),
                          "servicio_mediana_h": round(g.espera_servicio_h.median(), 1)})
        guardar[nombre] = h
    anual = pd.DataFrame(anual)
    anual.to_csv(TABLAS / "espera_dos_series_por_anio.csv", index=False)
    print("REPARTO DE LA ESPERA POR AÑO\n" + anual.to_string(index=False))

    h = guardar["HUN"]
    s = serie_diaria(h)
    s.round(3).to_csv(TABLAS / "espera_dos_series_diaria.csv", index_label="fecha")
    ev = evaluar(s)
    ev.round(3).to_csv(TABLAS / "espera_dos_series_pronostico.csv", index=False)
    err = resumir_error(ev)
    err.to_csv(TABLAS / "espera_dos_series_error.csv", index=False)
    print("\nPRONOSTICO (prueba jul-2025 a 9-abr-2026)\n" + err.to_string(index=False))

    pp = por_perfil(h)
    pp.round(2).to_csv(TABLAS / "espera_dos_series_por_perfil.csv", index=False)
    print("\nPOR PERFIL: % de la mediana que es 'sin cama' (min / mediana / max):",
          round(pp.pct_sin_cama_de_la_mediana.min(), 1), round(pp.pct_sin_cama_de_la_mediana.median(), 1), round(pp.pct_sin_cama_de_la_mediana.max(), 1))

    d = h[(h.ini_est >= DESDE) & (h.ini_est < HASTA) & h.espera_cama_h.notna()]
    mensual = d.groupby(d.ini_est.dt.to_period("M"))[["espera_sin_cama_h", "espera_servicio_h"]].mean()
    grafico(mensual, ev)
    por_hora = d.groupby(d.ini_est.dt.hour)[["espera_sin_cama_h", "espera_servicio_h"]].mean().round(1)
    por_hora.to_csv(TABLAS / "espera_dos_series_por_hora.csv", index_label="hora_llegada")
    print("\nPOR HORA DE LLEGADA (promedio, h)\n" + por_hora.T.to_string())
