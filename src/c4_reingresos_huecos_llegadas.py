"""
c4_reingresos_huecos_llegadas.py  -  version 1 (8-nov-2026)
Tarea C4 (opcionales): (1) reingresos depurados, (2) huecos entre etapas dentro del episodio (TU a TU y demas),
(3) cuanto cambian las llegadas si se quitan las replicas.

PREGUNTAS
  1. ¿Cuanto baja la tasa de reingreso (72 h, 30 dias) al quitar registros gemelos, episodios sin atencion y traslapes?
  2. ¿Hay tiempo sin etapa entre bloques seguidos de un mismo episodio (TU > TU, ER > TU, TU > HOSP)? ¿Cuanto pesa?
  3. ¿Cuantas llegadas son replicas (mismo segundo, personas con id cercano, ids de visita a un desfase de copia)
     y cuanto cambian los niveles diarios si se quitan?

LIMITES
  - Replica de llegada = cota inferior: solo pares que empiezan en el MISMO segundo (v. CLAUDE.md 4.6).
  - Periodo confiable: 1-feb-2023 a 9-abr-2026, sin el 28 y 29 de marzo de 2026.
  - El reingreso se mide con el fin registrado del episodio anterior; si ese fin es un minimo (estado no medida), el
    intervalo real hasta la nueva llegada es menor o igual al calculado.

ENTRADAS  datos/procesados/tabla_episodios.parquet, datos/procesados/bloques.csv, datos/procesados/para_equipo/panel_diario.csv
SALIDAS   resultados/tablas/c4_reingresos.csv, c4_huecos_entre_bloques.csv, c4_llegadas_replicas.csv, c4_llegadas_diarias_dedup.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC, TABLAS = RAIZ / "datos" / "procesados", RAIZ / "resultados" / "tablas"
INI, FIN = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-10")
CAIDA = pd.to_datetime(["2026-03-28", "2026-03-29"])
DESFASES = set(range(1746478, 1746490)) | {1757764} | set(range(11280, 11287))
pd.set_option("display.width", 200)


def titulo(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


t = pd.read_parquet(PROC / "tabla_episodios.parquet")
t["ini_s"] = t.ini.dt.floor("s")
t["en_periodo"] = (t.ini >= INI) & (t.ini < FIN) & ~t.ini.dt.normalize().isin(CAIDA)
t["con_atencion"] = ~((t.ruta_simple == "ER") & (t.estado == "sin_actividad"))
t["conservado"] = ~t.hospitalizado | t.estancia_unica.fillna(False).astype(bool)

# ----------------------------------------------------------------------
# 1) Reingresos depurados
# ----------------------------------------------------------------------
titulo("1. REINGRESOS DEPURADOS")


def tasas(d, etiqueta):
    """Tasas de reingreso sobre los episodios con atencion del periodo, dado un data frame ya ordenado por persona y ini."""
    d = d.sort_values(["person_id", "ini"]).copy()
    g = d.groupby("person_id")
    d["dias"] = (d.ini - g.fin.shift()).dt.total_seconds() / 86400
    d["ant_hosp"] = g.hospitalizado.shift()
    d["ant_medida"] = g.estado.shift() == "medida"
    base = d[d.en_periodo]
    n = len(base)
    ok = lambda x: x.sum() / n
    return {
        "version": etiqueta, "episodios_base": n,
        "reing_72h": ok((base.dias <= 3)), "reing_72h_sin_traslape": ok((base.dias >= 0) & (base.dias <= 3)),
        "reing_30d": ok((base.dias <= 30)), "reing_30d_sin_traslape": ok((base.dias >= 0) & (base.dias <= 30)),
        "traslapes_%": ok(base.dias < 0),
        "reing_30d_tras_hosp": ((base.dias >= 0) & (base.dias <= 30) & (base.ant_hosp == True)).sum() / max((base.ant_hosp == True).sum(), 1),
        "reing_30d_ant_medida": ((base.dias >= 0) & (base.dias <= 30) & base.ant_medida).sum() / max(base.ant_medida.sum(), 1),
    }


filas = [
    tasas(t, "A. todos los episodios (sin depurar)"),
    tasas(t[t.con_atencion], "B. solo con atencion"),
    tasas(t[t.con_atencion & t.conservado], "C. con atencion y sin registros gemelos (depurado)"),
]
res = pd.DataFrame(filas)
fmt = res.copy()
for c in fmt.columns[2:]:
    fmt[c] = (100 * fmt[c]).round(2)
print(fmt.T.to_string(header=False))
res.to_csv(TABLAS / "c4_reingresos.csv", index=False)

# ----------------------------------------------------------------------
# 2) Huecos entre bloques dentro de un episodio
# ----------------------------------------------------------------------
titulo("2. HUECOS ENTRE BLOQUES DE UN MISMO EPISODIO")
b = pd.read_csv(PROC / "bloques.csv", parse_dates=["ini", "fin"])
k = ["visit_occurrence_id", "episodio"]
b = b.merge(t.loc[t.en_periodo & t.conservado, k], on=k, how="inner").sort_values(k + ["bloque"])
g = b.groupby(k)
b["sig_etapa"] = g.etapa.shift(-1)
b["sig_ini"] = g.ini.shift(-1)
b["hueco_h"] = (b.sig_ini - b.fin).dt.total_seconds() / 3600
tr = b[b.sig_etapa.notna()].copy()
tr["transicion"] = tr.etapa + " > " + tr.sig_etapa
tr["con_hueco"] = tr.hueco_h > 1 / 60
tr["hueco_pos"] = tr.hueco_h.clip(lower=0)
tr["hueco_largo"] = tr.hueco_h > 1
tt = tr.groupby("transicion").agg(
    n=("hueco_h", "size"), pct_hueco_1min=("con_hueco", "mean"), pct_hueco_1h=("hueco_largo", "mean"),
    mediana_h_si_hueco=("hueco_pos", lambda s: s[s > 1 / 60].median()),
    p90_h_si_hueco=("hueco_pos", lambda s: s[s > 1 / 60].quantile(.9)), horas_hueco=("hueco_pos", "sum"),
    traslape_pct=("hueco_h", lambda s: (s < -1 / 60).mean())).sort_values("n", ascending=False)
tt["pct_horas_hueco"] = tt.horas_hueco / tt.horas_hueco.sum()
for c in ["pct_hueco_1min", "pct_hueco_1h", "traslape_pct", "pct_horas_hueco"]:
    tt[c] = (100 * tt[c]).round(2)
print(tt.round(2).to_string())
tt.to_csv(TABLAS / "c4_huecos_entre_bloques.csv")
tot = b.groupby(k).agg(h_bloques=("horas", "sum")).h_bloques.sum()
print(f"\nhoras de hueco entre bloques (todas las transiciones): {tr.hueco_pos.sum():,.0f} h = "
      f"{tr.hueco_pos.sum() / (tr.hueco_pos.sum() + tot):.2%} del tiempo total (bloques + huecos) de estos episodios")

# 2b) Huecos TU a TU: los bloques juntan las TU seguidas, asi que se miden sobre las etapas crudas
titulo("2b. HUECOS ENTRE ETAPAS TU DE UNA MISMA VISITA (etapas crudas)")
v = pd.read_csv(RAIZ / "datos" / "crudos" / "visit_detail.csv", parse_dates=["visit_detail_start_datetime", "visit_detail_end_datetime"])
v.columns = ["id", "vid", "c", "ini", "fin"]
tc = t[t.en_periodo & t.conservado]
v = v[(v.c == 3045729) & v.vid.isin(tc.visit_occurrence_id) & (v.fin > v.ini) & (v.fin == v.fin.dt.floor("s"))]
v = v.drop_duplicates(["vid", "ini", "fin"]).sort_values(["vid", "ini"])
v["prevfin"] = v.groupby("vid").fin.cummax().groupby(v.vid).shift()
v["gap_h"] = (v.ini - v.prevfin).dt.total_seconds() / 3600
gg = v[v.gap_h.notna() & (v.gap_h <= 168)]
filas = []
for lo, hi, n in [(-1e9, -1 / 60, "traslape"), (-1 / 60, 1 / 60, "pegadas (+-1 min)"), (1 / 60, 1, "1 min a 1 h"), (1, 6, "1 a 6 h"), (6, 168, "6 a 168 h")]:
    m = gg[(gg.gap_h > lo) & (gg.gap_h <= hi)]
    filas.append({"hueco": n, "pares": len(m), "pct_pares": len(m) / len(gg), "horas": m.gap_h.clip(lower=0).sum()})
tu_tu = pd.DataFrame(filas)
print(tu_tu.round(3).to_string(index=False))
h_tu = (v.fin - v.ini).dt.total_seconds().sum() / 3600
h_gap = gg[gg.gap_h > 1 / 60].gap_h.sum()
print(f"horas TU con tiempo: {h_tu:,.0f}; horas de hueco TU-TU: {h_gap:,.0f} = {h_gap / (h_tu + h_gap):.2%}; "
      f"visitas con hueco > 1 h: {gg[gg.gap_h > 1].vid.nunique()} de {v.vid.nunique()}")
tu_tu.to_csv(TABLAS / "c4_huecos_tu_tu.csv", index=False)

# ----------------------------------------------------------------------
# 3) Replicas de llegadas
# ----------------------------------------------------------------------
titulo("3. REPLICAS DE LLEGADAS (mismo segundo, persona cercana, desfase de copia)")
a = t.loc[t.en_periodo, ["visit_occurrence_id", "episodio", "person_id", "ini_s", "hospitalizado", "con_atencion"]].copy()
par = a.merge(a, on="ini_s", suffixes=("", "_b"))
par = par[par.visit_occurrence_id < par.visit_occurrence_id_b]
par = par[((par.person_id - par.person_id_b).abs() <= 10) & ((par.visit_occurrence_id_b - par.visit_occurrence_id).isin(DESFASES))]
print(f"pares de replica: {len(par):,}")
rep = par[["visit_occurrence_id_b", "episodio_b"]].drop_duplicates().rename(columns={"visit_occurrence_id_b": "visit_occurrence_id", "episodio_b": "episodio"})
rep["replica"] = True
t = t.merge(rep, on=["visit_occurrence_id", "episodio"], how="left")
t["replica"] = t.replica.fillna(False).astype(bool)
p = t[t.en_periodo]
print(f"episodios replica (el de id mayor de cada par): {p.replica.sum():,} de {len(p):,} = {p.replica.mean():.2%}")
cuadro = pd.DataFrame({
    "episodios": p.groupby("hospitalizado").size(), "replicas": p.groupby("hospitalizado").replica.sum()})
cuadro["pct"] = (100 * cuadro.replicas / cuadro.episodios).round(2)
print(cuadro.to_string())
cuadro.to_csv(TABLAS / "c4_llegadas_replicas.csv")

d = p.assign(fecha=p.ini.dt.normalize())
diario = pd.DataFrame({
    "llegadas": d.groupby("fecha").size(), "llegadas_dedup": d[~d.replica].groupby("fecha").size(),
    "con_atencion": d[d.con_atencion].groupby("fecha").size(), "con_atencion_dedup": d[d.con_atencion & ~d.replica].groupby("fecha").size(),
}).fillna(0).astype(int)
diario["anio"] = diario.index.year
diario["dow"] = diario.index.dayofweek
res3 = diario.groupby("anio")[["llegadas", "llegadas_dedup", "con_atencion", "con_atencion_dedup"]].mean().round(1)
res3["pct_replicas"] = (100 * (1 - res3.llegadas_dedup / res3.llegadas)).round(2)
res3["pct_replicas_con_atencion"] = (100 * (1 - res3.con_atencion_dedup / res3.con_atencion)).round(2)
print("\nmedia diaria por ano:")
print(res3.to_string())
diario["pct_replica_dia"] = 100 * (1 - diario.llegadas_dedup / diario.llegadas)
print("\nreplicas por dia de la semana (%):", diario.groupby("dow").pct_replica_dia.mean().round(2).to_dict())
print("replicas por mes-ano (% min / max):", diario.groupby(diario.index.to_period("M")).pct_replica_dia.mean().agg(["min", "max"]).round(2).to_dict())
diario.to_csv(TABLAS / "c4_llegadas_diarias_dedup.csv")

pan = pd.read_csv(PROC / "para_equipo" / "panel_diario.csv", parse_dates=["fecha"]).set_index("fecha")
com = diario.join(pan[["llegadas"]], rsuffix="_panel", how="inner")
print(f"\ncoincidencia con panel_diario.llegadas: dias iguales {(com.llegadas == com.llegadas_panel).mean():.1%}; "
      f"diferencia media {(com.llegadas - com.llegadas_panel).mean():.2f}")
# la replica es proporcional al nivel o crece con el? (si es proporcional, el pronostico relativo no cambia)
r = np.corrcoef(diario.llegadas, diario.llegadas_dedup)[0, 1]
print(f"correlacion diaria llegadas vs llegadas dedup: {r:.4f}; razon dedup/total media {diario.llegadas_dedup.sum() / diario.llegadas.sum():.4f}, "
      f"desv. est. de la razon diaria {(diario.llegadas_dedup / diario.llegadas).std():.4f}")
