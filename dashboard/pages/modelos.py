"""
dashboard/pages/modelos.py  -  pagina «Cómo se eligieron los modelos» (13-nov-2026; pagina 3.6 de docs/estructura_dashboard.md; formato de presentacion)
Para cada pregunta del hospital: que modelo se eligio, por que y que se descarto.

DATOS  Tabla ya publicada al inicio de la seccion 6 de docs/documento_final.md, escrita aqui como constante. No lee ninguna tabla.
"""
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import AZUL, PIZARRA, bloque, cifra, coma, estilo, grafico, hecho, lamina, leer, ficha_de, interpretacion_de, mensaje, metodo, pagina, portada  # noqa: E402

dash.register_page(__name__, path="/modelos", name="Elección de modelos", title="Cómo se eligieron los modelos - HUN", order=36)

# (pregunta, modelo elegido, por que, lo que se descarto)
MODELOS = [
    ("¿Cuántos pacientes llegan y cuántos van a cama cada día?",
     "Regresión de Poisson con día de la semana, festivos, Carnaval, nivel reciente y forma del año",
     "Son conteos y cada efecto se lee como un porcentaje. Error de 7,9 % a 1–7 días.",
     "SARIMAX y otros modelos de series (peores a corto plazo), quincenas, lluvia y calendario escolar."),
    ("¿Hoy será un día congestionado?",
     "Clasificador logístico sobre lo que ya llegó hasta las 12 h, mezclado con el pronóstico",
     "Simple y acierta: detecta el 87 % de los días congestionados a media jornada.",
     "La alerta un día antes: solo detecta 1 de cada 5."),
    ("¿Cuándo recibirá cama este paciente?",
     "Supervivencia hora a hora con árboles de gradiente",
     "Da la distribución completa del tiempo que falta y se actualiza con lo que va pasando.",
     "La fila «primero en llegar» (el orden no se cumple), cuantiles al llegar y un modelo de cola."),
    ("¿Qué perfiles esperan más y por qué?",
     "Regresión logística y regresión sobre el logaritmo de la espera",
     "Los coeficientes se leen con su intervalo. Explica; no reemplaza al estimador.",
     "Alertar por riesgo al llegar: marcaría al 44 % de los pacientes, con 4 de cada 10 falsas alarmas."),
    ("¿Se van a saturar las camas?",
     "Simulación Monte Carlo con estancias reales por perfil sobre los ingresos pronosticados",
     "Respeta la cola larga de las estancias y da la probabilidad de superar las 106 camas.",
     "Predecir la estancia de cada paciente (no se puede) y proyectar con las altas esperadas."),
    ("¿Cuántos pacientes estarán esperando cama en 6 a 12 horas?",
     "Modelo de flujo: entradas y salidas de la cola",
     "Un tercio menos de error que suponer que todo sigue igual.",
     "Suponer que la cola no cambia y usar la tasa típica."),
    ("¿Qué días fueron atípicos?",
     "La distancia de cada día frente al pronóstico del modelo de demanda (más de 3 desviaciones)",
     "Con el calendario ya modelado, lo que sobra no se explica por festivos ni por el día de la semana: solo 3 de los 14 días de llegadas tienen causa de calendario.",
     "Una regla por rango intercuartil (IQR): marcaba demasiados casos por la asimetría de los datos."),
]

VALIDACION = [
    ("Hasta jun 2025", "Entrenamiento", "Con estos meses aprende cada modelo. Nunca se mezclan con los de después."),
    ("Jul a dic 2025", "Validación", "Aquí se eligió cada variable y cada corte: lo que no mejoró en estos meses se descartó."),
    ("Ene a abr 2026", "Prueba", "Meses que el modelo nunca vio. Solo se reportan: no se usaron para decidir nada."),
    ("Regla simple", "Referencia", "Cada modelo se compara con la opción más sencilla; si no la supera, no se usa."),
]
HORIZONTES = {"1-7": "1–7 días", "8-30": "8–30 días", "31-91": "1–3 meses", "92-182": "3–6 meses", "183-365": "6–12 meses"}
SERIES = [("llegadas_con_atencion", "Llegadas con atención", AZUL), ("ingresos_a_cama", "Ingresos a cama", PIZARRA)]


