"""
estimador_estancia_restante.py  -  version 1 (19-nov-2026)
Tarea A6b: funcion de consulta del estimador de la ESTANCIA restante (modelo de landmarks por hora en
cama, src/comparar_estimadores_estancia.py). Para un paciente que YA tiene cama asignada, dice cuanto
le falta para el alta (percentiles 25, 50, 75 y 90), la fecha en que la mitad de los pacientes
parecidos ya habria salido y la probabilidad de salir en los proximos 1, 3 y 7 dias.

Espeja estimador_tiempo_restante.py (el estimador de la ESPERA de cama, ya validado, ~8-10 % de mejora
frente al rango general). La diferencia de fondo: aqui el "reloj" es la hora ya transcurrida DESDE LA
ASIGNACION DE CAMA (horas_en_cama), no desde la llegada a urgencias; y el modelo NO usa el diagnostico
de la estancia actual (fuga, ver cabecera de comparar_estimadores_estancia.py) ni el recorrido en
urgencias (pertenece al tramo urgencias->cama, no a la estancia).

QUE USA (todo se conoce en el momento de la consulta)
  - El paciente: edad, sexo, tipo de visita y cuantas horas lleva en cama.
  - El hospital: hora del reloj, dia de la semana y camas ocupadas en su zona (adultos o ninos).
  - Su historial (opcional): de su ultima hospitalizacion, cuanto espero, cuanto duro y hace cuantos
    dias termino; cuantas hospitalizaciones previas tiene; y el grupo del ultimo diagnostico de una
    visita ANTERIOR (nunca el de esta estancia).
  - Sus laboratorios del ingreso (opcional, primeras 6 h de la visita, FASE 1 -- estaticos, ver
    cabecera de comparar_estimadores_estancia.py): los mismos que estimador_tiempo_restante.py.

DONDE SE GUARDA EL MODELO
  HUN_PROCESADOS/modelos/m1_estancia_restante.joblib, fuera del proyecto. Si no existe, se entrena al
  primer uso (unos 6-7 min: 8 landmarks + 1 modelo agrupado desde las 240 h); para eso hace falta la
  tabla de episodios (HUN_PROCESADOS) y los CSV de laboratorio de las primeras 6 h (HUN_CRUDOS,
  opcionales: sin ellos el modelo entrena igual, sin esa variable).

USO
  from estimador_estancia_restante import estimar_estancia_restante
  estimar_estancia_restante(edad=67, sexo="Mujer", tipo_visita="Urgencias", horas_en_cama=30,
                             ahora="2026-03-04 19:00", hospitalizacion_previa={"espera_h": 40, "estancia_h": 120, "dias_desde": 60, "n_previas": 1})

LIMITES
  Rango de pacientes parecidos, no una promesa para una persona: los dos intentos anteriores de
  predecir la estancia de un paciente (prueba del 21-oct, R2≈0; src/factores_estancia.py, R2=7,9-
  10,8 %) ya mostraron que lo que se sabe al ingresar explica poco de la estancia; la ganancia real de
  este modelo (perdida de cuantiles vs. el rango por perfil de que_esperar.py) se mide en
  src/comparar_estimadores_estancia.py y se declara en la pagina del dashboard -- puede ser modesta,
  y se publica igual, con esos limites explicitos.
  A QUIEN APLICA: solo a pacientes YA hospitalizados (con cama asignada). No usa el diagnostico de
  esta estancia (fuga) ni el recorrido en urgencias de esta visita.
  DESACTUALIZACION: igual aviso que el modelo de espera si la fecha consultada esta muy lejos del fin
  del entrenamiento.
"""
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_estimadores as ce  # noqa: E402
import comparar_estimadores_estancia as cee  # noqa: E402
import estimador_tiempos as et  # noqa: E402

VIDA_MEDIA_DIAS = 182                          # igual peso a lo reciente que el modelo de espera (mitad cada 6 meses); sin calibrar aparte todavia
LIMITE_ENTRENAMIENTO = None                    # None = todo el periodo confiable (a diferencia del modelo de espera, las fechas de cama
                                                # (ini_hosp_est/fin_hosp_est) no tienen la caida de registro de las etapas TU que obligo a
                                                # recortar ese modelo antes de abril-2026; ver prueba de coherencia entre landmarks, 19-nov)
DIAS_AVISO = 60
NIVEL_P90 = 0.90                               # estandar, sin calibrar todavia (a diferencia del modelo de espera, que si tiene un nivel calibrado)
VERSION_MODELO = 1
MODELO = Path(os.environ.get("HUN_PROCESADOS", ce.PROC)) / "modelos" / "m1_estancia_restante.joblib"
_CACHE = {}


