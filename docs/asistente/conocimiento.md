# Base de conocimiento del asistente (dashboard HUN)

Este documento se arma solo con `src/armar_conocimiento.py` a partir de la documentación del proyecto. Es la única fuente del asistente de preguntas: lo que no esté aquí, el proyecto no lo sabe.

## Páginas del dashboard
- **Alertas**: `/alertas`
- **Llegada y altas**: `/altas`
- **Días atípicos**: `/atipicos`
- **Planeación de camas**: `/camas`
- **Comparar años**: `/comparar`
- **Datos y calidad**: `/datos`
- **Demanda**: `/demanda`
- **Diagnósticos**: `/diagnosticos`
- **Documentación**: `/documentacion`
- **Espera de cama**: `/espera`
- **Forma del año**: `/estacionalidad`
- **Estancias largas**: `/estancia`
- **Factores de la espera**: `/factores`
- **Asistente de flujo HUN**: `/`
- **Ocupación de camas**: `/ocupacion`
- **Paciente en espera**: `/paciente`
- **Paciente en cama**: `/paciente-cama`
- **Perfiles y picos**: `/perfiles`
- **Diagnóstico por periodo**: `/periodo`
- **Pronóstico**: `/pronostico`
- **Recomendaciones**: `/recomendaciones`
- **Resumen**: `/resumen`
- **Simulador integral**: `/simulador`

## Cómo está organizado el dashboard
El dashboard se abre en el asistente (la página de inicio), donde se pregunta en lenguaje natural; debajo hay una guía para explorar por categorías y un recorrido guiado que empieza en Resumen. El menú lateral tiene estas categorías:
- **Contexto** (El proyecto en una pantalla, y qué datos hay detrás): Resumen (`/resumen`), Datos y calidad (`/datos`)
- **Flujo** (Cuántos pacientes llegan, a qué hora y cómo cambia con los años): Demanda (`/demanda`), Llegada y altas (`/altas`), Forma del año (`/estacionalidad`), Comparar años (`/comparar`)
- **Capacidad** (Cuánto se llena el hospital y por qué se espera por una cama): Ocupación de camas (`/ocupacion`), Espera de cama (`/espera`), Factores de la espera (`/factores`), Estancias largas (`/estancia`)
- **Clínico** (Qué diagnósticos esperan más y dónde se acumula el tiempo): Diagnósticos (`/diagnosticos`), Diagnóstico por periodo (`/periodo`)
- **Riesgo** (Quiénes y cuándo se complica el flujo, y cómo avisar a tiempo): Perfiles y picos (`/perfiles`), Días atípicos (`/atipicos`), Alertas (`/alertas`)
- **Módulos** (Qué se espera y qué pasaría si algo cambia): Pronóstico (`/pronostico`), Paciente en espera (`/paciente`), Paciente en cama (`/paciente-cama`), Planeación de camas (`/camas`), Simulador integral (`/simulador`)
- **Conclusiones** (Qué hacer con lo que se encontró): Recomendaciones (`/recomendaciones`), Documentación (`/documentacion`)
Para empezar: Resumen (el proyecto en una pantalla), luego Espera de cama y Ocupación de camas (el problema), Recomendaciones (qué hacer) y, para probar escenarios, el Simulador integral.

# Fuente: docs/documento_final.md

## ¿Por qué se espera tanto por una cama?
### Flujo de pacientes, cuellos de botella y anticipación en el Hospital Universidad del Norte

**Data Challenge HUN 2026** · Hospital Universidad del Norte (HUN) y pregrado de Ciencia de Datos, Universidad del Norte  
**Equipo:** Daniela Amaya (coordinación, datos y análisis), Samuel Amador (estimador de tiempos, recomendaciones y dashboard), Anthony Amaya (modelo explicativo y simulación de camas)  
**Versión:** versión del 17-nov-2026 (estacionalidad anual completa, ficha A9: dengue, IRA y EDA del SIVIGILA; recomendaciones con 38 fuentes verificadas; capítulo 3 reorganizado: tablas y columnas de la base, exploración y limpieza paso a paso, variables y herramientas) · **Entregables:** este documento, el repositorio en GitHub y el dashboard interactivo  

> **Cómo leer este documento.** Cada cifra lleva al lado el documento del repositorio donde se calcula y el script que la produce. Casi todo
> son **asociaciones y escenarios**, no causas probadas, y cada hallazgo lleva su limitación junto a él. Los datos clínicos no están en el
> repositorio: solo el código, las consultas, los documentos y los gráficos.
> **Este documento es la versión completa**, pensada para quien quiera revisar el método. El dashboard cuenta lo mismo resumido para el
> hospital: cada página lleva al pie el enlace a la sección de aquí que la respalda.

---

### 1. Resumen ejecutivo

**La pregunta del reto:** comprender, predecir y optimizar el flujo de pacientes del hospital, identificando cuellos de botella, patrones
operacionales y oportunidades de mejora en los tiempos de atención. Abordamos los cuatro componentes del instructivo.

**Lo que encontramos, en ocho puntos:**

1. **El cuello de botella es la espera de cama.** Desde que el paciente llega hasta que se le asigna cama pasan, en mediana, **18,6 horas**;
   uno de cada diez espera más de **73,9 horas** y el 43,7 % espera más de un día. El 98 % de ese tiempo transcurre en urgencias antes de
   que se asigne la cama.
2. **Los peores casos empeoran.** La espera mediana casi no cambió entre 2023 y 2026 (17–20 h), pero el percentil 90 pasó de 61 a 81 horas y
   el exceso medio de espera por paciente creció 38 %.
3. **La cama llega en dos olas, por la tarde y por la noche.** El 61 % de las camas se asigna entre las 15 y las 17 h o entre las 20 y las 23 h;
   solo el 9 % en la mañana. El 63 % de las altas sale entre las 14 y las 19 h. Quien llega a media mañana espera hasta la tarde.
4. **Hay un límite de proceso, no solo de camas.** Una cama que se libera en la mañana tarda una mediana de 1,8 horas en volver a asignarse,
   aunque siempre haya unos 26 pacientes esperando.
5. **La ocupación sube porque los pacientes se quedan más, no porque lleguen más.** Las camas ocupadas pasaron de 94 (2023) a 105 (2025),
   frente a 106 camas del hospital; los ingresos se mantienen en ~20 por día y la estancia media subió 16 % (4,6 a 5,3 días).
6. **Se puede anticipar el día y el año:** las llegadas se pronostican con ~8 % de error a una semana y ~10 % a un año, ahora con la forma del
   año (más pacientes a mitad de año, menos en diciembre) tomada de datos públicos de vigilancia (dengue para las llegadas; infección
   respiratoria y diarrea para los ingresos a cama); una alerta a mediodía detecta 13 de cada 15 días
   congestionados; la cola de pacientes sin cama se pronostica a 6–12 h con un tercio menos de error que suponer que todo sigue igual.
7. **La simulación de camas muestra que la estancia es la palanca más barata:** bajar la estancia 5 % reduce los días saturados casi tanto como
   los aumentaría un 10 % más de ingresos.
8. **Se puede estimar cuándo recibirá cama cada paciente.** El estimador mejora el rango ~9 % al llegar y 11 % a las pocas horas, acierta sus
   percentiles y le gana a cinco alternativas. Con la **gravedad (triage) y el servicio** registrados al llegar, la mejora se duplicaría (de 8,4 % a
   16,9 %).

**Lo que proponemos:** registrar mejor (salida de urgencias, asignación de cama, triage, servicio y hora de la orden de hospitalización), una
reunión diaria de camas apoyada en alertas, adelantar las altas **y** asignar enseguida la cama que se libera, una alerta por paciente sin cama
con responsable, y revisar cada semana las estancias largas (sección 7).

---

### 2. El reto y qué abordamos

**Contexto.** El instructivo pide abordar uno o varios de cuatro componentes y valora los hallazgos estratégicos para el hospital, la
interpretabilidad, la visualización efectiva y la comunicación clara que traduzca los análisis en acciones. Los entregables son la
documentación, el repositorio en GitHub y el enlace a un dashboard interactivo (los organizadores aceptaron Dash en lugar de Power BI).

| Componente del instructivo | Qué hicimos | Dónde |
|---|---|---|
| 1. Caracterizar el flujo reconstruyendo las etapas | Limpieza de la base, episodios, rutas, tiempos por etapa | Sección 4; `docs/HALLAZGOS.md` 2–3 |
| 2. Factores de los tiempos y la estancia; cuellos de botella | Definición formal de cuello de botella, ranking, carga, altas tardías, perfiles, diagnósticos, estancias largas, etapas de urgencias | Sección 5 |
| 3. Modelos para estimar tiempos, saturación y patrones atípicos | Pronóstico de demanda, alertas, días atípicos, estimador de espera por paciente, simulación Monte Carlo de camas, pronóstico de la cola, simulador integral | Sección 6 |
| 4. Propuestas accionables | Siete recomendaciones con su cifra, su evidencia externa verificada y su límite | Sección 7 |

**Decisión de enfoque:** la profundidad va en la espera de cama (componente 2) y en los modelos (componente 3); el componente 1 da el contexto y

**La ruta del proyecto, de punta a punta.** Este documento sigue el orden en que se trabajó:

| Etapa | Qué se hizo | Dónde está |
|---|---|---|
| Contexto | El reto, lo que pide el instructivo y las decisiones de enfoque | Sección 2 |
| Extracción | Cómo se obtuvieron los datos de la base del hospital | 3.2 |
| Exploración | Qué hay en la base, tabla por tabla, y qué no trae | 3.1 y 3.3 |
| Limpieza | Visitas copia, estancias duplicadas, etapas abiertas, episodios y la persona real | 3.4 |
| Calidad y validación | El quiebre de abril de 2026 y lo que respondió el hospital | 3.5 y 3.6 |
| Construcción de variables | Calendario, carga, ocupación, diagnóstico y laboratorios | 3.7 |
| Flujo y cuello de botella | Cómo fluye el paciente, dónde se pierde el tiempo y qué factores se asocian | Secciones 4 y 5 |
| Modelos y simulación | Pronóstico, alertas, días atípicos, estimador, simulación de camas y simulador integral | Sección 6 |
| Recomendaciones | Siete acciones con su evidencia y su meta | Sección 7 |
| Dashboard | Cómo se presenta todo al hospital | Sección 8 |
| Límites y futuro | Lo que no sabemos y lo que sigue | Secciones 9 y 10 |
el 4 sale de los dos anteriores.

---

### 3. Los datos y su calidad

Este capítulo sigue el orden en que se trabajó: qué es la base (3.1), cómo se extrajeron los datos (3.2), qué tablas y columnas se usaron (3.3), cómo se exploró y se limpió paso a paso (3.4), qué pasó con el registro en abril de 2026 (3.5), lo que dijo el hospital (3.6), qué variables se construyeron (3.7) y con qué herramientas (3.8). Es la parte **previa a cualquier resultado**: sin ella, las cifras del hospital salían infladas cerca de 40 %.

#### 3.1 La base
Base PostgreSQL en el esquema estándar **OMOP** (`uninorte_omop`), de solo lectura y detrás de VPN. Tablas: `visit_occurrence` (1,7 millones de
visitas), `visit_detail` (3,28 millones de etapas), `person` (912 mil personas), `condition_occurrence` (38,6 millones de filas de
diagnósticos), `procedure_occurrence` (47 millones) y `measurement` (16,6 millones de laboratorios). Periodo: enero de 2023 a julio de 2026.

Lo que la base **no** trae, aunque el instructivo lo mencione: servicio, piso o cama; triage; hora de la orden de hospitalización; hora de los
procedimientos (la columna está vacía en toda la tabla); diagnóstico principal; signos vitales; y la duración de la visita (inicio = fin en el
100 %). Las duraciones salen de las **etapas** (`visit_detail`), que son de cuatro tipos:

| Código | Lo llamamos | Qué parece ser |
|---|---|---|
| 9203 | Llegada (ER) | Admisión o triage en urgencias; dura minutos |
| 3045729 | Urgencias (TU) | Atención en urgencias, incluida la observación y la espera |
| 9201 | Cama (HOSP) | Hospitalización; según el HUN, se registra **al asignar la cama** |
| 581479 | Ambulatorio (AMB) | Evento administrativo de duración cero; se descarta |

Cómo se obtuvieron los datos está en 3.2; el detalle de cada tabla y de sus columnas, en 3.3; cómo se exploró y se limpió, en 3.4.

#### 3.4 Cómo exploramos y limpiamos la base, paso a paso
1. **Exploración por agregados.** La base es lenta (consultas de 10 a 30 minutos, solo índices de llave primaria), así que nunca se bajaron tablas enteras: cada
   pregunta se resolvió con una consulta agregada por visita en SQL (`sql/`), exportada a CSV y analizada en Python. Antes de usar cada tabla se contaron sus filas,
   sus conceptos, sus fechas nulas y sus rangos; así aparecieron, por ejemplo, el 100 % de procedimientos sin fecha y los 80 diagnósticos con fecha futura. Desde
   noviembre las consultas se lanzan desde Python en segundo plano (la VPN apaga el internet mientras está conectada; `docs/conexion_bd.md`).
2. **Visitas copia (30 %).** Una visita cuyo id es otro id más un desfase fijo (1.746.478 y otros) y con las mismas etapas al segundo. Las de la misma persona se
   borran y su información clínica pasa a la visita original; las de otra persona se conservan como visitas, quitando las etapas que repiten.
