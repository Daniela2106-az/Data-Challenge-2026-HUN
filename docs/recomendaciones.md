# Recomendaciones para el HUN (versión verificada, cifras al 6-nov-2026)

Tarea B2 (Samuel): fuentes verificadas el 1-nov e integrada con las cifras vigentes de `main` el 6-nov. Parte del borrador de Daniela del 22-oct, con las cifras de R2 y R6 que Daniela respaldó con scripts el 25-oct
(`src/simulacion_altas.py` y `src/impacto_llegada_tarde.py`). Cambios frente al borrador:

1. **Se revisó cada fuente:** en texto original cuando se pudo y, en tres casos (Kausar, Hoot y Oskvarek), solo con un resumen. La sección 6 dice qué se verificó y cómo.
2. **Se corrigió una fuente mal descrita:** el artículo de BMC Health Services Research 2024 **no es una revisión**; es un proyecto de mejora en un
   solo hospital de Texas. Lo que sí hace es describir la literatura previa como mixta.
3. **Se precisó qué miden los estudios:** "2,1 horas menos" y "41 minutos más" son **tiempo de *boarding*** (paciente ya admitido que espera cama
   en urgencias), que es lo más parecido a nuestra **espera de cama**. No es la espera total en urgencias.
4. **Se añadieron dos estudios** que muestran que una meta de 25–40 % de altas antes del mediodía es alcanzable (NYU 2014 y Texas 2024).
5. **Todas las cifras propias tienen script de origen.** R2: las ~103 camas son el promedio a las 12 h (`escenario_camas_por_hora.csv`). R6: Daniela
   recalculó el impacto con `src/impacto_llegada_tarde.py` (antes no tenía script) y la franja quedó en 13:00–18:59 frente a 6:00–11:59.
6. **Las fuentes externas tienen su nivel de verificación escrito** (sección 6): las dos que Claude no pudo abrir el 25-oct las revisó Samuel en el navegador.

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
| 2 | Casi todo el tiempo está dentro de urgencias, no en huecos entre etapas | 80 % de las horas de espera es tiempo en urgencias antes de la cama; 21 % es tiempo sin ninguna etapa registrada | HALLAZGOS 4.2 |
| 3 | Las altas son tardías y la cama se asigna por la tarde | 62,7 % de las altas entre las 14:00 y las 18:59, solo 14 % antes del mediodía; la cama se asigna a las 17–18 h sin importar cuándo llegó el paciente | HALLAZGOS 4.4 |
| 4 | Quien llega a media tarde espera más | Mediana de ~25 h al llegar entre las 13 y las 16 h contra 12–15 h de madrugada; a las 16 h, el 72 % recibe cama al día siguiente | HALLAZGOS 4.4 |
| 5 | La ocupación sube por la estancia, no por más pacientes | Camas ocupadas 94 (2023) a 105 (2025); estancia media 4,57 a 5,31 días (+16 %); ingresos ~20 por día sin crecer | HALLAZGOS 4.6 |
| 6 | La carga del momento explica poco | Cada decil más de llegadas en 6 h sube la espera ~2,5 %; la ocupación y el día de la semana casi no importan | HALLAZGOS 4.4 y 4.5 |
| 7 | La espera larga concentra las horas perdidas | El 83 % de las horas de espera viene de esperas de más de 24 h; el 19 % de los pacientes espera más de 48 h | HALLAZGOS 4.2 y 4.6 |

**Qué dice la literatura sobre el problema en general:** dos revisiones sistemáticas de saturación de urgencias coinciden en que la espera de cama de
pacientes ya admitidos (*boarding*) y las altas tardías son de las principales causas del lado de salida del hospital (Hoot y Aronsky 2008, 93 estudios;
Oskvarek y colegas 2026, 226 estudios). Ambas advierten que la evidencia sobre soluciones es de calidad baja o moderada. Esto respalda que nuestro
cuello de botella sea un patrón conocido, no una rareza del HUN.

## 2. Resumen de recomendaciones

