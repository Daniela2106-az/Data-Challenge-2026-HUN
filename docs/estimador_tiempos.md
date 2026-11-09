# A6 · Estimación del tiempo de espera de cama (7-nov-2026; revisado el 9-nov, sección 7)

**Qué pide el instructivo (componente 3):** «modelos analíticos o predictivos que permitan estimar tiempos de atención». La pregunta concreta: **cuando un paciente espera cama, ¿cuánto le falta?**

## Resumen
1. **La espera es individual.** Pacientes que llegan el mismo día o a la misma hora no esperan parecido. Por eso la ocupación del hospital o la cola casi no ayudan a estimarla, y lo que sirve es información de cada paciente.
2. **El estimador es un modelo de tiempo restante.** Para un paciente que espera cama (**es decir, que ya tiene orden de hospitalización**: se entrenó solo con quienes recibieron cama, ver sección 7), da el rango de lo que le falta (percentiles 25, 50, 75 y 90) y la probabilidad de recibir cama en 6, 12 y 24 horas, y se recalcula a medida que pasa la espera. Usa el paciente, la hora del reloj, la ocupación, su historial de hospitalizaciones y su recorrido en urgencias, todo conocido en el momento. Se consulta con `estimar_tiempo_restante()`.
3. **Funciona mejor que todo lo demás que probamos, pero el techo es bajo.** Reentrenado cada mes con más peso en lo reciente, que es como se debe usar porque el hospital cambió, mejora el rango 8,1 % al llegar y 9,8–10,3 % entre las 3 y las 6 horas de espera, frente a darle a todos el mismo rango. Sus percentiles aciertan en datos nuevos, y le gana con margen comprobado a las otras cinco alternativas.
4. **Lo que más decide cuándo llega la cama es la hora del reloj:** entre las 6 y las 12 h casi nadie recibe cama; las camas se asignan entre las 15 y las 17 h y entre las 20 y las 23 h.
5. **Lo que de verdad lo mejoraría es saber, al llegar, la gravedad y el servicio.** Los procedimientos de cada estancia muestran que el hospital da cama rápido a los graves (UCI: mediana 2,7 h) y hace esperar más a cirugía, urología y ortopedia (30–38 h). Si esa información se conociera al llegar, la mejora pasaría de 7,6 % a 15,8 %, y a 18,6 % sumando el diagnóstico (comparando modelos entrenados una sola vez). Es más que cualquier cambio de modelo, y es el argumento para registrar el triage y el servicio en la base.

---

## 1. Qué decide la espera: lo que encontramos en los datos
Se usan las estancias únicas del periodo confiable, del 1-feb-2023 al 9-abr-2026 (22.819 estancias). La espera va de la llegada a la asignación de cama, como confirmó el HUN (`CLAUDE.md` 4.7): mediana 18,5 h, p25 6,4 h, p75 37,8 h y p90 72,9 h (`HALLAZGOS.md` 4.2).

**1.1 La espera es individual, no del momento.** Si la espera dependiera del estado del hospital, los pacientes que llegan juntos esperarían parecido. No pasa: el día de llegada explica un 0,1 % de la espera más allá de lo que daría el azar, y el día con el bloque de 3 horas, un 2,3 %. Por eso la ocupación y la cola casi no ayudan, como también encontró `docs/capacidad_efectiva.md`.

**1.2 La hora del reloj manda.** Para un paciente que sigue esperando, la probabilidad de recibir cama en la hora siguiente es:
- ~1 % entre las 6 y las 12 h;
- 6–8 % entre las 15 y las 17 h;
- 1 % a las 18 h;
- 9–11 % entre las 20 y las 22 h.

Los datos crudos lo confirman: el 24 % de las camas se asigna entre las 15 y las 17 h y el 37 % entre las 20 y las 23 h. Es coherente con las altas tardías (`CLAUDE.md` 6b). La subida de la noche no se había descrito antes; podría ser la hora en que se registra la asignación más que la del traslado.

