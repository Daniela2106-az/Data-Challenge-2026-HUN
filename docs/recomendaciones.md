# Recomendaciones para el HUN (borrador, 22-oct-2026)

Borrador de Daniela con Claude para que Persona 3 lo revise y lo amplíe (ficha 3.4 de `docs/fichas_de_tareas.md`).
Cada recomendación dice qué cambiar, qué muestran **nuestros datos**, qué dice la **literatura**, cómo medirla y cuánto se puede
esperar de ella. Detalle de métodos y limitaciones: `CLAUDE.md`, secciones 4.6 y 6b.

**Cómo leerlo.** Todo lo que sigue son **asociaciones y escenarios con supuestos escritos**, no causas probadas. El HUN dio
su número de camas el 29-oct (106 y 58 camillas), pero nuestra ocupación lo supera; tampoco tenemos el motivo clínico de cada espera. Donde un efecto no se puede calcular, se dice.

## 1. Lo que encontramos (con estancias contadas una sola vez)

| # | Hallazgo | Cifra |
|---|---|---|
| 1 | Esperar cama es largo y los peores casos empeoran | Espera mediana 18,6 h, percentil 90 de 73,9 h; el exceso medio sube de 17,3 h (2023) a 23,8 h (ene–abr 2026), +38 % |
| 2 | Casi todo el tiempo está dentro de urgencias, no en huecos entre etapas | 80 % de las horas de espera es tiempo en urgencias antes de la cama; 21 % es tiempo sin ninguna etapa registrada |
| 3 | Las altas son tardías y la cama se asigna por la tarde | 62,5 % de las altas entre las 14:00 y las 18:59, solo 14 % antes del mediodía; la cama se asigna a las 17–18 h sin importar cuándo llegó el paciente |
| 4 | Quien llega a media tarde espera más | Mediana de 25 h al llegar entre las 13 y las 16 h contra 12–15 h de madrugada; a las 16 h, 72 % recibe cama al día siguiente o después |
| 5 | La ocupación sube por la estancia, no por más pacientes | Camas ocupadas 94 (2023) a 105 (2025); estancia media 4,57 a 5,31 días (+16 %); ingresos ~20 por día sin crecer |
| 6 | La carga del momento explica poco | Cada decil más de llegadas en 6 h sube la espera ~2,5 %; la ocupación y el día de la semana casi no importan |
| 7 | El 83 % de las horas de espera viene de esperas de más de 24 h | El 19 % de los pacientes espera más de 48 h |

## 2. Resumen de recomendaciones

| Prioridad | Recomendación | Impacto que respaldan los datos | Qué tan firme |
|---|---|---|---|
| 1 | Registrar mejor: hora de salida de urgencias, asignación de cama y sin duplicados | Habilita medir todo lo demás | Alta |
| 2 | Seguimiento mensual de 6 indicadores | Permite ver si algo mejora | Alta |
| 3 | Reunión diaria de camas a media mañana, con alertas | No cuantificable; la alerta de las 12 h detecta 83 % de los días congestionados | Media |
| 4 | Meta de altas antes del mediodía (empezar con 25–30 %) | Hasta 5,1 camas libres a las 12 h; evita como máximo 8 % del exceso de espera (estimación central ~3 %) | Media-baja |
| 5 | Alerta por paciente a las 48 h sin cama, con responsable | ~4 alertas por día; 51 % termina esperando más de 72 h; 24 h de margen | Media |
| 6 | Protocolo para quien llega entre las 13 y las 18 h y se hospitaliza | Entre ~11 y ~49 horas-paciente por día (2–11 % del exceso de 447) si igualaran a quien llega por la mañana | Baja (el rango depende de usar promedios o medianas) |
| 7 | Revisar sistemáticamente las estancias largas | −5 % de estancia ≈ 5 camas; volver a la de 2023 ≈ 15 camas | Media (la causa del aumento no se conoce) |

## 3. Detalle

