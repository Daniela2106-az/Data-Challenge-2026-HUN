"""
dashboard/fichas_prediccion.py  -  «¿Cómo se interpreta?» y «Ficha técnica» de las paginas de Prediccion que no las tenian (14-nov-2026)
Pronostico, Paciente en espera y Planeacion de camas traen las suyas propias (con graficos); aqui estan las de Alertas y Dias atipicos, con la misma forma, para que todas las paginas de Prediccion tengan interpretacion, documentacion y ficha tecnica.
Cifras: docs/documento_final.md (6.2, 6.3, 6.8), docs/CONTEXTO_TECNICO.md 6b y docs/dias_atipicos.md.
"""
FICHAS = {
    "/alertas": {
        "interpretacion": [
            ("Qué estás viendo", "Cuántas veces habría sonado cada alerta en los meses de prueba, cuántas veces acertó y cuántas fueron falsas alarmas, según el momento del día en que se avisa."),
            ("Cómo se calculó", "Cada alerta se probó reproduciendo, día por día, lo que se habría sabido a esa hora en enero a abril de 2026. El corte de cada alerta se eligió antes con julio a diciembre de 2025, sin mirar la prueba."),
            ("Cómo leer precisión y detección", "**Precisión**: de cada 100 alertas que suenan, cuántas eran ciertas. **Detección**: de cada 100 días realmente congestionados, cuántos avisó. Más anticipación sube la detección pero baja la precisión."),
            ("Qué NO dice", "Son pocos días congestionados (15 en la prueba), así que las cifras se mueven. Las alertas de paciente sin cama cuentan solo a quienes luego se hospitalizan: es una cota inferior de la carga real. Una alerta no dice qué hacer: eso lo decide el hospital."),
        ],
        "ficha": {
            "sub": "cómo se construyó y qué se probó",
            "etapas": [("1. Pronóstico", "El pronóstico de llegadas (Poisson con calendario y forma del año) da el total esperado del día."),
                       ("2. Umbral", "Día congestionado = llegadas por encima del percentil 90 del mismo día de la semana en las últimas 12 semanas."),
                       ("3. Estimar el día", "A cada hora se estima el total del día con lo ya llegado, mezclado con el pronóstico."),
                       ("4. Corte", "El corte de cada alerta se elige con julio a diciembre de 2025."),
                       ("5. Prueba", "Se reproduce enero a 9-abr-2026, que no se usó para elegir.")],
            "tabla": [("Qué se probó", "Resultado", "Por qué"),
                      ("Día congestionado a las 12 h", "Entra", "AUC 0,94; precisión 52 %, detección 87 %"),
                      ("Día congestionado un día antes", "No entra", "AUC 0,61: casi no mejora al azar"),
                      ("Ocupación de camas a 24 h con altas e ingresos esperados", "No entra", "Error 3,7 camas contra 3,2 de «lo mismo que ahora»; se usa la persistencia"),
                      ("Paciente sin cama a las 48 h", "Entra", "4 alertas por día, 52 % termina esperando más de 72 h y 24 h de margen"),
                      ("Alertar por riesgo al llegar", "No entra", "Marcaría al 44 % con 4 de cada 10 falsas alarmas")],
            "nota": "Detalle: documentación, sección 6.2, y `src/alertas.py`."},
    },
    "/atipicos": {
        "interpretacion": [
            ("Qué estás viendo", "Los días en que las llegadas, los ingresos a cama o la espera se apartaron mucho de lo que el pronóstico esperaba, uno por uno."),
            ("Cómo se calculó", "A cada día se le resta lo que el pronóstico esperaba y se mide cuántas desviaciones típicas se aparta. Se marca como atípico si pasa de 3. Por azar se esperarían unos 3 días; hubo 14 de llegadas, 9 de ingresos y 7 de espera."),
            ("Cómo leer un día atípico", "Casi todos son días con **menos** actividad, no con más. Los dos más extremos (28-mar-2026 y 15-jun-2024) tienen caídas simultáneas de llegadas e ingresos: parecen cortes de registro o de sistema."),
            ("Qué NO dice", "No explica la causa de cada día: es una hipótesis sin comprobar. Con el calendario ya modelado, solo 3 de 14 días de llegadas tienen causa de calendario. Ningún día tuvo la espera más alta de lo esperado: el problema de la espera es crónico, no de días puntuales."),
        ],
        "ficha": {
            "sub": "cómo se construyó y qué se probó",
            "etapas": [("1. Pronóstico", "Se parte del mismo modelo del pronóstico, para llegadas, ingresos y espera."),
                       ("2. Residuo", "Real menos esperado, dividido por la variación típica de ese tipo de día."),
                       ("3. Umbral", "Atípico si el valor absoluto pasa de 3 desviaciones."),
                       ("4. Calendario", "Se revisa si el día coincide con un festivo, Carnaval o fin de año."),
                       ("5. Causa", "Si no hay causa de calendario, se mira si cayeron a la vez llegadas e ingresos (posible corte de registro).")],
            "tabla": [("Qué se probó", "Resultado", "Por qué"),
                      ("Residuo estandarizado frente al pronóstico", "Entra", "Reutiliza el modelo y se lee fácil"),
                      ("Regla del rango intercuartílico", "No entra", "Marcaba demasiados casos por la asimetría de los datos"),
                      ("Revisar los días raros para mejorar el pronóstico", "Entra", "Descubrió el efecto del Carnaval y del fin de año"),
                      ("Detectar días con espera más alta de lo esperado", "Sin casos", "Ningún día lo fue")],
            "nota": "Detalle: documentación, sección 6.3, `src/dias_atipicos.py` y `docs/dias_atipicos.md`."},
    },
}
