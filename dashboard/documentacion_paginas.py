"""
dashboard/documentacion_paginas.py  -  documentacion propia de cada pagina de Resultados y Prediccion (14-nov-2026)
Lo que sale en el panel «Documentación de esta sección» de cada pagina (componentes.metodo): el detalle del metodo, y en las
paginas de Prediccion la eleccion del modelo (que se probo y por que se eligio este). Es el resumen de docs/documento_final.md
para el hospital; el documento completo esta en /documentacion.

RELACION conecta cada resultado con la prediccion que lo usa (y al reves): un resultado dice QUE PASA; la prediccion dice QUE SE ESPERA.
"""

# ruta -> rutas con las que se conecta (resultado <-> prediccion). La relacion inversa se calcula sola.
RELACION = {
    "/demanda": ["/pronostico", "/atipicos"],
    "/estacionalidad": ["/pronostico"],
    "/ocupacion": ["/camas"],
    "/espera": ["/paciente", "/atipicos"],
    "/comparar": ["/camas"],
    "/altas": ["/camas"],
    "/factores": ["/paciente"],
    "/estancia": ["/camas", "/paciente-cama"],
    "/diagnosticos": ["/paciente"],
    "/perfiles": ["/paciente"],
    "/alertas": ["/pronostico", "/paciente", "/simulador"],
    "/datos": ["/demanda", "/ocupacion"],
    "/resumen": ["/espera", "/recomendaciones"],
    "/periodo": ["/comparar"],
}
MOTIVO = {  # (resultado, prediccion) -> por que se conectan
    ("/demanda", "/pronostico"): "las llegadas por hora y día son lo que el pronóstico proyecta",
    ("/demanda", "/atipicos"): "un día atípico es el que se aparta del pronóstico de llegadas",
    ("/estacionalidad", "/pronostico"): "la forma del año es una entrada del pronóstico",
    ("/ocupacion", "/camas"): "la ocupación observada es el punto de partida de la simulación",
    ("/espera", "/paciente"): "la espera de cada paciente se estima con la historia de la espera",
    ("/espera", "/atipicos"): "ningún día tuvo una espera fuera de lo esperado: el problema es crónico",
    ("/comparar", "/camas"): "el diagnóstico repetible se completa con la simulación de camas",
    ("/altas", "/camas"): "el escenario de adelantar altas se simula en la planeación de camas",
    ("/factores", "/paciente"): "los factores de la espera son entradas del estimador",
    ("/estancia", "/camas"): "la estancia larga es lo que más sube la ocupación",
    ("/estancia", "/paciente-cama"): "la estancia de cada paciente se estima con el mismo patrón de supervivencia que ya usa la espera de cama",
    ("/diagnosticos", "/paciente"): "el tipo de paciente cambia su tiempo de espera",
    ("/alertas", "/pronostico"): "el pronóstico de llegadas da el total esperado del día que la alerta compara",
    ("/alertas", "/paciente"): "el estimador hora a hora alimenta el aviso temprano de paciente sin cama",
    ("/alertas", "/simulador"): "el simulador dispara estas alertas mientras corre y muestra la recomendación de cada una",
    ("/perfiles", "/paciente"): "los perfiles que esperan más son los que el estimador distingue",
    ("/datos", "/demanda"): "la limpieza define los episodios que cuentan las llegadas",
    ("/datos", "/ocupacion"): "la regla de estancia única define cuántas camas se cuentan ocupadas",
    ("/resumen", "/espera"): "el cuello de botella es el primero de los ocho hallazgos",
    ("/resumen", "/recomendaciones"): "las siete acciones que se proponen a partir de los hallazgos",
    ("/periodo", "/comparar"): "es el mismo diagnóstico repetible, aquí por periodo y allá por año",
}


def conexiones(ruta):
    """[(ruta_vecina, motivo)] de una pagina, en los dos sentidos."""
    salida = [(v, MOTIVO.get((ruta, v), "")) for v in RELACION.get(ruta, [])]
    for r, vecinas in RELACION.items():
        if ruta in vecinas and r != ruta:
            salida.append((r, MOTIVO.get((r, ruta), "")))
    return salida