**1.3 El historial del paciente.** El 11,5 % de las estancias es de alguien que ya estuvo hospitalizado. En ellos la espera se repite: la espera anterior se correlaciona 0,34 con la actual. El historial probablemente refleja la enfermedad del paciente y el servicio que lo recibe.

**1.4 El recorrido en urgencias.** Son los registros de las etapas de urgencias de la propia visita (`visit_detail`). En tiempo real, sin trampa, se puede saber cuántas etapas de atención empezaron, cuántas cerraron y cuántas siguen abiertas. Por ejemplo, quien a las 6 h tiene 2 o más etapas abiertas a la vez (~5 % de los pacientes) recibe cama mucho antes: le faltan unas 5 h en la mediana, contra 23 h para el resto.

**1.5 La gravedad y el servicio.** En urgencias la prioridad se define con el triage, de I (inmediata) a V (muy baja). La base no lo trae: no está en ninguna tabla, la etapa 9203 solo trae la hora y entre los 157 procedimientos frecuentes no hay ninguno llamado «triage». Lo que sí hay son los **procedimientos de cada estancia** (`procedimientos_por_estancia.csv`, extraído por Daniela para A2b). Con ellos se marcaron dos cosas:
- **Gravedad:** UCI, gases arteriales, lactato, troponina, transfusión, catéter central, hemocultivos, TAC de cabeza y monitoreo cardiaco.
- **Servicio que atendió al paciente:** ginecobstetricia, cirugía general, urología, ortopedia, psiquiatría, pediatría y endoscopia digestiva, según interconsultas, remisiones y cirugías.

| Grupo | % de las estancias | Espera mediana | p90 |
|---|---|---|---|
| Todas | 100 % | 18,5 h | 72,9 h |
| **Urología** | 4,1 % | **37,7 h** | 105,1 h |
| **Ortopedia** | 3,2 % | **32,8 h** | 106,0 h |
| **Cirugía general** | 11,5 % | **29,6 h** | 89,2 h |
| Endoscopia digestiva | 1,2 % | 26,4 h | 76,4 h |
| Ginecobstetricia | 12,2 % | 15,9 h | 38,4 h |
| Psiquiatría | 2,7 % | 15,0 h | 70,2 h |
| Pediatría | 0,9 % | 7,3 h | 22,7 h |
| Ninguno de esos servicios | 64,1 % | 14,9 h | 69,7 h |
| **Ingreso a UCI** | 3,8 % | **2,7 h** | 36,5 h |
| Hemocultivo | 10,9 % | 5,5 h | 75,5 h |
| Troponina | 4,9 % | 6,9 h | 49,5 h |

**Lectura:** el hospital da cama rápido a los pacientes graves y hace esperar más a los quirúrgicos y urológicos. Es el mismo patrón que mostraban los diagnósticos (`HALLAZGOS.md` 4.5b), ahora visto desde los servicios. **Ojo: los procedimientos no tienen fecha.** Algunos pueden haber ocurrido después de recibir la cama (una cesárea, una transfusión), y el catéter central, por ejemplo, aparece en estancias muy largas porque se pone durante ellas (espera mediana 47,4 h). Es una descripción, no una causa.

---

## 2. El estimador
Código: `src/estimador_tiempo_restante.py` (consulta) y `src/comparar_estimadores.py` (construcción y prueba).

**Cómo funciona.** Para cada hora de espera, el modelo estima la probabilidad de recibir cama en la hora siguiente. Multiplicando esas probabilidades hora por hora sale la probabilidad de seguir esperando, y de ahí los percentiles de lo que falta. Usa árboles de gradiente (`HistGradientBoostingClassifier`).

| Grupo | Variables | Cuándo se conoce |
|---|---|---|
| Paciente | Edad, sexo, tipo de visita, horas que lleva esperando | Al llegar y en cada momento |
| Hospital | Hora del reloj, día de la semana, camas ocupadas en su zona (adultos o niños) | En cada momento |
| Historial | De su última hospitalización: espera, estancia y hace cuántos días terminó; hospitalizaciones previas; grupo del último diagnóstico de una visita anterior | Al llegar |
| Recorrido en urgencias | Etapas de atención iniciadas, cerradas y abiertas; horas de las cerradas; horas desde la última que empezó; admisiones | En cada momento |

