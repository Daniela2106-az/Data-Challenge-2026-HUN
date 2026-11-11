"""
Ampliacion del 10-nov-2026 sobre la tarea A6: aviso de perfil raro en el calculador (dashboard/estimador.py).

POR QUE  Al correr el mismo paciente en las 12 horas-landmark seguidas (0 a 11 h de espera), un perfil comun
         (30 anios, mujer, Urgencias) da un rango que se mueve con ruido moderado; un perfil raro (78 anios,
         hombre, Treatment urgency) da saltos irregulares (p. ej. el p90 sube 46 h de una hora-landmark a la
         siguiente). Cada hora-landmark es un modelo entrenado por separado (ver docs/estimador_tiempos.md,
         seccion 2): si el perfil tiene pocos casos historicos, cada uno de esos 12 modelos ve pocos ejemplos
         de esa celda y el rango que devuelve puede ser menos estable. Este modulo no corrige el modelo -- solo
         avisa cuando el perfil consultado cae en una celda chica, para que el calculador no muestre ese rango
         con la misma confianza visual que uno de un perfil comun.

QUE HACE  Cuenta, en el mismo periodo confiable y con la misma agrupacion y los mismos minimos que la tarea A1
          (src/perfiles_pacientes.py: MIN_EPISODIOS=100 episodios con atencion, MIN_ESTANCIAS=30 estancias
          unicas hospitalizadas), cuantos casos hay en la celda (grupo_edad x sexo x tipo_visita) del paciente
          consultado. Los cortes de edad son los mismos que usa estimador_tiempo_restante.py internamente.

DATOS  datos/procesados/tabla_episodios.parquet (o HUN_PROCESADOS si esta definido). No usa la base.
"""
import os
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = Path(os.environ.get("HUN_PROCESADOS", RAIZ / "datos" / "procesados"))
EDADES = ["0-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+"]
MIN_EPISODIOS, MIN_ESTANCIAS = 100, 30                 # mismos umbrales que A1
DESDE, HASTA = "2023-02-01", "2026-04-10"              # mismo periodo confiable que A1

_tam = None


def _cargar():
    global _tam
    if _tam is None:
        t = pd.read_parquet(PROC / "tabla_episodios.parquet",
                             columns=["ini", "grupo_edad", "sexo", "tipo_visita", "ruta", "hospitalizado", "estancia_unica"])
        t = t[(t.ini >= DESDE) & (t.ini < HASTA) & t.grupo_edad.notna() & t.sexo.isin(["Mujer", "Hombre"])
              & t.tipo_visita.isin(["Urgencias", "Treatment urgency", "Ambulatorio"])].copy()
        t["con_atencion"] = t.ruta != "ER"
        t["estancia"] = t.hospitalizado & t.estancia_unica
        _tam = (t.groupby(["grupo_edad", "sexo", "tipo_visita"], observed=True)
                 .agg(n_episodios_atencion=("con_atencion", "sum"), n_estancias=("estancia", "sum"))
                 .reset_index())
    return _tam


def clasificar_perfil(edad, sexo, tipo_visita):
    """Tamanio de la celda (grupo_edad x sexo x tipo_visita) del paciente en el periodo confiable, y si llega a
    los minimos de A1 para considerarse un perfil con datos suficientes (`poco_comun=False`)."""
    tam = _cargar()
    grupo = str(pd.cut([float(edad)], [-1, 4, 14, 29, 44, 59, 74, 200], labels=EDADES)[0])
    fila = tam[(tam.grupo_edad == grupo) & (tam.sexo == sexo) & (tam.tipo_visita == tipo_visita)]
    n_at = int(fila.n_episodios_atencion.iloc[0]) if len(fila) else 0
    n_est = int(fila.n_estancias.iloc[0]) if len(fila) else 0
    return {"grupo_edad": grupo, "n_episodios_atencion": n_at, "n_estancias": n_est,
            "poco_comun": n_at < MIN_EPISODIOS or n_est < MIN_ESTANCIAS}


if __name__ == "__main__":
    for edad, sexo, tipo in [(78, "Hombre", "Treatment urgency"), (30, "Mujer", "Urgencias"), (2, "Mujer", "Ambulatorio")]:
        print(edad, sexo, tipo, "->", clasificar_perfil(edad, sexo, tipo))