3. **Etapas.** Se descartan las ambulatorias (duración cero) y las abiertas en la extracción (fin con milisegundos). Las etapas de urgencias seguidas se juntan en
   un bloque para medir; las que tienen inicio = fin se marcan sin duración, no como cero.
4. **Episodios.** Una atención continua de un paciente; se corta un episodio nuevo cuando pasan más de 168 h sin etapas. Con esto desaparece el «desfase de 16 días»
   que vivía en las copias. Resultado: 337.194 episodios.
5. **Estancias gemelas (41 % de los hospitalizados).** La misma estancia en cama registrada en dos personas. Regla v3.8: los registros que comparten el inicio y el fin
   de cama, o algún intervalo de cama idéntico al segundo, son una sola estancia (25.777 estancias únicas). Sin esta regla el hospital parecía tener 146 camas ocupadas.
6. **Persona real (regla v4.0).** De cada estancia gemela se conserva el registro de la persona que domina en sus diagnósticos y laboratorios (identificada en el
   97,6 %); así la edad y el sexo son los correctos. Los diagnósticos y laboratorios se filtran siempre por esa persona.
7. **Periodo confiable.** Del 1-feb-2023 al 9-abr-2026, sin el 28 y 29 de marzo de 2026 (caída del registro). Después del 10-abr el registro de etapas se degrada y
   no se usa para estimar niveles ni errores.
8. **Verificación.** Una auditoría de 29 consultas directas en la base (altas por hora, ingresos, copias, camas ocupadas) reproduce las cifras del pipeline con otro
   método, y el pipeline completo se regeneró desde cero en un clon limpio del repositorio.

**Los problemas, en resumen:**

| Problema | Tamaño | Qué se hizo |
|---|---|---|
| Visitas copia (mismo contenido con otro id) | ~30 % de las visitas | Se borran las de la misma persona y su información pasa a la visita original |
| **Estancias en cama duplicadas en dos personas** | 41 % de los hospitalizados | Cada estancia se cuenta una vez (regla v3.8: 25.777 estancias únicas) y se conserva la **persona real**, identificada por quién domina los diagnósticos y laboratorios en el 97,6 % de los casos |
| Etapas de urgencias sin hora de salida | 36–42 % | Se marcan sin duración (no como 0 h); la duración de urgencias de quien se va de alta solo se describe, con métodos de supervivencia |
| Etapas abiertas al momento de la extracción | 2.053 | Se descartan |
| **Registro de etapas degradado desde el 10-abr-2026** | La etapa de llegada cae de 65 % a 30 % de las visitas mientras las visitas no bajan | Se usa solo el **periodo confiable: 1-feb-2023 a 9-abr-2026** |
| Caída de todo el registro el 28 y 29 de marzo de 2026 | 14 y 118 visitas (lo normal: 400–600) | Se excluyen |

**Por qué importa:** sin esta limpieza el hospital parecía tener ~146 camas ocupadas y 27,7 ingresos por día; los valores reales son ~100 camas y
~20 ingresos. La auditoría directa en la base (2-nov) y la reproducción del pipeline en un clon limpio confirmaron las cifras.
Detalle: `docs/CONTEXTO_TECNICO.md` 4.1–4.13; `docs/HALLAZGOS.md` 2; `src/analisis_etapas.py`, `src/preparar_variables.py`, `src/auditoria_bd.py`.

**Resultado:** 337.194 episodios (atención continua de un paciente; se corta tras 168 h sin etapas). En el periodo confiable, 22.819 estancias
únicas con espera de cama medida.

#### 3.5 El quiebre de abril de 2026 y lo que pasaba en el sistema de salud
La auditoría en la base (`docs/CONTEXTO_TECNICO.md` 4.9) muestra que desde el 10-abr-2026 las visitas de urgencias **suben ~40 %** mientras el registro de etapas se
degrada: no es menos demanda. El hospital no explicó la causa. Para el contexto se revisaron prensa y actos de la Superintendencia de Salud
(`docs/estacionalidad_anual.md`, cuarta ronda):
- **Oct-2023:** abre el Hospital Juan Domínguez Romero en Soledad, el mismo municipio del HUN. **Ene-2025:** abre el Nuevo Hospital de Barranquilla
  (122 camas de hospitalización y urgencias).
- **Ago-2025:** la Supersalud interviene la ESE Universitaria del Atlántico (red pública del departamento) por 49 hallazgos críticos, entre ellos
  fallas en urgencias.
- **Abr-2026:** la Supersalud prorroga la intervención de Nueva EPS; desde el 22-abr la Clínica General del Norte (Barranquilla) suspende las cirugías
  programadas por la cartera de las EPS, y varias clínicas acumulan deudas de más de 90 días con sus médicos.

**Lectura:** la crisis financiera de abril de 2026 pudo llevar pacientes de otras clínicas al HUN, lo que encaja con el aumento de visitas, pero las
fechas no coinciden exactamente (10-abr frente a 22-abr) y no se puede comprobar con los datos. Queda como hipótesis, no como causa; la decisión de
usar solo el periodo confiable no cambia.

#### 3.6 Lo que dijo el hospital (sesión del 29-oct-2026)
106 camas de hospitalización (88 de adultos y 18 de niños) y 58 camillas de urgencias; la hospitalización se registra al asignar la cama; las
estancias en dos personas «probablemente son duplicados»; hay horarios y costumbres de alta. No dieron la meta de tiempos ni la causa del cambio
de registro de abril de 2026. No hubo más sesiones.

### 4. Cómo fluye el paciente (componente 1)

- **Llegadas:** ~265 episodios por día. Pico entre las 9 y las 11 h, mínimo de 3 a 4 h; el lunes es el día más cargado y el fin de semana llega
  ~30 % menos. Incluyen ~4 % de réplicas de registro, estables en el tiempo (no se deduplican).
- **Recorrido:** llegada (minutos) → urgencias → cama. Solo ~1 de cada 8–10 atendidos se hospitaliza (~20 ingresos a cama por día).
- **Urgencias sin hospitalizar:** con supervivencia (Kaplan-Meier) la mediana es de ~11 h y el percentil 90 de 71–81 h; quedarse solo con los
  que tienen hora de salida la subestima (`docs/supervivencia_urgencias.md`).
- **Estancia en cama:** mediana de 71 h, percentil 90 de 280 h, media de 5,2 días.
- **Entre etapas casi no hay tiempo muerto:** el «hueco sin registro» antes de la cama que se creía del 21 % resultó un artefacto de las estancias
  duplicadas; en el registro de la persona real es ~1 % de las horas (`docs/CONTEXTO_TECNICO.md` 4.12).
- **Reingresos depurados:** 5,3 % en 72 h y 14,1 % en 30 días (`docs/c4_reingresos_huecos_llegadas.md`).

![Mapa de calor de llegadas por día y hora](../resultados/graficos/mapa_calor_llegadas.png)

---

### 5. El cuello de botella y sus factores (componente 2)

#### 5.1 Definición
Un segmento del recorrido es **cuello de botella** si (1) es una espera y no atención clínica, (2) tiene exceso sobre una referencia de «cuando
el hospital funciona bien» (la mediana con carga baja), (3) tiene impacto alto (volumen × retraso) y (4) se agrava con la carga. El orden de los
resultados no cambia con cuatro referencias distintas ni con tres cortes de episodio (`docs/plan_de_accion.md`; `src/ranking_cuellos.py`).

#### 5.2 La espera de cama es el cuello de botella

| Segmento (estancias únicas) | n | Mediana | p75 | p90 |
|---|---|---|---|---|
| **Espera de cama** | 25.373 | **18,6 h** | 37,9 h | **73,9 h** |
| Urgencias antes de la cama | 25.373 | 11,1 h | 29,5 h | 55,9 h |
| Estancia en cama | 25.777 | 70,7 h | 143,9 h | 280,3 h |

- El **64 %** de las horas de espera (518 mil de 812 mil horas-paciente) está por encima de la referencia de carga baja.
- El 83 % de las horas de espera viene de esperas de más de 24 h, y el 57 % de esperas de más de 48 h (el 19 % de los pacientes).

![Ranking de cuellos de botella](../resultados/graficos/ranking_cuellos.png)

#### 5.3 Los peores casos empeoran

| Año | Mediana | p90 | Exceso medio por paciente |
|---|---|---|---|
| 2023 | 19,5 h | 61,6 h | 17,3 h |
| 2024 | 18,3 h | 69,7 h | 18,6 h |
| 2025 | 17,4 h | 80,2 h | 23,8 h |
| 2026 (ene–9 abr) | 19,8 h | 81,9 h | 23,8 h |

#### 5.4 La hora del día manda más que el número de camas
- **Altas tardías (hipótesis sostenida en 4 de 4 criterios):** el 62,7 % de las altas ocurre entre las 14:00 y las 18:59 y solo el 14 % antes del
  mediodía. Quien llega a las 8 h recibe cama al día siguiente en el 50 % de los casos; a las 16 h, en el 72 %.
- **La cama llega en dos olas:** 23,8 % entre las 15 y las 17 h y 37,5 % entre las 20 y las 23 h (61 % juntas); 8,9 % entre las 6 y las 11 h.
  Parte de la ola nocturna podría ser la hora en que se digita en el sistema.
- **Límite de proceso:** una cama liberada entre las 6 y las 12 h tarda una mediana de 1,8 h en volver a asignarse (un tercio tarda más de 3 h),
  aunque haya ~26 pacientes esperando; las de la tarde tardan 0,4 h (`docs/saturacion_y_espera.md` 3).
- **El orden de llegada casi no predice el orden de cama** (53 % de pares en orden; el azar daría 50 %): no hay una fila única.

![Altas e ingresos a cama por hora](../resultados/graficos/altas_ingresos_por_hora.png)

#### 5.5 La saturación mueve la cola larga, no la espera típica
- El hospital está saturado casi siempre: en adultos nunca hay una hora sin pacientes esperando cama y el 75 % de las horas tiene el 90 % o más de
  las camas ocupadas.
- Cada 10 camas ocupadas más al llegar suben la espera ~7 % (adultos +7,2 %, IC 95 % +3,5 a +11,1); la **mediana casi no cambia** (18,7 h con
  ≤ 90 camas, 19,8 h con más de 115) pero el **p90 pasa de 60 a 80 h** (`docs/saturacion_y_espera.md`).
- La cola de pacientes esperando cama (media de 26) no depende de la ocupación: no se puede estimar un «techo» de camas desde los datos
  (`docs/capacidad_efectiva.md`).
- **La ocupación sube por la estancia:** 94 → 101 → 105 camas (2023–2025) con ingresos estables (20,6 → 19,8 por día) y estancia media de 4,57 a
  5,31 días. Con la ley de Little, volver a la estancia de 2023 liberaría ~15 camas. El exceso sobre las 106 camas está en **adultos** (101 % de
  sus 88 camas en 2025) y viene de estancias largas con actividad clínica diaria, no de camas «fantasma» (`docs/ocupacion_por_zona.md`,
  `docs/dias_cama_baja_actividad.md`). Pasar de 106 puede ser sobreocupación o una capacidad real mayor; los datos no lo distinguen.

#### 5.6 Dónde se va el tiempo dentro de urgencias
- Cada estancia tiene en promedio 2,5 etapas de urgencias seguidas. **El tiempo extra de las esperas largas está en la última etapa antes de la
  cama:** 53 % de la espera en quienes esperan menos de 6 h, 63 % entre 12 y 48 h y **78 %** en quienes esperan más de 72 h (mediana de 69 h).
- En esa última etapa hay ~1 laboratorio cada 10 h y casi ningún diagnóstico nuevo: es compatible con un paciente ya decidido que espera cama.
  **Hipótesis:** la base no dice qué es cada etapa (`docs/caracterizacion_etapas_tu.md`, `docs/etapas_tu_por_examen.md`).

#### 5.7 Qué factores se asocian a la espera y a la estancia

**Espera de cama** (modelo sobre el logaritmo, R² = 16 %: el 84 % de la variación no se explica con lo observado; `docs/HALLAZGOS.md` 4.5):
diagnóstico 7,2 puntos de R², edad y sexo 4,1, tipo de visita 2,0, hora de llegada 0,6, carga y año 0,1 cada uno, calendario ~0.

**Modelo explicativo de A4** (regresión logística sobre «esperar más de 24 h», validada en tres tramos temporales; `docs/modelo_espera.md`):
AUC de 0,68 en la prueba de 2026. Esperan más los de 30 a 59 años (OR 1,6–1,8 frente a 15–29), las **mujeres (OR 1,37)** y quienes llegan con
más carga reciente (OR 1,25 por desviación); esperan menos los niños de 0 a 4 años (OR 0,40) y las visitas ambulatorias (OR 0,16). Su valor
está en explicar qué perfiles esperan más; para avisar paciente por paciente se usa el estimador de la sección 6.4.

**Quién es el paciente** (`docs/que_esperar_segun_paciente.md`, `docs/perfiles_pacientes.md`):

| Característica | Espera de cama (mediana) | Estancia en cama (mediana) |
|---|---|---|
| Edad | Niños 0–4: 7,8 h; 5–14: 12,3 h; 15–29: 17,2 h; desde 30: 24–27 h | Sube con la edad: 52–68 h hasta los 44; 103 h desde los 75 |
| Sexo | **Mujeres 22,3 h frente a 14,3 h** (+27 % con todo controlado) | Sin diferencia |
| Tipo de visita | Urgencias 20,8 h; «Treatment urgency» 9,8 h; ambulatoria 11,3 h | «Treatment urgency» 112 h (+63 %) |
| Hora de llegada | Madrugada 12–15 h; tarde ~25 h | Sin efecto |