**Un modelo por momento de la espera.** El recorrido cambia mientras el paciente espera. Por eso hay un modelo para cada hora de espera de 0 a 11 h (desde el 9-nov; antes eran 0, 2, 4, 6 y 9 h, ver sección 7), entrenado con quienes seguían esperando en ese momento y con lo que se sabía entonces. Esta técnica se llama «landmark». Desde las 12 h de espera el recorrido ya no suma, y se usa un solo modelo con el historial. El corte de 12 h se eligió mirando la prueba.

**Qué no usa, y por qué.** No usa la cola de pacientes esperando cama: contarla exige saber quién se hospitalizará, y además no mejora nada (6,5 % con cola frente a 6,6 % sin ella al llegar).

**Cómo se consulta.**
```python
from estimador_tiempo_restante import estimar_tiempo_restante
estimar_tiempo_restante(edad=67, sexo="Mujer", tipo_visita="Urgencias", horas_esperando=6, ahora="2026-03-04 15:00",
                        hospitalizacion_previa={"espera_h": 60, "estancia_h": 200, "dias_desde": 45, "n_previas": 2},
                        diagnostico_previo="Cancer", etapas_urgencias=[(0.1, 3.0), (3.0, None)], admisiones=[0.0])
```
- El historial, el recorrido y la ocupación son opcionales. Sin historial, el paciente se trata como nuevo. Sin recorrido, se asume lo más común: una etapa de atención abierta desde la llegada.
- Devuelve los percentiles de lo que falta, la hora en que la mitad de los pacientes parecidos ya tendría cama y la probabilidad de recibirla en 6, 12 y 24 h.
- Los modelos se entrenan con todo el periodo confiable, **con más peso en lo reciente** (un dato de hace 6 meses pesa la mitad), y se guardan fuera del proyecto, en `HUN_PROCESADOS/modelos/` (salen de datos clínicos). Si no existen, se entrenan al primer uso (~1 min).
- **Hay que reentrenarlos cada mes** con los datos nuevos (basta con borrar el archivo `.joblib`). La sección 3.1 muestra por qué.

**Ejemplos** (miércoles 4-mar-2026, ocupación típica):

| Paciente | Faltan: p25 / mediana / p75 / p90 | Prob. de cama en 6 / 12 / 24 h |
|---|---|---|
| Mujer de 67 años, urgencias, recién llegada a las 9:00, sin historial | 11,5 / 32,5 / 60,2 / 91,8 h | 15 / 26 / 41 % |
| La misma, con 2 hospitalizaciones previas (la última: 60 h de espera, 200 h de estancia) | 13,7 / 36,9 / 60,7 / 84,7 h | 7 / 18 / 32 % |
| La misma sin historial, 6 h después: una etapa cerrada y una abierta | 14,4 / 31,7 / 59,7 / 102,9 h | 12 / 24 / 30 % |
| La misma sin historial, 6 h después: tres etapas abiertas | 3,9 / 6,8 / 24,3 / 48,5 h | 41 / 70 / 74 % |
| Niña de 8 años, urgencias, recién llegada a las 22:00 | 3,9 / 12,2 / 23,4 / 47,3 h | 34 / 50 / 77 % |

---

## 3. Qué tan bien funciona
**La prueba.** Todo se entrenó con llegadas de feb-2023 a jun-2025 y se probó con las 5.430 estancias de jul-2025 a 9-abr-2026, que ningún modelo había visto. Se mide la **mejora frente al rango general** (darle a todos los mismos percentiles), con la pérdida de cuantiles, que es el error estándar para percentiles. Los intervalos del 95 % salen de un bootstrap por semanas (1.000 repeticiones), porque los pacientes de una misma semana se parecen entre sí.