# ruta -> {"pasos": [frases], "modelo": [(alternativa, que mostro, por que)] solo en Prediccion}
DETALLE = {
    "/demanda": {"pasos": [
        "Se cuentan **episodios** (una atención continua de un paciente), no visitas: se quitan las visitas copia (≈30 % de la base) y se corta un episodio nuevo tras 168 h sin etapas.",
        "La hora de llegada es la de la primera etapa, porque la hora de la visita no es confiable en ~45 % de los casos.",
        "Periodo confiable: 1-feb-2023 a 9-abr-2026. Después el registro de etapas está incompleto y no se usa."]},
    "/estacionalidad": {"pasos": [
        "Con solo tres años del hospital no se distingue una temporada real de una casualidad, así que la forma del año se toma de datos públicos de muchos años (dengue de Barranquilla 2007–2022; infección respiratoria y diarrea 2016–2019).",
        "Se probaron 7 fuentes; entró solo lo que mejoró el error en jul–dic 2025 sin empeorar el corto plazo, y se confirmó en 2026, que no se usó para elegir.",
        "El resultado alimenta el pronóstico: por eso esta página es un resultado que se conecta con «Pronóstico»."]},
    "/ocupacion": {"pasos": [
        "Camas ocupadas = intervalos de hospitalización distintos abiertos en cada hora, contando una sola vez cada estancia (regla de estancia única, que quitó 2.179 duplicados).",
        "Se compara con las 106 camas que informó el HUN. La media sube de 94 (2023) a 105 (2025) y es por estancias más largas, no por más ingresos.",
        "Ley de Little: ingresos por día × estancia media ≈ camas ocupadas (19,8 × 5,31 ≈ 105)."]},
    "/espera": {"pasos": [
        "Espera de cama = desde el inicio del episodio hasta el inicio de la primera hospitalización (el HUN confirmó que ese registro se hace al asignar la cama).",
        "Cuello de botella = segmento con exceso sobre la referencia de «cuando funciona bien», alto impacto (volumen × retraso) y que se agrava con la carga.",
        "Urgencias antes de la cama concentra el 98 % de las horas de espera; el «hueco sin registro» era un artefacto de duplicados."]},
    "/comparar": {"pasos": [
        "Se repite el mismo diagnóstico del cuello de botella en dos años y se mide cuánto cambió cada componente de la espera.",
        "Es la versión por año de un sistema repetible (`src/diagnostico_cuello_botella.py`): sirve para volver a medir cuando el hospital cambie algo."]},
    "/altas": {"pasos": [
        "Se cruzan la hora de llegada, la hora de alta y la hora de asignación de cama de las estancias únicas.",
        "El 62,7 % de las altas ocurre entre las 14:00 y las 18:59; la cama se asigna con mediana a las 17–18 h sin importar la hora de llegada.",
        "El escenario de adelantar el 30 % de esas altas a la mañana libera hasta 5,1 camas a las 12 h: una cota, no una predicción."]},
    "/factores": {"pasos": [
        "Modelo explicativo sobre el logaritmo de la espera de cama; se mide cuánto R² aporta cada grupo de factores.",
        "Se usa la persona real de cada estancia gemela, para que edad y sexo no sean los de la persona equivocada.",
        "El modelo explica solo el 16 % de la variación: el 84 % depende de lo que no se registra (gravedad, servicio, tipo de cama)."]},
    "/estancia": {"pasos": [
        "Se separan las estancias por duración y se mide cuántas camas aporta cada grupo a la ocupación.",
        "De las 11 camas que sube la ocupación entre 2023 y 2025, ~7 vienen de estancias de más de 30 días: son pacientes con actividad diaria (laboratorios, UCI), no camas fantasma.",
        "Predecir la estancia de un paciente concreto no funciona (R² de 0 a 0,02); por eso se trabaja en conjunto."]},
    "/diagnosticos": {"pasos": [
        "El diagnóstico principal es el primero con código estándar por fecha; los ~300 más frecuentes se agruparon a mano (borrador, falta validación clínica).",
        "Se cuentan diagnósticos distintos, nunca filas, porque un mismo diagnóstico puede repetirse cientos de veces en una visita."]},
    "/perfiles": {"pasos": [
        "Se describen los grupos de pacientes por edad, sexo, tipo de visita y diagnóstico, con la persona real de cada estancia.",
        "Los días de alta demanda se identifican con el percentil 90 de llegadas y de ocupación, y se mira quién llega en esos picos."]},
    "/pronostico": {
        "pasos": [
            "Entrenamiento con feb-2023 a 9-abr-2026; los días desde el 10-abr se dejan fuera del nivel, del calendario y del error.",
            "El rango probable del 80 % sale de los errores reales de la prueba (cobertura 78–82 % en llegadas).",
            "La forma del año se explica en «Forma del año» (Flujo): es una entrada de este modelo."],
        "modelo": [
            ("Regresión de Poisson (elegido)", "7,9 % de error a 1–7 días y 11,5 % a un año en llegadas", "Son conteos y cada efecto se lee como un porcentaje"),
            ("SARIMAX y otros modelos de series", "Mejores en validación, peores a 1–7 días y en 2026", "Menos preciso a corto plazo y difícil de explicar"),
            ("Quincenas, puentes, deduplicar llegadas", "±0,15 puntos de error", "No justifican la complejidad"),
            ("Ingresos a cama por día", "Ningún método supera «día de la semana × nivel reciente» (~18 % de piso por ruido de conteo)", "Se recomienda el pronóstico semanal (error ~9,5 %)")]},
    "/alertas": {
        "pasos": [
            "Alerta A (día congestionado): estima el total del día con lo que ya llegó, mezclado con el pronóstico; corte elegido con jul–dic 2025 y probado en ene–abr 2026.",
            "Alerta B (ocupación): se recomienda la persistencia («lo mismo que ahora») porque la proyección con altas esperadas no la mejora.",
            "Alerta C (paciente sin cama): a las 48 h hay 4 alertas por día con 24 h de margen; más anticipación significa más alertas y menos precisión."],
        "modelo": [
            ("Clasificador logístico a las 12 h (elegido)", "AUC 0,94; precisión 52 %, detección 87 %", "Simple, avisa a media jornada"),
            ("Alerta un día antes", "AUC 0,61", "Casi no mejora al azar"),
            ("Proyectar camas a 24 h con altas esperadas", "Error de 3,7 camas contra 3,2 de la persistencia", "Persistencia"),
            ("Alertar por riesgo al llegar", "Marcaría al 44 % con 4 de cada 10 falsas alarmas", "Alertar a las 48 h de espera")]},
    "/atipicos": {
        "pasos": [
            "Un día es atípico si se aparta más de 3 desviaciones del pronóstico: 14 días de llegadas, 9 de ingresos y 7 de espera (se esperarían ~3 por azar).",
            "Solo 3 de los 14 días de llegadas tienen causa de calendario; los dos más extremos parecen cortes de registro o de sistema (hipótesis sin comprobar)."],
        "modelo": [
            ("Residuo estandarizado frente al pronóstico (elegido)", "Detecta días con llegadas o ingresos fuera de lo esperado", "Reutiliza el modelo de pronóstico y se lee fácil"),
            ("Regla del rango intercuartílico", "Marcaba demasiados casos por la asimetría de los datos", "Descartada")]},
    "/paciente": {
        "pasos": [
            "Un modelo de árboles de gradiente por cada hora de espera transcurrida (0 a 11 h; desde las 12 h, uno combinado) responde: «si sigue esperando, ¿qué probabilidad hay de cama en la próxima hora?». Encadenadas, dan la curva completa.",
            "Entradas: edad, sexo, tipo de visita, horas esperadas, hora y día, ocupación típica, recorrido en urgencias y, desde las 6 h, 11 banderas de laboratorio.",
            "Se reentrena cada mes dando más peso a lo reciente; el modelo de consulta usa datos hasta el 9-abr-2026."],
        "modelo": [
            ("Supervivencia hora a hora (elegido)", "Mejora ~9 % al llegar y ~11 % a las 3–6 h; el percentil 90 cubre 91 %", "Da la distribución completa y se actualiza con lo que pasa"),
            ("LightGBM, XGBoost y otros 13 enfoques", "Todos al mismo nivel", "El de supervivencia da además probabilidades calibradas"),
            ("Fila «primero en llegar, primero en cama»", "53 % de pares en orden, frente a 50 % por azar", "No se cumple en los datos"),
            ("Alerta de espera larga al llegar", "AUC 0,60–0,68", "Alerta a las 12 o 48 h con el estimador")]},
    "/camas": {
        "pasos": [
            "Simulación Monte Carlo: para cada día futuro se toman ingresos pronosticados y estancias reales por perfil (niños y adultos) y se cuenta la ocupación. Con miles de repeticiones sale la probabilidad de superar las 106 camas.",
            "Se validó con un backtest: la banda del 80 % cubre 78,8 % de los días reales.",
            "Escenarios: más ingresos, estancias más cortas, altas más temprano; se comparan con el caso base."],
        "modelo": [
            ("Monte Carlo con estancias reales (elegido)", "Respeta la cola larga de las estancias; cobertura de ~79–86 % en el backtest", "Da probabilidades de saturar y permite escenarios"),
            ("Predecir la estancia de cada paciente", "R² de 0 a 0,02", "Se trabaja la estancia en conjunto"),
            ("Proyección con altas esperadas", "Peor que «lo mismo que ahora»", "Persistencia y modelo de flujo para la cola"),
            ("Ley de Little sola", "Coherente (19,8 × 5,31 ≈ 105) pero sin incertidumbre", "Se usa como comprobación, no como modelo")]},
}

