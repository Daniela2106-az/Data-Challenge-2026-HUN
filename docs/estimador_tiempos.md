# A6 · Estimador de tiempos de atención (7-nov-2026)

**Qué pide el instructivo (componente 3):** «modelos analíticos o predictivos que permitan estimar tiempos de atención». La pregunta es: cuando llega un paciente, ¿cuánto va a esperar cama, cuánto se va a quedar hospitalizado o cuánto va a estar en urgencias?
Código: `src/estimador_tiempos.py`. Tablas (fuera de git): `resultados/tablas/estimador_tiempos.csv` y `estimador_validacion.csv`. Gráfico: `resultados/graficos/estimador_tiempos.png`.

## Por qué un rango y no un número
Ya se sabía que el tiempo de **un** paciente no se puede predecir con lo que se conoce al llegar: esperar más de 24 h tiene AUC 0,60 y la estancia, R² cercano a 0 (`CLAUDE.md` 6b). Por eso el estimador da el **rango típico de pacientes parecidos**: los percentiles 25, 50 (mediana), 75 y 90. Por ejemplo: «de cada 4 pacientes como este, 1 esperó menos de X horas y 1 más de Y». Además, da la **probabilidad de hospitalizarse**.

## Cómo se armó
- **Perfil de llegada:** solo lo que se sabe al llegar. Son cuatro variables: bloque de 3 horas de la llegada (8 bloques), grupo de edad (7), tipo de visita (urgencias, «Treatment urgency», ambulatoria) y sexo. En total hay 336 perfiles.
- **Mínimo de casos:** si un perfil tiene menos de 30 casos, se usa el perfil más general que sí los tenga. Primero se quita el sexo, luego el tipo de visita y luego la edad. La tabla dice qué nivel usó cada perfil (columna `_nivel`: 4 = las cuatro variables, 2 = solo hora y edad).
- **Periodo:** llegadas del 1-feb-2023 al 9-abr-2026, el periodo confiable (`CLAUDE.md` 4.9).
- **Las cuatro medidas:**

| Medida | Quiénes | Total del periodo |
|---|---|---|
| Probabilidad de hospitalizarse | Episodios con atención (no solo admisión), cada estancia contada una vez | 9,6 % (n = 241.694) |
| Espera de cama | Estancias únicas; de la llegada a la asignación de cama | Mediana 18,5 h, p25 6,4, p75 37,8, p90 72,9 (n = 22.819) |
| Estancia en cama | Estancias únicas con alta antes del 10-abr-2026 | Mediana 69,5 h, p25 40,0, p75 139,8, p90 265,5 (n = 23.114) |
| Urgencias sin hospitalizar | Episodios con algún tiempo en urgencias; Kaplan-Meier (los `minimo_conocido` cuentan como censurados) | Mediana 11,2 h, p25 6,6, p75 27,1, p90 80,6 (n = 108.070) |

Los totales coinciden con los del proyecto: la espera de 18,6 h (`HALLAZGOS.md` 4.2), la estancia de 69 h (`factores_estancia.md`) y la Kaplan-Meier de urgencias de 11,2 y 80,6 h (`supervivencia_urgencias.md`). La probabilidad de hospitalizarse (9,6 %) es algo menor que el 10,5 % de A1 porque aquí los registros duplicados de una estancia salen también del denominador.

## Prueba con datos nuevos (validación temporal)
La tabla se armó con feb-2023 a jun-2025 y se probó con jul-2025 a 9-abr-2026. Para la estancia, la prueba llega solo hasta el 9-ene-2026, para que las estancias largas alcancen a terminar. Se miden dos cosas:
- **¿Los rangos aciertan?** Si el p25 está bien, el 25 % de los casos nuevos debería quedar por debajo; con la mediana, el 50 %, y así sucesivamente.
- **¿Cuánto ayuda el perfil?** Es la mejora frente a dar el mismo rango general a todos, medida con la pérdida de cuantiles (el error estándar para percentiles).

