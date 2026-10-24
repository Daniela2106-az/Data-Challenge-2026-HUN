# Sesión de preguntas con el HUN (documento vivo)

**Estado (23-oct-2026):** el correo con las preguntas se envió y no hubo respuesta. El HUN abrirá una **sesión de preguntas**.
Fecha y hora de la sesión: ______________________  Quién asiste por el equipo: ______________________

**Cómo usar este documento**
1. **Antes:** elegir qué preguntas hacer. Si el tiempo es corto, solo la sección A (cambian las conclusiones del proyecto).
2. **Durante:** anotar la respuesta en la columna "Respuesta", con quién la dio y la fecha. Si no saben, escribir "No saben" (también sirve).
3. **Después:** seguir la lista de la sección E para actualizar el proyecto con cada respuesta.

**Nota para quien pregunte:** el HUN no conoce los nombres que usamos (ER, TU, HOSP). Hablar con los números de la base:
**9203** (llegada/triage a urgencias), **3045729** (atención en urgencias, "Treatment urgency") y **9201** (hospitalización).
No compartir identificadores de pacientes ni de visitas en la sesión escrita; si piden ejemplos, usar fechas.

---

## A. Imprescindibles (cambian las conclusiones)

| # | Pregunta | Por qué importa / qué cambia | Respuesta | Quién y fecha |
|---|---|---|---|---|
| A1 | ¿Cuántas camas de hospitalización tiene el hospital por año (y por servicio si se puede), y cuántos cubículos o camillas de urgencias? | Sin esto no hay porcentaje de ocupación, "días saturados" ni escenarios de capacidad. Hoy solo sabemos que se ocupan ~113 camas en promedio (máximo observado ~143). | | |
| A2 | Desde abril de 2026 las llegadas bajan 25–35 % y los ingresos a cama 20–30 % (244 llegadas por día en ene–abr, 186 en mayo, 171 en junio). ¿Hubo un cambio real (cierre o traslado de servicio, otro triage, otra sede) o cambió el registro o la extracción está incompleta? | Decide si mayo–julio de 2026 se usan o se descartan, y si la "caída" es un hallazgo o un problema de datos. | | |
| A3 | El 41 % de las estancias en cama aparece repetido en dos pacientes distintos (mismo inicio y fin de cama, ids de paciente casi consecutivos). ¿Es un error de extracción o de anonimización? ¿Cuál de los dos pacientes es el real? | Confirma que contar cada estancia una sola vez es correcto (cambia 27,7 a ~22 ingresos por día y 146 a ~113 camas). | | |
| A4 | Para los pacientes que terminan hospitalizados, el tiempo en la etapa 3045729 antes de la cama, ¿es atención clínica, espera de cama o ambas? ¿Se registra cuándo se decide hospitalizar y cuándo se asigna la cama? | Hoy la espera de cama (mediana 18 h) mezcla atención y espera: no podemos separarlas. Es la limitación principal del hallazgo central. | | |
| A5 | En la etapa 9201, ¿el inicio es la asignación de cama, la llegada al piso o el ingreso administrativo? ¿El fin es la hora de la orden de alta o la salida física del paciente? | El hallazgo de "altas tardías" (61,5 % entre las 14:00 y las 18:59, solo 15 % antes del mediodía) depende de qué hora es esa. | | |

## B. Importantes

