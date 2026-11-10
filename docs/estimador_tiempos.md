# A6 · Estimación del tiempo de espera de cama (7 y 8-nov-2026; revisado e integrado el 9-nov, sección 7)

**Qué pide el instructivo (componente 3):** «modelos analíticos o predictivos que permitan estimar tiempos de atención». La pregunta concreta: **cuando un paciente espera cama, ¿cuánto le falta?**

## Resumen
1. **La espera es individual.** Pacientes que llegan el mismo día o a la misma hora no esperan parecido. Por eso la ocupación del hospital o la cola casi no ayudan a estimarla, y lo que sirve es información de cada paciente.
2. **El estimador es un modelo de tiempo restante.** Para un paciente que espera cama (**es decir, que ya tiene orden de hospitalización**: se entrenó solo con quienes recibieron cama, ver sección 7), da el rango de lo que le falta (percentiles 25, 50, 75 y 90) y la probabilidad de recibir cama en 6, 12 y 24 horas, y se recalcula a medida que pasa la espera. Usa el paciente, la hora del reloj, la ocupación, su historial de hospitalizaciones, su recorrido en urgencias y, desde las 6 h de espera, las banderas de sus laboratorios de las primeras 6 h (sección 3.3), todo conocido en el momento. Se consulta con `estimar_tiempo_restante()`.
3. **Funciona mejor que todo lo demás que probamos, pero el techo es bajo.** Reentrenado cada mes con más peso en lo reciente, que es como se debe usar porque el hospital cambió, mejora el rango 9,2 % al llegar y 11,0–11,3 % entre las 3 y las 6 horas de espera (cifras del 9-nov, con las correcciones de la revisión), frente a darle a todos el mismo rango. Sus percentiles aciertan en datos nuevos, y le gana con margen comprobado a las otras cinco alternativas.
4. **Lo que más decide cuándo llega la cama es la hora del reloj:** entre las 6 y las 12 h casi nadie recibe cama; las camas se asignan entre las 15 y las 17 h y entre las 20 y las 23 h.
5. **Pensado para usarse cada día** (sección 3.2):
   - **Para el paciente:** responde en ventanas del día («esta tarde», «esta noche», «mañana en la tarde») con probabilidades que dicen la verdad.
   - **Para la reunión de camas:** dice cuántos de los que esperan tendrán cama en 12 o 24 h, con un error en el mínimo que permite el azar y un rango que acierta el 87–88 % de los días.
   - **Para actuar antes:** a las 12 h de espera avisa quién seguirá sin cama a las 48 h.
   - **En el dashboard:** tiene su página, la 3.7 del menú (`dashboard/pages/estimador.py`).
6. **Lo que de verdad lo mejoraría es saber, al llegar, la gravedad y el servicio.** Los procedimientos de cada estancia muestran que el hospital da cama rápido a los graves (UCI: mediana 2,7 h) y hace esperar más a cirugía, urología y ortopedia (30–38 h). Si esa información se conociera al llegar, la mejora pasaría de 8,4 % a 16,9 %, y a 20,0 % sumando el diagnóstico (comparando modelos entrenados una sola vez). Es más que cualquier cambio de modelo, y es el argumento para registrar el triage y el servicio en la base.

---

## 1. Qué decide la espera: lo que encontramos en los datos
Se usan las estancias únicas del periodo confiable, del 1-feb-2023 al 9-abr-2026 (22.819 estancias). La espera va de la llegada a la asignación de cama, como confirmó el HUN (`CLAUDE.md` 4.7): mediana 18,5 h, p25 6,4 h, p75 37,8 h y p90 72,9 h (`HALLAZGOS.md` 4.2).

**1.1 La espera es individual, no del momento.** Si la espera dependiera del estado del hospital, los pacientes que llegan juntos esperarían parecido. No pasa: el día de llegada explica un 0,1 % de la espera más allá de lo que daría el azar, y el día con el bloque de 3 horas, un 2,3 %. Por eso la ocupación y la cola casi no ayudan, como también encontró `docs/capacidad_efectiva.md`.

**1.2 La hora del reloj manda.** Para un paciente que sigue esperando, la probabilidad de recibir cama en la hora siguiente es:
- ~1 % entre las 6 y las 12 h;
- 6–9 % entre las 15 y las 17 h;
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

**Qué no usa, y por qué.** No usa la cola de pacientes esperando cama: contarla exige saber quién se hospitalizará, y además empeora la estimación (al llegar, 6,2 % con cola frente a 7,0 % sin ella).

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
- También devuelve `ventanas`: la probabilidad de recibir cama en cada bloque del día (madrugada 0–7 h, mañana 7–14 h, tarde 14–19 h, noche 19–24 h) de hoy, mañana y pasado mañana, y después, con la acumulada. También devuelve `ventana_mas_probable` (entre las que tienen fecha).
- **Página del dashboard:** la 3.7 del menú (`dashboard/pages/estimador.py`, dentro de `dashboard/app.py`). Se describe al paciente y muestra las ventanas, el rango, los avisos y el resumen de qué tan bien funciona.

