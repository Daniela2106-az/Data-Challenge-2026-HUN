# Recomendaciones para el HUN (versión verificada, cifras al 13-nov-2026)

Tarea B2 (Samuel): fuentes verificadas el 1-nov y comprobadas de nuevo el 6-nov; integrada con las cifras vigentes de `main` el 6-nov. Parte del borrador de Daniela del 22-oct, con las cifras de R2 y R6 que Daniela respaldó con scripts el 25-oct
(`src/simulacion_altas.py` y `src/impacto_llegada_tarde.py`). Cambios frente al borrador:

1. **Se revisó cada fuente:** en texto original cuando se pudo y, en cuatro casos (Kausar, Siddique, Hoot y Oskvarek), con un resumen. La sección 6 dice qué se verificó y cómo.
2. **Se corrigió una fuente mal descrita:** el artículo de BMC Health Services Research 2024 **no es una revisión**; es un proyecto de mejora en un
   solo hospital de Texas. Lo que sí hace es describir la literatura previa como mixta.
3. **Se precisó qué miden los estudios:** "2,1 horas menos" y "41 minutos más" son **tiempo de *boarding*** (paciente ya admitido que espera cama
   en urgencias), que es lo más parecido a nuestra **espera de cama**. No es la espera total en urgencias.
4. **Se añadieron dos estudios** que muestran que una meta de 25–40 % de altas antes del mediodía es alcanzable (NYU 2014 y Texas 2024).
5. **Todas las cifras propias tienen script de origen.** R2: las ~103 camas son el promedio a las 12 h (`escenario_camas_por_hora.csv`). R6: Daniela
   recalculó el impacto con `src/impacto_llegada_tarde.py` (antes no tenía script) y la franja quedó en 13:00–18:59 frente a 6:00–11:59.
6. **Las 12 fuentes externas se comprobaron de nuevo el 6-nov** y cada una tiene su nivel de verificación escrito (sección 6).
7. **Revisión del 9-nov con lo nuevo del equipo:** A4 (modelo explicativo, `docs/modelo_espera.md`), A5 (simulación Monte Carlo de camas, `docs/modelo_camas.md` y `docs/simulacion.md`),
   A6 (estimador de tiempo restante, `docs/estimador_tiempos.md`), saturación y espera (`docs/saturacion_y_espera.md`), etapas de urgencias (`docs/caracterizacion_etapas_tu.md`)
   y pronóstico de la cola (`docs/pronostico_espera_sistema.md`). Ninguna recomendación cambia de orden; se corrigieron dos afirmaciones que ya no se sostienen (la ocupación «casi no importa»
   y el AUC de 0,60) y se sumaron cifras que refuerzan R3, R4, R5, R6 y R7.
8. **Revisión del 12-nov: evidencia externa para todas las recomendaciones y verificación más fuerte.** R1, R2, R5 y R6 ya no dicen «no aplica» ni
   «no encontrada» (Imhoff 2022, Welch 2011, Yiadom 2020, la norma de flujo de la Joint Commission, Viccellio 2009 y Tcheroyan 2026). Las 4 fuentes
   que antes solo se habían comprobado con un resumen secundario se abrieron en su versión original. Las cifras de la simulación de camas se
   actualizaron a la versión del 10-nov (bootstrap suavizado). Detalle en la sección 6.
9. **Segunda búsqueda del 12-nov para R3, R4, R6 y R7:** 9 fuentes más, todas leídas en el resumen oficial de PubMed (Hammer 2022, Patel 2017,
   Riahi 2026, Kirubarajan 2021, Rajkomar 2016, Erdmann 2024, Amarasingham 2010, Paiva 2024 y Logrono 2026). Cambia el énfasis de R4: dos estudios
   grandes no encuentran beneficio de las altas antes del mediodía por sí solas, así que la acción clave es **asignar enseguida la cama que se libera**.
10. **Tercera búsqueda (13-nov) para que ninguna recomendación quede por debajo de firmeza media:** 8 fuentes más, cada una abierta en su versión
    original (Alotaibi 2021, Farok 2026, Olson 2025, Cheng 2026, Ibrahim 2022, Dowling 2026, Boudi 2020 y Singer 2011). Suben R4 (de media-baja a
    media) y R6 (de baja a media): en las dos, varios estudios independientes respaldan el **mecanismo** (asignar la cama apenas se libera; pedir la cama
    antes), aunque el tamaño del efecto en el HUN sigue incierto. R5 suma la evidencia de que esperar mucho por una cama se asocia con más mortalidad.
    Las 35 fuentes están en la sección 6. Una fuente que no se pudo abrir (NHS England, revisiones semanales de estancias largas) **no se cita**.
11. **Cuarta búsqueda (13-nov, tarde) y criterio escrito de firmeza:** 3 fuentes más, leídas en su resumen oficial vía Europe PMC (Howell 2008,
    Al Harbi 2024 y Devia 2025). Con el criterio de abajo, **R3 y R5 pasan a firmeza alta**; R4 se queda con su enfoque original (meta de altas antes del mediodía) y firmeza
    media; R6 y R7 se quedan en media porque no lo cumplen
    (en R7 una revisión halla que los equipos multidisciplinarios no cambian la estancia en el 70 % de los estudios; en R6 el efecto en el HUN es
    incierto). Son 38 fuentes.

**Criterio de firmeza (13-nov).** **Alta:** se cumplen las tres condiciones: (1) los datos del HUN muestran el problema con claridad y con su
cifra; (2) al menos tres estudios independientes, o uno multicéntrico, coinciden en que actuar sobre ese punto ayuda (o, para las alertas, en que el
problema que se vigila se asocia con daño); y (3) la acción es de bajo costo y bajo riesgo. **Media:** el mecanismo tiene respaldo, pero falta una de
las tres (evidencia inconsistente, efecto incierto en el HUN o acción más costosa). La firmeza no es una garantía de efecto: casi todos los estudios
son de antes y después, sin grupo de comparación.

**Cómo leerlo.** Todo son **asociaciones y escenarios con supuestos escritos**, no causas probadas. El HUN dio su número de camas el 29-oct (106 camas de
hospitalización y 58 camillas de urgencias), sin decir a qué fecha corresponde; no tenemos el motivo clínico de cada espera. Donde un efecto no se puede calcular, se dice. Cifras propias: `docs/HALLAZGOS.md` y `CLAUDE.md` (secciones 4.8 a 4.11 y 6b).

**Términos usados:**
- *Boarding*: tiempo que un paciente ya admitido pasa en urgencias esperando una cama de hospitalización.
- *Estancia O/E*: estancia observada dividida por la esperada según la gravedad del paciente; menos de 1 es mejor de lo esperado.
- *Proyecto de mejora sin grupo de comparación* (antes y después): muestra que algo cambió, no prueba que la intervención lo causó.

## 1. Lo que encontramos (con estancias contadas una sola vez)

| # | Hallazgo | Cifra | Fuente |
|---|---|---|---|
| 1 | Esperar cama es largo y los peores casos empeoran | Espera mediana 18,6 h, percentil 90 de 73,9 h; el exceso medio sube de 17,3 h (2023) a 23,8 h (ene–abr 2026), +38 % | HALLAZGOS 4.2 y 4.3 |
| 2 | Casi todo el tiempo está dentro de urgencias, no en huecos entre etapas | 98 % de las horas de espera es tiempo en urgencias antes de la cama; el tiempo sin ninguna etapa registrada es ~1–3 % (corregido el 7-nov: el 21 % anterior era un artefacto de las estancias duplicadas, `CLAUDE.md` 4.12) | HALLAZGOS 4.2 |
| 3 | Las altas son tardías y la cama se asigna en dos olas | 62,7 % de las altas entre las 14:00 y las 18:59, solo 14 % antes del mediodía; el 61 % de las camas se asigna entre las 15 y las 17 h o entre las 20 y las 23 h, y solo el 9 % entre las 6 y las 11 h. Una cama que se libera en la mañana tarda una mediana de 1,8 h en volver a asignarse aunque haya ~26 pacientes esperando: además de faltar camas, hay un límite de proceso | HALLAZGOS 4.4; `docs/saturacion_y_espera.md` 3 y 4 |
| 4 | Quien llega a media tarde espera más | Mediana de ~25 h al llegar entre las 13 y las 16 h contra 12–15 h de madrugada; a las 16 h, el 72 % recibe cama al día siguiente | HALLAZGOS 4.4 |
| 5 | La ocupación sube por la estancia, no por más pacientes | Camas ocupadas 94 (2023) a 105 (2025); estancia media 4,57 a 5,31 días (+16 %); ingresos ~20 por día sin crecer | HALLAZGOS 4.6 |
| 6 | La saturación del momento mueve poco la espera típica, pero sí la cola larga | Cada 10 camas ocupadas más al llegar suben la espera ~7 % (adultos +7,2 %, IC +3,5 a +11,1); la mediana casi no cambia (18,7 h con ≤ 90 camas, 19,8 h con > 115) y el p90 pasa de 60 a 80 h. Cada decil más de llegadas en 6 h sube la espera ~2,5 %; el día de la semana casi no importa. El hospital está saturado casi siempre: en adultos nunca hay una hora sin pacientes esperando cama | HALLAZGOS 4.4 y 4.5; `docs/saturacion_y_espera.md` 1, 2 y 4 |
| 7 | La espera larga concentra las horas perdidas | El 83 % de las horas de espera viene de esperas de más de 24 h; el 19 % de los pacientes espera más de 48 h | HALLAZGOS 4.2 y 4.6 |
| 8 | En las esperas largas, el tiempo se va en la última etapa de urgencias, con poca actividad | La última etapa concentra el 63 % de la espera de quien espera 12–48 h y el 78 % de quien espera más de 72 h (mediana de 69 h); en ella hay ~1 laboratorio cada 10 h y casi ningún diagnóstico nuevo. Es compatible con un paciente ya decidido que espera cama, pero es una hipótesis: la base no dice qué es cada etapa | `docs/caracterizacion_etapas_tu.md` |