| Medida (perfil completo) | Debajo del p25 | p50 | p75 | p90 | Mejora frente al rango general |
|---|---|---|---|---|---|
| Espera de cama | 27,9 % | 52,0 % | 73,1 % | 87,0 % | 5,4 % |
| Estancia en cama | 25,9 % | 46,9 % | 71,7 % | 87,8 % | 2,0 % |
| Urgencias sin hospitalizar (Kaplan-Meier) | 28,4 % | 52,9 % | 76,8 % | 91,8 % | — |

**Cuánto suma cada variable en la espera de cama:** hora sola, 0,6 %; más la edad, 4,4 %; más el tipo de visita, 5,3 %; más el sexo, 5,4 %. En la estancia: 0 %, 1,5 %, 2,1 % y 2,0 %.

**Probabilidad de hospitalizarse:** AUC 0,62 con el perfil completo (0,52 con la hora sola, 0,58 con la hora y la edad, 0,61 con el tipo de visita). Además está bien calibrada: estimó 9,85 % y en la prueba fue 10,1 %.

**Qué significa:**
1. **Los rangos son honestos.** En datos que el estimador no había visto, los casos caen donde dicen los percentiles, con un error de 3 puntos o menos en casi todos. La excepción es el p90 de la espera y de la estancia: cae el 87–88 % debajo en vez del 90 %, porque los peores casos siguen empeorando (`HALLAZGOS.md` 4.3). Conviene leer el p90 como un piso.
2. **El perfil afina poco.** Saber la hora, la edad, el tipo de visita y el sexo mejora el rango solo un 5 % en la espera y un 2 % en la estancia frente a no saber nada del paciente. Los rangos son anchos porque la espera depende de cosas que la base no registra, como el servicio, el tipo de cama o la gravedad. Es el mismo hallazgo del modelo explicativo (R² de 15,8 %, `HALLAZGOS.md` 4.5), visto desde otro lado.
3. **Lo que más separa a los pacientes es la edad y el tipo de visita**, no la hora. Entre perfiles, la mediana de espera va de 2,5 h a 44,9 h (mediana 15,2 h), y la probabilidad de hospitalizarse, de 4 % a 53 %.

## Ejemplos (perfil completo, todo el periodo)
| Llegada | Prob. de hospitalizarse | Espera de cama: p25 / mediana / p75 / p90 | n de estancias |
|---|---|---|---|
| Entre las 9 y las 11 h, mujer de 30–44 años, urgencias | 8 % | 11,8 / 30,4 / 55,1 / 83,4 h | 474 |
| Entre las 15 y las 17 h, mujer de 30–44 años, urgencias | 7 % | 15,1 / 29,5 / 53,3 / 90,7 h | 294 |
| Entre las 15 y las 17 h, hombre de 75 años o más, urgencias | 15 % | 3,2 / 24,5 / 48,2 / 93,2 h | 132 |

Para consultar cualquier perfil: `estimar(hora, grupo_edad, tipo_visita, sexo)` en `src/estimador_tiempos.py`, o filtrar `estimador_tiempos.csv`.