| Prioridad | Recomendación | Impacto que respaldan nuestros datos | Evidencia externa | Qué tan firme |
|---|---|---|---|---|
| 1 | Registrar mejor: hora de salida de urgencias, asignación de cama y sin duplicados | Habilita medir todo lo demás | No aplica | Alta |
| 2 | Seguimiento mensual de 6 indicadores | Permite ver si algo mejora | No aplica | Alta |
| 3 | Reunión diaria de camas a media mañana, con alertas | No cuantificable; la alerta de las 12 h detecta 83 % de los días congestionados | Débil: un resumen de congreso (altas más tempranas, misma estancia) y un caso escocés donde la reunión fue parte de una intervención más amplia | Media |
| 4 | Meta de altas antes del mediodía (empezar con 25–30 %) | Hasta 5,1 camas libres a las 12 h; evita como máximo 8 % del exceso de espera (estimación central ~3 %) | Mixta: 3 proyectos con mejoras, 1 sin efecto y con más *boarding* | Media-baja |
| 5 | Alerta por paciente a las 48 h sin cama, con responsable | ~4 alertas por día; 51 % termina esperando más de 72 h; 24 h de margen | No encontrada | Media |
| 6 | Protocolo para quien llega entre las 13 y las 18 h y se hospitaliza | Entre ~11 y ~49 horas-paciente por día (2–11 % del exceso de 455) si esperaran como quien llega por la mañana | No encontrada | Baja (el rango depende de usar promedios o medianas) |
| 7 | Revisar sistemáticamente las estancias largas | −5 % de estancia ≈ 5 camas; volver a la de 2023 ≈ 15 camas. Las estancias de más de 14 días ocupan unas 36 camas; las de más de 30 días pasaron de 6 a 13 camas entre 2023 y 2025 | Inconsistente según la población | Media |

## 3. Detalle

### R1. Registrar mejor los datos (prioridad 1)
- **Qué cambiar:** registrar la hora de salida de urgencias en todas las atenciones (hoy el 36–42 % de las etapas de urgencias no la tiene), registrar
  la hora en que se asigna la cama, y evitar que un mismo ingreso quede en dos pacientes.
- **Por qué:** el 41 % de los episodios hospitalizados tenía una estancia duplicada en otra persona. Sin corregirlo se estimaban 27,7 ingresos por día
  (son ~20) y ~146 camas ocupadas (son ~100). Desde el 10 de abril de 2026 el registro de las etapas se degrada: la auditoría en la base muestra que las visitas no bajaron en mayo, así que no es menos demanda, y esos días no se usan para estimar nivel ni evaluar. (HALLAZGOS 2; CLAUDE.md 4.6, 4.8 y 4.9)
- **Evidencia externa:** no aplica; es un requisito para medir cualquier mejora. Como referencia, el estudio de Bradford (ver sección 4) también encontró
  fechas de atención faltantes en el 23–43 % de los registros de urgencias: no es un problema exclusivo del HUN.
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

### R3. Reunión diaria de camas con alertas (prioridad 3)
- **Qué hacer:** una reunión corta de 10 a 15 minutos a media mañana con censo, altas previstas e ingresos previstos, apoyada en las alertas de
  `src/alertas.py`: día congestionado a las 12 h y ocupación alta.
- **Por qué (nuestros datos):** a las 12 h la alerta de día congestionado tiene AUC de 0,94 y detecta 5 de cada 6 días congestionados (28 alertas en
  120 días, 54 % de precisión). Para la ocupación a 24 h, "lo mismo que ahora" funciona mejor que una proyección (precisión 75 %, detección 90 %). Se
  liberan ~20 camas por día, solo como orden de magnitud. (HALLAZGOS 5.2)