**Qué dice la literatura sobre el problema en general:** dos revisiones sistemáticas de saturación de urgencias señalan causas del lado de salida del hospital: la espera de cama de
pacientes ya admitidos (*boarding*) y la falta de camas (Hoot y Aronsky 2008, 93 estudios), y el *boarding* y las altas tardías
(Oskvarek y colegas 2026, 226 estudios). Ambas piden más estudios de alta calidad; en la de 2026, la mayoría de los estudios es de calidad baja (62 %) o aceptable (35 %). Esto respalda que nuestro
cuello de botella sea un patrón conocido, no una rareza del HUN.

## 2. Resumen de recomendaciones

| Prioridad | Recomendación | Impacto que respaldan nuestros datos | Evidencia externa | Qué tan firme |
|---|---|---|---|---|
| 1 | Registrar mejor: hora de salida de urgencias, asignación de cama y sin duplicados | Habilita medir todo lo demás | Moderada: sin la hora de la decisión de ingreso no se puede medir el *boarding*; un hospital que empezó por registrarla redujo luego ese paso a la mitad (Imhoff 2022); hay definiciones estándar para cada hora (Welch 2011, Yiadom 2020) | Alta |
| 2 | Seguimiento mensual de 6 indicadores | Permite ver si algo mejora | Norma de acreditación: la Joint Commission exige medir el flujo y fijar metas de *boarding*, con 4 h como guía (no obligatoria) | Alta |
| 3 | Reunión diaria de camas a media mañana, con alertas | No cuantificable; la alerta de las 12 h detecta 87 % de los días congestionados (13 de 15); la cola de pacientes sin cama se pronostica a 6–12 h con un tercio menos de error que «lo mismo que ahora» | Consistente: reunión diaria de camas dentro de un paquete en **6 hospitales**, con *boarding* de 16,6 a 9,5 h (Alotaibi 2021); rondas de camas dos veces al día y un responsable de camas bajaron 98 min el tiempo en urgencias de los ingresados, sin cambio en la mortalidad (Howell 2008, Johns Hopkins); pase diario con *boarding* −50 % (Hammer 2022); reunión de la tarde con más altas tempranas (Patel 2017). Sin grupo de comparación | **Alta** |
| 4 | Meta de altas antes del mediodía (empezar con 25–30 %), acompañada de asignar enseguida la cama que se libera | Hasta 5,1 camas libres a las 12 h; evita como máximo 8 % del exceso de espera (estimación central ~3 %). Hoy una cama liberada en la mañana tarda 1,8 h en asignarse | La meta es alcanzable: altas antes del mediodía de 11 % a 38 % (Wertheimer 2014), de 9,5 % a 26,8 % (Bailey 2024) y de 16 % a 36 % con 7,1 h menos de *boarding* en 6 hospitales (Alotaibi 2021); en Baystate el *boarding* bajó de 7,6 a 5,5 h (Artenstein 2017). Asignar rápido la cama liberada potencia el efecto (Erdmann 2024; Farok 2026; Howell 2008; Al Harbi 2024). Hay estudios grandes sin efecto de la meta por sí sola (Kirubarajan 2021; Rajkomar 2016) | Media |
| 5 | Alerta por paciente a las 48 h sin cama, con responsable | ~4 alertas por día; 52 % termina esperando más de 72 h; 24 h de margen. Opción más temprana con el estimador A6: a las 12 h, ~4 alertas por día con 55 % de acierto | Moderada sobre **por qué** actuar: esperar mucho se asocia con más mortalidad (2,5 % con menos de 2 h frente a 4,5 % con 12 h o más, 41.256 ingresos, Singer 2011) y con errores y retrasos de tratamiento (revisión de 21 estudios, Dowling 2026; otra revisión halla solo una tendencia, Boudi 2020). Indirecta sobre **qué** hacer: escalar al paciente a la planta no aumentó la mortalidad (Viccellio 2009; Tcheroyan 2026). Bajo costo: es revisar unos 4 casos al día | **Alta** (es la más débil de las altas: lo respaldado es el daño de esperar, no el efecto de la alerta misma) |
| 6 | Protocolo para quien llega entre las 13 y las 18 h y se hospitaliza: pedir la cama antes | Entre ~11 y ~49 horas-paciente por día (2–11 % del exceso de 451) si esperaran como quien llega por la mañana | Consistente para el mecanismo: protocolo de ingreso rápido con *boarding* de 360 a 270 min (Amarasingham 2010, 9.604 ingresos); decisión → solicitud de cama de 75 a 40 min (Imhoff 2022); ciclo de ingreso de 390 a 175 min (Farok 2026); pedir la cama según la probabilidad de ingreso bajaría el *boarding* 30–70 % en una simulación (Cheng 2026, preprint); un médico en el triage reduce 22 min la estancia en urgencias, certeza moderada (revisión sistemática, Devia 2025). La hora del día pesa distinto en cada hospital (Olson 2025) | Media (el mecanismo tiene respaldo; el tamaño del efecto en el HUN es incierto) |
| 7 | Revisar sistemáticamente las estancias largas | −5 % de estancia ≈ 5 camas (la simulación Monte Carlo da 4,9 y baja los días con más de 106 camas ocupadas de 65 % a 48 %); volver a la de 2023 ≈ 15 camas. Las estancias de más de 14 días ocupan unas 36 camas; las de más de 30 días pasaron de 6 a 13 camas entre 2023 y 2025 | Inconsistente en revisiones (Siddique 2021); proyectos con −4,8 días de estancia mediana en Brasil (Paiva 2024, Red2Green), −68 % de días de cama innecesarios (Logrono 2026) y estancia de 15,5 a 9,0 días en pacientes con alta demorada con un equipo que se reúne cada semana (Ibrahim 2022, Emiratos) | Media |

## 3. Detalle

### R1. Registrar mejor los datos (prioridad 1)
- **Qué cambiar:** registrar la hora de salida de urgencias en todas las atenciones (hoy el 36–42 % de las etapas de urgencias no la tiene), registrar
  la hora en que se asigna la cama, y evitar que un mismo ingreso quede en dos pacientes.
- **Por qué:** el 41 % de los episodios hospitalizados tenía una estancia duplicada en otra persona. Sin corregirlo se estimaban 27,7 ingresos por día
  (son ~20) y ~146 camas ocupadas (son ~100). Desde el 10 de abril de 2026 el registro de las etapas se degrada: la auditoría en la base muestra que las visitas no bajaron en mayo, así que no es menos demanda, y esos días no se usan para estimar nivel ni evaluar. (HALLAZGOS 2; CLAUDE.md 4.6, 4.8 y 4.9)
- **Evidencia externa (verificada el 12-nov):**
  - **Imhoff y colegas** (*BMJ Open Quality* 2022, hospital académico urbano de EE. UU., 25.183 pacientes, antes y después): el primer obstáculo que
    encontraron fue que **no se registraba la hora de la decisión de ingreso**. Su primer paso fue crear una orden en la historia clínica que la
    guardara; con ese dato vieron que el 43 % del tiempo en urgencias de los ingresados era *boarding* y luego redujeron un paso del proceso de 75 a
    40 minutos. Es exactamente lo que le falta al HUN.
  - **Welch y colegas** (*Ann Emerg Med* 2011) y **Yiadom y colegas** (*Acad Emerg Med* 2020): consensos de expertos (32 y 46) del Emergency
    Department Benchmarking Alliance que definen las horas e intervalos estándar de urgencias (llegada, decisión de ingreso, salida, *boarding*) y
    concluyen que un conjunto completo y preciso de definiciones es necesario para gestionar a tiempo. La definición usual de *boarding* empieza en
    la decisión de ingreso y termina en la salida de urgencias (Imhoff 2022 la adopta).
  - El estudio de Bradford (sección 4) también encontró fechas de atención faltantes en el 23–43 % de los registros de urgencias: no es un problema
    exclusivo del HUN.
- **Cómo medirla:** % de atenciones con hora de salida; número de registros duplicados.
- **Límite:** el HUN dijo que las estancias gemelas son «lo más probable» duplicados. La persona real se dedujo de los datos (se identifica en el 97,6 % de las gemelas, `CLAUDE.md` 4.10); el hospital no lo ha confirmado.

### R2. Seguimiento mensual de indicadores (prioridad 2)
Valores de partida con nuestros datos:

| Indicador | Hoy | Fuente |
|---|---|---|
| Espera de cama, mediana / percentil 90 | 18,6 h / 73,9 h | HALLAZGOS 4.2 |
| % de pacientes con más de 48 h sin cama | 19 % | HALLAZGOS 4.2 |
| % de altas antes del mediodía | 14 % | HALLAZGOS 4.4 |
| Hora mediana de asignación de cama | 17–18 h | HALLAZGOS 4.4 |
| Camas ocupadas a las 12 h (promedio mar-2023 a abr-2026) | ~103 | `escenario_camas_por_hora.csv` (`src/simulacion_altas.py`) |
| Estancia media | 5,31 días (2025) | HALLAZGOS 4.6 |