- **Hallazgo abierto:** las mujeres esperan cama +27 % más (IC 23 a 31 %) controlando edad, tipo de visita, franja y año. No es obstetricia (sin
  embarazo ni ginecología la diferencia crece) ni la saturación del momento. Hipótesis sin comprobar: camas agrupadas por sexo. No es una rareza
  del HUN: en dos hospitales de Boston (38.766 ingresos) las mujeres también tienen más probabilidad de esperar 4 h o más por una cama (OR 1,08;
  Olson y colegas, *J Hosp Med* 2025), aunque la brecha del HUN es mucho mayor.
- **Diagnóstico** (`docs/diagnosticos_todos.md`, 69 % de las estancias con diagnóstico de la persona real): esperan menos cardiovascular,
  neurológico y respiratorio (~9–13 h); más musculoesquelético (+64 % ajustado), renal, cáncer y digestivo (29–39 h). El diagnóstico se
  registra tarde: sirve para explicar, no para predecir al llegar.
- **Gravedad y servicio** (desde los procedimientos de cada estancia, sin fecha): UCI recibe cama en una mediana de 2,7 h; urología (37,7 h),
  ortopedia (32,8 h) y cirugía general (29,6 h) esperan más.
- **Laboratorios de las primeras 6 h** (`docs/espera_con_labs_y_severidad.md`): con troponina alta la espera es 42 % menor; con BUN o lactato
  alto ~16–17 % menor; con PCR alta 16 % mayor y con creatinina alta 13 % mayor. Sumados se cancelan; por separado ayudan al estimador.

**Estancia larga** (`docs/factores_estancia.md`, `docs/estancias_disparadas.md`): la estancia media subió 16 % y **cerca de la mitad del aumento
viene de las estancias de más de 30 días** (de 63 a 117 por año). Las largas (más de 14 días, 6,5 %) se asocian con la edad (×3 desde los 75 años),
la visita «Treatment urgency» (×2,4) y diagnósticos de cáncer, infecciosas y salud mental. Quien entra a cama un sábado se queda 12 % más
(`docs/efecto_fin_de_semana.md`).

#### 5.8 Lo que no explica la espera
El día de la semana y los festivos casi no la cambian; ningún día tuvo una espera más alta de lo esperado (el problema es crónico, no de días
puntuales; `docs/dias_atipicos.md`); las camas de baja actividad clínica son ~6 y no crecen.

---

### 6. Modelos, predicción y simulación (componente 3)

Construimos un conjunto de herramientas que permiten **anticipar** lo que va a pasar en el hospital: cuántos pacientes llegarán, qué días se
congestionará urgencias, cuándo recibirá cama cada paciente, qué pasaría con las camas en distintos escenarios y, con el simulador integral (6.9), cómo se mueven a la vez la demanda, la cola y la ocupación cuando se cambia una decisión. Todas se validaron con el método más
exigente: entrenar con el pasado y probar con meses que el modelo nunca vio, y siempre frente a una referencia simple para demostrar que aportan.

**Por qué estos modelos y no otros.** Para cada pregunta se eligió el método más simple que diera el mejor resultado en datos que no había visto, y que un
hospital pudiera leer:

| Pregunta | Modelo elegido | Por qué | Lo que se descartó (6.8) |
|---|---|---|---|
| ¿Cuántos pacientes llegan y cuántos van a cama cada día? | Regresión de Poisson con día de la semana, festivos, Carnaval, nivel reciente y forma del año | Son conteos; cada efecto se lee como un porcentaje; error de 7,9 % a 1–7 días | SARIMAX y otros modelos de series (peor a corto plazo), quincenas, deduplicar llegadas |
| ¿Hoy será un día congestionado? | Clasificador logístico sobre lo que ya llegó hasta las 12 h, mezclado con el pronóstico | Simple y con AUC de 0,94; avisa a media jornada | Alerta un día antes (AUC 0,61) |
| ¿Cuándo recibirá cama este paciente? | Supervivencia hora a hora con árboles de gradiente (un modelo por hora de espera) | Da la distribución completa del tiempo que falta y se actualiza con lo que pasa; percentiles calibrados | Fila «primero en llegar» (el orden no se cumple), cuantiles al llegar, modelo de cola, LightGBM y XGBoost (mismo nivel) |
| ¿Qué perfiles esperan más y por qué? | Regresión logística y regresión sobre el logaritmo de la espera | Coeficientes interpretables con intervalos; explica, no reemplaza al estimador | Alertar por riesgo al llegar (marcaría al 44 % con 4 de cada 10 falsas alarmas) |
| ¿Se van a saturar las camas? | Simulación Monte Carlo con estancias reales por perfil (edad y ruta) sobre los ingresos pronosticados | Respeta la cola larga de las estancias y da probabilidades de superar las 106 camas; cobertura 86 % en el backtest | Predecir la estancia de cada paciente (R² ≈ 0), proyección con altas esperadas (peor que «lo mismo que ahora») |
| ¿Cuántos esperarán cama en 6–12 h? | Modelo de flujo (entradas y salidas de la cola) | Un tercio menos de error que suponer que todo sigue igual | Persistencia y tasa típica |
| ¿Cómo se mueven a la vez la demanda, la cola y las camas? | Un solo motor de agentes (simulador integral) que sigue a cada paciente simulado | Las tres vistas salen del mismo paciente y se validaron contra la cola y la ocupación reales | Encadenar pronóstico, estimador y Monte Carlo en serie (6.9) |

#### 6.1 Pronóstico de demanda (`src/modelo_pronostico.py`; página de pronóstico del dashboard)
Un modelo de Poisson que combina el calendario (día de la semana, festivos, semana santa, fin de año y el **Carnaval de Barranquilla**, que reduce las
llegadas ~17 %) con **la forma del año** tomada de datos públicos de vigilancia.
- **Llegadas con atención:** error de **8,0 % a una semana y 9,6 % a un año**. Con unos 200 pacientes al día, a un año el pronóstico se equivoca en unos
  19 pacientes diarios.
- **Ingresos a cama:** error de **9,5 % por semana**, que es como se planean las camas. A nivel diario el error (~18 %) está prácticamente en el mínimo que
  permite el azar en un conteo de ~20 ingresos al día.
- **Rango probable del 80 %:** en meses que el modelo no vio cubre el 78–82 % de los días en las llegadas, justo lo que promete; en los ingresos es
  conservador.

**La forma del año (ficha A9, `docs/estacionalidad_anual.md`).** Con solo tres años de datos del hospital no se puede aprender qué épocas del año traen
más pacientes, así que la tomamos de **datos públicos de muchos años** y la validamos con datos que el modelo no conocía:
- **En las llegadas, la forma del año del dengue en Barranquilla** (2007–2022, SIVIGILA, publicada por Drexel, Los Andes y Uninorte) **bajó el error a largo
  plazo de 11,6 % a 9,6 %** (de 11,4 % a 9,1 % a 3–6 meses), sin afectar el corto plazo. Funciona como un marcador de la temporada del año.
- **En los ingresos a cama, la forma del año de la infección respiratoria aguda (IRA) y la diarrea aguda (EDA)**, que obtuvimos de los microdatos
  oficiales del SIVIGILA del Instituto Nacional de Salud, **mejora todos los horizontes y se confirmó en 2026**, un periodo que no se usó para elegirla
  (19,8 % → 19,3 % a 1–6 meses). Las dos enfermedades tienen el pico en junio, en la temporada de lluvias, igual que la demanda de camas.
- **Rigor:** se evaluaron todas las fuentes que pedía la ficha (lluvia de NASA y del IDEAM, temperatura, calendario escolar oficial, El Niño, población
  del DANE) y un modelo más complejo (SARIMAX); solo se adoptó lo que mejoró en datos nuevos. Por eso el modelo sigue siendo un Poisson
  interpretable: cada variable tiene un efecto que se puede leer.

| Error diario (WAPE) | 1–7 días | 1–3 meses | 3–6 meses | 6–12 meses |
|---|---|---|---|---|
| Llegadas con atención, sin forma del año | 8,0 % | 9,3 % | 11,4 % | 11,6 % |
| **Llegadas con atención, con dengue (vigente)** | **8,0 %** | **8,6 %** | **9,1 %** | **9,6 %** |
| Ingresos a cama, con curva del año | 18,2 % | 19,3 % | 19,7 % | 19,4 % |
| **Ingresos a cama, + IRA y EDA (vigente)** | **18,0 %** | **18,7 %** | **19,3 %** | **19,0 %** |

![Pronóstico de demanda con la forma del año](../resultados/graficos/pronostico_futuro.png)

![Climatologías y efecto de la estacionalidad](../resultados/graficos/estacionalidad_anual.png)

#### 6.2 Alertas (`src/alertas.py`, probadas reproduciendo días de 2026)

| Alerta | Resultado |
|---|---|
| A. Día congestionado, a las 12 h | **Detecta 13 de cada 15 días congestionados** (AUC 0,94), con apenas una alerta cada cuatro días |
| B. Ocupación alta a 24 h | AUC 0,82: identifica 3 de cada 4 días con ocupación alta |
| C. Paciente sin cama a las 48 h | ~4 alertas por día; la mitad de esos pacientes terminaría esperando más de 72 h, así que avisa con 24 h de margen |

En conjunto son unas 4–5 alertas al día: una carga manejable para una reunión diaria de camas.

En el dashboard, la página **Alertas** (categoría Riesgo) muestra la prueba de cada alerta, y el **simulador integral** (6.9) las dispara mientras corre, con la recomendación de la que se derivan. Cada alerta apunta a una o más de las siete recomendaciones (sección 7): día congestionado y ocupación alta, a la reunión diaria de camas y a adelantar las altas; paciente sin cama, a la alerta con responsable.

#### 6.3 Días atípicos (`src/dias_atipicos.py`)
El modelo identifica automáticamente los días que se salen de lo esperado (14 de llegadas, 9 de ingresos y 7 de espera). Los más extremos coinciden con
cortes de registro, lo que también sirve para vigilar la calidad de los datos. Un hallazgo útil: ningún día tuvo una espera fuera de lo normal, así que
el problema de la espera es estructural, no de días puntuales.

#### 6.4 Estimador de la espera de cada paciente (A6; `docs/estimador_tiempos.md`; página «Paciente en espera»)
- **Qué hace:** para un paciente que ya tiene orden de hospitalización y espera cama, estima cuánto le falta (con su rango) y la probabilidad de recibir
  cama en 6, 12 y 24 horas, y se actualiza hora a hora mientras espera. Usa un modelo de supervivencia en tiempo discreto con árboles de gradiente.
- **Qué usa:** edad, sexo, tipo de visita, la hora, la ocupación del hospital, el historial del paciente, su recorrido en urgencias y, desde las 6 horas,
  las alertas de sus laboratorios.
- **Resultado** (probado con 5.430 estancias de jul-2025 a abr-2026 que el modelo no vio): mejora el rango **9,2 % al llegar y 11 % entre las 3 y las 6
  horas** frente a darle a todos el mismo rango, y le gana a cinco alternativas, incluidos modelos hechos desde cero con LightGBM y XGBoost. Su
  percentil 90 está bien calibrado (cubre ~91 %).
- **Extrae todo lo que permiten los datos:** más de 15 enfoques distintos llegan al mismo nivel. Si el hospital registrara la **gravedad y el servicio**
  al llegar, la mejora se duplicaría (de 8,4 % a 16,9 %).
- **Uso diario:** responde en ventanas del día («esta tarde», «mañana en la noche»); da el censo para la reunión de camas (cuántos de los que esperan
  tendrán cama en 12 o 24 horas, con un rango que acierta el 87–88 % de los días); y avisa a las 12 horas quién seguirá sin cama a las 48 (4 por día,
  con 12 horas más de margen que esperar a las 24).

![Comparación de estimadores](../resultados/graficos/comparacion_estimadores.png)

#### 6.5 Simulación Monte Carlo de camas (A5; `docs/modelo_camas.md`, `docs/simulacion.md`)
**Qué responde:** ¿cuántas camas estarán ocupadas en los próximos meses, qué tan seguido se superará la capacidad del hospital y qué pasaría si
cambian los ingresos o la estancia? Es la pregunta del instructivo sobre «el efecto de cambios operativos en la ocupación y la disponibilidad de camas».

**Cómo funciona.** Se simulan los próximos 180 días 1.000 veces. Cada día, el número de ingresos sale de una distribución de Poisson alrededor del
pronóstico de demanda (sección 6.1); a cada paciente se le asigna un **perfil real** (grupo de edad y ruta de llegada: urgencias, «Treatment urgency»
o ambulatorio, con la mezcla real de 2025) y una estancia tomada al azar de pacientes reales con ese mismo perfil (2024–2025, 21 combinaciones de edad
y ruta). Así la simulación respeta que los mayores de 75 años se quedan una mediana de 100 horas frente a 59 de los jóvenes, y que la ruta «Treatment
urgency» se queda 63 % más. El censo se separa en **adultos (88 camas) y niños (18 camas)** con el desglose que dio el hospital.

**Validación (puerta de decisión de la ficha).** Entrenada solo hasta diciembre de 2025 y probada en enero a abril de 2026, la ocupación real cayó
dentro de la banda del 80 % el **78,8 % de los días** (la meta era 70–90 %), con un error medio de 8,6 camas sobre una ocupación de ~105, es decir
~7 %. El modelo predice bien porque pronostica un número agregado (todo el hospital), donde el ruido de cada paciente se compensa.

**Riesgo de saturación en los próximos 180 días:**

