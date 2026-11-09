"""
estimador_tiempo_restante.py  -  version 4 (9-nov-2026)
(v4: un modelo por cada hora de espera de 0 a 11 h, en vez de 0, 2, 4, 6 y 9 h con el mas cercano por debajo; asi el modelo que se consulta es el mismo
 que se prueba en cada hora (src/revision_estimador.py, prueba 1). Modelo guardado version 7: el .joblib anterior se vuelve a entrenar solo.)
(v3: avisa cuando el modelo esta desactualizado frente a la fecha consultada y cuando se usa la ocupacion tipica en vez de la real; dice a quien aplica
 (pacientes con orden de hospitalizacion); el modelo guardado pasa a la version 6 porque comparar_estimadores.py v3 corrigio el diagnostico previo y la
 zona de la ocupacion, asi que el .joblib anterior se vuelve a entrenar solo.)
Tarea A6: funcion de consulta del estimador final (modelo de tiempo restante). Para un paciente que espera cama, dice cuanto le falta (percentiles 25, 50,
75 y 90), la hora en que la mitad de los pacientes parecidos ya tendria cama y la probabilidad de recibirla en las proximas 6, 12 y 24 horas.

QUE USA (todo se conoce en el momento de la consulta)
  - El paciente: edad, sexo, tipo de visita y cuantas horas lleva esperando.
  - El hospital: hora del reloj, dia de la semana y camas ocupadas en su zona (adultos o ninos).
  - Su historial (opcional): de su ultima hospitalizacion, cuanto espero, cuanto duro y hace cuantos dias termino; cuantas hospitalizaciones previas
    tiene; y el grupo del ultimo diagnostico de una visita anterior. Sin historial, el modelo lo trata como paciente nuevo.
  - Su recorrido en urgencias (opcional): las etapas de atencion de esta visita, en horas desde la llegada (inicio y fin, o fin vacio si sigue abierta),
    y las admisiones. Si no se da, se asume lo mas comun: una etapa de atencion abierta desde la llegada y una admision al llegar.
  Modelo: comparar_estimadores.py (M1, version 2): con menos de 12 h de espera, un modelo por cada hora de espera (LANDMARKS: 0 a 11 h; se usa el de la hora entera ya cumplida) con historial y recorrido; desde las 12 h, un
  modelo con solo el historial (el recorrido ya no suma). Validado con jul-2025 a 9-abr-2026 (docs/estimador_tiempos.md); el modelo que se consulta se entrena
  con TODO el periodo confiable (feb-2023 a 9-abr-2026), con MAS PESO A LO RECIENTE (un dato de hace 6 meses pesa la mitad): el hospital cambio y asi
  estima mejor los meses nuevos (src/ventana_entrenamiento.py). Lo ideal es volver a entrenarlo cada mes con los datos nuevos (borrar el .joblib).

DONDE SE GUARDA EL MODELO
  HUN_PROCESADOS/modelos/m1_tiempo_restante.joblib, fuera del proyecto (sale de datos clinicos). Si no existe, se entrena al primer uso (~2 min); para eso
  hacen falta la tabla de episodios (HUN_PROCESADOS) y visit_detail.csv (HUN_CRUDOS). Son 13 modelos (12 por hora de espera y 1 desde las 12 h); entrenarlos tarda unos 4-5 min.

USO
  from estimador_tiempo_restante import estimar_tiempo_restante
  estimar_tiempo_restante(edad=67, sexo="Mujer", tipo_visita="Urgencias", horas_esperando=10, ahora="2026-03-04 19:00",
                          hospitalizacion_previa={"espera_h": 40, "estancia_h": 120, "dias_desde": 60, "n_previas": 1},
                          diagnostico_previo="Cancer", etapas_urgencias=[(0.1, 2.5), (2.5, None)])
  Desde la terminal (sin historial ni recorrido):  python3 src/estimador_tiempo_restante.py 67 Mujer Urgencias 10 "2026-03-04 19:00"

LIMITES
  Rango de pacientes parecidos, no una promesa para una persona: mejora ~8-10 % frente a dar el mismo rango a todos. La espera depende sobre todo de lo que
  la base no registra (triage, servicio, tipo de cama). La "espera de cama" termina en la asignacion administrativa, que puede ser una silla o camilla.
  A QUIEN APLICA: solo a pacientes que se van a hospitalizar (orden de hospitalizacion ya dada). Se entreno solo con quienes recibieron cama; para un
  paciente cualquiera que llega a urgencias no sirve (solo ~9 % se hospitaliza y eso no se sabe al llegar).
  DESACTUALIZACION: los datos confiables terminan el 9-abr-2026 (CLAUDE.md 4.9) y no se puede reentrenar con meses nuevos mientras el registro siga
  degradado. Si la fecha consultada esta a mas de DIAS_AVISO dias del fin del entrenamiento, el resultado trae un aviso.
  Hay un modelo por cada hora de 0 a 11 h, validado hora por hora en src/revision_estimador.py (la v2 tenia 0, 2, 4, 6 y 9 h y solo se probo en 0, 3 y 6 h).
"""
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402
import estimador_tiempos as et  # noqa: E402