## Límites (deben ir junto al estimador)
- **Es un rango de pacientes parecidos, no una predicción para una persona.** Sirve para planear y para comunicar expectativas («la mitad de los pacientes como usted esperan menos de X h»), no para prometer un tiempo.
- **Urgencias:** el rango es solo de los episodios con algún tiempo registrado. La mitad de los episodios de urgencias no tiene ningún tiempo y ningún método lo recupera (`docs/supervivencia_urgencias.md`). La columna `urgencias_sin_hosp_h_pct_con_hora_salida` es la parte con cierre **entre quienes tienen algún tiempo**. Además, Kaplan-Meier supone que la falta de cierre no depende de la duración. En 5 perfiles el p90 de urgencias queda vacío porque supera el último dato observado.
- **Espera de cama:** va de la llegada a la asignación de cama, como confirmó el HUN. Mezcla la atención clínica en urgencias con la espera por una cama, y no se pueden separar.
- **Edad y sexo de las estancias duplicadas:** esta corrida no tuvo los archivos del lote 4 de `src/auditoria_bd.py` (`P02` y `P03`). Por eso, en las estancias registradas en dos personas se conservó el registro con más información, que es el de la persona real en ~81–85 % de los casos (`CLAUDE.md` 4.10). Con esos archivos, la edad y el sexo de esas estancias quedarían corregidos.
- **Registros réplica:** las llegadas incluyen al menos un 4 % de réplicas (`CLAUDE.md` 4.6), que pesan en la probabilidad de hospitalizarse.
- **Asociación, no causa:** que un perfil espere más no dice por qué.
- **Cama o silla:** según el equipo (7-nov), a muchos pacientes se les atiende en sillas, y no se sabe si eso se registra como estar en cama. La base no tiene columna de cama, silla, piso ni servicio (`CLAUDE.md` 4.8). Si a un paciente hospitalizado se le registra la etapa 9201 estando en una silla o camilla de apoyo, la «espera de cama» mide la espera hasta la asignación administrativa, no hasta una cama real. Además, la ocupación de hospitalización incluiría puestos que no son camas, lo que explicaría que pase de las 106 camas el 42 % de las horas de 2025. En urgencias ya se sabía que la etapa 3045729 incluye sillas, consultorios y observación.

## Segunda parte: la espera en dos series (sin cama y demora del servicio)
Código: `src/espera_dos_series.py`. Tablas (fuera de git): `espera_dos_series_*.csv`. Gráfico: `resultados/graficos/espera_dos_series.png`.

**Cómo se separa.** Cada hora se cuentan las camas ocupadas por zona, con estancias únicas: adultos (15 años o más) frente a 88 camas y niños frente a 18, las capacidades que dio el HUN (`CLAUDE.md` 4.7). Es la misma división por zona de `docs/ocupacion_por_zona.md`. La espera de cada paciente se reparte hora por hora en dos partes que suman la espera total:
- **Sin cama:** horas en que la zona del paciente estaba llena.
- **Demora del servicio:** horas en que el conteo mostraba camas libres.

Con esas dos partes se arman dos series diarias, según la fecha de llegada.

**Reparto por año (promedio por paciente, capacidad del HUN):**

| Año | % de horas con adultos llenos | Espera media | Sin cama | Demora del servicio | % de la espera sin cama |
|---|---|---|---|---|---|
| 2023 | 1,6 % | 28,0 h | 2,3 h | 25,7 h | 8 % |
| 2024 | 37,5 % | 29,2 h | 10,9 h | 18,3 h | 37 % |
| 2025 | 58,3 % | 33,4 h | 18,8 h | 14,6 h | 56 % |
| 2026 (ene–9 abr) | 37,6 % | 34,1 h | 12,7 h | 21,4 h | 37 % |

**Prueba de sensibilidad:** con capacidades 10 % mayores (97 y 20), la parte sin cama baja a 5–10 % todos los años. **La separación depende casi por completo de cuántas camas haya de verdad**, y ese número no está confirmado (el HUN no dijo a qué fecha corresponde). Además, si se usan sillas o camillas de apoyo y se registran como cama, «zona llena» no significa que no hubiera dónde ubicar al paciente.

**Qué dicen las dos series:**
1. **Con las camas que dio el HUN, el cambio es de composición.** En 2023 casi toda la espera ocurría con camas libres en el conteo. En 2025, más de la mitad ocurrió con la zona de adultos llena. La espera media subió unas 5 h, pero la parte sin cama subió unas 16 h y la de servicio bajó unas 11 h. Coincide con lo que mostró Daniela: la ocupación de adultos pasó del 88 % al 101 % de sus camas (`docs/ocupacion_por_zona.md`).
2. **Pero la espera total casi no responde a esa diferencia.** La cola de espera no cambia con la ocupación (`docs/capacidad_efectiva.md`). Cuando las camas están llenas casi todo el tiempo, las horas pasan de "servicio" a "sin cama" por construcción, sin que el paciente espere más. Por eso la separación se lee como una descripción de en qué condiciones se esperó, no como la causa de la espera.
3. **La hora de llegada mueve la demora del servicio, no la parte sin cama.** La parte sin cama es pareja en el día (~7–14 h por paciente). La de servicio es de 13–15 h para quien llega de noche y de 19–22 h para quien llega entre las 7 y las 19 h. Es coherente con las altas tardías y la asignación de cama por la tarde (`CLAUDE.md` 6b): esa parte depende del proceso del día, no del conteo de camas.

