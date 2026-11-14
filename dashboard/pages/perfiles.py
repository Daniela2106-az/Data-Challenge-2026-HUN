"""
dashboard/pages/perfiles.py  -  pagina del dashboard multipagina (10-nov-2026, migrada de dashboard/perfiles.py standalone)
"Perfiles y picos de demanda": pagina ESTATICA (sin controles ni callbacks) que muestra la tabla de
perfil x carga de src/perfiles_en_picos.py y la lista de dias de alta demanda, con la advertencia de
docs/dias_atipicos.md siempre visible al lado (nunca se presenta como "cuello de botella").

Misma logica que la version standalone (dashboard/perfiles.py, ya retirada); solo cambian los ids de
componentes (prefijo "perf-") para no chocar con las otras paginas de la misma app.

DATOS  resultados/tablas/perfiles_en_picos_llegadas.csv, perfiles_en_picos_ocupacion.csv,
       dias_alta_demanda.csv (de src/perfiles_en_picos.py; correrlo antes si no existen).
"""
import os
import sys
from pathlib import Path

import dash
import pandas as pd
from dash import dash_table, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))        # dashboard/ para las piezas comunes
from componentes import mensaje, metodo  # noqa: E402

dash.register_page(__name__, path="/perfiles", name="Perfiles y picos", title="Perfiles y picos de demanda - HUN", order=4)

GRIS, AZUL, NARANJA = "#6b6b6b", "#2a6fb0", "#eb6834"
RAIZ = Path(__file__).resolve().parent.parent.parent
TABLAS = Path(os.environ.get("HUN_TABLAS", RAIZ / "resultados" / "tablas"))


def tabla_dash(df, id_, columnas):
    cols = [{"name": c.replace("_", " "), "id": c} for c in columnas]
    return dash_table.DataTable(
        id=id_, data=df[columnas].to_dict("records"), columns=cols,
        style_cell={"fontSize": "13px", "padding": "6px", "fontFamily": "system-ui, sans-serif", "textAlign": "center"},
        style_header={"fontWeight": 700, "backgroundColor": "#f2f2f2"},
        style_data_conditional=[
            {"if": {"filter_query": "{espera_contraste} contains 'GRANDE'"}, "backgroundColor": "#fdecdc"},
        ] if "espera_contraste" in columnas else [],
        sort_action="native", page_size=15, style_table={"overflowX": "auto"},
    )


def bloque_carga(titulo, id_, df, n_grande):
    cols = ["grupo_edad", "sexo", "tipo_visita", "espera_mediana_pico_h", "espera_mediana_resto_h",
            "estancia_mediana_pico_h", "estancia_mediana_resto_h", "espera_contraste", "sobrerrepresentado_en_picos"]
    cols = [c for c in cols if c in df.columns]
    return html.Div([
        html.H4(titulo),
        html.P(f"{n_grande} de {len(df)} perfiles con contraste GRANDE en la espera (ver docs/perfiles_en_picos.md "
               "para la lectura completa). Las filas resaltadas son las que sí tienen un contraste grande.",
               style={"color": GRIS, "fontSize": "13px"}),
        tabla_dash(df, id_, cols),
    ], style={"marginBottom": "28px"})