- **Evidencia externa (verificada):**
  - La guía práctica de Becker's (2014), que resume recomendaciones del Institute for Healthcare Improvement, propone 10–15 minutos con un orden fijo:
    censo, altas, ingresos y traslados previstos por unidad. **Es una guía, no un estudio: no reporta resultados.**
  - Un resumen de congreso de Wake Forest (Hospital Medicine 2019, unidad de 38 camas, antes y después, sin grupo de comparación) usó una reunión de
    menos de 10 minutos (promedio 8,3). Las órdenes de alta y las salidas fueron más tempranas, pero **la estancia no cambió** (p = 0,98).
  - El caso de NHS Dumfries and Galloway (Escocia, publicado por el gobierno escocés) describe reuniones diarias de coordinación y gestión dinámica
    del alta, y reporta menos estancia. **Ojo:** las reuniones eran parte de una intervención organizativa más amplia, y el informe no demuestra que las
    reuniones por sí solas causaran la reducción. Es un caso descriptivo, no un estudio con grupo de comparación.
- **Cómo medirla:** alertas atendidas, acciones tomadas, ocupación a las 12 h.
- **Límite:** las alertas se probaron sobre días pasados con pocos días congestionados (18); las cifras pueden moverse. **Por confirmar:** `CLAUDE.md` 4.8 avisa que los detalles de las alertas de camas son de la regla anterior (v3.7), así que la precisión y la detección de la alerta de ocupación pueden cambiar al recalcularlas. La evidencia externa es de casos
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
- **Ojo al comparar:** Baystate mide *órdenes* de alta; el HUN y los demás miden la *salida* del paciente. Una orden antes del mediodía no garantiza que la cama
  quede libre antes del mediodía.
- **Cómo medirla:** % de altas antes de las 12 h; hora mediana de asignación de cama; espera de quien llega de 12 a 18 h.
- **Complemento de bajo costo:** dar altas también en fin de semana y festivos. Las altas por cada 100 camas bajan 27 % el domingo y 34 % en festivos, pero el efecto estimado es pequeño: ~1–2 camas equivalentes (`docs/efecto_fin_de_semana.md`).
- **Límite:** es una cota con supuestos (el alta de los demás pacientes no cambia; la ocupación es de ~103 camas a las 12 h frente a las 106 que dio el HUN). Mejora la **hora** de la cama,
  no la capacidad. Todos los estudios externos son de un solo centro y sin grupo de comparación.

### R5. Alerta por paciente a las 48 h sin cama (prioridad 5)
- **Qué hacer:** cuando un paciente lleva 48 h desde su llegada sin cama, avisar a un responsable que revise por qué.
- **Por qué (nuestros datos):** ~4,1 alertas por día; el 51 % de esos pacientes termina esperando más de 72 h, con 24 h de margen. A las 36 h serían 5,5 por día
  (38 %); a las 60 h, 2,7 por día (79 %, solo 12 h de margen). (HALLAZGOS 5.2)
- **Evidencia externa:** no se encontró un estudio que evalúe esta alerta concreta. La revisión de Oskvarek y colegas (2026) menciona la gestión activa de
  camas entre las medidas prometedoras, sin evidencia de alta calidad.
- **Límite:** solo cuenta a quienes luego se hospitalizan, así que en tiempo real habría más alertas; riesgo de fatiga por alertas. Sin una acción definida
  para cada alerta no sirve.

### R6. Protocolo para quien llega entre las 13 y las 18 h y se hospitaliza (prioridad 6)
- **Qué hacer:** anticipar la decisión de ingreso y la solicitud de cama durante la tarde, para no esperar al ciclo de altas del día siguiente.
- **Por qué (nuestros datos):** mediana de espera de 23,6 h al llegar entre las 13:00 y las 18:59, contra 15,7 h al llegar entre las 6:00 y las 11:59
  (HALLAZGOS 4.4 describe el mismo patrón por hora: ~25 h al llegar de 13 a 16 h, con un salto a las 13:00). La carga del momento explica unos dos quintos
  del efecto de la tarde; el resto no.
- **Impacto:** llegan unos 6,4 pacientes por día en esa franja. Si su espera bajara a la de la mañana, se evitarían **~49 horas-paciente por día midiendo con
  medianas (11 % del exceso de 455 horas por día) pero solo ~11 midiendo con promedios (2 %)**, porque los promedios de la mañana y de la tarde se parecen
  (~31–32 h) y los dominan las esperas largas. Por eso es de confianza baja: ayuda a la espera típica, no a la cola de esperas de varios días.