Como referencia, no como séptimo indicador: la ocupación media de todo el día en 2025 fue de 105 camas, frente a las 106 que dio el HUN (HALLAZGOS 4.6).

**Cambio frente al borrador:** el valor a las 12 h y el promedio anual de todo el día son cifras distintas y ya no se presentan como una sola.

**Evidencia externa (verificada el 12-nov):** la **Joint Commission** (el acreditador de hospitales de EE. UU.) revisó en 2012 su norma de flujo de
pacientes, LD.04.03.11: los líderes deben usar datos y métricas para gestionar el flujo y fijar metas para el *boarding*; desde 2014 una nota sugiere
**4 horas** como guía, que no es obligatoria porque «los plazos varían de una organización a otra» (comunicado citado por Becker's Hospital Review,
2012 y 2013; el informe original, R3 Report n.º 4, ya no está en línea). Es la referencia para que el HUN fije su propia meta, que hoy no tiene.

### R3. Reunión diaria de camas con alertas (prioridad 3)
- **Qué hacer:** una reunión corta de 10 a 15 minutos a media mañana con censo, altas previstas e ingresos previstos, apoyada en las alertas de
  `src/alertas.py`: día congestionado a las 12 h y ocupación alta.
- **Por qué (nuestros datos):** a las 12 h la alerta de día congestionado tiene AUC de 0,94 y detecta 13 de 15 días congestionados (25 alertas en
  99 días, 52 % de precisión). Para la ocupación a 24 h (umbral de 107–109 camas, el percentil 80 de las 12 h), "lo mismo que ahora" funciona mejor que una proyección (AUC 0,82, precisión 48 %, detección 76 %, 0,4 alertas por día). Se
  liberan ~20 camas por día, solo como orden de magnitud. (HALLAZGOS 5.2; recalculado el 8-nov con `src/alertas.py` y la regla v3.8)
- **Dos insumos nuevos para la reunión (9-nov):**
  - **Cuántos pacientes seguirán sin cama en 6 y 12 h:** el modelo de flujo (cola de ahora + llegadas esperadas − camas que se suelen asignar a esa hora) se equivoca en 2,6 pacientes a 6 h y 3,5 a 12 h,
    frente a 3,8 y 5,5 de «lo mismo que ahora» (−33 % y −36 %); a 24 h la ventaja baja a −9 %. (`docs/pronostico_espera_sistema.md` 1a)
  - **Cuántos de los que esperan tendrán cama en 12 o 24 h:** el censo del estimador A6 acierta con su rango del 80 % el 87–88 % de los días, y su error está en el mínimo que permite el azar. (`docs/estimador_tiempos.md` 3.2)
- **Evidencia externa (verificada):**
  - La guía práctica de Becker's (2014), que resume recomendaciones del Institute for Healthcare Improvement, propone 10–15 minutos con un orden fijo:
    censo, altas, ingresos y traslados previstos por unidad. **Es una guía, no un estudio: no reporta resultados.**
  - Un resumen de congreso de Wake Forest (Hospital Medicine 2019, unidad de 38 camas, antes y después, sin grupo de comparación) usó una reunión de
    menos de 10 minutos (promedio 8,3). Las órdenes de alta y las salidas fueron más tempranas, pero **la estancia no cambió** (p = 0,98).
  - El caso de NHS Dumfries and Galloway (Escocia, publicado por el gobierno escocés) (unidad 10: estancia de 6,8 a 6,2 días tras 12 semanas) describe reuniones diarias de coordinación y gestión dinámica
    del alta, y reporta menos estancia. **Ojo:** las reuniones eran parte de una intervención organizativa más amplia, y el informe no demuestra que las
    reuniones por sí solas causaran la reducción. Es un caso descriptivo, no un estudio con grupo de comparación.
- **Evidencia nueva (12-nov, resúmenes oficiales en PubMed):**
  - **Hammer y colegas** (*J Emerg Nurs* 2022, planta de medicina de 30 camas, hospital de trauma nivel I, antes y después): un **pase diario
    multidisciplinario** que resuelve en el momento las barreras del flujo, con un modelo de demanda y capacidad en tiempo real, bajó la estancia
    0,83 días y las horas de *boarding* en urgencias de los pacientes de esa planta en 8,83 h por mes (más de 50 % frente a la línea de base).
  - **Patel y colegas** (*Jt Comm J Qual Patient Saf* 2017): una **reunión por la tarde entre médicos y gestores de casos**, junto con educación y un
    tablero de seguimiento, llevó las altas antes del mediodía de 10,4 % a 19,7 % y la estancia media de 5,88 a 5,60 días.
  - **Riahi y colegas** (*Med J Aust* 2026, 25 hospitales públicos de Queensland, 5,5 años): cada 10 % más de ocupación alarga la estancia en
    urgencias 19 min (33 min en los que se hospitalizan), y el umbral en que el flujo se rompe **varía por hospital**: el 85 % genérico no sirve. Respalda
    que la reunión mire la ocupación del propio HUN hora a hora, como hace nuestra alerta de ocupación.
- **Evidencia nueva (13-nov, texto completo en PMC):** **Alotaibi y colegas** (*BMJ Open Qual* 2021, proyecto «Ensiab», **6 hospitales terciarios**
  de Arabia Saudita con 3.736 camas, cuasi-experimental antes y después, 12 meses): un paquete con equipos de flujo, el bundle SAFER, días
  Red2Green y una **reunión diaria de camas para los ingresos de urgencias** bajó el *boarding* de 16,6 a 9,5 h en promedio (−7,1 h), subió las
  altas antes del mediodía de 16 % a 36 % y acortó el tiempo hasta el alta de 265 a 117 min. **La estancia media no cambió** (6,5 a 6,8 días). Es la
  evidencia multicéntrica más cercana a lo que se propone, pero la reunión no se evaluó por separado y el artículo tiene inconsistencias menores
  en sus intervalos de confianza.
- **Evidencia nueva (13-nov, tarde, resumen oficial vía Europe PMC):** **Howell y colegas** (*Ann Intern Med* 2008;149:804–811, Johns Hopkins
  Bayview, antes y después): una **gestión activa de camas** liderada por hospitalistas, con **rondas de camas dos veces al día**, visitas a urgencias
  para ver la congestión y un «director de camas» que mueve recursos en tiempo real, bajó el tiempo en urgencias de los pacientes que se
  hospitalizan de 458 a 360 min (**−98 min**) aunque llegaron 8,8 % más pacientes; los que no se hospitalizaban no cambiaron, y la estancia, la
  mortalidad y los traslados a UCI se mantuvieron. Con Alotaibi (6 hospitales), Hammer y Patel, cumple el criterio de firmeza **alta**.
- **Cómo medirla:** alertas atendidas, acciones tomadas, ocupación a las 12 h.
- **Límite:** las alertas se probaron sobre días pasados con pocos días congestionados (15 en la prueba y 18 en la validación); las cifras pueden moverse. **Recalculado el 8-nov** con la regla de estancia única v3.8 (`src/alertas.py`). La evidencia externa es de casos
  únicos sin grupo de comparación, y en ellos la reunión siempre venía junto con otras medidas: no se puede aislar su efecto.

### R4. Meta de altas antes del mediodía (prioridad 4)
- **Qué hacer:** pasar del 14 % actual al 25–30 % de las altas antes de las 12 h, con ronda médica temprana y preparación del alta el día anterior.
- **Por qué (nuestros datos):** las altas se concentran de las 14 a las 19 h y las camas se asignan a las 17–18 h; los ingresos a cama siguen a las altas en
  la misma hora. Con el 30 % de las altas de la tarde antes del mediodía: hasta **5,1 camas libres a las 12 h** (~34 horas-cama por día). (HALLAZGOS 4.4 y 4.6)
- **Impacto en espera:** como máximo ~8 % del exceso de espera, estimación central ~3 %. Adelantar el 100 % daría como máximo 27 %. El 83 % de las horas
  de espera viene de esperas de más de 24 h, que unas horas de adelanto no deshacen.
- **¿Es alcanzable la meta?** Sí, según tres proyectos en hospitales universitarios de Estados Unidos:
  - NYU Langone, Nueva York (Wertheimer y colegas, *J Hosp Med* 2014): de 11 % a 38 % de altas antes del mediodía en 13 meses en dos unidades. La estancia
    O/E bajó de 1,06 a 0,96. Los autores advierten que aplicaron varias medidas a la vez y no pueden aislar el efecto de cada una.
  - Hospital de 650 camas en Texas (Bailey y colegas, *BMC Health Serv Res* 2024): de 9,5 % a 26,8 % durante 41 meses. Estancia O/E de 1,16 a 1,09 (−6 %).
    No midieron el *boarding*.
  - Baystate, Massachusetts (Artenstein y colegas, *West J Emerg Med* 2017): las **órdenes** de alta antes del mediodía subieron de ~43 % a 54 % y se sostuvieron
    24 meses; la estancia bajó 0,30 días (5,3 a 5,0) y el ***boarding* bajó de 7,6 a 5,5 horas por paciente**. Fue un programa con varias acciones a la vez
    (rondas interdisciplinarias diarias, gestión de camas), así que no se puede atribuir todo a las altas tempranas.
