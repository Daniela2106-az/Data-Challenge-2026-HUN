"""
dashboard/pages/paciente.py  -  pagina del dashboard multipagina (10-nov-2026, migrada de dashboard/estimador.py;
rediseno del 14-nov-2026: formulario tipo stepper sin recuadros, chips para las etapas, grafico con iconos de
jornada en vez de etiquetas apiñadas, y ficha tecnica plegable)
Tarea A6: ¿CUANDO RECIBIRA CAMA ESTE PACIENTE?

Se describe al paciente (edad, sexo, tipo de visita, cuantas horas lleva esperando y sus etapas de atencion en
urgencias) y la pagina muestra:
  - la probabilidad de recibir cama en cada bloque del dia (madrugada, mañana, tarde, noche) de hoy, mañana y
    pasado mañana, con un icono por jornada (el icono en la leyenda tambien sirve de filtro: un clic aisla esa
    jornada, doble clic vuelve a mostrar todas -- comportamiento nativo de la leyenda de Plotly);
  - lo que le falta en una linea numerica (p25-p75, con el p90 como "peor caso" en la cola) y la ventana mas
    probable en una tarjeta;
  - un aviso visible junto al boton "Estimar" si el perfil (edad x sexo x tipo) tiene pocos casos historicos;
  - que tan bien funciona el estimador en la prueba (jul-2025 a 9-abr-2026), si las tablas de validacion
    estan disponibles.

CAMBIOS DEL 14-NOV (pedidos por el usuario, con una correccion honesta):
  - Se quito la seccion de "hospitalizacion anterior": la correlacion que aporta (0,34) es debil-moderada y,
    en el uso real, quien atiende a un paciente nuevo rara vez tiene a mano la espera/estancia exacta de su
    hospitalizacion anterior -- se prefirio simplificar el formulario a pedir un dato poco fiable de conseguir.
    El modelo sigue aceptando ese dato internamente (estimador_tiempo_restante.py no cambio), solo que esta
    pagina ya no lo pide.
  - "Tipo de visita" pedia los codigos "ER/TU/HOSP", pero esos son los codigos de las ETAPAS (visit_detail),
    no de "tipo de visita" (visit_concept_id) -- son campos distintos y "HOSP" no corresponde a "Ambulatorio".
    Se usan en su lugar URG/TU/AMB (con su info al pasar el mouse), para no mostrar un dato incorrecto.
  - Se quito la linea de probabilidad acumulada del grafico y, por lo tanto, la tarjeta "Cama en 6/12/24 h"
    (perdia sentido sin esa linea): quedan barras limpias + las tarjetas que ya resumian "para cuando" y
    "peor caso".
Es la misma funcion de consulta de src/estimador_tiempo_restante.py: rango de pacientes parecidos, no una
promesa para una persona. Solo cambian los ids de componentes (prefijo "pac-") para no chocar con las otras
paginas de la misma app.

DATOS  No se conecta a la base. Usa el modelo guardado (fuera del proyecto, se entrena al primer uso, ~1 min)
       y, para la seccion de validacion, las tablas agregadas de src/utilidad_estimador.py (en HUN_TABLAS).
"""
import sys
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, clientside_callback, dcc, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))        # dashboard/ para el tema de graficos
import confianza_perfil as cp  # noqa: E402
import estimador_tiempo_restante as etr  # noqa: E402
import estimador_tiempos as et  # noqa: E402
import tema_graficos as tg  # noqa: E402
from componentes import mensaje, metodo  # noqa: E402

from eleccion_modelos import tarjeta_eleccion  # noqa: E402
from componentes import ETAPAS_Y_PRUEBAS, secciones  # noqa: E402
from widgets_paciente import GRUPOS_DX, LABS_FUERA, TIPOS_INFO, info_badge, stepper, campo_stepper_clientside, tabla_html, tarjeta, rango_widget  # noqa: E402
dash.register_page(__name__, path="/paciente", name="Paciente en espera", title="¿Cuándo recibirá cama? - HUN", order=2)

GRIS, AZUL, NARANJA, VERDE, ROSA = "#6b6b6b", "#2a6fb0", "#eb6834", "#2e9b5b", "#d6336c"
AZUL_PALIDO = "#bcd4ea"