**Ejemplos** (miércoles 4-mar-2026, ocupación típica):

| Paciente | Faltan: p25 / mediana / p75 / p90 | Prob. de cama en 6 / 12 / 24 h |
|---|---|---|
| Mujer de 67 años, urgencias, recién llegada a las 9:00, sin historial | 11,8 / 34,4 / 60,6 / 104,2 h | 14 / 25 / 39 % |
| La misma, con 2 hospitalizaciones previas (la última: 60 h de espera, 200 h de estancia) | 17,5 / 53,9 / 79,9 / 131,7 h | 7 / 16 / 27 % |
| La misma sin historial, 6 h después: una etapa cerrada y una abierta | 15,7 / 31,7 / 59,3 / 102,9 h | 11 / 23 / 30 % |
| La misma sin historial, 6 h después: tres etapas abiertas | 5,8 / 11,6 / 32,3 / 71,7 h | 27 / 50 / 58 % |
| Niña de 8 años, urgencias, recién llegada a las 22:00 | 4,4 / 12,6 / 23,5 / 47,4 h | 33 / 48 / 76 % |

---

## 3. Qué tan bien funciona
**La prueba.** Todo se entrenó con llegadas de feb-2023 a jun-2025 y se probó con las 5.430 estancias de jul-2025 a 9-abr-2026, que ningún modelo había visto. Se mide la **mejora frente al rango general** (darle a todos los mismos percentiles), con la pérdida de cuantiles, que es el error estándar para percentiles. Los intervalos del 95 % salen de un bootstrap por semanas (1.000 repeticiones), porque los pacientes de una misma semana se parecen entre sí.

**Cómo mejora al sumar información** (lo que le falta a quien sigue esperando). Todos los modelos de esta tabla se entrenaron una sola vez, para compararlos en igualdad de condiciones. Reentrenado cada mes con más peso en lo reciente, el estimador final gana hasta 1,3 puntos más en las primeras 6 h (sección 3.1). Desde las 6 h incluye las banderas de laboratorio (sección 3.3).

| Horas esperando | Tabla de perfiles | Modelo sin historial ni recorrido | + historial | **Estimador final** (IC 95 %) |
|---|---|---|---|---|
| 0 (al llegar) | 6,4 % | 7,0 % | 8,0 % | **8,4 % (7,5 a 9,3)** |
| 3 h | 7,1 % | 8,0 % | 8,7 % | **10,4 % (9,4 a 11,3)** |
| 6 h | 6,2 % | 7,7 % | 8,3 % | **10,6 % (9,6 a 11,6)** |
| 12 h | 4,1 % | 6,7 % | 7,1 % | **8,0 % (6,4 a 9,5)** |
| 24 h | 2,6 % | 4,9 % | 5,3 % | **6,1 % (4,5 a 7,8)** |
| 48 h | −1,3 % | 2,0 % | 1,5 % | **2,9 % (0,9 a 4,7)** |

**¿Aciertan los percentiles?** Lo ideal es que el 25 / 50 / 75 / 90 % de los casos nuevos quede por debajo de cada uno. Con el estimador final quedan 26,5 / 51,8 / 74,2 / 87,7 % al llegar y 25,5 / 49,4 / 72,1 / 87,2 % a las 6 h. El p90 queda algo corto (87–88 %) porque los peores casos siguen empeorando (`HALLAZGOS.md` 4.3); conviene leerlo como un piso.

**Cómo leerlo:**
- **Contra la tabla de perfiles, la ventaja es real en todos los momentos:** el intervalo de la diferencia nunca incluye el 0 (+1,4 a +2,8 puntos al llegar; +3,0 a +4,7 a las 6 h).
- **Contra el modelo de cuantiles al llegar,** que era el segundo mejor, la ventaja también es real: +0,8 a +2,1 puntos.
- **El historial suma desde la llegada, y el recorrido en las primeras horas** (probado a las 3 y a las 6 h). Desde las 6 h suman las banderas de laboratorio (+0,9 puntos a las 6 h, +0,9 a las 12 h, +0,8 a las 24 h); a las 48 h la mejora es pequeña (2,9 %), aunque ya no incluye el 0.
- **El techo es bajo:** el error de la mediana sigue siendo de unas 24 h al llegar.

