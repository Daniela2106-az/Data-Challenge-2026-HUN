"""
comparar_estimadores.py  -  version 3 (9-nov-2026)
Tarea A6: maneras de estimar la espera de cama, comparadas en la misma prueba. Define tambien el modelo final (M1), que usa
estimador_tiempo_restante.py.
(v2: M1 suma el HISTORIAL del paciente y su RECORRIDO en urgencias, con un modelo por momento de la espera ("landmark"); ver abajo.)
(v3, 9-nov: correcciones de la revision de A6, docs/estimador_tiempos.md seccion 7: (1) el diagnostico previo se fecha al FIN del episodio anterior, no
 a su inicio (habia fuga); (2) la ocupacion por zona usa la edad corregida de la persona real; (3) opcion retraso_h para probar si el recorrido en
 urgencias es una fuga del tramite de hospitalizacion. Las pruebas de la revision estan en src/revision_estimador.py.)
OJO SOBRE A QUIEN APLICA: se entrena y se prueba solo con pacientes que al final recibieron cama. Sirve para quien ya tiene orden de hospitalizacion,
no para cualquier paciente que llega a urgencias (solo ~9 % se hospitaliza).

LOS TRES METODOS
  M1. TIEMPO RESTANTE (supervivencia por hora): para cada hora de espera se estima la probabilidad de recibir cama en la hora siguiente, segun cuanto lleva
      esperando, la hora del reloj, el dia de la semana, la ocupacion de su zona en ese momento, la edad, el sexo y el tipo de visita (arboles de
      gradiente), mas su historial y su recorrido en urgencias. La version con la cola se prueba aparte: no mejora y usa saber quien se hospitalizara,
      asi que la final va sin cola. Multiplicando hora por hora sale la distribucion completa del tiempo que falta, y se puede recalcular en cualquier momento de la espera.
  M2. AL LLEGAR CON MAS VARIABLES (regresion por cuantiles): un modelo por percentil (25, 50, 75, 90) con lo que se sabe al llegar mas el estado del
      hospital en ese momento: hora, dia, mes, edad, sexo, tipo de visita, ocupacion de su zona, llegadas de las 6 h previas (la cola, aparte).
  M3. COLA: las camas se asignan a la tasa historica de su zona en cada hora del dia y dia de la semana. Dos versiones:
      M3a orden aleatorio: cada hora, la probabilidad de recibir cama es camas asignadas / pacientes en cola;
      M3b en orden de llegada: recibe cama cuando se han asignado tantas camas como pacientes tenia delante (Poisson).
  Referencias: el rango general (el mismo para todos) y la tabla de perfiles de estimador_tiempos.py (hora, edad, tipo de visita y sexo).

LA PRUEBA
  Entrenamiento con llegadas de feb-2023 a jun-2025; prueba con jul-2025 a 9-abr-2026 (estancias unicas con espera medida).
  1. Al llegar: cada metodo da los percentiles 25, 50, 75 y 90. Se mide la perdida de cuantiles (menor es mejor), la mejora frente al rango general y si
     los percentiles aciertan (cuantos casos quedan por debajo de cada uno).
  2. Durante la espera (despues de 6, 12, 24 y 48 h sin cama): el tiempo que le falta a quien sigue esperando. M2 no aplica (solo estima al llegar).
  3. Intervalos del 95 % por bootstrap por semanas (1.000 repeticiones) de la mejora de cada metodo y de su diferencia con M1.

HISTORIAL Y RECORRIDO (se conocen en el momento, sin trampa)
  Historial: de la ultima hospitalizacion de la misma persona terminada antes de llegar: su espera, su estancia, cuantos dias hace; cuantas hospitalizaciones
  previas tiene; y el grupo del ultimo diagnostico registrado en una visita anterior. La espera se repite (Spearman 0,34 con la anterior).
  Recorrido: registros de urgencias de la propia visita (visit_detail, etapas 9203 y 3045729) iniciados antes de cada hora: cuantas etapas de atencion
  empezaron, cuantas se sabe que cerraron y sus horas, cuantas siguen sin cierre, horas desde la ultima que empezo y cuantas admisiones. Solo cuenta un
  cierre si ocurrio antes de esa hora. Supuesto: el sistema registra cada etapa cuando empieza (no se pudo comprobar).
  Un modelo por momento ("landmark": al llegar, 3, 6, 12 h...): cada uno se entrena con quienes seguian esperando en ese momento y con el recorrido tal
  como se conocia entonces, y estima desde ahi. Un solo modelo con el recorrido hora por hora falla al estimar hacia adelante (al llegar, el recorrido
  queda congelado en cero etapas, algo que en los datos casi no ocurre despues de la primera hora).
  ESTIMADOR FINAL: con menos de HORAS_RECORRIDO horas de espera, el modelo del momento (historial + recorrido); desde ahi, un solo modelo con el historial
  (el recorrido ya no suma: 6,8 frente a 6,6 % a las 12 h, 4,7 frente a 5,3 % a las 24 h). OJO: el corte de 12 h se eligio mirando la prueba.

PROCEDIMIENTOS (si existe procedimientos_por_estancia.csv en HUN_CRUDOS; extraido por Daniela para A2b, lote 5)
  1. Corrige la edad y el sexo de esas estancias con los de la persona real (CLAUDE.md 4.10), que trae el archivo.
  2. Marca la GRAVEDAD (UCI, gases arteriales, lactato, troponina, transfusion, cateter central, hemocultivos, TAC de cabeza, monitoreo cardiaco) y el
     SERVICIO que atendio al paciente (ginecobstetricia, cirugia general, urologia, ortopedia, psiquiatria, pediatria, endoscopia digestiva).
  Los procedimientos NO tienen fecha: pueden ser de despues de recibir cama. Solo se usan como ESCENARIO (src/procedimientos_escenario.py), no en el
  estimador final.

COLA Y OCUPACION
  Por hora y por zona (adultos de 15 anos o mas, ninos), con estancias unicas: ocupacion = pacientes en cama; cola = pacientes que ya llegaron, se
  hospitalizaran y aun no tienen cama. OJO: la cola usa saber quien se hospitalizara despues; en el hospital equivale a los pacientes con orden de
  hospitalizacion pendiente, que si se conocen en el momento, pero aqui incluye tambien la atencion clinica previa a esa orden.
  Para estimar hacia adelante, la cola y la ocupacion se dejan fijas en el ultimo valor conocido (persistencia, que fue lo mejor para camas, CLAUDE.md 6b).

ENTRADA  tabla_episodios.parquet en HUN_PROCESADOS y visit_detail.csv en HUN_CRUDOS (por defecto datos/crudos) ; SALIDAS en HUN_TABLAS: comparacion_estimadores_al_llegar.csv, comparacion_estimadores_en_espera.csv,
         comparacion_estimadores_ic.csv,
         m1_probabilidad_por_hora_reloj.csv ; resultados/graficos/comparacion_estimadores.png
COMO CORRERLO  HUN_PROCESADOS=... HUN_TABLAS=... python3 src/comparar_estimadores.py   (unos minutos)
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
import estimador_tiempos as et  # noqa: E402

PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))
CRUDOS = Path(os.environ.get("HUN_CRUDOS", RAIZ / "datos" / "crudos"))
GRAF = RAIZ / "resultados" / "graficos"
DESDE, HASTA, CORTE = et.DESDE, et.HASTA, et.CORTE
Q = et.CUANTILES
MAX_H = 240                                   # horizonte de la supervivencia (10 dias); mas alla se toma como 240 h
CONTROLES = [3, 6, 12, 24, 48]
HORAS_RECORRIDO = 12                          # desde aqui el estimador final usa solo el historial
SEMILLA = 7
N_BOOT = 1000
# Ago-sep 2025: sobredemanda porque hospitales cercanos fueron intervenidos por el Estado y el HUN quedo como la unica opcion de la zona (dato del
# equipo, 7-nov). En los datos se ve poco: +6-7 % de llegadas frente a ago-sep 2024 y ingresos y espera mediana normales. Se evaluan aparte.
MESES_SOBREDEMANDA = ["2025-08", "2025-09"]
DX_PREVIO_AL_INICIO = os.environ.get("DX_PREVIO_AL_INICIO", "0") == "1"   # 1 = comportamiento de la v2 (con fuga), solo para comparar
H1 = np.timedelta64(1, "h")


# ----------------------------------------------------------------------
# 1) Estancias, cola y ocupacion por hora y zona
# ----------------------------------------------------------------------
def preparar():
    t = pd.read_parquet(PROC / "tabla_episodios.parquet")
    h = t[t.hospitalizado & t.estancia_unica & t.edad.notna() & (t.ini_est <= t.ini_hosp_est)].copy()
    h["zona"] = np.where(h.edad < 15, "ninos", "adultos")
    rejilla = pd.date_range(h.ini_est.min().floor("h"), h.fin_hosp_est.max().ceil("h"), freq="h").to_numpy()
    d = h[(h.ini_est >= DESDE) & (h.ini_est < HASTA) & h.espera_cama_h.notna() & h.sexo.isin(["Mujer", "Hombre"]) & h.tipo_visita.isin(et.TIPOS)].copy()
    d["grupo_edad"] = d.grupo_edad.astype(str)
    d["bloque_hora"] = pd.Series(et.BLOQUES)[d.hora.to_numpy() // 3].to_numpy()
    d["edad_cod"] = d.grupo_edad.map({e: i for i, e in enumerate(et.EDADES)})
    d["tipo_cod"] = d.tipo_visita.map({v: i for i, v in enumerate(et.TIPOS)})
    d["sexo_cod"] = (d.sexo == "Mujer").astype(int)
    d["zona_cod"] = (d.zona == "ninos").astype(int)
    d["llegadas_6h"] = d.get("llegadas_6h_previas", pd.Series(np.nan, index=d.index))
    d = d.reset_index(drop=True)
    d["clave"] = np.arange(len(d))
    d = procedimientos(d)
    # v3 (9-nov): la zona (adultos o ninos) de la ocupacion se cuenta con la edad CORREGIDA de la persona real cuando se conoce, igual que la del
    # paciente; antes la ocupacion usaba la edad sin corregir y un paciente podia quedar con la ocupacion de la otra zona.
    if "estancia_id" in d.columns:
        zona_corr = d.drop_duplicates("estancia_id").set_index("estancia_id").zona
        h["zona"] = h.estancia_id.map(zona_corr).fillna(h.zona)
    estado = contar_estado(h, rejilla)
    d = historial(t, d)
    cargar_etapas(d)
    return d, h, rejilla, estado


def contar_estado(h, rejilla):
    """Cola y ocupacion por hora y zona."""
    def contar(a, b):
        return np.searchsorted(np.sort(a), rejilla, side="right") - np.searchsorted(np.sort(b), rejilla, side="right")
    return {zona: {"cola": contar(g.ini_est.to_numpy(), g.ini_hosp_est.to_numpy()), "ocup": contar(g.ini_hosp_est.to_numpy(), g.fin_hosp_est.to_numpy())}
            for zona, g in h.groupby("zona")}


GRUPOS_DX = None
GRAVEDAD = {"uci": [4137917], "gases_arteriales": [4239236], "lactato": [3014111], "troponina": [3033745],
            "transfusion": [4323715, 4219996, 4205859, 4271693], "cateter_central": [4322380], "hemocultivo": [4252846, 4252847],
            "tac_cabeza": [4125350], "monitoreo_cardiaco": [4144544]}
SERVICIOS = {   # en orden de prioridad para el servicio principal
    "ginecobstetricia": [4138639, 4149939, 4070024, 37312440, 42536960, 4170107, 4324607, 44790279, 37016955, 4073278, 4064145, 4149132,
                         4015701, 4327269, 4062216],
    "cirugia_general": [4139904, 4198190, 4163971, 2003447, 43531100, 4119555, 37157276, 4157529, 4125906, 4134713],
    "urologia": [4125854, 4305063, 46232820, 4171400, 3031769],
    "ortopedia": [37208848, 37016880, 2790145, 37016878, 1072908, 37204684, 1072944, 3009096, 37204683, 37019010],
    "psiquiatria": [4136624, 4012657, 4230209, 4013683],
    "pediatria": [4080075],
    "endoscopia_digestiva": [4294382, 4249893],
}
PROC_GRAV = list(GRAVEDAD) + ["n_marcas_gravedad"]
PROC_SERV = ["servicio_cod"] + list(SERVICIOS)


def procedimientos(d):
    """Corrige edad y sexo con la persona real y agrega gravedad y servicio desde procedimientos_por_estancia.csv (si existe)."""
    ruta = CRUDOS / "procedimientos_por_estancia.csv"
    if not ruta.exists():
        return d
    pr = pd.read_csv(ruta)
    pers = pr.drop_duplicates("estancia_id").set_index("estancia_id")[["grupo_edad", "sexo"]]
    m = d.estancia_id.map(pers.grupo_edad)
    s = d.estancia_id.map(pers.sexo)
    d["grupo_edad"] = m.fillna(d.grupo_edad)
    d["sexo"] = s.where(s.isin(["Mujer", "Hombre"]), d.sexo)
    d["edad_cod"] = d.grupo_edad.map({e: i for i, e in enumerate(et.EDADES)})
    d["sexo_cod"] = (d.sexo == "Mujer").astype(int)
    d["zona"] = np.where(d.grupo_edad.isin(["0-4", "5-14"]), "ninos", "adultos")
    d["zona_cod"] = (d.zona == "ninos").astype(int)
    tiene = pr.groupby("estancia_id").concepto.apply(set)
    conj = d.estancia_id.map(tiene)
    d["con_procedimientos"] = conj.notna().astype(int)
    vacio = set()
    for nombre, ids in {**GRAVEDAD, **SERVICIOS}.items():
        d[nombre] = [int(bool((c if isinstance(c, set) else vacio) & set(ids))) for c in conj]
    d["n_marcas_gravedad"] = d[list(GRAVEDAD)].sum(axis=1)
    serv = np.full(len(d), len(SERVICIOS))                  # ultimo codigo = ninguno de esos servicios
    for i, nombre in reversed(list(enumerate(SERVICIOS))):
        serv = np.where(d[nombre] == 1, i, serv)
    d["servicio_cod"] = serv
    return d


def historial(t, d):
    """Datos de visitas anteriores de la misma persona, todos conocidos al llegar."""
    global GRUPOS_DX
    ep = t[["person_id", "ini", "hospitalizado", "estancia_unica", "espera_cama_h", "categoria_dx", "ini_hosp_est", "fin_hosp_est"]]
    hs = ep[ep.hospitalizado & ep.estancia_unica & ep.fin_hosp_est.notna()]
    hp = hs.assign(estancia_prev_h=(hs.fin_hosp_est - hs.ini_hosp_est).dt.total_seconds() / 3600)[["person_id", "fin_hosp_est", "espera_cama_h", "estancia_prev_h"]]
    hp = hp.rename(columns={"fin_hosp_est": "t_hosp", "espera_cama_h": "espera_prev_h"}).sort_values("t_hosp")
    # v3 (9-nov): el diagnostico de una visita anterior se da por conocido cuando TERMINA ese episodio, no cuando empieza: el 88 % de los
    # diagnosticos se registra tarde y con el inicio se colaba informacion que aun no existia al llegar (fuga). DX_PREVIO_AL_INICIO=1 vuelve a lo anterior.
    t_dx = "ini" if (DX_PREVIO_AL_INICIO or "fin" not in t.columns) else "fin"
    if t_dx == "ini" and not DX_PREVIO_AL_INICIO:
        print("AVISO: tabla_episodios no trae 'fin'; el diagnostico previo se fecha con el inicio del episodio (puede tener fuga)")
    dxp = t[t.categoria_dx.notna() & (t.categoria_dx != "Sin diagnostico") & t[t_dx].notna()][["person_id", t_dx, "categoria_dx"]]
    dxp = dxp.rename(columns={t_dx: "t_dx", "categoria_dx": "dx_previo"})
    q = d[["clave", "person_id", "ini_est"]].sort_values("ini_est")
    q = pd.merge_asof(q, hp, left_on="ini_est", right_on="t_hosp", by="person_id", allow_exact_matches=False)
    q = pd.merge_asof(q.sort_values("ini_est"), dxp.sort_values("t_dx"), left_on="ini_est", right_on="t_dx", by="person_id", allow_exact_matches=False)
    fines = hs.groupby("person_id").fin_hosp_est.apply(lambda s: np.sort(s.to_numpy()))
    vacio = np.array([], dtype="datetime64[ns]")
    q["n_hosp_previas"] = [int(np.searchsorted(fines.get(p, vacio), np.datetime64(x))) for p, x in zip(q.person_id, q.ini_est)]
    q["dias_desde_hosp"] = (q.ini_est - q.t_hosp).dt.total_seconds() / 86400
    GRUPOS_DX = sorted(ep.categoria_dx.dropna().unique())
    q["dx_previo_cod"] = q.dx_previo.map({g: i for i, g in enumerate(GRUPOS_DX)})
    return d.merge(q[["clave"] + HIST], on="clave", how="left")


ETAPAS = {}


def cargar_etapas(d):
    """Etapas de urgencias de cada estancia, en horas desde la llegada: inicios y fines de atencion (fin = nan si no tiene cierre) y admisiones."""
    ruta = CRUDOS / "visit_detail.csv"
    if not ruta.exists():
        raise FileNotFoundError(f"Falta {ruta}: el recorrido en urgencias sale de visit_detail.csv (indicar la carpeta con HUN_CRUDOS)")
    vd = pd.read_csv(ruta, usecols=["visit_occurrence_id", "visit_detail_concept_id", "visit_detail_start_datetime", "visit_detail_end_datetime"],
                     parse_dates=["visit_detail_start_datetime", "visit_detail_end_datetime"])
    vd = vd[vd.visit_detail_concept_id.isin([9203, 3045729]) & vd.visit_occurrence_id.isin(d.visit_occurrence_id)]
    vd = vd.merge(d[["visit_occurrence_id", "clave", "ini_est", "ini_hosp_est"]], on="visit_occurrence_id")
    vd = vd[(vd.visit_detail_start_datetime >= vd.ini_est) & (vd.visit_detail_start_datetime < vd.ini_hosp_est)]
    s = (vd.visit_detail_start_datetime - vd.ini_est).dt.total_seconds() / 3600
    e = ((vd.visit_detail_end_datetime - vd.ini_est).dt.total_seconds() / 3600).where(vd.visit_detail_end_datetime > vd.visit_detail_start_datetime)
    vd = vd.assign(s=s, e=e)
    ETAPAS.clear()
    for clave, g in vd.groupby("clave"):
        tu = g[g.visit_detail_concept_id == 3045729]
        ETAPAS[clave] = (tu.s.to_numpy(), tu.e.to_numpy(), g.loc[g.visit_detail_concept_id == 9203, "s"].to_numpy())


def recorrido_paciente(s, e, er, k_info, k):
    """Variables del recorrido con lo que se sabe en k_info (horas desde la llegada), para las horas k (las horas desde la ultima etapa se cuentan hasta k)."""
    k_info, k = np.asarray(k_info, float), np.asarray(k, float)
    out = {c: np.zeros(len(k)) for c in REC}
    out["horas_desde_ultimo_inicio"] = np.full(len(k), np.nan)
    if len(s):
        empezo = s[None, :] < k_info[:, None]
        valida = ~np.isnan(e)
        cerro = empezo & valida[None, :] & (np.where(valida, e, np.inf)[None, :] <= k_info[:, None])
        out["n_tu_iniciadas"] = empezo.sum(1).astype(float)
        out["n_tu_cerradas_antes"] = cerro.sum(1).astype(float)
        out["n_tu_sin_cierre"] = out["n_tu_iniciadas"] - out["n_tu_cerradas_antes"]
        out["horas_tu_cerradas_antes"] = (cerro * np.where(valida, np.nan_to_num(e) - s, 0)[None, :]).sum(1)
        ultima = np.where(empezo, s[None, :], -np.inf).max(1)
        out["horas_desde_ultimo_inicio"] = np.where(np.isfinite(ultima), k - ultima, np.nan)
    if len(er):
        out["n_admisiones"] = (er[None, :] < k_info[:, None]).sum(1).astype(float)
    return out


def recorrido_filas(d, idx, kk, desde, fijar, retraso_h=0.0):
    """Recorrido de cada fila paciente-hora; si fijar, con lo sabido en 'desde' (estimacion hacia adelante).
    retraso_h > 0: solo se ve lo que paso hasta 'retraso_h' horas antes (prueba de fuga, src/revision_estimador.py)."""
    res = {c: np.zeros(len(idx)) for c in REC}
    claves = d.clave.to_numpy()
    orden = np.argsort(idx, kind="stable")
    unicos, inicio = np.unique(idx[orden], return_index=True)
    fin = np.append(inicio[1:], len(orden))
    vacio = (np.array([]), np.array([]), np.array([]))
    for i, a, b in zip(unicos, inicio, fin):
        filas = orden[a:b]
        k = kk[filas]
        r = recorrido_paciente(*ETAPAS.get(claves[i], vacio), (np.full(len(k), desde) if fijar else k) - retraso_h, k)
        for c in REC:
            res[c][filas] = r[c]
    return res


def estado_en(d, rejilla, estado, horas_despues):
    """Cola y ocupacion de la zona de cada paciente, horas_despues de su llegada (arreglo o escalar)."""
    x = d.ini_est.to_numpy() + np.asarray(horas_despues) * H1
    k = np.clip(((x - rejilla[0]) // H1).astype(int), 0, len(rejilla) - 1)
    ninos = d.zona.to_numpy() == "ninos"
    cola = np.where(ninos, estado["ninos"]["cola"][k], estado["adultos"]["cola"][k])
    ocup = np.where(ninos, estado["ninos"]["ocup"][k], estado["adultos"]["ocup"][k])
    return cola, ocup


# ----------------------------------------------------------------------
# 2) Utilidades de evaluacion
# ----------------------------------------------------------------------
def perdida(y, pred):
    """Suma de las perdidas de cuantiles de los 4 percentiles (pred: matriz n x 4)."""
    e = y[:, None] - pred
    return np.nanmean(np.maximum(np.array(Q) * e, (np.array(Q) - 1) * e), axis=0).sum()


def perdida_por_caso(y, pred):
    """Perdida de cuantiles de cada caso (suma de los 4 percentiles); su promedio es perdida(y, pred)."""
    e = y[:, None] - pred
    return np.maximum(np.array(Q) * e, (np.array(Q) - 1) * e).sum(axis=1)


def intervalo_mejora(semana, l_metodo, l_ref, n_rep=N_BOOT):
    """Bootstrap por semanas (los pacientes de una misma semana se parecen): intervalo del 95 % de 1 - perdida(metodo) / perdida(referencia)."""
    rng = np.random.default_rng(SEMILLA)
    semanas = np.unique(semana)
    pos = {s: np.flatnonzero(semana == s) for s in semanas}
    sm = np.array([l_metodo[pos[s]].sum() for s in semanas]); sr = np.array([l_ref[pos[s]].sum() for s in semanas])
    elige = rng.integers(0, len(semanas), size=(n_rep, len(semanas)))
    mejora = 100 * (1 - sm[elige].sum(axis=1) / sr[elige].sum(axis=1))
    return np.percentile(mejora, [2.5, 97.5])


def cuantiles_de_supervivencia(S):
    """S: matriz n x (H+1) con S[:, k] = P(T > k horas). Devuelve n x 4 percentiles en horas (interpolados)."""
    F = 1 - S
    out = np.full((len(S), len(Q)), float(S.shape[1] - 1))
    for j, q in enumerate(Q):
        llega = F >= q
        k = np.where(llega.any(axis=1), llega.argmax(axis=1), -1)
        ok = k > 0
        f0, f1 = F[ok, k[ok] - 1], F[ok, k[ok]]
        out[ok, j] = (k[ok] - 1) + (q - f0) / np.maximum(f1 - f0, 1e-9)
        out[k == 0, j] = 0.0
    return out


# ----------------------------------------------------------------------
# 3) M1: supervivencia por hora (tiempo restante)
# ----------------------------------------------------------------------
HIST = ["espera_prev_h", "estancia_prev_h", "n_hosp_previas", "dias_desde_hosp", "dx_previo_cod"]
REC = ["n_tu_iniciadas", "n_tu_cerradas_antes", "n_tu_sin_cierre", "horas_tu_cerradas_antes", "horas_desde_ultimo_inicio", "n_admisiones"]
DINAMICAS = ["transcurrido", "hora_reloj", "dia_semana", "cola", "ocup"] + REC
COLS_M1 = ["transcurrido", "hora_reloj", "dia_semana", "cola", "ocup", "edad_cod", "tipo_cod", "sexo_cod", "zona_cod"]
CATEGORICAS = ["hora_reloj", "dia_semana", "tipo_cod", "dx_cod", "dx_previo_cod", "servicio_cod"]
COLS_M1_BASE = [c for c in COLS_M1 if c != "cola"]      # la cola no mejora la estimacion y no se conoce del todo en el momento
COLS_M1_FINAL = COLS_M1_BASE + HIST + REC


def filas_persona_hora(d, rejilla, estado, desde=0, fijar_estado=False, cols=COLS_M1, retraso_h=0.0):
    """Una fila por paciente y hora de espera desde 'desde' hasta MAX_H (o hasta recibir cama si se entrena)."""
    n = len(d)
    k = np.arange(desde, MAX_H)
    idx = np.repeat(np.arange(n), len(k))
    kk = np.tile(k, n)
    t = d.ini_est.to_numpy()[idx] + kk * H1
    reloj = pd.DatetimeIndex(t)
    if fijar_estado:
        cola0, ocup0 = estado_en(d, rejilla, estado, desde)
        cola, ocup = cola0[idx], ocup0[idx]
    else:
        cola, ocup = estado_en(d.iloc[idx].reset_index(drop=True), rejilla, estado, kk)
    X = pd.DataFrame({"transcurrido": kk, "hora_reloj": reloj.hour, "dia_semana": reloj.day_of_week, "cola": cola, "ocup": ocup,
                      **{c: d[c].to_numpy()[idx] for c in cols if c not in DINAMICAS}})
    if any(c in REC for c in cols):
        for c, v in recorrido_filas(d, idx, kk, desde, fijar_estado, retraso_h).items():
            X[c] = v
    return X, idx, kk


def pesos_recientes(d, idx, vida_media_dias):
    """Peso de cada fila segun lo reciente de la llegada: la mitad cada 'vida_media_dias' hacia atras (None = todos pesan igual)."""
    if vida_media_dias is None:
        return None
    edad = (d.ini_est.max() - d.ini_est).dt.total_seconds().to_numpy()[idx] / 86400
    return 0.5 ** (edad / vida_media_dias)


def entrenar_m1(tr, rejilla, estado, cols=COLS_M1, vida_media_dias=None):
    X, idx, kk = filas_persona_hora(tr, rejilla, estado, cols=cols)
    e = tr.espera_cama_h.to_numpy()[idx]
    vivo = kk <= np.floor(e)                                # en riesgo en la hora kk
    y = (kk == np.floor(e)).astype(int)
    w = pesos_recientes(tr, idx, vida_media_dias)
    X, y = X[vivo], y[vivo]
    print(f"M1: {len(X):,} filas paciente-hora para entrenar, {y.mean():.3f} de probabilidad media por hora")
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=63, min_samples_leaf=200,
                                       categorical_features=[cols.index(c) for c in CATEGORICAS if c in cols], random_state=SEMILLA)
    m.fit(X[cols], y, sample_weight=None if w is None else w[vivo])
    m.cols_ = cols
    return m


def entrenar_landmark(tr, rejilla, estado, desde, cols=None, vida_media_dias=None, retraso_h=0.0):
    """Modelo para estimar desde 'desde' horas de espera: quienes seguian esperando, con lo que se sabia en ese momento."""
    cols = COLS_M1_FINAL if cols is None else cols
    sub = tr[tr.espera_cama_h > desde].reset_index(drop=True)
    X, idx, kk = filas_persona_hora(sub, rejilla, estado, desde=desde, fijar_estado=True, cols=cols, retraso_h=retraso_h)
    e = sub.espera_cama_h.to_numpy()[idx]
    vivo = kk <= np.floor(e)
    y = (kk == np.floor(e)).astype(int)
    w = pesos_recientes(sub, idx, vida_media_dias)
    X = X[vivo]
    cols = [c for c in cols if X[c].nunique(dropna=True) > 1]           # al llegar, el recorrido aun no tiene informacion (todo cero): se deja fuera
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=63, min_samples_leaf=200,
                                       categorical_features=[cols.index(c) for c in CATEGORICAS if c in cols], random_state=SEMILLA)
    m.fit(X[cols], y[vivo], sample_weight=None if w is None else w[vivo])
    m.cols_, m.desde_, m.retraso_h_ = cols, desde, retraso_h
    return m


def predecir_m1(m, d, rejilla, estado, desde=0):
    X, idx, kk = filas_persona_hora(d, rejilla, estado, desde=desde, fijar_estado=True, cols=m.cols_, retraso_h=getattr(m, "retraso_h_", 0.0))
    p = m.predict_proba(X[m.cols_])[:, 1].reshape(len(d), MAX_H - desde)
    S = np.hstack([np.ones((len(d), 1)), np.cumprod(1 - p, axis=1)])
    return cuantiles_de_supervivencia(S)                    # horas que faltan desde 'desde'


# ----------------------------------------------------------------------
# 4) M2: cuantiles al llegar
# ----------------------------------------------------------------------
COLS_M2 = ["hora", "dia_semana_num", "mes", "edad_cod", "tipo_cod", "sexo_cod", "zona_cod", "cola0", "ocup0", "llegadas_6h"]


def matriz_m2(d, rejilla, estado):
    cola0, ocup0 = estado_en(d, rejilla, estado, 0)
    return d.assign(cola0=cola0, ocup0=ocup0, mes=d.ini_est.dt.month, dia_semana_num=d.ini_est.dt.day_of_week)[COLS_M2]


def m2(tr, te, rejilla, estado, cols=COLS_M2):
    Xtr, Xte = matriz_m2(tr, rejilla, estado)[cols], matriz_m2(te, rejilla, estado)[cols]
    ytr = np.log1p(tr.espera_cama_h.to_numpy())
    pred = np.column_stack([np.expm1(HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=300, learning_rate=0.05,
                                                                   max_leaf_nodes=31, min_samples_leaf=100, random_state=SEMILLA).fit(Xtr, ytr).predict(Xte))
                            for q in Q])
    return np.maximum.accumulate(np.clip(pred, 0, None), axis=1)


# ----------------------------------------------------------------------
# 5) M3: modelo de cola
# ----------------------------------------------------------------------
def tasas_asignacion(h):
    """Camas asignadas por hora, por zona, hora del dia y dia de la semana (promedio del entrenamiento)."""
    a = h[(h.ini_hosp_est >= DESDE) & (h.ini_hosp_est < CORTE)]
    slots = pd.date_range(DESDE, CORTE, freq="h", inclusive="left")
    n_slots = pd.Series(1, index=slots).groupby([slots.day_of_week, slots.hour]).sum()
    tasa = {}
    for zona, g in a.groupby("zona"):
        c = g.groupby([g.ini_hosp_est.dt.day_of_week, g.ini_hosp_est.dt.hour]).size()
        tasa[zona] = (c.reindex(n_slots.index, fill_value=0) / n_slots).to_numpy().reshape(7, 24)
    return tasa


def m3(d, rejilla, estado, tasa, desde=0, fifo=False):
    cola, _ = estado_en(d, rejilla, estado, desde)
    k = np.arange(desde, MAX_H)
    t = d.ini_est.to_numpy()[:, None] + k[None, :] * H1
    reloj = pd.DatetimeIndex(t.ravel())
    ninos = (d.zona.to_numpy() == "ninos")[:, None]
    lam = np.where(ninos, tasa["ninos"][reloj.day_of_week, reloj.hour].reshape(t.shape), tasa["adultos"][reloj.day_of_week, reloj.hour].reshape(t.shape))
    if fifo:
        delante = np.maximum(cola - 1, 0)                   # la cola ya incluye al paciente
        Lam = np.cumsum(lam, axis=1)
        S = np.hstack([np.ones((len(d), 1)), poisson.cdf(delante[:, None], Lam)])   # P(menos de 'delante'+1 camas asignadas)
    else:
        p = np.minimum(1, lam / np.maximum(cola, 1)[:, None])
        S = np.hstack([np.ones((len(d), 1)), np.cumprod(1 - p, axis=1)])
    return cuantiles_de_supervivencia(S)


# ----------------------------------------------------------------------
# 6) Referencias: rango general y tabla de perfiles (tambien condicionadas a seguir esperando)
# ----------------------------------------------------------------------
def referencias(tr, te, desde=0):
    trc = tr[tr.espera_cama_h > desde].assign(valor=lambda x: x.espera_cama_h - desde)
    res = et.tabla_por_nivel(trc, "espera_cama_h")
    general = np.tile(res[res.nivel == 0][[f"p{int(q * 100)}" for q in Q]].to_numpy(), (len(te), 1))
    perfil = et.asignar(te, res, len(et.DIMS))[[f"p{int(q * 100)}" for q in Q]].to_numpy()
    return general, perfil


def puntuar(nombre, y, pred, base, desde):
    fila = {"horas_esperando": desde, "metodo": nombre, "n_prueba": len(y), "perdida_cuantiles": round(perdida(y, pred), 3),
            "mejora_vs_general_pct": round(100 * (1 - perdida(y, pred) / base), 1),
            "error_abs_mediana_h": round(np.nanmean(np.abs(y - pred[:, 1])), 2)}
    for j, q in enumerate(Q):
        fila[f"pct_debajo_p{int(q * 100)}"] = round(100 * np.nanmean(y <= pred[:, j]), 1)
    fila["pct_dentro_p25_p75"] = round(100 * np.nanmean((y > pred[:, 0]) & (y <= pred[:, 2])), 1)
    return fila


if __name__ == "__main__":
    pd.set_option("display.width", 230)
    TABLAS.mkdir(parents=True, exist_ok=True)
    d, h, rejilla, estado = preparar()
    tr, te = d[d.ini_est < CORTE].reset_index(drop=True), d[d.ini_est >= CORTE].reset_index(drop=True)
    print(f"entrenamiento {len(tr):,} estancias | prueba {len(te):,}")
    m1_base = entrenar_m1(tr, rejilla, estado, COLS_M1_BASE)             # sin historial ni recorrido
    m1_hist = entrenar_m1(tr, rejilla, estado, COLS_M1_BASE + HIST)      # solo con historial
    m1_con_cola = entrenar_m1(tr, rejilla, estado, COLS_M1_BASE + ["cola"])
    tasa = tasas_asignacion(h)
    ic = []

    filas = []
    for desde in [0] + CONTROLES:
        sub = te[te.espera_cama_h > desde].reset_index(drop=True)
        y = np.minimum(sub.espera_cama_h.to_numpy() - desde, MAX_H)
        general, perfil = referencias(tr, sub, desde)
        base = perdida(y, general)
        preds = {"rango general (referencia)": general, "tabla de perfiles": perfil,
                 "M1 tiempo restante": predecir_m1(entrenar_landmark(tr, rejilla, estado, desde) if desde < HORAS_RECORRIDO else m1_hist, sub, rejilla, estado, desde),
                 "M1 sin historial ni recorrido": predecir_m1(m1_base, sub, rejilla, estado, desde),
                 "M1 solo con historial": predecir_m1(m1_hist, sub, rejilla, estado, desde),
                 "M1 sin historial ni recorrido, con cola (prueba)": predecir_m1(m1_con_cola, sub, rejilla, estado, desde),
                 "M3a cola, orden aleatorio": m3(sub, rejilla, estado, tasa, desde),
                 "M3b cola, orden de llegada": m3(sub, rejilla, estado, tasa, desde, fifo=True)}
        if desde == 0:
            preds["M2 al llegar con mas variables"] = m2(tr, sub, rejilla, estado, [c for c in COLS_M2 if c != "cola0"])
            preds["M2 con cola (prueba)"] = m2(tr, sub, rejilla, estado)
        semana = sub.ini_est.dt.to_period("W").astype(str).to_numpy()
        l_gen = perdida_por_caso(y, general)
        for nombre, pred in preds.items():
            lo, hi = intervalo_mejora(semana, perdida_por_caso(y, pred), l_gen)
            fila = {"horas_esperando": desde, "metodo": nombre, "mejora_vs_general_pct": round(100 * (1 - perdida_por_caso(y, pred).mean() / l_gen.mean()), 1),
                    "ic95_bajo": round(lo, 1), "ic95_alto": round(hi, 1)}
            if nombre != "M1 tiempo restante":                       # diferencia frente a M1: positiva = M1 mejor
                d_lo, d_hi = intervalo_mejora(semana, perdida_por_caso(y, preds["M1 tiempo restante"]), perdida_por_caso(y, pred))
                fila.update(m1_mejor_por_pct_ic95_bajo=round(d_lo, 1), m1_mejor_por_pct_ic95_alto=round(d_hi, 1))
            ic.append(fila)
        sobre = sub.ini_est.dt.to_period("M").astype(str).isin(MESES_SOBREDEMANDA).to_numpy()
        for periodo, m in [("toda la prueba", np.ones(len(sub), bool)), ("sin ago-sep 2025", ~sobre), ("solo ago-sep 2025", sobre)]:
            base_p = perdida(y[m], general[m])
            for nombre, pred in preds.items():
                filas.append({"periodo": periodo, **puntuar(nombre, y[m], pred[m], base_p, desde)})
        print(f"listo: {desde} h esperando ({len(sub):,} casos)")
    ic = pd.DataFrame(ic)
    ic.to_csv(TABLAS / "comparacion_estimadores_ic.csv", index=False)
    print("\nINTERVALOS DEL 95 % (bootstrap por semanas) y diferencia frente a M1 (positiva = M1 mejor)")
    print(ic.to_string(index=False))
    todo = pd.DataFrame(filas)
    todo[todo.horas_esperando == 0].to_csv(TABLAS / "comparacion_estimadores_al_llegar.csv", index=False)
    todo.to_csv(TABLAS / "comparacion_estimadores_en_espera.csv", index=False)
    res = todo[todo.periodo == "toda la prueba"]
    print("\nCOMPARACION (prueba jul-2025 a 9-abr-2026; perdida menor = mejor; lo ideal debajo de cada percentil es 25 / 50 / 75 / 90 %)")
    print(res.drop(columns="periodo").to_string(index=False))
    print("\nAL LLEGAR, SEPARANDO AGO-SEP 2025 (sobredemanda)")
    print(todo[(todo.horas_esperando == 0) & (todo.periodo != "toda la prueba")][["periodo", "metodo", "n_prueba", "mejora_vs_general_pct",
          "error_abs_mediana_h", "pct_debajo_p25", "pct_debajo_p50", "pct_debajo_p75", "pct_debajo_p90"]].to_string(index=False))

    # Lectura de M1: probabilidad media de recibir cama en la hora siguiente segun la hora del reloj (con todo lo demas como en la prueba)
    m1 = entrenar_landmark(tr, rejilla, estado, 0)
    X, _, _ = filas_persona_hora(te.sample(min(1500, len(te)), random_state=SEMILLA).reset_index(drop=True), rejilla, estado, cols=m1.cols_)
    X = X[X.transcurrido < 72]
    reloj = pd.DataFrame({"hora_reloj": range(24), "prob_cama_siguiente_hora": [m1.predict_proba(X.assign(hora_reloj=hh)[m1.cols_])[:, 1].mean() for hh in range(24)]})
    reloj.round(4).to_csv(TABLAS / "m1_probabilidad_por_hora_reloj.csv", index=False)
    print("\nM1: probabilidad media de recibir cama en la hora siguiente, por hora del reloj\n" + reloj.round(3).T.to_string())

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6))
    orden = ["rango general (referencia)", "tabla de perfiles", "M2 al llegar con mas variables", "M1 sin historial ni recorrido", "M1 tiempo restante",
             "M3a cola, orden aleatorio", "M3b cola, orden de llegada"]
    colores = {"rango general (referencia)": "#c9c8c3", "tabla de perfiles": "#8a8984", "M2 al llegar con mas variables": "#1baf7a",
               "M1 sin historial ni recorrido": "#9fc3ee", "M1 tiempo restante": "#2a78d6", "M3a cola, orden aleatorio": "#eb6834", "M3b cola, orden de llegada": "#f2a37f"}
    for nombre in orden:
        g = ic[ic.metodo == nombre]
        a1.plot(g.horas_esperando, g.mejora_vs_general_pct, marker="o", color=colores[nombre], label=nombre)
        a1.fill_between(g.horas_esperando, g.ic95_bajo, g.ic95_alto, color=colores[nombre], alpha=0.15, lw=0)
    a1.axhline(0, color="#52514e", lw=0.8)
    a1.set_xlabel("horas que el paciente ya lleva esperando")
    a1.set_ylabel("mejora frente al rango general (%)")
    a1.set_title("¿Qué método estima mejor lo que falta? (banda: IC 95 %)")
    a1.legend(frameon=False, fontsize=8)
    a1.grid(axis="y", color="#e5e4df")
    a2.bar(reloj.hora_reloj, 100 * reloj.prob_cama_siguiente_hora, color="#2a78d6")
    a2.set_xlabel("hora del reloj")
    a2.set_ylabel("% que recibe cama en la hora siguiente")
    a2.set_title("La hora del reloj manda (paciente que sigue esperando)")
    a2.grid(axis="y", color="#e5e4df")
    fig.text(0.01, 0.01, "Prueba con jul-2025 a 9-abr-2026 (entrenamiento feb-2023 a jun-2025). Fuente: src/comparar_estimadores.py", fontsize=8, color="#52514e")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(GRAF / "comparacion_estimadores.png", dpi=150)
