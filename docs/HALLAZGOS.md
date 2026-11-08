# Hallazgos del proyecto (versión autocontenida, 23-oct-2026)

Este documento resume **todo lo que se averiguó**, con las cifras y la fuente de cada una. Está escrito para que una persona, o un
Claude que abra este repositorio sin acceso a los datos, pueda contestar preguntas sin inventar nada. Detalle técnico completo:
`CLAUDE.md`. Plan y fases: `docs/plan_de_accion.md`. Recomendaciones: `docs/recomendaciones.md`. Días atípicos: `docs/dias_atipicos.md`.

**Regla de oro al contestar:** si una cifra no está en este documento o en `CLAUDE.md`, no la afirmes; di que no está registrada y
señala qué script o consulta la produciría. Distingue siempre *asociación* de *causa*, y di la limitación junto a cada hallazgo.

---

## 0. Resumen en 12 líneas

> **Actualización del 1-nov-2026 (regla de estancia única v3.8):** se detectaron 2.179 estancias duplicadas más (ver `CLAUDE.md` 4.8). Todas las cifras de espera de cama, ingresos, camas y ocupación de este documento se recalcularon: ocupación media de 94 camas (2023) a 105 (2025), ~20 ingresos por día y espera de cama mediana de 18,6 h. Las que no cambian (calendario, pronóstico de llegadas, diagnósticos de A3) se marcan con su fecha. Respaldo de las cifras anteriores: `resultados/respaldo_dedup_v37/`.


1. **El reto** (Hospital Universidad del Norte, HUN + Ciencia de Datos Uninorte): entender, predecir y optimizar el flujo de pacientes
   del hospital, hallando cuellos de botella y proponiendo acciones. Entregables: documentación, repositorio y dashboard de Power BI.
2. **Los datos** (2023-01 a 2026-06, esquema OMOP) traen problemas serios que hubo que resolver: ~30 % de visitas copiadas, 41 % de
   las estancias en cama duplicadas entre dos personas, 36–42 % de las etapas de urgencias sin hora de salida.
3. **Cuello de botella (definición del proyecto):** un segmento donde el paciente espera un recurso, con exceso sobre una referencia
   de "cuando funciona bien", impacto alto (volumen × retraso) y que se agrava con la carga.
4. **El principal cuello de botella es la espera de cama:** mediana de **18,6 h** y percentil 90 de **73,9 h** desde que llega el
   paciente hasta que entra a cama. El 80 % de esas horas es tiempo en urgencias y el 21 % es tiempo sin ninguna etapa registrada.
5. **Los peores casos empeoran:** la espera mediana casi no cambia (17–19 h) pero el percentil 90 sube de 61 h (2023) a 80 h (2026).
6. **Las altas son tardías:** el 62,7 % de las altas ocurre entre las 14:00 y las 18:59 y solo el 14 % antes del mediodía; las camas
   se asignan a las 17–18 h. Quien llega a media tarde espera más (mediana de ~25 h frente a 12–15 h de madrugada).
7. **Adelantar altas ayuda poco:** pasar el 30 % de las altas de la tarde a la mañana libera hasta 5,1 camas a las 12 h, pero evita
   como máximo ~8 % del exceso de espera (estimación central ~3 %). El 83 % de las horas de espera viene de esperas de más de 24 h.
8. **La ocupación sube por la estancia (sobre todo las de más de 30 días: 6 a 13 camas entre 2023 y 2025), no por la demanda:** camas ocupadas de 94 (2023) a 105 (2025); estancia media de 4,57 a
   5,31 días (+16 %); ingresos estables en ~20 por día.
9. **La carga del momento explica poco:** cada decil más de llegadas sube la espera ~2,5 %; la ocupación y el día de la semana casi
   no importan. Todos los factores observables juntos explican solo el 16 % de la variación de la espera.
10. **Se puede pronosticar la demanda:** llegadas por día con error de **7,5 %** a 1 día (mejora a las referencias simples);
    los ingresos diarios no (es ruido de conteo), pero por semana el error baja a **9,5 %**.