### R1. Registrar mejor los datos (prioridad 1)
- **Qué cambiar:** registrar la hora de salida de urgencias en todas las atenciones (hoy el 36–42 % de las etapas de urgencias no la
  tiene), registrar la hora en que se asigna la cama, y evitar que un mismo ingreso quede en dos pacientes.
- **Por qué:** el 41 % de los episodios hospitalizados tenía una estancia duplicada en otra persona. Sin corregirlo se estimaban 27,7
  ingresos por día (son ~20) y ~146 camas ocupadas (son ~100). Desde el 10 de abril de 2026 el registro de las etapas se degrada (la auditoría en la base muestra que las visitas no bajaron en mayo: no es menos demanda);
  esos días no se usan para estimar nivel ni evaluar.
- **Fuente externa:** no aplica; es un requisito para medir cualquier mejora.
- **Cómo medirla:** % de atenciones con hora de salida; número de registros duplicados.
- **Límite:** no sabemos cuál de las dos personas duplicadas es la real (pregunta 1 al HUN).

### R2. Seguimiento mensual de indicadores (prioridad 2)
Valores de partida con nuestros datos:

| Indicador | Hoy |
|---|---|
| Espera de cama, mediana / percentil 90 | 18,6 h / 73,9 h |
| % de pacientes con más de 48 h sin cama | 19 % |
| % de altas antes del mediodía | 15 % |
| Hora mediana de asignación de cama | 17–18 h |
| Camas ocupadas a las 12 h (promedio mar-2023 a abr-2026) | ~103 (`escenario_camas_por_hora.csv`, `simulacion_altas.py`). Ocupación media de todo el día en 2025: 105, que cuadra con las 106 camas de hospitalización que dio el HUN (ver `CLAUDE.md` 4.8) |
| Estancia media | 5,31 días (2025) |

### R3. Reunión diaria de camas con alertas (prioridad 3)
- **Qué hacer:** una reunión corta de 10 a 15 minutos a media mañana con censo, altas previstas e ingresos previstos, apoyada en las
  alertas de `src/alertas.py`: día congestionado a las 12 h y ocupación alta.
- **Por qué (nuestros datos):** a las 12 h la alerta de día congestionado tiene AUC de 0,94 y detecta 5 de cada 6 días congestionados
  (28 alertas en 120 días, 54 % de precisión). Para la ocupación a 24 h, "lo mismo que ahora" funciona mejor que una proyección
  (precisión 75 %, detección 90 %). Se liberan ~20 camas por día, solo como orden de magnitud.