| Grupo | Capacidad | Días en que se supera (promedio del horizonte) |
|---|---|---|
| Total del hospital | 106 camas | **65 %** |
| Adultos | 88 camas | **71 %** |
| Niños y neonatos | 18 camas | 35 % |

El resultado es robusto: con un umbral independiente del dato del hospital (el percentil 90 de la ocupación real observada, 109,5 camas) el riesgo sigue
siendo alto (55 %). La presión está en los adultos, que en 2025 ya operaron en promedio al 100 % de sus camas.

**Escenarios «¿qué pasaría si…?»:**

| Escenario | Ocupación media | Días saturados (total) | Lectura |
|---|---|---|---|
| Hoy, sin cambios | 111,1 camas | 65 % | Punto de partida |
| Ingresos +10 % (brote o temporada alta) | 121,9 camas | 91 % | El escenario más costoso: 9 de cada 10 días saturados |
| **Estancia −5 %** | **106,2 camas** | **48 %** | Libera ~5 camas sin necesitar ninguna nueva |
| Ruta «Treatment urgency» del 13,5 % al 27 % | 118,1 camas | 85 % | Si sigue creciendo como entre 2023 y 2025 |

**La estancia es la palanca más barata:** bajarla apenas 5 % mueve la ocupación casi tanto como la subiría un 10 % más de pacientes. La ley de Little
llega al mismo número (~5 camas) por un camino distinto, y tres versiones del simulador coinciden: eso da confianza en la cifra. La simulación también
dice **dónde mirar**: los mayores de 60 años (se quedan 33–46 % más), la ruta «Treatment urgency» y las estancias de más de 30 días, que explican la
mitad del aumento de la estancia.

**Curva de capacidad.** En lugar de preguntar si «más camas ayudan», la simulación calcula cuántas harían falta para que el riesgo de saturación baje a
10 % o menos: **~126 camas en total (+20)**, de las cuales 108 serían de adultos (+20) y 22 de niños (+4). El umbral de riesgo es un parámetro: el
hospital puede recalcularlo para el nivel que considere aceptable, y en el dashboard se mueve con un control.

![Simulación de camas](../resultados/graficos/simcamas_resultados.png)

#### 6.6 Pronóstico de la cola de pacientes sin cama y de la espera del sistema (`docs/pronostico_espera_sistema.md`)
**Qué responde:** ¿cuántos pacientes seguirán esperando cama dentro de unas horas, y cuánto esperará en promedio quien llegue hoy? Es el complemento
de la simulación de camas: aquella mira las camas ocupadas; esta mira la fila de pacientes que esperan una.

**El modelo de flujo.** La cola de dentro de unas horas es la cola de ahora, más las llegadas que terminarán en hospitalización, menos las camas que el
hospital suele asignar a esa hora y ese día de la semana. En la prueba (julio de 2025 a abril de 2026, una cola media de 28 pacientes):

| Horizonte | «Lo mismo que ahora» | **Modelo de flujo** | Mejora |
|---|---|---|---|
| 6 horas | 3,8 pacientes de error | **2,6** | **−33 %** |
| 12 horas | 5,5 | **3,5** | **−36 %** |
| 24 horas | 4,5 | **4,1** | −9 % |

A diferencia de la proyección de camas ocupadas a 24 horas, aquí el modelo sí le gana con claridad a suponer que todo sigue igual, justo en el horizonte
que le sirve a la reunión de camas de la mañana.

**De la cola a la espera: la ley de Little.** Se hospitalizan 0,85 pacientes por hora y la cola media es de 25,8, así que la espera media esperada es
de **30,4 horas, frente a 30,5 horas reales**. La relación se cumple casi exacta, lo que valida la coherencia de todos los datos de flujo. Con el
pronóstico de la cola, la espera media del sistema se estima con unas 3–4 horas de error sobre ~30.

**Qué aprendimos sobre la espera de cada paciente.** La saturación explica la espera del sistema, pero muy poco la de un paciente concreto: saber la
ocupación real al llegar mejora su rango solo 3,7 %, y la hora y el día, 0,4 %. Por eso cada herramienta tiene su uso: la cola y la ley de Little para
planear la jornada, y el estimador de la sección 6.4 para cada paciente.

#### 6.7 Diagnóstico repetible del cuello de botella (A7; `docs/diagnostico_cuello_botella.md`)
**Qué es:** convierte todo el análisis del cuello de botella en una herramienta que el hospital puede correr sobre **cualquier periodo** para saber si el
problema sigue siendo el mismo o cambió. Un solo comando genera un reporte con indicadores y recomendaciones, sin acceso a la base (lee las tablas ya
procesadas) y sin datos de pacientes en la salida.

**Los cinco pasos del reporte:**
1. **Dónde está el cuello de botella:** compara las partes de la espera de cama con una referencia de «cuando funciona bien» (la espera cuando llegan
   pocos pacientes), calculada con un periodo de referencia para que dos periodos se midan con la misma vara.
2. **Qué se dispara:** cuánto del exceso viene de esperas de más de 24, 48 y 72 horas; la ocupación frente a las 106 camas; la ley de Little; y el
   porcentaje de altas por la tarde.
3. **Qué registros se disparan:** estancias con esperas por encima del percentil 90 y estancias de más de 14 días.
4. **Qué comparten:** edad, tipo de visita, franja horaria, sexo y diagnóstico de los casos disparados frente al resto.
5. **Qué hacer:** frases ligadas a las recomendaciones de la sección 7 que solo aparecen si las cifras del periodo las activan.

**Pruebas:**
- **Todo el periodo confiable:** el cuello de botella es urgencias antes de la cama (98 % del exceso); las esperas de más de 48 horas son el 20 % de los
  pacientes pero el 75 % de las horas de exceso; el 63 % de las altas sale entre las 14 y las 19 horas.
- **2025 frente a 2023:** el cuello de botella no cambió de lugar, pero se agravó: el exceso medio por estancia pasó de 16,9 a 22,6 horas, los casos
  disparados subieron de 10 % a 15 % y la ocupación superó las 106 camas el 42 % de las horas.

Es la base para el seguimiento mensual de la recomendación 2: el hospital puede correrlo cada mes y ver de inmediato si las acciones están funcionando.

**En el dashboard** (página «Diagnóstico por periodo», categoría Clínico) se eligen un periodo (todo el periodo, cada año o cada semestre) y otro con el que compararlo; la página muestra el cuello de botella, cuánto cambió frente a la referencia, qué se dispara, qué estancias esperan muchísimo, qué tienen en común y las camas del periodo, cada resultado con su gráfica. Los reportes se calculan de antemano para cada combinación (`src/exportar_reportes_periodo.py`). El paso 5 («qué hacer») ya no se muestra ahí: las acciones se leen en la página de Recomendaciones.

#### 6.8 Alternativas evaluadas
Parte de la solidez de los modelos está en lo que se comparó para elegirlos. Cada alternativa se probó con el mismo método (datos que el modelo no
vio) y quedó documentada en el repositorio:

| Alternativa evaluada | Qué mostró | Qué se eligió en su lugar |
|---|---|---|
| Fila «primero en llegar, primero en cama» | El orden de llegada casi no predice el orden de asignación (53 % de pares en orden, frente a 50 % por azar) | Simular la ocupación con estancias reales por perfil (6.5) |
| Predecir la estancia de cada paciente al ingresar | Ni con diagnóstico ni con laboratorios se explica la estancia individual (R² de 0 a 0,02) | Trabajar la estancia en conjunto: simulación y ley de Little (6.5) |
| Alerta de espera larga desde la llegada | Con lo que se sabe al llegar, la discriminación es modesta (AUC 0,60–0,68) | El estimador que se actualiza hora a hora y la alerta a las 12 o 48 horas (6.2, 6.4) |
| Proyectar camas a 24 h con altas e ingresos esperados | Error de 3,7 camas, frente a 3,2 de «lo mismo que ahora» | La persistencia para la alerta de ocupación y el modelo de flujo para la cola (6.2, 6.6) |
| SARIMAX y otros modelos de series de tiempo | Mejor en validación, pero peor a 1–7 días y en 2026 | Poisson con la forma del año, más preciso e interpretable (6.1) |
| Quincenas, puentes y deduplicar las llegadas | Cambios de ±0,15 puntos de error; las réplicas son una proporción estable | Mantener el modelo más simple (6.1) |
| LightGBM, XGBoost y otros 13 enfoques para el estimador | Todos llegan al mismo nivel | El modelo de supervivencia, que además da probabilidades calibradas (6.4) |
| Encadenar pronóstico, estimador de espera y Monte Carlo en serie | Cada módulo se hizo para otra población y encadenarlos rompe sus supuestos | Un motor único de agentes con trayectorias reales sorteadas (6.9) |

Que alternativas muy distintas lleguen al mismo resultado confirma que los modelos elegidos aprovechan lo que permiten los datos, y señala con
precisión qué dato nuevo (gravedad, servicio y hora de la orden de hospitalización) haría el siguiente salto.


#### 6.10 Estimador de la estancia restante de cada paciente (A6b; `docs/estimador_estancia.md`; página «Paciente en cama»)
- **Qué hace:** para un paciente que YA tiene cama asignada, estima cuánto le falta para el alta (con su rango) y la probabilidad de recibir el alta en 1,
  3 y 7 días, y se actualiza con las horas que lleva en cama. Usa el mismo tipo de modelo de supervivencia en tiempo discreto del estimador de espera
  (6.4), aplicado por primera vez a la estancia: un modelo por cada hora **ya transcurrida en cama**, no uno solo al momento del ingreso.
- **Por qué se vuelve a intentar:** ya se había descartado un estimador de estancia por mala precisión — una prueba rápida (21-oct) con regresión al
  ingreso dio R² ≈ 0,00-0,02 (igual que adivinar la mediana), y un modelo explicativo con más variables (`factores_estancia.py`, 3-nov) solo llegó a
  R² = 7,9-10,8 %, declarado como «explica, no predice». Ambos intentaban resolver, de una sola vez al ingresar, la estancia TOTAL; nunca se había
  probado la arquitectura que sí funciona para la espera (un modelo por hora ya transcurrida).
- **Qué usa:** edad, sexo, tipo de visita, horas ya en cama, la hora, la ocupación del hospital, el historial de hospitalizaciones anteriores (incluido
  el diagnóstico de esa visita anterior) y sus laboratorios del ingreso. NO usa el diagnóstico de esta estancia (se registra tarde: fuga) ni el
  recorrido en urgencias (pertenece al tramo antes de la cama).
- **Resultado** (probado con 3.900 estancias de jul-2025 a 9-ene-2026 que el modelo no vio, contra el rango por perfil que ya usa el dashboard): mejora
  **1,6 % al asignarse la cama (IC 95 % 0,9 a 2,4 %)**, bajando con las horas y modestamente negativa desde las 120 h (muestra de prueba ya chica). Es
  real pero mucho menor que el ~9-11 % del estimador de espera: lo que no se registra (servicio, tipo de cama, gravedad clínica) sigue explicando la
  mayor parte de cuánto dura una estancia. Se publica igual, con este límite explícito.
- **Mejora metodológica:** a diferencia de `que_esperar.py` y `factores_estancia.py`, las estancias sin alta resuelta no se descartan — aportan al
  entrenamiento como censuradas, sin sesgar contra las estancias largas.

---

### 7. Recomendaciones (componente 4)

Las recomendaciones salen directamente de los hallazgos: el problema no es solo cuántas camas hay, sino **cuándo se liberan, cuándo se asignan y
cuánto tiempo se quedan ocupadas**. Por eso proponemos siete acciones, ordenadas de la más básica a la más específica. Cada una se apoya en dos
cosas: lo que muestran los datos del HUN y lo que se ha encontrado en otros hospitales. En total se revisaron **38 fuentes**, y cada una se leyó en
su versión original (el detalle, con el nivel de verificación de cada fuente, está en `docs/recomendaciones.md`).

**Por qué vale la pena actuar.** Esperar mucho por una cama no es solo incómodo: en un estudio de 41.256 ingresos, la mortalidad pasó de 2,5 % en
quienes esperaron menos de 2 horas a 4,5 % en quienes esperaron 12 horas o más (Singer 2011), y una revisión de 21 estudios asocia las esperas largas
con más errores de medicación y retrasos en el tratamiento (Dowling 2026). En el HUN, uno de cada cinco pacientes espera más de 48 horas.

| # | Qué proponemos | Por qué, según nuestros datos | Firmeza |
|---|---|---|---|
| 1 | Registrar mejor la información | Sin la hora de salida de urgencias ni la de asignación de cama no se puede medir el problema | Alta |
| 2 | Seguir seis indicadores cada mes | Hoy no hay una meta ni una línea base compartida | Alta |
| 3 | Reunión diaria de camas a media mañana | La alerta de las 12 h detecta 13 de cada 15 días congestionados | Alta |
| 4 | Meta de altas antes del mediodía (25–30 %) | Solo el 14 % de las altas sale antes del mediodía; adelantarlas liberaría hasta 5,1 camas a las 12 h | Media |
| 5 | Alerta por paciente que lleva 48 h sin cama | Uno de cada dos de esos pacientes termina esperando más de 72 h | Alta |
| 6 | Pedir antes la cama de quien llega por la tarde | Quien llega entre las 13 y las 18 h espera ~8 h más que quien llega en la mañana | Media |
| 7 | Revisar cada semana las estancias largas | La ocupación subió porque los pacientes se quedan más, no porque lleguen más | Media |