11. **Alertas probadas sobre días pasados:** la de "día congestionado" a las 12 h detecta 83 % de esos días (precisión 54 %); una alerta
    por paciente a las 48 h sin cama genera ~4 avisos por día. Carga total recomendada: ~5 alertas por día.
12. **Desde el 10 de abril de 2026 el registro de las etapas se degrada** (auditoría directa en la base, `CLAUDE.md` 4.9): las visitas de urgencias no bajaron en mayo (+2 % frente a mayo de 2025) mientras las etapas ER bajaron 64 %; más visitas sin etapas, menos visitas con etapa de llegada, diagnósticos sin código desde el 11-may. Esos días no se usan para estimar nivel ni evaluar. El número de camas del hospital no se conoce, así que la capacidad se trabaja con escenarios.

---

## 1. Glosario

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

## 2. La base de datos y sus problemas (qué se hizo)

Esquema `uninorte_omop`, solo lectura, detrás de VPN. Tablas grandes: `measurement` 16,6 M filas, `procedure_occurrence` 47 M,
`condition_occurrence` 38,6 M, `visit_detail` 3,28 M, `visit_occurrence` 1,7 M, `person` 912 mil (304 mil con visitas).

| Problema | Cifra | Qué se hizo |
|---|---|---|
| Visitas copia de la misma persona | ~238 mil visitas | Se borran y sus etapas pasan a la visita original |
| Visitas replicadas entre dos personas | ~280 mil visitas | Se conservan; se quitan solo las etapas idénticas (episodios con todas sus etapas repetidas) |
| **Estancias en cama gemelas** (misma estancia en dos personas) | **53 % de los episodios hospitalizados** (18.786 de 35.343) | Se cuenta cada estancia una vez (25.777 únicas; regla v3.8, ver `CLAUDE.md` 4.8). Evidencia: `person_id` difiere en ≤ 2 en el 78 % de los pares (azar: 0,005 %) |
| Etapas TU sin hora de salida (inicio = fin) | 36–42 % de las etapas TU, estable por año | Se marcan "sin duración", no como 0 h; la duración de urgencias de quien se va de alta se trata solo como descriptiva |
| Etapas abiertas (fin con milisegundos) | 2.053 | Se descartan: son pacientes aún hospitalizados al extraer |
| `visit_end_datetime = visit_start_datetime` | 100 % | La duración sale de las etapas, no de la visita |
| `visit_concept_id` poco confiable | — | No se usa el tipo de visita para saber por dónde pasó el paciente |
| Diagnósticos tardíos, en SNOMED y sin jerarquía | 88 % se registra después de las 2 primeras horas | Solo sirven para explicar, no para predecir "al llegar" |
| **Registro de etapas degradado desde el 10-abr-2026** | Etapas ER −64 % en mayo; visitas de urgencias +2 %; visitas sin ninguna etapa de 10 % a 22 % | El periodo confiable termina el 9-abr-2026; después no se usa para estimar nivel ni evaluar |

**Resultado de la limpieza:** 337.194 episodios; ~10 % de los episodios con atención terminan hospitalizados (~27,9 mil estancias únicas
de ~274 mil episodios que no son solo-ER); 62.927 episodios son solo-ER sin nada clínico.

**Verificación contra la base real (22-oct):** una versión resumida de la consulta central (Q3b) dio exactamente los mismos 23
controles sobre la base y sobre los CSV exportados; Q1 y Q2 también coincidieron fila por fila.

---

## 3. Componente 1: cómo fluye el paciente

- **Llegadas:** ~265 por día (282 en 2023, 263 en 2024, 260 en 2025, 244 en ene–abr 2026). Pico entre las 9 y las 11 h (~19 por hora),
  mínimo de 3 a 4 h. Lunes el día más cargado (302 de promedio) y domingo el más tranquilo (202); el fin de semana ~30 % menos.