- **Literatura:** la guía de la "reunión matutina de cabecera" propone 10–15 minutos revisando censo, altas e ingresos esperados
  ([Becker's](https://www.beckershospitalreview.com/capacity-management/the-am-bedside-huddle-what-to-cover-to-achieve-streamlined-patient-flow.html)).
  Un resumen de congreso (un solo hospital) encontró altas más tempranas pero sin cambio significativo en la estancia
  ([SHM](https://shmabstracts.org/?p=23287)). La evidencia es sobre todo de un solo centro y sin grupo de comparación.
- **Cómo medirla:** alertas atendidas, acciones tomadas, ocupación a las 12 h.
- **Límite:** las alertas se probaron sobre días pasados con pocos días congestionados (18); las cifras pueden moverse.

### R4. Meta de altas antes del mediodía (prioridad 4)
- **Qué hacer:** pasar del 15 % actual al 25–30 % de las altas antes de las 12 h, con ronda médica temprana y preparación del alta
  el día anterior.
- **Por qué (nuestros datos):** las altas se concentran de las 14 a las 19 h y las camas se asignan a las 17–18 h; los ingresos a cama
  siguen a las altas en la misma hora. Con el 30 % de las altas de la tarde antes del mediodía: hasta **5,1 camas libres a las 12 h**
  (~37 horas-cama por día).
- **Impacto en espera:** como máximo ~8 % del exceso de espera, estimación central ~3 %. Adelantar el 100 % daría como máximo 27 %. El
  83 % de las horas de espera viene de esperas de más de 24 h, que unas horas de adelanto no deshacen.
- **Literatura (mixta):** un programa con rondas interdisciplinarias sostuvo más del 50 % de órdenes de alta antes del mediodía durante
  24 meses y reportó 0,30 días menos de estancia y 2,1 horas menos de espera en urgencias por paciente
  ([PMC5654890](https://pmc.ncbi.nlm.nih.gov/articles/PMC5654890)). Otro hospital duplicó las altas antes del mediodía (5,0 a 11,4 %)
  sin efecto en la estancia y con 41 minutos más de espera en urgencias
  ([The Hospitalist](https://www.the-hospitalist.org/hospitalist/article/38356/critical-care/implementing-and-evaluating-a-dbn-initiative-in-a-large-tertiary-care-urban-hospital/)).
  Una revisión describe la evidencia como mixta ([BMC Health Serv Res 2024](https://bmchealthservres.biomedcentral.com/counter/pdf/10.1186/s12913-024-10960-x.pdf)).
- **Cómo medirla:** % de altas antes de las 12 h; hora mediana de asignación de cama; espera de quien llega de 12 a 18 h.
- **Límite:** es una cota con supuestos (el alta de los demás pacientes no cambia; el HUN dijo el 29-oct que tiene 106 camas de hospitalización y 58 camillas de urgencias; con la regla de estancia única v3.8 nuestra ocupación (~103 a las 12 h, media de 105 en 2025) es coherente con esa cifra). Mejora
  la **hora** de la cama, no la capacidad.

### R5. Alerta por paciente a las 48 h sin cama (prioridad 5)
- **Qué hacer:** cuando un paciente lleva 48 h desde su llegada sin cama, avisar a un responsable que revise por qué.
- **Por qué (nuestros datos):** ~4,1 alertas por día; el 51 % de esos pacientes termina esperando más de 72 h, con 24 h de margen. A las
  36 h serían 5,5 por día (38 %); a las 60 h, 2,7 por día (79 %, solo 12 h de margen).
- **Límite:** solo cuenta a quienes luego se hospitalizan, así que en tiempo real habría más alertas; riesgo de fatiga por alertas. Sin
  una acción definida para cada alerta no sirve.

### R6. Protocolo para quien llega entre las 13 y las 18 h y se hospitaliza (prioridad 6)
- **Qué hacer:** anticipar la decisión de ingreso y la solicitud de cama durante la tarde, para no esperar al ciclo de altas del día
  siguiente.
- **Por qué:** mediana de 23,6 h al llegar de 13:00 a 18:59 contra 15,7 h al llegar de 6:00 a 11:59. Llegan unos 6,4 pacientes por día en esa franja.
  Si su espera bajara a la de la mañana, se evitarían **~49 horas-paciente por día midiendo con medianas (11 % del exceso de 447
  horas por día) pero solo ~9 midiendo con promedios (2 %)**, porque los promedios de la mañana y de la tarde son parecidos
  (~31–32 h) y los dominan las esperas largas. Por eso es una recomendación de confianza baja: ayuda a la espera típica, no a la cola.
- **Límite:** la espera mezcla atención clínica con espera de cama y no se pueden separar con los datos (preguntas 4 y 5 al HUN).
- **Fuente:** `src/impacto_llegada_tarde.py` → `resultados/tablas/impacto_llegada_tarde.csv` (estancias únicas, feb-2023 a abr-2026). Es asociación por hora de llegada, no causa.

### R7. Revisar las estancias largas (prioridad 7)
- **Qué hacer:** revisión semanal de pacientes con estancias de más de 7 días, con gestión de casos.
- **Por qué:** la ocupación subió 12 % por la estancia (+16 %). Con la ley de Little: bajar la estancia 5 % libera ~5 camas; volver a la
  de 2023, ~16. Estancias: mediana 71 h, percentil 75 de 144 h, percentil 90 de 280 h.
- **Literatura:** una revisión de revisiones encontró estrategias como planificación del alta, gestión de casos y rutas clínicas, con
  resultados inconsistentes entre poblaciones ([JAMA Netw Open 2021, PMC8453321](https://pmc.ncbi.nlm.nih.gov/articles/PMC8453321/)).
- **Límite:** no sabemos por qué subió la estancia (tipo de pacientes, procesos o demoras); requiere revisión clínica.

## 4. Lo que los datos NO respaldan
- **"Hacen falta más camas":** el HUN dice que tiene 106 camas de hospitalización y 58 camillas, y nuestra ocupación media de 2025 (105) coincide con ese número, así que el hospital opera cerca de su capacidad de camas; los picos (hasta 123) superan las 106 camas y son posibles con camillas de apoyo (no comprobado). Además, la espera casi no sube con la ocupación (la carga explica 0,1 punto de
  la variación) y la ocupación subió por la estancia, no por la demanda.
- **Más personal según el día de la semana:** el día de la semana y los festivos casi no cambian la espera.
- **Priorizar a un paciente concreto por riesgo de esperar:** un modelo con lo que se sabe al llegar acierta apenas mejor que el azar
  (AUC 0,60) y todos los factores juntos explican solo el 14 % de la variación.
- **Un centro de comando o tablero como solución en sí:** los resultados publicados son sobre todo autoinformados; el estudio con
  diseño controlado que encontramos no halló cambio significativo en la estancia
  (análisis retrospectivo de series de tiempo en [Bradford](https://eprints.whiterose.ac.uk/209410/1/mzad072.pdf)).

## 5. Qué necesitamos del HUN antes de cerrar
1. ~~Número de camas~~ (contestado el 29-oct: 106 camas y 58 camillas; falta saber desde cuándo) y meta de tiempo para asignar cama (sin respuesta; no habrá más sesiones, se declara como limitación).
2. ~~Por qué las llegadas bajan desde abril de 2026~~ (auditoría del 2-nov: el registro de las etapas se degrada desde el 10-abr-2026; las visitas de urgencias no bajaron en mayo; falta la causa del cambio de registro).
3. Dónde está el paciente durante el tiempo sin etapa antes de la cama (~1 de cada 4 hospitalizados) y qué significa esa espera en
   urgencias.
4. Cuál de las dos personas es la real cuando una estancia aparece duplicada.

## 6. Fuentes consultadas
Encontradas con una búsqueda web el 22-oct-2026; **solo se leyeron los resúmenes de la búsqueda: verificar el texto original antes
de citarlas en el documento final.**
- Altas antes del mediodía: [PMC5654890](https://pmc.ncbi.nlm.nih.gov/articles/PMC5654890), [The Hospitalist (Maimonides)](https://www.the-hospitalist.org/hospitalist/article/38356/critical-care/implementing-and-evaluating-a-dbn-initiative-in-a-large-tertiary-care-urban-hospital/), [BMC Health Serv Res 2024](https://bmchealthservres.biomedcentral.com/counter/pdf/10.1186/s12913-024-10960-x.pdf).
- Reuniones de camas: [Becker's](https://www.beckershospitalreview.com/capacity-management/the-am-bedside-huddle-what-to-cover-to-achieve-streamlined-patient-flow.html), [SHM](https://shmabstracts.org/?p=23287), [NHS Dumfries and Galloway](https://www.gov.scot/publications/nhs-dumfries-galloway-case-study-balancing-capacity-demand-dumfries-galloway-9781788510479/pages/15/).
- Congestión de urgencias: [Hoot y Aronsky 2008](https://pubmed.ncbi.nlm.nih.gov/18433933/), [revisión 2018–2025](https://hsrc.himmelfarb.gwu.edu/gwhpubs/8570).
- Centros de comando: [Bradford](https://eprints.whiterose.ac.uk/209410/1/mzad072.pdf), [Queen's Health System](https://www.beckershospitalreview.com/healthcare-information-technology/the-queens-health-systems-saves-20-million-in-the-first-year-after-opening-a-command-center/).
- Reducir la estancia: [JAMA Netw Open 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8453321/).