def _entrenar_y_guardar():
    d, h, rejilla, estado = cee.preparar()
    paquete = cee.entrenar_paquete_estancia(d, rejilla, estado, hasta=LIMITE_ENTRENAMIENTO, vida_media_dias=VIDA_MEDIA_DIAS)
    paquete["version"] = VERSION_MODELO
    MODELO.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(paquete, MODELO)
    return paquete


def _cargar():
    if "m" not in _CACHE:
        paq = joblib.load(MODELO) if MODELO.exists() else None
        _CACHE["m"] = paq if paq is not None and paq.get("version") == VERSION_MODELO else _entrenar_y_guardar()
    return _CACHE["m"]


DIAS_VENTANA = 10


def ventanas_de_alta(S, c, horas_en_cama, ahora, dias=DIAS_VENTANA):
    """Probabilidad de recibir el alta en cada dia (1 a 'dias', desde ahora) y despues. A diferencia de
    ventanas_de_cama() del modelo de espera (bloques de 4 franjas por dia): la estancia opera a escala de
    dias, no de horas (mediana ~70 h frente a ~18,6 h de espera), asi que bloques de 4 franjas dejarian casi
    toda la probabilidad en 'despues'. S[j] = P(sigue en cama j horas despues de 'c')."""
    ahora = pd.Timestamp(ahora)
    horas = c + np.arange(len(S))
    sigue = lambda t: float(np.interp(t, horas, S, left=1.0, right=S[-1]))
    out, t_fin = [], horas_en_cama
    for dia in range(1, dias + 1):
        ini, fin = ahora + pd.Timedelta(hours=24 * (dia - 1)), ahora + pd.Timedelta(hours=24 * dia)
        t_a = horas_en_cama + (ini - ahora).total_seconds() / 3600
        t_fin = horas_en_cama + (fin - ahora).total_seconds() / 3600
        out.append({"ventana": f"día {dia}", "desde": ini.strftime("%Y-%m-%d %H:%M"), "hasta": fin.strftime("%Y-%m-%d %H:%M"),
                    "probabilidad": round(sigue(t_a) - sigue(t_fin), 3), "acumulada": round(1 - sigue(t_fin), 3)})
    out.append({"ventana": f"más de {dias} días", "desde": (ahora + pd.Timedelta(hours=24 * dias)).strftime("%Y-%m-%d %H:%M"), "hasta": None,
                "probabilidad": round(sigue(t_fin), 3), "acumulada": 1.0})
    return out