- **Etapas, con duración conocida:** ER mediana de 3,6 min. TU mediana de 3,3 h (percentil 90 de 17–24 h), y el 36–42 % de las etapas TU
  no tiene hora de salida. HOSP: mediana de 46–47 h por etapa.
- **Estancia en cama (episodio):** mediana 71 h, percentil 75 de 144 h, percentil 90 de 280 h, media 5,2 días.
- **Urgencias sin hospitalizar (solo el 38 % tiene duración):** mediana 9,6 h, percentil 90 de 45 h. Está sesgada: los niños (30 % medidos) y las
  visitas ambulatorias (10 %) están subrepresentados frente a adultos mayores de 65 (48 %).
- **Entre etapas casi no hay tiempo muerto:** ER>TU 99 % pegadas; HOSP>HOSP 99 %; TU>TU 94 %. La excepción es TU>HOSP: 23,8 % de los
  hospitalizados tiene más de 1 h sin ninguna etapa antes de la cama (mediana de 19,7 h entre los que tienen hueco).
- **Hospitalizados:** ~20 ingresos a cama por día.

---

## 4. Componente 2: cuellos de botella

### 4.1 Definición y método
Un segmento es cuello de botella si (1) es una **espera**, no atención clínica; (2) tiene **exceso** sobre una referencia interna del
hospital; (3) tiene **impacto alto** (volumen × retraso); y (4) **se agrava con la carga**. Referencias probadas: mediana con carga baja
(llegadas de 6 h en el 20 % más bajo), percentil 25 y percentil 10. El orden de los resultados no cambia con la referencia ni con el corte
de episodios (72, 168 o 336 h). La meta de tiempos del HUN no se conoce.
Candidatos: espera de cama, urgencias antes de la cama, hueco antes de la cama. La estancia en cama es servicio clínico (va a la
simulación de camas). Fuente: `src/construir_segmentos.py`, `src/ranking_cuellos.py`.

### 4.2 Resultados (estancias únicas)
| Segmento | n | p25 | mediana | p75 | p90 |
|---|---|---|---|---|---|
| **Espera de cama** | 25.373 | 6,6 h | **18,6 h** | 37,9 h | **73,9 h** |
| Urgencias antes de la cama | 25.373 | 3,4 | 11,1 | 29,5 | 55,9 |
| Hueco antes de la cama (solo si > 0) | 6.585 | 7,1 | 19,7 | 39,1 | 70,9 |
| Estancia en cama | 25.777 | 40,0 | 70,7 | 143,9 | 280,3 |

- El 43,7 % espera más de 24 h y el 19 % más de 48 h.
- Urgencias antes de la cama concentra el **80 %** de las horas de espera; el hueco, el 21 %. Lidera con las 4 referencias.
- Con la referencia de carga baja (mediana de 14,7 h), el **64 %** de las horas de espera de cama (518 mil de 812 mil horas-paciente) es exceso.

### 4.3 Tendencia: empeoran los peores casos
| Año | Mediana | Percentil 75 | Percentil 90 | Exceso medio por episodio |
|---|---|---|---|---|
| 2023 | 19,5 h | 35,8 | 61,6 | 17,3 h |
| 2024 | 18,3 | 36,5 | 69,7 | 18,6 |
| 2025 | 17,4 | 40,8 | 80,2 | 23,8 |
| 2026 (ene–abr) | 19,8 | 46,2 | 81,9 | 23,8 |
Desde el 10-abr-2026 el registro está degradado (ver 4.9 de `CLAUDE.md`): lo que muestra la espera en esos meses no es confiable.

### 4.4 Carga, hora y altas tardías
- **Carga:** la mediana de espera va de 14,2 h (decil con menos llegadas en 6 h) a 25,9 h (decil con más); con controles, +2,5 % por decil. La
  ocupación pesa poco (+1,1 % por decil) y las llegadas de 24 h casi nada.
