"""
estimador_tiempo_restante.py  -  version 1 (7-nov-2026)
Tarea A6: funcion de consulta del modelo ganador (M1, tiempo restante). Para un paciente que espera cama, dice cuanto le falta (percentiles 25, 50, 75 y 90),
a que hora es mas probable que la reciba y la probabilidad de recibirla en las proximas 6, 12 y 24 horas.

COMO FUNCIONA
  El modelo (comparar_estimadores.py, M1 sin la cola) estima, hora por hora, la probabilidad de recibir cama en la hora siguiente segun cuanto lleva
  esperando el paciente (la "hora estimada" es la llegada a la mediana: la mitad de los pacientes parecidos ya tendria cama), la hora del reloj, el dia de la semana, la ocupacion de su zona, la edad, el sexo y el tipo de visita. Multiplicando hora por hora sale
  la probabilidad de seguir esperando y de ahi los percentiles. Validado con jul-2025 a 9-abr-2026 (docs/estimador_tiempos.md); el modelo que se consulta
  se entrena con TODO el periodo confiable (feb-2023 a 9-abr-2026).

DONDE SE GUARDA EL MODELO
  En HUN_PROCESADOS/modelos/m1_tiempo_restante.joblib (fuera del proyecto: el modelo sale de datos clinicos). Si no existe, se entrena al primer uso (~20 s).

USO
  from estimador_tiempo_restante import estimar_tiempo_restante
  estimar_tiempo_restante(edad=67, sexo="Mujer", tipo_visita="Urgencias", horas_esperando=10, ahora="2026-03-04 09:00")
  Desde la terminal:  python3 src/estimador_tiempo_restante.py 67 Mujer Urgencias 10 "2026-03-04 09:00"
  La ocupacion de la zona (camas ocupadas ahora) es opcional; si no se da, se usa la mediana de los ultimos 90 dias de datos confiables.

LIMITES
  Rango de pacientes parecidos, no una promesa para una persona. Mejora ~7 % frente a dar el mismo rango a todos: la espera depende sobre todo de lo que la base
  no registra (triage, servicio, tipo de cama). La "espera de cama" termina en la asignacion administrativa, que puede ser una silla o camilla de apoyo.
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

MODELO = Path(os.environ.get("HUN_PROCESADOS", ce.PROC)) / "modelos" / "m1_tiempo_restante.joblib"
_CACHE = {}


def _entrenar_y_guardar():
    d, h, rejilla, estado = ce.preparar()
    m = ce.entrenar_m1(d, rejilla, estado, ce.COLS_M1_FINAL)                    # todo el periodo confiable
    fin = rejilla[(rejilla >= np.datetime64(ce.HASTA) - np.timedelta64(90, "D")) & (rejilla < np.datetime64(ce.HASTA))]
    k = np.searchsorted(rejilla, fin)
    ocup_tipica = {z: float(np.median(estado[z]["ocup"][k])) for z in estado}
    MODELO.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": m, "ocup_tipica": ocup_tipica, "entrenado_hasta": str(ce.HASTA.date())}, MODELO)
    return _CACHE.setdefault("m", joblib.load(MODELO))


def _cargar():
    if "m" not in _CACHE:
        _CACHE["m"] = joblib.load(MODELO) if MODELO.exists() else _entrenar_y_guardar()
    return _CACHE["m"]


def estimar_tiempo_restante(edad, sexo, tipo_visita, horas_esperando=0, ahora=None, ocupacion_zona=None):
    """Tiempo que le falta a un paciente para recibir cama. sexo: 'Mujer' u 'Hombre'; tipo_visita: 'Urgencias', 'Treatment urgency' o 'Ambulatorio'."""
    if sexo not in ("Mujer", "Hombre") or tipo_visita not in et.TIPOS:
        raise ValueError(f"sexo debe ser Mujer u Hombre y tipo_visita uno de {et.TIPOS}")
    if not 0 <= horas_esperando < ce.MAX_H - 1:
        raise ValueError(f"horas_esperando debe estar entre 0 y {ce.MAX_H - 1}")
    paq = _cargar()
    m = paq["modelo"]
    ahora = pd.Timestamp(ahora) if ahora is not None else pd.Timestamp.now().floor("min")
    zona = "ninos" if edad < 15 else "adultos"
    ocup = paq["ocup_tipica"][zona] if ocupacion_zona is None else float(ocupacion_zona)
    grupo = pd.cut([edad], [-1, 4, 14, 29, 44, 59, 74, 200], labels=et.EDADES)[0]
    c = int(np.floor(horas_esperando))
    k = np.arange(c, ce.MAX_H)
    reloj = pd.DatetimeIndex(ahora + pd.to_timedelta(k - horas_esperando, unit="h"))
    X = pd.DataFrame({"transcurrido": k, "hora_reloj": reloj.hour, "dia_semana": reloj.dayofweek, "ocup": ocup,
                      "edad_cod": et.EDADES.index(str(grupo)), "tipo_cod": et.TIPOS.index(tipo_visita), "sexo_cod": int(sexo == "Mujer"),
                      "zona_cod": int(zona == "ninos")})[m.cols_]
    p = m.predict_proba(X)[:, 1]
    S = np.concatenate([[1.0], np.cumprod(1 - p)])[None, :]                    # S[j] = P(sigue esperando j horas despues de 'c')
    pct = ce.cuantiles_de_supervivencia(S)[0] - (horas_esperando - c)
    pct = np.clip(pct, 0, None)
    prob = {f"prob_cama_en_{hh}h": round(float(1 - S[0, min(hh, S.shape[1] - 1)]), 3) for hh in (6, 12, 24)}
    return {"zona": zona, "ocupacion_usada": ocup,
            **{f"faltan_p{int(q * 100)}_h": round(float(v), 1) for q, v in zip(ce.Q, pct)},
            "hora_estimada_mediana": (ahora + pd.Timedelta(hours=float(pct[1]))).strftime("%Y-%m-%d %H:%M"),
            **prob,
            "aviso": "Rango de pacientes parecidos, no una promesa individual (mejora ~7 % frente al rango general)."}


if __name__ == "__main__":
    if len(sys.argv) >= 5:
        e, s, t, hs = sys.argv[1:5]
        print(estimar_tiempo_restante(float(e), s, t, float(hs), sys.argv[5] if len(sys.argv) > 5 else None))
    else:
        for ej in [(67, "Mujer", "Urgencias", 0, "2026-03-04 09:00"), (67, "Mujer", "Urgencias", 10, "2026-03-04 19:00"),
                   (35, "Hombre", "Urgencias", 2, "2026-03-04 16:00"), (8, "Mujer", "Urgencias", 0, "2026-03-04 22:00")]:
            print(ej, "->", estimar_tiempo_restante(*ej))
