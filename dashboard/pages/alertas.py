"""
dashboard/pages/alertas.py  -  pagina «Alertas» (17-nov-2026; pagina 3.2 de docs/estructura_dashboard.md; formato de presentacion de Resultados)
Las alertas del proyecto y lo que se midio de cada una, sin controles: la prueba ya esta hecha, se ve completa. Frase, una grafica por alerta,
cuatro tarjetas resumen, «que significa para el hospital» y la documentacion. Es un resultado (reproduce lo que habrian avisado los datos de
enero a abril de 2026), no una herramienta que el usuario ajuste, asi que vive en Resultados.

DATOS  datos/tablas_dashboard/alertas_tabla.csv (src/exportar_tabla_alertas.py, a partir de resultados/tablas/alertas_*.csv): una fila por
       alerta y momento de aviso, con identificador fijo (A1 a A4; la cola proyectada S1 es una senal, no una alerta). La relacion con las
       recomendaciones sale de datos/tablas_dashboard/recomendaciones_tabla.csv mediante dashboard/catalogo.py.
       /alertas?alerta=A3 sigue abriendo la pagina (el parametro ya no cambia nada).
Prueba: enero al 9-abr-2026 reproduciendo los dias, con los cortes elegidos en jul-dic 2025 (src/alertas.py); no es tiempo real.
"""
import re
import sys
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, html

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from componentes import (AZUL, PIZARRA, TENUE, aviso_datos, cifra, coma, estilo, ficha_de, frase, grafico, lamina, laminas_grupo, mensaje,  # noqa: E402
                         metodo, pagina, portada, secciones, tarjetas)
import catalogo as cat  # noqa: E402
import umbrales_alertas as um  # noqa: E402

dash.register_page(__name__, path="/alertas", name="Alertas", title="Alertas - HUN", order=33)


def _corto(f):
    """Etiqueta corta del momento de aviso para el eje."""
    if f.alerta_id == "A4":
        m = re.search(r"≥ (\d+) %", f.momento)
        return f"Probabilidad ≥ {m.group(1)} %" if m else f.momento
    if f.alerta_id == "A2":
        return "Mañana = hoy" if "persistencia" in f.momento else "Proyección con altas"
    return f.momento


def _filas(tabla, tipo):
    return tabla[tabla.alerta_id == tipo].sort_values("orden")


def _rec(tabla, tipo):
    f = _filas(tabla, tipo)
    r = f[f.recomendada == 1]
    return (r if len(r) else f).iloc[0]