- **Hora de llegada:** mediana de 12–15 h de madrugada y ~25 h al llegar entre las 13 y las 16 h (hay un salto a las 13:00). La carga
  explica unos dos quintos del efecto de la tarde; el resto no.
- **Altas tardías (se sostiene, 4 de 4 criterios):** el 62,7 % de las altas es de 14:00 a 18:59 y solo el 14 % antes del mediodía (13–16 %
  cada año); la cama se asigna con mediana a las 17–18 h sin importar la hora de llegada. Quien llega a las 8 h recibe cama al día siguiente en
  el 50 %; a las 16 h, en el 72 %. Los ingresos a cama siguen a las altas en la misma hora (correlación cruzada 0,17). A nivel *diario* la
  relación no aparece: el mecanismo es dentro del día.
- **El orden de llegada casi no predice el orden de cama** (53 % de pares consecutivos en orden; el azar sería 50 %).

### 4.5 Qué explica la espera (modelo sobre log(espera + 1), R² = 15,8 %; recalculado el 3-nov con la regla de la persona real, CLAUDE.md 4.10)
Pérdida de R² al quitar cada factor: diagnóstico 7,0 puntos (ojo: es en parte un dato administrativo; antes 3,9 con solo 38 % de cobertura), edad y sexo 4,1, tipo de visita 1,6 (por urgencias se
espera más: ambulatorio −31 %, treatment urgency −39 %), hora de llegada 0,7, año 0,1, carga 0,1, laboratorios de 6 h 0,1,
calendario ~0. **El 86 % de la variación no se explica con lo que se observa.** Un modelo "al llegar" para predecir si un paciente esperará
más de 24 h tiene AUC de 0,60: no sirve para alertar a un paciente individual.

### 4.5b Espera y estancia por grupo de diagnóstico (`docs/diagnosticos_y_tiempos.md`)
Dentro de los hospitalizados con diagnóstico traducido (61 %, después de quedarse con el registro más completo de cada estancia gemela, 29-oct), esperan cama ~9–13 h cardiovascular, neurológico y respiratorio y 29–39 h musculoesquelético, renal, cáncer y digestivo; el patrón sigue tras controlar tipo de visita, hora, año y edad (cardiovascular −68 %, IC 95 % −70 a −66, frente a digestivo; mapeo revisado a mano el 3-nov, `docs/revision_mapeo_dx.md`) y es estable por año. **Advertencia:** el diagnóstico puede ser de la otra persona del par duplicado y falta en el 39 % de los hospitalizados; antes del cambio el sesgo era fuerte (60 % con diagnóstico si esperaba ≤ 6 h y 27 % si esperaba > 24 h), ahora es de 56–69 % en todos los tramos. No es causa. Hipótesis sin comprobar: la espera larga se concentra en cirugía, urología y ortopedia (sin dato de servicio).

### 4.6 Ocupación, estancia y escenario de altas
*Aclaración: lo que aquí se llama "simulación" (`src/simulacion_altas.py`) es un **análisis de escenarios sobre datos históricos** con cotas, no una simulación
estocástica de pacientes llegando. La simulación Monte Carlo de camas (ficha 3.1) está pendiente.*
| | 2023 | 2024 | 2025 |
|---|---|---|---|
| Ingresos por día | 20,6 | 20,8 | 19,8 |
| Estancia media (días) | 4,57 | 4,90 | 5,31 |
| Camas ocupadas | 94 | 101 | 105 |
- Con la ley de Little (camas = ingresos × estancia): volver a la estancia de 2023 liberaría ~15 camas; bajarla 5 %, ~5; subir los ingresos 10 %
  añadiría ~10.
