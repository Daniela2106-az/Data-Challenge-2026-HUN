# A9 · Estacionalidad anual del pronóstico de demanda (12-nov-2026)

**Problema.** El pronóstico (`src/modelo_pronostico.py`) ya modela la semana, los festivos, la semana santa, el Carnaval y el fin de año, pero no
**la forma del año**. Con ~3 ciclos anuales confiables (feb-2023 a 9-abr-2026), estimar 12 efectos de mes es frágil. La ficha A9 propone tomar
prestada la forma del año de **climatologías externas** de muchos años (la forma típica por semana, no los valores observados del futuro).

Script: `src/estacionalidad_anual.py`. Tablas: `estacionalidad_variantes.csv` y `estacionalidad_climatologias.csv` (en `HUN_TABLAS`, fuera de git).
Gráfico: `resultados/graficos/estacionalidad_anual.png`.

## Datos externos (públicos, fuera del repositorio, en `<datos>/externos/` con su README)
| Fuente | Qué trae | Licencia |
|---|---|---|
| Dengue en Barranquilla 2007–2022 (SIVIGILA; Quistberg, Sarmiento y Hoyos Botero, Harvard Dataverse 2025, doi:10.7910/DVN/P0KY1D) | 37.532 casos con año y semana epidemiológica | CC BY 4.0 |
| NASA POWER, punto de Barranquilla (lat 10,98, lon −74,80), 2005–2025 | Lluvia, temperatura y humedad diarias | Pública |

**Climatologías** (forma típica por semana del año, 53 valores): el dengue baja a mitad de año (semanas 11–26) y sube a fin de año (semanas 44–52);
la lluvia tiene los dos picos del Caribe (mayo y septiembre–octubre). Para el dengue se usa la forma **relativa** de cada año (casos de la semana
sobre el promedio de su año), así las epidemias grandes (2013, 2021, 2022) no dominan.

## Cómo se probó (sin mirar la prueba para decidir)
- Backtest igual al del modelo vigente: cortes cada 14 días, pronóstico a 365 días, destinos hasta el 9-abr-2026.
- Variantes: armónicos de Fourier del día del año (1 a 3; forma aprendida solo de nuestros datos), temperatura, y dengue y lluvia con rezagos de
  0, 2, 4, 6 y 8 semanas; combinaciones de las mejores. Todas estandarizadas.
- **Elección** con la validación de jul–dic 2025, error (WAPE) a 1–6 meses. **Regla de la ficha:** se acepta solo si mejora a 1–6 meses sin empeorar
  a 1–7 días. **Prueba** aparte: destinos de ene–9 abr 2026.

## Resultados (error relativo diario, WAPE)
**Llegadas con atención:**

| Variante | Validación 1–7 d | Validación 1–6 meses | Prueba 1–6 meses | Backtest 3–6 meses | Backtest 6–12 meses |
|---|---|---|---|---|---|
| Modelo actual | 8,8 % | 11,6 % | 10,5 % | 11,4 % | 11,6 % |
| Fourier, 1 armónico | 8,9 % | 9,9 % | 11,8 % | 9,3 % | 9,5 % |
| Lluvia (mejor rezago) | 8,7 % | 11,5 % | 13,1 % | 10,8 % | 10,9 % |
| **Dengue, 2 semanas antes (elegida)** | **8,7 %** | **9,6 %** | 10,6 % | **9,2 %** | **9,6 %** |
| Dengue + lluvia | 8,7 % | 10,0 % | 11,5 % | 9,4 % | 9,8 % |

Con la variante elegida ya dentro del modelo, el error del backtest completo queda en **8,0 % a 1–7 días (igual), 8,6 % a 1–3 meses (antes 9,3 %),
9,1 % a 3–6 meses (antes 11,4 %) y 9,6 % a 6–12 meses (antes 11,6 %)**. El sesgo a 3–12 meses baja de +4,2/+4,3 % a +3,2/+3,3 %.