def layout(alerta=None, **_):
    tabla = cat.alertas()
    if tabla is None:
        return pagina(aviso_datos("Alertas", ["alertas_tabla.csv"]))
    a1, a2, a3, a4 = (_rec(tabla, t) for t in ("A1", "A2", "A3", "A4"))
    total = tabla[(tabla.recomendada == 1) & tabla.alerta_id.isin(["A1", "A2", "A3"])].alertas_por_dia.sum()
    return pagina(
        portada("Riesgo · Alertas", "Las alertas avisan a tiempo y cada una apunta a la recomendación que dispara",
                "Se probó reproduciendo, día por día, los primeros meses de 2026: qué habría avisado cada alerta, cuántas veces acertó y cuántas fueron falsas alarmas.",
                [cifra(f"{a1.deteccion_pct:.0f} %", "de los días congestionados se detecta a las 12 h (13 de 15)"),
                 cifra(f"{a3.alertas_por_dia:.0f} por día", "pacientes cumplen 48 horas sin cama; la mitad terminará esperando más de 72"),
                 cifra(coma(total, 1), "alertas por día en total con el diseño recomendado")]),
        frase(f"Con las tres alertas recomendadas (día congestionado a las 12 h, ocupación alta de mañana y paciente a las 48 h sin cama) el hospital recibiría unas "
              f"{coma(total, 1)} alertas por día."),
        laminas_grupo(
            lamina(1, f"Día congestionado: a las 12 h detecta {a1.deteccion_pct:.0f} % de los casos y acierta {a1.precision_pct:.0f} % de los avisos",
                   "Un día es congestionado cuando llegan más pacientes de lo habitual para ese día de la semana. **La barra azul es los casos que avisa; la gris, los avisos que acertaron.** "
                   "Avisar con más tiempo sube la detección y baja la precisión.",
                   grafico("ale-A1", alto=300), dato=(coma(a1.auc, 2), "AUC a las 12 h: qué tan bien separa los días congestionados (0,5 es azar)"), ancla="alerta-A1"),
            lamina(2, "Ocupación alta de mañana: suponer que será igual que hoy funciona mejor que proyectar altas e ingresos",
                   "Avisa cuando la ocupación de camas al mediodía está entre el 20 % más alto (107 a 109 camas). **La opción recomendada (la más simple) detecta "
                   f"{a2.deteccion_pct:.0f} % y acierta {a2.precision_pct:.0f} %**, con menos avisos por día.",
                   grafico("ale-A2", alto=280), dato=("3,2 camas", "error de «mañana igual que hoy», frente a 3,7 de proyectar"), invertida=True, ancla="alerta-A2"),
            lamina(3, f"Paciente sin cama a las 48 h: {a3.alertas_por_dia:.0f} avisos por día, y {a3.precision_pct:.0f} % termina esperando más de 72 h",
                   "Avisa de un paciente que lleva las horas elegidas desde su llegada sin cama. **Avisar antes da más alertas y menos precisión; avisar después deja menos margen.** "
                   "Cuenta solo a quienes luego se hospitalizan, así que la carga real es mayor.",
                   grafico("ale-A3", alto=300), dato=(f"{a3.margen_h:.0f} h", "de margen para actuar antes de que cumpla 72 horas"), ancla="alerta-A3"),
            lamina(4, "A las 12 h el estimador avisa quién seguirá sin cama a las 48 h",
                   "Para pacientes con orden de hospitalización: el estimador calcula la probabilidad de seguir sin cama a las 48 h. **Con el corte de 40 % se avisa a unos "
                   f"{coma(a4.alertas_por_dia, 0)} pacientes por día, con 36 horas de margen.** Solo sirve a quienes ya tienen la orden.",
                   grafico("ale-A4", alto=280), dato=(f"{a4.precision_pct:.0f} %", "de los avisados termina esperando más de 72 h"), invertida=True, ancla="alerta-A4"),
            lamina(5, "La cola de pacientes sin cama se pronostica con un tercio menos de error",
                   "Una señal para la reunión de camas, no una alerta con umbral: cuántos pacientes estarán esperando cama dentro de unas horas. "
                   "**En azul, el error del modelo; en gris, el de suponer «lo mismo que ahora».**",
                   grafico("ale-S1", alto=280), dato=("−33 %", "de error a 6 horas frente a «lo mismo que ahora»"), ancla="alerta-S1"),
        ),
        tarjetas("Las alertas probadas con datos de 2026", "Cuándo salta cada una, qué tan bien acierta y qué recomendación dispara",
                 ("A1", "Día congestionado", f"A las 12 h, si las llegadas del día pasan el percentil 90 de su día de la semana. Detecta {a1.deteccion_pct:.0f} % y acierta {a1.precision_pct:.0f} %. Dispara las recomendaciones 3 y 4."),
                 ("A2", "Ocupación alta de mañana", f"Si la ocupación al mediodía está entre el 20 % más alto (107 a 109 camas), suponiendo que mañana será igual que hoy. Detecta {a2.deteccion_pct:.0f} % y acierta {a2.precision_pct:.0f} %. Recomendaciones 3 y 4."),
                 ("A3", "Paciente con 48 h sin cama", f"Cuando un paciente cumple 48 horas desde su llegada sin cama (unos {a3.alertas_por_dia:.0f} por día). {a3.precision_pct:.0f} % termina esperando más de 72 h; hay {a3.margen_h:.0f} h de margen. Recomendación 5."),
                 ("A4", "Aviso temprano con el estimador", f"A las 12 h de espera, si la probabilidad de seguir sin cama a las 48 h es de 40 % o más (unos {a4.alertas_por_dia:.0f} por día, {a4.precision_pct:.0f} % acierta, {a4.margen_h:.0f} h de margen). Recomendación 5."),
                 ("S1", "Cola proyectada", "Una señal para la reunión de camas, no una alerta con umbral: cuántos pacientes esperarán cama en 6, 12 o 24 horas. Recomendación 3.")),
        tarjetas("Las alertas del simulador integral", "Son las únicas que saltan en el simulador; las tres últimas miran a los pacientes uno por uno. Hay dos gravedades, aviso (amarillo) y crítico (rojo); las dos frenan la simulación, y una alerta salta cuando aparece; si se dejó sin corregir no vuelve a frenar la simulación, sino que queda marcada como activa en su fila comprimida, y vuelve a saltar si reaparece después de aplicarle la mejora o si se agrava de aviso a crítico. Los umbrales son criterios del simulador, no resultados validados como los de A1 a A4",
                 ("Sim 1", "Faltarán camas", f"Se necesitarán más de las 106 camas. Dice cuándo (probabilidad de superarlas a 48 h) y cuántas faltan (camas ocupadas en la mediana de las repeticiones menos 106). Aviso (media) desde {um.UMBRAL_ALERTA_MEDIA} % o desde {um.UMBRAL_FALTAN} cama que falta; crítico (alta) desde {um.UMBRAL_ALERTA} % o desde {um.UMBRAL_FALTAN_CRITICO} camas que faltan. Recomendaciones 3, 4 y 7."),
                 ("Sim 2", "Cola de espera larga", f"Pacientes esperando cama a la vez. Aviso desde {um.UMBRAL_COLA}; crítico desde {um.UMBRAL_COLA_CRITICA} (el percentil 90 real). Recomendaciones 5 y 6."),
                 ("Sim 3", "Estancias más largas de lo normal", f"Pacientes en cama que ya llevan más días que 9 de cada 10 pacientes de su misma edad y tipo de visita (estancias reales 2023–2026). Ve también a los que aún no cumplen 14 días. Aviso desde {um.UMBRAL_SOBRE_PERFIL} pacientes; crítico desde {um.UMBRAL_SOBRE_PERFIL_CRITICO} (lo habitual son ~{um.NORMAL_SOBRE_PERFIL}). Recomendación 7."),
                 ("Sim 4", "Esperas de más de 3 días", f"Pacientes que llevan 72 h o más sin cama: los peores casos, que la cola total no muestra. Aviso desde {um.UMBRAL_ESPERA_EXTREMA}; crítico desde {um.UMBRAL_ESPERA_EXTREMA_CRITICO} (lo habitual son ~{um.NORMAL_ESPERA_EXTREMA}). Recomendaciones 5 y 6."),
                 ("Sim 5", "Ingresos con riesgo de estancia larga", f"Porcentaje de los ingresos de la última semana que son mayores de 60 o «treatment urgency», perfiles con 2 a 3 veces más riesgo de pasar de 14 días: avisa antes de que se llenen las camas. Aviso desde {um.UMBRAL_INGRESOS_RIESGO} %; crítico desde {um.UMBRAL_INGRESOS_RIESGO_CRITICO} % (lo habitual es ~{um.NORMAL_INGRESOS_RIESGO} %). Recomendación 7.")),
        tarjetas("Lo esencial de las alertas", "Cuatro cifras de la prueba de enero a abril de 2026",
                 (coma(total, 1), "Alertas por día", "Con el diseño recomendado; casi todas son de pacientes que llevan 48 horas sin cama."),
                 (f"{a1.deteccion_pct:.0f} %", "Días congestionados que detecta", f"A las 12 h, con {a1.precision_pct:.0f} % de acierto. Es la alerta con más señal."),
                 (f"{a3.alertas_por_dia:.0f} por día", "Pacientes a las 48 h sin cama", f"{a3.precision_pct:.0f} % termina esperando más de 72 h; hay 24 horas de margen."),
                 ("15", "Días congestionados en la prueba", "Son pocos: los porcentajes pueden moverse. No se probó en tiempo real.")),
        mensaje(f"Con las tres alertas del diseño recomendado el hospital recibiría **unas {coma(total, 1)} alertas por día**, casi todas de pacientes que llevan 48 horas "
                "sin cama: una lista corta y accionable, no una alarma constante. Qué hacer cuando suena cada una está en la página de Recomendaciones."),
        metodo(
            "Prueba de enero al 9 de abril de 2026 reproduciendo cada día con lo que se sabía en ese momento; los cortes se eligieron con "
            "julio a diciembre de 2025. Día congestionado: llegadas por encima del percentil 90 del mismo día de la semana en las últimas "
            "12 semanas. Ocupación alta: por encima del percentil 80 de las 12 h.",
            "No se probaron en tiempo real. En la prueba solo hubo **15 días congestionados**, así que los porcentajes pueden moverse. La "
            "alerta de paciente sin cama solo cuenta a quienes después se hospitalizan: la carga real es mayor. La alerta por zona (niños y adultos "
            "por separado) no se probó. Una alerta no dice qué hacer: eso lo decide el hospital.",
            "Fuente: src/alertas.py · documentación, sección 6.2.", ruta="/alertas",
            despues=secciones(ficha_de("/alertas"), solo=("Etapas", "Qué se probó")), modelo=False),
    )


