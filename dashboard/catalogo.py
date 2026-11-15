"""
dashboard/catalogo.py  -  alertas y recomendaciones enlazadas (14-nov-2026)

Lee las dos tablas que unen alertas y recomendaciones y arma los enlaces entre paginas:
  - datos/tablas_dashboard/alertas_tabla.csv          (src/exportar_tabla_alertas.py): A1 a A4 y la senal S1, con lo que se midio.
  - datos/tablas_dashboard/recomendaciones_tabla.csv  (docs/recomendaciones.md): columnas nuevas `alerta_ids` (que alerta dispara la
    recomendacion) y `paginas_respaldo` (que paginas de Resultados la sustentan).
Es la interfaz que otro modulo (por ejemplo un flujo de predicciones en secuencia) puede leer: dada una alerta (alerta_id) devuelve la
recomendacion que le corresponde, y dada una recomendacion, las alertas que la disparan.
No todas las recomendaciones tienen alerta: R1, R2, R6 y R7 no la tienen hoy (son registro, seguimiento mensual, protocolo y revision semanal).
"""
import sys
from pathlib import Path

import dash
import pandas as pd
from dash import dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent))
from componentes import leer  # noqa: E402

NOMBRES_ALERTA = {"A1": "Día congestionado", "A2": "Ocupación alta de mañana", "A3": "Paciente sin cama (48 h)",
                  "A4": "Paciente sin cama, aviso temprano", "S1": "Cola proyectada"}


def alertas():
    """Tabla de alertas (una fila por alerta y momento de aviso) o None si falta el archivo."""
    return leer("alertas_tabla.csv", encoding="utf-8")


def recomendaciones():
    """Tabla de recomendaciones con sus enlaces, ordenada por prioridad, o None si falta."""
    d = leer("recomendaciones_tabla.csv", encoding="utf-8")
    if d is None:
        return None
    for c in ("alerta_ids", "paginas_respaldo"):
        d[c] = d[c].fillna("") if c in d else ""
    return d.sort_values("prioridad")


def _lista(texto):
    return [x for x in str(texto or "").split(";") if x]


def nombre_pagina(ruta):
    """Nombre de una pagina del dashboard a partir de su ruta; si no esta registrada, la propia ruta."""
    for p in dash.page_registry.values():
        if p.get("path") == ruta:
            return p.get("name", ruta)
    return ruta


def enlaces_paginas(cadena):
    """Enlaces (dcc.Link) a las paginas de una cadena `/a;/b`."""
    return [dcc.Link(nombre_pagina(r), href=r, className="enlace-chip") for r in _lista(cadena)]


def enlaces_alertas(cadena):
    """Enlaces a la pagina de alertas, uno por identificador `A1;A3`, con el nombre de la alerta."""
    return [dcc.Link(f"{a} · {NOMBRES_ALERTA.get(a, a)}", href=f"/alertas?alerta={a}", className="enlace-chip enlace-chip--alerta")
            for a in _lista(cadena)]


def fila_enlaces(rotulo, enlaces, vacio):
    """Una linea `rotulo + enlaces`; si no hay enlaces, el texto `vacio` en tono tenue."""
    return html.Div(className="enlaces", children=[
        html.Span(rotulo, className="enlaces__rotulo"),
        *(enlaces if enlaces else [html.Span(vacio, className="enlaces__vacio")])])


def recomendaciones_de(alerta_id):
    """Recomendaciones (prioridad, texto) que dispara una alerta, segun alertas_tabla.csv."""
    a, r = alertas(), recomendaciones()
    if a is None or r is None:
        return []
    ids = set()
    for v in a[a.alerta_id == alerta_id].recomendacion_ids.dropna():
        ids |= {int(x[1:]) for x in _lista(v)}
    return [(int(f.prioridad), f.recomendacion) for f in r.itertuples() if int(f.prioridad) in ids]