**Ingresos a cama:** la mejor variante (Fourier, 3 armónicos) baja el error de validación a 1–6 meses solo de 17,7 % a 17,2 %, y en la prueba el
error a 1–7 días sube (16,2 % → 16,5 %). Está dentro del ruido de conteo (piso teórico ~18 %): **no se adopta**.

## Cómo leerlo (importante)
- **Lo que mejora el pronóstico es la forma del año, no el dengue en sí.** El coeficiente de la curva de dengue es **negativo** (−4,3 % por cada
  desviación estándar): las llegadas del HUN son más altas de mayo a agosto (~225–234 por día) y más bajas en diciembre (~193), justo al revés de la
  curva del dengue. La curva funciona como una descripción estable de «fin de año bajo, mitad de año alto», tomada de 16 años, y por eso le gana a
  la forma aprendida solo con nuestros 3 años (Fourier). **No** se puede decir que el dengue traiga o quite pacientes.
- **La prueba de 2026 no confirma ni contradice:** con solo ene–9 abr 2026 (99 días) el error a 1–6 meses queda igual (10,5 % frente a 10,6 %).
  La mejora se ve en el backtest de todo el periodo, que abarca los ciclos de 2024 y 2025.
- **La lluvia no ayuda** en ningún rezago, y la temperatura apenas.
- **Pendiente:** el calendario escolar y las infecciones respiratorias (IRA) no se probaron por falta de una fuente con fechas verificadas; podrían
  explicar mejor la caída de diciembre y el alza de mitad de año. Las proyecciones de población del DANE y el fenómeno de El Niño quedan como hipótesis.

## Diagnósticos de los niveles 1 y 2 de la ficha (`src/estacionalidad_diagnostico.py`)
**1. Ljung-Box (¿quedan patrones en los errores?).** En las llegadas con atención, la autocorrelación de los residuos de un día al siguiente baja de
0,39 a 0,30 con la estacionalidad (Q a 28 días de 2.456 a 840), pero **sigue siendo significativa** (p < 0,001). En los ingresos a cama los residuos
casi no tienen autocorrelación (0,03): ahí no hay nada más que modelar. Según la regla de la ficha, en las llegadas está indicado probar el **nivel 1**
(SARIMAX o un modelo aditivo). Ojo: el modelo en uso ya corrige el nivel con los últimos 28 días, cosa que esta prueba sobre el ajuste fijo no ve.

**2. Banda del 80 % fuera de muestra** (factores calculados con destinos antes de jul-2025; prueba jul-2025 a 9-abr-2026):

| Llegadas con atención | 1–7 d | 8–30 d | 1–3 meses | 3–6 meses | 6–12 meses |
|---|---|---|---|---|---|
| Cobertura sin estacionalidad | 74 % | 78 % | 78 % | 79 % | 72 % |
| Cobertura con estacionalidad | 71 % | 79 % | 76 % | **72 %** | **71 %** |
| Ancho de la banda, con estacionalidad | 24 % | 25 % | 26 % | 25 % | 25 % (antes 30–33 %) |

La banda queda **más angosta** (el modelo se equivoca menos dentro de la muestra) pero **cubre de menos** a 3–12 meses (71–72 % frente al 80 %
buscado). Ya cubría de menos antes (72–79 %). Pendiente: recalibrarla (nivel 2 de la ficha) sin usar la prueba para elegir el ancho. En los ingresos a
cama la banda cubre 78–87 %.

**3. Llegadas totales:** también mejoran a 3–12 meses (10,6 → 8,2 % y 10,5 → 8,5 %), pero a 1–7 días suben de 7,3 a 7,4 %; por la regla de la ficha
(no empeorar 1–7 días) **no se activa** para esa serie. El dashboard no la usa.