# 20-nov-2026: todas las paginas tienen el mismo panel (como se calculo, que NO dice, paso a paso, que se probo y descarto, paginas relacionadas).
# Lo que faltaba se completa aqui con lo que ya dicen las propias paginas y el documento final.
DETALLE.setdefault("/demanda", {})["modelo"] = [('Deduplicar las llegadas (≈4 % de réplicas)', 'Cambia el error del pronóstico en ±0,15 puntos; la proporción es estable en el tiempo', 'No se deduplican'), ('Contar visitas en vez de episodios', '≈30 % de la base son visitas copia', 'Se cuentan episodios'), ('Hora de la visita como hora de llegada', 'No es confiable en ~45 % de los casos', 'Se usa la hora de la primera etapa')]
DETALLE.setdefault("/estacionalidad", {})["modelo"] = [('Estacionalidad solo con los tres años del hospital', 'No distingue una temporada real de una casualidad', 'Datos públicos de muchos años'), ('Siete fuentes públicas', 'Entró solo lo que mejoró el error en jul–dic 2025 sin empeorar el corto plazo', 'Dengue en las llegadas; infección respiratoria y diarrea en los ingresos')]
DETALLE.setdefault("/ocupacion", {})["modelo"] = [('Contar todas las filas de hospitalización', 'Había 2.179 duplicados', 'Regla de estancia única'), ('Atribuir la subida a más ingresos', 'Los ingresos casi no cambian; la estancia sí (media de 94 a 105 camas)', 'La subida se explica por estancias más largas')]
DETALLE.setdefault("/espera", {})["modelo"] = [('El «hueco sin registro» como parte de la espera', 'Era un artefacto de duplicados', 'Se corrigió: urgencias antes de la cama concentra el 98 % de las horas'), ('Camas de baja actividad clínica', 'Son ~6 y no crecen', 'No explican el cuello de botella')]
DETALLE.setdefault("/comparar", {})["modelo"] = [('Atribuir el cambio a una sola causa', 'Todo son asociaciones, no causas', 'Se mide cuánto cambió cada componente de la espera')]
DETALLE.setdefault("/altas", {})["modelo"] = [('Leer el 30 % adelantado como predicción', 'Es una cota, no una predicción', 'Se presenta como escenario'), ('Asignar la cama según la hora de llegada', 'La mediana de asignación es 17–18 h sin importar la hora de llegada', 'Se explica por el proceso de altas')]
DETALLE.setdefault("/factores", {})["modelo"] = [('Predecir la espera con todos los factores', 'El modelo explica solo el 16 % de la variación', 'Se publica como «explica, no predice»'), ('Día de la semana y festivos', 'Casi no cambian la espera', 'No se destacan como factor'), ('Edad y sexo de la persona equivocada en estancias gemelas', 'Sesgaba el modelo', 'Se usa la persona real de cada estancia')]
DETALLE.setdefault("/estancia", {})["modelo"] = [('Predecir la estancia de cada paciente al ingreso', 'R² de 0 a 0,02', 'Se trabaja la estancia en conjunto'), ('«Camas fantasma» en las estancias de más de 30 días', '~7 de las 11 camas son pacientes con actividad diaria (laboratorios, UCI)', 'No son camas fantasma'), ('Modelo explicativo de estancia', 'R² de 7,9 a 10,8 %', 'Se declara «explica, no predice»')]
DETALLE.setdefault("/diagnosticos", {})["modelo"] = [('Contar filas de diagnóstico', 'Un mismo diagnóstico se repite cientos de veces en una visita', 'Se cuentan diagnósticos distintos'), ('Los ~300 diagnósticos más frecuentes por separado', 'Demasiados para leerlos', 'Agrupados a mano: borrador, falta validación clínica')]
DETALLE.setdefault("/perfiles", {})["modelo"] = [('Alertar por riesgo al llegar', 'Marcaría al 44 % con 4 de cada 10 falsas alarmas', 'No se usa; se alerta a las 12 o 48 h'), ('Edad y sexo de la estancia duplicada', 'Podían ser de otra persona', 'Se usa la persona real de cada estancia')]
DETALLE.setdefault("/resumen", {})["pasos"] = ['Se toman los ocho hallazgos del resumen ejecutivo (capítulo 1 del documento final).', 'Cada cifra remite a la página donde se calcula y se explica.', 'Los escenarios llevan sus supuestos escritos y las recomendaciones, su firmeza.']
DETALLE.setdefault("/resumen", {})["modelo"] = [('Presentar causas o promesas', 'Casi todo son asociaciones y escenarios con supuestos', 'Los supuestos se escriben junto a cada cifra')]
DETALLE.setdefault("/datos", {})["pasos"] = ['Se extraen las tablas de la base del hospital (modelo OMOP, enero de 2023 a julio de 2026).', 'Se descartan etapas ambulatorias de duración cero y etapas abiertas al extraer.', 'Se quitan las visitas copia y las estancias duplicadas con reglas documentadas.', 'Se fija el periodo confiable: 1-feb-2023 a 9-abr-2026.']
DETALLE.setdefault("/datos", {})["modelo"] = [('Etapas ambulatorias (duración cero)', 'Son eventos administrativos', 'Se descartan'), ('Etapas abiertas al extraer (2.053)', 'Su fin trae milisegundos, no una hora real', 'Se descartan'), ('Registro desde el 10-abr-2026', 'Etapas incompletas; el hospital no explicó la causa', 'No se usa en el análisis')]
DETALLE.setdefault("/periodo", {})["pasos"] = ['Cada reporte se calcula de antemano con el diagnóstico repetible del cuello de botella.', 'Se mide cuánto espera cada estancia por encima de «lo normal»: la espera de los momentos con menos pacientes.', 'Esa referencia se calcula con el periodo con el que se compara.', 'Se muestran años y semestres, hasta el 9-abr-2026.']
DETALLE.setdefault("/periodo", {})["modelo"] = [('Un rango libre de fechas', 'Cada reporte se calcula de antemano', 'Se ofrecen años y semestres'), ('Una referencia fija de «lo normal»', 'La referencia depende del periodo con que se compara', 'Se recalcula con cada periodo')]
DETALLE.setdefault("/paciente-cama", {})["pasos"] = ['Un modelo por cada hora ya pasada en cama estima la probabilidad de recibir el alta en la hora siguiente.', 'Encadenadas, esas probabilidades dan el rango completo de lo que falta.', 'Se entrena con las estancias del periodo confiable; las que aún no tienen alta aportan como censuradas.', 'El diagnóstico entra solo si se indica.']
DETALLE.setdefault("/simulador", {})["pasos"] = ['Cada llegada simulada recibe un perfil real (edad × ruta).', 'Se hospitaliza con la probabilidad histórica de su perfil y, si va a cama, hereda la trayectoria de un paciente real parecido.', 'Se repite varias veces para mostrar el rango; parte del 9-abr-2026 con el censo y la cola reales.', 'Las alertas se evalúan sobre cada repetición mientras corre.']