**Cómo mejora al sumar información** (lo que le falta a quien sigue esperando). Todos los modelos de esta tabla se entrenaron una sola vez, para compararlos en igualdad de condiciones. Reentrenado cada mes con más peso en lo reciente, el estimador final gana entre 0,5 y 0,8 puntos más (sección 3.1).

| Horas esperando | Tabla de perfiles | Modelo sin historial ni recorrido | + historial | **Estimador final** (IC 95 %) |
|---|---|---|---|---|
| 0 (al llegar) | 5,8 % | 6,7 % | 7,5 % | **7,6 % (6,7 a 8,5)** |
| 3 h | 6,2 % | 7,4 % | 8,2 % | **9,5 % (8,6 a 10,4)** |
| 6 h | 5,4 % | 7,0 % | 7,6 % | **9,2 % (8,4 a 10,1)** |
| 12 h | 3,8 % | 6,1 % | 6,5 % | **6,5 % (5,2 a 7,6)** |
| 24 h | 2,2 % | 5,0 % | 5,2 % | **5,2 % (3,5 a 6,7)** |
| 48 h | −0,8 % | 1,8 % | 1,8 % | **1,8 % (0,1 a 3,3)** |

**¿Aciertan los percentiles?** Lo ideal es que el 25 / 50 / 75 / 90 % de los casos nuevos quede por debajo de cada uno. Con el estimador final quedan 26,5 / 51,7 / 74,0 / 87,8 % al llegar y 25,9 / 49,3 / 71,9 / 87,2 % a las 6 h. El p90 queda algo corto (87–88 %) porque los peores casos siguen empeorando (`HALLAZGOS.md` 4.3); conviene leerlo como un piso.

**Cómo leerlo:**
- **Contra la tabla de perfiles, la ventaja es real en todos los momentos:** el intervalo de la diferencia nunca incluye el 0 (+1,3 a +2,6 puntos al llegar; +3,3 a +4,9 a las 6 h).
- **Contra el modelo de cuantiles al llegar,** que era el segundo mejor, la ventaja también es real: +0,8 a +1,8 puntos.
- **El historial suma desde la llegada, y el recorrido en las primeras horas** (probado a las 3 y a las 6 h). Desde las 12 h, la espera depende de otras cosas.
- **El techo es bajo:** el error de la mediana sigue siendo de unas 24 h al llegar.

**Agosto y septiembre de 2025.** Según el equipo, el HUN tuvo sobredemanda porque los hospitales cercanos fueron intervenidos por el Estado y quedó como la única opción de la zona. En los datos se ve poco: un 6–7 % más de llegadas que en los mismos meses de 2024, con ingresos a cama y espera mediana normales. Evaluado aparte, el estimador mejora 7,2 % en esos meses y 7,7 % en el resto. El resultado se sostiene.

### 3.1 ¿Sirve estimar el presente con datos de 2023 a 2025?
Código: `src/ventana_entrenamiento.py`. El hospital cambió en el periodo: la mediana de la espera se mantuvo, pero los peores casos empeoraron.

| Semestre de llegada | Mediana | p75 | p90 |
|---|---|---|---|
| 2023 (1.er semestre) | 19,8 h | 35,5 h | 61,2 h |
| 2024 (1.er semestre) | 18,4 h | 35,9 h | 69,1 h |
| 2025 (1.er semestre) | 20,6 h | 43,4 h | 78,8 h |
| 2026 (ene–9 abr) | 17,5 h | 46,6 h | 80,9 h |

Un modelo entrenado sobre todo con 2023 y 2024 aprende un hospital que ya no existe. Se probaron siete formas de entrenar, con la misma prueba (mejora frente al rango general):