- **Pero no siempre funciona:** en Maimonides, Nueva York (Kausar y colegas, *Jt Comm J Qual Patient Saf* 2024), las altas antes del mediodía pasaron de
  5,0 % a 11,4 %, pero no se asociaron con la estancia y el ***boarding* subió 41 minutos**. Bailey y colegas (2024) describen la literatura previa como
  **mixta**: algunos estudios no hallan relación con la estancia y otros la ven aumentar.
- **Evidencia nueva (12-nov, resúmenes oficiales en PubMed), que cambia el énfasis:**
  - **Kirubarajan y colegas** (*J Hosp Med* 2021, 7 hospitales de Ontario, 189.781 ingresos a medicina interna, cohorte multicéntrica): el número de
    altas de la mañana **no se asoció** con menos estancia en urgencias (razón 0,999; IC 0,997 a 1,000) ni con menos estancia en el hospital; solo en 1 de
    los 7 hospitales hubo 1,9 % menos de estancia en urgencias. Concluyen que aumentar las altas de la mañana **por sí solo** difícilmente mejora el flujo.
  - **Rajkomar y colegas** (*J Hosp Med* 2016, 38.365 hospitalizaciones): el alta antes del mediodía se asoció con una estancia **más larga** (OR 1,04;
    1,14 en ingresos urgentes), posiblemente porque se retrasan altas para cumplir la meta al día siguiente.
  - **Erdmann y colegas** (*West J Emerg Med* 2024, hospital mediano del medio oeste de EE. UU., 6.400 ingresos): el 61 % de las demoras para sacar al
    paciente admitido de urgencias venía de fallas entre **aseo de camas** y el equipo clínico, y el 78 % de sistemas que no mostraban la información
    necesaria («ceguera digital»). Al corregirlas, la espera desde la decisión de ingreso bajó 12,7 min por paciente (IC −22,7 a −2,7), unas 689 h de
    *boarding* evitadas en 9 meses, aun con más volumen.
  - **Qué significa para el HUN:** la meta de altas antes del mediodía es un medio, no el fin. Lo que respaldan juntos nuestros datos (1,8 h para
    reasignar una cama de la mañana) y esta evidencia es **dar el alta cuando el paciente esté listo y asignar enseguida la cama que se libera**
    (aviso inmediato de cama libre, aseo priorizado), sin retrasar altas para cumplir una hora.
- **Evidencia nueva (13-nov, texto completo en PMC) que respalda asignar rápido la cama:**
  - **Farok y colegas** (*Cureus* 2026, hospital de Medina, Arabia Saudita, 435 ingresos, antes y después): con **gestión de camas «pull»** (la planta
    prepara y ofrece la cama sin esperar a que urgencias la pida), una meta de 120 min de la decisión a la cama, triage rápido y escalamiento del
    traslado, el ciclo de ingreso bajó de **390 a 175 min** (mediana) y el tiempo sin valor de 290 a 90 min. La causa más frecuente de demora era la
    **unidad que recibe** (~42 %). Sin grupo de comparación; los autores advierten que no es evidencia causal.
  - **Alotaibi y colegas** (2021, ver R3): en 6 hospitales, las altas antes del mediodía pasaron de 16 % a 36 % junto con un *boarding* 7,1 h menor,
    dentro de un paquete que también aceleraba el alta y la asignación.
  - **Howell y colegas** (2008, ver R3): la gestión activa de camas bajó 98 min el tiempo en urgencias de los ingresados.
  - **Al Harbi y colegas** (*BMJ Open Qual* 2024;13:e002484, hospital terciario, mejora de calidad antes y después, 2019–2022; resumen oficial vía
    Europe PMC): un programa de **gestión de casos** que coordina el flujo y las camas bajó el *boarding* promedio de **11,9 a 1,2 horas**, la estancia
    de 11,5 a 4,4 días y subió el recambio de camas de 0,57 a 0,93. Un solo centro, sin grupo de comparación.
  - **Lectura:** la meta de altas antes del mediodía es alcanzable (Wertheimer, Bailey, Alotaibi, Patel) y rinde más cuando la cama que se libera se
    asigna enseguida, como coinciden seis proyectos (Erdmann, Farok, Alotaibi, Artenstein, Howell y Al Harbi). Como algunos estudios grandes no
    encuentran efecto de la meta por sí sola (Kirubarajan, Rajkomar y Kausar), R4 queda con firmeza **media**.
- **Ojo al comparar:** Baystate mide *órdenes* de alta; el HUN y los demás miden la *salida* del paciente. Una orden antes del mediodía no garantiza que la cama
  quede libre antes del mediodía.
- **Cómo medirla:** % de altas antes de las 12 h; tiempo entre un alta de la mañana y la siguiente asignación de cama; hora mediana de asignación de cama; espera de quien llega de 12 a 18 h.
- **No basta con dar el alta antes: la cama liberada tiene que asignarse enseguida.** Hoy las camas que se liberan entre las 6 y las 12 h tardan una mediana de 1,8 h en volver a asignarse
  (un tercio tarda más de 3 h), aunque siempre hay ~26 pacientes esperando; las de la tarde tardan 0,4 h. Solo el 9 % de las camas se asigna entre las 6 y las 11 h. Si la asignación de la mañana
  sigue lenta, adelantar altas rinde menos de lo estimado. Prueba débil: no hay identificador de cama ni de servicio. (`docs/saturacion_y_espera.md` 3 y 4)
- **Complemento de bajo costo:** dar altas también en fin de semana y festivos. Las altas por cada 100 camas bajan 27 % el domingo y 34 % en festivos, pero el efecto estimado es pequeño: ~1–2 camas equivalentes (`docs/efecto_fin_de_semana.md`).
- **Límite:** es una cota con supuestos (el alta de los demás pacientes no cambia; la ocupación es de ~103 camas a las 12 h frente a las 106 que dio el HUN). Mejora la **hora** de la cama,
  no la capacidad. Todos los estudios externos son de un solo centro y sin grupo de comparación.

### R5. Alerta por paciente a las 48 h sin cama (prioridad 5)
- **Qué hacer:** cuando un paciente lleva 48 h desde su llegada sin cama, avisar a un responsable que revise por qué.
- **Por qué (nuestros datos):** ~4,0 alertas por día; el 52 % de esos pacientes termina esperando más de 72 h, con 24 h de margen. A las 36 h serían 5,3 por día
  (39 %); a las 60 h, 2,6 por día (80 %, solo 12 h de margen). (HALLAZGOS 5.2)
- **Opción más temprana (9-nov, estimador A6):** a las 12 h de espera, avisar cuando el estimador dé 40 % o más de probabilidad de seguir sin cama a las 48 h: 4,1 alertas por día,
  acierta en el 55 % (igual que alertar a todos los que llevan 24 h, 53 %) pero con 12 h más de margen; a cambio detecta solo a la mitad (53 %; cifras recalculadas el 14-nov). Sirve solo para pacientes con orden
  de hospitalización. (`docs/estimador_tiempos.md` 3.2)
- **Evidencia externa (verificada el 12-nov; indirecta):** no hay un estudio de esta alerta exacta, pero sí de lo que se hace cuando salta:
  - **Viccellio y colegas** (*Ann Emerg Med* 2009, Stony Brook, 55.062 ingresos en 4 años, cohorte retrospectiva): con un **protocolo de capacidad
    completa**, cuando urgencias se llena el paciente ya admitido se pasa a un pasillo de la planta. Los 2.042 trasladados así tuvieron menor mortalidad
    (1,1 % frente a 2,6 %) y menos traslados a UCI (2,5 % frente a 6,7 %), aunque eran pacientes distintos (no es una comparación causal): el
    escalamiento no causó daño visible.
  - **Tcheroyan y colegas** (*Am J Manag Care* 2026, revisión sistemática de 11 estudios): el 61 % de los pacientes prefiere esperar en la planta y no en
    urgencias; ningún estudio mostró más mortalidad; pero la calidad de la evidencia es baja o muy baja (GRADE) y los autores dicen que no alcanza para
    conclusiones claras.
  - **Oskvarek y colegas** (2026) incluyen la gestión activa de camas entre las medidas de salida que requieren coordinación de todo el sistema.
  - **Por qué vale la pena actuar sobre las esperas largas (13-nov):**
    - **Singer y colegas** (*Acad Emerg Med* 2011;18:1324–1329, 41.256 ingresos, cohorte retrospectiva; resumen oficial vía Europe PMC): la
      mortalidad sube con el tiempo esperando cama, de **2,5 %** (menos de 2 h) a **4,5 %** (12 h o más), y la estancia de 5,6 a 8,7 días (más de 24 h),
      aun ajustando por comorbilidades.
    - **Dowling y colegas** (*Health Aff Scholar* 2026, revisión sistemática de 21 estudios de EE. UU., 2014–2024): las esperas largas por cama se
      asocian con más mortalidad, morbilidad, estancia, errores de medicación y retrasos de tratamiento; el efecto varía entre UCI y planta.
    - **Boudi y colegas** (*PLoS One* 2020, revisión sistemática de 12 estudios, 182.991 pacientes): 6 estudios hallan asociación con la mortalidad y 5
      no; hay una «tendencia» sin evidencia fuerte. Se cita para no exagerar.
    - Lectura: no hay estudio de una alerta a las 48 h, pero sí evidencia razonable de que las esperas que busca la alerta (más de 48–72 h en el
      HUN, muy por encima de las 12 h de Singer) son las que más se asocian con daño.
  - **Firmeza alta, con un matiz (13-nov):** cumple el criterio porque el problema está bien medido en el HUN (4 alertas al día, la mitad termina en
    más de 72 h), la evidencia de que esas esperas se asocian con daño es consistente (Singer, Dowling; Boudi con tendencia) y la acción es barata
    (revisar unos 4 casos al día) y segura (Viccellio, Tcheroyan). Lo que **no** está probado es el efecto de la alerta misma: es la más débil de las
    cinco recomendaciones con firmeza alta.
  - Lectura para el HUN: la alerta solo sirve si dispara una acción definida (revisar el caso, buscar cama en otra zona, escalar a la dirección).