**1. Registrar mejor la información.** Es la base de todo lo demás. Hoy el 36–42 % de las atenciones de urgencias no tiene hora de salida, no se
registra cuándo se decide hospitalizar al paciente y el 41 % de las estancias aparecía duplicado en otra persona. Proponemos registrar la hora de
salida de urgencias, la de la orden de hospitalización, la de asignación de cama, el triage y el servicio. Un hospital de Estados Unidos empezó justo
por ahí y luego redujo a la mitad el tiempo entre decidir el ingreso y pedir la cama (Imhoff 2022); además, existen definiciones estándar para cada
una de estas horas (Welch 2011; Yiadom 2020). Con el triage y el servicio, nuestro estimador de espera duplicaría su mejora.

**2. Seguir seis indicadores cada mes.** Lo que no se mide no se puede mejorar. Proponemos seguir la espera de cama (hoy 18,6 h en mediana y 73,9 h
en el percentil 90), el porcentaje de pacientes con más de 48 h sin cama (19 %), las altas antes del mediodía (14 %), la hora típica de asignación
(17–18 h), las camas ocupadas a las 12 h (~103) y la estancia media (5,3 días). El principal acreditador de hospitales de Estados Unidos, la Joint
Commission, exige medir el flujo de pacientes y fijar una meta para la espera de cama, con 4 horas como referencia.

**3. Reunión diaria de camas a media mañana.** Una reunión corta (10–15 minutos) para revisar el censo, las altas previstas y los ingresos esperados,
apoyada en las alertas que construimos: la de día congestionado a las 12 h acierta 13 de cada 15 días, y el pronóstico de la cola de pacientes sin
cama se equivoca un tercio menos que suponer que todo sigue igual. En seis hospitales de Arabia Saudita, un paquete de medidas que incluía una
reunión diaria de camas bajó la espera por cama de 16,6 a 9,5 horas (Alotaibi 2021); en Johns Hopkins, rondas de camas dos veces al día y un
responsable de camas bajaron 98 minutos el tiempo en urgencias de quienes se hospitalizan, sin cambio en la mortalidad (Howell 2008); y en otro
hospital un pase diario multidisciplinario la redujo a la mitad (Hammer 2022).

**4. Meta de altas antes del mediodía.** Hoy solo el 14 % de las altas sale antes del mediodía y el 63 % entre las 14 y las 19 horas, así que la
cama llega por la tarde. Proponemos empezar con una meta de 25–30 % de altas antes de las 12, con la ronda médica temprano y el alta preparada desde el
día anterior. Con el 30 % de las altas de la tarde movidas a la mañana quedarían hasta **5,1 camas libres a las 12 h**. Es una meta alcanzable: en
hospitales universitarios pasó de 11 % a 38 % (Wertheimer 2014) y de 9,5 % a 26,8 % (Bailey 2024), y en seis hospitales de Arabia Saudita de 16 % a 36 %,
junto con 7,1 horas menos de espera por cama (Alotaibi 2021). Rinde más si la cama que se libera se asigna enseguida: hoy tarda 1,8 horas en la mañana,
aunque siempre hay unos 26 pacientes esperando, y varios proyectos muestran que acortar ese paso reduce la espera (Erdmann 2024; Farok 2026; Howell 2008).

**5. Alerta por paciente que lleva 48 h sin cama.** Cuando un paciente cumple 48 horas sin cama, un responsable revisa su caso. Serían unas
cuatro alertas por día, con 24 horas de margen antes de que la espera supere las 72 horas, que es lo que le pasa a la mitad de ellos. Con nuestro
estimador se puede alertar antes, a las 12 horas. La alerta solo sirve si dispara una acción clara, como buscar cama en otra zona o escalar a la
dirección; en otros hospitales, pasar al paciente a la planta cuando urgencias se llena no aumentó la mortalidad (Viccellio 2009).

**6. Pedir antes la cama de quien llega por la tarde.** Quien llega entre las 13 y las 18 horas y se hospitaliza espera una mediana de 24 horas,
frente a 16 de quien llega en la mañana, porque queda fuera de la ola de asignación de la tarde. Proponemos adelantar la decisión de ingreso y la
solicitud de cama para esos pacientes. Varios estudios respaldan que adelantar ese paso acorta la espera: un protocolo de ingreso rápido la bajó de
360 a 270 minutos (Amarasingham 2010) y una simulación estima reducciones de 30 a 70 % al pedir la cama según la probabilidad de ingreso (Cheng
2026, aún sin revisión por pares). Lo que no sabemos es cuánto ahorraría en el HUN: entre el 2 % y el 11 % del exceso de espera, según cómo se mida.

**7. Revisar cada semana las estancias largas.** La ocupación pasó de 94 a 105 camas entre 2023 y 2025 porque la estancia media subió 16 %, no
porque lleguen más pacientes; las estancias de más de 14 días ocupan unas 36 camas. Proponemos una revisión semanal de los pacientes con más de 7
días, con foco en los de más de 14. Bajar la estancia apenas 5 % liberaría unas 5 camas y, según la simulación, bajaría los días saturados de 65 % a
48 %. En otros hospitales, un equipo que se reúne cada semana bajó la estancia de los pacientes con alta demorada de 15,5 a 9 días (Ibrahim 2022), y
una herramienta de seguimiento diario la redujo de 19 a 14 días en un hospital universitario de Brasil (Paiva 2024).

**Qué cambiar, en concreto.** Cada recomendación se traduce en pasos y en una meta con la que se sabe si funcionó (la página de Recomendaciones del dashboard las muestra ordenadas por firmeza):

| # | Qué cambiar | Meta |
|---|---|---|
| 1 | Hacer obligatoria la hora de salida de urgencias, registrar la hora de asignación de cama y la de la orden de hospitalización, y revisar cada mes que un ingreso no quede en dos pacientes | 100 % de las atenciones con hora de salida y ningún ingreso duplicado |
| 2 | Definir una meta propia de espera de cama (la guía internacional usa 4 horas) y revisar cada mes seis cifras con la dirección de urgencias y de hospitalización | Una meta escrita y las seis cifras en la reunión mensual |
| 3 | Reunir 10 a 15 minutos antes del mediodía a quien administra las camas, urgencias y los pisos, con el censo, las altas y los ingresos previstos y las alertas | La reunión se hace todos los días y se anotan las alertas atendidas |
| 4 | Pasar la ronda médica a primera hora, dejar preparada el día anterior el alta de la tarde y asignar la cama liberada apenas queda libre | De 14 % a 25–30 % de altas antes de las 12 h; asignar la cama en menos de 1,8 h |
| 5 | Dar a una persona por turno la lista diaria de pacientes con 48 h sin cama (unos 4 por día), revisarlos uno por uno y anotar qué se hizo | Ningún paciente con 48 h sin cama queda sin responsable |
| 6 | Para quien llega entre las 13 y las 18 h, pedir la cama en cuanto se decide hospitalizarlo, sin esperar el ciclo de altas del día siguiente | Que espere como quien llega por la mañana (hoy, 24 h frente a 16 h) |
| 7 | Reunir cada semana a quien coordina las altas con los médicos tratantes y revisar a quienes llevan más de 7 días, empezando por los de más de 14 | Bajar la estancia 5 % (unas 5 camas) |

**Qué no recomendamos.** Los datos no respaldan reforzar el personal según el día de la semana (casi no cambia la espera), ni ordenar la fila según
el riesgo de cada paciente al llegar (el mejor modelo marcaría al 44 % de los pacientes, con 4 de cada 10 falsas alarmas), ni un centro de comando
como solución por sí mismo (el estudio mejor diseñado no encontró efecto). Tampoco permiten calcular cuántas camas más harían falta: antes de
pensar en camas nuevas, conviene atacar la estancia y el proceso de asignación.

**Cómo leer la firmeza.** Una recomendación tiene firmeza **alta** cuando cumple tres condiciones: los datos del HUN muestran el problema con
claridad; al menos tres estudios independientes, o uno multicéntrico, coinciden en que actuar ahí ayuda (o, para las alertas, en que el problema
vigilado se asocia con daño); y la acción es de bajo costo y riesgo. Las recomendaciones 1, 2, 3 y 5 las cumplen; la 4, la 6 y la 7 quedan en **media** porque
algunos estudios no encuentran el mismo efecto o porque el ahorro en el HUN depende de cómo se aplique. La 5 es la más débil de las altas: lo respaldado es el daño de esperar,
no el efecto de la alerta misma. Ninguna cifra de impacto es una promesa: son escenarios con supuestos escritos, y casi todos los estudios
externos son de antes y después, sin grupo de comparación.

---

### 9. Limitaciones

- **Calidad del registro:** 30 % de visitas copia y 41 % de estancias duplicadas (resueltas con reglas documentadas); 36–42 % de etapas de
  urgencias sin hora de salida; registro degradado desde el 10-abr-2026 (causa no explicada por el hospital).
- **Lo que no está en la base:** triage, servicio, piso o cama, hora de la orden de hospitalización, hora de los procedimientos y signos
  vitales. Por eso la espera de cama mezcla atención clínica y espera pura, y no se separan.
- **La persona real** en las estancias duplicadas se deduce de los datos (97,6 %); el hospital no la confirmó.
- **Capacidad:** las 106 camas son el dato del hospital sin fecha; la ocupación lo supera el 42 % de las horas de 2025 y no se sabe si es
  sobreocupación o capacidad mayor.
- **Validación:** solo ~3 ciclos anuales confiables (feb-2023 a abr-2026); algunas decisiones del estimador se tomaron mirando la prueba (se
  corrigió con un periodo de validación aparte para el corte y el p90).
- **Geografía:** según los directorios de establecimientos de salud, el HUN está en Soledad, en el área metropolitana de Barranquilla; se usan el
  Carnaval, el calendario y los datos públicos de Barranquilla como los de la zona. No se sabe de qué municipio viene cada paciente.
- **Datos externos de 2026:** el INS aún no publica por semana el dengue, la IRA ni la EDA de 2026, así que la forma del año usa climatologías de
  años anteriores y no hay un aviso de corto plazo con casos recientes.
- **Diagnósticos:** registrados tarde, en SNOMED y sin jerarquía; el agrupamiento (`mapeo_dx.csv`) es un borrador sin validación clínica.
- **Causalidad:** casi todo son asociaciones; las cifras de impacto son escenarios y cotas con supuestos escritos.

---

### 11. Anexos

#### 11.1 Glosario
| Término | Significado |
|---|---|
| Episodio | Atención continua de un paciente dentro de una visita; se corta tras 168 h sin etapas |
| Estancia única | Una estancia en cama contada una sola vez aunque aparezca en dos registros |
| Espera de cama | Desde la llegada hasta la asignación de cama (primera etapa de hospitalización) |
| Percentil 90 (p90) | El tiempo que supera el 90 % de los pacientes: «1 de cada 10 espera más» |
| Exceso | Horas por encima de la referencia de «cuando funciona bien», sumadas por paciente |
| Ley de Little | Camas ocupadas = ingresos por día × estancia media |
| AUC | Qué tan bien separa una alerta: 0,5 = azar, 1 = perfecta |
| WAPE | Error relativo de un pronóstico: suma de errores absolutos entre suma de lo real |
| Mejora frente al rango general | Cuánto baja la pérdida de cuantiles del estimador frente a darle a todos los mismos percentiles |
| Monte Carlo | Simular muchos futuros posibles al azar para obtener probabilidades |
| Triage | Clasificación de la gravedad del paciente al llegar a urgencias |
| Troponina, lactato, PCR, BUN, creatinina | Exámenes de sangre: daño al corazón, falta de oxígeno, inflamación o infección, y función del riñón |


# Fuente: docs/HALLAZGOS.md

### 1. Glosario

| Término | Significado en este proyecto |
|---|---|
| **OMOP** | Formato estándar de datos clínicos. La base está en el esquema `uninorte_omop` (PostgreSQL). |
| **Visita** | Una fila de `visit_occurrence` (un id administrativo). |
| **Etapa** | Una fila de `visit_detail`: un tramo de la visita con inicio y fin. Solo hay 4 tipos. |
| **ER** (9203) | Registro de llegada o triage a urgencias. Dura minutos. |
| **TU** (3045729) | Atención en urgencias, incluida observación y espera. |
| **HOSP** (9201) | Paciente en cama de hospitalización. |
| **AMB** (581479) | Evento ambulatorio administrativo de duración cero; se descarta. |
| **Episodio** | Atención continua de un paciente dentro de una visita. Se corta cuando pasan más de 168 h sin ninguna etapa. Unidad de análisis. |
| **Estado del episodio** | `medida` (duración confiable), `minimo_conocido`, `minimo_dx`, `sin_duracion`, `sin_actividad`. |
| **Estancia gemela** | La misma estancia en cama registrada en dos personas (mismo inicio y fin de HOSP). Se cuenta una sola vez. |
| **Estancia única** | La que se queda tras quitar las gemelas (la de menor `visit_occurrence_id`). |
| **Espera de cama** | Desde el inicio del episodio hasta el inicio de la primera HOSP. |
| **Urgencias antes de la cama** | Desde el inicio del episodio hasta el fin de lo que había antes de la HOSP. |
| **Hueco antes de la cama** | Tiempo sin ninguna etapa registrada justo antes de la HOSP. |
| **Segmento** | Un tiempo medido de un episodio (espera de cama, urgencias antes de la cama, hueco, estancia en cama...). |
| **p25, p50, p75, p90** | Percentiles: el 25 %, 50 % (mediana), 75 % o 90 % de los casos tarda esto o menos. |
| **Exceso** | `max(0, horas − referencia)`; sumado da horas-paciente perdidas. |
| **Referencia** | Valor de "cuando funciona bien": mediana con carga baja, o percentil 25 del segmento. |
| **Carga** | Llegadas de las 6 o 24 h previas, o pacientes en cama al llegar. |
| **WAPE** | Error relativo de un pronóstico: suma de errores absolutos / suma de lo real. Menos es mejor. |
| **AUC** | Qué tan bien separa una alerta: 0,5 = azar, 1 = perfecta. |