| Forma de entrenar | Al llegar | 3 h | 6 h | 12 h | 24 h |
|---|---|---|---|---|---|
| Todo feb-2023 a jun-2025 (modelo fijo) | 7,6 % | 9,5 % | 9,2 % | 6,5 % | 5,2 % |
| Solo los últimos 12 meses | 7,7 % | 9,6 % | 9,5 % | 5,9 % | 4,7 % |
| Solo los últimos 6 meses | 7,0 % | 9,1 % | 8,4 % | 6,6 % | 5,5 % |
| Todo, con más peso en lo reciente (vida media de 6 meses) | 7,6 % | 9,6 % | 9,6 % | 6,6 % | 5,1 % |
| Reentrenado cada mes con todo lo anterior | 8,0 % | 10,0 % | 9,5 % | 6,9 % | 5,8 % |
| **Reentrenado cada mes, con más peso en lo reciente** | **8,1 %** | **10,3 %** | **9,8 %** | **7,0 %** | **5,9 %** |

En el reentrenamiento mensual, cada mes de la prueba se estimó con un modelo entrenado solo con lo que se sabía antes de empezar ese mes. Es decir, con las estancias que ya tenían cama y que llegaron al menos 14 días antes.

**Lectura:**
1. **Sí, entrenar con lo viejo era un problema, pero pequeño.** Reentrenar cada mes con más peso en lo reciente es lo mejor en todos los momentos: mejora entre 0,5 y 0,8 puntos frente al modelo fijo. La diferencia es real al llegar, a las 3 h y a las 6 h (el intervalo de la diferencia no incluye el 0: +0,1 a +1,0 % al llegar, +0,4 a +1,5 % a las 3 h). Además, el p90 acierta mejor: 88,9 % en vez de 87,8 % al llegar.
2. **Lo que más ayuda es incluir los meses nuevos.** Darle más peso a lo reciente sin reentrenar casi no cambia nada. Usar solo los últimos meses empeora, porque se pierden demasiados datos.
3. **Por eso el estimador final se entrena con todo el historial y más peso en lo reciente,** y debe reentrenarse cada mes.

**Edad y sexo corregidos.** Las cifras de esta sección ya usan la edad y el sexo de la persona real en las 14.126 estancias que trae `procedimientos_por_estancia.csv` (difieren de los nuestros en el 4 % de esas estancias en la edad y en el 2 % en el sexo). Con la corrección, los resultados prácticamente no cambian.

---

## 4. Qué haría falta para mejorarlo: la gravedad y el servicio al llegar
Código: `src/procedimientos_escenario.py` (procedimientos) y `src/triage_aproximado.py` (laboratorios). Se recalcularon todos los modelos que usan datos del paciente agregando lo que dicen los procedimientos (gravedad y servicio, sección 1.5) y el grupo de diagnóstico. Los modelos de cola y las dos series no usan datos del paciente, así que no cambian.

**Es un escenario, no un modelo para hoy:** los procedimientos no tienen fecha y el 88 % de los diagnósticos se registra tarde. La pregunta es «¿cuánto mejoraría si el hospital supiera esto al llegar?», y la respuesta es una cota optimista.

**Estimador final** (mejora frente al rango general):

| Horas esperando | Sin procedimientos | + gravedad | + servicio | + gravedad y servicio | + diagnóstico | **+ todo** |
|---|---|---|---|---|---|---|
| Al llegar | 7,6 % | 11,7 % | 11,5 % | 15,8 % | 12,5 % | **18,6 % (17,5 a 19,8)** |
| 3 h | 9,5 % | 12,0 % | 13,0 % | 15,0 % | 12,3 % | **16,9 %** |
| 6 h | 9,2 % | 11,2 % | 11,9 % | 13,6 % | 12,1 % | **15,3 %** |
| 12 h | 6,5 % | 9,1 % | 8,9 % | 11,2 % | 9,4 % | **12,3 %** |
| 24 h | 5,2 % | 8,1 % | 7,1 % | 9,6 % | 7,3 % | **9,4 %** |

**Los otros modelos con la misma información, al llegar:**
- **Modelo de cuantiles:** pasa de 6,4 % a 15,1 % con gravedad y servicio.
- **Tabla de perfiles:** pasa de 5,8 % a 8,5 % agregando el servicio como primera dimensión.

En todos los casos los percentiles siguen bien calibrados (al llegar, con todo: 25,4 / 50,2 / 72,8 % debajo de p25 / p50 / p75).