**4. Pronóstico a futuro regenerado** (`src/pronostico_futuro.py`, gráfico `resultados/graficos/pronostico_futuro.png`): las llegadas con atención
(nivel histórico) pasan de ~191–196 por día en nov-2026–ene-2027 a ~221–225 en abr–jun 2027 y vuelven a ~207 en oct-nov: ya no es una plantilla plana.

## Segunda ronda (12-nov, tarde): datos que faltaban, banda y SARIMAX (`src/estacionalidad_extra.py`)
**Datos agregados** (en `<datos>/externos/`, fuera del repositorio):
- **Calendario escolar** de los colegios oficiales de Barranquilla 2023–2026 (`calendario_escolar/calendario_escolar_barranquilla.csv`): inicio de
  clases, vacaciones de mitad de año, semana de receso de octubre y fin de clases, tomados de prensa que cita a la Secretaría de Educación (El Tiempo,
  Infobae, Portafolio y la Alcaldía; el sitio de la Alcaldía no permite leer las resoluciones de forma automática). En 2025 las fuentes no coinciden y se
  usó El Tiempo. Para 2027 en adelante, regla típica (clases desde el último lunes de enero, 3 semanas de mitad de año desde el lunes siguiente al 20 de
  junio, receso la semana del primer lunes de octubre, fin el primer domingo de diciembre).
- **Índice ONI de El Niño** (NOAA, `noaa_oni/oni.ascii.txt`, 1950 a oct-2026). En cada corte del backtest el ONI del futuro es el último valor conocido
  (persistencia, con 1 mes de retraso de publicación): no se usa el ONI observado del futuro.
- **IRA y EDA del Atlántico por semana: no hay una serie abierta.** El INS las publica en boletines PDF y en el portal SIVIGILA, sin descarga
  semanal por departamento; solo Bogotá tiene un canal endémico abierto. Queda pendiente: pedirla a la Secretaría de Salud del Atlántico.

**Resultados (llegadas con atención; error WAPE):**

| Variante | Validación 1–7 d | Validación 1–6 meses | Prueba 1–6 meses | Decisión |
|---|---|---|---|---|
| Dengue (modelo actual) | 8,7 % | 9,6 % | 10,6 % | se mantiene |
| + calendario escolar | 9,4 % | 10,1 % | 10,9 % | **se descarta** (empeora corto y largo plazo) |
| + ONI | 8,7 % | 9,5 % | 10,6 % | **se descarta** (efecto nulo; queda como hipótesis) |
| Sin dengue + calendario escolar | 9,2 % | 11,0 % | 10,6 % | se descarta (peor que el dengue) |

En los ingresos a cama ninguna variable mejora fuera del ruido. El calendario escolar empeora porque se solapa con los festivos y el fin de año, que el
modelo ya tiene, y las vacaciones de mitad de año caen justo cuando las llegadas son **más altas**, al contrario de lo que se esperaría si los niños
dejaran de consultar.

**SARIMAX (nivel 1 de la ficha; log de las llegadas con el mismo calendario como regresores y errores ARMA; cortes cada 28 días):**

| Modelo | Validación 1–7 d | Validación 1–6 meses | Prueba 1–7 d | Prueba 1–6 meses |
|---|---|---|---|---|
| Poisson actual (mismos cortes) | **7,3 %** | 9,7 % | **8,3 %** | **10,5 %** |
| SARIMAX (1,0,1) | 8,3 % | 8,9 % | 12,7 % | 13,0 % |
| SARIMAX (2,0,1) | 8,3 % | 8,9 % | 12,9 % | 13,0 % |

El SARIMAX mejora el largo plazo en la validación, pero **empeora a 1–7 días y es mucho peor en la prueba de 2026**, y su ajuste no converge en varios
cortes. Por la regla de la ficha **se queda el Poisson**. La autocorrelación que señala Ljung-Box ya la absorbe, en el modelo en uso, el ajuste de nivel con
los últimos 28 días.