---

### 7. Lo que no sabemos (limitaciones y pendientes)
- **Número de camas** del hospital y **meta de tiempos**: desconocidos. El correo con las preguntas se envió al HUN y no tuvo respuesta; el HUN abrirá una sesión de preguntas (`docs/hun/sesion_de_preguntas.md`).
- **Por qué se degrada el registro de etapas desde el 10-abr-2026:** cambio de sistema o de extracción; la auditoría descarta que sea menos demanda (las visitas no bajaron).
- **Cuál de las dos personas es la real** en las estancias gemelas.
- **La espera en urgencias mezcla atención y espera de cama**; no se pueden separar con los datos.
- Las **llegadas** incluyen 4,3 % de réplicas (cota inferior; sin deduplicar a propósito, 4.9); la ocupación de urgencias (`ocup_tu`) y la cobertura por ruta cuentan todos los episodios.
- Todo son **asociaciones y escenarios**, no causas probadas.
- **El reparto de lo que falta, con responsable y entrega, está en `docs/pendientes_y_reparto.md`.** El modelo explicativo de la espera (A4) y la simulación Monte Carlo de camas (A5) ya están hechos (8 y 9-nov; ver 4.5 y 5.5). Pendiente de ensamblaje: documento final y dashboard en Dash (Samuel/B1). `mapeo_dx.csv` queda como borrador sin validación clínica (limitación declarada).

---

### 8. Preguntas frecuentes (con respuesta y dónde verificarla)

| Pregunta | Respuesta corta | Dónde |
|---|---|---|
| ¿Cuánto espera un paciente por cama? | Mediana 18,6 h, percentil 90 73,9 h; el 44 % más de 24 h | 4.2; `src/construir_segmentos.py` |
| ¿Dónde está el cuello de botella? | En la espera de cama, sobre todo en urgencias antes de la cama (77 % de las horas) | 4.1–4.2 |
| ¿Está empeorando? | Sí, los peores casos: percentil 90 de 61 h (2023) a 80 h (2026); la mediana no | 4.3 |
| ¿Faltan camas? | No se puede afirmar: la ocupación (99 % de las 106 camas reportadas en 2025, 42 % de las horas por encima) subió por las estancias largas (+16 % de estancia media), no por la demanda; sobreocupación o capacidad mayor, sin dato para distinguirlo | 4.6; `docs/CONTEXTO_TECNICO.md` 4.8 |
| ¿Adelantar altas resuelve? | Ayuda poco: como máximo ~8 % del exceso | 4.6; `src/simulacion_altas.py` |
| ¿Se puede predecir la demanda? | Llegadas sí (7,5 % de error); ingresos diarios no, por semana 9,5 % | 5.1 |
| ¿Qué alertas se proponen? | Día congestionado a las 12 h; ocupación alta; paciente a las 48 h sin cama | 5.2 |
| ¿Por qué se quitaron datos como "duplicados"? | 41 % de las estancias estaban en dos personas | 2 |
| ¿Se puede reproducir sin la base? | No: hay 10 archivos exportados de la base (los 8 CSV de entrada y P02 y P03, que dan la persona real) que no están en git y no se pueden regenerar. Con ellos el pipeline se regenera en menos de un minuto y la tabla de episodios sale idéntica (probado en un clon limpio el 8-nov) | `README.md` |
| ¿Qué dijo el HUN? | Nada por correo; habrá una sesión de preguntas (preguntas listas en `docs/hun/sesion_de_preguntas.md`) | 7 |

---

# Fuente: docs/recomendaciones.md

### 4. Lo que los datos NO respaldan
- **Más personal según el día de la semana:** el día de la semana y los festivos casi no cambian la espera.
- **Priorizar a un paciente concreto por riesgo de esperar:** el modelo explicativo de A4, con lo que se sabe al llegar, tiene un AUC de 0,68 en la prueba de 2026: para no perder
  casos habría que marcar al 44 % de los pacientes, y 4 de cada 10 marcados serían falsas alarmas (`docs/modelo_espera.md` 5). Todos los factores juntos explican solo el 16 % de la variación,
  y el estimador A6 mejora el rango apenas un 9 % al llegar. Sirven para planear y para la alerta a las 12 h (R5), no para ordenar la fila al llegar.
- **Un centro de comando o tablero como solución en sí:**
  - El estudio con mejor diseño que encontramos (Mebrahtu y colegas, *Int J Qual Health Care* 2023, Bradford, Reino Unido, series de tiempo interrumpidas) **no halló cambio
    significativo en la estancia** de los ingresos por urgencias en ninguna fase. Coincidió con el COVID-19, lo que complica separar efectos.
  - Los casos de éxito publicados son **autoinformados**. Por ejemplo, Queen's Health System (Hawái) reporta 1,07 días menos de estancia, 64 % menos *boarding* y 20 millones
    de dólares de ahorro, pero las cifras las dio el propio hospital, la nota se publicó en colaboración con el proveedor del centro de comando, no hay grupo de comparación
    y el ahorro es un cálculo con un costo diario supuesto.

**Lo que los datos tampoco permiten calcular: cuántas camas harían falta.** La ocupación media de 2025 (105) roza las 106 camas que dio el HUN y las supera el 42 % de las horas; en adultos es el 101 % de sus 88 camas. No se distingue si es sobreocupación o una capacidad real mayor. Por otro lado, la espera típica casi no sube con la ocupación (~7 % por cada 10 camas; la mediana no cambia, sí el p90) y la ocupación subió por la estancia, no por la demanda. La simulación Monte Carlo da 65 % de días con más de 106 camas ocupadas en los próximos 6 meses (71 % en adultos), así que el problema de capacidad existe, pero bajar la estancia 5 % lo reduce casi tanto como lo empeoraría un 10 % más de ingresos (`docs/simulacion.md`). Por eso no se recomienda ni se descarta aumentar camas: primero la estancia y el proceso de asignación.

### 5. Qué quedó sin respuesta del HUN
La sesión del 29-oct fue la última, así que estos puntos se declaran como limitaciones:
1. Desde cuándo rige el número de camas (106 y 58 camillas) y cuál es la meta de tiempo para asignar cama.
2. Por qué se degrada el registro de las etapas desde el 10-abr-2026 (la auditoría del 2-nov descarta que sea menos demanda).
3. Qué significa cada etapa de urgencias y qué pasa en la última, donde se va la mayor parte de las esperas largas con poca actividad registrada (`docs/caracterizacion_etapas_tu.md`). (La pregunta sobre el «tiempo sin etapa» antes de la cama perdió sentido el 7-nov: era un artefacto de las estancias duplicadas y solo afecta al 1,7 % de las estancias, `docs/CONTEXTO_TECNICO.md` 4.12.)

# Fuente: docs/simulador_integral.md

## Simulador integral del hospital (Fase 1, 14-nov-2026)

**Qué es:** un solo motor de agentes que sigue a cada paciente sintético por todo su recorrido — llega al
hospital, espera cama, la ocupa y sale de alta — y emite **tres vistas sincronizadas del mismo paciente**:
la demanda (llegadas por día), la cola de espera de cama (cuántos esperan a la vez, con perfiles) y la
ocupación de camas con sus altas diarias. Antes esas vistas vivían en tres herramientas separadas
(/pronostico, /paciente y /camas del dashboard); el simulador las une **sobre un motor único**, sin encadenar
los tres modelos en serie.

Código: `src/simulador_integral.py` (motor) y `dashboard/pages/simulador.py` (página `/simulador`).
Tablas: `resultados/tablas/simint_*.csv`; gráfico: `resultados/graficos/simint_resultados.png`.
Es la **Fase 1** del plan de Samuel (simulador → alertas operativas → motor de recomendaciones).

### Cómo funciona (una repetición)

1. **Llegadas** diarias ~ Poisson(pronóstico de `llegadas` de `modelo_pronostico.py`).
2. Cada llegada recibe un **perfil** (grupo de edad × ruta) de la mezcla real de llegadas de 2025 (21 perfiles).
   **Desde el 16-nov el perfil puede completarse con el sexo** (para la vista de perfiles del dashboard):
   en llegadas, sorteado con la mezcla real por perfil (`sexo_llegada`, P(mujer) de 41 a 62 % según la celda,
   global 56 %); en hospitalizados, **el del mismo paciente histórico de la trayectoria** (4.º valor de
   `trayectoria_para`), para que la etiqueta sea coherente con la espera mostrada (las mujeres esperan más:
   mediana 21,8 h contra 14,3 h en el pool 2024-2025, hallazgo abierto de A1). El sexo **no entra en ningún
   cálculo del motor** (P(cama), espera y estancia ya lo promedian dentro de cada perfil): los resultados son
   bit-idénticos con o sin él. **Raza y etnia no se asignan**: en la base la raza está 95 % sin dato y la
   etnia es casi constante ("Hispanic or Latino", `docs/CONTEXTO_TECNICO.md` sección 3); si la vista las muestra, que diga
   "Sin dato en la base".
3. Cada llegada **se hospitaliza** con probabilidad κ × P(cama|perfil), donde P viene de `tabla_episodios`
   (hospitalizado y `estancia_unica` entre TODOS los episodios de 2025: global 7,6 %; va de 5,1 % en adultos
   jóvenes por urgencias a 35,6 % en los de 75+ por Treatment urgency) y κ calibra el nivel contra el
   pronóstico de ingresos a cama del mismo horizonte.
4. A cada futuro hospitalizado se le **sortea una trayectoria real** de un paciente de su mismo perfil
   (hora de llegada, espera y estancia del MISMO paciente histórico, ventana 2024-2025, 14.287 estancias,
   20 de 21 celdas con ≥ 30 casos), suavizada con ruido de Silverman (misma técnica que el motor A5).
   **Desde el 16-nov**, la espera sorteada se ajusta por la **carga de llegadas del día simulado**
   (ver la subsección del backtest; `HUN_SIMINT_CARGA=0` lo desactiva).
5. **cama = llegada + espera; alta = cama + estancia.** La ocupación se acumula por día (misma convención
   validada de A5); la cola de espera por HORA y se promedia por día, igual que la cola real observada.
6. **Siembra** en el corte: el censo real en cama (~100) y la cola real (~21-36) de ese día.

La cola real observada (censo horario entre `llegada` e `ingreso_cama` de las estancias únicas) da media
**25,8 pacientes** — reproduce la referencia de `docs/capacidad_efectiva.md` (~26) con un cálculo independiente.

### Backtest integrado (puerta de validación): ene a 9-abr-2026, entrenado hasta dic-2025

La puerta era doble: no empeorar el backtest de ocupación del motor A5 (tolerancia: MAE hasta 1 cama peor,
cobertura dentro de la meta 70-90 %) y reproducir la cola y las altas, que A5 no emitía. **Cumple.**

| Serie | MAE | Sesgo | Cobertura 10-90 % | Nota |
|---|---|---|---|---|
| Ocupación (camas) | 9,3 | +7,8 | **74,7 %** | A5: 8,6 / +7,0 / 78,8 % — dentro de tolerancia |
| Cola de espera | 4,3 | −2,4 | 70,7 % | real medio del periodo: 27,4 — la reproduce |
| Ingresos a cama/día (emergentes) | 4,0 | +0,7 | 79,8 % | los conteos que emergen de los agentes cuadran |
| Altas/día | 4,7 | +0,5 | 68,7 % | — |
| Llegadas/día | 18,8 | +11,7 | 58,8 % | banda angosta: solo ruido Poisson, no error del pronóstico (límite heredado de A5) |

#### Validación directa de distribuciones (15-nov-2026, sección 5b del script)

La validación por agregados es indirecta (la cola es la huella de la espera y la ocupación la de la estancia,
ley de Little). Para cerrar el argumento se compararon **de frente** los percentiles de los tiempos que reciben
los agentes (100.000 sorteos con el mismo mecanismo: perfil ponderado por P(cama) y `trayectoria_para`) contra
los reales del periodo de backtest (`resultados/tablas/simint_distribuciones.csv`):

| Serie | n real | Mediana sim / real | p75 sim / real | p90 sim / real | Media sim / real |
|---|---|---|---|---|---|
| Espera de cama (h) | 1.810 | 18,9 / 17,0 | 40,3 / 45,1 | 74,7 / 79,6 | 31,7 / 33,8 |
| Estancia (h) | 1.756 | 75,2 / 69,6 | 149,1 / 141,6 | 283,8 / 260,6 | 125,9 / 116,9 |

Los percentiles casi se calcan. Dos sesgos chicos y explicables: la cola alta de la **espera** real de 2026 es
algo peor que el pool 2024-2025 (coherente con que los peores casos empeoran año a año, `docs/CONTEXTO_TECNICO.md` 6b), y la
cola alta de la **estancia** real está algo recortada porque las estancias largas que entraron en el backtest y
aún no tenían alta registrada quedan fuera del lado real (censura, no error del simulador).

#### Ajuste de la espera por carga de llegadas del día (16-nov-2026, sección 1b del script)