**Pronóstico con las dos series** (nivel de los 28 días previos × día de la semana; el nivel solo usa llegadas de hace 7 días o más, porque la espera de quien llegó ayer aún no se conoce completa; prueba de jul-2025 a 9-abr-2026):

| Método | Error medio diario, a 1 día | a 7 días | Error medio semanal, a 7 días |
|---|---|---|---|
| Dos series (sin cama + servicio) | 8,8 h | 8,7 h | 4,5 h |
| Una sola serie (espera total) | 8,8 h | 8,7 h | 4,6 h |
| Promedio histórico por día de la semana | 8,4 h | 8,4 h | 4,6 h (sesgo de −2,9 h) |

La espera media diaria ronda las 33 h y cada día se hospitalizan unas 19 personas, así que el promedio de un día es muy ruidoso. Por semana, el error baja a ~4,5 h (~14 %), igual que pasa con los ingresos (`CLAUDE.md` 6b). **Separar en dos series no mejora el pronóstico:** da lo mismo que una sola. Lo que aporta es la lectura (cuánto de la espera ocurre con las camas llenas y cuánto con camas libres) y un indicador para seguir mes a mes, siempre que el HUN confirme su número de camas.

**Por perfil:** en la mediana de cada perfil, la parte sin cama va de 0 % a 88 % (mediana 5 %), porque la mediana de esa parte es 0 en muchos perfiles: la mayoría de los pacientes no espera con la zona llena y unos pocos esperan mucho así. Las columnas por perfil están en `espera_dos_series_por_perfil.csv`.

**Relación con el trabajo del equipo:**
- **Daniela:** zonas y capacidades de `docs/ocupacion_por_zona.md`, el aviso de `docs/capacidad_efectiva.md`, la espera de la estancia (regla v3.8) y la mayor espera de las mujeres (A1, por eso el perfil incluye el sexo).
- **Anthony:** su simulación Monte Carlo de camas (A5) todavía no está en el repositorio. Cuando exista, la parte sin cama se puede proyectar con su banda de ocupación en lugar del nivel reciente; su idea de A2b y A7 (qué comparten las estancias que se disparan) ya está en los documentos de Daniela.

## Tercera parte: tres métodos comparados (cuál estima mejor)
Código: `src/comparar_estimadores.py`. Tablas (fuera de git): `comparacion_estimadores_*.csv` y `m1_probabilidad_por_hora_reloj.csv`. Gráfico: `resultados/graficos/comparacion_estimadores.png`.

**Los métodos:**
- **M1, tiempo restante (supervivencia por hora).** Para cada hora de espera estima la probabilidad de recibir cama en la hora siguiente. Usa cuánto lleva esperando el paciente, la hora del reloj, el día de la semana, la cola y la ocupación de su zona, la edad, el sexo y el tipo de visita, con árboles de gradiente. Hora por hora sale la distribución del tiempo que falta, y se puede recalcular en cualquier momento de la espera.
- **M2, al llegar con más variables (regresión por cuantiles).** Un modelo por percentil, con lo que se sabe al llegar más el estado del hospital: cola, ocupación y llegadas de las 6 h previas.
- **M3, modelo de cola.** Las camas se asignan a la tasa histórica de cada zona, hora y día de la semana. En M3a, cada hora recibe cama un paciente al azar de la cola. En M3b, la reciben en orden de llegada.
- **Referencias:** el rango general (igual para todos) y la tabla de perfiles de la primera parte.

**La cola** es el número de pacientes de la zona que ya llegaron, se hospitalizarán y aún no tienen cama. En el hospital equivale a los pacientes con orden de hospitalización pendiente, que sí se conocen en el momento. Aquí también incluye la atención clínica previa a esa orden, porque los datos no la separan. Para estimar hacia adelante, la cola y la ocupación se dejan fijas en el último valor conocido.

