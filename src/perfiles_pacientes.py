"""
perfiles_pacientes.py  -  version 1 (2-nov-2026)
Tarea A1 (docs/pendientes_y_reparto.md): "como se comportan distintos perfiles de pacientes" (instructivo del reto).
Un PERFIL es una combinacion de grupo de edad x sexo x tipo de visita. Para cada perfil se comparan: cuantos llegan, que parte recibe atencion, que parte se
hospitaliza, la espera de cama, la estancia en cama y el reingreso. Cada diferencia frente al total se clasifica como GRANDE (el intervalo de confianza no incluye
el total y la diferencia relativa es de 20 % o mas) o RUIDO (cualquier otra cosa), y las celdas con pocos casos no se interpretan.

REGLAS
  - Periodo confiable: llegadas del 2023-02-01 al 2026-04-09 (el registro de etapas se degrada desde el 10-abr-2026, docs/CONTEXTO_TECNICO.md 4.9).
  - Espera y estancia en cama: solo el registro conservado de cada estancia (`estancia_unica`; una fila por estancia, identificada por `estancia_id`, el mismo
    identificador que usara A2b para cruzar perfil con "estancia disparada"). La espera es la de la estancia (`espera_cama_h`).
  - "Con atencion" = el episodio no es solo la etapa ER de admision (ruta distinta de "ER"). Los porcentajes de hospitalizacion se calculan sobre los episodios con atencion.
  - Edad "<1 ano" no se separa del grupo 0-4 (el grupo de edad ya viene asi en la tabla).
  - Diagnostico: solo entre quienes lo tienen (65 % de las estancias hospitalizadas, 20 % de las demas) y SIEMPRE con su cobertura; hasta el 30-abr (despues no hay codigo).
  - Reingreso: `reingreso_72h` y `reingreso_30d` de tabla_episodios (sin validar; docs/CONTEXTO_TECNICO.md C4): se reportan, con esa advertencia.
  - Minimos: celdas con menos de 100 episodios con atencion no se interpretan; esperas y estancias, menos de 30 estancias no se interpretan.

ENTRADAS  datos/procesados/tabla_episodios.parquet
SALIDAS   resultados/tablas/perfiles_pacientes.csv            (un perfil por fila, edad x sexo x tipo de visita)
          resultados/tablas/perfiles_por_edad.csv, perfiles_por_sexo.csv, perfiles_por_tipo_visita.csv, perfiles_por_diagnostico.csv (cortes de una dimension)
          resultados/tablas/perfiles_trayectorias.csv        (rutas que siguen, con su porcentaje)
          resultados/tablas/perfiles_por_estancia.csv        (una fila por estancia con su perfil y su estancia_id; para A2b; no se sube a git)
          resultados/graficos/perfiles_pacientes.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"
DESDE, HASTA = "2023-02-01", "2026-04-10"          # periodo confiable (llegadas antes del 10-abr-2026)
HASTA_DX = "2026-05-01"                            # los diagnosticos traducidos terminan a fines de abril
MIN_EPISODIOS, MIN_ESTANCIAS = 100, 30
EDADES = ["0-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+"]
rng = np.random.default_rng(7)

t = pd.read_parquet(PROC / "tabla_episodios.parquet")
t = t[(t.ini >= DESDE) & (t.ini < HASTA) & t.grupo_edad.notna() & t.sexo.isin(["Mujer", "Hombre"]) & t.tipo_visita.isin(["Urgencias", "Treatment urgency", "Ambulatorio"])].copy()
t["con_atencion"] = t.ruta != "ER"
t["hosp"] = t.hospitalizado & t.estancia_unica                      # una vez por estancia
t["tipo"] = t.tipo_visita.replace({"Treatment urgency": "Treatment urgency", "Urgencias": "Urgencias", "Ambulatorio": "Ambulatorio"})
dias = (pd.Timestamp(HASTA) - pd.Timestamp(DESDE)).days
a = t[t.con_atencion]
h = t[t.hosp].copy()
h["estancia_h"] = np.nan
# estancia en cama: el panel de estancias tiene el tramo de toda la estancia (inicio y fin de cama)
est = pd.read_csv(PROC / "para_equipo" / "estancias_hospitalizacion.csv", usecols=["visit_occurrence_id", "episodio", "ingreso_cama", "alta", "alta_completa"], parse_dates=["ingreso_cama", "alta"])
h = h.drop(columns="estancia_h").merge(est, on=["visit_occurrence_id", "episodio"], how="left")
h["estancia_h"] = ((h.alta - h.ingreso_cama).dt.total_seconds() / 3600).where(h.alta_completa == True)   # noqa: E712

TOT_ATENCION = len(a)
TOT_HOSP = h.hosp.mean() if False else len(h) / TOT_ATENCION
MED_ESPERA, MED_ESTANCIA = h.espera_cama_h.median(), h.estancia_h.median()
TASA_REING72 = a.reingreso_72h.mean()


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - m, c + m


def ic_mediana(x, B=400):
    x = np.asarray(x.dropna(), float)
    if len(x) < MIN_ESTANCIAS:
        return np.nan, np.nan
    med = np.median(rng.choice(x, size=(B, len(x)), replace=True), axis=1)
    return np.percentile(med, 2.5), np.percentile(med, 97.5)


def clasificar(valor, bajo, alto, ref, relativo=0.20):
    """GRANDE si el IC no incluye la referencia y la diferencia relativa es >= 20 %; RUIDO en otro caso."""
    if np.isnan(valor) or np.isnan(bajo):
        return "sin datos suficientes"
    fuera = (bajo > ref) or (alto < ref)
    if fuera and abs(valor / ref - 1) >= relativo:
        return "GRANDE (más alto)" if valor > ref else "GRANDE (más bajo)"
    return "ruido" if not fuera else "pequeña"


def resumen(g_all, g_at, g_h, etiquetas):
    n_all, n_at, n_h = len(g_all), len(g_at), len(g_h)
    lo, hi = wilson(n_h, n_at)
    p_h = n_h / n_at if n_at else np.nan
    med_e, (e_lo, e_hi) = g_h.espera_cama_h.median(), ic_mediana(g_h.espera_cama_h)
    med_s, (s_lo, s_hi) = g_h.estancia_h.median(), ic_mediana(g_h.estancia_h)
    k72 = int(g_at.reingreso_72h.sum())
    r_lo, r_hi = wilson(k72, n_at)
    out = dict(etiquetas)
    out.update(episodios=n_all, llegadas_por_dia=round(n_all / dias, 2), pct_con_atencion=round(100 * n_at / n_all, 1) if n_all else np.nan, episodios_con_atencion=n_at,
               pct_hospitaliza=round(100 * p_h, 1) if n_at else np.nan, pct_hospitaliza_ic_bajo=round(100 * lo, 1), pct_hospitaliza_ic_alto=round(100 * hi, 1),
               estancias=n_h, espera_mediana_h=round(med_e, 1) if n_h >= MIN_ESTANCIAS else np.nan, espera_ic_bajo=round(e_lo, 1), espera_ic_alto=round(e_hi, 1),
               espera_p90_h=round(g_h.espera_cama_h.quantile(0.9), 1) if n_h >= MIN_ESTANCIAS else np.nan, pct_espera_mas_24h=round(100 * (g_h.espera_cama_h > 24).mean(), 1) if n_h >= MIN_ESTANCIAS else np.nan,
               estancia_mediana_h=round(med_s, 1) if g_h.estancia_h.notna().sum() >= MIN_ESTANCIAS else np.nan, estancia_ic_bajo=round(s_lo, 1), estancia_ic_alto=round(s_hi, 1),
               pct_reingreso_72h=round(100 * k72 / n_at, 2) if n_at else np.nan, pct_reingreso_72h_ic_bajo=round(100 * r_lo, 2), pct_reingreso_72h_ic_alto=round(100 * r_hi, 2),
               pct_con_diagnostico=round(100 * ((g_h.n_dx_distintos > 0) & (g_h.ini < HASTA_DX)).sum() / max((g_h.ini < HASTA_DX).sum(), 1), 1))
    out["lectura_hospitaliza"] = clasificar(100 * p_h, 100 * lo, 100 * hi, 100 * TOT_HOSP) if n_at >= MIN_EPISODIOS else "sin datos suficientes"
    out["lectura_espera"] = clasificar(med_e, e_lo, e_hi, MED_ESPERA) if n_h >= MIN_ESTANCIAS else "sin datos suficientes"
    out["lectura_estancia"] = clasificar(med_s, s_lo, s_hi, MED_ESTANCIA) if g_h.estancia_h.notna().sum() >= MIN_ESTANCIAS else "sin datos suficientes"
    out["lectura_reingreso"] = clasificar(100 * k72 / n_at, 100 * r_lo, 100 * r_hi, 100 * TASA_REING72) if n_at >= MIN_EPISODIOS else "sin datos suficientes"
    return out


def tabla(columnas, nombre):
    filas = []
    for clave, g_all in t.groupby(columnas, observed=True):
        clave = clave if isinstance(clave, tuple) else (clave,)
        et = dict(zip(columnas, clave))
        g_at = g_all[g_all.con_atencion]
        g_h = h.merge(g_all[["visit_occurrence_id", "episodio"]], on=["visit_occurrence_id", "episodio"])
        filas.append(resumen(g_all, g_at, g_h, et))
    d = pd.DataFrame(filas)
    if "grupo_edad" in columnas:
        d["_o"] = d.grupo_edad.map({e: i for i, e in enumerate(EDADES)}); d = d.sort_values(["_o"] + [c for c in columnas if c != "grupo_edad"]).drop(columns="_o")
    d.to_csv(TABLAS / f"{nombre}.csv", index=False)
    return d


print(f"periodo {DESDE} a {HASTA}: {len(t)} episodios | {TOT_ATENCION} con atencion | {len(h)} estancias unicas | referencia: {100 * TOT_HOSP:.1f} % se hospitaliza, "
      f"espera mediana {MED_ESPERA:.1f} h, estancia mediana {MED_ESTANCIA:.1f} h, reingreso 72 h {100 * TASA_REING72:.2f} %")
p_edad = tabla(["grupo_edad"], "perfiles_por_edad")
p_sexo = tabla(["sexo"], "perfiles_por_sexo")
p_tipo = tabla(["tipo"], "perfiles_por_tipo_visita")
p_edsx = tabla(["grupo_edad", "sexo"], "perfiles_por_edad_y_sexo")
p_all = tabla(["grupo_edad", "sexo", "tipo"], "perfiles_pacientes")
# diagnostico: solo estancias con diagnostico y llegadas antes del fin de los codigos
d_h = h[(h.n_dx_distintos > 0) & (h.ini < HASTA_DX) & (h.categoria_dx != "Sin diagnostico")]
rows = []
for dx, g in d_h.groupby("categoria_dx"):
    lo, hi = wilson(0, 1)
    e_lo, e_hi = ic_mediana(g.espera_cama_h); s_lo, s_hi = ic_mediana(g.estancia_h)
    rows.append(dict(categoria_dx=dx, estancias=len(g), espera_mediana_h=round(g.espera_cama_h.median(), 1), espera_ic_bajo=round(e_lo, 1), espera_ic_alto=round(e_hi, 1),
                     estancia_mediana_h=round(g.estancia_h.median(), 1), estancia_ic_bajo=round(s_lo, 1), estancia_ic_alto=round(s_hi, 1),
                     edad_mediana=g.edad.median(), pct_mujeres=round(100 * (g.sexo == "Mujer").mean(), 1),
                     lectura_espera=clasificar(g.espera_cama_h.median(), e_lo, e_hi, d_h.espera_cama_h.median()), lectura_estancia=clasificar(g.estancia_h.median(), s_lo, s_hi, d_h.estancia_h.median())))
p_dx = pd.DataFrame(rows).sort_values("espera_mediana_h", ascending=False)
p_dx["cobertura_diagnostico_pct_de_las_estancias"] = round(100 * len(d_h) / len(h[h.ini < HASTA_DX]), 1)
p_dx.to_csv(TABLAS / "perfiles_por_diagnostico.csv", index=False)
# tabla por estancia (para cruzar perfil con "estancia disparada" en A2b; una fila por estancia; datos por estancia: NO se sube a git)
h[["estancia_id", "visit_occurrence_id", "episodio", "grupo_edad", "sexo", "tipo", "categoria_dx", "n_dx_distintos", "espera_cama_h", "estancia_h", "ini"]].to_csv(TABLAS / "perfiles_por_estancia.csv", index=False)
# trayectorias
tr = a.groupby("ruta_simple").size().sort_values(ascending=False)
tr = pd.DataFrame({"ruta": tr.index, "episodios": tr.values, "pct": (100 * tr.values / tr.sum()).round(2)})
tr.head(15).to_csv(TABLAS / "perfiles_trayectorias.csv", index=False)

pd.set_option("display.width", 250, "display.max_columns", 40)
cols = ["episodios", "llegadas_por_dia", "pct_con_atencion", "pct_hospitaliza", "espera_mediana_h", "estancia_mediana_h", "pct_reingreso_72h", "lectura_hospitaliza", "lectura_espera", "lectura_estancia"]
print("\nPOR EDAD\n", p_edad[["grupo_edad"] + cols].to_string(index=False))
print("\nPOR SEXO\n", p_sexo[["sexo"] + cols].to_string(index=False))
print("\nPOR TIPO DE VISITA\n", p_tipo[["tipo"] + cols].to_string(index=False))
print("\nPOR EDAD Y SEXO\n", p_edsx[["grupo_edad", "sexo"] + cols[:7]].to_string(index=False))
print("\nTRAYECTORIAS (con atencion)\n", tr.head(8).to_string(index=False))
print("\nPERFILES completos:", len(p_all), "| con datos suficientes:", int((p_all.episodios_con_atencion >= MIN_EPISODIOS).sum()))
print("\nPOR DIAGNOSTICO (solo estancias con diagnostico; cobertura", p_dx.cobertura_diagnostico_pct_de_las_estancias.iloc[0], "% de las estancias)\n",
      p_dx[["categoria_dx", "estancias", "espera_mediana_h", "estancia_mediana_h", "edad_mediana", "lectura_espera", "lectura_estancia"]].to_string(index=False))

# ---- grafico: tres paneles (hospitalizacion, espera, estancia) por edad, separado por tipo de visita
fig, ejes = plt.subplots(1, 3, figsize=(16, 4.8))
colores = {"Urgencias": "#2a6fb0", "Treatment urgency": "#d9730d", "Ambulatorio": "#6b6b6b"}
for ax, (col, titulo, ref, ic) in zip(ejes, [("pct_hospitaliza", "% de los atendidos que se hospitaliza", 100 * TOT_HOSP, ("pct_hospitaliza_ic_bajo", "pct_hospitaliza_ic_alto")),
                                              ("espera_mediana_h", "Espera de cama, mediana (h)", MED_ESPERA, ("espera_ic_bajo", "espera_ic_alto")),
                                              ("estancia_mediana_h", "Estancia en cama, mediana (h)", MED_ESTANCIA, ("estancia_ic_bajo", "estancia_ic_alto"))]):
    d0 = tabla(["grupo_edad", "tipo"], "perfiles_por_edad_y_tipo") if col == "pct_hospitaliza" else pd.read_csv(TABLAS / "perfiles_por_edad_y_tipo.csv")
    for tipo, g in d0.groupby("tipo"):
        g = g[g.episodios_con_atencion >= MIN_EPISODIOS]
        g = g.assign(_o=g.grupo_edad.map({e: i for i, e in enumerate(EDADES)})).sort_values("_o")
        if col != "pct_hospitaliza":
            g = g[g.estancias >= MIN_ESTANCIAS]
        ax.errorbar(g._o + {"Urgencias": -0.1, "Treatment urgency": 0.1, "Ambulatorio": 0.3}[tipo], g[col], yerr=[g[col] - g[ic[0]], g[ic[1]] - g[col]], fmt="o-", color=colores[tipo],
                    label=f"{tipo}", lw=1.4, capsize=2, ms=4)
    ax.axhline(ref, color="#999", ls="--", lw=1)
    ax.set_xticks(range(len(EDADES)))
    ax.set_xticklabels(EDADES)
    ax.set_title(titulo, fontsize=10.5)
    ax.set_xlabel("grupo de edad")
    ax.grid(alpha=0.25)
ejes[0].legend(fontsize=8)
fig.suptitle(f"Perfiles de pacientes ({DESDE[:7]} a 9-abr-2026): barras = intervalo de confianza 95 %; línea punteada = total", fontsize=11)
fig.tight_layout()
fig.savefig(GRAFICOS / "perfiles_pacientes.png", dpi=120)
print("\nguardado: perfiles_*.csv y perfiles_pacientes.png")