def _agrupadas(tabla, tipo, tema, etiq_a="Casos que avisa (detección)", etiq_b="Avisos que aciertan (precisión)"):
    """Detección y precisión por momento de aviso; el momento recomendado, en tono pleno."""
    f = _filas(tabla, tipo)
    x = [_corto(r) + (" ✓" if r.recomendada else "") for r in f.itertuples()]
    opac = [1.0 if r.recomendada else 0.45 for r in f.itertuples()]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=f.deteccion_pct, name=etiq_a, marker_color=AZUL, marker_opacity=opac, text=[f"{d:.0f} %" for d in f.deteccion_pct],
                         textposition="outside", cliponaxis=False, hovertemplate="%{x}: detecta el %{y} % de los casos<extra></extra>"))
    fig.add_trace(go.Bar(x=x, y=f.precision_pct, name=etiq_b, marker_color=PIZARRA, marker_opacity=opac, text=[f"{p:.0f} %" for p in f.precision_pct],
                         textposition="outside", cliponaxis=False, hovertemplate="%{x}: acierta el %{y} % de los avisos<extra></extra>"))
    estilo(fig, tema, leyenda=True).update_yaxes(ticksuffix=" %", range=[0, 112])
    fig.update_layout(barmode="group", bargap=0.34, bargroupgap=0.08)
    return fig