- **Relación con los diagnósticos (A3):** la espera larga se concentra en pacientes de ortopedia, riñón y vías urinarias, digestivo y cáncer (29–39 h), frente a
  ~9–13 h en cardiovascular, neurológico y respiratorio (HALLAZGOS 4.5b; `docs/diagnosticos_y_tiempos.md`). Si se confirma que es una fila por tipo de cama o servicio, el protocolo de la tarde
  podría enfocarse en esos servicios. Hipótesis sin comprobar: la base no tiene servicio ni piso.
- **Fuente:** `src/impacto_llegada_tarde.py` → `resultados/tablas/impacto_llegada_tarde.csv` (estancias únicas, feb-2023 a abr-2026).
- **Evidencia externa:** no se encontró.
- **Límite:** asociación por hora de llegada, no causa. La espera va de la llegada a la asignación de cama (así lo confirmó el HUN): mezcla atención clínica con espera de cama y no se pueden separar con los datos. **Por confirmar:** el valor con promedios aparecía como ~9 y ~11 en versiones anteriores; aquí se usa el de `docs/HALLAZGOS.md` y falta contrastarlo con `impacto_llegada_tarde.csv`.

### R7. Revisar las estancias largas (prioridad 7)
- **Qué hacer:** revisión semanal de pacientes con estancias de más de 7 días, con gestión de casos (una persona que coordina el plan y el alta de cada paciente), con foco en las de más de 14 días.
- **Por qué (nuestros datos):** la ocupación subió 12 % (94 a 105 camas) por la estancia (+16 %). Con la ley de Little: bajar la estancia 5 % libera ~5 camas;
  volver a la de 2023, ~15. En 2025 las estancias de más de 14 días (7,3 % de las estancias) ocupan unas 36 camas. Estancias: mediana 71 h, percentil 75 de 144 h, percentil 90 de 280 h. (HALLAZGOS 4.2 y 4.6)
- **Evidencia externa:** una revisión de 19 revisiones sistemáticas (*JAMA Netw Open* 2021, encargada por la agencia AHRQ de
  Estados Unidos) evaluó 8 estrategias. Las rutas clínicas (protocolos paso a paso por enfermedad) y la gestión de casos se asociaron con menos estancia en
  **insuficiencia cardíaca**. En pacientes con varias enfermedades, la planificación del alta y los equipos interdisciplinarios dieron **resultados inconsistentes**.
- **Qué dice A2:** cerca de la mitad del aumento de la estancia media viene de las estancias de más de 30 días (de 54 a 117 por año); del resto, una parte importante es la llegada de visitas «Treatment urgency». La mediana casi no cambió (`docs/factores_estancia.md`).
- **Límite:** es una asociación y requiere revisión clínica. No es una recomendación de «reducir días evitables»: las camas de baja actividad son ~6 y no crecen, y las estancias largas son de pacientes con actividad clínica (`docs/dias_cama_baja_actividad.md`).

## 4. Lo que los datos NO respaldan
- **Cuántas camas harían falta (por decidir con Daniela si este punto sigue en esta lista):** los datos no permiten calcularlo. La ocupación media de 2025 (105) roza las 106 camas que dio el HUN y las supera el 42 % de las horas; en adultos es el 101 % de sus 88 camas. No se distingue si es sobreocupación o una capacidad real mayor. Por otro lado, la espera casi no sube con la ocupación (la carga explica 0,1 punto de la variación) y la ocupación subió por la estancia, no por la demanda. **Decir que los datos «no respaldan» más camas sería demasiado fuerte; tampoco lo piden.**
- **Más personal según el día de la semana:** el día de la semana y los festivos casi no cambian la espera.
- **Priorizar a un paciente concreto por riesgo de esperar:** un modelo con lo que se sabe al llegar acierta apenas mejor que el azar (AUC 0,60) y todos los factores
  juntos explican solo el 15,8 % de la variación.