- **Escenario "30 % de las altas de la tarde antes del mediodía"** (`src/simulacion_altas.py`): hasta 5,1 camas libres adicionales a las 12 h
  (~34 horas-cama por día). Traducido a espera: **como máximo ~8 % del exceso** (455 horas-paciente por día), estimación ~3 %. Con el 100 %:
  máximo 27 %. Supuestos: el alta de los demás no cambia; es una cota, no una predicción. **Nota sobre la capacidad:** el HUN reportó 106 camas de hospitalización; la ocupación media fue 94 (2023), 101 (2024) y 105 (2025), y en 2025 superó las 106 camas el 42 % de las horas (en 2023, el 2 %). El exceso viene de estancias largas con actividad diaria de hospitalización (las de más de 30 días pasaron de 6 a 13 camas). Puede ser sobreocupación con camas adicionales o una capacidad real mayor; los datos no lo distinguen (`CLAUDE.md` 4.8).
- El **83 % de las horas de espera** viene de esperas de más de 24 h y el 57 % de esperas de más de 48 h (el 19 % de los pacientes).

### 4.7 Días atípicos (`docs/dias_atipicos.md`)
Con |z| > 3 frente al pronóstico: 14 días de llegadas, 9 de ingresos y 7 de espera (por azar se esperarían ~3 por serie). Casi todos son de
menos actividad. Los dos más extremos (sábados 28-mar-2026 y 15-jun-2024: 88 y 111 llegadas con 1 y 8 ingresos a cama) parecen cortes de
registro o de sistema (hipótesis). **Ningún día tuvo la espera más alta de lo esperado: el problema es crónico y de cola larga, no de días puntuales.**

---

## 5. Componente 3: modelos y alertas

### 5.1 Pronóstico de demanda (`src/pronostico_demanda.py` v1.3)
Entrenado hasta 2025-12, probado en ene–abr 2026, método elegido con la validación de 2025-07 a 2025-12.
- **Llegadas por día:** regresión de Poisson con día de la semana, festivos, semana santa, fin de año (24 y 31 de diciembre bajan ~37 %), Carnaval,
  nivel de los últimos 28 días y la "sorpresa" del último día conocido. Error **7,5 % a 1 día** y 8,8 % a 7 días, contra 9,9 % y 10,5 % de la mejor
  referencia. Por hora: 26,5 % frente a 28,8 %.
- **Carnaval de Barranquilla:** los días de carnaval (sábado a martes) tienen ~17 % menos visitas que el mismo día de la semana en las semanas vecinas
  (sábados −24 %, lunes −28 %, domingos −6 %, martes −8 %, consulta Q5). Se asume que el HUN está en Barranquilla.
- **Ingresos a cama:** ningún método mejora a "día de la semana × nivel reciente" a nivel diario (error ~23 %: la varianza es igual a la media,
  ruido de conteo). **Por semana el error baja a 9,5 %** (frente a 14,7 % de repetir la semana anterior).
- Limitaciones: las bandas de ingresos cubren ~71 % (angostas); desde el 10-abr-2026 el registro está degradado y el modelo (que se entrena hasta el 9-abr) no lo anticipa; tampoco anticipa brotes ni cortes de sistema.

### 5.2 Alertas (`src/alertas.py`, reproduciendo ene–abr 2026; cortes elegidos con la validación de 2025)
| Alerta | Resultado |
|---|---|
| **A. Día congestionado a las 12 h** (llegadas > percentil 90 del mismo día de la semana) | AUC 0,94; 28 alertas (0,23/día), 15 aciertos: precisión 54 %, detección 83 %. A las 15 h: 73 % y 61 %. **Un día antes:** AUC 0,61 (precisión 43 %, detección 17 %): avisa a media jornada, no con un día de margen |
| **B. Camas a 24 h** | La proyección (camas − altas esperadas + ingresos esperados) **no mejora a la persistencia** ("lo mismo que ahora"): error 4,3 contra 3,5 camas. Las altas esperadas tienen sesgo de +2,6 camas. Alerta de ocupación alta (≥ 123 camas): AUC 0,92, precisión 75 %, detección 90 %, 0,5 por día |
| **C. Paciente sin cama** (solo los que luego se hospitalizan) | A las 24 h: 9,1 alertas/día, 23 % termina esperando > 72 h. **A las 48 h: 4,1/día, 51 %, 24 h de margen.** A las 60 h: 2,7/día, 79 %, 12 h de margen |
Carga total recomendada (A a las 12 h, B persistencia, C a las 48 h): **~4,9 alertas por día**. Solo hay 18 días congestionados en la prueba: las cifras se mueven.