LANDMARKS = list(range(ce.HORAS_RECORRIDO))    # 0 a 11 h, uno por hora; con 12 h o mas se usa el modelo con solo el historial
VIDA_MEDIA_DIAS = 182                          # peso a lo reciente: la mitad cada 6 meses hacia atras
DIAS_AVISO = 60                                # mas de 60 dias entre el fin del entrenamiento y la fecha consultada: el modelo puede estar viejo
VERSION_MODELO = 7
MODELO = Path(os.environ.get("HUN_PROCESADOS", ce.PROC)) / "modelos" / "m1_tiempo_restante.joblib"
_CACHE = {}


def _entrenar_y_guardar():
    d, h, rejilla, estado = ce.preparar()
    modelos = {L: ce.entrenar_landmark(d, rejilla, estado, L, vida_media_dias=VIDA_MEDIA_DIAS) for L in LANDMARKS}   # todo el periodo confiable
    modelos["desde_12h"] = ce.entrenar_m1(d, rejilla, estado, ce.COLS_M1_BASE + ce.HIST, vida_media_dias=VIDA_MEDIA_DIAS)
    fin = rejilla[(rejilla >= np.datetime64(ce.HASTA) - np.timedelta64(90, "D")) & (rejilla < np.datetime64(ce.HASTA))]
    k = np.searchsorted(rejilla, fin)
    paquete = {"modelos": modelos, "ocup_tipica": {z: float(np.median(estado[z]["ocup"][k])) for z in estado}, "grupos_dx": ce.GRUPOS_DX,
               "entrenado_hasta": str((ce.HASTA - pd.Timedelta(days=1)).date()), "vida_media_dias": VIDA_MEDIA_DIAS, "version": VERSION_MODELO}
    MODELO.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(paquete, MODELO)
    return paquete


def _cargar():
    if "m" not in _CACHE:
        paq = joblib.load(MODELO) if MODELO.exists() else None
        _CACHE["m"] = paq if paq is not None and paq.get("version") == VERSION_MODELO else _entrenar_y_guardar()
    return _CACHE["m"]


