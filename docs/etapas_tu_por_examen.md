# Las etapas TU según el tipo de examen que se pide (10-nov-2026)

Script: `src/etapas_tu_por_examen.py`. Tablas (fuera de git): `etapas_examen_*.csv`. Continuación de `docs/caracterizacion_etapas_tu.md`.
**Pregunta de Daniela:** etiquetar cada etapa TU por qué tipo de examen trae, y ver cuáles se alargan.

## Qué se pudo y qué no
| Dato | ¿Tiene fecha y hora? | ¿Se pudo asignar a una etapa TU? |
|---|---|---|
| **Laboratorio** (`measurement`) | Sí, el 100 % de las filas (`measurement_datetime`); en la ventana de espera, ~70 % de las estancias tiene alguna toma | **Sí**, por su hora dentro del intervalo de la etapa. El 42 % de las filas viene con concepto traducido; el 58 % no (concepto 0): de esas solo se sabe que hubo una toma |
| **Diagnóstico** (`condition_occurrence`) | Sí, el 100 % de las filas (`condition_start_datetime`), pero es la fecha de registro: casi siempre al llegar y justo antes de la cama | **Sí**, por la hora de su primer registro: 53 % cae en la primera etapa, 32 % en la «única», 10 % en la última |
| **Procedimiento** | **No**: 0 % de las filas (`procedure_date` vacía en toda la tabla) | **No**; solo indirectamente (`docs/procedimientos_y_laboratorios.md`) |

**¿Qué porcentaje tiene fecha y hora?** (medido directo en la base el 10-nov, `sql/fechas_y_nombres.sql`):

| Tabla | Filas | Con fecha y hora | Fechas fuera de rango | Concepto 0 (sin traducir) | Conceptos distintos |
|---|---|---|---|---|---|
| Laboratorios (`measurement_datetime`) | 16.575.888 | **100 %** (0 filas sin fecha) | 0 | 53,5 % (8.876.114) | 72 |
| Diagnósticos (`condition_start_datetime`) | 38.636.063 | **100 %** (0 sin fecha) | 80 filas (fechas hasta 2033) | 37,8 % (14.605.421) | 4.145 |
| Procedimientos (`procedure_date`) | 47.042.032 | **0 %** (las 47.042.032 filas sin fecha) | — | 0 % | 158 |

- **Laboratorios:** todos tienen fecha y hora válidas (de 2023-01-01 a 2026-07-17); además el 94,8 % cae dentro de la visita (auditoría). El problema no es la fecha sino que **el 53,5 % no tiene concepto** (no se sabe qué examen es).
- **Diagnósticos:** todos tienen fecha, pero es la de **registro**, no la de cuando se supo: se anota casi siempre al llegar y justo antes de la cama. Por eso sirven para ubicarlos en una etapa, pero no para medir actividad clínica. Hay 80 filas con fecha imposible (hasta 2033) en una sola visita, despreciables.
- **Procedimientos:** ninguno tiene fecha. Solo se pueden relacionar con una etapa de forma indirecta (`docs/procedimientos_y_laboratorios.md`).

## Cómo se etiqueta
Los 71 conceptos de laboratorio traducidos se agrupan en categorías: **inestabilidad** (gases arteriales, lactato), **cardíaco** (troponina, BNP, creatina quinasa), **infección** (cultivos, PCR, antibiograma, serologías), **coagulación**, **hígado y páncreas**, **metabólico y endocrino**, **orina y embarazo**, **rutina** (hemograma, urea, creatinina, electrolitos, glucosa) y **otros**. La etiqueta de una etapa es la primera categoría presente en ese orden; si hay tomas pero ninguna traducida, «solo tomas sin traducir»; si no hay tomas, «sin toma».
Para que las etapas largas no tengan más chance de «tener de todo», la etiqueta se calcula con lo que se pidió **en las primeras 2 horas de cada etapa** (misma exposición para todas), y se compara con la duración total de la etapa.

## Resultados (etapas de más de 2 h; estancias con alguna toma)
**Qué tipo de examen hay en cada posición** (% de las etapas con al menos un examen de la categoría): la primera etapa casi no trae exámenes traducidos (rutina 11 %, infección 5 %, inestabilidad 3 %); las intermedias y la última traen más infección (12–14 %), coagulación (8–9 %), rutina (19–20 %) y, en la última, más higado/páncreas y metabólico.

**Duración de la ÚLTIMA etapa según lo que se pidió en sus primeras 2 h:**
| Lo que se pidió | Etapas | Duración mediana | % de más de 24 h |
|---|---|---|---|
| **Cardíaco (troponina, BNP)** | 123 | **7,1 h** | 8,9 % |
| Inestabilidad (gases, lactato) | 172 | 10,9 h | 29,7 % |
| Infección | 560 | 10,9 h | 21,2 % |
| Coagulación | 191 | 10,2 h | 25,7 % |
| Rutina | 307 | 12,0 h | 26,4 % |
| Solo tomas sin traducir | 2.416 | 11,6 h | 25,7 % |
| Metabólico y endocrino | 47 | 20,7 h | 36,2 % |
| **Sin ninguna toma** | 7.663 | **19,1 h** | **37,2 %** |

- **La última etapa que arranca «en silencio» (sin ningún examen en sus 2 primeras horas) dura casi el doble** (19,1 h frente a 10–12 h) y es más probable que pase de 24 h (37 % frente a 21–30 %).
- **La que arranca con troponina o BNP es la más corta** (7,1 h): los casos cardíacos reciben cama rápido (consistente con que infarto y falla cardíaca tienen espera corta, `docs/diagnosticos_todos.md`).
- En las **primeras etapas** no hay diferencia (todas ~3 h) y en las **intermedias** la diferencia es pequeña (sin toma: 9,3 h frente a 6–9 h).

## Lectura
- El cuello de botella (la última etapa) **se alarga cuando la etapa empieza sin actividad clínica**. Una etapa que arranca con un estudio de gravedad se resuelve antes. Es coherente con que la espera larga es espera con poca actividad (`docs/caracterizacion_etapas_tu.md`).
- No hay un «tipo de examen» que alargue la etapa: los más largos son «sin toma» y algunos metabólicos con pocos casos.

## Límites
- 58 % de las tomas sin traducir: la etiqueta «solo tomas sin traducir» (2.416 etapas) esconde de qué examen se trata.
- «Sin toma» no es «sin atención»: enfermería, imágenes e interconsultas no tienen hora en la base.
- Algunas categorías tienen pocos casos (metabólico 47, hígado 75, cardíaco 123): las diferencias entre ellas son frágiles.
- Son asociaciones, no causas.