**Agosto y septiembre de 2025.** Según el equipo, el HUN tuvo sobredemanda porque los hospitales cercanos fueron intervenidos por el Estado y quedó como la única opción de la zona. En los datos se ve poco: un 6–7 % más de llegadas que en los mismos meses de 2024, con ingresos a cama y espera mediana normales. Evaluado aparte, el estimador mejora 8,4 % en esos meses y 8,4 % en el resto. El resultado se sostiene.

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
| Todo feb-2023 a jun-2025 (modelo fijo) | 8,6 % | 10,5 % | 9,6 % | 7,3 % | 5,4 % |
| Solo los últimos 12 meses | 8,7 % | 10,4 % | 9,9 % | 6,4 % | 4,7 % |
| Solo los últimos 6 meses | 8,2 % | 10,1 % | 9,5 % | 7,2 % | 5,7 % |
| Todo, con más peso en lo reciente (vida media de 6 meses) | 8,9 % | 10,7 % | 10,0 % | 7,3 % | 5,3 % |
| Reentrenado cada mes con todo lo anterior | 9,0 % | 10,9 % | 10,3 % | 7,5 % | 5,7 % |
| **Reentrenado cada mes, con más peso en lo reciente** | **9,2 %** | **11,3 %** | **11,0 %** | **7,5 %** | **6,0 %** |

En el reentrenamiento mensual, cada mes de la prueba se estimó con un modelo entrenado solo con lo que se sabía antes de empezar ese mes. Es decir, con las estancias que ya tenían cama y que llegaron al menos 14 días antes.

**Lectura:**
1. **Sí, entrenar con lo viejo era un problema, pero pequeño.** Reentrenar cada mes con más peso en lo reciente es lo mejor en todos los momentos: mejora entre 0,5 y 1,1 puntos frente al modelo fijo. La diferencia es real a las 3, 6 y 24 h (el intervalo de la diferencia no incluye el 0: +0,3 a +1,6 % a las 3 h, +0,6 a +2,0 % a las 6 h) y queda en el límite al llegar (+0,0 a +1,1 %). Además, el p90 acierta mejor: 89,0 % en vez de 87,7 % al llegar.
2. **Lo que más ayuda es incluir los meses nuevos.** Darle más peso a lo reciente sin reentrenar casi no cambia nada. Usar solo los últimos meses empeora, porque se pierden demasiados datos.
3. **Por eso el estimador final se entrena con todo el historial y más peso en lo reciente,** y debe reentrenarse cada mes.

**Edad y sexo de la persona real (8-nov).** Todas las cifras de este documento usan la tabla de episodios rehecha con `P02_persona_de_los_diagnosticos.csv` y `P03_persona_de_los_laboratorios.csv` (lote 4 de `src/auditoria_bd.py`, `CLAUDE.md` 4.10): la persona real se identificó en 16.384 estancias y el registro conservado es el suyo en el 99,6 % de ellas. Frente a la versión anterior, el 5,4 % de las estancias cambió de grupo de edad y el 3,2 % de sexo. La espera no cambia (mediana 18,5 h), pero **el estimador mejora**: al llegar pasa de 7,6 % a 8,4 % (modelo fijo) y a las 3 h de 9,5 % a 10,4 %. Tener los datos del paciente bien corregidos importa.

---

### 3.2 ¿Qué tan útil es? Tres salidas para el día a día
Código: `src/utilidad_estimador.py`. La precisión para un paciente tiene un techo (sección 3), pero la utilidad depende de responder las preguntas que el hospital necesita resolver cada día. Las tres salidas se probaron igual que todo lo demás: modelos entrenados hasta jun-2025 y prueba con jul-2025 a 9-abr-2026.

**1. Para el paciente: ¿en qué momento del día recibirá cama?** Se responde en ventanas, porque las camas se asignan en bloques del día.

| | Al llegar | A las 6 h de espera |
|---|---|---|
| La ventana real está entre las 2 más probables | **45,5 %** (sin modelo: 36,9 %) | **44,0 %** (sin modelo: 34,3 %) |
| La ventana con fecha más probable acierta | 26,2 % (sin modelo: 21,6 %) | 20,7 % (sin modelo: 17,4 %) |
| Error de las probabilidades (Brier, menor es mejor) | 0,833 (sin modelo: 0,870; −4,2 %) | 0,835 (sin modelo: 0,875; −4,6 %) |

«Sin modelo» es la distribución histórica de la ventana según la hora del reloj. Hay 12 ventanas posibles, así que acertar la exacta es difícil. Lo que más importa para comunicar es que las probabilidades **dicen la verdad**: cuando el estimador dice 7 %, pasa el 7 %; cuando dice 12 %, pasa el 11 %; cuando dice 24 %, pasa el 28 %. En las probabilidades más altas queda algo corto: dice 34 % y pasa el 42 %. El 14 % de los pacientes recibe la cama después de 3 días.

