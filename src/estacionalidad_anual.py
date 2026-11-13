"""
estacionalidad_anual.py  -  version 1 (12-nov-2026)  ·  ficha A9: darle forma de año al pronostico de demanda

PROBLEMA
  src/modelo_pronostico.py ya modela la semana, los festivos, la semana santa, el Carnaval y el fin de año, pero no la FORMA DEL AÑO (temporadas
  de lluvia, dengue, respiratorias). Con ~3 ciclos anuales confiables (feb-2023 a 9-abr-2026) estimar 12 efectos de mes es fragil, asi que se toma
  prestada la forma del año de CLIMATOLOGIAS externas de muchos años (la forma tipica por semana, no los valores observados del futuro).

VARIABLES CANDIDATAS (todas se conocen para cualquier fecha futura; ninguna usa datos del mismo periodo que se pronostica)
  fourier_k       senos y cosenos del dia del año (k = 1..3 armonicos): forma suave aprendida SOLO de nuestros datos (referencia barata)
  dengue_L        climatologia semanal de dengue en Barranquilla 2007-2022 (casos de la semana / promedio de su año, promediado entre años,
                  en log), adelantada L semanas (L en 0, 2, 4, 6, 8: el dengue de hace L semanas)
  lluvia_L        climatologia semanal de lluvia en Barranquilla 2005-2025 (NASA POWER), adelantada L semanas
  temperatura     climatologia semanal de temperatura
  Todas estandarizadas (media 0, desviacion 1) antes del ajuste de Poisson.

DISEÑO (sin mirar la prueba para decidir)
  Backtest igual que modelo_pronostico.retroceso: cortes cada 14 dias, pronostico a 365 dias con la regla vigente (nivel reciente + calendario),
  destinos hasta el 9-abr-2026. Se compara el WAPE por tramo de horizonte frente al modelo actual.
  - ELECCION (validacion): destinos de jul-dic 2025, horizontes de 31 a 182 dias (1-6 meses). Se elige la mejor variante por objetivo.
  - REGLA DE ACEPTACION (ficha A9): se acepta solo si mejora el error a 1-6 meses en la validacion SIN empeorar el de 1-7 dias.
  - PRUEBA: destinos de ene-9 abr 2026 (no se usan para elegir) y el backtest completo, para reportar.

DATOS  HUN_PROCESADOS/para_equipo/panel_diario.csv (agregado por dia) y HUN_EXTERNOS (por defecto <datos>/externos): dengue_barranquilla/Dengue_Bar.tab
       y nasa_power/barranquilla_diario_2005_2025.csv (ver su README). Nada de esto se sube a git.
SALIDA HUN_TABLAS/estacionalidad_*.csv y resultados/graficos/estacionalidad_anual.png
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modelo_pronostico as mp  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))
EXT = Path(os.environ.get("HUN_EXTERNOS", PROC.parent / "externos"))
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
GRAF = RAIZ / "resultados" / "graficos"
REZAGOS = [0, 2, 4, 6, 8]
VAL = ("2025-07-01", "2025-12-31")
PRUEBA = ("2026-01-01", mp.FIN_CONFIABLE)
OBJ = ["llegadas_con_atencion", "ingresos_a_cama"]


# ---------------------------------------------------------------- climatologias semanales (53 semanas)
def semana(idx):
    return np.minimum(pd.DatetimeIndex(idx).isocalendar().week.to_numpy(), 53)


def clima_dengue():
    d = pd.read_csv(EXT / "dengue_barranquilla" / "Dengue_Bar.tab", sep=None, engine="python")
    c = d.groupby(["DNGYEAR", "DNGWK"]).size().unstack(fill_value=0).reindex(columns=range(1, 54), fill_value=0)
    rel = c.div(c.iloc[:, :52].mean(axis=1), axis=0)              # forma relativa de cada año (quita los años de epidemia grande)
    s = np.log(rel.mean(axis=0) + 0.05)
    s[53] = s[52]                                                  # la semana 53 existe solo algunos años
    return s, c


def clima_nasa():
    ruta = EXT / "nasa_power" / "barranquilla_diario_2005_2025.csv"
    texto = ruta.read_text(encoding="utf-8").splitlines()
    ini = next(i for i, l in enumerate(texto) if l.startswith("YEAR"))
    n = pd.read_csv(ruta, skiprows=ini)
    n["fecha"] = pd.to_datetime(dict(year=n.YEAR, month=n.MO, day=n.DY))
    n = n.replace(-999, np.nan)
    n["sem"] = semana(n.fecha)
    s = n.groupby("sem").agg(lluvia=("PRECTOTCORR", "mean"), temperatura=("T2M", "mean"), humedad=("RH2M", "mean"))
    s["lluvia"] = s.lluvia.rolling(3, center=True, min_periods=1).mean()   # suaviza el ruido semanal de la lluvia
    return s.reindex(range(1, 54)).ffill(), n


def extras(idx, variante, cd, cn):
    """Columnas adicionales para un rango de fechas. Variante: 'fourier3', 'dengue_4', 'lluvia_6', 'dengue_4+lluvia_6', etc."""
    idx = pd.DatetimeIndex(idx)
    out = pd.DataFrame(index=idx)
    for parte in variante.split("+"):
        if parte.startswith("fourier"):
            k = int(parte[-1])
            t = 2 * np.pi * idx.dayofyear.to_numpy() / 365.25
            for j in range(1, k + 1):
                out[f"sen{j}"], out[f"cos{j}"] = np.sin(j * t), np.cos(j * t)
        else:
            nombre, _, rez = parte.partition("_")
            rez = int(rez or 0)
            base = cd if nombre == "dengue" else cn[nombre]
            out[parte] = base.reindex(semana(idx - pd.Timedelta(weeks=rez))).to_numpy()
    return out


def calendario_con(variante, cd, cn):
    def cal(idx):
        c = mp.calendario(idx)
        if variante == "actual":
            return c
        e = extras(idx, variante, cd, cn)
        e = (e - e.mean()) / e.std(ddof=0)                         # estandarizadas
        return pd.concat([c, e], axis=1)
    return cal


def retroceso(serie, calf, paso=14, minimo_dias=400):
    """Igual que modelo_pronostico.retroceso, con el calendario que se le pase."""
    cal = calf(pd.date_range(serie.index.min(), serie.index.max() + pd.Timedelta(days=366)))
    filas = []
    n_valido = serie.index.get_loc(serie.dropna().index.max()) + 1
    for pos in range(minimo_dias, n_valido - 7, paso):
        corte = serie.index[pos]
        f = mp.pronosticar_desde(serie.iloc[:pos + 1], cal, corte, 365, "reciente")
        real = serie.reindex(f.index)
        ok = real.notna().values
        filas.append(pd.DataFrame({"corte": corte, "lead": np.arange(1, len(f) + 1)[ok], "fecha": f.index[ok],
                                   "real": real.values[ok], "pronostico": f.values[ok]}))
    return pd.concat(filas, ignore_index=True)


def wape(bt, a, b, desde=None, hasta=None):
    t = bt[(bt.lead >= a) & (bt.lead <= b)]
    if desde:
        t = t[(t.fecha >= desde) & (t.fecha <= hasta)]
    return 100 * (t.real - t.pronostico).abs().sum() / t.real.sum() if len(t) else np.nan


TRAMOS = [(1, 7), (8, 30), (31, 91), (92, 182), (183, 365)]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cd, conteos = clima_dengue()
    cn, nasa = clima_nasa()
    print(f"dengue: {int(conteos.values.sum()):,} casos, años {conteos.index.min()}-{conteos.index.max()}; "
          f"semana pico de la climatologia: {int(cd.idxmax())}; nasa: {nasa.fecha.min().date()} a {nasa.fecha.max().date()}")
    panel = mp.cargar_panel(PROC / "para_equipo" / "panel_diario.csv")
    variantes = ["actual", "fourier1", "fourier2", "fourier3", "temperatura"] + [f"dengue_{r}" for r in REZAGOS] + [f"lluvia_{r}" for r in REZAGOS]
    filas, bts = [], {}
    for obj in OBJ:
        serie = panel[obj]
        serie.name = obj
        for v in variantes:
            bt = retroceso(serie, calendario_con(v, cd, cn))
            bts[(obj, v)] = bt
            fila = {"objetivo": obj, "variante": v,
                    "val_1_7": wape(bt, 1, 7, *VAL), "val_31_182": wape(bt, 31, 182, *VAL),
                    "prueba_1_7": wape(bt, 1, 7, *PRUEBA), "prueba_31_182": wape(bt, 31, 182, *PRUEBA)}
            for a, b in TRAMOS:
                fila[f"todo_{a}_{b}"] = wape(bt, a, b)
            filas.append(fila)
            print(obj, v, {k: round(x, 2) for k, x in fila.items() if isinstance(x, float)}, flush=True)
    res = pd.DataFrame(filas).round(2)
    # combinacion de las mejores fuentes externas por objetivo (elegidas en validacion)
    combos = []
    for obj in OBJ:
        r = res[res.objetivo == obj]
        mejor_d = r[r.variante.str.startswith("dengue")].sort_values("val_31_182").variante.iloc[0]
        mejor_l = r[r.variante.str.startswith("lluvia")].sort_values("val_31_182").variante.iloc[0]
        for v in [f"{mejor_d}+{mejor_l}", f"{mejor_d}+{mejor_l}+temperatura"]:
            serie = panel[obj]; serie.name = obj
            bt = retroceso(serie, calendario_con(v, cd, cn)); bts[(obj, v)] = bt
            fila = {"objetivo": obj, "variante": v, "val_1_7": wape(bt, 1, 7, *VAL), "val_31_182": wape(bt, 31, 182, *VAL),
                    "prueba_1_7": wape(bt, 1, 7, *PRUEBA), "prueba_31_182": wape(bt, 31, 182, *PRUEBA)}
            for a, b in TRAMOS:
                fila[f"todo_{a}_{b}"] = wape(bt, a, b)
            combos.append(fila)
            print(obj, v, {k: round(x, 2) for k, x in fila.items() if isinstance(x, float)}, flush=True)
    res = pd.concat([res, pd.DataFrame(combos).round(2)], ignore_index=True)
    base = res[res.variante == "actual"].set_index("objetivo")
    res["mejora_val_31_182"] = res.apply(lambda f: round(base.loc[f.objetivo, "val_31_182"] - f.val_31_182, 2), axis=1)
    res["cambio_val_1_7"] = res.apply(lambda f: round(f.val_1_7 - base.loc[f.objetivo, "val_1_7"], 2), axis=1)
    res["acepta"] = (res.mejora_val_31_182 > 0) & (res.cambio_val_1_7 <= 0.05) & (res.variante != "actual")
    TABLAS.mkdir(parents=True, exist_ok=True)
    res.to_csv(TABLAS / "estacionalidad_variantes.csv", index=False)
    pd.DataFrame({"dengue_log_relativo": cd, "lluvia_mm_dia": cn.lluvia, "temperatura_c": cn.temperatura}).round(3).to_csv(
        TABLAS / "estacionalidad_climatologias.csv", index_label="semana")
    elegidas = {}
    for obj in OBJ:
        r = res[(res.objetivo == obj) & res.acepta].sort_values("val_31_182")
        elegidas[obj] = r.variante.iloc[0] if len(r) else "actual"
    print("\nELEGIDAS (por validacion jul-dic 2025):", elegidas)
    print(res[["objetivo", "variante", "val_1_7", "val_31_182", "prueba_1_7", "prueba_31_182", "todo_1_7", "todo_31_91", "todo_92_182",
               "todo_183_365", "mejora_val_31_182", "acepta"]].to_string(index=False))

    # grafico: climatologias y el efecto de calendario estimado del año con la variante elegida
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
    s = np.arange(1, 54)
    ax[0].plot(s, (cd - cd.mean()) / cd.std(), label="Dengue (forma relativa, 2007-2022)", color="#c0392b")
    ax[0].plot(s, (cn.lluvia - cn.lluvia.mean()) / cn.lluvia.std(), label="Lluvia (2005-2025)", color="#2a6fb0")
    ax[0].set_xlabel("semana del año"); ax[0].set_title("Climatologias de Barranquilla (estandarizadas)"); ax[0].legend(fontsize=8)
    for obj in OBJ:
        serie = panel[obj].loc[:"2026-04-09"]
        dias = pd.date_range("2027-01-01", "2027-12-31")
        v = elegidas[obj]
        if v == "actual":
            continue
        calf = calendario_con(v, cd, cn)
        cal = calf(pd.date_range(serie.index.min(), dias.max()))
        beta = mp._ajustar(serie, cal, pd.Timestamp(mp.ENTRENA_HASTA))
        cols = [i for i, c in enumerate(cal.columns) if c not in mp.COLUMNAS]
        efecto = np.exp(cal.loc[dias].values[:, cols] @ beta[cols])
        ax[1].plot(dias, 100 * (efecto / efecto.mean() - 1), label=f"{obj} ({v})")
    ax[1].axhline(0, color="#999", lw=0.8); ax[1].set_title("Efecto de la estacionalidad sobre el pronostico de 2027 (%)"); ax[1].legend(fontsize=8)
    fig.tight_layout(); GRAF.mkdir(parents=True, exist_ok=True); fig.savefig(GRAF / "estacionalidad_anual.png", dpi=130)