def layout():
    try:
        d_lleg = pd.read_csv(TABLAS / "perfiles_en_picos_llegadas.csv")
        d_ocup = pd.read_csv(TABLAS / "perfiles_en_picos_ocupacion.csv")
        d_dias = pd.read_csv(TABLAS / "dias_alta_demanda.csv")
    except (FileNotFoundError, OSError):
        return html.Div(className="page-container", children=[html.H2("Perfiles y picos de demanda"),
                          html.P("Las tablas no están disponibles. Correr primero: python3 src/perfiles_en_picos.py",
                                 style={"color": NARANJA})])
    n_g_lleg = d_lleg.espera_contraste.str.startswith("GRANDE", na=False).sum()
    n_g_ocup = d_ocup.espera_contraste.str.startswith("GRANDE", na=False).sum()
    return html.Div(className="page-container", children=[
        html.H2("Perfiles y picos de demanda"),
        html.P("¿El mismo perfil de paciente espera o se queda distinto cuando llega en un momento de carga alta? "
               "Tabla histórica, para leer, sin controles interactivos. Detalle y límites en docs/perfiles_en_picos.md.",
               style={"color": GRIS}),
        html.P("Resultado resumido: ni nulo ni generalizado. El efecto se concentra en los perfiles de Urgencias más "
               "comunes (adultos y niños escolares), con 30–70 % más espera en los picos; no cambia quién llega "
               "más seguido ni cuánto se queda en cama.", style={"fontWeight": 600}),

        bloque_carga("Criterio 1: llegadas en las 6 h previas (decil 10 = pico)", "perf-tabla-llegadas", d_lleg, n_g_lleg),
        bloque_carga("Criterio 2: ocupación del hospital al llegar (decil 10 = pico)", "perf-tabla-ocupacion", d_ocup, n_g_ocup),

        html.H4("Días de alta demanda"),
        html.Div([
            html.P(f"⚠ {len(d_dias)} días identificados (llegadas > percentil 90 del mismo día de la semana en "
                   "las 12 semanas anteriores) — 1 de cada 6 días aproximadamente, no es un evento raro.",
                   style={"fontWeight": 600}),
            html.P("docs/dias_atipicos.md ya probó que ningún día tuvo una espera más alta de lo esperado: el "
                   "problema de la espera es crónico y de cola larga, no de días puntuales. Esta lista dice "
                   "únicamente que ese día llegaron más pacientes de lo normal para ese día de la semana — "
                   "NUNCA debe leerse como \"día de cuello de botella\".",
                   style={"color": NARANJA, "border": f"1px solid {NARANJA}", "borderRadius": "6px", "padding": "8px 12px"}),
        ], style={"marginBottom": "10px"}),
        tabla_dash(d_dias.sort_values("fecha", ascending=False), "perf-tabla-dias",
                   ["fecha", "llegadas", "umbral_p90_mismo_dia_semana", "pct_sobre_umbral"]),

        html.P("Asociación, no causa; mismos límites que el resto del proyecto. Periodo confiable: 1-feb-2023 a "
               "9-abr-2026.", style={"fontSize": "11px", "color": GRIS, "marginTop": "16px"}),
        mensaje("**Los picos de llegadas golpean sobre todo a los perfiles más comunes de urgencias** (adultos y niños escolares), que esperan entre "
                "30 y 70 % más cuando llegan en un momento de carga alta; no cambia quién llega ni cuánto se queda en cama. Un día de alta demanda no "
                "es un «día de cuello de botella»: la espera larga es crónica, y por eso las acciones de fondo valen todos los días."),
        metodo("Se cruzan los 42 perfiles de paciente (grupo de edad, sexo y tipo de visita) con el momento de carga en que llegaron, medido de dos "
               "formas: las llegadas de las 6 horas previas o la ocupación del hospital, tomando el 10 % más alto como «pico». Para cada perfil se "
               "compara la espera y la estancia medianas en los picos frente al resto, y la diferencia se clasifica como grande, pequeña o ruido según "
               "el tamaño de los grupos (los de menos de 30 estancias no se muestran).",
               "Asociación, no causa: un perfil que espera más en los picos no necesariamente espera por el pico. Los días de alta demanda son solo "
               "días con más llegadas de lo normal para ese día de la semana (1 de cada 6); ningún día del periodo tuvo una espera fuera de lo esperado.",
               "Fuente: src/perfiles_en_picos.py (tablas agregadas por perfil). Detalle: documentación, sección 5.7, y docs/perfiles_en_picos.md y docs/perfiles_pacientes.md."),
    ])