**Banda del 80 % recalibrada (nivel 2 de la ficha, sin migrar a otro modelo).** Para cada tramo de horizonte se eligió el percentil (q, 1 − q) de
real/pronóstico más angosto que cubre al menos el 80 % en una validación (destinos de ene–jun 2025, factores con destinos anteriores); luego se midió en la
prueba (jul-2025 a 9-abr-2026), con factores de todos los destinos anteriores a jul-2025:

| Llegadas con atención | 1–7 d | 8–30 d | 1–3 meses | 3–6 meses | 6–12 meses |
|---|---|---|---|---|---|
| q elegido | 0,08 | 0,10 | 0,10 | 0,06 | 0,06 |
| Cobertura en la prueba, antes (q = 0,10) | 71 % | 79 % | 76 % | 72 % | 71 % |
| **Cobertura en la prueba, ahora** | **82 %** | **79 %** | **76 %** | **81 %** | **81 %** |

En los ingresos a cama (q = 0,10 salvo 0,07 a 8–30 días) la cobertura en la prueba queda en 78–88 %.

**¿Por qué no se migró la banda a un modelo estructural (nivel 2)?** La ficha pone una condición: migrar la banda a un modelo estructural (componentes no
observados o BSTS) **solo si**, después de mejorar la banda actual, la cobertura por tramo sigue mal calibrada. Tras la recalibración, la cobertura en la
prueba quedó en 76–82 % en llegadas y 78–88 % en ingresos, alrededor del 80 % buscado y sin un tramo claramente por debajo. Con eso se cumple el nivel 0/1
y la ficha indica quedarse ahí: cambiar de familia de modelo agregaría trabajo y riesgo sin una falla que corregir. Si con datos nuevos la cobertura de algún
tramo cayera por debajo de ~75 %, ese sería el momento de probarlo. Implementado en `NIVEL_BANDA`
(`src/modelo_pronostico.py`); el pronóstico a futuro y su gráfico se regeneraron.

## Cierre (12-nov): población del DANE y GAM (`src/estacionalidad_cierre.py`)
- **Población** (DANE, proyecciones municipales 2018–2042, versión de ago-2025, `<datos>/externos/dane_poblacion/`; área metropolitana: Barranquilla,
  Soledad, Malambo, Puerto Colombia y Galapa). Se aplicó como ajuste de tendencia (pronóstico × población del destino / población del corte). **No cambia
  nada** (llegadas: 9,61 → 9,61 % en validación a 1–6 meses; a 6–12 meses empeora una décima): el ajuste de nivel con los últimos 28 días ya recoge la
  tendencia. **Se descarta.**
- **GAM** (curva cíclica suave del día del año, spline cíclico con 4, 6 u 8 grados de libertad, dentro del mismo Poisson):
  - En **llegadas** es peor que el dengue (validación 9,9–10,2 % frente a 9,6 %; prueba 11,7–11,9 % frente a 10,6 %). Se queda el dengue.
  - En **ingresos a cama**, con 4 grados de libertad, baja la validación a 1–6 meses de 17,7 % a 17,3 % y la prueba de 19,9 % a 19,8 %, sin empeorar
    1–7 días (16,7 → 16,6 % en validación; 16,2 % igual en la prueba). **Se adopta**, con la advertencia de que la mejora es pequeña frente al ruido de conteo
    (~18 %). Con 8 grados mejora más la validación pero empeora la prueba a 1–7 días (16,2 → 17,2 %): se descarta por sobreajuste.
- **Implementado:** `ESTACIONALIDAD = {"llegadas_con_atencion": "dengue", "ingresos_a_cama": "gam"}` en `src/modelo_pronostico.py`; las bases del spline
  se fijan una vez sobre los días 1 a 366 para que no dependan del rango de fechas. `src/pronostico_demanda.py` suma las mismas columnas. Comprobado con el
  backtest del propio modelo (mismas cifras) y en el dashboard del equipo (`dashboard/main.py`, página de pronóstico: a 1 año el pronóstico sube desde abril
  y baja a fin de año; la nota de la página ya menciona la forma del año).