**2. Para la reunión de camas: de los que esperan ahora, ¿cuántos tendrán cama en 12 o 24 horas?** Cada día a las 7:00 y a las 13:00, el estimador suma las probabilidades de los pacientes en espera.

| Momento y plazo | En espera | Reciben cama | Error por día | Mínimo posible por azar | Sin modelo | Rango del 80 % acierta | Error por semana |
|---|---|---|---|---|---|---|---|
| 7:00, en 12 h | 23,6 | 5,1 | 1,8 | 1,9 | 2,1 | 87,9 % | 18,1 % |
| 7:00, en 24 h | 23,6 | 10,5 | 2,6 | 2,6 | 2,8 | 87,2 % | 11,6 % |
| 13:00, en 12 h | 28,9 | 11,6 | 2,6 | 2,7 | 2,7 | 88,3 % | 10,3 % |
| 13:00, en 24 h | 28,9 | 12,9 | 2,7 | 2,9 | 2,8 | 87,9 % | 9,3 % |

**El error está en el mínimo que permite el azar.** Cuántos pacientes reciben cama en unas horas es un conteo pequeño con ruido inevitable, como contar caras al lanzar monedas. El «mínimo posible» es el error que tendría hasta un estimador perfecto (distribución de Poisson), y el estimador lo alcanza. Por eso la referencia histórica, que es la cantidad en espera por la fracción que suele recibir cama a esa hora, queda casi igual. Lo útil es el **rango**: con la distribución de Poisson del estimado, el rango del 80 % acierta el 87–88 % de los días. Una banda que supusiera pacientes independientes acertaba solo el 64–73 %, porque las camas se asignan en tandas. Por semana el error baja a 9–18 %, pero el rango semanal queda algo angosto: acierta el 67–80 % de las semanas en vez del 80 %, porque hay semanas enteras más rápidas o más lentas.

**3. Para actuar antes: ¿quién seguirá sin cama a las 48 h?** A las 12 h de espera, la probabilidad de seguir sin cama a las 48 h (AUC 0,68):

| Regla | Alertas por día | Acierta | Detecta |
|---|---|---|---|
| Sin modelo: todos los que llevan 12 h | 11,1 | 38,6 % | 100 % |
| Probabilidad ≥ 30 % | 7,0 | 47,9 % | 78,3 % |
| **Probabilidad ≥ 40 %** | **4,1** | **55,3 %** | 53,5 % |
| Probabilidad ≥ 50 % | 1,5 | 58,9 % | 20,3 % |
| Sin modelo: todos los que llevan 24 h (12 h más tarde) | 8,1 | 52,9 % | 100 % |

**Lectura:** con un corte de 40 %, el estimador da 4,1 alertas diarias a las 12 h y acierta algo más que esperar a las 24 h y alertar a todos (55 % frente a 53 %), pero con **12 horas más de margen** y la mitad de alertas. A cambio, detecta solo a la mitad (54 %) de los que terminarán esperando más de 48 h. Complementa la alerta C de `src/alertas.py` (a las 48 h de espera), que avisa más tarde y acierta más.

**4. En el dashboard.** La página 3.7 del menú (`dashboard/pages/estimador.py`) reúne todo. Se describe al paciente (edad, sexo, tipo de visita, horas de espera y, si se sabe, su hospitalización anterior, sus etapas en urgencias y sus laboratorios de las primeras 6 h) y muestra:
- la ventana más probable y el gráfico de ventanas con la acumulada;
- lo que le falta (mediana y rango) y la probabilidad de cama en 6, 12 y 24 h;
- el resumen de qué tan bien funciona, leído de las tablas agregadas.

No usa datos de pacientes. El censo de pacientes en espera necesitaría los datos del hospital en tiempo real, que no tenemos.

### 3.3 Banderas de laboratorio de las primeras 6 h (8-nov) y las dos maneras de entrenar
Código: `src/comparar_estimadores.py` v3 (`laboratorios()`, `cols_finales()`); datos: `sev_hemograma_6h_*.csv` y `sev_quimica_6h_*.csv` (`sql/severidad_labs_6h.sql`, de Daniela).
Con los valores de las primeras 6 h de la visita se arma una bandera por cada valor anormal, con los cortes de `src/severidad_labs.py`: leucocitos > 12 o < 4, hemoglobina < 10, creatinina > 1,5, BUN > 40, lactato > 2,2, potasio > 5,5, sodio < 130 o > 150, troponina > 1,0 y PCR > 50. Se usan **por separado**, porque sumarlas cancela efectos opuestos (`docs/espera_con_labs_y_severidad.md`). Las banderas solo entran desde las 6 h de espera, porque antes el resultado no se conoce. El 40 % de las estancias tiene algún valor; las demás quedan con todas las banderas en 0 y `con_laboratorio_6h = 0`. Con los valores numéricos en vez de las banderas el resultado es casi igual; se eligen las banderas porque se explican solas.