### 5.3 Lo que se probó y no funcionó
Fila de espera tipo "primero en llegar, primero en cama" (no respaldada por los datos); predecir la estancia de cada paciente (R² ≈ 0);
pronóstico diario de ingresos con modelos más finos; proyección de camas a 24 h con altas esperadas; nivel con mediana de 28 días;
deduplicar las llegadas, separar por edad o tipo de visita, puentes festivos y quincena (sin mejora). *No probado:* ingresos como fracción
de las llegadas pronosticadas; factores externos (clima, dengue, eventos).

---

### 5.4 Estimación de la espera de cada paciente (A6, `docs/estimador_tiempos.md`)
- **La espera es individual:** los pacientes que llegan el mismo día no esperan parecido (el día explica un 0,1 % más allá del azar). La ocupación y la cola casi no ayudan.
- **Estimador: modelo de tiempo restante** (`src/estimador_tiempo_restante.py`). Da el rango de lo que le falta a un paciente que espera cama y la probabilidad de recibirla en 6, 12 y 24 h. Usa el paciente, la hora del reloj, la ocupación, su historial (la espera se repite: Spearman 0,34 con la hospitalización anterior) y su recorrido en urgencias, con un modelo por momento de la espera.
- **Prueba** (entrenamiento feb-2023 a jun-2025, prueba jul-2025 a 9-abr-2026, 5.430 estancias): mejora 7,6 % al llegar (IC 95 % 6,7 a 8,5) y 9,2–9,5 % a las 3–6 h frente a dar el mismo rango a todos; los percentiles aciertan (26,3 / 51,4 / 73,8 / 87,7 % debajo de p25 / p50 / p75 / p90). Le gana con margen comprobado a la tabla de perfiles, a un modelo de cuantiles y a dos modelos de cola. Agosto y septiembre de 2025 (sobredemanda, dato del equipo) dan el mismo resultado.
- **Gravedad y servicio (procedimientos de cada estancia, sin fecha):** el hospital da cama rápido a los graves (UCI: mediana 2,7 h) y hace esperar más a urología (37,7 h), ortopedia (32,8 h) y cirugía general (29,6 h). Si al llegar se supieran la gravedad y el servicio, la mejora pasaría de 7,6 % a 15,8 % (18,6 % sumando el diagnóstico; escenario optimista). **Registrar el triage y el servicio** es la mejora de datos que más ayudaría.
- **La hora del reloj manda:** el 24 % de las camas se asigna entre las 15 y las 17 h y el 37 % entre las 20 y las 23 h; entre las 6 y las 12 h casi nadie recibe cama.
- **El hospital cambió** (p90 de la espera de 61 a 81 h entre 2023 y 2026): reentrenar cada mes con más peso en lo reciente mejora la estimación en todos los momentos (8,1 % al llegar, 10,3 % a las 3 h; la diferencia con el modelo fijo es real hasta las 6 h). El estimador final se entrena así (`src/ventana_entrenamiento.py`).

---

## 6. Componente 4: recomendaciones (`docs/recomendaciones.md`, borrador)
1. Registrar mejor: hora de salida de urgencias, asignación de cama y sin duplicados (habilita medir todo lo demás).
2. Seguimiento mensual de 6 indicadores (espera p50/p90 de 18/73,9 h, % con más de 48 h sin cama 19 %, % de altas antes del mediodía 15 %, hora de
   asignación de cama 17–18 h, camas ocupadas a las 12 h ~103, estancia media 5,31 días).