## Tercera ronda (12-nov, noche): IRA, EDA y demanda total de Barranquilla, y calendario escolar oficial (`src/estacionalidad_ira_eda.py`)
**Datos (públicos, fuera del repositorio, `<datos>/externos/sivigila/` con su README):** microdatos del SIVIGILA del INS (portal SIVIGILA, buscador de
microdatos, archivos `Datos_<año>_<evento>.xlsx`), eventos **995 (morbilidad por IRA)** y **998 (morbilidad por EDA)**, de notificación colectiva
(códigos verificados en el anexo de codificación SIVIGILA 2026), 2016–2025, agregados a casos por semana epidemiológica en Barranquilla (municipio de
notificación) y en el resto del Atlántico. La ficha de IRA trae además las consultas y hospitalizaciones por **todas las causas** de las mismas
instituciones. 2026 no está publicado. Calendario escolar: las resoluciones oficiales 06040/2022, 06182/2023, 07036/2024 y 07248/2025 (copias de
MinEducación); corrigen las fechas de prensa de 2025 (inicio 27-ene, fin 7-dic) y el fin del receso de octubre de 2026 (11-oct).

**Cómo:** igual que las rondas anteriores, pero **encima del modelo vigente** (dengue en llegadas, GAM en ingresos). Climatologías con la misma
construcción que el dengue, con los años **2016–2019** (antes de la pandemia y sin solaparse con la evaluación de 2023–2026). Rezago 0 o 2 semanas.

| Ingresos a cama (WAPE %) | Valid. 1–7 d | Valid. 1–6 m | Prueba 1–6 m | Backtest 183–365 d |
|---|---|---|---|---|
| Vigente (GAM) | 16,64 | 17,30 | 19,81 | 19,40 |
| + IRA consulta (misma semana) | 16,21 | 16,95 | 19,17 | 19,11 |
| + EDA (misma semana) | 16,49 | 16,96 | 19,70 | 19,14 |
| **+ IRA + EDA (adoptado)** | **16,30** | **16,87** | **19,32** | **19,04** |
| + calendario escolar oficial | 16,31 | 17,60 | 20,42 | 19,42 |

- **Ingresos a cama: entra IRA + EDA.** Mejora la validación a 1–6 meses (17,30 → 16,87 %) sin empeorar 1–7 días, y **se confirma en la prueba de
  2026, que no se usó para elegir** (19,81 → 19,32 %) y en todos los tramos del backtest. Las dos climatologías tienen el pico en la semana 24 (junio,
  temporada de lluvias) y el valle a fin de año, igual que la demanda de camas.
- **Llegadas con atención: no entra nada.** Todas las variables nuevas empeoran la validación encima del dengue (la mejor, hospitalizaciones por todas
  las causas 2 semanas antes, 9,61 → 9,65 %).
- **Calendario escolar oficial:** con las fechas corregidas sigue empeorando las dos series. Se confirma el descarte.
- **Banda:** la de ingresos sigue conservadora (cubre 85–92 % en la prueba); recalibrarla no ayuda (`src/calibrar_banda.py`).
- **Aviso de dengue a corto plazo con casos recientes:** no se puede usar todavía: los microdatos llegan a 2025 y el pronóstico parte de 2026.

## Cuarta ronda (12-nov, noche): lluvia del IDEAM, calendario universitario y contexto del sistema de salud
Son las tres fuentes de la ficha que faltaban. Ninguna cambia el modelo; quedan documentadas.

**1. Lluvia del IDEAM (`src/estacionalidad_ideam.py`).** Fuente: precipitación del IDEAM en datos.gov.co (conjunto `s54a-sgyg`), estación automática
0029004520 «Escuela Naval Barranquilla», lecturas cada 10 minutos sumadas por día (`<datos>/externos/ideam/`). Solo 2017–2020 están completos (la
estación tiene huecos grandes desde 2021 y 2024–2025 no se pudieron descargar: el servidor corta la consulta). Climatología con 2017–2020, igual que
la de NASA. Se parece a la de NASA (correlación 0,77; semana más lluviosa la 45, en noviembre). Encima del modelo vigente:

| | Valid. 1–7 d | Valid. 1–6 m | Prueba 1–6 m |
|---|---|---|---|
| Llegadas, vigente | 8,67 | 9,61 | 10,56 |
| Llegadas + lluvia IDEAM (4 sem. antes) | 8,66 | 9,59 | 11,16 |
| Ingresos, vigente | 16,30 | 16,87 | 19,32 |
| Ingresos + lluvia IDEAM (misma semana) | 16,20 | 16,80 | 19,43 |

Algunos rezagos pasan la regla por 0,01–0,07 puntos (ruido) y **empeoran la prueba de 2026** en las dos series: **se descarta**, igual que la de NASA.

**2. Calendario universitario.** No se pudo armar completo, así que **no se probó**:
- **Uninorte:** no publica el calendario académico en su sitio (la página de calendario da 404 y Registro Académico no lo enlaza); no hay notas de
  prensa con las fechas de cada semestre.
- **Uniatlántico** (resoluciones académicas oficiales): 2024-1 del 5-feb al 25-may-2024 (Res. 000037 de 2023); 2025-1 del 3-feb al 24-may-2025 y
  2025-2 programado del 4-ago al 22-nov (Res. 000022 del 15-oct-2024), corrido al 25-ago–13-dic (Res. 000018 de 2025); paro de 8 de 10 facultades
  desde el 30-oct-2025 y reinicio del 15-ene al 7-feb-2026 (Res. 000001 de 2026). Faltan 2023, 2024-2 y 2026-1 (solo hay modificaciones parciales
  de 2023). Con estos huecos y los paros, el calendario no sirve como variable; además el escolar, que es más regular, ya empeoraba el modelo.

**3. Contexto del sistema de salud (prensa y Supersalud; no entra al modelo, es para el documento).** Ninguno coincide con el 10-abr-2026, y la
auditoría (CLAUDE.md 4.9) ya mostró que el quiebre está en el registro de etapas, no en la demanda. Lo que pasó alrededor:
- **11-oct-2023:** entra en funcionamiento el Hospital Juan Domínguez Romero de Soledad (El Heraldo). El HUN también está en Soledad.
- **27-ene-2025:** abre el Nuevo Hospital de Barranquilla (122 camas de hospitalización y urgencias, 16 UCI); 2.300 atenciones de urgencias el primer mes (Consultor Salud).
- **19-ago-2025:** la Supersalud interviene la ESE Universitaria del Atlántico (red pública departamental) por 49 hallazgos críticos, entre
  ellos fallas en urgencias; prorrogada hasta ago-2027.
- **Abr-2026:** la Supersalud prorroga la intervención de Nueva EPS (Res. 2026100000003814-6). Desde el **22-abr-2026** la Clínica General del
  Norte (Barranquilla) suspende cirugías programadas por cartera de EPS (urgencias siguen); denuncias de que a afiliados de Nueva EPS solo se les
  atiende urgencia vital allí; clínicas con deudas de más de 90 días con sus médicos (El Heraldo, 30-abr-2026).
- **Lectura:** la crisis financiera de abril de 2026 podría haber llevado pacientes a otros hospitales (las visitas de urgencias del HUN suben ~40 %
  desde el 10-abr, CLAUDE.md 4.9), pero las fechas no calzan exactamente (10-abr frente a 22-abr) y no hay forma de comprobarlo con los datos.
  Queda como hipótesis, no como causa.