**Qué significa:**
1. **La gravedad y el servicio son la información que faltaba.** Juntos duplican la mejora al llegar (de 7,6 % a 15,8 %), y con el diagnóstico la llevan a 18,6 %. Ningún cambio de modelo se acercó a eso. El error de la mediana baja de 23,8 h a 21,1 h.
2. **Gravedad y servicio aportan cosas distintas,** porque juntos suman más que cada uno por separado. La gravedad dice quién recibe cama rápido (UCI); el servicio dice quién espera más (cirugía, urología, ortopedia).
3. **Un triage real debería servir todavía más,** porque se registra al llegar y no tiene el ruido de los procedimientos sin fecha.
4. **Los laboratorios tempranos casi no ayudan** (−0,1 a +0,7 puntos, `src/triage_aproximado.py`).

**Para la recomendación R1** (`docs/recomendaciones.md`): **registrar en la base el nivel de triage y el servicio que recibirá al paciente**, con su hora. Con esos dos datos, la estimación de la espera de cada paciente podría mejorar alrededor del doble.

**Otros pendientes:**
- **Corrección completa de edad y sexo:** con `procedimientos_por_estancia.csv` ya se corrigieron las 14.126 estancias que trae (55 %). Para el resto, pedir a Daniela `P02_persona_de_los_diagnosticos.csv` y `P03_persona_de_los_laboratorios.csv`.
- **Dashboard:** la estructura (`docs/estructura_dashboard.md`) no tiene página para A6. Como el dashboard está en Dash (Python), la página puede llamar a `estimar_tiempo_restante()`. Falta decidir con Daniela dónde va y si los modelos guardados pueden publicarse: contienen los cortes de los árboles, no filas de pacientes, pero salen de datos clínicos.

---

## 5. Alternativas probadas y descartadas

| Alternativa | Resultado | Por qué se descartó |
|---|---|---|
| Tabla de perfiles (`src/estimador_tiempos.py`): rango por bloque de 3 h, edad, tipo de visita y sexo | 5,8 % al llegar; −0,9 % a las 48 h | Peor que el estimador final en todos los momentos. Se conserva porque cubre otras medidas: probabilidad de hospitalizarse (9,6 %, AUC 0,62, bien calibrada), estancia en cama (mediana 69,5 h) y urgencias sin hospitalizar (Kaplan-Meier, mediana 11,2 h) |
| Modelo de cuantiles al llegar (M2) | 6,3 % al llegar | Solo estima al llegar y queda por debajo del estimador final |
| Cola en orden de llegada (M3b) | −17,9 % | El orden de llegada casi no predice el orden de cama (`CLAUDE.md` 6b) |
| Cola en orden aleatorio (M3a) | −0,3 % | La cola casi no cambia la espera |
| Espera en dos series: con la zona llena («sin cama») y con camas libres («demora del servicio») (`src/espera_dos_series.py`) | No mejora el pronóstico frente a una sola serie (~4,5 h de error semanal) | Es frágil: con las camas del HUN, la parte sin cama pasa del 8 % (2023) al 56 % (2025), pero con un 10 % más de camas queda en 5–10 %. Queda como lectura descriptiva |
| Laboratorios de las primeras 6 h como aproximación a la gravedad | −0,1 a +0,7 puntos | Casi no ayudan |
| Entrenar solo con los últimos 6 o 12 meses | 7,0 % y 7,7 % al llegar | Se pierden datos; es mejor usar todo el historial con más peso en lo reciente y reentrenar cada mes (sección 3.1) |
| Efecto del día o de la hora de llegada | 0,1 % a 2,3 % más allá del azar | La espera es individual |
| Hora del primer diagnóstico como momento de la decisión de hospitalizar | Casi siempre coincide con la llegada | No marca la decisión |

---