3. Reunión diaria de camas a media mañana apoyada en las alertas.
4. Meta de altas antes del mediodía (empezar con 25–30 %): hasta 5,1 camas libres, como máximo 8 % del exceso de espera.
5. Alerta por paciente a las 48 h sin cama, con un responsable (~4 por día).
6. Protocolo para quien llega entre las 13 y las 18 h y se hospitaliza (entre ~11 y ~49 horas-paciente por día, ver `src/impacto_llegada_tarde.py`; confianza baja).
7. Revisión semanal de estancias largas (−5 % de estancia ≈ 5 camas).
**Los datos no respaldan:** "hacen falta más camas" (la ocupación ya supera las 106 camas reportadas el 42 % de las horas de 2025, pero no se sabe si es sobreocupación o mayor capacidad real), más personal según el día de la semana, ni priorizar pacientes
concretos por riesgo de esperar. La literatura externa sobre altas antes del mediodía es **mixta** (un programa reportó 0,30 días menos de estancia;
otro hospital no halló efecto); las fuentes se leyeron solo en resumen y hay que verificarlas.

---

## 7. Lo que no sabemos (limitaciones y pendientes)
- **Número de camas** del hospital y **meta de tiempos**: desconocidos. El correo con las preguntas se envió al HUN y no tuvo respuesta; el HUN abrirá una sesión de preguntas (`docs/hun/sesion_de_preguntas.md`).
- **Por qué se degrada el registro de etapas desde el 10-abr-2026:** cambio de sistema o de extracción; la auditoría descarta que sea menos demanda (las visitas no bajaron).
- **Cuál de las dos personas es la real** en las estancias gemelas.
- **La espera en urgencias mezcla atención y espera de cama**; no se pueden separar con los datos.
- Las **llegadas** incluyen ≥ 4 % de réplicas (sin deduplicar a propósito); la ocupación de urgencias (`ocup_tu`) y la cobertura por ruta cuentan todos los episodios.
- Todo son **asociaciones y escenarios**, no causas probadas.
- **El reparto de lo que falta, con responsable y entrega, está en `docs/pendientes_y_reparto.md`.** Pendiente de ensamblaje: documento final, dashboard de Power BI (Samuel), simulación Monte Carlo de camas y modelo explicativo (Anthony), perfiles de pacientes y factores de la estancia (Daniela),
  `mapeo_dx.csv` (grupos de diagnóstico), sesión de preguntas con el HUN y una simulación estocástica (Monte Carlo) de la ocupación de camas.

---

## 8. Preguntas frecuentes (con respuesta y dónde verificarla)

| Pregunta | Respuesta corta | Dónde |
|---|---|---|
| ¿Cuánto espera un paciente por cama? | Mediana 18,6 h, percentil 90 73,9 h; el 44 % más de 24 h | 4.2; `src/construir_segmentos.py` |
| ¿Dónde está el cuello de botella? | En la espera de cama, sobre todo en urgencias antes de la cama (77 % de las horas) | 4.1–4.2 |
| ¿Está empeorando? | Sí, los peores casos: percentil 90 de 61 h (2023) a 80 h (2026); la mediana no | 4.3 |
| ¿Faltan camas? | No se puede afirmar: la ocupación (99 % de las 106 camas reportadas en 2025, 42 % de las horas por encima) subió por las estancias largas (+16 % de estancia media), no por la demanda; sobreocupación o capacidad mayor, sin dato para distinguirlo | 4.6; `CLAUDE.md` 4.8 |
| ¿Adelantar altas resuelve? | Ayuda poco: como máximo ~8 % del exceso | 4.6; `src/simulacion_altas.py` |
| ¿Se puede predecir la demanda? | Llegadas sí (7,5 % de error); ingresos diarios no, por semana 9,5 % | 5.1 |
| ¿Qué alertas se proponen? | Día congestionado a las 12 h; ocupación alta; paciente a las 48 h sin cama | 5.2 |
| ¿Por qué se quitaron datos como "duplicados"? | 41 % de las estancias estaban en dos personas | 2 |
| ¿Se puede reproducir sin la base? | No: hay 8 CSV exportados de la base que no están en git y no se pueden regenerar. Con ellos todo se regenera en menos de un minuto (probado en un clon limpio) | `README.md` |
| ¿Qué dijo el HUN? | Nada por correo; habrá una sesión de preguntas (preguntas listas en `docs/hun/sesion_de_preguntas.md`) | 7 |