def estimar_estancia_restante(edad, sexo, tipo_visita, horas_en_cama=0, ahora=None, ocupacion_zona=None,
                              hospitalizacion_previa=None, diagnostico_previo=None, laboratorios_ingreso=None):
    """Tiempo que le falta a un paciente YA hospitalizado para recibir el alta.
    sexo: 'Mujer' u 'Hombre'; tipo_visita: 'Urgencias', 'Treatment urgency' o 'Ambulatorio'.
    hospitalizacion_previa: dict con espera_h, estancia_h, dias_desde y n_previas (o None si nunca estuvo hospitalizado antes).
    diagnostico_previo: grupo de diagnostico de una visita ANTERIOR (como en datos/referencia/mapeo_dx.csv), o None. NUNCA el de esta estancia.
    laboratorios_ingreso: dict con los valores de las primeras 6 h de la visita (igual formato que estimador_tiempo_restante.py), o None."""
    if sexo not in ("Mujer", "Hombre") or tipo_visita not in et.TIPOS:
        raise ValueError(f"sexo debe ser Mujer u Hombre y tipo_visita uno de {et.TIPOS}")
    if not 0 <= horas_en_cama < cee.MAX_H_ESTANCIA - 1:
        raise ValueError(f"horas_en_cama debe estar entre 0 y {cee.MAX_H_ESTANCIA - 1}")
    paq = _cargar()
    m = cee.modelo_para_estancia(paq, horas_en_cama)
    ahora = pd.Timestamp(ahora) if ahora is not None else pd.Timestamp.now().floor("min")
    zona = "ninos" if edad < 15 else "adultos"
    ocup = paq["ocup_tipica"][zona] if ocupacion_zona is None else float(ocupacion_zona)
    grupo = str(pd.cut([edad], [-1, 4, 14, 29, 44, 59, 74, 200], labels=et.EDADES)[0])
    hp = hospitalizacion_previa or {}
    if diagnostico_previo is not None and diagnostico_previo not in paq["grupos_dx"]:
        raise ValueError(f"diagnostico_previo debe ser uno de {paq['grupos_dx']}")
    banderas = ({c: 0.0 for c in ce.LAB} if not laboratorios_ingreso else
                {**ce.banderas_desde_valores(pd.DataFrame([laboratorios_ingreso])).iloc[0].to_dict(), "con_laboratorio_6h": 1.0})
    c = int(np.floor(horas_en_cama))
    k = np.arange(c, cee.MAX_H_ESTANCIA)
    reloj = pd.DatetimeIndex(ahora + pd.to_timedelta(k - horas_en_cama, unit="h"))
    X = pd.DataFrame({"transcurrido": k, "hora_reloj": reloj.hour, "dia_semana": reloj.day_of_week, "ocup": ocup,
                      "edad_cod": et.EDADES.index(grupo), "tipo_cod": et.TIPOS.index(tipo_visita), "sexo_cod": int(sexo == "Mujer"),
                      "zona_cod": int(zona == "ninos"),
                      "espera_prev_h": hp.get("espera_h", np.nan), "estancia_prev_h": hp.get("estancia_h", np.nan),
                      "n_hosp_previas": hp.get("n_previas", 1 if hp else 0), "dias_desde_hosp": hp.get("dias_desde", np.nan),
                      "dx_previo_cod": paq["grupos_dx"].index(diagnostico_previo) if diagnostico_previo else np.nan,
                      **{c2: float(v) for c2, v in banderas.items()}})[m.cols_]
    p = m.predict_proba(X)[:, 1]
    S = np.concatenate([[1.0], np.cumprod(1 - p)])[None, :]            # S[j] = P(sigue en cama j horas despues de 'c')
    pct = ce.cuantiles_de_supervivencia(S)[0]
    pct[3] = ce.cuantiles_de_supervivencia(S, niveles=[NIVEL_P90])[0, 0]
    pct = np.clip(pct - (horas_en_cama - c), 0, None)
    ventanas = ventanas_de_alta(S[0], c, horas_en_cama, ahora)
    avisos = ["Rango de pacientes parecidos, no una promesa individual.",
              "No usa el diagnóstico de esta estancia (se registra tarde, la mayoría después de la mitad de la estancia); solo el de una hospitalización anterior, si la hubo.",
              "Solo para pacientes ya hospitalizados (con cama asignada)."]
    atraso = (ahora - pd.Timestamp(paq["entrenado_hasta"])).days
    if atraso > DIAS_AVISO:
        avisos.append(f"Modelo entrenado hasta {paq['entrenado_hasta']} ({atraso} dias antes de la fecha consultada): el hospital pudo cambiar.")
    if ocupacion_zona is None:
        avisos.append(f"Se usó la ocupación típica ({ocup:.0f} camas, zona {zona}), no la real del momento.")
    return {"zona": zona, "ocupacion_usada": ocup,
            **{f"faltan_p{int(q * 100)}_h": round(float(v), 1) for q, v in zip(ce.Q, pct)},
            "hora_estimada_alta_mediana": (ahora + pd.Timedelta(hours=float(pct[1]))).strftime("%Y-%m-%d %H:%M"),
            **{f"prob_alta_en_{d_}d": round(float(1 - S[0, min(d_ * 24, S.shape[1] - 1)]), 3) for d_ in (1, 3, 7)},
            "ventanas": ventanas,
            "ventana_mas_probable": max(ventanas[:-1], key=lambda v: v["probabilidad"])["ventana"],
            "avisos": avisos}


if __name__ == "__main__":
    if len(sys.argv) >= 5:
        e_, s_, t_, h_ = sys.argv[1:5]
        print(estimar_estancia_restante(float(e_), s_, t_, float(h_), sys.argv[5] if len(sys.argv) > 5 else None))
    else:
        ejemplos = [
            ("Mujer de 67, urgencias, recien asignada la cama", dict(edad=67, sexo="Mujer", tipo_visita="Urgencias", horas_en_cama=0, ahora="2026-03-04 09:00")),
            ("La misma, 48 h despues en cama", dict(edad=67, sexo="Mujer", tipo_visita="Urgencias", horas_en_cama=48, ahora="2026-03-06 09:00")),
            ("La misma, con hospitalizacion previa larga", dict(edad=67, sexo="Mujer", tipo_visita="Urgencias", horas_en_cama=0, ahora="2026-03-04 09:00",
                                                              hospitalizacion_previa={"espera_h": 60, "estancia_h": 200, "dias_desde": 45, "n_previas": 2})),
            ("Niña de 8, urgencias, recien asignada la cama", dict(edad=8, sexo="Mujer", tipo_visita="Urgencias", horas_en_cama=0, ahora="2026-03-04 22:00")),
        ]
        for nombre, kw in ejemplos:
            r = estimar_estancia_restante(**kw)
            print(nombre, "->", {k: v for k, v in r.items() if k.startswith(("faltan", "prob", "hora"))})
