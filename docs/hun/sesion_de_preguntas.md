# Sesión de preguntas con el HUN (documento vivo)

**Estado (29-oct-2026):** la sesión de preguntas **ya se hizo** (29-oct, por chat de reunión, con otros equipos presentes) y **no habrá más sesiones**. Se contestaron las preguntas 1, 3, 4, 5 (en parte) y 6; las demás (2, 7, 8 y las de organizadores) quedan sin respuesta y se declaran como limitaciones. Las respuestas ya están reflejadas en `CLAUDE.md` 4.7.
Fecha y hora de la sesión: ______________________  Quién asiste por el equipo: ______________________

**Cómo usar este documento**
1. **En la reunión:** usar solo la lista corta de abajo (8 preguntas). Están escritas en palabras simples, sin números ni nombres de la base, para que cualquiera en el hospital pueda
   contestar aunque sea de forma aproximada. "No sé" o "le pregunto a X" también sirve: anotar quién sabría.
2. **Antes de la reunión:** si el tiempo es corto, hacer solo las preguntas 1 a 4.
3. **Después:** seguir la sección E para actualizar el proyecto con cada respuesta.

**Nota para quien pregunte:** el HUN no conoce los nombres que usamos (ER, TU, HOSP). Si piden precisión, hablar con los números de la base:
**9203** (llegada a urgencias), **3045729** (atención en urgencias) y **9201** (hospitalización). No compartir identificadores de pacientes ni de visitas; si piden ejemplos, usar fechas.

---

## Lista corta para la reunión (en orden de prioridad)

| # | Pregunta (en palabras simples) | Para qué la necesitamos | Respuesta | Quién y fecha |
|---|---|---|---|---|
| 1 | **¿Cuántas camas de hospitalización tiene el hospital, y cuántas camillas o cubículos en urgencias?** (un número aproximado sirve) | Para decir cuántas camas están llenas, en porcentaje. Hoy solo sabemos que se ocupan unas 113 en promedio. | **106 camas de hospitalización** (Adultos 64, Pediátrica 8, TPR 4, Intermedia Adultos 6, Intensiva Adultos 14, incubadoras neonatales 6 + 3 + 1) y **58 camillas de urgencias** (Obs. Pediátrica 14, Adultos Hombres 18, Adultos Mujeres 26; primero dijeron 68 y corrigieron a 58). Sin fecha de la lista. | HUN, chat de la reunión, 29-oct-2026 |
| 2 | **¿Desde abril de 2026 llegan menos pacientes?** Los datos muestran un 25 a 35 % menos. ¿Cambió algo en el hospital (un servicio cerró, otra sede, otro triage), o puede que a los datos les falten registros de los últimos meses? | Para saber si usamos o descartamos los últimos meses. | | |
| 3 | **Vemos la misma hospitalización anotada en dos pacientes distintos** (pasa en 4 de cada 10 hospitalizaciones). ¿Saben por qué pasa? ¿Es un error al sacar o anonimizar los datos? | Contamos cada hospitalización una sola vez; queremos confirmar que está bien. | **Lo más probable es que sean duplicados; elegir el registro que tenga la información clínica** (condición, procedimiento, etc.). No dijeron la causa. | HUN, 29-oct-2026 |
| 4 | **Cuando un paciente de urgencias queda hospitalizado, ¿se anota en algún sitio a qué hora se decide hospitalizarlo y a qué hora se le asigna la cama?** | Hoy medimos la espera desde que llega hasta que aparece la hospitalización, y no podemos separar atención de espera de cama. | **La hospitalización (9201) se registra cuando se asigna la cama**; el traslado físico tarda un par de minutos. No dijeron si se anota la hora de la decisión. | HUN, 29-oct-2026 |
| 5 | **En el registro de hospitalización, ¿la hora de inicio es cuando se asigna la cama o cuando el paciente llega al piso? ¿Y la hora final es la orden de alta o cuando el paciente sale?** | Más de 6 de cada 10 altas están entre las 2 y las 7 de la tarde y queremos saber qué hora es esa. | Inicio = asignación de cama (ver pregunta 4). Falta saber si el fin es la orden de alta o la salida física. | HUN, 29-oct-2026 |
| 6 | **¿Hay horarios o costumbres para dar de alta** (rondas médicas, cierre de facturación, hora en que se entrega la cama)? | Explicaría por qué solo 15 de cada 100 altas son antes del mediodía. | **Sí hay horarios y costumbres de alta.** No dieron el detalle. | HUN, 29-oct-2026 |
| 7 | **¿En qué momento se escribe el diagnóstico** (en urgencias, al subir a piso, al dar de alta)? | Los pacientes que esperan más cama casi no tienen diagnóstico anotado; queremos saber si es porque se escribe más tarde. | | |
| 8 | **¿Hay una meta de tiempo, por ejemplo "cama asignada en X horas"?** ¿Y qué pasó con la estancia, que subió de 4,7 a 5,5 días entre 2023 y 2025: cambió el tipo de pacientes o algún proceso? | La meta sería nuestra referencia de "cuando funciona bien"; lo segundo explica por qué suben las camas ocupadas. | | |