**Manera 1: validación honesta** (entrenar hasta jun-2025 y probar con jul-2025 a 9-abr-2026). Mejora frente al rango general:

| Horas esperando | Sin banderas, modelo fijo | **Con banderas, modelo fijo** | Sin banderas, reentreno mensual | **Con banderas, reentreno mensual** |
|---|---|---|---|---|
| 6 h | 9,7 % | **10,6 % (9,6 a 11,6)** | 10,8 % | **11,7 % (10,7 a 12,8)** |
| 12 h | 7,1 % | **8,0 % (6,4 a 9,5)** | 7,6 % | **7,9 % (6,3 a 9,5)** |
| 24 h | 5,3 % | **6,1 % (4,5 a 7,8)** | 6,3 % | **6,3 % (4,4 a 8,0)** |
| 48 h | 1,5 % | **2,9 % (0,9 a 4,7)** | — | — |

Antes de las 6 h nada cambia (la tabla de arriba es de la corrida del 8-nov; la comparación principal de la sección 3.1 se rehízo el 9-nov). En la prueba con el modelo fijo, la diferencia por las banderas es real: +1,1 puntos a las 6 h (IC 0,7 a 1,5), +1,1 a las 12 h (0,5 a 1,8) y +1,1 a las 24 h (0,4 a 1,9). Los percentiles siguen calibrados (87–88 % debajo del p90). Con el reentreno mensual, la ganancia se concentra en las 6 h; a las 12 y 24 h el reentreno ya no le suma al modelo fijo (diferencia −0,7 a +0,6 y −0,9 a +1,1).

**Manera 2: el modelo que se consulta, con todos los datos** (feb-2023 a 9-abr-2026, con más peso en lo reciente, vida media de 6 meses). Es el que guarda `src/estimador_tiempo_restante.py` (versión 8 del paquete, en `HUN_PROCESADOS/modelos/`, fuera del repositorio). **No se puede calificar con datos que no vio**, porque usa todos los meses y no queda nada para probar. Su precisión esperada es la de la columna «reentreno mensual» de la manera 1, que imita justamente esto: cada mes se entrena con todo lo conocido hasta ese momento, con más peso en lo reciente. Por eso se recomienda volver a entrenarlo cada mes (borrar el `.joblib`).

**Cómo se consulta:** `estimar_tiempo_restante(..., laboratorios_6h={"troponina_max": 2.3, "pcr_max": 80})`. Los valores que falten se toman como normales; sin el argumento se supone que no le tomaron laboratorio.

## 4. Qué haría falta para mejorarlo: la gravedad y el servicio al llegar
Código: `src/procedimientos_escenario.py` (procedimientos) y `src/triage_aproximado.py` (laboratorios). Se recalcularon todos los modelos que usan datos del paciente agregando lo que dicen los procedimientos (gravedad y servicio, sección 1.5) y el grupo de diagnóstico. Los modelos de cola y las dos series no usan datos del paciente, así que no cambian.

**Es un escenario, no un modelo para hoy:** los procedimientos no tienen fecha y el 88 % de los diagnósticos se registra tarde. La pregunta es «¿cuánto mejoraría si el hospital supiera esto al llegar?», y la respuesta es una cota optimista.

**Estimador final** (mejora frente al rango general):

| Horas esperando | Sin procedimientos | + gravedad | + servicio | + gravedad y servicio | + diagnóstico | **+ todo** |
|---|---|---|---|---|---|---|
| Al llegar | 8,4 % | 12,8 % | 12,7 % | 16,9 % | 14,1 % | **20,0 % (18,8 a 21,1)** |
| 3 h | 10,4 % | 12,9 % | 13,7 % | 15,9 % | 13,4 % | **17,9 %** |
| 6 h | 9,7 % | 11,9 % | 12,8 % | 14,5 % | 12,6 % | **16,1 %** |
| 12 h | 7,1 % | 9,8 % | 10,2 % | 12,1 % | 9,8 % | **14,5 %** |
| 24 h | 5,3 % | 8,5 % | 7,5 % | 9,9 % | 7,1 % | **11,5 %** |

**Los otros modelos con la misma información, al llegar:**
- **Modelo de cuantiles:** pasa de 7,1 % a 16,1 % con gravedad y servicio.
- **Tabla de perfiles:** pasa de 6,4 % a 9,1 % agregando el servicio como primera dimensión.

En todos los casos los percentiles siguen bien calibrados (al llegar, con todo: 24,8 / 49,7 / 72,9 % debajo de p25 / p50 / p75).