def _mezclar_color(c1, c2, t):
    """Interpola linealmente entre dos colores hex (t=0 -> c1, t=1 -> c2); usado para pintar cada tramo de la
    curva acumulada según su propia probabilidad."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r, g, b = round(r1 + (r2 - r1) * t), round(g1 + (g2 - g1) * t), round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

ICONOS_JORNADA = {"madrugada": "🌙", "mañana": "🌅", "tarde": "☀️", "noche": "🌆"}
RANGO_12H = {"madrugada": "12-7 am", "mañana": "7 am-2 pm", "tarde": "2-7 pm", "noche": "7 pm-12 am"}
ORDEN_JORNADA = ["madrugada", "mañana", "tarde", "noche"]
DIAS_CAP = ["Hoy", "Mañana", "Pasado mañana"]

# ----------------------------------------------------------------------
# Ficha tecnica (para evaluadores): etapas de construccion y comparativo contra las alternativas, con los
# numeros tal como quedan en docs/estimador_tiempos.md (secciones 2, 3, 3.1, 3.2, 7, 7.1; version del 11-nov).
# ----------------------------------------------------------------------
ETAPAS_PIPELINE_A6 = [
    ("1. Preparar los datos", "Para cada hora de espera ya transcurrida (0 a 11 h) se construye una fila por "
     "cada paciente que seguía esperando en ese momento, con todo lo que se sabía hasta ahí -- la técnica se "
     "llama «landmark». Desde las 12 h se usa un solo modelo combinado con el historial."),
    ("2. Un modelo por hora", "12 modelos de árboles de gradiente (HistGradientBoostingClassifier), cada uno "
     "entrenado solo con quienes seguían esperando a esa hora exacta, más un modelo combinado desde las 12 h."),
    ("3. Calibrar el p90", "El nivel 0,90 dejaba por debajo solo al 87-88 % de los casos reales (los peores "
     "casos siguen empeorando). Se subió a 0,93: así el «peor caso» que se muestra cubre de verdad ~91 % de "
     "las veces (sección 7.1)."),
    ("4. Revisar fugas", "Se probó si el recorrido en urgencias es en parte el trámite de hospitalización: "
     "con 2 h de retraso conserva el 43-57 % de su aporte. Se corrigió también una fuga pequeña en la fecha "
     "del diagnóstico previo (sección 7)."),
    ("5. Reentrenar cada mes", "Se probaron 7 formas de entrenar; gana reentrenar cada mes con más peso en lo "
     "reciente (vida media de 6 meses) frente a un modelo fijo, con la diferencia real a las 3, 6 y 24 h "
     "(sección 3.1)."),
    ("6. Probar la utilidad real", "Tres salidas del día a día -- ventana más probable, censo para la reunión "
     "de camas y alerta a las 48 h -- probadas igual que todo lo demás: entrenadas hasta jun-2025, evaluadas "
     "con jul-2025 a 9-abr-2026, datos que el modelo nunca vio (sección 3.2)."),
]

HORAS_MEJORA = ["Al llegar", "3 h", "6 h", "12 h", "24 h", "48 h"]
MEJORA_METODOS = {
    "Tabla de perfiles": [6.4, 7.1, 6.2, 4.1, 2.6, -1.3],
    "Sin historial ni recorrido": [7.0, 8.0, 7.7, 6.7, 4.9, 2.0],
    "+ historial y recorrido": [8.2, 8.9, 8.5, 7.3, 5.4, 2.0],
    "Estimador final (vigente)": [8.6, 10.5, 10.8, 7.7, 6.1, 2.9],
}
COLORES_MEJORA = ["#c9d3dc", "#8aa0b3", "#5b8fc4", AZUL]


def grafico_mejora():
    """Mejora (%) frente al rango general, por metodo y hora de espera -- docs/estimador_tiempos.md seccion 3."""
    fig = go.Figure([
        go.Bar(x=HORAS_MEJORA, y=valores, name=metodo, marker_color=color,
               hovertemplate="%{x}<br>%{y:.1f} %% de mejora<extra></extra>")
        for (metodo, valores), color in zip(MEJORA_METODOS.items(), COLORES_MEJORA)
    ])
    fig.update_layout(title="Mejora frente al rango general, por método y hora de espera", barmode="group",
                      yaxis_title="Mejora (%)", legend=dict(orientation="h", y=-0.25),
                      template="simple_white", margin=dict(l=40, r=20, t=50, b=40))
    return fig


campo_stepper_clientside("pac-edad", 0, 110)
campo_stepper_clientside("pac-horas", 0, 200)

# Selector de "cerradas"/"abiertas": que chip esta activo (recibe el +/-)
clientside_callback(
    """
    function(nCerr, nAbie) {
        var ctx = dash_clientside.callback_context;
        if (!ctx.triggered.length) { return 'abie'; }
        return ctx.triggered[0].prop_id.indexOf('cerr') !== -1 ? 'cerr' : 'abie';
    }
    """,
    Output("pac-etapas-sel", "data"),
    Input("pac-etapas-chip-cerr", "n_clicks"), Input("pac-etapas-chip-abie", "n_clicks"),
)
# +/- compartido: cambia el valor del chip activo (los otros quedan sin cambio)
clientside_callback(
    """
    function(nMenos, nMas, sel, vCerr, vAbie) {
        var ctx = dash_clientside.callback_context;
        if (!ctx.triggered.length) { return [dash_clientside.no_update, dash_clientside.no_update]; }
        var delta = ctx.triggered[0].prop_id.indexOf('menos') !== -1 ? -1 : 1;
        if (sel === 'cerr') { return [Math.max(0, (vCerr || 0) + delta), dash_clientside.no_update]; }
        return [dash_clientside.no_update, Math.max(0, (vAbie || 0) + delta)];
    }
    """,
    Output("pac-n_cerr", "data"), Output("pac-n_abie", "data"),
    Input("pac-etapas-menos", "n_clicks"), Input("pac-etapas-mas", "n_clicks"),
    State("pac-etapas-sel", "data"), State("pac-n_cerr", "data"), State("pac-n_abie", "data"),
)
# Pinta los dos chips (valor + cual esta activo) y el texto "Editando: ..."
clientside_callback(
    """
    function(sel, vCerr, vAbie) {
        var cerrClase = 'chip' + (sel === 'cerr' ? ' is-active' : '');
        var abieClase = 'chip' + (sel === 'abie' ? ' is-active' : '');
        var etiqueta = sel === 'cerr' ? 'Editando: ' : 'Editando: ';
        var detalle = sel === 'cerr' ? 'Cerradas' : 'Abiertas';
        return [String(vCerr == null ? 0 : vCerr), String(vAbie == null ? 1 : vAbie), cerrClase, abieClase, etiqueta, detalle];
    }
    """,
    Output("pac-etapas-cerr-value", "children"), Output("pac-etapas-abie-value", "children"),
    Output("pac-etapas-chip-cerr", "className"), Output("pac-etapas-chip-abie", "className"),
    Output("pac-etapas-label-fijo", "children"), Output("pac-etapas-label-var", "children"),
    Input("pac-etapas-sel", "data"), Input("pac-n_cerr", "data"), Input("pac-n_abie", "data"),
)


def panel_interpretacion():
    """Panel corto para el personal del hospital: que se ve en el grafico, como se calculo, que significa
    cada elemento y que NO dice -- mismo patron y mismo titulo que /pronostico. La parte "Que NO dice" incluye
    los avisos dinamicos (pac-nota), que cambian con cada estimacion."""
    return html.Details(className="metodo metodo--panel", children=[
        html.Summary([html.Span("¿Cómo se interpreta?", className="metodo__titulo"), html.Span("qué ves, cómo se calculó y qué no dice", className="metodo__sub")]),
        html.Div(className="metodo__apilado", children=[
            html.Div([html.Div("Qué estás viendo", className="metodo__rotulo"),
                      html.Div("La probabilidad de recibir cama en cada bloque del día (madrugada, mañana, tarde, "
                               "noche), agrupada por hoy, mañana y pasado mañana.")]),
            html.Div([html.Div("Cómo se calculó", className="metodo__rotulo"),
                      html.Div("Con un modelo entrenado en la historia del hospital que, a partir del paciente y su "
                               "situación actual, calcula qué tan probable es cada ventana (detalle técnico completo "
                               "más abajo, en la ficha técnica).")]),
            html.Div([html.Div("Qué significa cada cosa del gráfico", className="metodo__rotulo"),
                      html.Ul([
                          html.Li("La barra naranja es la ventana con mayor probabilidad de que le entreguen la cama."),
                          html.Li("Cada ícono de la leyenda (🌙🌅☀️🌆) es una jornada del día; haz clic en uno para ver "
                                  "solo esa jornada, doble clic para volver a ver todas."),
                          html.Li("Hoy / Mañana / Pasado mañana agrupan las barras del eje horizontal; las líneas "
                                  "punteadas verticales marcan dónde termina un día y empieza el siguiente."),
                          html.Li("La vista «Normal» solo muestra hoy, mañana y pasado mañana. La probabilidad de "
                                  "recibir cama después del tercer día no se dibuja como barra: junta TODO lo que "
                                  "sigue, sin límite de tiempo, y no es comparable con bloques de 5-7 horas. Puedes "
                                  "verla en la vista «Acumulada» (es el último tramo de la línea) y en la tabla de "
                                  "la ficha técnica."),
                      ], style={"marginTop": "4px"})]),
            html.Div([html.Div("El switch «Normal / Acumulada»", className="metodo__rotulo"),
                      html.Div("Arriba a la derecha del gráfico puedes alternar entre dos formas de ver lo mismo. "
                               "«Normal» (barras) responde «¿en qué momento?». «Acumulada» responde «¿para cuándo ya "
                               "habría cama?»: es la misma información, sumada paso a paso, y por construcción esa línea "
                               "siempre sube — por sí sola solo confirma algo obvio (mientras más se espera, más probable "
                               "es que ya haya cama). Lo que de verdad importa no es que la curva suba, sino dónde se "
                               "empina (abajo se explica cómo leer eso en el color de cada tramo).")]),
            html.Div([html.Div("Qué significa el color de cada tramo", className="metodo__rotulo"),
                      html.Div(style={"height": "10px", "borderRadius": "6px", "margin": "6px 0",
                                     "background": f"linear-gradient(to right, {AZUL_PALIDO}, {NARANJA})"}),
                      html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "11.5px",
                                     "color": GRIS, "marginBottom": "4px"}, children=[
                          html.Span("Poco probable en esa ventana"), html.Span("Muy probable en esa ventana"),
                      ]),
                      html.Div("En la vista Acumulada, cada tramo de la línea toma un color de esta barra según qué "
                               "tan probable es la ventana a la que llega: mientras más azul y delgado, menos aporta "
                               "esa ventana; mientras más naranja y grueso, más aporta. Así se puede comparar la "
                               "pendiente de cualquier tramo con solo mirar el color, no solo la del tramo ganador. "
                               "El tramo que llega a la ventana con mayor probabilidad siempre queda en el extremo "
                               "naranja, con una flecha que dice «mayor probabilidad aquí» — es el mismo bloque del "
                               "día que ya se marca en naranja en la vista Normal.")]),
            html.Div([html.Div("Por qué el salto importa más que el nivel", className="metodo__rotulo"),
                      html.Div("La cama no depende tanto de cuánto lleva esperando el paciente sino de a qué hora del día "
                               "está esperando, porque las altas se concentran entre las 14:00 y las 18:59 (62,7 %, "
                               "docs/CONTEXTO_TECNICO.md 4.8). Dos pacientes con las mismas 10 horas de espera pueden tener probabilidades "
                               "muy distintas en la próxima hora según sean las 3 a.m. o las 3 p.m. Los tramos naranja y "
                               "gruesos de la vista acumulada son justamente esos saltos — la misma información de las "
                               "probabilidades a 6/12/24/48 h que usa el estimador por dentro (ver la tabla de alertas en "
                               "la ficha técnica), mostrada como cambios de pendiente en vez de números sueltos.")]),
            html.Div([html.Div("Qué NO dice", className="metodo__rotulo"),
                      html.Div(id="pac-nota")]),
        ]),
    ])


def panel_tecnico():
    """Ficha tecnica para quien evalua la construccion de la solucion (no la finalidad para el hospital, que
    ya esta en el panel de arriba): como se construyo el estimador paso a paso, su comparativo contra las
    alternativas probadas, las pruebas de utilidad real y los limites. Mismo patron que /pronostico (linea de
    tiempo con hover + grafico + tablas), con los numeros de docs/estimador_tiempos.md."""
    pasos = [html.Div(className="pipeline__step tooltip-trigger", children=[
                html.Div(className="pipeline__dot"), html.Div(titulo, className="pipeline__label"),
                html.Span(detalle, className="tooltip-content")])
             for titulo, detalle in ETAPAS_PIPELINE_A6]
    return html.Details(className="metodo metodo--panel", children=[
        html.Summary([html.Span("Ficha técnica del estimador", className="metodo__titulo"), html.Span("cómo funciona por dentro", className="metodo__sub")]),
        html.Div(className="metodo__apilado", children=[
            html.Div([
                html.Div("Cómo funciona por dentro", className="metodo__rotulo"),
                html.Div("Hay un modelo de árboles de gradiente distinto para cada hora de espera ya transcurrida "
                         "(0 a 11 h; desde las 12 h, uno combinado). Cada uno responde una sola pregunta: «dado que "
                         "el paciente sigue esperando ahora, ¿cuál es la probabilidad de que reciba cama en la "
                         "próxima hora?». Encadenando esas probabilidades hora por hora se construye la curva "
                         "completa de la que salen los percentiles y las ventanas del día. Usa edad, sexo, tipo de "
                         "visita, horas ya esperadas, hora del reloj, día de la semana, ocupación típica de la zona "
                         "y el recorrido en urgencias (etapas cerradas y abiertas).", style={"fontSize": "13px", "lineHeight": "1.6"}),
                html.Div("No pide la hospitalización anterior: su correlación con la espera actual (0,34) es "
                         "débil-moderada y, en el uso real, ese dato rara vez está a la mano al atender a alguien "
                         "nuevo.", style={"fontSize": "12px", "color": GRIS, "marginTop": "4px"}),
            ]),
            html.Div([
                html.Div("La vista «Acumulada» del gráfico", className="metodo__rotulo"),
                html.Div("Es 1 − S(j): la curva de supervivencia S(j) (probabilidad de seguir esperando j horas más, la "
                         "misma que da los percentiles del rango) leída al revés, acumulada por bloque del día en vez de "
                         "por hora. Cada TRAMO (no solo el de mayor probabilidad) está codificado por color y grosor "
                         "según su propia probabilidad individual: interpolación lineal entre azul pálido (t=0, la menor "
                         "probabilidad entre las ventanas) y naranja (t=1, la mayor), con ancho de línea 2 + 5·t px. Así "
                         "la pendiente de CUALQUIER segmento se lee directo del color, no solo la del ganador. El tramo "
                         "más naranja y grueso coincide, por construcción, con la ventana de mayor probabilidad individual "
                         "(la misma marcada en naranja en la vista Normal) y lleva además una anotación con flecha. Esta "
                         "curva es exactamente de donde salían las probabilidades a 6/12/24 h de la tarjeta que se quitó, "
                         "y es la misma lógica de la tabla 3 de abajo (alerta a las 48 h): ambas leen puntos fijos de la "
                         "misma S(j), solo que la tabla lo hace con un corte de probabilidad y el gráfico lo muestra como "
                         "curva completa.", style={"fontSize": "13px", "lineHeight": "1.6"}),
            ]),
            html.Div([
                html.Div("Etapas de construcción (pasa el mouse sobre cada una)", className="metodo__rotulo"),
                html.Div(className="pipeline", children=pasos),
            ]),
            html.Div([
                html.Div("Comparativo contra las alternativas", className="metodo__rotulo"),
                html.Div("Mejora frente a dar el mismo rango a todos (pérdida de cuantiles), probado con 5.430 "
                         "estancias de jul-2025 a 9-abr-2026 que ningún modelo vio.", style={"fontSize": "12px", "color": GRIS, "marginBottom": "4px"}),
                dcc.Graph(figure=grafico_mejora(), config={"displaylogo": False}),
            ]),
            html.Div([
                html.Div("¿Qué tan útil es? Tres pruebas del uso diario", style={"fontWeight": 700, "marginBottom": "2px"}),
                html.Div("Cifras calculadas corriendo src/utilidad_estimador.py en este equipo (modelo entrenado hasta "
                         "jun-2025, probado con 5.430 estancias de jul-2025 a 9-abr-2026 que nunca vio). Detalle del método "
                         "en docs/estimador_tiempos.md, sección 3.2.", style={"fontSize": "12px", "color": GRIS, "marginBottom": "8px"}),
                html.Div("1. Para el paciente: ¿en qué ventana recibirá cama?", style={"fontWeight": 600}),
                tabla_html(["", "Al llegar (n = 5.430)", "A las 6 h (n = 4.013)"], [
                    ["Acierta la ventana más probable", "28,7 % (sin modelo 21,6 %)", "25,8 % (sin modelo 18,6 %)"],
                    ["La real está entre las 2 más probables", "45,7 % (sin modelo 36,9 %)", "43,4 % (sin modelo 34,3 %)"],
                    ["Acierta la ventana exacta con fecha", "26,0 % (sin modelo 21,6 %)", "20,8 % (sin modelo 17,4 %)"],
                    ["Error de probabilidad (Brier, menor mejor)", "0,833 (sin modelo 0,870)", "0,836 (sin modelo 0,875)"],
                    ["Recibe la cama después de 3 días", "14,3 %", "17,3 %"],
                ]),
                html.Div("2. Para la reunión de camas: ¿cuántos de los que esperan tendrán cama en 12-24 h?",
                         style={"fontWeight": 600, "marginTop": "14px"}),
                tabla_html(["Momento y plazo", "En espera", "Reciben cama", "Error/día", "Mínimo por azar", "Rango 80 % acierta"], [
                    ["7:00, en 12 h", "23,6", "5,1", "1,84", "1,85", "88,3 %"],
                    ["7:00, en 24 h", "23,6", "10,5", "2,56", "2,61", "87,6 %"],
                    ["13:00, en 12 h", "28,9", "11,6", "2,62", "2,72", "87,6 %"],
                    ["13:00, en 24 h", "28,9", "12,9", "2,71", "2,89", "87,6 %"],
                ]),
                html.Div("3. Para actuar antes: ¿quién seguirá sin cama a las 48 h? (a las 12 h de espera, AUC 0,68)",
                         style={"fontWeight": 600, "marginTop": "14px"}),
                tabla_html(["Regla", "Alertas/día", "Acierta", "Detecta"], [
                    ["Sin modelo: todos los que llevan 12 h", "11,07", "38,6 %", "100 %"],
                    ["Probabilidad ≥ 20 %", "9,53", "42,6 %", "95,0 %"],
                    ["Probabilidad ≥ 30 %", "6,89", "48,2 %", "77,7 %"],
                    ["Probabilidad ≥ 40 % (recomendada)", "4,13", "54,8 %", "53,0 %"],
                    ["Probabilidad ≥ 50 %", "1,45", "58,8 %", "19,9 %"],
                    ["Probabilidad ≥ 60 %", "0,23", "65,2 %", "3,6 %"],
                    ["Mismas alertas que «24 h», decididas a las 12 h", "8,07", "45,7 %", "86,4 %"],
                    ["Sin modelo: todos los que llevan 24 h (12 h más tarde)", "8,07", "52,9 %", "100 %"],
                ], resaltar_fila=3),
            ]),
            html.Div([
                html.Div("Límites", className="metodo__rotulo"),
                html.Div("La base no registra el triage, el servicio ni el tipo de cama, que es de lo que más "
                         "depende la espera; la «cama» es la asignación administrativa, que puede ser una silla o "
                         "camilla de apoyo; probado con jul-2025 a 9-abr-2026. El techo de precisión es bajo: el "
                         "error de la mediana sigue siendo de unas 24 h al llegar. Detalle completo en "
                         "docs/estimador_tiempos.md.", style={"fontSize": "12.5px", "color": GRIS}),
            ]),
        ]),
    ])


def layout():
    hoy = pd.Timestamp.now(tz="America/Bogota")
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return html.Div(className="page-container", children=[
        html.Div(className="page-head", children=[
            html.H2("¿Cuándo recibirá cama este paciente?"),
            html.P("Describe al paciente y el estimador muestra en qué momento del día es más probable que reciba cama.",
                   className="page-head__sub"),
        ]),
        html.Div(style={"display": "flex", "flexWrap": "wrap", "gap": "32px", "alignItems": "flex-start"}, children=[
            html.Div(className="form-panel", style={"flex": "0 0 320px"}, children=[
                html.Div(f"Hoy, {hoy.day} de {meses[hoy.month - 1]} de {hoy.year}", className="field-group__help", style={"marginBottom": "10px", "fontWeight": 600}),
                html.Div(className="field-group", children=[
                    html.Span("Edad (años)", className="field-group__label"),
                    stepper("pac-edad", 67, 0, 110),
                ]),
                html.Div(className="field-group", children=[
                    html.Span("Sexo", className="field-group__label"),
                    dcc.RadioItems(id="pac-sexo", className="pill-switch pill-switch--icons", value="Mujer", options=[
                        {"value": "Mujer", "label": html.Span(className="pill-icon-option", children=[
                            html.Span("♀", className="gender-icon", style={"color": ROSA, "fontWeight": 700})])},
                        {"value": "Hombre", "label": html.Span(className="pill-icon-option", children=[
                            html.Span("♂", className="gender-icon", style={"color": AZUL, "fontWeight": 700})])},
                    ]),
                ]),
                html.Div(className="field-group", children=[
                    html.Span(["Tipo de visita ", info_badge("Los tres tipos que trae la base. Pasa el mouse sobre cada "
                               "código para ver qué significa.")], className="field-group__label"),
                    dcc.RadioItems(id="pac-tipo", className="pill-switch pill-switch--compact", value="Urgencias", options=[
                        {"value": tv, "label": html.Span(className="pill-icon-option", children=[cod, info_badge(info)])}
                        for tv, (cod, info) in TIPOS_INFO.items()]),
                ]),
                html.Div(className="field-group", children=[
                    html.Span("Horas que lleva esperando", className="field-group__label"),
                    stepper("pac-horas", 0, 0, 200),
                ]),
                html.Div(className="field-group", children=[
                    html.Span("Etapas en urgencias de esta visita", className="field-group__label"),
                    html.Div(className="chip-row", children=[
                        html.Div(id="pac-etapas-chip-cerr", className="chip", n_clicks=0, children=[
                            html.Div(id="pac-etapas-cerr-value", className="chip__value"), html.Div("Cerradas", className="chip__label")]),
                        html.Div(id="pac-etapas-chip-abie", className="chip is-active", n_clicks=0, children=[
                            html.Div(id="pac-etapas-abie-value", className="chip__value"), html.Div("Abiertas", className="chip__label")]),
                    ]),
                    html.Div(className="stepper", style={"marginTop": "8px"}, children=[
                        html.Button("–", id="pac-etapas-menos", n_clicks=0, className="stepper__btn", type="button"),
                        html.Span(id="pac-etapas-label-fijo", style={"minWidth": "90px", "textAlign": "center", "color": GRIS, "fontSize": "12px"}),
                        html.Button("+", id="pac-etapas-mas", n_clicks=0, className="stepper__btn", type="button"),
                    ]),
                    html.Div(id="pac-etapas-label-var", className="chip-editing-label"),
                    dcc.Store(id="pac-n_cerr", data=0), dcc.Store(id="pac-n_abie", data=1), dcc.Store(id="pac-etapas-sel", data="abie"),
                ]),
                html.Details(className="field-group", children=[
                    html.Summary("Laboratorios de las primeras 6 horas (opcional)", className="field-group__label", style={"cursor": "pointer"}),
                    html.Div("Cuentan desde que el paciente lleva 6 horas esperando. Marca solo lo que salió fuera de rango; si no marcas nada, no se usan.", className="field-group__help"),
                    dcc.Checklist(id="pac-labs", options=[{"label": t, "value": k} for k, (_c, _v, t) in LABS_FUERA.items()], value=[],
                                  style={"display": "grid", "gap": "4px", "marginTop": "8px", "fontSize": "13px"}),
                ]),
                html.Div(className="field-group", children=[
                    html.Span("Camas ocupadas ahora en su zona (opcional)", className="field-group__label"),
                    dcc.Input(id="pac-ocup", type="number", min=0, step=1, style={"width": "100%"}),
                    html.Div("Si no lo sabes, se usa la ocupación típica de los últimos meses.", className="field-group__help"),
                ]),
                html.Button("Estimar", id="pac-estimar", n_clicks=0, className="btn-primary", style={"width": "100%", "marginTop": "6px"}),
                html.Div(id="pac-alerta-perfil"),
            ]),
            html.Div(style={"flex": "1 1 600px"}, children=[
                html.Div(className="pac-metrics-row", children=[
                    html.Div(id="pac-lead", className="pac-lead-wrap"),
                    html.Div(id="pac-rango", className="pac-rango-wrap"),
                ]),
                html.Div(style={"display": "flex", "justifyContent": "flex-end", "marginBottom": "12px"}, children=[
                    dcc.RadioItems(id="pac-vista", className="pill-switch", value="normal", options=[
                        {"label": "Normal", "value": "normal"}, {"label": "Acumulada", "value": "acumulada"}]),
                ]),
                dcc.Graph(id="pac-grafico", config={"displaylogo": False}),
                dcc.Store(id="pac-ventanas-datos"),
            ]),
        ]),
        tarjeta_eleccion("/paciente"),
        mensaje("**Es el rango de pacientes parecidos, no una promesa para una persona.** Sirve para responder al paciente y a su familia en qué "
                "momento del día es más probable la cama, para el censo de la reunión de camas (cuántos de los que esperan tendrán cama en 12 o 24 h) "
                "y para avisar a las 12 h quién seguirá sin cama a las 48. Solo aplica a pacientes que ya tienen orden de hospitalización."),
        metodo("Para cada hora de espera, el modelo estima la probabilidad de recibir cama en la hora siguiente según la hora del reloj, el día, la "
               "ocupación, la edad, el sexo, el tipo de visita, el historial del paciente, su recorrido en urgencias y, desde las 6 h, sus "
               "laboratorios. Encadenando esas probabilidades sale el rango completo de lo que falta. Se entrena con las estancias de feb-2023 a "
               "abr-2026 dando más peso a lo reciente, y conviene reentrenarlo cada mes. Probado con 5.430 estancias que no había visto: mejora el "
               "rango cerca de 9 % al llegar y 11 % a las pocas horas frente a darle a todos el mismo rango, y su percentil 90 cubre el 91 %.",
               "No separa la atención clínica de la espera pura por una cama, porque la base no registra la hora de la orden de hospitalización. No "
               "conoce el triage, el servicio ni el tipo de cama, que es de lo que más depende la espera: con esos datos la mejora se duplicaría. La "
               "«cama» es la asignación administrativa, que puede ser una camilla de apoyo. En las primeras horas, parte de la probabilidad refleja "
               "el trámite de registro, no una predicción.",
               "Fuente: src/estimador_tiempo_restante.py (modelo guardado, versión 9) y las tablas de src/utilidad_estimador.py. Detalle: documentación, sección 6.4, y docs/estimador_tiempos.md.", ruta="/paciente",
               antes=secciones(panel_interpretacion(), solo=("Qué estás viendo", "Qué significa cada cosa del gráfico")) + [html.Div([html.Div("Avisos de esta estimación", className="metodo__rotulo"), html.Div(id="pac-nota")])], despues=secciones(panel_tecnico(), solo=ETAPAS_Y_PRUEBAS), pasos=False, modelo=False),
    ])


def etapas_desde_conteos(n_cerradas, n_abiertas, horas):
    """Convierte los conteos en etapas aproximadas: las cerradas repartidas desde la llegada y las abiertas empezando despues."""
    n_cerradas, n_abiertas = int(n_cerradas or 0), int(n_abiertas or 0)
    paso = horas / (n_cerradas + 1) if horas > 0 else 0
    etapas = [(i * paso, (i + 1) * paso) for i in range(n_cerradas)]
    inicio = n_cerradas * paso
    etapas += [(inicio + j * 0.01, None) for j in range(n_abiertas)]
    return etapas


def parse_ventana(v):
    if v == "después":
        return None, None
    dia, resto = v.split(", ", 1)
    return dia, resto.split(" (")[0]


def frase_ventana(v):
    """Convierte la ventana en una frase legible: 'hoy, mañana (7 am-2 pm)' -> 'Hoy en la mañana';
    'pasado mañana, tarde (...)' -> 'Pasado mañana en la tarde'; 'después' -> 'En más de 3 días'."""
    if v == "después":
        return "En más de 3 días"
    dia, jornada = parse_ventana(v)
    return f"{dia.capitalize()} en la {jornada}"


def _secuencia_ventanas(v):
    """Construye, en el orden cronológico real de `v` (garantizado por ventanas_de_cama), la secuencia de
    posiciones numéricas del eje x, el ícono de cada punto, el día de cada punto y los límites/centros de cada
    grupo de día (para dibujar separadores y la etiqueta del día). No usar un eje 'multicategoría' de Plotly
    aquí: cuando un día tiene menos bloques que otro (p. ej. 'hoy' ya pasó la madrugada), Plotly puede reordenar
    las categorías y romper el orden cronológico -- eso fue lo que causaba el zigzag en la vista Acumulada."""
    iconos, dias = [], []
    for ventana in v.ventana:
        if ventana == "después":
            iconos.append("⋯")
            dias.append("Después")
        else:
            dia, jornada = parse_ventana(ventana)
            iconos.append(ICONOS_JORNADA[jornada])
            dias.append(dia.capitalize())
    xs = list(range(len(dias)))
    centros, fronteras = [], []
    inicio = 0
    for i in range(1, len(dias) + 1):
        if i == len(dias) or dias[i] != dias[inicio]:
            etiqueta = dias[inicio]
            if etiqueta == "Después":    # aclara que no es un bloque mas: junta todo lo que sigue despues del dia 3
                etiqueta = "Después (todo lo que sigue)"
            centros.append(((inicio + i - 1) / 2, etiqueta))
            if i < len(dias):
                fronteras.append(i - 0.5)
            inicio = i
    return xs, iconos, dias, centros, fronteras


def construir_grafico_normal(v, ventana_mas_probable, dark):
    """Vista 'Normal': barras limpias por jornada (sin la acumulada) -- responde '¿en qué momento?'.
    Solo muestra hoy / mañana / pasado mañana: la barra 'Después' se quitó (16-nov) porque el modelo no mueve
    esa probabilidad con las horas que el paciente lleva esperando (limitación conocida del estimador) y
    porque junta un rango sin límite de tiempo que no es comparable con bloques de 5-7 h. Esa probabilidad
    sigue visible en la vista Acumulada (su último tramo). El eje y no se fija a [0, 100]: así el gráfico
    llega ya ajustado al tamaño real de las barras, sin que haya que darle clic a 'autoscale' en la barra de
    herramientas de Plotly."""
    v = v[v.ventana != "después"].reset_index(drop=True)
    xs, iconos, dias, centros, fronteras = _secuencia_ventanas(v)
    fig = go.Figure()
    for jornada in ORDEN_JORNADA:
        xj = [x for x, ventana in zip(xs, v.ventana) if ventana != "después" and parse_ventana(ventana)[1] == jornada]
        if not xj:
            continue
        yj = [round(100 * v.probabilidad.iloc[x], 1) for x in xj]
        colores = [NARANJA if v.ventana.iloc[x] == ventana_mas_probable else AZUL for x in xj]
        fig.add_trace(go.Bar(
            x=xj, y=yj, marker_color=colores,
            name=f"{ICONOS_JORNADA[jornada]} {jornada.capitalize()} · {RANGO_12H[jornada]}",
            customdata=[v.ventana.iloc[x] for x in xj],
            hovertemplate="%{customdata}<br>%{y} %%<extra></extra>",
        ))
    for fr in fronteras:
        fig.add_vline(x=fr, line_width=1.3, line_dash="dash", line_color="rgba(120,120,120,.75)")
    for centro, etiqueta in centros:
        fig.add_annotation(x=centro, y=-0.2, yref="paper", text=etiqueta, showarrow=False, font=dict(size=11))
    fig.update_layout(title="¿En qué momento recibirá cama?", yaxis_title="Probabilidad (%)",
                      template="simple_white", legend=dict(orientation="h", y=-0.42), margin=dict(l=40, r=20, t=50, b=95),
                      bargap=0.3, bargroupgap=0.08,
                      xaxis=dict(tickmode="array", tickvals=xs, ticktext=iconos, tickfont=dict(size=15)))
    tg.aplicar(fig, dark)
    return fig


def construir_grafico_acumulada(v, ventana_mas_probable, dark):
    """Vista 'Acumulada': la misma curva de supervivencia, pero resaltando el TRAMO con el salto mas grande
    (que es, por construccion, la misma ventana que ya se marca en naranja en la vista Normal) -- el valor de
    esta vista esta en la pendiente, no en que la linea suba. Eje x numérico (no multicategoría): así el orden
    de los puntos es siempre el cronológico real y la curva no puede zigzaguear. Cada TRAMO (no solo el más
    probable) se colorea y engrosa según su propia probabilidad -- de azul pálido (poco probable) a naranja
    intenso (muy probable) -- para que la pendiente de cualquier segmento se pueda leer de un vistazo, no solo
    la de la ventana ganadora."""
    xs, iconos, dias, centros, fronteras = _secuencia_ventanas(v)
    ys = [round(100 * a, 1) for a in v.acumulada]
    probs = [round(100 * p, 1) for p in v.probabilidad]
    pos_destacada = None
    for i, ventana in enumerate(v.ventana):
        if ventana == ventana_mas_probable:
            pos_destacada = i
    p_min, p_max = min(probs), max(probs)
    rango_p = (p_max - p_min) or 1.0

    def _t(p):
        return (p - p_min) / rango_p

    fig = go.Figure()
    for i in range(len(xs) - 1):
        t = _t(probs[i + 1])    # el tramo i -> i+1 "sube" exactamente lo que vale la probabilidad de la ventana i+1
        fig.add_trace(go.Scatter(
            x=xs[i:i + 2], y=ys[i:i + 2], mode="lines", line=dict(color=_mezclar_color(AZUL_PALIDO, NARANJA, t), width=2 + 5 * t),
            hovertemplate=f"{probs[i + 1]} %% de probabilidad en esta ventana<extra></extra>", showlegend=False))
    tamanos = [15 if i == pos_destacada else 7 for i in range(len(ys))]
    colores_marcador = [NARANJA if i == pos_destacada else AZUL for i in range(len(ys))]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", marker=dict(size=tamanos, color=colores_marcador),
                             customdata=list(v.ventana),
                             hovertemplate="%{customdata}<br>%{y} %% ya tiene cama<extra></extra>", showlegend=False))
    if pos_destacada is not None:
        fig.add_annotation(x=xs[pos_destacada], y=ys[pos_destacada], text="mayor probabilidad aquí",
                           showarrow=True, arrowhead=2, ax=0, ay=-32, font=dict(size=11, color=NARANJA))
    for fr in fronteras:
        fig.add_vline(x=fr, line_width=1.3, line_dash="dash", line_color="rgba(120,120,120,.75)")
    for centro, etiqueta in centros:
        fig.add_annotation(x=centro, y=-0.17, yref="paper", text=etiqueta, showarrow=False, font=dict(size=11))
    fig.add_annotation(x=1, y=1.14, xref="paper", yref="paper", xanchor="right", showarrow=False,
                       text="más naranja y grueso = más probable en esa ventana", font=dict(size=10.5, color=GRIS))
    fig.update_layout(title="Probabilidad acumulada de ya tener cama", yaxis_title="Probabilidad acumulada (%)",
                      yaxis_range=[0, 100], template="simple_white", margin=dict(l=40, r=20, t=60, b=80),
                      xaxis=dict(tickmode="array", tickvals=xs, ticktext=iconos, tickfont=dict(size=15)))
    tg.aplicar(fig, dark)
    return fig


@callback(Output("pac-ventanas-datos", "data"), Output("pac-lead", "children"), Output("pac-rango", "children"),
          Output("pac-nota", "children"), Output("pac-alerta-perfil", "children"),
          Input("pac-estimar", "n_clicks"),
          State("pac-edad", "value"), State("pac-sexo", "value"), State("pac-tipo", "value"), State("pac-horas", "value"),
          State("pac-n_cerr", "data"), State("pac-n_abie", "data"),
          State("pac-labs", "value"), State("pac-ocup", "value"))
def actualizar(_, edad, sexo, tipo, horas, n_cerr, n_abie, labs, ocup):
    try:
        horas = float(horas or 0)
        ahora = pd.Timestamp.now(tz="America/Bogota").strftime("%Y-%m-%d %H:%M")      # la hora actual, en Colombia (el servidor puede estar en otra zona)
        valores_lab = {LABS_FUERA[k][0]: LABS_FUERA[k][1] for k in (labs or []) if k in LABS_FUERA} or None      # sin nada marcado, no se usan los laboratorios
        r = etr.estimar_tiempo_restante(float(edad), sexo, tipo, horas, ahora, ocupacion_zona=float(ocup) if ocup else None,
                                        hospitalizacion_previa=None, diagnostico_previo=None, laboratorios_6h=valores_lab,
                                        etapas_urgencias=etapas_desde_conteos(n_cerr, n_abie, horas), admisiones=[0.0])
    except Exception as err:                                             # datos mal escritos: mostrar el motivo en vez de romper la pagina
        return None, [], [], f"No se pudo estimar: {err}", []
    v = pd.DataFrame(r["ventanas"])
    datos = {"ventanas": r["ventanas"], "ventana_mas_probable": r["ventana_mas_probable"]}

    lead = [tarjeta("Momento más probable", frase_ventana(r["ventana_mas_probable"]),
                    f"{100 * v.probabilidad.max():.0f} % de probabilidad", destacada=True)]
    rango = [rango_widget(r["faltan_p25_h"], r["faltan_p50_h"], r["faltan_p75_h"], r["faltan_p90_h"])]

    perfil = cp.clasificar_perfil(edad, sexo, tipo)
    avisos_html = [html.Li(a) for a in r["avisos"]]
    nota = html.Div([
        html.P(f"Zona: {'niños' if r['zona'] == 'ninos' else 'adultos'}; camas ocupadas usadas: {r['ocupacion_usada']:.0f} ({'la que indicaste' if ocup else 'típico de los últimos meses'}). "
               "Las etapas en urgencias se aproximan a partir de los conteos.", style={"margin": "0 0 4px 0"}),
        html.Ul(avisos_html, style={"margin": 0, "paddingLeft": "18px"}),
    ])
    alerta = []
    if perfil["poco_comun"]:
        alerta = html.Div(className="alert-inline", children=[
            "⚠ Perfil poco común: ", f"edad {perfil['grupo_edad']}, {sexo}, {tipo} tiene solo {perfil['n_estancias']} estancias "
            f"y {perfil['n_episodios_atencion']} episodios atendidos desde feb-2023 en la base. El rango puede ser menos estable "
            "que para un perfil común."])
    return datos, lead, rango, nota, alerta


@callback(Output("pac-grafico", "figure"), Input("pac-ventanas-datos", "data"), Input("pac-vista", "value"), State("theme-store", "data"))
def mostrar_grafico(datos, vista, tema):
    """Separado de actualizar(): cambiar el switch Normal/Acumulada solo redibuja, no vuelve a estimar."""
    if not datos:
        return go.Figure()
    v = pd.DataFrame(datos["ventanas"])
    dark = tg.es_oscuro(tema)
    if vista == "acumulada":
        return construir_grafico_acumulada(v, datos["ventana_mas_probable"], dark)
    return construir_grafico_normal(v, datos["ventana_mas_probable"], dark)