- **Un centro de comando o tablero como solución en sí:**
  - El estudio con mejor diseño que encontramos (Mebrahtu y colegas, *Int J Qual Health Care* 2023, Bradford, Reino Unido, series de tiempo interrumpidas) **no halló cambio
    significativo en la estancia** de los ingresos por urgencias en ninguna fase. Coincidió con el COVID-19, lo que complica separar efectos.
  - Los casos de éxito publicados son **autoinformados**. Por ejemplo, Queen's Health System (Hawái) reporta 1,07 días menos de estancia, 64 % menos *boarding* y 20 millones
    de dólares de ahorro, pero las cifras las dio el propio hospital, la nota se publicó en colaboración con el proveedor del centro de comando, no hay grupo de comparación
    y el ahorro es un cálculo con un costo diario supuesto.

## 5. Qué quedó sin respuesta del HUN
La sesión del 29-oct fue la última, así que estos puntos se declaran como limitaciones:
1. Desde cuándo rige el número de camas (106 y 58 camillas) y cuál es la meta de tiempo para asignar cama.
2. Por qué se degrada el registro de las etapas desde el 10-abr-2026 (la auditoría del 2-nov descarta que sea menos demanda).
3. Dónde está el paciente durante el tiempo sin etapa antes de la cama (~1 de cada 4 hospitalizados) y qué significa esa espera en urgencias.

## 6. Fuentes y verificación (25-oct-2026; comprobación parcial el 6-nov)

**Comprobación del 6-nov:** se volvieron a abrir Artenstein, Bailey, Wertheimer y Mebrahtu y sus cifras coinciden; de ahí sale el ajuste de la frase sobre Wertheimer en R4. No se confirmó que Bailey no midiera *boarding*. Las otras ocho fuentes conservan la verificación de octubre.

