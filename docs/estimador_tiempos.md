# A6 · Estimación del tiempo de espera de cama (7-nov-2026)

**Qué pide el instructivo (componente 3):** «modelos analíticos o predictivos que permitan estimar tiempos de atención». La pregunta concreta: **cuando un paciente espera cama, ¿cuánto le falta?**

## Resumen
1. **La espera es individual.** Pacientes que llegan el mismo día o a la misma hora no esperan parecido. Por eso la ocupación del hospital o la cola casi no ayudan a estimarla, y lo que sirve es información de cada paciente.
2. **El estimador es un modelo de tiempo restante.** Para un paciente que espera cama, da el rango de lo que le falta (percentiles 25, 50, 75 y 90) y la probabilidad de recibir cama en 6, 12 y 24 horas, y se recalcula a medida que pasa la espera. Usa el paciente, la hora del reloj, la ocupación, su historial de hospitalizaciones y su recorrido en urgencias, todo conocido en el momento. Se consulta con `estimar_tiempo_restante()`.
3. **Funciona mejor que todo lo demás que probamos, pero el techo es bajo.** Mejora el rango 7,6 % al llegar y 9,2–9,5 % entre las 3 y las 6 horas de espera, frente a darle a todos el mismo rango. Sus percentiles aciertan en datos nuevos, y le gana con margen comprobado a las otras cinco alternativas.
4. **Lo que más decide cuándo llega la cama es la hora del reloj:** entre las 6 y las 12 h casi nadie recibe cama; las camas se asignan entre las 15 y las 17 h y entre las 20 y las 23 h.
5. **Lo que de verdad lo mejoraría es registrar el triage.** Con una aproximación a la gravedad al llegar, la mejora llega a 12,7 %, más que con cualquier cambio de modelo.

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

**1.5 Lo que no está: la gravedad.** En urgencias la prioridad se define con el triage, de I (inmediata) a V (muy baja). La base no lo trae: no está en ninguna tabla y la etapa 9203 solo trae la hora. La sección 4 estima cuánto ayudaría.

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

**Un modelo por momento de la espera.** El recorrido cambia mientras el paciente espera. Por eso hay un modelo para cada momento (al llegar, a las 2, 4, 6 y 9 h), entrenado con quienes seguían esperando en ese momento y con lo que se sabía entonces. Esta técnica se llama «landmark». Desde las 12 h de espera el recorrido ya no suma, y se usa un solo modelo con el historial. El corte de 12 h se eligió mirando la prueba.

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
- Los modelos se entrenan con todo el periodo confiable y se guardan fuera del proyecto, en `HUN_PROCESADOS/modelos/` (salen de datos clínicos). Si no existen, se entrenan al primer uso (~1 min).

**Ejemplos** (miércoles 4-mar-2026, ocupación típica):

| Paciente | Faltan: p25 / mediana / p75 / p90 | Prob. de cama en 6 / 12 / 24 h |
|---|---|---|
| Mujer de 67 años, urgencias, recién llegada a las 9:00, sin historial | 12,0 / 32,1 / 56,9 / 84,7 h | 15 / 25 / 41 % |
| La misma, con 2 hospitalizaciones previas (la última: 60 h de espera, 200 h de estancia) | 20,0 / 39,9 / 77,1 / 109,3 h | 5 / 13 / 26 % |
| La misma sin historial, 6 h después: una etapa cerrada y una abierta | 10,8 / 30,5 / 54,9 / 96,7 h | 12 / 26 / 33 % |
| La misma sin historial, 6 h después: tres etapas abiertas | 5,5 / 7,7 / 24,3 / 31,5 h | 32 / 67 / 74 % |
| Niña de 8 años, urgencias, recién llegada a las 22:00 | 4,3 / 13,6 / 23,4 / 45,7 h | 33 / 47 / 77 % |

---