- **Límite:** solo cuenta a quienes luego se hospitalizan, así que en tiempo real habría más alertas; riesgo de fatiga por alertas. Sin una acción definida
  para cada alerta no sirve.

### R6. Protocolo para quien llega entre las 13 y las 18 h y se hospitaliza (prioridad 6)
- **Qué hacer:** anticipar la decisión de ingreso y la solicitud de cama durante la tarde, para no esperar al ciclo de altas del día siguiente.
- **Por qué (nuestros datos):** mediana de espera de 24,2 h al llegar entre las 13:00 y las 18:59, contra 16,0 h al llegar entre las 6:00 y las 11:59
  (HALLAZGOS 4.4 describe el mismo patrón por hora: ~25 h al llegar de 13 a 16 h, con un salto a las 13:00). La carga del momento explica unos dos quintos
  del efecto de la tarde; el resto no.
- **Impacto:** llegan unos 5,9 pacientes por día en esa franja. Si su espera bajara a la de la mañana, se evitarían **~49 horas-paciente por día midiendo con
  medianas (11 % del exceso de 451 horas por día) pero solo ~11 midiendo con promedios (2 %)**, porque los promedios de la mañana y de la tarde se parecen
  (~34 y ~32 h) y los dominan las esperas largas. Por eso es de confianza baja: ayuda a la espera típica, no a la cola de esperas de varios días.
- **Relación con los diagnósticos (A3):** la espera larga se concentra en pacientes de ortopedia, riñón y vías urinarias, digestivo y cáncer (29–39 h), frente a
  ~9–13 h en cardiovascular, neurológico y respiratorio (HALLAZGOS 4.5b; `docs/diagnosticos_y_tiempos.md`). Si se confirma que es una fila por tipo de cama o servicio, el protocolo de la tarde
  podría enfocarse en esos servicios. Hipótesis sin comprobar: la base no tiene servicio ni piso.
- **Por qué anticipar la decisión ayuda (9-nov):** en las esperas largas, la última etapa de urgencias dura una mediana de 69 h con casi ninguna prueba nueva (`docs/caracterizacion_etapas_tu.md`),
  y la cama se asigna sobre todo entre las 15 y las 17 h y entre las 20 y las 23 h (`docs/saturacion_y_espera.md` 4). Quien llega a media tarde queda fuera de la ola de las 15–17 h si la solicitud
  de cama no está lista a tiempo. Hipótesis: la base no registra la hora de la orden de hospitalización.
- **Fuente:** `src/impacto_llegada_tarde.py` → `resultados/tablas/impacto_llegada_tarde.csv` (estancias únicas, feb-2023 a abr-2026).
- **Evidencia externa (verificada el 12-nov):** **Imhoff y colegas** (*BMJ Open Quality* 2022, 25.183 ingresos a medicina interna, antes y después sin grupo
  de comparación) atacaron el primer paso del ingreso: de la decisión del médico de urgencias a la solicitud de cama. Con una orden electrónica que
  avisa al médico de planta, educación y seguimiento del desempeño, el tiempo medio bajó de **75,1 a 39,7 minutos** (p < 0,0001). No midieron si bajó
  la espera total, y el HUN no registra la hora de la decisión de ingreso, así que no se puede medir aquí todavía (ver R1).
- **Evidencia nueva (12-nov, resumen oficial en PubMed):** **Amarasingham y colegas** (*Qual Saf Health Care* 2010, 9.604 ingresos a medicina
  interna, serie de tiempo interrumpida): un **protocolo de ingreso rápido** redujo el proceso de ingreso de 50 a 10 pasos (roles claros,
  comunicación directa entre médicos, órdenes de espera predefinidas). El *boarding* bajó de 360 a 270 min y el tiempo hasta las órdenes de ingreso de
  210 a 75 min (p < 0,001), unas 27.884 h ahorradas en un año; **no mejoró** para pacientes que iban a telemetría o UCI. Es el tipo de protocolo que R6
  propone para la franja de la tarde.
- **Evidencia nueva (13-nov):**
  - **Farok y colegas** (*Cureus* 2026, ver R4): triage rápido y gestión de camas «pull» llevaron el ciclo de ingreso de 390 a 175 min.
  - **Cheng y colegas** (arXiv 2026, **preprint sin revisión por pares**, simulación con datos de una urgencia grande de EE. UU.): pedir camas de forma
    anticipada según la probabilidad de ingreso de los pacientes en urgencias bajaría el *boarding* promedio **30–70 %** y la estancia en urgencias
    6–15 %, con poco tiempo de cama reservada sin usar. Es lo que R6 propone para la tarde, pero es una simulación, no una prueba en un hospital.
  - **Olson y colegas** (*J Hosp Med* 2025, 38.766 ingresos en 2 hospitales de Boston): la hora del día cambia la probabilidad de esperar 4 h o más,
    pero allí el peor momento es la madrugada (OR 1,63 frente a la mañana) y la tarde es mejor (OR 0,78). **El patrón es propio de cada hospital**: en
    el HUN el peor momento es la tarde, por eso el protocolo se enfoca ahí y debe ajustarse con los datos del propio hospital.
  - **Devia Jaramillo y colegas** (*BMC Emerg Med* 2025;25:25, revisión sistemática y metaanálisis, 245.404 pacientes; resumen oficial vía Europe
    PMC): las intervenciones de médicos en el triage (decisiones más tempranas) reducen la estancia en urgencias 21,9 min (IC −28,4 a −15,4), con
    certeza **moderada** (GRADE); la mayoría de los estudios son de antes y después.
  - **Lectura:** cinco fuentes (Amarasingham, Imhoff, Farok, Devia y la simulación de Cheng) coinciden en que adelantar la decisión y la solicitud de
    cama acorta la espera. R6 se queda en firmeza **media** porque no cumple la primera condición del criterio: cuánto ahorraría en el HUN es incierto
    (2–11 % del exceso, según cómo se mida).
- **Límite:** asociación por hora de llegada, no causa. La espera va de la llegada a la asignación de cama (así lo confirmó el HUN): mezcla atención clínica con espera de cama y no se pueden separar con los datos. **Recalculado el 8-nov** con `src/impacto_llegada_tarde.py` (regla v3.8): ~49 h con medianas y 11,0 h con promedios; el valor con promedios aparecía como ~9 y ~11 en versiones anteriores. Es cerca del 2 % del exceso, así que la conclusión no cambia.

### R7. Revisar las estancias largas (prioridad 7)
- **Qué hacer:** revisión semanal de pacientes con estancias de más de 7 días, con gestión de casos (una persona que coordina el plan y el alta de cada paciente), con foco en las de más de 14 días.
- **Por qué (nuestros datos):** la ocupación subió 12 % (94 a 105 camas) por la estancia (+16 %). Con la ley de Little: bajar la estancia 5 % libera ~5 camas;
  volver a la de 2023, ~15. En 2025 las estancias de más de 14 días (7,3 % de las estancias) ocupan unas 36 camas. Estancias: mediana 71 h, percentil 75 de 144 h, percentil 90 de 280 h. (HALLAZGOS 4.2 y 4.6)
- **Evidencia externa:** una revisión de 19 revisiones sistemáticas (*JAMA Netw Open* 2021, encargada por la agencia AHRQ de
  Estados Unidos) evaluó 8 estrategias. Las rutas clínicas (protocolos paso a paso por enfermedad) y la gestión de casos se asociaron con menos estancia en
  **insuficiencia cardíaca**. En pacientes con varias enfermedades, la planificación del alta y los equipos interdisciplinarios dieron **resultados inconsistentes**.