## Resumen de decisiones por variable
| Variable | Llegadas con atención | Ingresos a cama | Razón |
|---|---|---|---|
| Climatología de dengue (2 semanas antes) | **Entra** | No | Mejor en validación; describe la forma del año (signo negativo) |
| Curva cíclica (GAM, 4 g. l.) | No (peor que el dengue) | **Entra** | Mejora pequeña confirmada en la prueba |
| IRA + EDA (SIVIGILA, misma semana) | No (empeora) | **Entra** | Mejora validación y prueba en todos los tramos (tercera ronda) |
| Consultas / hospitalizaciones por todas las causas | No | No | Sin mejora clara |
| Fourier (1–3 armónicos) | No | No | Peor que dengue / empeora 1–7 días en la prueba |
| Lluvia NASA y lluvia IDEAM (0–8 semanas) | No | No | Sin mejora; la del IDEAM empeora la prueba de 2026 |
| Temperatura | No | No | Mejora menor que el dengue y no suma |
| Calendario escolar (oficial, resoluciones) | No | No | Empeora corto y largo plazo, también con las fechas oficiales |
| Calendario universitario | — | — | No se pudo armar: Uninorte no lo publica; Uniatlántico incompleto y con paros |
| Contexto del sistema de salud | — | — | No es una serie; documentado como contexto del quiebre de abril-2026 |
| El Niño (ONI, persistencia) | No | No | Efecto nulo |
| Población DANE | No | No | Efecto nulo |
| SARIMAX | No | — | Peor a 1–7 días y en la prueba de 2026 |
| Banda recalibrada por horizonte | **Sí** | **Sí** | Cobertura en la prueba 76–82 % (llegadas) y 78–88 % (ingresos) |

## Qué datos faltan todavía
- **2026 por semana** (dengue, IRA, EDA): el INS aún no publica los microdatos; solo hay acumulados preliminares en el boletín semanal.
- **Calendario de Uninorte** y los periodos 2023, 2024-2 y 2026-1 de Uniatlántico: habría que pedirlos a cada universidad.
- **Lluvia IDEAM 2021–2025** de la estación de Barranquilla: con huecos o sin descargar (el servidor de datos.gov.co corta la consulta).

## Qué cambió en el código
`src/modelo_pronostico.py` (12-nov): **`regresor_estacional(idx, clim, lag_sem)`**, el generador que pide la ficha: lleva cualquier fecha (pasada o futura, incluido 2027) a su semana ISO, aplica el rezago y devuelve el valor de la climatología (una lista de 53 valores o un CSV con columnas `semana` y `valor`); `CLIMA_DENGUE`, `CLIMA_IRA` y `CLIMA_EDA` (53 números públicos cada una), `REZAGO_DENGUE_SEMANAS = 2` y `ESTACIONALIDAD` por objetivo (dengue en
`llegadas_con_atencion`; GAM + IRA + EDA en `ingresos_a_cama`). `columnas_estacionales(idx, objetivo)` arma esas columnas y la usan `calendario()` y
`pronostico_demanda.diseno()`, así las dos matrices quedan sincronizadas. `calendario(idx, objetivo)` suma la columna `estacional_dengue` cuando corresponde; `retroceso()` y `pronostico_con_banda()` le
pasan el nombre de la serie. Sin `objetivo`, `calendario()` se comporta igual que antes, así que los demás scripts (pruebas, Monte Carlo) no cambian.
El pronóstico del dashboard (página `/`) la usa automáticamente para «ingresos al hospital». `src/pronostico_demanda.py` suma la misma columna, en el
mismo orden, para las series que la tengan activa (la ficha pide los dos scripts sincronizados). `modelo_pronostico.py` y `pronostico_futuro.py` leen y
escriben fuera del proyecto si existen `HUN_PROCESADOS` y `HUN_TABLAS`.

## Límites
Solo ~3 ciclos anuales en el hospital; se asume Barranquilla; climatologías y no pronósticos de dengue o lluvia; la prueba de 2026 es corta por el
quiebre de registro del 10-abr-2026; asociación, no causa.
