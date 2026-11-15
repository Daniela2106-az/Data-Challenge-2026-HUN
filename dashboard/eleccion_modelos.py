"""
dashboard/eleccion_modelos.py  -  resumen de «como se eligio este modelo» para cada componente de Prediccion (15-nov-2026)

La eleccion de modelos vive en la Documentacion (documento final, seccion 6.8 «Alternativas evaluadas», y la pagina /modelos, que
ahora se abre desde la Documentacion). Cada componente trae aqui su parte: que se eligio, por que y que se descarto, con las mismas
alternativas y cifras del cuadro 6.8 de docs/documento_final.md. Si cambia ese cuadro, actualizar RESUMEN.

USO  en la pagina: `eleccion_modelo("/pronostico")` devuelve un desplegable listo para el diseño de la pagina.
"""
from dash import dcc, html

# ruta -> (que se eligio y por que, [(alternativa, que mostro, que se eligio en su lugar)])
RESUMEN = {
    "/pronostico": (
        "Una regresión de Poisson con el día de la semana, los festivos, Semana Santa, Carnaval y la forma del año, sobre el nivel reciente de pacientes. "
        "Es más preciso e interpretable que las alternativas probadas.",
        [("SARIMAX y otros modelos de series de tiempo", "Mejor en validación, pero peor a 1–7 días y en 2026", "Poisson con la forma del año"),
         ("Quincenas, puentes y deduplicar las llegadas", "Cambios de ±0,15 puntos de error; las réplicas son una proporción estable", "Mantener el modelo más simple")]),
    "/alertas": (
        "Cada alerta usa la regla más simple que funcionó mejor al reproducir los días de 2026: el día congestionado se avisa a mediodía con lo que ya llegó, "
        "la ocupación de mañana suponiendo que será igual que hoy y el paciente sin cama a las 48 horas.",
        [("Proyectar camas a 24 h con altas e ingresos esperados", "Error de 3,7 camas, frente a 3,2 de «lo mismo que ahora»", "La persistencia para la alerta de ocupación y el modelo de flujo para la cola"),
         ("Alerta de espera larga desde la llegada", "Con lo que se sabe al llegar, la discriminación es modesta (AUC 0,60–0,68)", "El estimador que se actualiza hora a hora y la alerta a las 12 o 48 horas")]),
    "/paciente": (
        "Un modelo de supervivencia que se vuelve a calcular cada hora de espera y da probabilidades calibradas: cuando dice 24 %, pasa cerca de ese porcentaje.",
        [("LightGBM, XGBoost y otros 13 enfoques para el estimador", "Todos llegan al mismo nivel", "El modelo de supervivencia, que además da probabilidades calibradas"),
         ("Alerta de espera larga desde la llegada", "Con lo que se sabe al llegar, la discriminación es modesta (AUC 0,60–0,68)", "El estimador que se actualiza hora a hora")]),
    "/camas": (
        "Una simulación Monte Carlo: ingresos pronosticados cada día y estancias reales de pacientes con el mismo perfil. "
        "No se predice la estancia de cada paciente ni se supone una fila por orden de llegada.",
        [("Fila «primero en llegar, primero en cama»", "El orden de llegada casi no predice el orden de asignación (53 % de pares en orden, frente a 50 % por azar)", "Simular la ocupación con estancias reales por perfil"),
         ("Predecir la estancia de cada paciente al ingresar", "Ni con diagnóstico ni con laboratorios se explica la estancia individual (R² de 0 a 0,02)", "Trabajar la estancia en conjunto: simulación y ley de Little")]),
}


def eleccion_modelo(ruta):
    """Desplegable «Cómo se eligió este modelo» de un componente; vacío si la ruta no tiene resumen."""
    if ruta not in RESUMEN:
        return html.Div()
    eligio, alternativas = RESUMEN[ruta]
    filas = [html.Tr([html.Td(a), html.Td(m), html.Td(e)]) for a, m, e in alternativas]
    tabla = html.Div(className="tech-table-wrap", children=[html.Table(className="tech-table", children=[
        html.Thead(html.Tr([html.Th("Alternativa probada"), html.Th("Qué mostró"), html.Th("Qué se eligió en su lugar")])), html.Tbody(filas)])])
    return html.Details(className="metodo metodo--panel", children=[
        html.Summary([html.Span("Cómo se eligió este modelo", className="metodo__titulo"), html.Span("qué se eligió y qué se descartó", className="metodo__sub")]),
        html.Div(className="metodo__apilado", style={"display": "grid"}, children=[
            html.Div([html.Div("Qué se eligió", className="metodo__rotulo"), html.Div(eligio)]),
            html.Div([html.Div("Qué se descartó", className="metodo__rotulo"), tabla]),
            html.Div(dcc.Link("Ver todas las alternativas evaluadas en la Documentación", href="/modelos", className="enlace-chip")),
        ])])