| # | Pregunta | Por qué importa / qué cambia | Respuesta | Quién y fecha |
|---|---|---|---|---|
| B1 | Entre el 36 y el 42 % de las etapas 3045729 tienen inicio igual a fin. ¿Falta la hora de salida? ¿Existe otra fecha de alta en alguna parte? | Hoy no podemos medir cuánto dura urgencias de quien se va de alta. | | |
| B2 | Cerca de 1 de cada 4 hospitalizados pasa tiempo sin ninguna etapa registrada antes de la cama (mediana de 19,7 h entre ellos). ¿Dónde está el paciente en ese tiempo? | Es el 23 % de las horas de espera de cama. | | |
| B3 | ¿El hospital tiene una meta de tiempos (por ejemplo, cama asignada en X horas desde que se decide hospitalizar)? | Sería la referencia externa de "cuando funciona bien"; hoy usamos una referencia interna. | | |
| B4 | La estancia media subió de 4,7 días (2023) a 5,5 días (2025). ¿Cambió el tipo de pacientes, algún proceso, convenio o política? | Explica por qué la ocupación subió 13 % con ingresos estables; es el mayor palanca de camas (−16 si volviera a 2023). | | |
| B5 | Los sábados 28-mar-2026 y 15-jun-2024 casi no hay llegadas (88 y 111) ni ingresos a cama (1 y 8). ¿Hubo una falla de sistema, de registro o un cierre? | Confirmaría que son fallas de datos y no días reales. | | |
| B6 | ¿El hospital está en Barranquilla y baja la afluencia durante el Carnaval? | Asumimos que sí; las visitas bajan ~17 % esos días. | | |
| B7 | Unos 63 mil episodios tienen solo la etapa de llegada (9203) y nada clínico. ¿Son pacientes que se fueron sin atención o registros administrativos? | Define si cuentan como llegadas. | | |
| B8 | ¿Hay alguna práctica o política de horario de altas (rondas, cierre de facturación, hora de entrega de camas)? | Explicaría por qué solo el 15 % de las altas es antes del mediodía. | | |

## C. Si hay tiempo

| # | Pregunta | Respuesta | Quién y fecha |
|---|---|---|---|
| C1 | ¿Qué significa realmente `visit_concept_id`? (visitas "ambulatorias" que incluyen hospitalización; "Treatment urgency" con 43 h de mediana sin hospitalizar) | | |
| C2 | Faltan columnas que menciona el instructivo (`visit_type_concept_id`, `preceding_visit_occurrence_id`, otras). ¿Hay una versión actualizada de la base? | | |
| C3 | Varias etapas 9201 seguidas, ¿son traslados entre servicios? ¿Hay servicio, piso o cama en alguna tabla? | | |
| C4 | La única señal de cuidados intensivos es "Admission to adult intensive care unit". ¿Hay más datos de UCI? | | |
| C5 | `procedure_date` está vacía en toda la tabla. ¿Pueden entregarla? | | |
| C6 | ¿Cuál es el diagnóstico principal de cada visita? (`condition_type_concept_id` siempre vale 0) | | |
| C7 | Fines con milisegundos en julio de 2026: ¿son pacientes que seguían hospitalizados cuando se extrajo la base? | | |

## D. Para los organizadores del reto (no para el hospital)

| # | Pregunta | Respuesta | Quién y fecha |
|---|---|---|---|
| D1 | ¿Cuál es la rúbrica de evaluación? | | |
| D2 | ¿El repositorio de GitHub debe ser público? ¿Se pueden subir gráficos y tablas agregadas, o ninguna cifra derivada de los datos? | | |
| D3 | ¿El dashboard de Power BI puede usar datos agregados? ¿Cuál es el plazo exacto de entrega (fin de noviembre de 2026)? | | |

---

## E. Después de la sesión: qué actualizar según cada respuesta

| Si responden... | Actualizar |
|---|---|
| A1 (camas) | `docs/HALLAZGOS.md` 4.6 y 5.2, `docs/recomendaciones.md` (quitar "capacidad desconocida"); calcular % de ocupación y días saturados en `src/simulacion_altas.py` y `src/alertas.py` |
| A2 (caída de llegadas) | `CLAUDE.md` (aviso de la sección 2), si es de registro: excluir los meses afectados en `src/` y repetir pronóstico y alertas |
| A3 (gemelas) | `CLAUDE.md` 4.6; si dicen cuál es la persona real, ajustar la regla de qué episodio se conserva en `src/analisis_etapas.py` |
| A4, A5 (etapas) | Reescribir la definición de espera de cama en `docs/plan_de_accion.md` sección 0 y repetir `src/construir_segmentos.py` y `src/ranking_cuellos.py` |
| B3 (meta) | Agregar la referencia (c) en `src/ranking_cuellos.py` |
| B5 (días extremos) | Marcar esos días como fallas de datos en `docs/dias_atipicos.md` |
| Cualquiera | Anotar la respuesta arriba, mover la pregunta en `CLAUDE.md` sección 8 a "respondida" y quitar el supuesto correspondiente de `docs/HALLAZGOS.md` sección 7 |

## Notas libres de la sesión

(Anotar aquí lo que digan que no encaje en las preguntas: nombres de servicios, cambios de proceso, fechas importantes, personas de contacto.)

-
-
-