def estimar_tiempo_restante(edad, sexo, tipo_visita, horas_esperando=0, ahora=None, ocupacion_zona=None,
                            hospitalizacion_previa=None, diagnostico_previo=None, etapas_urgencias=None, admisiones=None):
    """Tiempo que le falta a un paciente para recibir cama.
    sexo: 'Mujer' u 'Hombre'; tipo_visita: 'Urgencias', 'Treatment urgency' o 'Ambulatorio'.
    hospitalizacion_previa: dict con espera_h, estancia_h, dias_desde y n_previas (o None si nunca estuvo hospitalizado).
    diagnostico_previo: grupo de diagnostico de una visita anterior (como en datos/referencia/mapeo_dx.csv), o None.
    etapas_urgencias: lista de (inicio_h, fin_h o None) en horas desde la llegada; admisiones: lista de horas desde la llegada."""
    if sexo not in ("Mujer", "Hombre") or tipo_visita not in et.TIPOS:
        raise ValueError(f"sexo debe ser Mujer u Hombre y tipo_visita uno de {et.TIPOS}")
    if not 0 <= horas_esperando < ce.MAX_H - 1:
        raise ValueError(f"horas_esperando debe estar entre 0 y {ce.MAX_H - 1}")
    paq = _cargar()
    m = paq["modelos"]["desde_12h"] if horas_esperando >= ce.HORAS_RECORRIDO else paq["modelos"][max(L for L in LANDMARKS if L <= horas_esperando)]
    ahora = pd.Timestamp(ahora) if ahora is not None else pd.Timestamp.now().floor("min")
    zona = "ninos" if edad < 15 else "adultos"
    ocup = paq["ocup_tipica"][zona] if ocupacion_zona is None else float(ocupacion_zona)
    grupo = str(pd.cut([edad], [-1, 4, 14, 29, 44, 59, 74, 200], labels=et.EDADES)[0])
    hp = hospitalizacion_previa or {}
    if diagnostico_previo is not None and diagnostico_previo not in paq["grupos_dx"]:
        raise ValueError(f"diagnostico_previo debe ser uno de {paq['grupos_dx']}")
    etapas = [(0.0, None)] if etapas_urgencias is None else etapas_urgencias
    adm = [0.0] if admisiones is None and etapas_urgencias is None else (admisiones or [])

    c = int(np.floor(horas_esperando))
    k = np.arange(c, ce.MAX_H)
    reloj = pd.DatetimeIndex(ahora + pd.to_timedelta(k - horas_esperando, unit="h"))
    s = np.array([a for a, _ in etapas], float)
    e = np.array([np.nan if b is None else b for _, b in etapas], float)
    rec = ce.recorrido_paciente(s, e, np.array(adm, float), np.full(len(k), float(horas_esperando)), k.astype(float))
    X = pd.DataFrame({"transcurrido": k, "hora_reloj": reloj.hour, "dia_semana": reloj.day_of_week, "ocup": ocup,
                      "edad_cod": et.EDADES.index(grupo), "tipo_cod": et.TIPOS.index(tipo_visita), "sexo_cod": int(sexo == "Mujer"),
                      "zona_cod": int(zona == "ninos"),
                      "espera_prev_h": hp.get("espera_h", np.nan), "estancia_prev_h": hp.get("estancia_h", np.nan),
                      "n_hosp_previas": hp.get("n_previas", 1 if hp else 0), "dias_desde_hosp": hp.get("dias_desde", np.nan),
                      "dx_previo_cod": paq["grupos_dx"].index(diagnostico_previo) if diagnostico_previo else np.nan, **rec})[m.cols_]
    p = m.predict_proba(X)[:, 1]
    S = np.concatenate([[1.0], np.cumprod(1 - p)])[None, :]                    # S[j] = P(sigue esperando j horas despues de 'c')
    pct = np.clip(ce.cuantiles_de_supervivencia(S)[0] - (horas_esperando - c), 0, None)
    avisos = ["Rango de pacientes parecidos, no una promesa individual.",
              "Solo para pacientes con orden de hospitalizacion: el modelo se entreno con quienes recibieron cama."]
    atraso = (ahora - pd.Timestamp(paq["entrenado_hasta"])).days
    if atraso > DIAS_AVISO:
        avisos.append(f"Modelo entrenado hasta {paq['entrenado_hasta']} ({atraso} dias antes de la fecha consultada): el hospital pudo cambiar y no hay "
                      "datos confiables nuevos para reentrenarlo (registro degradado desde el 10-abr-2026).")
    if ocupacion_zona is None:
        avisos.append(f"Se uso la ocupacion tipica de ene-abr 2026 ({ocup:.0f} camas, zona {zona}), no la real del momento.")
    return {"zona": zona, "ocupacion_usada": ocup,
            **{f"faltan_p{int(q * 100)}_h": round(float(v), 1) for q, v in zip(ce.Q, pct)},
            "hora_estimada_mediana": (ahora + pd.Timedelta(hours=float(pct[1]))).strftime("%Y-%m-%d %H:%M"),
            **{f"prob_cama_en_{hh}h": round(float(1 - S[0, min(hh, S.shape[1] - 1)]), 3) for hh in (6, 12, 24)},
            "avisos": avisos}


if __name__ == "__main__":
    if len(sys.argv) >= 5:
        e_, s_, t_, h_ = sys.argv[1:5]
        print(estimar_tiempo_restante(float(e_), s_, t_, float(h_), sys.argv[5] if len(sys.argv) > 5 else None))
    else:
        ejemplos = [
            ("Mujer de 67, urgencias, recien llegada 9:00", dict(edad=67, sexo="Mujer", tipo_visita="Urgencias", horas_esperando=0, ahora="2026-03-04 09:00")),
            ("La misma, con hospitalizacion previa larga", dict(edad=67, sexo="Mujer", tipo_visita="Urgencias", horas_esperando=0, ahora="2026-03-04 09:00",
                                                              hospitalizacion_previa={"espera_h": 60, "estancia_h": 200, "dias_desde": 45, "n_previas": 2})),
            ("La misma, 6 h despues, una etapa cerrada y otra abierta", dict(edad=67, sexo="Mujer", tipo_visita="Urgencias", horas_esperando=6,
                                                                            ahora="2026-03-04 15:00", etapas_urgencias=[(0.1, 3.0), (3.0, None)], admisiones=[0.0])),
            ("Niña de 8, urgencias, recien llegada 22:00", dict(edad=8, sexo="Mujer", tipo_visita="Urgencias", horas_esperando=0, ahora="2026-03-04 22:00")),
        ]
        for nombre, kw in ejemplos:
            r = estimar_tiempo_restante(**kw)
            print(nombre, "->", {k: v for k, v in r.items() if k.startswith(("faltan", "prob", "hora"))})