**Qué significa:**
1. **La gravedad y el servicio son la información que faltaba.** Juntos duplican la mejora al llegar (de 8,4 % a 16,9 %), y con el diagnóstico la llevan a 20,0 %. Ningún cambio de modelo se acercó a eso. El error de la mediana baja de 23,7 h a 20,8 h.
2. **Gravedad y servicio aportan cosas distintas,** porque juntos suman más que cada uno por separado. La gravedad dice quién recibe cama rápido (UCI); el servicio dice quién espera más (cirugía, urología, ortopedia).
3. **Un triage real debería servir todavía más,** porque se registra al llegar y no tiene el ruido de los procedimientos sin fecha.
4. **El número de laboratorios tempranos casi no ayuda** (−0,3 a +0,4 puntos, `src/triage_aproximado.py`), pero **sus valores sí**: las banderas de valores anormales de Daniela suman ~1 punto desde las 6 h y ya están en el estimador (sección 3.3). Esta tabla de escenarios se calculó antes de sumarlas (columna «Sin procedimientos» = estimador sin banderas).

**Para la recomendación R1** (`docs/recomendaciones.md`): **registrar en la base el nivel de triage y el servicio que recibirá al paciente**, con su hora. Con esos dos datos, la estimación de la espera de cada paciente podría mejorar alrededor del doble.

**Otros pendientes:**
- **Datos con hora durante la espera:** pedir a Daniela los laboratorios y los diagnósticos registrados antes de la cama, con su hora, para usarlos como señales en tiempo real.
- **Dashboard:** integrada al menú el 9-nov como página 3.7 (`dashboard/pages/estimador.py`). Falta decidir con Daniela si los modelos guardados pueden publicarse: contienen los cortes de los árboles, no filas de pacientes, pero salen de datos clínicos. Mientras no se publiquen, la página muestra un aviso en el dashboard publicado.

---

## 5. Alternativas probadas y descartadas

| Alternativa | Resultado | Por qué se descartó |
|---|---|---|
| Tabla de perfiles (`src/estimador_tiempos.py`): rango por bloque de 3 h, edad, tipo de visita y sexo | 6,4 % al llegar; −1,3 % a las 48 h | Peor que el estimador final en todos los momentos. Se conserva porque cubre otras medidas: probabilidad de hospitalizarse (9,6 %, AUC 0,62, bien calibrada), estancia en cama (mediana 69,5 h) y urgencias sin hospitalizar (Kaplan-Meier, mediana 11,2 h) |
| Modelo de cuantiles al llegar (M2) | 7,1 % al llegar | Solo estima al llegar y queda por debajo del estimador final |
| Cola en orden de llegada (M3b) | −17,2 % | El orden de llegada casi no predice el orden de cama (`CLAUDE.md` 6b) |
| Cola en orden aleatorio (M3a) | 0,4 % | La cola casi no cambia la espera |
| Espera en dos series: con la zona llena («sin cama») y con camas libres («demora del servicio») (`src/espera_dos_series.py`) | No mejora el pronóstico frente a una sola serie (~4,5 h de error semanal) | Es frágil: con las camas del HUN, la parte sin cama pasa del 7 % (2023) al 61 % (2025), pero con un 10 % más de camas queda en 4–9 %. Queda como lectura descriptiva |
| Visitas previas a urgencias, congestión de urgencias al llegar y calendario (festivo, día no hábil, mes) (`src/variables_descartadas.py`) | De −0,5 a +0,5 puntos sobre el estimador final; ningún intervalo excluye el 0 | No aportan: el estimador ya captura lo útil de estos datos |
| Hora del primer diagnóstico como señal en tiempo real | Coincide con la llegada en la mitad de los casos y en el 10 % es semanas antes (visitas copia) | No marca un momento real; se descartó sin probar |
| Laboratorios de las primeras 6 h como aproximación a la gravedad | −0,3 a +0,4 puntos | Casi no ayudan |
| **Estimador construido desde cero** (`src/estimador_desde_cero.py`): LightGBM por cuantiles, XGBoost con tiempo de falla acelerado (AFT) y su combinación, con la edad en años, todas las variables conocidas en el momento y ajustes elegidos con su propia validación (ene–jun 2025) | Al llegar: 8,6 % (LightGBM), 6,3 % (AFT) y 8,3 % (combinación), frente a 8,6 % del actual entrenado igual; a las 6 h, 9,9–10,4 % frente a 9,9 %; a las 12 h la combinación gana 1,3 puntos (IC +0,1 a +2,5) | Un camino independiente llega al mismo techo: el límite está en los datos, no en el modelo. La pequeña ganancia a las 12 h es una sola diferencia entre varias probadas y apenas excluye el 0; no se integra |
| Mejorar la mediana con un modelo más grande, un modelo dedicado solo a la mediana o la combinación de ambos | El error promedio no se mueve (23,7 h al llegar); el modelo dedicado baja el error típico de 14,5 a 13,5 h | Ganancia pequeña y su mediana no siempre cuadra con los percentiles del estimador; el error de ~24 h es la dispersión real de la espera sin datos de gravedad ni servicio |
| Entrenar sin el 10 % de esperas más largas (más de 69 h) | El error típico baja de 14,5 a 12,4 h, pero la mejora real cae de 8,6 % a 1,4 %, el p90 acierta en el 78 % en vez del 89 % y a los que esperan mucho les promete ~20 h cuando esperan ~100 h | Peligroso: esconde justo los casos que más importan (el 83 % de las horas de espera viene de esperas de más de 24 h) |
| Entrenar solo con los últimos 6 o 12 meses | 8,4 % y 8,3 % al llegar, y peor en las demás horas | Se pierden datos; es mejor usar todo el historial con más peso en lo reciente y reentrenar cada mes (sección 3.1) |
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
- **Edad y sexo de las estancias duplicadas:** corregidos con la persona real (P02 y P03); en las pocas estancias duplicadas donde no se pudo identificar, se conserva el registro con más información (`CLAUDE.md` 4.10).
- **El recorrido podría ser una fuga del trámite de hospitalización:** si las etapas que se abren poco antes de la cama son parte del trámite, el modelo estaría viendo que ya se pidió la cama, no prediciéndola. Se mide en la sección 7.
- **La subida de asignaciones entre las 20 y las 23 h** puede ser la hora en que se digita en el sistema y no la del traslado; el modelo aprendería costumbres de registro.
- **La espera se recorta en 10 días (240 h).**