---

## 9. Mapa de archivos (script → qué produce)

| Script | Qué hace | Salida principal |
|---|---|---|
| `src/analisis_etapas.py` (v3.7) | Limpia etapas y copias, arma episodios, marca estancias gemelas, espera de cama | `episodios.csv`, `bloques.csv`, `espera_cama.csv` |
| `src/generar_borrador_mapeo_dx.py` → `src/diagnosticos_y_tiempos.py` | Agrupa diagnósticos y compara tiempos por grupo | `datos/referencia/mapeo_dx.csv`, `tiempos_por_dx.csv`, `efecto_dx_espera.csv` |
| `src/preparar_variables.py` (v2.1) | Agrega calendario, paciente, diagnóstico, ocupación, series | `tabla_episodios.parquet`, `serie_horaria.csv`, `serie_diaria.csv` |
| `src/comparar_estimadores.py` → `src/estimador_tiempo_restante.py` | A6: construye y prueba el estimador de la espera (historial, recorrido, un modelo por momento) contra las alternativas, y deja la función de consulta | `comparacion_estimadores_ic.csv`, `comparacion_estimadores.png` |
| `src/estimador_tiempos.py`, `src/espera_dos_series.py`, `src/triage_aproximado.py` | A6: tabla de perfiles, espera en dos series y escenario de gravedad | `estimador_tiempos.csv`, `espera_dos_series_*.csv`, `triage_aproximado.csv` |
| `src/exportar_para_equipo.py` (v2) | Tablas para el equipo y Power BI | `estancias_hospitalizacion.csv`, `panel_diario.csv` |
| `src/generar_q3_q4_desde_csv.py` | Reproduce Q3 y Q4 sobre los CSV con DuckDB | `q3_episodios.csv`, `q4_ocupacion_por_hora.csv` |
| `src/construir_segmentos.py` | Segmentos, inventario, sesgo de medición | `segmentos.csv` |
| `src/ranking_cuellos.py` | Referencias, exceso, ranking | `ranking_cuellos.csv`, gráfico |
| `src/dependencia_carga.py` | Espera frente a carga y hora | `carga_por_decil.csv` |
| `src/altas_y_factores.py` | Altas tardías y factores | `importancia_factores.csv` |
| `src/simulacion_altas.py` | Ocupación y escenario de altas | `escenario_altas_antes.csv` |
| `src/pronostico_demanda.py` (v1.3) | Pronóstico de demanda | `pronostico_metricas.csv` |
| `src/alertas.py` | Alertas A, B y C | `alertas_*.csv` |
| `src/dias_atipicos.py` | Días atípicos | `dias_atipicos.csv` |
| `sql/exportaciones_base.sql`, `sql/consultas_semana1.sql` | Exportan de la base los 8 CSV de entrada | `datos/crudos/*.csv` |
| `sql/consultas_cuellos_botella.sql` | Q0 a Q5 y Q3b | — |

**Gráficos (en `resultados/graficos/`, sí están en git):** `ranking_cuellos.png` (impacto por segmento y tendencia), `dependencia_carga.png`
(espera frente a carga y hora), `altas_y_factores.png` (altas por hora y factores), `simulacion_altas.png` (camas y escenario),
`pronostico_demanda.png`, `alertas.png`, `dias_atipicos.png`, y los del pipeline (`serie_diaria.png`, `mapa_calor_llegadas.png`,
`boxplot_rutas.png`, `cobertura_por_ruta.png`, `espera_vs_ocupacion.png`, `altas_ingresos_por_hora.png`).
