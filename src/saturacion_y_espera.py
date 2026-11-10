"""
saturacion_y_espera.py  -  version 1 (9-nov-2026)
Pregunta (Daniela, 9-nov): ¿la espera de cama sube cuando las camas estan saturadas? Si si, el cuello de botella son las camas; si no, el tiempo se va
en las etapas TU de antes de la cama (atencion y tramite en urgencias) y habria que caracterizarlas.

COMO SE MIDE (todo con las estancias unicas que ya tenemos; no hace falta la VPN)
  - Espera de cama = llegada a urgencias (ini_est) hasta la asignacion de la cama (ini_hosp_est), como en HALLAZGOS 4.
  - Saturacion, hora por hora, en cada hora h:
      cola(h)  = estancias que ya llegaron y todavia no reciben cama (solo las que luego se hospitalizan: cota inferior)
      ocup(h)  = estancias en cama en la hora h (HOSP)
    por zona: adultos (15 anos o mas; 88 camas del HUN) y ninos (menos de 15; 18 camas) y total (106).
  - AVISO DE CIRCULARIDAD: la cola es la suma de lo que estan esperando los pacientes (ley de Little: cola = llegadas x espera). Una cola grande y una
    espera larga se acompanan casi por definicion, asi que NO prueban saturacion. La ocupacion si es una medida de saturacion que no depende de la espera.
    Se reportan las dos, pero la conclusion sobre las camas se apoya sobre todo en la ocupacion y en la prueba 3.

QUE SE HACE
  1. Descripcion: que porcentaje de las horas la cola esta vacia y como se reparte la ocupacion frente a las camas.
  2. POR HORA DE LLEGADA: para cada paciente, la ocupacion y la cola en la hora en que llego. Espera mediana por franjas de saturacion y regresion de
     log(espera + 1) con efectos fijos por hora del dia, dia de la semana y mes (errores agrupados por dia). Efecto de +10 camas ocupadas y de +10 en la cola.
  3. ¿LA CAMA SE ASIGNA APENAS SE LIBERA? Para cada alta, cuanto tarda en asignarse la siguiente cama a otro paciente (cualquier zona o solo adultos), con
     cola > 0 en ese momento. Se compara con un "como si no hubiera relacion": los mismos ingresos corridos 1 a 8 semanas (mismo patron de hora y dia, sin
     el emparejamiento real). Si las camas fueran el limite, la cama se asignaria mucho mas rapido que en esa comparacion.

  4. ¿LAS 106 CAMAS SON UN TOPE DURO? Si lo fueran, la ocupacion se aplastaria contra 106 y los ingresos se frenarian al llegar; ademas, a que horas se
     asignan las camas.

SALIDAS (HUN_TABLAS): saturacion_techo.csv, saturacion_espera_por_ocupacion_total.csv, saturacion_ingresos_por_franja.csv, saturacion_descripcion.csv, saturacion_espera_por_franja.csv, saturacion_regresion.csv, saturacion_alta_a_ingreso.csv, saturacion_resumen.txt
ENTRADA tabla_episodios.parquet (HUN_PROCESADOS)
COMO CORRERLO  python3 src/saturacion_y_espera.py   (1-2 min)
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

RAIZ = Path(__file__).resolve().parent.parent
PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
DESDE, HASTA = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10")      # periodo confiable (HASTA no incluido)
DIAS_CORTE = [pd.Timestamp("2026-03-28").date(), pd.Timestamp("2026-03-29").date()]
CAMAS = {"total": 106, "adultos": 88, "ninos": 18}                            # HUN, 29-oct-2026
LINEAS = []


def decir(txt=""):
    print(txt, flush=True)
    LINEAS.append(txt)


def contar(rejilla, ini, fin):
    """Cuantos intervalos [ini, fin) estan abiertos en cada hora de la rejilla."""
    return np.searchsorted(np.sort(ini), rejilla, side="right") - np.searchsorted(np.sort(fin), rejilla, side="right")


def cargar():
    t = pd.read_parquet(PROC / "tabla_episodios.parquet")
    h = t[t.hospitalizado & t.estancia_unica & t.ini_hosp_est.notna() & t.fin_hosp_est.notna() & (t.ini_est <= t.ini_hosp_est)].copy()
    h["zona"] = np.where(h.edad.isna(), "sin_edad", np.where(h.edad < 15, "ninos", "adultos"))
    return h


def estado_por_hora(h):
    rejilla = pd.date_range(DESDE, HASTA, freq="h", inclusive="left")
    r = rejilla.to_numpy()
    est = pd.DataFrame(index=rejilla)
    for zona, g in [("total", h), ("adultos", h[h.zona == "adultos"]), ("ninos", h[h.zona == "ninos"])]:
        est[f"cola_{zona}"] = contar(r, g.ini_est.to_numpy(), g.ini_hosp_est.to_numpy())
        est[f"ocup_{zona}"] = contar(r, g.ini_hosp_est.to_numpy(), g.fin_hosp_est.to_numpy())
    dia = pd.Series(rejilla.date, index=rejilla)
    return est[~dia.isin(DIAS_CORTE)]


def descripcion(est):
    decir("1. DESCRIPCION (cada fila es una hora del periodo confiable, sin el 28 y 29 de marzo de 2026)")
    filas = []
    for z in ["total", "adultos", "ninos"]:
        c, o, cap = est[f"cola_{z}"], est[f"ocup_{z}"], CAMAS[z]
        fila = {"zona": z, "camas_HUN": cap, "horas": len(est), "pct_horas_cola_vacia": round(100 * (c == 0).mean(), 1), "cola_mediana": float(c.median()),
                "cola_p10": float(c.quantile(.1)), "cola_p90": float(c.quantile(.9)), "ocup_mediana": float(o.median()),
                "ocup_p10": float(o.quantile(.1)), "ocup_p90": float(o.quantile(.9)),
                "pct_horas_ocup_desde_90pct_camas": round(100 * (o >= 0.9 * cap).mean(), 1), "pct_horas_ocup_sobre_camas": round(100 * (o > cap).mean(), 1)}
        filas.append(fila)
        decir(f"  {z:8s} ({cap} camas): cola vacia {fila['pct_horas_cola_vacia']} % de las horas; cola mediana {fila['cola_mediana']:.0f} (p10 {fila['cola_p10']:.0f}, "
              f"p90 {fila['cola_p90']:.0f}); ocupacion mediana {fila['ocup_mediana']:.0f} (p10 {fila['ocup_p10']:.0f}, p90 {fila['ocup_p90']:.0f}); "
              f"{fila['pct_horas_ocup_desde_90pct_camas']} % de las horas con >= 90 % de las camas, {fila['pct_horas_ocup_sobre_camas']} % sobre las camas")
    tabla = pd.DataFrame(filas)
    tabla.to_csv(TABLAS / "saturacion_descripcion.csv", index=False)
    return tabla


def pacientes(h, est):
    """Cada estancia con la saturacion de su zona en la hora en que llego."""
    p = h[(h.ini_est >= DESDE) & (h.ini_est < HASTA) & h.espera_cama_h.notna() & h.zona.isin(["adultos", "ninos"])].copy()
    p = p[~p.ini_est.dt.date.isin(DIAS_CORTE)]
    hora = p.ini_est.dt.floor("h")
    for z in ["adultos", "ninos"]:
        for var in ["cola", "ocup"]:
            p[f"{var}_zona_llegada"] = np.nan
    for z in ["adultos", "ninos"]:
        m = p.zona == z
        p.loc[m, "cola_zona_llegada"] = est[f"cola_{z}"].reindex(hora[m]).to_numpy()
        p.loc[m, "ocup_zona_llegada"] = est[f"ocup_{z}"].reindex(hora[m]).to_numpy()
    p["cola_total_llegada"] = est["cola_total"].reindex(hora).to_numpy()
    p["ocup_total_llegada"] = est["ocup_total"].reindex(hora).to_numpy()
    p["hora_llegada"] = p.ini_est.dt.hour
    p["dia_semana"] = p.ini_est.dt.dayofweek
    p["mes"] = p.ini_est.dt.to_period("M").astype(str)
    p["dia"] = p.ini_est.dt.date.astype(str)
    p["log_espera"] = np.log1p(p.espera_cama_h)
    p["ratio_ocup"] = np.where(p.zona == "adultos", p.ocup_zona_llegada / CAMAS["adultos"], p.ocup_zona_llegada / CAMAS["ninos"])
    return p.dropna(subset=["cola_zona_llegada", "ocup_zona_llegada"])


def por_franja(p):
    decir("\n2a. ESPERA SEGUN LA SATURACION AL LLEGAR (franjas; adultos y niños por separado)")
    filas = []
    for z in ["adultos", "ninos"]:
        g = p[p.zona == z].copy()
        g["franja_ocup"] = pd.qcut(g.ocup_zona_llegada, 5, duplicates="drop")
        g["franja_cola"] = pd.qcut(g.cola_zona_llegada, 5, duplicates="drop")
        for var, nombre in [("franja_ocup", "ocupacion"), ("franja_cola", "cola")]:
            r = g.groupby(var, observed=True).espera_cama_h.agg(n="size", mediana="median", p75=lambda s: s.quantile(.75), p90=lambda s: s.quantile(.9),
                                                                pct_mas_24h=lambda s: 100 * (s > 24).mean()).reset_index()
            r.insert(0, "medida", nombre)
            r.insert(0, "zona", z)
            r = r.rename(columns={var: "franja"})
            r["franja"] = r.franja.astype(str)
            filas.append(r)
            decir(f"  {z} - segun {nombre} al llegar (quintiles):")
            decir(r.drop(columns=["zona", "medida"]).round(1).to_string(index=False))
    tabla = pd.concat(filas)
    tabla.to_csv(TABLAS / "saturacion_espera_por_franja.csv", index=False)
    return tabla


def regresion(p):
    decir("\n2b. REGRESION: log(espera + 1) frente a la saturacion al llegar, con efectos fijos de hora del dia, dia de la semana y mes (errores agrupados por dia)")
    decir("    Efecto = cambio % de la espera por cada +10 camas ocupadas o +10 pacientes en la cola. Entre parentesis, el IC 95 %.")
    filas = []
    for z in ["adultos", "ninos", "total"]:
        g = p if z == "total" else p[p.zona == z]
        g = g.assign(ocup10=(g.ocup_total_llegada if z == "total" else g.ocup_zona_llegada) / 10, cola10=(g.cola_total_llegada if z == "total" else g.cola_zona_llegada) / 10)
        for nombre, f in [("solo ocupacion", "log_espera ~ ocup10"), ("solo cola", "log_espera ~ cola10"), ("ocupacion y cola", "log_espera ~ ocup10 + cola10")]:
            m = smf.ols(f + " + C(hora_llegada) + C(dia_semana) + C(mes)", data=g).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g.dia)[0]})
            for var in ["ocup10", "cola10"]:
                if var in m.params:
                    b, lo, hi = m.params[var], *m.conf_int().loc[var]
                    filas.append({"zona": z, "modelo": nombre, "variable": var, "n": int(m.nobs), "efecto_pct": round(100 * (np.exp(b) - 1), 1),
                                  "ic95_bajo": round(100 * (np.exp(lo) - 1), 1), "ic95_alto": round(100 * (np.exp(hi) - 1), 1), "r2": round(m.rsquared, 3)})
    tabla = pd.DataFrame(filas)
    tabla.to_csv(TABLAS / "saturacion_regresion.csv", index=False)
    for _, r in tabla.iterrows():
        decir(f"  {r.zona:8s} {r.modelo:17s} {r.variable:6s}: {r.efecto_pct:+.1f} % ({r.ic95_bajo:+.1f} a {r.ic95_alto:+.1f}) n={r.n:,}")
    return tabla


def alta_a_ingreso(h, est):
    decir("\n3. ¿LA CAMA SE ASIGNA APENAS SE LIBERA OTRA? Tiempo desde cada alta hasta el siguiente ingreso a cama (de cualquier otro paciente)")
    filas = []
    SEM = np.timedelta64(7, "D")
    lo, hi = pd.Timestamp("2023-04-01"), pd.Timestamp("2026-02-01")            # margen para no sesgar con los bordes al correr 8 semanas
    for nombre, g in [("todas las camas", h), ("solo adultos", h[h.zona == "adultos"])]:
        ing = np.sort(g.ini_hosp_est.to_numpy())
        altas = g.fin_hosp_est[(g.fin_hosp_est >= lo) & (g.fin_hosp_est < hi) & ~g.fin_hosp_est.dt.date.isin(DIAS_CORTE)]
        # con cola > 0 en el momento del alta
        col = "cola_total" if nombre == "todas las camas" else "cola_adultos"
        cola = est[col].reindex(altas.dt.floor("h")).to_numpy()
        altas = altas[cola > 0].to_numpy()

        def demora(ingresos):
            k = np.searchsorted(ingresos, altas, side="left")
            ok = k < len(ingresos)
            return (ingresos[k[ok]] - altas[ok]) / np.timedelta64(1, "h")

        real = demora(ing)
        nulos = [demora(ing + s * SEM) for s in list(range(-8, 0)) + list(range(1, 9))]
        horas = pd.DatetimeIndex(altas).hour
        for etiqueta, d_real, d_nulo in [("todas las horas", real, nulos)] + [
                (f"alta entre las {a} y las {b} h", real[(horas >= a) & (horas < b)], [x[(horas >= a) & (horas < b)] if len(x) == len(altas) else x for x in nulos])
                for a, b in [(6, 12), (12, 14), (14, 19), (19, 24)]]:
            fila = {"camas": nombre, "altas": etiqueta, "n_altas": len(d_real), "demora_mediana_h_real": round(float(np.median(d_real)), 2),
                    "demora_mediana_h_sin_relacion": round(float(np.mean([np.median(x) for x in d_nulo])), 2),
                    "pct_en_1h_real": round(100 * float((d_real <= 1).mean()), 1), "pct_en_1h_sin_relacion": round(100 * float(np.mean([(x <= 1).mean() for x in d_nulo])), 1),
                    "pct_en_3h_real": round(100 * float((d_real <= 3).mean()), 1), "pct_en_3h_sin_relacion": round(100 * float(np.mean([(x <= 3).mean() for x in d_nulo])), 1)}
            filas.append(fila)
    tabla = pd.DataFrame(filas)
    tabla.to_csv(TABLAS / "saturacion_alta_a_ingreso.csv", index=False)
    decir(tabla.to_string(index=False))
    return tabla


def techo_y_horario(h, est, p):
    """4. ¿Las 106 camas son un tope? ¿Y a que horas se asignan las camas?"""
    decir("\n4. ¿LAS 106 CAMAS SON UN TOPE DURO? ¿A QUE HORAS SE ASIGNA LA CAMA?")
    o = est.ocup_total
    etiquetas = ["<=90", "91-95", "96-100", "101-105", "106", "107-110", "111-115", ">115"]
    nivel = pd.cut(o, bins=[-1, 90, 95, 100, 105, 106, 110, 115, 200], labels=etiquetas)
    r = est.index
    ing = pd.Series(1, index=h.ini_hosp_est.dt.floor("h")).groupby(level=0).sum().reindex(r, fill_value=0)
    alt = pd.Series(1, index=h.fin_hosp_est.dt.floor("h")).groupby(level=0).sum().reindex(r, fill_value=0)
    rel = lambda x: (x / x.groupby(r.hour).transform("mean")).groupby(nivel, observed=True).mean().reindex(etiquetas)
    t = pd.DataFrame({"pct_horas": (100 * nivel.value_counts(normalize=True)).reindex(etiquetas), "ingresos_vs_lo_normal_de_la_hora": rel(ing), "altas_vs_lo_normal_de_la_hora": rel(alt)}).round(2)
    decir(f"  Ocupacion total: maximo {o.max()}, p95 {o.quantile(.95):.0f}. Por ano (media / max): " + "; ".join(f"{a} {g.mean():.0f} / {g.max()}" for a, g in o.groupby(o.index.year)))
    decir("  % de horas por nivel de ocupacion, y ingresos y altas por hora frente a lo normal de esa hora del dia:")
    decir(t.to_string())
    nivel_p = pd.cut(p.ocup_total_llegada, bins=[-1, 90, 100, 105, 110, 115, 200], labels=["<=90", "91-100", "101-105", "106-110", "111-115", ">115"])
    e = p.groupby(nivel_p, observed=True).espera_cama_h.agg(n="size", mediana="median", p90=lambda x: x.quantile(.9)).round(1)
    decir("  Espera segun la ocupacion total al llegar:")
    decir(e.to_string())
    franja = pd.cut(h.ini_hosp_est.dt.hour, [-1, 5, 11, 14, 17, 19, 23], labels=["0-5 h", "6-11 h", "12-14 h", "15-17 h", "18-19 h", "20-23 h"])
    f = (100 * franja.value_counts(normalize=True)).sort_index().round(1)
    decir("  % de las camas asignadas por franja horaria (hora del ingreso a cama):")
    decir(f.to_string())
    t.to_csv(TABLAS / "saturacion_techo.csv")
    e.to_csv(TABLAS / "saturacion_espera_por_ocupacion_total.csv")
    f.rename("pct_ingresos").to_csv(TABLAS / "saturacion_ingresos_por_franja.csv")


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    TABLAS.mkdir(parents=True, exist_ok=True)
    h = cargar()
    est = estado_por_hora(h)
    decir(f"SATURACION Y ESPERA | {len(h):,} estancias unicas | horas del periodo {len(est):,}")
    descripcion(est)
    p = pacientes(h, est)
    decir(f"\nEstancias con espera medida en el periodo: {len(p):,} (adultos {int((p.zona == 'adultos').sum()):,}, ninos {int((p.zona == 'ninos').sum()):,})")
    por_franja(p)
    regresion(p)
    alta_a_ingreso(h, est)
    techo_y_horario(h, est, p)
    (TABLAS / "saturacion_resumen.txt").write_text("\n".join(LINEAS), encoding="utf-8")