| Fuente | Qué es | Se usa en | Verificación |
|---|---|---|---|
| Artenstein AW y colegas. *Decreasing Emergency Department Walkout Rate and Boarding Hours by Improving Inpatient Length of Stay.* West J Emerg Med 2017;18(6):982–992. [PMC5654890](https://pmc.ncbi.nlm.nih.gov/articles/PMC5654890/) | Proyecto de mejora, 24 meses, Baystate (720 camas), sin grupo de comparación | R4 | Texto completo leído. **Corrección:** las 2,1 h son de *boarding*, no de espera total en urgencias; la tasa ya partía de ~43 % |
| Kausar K y colegas. *Implementing and evaluating a discharge before noon initiative in a large tertiary care urban hospital.* Jt Comm J Qual Patient Saf 2024;50(2):127–138. Resumen en [The Hospitalist](https://www.the-hospitalist.org/hospitalist/article/38356/critical-care/implementing-and-evaluating-a-dbn-initiative-in-a-large-tertiary-care-urban-hospital/) | Estudio retrospectivo antes y después, Maimonides | R4 | Resumen de The Hospitalist leído. Citar la revista original, no The Hospitalist. Los 41 min son de *boarding* |
| Bailey R y colegas. *Increasing and sustaining discharges by noon – a multi-year process improvement project.* BMC Health Serv Res 2024;24:478. [doi:10.1186/s12913-024-10960-x](https://bmchealthservres.biomedcentral.com/articles/10.1186/s12913-024-10960-x) | Proyecto de mejora en un hospital de Texas, 41 meses | R4 | Texto completo leído. **Corrección: no es una revisión** (el borrador lo llamaba así) |
| Wertheimer B y colegas. *Discharge Before Noon: An Achievable Hospital Goal.* J Hosp Med 2014;9:210–214. [PDF](https://cdn.mdedge.com/files/s3fs-public/pdfs/journals/jhm2154.pdf) | Antes y después, NYU Langone, dos unidades | R4 | Texto completo leído. **Nueva** |
| Siddique SM y colegas. *Interventions to Reduce Hospital Length of Stay in High-risk Populations: A Systematic Review.* JAMA Netw Open 2021. [PMC8453321](https://pmc.ncbi.nlm.nih.gov/articles/PMC8453321/) | Revisión de 19 revisiones sistemáticas | R7 | Texto original revisado por Samuel (25-oct): coincide (19 revisiones; rutas clínicas y gestión de casos en insuficiencia cardíaca; resultados inconsistentes en otros pacientes) |
| Becker's Hospital Review. *The AM Bedside Huddle: What to Cover to Achieve Streamlined Patient Flow.* 2014. [Enlace](https://www.beckershospitalreview.com/capacity-management/the-am-bedside-huddle-what-to-cover-to-achieve-streamlined-patient-flow.html) | Guía práctica (resumen del IHI), sin resultados | R3 | Leído |
| Sunkara P y colegas. *Lightning Huddle: An Innovative Method For Improving Patient Throughput.* Hospital Medicine 2019, resumen 463. [SHM](https://shmabstracts.org/?p=23287) | Resumen de congreso, antes y después, Wake Forest | R3 | Leído |
| Mebrahtu TF y colegas. *The impact of hospital command centre on patient flow and data quality: findings from the UK National Health Service.* Int J Qual Health Care 2023;35(4):mzad072. [PDF](https://eprints.whiterose.ac.uk/209410/1/mzad072.pdf) | Cohorte retrospectiva con series de tiempo interrumpidas, Bradford | Sección 4, R1 | Texto completo leído |
| Becker's Hospital Review. *The Queen's Health Systems saves $20 million in the first year after opening a command center.* 2025. [Enlace](https://www.beckershospitalreview.com/healthcare-information-technology/the-queens-health-systems-saves-20-million-in-the-first-year-after-opening-a-command-center/) | Nota patrocinada con datos del propio hospital | Sección 4 | Leído |
| Hoot NR, Aronsky D. *Systematic review of emergency department crowding: causes, effects, and solutions.* Ann Emerg Med 2008;52(2):126–136. [PubMed 18433933](https://pubmed.ncbi.nlm.nih.gov/18433933/) | Revisión sistemática, 93 estudios | Sección 1 | Verificado con un resumen académico ([WUSTL Journal Club](https://journalclub.wustl.edu/2008/08/09/systematic-review-of-emergency-department-crowding-causes-effects-and-solutions)); PubMed no cargó |
| Oskvarek JJ y colegas. *Emergency Department Crowding in the Modern Era: A Systematic Review (2018–2025).* Clin Exp Emerg Med 2026. [Enlace](https://hsrc.himmelfarb.gwu.edu/gwhpubs/8570) | Revisión sistemática, 226 estudios | Sección 1, R5 | Ficha y resumen leídos |
| NHS Dumfries and Galloway, *Balancing capacity with demand* (gobierno de Escocia). [Enlace](https://www.gov.scot/publications/nhs-dumfries-galloway-case-study-balancing-capacity-demand-dumfries-galloway-9781788510479/pages/15/) | Caso descriptivo de una intervención organizativa | R3 | Texto original revisado por Samuel (25-oct): describe reuniones diarias y gestión del alta con menos estancia, pero dentro de una intervención más amplia; no aísla el efecto de las reuniones |

## 7. Estado

**B2 lista para revisión de Daniela (6-nov-2026).** Cada fuente externa tiene su nivel de verificación (sección 6) y las cifras propias salen de `docs/HALLAZGOS.md`, `CLAUDE.md`, los documentos de análisis citados o un script.

Falta resolver con Daniela:
- **Sección 4:** si el punto sobre cuántas camas harían falta sigue en esa lista.
- **R6:** contrastar ~11 frente a ~9 horas-paciente con `impacto_llegada_tarde.csv`.
- **R3:** recalcular la alerta de ocupación con la regla v3.8 (el corte de 123 camas es de antes).
- **R7:** `CLAUDE.md` 4.8 dice que las estancias de más de 14 días son el 3 %, y `docs/factores_estancia.md` dice 7,3 % en 2025. Aquí se usa 7,3 %, que es la tabla por año; falta corregir la otra cifra.
- **Hallazgo 2:** 80 % + 21 % suma 101 % (el roadmap de Power BI dice 79 % y 21 %).

Lo que puede cambiar estas recomendaciones más adelante:
- **A4 y A5 (Anthony):** si el modelo explicativo o la simulación Monte Carlo cambian las cifras de R4 o R7, actualizar aquí y en `powerbi/recomendaciones_tabla.csv` (la usa la página 4.1 del dashboard).
