"""
simulador_integral.py  -  version 2 (15-nov-2026: entrenamiento con estacionalidad y casos)
Simulador integral del hospital (Fase 1 del plan de Samuel): UN SOLO motor de agentes que sigue a cada paciente
sintetico por toda su historia (llegada -> espera de cama -> cama -> estancia -> alta) y emite las vistas
sincronizadas que antes daban tres herramientas separadas: la demanda (pronostico), la cola de espera de cama
(con perfiles) y la ocupacion con altas diarias (planeador de camas).

QUE ES Y QUE NO ES (decidido en la conversacion de diseno del 14-nov; ver docs/simulador_integral.md)
  - NO encadena los tres modelos en serie (eso rompia los supuestos de cada uno): EXTIENDE el motor validado de
    A5 (src/simulacion_camas_montecarlo.py) hacia atras, de la cama a la llegada.
  - La espera de cada agente se SORTEA de trayectorias reales (muestreo), no se predice con el estimador A6:
    asignar la prediccion puntual comprimiria la varianza y danaria las bandas. A6 sigue siendo la herramienta
    de consulta para pacientes REALES (dashboard/pages/paciente.py); aqui solo vive su esqueleto estadistico.
  - Los ingresos a cama diarios EMERGEN de los agentes (llegadas x P(cama|perfil) x espera sorteada) y se
    CALIBRAN (factor kappa) para que su nivel esperado coincida con el pronostico validado de ingresos a cama.
    No se fuerza una cuota diaria con un ranking: el orden de llegada casi no predice el orden de cama
    (53 % de pares en orden, azar 50 % - CLAUDE.md 6b), asi que una fila de prioridad seria inventada.
  - La cola simulada es COTA INFERIOR de la presion real: solo contiene agentes que terminaran en cama (los
    que se van de alta desde urgencias no esperan cama y el 36-42 % de sus etapas no tiene hora de fin).

COMO FUNCIONA (una repeticion)
  1. Llegadas diarias ~ Poisson(pronostico de `llegadas` de modelo_pronostico.py) x ajuste_llegadas.
  2. Cada llegada recibe un perfil (grupo_edad x ruta) de la mezcla real de llegadas de 2025.
  3. Cada llegada se hospitaliza con probabilidad kappa x P(cama|perfil), donde P viene de tabla_episodios
     (hospitalizado & estancia_unica entre TODOS los episodios de 2025) y kappa calibra el nivel esperado
     contra el pronostico de ingresos a cama del MISMO horizonte y escenario.
  4. A cada agente que ira a cama se le sortea UNA TRAYECTORIA REAL de un paciente del mismo perfil
     (hora de llegada, espera de cama y estancia del MISMO paciente historico, ventana 2024-2025), suavizada
     con ruido gaussiano de ancho de Silverman (espera y estancia; misma tecnica que el motor A5).
  5. cama = llegada + espera ; alta = cama + estancia. El censo de camas se acumula por dia (identica
     convencion que A5: dur_dias = ceil(horas/24), alta exclusiva); la cola de espera se acumula POR HORA
     (de la hora de llegada a la hora de cama) y se promedia por dia, igual que la cola real observada.
  6. Siembra en el dia de corte: n0 pacientes ya en cama (censo real, estancia restante del bootstrap de A5,
     "inspection paradox" declarado) y q0 pacientes ya esperando (cola real del corte, espera completa
     sorteada - aproximacion declarada, solo afecta los primeros dias).

PUERTA DE VALIDACION (seccion backtest, __main__): el simulador integrado debe RE-PASAR el backtest de
ocupacion del motor A5 (ene a 9-abr-2026, entrenado hasta dic-2025; A5 dio MAE 8,6 camas, cobertura 78,8 %)
y ademas reproducir la cola real (media ~26 pacientes, docs/capacidad_efectiva.md) y las altas diarias.
Si la integracion empeora el backtest de ocupacion, se revierte a generar ingresos a cama directo (motor A5)
y la vista de llegadas queda desacoplada.

ENTRADAS  datos/procesados/para_equipo/estancias_hospitalizacion.csv (via simulacion_camas_montecarlo)
          datos/procesados/tabla_episodios.parquet (solo 5 columnas: P(cama|perfil) y mezcla de llegadas)
          datos/procesados/para_equipo/panel_diario.csv (serie de llegadas, via modelo_pronostico)
SALIDAS   resultados/tablas/simint_*.csv ; resultados/graficos/simint_resultados.png

LIMITES
  - Cola = solo futuros hospitalizados (cota inferior; la congestion de urgencias NO se puede simular con
    estos datos). Fidelidad ESTADISTICA, no bola de cristal: reproduce patrones, no dias concretos.
  - P(cama|perfil) constante por dia: el patron semanal de los ingresos emergentes hereda el de las llegadas
    suavizado por la espera; la calibracion kappa es global (un factor por corrida), no por dia de semana.
  - Los agentes sembrados en la cola reciben su espera completa (no la restante); solo afecta ~primeros dias.
  - Asociacion, no causa; periodo confiable hasta el 9-abr-2026; todo lo de siempre del proyecto.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modelo_pronostico as mp
import simulacion_camas_montecarlo as scm

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
GRAFICOS = RAIZ / "resultados" / "graficos"

VENTANA_MEZCLA_LLEGADAS = ("2025-01-01", "2026-01-01")   # mezcla de perfiles y P(cama) entre llegadas: ultimo ano completo confiable
MIN_CELDA = 30                                            # igual criterio que scm.PERFIL_MIN_CELDA
N_REP = scm.N_REP
SEMILLA = scm.SEMILLA
BACKTEST_CORTE = scm.BACKTEST_CORTE
HORIZONTE_PROYECCION = scm.HORIZONTE_PROYECCION
SERIES_SALIDA = ("llegadas", "ingresos_cama", "altas", "cola", "total", "ninos", "adultos")


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


# ----------------------------------------------------------------------
# 1) Serie de llegadas (panel) y P(cama | perfil) + mezcla de llegadas (tabla_episodios)
# ----------------------------------------------------------------------
titulo("1. LLEGADAS: serie diaria, mezcla de perfiles y P(cama | perfil)")
_panel = mp.cargar_panel()                                 # ya blanqueado desde el 10-abr-2026 (CLAUDE.md 4.9)
serie_llegadas = _panel["llegadas"].rename("llegadas")
print(f"serie_llegadas: {serie_llegadas.dropna().index.min().date()} a {serie_llegadas.dropna().index.max().date()} "
      f"(media 2025: {serie_llegadas['2025'].mean():.0f}/dia; incluye ~4 % de replicas, cota conocida - CLAUDE.md 4.13)")

_ep = pd.read_parquet(PROC / "tabla_episodios.parquet",
                      columns=["fecha", "grupo_edad", "tipo_visita", "hospitalizado", "estancia_unica"])
_ep = _ep[_ep.grupo_edad.notna() & _ep.tipo_visita.notna()].copy()
_ep["ruta"] = _ep.tipo_visita.where(_ep.tipo_visita.isin(scm.TIPOS_VALIDOS), "Urgencias")  # mismo plegado que A5
_ep["fecha"] = pd.to_datetime(_ep.fecha)
_ep25 = _ep[(_ep.fecha >= VENTANA_MEZCLA_LLEGADAS[0]) & (_ep.fecha < VENTANA_MEZCLA_LLEGADAS[1])]
# el numerador usa estancia_unica para no contar dos veces las estancias gemelas (CLAUDE.md 4.6/4.8); el
# denominador (todas las llegadas) incluye las replicas igual que la serie del panel, asi ambos lados cuadran.
_grupos = _ep25.groupby(["grupo_edad", "ruta"], observed=True)
_tam = _grupos.size()
_p_celda = _grupos.apply(lambda g: (g.hospitalizado & g.estancia_unica).mean(), include_groups=False)
_p_global = float((_ep25.hospitalizado & _ep25.estancia_unica).mean())
P_CAMA = {per: (float(_p_celda[per]) if _tam[per] >= MIN_CELDA else _p_global) for per in _tam.index}

_mz = _tam / _tam.sum()
PERFILES_LLEG = list(_mz.index)                            # lista de tuplas (grupo_edad, ruta)
PROB_LLEG = _mz.values
P_CAMA_VEC = np.array([P_CAMA[per] for per in PERFILES_LLEG])
P_MEDIA = float((PROB_LLEG * P_CAMA_VEC).sum())
print(f"mezcla de llegadas {VENTANA_MEZCLA_LLEGADAS[0]} a {VENTANA_MEZCLA_LLEGADAS[1]}: {len(PERFILES_LLEG)} perfiles "
      f"(edad x ruta) | P(cama) global {100 * _p_global:.1f} % | P media ponderada {100 * P_MEDIA:.1f} %")
print(pd.Series(P_CAMA).mul(100).round(1).unstack().to_string())

# ----------------------------------------------------------------------
# 2) Trayectorias reales por perfil: (hora de llegada, espera de cama, estancia) del MISMO paciente
# ----------------------------------------------------------------------
titulo("2. TRAYECTORIAS (hora de llegada, espera, estancia) POR PERFIL - bootstrap conjunto suavizado")
_tr = scm.est.copy()                                       # estancias unicas, ya cargadas por el motor A5
_tr["llegada"] = pd.to_datetime(_tr.llegada)
_tr = _tr[_tr.alta_completa & _tr.horas_hosp.notna() & _tr.grupo_edad.notna() & _tr.tipo_visita.notna()]
_n_sin_espera = int(_tr.espera_cama_h.isna().sum())
_tr = _tr[_tr.espera_cama_h.notna()]
_tr = _tr[(_tr.ingreso_cama >= scm.VENTANA_BOOTSTRAP[0]) & (_tr.ingreso_cama < scm.VENTANA_BOOTSTRAP[1])]
_tr["ruta"] = _tr.tipo_visita.where(_tr.tipo_visita.isin(scm.TIPOS_VALIDOS), "Urgencias")
print(f"estancias con trayectoria completa en {scm.VENTANA_BOOTSTRAP[0]} a {scm.VENTANA_BOOTSTRAP[1]}: {len(_tr)} "
      f"(descartadas por espera faltante en toda la historia: {_n_sin_espera})")


def _pool(df):
    return (df.hora_llegada.to_numpy(float), df.espera_cama_h.to_numpy(float), df.horas_hosp.to_numpy(float),
            scm.ancho_banda_silverman(df.espera_cama_h.to_numpy(float)),
            scm.ancho_banda_silverman(df.horas_hosp.to_numpy(float)))


TRAY_PERFIL = {per: _pool(g) for per, g in _tr.groupby(["grupo_edad", "ruta"], observed=True) if len(g) >= MIN_CELDA}
TRAY_EDAD = {g: _pool(gg) for g, gg in _tr.groupby("grupo_edad", observed=True)}
TRAY_GLOBAL = _pool(_tr)
print(f"celdas de trayectoria con >= {MIN_CELDA} casos: {len(TRAY_PERFIL)}; respaldo por edad: {len(TRAY_EDAD)}; "
      f"espera mediana del pool: {np.median(TRAY_GLOBAL[1]):.1f} h; estancia mediana: {np.median(TRAY_GLOBAL[2]):.1f} h")


def trayectoria_para(grupo, ruta, rng, n):
    """Sortea `n` trayectorias reales (hora de llegada, espera_h, estancia_h) de pacientes del perfil, con
    suavizado gaussiano de Silverman sobre la espera y la estancia (la hora de llegada queda tal cual: es
    discreta 0-23). Conserva la correlacion espera-estancia del paciente real (los que esperan mas tienden a
    quedarse mas, docs/factores_estancia.md: +9 % por desviacion de espera)."""
    horas, esperas, estancias, ancho_e, ancho_s = TRAY_PERFIL.get((grupo, ruta)) or TRAY_EDAD.get(grupo) or TRAY_GLOBAL
    sel = rng.integers(0, len(horas), size=n)
    e = esperas[sel] + (rng.normal(0, ancho_e, n) if ancho_e else 0.0)
    s = estancias[sel] + (rng.normal(0, ancho_s, n) if ancho_s else 0.0)
    return horas[sel], np.clip(e, 0, None), np.clip(s, 0, None)


# ----------------------------------------------------------------------
# 3) Cola real observada (para sembrar y para el backtest): pacientes entre su llegada y su cama
# ----------------------------------------------------------------------
titulo("3. COLA REAL DE ESPERA DE CAMA (censo horario de llegada a cama, promedio diario)")
_cq = scm.est[["llegada", "ingreso_cama"]].copy()
_cq["llegada"] = pd.to_datetime(_cq.llegada)
_cq = _cq.dropna()
_horas_q = pd.date_range(_cq.llegada.min().floor("h"), _cq.ingreso_cama.max().floor("h"), freq="h")
_dq = (_cq.llegada.dt.floor("h").value_counts()
       .sub(_cq.ingreso_cama.dt.floor("h").value_counts(), fill_value=0).reindex(_horas_q, fill_value=0))
_colah = _dq.cumsum()
COLA_REAL_D = _colah.groupby(_colah.index.normalize()).mean().reindex(scm.dias_panel)
print(f"cola real media {COLA_REAL_D.mean():.1f} pacientes (referencia docs/capacidad_efectiva.md: ~26) | "
      f"p90 {COLA_REAL_D.quantile(.9):.0f} | ultimo corte confiable: {COLA_REAL_D.dropna().index.max().date()}")

ALTAS_REAL_D = scm.est.alta.dt.normalize().value_counts().reindex(scm.dias_panel, fill_value=0).astype(float)


# ----------------------------------------------------------------------
# 4) Motor integrado
# ----------------------------------------------------------------------
titulo("4. MOTOR INTEGRADO (agentes: llegada -> espera -> cama -> estancia -> alta)")


def _una_repeticion(lam_lleg, p_eff, rng, ajuste_estancia, ajuste_espera, n0_camas, q0_cola):
    """Una repeticion sobre len(lam_lleg) dias. Devuelve dict de arrays diarios (ver SERIES_SALIDA)."""
    n_dias = len(lam_lleg)
    n_horas = n_dias * 24
    n_lleg = rng.poisson(np.clip(lam_lleg, 0, None))                       # llegadas por dia
    por_perfil = rng.multinomial(n_lleg, PROB_LLEG)                        # (dias, perfiles)
    n_hosp = rng.binomial(por_perfil, p_eff)                               # cuantos de cada celda iran a cama

    # --- agentes nuevos que iran a cama: dia de llegada + perfil ---
    d_idx, p_idx = np.nonzero(n_hosp)
    reps = n_hosp[d_idx, p_idx]
    dia_lleg = np.repeat(d_idx, reps)
    perf = np.repeat(p_idx, reps)

    # --- siembra: q0 ya esperando (llegada en el dia 0) y n0 ya en cama ---
    perf_semilla_q = rng.choice(len(scm.PERFILES_HIST), size=q0_cola, p=scm.PROB_PERFILES)
    dia_lleg = np.concatenate([np.zeros(q0_cola, dtype=int), dia_lleg])
    # los perfiles de la cola sembrada vienen de la mezcla de INGRESOS (son futuros hospitalizados);
    # se traducen al indice de PERFILES_LLEG por su tupla (grupo, ruta) - si una tupla no esta, cae al global.
    _map = {per: i for i, per in enumerate(PERFILES_LLEG)}
    perf = np.concatenate([np.array([_map.get(scm.PERFILES_HIST[i], 0) for i in perf_semilla_q], dtype=int), perf])
    total = len(dia_lleg)

    hora = np.empty(total)
    espera = np.empty(total)
    estancia = np.empty(total)
    for p in np.unique(perf):
        m = perf == p
        g, r = PERFILES_LLEG[p]
        hora[m], espera[m], estancia[m] = trayectoria_para(g, r, rng, int(m.sum()))
    espera = espera * ajuste_espera
    estancia = estancia * ajuste_estancia
    # la cola sembrada ya esta esperando en el instante 0: su "llegada" es la hora 0 del dia 0
    hora[:q0_cola] = 0.0

    t_lleg_h = dia_lleg * 24.0 + hora                                      # horas desde el inicio del dia 0
    t_cama_h = t_lleg_h + espera
    dia_cama = np.floor(t_cama_h / 24.0).astype(int)
    dur_dias = np.clip(np.ceil(estancia / 24.0).astype(int), 1, None)      # misma convencion que el motor A5
    dia_alta = dia_cama + dur_dias                                         # exclusivo
    grupos = np.array([PERFILES_LLEG[p][0] for p in perf])
    es_nino = np.isin(grupos, scm.GRUPOS_NINOS)

    # --- pacientes ya en cama el dia 0 (censo real del corte): estancia restante del bootstrap de A5 ---
    idx0 = rng.choice(len(scm.PERFILES_HIST), size=n0_camas, p=scm.PROB_PERFILES)
    g0 = np.array([scm.PERFILES_HIST[i][0] for i in idx0])
    est0 = np.empty(n0_camas)
    for i in np.unique(idx0):
        m = idx0 == i
        g, r = scm.PERFILES_HIST[i]
        est0[m] = scm.horas_para(g, r, rng, int(m.sum()))
    est0 = est0 * ajuste_estancia
    dur0 = np.clip(np.ceil(est0 / 24.0).astype(int), 1, None)
    nino0 = np.isin(g0, scm.GRUPOS_NINOS)

    # --- censo de camas por dia (entra el dia de cama, sale el dia de alta; semillas entran el dia 0) ---
    en_horizonte = dia_cama < n_dias

    def censo_camas(mask):
        delta = np.zeros(n_dias + 1)
        np.add.at(delta, dia_cama[mask & en_horizonte], 1.0)
        np.add.at(delta, np.clip(dia_alta[mask & en_horizonte], 0, n_dias), -1.0)
        m0 = np.ones(n0_camas, dtype=bool) if mask is TODOS else (nino0 if mask is NINOS_MASK else ~nino0)
        delta[0] += m0.sum()
        np.add.at(delta, np.clip(dur0[m0], 0, n_dias), -1.0)
        return np.cumsum(delta)[:n_dias]

    TODOS = np.ones(total, dtype=bool)
    NINOS_MASK = es_nino
    censo_total = censo_camas(TODOS)
    censo_ninos = censo_camas(NINOS_MASK)
    censo_adultos = censo_camas(~NINOS_MASK)

    # --- ingresos a cama y altas por dia (emergentes) ---
    ingresos = np.bincount(dia_cama[en_horizonte], minlength=n_dias)[:n_dias].astype(float)
    alta_valida = (dia_alta >= 0) & (dia_alta < n_dias) & en_horizonte
    altas = np.bincount(dia_alta[alta_valida], minlength=n_dias)[:n_dias].astype(float)
    alta0 = dur0[dur0 < n_dias]
    altas += np.bincount(alta0, minlength=n_dias)[:n_dias]

    # --- cola de espera por HORA (llegada a cama), promediada por dia (igual que la cola real observada) ---
    q_in = np.clip(np.floor(t_lleg_h).astype(int), 0, n_horas)
    q_out = np.clip(np.floor(t_cama_h).astype(int), 0, n_horas)
    delta_q = np.zeros(n_horas + 1)
    con_espera = q_out > q_in
    np.add.at(delta_q, q_in[con_espera], 1.0)
    np.add.at(delta_q, q_out[con_espera], -1.0)
    cola = np.cumsum(delta_q)[:n_horas].reshape(n_dias, 24).mean(axis=1)

    return {"llegadas": n_lleg.astype(float), "ingresos_cama": ingresos, "altas": altas, "cola": cola,
            "total": censo_total, "ninos": censo_ninos, "adultos": censo_adultos}



# ----------------------------------------------------------------------
# MODELOS DE LA FICHA A9 Y CASOS (15-nov-2026)
# ----------------------------------------------------------------------
# MODELOS: por defecto el pronostico usa solo el calendario (dia de la semana, festivos, Semana Santa, Carnaval). El usuario puede marcar,
# uno por uno, los modelos de la ficha A9 (formas del año tomadas de climatologias publicas). Cada modelo entra SOLO en la serie donde A9
# lo probo: dengue y lluvia en las llegadas; curva del año, IRA y EDA en los ingresos a cama. La forma del año pone el RITMO del año.
# CASOS: solo para los modelos marcados (la curva del año no tiene caso). El usuario elige un nivel de la escala de ese caso (muy bajo,
# bajo, normal, alto, muy alto, grave, record: lo que de verdad paso en 2023-2025, ESCALA_CASOS), y el caso multiplica el pronostico de las
# llegadas y de los ingresos a cama por el efecto PROPIO medido en las semanas reales de 2023 a 2025 (src/medir_casos.py ->
# casos_efecto.csv): una elasticidad b por caso y serie, efecto = (1 + X/100)^b. Al medirse contra lo normal de cada semana y descontando
# la forma del año, el efecto vale igual en cualquier mes (un brote de dengue en julio cuenta como brote) y no repite la temporada del
# modelo marcado. Los cuatro casos se midieron juntos, asi que combinarlos multiplicando no repite efectos. El caso dura todo el horizonte.
# Es una asociacion. Los datos externos llegan a 2025.
MODELOS_A9 = {
    "dengue": ("Dengue", "llegadas", "Forma del año del dengue en Barranquilla (2007–2022), en las llegadas."),
    "lluvia": ("Lluvia", "llegadas", "Forma del año de la lluvia (NASA POWER, 2005–2025), en las llegadas. A9 la probó y la descartó."),
    "curva": ("Curva suave del año", "ingresos", "Una curva que solo sigue el día del año, en los ingresos a cama."),
    "ira": ("Infecciones respiratorias", "ingresos", "Forma del año de las consultas por IRA (SIVIGILA, 2016–2019), en los ingresos a cama."),
    "eda": ("Diarreas", "ingresos", "Forma del año de los casos de EDA (SIVIGILA, 2016–2019), en los ingresos a cama."),
}
CASOS = {"dengue": "Dengue", "lluvia": "Lluvias", "ira": "Infecciones respiratorias", "eda": "Diarreas"}
DASHBOARD_TABLAS = Path(__import__("os").environ.get("HUN_PROCESADOS", PROC)) / "dashboard"
# Elasticidades de la ultima corrida de src/medir_casos.py (15-nov-2026), por si casos_efecto.csv no esta en este equipo.
_EFECTO_RESPALDO = {}
_ERROR_RESPALDO = {("llegadas", "ninguno"): (7.83, 6.90), ("llegadas", "dengue"): (7.28, 7.05), ("llegadas", "lluvia"): (7.57, 6.79),
                   ("ingresos", "ninguno"): (16.73, 20.07), ("ingresos", "curva"): (16.75, 19.84), ("ingresos", "ira"): (16.63, 19.98),
                   ("ingresos", "eda"): (16.95, 19.95)}


def _leer_efectos():
    try:
        t = pd.read_csv(DASHBOARD_TABLAS / "casos_efecto.csv")
        return {(r.caso, r.serie): float(r.elasticidad) for r in t.itertuples()}
    except (OSError, KeyError, ValueError, AttributeError):
        return _EFECTO_RESPALDO


def _leer_errores():
    try:
        t = pd.read_csv(DASHBOARD_TABLAS / "modelos_error.csv")
        return {(r.serie, r.modelo): (float(r.wape_validacion), float(r.wape_prueba)) for r in t.itertuples()}
    except (OSError, KeyError, ValueError, AttributeError):
        return _ERROR_RESPALDO


# Escala de niveles de cada caso (src/medir_casos.py -> casos_escala.csv): cuanto estuvo por encima o por debajo de lo normal en las
# semanas reales de 2023 a 2025 (percentiles 5, 25, 75, 90, 95 y maximo). Respaldo con la ultima corrida (15-nov-2026).
_ESCALA_RESPALDO = {
    "dengue": [("Muy bajo", -47), ("Alto", 216), ("Muy alto", 309), ("Grave", 369), ("Récord", 492)],
    "ira": [("Alto", 44), ("Muy alto", 63), ("Grave", 78), ("Récord", 113)],
    "eda": [("Muy bajo", -27), ("Bajo", -6), ("Alto", 24), ("Muy alto", 35), ("Grave", 41), ("Récord", 92)],
    "lluvia": [("Muy bajo", -79), ("Bajo", -61), ("Alto", 92), ("Muy alto", 195), ("Grave", 479), ("Récord", 1570)],
}


def _leer_escala():
    try:
        t = pd.read_csv(DASHBOARD_TABLAS / "casos_escala.csv", encoding="utf-8").sort_values(["caso", "percentil"])
        return {c: [(r.nivel, int(r.pct_sobre_normal)) for r in g.itertuples()] for c, g in t.groupby("caso")}
    except (OSError, KeyError, ValueError, AttributeError):
        return _ESCALA_RESPALDO


def niveles_caso(caso):
    """Niveles del caso en orden, con «Normal» (0 %) en su lugar: [(nombre, % sobre lo normal), ...]."""
    esc = ESCALA_CASOS.get(caso, [])
    return [n for n in esc if n[1] < 0] + [("Normal", 0)] + [n for n in esc if n[1] > 0]


EFECTO_CASOS = _leer_efectos()      # (caso, serie) -> elasticidad
ERROR_MODELOS = _leer_errores()     # (serie, modelo) -> (WAPE validacion jul-dic 2025, WAPE prueba ene-9 abr 2026)
ESCALA_CASOS = _leer_escala()       # caso -> [(nivel, % sobre lo normal)] sin «Normal»


def _clima_lluvia():
    """Climatologia semanal de lluvia (mm/dia por semana ISO 1..53, NASA POWER 2005-2025, suavizada 3 semanas como en A9),
    estandarizada. None si la tabla de A9 no esta en este equipo (entonces el modelo «lluvia» no se ofrece)."""
    try:
        c = pd.read_csv(TABLAS / "estacionalidad_climatologias.csv")
        v = c.set_index("semana")["lluvia_mm_dia"].reindex(range(1, 54)).ffill().rolling(3, center=True, min_periods=1).mean()
        return ((v - v.mean()) / v.std()).to_numpy()
    except (OSError, KeyError, ValueError):
        return None


CLIMA_LLUVIA = _clima_lluvia()
MODELOS_DISPONIBLES = [k for k in MODELOS_A9 if k != "lluvia" or CLIMA_LLUVIA is not None]


def columnas_bases(idx, bases):
    """Columnas de las bases elegidas para un rango de fechas."""
    idx = pd.DatetimeIndex(idx)
    out = pd.DataFrame(index=idx)
    for b in bases or ():
        if b == "dengue":
            out["base_dengue"] = mp.regresor_estacional(idx, mp.CLIMA_DENGUE, mp.REZAGO_DENGUE_SEMANAS).to_numpy()
        elif b == "ira":
            out["base_ira"] = mp.regresor_estacional(idx, mp.CLIMA_IRA, 0).to_numpy()
        elif b == "eda":
            out["base_eda"] = mp.regresor_estacional(idx, mp.CLIMA_EDA, 0).to_numpy()
        elif b == "lluvia" and CLIMA_LLUVIA is not None:
            out["base_lluvia"] = mp.regresor_estacional(idx, CLIMA_LLUVIA, 0).to_numpy()
        elif b == "curva":
            g = mp._base_gam(idx.dayofyear)
            for i in range(g.shape[1]):
                out[f"base_curva_{i}"] = g[:, i]
    return out


def pronostico_entrenado(serie, corte, dias, escenario="historico", bases=()):
    """Pronostico de `dias` dias despues de `corte`, entrenado con el calendario mas las `bases` (sin bases, el de siempre)."""
    corte = pd.Timestamp(corte)
    if not bases:
        cal = mp.calendario(pd.date_range(serie.index.min(), corte + pd.Timedelta(days=dias + 2)))
        return mp.pronosticar_desde(serie, cal, corte, dias, escenario)
    idx = pd.date_range(serie.index.min(), corte + pd.Timedelta(days=dias + 2))
    cal = pd.concat([mp.calendario(idx), columnas_bases(idx, bases)], axis=1)
    return mp.pronosticar_desde(serie, cal, corte, dias, escenario)


def efecto_aplicado(caso, serie, cambio_pct):
    """% de cambio de la demanda de `serie` si el caso esta `cambio_pct` % por encima (o por debajo) de lo normal: (1 + X/100)^b - 1."""
    if not cambio_pct:
        return 0.0
    return 100.0 * ((1 + cambio_pct / 100.0) ** EFECTO_CASOS.get((caso, serie), 0.0) - 1)


def factor_casos(casos, serie):
    """Factor de la demanda de `serie` por los casos ({caso: % sobre lo normal}); los casos se combinan multiplicando."""
    f = 1.0
    for caso, cambio in (casos or {}).items():
        f *= 1 + efecto_aplicado(caso, serie, cambio) / 100.0
    return f


def simular_integral(corte, dias, escenario="historico", ajuste_llegadas=1.0, ajuste_estancia=1.0,
                     ajuste_espera=1.0, n_rep=N_REP, semilla=SEMILLA, modelos=None, casos=None):
    """Simula `dias` dias despues de `corte`. Devuelve (fechas, salidas, info) donde salidas es un dict
    {serie: array (n_rep, dias)} con las 7 series de SERIES_SALIDA e info trae kappa y las siembras.

    kappa calibra el NIVEL de los ingresos emergentes contra el pronostico validado de ingresos a cama del
    mismo horizonte y escenario (opcion B de la conversacion de diseno: los conteos emergen de los agentes,
    no se fuerza una cuota con ranking). ajuste_llegadas escala la demanda completa (llegadas y, via los
    agentes, los ingresos); ajuste_espera solo mueve la cola (la ocupacion no depende de la espera);
    ajuste_estancia es la palanca de camas de siempre (escenario C).

    modelos: claves de MODELOS_A9 marcadas (vacia = sin modelo); cada una entra solo en su serie. casos = {caso: % sobre lo normal},
    solo de los modelos marcados, con el efecto propio medido (EFECTO_CASOS). Sin modelos ni casos, igual que antes."""
    rng = np.random.default_rng(semilla)
    corte = pd.Timestamp(corte)
    modelos = [m for m in (modelos or ()) if m in MODELOS_DISPONIBLES]
    casos = {c: n for c, n in (casos or {}).items() if c in modelos and c in CASOS}      # un caso solo cuenta si su modelo esta marcado
    bases_l = [m for m in modelos if MODELOS_A9[m][1] == "llegadas"]
    bases_i = [m for m in modelos if MODELOS_A9[m][1] == "ingresos"]
    f_lleg = factor_casos(casos, "llegadas")
    f_ing = factor_casos(casos, "ingresos")
    pron_lleg = pronostico_entrenado(serie_llegadas, corte, dias, escenario, bases_l) * ajuste_llegadas * f_lleg
    pron_ing = pronostico_entrenado(scm.serie_ingresos, corte, dias, escenario, bases_i) * ajuste_llegadas * f_ing
    fechas = pron_lleg.index
    lam_lleg = pron_lleg.values
    kappa = float(pron_ing.values.sum() / max(lam_lleg.sum() * P_MEDIA, 1e-9))
    p_eff = np.clip(kappa * P_CAMA_VEC, 0.0, 1.0)

    censo_real = scm.ocup_d["mean"].reindex([corte]).iloc[0]
    if pd.isna(censo_real):
        censo_real = scm.ocup_d["mean"].dropna().iloc[-1]
    n0 = int(round(censo_real))
    cola_real = COLA_REAL_D.reindex([corte]).iloc[0]
    if pd.isna(cola_real):
        cola_real = COLA_REAL_D.dropna().iloc[-1]
    q0 = int(round(cola_real))

    out = {s: np.zeros((n_rep, dias)) for s in SERIES_SALIDA}
    for r in range(n_rep):
        rep = _una_repeticion(lam_lleg, p_eff, rng, ajuste_estancia, ajuste_espera, n0, q0)
        for s in SERIES_SALIDA:
            out[s][r] = rep[s]
    info = {"kappa": kappa, "n0_camas": n0, "q0_cola": q0,
            "ingresos_esperados_dia": float(pron_ing.values.mean()), "llegadas_esperadas_dia": float(lam_lleg.mean()),
            "modelos": modelos, "casos": casos, "factor_llegadas": f_lleg, "factor_ingresos": f_ing}
    return fechas, out, info


def percentiles(salidas, pcts=(10, 50, 90)):
    return {k: {p: np.percentile(v, p, axis=0) for p in pcts} for k, v in salidas.items()}


print(f"motor integrado listo: {len(PERFILES_LLEG)} perfiles de llegada, P(cama) por perfil calibrada con kappa, "
      f"trayectorias conjuntas (hora, espera, estancia) por perfil, cola horaria, siembra de camas y de cola")

# ----------------------------------------------------------------------
# A PARTIR DE AQUI, SOLO AL CORRER EL SCRIPT (igual patron que el motor A5): backtest con puerta de validacion,
# proyeccion de 180 dias y graficos. Importar el modulo (p. ej. dashboard/pages/simulador.py) no paga esto.
# ----------------------------------------------------------------------
if __name__ == "__main__":
    for _d in (TABLAS, GRAFICOS):
        _d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 5) BACKTEST (puerta de validacion): ene a 9-abr-2026, entrenado solo hasta dic-2025
    # ------------------------------------------------------------------
    titulo("5. BACKTEST INTEGRADO: ene a 9-abr-2026 (puerta: no empeorar el backtest del motor A5)")
    dias_bt = (pd.Timestamp("2026-04-09") - pd.Timestamp(BACKTEST_CORTE)).days
    fechas_bt, out_bt, info_bt = simular_integral(BACKTEST_CORTE, dias_bt)
    pct_bt = percentiles(out_bt)
    print(f"kappa de calibracion: {info_bt['kappa']:.3f} | siembras: {info_bt['n0_camas']} en cama, "
          f"{info_bt['q0_cola']} esperando | llegadas esperadas {info_bt['llegadas_esperadas_dia']:.0f}/dia, "
          f"ingresos esperados {info_bt['ingresos_esperados_dia']:.1f}/dia")

    real_ocup = scm.ocup_d["mean"].reindex(fechas_bt)
    real_ing = scm.serie_ingresos.reindex(fechas_bt)
    real_cola = COLA_REAL_D.reindex(fechas_bt)
    real_altas = ALTAS_REAL_D.reindex(fechas_bt)
    real_lleg = serie_llegadas.reindex(fechas_bt)

    def gate(nombre, sim_p, real, p10=None, p90=None):
        v = real.values.astype(float)
        ok = ~np.isnan(v)
        err = sim_p[ok] - v[ok]
        linea = f"{nombre:<22} MAE {np.abs(err).mean():6.2f}   sesgo {err.mean():+6.2f}   real medio {v[ok].mean():7.2f}"
        if p10 is not None:
            cob = ((v[ok] >= p10[ok]) & (v[ok] <= p90[ok])).mean()
            linea += f"   cobertura 10-90: {100 * cob:5.1f} %"
        print(linea)
        return np.abs(err).mean(), err.mean(), (cob if p10 is not None else np.nan)

    print(f"\ndias de backtest: {dias_bt} ({fechas_bt.min().date()} a {fechas_bt.max().date()})")
    mae_oc, sesgo_oc, cob_oc = gate("ocupacion (camas)", pct_bt["total"][50], real_ocup, pct_bt["total"][10], pct_bt["total"][90])
    mae_cl, sesgo_cl, cob_cl = gate("cola de espera", pct_bt["cola"][50], real_cola, pct_bt["cola"][10], pct_bt["cola"][90])
    mae_in, sesgo_in, cob_in = gate("ingresos a cama/dia", pct_bt["ingresos_cama"][50], real_ing, pct_bt["ingresos_cama"][10], pct_bt["ingresos_cama"][90])
    mae_al, sesgo_al, cob_al = gate("altas/dia", pct_bt["altas"][50], real_altas, pct_bt["altas"][10], pct_bt["altas"][90])
    mae_ll, sesgo_ll, cob_ll = gate("llegadas/dia", pct_bt["llegadas"][50], real_lleg, pct_bt["llegadas"][10], pct_bt["llegadas"][90])
    print(f"\nPUERTA (motor A5 documentado: MAE 8,6 camas, sesgo +7,0, cobertura 78,8 %): "
          f"{'CUMPLE' if mae_oc <= 9.6 and 0.70 <= cob_oc else 'NO CUMPLE -> revisar antes de usar'}")
    print("(tolerancia: MAE de ocupacion hasta 1 cama peor que A5 y cobertura dentro de la meta 70-90 %)")

    bt = pd.DataFrame({"fecha": fechas_bt})
    for s, real in [("total", real_ocup), ("cola", real_cola), ("ingresos_cama", real_ing),
                    ("altas", real_altas), ("llegadas", real_lleg)]:
        bt[f"{s}_real"] = real.values
        for p in (10, 50, 90):
            bt[f"{s}_p{p}"] = pct_bt[s][p]
    bt.to_csv(TABLAS / "simint_backtest.csv", index=False)
    print("guardado: resultados/tablas/simint_backtest.csv")

    # ------------------------------------------------------------------
    # 6) PROYECCION INTEGRADA (desde el ultimo dato confiable, 180 dias)
    # ------------------------------------------------------------------
    titulo("6. PROYECCION INTEGRADA: 180 dias desde el ultimo dato confiable")
    fechas_f, out_f, info_f = simular_integral(scm.ULTIMO_CONFIABLE, HORIZONTE_PROYECCION)
    pct_f = percentiles(out_f)
    print(f"desde {scm.ULTIMO_CONFIABLE.date()} | kappa {info_f['kappa']:.3f} | siembra {info_f['n0_camas']} en cama, "
          f"{info_f['q0_cola']} esperando")
    resumen = []
    for s, nombre in [("llegadas", "Llegadas al hospital/dia"), ("ingresos_cama", "Ingresos a cama/dia"),
                      ("altas", "Altas/dia"), ("cola", "Pacientes esperando cama"), ("total", "Camas ocupadas")]:
        m = out_f[s].mean()
        resumen.append({"serie": s, "nombre": nombre, "media": round(float(m), 1),
                        "p10_medio": round(float(pct_f[s][10].mean()), 1), "p90_medio": round(float(pct_f[s][90].mean()), 1)})
    prob_sat = float((out_f["total"] > scm.CAPACIDAD["total"]).mean())
    resumen.append({"serie": "prob_saturacion", "nombre": "% dias-repeticion sobre 106 camas",
                    "media": round(100 * prob_sat, 1), "p10_medio": np.nan, "p90_medio": np.nan})
    tabla_resumen = pd.DataFrame(resumen)
    print(tabla_resumen.to_string(index=False))
    tabla_resumen.to_csv(TABLAS / "simint_resumen.csv", index=False)

    proy = pd.DataFrame({"fecha": fechas_f})
    for s in SERIES_SALIDA:
        for p in (10, 50, 90):
            proy[f"{s}_p{p}"] = pct_f[s][p]
    proy.to_csv(TABLAS / "simint_proyeccion.csv", index=False)
    print("guardado: resultados/tablas/simint_resumen.csv y simint_proyeccion.csv")
    print(f"\n(referencia motor A5 con bootstrap suavizado: ocupacion media 111,1 y 65,4 % de dias-repeticion "
          f"saturados - docs/modelo_camas.md; aqui: {out_f['total'].mean():.1f} y {100 * prob_sat:.1f} %)")

    # ------------------------------------------------------------------
    # 7) Graficos
    # ------------------------------------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\nmatplotlib no esta instalado: se omite el grafico")
    else:
        SUPERFICIE, TINTA, TINTA2, REJILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e5e4df"
        AZUL, NARANJA, AQUA, ROJO = "#2a78d6", "#eb6834", "#1baf7a", "#c0392b"
        fig, axs = plt.subplots(2, 3, figsize=(19, 8.6), facecolor=SUPERFICIE)

        def estilo(ax):
            ax.set_facecolor(SUPERFICIE)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            for s in ("left", "bottom"):
                ax.spines[s].set_color(REJILLA)
            ax.tick_params(colors=TINTA2, labelsize=8)
            ax.grid(axis="y", color=REJILLA, linewidth=.8)
            ax.set_axisbelow(True)
            ax.tick_params(axis="x", rotation=30)

        def panel_bt(ax, serie, real, titulo_p, capacidad=None):
            ax.fill_between(fechas_bt, pct_bt[serie][10], pct_bt[serie][90], color=AZUL, alpha=.18, label="banda 10-90 %")
            ax.plot(fechas_bt, pct_bt[serie][50], color=AZUL, linewidth=1.6, label="mediana simulada")
            ax.plot(fechas_bt, real.values, color=NARANJA, linewidth=1.4, label="real")
            if capacidad:
                ax.axhline(capacidad, color=TINTA, linewidth=1, linestyle=(0, (4, 3)))
            ax.set_title(titulo_p, loc="left", color=TINTA, fontsize=10, fontweight="bold")
            ax.legend(frameon=False, fontsize=7, labelcolor=TINTA2)
            estilo(ax)

        panel_bt(axs[0][0], "total", real_ocup, f"Backtest ocupacion (MAE {mae_oc:.1f}, cobertura {100 * cob_oc:.0f} %)",
                 scm.CAPACIDAD["total"])
        panel_bt(axs[0][1], "cola", real_cola, f"Backtest cola de espera (MAE {mae_cl:.1f}, cobertura {100 * cob_cl:.0f} %)")
        panel_bt(axs[0][2], "ingresos_cama", real_ing, f"Backtest ingresos a cama (MAE {mae_in:.1f})")

        def panel_f(ax, serie, titulo_p, color=AZUL, capacidad=None):
            ax.fill_between(fechas_f, pct_f[serie][10], pct_f[serie][90], color=color, alpha=.18)
            ax.plot(fechas_f, pct_f[serie][50], color=color, linewidth=1.6)
            if capacidad:
                ax.axhline(capacidad, color=TINTA, linewidth=1, linestyle=(0, (4, 3)))
            ax.set_title(titulo_p, loc="left", color=TINTA, fontsize=10, fontweight="bold")
            estilo(ax)

        panel_f(axs[1][0], "total", f"Proyeccion ocupacion ({HORIZONTE_PROYECCION} d, prob. saturar 106: {100 * prob_sat:.0f} %)",
                AZUL, scm.CAPACIDAD["total"])
        panel_f(axs[1][1], "cola", "Proyeccion cola de espera (cota inferior)", ROJO)
        ax = axs[1][2]
        ax.plot(fechas_f, pct_f["ingresos_cama"][50], color=AQUA, linewidth=1.4, label="ingresos a cama")
        ax.plot(fechas_f, pct_f["altas"][50], color=NARANJA, linewidth=1.4, label="altas")
        ax.set_title("Proyeccion flujo diario (medianas)", loc="left", color=TINTA, fontsize=10, fontweight="bold")
        ax.legend(frameon=False, fontsize=7, labelcolor=TINTA2)
        estilo(ax)

        fig.tight_layout(rect=(0, .03, 1, 1))
        fig.text(.01, .01, "Simulador integral (motor de agentes sobre el Monte Carlo A5; 1.000 repeticiones). "
                 "La cola solo cuenta futuros hospitalizados (cota inferior). Asociacion, no causa.",
                 color=TINTA2, fontsize=7.5)
        fig.savefig(GRAFICOS / "simint_resultados.png", dpi=150, facecolor=SUPERFICIE)
        print("\nguardado: resultados/graficos/simint_resultados.png")