**Prueba:** los métodos se entrenaron con llegadas de feb-2023 a jun-2025 y se probaron con las 5.430 estancias de jul-2025 a 9-abr-2026.

**Al llegar:**

| Método | Mejora frente al rango general | Error de la mediana | Debajo de p25 / p50 / p75 / p90 |
|---|---|---|---|
| **M1 tiempo restante** | **6,5 %** | 24,0 h | 27,0 / 52,6 / 75,8 / 89,1 % |
| M2 al llegar con más variables | 6,3 % | 24,0 h | 27,1 / 52,0 / 74,0 / 87,0 % |
| Tabla de perfiles (primera parte) | 5,8 % | 24,2 h | 27,9 / 52,0 / 73,1 / 87,0 % |
| M3a cola, orden aleatorio | −0,3 % | 25,7 h | 31,3 / 53,9 / 74,8 / 87,4 % |
| M3b cola, orden de llegada | −17,9 % | 28,0 h | 59,1 / 65,7 / 70,7 / 75,6 % |

**Durante la espera** (lo que falta para quienes siguen sin cama), mejora frente al rango general en las mismas condiciones:

| Horas esperando | M1 | Tabla de perfiles | M3a | M3b |
|---|---|---|---|---|
| 6 h | **6,9 %** | 5,5 % | 0,4 % | −16,9 % |
| 12 h | **6,0 %** | 3,7 % | 0,5 % | −15,6 % |
| 24 h | **4,5 %** | 2,2 % | 1,4 % | −14,2 % |
| 48 h | **1,6 %** | −0,9 % | −2,4 % | −18,3 % |

**Agosto y septiembre de 2025:** según el equipo, el HUN tuvo sobredemanda porque los hospitales cercanos fueron intervenidos por el Estado y quedó como la única opción de la zona. En los datos se ve poco: un 6–7 % más de llegadas que en los mismos meses de 2024, con ingresos a cama y espera mediana normales. Evaluados aparte, esos meses dan el mismo orden de métodos: M1 mejora 5,9 % y M2 6,5 % en ago-sep, frente a 6,7 % y 6,3 % en el resto. Los modelos no fallaron más en ese periodo.

**Veredicto:**
1. **El mejor es M1 (tiempo restante).** Gana o empata en todos los momentos, tiene los percentiles mejor calibrados (el p90 acierta en el 89 % de los casos, contra el 87 % de los demás) y es el único que mejora la estimación a medida que el paciente sigue esperando. Al llegar, M2 da casi lo mismo, pero solo sirve en ese momento.
2. **El modelo de cola no funciona.** En orden de llegada falla mucho: confirma que el orden de llegada casi no predice el orden de cama (`CLAUDE.md` 6b). Con orden aleatorio no mejora al rango general, porque la cola casi no cambia la espera (`docs/capacidad_efectiva.md`).
3. **Ningún método achica mucho el rango.** El mejor mejora un 6–7 % frente a no saber nada del paciente. La espera depende sobre todo de cosas que la base no tiene, como el servicio, el tipo de cama, la gravedad y la orden de hospitalización. Esto no se arregla con un modelo más complejo, y debe decirse así en la entrega.
4. **Lo que más pesa en M1 es la hora del reloj.** La probabilidad de recibir cama en la hora siguiente es de ~1 % entre las 6 y las 12 h, sube a 5–8 % entre las 15 y las 17 h, baja a 1 % a las 18 h y llega a 8–10 % entre las 20 y las 22 h. Los datos crudos muestran lo mismo: el 24 % de las camas se asigna entre las 15 y las 17 h y el 37 % entre las 20 y las 23 h. Para quien espera en la mañana, lo más probable es recibir cama en la tarde o en la noche. Es coherente con las altas tardías (`CLAUDE.md` 6b). La segunda subida, de noche, no se había descrito antes; podría ser la hora en que se registra la asignación, no la del traslado.