- **Evidencia nueva (12-nov, resúmenes oficiales en PubMed):**
  - **Paiva y colegas** (*BMJ Open Qual* 2024, hospital universitario de **Brasil**, medicina interna, antes y después): con el paquete SAFER y la
    herramienta **Red2Green** del NHS (marcar cada día de estancia como «verde» si avanzó el plan o «rojo» si no), la estancia mediana bajó de **19 a 14,2
    días** sin cambiar mortalidad ni reingresos. El 55,8 % de los días eran «rojos» y la causa más común fue la **falta de revisión por un médico
    senior** (42,4 %). Es lo más parecido a la revisión semanal que se propone, en un hospital latinoamericano.
  - **Logrono y colegas** (*BMJ Open Qual* 2026, colaborativo de flujo en todo el sistema): atacando los días de cama innecesarios (planificación
    temprana del alta, una herramienta de seguimiento y trabajo social desde el inicio), estos bajaron **68 %** en un año (de 1.522,7 a 493,4 días), las
    camas libres a las 7 a. m. pasaron de 1,5 a 2,8 y los pacientes de urgencias esperando ingreso bajaron 23 %.
  - **Hammer y colegas** (2022, ver R3): el pase diario multidisciplinario bajó la estancia 0,83 días.
  - **Ibrahim y colegas** (*Risk Manag Healthc Policy* 2022;15:141–149, hospital de 586 camas en Abu Dabi, antes y después): un **equipo
    multidisciplinario que se reúne cada semana** (hospitalistas, gestores de casos, trabajo social, finanzas) para destrabar altas demoradas bajó la
    estancia de esos pacientes de **15,45 a 9,04 días** (−41,5 %, p < 0,0001) sin más reingresos a 30 días. Es la forma que se propone para la revisión
    semanal del HUN.
  - **En contra:** en Alotaibi (2021, 6 hospitales) la estancia media **no** bajó con un paquete parecido (6,5 a 6,8 días); los efectos se ven en los
    pacientes de estancia larga, no en la media general.
  - Todos son proyectos de un solo centro (salvo Alotaibi), antes y después, sin grupo de comparación.
  - **Por qué se queda en media:** las revisiones son inconsistentes (Siddique 2021) y, en pacientes de medicina general, los equipos
    multidisciplinarios no cambian la estancia en la mayoría de los estudios; no cumple la segunda condición del criterio.
- **Qué dice la simulación Monte Carlo (A5, versión del 10-nov con bootstrap suavizado):** proyectando 180 días desde el 9-abr-2026, bajar la estancia 5 % lleva la ocupación media de 111,1 a 106,2 camas (−4,9, casi lo mismo que la ley de Little)
  y los días con más de 106 camas ocupadas de 65,4 % a 48,1 %. En cambio, 10 % más de ingresos la sube a 121,9 camas y a 90,9 % de días saturados. **La estancia pesa más que el volumen.**
  Es una proyección condicionada a que el patrón siga igual, no una predicción. (`docs/simulacion.md`)
- **Qué dice A2:** cerca de la mitad del aumento de la estancia media viene de las estancias de más de 30 días (de 54 a 117 por año); del resto, una parte importante es la llegada de visitas «Treatment urgency». La mediana casi no cambió (`docs/factores_estancia.md`).
- **Límite:** es una asociación y requiere revisión clínica. No es una recomendación de «reducir días evitables»: las camas de baja actividad son ~6 y no crecen, y las estancias largas son de pacientes con actividad clínica (`docs/dias_cama_baja_actividad.md`).

## 4. Lo que los datos NO respaldan
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

## 5. Qué quedó sin respuesta del HUN
La sesión del 29-oct fue la última, así que estos puntos se declaran como limitaciones:
1. Desde cuándo rige el número de camas (106 y 58 camillas) y cuál es la meta de tiempo para asignar cama.
2. Por qué se degrada el registro de las etapas desde el 10-abr-2026 (la auditoría del 2-nov descarta que sea menos demanda).
3. Qué significa cada etapa de urgencias y qué pasa en la última, donde se va la mayor parte de las esperas largas con poca actividad registrada (`docs/caracterizacion_etapas_tu.md`). (La pregunta sobre el «tiempo sin etapa» antes de la cama perdió sentido el 7-nov: era un artefacto de las estancias duplicadas y solo afecta al 1,7 % de las estancias, `CLAUDE.md` 4.12.)

## 6. Fuentes y verificación (25-oct-2026; comprobaciones del 6-nov, 12-nov y 13-nov)

**Comprobación del 13-nov:** 8 fuentes nuevas, cada una abierta en su versión original: texto completo en PMC o en la revista (Alotaibi, Farok, Olson, Ibrahim, Boudi y Dowling), el preprint en arXiv (Cheng) y el resumen oficial vía Europe PMC (Singer, porque PubMed bloqueó la lectura automática). Las cifras citadas coinciden con el original; donde el artículo tiene inconsistencias internas se dice. NHS England (revisiones semanales de estancias largas, «hasta 50 %») no se pudo abrir y no se usa.

**Comprobación del 12-nov:** las cuatro fuentes que solo se habían verificado con un resumen secundario se abrieron en su versión original: **Siddique**
(texto completo en PMC: 19 revisiones, 8 estrategias; rutas clínicas −1,89 días y gestión de casos −1,28 días en insuficiencia cardíaca), **Oskvarek**
(texto completo en la revista: 226 estudios; calidad baja 62 %, aceptable 35 %, alta 4 %; *boarding* y altas tardías entre las causas), **Hoot**
(resumen oficial en PubMed: 93 artículos; *boarding* y falta de camas entre las causas) y **Kausar** (resumen oficial en PubMed: altas antes del mediodía
de 5,0 % a 11,4 %, sin asociación con la estancia, *boarding* +41 min). Todas las cifras coinciden. Se sumaron 6 fuentes nuevas para R1, R2, R5 y R6
(al final de la tabla). Nivel de verificación: **texto completo** (lectura del artículo), **resumen oficial** (PubMed o la revista) o **secundaria**
(nota de prensa especializada, cuando el original ya no está en línea).

**Comprobación del 6-nov:** se volvieron a abrir las 12 fuentes y las cifras citadas coinciden. Texto completo o nota completa: Artenstein, Bailey, Wertheimer, Mebrahtu, Becker's (2), Sunkara y NHS Dumfries. Solo resumen: Siddique y Oskvarek (resumen del artículo), Hoot (resumen en PubMed) y Kausar (reseña en The Hospitalist). La columna «Verificación» conserva lo anotado en octubre.