- **La ocupación hacia adelante se deja fija** en el último valor conocido.
- **Asociación, no causa.**

---

## 7. Revisión del 9-nov-2026: problemas encontrados en el código y qué se hizo
Al revisar el código aparecieron problemas que la versión del 7-nov no había medido. Se corrigió lo que se podía y se midió con los datos reales (`src/revision_estimador.py`, 9-nov, jul-2025 a 9-abr-2026, ramas `a6-utilidad` y `a6-revision` integradas).

| # | Problema | Qué se hizo | Resultado con datos reales |
|---|---|---|---|
| 1 | Solo aprende de pacientes que se hospitalizaron; la cifra "al llegar" no vale para cualquier paciente | Se dice en el resumen, en los límites, en el código y en cada respuesta de `estimar_tiempo_restante()` (campo `avisos`) | No se puede corregir con estos datos: haría falta la hora de la orden de hospitalización |
| 2 | No se puede reentrenar cada mes: los datos confiables terminan el 9-abr-2026 | La función avisa cuando la fecha consultada está a más de 60 días del fin del entrenamiento y cuando usa la ocupación típica | Hecho |
| 3 | El modelo que se consultaba (0, 2, 4, 6 y 9 h; el más cercano por debajo) no era el que se probó | Un modelo por cada hora de 0 a 11 h | Mejora real pero pequeña: claramente mejor solo a la 1 h (+0,7 puntos) y a las 3 h (+0,4); en las demás horas, igual o dentro del azar |
| 4 | Posible fuga: las etapas que se abren justo antes de la cama pueden ser el trámite de hospitalización | Prueba 2: el modelo reentrenado viendo el recorrido con 0, 1, 2 y 3 h de retraso | **En parte sí.** El recorrido aporta +1,4 puntos sin retraso; con 2 h de retraso conserva el 43 % de ese aporte a las 3 h y el 57 % a las 6 h. A las 3 h está por debajo de la mitad: ese aporte es sobre todo trámite y **no debe venderse como predicción**. Sin el recorrido el modelo sigue mejorando 9,2 % a las 3 h y 8,4 % a las 6 h |
| 5 | Fuga del diagnóstico previo: se fechaba con el inicio del episodio anterior | Se fecha al fin del episodio anterior | Cambia en el 1,2 % de las estancias; la mejora al llegar pasa de 8,4 % (con fuga) a 8,6 %: la fuga era despreciable |
| 6 | La ocupación por zona usaba la edad sin corregir | Usa la edad de la persona real | Ya no cambia ninguna estancia (0,00 %): P02 y P03 dejaron la edad corregida en todas |
| 7 | Decisiones tomadas mirando la prueba (corte de 12 h, vida media) | Estabilidad por periodo y, para el corte y el p90, un periodo de validación aparte (7.1) | Jul-dic 2025 y ene-9 abr 2026 dan resultados parecidos (al llegar 8,7 % y 8,5 %; a las 3 h 10,9 % y 9,7 %); el p90 cubre 86–88 % en los dos |