En los días con más llegadas la espera **típica** de cama es más larga: coeficiente de log(espera+1) sobre las
llegadas estandarizadas del día de llegada = **+4,7 % por desviación** (~48 llegadas; se 0,011, t ≈ 4,5,
14.289 estancias de 2024-2025). Desde el 16-nov cada día simulado multiplica las esperas sorteadas de sus
llegadas por `exp(β·z)/C`, con z acotado a ±3 (soporte histórico) y C un centrado medido entre hospitalizados
que deja la **media poblacional de la espera sin cambio**. Verificación (puerta: no distorsionar el backtest y
conservar el promedio — **cumple**):

| Métrica | Sin ajuste (base 15-nov) | Con ajuste (16-nov) |
|---|---|---|
| Backtest ocupación MAE / cobertura | 9,32 / 74,7 % | 9,38 / 75,8 % |
| Backtest cola MAE / sesgo / cobertura | 4,33 / −2,37 / 70,7 % | 4,34 / −2,44 / 70,7 % |
| Cola media simulada (demo misma semilla) | 25,29 | 25,21 |
| Corr(llegadas, cola) día a día simulada | 0,260 | **0,264** (real: 0,289) |
| Proyección 180 d: ocupación / % saturación | 112,2 / 69,1 % | 112,2 / 69,2 % |

Qué hace y qué no (medido antes de implementarlo, decisión de la conversación del 16-nov):
- **Se descartó condicionar por decil de llegadas del día con multiplicadores de la media**: salen 0,95–1,09
  **sin patrón monótono** (el decil más cargado da 0,99) — a esa granularidad la espera MEDIA es plana; solo la
  típica (mediana/escala log) sube. El ajuste implementado usa la escala log, y por eso **redistribuye** la
  espera típica entre días cargados y tranquilos sin cambiar las horas totales.
- El gradiente fuerte de la Fase 4 (14 → 26 h por decil de llegadas de las **6 h previas**) vive dentro del día
  y **ya estaba embebido**: las trayectorias sortean hora y espera juntas del mismo paciente real, así que el
  patrón por franja (madrugada 13,7 h / tarde 24,3 h de mediana) se reproduce solo.
- **La retroalimentación ocupación → espera NO se modela**: no es estimable del histórico (espera plana por
  quintil de ocupación, Fase 4; cola sin correlación con la ocupación, `docs/capacidad_efectiva.md`). El
  hospital nunca operó holgado, así que no hay contraste para medirla; se declara como límite.

### Proyección integrada (180 días desde el 9-abr-2026, 1.000 repeticiones)

| Vista | Media | p10-p90 medio |
|---|---|---|
| Llegadas al hospital/día | 260 | 240-281 |
| Ingresos a cama/día | 19,7 | 14-26 |
| Altas/día | 19,6 | 14-25 |
| Pacientes esperando cama a la vez | **25,4** | 20-31 |
| Camas ocupadas | **112,2** | 99-126 |
| % días-repetición sobre 106 camas | **69,1 %** | — |

Coherente con el motor A5 (111,1 camas y 65,4 %, `docs/modelo_camas.md`); la diferencia (~1 cama) viene de que
las estancias ahora se sortean junto con la espera del mismo paciente y de la siembra de la cola.

### La página del dashboard (`/simulador`)

Mismo patrón que `/camas`: panel de sliders a la izquierda (botón **Simular**, 200 repeticiones en vivo),
tarjetas de métricas y un gráfico de **tres paneles apilados con el mismo eje de tiempo** (flujo diario /
camas ocupadas frente a 106 / cola de espera), más los paneles "¿Cómo se interpreta?" y "Ficha técnica".
Sliders: **demanda** (escala llegadas y, vía los agentes, los ingresos), **estancia** (escenario C) y
**espera** (palanca nueva: mueve la cola pero NO la ocupación — la cama se ocupa igual, solo que antes o
después; la nota de la página lo advierte para que nadie lea "menos espera = camas libres").

### Límites (declarados también en la página)

- **La cola es cota inferior:** solo contiene futuros hospitalizados. La congestión completa de urgencias no
  se puede simular (36-42 % de las etapas TU sin hora de fin, `docs/CONTEXTO_TECNICO.md` 4.3).
- **Fidelidad estadística, no bola de cristal:** reproduce patrones (cuántos, qué perfiles, qué tan lleno),
  no días concretos ni pacientes concretos.
- P(cama|perfil) constante por día; κ global por corrida (no por día de semana). El patrón semanal de los
  ingresos emergentes hereda el de las llegadas suavizado por la espera (el backtest muestra que alcanza).
- Los sembrados reciben tiempos completos del bootstrap (sin corregir el sesgo de selección); solo afecta los
  primeros días.
- Las llegadas incluyen ~4 % de réplicas (cota conocida, `docs/CONTEXTO_TECNICO.md` 4.13).
- El ajuste por carga del día (16-nov) mueve la espera típica, no la media por día (que es plana en los datos);
  la retroalimentación ocupación → espera no se modela porque no es estimable del histórico (ver la subsección
  del backtest). Si la simulación sale muy lejos del régimen histórico de ocupación, las esperas no se alargan
  solas: el resultado de esos escenarios es la presión sobre camas, no la espera individual.
- Asociación, no causa; periodo confiable hasta el 9-abr-2026; 106 camas es la cifra del HUN sin fecha.

### Modelos de la ficha A9 y casos (15-nov-2026)

En el panel de la izquierda hay controles nuevos. Cambian el pronóstico de llegadas y de ingresos a cama, del que salen las tres gráficas
(demanda, cola de espera y ocupación), así que las tres se mueven a la vez y se actualizan solas. Sin nada marcado, el motor es el de siempre.

- **Entrenar el pronóstico con (ficha A9):** casillas para marcar, uno por uno, los modelos de la ficha A9. Cada uno entra solo en la serie
  donde A9 lo probó: dengue y lluvia en las llegadas; curva suave del año, infecciones respiratorias y diarreas en los ingresos a cama. Al
  marcar uno se muestra su error en la prueba frente a «sin modelo».
- **Casos:** solo aparecen los de los modelos marcados (la curva del año no tiene caso). Cada caso tiene **su propia escala**, sacada de lo
  que de verdad pasó en las semanas de 2023-2025 frente a lo normal de esa época del año (`casos_escala.csv`): muy bajo (una semana más baja
  que 19 de cada 20), bajo (más baja que 3 de cada 4), normal, alto (más alta que 3 de cada 4), muy alto (9 de cada 10), grave (19 de cada
  20) y récord (la más alta). Solo aparecen los niveles que existieron en ese caso. El caso se aplica a todo el horizonte simulado.

| Caso | Muy bajo | Bajo | Alto | Muy alto | Grave | Récord |
|---|---|---|---|---|---|---|
| Dengue | −47 % | — | +216 % | +309 % | +369 % | +492 % |
| Infecciones respiratorias | — | — | +44 % | +63 % | +78 % | +113 % |
| Diarreas | −27 % | −6 % | +24 % | +35 % | +41 % | +92 % |
| Lluvias | −79 % | −61 % | +92 % | +195 % | +479 % | +1.570 % |

  (% sobre lo normal de esa semana en 2016-2022; «—» = ese nivel no se dio. Las respiratorias estuvieron casi siempre por encima de lo
  normal prepandemia, por eso no tienen niveles bajos. 2023-2025 fueron años de mucho dengue.)

**Error de cada modelo** (`src/medir_casos.py`; entrenado hasta el 30-jun-2025, WAPE diario):

| Serie | Modelo | Validación (jul–dic 2025) | Prueba (ene–9 abr 2026) |
|---|---|---|---|
| Llegadas | Sin modelo | 7,8 % | 6,9 % |
| Llegadas | Dengue | 7,3 % | 7,1 % |
| Llegadas | Lluvia | 7,6 % | 6,8 % |
| Ingresos a cama | Sin modelo | 16,7 % | 20,1 % |
| Ingresos a cama | Curva del año | 16,8 % | 19,8 % |
| Ingresos a cama | Respiratorias | 16,6 % | 20,0 % |
| Ingresos a cama | Diarreas | 17,0 % | 20,0 % |

Las diferencias son de décimas: ningún modelo cambia mucho el error diario. Su valor está en el ritmo del año a varios meses (ficha A9).

**Cómo se midió el efecto de los casos** (`src/medir_casos.py` → `casos_efecto.csv`, fuera del repositorio). Es el efecto **propio** de cada
caso, en porcentaje, y vale igual en cualquier mes:
- Para cada caso y cada semana epidemiológica se calcula cuánto está por encima o por debajo de **lo normal para esa semana del año** (la media
  de esa semana en 2016-2022 para dengue, IRA y EDA de Barranquilla; 2005-2022 para la lluvia). Así un brote de dengue en julio cuenta como
  brote aunque julio no sea temporada, y la baja de pacientes de diciembre no se confunde con el dengue.
- La demanda de cada semana se compara contra lo esperado por el calendario, el nivel de cada año y las formas del año de esa serie.
- Una regresión con las 151 semanas de feb-2023 a dic-2025 y los cuatro casos juntos da una elasticidad por caso y serie: si el caso está X %
  por encima de lo normal, la demanda cambia (1 + X/100)^b − 1. El simulador aplica esa fórmula al valor del deslizador.

| Caso | Alto: llegadas / ingresos | Grave: llegadas / ingresos | Récord: llegadas / ingresos |
|---|---|---|---|
| Infecciones respiratorias | **+3,2 %** / +1,1 % | **+5,1 %** / +1,7 % | **+6,7 %** / +2,3 % |
| Dengue | +0,2 % / +0,1 % | +0,2 % / +0,1 % | +0,2 % / +0,1 % |
| Diarreas | −0,2 % / +0,0 % | −0,3 % / +0,1 % | −0,5 % / +0,1 % |
| Lluvias | −0,2 % / −0,2 % | −0,6 % / −0,6 % | −1,0 % / −1,0 % |

En negrita, el único efecto cuyo intervalo del 95 % no incluye el cero. **Lo que dicen los datos:** en 2023-2025, las semanas con más
infecciones respiratorias que lo normal traen más pacientes al hospital; las semanas con más dengue, diarreas o lluvia que lo normal casi
no cambian la demanda, ni siquiera en las semanas de más dengue. El efecto del dengue que se ve al mirar el año completo es de temporada
(su pico coincide con diciembre y enero) y lo aplica el modelo de dengue al marcarlo, no el caso. Como cada nivel salió de semanas reales,
ningún nivel se sale de los datos.

**Límites:** son asociaciones; las semanas altas son pocas (12 a 14 para IRA y EDA); los datos externos llegan a 2025 y la simulación parte
de abril de 2026; el efecto se aplica parejo durante todo el horizonte.

Código: `src/simulador_integral.py` (sección «Modelos de la ficha A9 y casos»: `MODELOS_A9`, `CASOS`, `EFECTO_CASOS`, `ERROR_MODELOS`,
`pronostico_entrenado`, `efecto_aplicado`, `factor_casos`; `simular_integral(..., modelos=, casos=)`), `src/medir_casos.py` y
`dashboard/pages/simulador.py`. Si `casos_efecto.csv` y `modelos_error.csv` no están, el motor usa los valores de la última corrida.

### Alertas y operación óptima durante la simulación (18-nov-2026)

La simulación se reproduce siempre como «hoy». Mientras corre, salta una tarjeta arriba del gráfico (dentro del flujo de la página, sin tapar nada) con la etiqueta **Alerta**, su gravedad, **qué pasó** y la **recomendación** (con su primer paso). Tiene flechas ◀ ▶ para recorrer las alertas anteriores sin interrumpir la reproducción, y enlaces a **la alerta** (`/alertas#alerta-A2`) y a **la recomendación** (`/recomendaciones#rec-R4`) que abren la página y llevan a esa tarjeta, resaltada un momento.

**Calibración.** En un caso normal de la propia simulación (90 días, sin palancas) la probabilidad de superar las 106 camas tiene mediana 68 % y casi nunca pasa de 84 %; las camas ocupadas, mediana 111 y p90 114,5; la cola, mediana 25 y p99 28. Superar las 106 camas es lo normal en esta simulación: por eso esa condición avisa **una sola vez** y lo que **frena** la simulación es lo crítico, por encima de lo típico. Los primeros 7 días (4 si el plazo es de 2 semanas o menos; 12 horas en la vista horaria), que vienen de la siembra con el censo real, no generan alertas. Si los controles mejoran claramente al hospital (por ejemplo, estancia −10 %), no saltan alertas porque ya no hay riesgo.

**Gravedades y pausa.** Hay dos gravedades: aviso (media) y crítico (alta). **Las dos frenan la simulación**, para poder revisarlas y aplicar la mejora antes de que la condición escale. Una alerta salta cuando **aparece** (20-nov-2026). Si se dejó **sin corregir** (Continuar), al volver no frena otra vez: su fila comprimida queda marcada como activa (el punto late) mientras la condición se cumpla. **Vuelve a saltar** si reaparece después de aplicarle la mejora (la mejora no alcanzó) o si se agrava de aviso a crítico, aunque siga activa. Reiniciar o una corrida nueva borran esa memoria; aplicar una mejora no. Todas las alertas tienen **histéresis**: se encienden en el umbral de aviso y, ya encendidas, solo se apagan al volver claramente a lo normal (cola por debajo de 26; faltarán camas con probabilidad por debajo de 40 % y sin camas faltantes; las por paciente, en su nivel de suelta). Así un vaivén de uno o dos pacientes no cuenta como alerta nueva.