## 3. Qué tan bien funciona
**La prueba.** Todo se entrenó con llegadas de feb-2023 a jun-2025 y se probó con las 5.430 estancias de jul-2025 a 9-abr-2026, que ningún modelo había visto. Se mide la **mejora frente al rango general** (darle a todos los mismos percentiles), con la pérdida de cuantiles, que es el error estándar para percentiles. Los intervalos del 95 % salen de un bootstrap por semanas (1.000 repeticiones), porque los pacientes de una misma semana se parecen entre sí.

**Cómo mejora al sumar información** (lo que le falta a quien sigue esperando):

| Horas esperando | Tabla de perfiles | Modelo sin historial ni recorrido | + historial | **Estimador final** (IC 95 %) |
|---|---|---|---|---|
| 0 (al llegar) | 5,8 % | 6,6 % | 7,6 % | **7,6 % (6,7 a 8,5)** |
| 3 h | 6,3 % | 7,5 % | 8,2 % | **9,5 % (8,6 a 10,4)** |
| 6 h | 5,5 % | 6,9 % | 7,6 % | **9,2 % (8,4 a 10,1)** |
| 12 h | 3,7 % | 6,1 % | 6,6 % | **6,6 % (5,2 a 7,6)** |
| 24 h | 2,2 % | 4,9 % | 5,3 % | **5,3 % (3,8 a 6,8)** |
| 48 h | −0,9 % | 1,8 % | 2,1 % | **2,1 % (0,6 a 3,4)** |

**¿Aciertan los percentiles?** Lo ideal es que el 25 / 50 / 75 / 90 % de los casos nuevos quede por debajo de cada uno. Con el estimador final quedan 26,3 / 51,4 / 73,8 / 87,7 % al llegar y 25,8 / 49,6 / 71,8 / 86,9 % a las 6 h. El p90 queda algo corto (87–88 %) porque los peores casos siguen empeorando (`HALLAZGOS.md` 4.3); conviene leerlo como un piso.

**Cómo leerlo:**
- **Contra la tabla de perfiles, la ventaja es real en todos los momentos:** el intervalo de la diferencia nunca incluye el 0 (+1,3 a +2,5 puntos al llegar; +3,3 a +4,8 a las 6 h).
- **Contra el modelo de cuantiles al llegar,** que era el segundo mejor, la ventaja también es real: +0,9 a +1,9 puntos.
- **El historial suma desde la llegada, y el recorrido en las primeras horas** (probado a las 3 y a las 6 h). Desde las 12 h, la espera depende de otras cosas.
- **El techo es bajo:** el error de la mediana sigue siendo de unas 24 h al llegar.

**Agosto y septiembre de 2025.** Según el equipo, el HUN tuvo sobredemanda porque los hospitales cercanos fueron intervenidos por el Estado y quedó como la única opción de la zona. En los datos se ve poco: un 6–7 % más de llegadas que en los mismos meses de 2024, con ingresos a cama y espera mediana normales. Evaluado aparte, el estimador mejora 7,3 % en esos meses y 7,7 % en el resto. El resultado se sostiene.

---

## 4. Qué haría falta para mejorarlo
**La gravedad (triage).** Código: `src/triage_aproximado.py`. Se probaron dos aproximaciones dentro del modelo con historial, y ninguna es el triage:
- **Laboratorios de las primeras 6 h:** se conocen a las 6 h.
- **Grupo de diagnóstico:** el 88 % se registra tarde y el 35 % de las estancias no tiene ninguno. Se usa como **escenario**: «¿cuánto mejoraría si el HUN registrara la gravedad al llegar?».

| Horas esperando | Sin gravedad | + laboratorios de 6 h | + grupo de diagnóstico (escenario) |
|---|---|---|---|
| Al llegar | 7,6 % | 8,0 % (no válido: se conocen a las 6 h) | **12,7 %** |
| 6 h | 7,6 % | 7,6 % | **10,9 %** |
| 12 h | 6,6 % | 6,5 % | 9,0 % |
| 24 h | 5,3 % | 4,8 % | 6,5 % |
| 48 h | 2,1 % | 1,8 % | 2,0 % |