### 7.1 Corte de 12 h y percentil 90, con un periodo de validación (`src/calibracion_y_corte.py`)
Entrenamiento hasta dic-2024, validación ene–jun 2025 y prueba jul-2025 a 9-abr-2026, que no se usa para decidir.
- **Corte.** El modelo por momento (con el recorrido) le gana al modelo único en la validación hasta las 24 h (ventaja +3,5 %, IC95 +0,6 a +6,4) y deja de ganarle claramente a las 36 h (+1,0 %, IC95 −0,7 a +2,8). Por la regla (el corte más bajo sin ventaja clara) saldría 36 h, no 12. Con 36 h, en la prueba la mejora sube solo 0,4 puntos a las 12 h (7,3 % a 7,7 %) y 0,1 a las 24 h, y haría falta guardar 37 modelos en vez de 13. **Se deja el corte en 12 h por costo**, y queda dicho que ya no es «porque el recorrido deje de servir», sino porque ganar más tendría poco efecto.
- **P90.** Con el nivel 0,90 el p90 deja por debajo al 87,9 % de los casos en la validación; con **0,93 llega al 90,7 %**. Se aplica 0,93 (`NIVEL_P90` en `estimador_tiempo_restante.py` v5). En la prueba, con el nivel ya fijado, el p90 queda en 91–92 % (antes 87–88 %) desde las 0 hasta las 24 h, y la mejora frente al rango general no cambia (8,9 % a 9,0 % al llegar). A las 48 h queda en 92,5 %, algo pasado.

---

## 8. Cómo reproducirlo
Los datos viven fuera del proyecto. Se indican con tres variables (en Bash). `HUN_CRUDOS` es la carpeta con `visit_detail.csv` y `procedimientos_por_estancia.csv`; este último corrige la edad y el sexo y alimenta los escenarios.
```bash
export HUN_PROCESADOS="D:/Descargas D/Datos/procesados" HUN_TABLAS="D:/Descargas D/Datos/procesados/tablas" HUN_CRUDOS="D:/Descargas D/Datos"
```
1. **Tabla de episodios:** `src/analisis_etapas.py` y `src/preparar_variables.py`, con los CSV de la base en `datos/crudos/` y `P02_persona_de_los_diagnosticos.csv` y `P03_persona_de_los_laboratorios.csv` en `datos/crudos/auditoria_bd/`. Copiarlos ahí solo mientras corren y mover luego `datos/procesados/` a la carpeta externa.
2. **Utilidad (ventanas, censo y alerta):** `python3 src/utilidad_estimador.py` (~10 min). Escribe `utilidad_*.csv` en `HUN_TABLAS` y `resultados/graficos/utilidad_estimador.png`.
3. **Construcción y prueba del estimador:** `python3 src/comparar_estimadores.py` (~1,5 min). Escribe `comparacion_estimadores_*.csv` en `HUN_TABLAS` y `resultados/graficos/comparacion_estimadores.png`. Las formas de entrenar (sección 3.1): `python3 src/ventana_entrenamiento.py` (~10 min). Las banderas de laboratorio (sección 3.3) entran solas si `sev_hemograma_6h_*.csv` y `sev_quimica_6h_*.csv` están en `HUN_CRUDOS`; el modelo de consulta con todos los datos se entrena con `python3 src/estimador_tiempo_restante.py` (borrando antes el `.joblib`).
4. **Escenarios de gravedad y servicio:** `python3 src/procedimientos_escenario.py` (~4 min; necesita `procedimientos_por_estancia.csv` en `HUN_CRUDOS`) y `python3 src/triage_aproximado.py` (laboratorios).
5. **Alternativas:** `python3 src/estimador_tiempos.py` (tabla de perfiles), `python3 src/espera_dos_series.py` (dos series) y `python3 src/variables_descartadas.py` (datos que no aportan).
6. **Revisión del 9-nov (sección 7):** `python3 src/revision_estimador.py` (~15–25 min; `RAPIDO=1` omite la prueba hora por hora). Escribe `revision_estimador_*.csv` y `revision_estimador_resumen.txt` en `HUN_TABLAS`.
7. **Corte y calibración del p90 con un periodo de validación (sección 7.1):** `python3 src/calibracion_y_corte.py` (~15 min). Escribe `calibracion_corte_*.csv` y `calibracion_corte_resumen.txt` en `HUN_TABLAS`.
8. **Consulta:** `python3 src/estimador_tiempo_restante.py 67 Mujer Urgencias 6 "2026-03-04 15:00"`. Sin argumentos muestra los ejemplos de la sección 2.
9. **Página del dashboard:** `python3 dashboard/app.py`, abrir http://127.0.0.1:8050 y elegir «3.7 ¿Cuándo recibirá cama?» en el menú.