**Recomendación para A6:** entregar M1 como el estimador principal («a esta hora y con esta cola, un paciente que lleva X horas esperando recibe cama en tantas horas, con este rango») y la tabla de perfiles como su versión simple para el dashboard. M2 y M3 quedan documentados como alternativas probadas y descartadas.

## Cuarta parte: la gravedad del paciente (triage)
Código: `src/triage_aproximado.py`. Tabla (fuera de git): `triage_aproximado.csv`.

En urgencias la prioridad se define con el **triage**: I (inmediata, riesgo vital), II (muy alta), III (media), IV (baja) y V (muy baja). **La base no trae el nivel de triage.** No está en ninguna de las 8 tablas, la etapa 9203 solo trae la hora, y entre los nombres de los diagnósticos no aparece ningún triage ni prioridad. Se probaron dos aproximaciones dentro del modelo de tiempo restante (M1), y ninguna es el triage:
- **Laboratorios de las primeras 6 h:** pedir exámenes temprano indica urgencia o complejidad. Se conocen a las 6 h. El 48 % de las estancias tiene alguno.
- **Grupo de diagnóstico:** es lo más parecido a la gravedad que hay. Los pacientes cardiovasculares y neurológicos reciben cama mucho antes (HALLAZGOS 4.5b), lo que sugiere que el hospital ya prioriza por gravedad. Pero el 88 % de los diagnósticos se registra tarde y el 35 % de las estancias no tiene ninguno. Por eso se usa como **escenario**: «¿cuánto mejoraría si el HUN registrara la gravedad al llegar?».

| Horas esperando | M1 sin gravedad | M1 + laboratorios de 6 h | M1 + grupo de diagnóstico (escenario) |
|---|---|---|---|
| 0 h (al llegar) | 6,5 % | 7,0 % (no válido: se conocen a las 6 h) | **12,2 %** |
| 6 h | 6,9 % | 7,0 % | **10,9 %** |
| 12 h | 6,0 % | 6,1 % | 9,2 % |
| 24 h | 4,5 % | 4,3 % | 6,4 % |
| 48 h | 1,6 % | 1,4 % | 1,7 % |

(Mejora frente al rango general. Los percentiles siguen bien calibrados en todas las versiones.)

**Qué significa:**
1. **Los laboratorios tempranos casi no ayudan** (+0,1 a +0,5 puntos).
2. **Una medida de gravedad al llegar casi duplicaría la mejora**, de 6,5 % a 12 %, y eso que el diagnóstico es una aproximación tosca y tardía. Un triage real de I a V debería servir más. Es un argumento concreto para la recomendación R1 (registrar mejor los datos): **registrar el nivel de triage en la base** permitiría estimar mejor la espera de cada paciente.
3. **Pasados los 2 días la gravedad ya no cambia la estimación.** Las esperas muy largas dependen de otras cosas.

**Siguiente paso posible: los procedimientos.** Los procedimientos que recibió el paciente (ingreso a UCI, intubación, ventilación, transfusión, reanimación, cirugía) indican qué tan grave fue. Daniela ya los extrajo de la base para A2b (lote 5 de `src/auditoria_bd.py`: `Q01_procedimientos_por_estancia.csv` y `Q03_nombres_de_conceptos.csv`), así que no hace falta otra consulta. En `Q03` se puede revisar además si algún concepto se llama «triage». Limitación: los procedimientos no tienen fecha, así que no se sabe si ocurrieron antes o después de recibir la cama. Servirían como escenario y para explicar, no para estimar al llegar.

## Cómo se usa en el dashboard
Las dos tablas son agregadas (una fila por perfil, solo con grupos de 30 casos o más) y no tiene datos por paciente. Puede alimentar una página «¿Cuánto esperaría un paciente como este?»: el usuario elige hora, edad, tipo de visita y sexo, y ve la probabilidad de hospitalizarse y los tres rangos con su n. La advertencia «rango típico de pacientes parecidos, no una predicción individual» va fija en la página. La estructura del dashboard (`docs/estructura_dashboard.md`) todavía no tiene esa página; falta decidir con Daniela dónde va.