| Alerta | Aviso (gravedad media) | Crítico (gravedad alta) | Recomendación | Alerta (página Alertas, categoría Riesgo) |
|---|---|---|---|---|
| Faltarán camas (se necesitarán más de las 106: probabilidad de superar la capacidad a 48 h y camas que faltan, en la mediana) | desde 50 % o 1 cama que falta (107 ocupadas) | desde 84 % o 12 camas que faltan (118 ocupadas) | R3, R4 y R7 | A2 |
| Cola de espera larga (pacientes a la vez) | desde 28 | desde 33 (el percentil 90 real) | R5 y R6 | S1 |
| Estancias más largas de lo normal (en cama con más días que el p90 de su perfil) | desde 23 | desde 28 | R7 | A2 |
| Esperas de más de 3 días (72 h o más sin cama) | desde 10 | desde 13 | R5 y R6 | A3 |
| Ingresos con riesgo de estancia larga (% de ingresos de 7 días de 60+ o treatment urgency) | desde 47 % | desde 55 % | R7 | A2 |

La tarjeta apila sus botones de arriba abajo: Continuar, Aplicar mejora y comparar, Ver más sobre esta alerta y Ver recomendación. La reproducción nueva arranca cuando la figura nueva ya está dibujada, para que el gráfico no parpadee al reiniciar.

Los umbrales son criterios de esta página, no resultados validados como los de `docs/recomendaciones.md`. Si coinciden varias, gana la más grave.

Al aplicar la mejora, las alertas de la corrida anterior **no desaparecen**: siguen consultables, y las nuevas se suman al historial.

**Una sola acción: «Aplicar mejora y comparar».** Se frena la reproducción, el panel de configuración se abre y los controles se desplazan, uno tras otro, a la operación óptima (R7: 15 % menos en las estancias de más de 14 días; R4: 30 % de las altas de la tarde adelantadas a la mañana). El panel se enfoca en las dos palancas que cambian, se mueven una tras otra y, cuando terminan, **se cierra solo y la vista baja al gráfico**. Entonces la simulación se **repite desde el día 1** con la operación óptima a todo color y cómo iba antes («Antes de la mejora») en gris punteado, durante toda la corrida. La alerta de cola no ofrece la mejora, porque la operación óptima no la mueve directamente. «Reiniciar» devuelve los controles a cero.

### Ingresos por franja horaria (19-nov-2026)

El pronóstico de ingresos a cama ahora se reparte en cuatro franjas del día: **madrugada (0-7 h), mañana (7-14 h), tarde (14-19 h) y noche (19-24 h)**, las mismas de `src/estimador_tiempo_restante.py`.

- **Cómo:** `simular_integral` devuelve `info["ingresos_franja"]` = `{franja: {p10, p50, p90, media}}` por día. Reparte cada ingreso diario simulado con la distribución horaria **real** de asignación de cama (2024-2025), medida por día de la semana (`REPARTO_FRANJA`).
- **Por qué no sale de los agentes:** el motor diario suaviza la espera con ruido, lo que aplana la hora y daba ~25 % por franja. Lo medido es madrugada ~17 %, mañana ~12 %, tarde ~32 %, noche ~38 %.
- **Garantías:** no usa números aleatorios nuevos (las series existentes salen idénticas) y las medias de las cuatro franjas suman el total diario. Los percentiles son bandas, no suman exacto.
- **Vista horaria (72 h):** `ingresos_por_franja_horario(horas_idx, out)` agrupa las horas simuladas en las mismas franjas.
- **Límite:** el reparto es el promedio histórico; no cambia con la saturación ni con los controles del simulador.

### Confirmación verde al aplicar una mejora y pico de llegadas de la tarde (19-nov-2026)

- **Pacientes de ejemplo:** `simular_integral(..., registrar_rep=0)` devuelve `info["pacientes"]` con los pacientes de **una** repetición (perfil, sexo, llegada, espera, estancia, día de cama y de alta; los que ya estaban en cama el día 0 aparte). No usa números aleatorios del motor: las series salen idénticas con o sin el registro. El sexo de los sembrados en cama sale de un generador aparte.
- **Panel verde (`dashboard/pacientes_alerta.py`):** al pulsar «Aplicar mejora y comparar», los controles se mueven y la simulación **queda en pausa** con un panel verde hasta pulsar «Continuar con la mejora».
  - *Faltarán camas:* las altas del día (llegada + espera + estancia) y el 30 % de ellas que pasaría a la mañana (se sortea con semilla fija, así que el mismo día da el mismo resultado); y los pacientes de 14 días o más, separados en «ya llevan 14 días o más en cama» y «estimados de 14 días o más».
  - *Cola de espera:* para 48 h y para 72 h, «esperando ese tiempo o más ahora mismo» (al cierre del día) y «estimados» (llevan menos, pero su espera asignada es de ese tiempo o más).
- **Límites:** las tablas son una corrida, no el promedio; la cifra del texto de la recomendación (~34) sale de promedios y puede diferir. Los pacientes que ya estaban en cama el día 0 no tienen fecha de ingreso, así que solo entran en «estimados». Las estancias y esperas «estimadas» son las del simulador según el perfil, no las del modelo de «Paciente en espera». La vista horaria no tiene estas tablas.
- **R3 («Reunión de camas»):** ya no repite las camas esperadas, que están en «Qué pasó».
- **Estancia y espera acopladas (supuesto):** con `acoplar_estancia=True` (lo usa el dashboard) la espera de cada paciente sube en la misma proporción que la estancia. No está calibrado con datos.
- **Pico de llegadas de la tarde:** la alerta de cola también salta si las llegadas de 14 a 19 h llegan a 81 o más ese día (percentil 90 de los datos reales; promedio 65) y la cola ya es de al menos el 80 % del umbral (22 de 28). Con la operación normal del simulador nunca se supera (máximo 76,7 en 90 días); con 15 % más de llegadas se supera 19 de 90 días. Es un indicador del volumen del día, no una medida independiente, porque el reparto por franja es fijo por día de la semana.
- **Alertas:** una alerta salta cuando **aparece**; si ya estaba activa no vuelve a saltar, y si se va y reaparece salta de nuevo. Las que coinciden el mismo día se encolan y se muestran una tras otra.


# Fuente: docs/alertas_por_paciente.md

## Alertas por paciente del simulador integral (20-nov-2026)

Tres alertas nuevas del simulador integral (`dashboard/pages/simulador.py`, `_alertas_paciente`) que miran a los pacientes uno por uno, no a los totales del día.
Se cuentan sobre los pacientes de **una** repetición de la simulación, que son los mismos de las tablas de pacientes (`dashboard/pacientes_alerta.py`, `series_alertas`).
Los umbrales están en `dashboard/umbrales_alertas.py`.

### Cómo se calibraron

Se hicieron corridas de 90 días desde el 9-abr-2026 en cuatro escenarios: operación normal, estancia +15 %, espera +20 % y 20–40 % de perfiles de estrés.
Para cada conteo diario se midieron la mediana, el percentil 90 y el máximo. Los umbrales quedan por encima de lo normal: el aviso está cerca del máximo de la operación normal y el crítico, en lo que solo se alcanza con una palanca en contra.
Las alertas tienen **histéresis**: una alerta que ya saltó sigue activa hasta que el conteo baja de un nivel de suelta. Sin ella, el conteo cruzaba el umbral una y otra vez (hasta 10 avisos por corrida). Con ella, en operación normal cada alerta salta 1 o 2 veces en 90 días.

| Conteo diario (una repetición) | Normal: mediana / p90 / máx | Con la palanca en contra | Aviso | Crítico | Suelta |
|---|---|---|---|---|---|
| En cama por encima del p90 de su perfil | 15 / 21 / 23 | estancia +15 %: 20 / 28 / 30 | 23 | 28 | 19 |
| Esperando 72 h o más | 5 / 8 / 12 | espera +20 %: 8 / 12 / 14 | 10 | 13 | 7 |
| % de ingresos (7 días) de perfil de riesgo | 37 / 42 / 46 | 20 % de estrés: 56 / 62 / 64 | 47 | 55 | 42 |

Correlaciones en operación normal: «esperando 72 h o más» con la cola total, 0,35; «por encima del p90 del perfil» con las camas ocupadas, 0,49. Las dos alertas miden algo distinto de las que ya había.

### Alertas aprobadas

#### Estancias más largas de lo normal (Sim 3, idea del equipo, ajustada)
- **Qué mide:** los pacientes en cama que ya llevan más días que 9 de cada 10 pacientes de su mismo perfil (edad × tipo de visita), según las estancias reales de 2023–2026 (`si.TRAY_PERFIL`).
- **Por qué aporta:** la ocupación sube por la estancia y no por la demanda (Ocupación de camas, resultados 1 y 2). La revisión de estancias largas (R7) empieza a los 14 días y no ve a los pacientes de perfiles cortos que ya se alargaron; son unos 3 de los 15 de un día normal.
- **Ajuste a la idea original:** el proyecto no tiene un «estimador de estancia», y predecir la estancia de un paciente al ingresar no funcionó (R² ≈ 0, HALLAZGOS 5.3). Por eso la alerta compara **cuánto lleva** cada paciente con lo normal de su perfil, en vez de intentar adivinar cuánto le falta.
- **Estancias de más de 30 días** (página Estancias largas): no quedan como alerta aparte. En la simulación son 2 a 4 pacientes, con mucho ruido, y su correlación con las camas es de 0,19. Aparecen como dato dentro de esta tarjeta.
- **Mejora:** R7, gestión de casos con una dosis calculada según cuánto se pasa el conteo de lo normal (recorte de las estancias de más de 14 días, entre 10 y 30 %).

#### Esperas de más de 3 días (Sim 4, idea del equipo, ajustada)
- **Qué mide:** los pacientes que llevan 72 h o más sin cama. El percentil 90 real de la espera es 73,9 h, y los peores casos son los que empeoran (Espera de cama, resultado 2).
- **Por qué aporta:** la cola total puede verse normal mientras se acumulan los peores casos; la correlación entre las dos es solo de 0,35.
- **Resultados 3 y 5 (quién espera más):** se usan para **describir** a los pacientes (cuántos son mayores de 60 por urgencias y cuántos llegaron en la mañana), no para darles prioridad.
  - **Se rechazó** la idea de dar atención o cama prioritaria por perfil. Lo que se sabe del paciente explica solo el 16 % de su espera. Ordenar la fila por riesgo al llegar obligaría a marcar al 44 % de los pacientes, con 4 de cada 10 falsas alarmas (recomendaciones, sección 4).
  - Priorizar por sexo no tiene una causa conocida que lo justifique.
  - Lo que sí es accionable del resultado 5 es la llegada en la mañana: esos pacientes dependen de la asignación de camas de las 15 a 17 h.
- **Recomendación:** R5 (un responsable revisa cada caso) y R6 (dejar lista la solicitud de cama antes de las 15 h; en la simulación, espera −5 %). Para los pacientes que van en camino a 72 h, se sugiere el estimador de «Paciente en espera» a las 12 h, que existe y está validado (acierta 1 de cada 2).

#### Ingresos con riesgo de estancia larga (Sim 5, propuesta nueva)
- **Qué mide:** el porcentaje de quienes recibieron cama en los últimos 7 días que son mayores de 60 o «treatment urgency». Son los perfiles con 2 a 3 veces más riesgo de pasar de 14 días (Estancias largas, resultados 3 y 4).
- **Por qué pasaría desapercibido:** las camas reflejan ese cambio en la mezcla de pacientes una o dos semanas después, cuando las estancias se alargan.
- **Límite:** en el simulador solo salta con los perfiles de estrés. Si se suben desde el inicio de la corrida, coincide con «Faltarán camas» y no da tiempo extra; el adelanto solo se ve si la mezcla cambia a mitad de la corrida.
- **Mejora:** plan de alta desde el ingreso (R7 temprano; en la simulación, recorte de 15 %).

### Ideas evaluadas y descartadas

| Idea | Por qué no |
|---|---|
| Atención o cama prioritaria por perfil (resultado 3) o por sexo (resultado 5) | Ver Sim 4: con los datos no se puede saber al llegar quién esperará mucho, y por sexo no hay causa conocida. |
| Estancias de más de 30 días como alerta propia | Ver Sim 3: pocos casos y mucho ruido en la simulación; queda como dato en la tarjeta. |
| Reingresos a 72 h (5,3 %) | El simulador no los modela: la alerta sería inventada. |
| Días de la semana y fines de semana | El día de la semana y los festivos casi no cambian la espera (Qué influye en la espera, resultado 1). |
| Desbalance de ingresos y altas en varios días | El balance diario es casi todo azar, y la proyección de camas a 24 h no le gana a «mañana igual que hoy» (`src/alertas.py`). |
| Días-cama de baja actividad | Son unos 6 y no crecen (`docs/dias_cama_baja_actividad.md`). |

### Histéresis también en las alertas de totales (20-nov-2026)
«Cola de espera larga» volvía a encenderse 12 o 13 veces en 90 días cuando se subía la espera o la estancia, porque la cola oscila alrededor de 28. Ahora tiene histéresis: una vez encendida, sigue así hasta bajar de 26 pacientes. «Faltarán camas» sigue encendida hasta que la probabilidad de superar la capacidad a 48 h baja de 40 % y ya no falta ninguna cama (`SUELTA_COLA`, `SUELTA_PROB` y `SUELTA_FALTAN` en `dashboard/umbrales_alertas.py`).
Con espera +20 %, la cola pasó de 12 a 3 encendidas por corrida; con estancia +15 %, de 13 a 8. En operación normal, «Faltarán camas» pasó de 5 a 1.
Además, una alerta que se dejó sin corregir no vuelve a frenar la simulación al reaparecer: solo marca como activa su fila comprimida.