@callback(Output("ale-A1", "figure"), Output("ale-A2", "figure"), Output("ale-A3", "figure"), Output("ale-A4", "figure"), Output("ale-S1", "figure"),
          Input("theme-store", "data"))
def figuras(tema):
    tabla = cat.alertas()
    if tabla is None:
        return [go.Figure()] * 5
    a1 = _agrupadas(tabla, "A1", tema)
    a2 = _agrupadas(tabla, "A2", tema)
    a4 = _agrupadas(tabla, "A4", tema, "Casos que avisa (detección)", "Avisos que aciertan (precisión)")

    f = _filas(tabla, "A3")
    x = [f"{r.momento.replace(' sin cama', '')}<br>{coma(r.alertas_por_dia, 1)} avisos por día" for r in f.itertuples()]
    a3 = go.Figure(go.Bar(x=x, y=f.precision_pct, marker_color=[AZUL if r.recomendada else TENUE for r in f.itertuples()], text=[f"{p:.0f} %" for p in f.precision_pct],
                          textposition="outside", cliponaxis=False, hovertemplate="%{y} % de los avisos termina esperando más de 72 horas<extra></extra>"))
    estilo(a3, tema).update_yaxes(ticksuffix=" %", range=[0, 95], title_text="termina esperando más de 72 h")
    a3.update_layout(margin=dict(l=64, b=58), bargap=0.4)

    s = _filas(tabla, "S1")
    modelo, base = [], []
    for r in s.itertuples():
        m = re.search(r"Error de ([\d,]+) pacientes frente a ([\d,]+)", r.medida)
        modelo.append(float(m.group(1).replace(",", ".")) if m else None)
        base.append(float(m.group(2).replace(",", ".")) if m else None)
    xs = [r.momento + (" ✓" if r.recomendada else "") for r in s.itertuples()]
    s1 = go.Figure()
    s1.add_trace(go.Bar(x=xs, y=modelo, name="Error del modelo", marker_color=AZUL, text=[coma(v, 1) for v in modelo], textposition="outside", cliponaxis=False,
                        hovertemplate="%{x}: error de %{y} pacientes<extra></extra>"))
    s1.add_trace(go.Bar(x=xs, y=base, name="Error de «lo mismo que ahora»", marker_color=PIZARRA, text=[coma(v, 1) for v in base], textposition="outside", cliponaxis=False,
                        hovertemplate="%{x}: error de %{y} pacientes<extra></extra>"))
    estilo(s1, tema, leyenda=True).update_yaxes(rangemode="tozero", title_text="pacientes de error", range=[0, max(base) * 1.25])
    s1.update_layout(barmode="group", bargap=0.34, bargroupgap=0.08, margin_l=64)
    return a1, a2, a3, a4, s1