| Fuente | Qué es | Se usa en | Verificación |
|---|---|---|---|
| Artenstein AW y colegas. *Decreasing Emergency Department Walkout Rate and Boarding Hours by Improving Inpatient Length of Stay.* West J Emerg Med 2017;18(6):982–992. [PMC5654890](https://pmc.ncbi.nlm.nih.gov/articles/PMC5654890/) | Proyecto de mejora, 24 meses, Baystate (720 camas), sin grupo de comparación | R4 | Texto completo leído. **Corrección:** las 2,1 h son de *boarding*, no de espera total en urgencias; la tasa ya partía de ~43 % |
| Kausar K y colegas. *Implementing and evaluating a discharge before noon initiative in a large tertiary care urban hospital.* Jt Comm J Qual Patient Saf 2024;50(2):127–138. Resumen en [The Hospitalist](https://www.the-hospitalist.org/hospitalist/article/38356/critical-care/implementing-and-evaluating-a-dbn-initiative-in-a-large-tertiary-care-urban-hospital/) | Estudio retrospectivo antes y después, Maimonides | R4 | **Resumen oficial en PubMed (12-nov)** ([PMID 37845151](https://pubmed.ncbi.nlm.nih.gov/37845151/)): 5,0 % → 11,4 %; sin asociación con la estancia ni los reingresos; *boarding* mediano +41 min. Antes: reseña de The Hospitalist |
| Bailey R y colegas. *Increasing and sustaining discharges by noon – a multi-year process improvement project.* BMC Health Serv Res 2024;24:478. [doi:10.1186/s12913-024-10960-x](https://bmchealthservres.biomedcentral.com/articles/10.1186/s12913-024-10960-x) | Proyecto de mejora en un hospital de Texas, 41 meses | R4 | Texto completo leído. **Corrección: no es una revisión** (el borrador lo llamaba así) |
| Wertheimer B y colegas. *Discharge Before Noon: An Achievable Hospital Goal.* J Hosp Med 2014;9:210–214. [PDF](https://cdn.mdedge.com/files/s3fs-public/pdfs/journals/jhm2154.pdf) | Antes y después, NYU Langone, dos unidades | R4 | Texto completo leído. **Nueva** |
| Siddique SM y colegas. *Interventions to Reduce Hospital Length of Stay in High-risk Populations: A Systematic Review.* JAMA Netw Open 2021. [PMC8453321](https://pmc.ncbi.nlm.nih.gov/articles/PMC8453321/) | Revisión de 19 revisiones sistemáticas (encargada por AHRQ) | R7 | **Texto completo (12-nov)**: 19 revisiones, 8 estrategias; en insuficiencia cardíaca rutas clínicas −1,89 días (IC 1,33 a 2,44) y gestión de casos −1,28 días (IC 0,52 a 2,04); planificación del alta y equipos interdisciplinarios inconsistentes en pacientes complejos |
| Becker's Hospital Review. *The AM Bedside Huddle: What to Cover to Achieve Streamlined Patient Flow.* 2014. [Enlace](https://www.beckershospitalreview.com/capacity-management/the-am-bedside-huddle-what-to-cover-to-achieve-streamlined-patient-flow.html) | Guía práctica (resumen del IHI), sin resultados | R3 | Leído |
| Sunkara P y colegas. *Lightning Huddle: An Innovative Method For Improving Patient Throughput.* Hospital Medicine 2019, resumen 463. [SHM](https://shmabstracts.org/?p=23287) | Resumen de congreso, antes y después, Wake Forest | R3 | Leído |
| Mebrahtu TF y colegas. *The impact of hospital command centre on patient flow and data quality: findings from the UK National Health Service.* Int J Qual Health Care 2023;35(4):mzad072. [PDF](https://eprints.whiterose.ac.uk/209410/1/mzad072.pdf) | Cohorte retrospectiva con series de tiempo interrumpidas, Bradford | Sección 4, R1 | Texto completo leído |
| Becker's Hospital Review. *The Queen's Health Systems saves $20 million in the first year after opening a command center.* 2025. [Enlace](https://www.beckershospitalreview.com/healthcare-information-technology/the-queens-health-systems-saves-20-million-in-the-first-year-after-opening-a-command-center/) | Nota patrocinada con datos del propio hospital | Sección 4 | Leído |
| Hoot NR, Aronsky D. *Systematic review of emergency department crowding: causes, effects, and solutions.* Ann Emerg Med 2008;52(2):126–136. [PubMed 18433933](https://pubmed.ncbi.nlm.nih.gov/18433933/) | Revisión sistemática, 93 estudios | Sección 1 | **Resumen oficial en PubMed (12-nov)**: 93 artículos (de 4.271 resúmenes); causas estudiadas: visitas no urgentes, influenza, personal insuficiente, *boarding* y falta de camas; pide más estudios de alta calidad |
| Oskvarek JJ y colegas. *Emergency Department Crowding in the Modern Era: A Systematic Review (2018–2025).* Clin Exp Emerg Med 2026. [Enlace](https://hsrc.himmelfarb.gwu.edu/gwhpubs/8570) | Revisión sistemática, 226 estudios (Clin Exp Emerg Med 2026;13(2):119–139, [doi:10.15441/ceem.25.172](https://doi.org/10.15441/ceem.25.172)) | Sección 1, R5 | **Texto completo (12-nov)**: 226 de 23.408 registros; calidad baja 62 %, aceptable 35 %, alta 4 %; *boarding* y altas tardías entre las causas de salida; la gestión activa de camas requiere coordinación de todo el sistema |
| NHS Dumfries and Galloway, *Balancing capacity with demand* (gobierno de Escocia). [Enlace](https://www.gov.scot/publications/nhs-dumfries-galloway-case-study-balancing-capacity-demand-dumfries-galloway-9781788510479/pages/15/) | Caso descriptivo de una intervención organizativa | R3 | Texto original revisado por Samuel (25-oct): describe reuniones diarias y gestión del alta con menos estancia, pero dentro de una intervención más amplia; no aísla el efecto de las reuniones |
| Imhoff B y colegas. *Reducing time to admission in emergency department patients: a cross-functional quality improvement project.* BMJ Open Qual 2022;11(3):e001987. [PMC9486293](https://pmc.ncbi.nlm.nih.gov/articles/PMC9486293/) | Proyecto de mejora antes y después (jul-2019 a jul-2021), hospital académico urbano de EE. UU., 25.183 ingresos | R1, R6 | **Texto completo (12-nov)**: no se registraba la hora de la decisión de ingreso; tras registrarla, decisión → solicitud de cama de 75,1 a 39,7 min (p < 0,0001); 43 % del tiempo en urgencias de los ingresados era *boarding*. **Nueva** |
| Welch SJ y colegas. *Emergency department operational metrics, measures and definitions: results of the Second Performance Measures and Benchmarking Summit.* Ann Emerg Med 2011;58(1):33–40. [PMID 21067846](https://pubmed.ncbi.nlm.nih.gov/21067846/) | Consenso de 32 expertos | R1 | **Resumen oficial en PubMed (12-nov)**: conjunto estándar de definiciones y métricas de operación de urgencias, alineado con CMS y NQF. **Nueva** |
| Yiadom MYAB y colegas. *Managing and Measuring Emergency Department Care: Results of the Fourth Emergency Department Benchmarking Definitions Summit.* Acad Emerg Med 2020. [PMID 32248605](https://pubmed.ncbi.nlm.nih.gov/32248605/) | Consenso de 46 expertos | R1 | **Resumen oficial en PubMed (12-nov)**: actualiza las definiciones de ingreso a urgencias y *boarding*; un conjunto completo de definiciones e intervalos es necesario para una atención oportuna. **Nueva** |
| The Joint Commission, norma LD.04.03.11 («patient flow standard») y R3 Report n.º 4 (19-dic-2012), vía Becker's Hospital Review ([2012](https://www.beckershospitalreview.com/care-coordination/joint-commission-publishes-report-on-updated-patient-flow-standards/), [2013](https://www.beckershospitalreview.com/care-coordination/joint-commission-clarifies-qpatient-flow-standardq/)) | Norma de acreditación de hospitales de EE. UU. | R2 | **Secundaria (12-nov)**: uso de datos y métricas para gestionar el flujo; nota de 4 h para el *boarding* como guía, no requisito (vigente desde 2014). El informe original ya no está en el sitio de la Joint Commission (404). **Nueva** |
| Viccellio A y colegas. *The association between transfer of emergency department boarders to inpatient hallways and mortality: a 4-year experience.* Ann Emerg Med 2009;54(4):487–491. [PMID 19345442](https://pubmed.ncbi.nlm.nih.gov/19345442/) | Cohorte retrospectiva, Stony Brook, 55.062 ingresos | R5 | **Resumen oficial en PubMed (12-nov)**: 2.042 pasados a pasillo de planta; mortalidad 1,1 % frente a 2,6 %; traslado a UCI 2,5 % frente a 6,7 %; «no parece causar daño». Grupos no comparables. **Nueva** |
| Tcheroyan R y colegas. *Hospital Floor Hallway Boarding: A Systematic Review of Outcomes.* Am J Manag Care 2026;32(9):e343–e348. [Enlace](https://www.ajmc.com/view/hospital-floor-hallway-boarding-a-systematic-review-of-outcomes) | Revisión sistemática y metaanálisis, 11 estudios | R5 | **Texto en el sitio de la revista (12-nov)**: 61 % prefiere la planta (IC 50 a 71 %); ningún estudio con más mortalidad; GRADE bajo (7) o muy bajo (4); evidencia insuficiente para conclusiones claras. **Nueva** |
| Hammer C y colegas. *Enhancing Hospital-Wide Patient Flow to Reduce Emergency Department Crowding and Boarding.* J Emerg Nurs 2022. [PMID 36084984](https://pubmed.ncbi.nlm.nih.gov/36084984/) | Proyecto de mejora antes y después, planta de 30 camas | R3, R7 | **Resumen oficial en PubMed (12-nov)**: estancia −0,83 días; *boarding* −8,83 h por mes (> 50 %). **Nueva** |
| Patel H y colegas. *Using a Systematic Framework of Interventions to Improve Early Discharges.* Jt Comm J Qual Patient Saf 2017. [PMID 28325207](https://pubmed.ncbi.nlm.nih.gov/28325207/) | Proyecto de mejora, 24 meses | R3, R4 | **Resumen oficial en PubMed (12-nov)**: altas antes del mediodía 10,4 % → 19,7 %; estancia media 5,88 → 5,60 días; reunión de la tarde médicos-gestores de casos. **Nueva** |
| Riahi V y colegas. *The Impact of Hospital Bed Occupancy on Patient Flow and Emergency Department Access: A 25-Hospital Cohort Study.* Med J Aust 2026. [PMID 41755541](https://pubmed.ncbi.nlm.nih.gov/41755541/) | Cohorte retrospectiva, 25 hospitales, 5,5 años | R3 | **Resumen oficial en PubMed (12-nov)**: +10 % de ocupación → +19 min de estancia en urgencias (+33 min si se hospitaliza); umbrales propios de cada hospital. **Nueva** |
| Kirubarajan A y colegas. *Morning Discharges and Patient Length of Stay in Inpatient General Internal Medicine.* J Hosp Med 2021. [PMID 34129483](https://pubmed.ncbi.nlm.nih.gov/34129483/) | Cohorte multicéntrica, 7 hospitales, 189.781 ingresos | R4 | **Resumen oficial en PubMed (12-nov)**: sin asociación entre altas de la mañana y estancia en urgencias u hospitalaria. **Nueva** |
| Rajkomar A y colegas. *The association between discharge before noon and length of stay in medical and surgical patients.* J Hosp Med 2016. [PMID 26717556](https://pubmed.ncbi.nlm.nih.gov/26717556/) | Retrospectivo, 38.365 hospitalizaciones | R4 | **Resumen oficial en PubMed (12-nov)**: alta antes del mediodía asociada a estancia más larga (OR 1,04; 1,14 en urgentes). **Nueva** |
| Erdmann MA y colegas. *Reduced Time to Admit Emergency Department Patients to Inpatient Beds Using Outflow Barrier Analysis and Process Improvement.* West J Emerg Med 2024. [PMID 39319806](https://pubmed.ncbi.nlm.nih.gov/39319806/) | Antes y después con regresión, ~6.400 ingresos | R4 | **Resumen oficial en PubMed (12-nov)**: 61 % de demoras por aseo de camas y 78 % por «ceguera digital»; −12,7 min por paciente. **Nueva** |
| Amarasingham R y colegas. *A rapid admission protocol to reduce emergency department boarding times.* Qual Saf Health Care 2010. [PMID 20142408](https://pubmed.ncbi.nlm.nih.gov/20142408/) | Serie de tiempo interrumpida, 9.604 ingresos | R6 | **Resumen oficial en PubMed (12-nov)**: 50 → 10 pasos; *boarding* 360 → 270 min; órdenes 210 → 75 min; sin mejora en telemetría ni UCI. **Nueva** |
| Paiva MBS y colegas. *Reduction of hospital length of stay through the implementation of SAFER patient flow bundle and Red2Green days tool: a pre-post study.* BMJ Open Qual 2024. [PMID 38191217](https://pubmed.ncbi.nlm.nih.gov/38191217/) | Antes y después, hospital universitario de Brasil | R7 | **Resumen oficial en PubMed (12-nov)**: estancia mediana 19 → 14,2 días; 55,8 % de días «rojos», 42,4 % por falta de revisión senior. **Nueva** |
| Logrono KJ y colegas. *Reducing unnecessary bed days to optimise flow and improve demand-capacity mismatch.* BMJ Open Qual 2026. [PMID 42349993](https://pubmed.ncbi.nlm.nih.gov/42349993/) | Proyecto de mejora en todo el sistema, 1 año | R7 | **Resumen oficial en PubMed (12-nov)**: días de cama innecesarios −68 %; camas libres a las 7 a. m. 1,5 → 2,8; pendientes de ingreso en urgencias −23 %. **Nueva** |
| Alotaibi Y, Alnowaiser N, Alamry A. *Improving hospital flow «Ensiab Project».* BMJ Open Qual 2021;10(3):e001505. [PMC8479940](https://pmc.ncbi.nlm.nih.gov/articles/PMC8479940/) (PMID 34583936) | Cuasi-experimental antes y después, 6 hospitales terciarios de Arabia Saudita (3.736 camas), 12 meses | R3, R4, R7 | **Texto completo (13-nov)**: *boarding* 16,6 → 9,5 h (−7,1 h); altas antes del mediodía 16 % → 36 %; tiempo al alta 265 → 117 min; estancia media sin cambio (6,5 → 6,8 días). El intervalo de confianza de la tabla es inconsistente con la reducción. **Nueva** |
| Farok SM y colegas. *Reducing Emergency Department (ED) Boarding Time Through Lean Redesign of the ED-to-Inpatient Admission Pathway: A Single-Center Quality-Improvement Study.* Cureus 2026;18(5):e109766. [PMC13310080](https://pmc.ncbi.nlm.nih.gov/articles/PMC13310080/) (PMID 42367400) | Antes y después, un hospital de Medina, 435 ingresos (2023) | R4, R6 | **Texto completo (13-nov)**: ciclo de ingreso 390 → 175 min (mediana); tiempo sin valor 290 → 90 min; demora más frecuente en la unidad que recibe (~42 %); «no causal». **Nueva** |
| Olson RM y colegas. *Waiting for a hospital bed: Disparities in emergency department boarding.* J Hosp Med 2025;21(3):261–272. [PMC12954383](https://pmc.ncbi.nlm.nih.gov/articles/PMC12954383/) (PMID 40753491) | Cohorte retrospectiva, 2 hospitales de Boston, 38.766 ingresos (2018–2024) | R6; documento (brecha por sexo) | **Texto completo (13-nov)**: *boarding* ≥ 4 h frente a la mañana: tarde OR 0,78; 17–22 h 0,92; madrugada 1,63 (sin ajustar); mujeres OR 1,08 (1,04–1,13). **Nueva** |
| Cheng Q, Argon NT, Ganesaraman A, Ziya S. *Proactive Inpatient Bed Requests for Emergency Department Admissions.* arXiv:2607.15432, 2026. [Enlace](https://arxiv.org/abs/2607.15432) | **Preprint sin revisión por pares**; simulación con datos de una urgencia grande de EE. UU. | R6 | **Texto en arXiv (13-nov)**: pedir camas de forma anticipada reduciría el *boarding* 30–70 % y la estancia en urgencias 6–15 %. **Nueva** |
| Ibrahim H y colegas. *Multi-Disciplinary Discharge Coordination Team to Overcome Discharge Barriers and Address the Risk of Delayed Discharges.* Risk Manag Healthc Policy 2022;15:141–149. [doi:10.2147/RMHP.S347693](https://doi.org/10.2147/RMHP.S347693) | Antes y después, hospital de 586 camas en Abu Dabi (2019 frente a 2020) | R7 | **Texto completo (13-nov)**: estancia de los pacientes con alta demorada 15,45 → 9,04 días (−41,5 %, p < 0,0001), sin más reingresos; un solo centro. **Nueva** |
| Dowling MK y colegas. *Patient and staff safety implications of emergency department boarding: a systematic review.* Health Aff Scholar 2026;4(5):qxag084. [doi:10.1093/haschl/qxag084](https://doi.org/10.1093/haschl/qxag084) | Revisión sistemática, 21 estudios de EE. UU. (2014–2024) | R5 | **Texto en la revista (13-nov, resumen y puntos clave)**: esperas largas asociadas a más mortalidad, morbilidad, estancia, errores de medicación y retrasos; el efecto varía entre UCI y planta; pide estudios multicéntricos. **Nueva** |
| Boudi Z y colegas. *Association between boarding in the emergency department and in-hospital mortality: A systematic review.* PLoS One 2020;15(4):e0231253. [PMC7159217](https://pmc.ncbi.nlm.nih.gov/articles/PMC7159217/) (PMID 32294111) | Revisión sistemática, 12 estudios, 182.991 pacientes | R5 | **Texto completo (13-nov)**: 6 estudios con asociación y 5 sin ella; «tendencia» sin evidencia fuerte. **Nueva** |
| Singer AJ, Thode HC, Viccellio P, Pines JM. *The association between length of emergency department boarding and mortality.* Acad Emerg Med 2011;18:1324–1329. [doi:10.1111/j.1553-2712.2011.01236.x](https://doi.org/10.1111/j.1553-2712.2011.01236.x) (PMID 22168198) | Cohorte retrospectiva, 41.256 ingresos (2005–2008) | R5 | **Resumen oficial (13-nov, vía Europe PMC)**: mortalidad 2,5 % (< 2 h) → 4,5 % (≥ 12 h); estancia 5,6 → 8,7 días (> 24 h); se mantiene al ajustar. **Nueva** |
| Howell E, Bessman E, Kravet S, Kolodner K, Marshall R, Wright S. *Active bed management by hospitalists and emergency department throughput.* Ann Intern Med 2008;149(11):804–811. [doi:10.7326/0003-4819-149-11-200812020-00006](https://doi.org/10.7326/0003-4819-149-11-200812020-00006) (PMID 19047027) | Antes y después, Johns Hopkins Bayview (nov-2005 a feb-2007) | R3, R4 | **Resumen oficial (13-nov, vía Europe PMC)**: tiempo en urgencias de los ingresados 458 → 360 min (−98 min) con 8,8 % más pacientes; sin cambio en estancia, mortalidad ni traslados a UCI; desvío de ambulancias −6 % y −27 %. Un solo hospital. **Nueva** |
| Al Harbi S y colegas. *Streamlining patient flow and enhancing operational efficiency through case management implementation.* BMJ Open Qual 2024;13(1):e002484. [doi:10.1136/bmjoq-2023-002484](https://doi.org/10.1136/bmjoq-2023-002484) (PMID 38423585) | Mejora de calidad antes y después, hospital terciario (2019–2022) | R4, R7 | **Resumen oficial (13-nov, vía Europe PMC)**: *boarding* 11,9 → 1,2 h; estancia 11,5 → 4,4 días; recambio de camas 0,57 → 0,93. Un solo centro. **Nueva** |
| Devia Jaramillo G, Esmeral Zuluaga N, Velandia Avellaneda VA. *Effective strategies for reducing patient length of stay in the emergency department: a systematic review and meta-analysis.* BMC Emerg Med 2025;25:25. [doi:10.1186/s12873-024-01163-y](https://doi.org/10.1186/s12873-024-01163-y) (PMID 39979831) | Revisión sistemática y metaanálisis, 245.404 pacientes | R6 | **Resumen oficial (13-nov, vía Europe PMC)**: médico en el triage −21,9 min de estancia en urgencias (IC −28,4 a −15,4), certeza moderada; fast-track −21,8 min (certeza baja). **Nueva** |

## 7. Estado

**B2 completa (mergeada el 8-nov), revisada el 9-nov con A4, A5, A6 y los análisis de saturación, etapas de urgencias y pronóstico de la cola, reforzada el 13-nov con 8 fuentes más y, por la tarde, con 3 más y un criterio de firmeza escrito (38 fuentes): 4 recomendaciones con firmeza alta (R1, R2, R3 y R5) y 3 con media (R4, R6 y R7).** Cada recomendación tiene fuente comprobada, o una razón escrita de por qué no la hay, y una cifra o una razón de por qué no se puede calcular.

La cifra baja de R6 y la precisión de la alerta de ocupación de R3 se recalcularon el 8-nov con `src/impacto_llegada_tarde.py` y `src/alertas.py` (regla v3.8).

Lo que puede cambiar estas recomendaciones más adelante:
- **A4 y A5 (Anthony): revisadas el 9-nov.** No cambian las cifras de R4 (el escenario de altas sigue siendo el de `src/simulacion_altas.py`; A5 no lo recalculó) y confirman la de R7 por otro método (−4,7 camas frente a ~5). A4 corrige el AUC de la sección 4 (0,68 en vez de 0,60).
- Si cambian las cifras, actualizar aquí y en `datos/tablas_dashboard/recomendaciones_tabla.csv` (la usará la página 4.1 del dashboard).