def _parte(titulo, texto):
    return html.Div(className="rec-block", children=[html.Div(titulo, className="rec-block__label"), html.P(texto)])


def _tarjeta(numero, pregunta, modelo, por_que, descartado):
    return html.Div(className="hecho modelo", children=[
        html.Div(f"{numero:02d}", className="lamina__num"), html.Div(pregunta, className="modelo__pregunta"),
        _parte("Modelo elegido", modelo), _parte("Por qué", por_que), _parte("Se probó y se descartó", descartado)])


def layout():
    return pagina(
        portada("Documentación · Elección de modelos", "Para cada pregunta, el modelo más simple que acertó en datos que no había visto",
                "Ningún modelo se eligió por ser sofisticado. Cada uno se comparó con una referencia sencilla y solo se quedó si la superaba "
                "en meses que nunca vio.",
                [cifra("7", "preguntas del hospital, cada una con su modelo"), cifra("7,9 %", "de error al pronosticar las llegadas a una semana"),
                 cifra("87 %", "de los días congestionados se detecta a mediodía")]),
        bloque("Una pregunta, un modelo", "Qué se eligió, por qué y qué alternativas se descartaron"),
        html.Div(className="hechos hechos--2", children=[_tarjeta(i, *m) for i, m in enumerate(MODELOS, 1)]),
        lamina(1, "El pronóstico falla cerca de 8 % a una semana y 10 % a un año",
               "Error diario del pronóstico según qué tan lejos se mira, para las dos series. **Los ingresos a cama son más "
               "difíciles**: son unos 20 por día y el azar pesa más, así que su error no puede bajar mucho de 18 %.",
               grafico("mod-error", alto=320), dato=("8 %", "de error en las llegadas a una semana"))
        if leer("estacionalidad_error.csv") is not None else None,
        bloque("Cómo se validó cada uno", "Siempre con el pasado para entrenar y con meses posteriores para comprobar"),
        html.Div(className="hechos", children=[hecho(*v) for v in VALIDACION]),
        mensaje("Todos los modelos se probaron **entrenando con el pasado y evaluando en meses que no habían visto**, siempre contra una "
                "referencia simple. Donde un modelo complejo no ganó, se dejó el simple, que el hospital puede leer y mantener."),
        interpretacion_de("/modelos"),
        metodo(
            "Validación temporal: se entrena hasta una fecha y se evalúa después, nunca al azar. Las variables se eligieron con julio a "
            "diciembre de 2025 y se confirmaron en 2026. El periodo de evaluación termina el 9 de abril de 2026.",
            "Que un modelo acierte en el pasado no garantiza que acierte si cambia el hospital o el registro. Ninguno anticipa brotes ni "
            "cortes del sistema, y casi todos describen **asociaciones**, no causas.",
            "Fuente: docs/documento_final.md, sección 6 · src/modelo_pronostico.py · src/alertas.py · docs/estimador_tiempos.md · "
            "docs/modelo_camas.md.", ruta="/modelos"),
        ficha_de("/modelos"),
    )


@callback(Output("mod-error", "figure"), Input("theme-store", "data"))
def error(tema):
    e = leer("estacionalidad_error.csv")
    fig = go.Figure()
    if e is not None:
        for clave, nombre, color in SERIES:
            d = e[e.objetivo == clave].sort_values("orden")
            fig.add_trace(go.Bar(x=[HORIZONTES.get(t, t) for t in d.tramo_dias], y=d.wape_con, name=nombre, marker_color=color,
                                 text=[f"{coma(v, 0)} %" for v in d.wape_con], textposition="outside", cliponaxis=False,
                                 hovertemplate=nombre + ", %{x}: %{y:.1f} % de error<extra></extra>"))
    estilo(fig, tema, leyenda=True).update_yaxes(ticksuffix=" %", range=[0, 24])
    fig.update_layout(barmode="group", bargap=0.34, bargroupgap=0.06)
    return fig