## 6. Límites (van junto al estimador)
- **Solo aplica a quien se va a hospitalizar.** Se entrena y se prueba solo con pacientes que al final recibieron cama. Al llegar a urgencias nadie sabe quién se hospitalizará (solo el ~9 % lo hace y el modelo de "¿se hospitaliza?" tiene AUC 0,62), así que la cifra "al llegar" vale para un paciente del que ya se sabe que se hospitalizará, no para cualquiera. Tampoco contempla a quien se va, se traslada o muere en urgencias.
- **No se puede reentrenar cada mes por ahora.** Los datos confiables terminan el 9-abr-2026 (`CLAUDE.md` 4.9). Consultado hoy, el modelo tiene más de 7 meses de atraso y la ocupación que usa por defecto es la típica de ene–abr 2026; la función lo avisa.
- **Varias decisiones se tomaron mirando la prueba** (el corte de 12 h, la vida media de 6 meses y la mejor de 7 formas de entrenar). No hay un periodo que nadie haya mirado, así que las cifras son algo optimistas; las diferencias de 0,5–0,8 puntos entre formas de entrenar pueden ser suerte.
- **Rango de pacientes parecidos, no una promesa para una persona.** Sirve para comunicar expectativas y planear, no para darle una hora a un paciente.
- **La espera termina en la asignación administrativa.** Mezcla la atención clínica en urgencias con la espera de cama, y no se pueden separar.
- **Cama o silla:** según el equipo, a muchos pacientes se les atiende en sillas aunque necesiten una cama, y no se sabe si eso se registra como estar en cama. La base no tiene columna de cama, silla, piso ni servicio (`CLAUDE.md` 4.8). Si se registra, la espera real hasta una cama sería más larga, la falta de camas mayor de lo que muestran los datos y la ocupación incluiría puestos que no son camas (lo que explicaría que pase de las 106 camas el 42 % de las horas de 2025).
- **El recorrido supone que el sistema registra cada etapa cuando empieza.** No se pudo comprobar. Si las etapas se cargan después, el recorrido no estaría disponible en tiempo real.
- **El recorrido podría ser una fuga del trámite de hospitalización:** si las etapas que se abren poco antes de la cama son parte del trámite, el modelo estaría viendo que ya se pidió la cama, no prediciéndola. Se mide en la sección 7.
- **La subida de asignaciones entre las 20 y las 23 h** puede ser la hora en que se digita en el sistema y no la del traslado; el modelo aprendería costumbres de registro.
- **La espera se recorta en 10 días (240 h).**
- **Edad y sexo de las estancias duplicadas:** se corrigieron con la persona real en las 14.126 estancias de `procedimientos_por_estancia.csv` (55 %). En el resto se conservó el registro con más información, que es el de la persona real en ~81–85 % de los casos (`CLAUDE.md` 4.10). El historial, que se busca por persona, tiene la misma limitación.
- **La ocupación hacia adelante se deja fija** en el último valor conocido.
- **Asociación, no causa.**

---

## 7. Revisión del 9-nov-2026: problemas encontrados en el código y qué se hizo
Al revisar el código aparecieron problemas que la versión del 7-nov no había medido. Se corrigió lo que se podía corregir sin datos y se preparó la prueba de lo demás en `src/revision_estimador.py`. **Las pruebas solo se corrieron con datos inventados para comprobar que el código funciona; falta correrlas con los datos reales** y anotar aquí los resultados.