Una medida de gravedad al llegar mejoraría más que cualquier cambio de modelo, y un triage real debería servir más que el diagnóstico. Es un argumento concreto para la recomendación R1 (`docs/recomendaciones.md`): **registrar el nivel de triage en la base.** Los laboratorios tempranos casi no ayudan.

**Otros pendientes:**
- **Correcciones de datos:** pedir a Daniela `P02_persona_de_los_diagnosticos.csv` y `P03_persona_de_los_laboratorios.csv` para corregir la edad y el sexo de las estancias duplicadas, y volver a correr.
- **Gravedad desde los procedimientos:** con `Q01_procedimientos_por_estancia.csv` y `Q03_nombres_de_conceptos.csv` (lote 5, ya extraídos por Daniela) se puede armar una medida de gravedad (UCI, vía aérea, transfusión, reanimación) y buscar si algún concepto se llama «triage». Los procedimientos no tienen fecha, así que serviría como escenario.
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
| Efecto del día o de la hora de llegada | 0,1 % a 2,3 % más allá del azar | La espera es individual |
| Hora del primer diagnóstico como momento de la decisión de hospitalizar | Casi siempre coincide con la llegada | No marca la decisión |

---

## 6. Límites (van junto al estimador)
- **Rango de pacientes parecidos, no una promesa para una persona.** Sirve para comunicar expectativas y planear, no para darle una hora a un paciente.
- **La espera termina en la asignación administrativa.** Mezcla la atención clínica en urgencias con la espera de cama, y no se pueden separar.
- **Cama o silla:** según el equipo, a muchos pacientes se les atiende en sillas aunque necesiten una cama, y no se sabe si eso se registra como estar en cama. La base no tiene columna de cama, silla, piso ni servicio (`CLAUDE.md` 4.8). Si se registra, la espera real hasta una cama sería más larga, la falta de camas mayor de lo que muestran los datos y la ocupación incluiría puestos que no son camas (lo que explicaría que pase de las 106 camas el 42 % de las horas de 2025).
- **El recorrido supone que el sistema registra cada etapa cuando empieza.** No se pudo comprobar. Si las etapas se cargan después, el recorrido no estaría disponible en tiempo real.
- **Edad y sexo de las estancias duplicadas:** esta corrida no tuvo `P02` y `P03`. En las estancias registradas en dos personas se conservó el registro con más información, que es el de la persona real en ~81–85 % de los casos (`CLAUDE.md` 4.10). Lo mismo afecta al historial, que se busca por persona.
- **La ocupación hacia adelante se deja fija** en el último valor conocido.
- **Asociación, no causa.**

---

## 7. Cómo reproducirlo
Los datos viven fuera del proyecto. Se indican con tres variables (en Bash):
```bash
export HUN_PROCESADOS="D:/Descargas D/Datos/procesados" HUN_TABLAS="D:/Descargas D/Datos/procesados/tablas" HUN_CRUDOS="D:/Descargas D/Datos"
```
1. **Tabla de episodios:** `src/analisis_etapas.py` y `src/preparar_variables.py`, con los CSV de la base en `datos/crudos/`. Copiarlos ahí solo mientras corren y mover luego `datos/procesados/` a la carpeta externa.
2. **Construcción y prueba del estimador:** `python3 src/comparar_estimadores.py` (~1,5 min). Escribe `comparacion_estimadores_*.csv` en `HUN_TABLAS` y `resultados/graficos/comparacion_estimadores.png`.
3. **Escenario de gravedad:** `python3 src/triage_aproximado.py`.
4. **Alternativas:** `python3 src/estimador_tiempos.py` (tabla de perfiles) y `python3 src/espera_dos_series.py` (dos series).
5. **Consulta:** `python3 src/estimador_tiempo_restante.py 67 Mujer Urgencias 6 "2026-03-04 15:00"`. Sin argumentos muestra los ejemplos de la sección 2.