**Preguntas que también pueden contestar los organizadores u otros equipos** (no son del hospital):

| # | Pregunta | Respuesta | Quién y fecha |
|---|---|---|---|
| 9 | ¿Hay una rúbrica de evaluación? ¿Cuál es la fecha límite exacta de entrega? | | |
| 10 | ¿El repositorio de GitHub debe ser público? ¿Podemos publicar gráficos y cifras resumidas (no datos de pacientes)? | | |
| 11 | ¿El dashboard de Power BI puede usar tablas resumidas en vez de una fila por paciente? ¿Cómo se comparte el enlace? | | |
| 12 | ¿Alguien sabe si hay una versión más completa de la base (con servicio o piso, signos vitales, fecha de los procedimientos)? | | |

---

# Referencia técnica del equipo (no se lee en la reunión)

Las preguntas 1 a 8 de arriba resumen las siguientes del detalle: 1 = A1; 2 = A2; 3 = A3; 4 = A4 y B2; 5 = A5; 6 = B8; 7 = B9; 8 = B3 y B4.
9 a 12 = D1, D2, D3 y C2/C5. Los códigos A1 a D3 se usan en otros documentos del repositorio (`powerbi/`, `docs/`).

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
| B9 | ¿Cuándo y dónde se registra el diagnóstico (urgencias, ingreso a piso, alta)? Entre los hospitalizados lo tiene el 60 % de quienes esperan cama 6 h o menos y el 27 % de quienes esperan más de 24 h | Si se registra al llegar a piso, los pacientes con espera larga no lo tienen aún y los análisis por diagnóstico están sesgados. | | |

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
| 1 / A1 (camas) | `docs/HALLAZGOS.md` 4.6 y 5.2, `docs/recomendaciones.md` (quitar "capacidad desconocida"); calcular % de ocupación y días saturados en `src/simulacion_altas.py` y `src/alertas.py` |
| 2 / A2 (caída de llegadas) | `CLAUDE.md` (aviso de la sección 2), si es de registro: excluir los meses afectados en `src/` y repetir pronóstico y alertas |
| 3 / A3 (gemelas) | `CLAUDE.md` 4.6; si dicen cuál es la persona real, ajustar la regla de qué episodio se conserva en `src/analisis_etapas.py` |
| 4 y 5 / A4, A5 (etapas) | Reescribir la definición de espera de cama en `docs/plan_de_accion.md` sección 0 y repetir `src/construir_segmentos.py` y `src/ranking_cuellos.py` |
| 8 / B3 (meta) | Agregar la referencia (c) en `src/ranking_cuellos.py` |
| 7 / B9 (cuándo se registra el diagnóstico) | Ajustar `docs/diagnosticos_y_tiempos.md` y la advertencia de sesgo en `docs/HALLAZGOS.md` 4.5b |
| 6 / B8 (horario de altas) | Matizar la explicación de altas tardías en `docs/recomendaciones.md` |
| B5 (días extremos, solo si se pregunta) | Marcar esos días como fallas de datos en `docs/dias_atipicos.md` |
| Cualquiera | Anotar la respuesta arriba, mover la pregunta en `CLAUDE.md` sección 8 a "respondida" y quitar el supuesto correspondiente de `docs/HALLAZGOS.md` sección 7 |

## Notas libres de la sesión

(Anotar aquí lo que digan que no encaje en las preguntas: nombres de servicios, cambios de proceso, fechas importantes, personas de contacto.)

-
-
-