| # | Problema | Qué se hizo | Estado |
|---|---|---|---|
| 1 | Solo aprende de pacientes que se hospitalizaron; la cifra "al llegar" no vale para cualquier paciente | Se dice en el resumen, en los límites, en el código y en cada respuesta de `estimar_tiempo_restante()` (campo `avisos`) | Hecho (no se puede corregir con estos datos: haría falta la hora de la orden de hospitalización) |
| 2 | No se puede reentrenar cada mes: los datos confiables terminan el 9-abr-2026 | La función avisa cuando la fecha consultada está a más de 60 días del fin del entrenamiento, y cuando usa la ocupación típica en vez de la real | Hecho |
| 3 | El modelo que se usaba (modelos en 0, 2, 4, 6 y 9 h; el más cercano por debajo) no era el que se probó (0, 3 y 6 h exactos) | Corregido en `estimador_tiempo_restante.py` v4: un modelo por cada hora de 0 a 11 h, así el que se consulta es el mismo que se prueba. La prueba 1 mide cada hora y lo compara con el esquema viejo | Corregido; **falta medir con datos reales** cuánto mejora |
| 4 | Posible fuga: las etapas que se abren justo antes de la cama pueden ser el trámite de hospitalización | Prueba 2: cuánto antes de la cama empieza la última etapa, y el modelo de 3 y 6 h reentrenado viendo el recorrido con 1, 2 y 3 h de retraso | **Falta correr con datos reales.** Si con 2 h de retraso el recorrido conserva menos de la mitad de su aporte, no presentarlo como predicción |
| 5 | Fuga del diagnóstico previo: se fechaba con el inicio del episodio anterior, y el 88 % de los diagnósticos se registra tarde | Corregido en `comparar_estimadores.py` v3: se fecha al fin del episodio anterior. Prueba 3 mide cuánto cambiaba | Corregido; **falta medir el efecto con datos reales** |
| 6 | La ocupación por zona usaba la edad sin corregir | Corregido en `comparar_estimadores.py` v3: usa la edad de la persona real cuando se conoce | Corregido; la prueba 5 cuenta cuántas estancias cambian |
| 7 | Decisiones tomadas mirando la prueba (corte de 12 h, vida media) | Prueba 4: el resultado por separado en jul–dic 2025 y en ene–9 abr 2026. No reemplaza a un periodo nuevo, que no existe | **Falta correr con datos reales** |

**Ojo con las cifras de las secciones 2 a 5:** son de la versión del 7-nov. Con las correcciones 5 y 6 pueden moverse un poco; hay que volver a correr `src/comparar_estimadores.py` y `src/ventana_entrenamiento.py` y actualizarlas. El modelo guardado pasa a la versión 6 y se vuelve a entrenar solo en la primera consulta.

---

## 8. Cómo reproducirlo
Los datos viven fuera del proyecto. Se indican con tres variables (en Bash). `HUN_CRUDOS` es la carpeta con `visit_detail.csv` y `procedimientos_por_estancia.csv`; este último corrige la edad y el sexo y alimenta los escenarios.
```bash
export HUN_PROCESADOS="D:/Descargas D/Datos/procesados" HUN_TABLAS="D:/Descargas D/Datos/procesados/tablas" HUN_CRUDOS="D:/Descargas D/Datos"
```
1. **Tabla de episodios:** `src/analisis_etapas.py` y `src/preparar_variables.py`, con los CSV de la base en `datos/crudos/`. Copiarlos ahí solo mientras corren y mover luego `datos/procesados/` a la carpeta externa.
2. **Construcción y prueba del estimador:** `python3 src/comparar_estimadores.py` (~1,5 min). Escribe `comparacion_estimadores_*.csv` en `HUN_TABLAS` y `resultados/graficos/comparacion_estimadores.png`. Las formas de entrenar (sección 3.1): `python3 src/ventana_entrenamiento.py` (~10 min).
3. **Escenarios de gravedad y servicio:** `python3 src/procedimientos_escenario.py` (~4 min; necesita `procedimientos_por_estancia.csv` en `HUN_CRUDOS`) y `python3 src/triage_aproximado.py` (laboratorios).
4. **Alternativas:** `python3 src/estimador_tiempos.py` (tabla de perfiles) y `python3 src/espera_dos_series.py` (dos series).
5. **Revisión del 9-nov (sección 7):** `python3 src/revision_estimador.py` (~15–25 min; `RAPIDO=1` omite la prueba hora por hora). Escribe `revision_estimador_*.csv` y `revision_estimador_resumen.txt` en `HUN_TABLAS`.
6. **Consulta:** `python3 src/estimador_tiempo_restante.py 67 Mujer Urgencias 6 "2026-03-04 15:00"`. Sin argumentos muestra los ejemplos de la sección 2.
