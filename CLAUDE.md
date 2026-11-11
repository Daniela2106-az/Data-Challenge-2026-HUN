# CLAUDE.md — Data Challenge HUN 2026 (contexto completo del proyecto)

Este archivo resume TODO lo que ya se averiguó de la base de datos en semanas de consultas.
**Léelo completo antes de proponer consultas nuevas.** La base es lenta (consultas pesadas de 10–30 min
que traban el computador), así que antes de pedir una consulta comprueba aquí si la respuesta ya existe.
Última actualización: 1-nov-2026 (sección 4.7: respuestas del HUN; sección 4.8: la ocupación no cuadraba con las 106 camas porque faltaban duplicados por detectar; regla de estancia única v3.8 y todas las cifras recalculadas). (Cambio del 22-oct: las estancias en cama replicadas entre dos personas se cuentan
una sola vez; ver sección 4.6. Las cifras de espera de cama, ingresos y ocupación anteriores a esa fecha están infladas.)

## Lee esto primero (si eres un Claude que abre este repositorio por primera vez)

**Qué es:** proyecto del Data Challenge HUN 2026 (Hospital Universidad del Norte + Ciencia de Datos, Uninorte): entender y optimizar el
flujo de pacientes, hallar cuellos de botella, modelar demanda y proponer acciones. Casi todo el trabajo ya está hecho; este archivo y
`docs/HALLAZGOS.md` dicen **qué se encontró** con cifras y fuentes.

**Orden de lectura:** (1) `README.md`, (2) **`docs/HALLAZGOS.md`** (hallazgos, glosario, preguntas frecuentes, mapa de archivos),
(3) este archivo: sección 4.6 (estancias gemelas), 6b (resultados de cuellos de botella), 8 (preguntas al HUN), (4) `docs/plan_de_accion.md`
(definición de cuello de botella y fases), (5) `docs/recomendaciones.md` y `docs/dias_atipicos.md`, (6) `docs/fichas_de_tareas.md` (reparto del equipo).

**Lo que NO hay en el repositorio:** los datos (`datos/`) ni las tablas de resultados (`resultados/tablas/`, `resultados/excel/`) están fuera de git
porque son datos clínicos. Solo hay código, consultas SQL, documentos y los gráficos de `resultados/graficos/`. Por eso contesta **desde los
documentos**; si te piden una cifra que no está escrita, di que no está registrada, señala el script que la produce y que hace falta
tener los datos (ver `README.md`, "Cómo reproducirlo"). Nunca pidas ni escribas la contraseña de la base.

**Reglas al contestar:**
- Cita el archivo o la sección de donde sale cada cifra. No inventes números ni causas.
- Distingue **asociación** de **causa** y di siempre la limitación al lado del hallazgo (casi todo son asociaciones y escenarios).
- **Cifras obsoletas:** las de espera de cama mediana 22,4 h, 27,7 ingresos por día y ~145 camas (secciones 5 y 6 y algunos textos viejos) estaban
  infladas por estancias duplicadas. **Vigentes (1-nov, regla v3.8, sección 4.8): espera mediana 18,6 h, ~20 ingresos por día, ~100 camas ocupadas en promedio (94 en 2023 a 105 en 2025).** Las cifras de 22-oct (18 h, ~22 ingresos, ~113 camas) también quedaron infladas por duplicados que faltaban.
- La meta de tiempos y la causa del cambio de registro desde el 10 de abril de 2026 **no se conocen** (la auditoría de 4.9 descarta que sea menos demanda). El HUN respondió en la sesión del 29-oct: **106 camas, 58 camillas**, la hospitalización se registra al asignar cama, las gemelas son duplicados y hay horarios de alta (sección 4.7). No habrá más sesiones.

**Dónde está cada respuesta:** espera de cama y cuello de botella → `HALLAZGOS.md` 4; altas tardías y factores → 6b; pronóstico y alertas → 6b;
calidad de datos y duplicados → 4.1 y 4.6; recomendaciones → `docs/recomendaciones.md`; qué falta → sección 9.

---

## 0. Cómo trabajar conmigo (preferencias del equipo)

*(Son las preferencias de la persona que lleva el proyecto, que habla en primera persona. Si eres otra persona del equipo, sigue
las mismas salvo que te digan otra cosa.)*

- Habla en español, claro y explícito, para que no haga falta preguntar dos veces.
- Cuando cambies código, entrega SIEMPRE el archivo completo, nunca "cambia esta partecita".
- No me des la razón por complacerme: si una idea mía es mala o hay un camino mejor, dilo y explica por qué.
- No tengo formación médica: explica los términos clínicos en palabras simples.
- **Nunca** pidas ni escribas la contraseña de la base en el chat ni en un archivo del proyecto.
- Las consultas a la base las corro yo en DBeaver y exporto CSV; tú trabajas sobre los CSV en Python.
  Si necesitas un dato nuevo de la base, dame UNA consulta lista para copiar, explica cuánto puede tardar
  y con qué nombre guardar el CSV. Prefiere agregar por visita en SQL antes que exportar tablas enteras.
- Verifica tus cambios corriéndolos antes de decir que funcionan.

---

## 1. El reto

**Data Challenge HUN 2026** (Hospital Universidad del Norte + pregrado de Ciencia de Datos, Uninorte).
Pregunta central: *comprender, predecir y optimizar el flujo de pacientes dentro del hospital,
identificando cuellos de botella, patrones operacionales y oportunidades de mejora en los tiempos de atención.*

Componentes (el instructivo pide abordar **uno o varios**, no todos obligatoriamente):
1. Caracterizar el flujo hospitalario reconstruyendo las etapas de cada visita.
2. Identificar factores asociados a mayores tiempos de atención y estancias; detectar cuellos de botella.
3. Modelos analíticos o predictivos: estimar tiempos, detectar saturación o patrones atípicos.
4. Propuestas que expliquen qué afecta la eficiencia y cómo traducirlo en acciones concretas.

Se valora: hallazgos estratégicos para el hospital, interpretabilidad, visualización efectiva y
comunicación clara de resultados.

**Entregables (fin de noviembre 2026):** documentación del proyecto, repositorio en GitHub y
enlace a un dashboard interactivo en Power BI.

**Decisión de enfoque:** la profundidad va en los componentes 2 (espera de cama) y 3 (modelos);
el 1 da contexto y el 4 sale de los dos anteriores.

---

## 2. Acceso a la base

> **Cómo consultar la base desde Claude Code (conexión de solo lectura con SQLAlchemy, la VPN que apaga el internet y el flujo para correr consultas en segundo plano): ver `docs/conexion_bd.md`.** Las credenciales viven fuera del proyecto (`~/.pgpass` y `~/.hun_db.json`); nunca las pidas ni las escribas.

- PostgreSQL detrás de VPN, esquema **`uninorte_omop`** (el esquema `public` está vacío).
- Conexión **de solo lectura**: `CREATE TEMP TABLE` falla ("read-only transaction"). Usar `WITH` (CTE).
- Solo existen índices de llave primaria. `concept` no tiene ningún índice. Las tablas grandes no tienen
  índice por `visit_occurrence_id` ni `person_id`.
- Antes de consultas pesadas: `SET statement_timeout = 0;` (o `'30min'`).
- DBeaver muestra por defecto 200 filas: subir el límite o exportar con "Exportar datos > CSV"
  (que vuelve a correr la consulta completa). Ojo: copiar desde la grilla exporta solo lo cargado.
- Periodo de datos: **enero 2023 a julio 2026 (último día con etapas: 2026-07-17)**; la tabla de visitas llega hasta el 13-ago-2026. Para modelos y comparaciones el periodo confiable termina el 9-abr-2026.
  **Aviso (actualizado 2-nov, auditoría en la base, ver 4.9): el registro de las etapas (`visit_detail`) se degrada desde el 10 de abril de 2026** (más visitas sin etapas, menos visitas con etapa ER; desde el 29-abr empeora). Las visitas de urgencias de cabecera no bajaron en mayo (+2 % frente a mayo de 2025). El periodo confiable es feb-2023 a 9-abr-2026; después no se usa para estimar nivel, calendario ni error. (Contexto del 22-oct: las llegadas por día bajaban de 244 en ene–abr a 186 en mayo y 171 en junio; eso era el efecto del registro, no de la demanda.)

### Tamaños

| Tabla | Filas | Tamaño |
|---|---|---|
| measurement | 16,6 M | 15 GB |
| procedure_occurrence | 47,0 M | 3,9 GB |
| condition_occurrence | 38,6 M | 3,8 GB |
| concept | 10,0 M | 1,1 GB |
| visit_detail | 3,28 M | 318 MB |
| visit_occurrence | 1,706 M | 153 MB |
| person | 912 mil | 92 MB |

---

## 3. Tablas y columnas (lo que de verdad hay, no lo que dice el instructivo)

### person
- `person_id`, `gender_concept_id` (sexo; 53 % mujeres, 47 % hombres, 129 sin dato),
  `year_of_birth` (confiable; 39 visitas con año 0 o 1 y 3 con más de 110 años → descartar),
  `race_concept_id` (95 % sin dato, no sirve), `ethnicity_concept_id` (casi todo "Hispanic or Latino", no sirve).
- 304.457 pacientes tienen visitas (5,6 visitas por paciente); los otros 607.748 no tienen visitas.

### visit_occurrence (una fila por "visita")
- `visit_occurrence_id`, `person_id`, `visit_concept_id`, `visit_start_datetime`, `visit_end_datetime`, `provider_id`.
- **No existen** `visit_type_concept_id` ni `preceding_visit_occurrence_id` (el instructivo dice que sí).
- `visit_end_datetime = visit_start_datetime` en el **100 %**: la visita no tiene duración. Las duraciones
  salen de `visit_detail`.
- `provider_id` siempre 0.
- `visit_concept_id`: 581479 "Ambulatory Rehabilitation Visit" 1.089.461 (63,9 %, probablemente consulta
  externa mal mapeada); 9203 "Emergency Room Visit" 598.088; 3045729 "Treatment urgency" 17.858
  (35 % niños de 0–9 años, quizá urgencia pediátrica u observación); 9201 "Inpatient Visit" 592
  (casi desaparece desde 2025); 0: 2 visitas.
- **El tipo de visita NO es confiable para saber por dónde pasó el paciente:** visitas "ambulatorias" contienen
  etapas de urgencias y hospitalización. Origen de las 69.344 visitas con hospitalización:
  urgencias 69 %, ambulatorio 23 %, treatment urgency 7 %, inpatient 1 %. Por eso el análisis usa
  TODOS los tipos de visita.
- `visit_start_datetime` no se usa para medir: en ~45 % de las visitas la primera etapa empieza antes que la
  visita (ver sección 5.6). Todos los tiempos se miden desde la primera etapa.

### visit_detail (LA tabla clave: etapas del recorrido)
- `visit_detail_id`, `visit_occurrence_id`, `visit_detail_concept_id`, `visit_detail_start_datetime`,
  `visit_detail_end_datetime`, `provider_id` (siempre 0). **No tiene `person_id`**: se llega al paciente por
  `visit_occurrence`. No hay columna de servicio/piso/cama.
- Solo 4 tipos de etapa:

| Código | Nombre en la base | Lo llamamos | Qué parece ser | Registros | Mediana |
|---|---|---|---|---|---|
| 9203 | Emergency Room Visit | ER | llegada/admisión/triage a urgencias | 481.481 | 3 min |
| 3045729 | Treatment urgency | TU | atención en urgencias (incluye observación/espera) | 1.152.191 | 1,2 h por etapa |
| 9201 | Inpatient Visit | HOSP | hospitalización (paciente en cama) | 108.601 | 46 h por etapa |
| 581479 | Ambulatory... | AMB | evento ambulatorio administrativo | 1.539.340 | 0 (siempre inicio = fin) |

- AMB siempre dura 0 y suele estar ~2 semanas antes a hora redonda (una cita previa). Se quita del análisis.
- Las etapas TU se repiten varias veces seguidas sin información extra; lo que las distingue es su posición.
  Las etapas iguales consecutivas se juntan en un "bloque".
- Las etapas van pegadas (fin de una = inicio de la siguiente, a veces con 1 s de solape).
- Varias HOSP seguidas = probablemente traslados entre servicios.
- **Estos códigos son internos del hospital mapeados a OMOP; el HUN no los conoce como ER/TU/HOSP.**
  Al preguntarles, usar los números.

### condition_occurrence (diagnósticos)
- Columnas reales: `condition_occurrence_id`, `person_id`, `visit_occurrence_id`, `condition_concept_id`,
  `condition_start_datetime`, `condition_type_concept_id`. **No hay `condition_source_value`** → no hay
  código CIE-10 original.
- 37 % de las filas con concepto 0 ("No matching concept", sin traducción).
- Los traducidos están en **SNOMED** (no CIE-10). Sin `concept_ancestor` no se pueden agrupar por jerarquía
  → hay que agrupar a mano (plan: `mapeo_dx.csv` con los ~300 diagnósticos más frecuentes).
- `condition_type_concept_id` siempre 0: no se sabe cuál es el diagnóstico principal → se usa el primero
  mapeado por fecha.
- Repetición enorme: un mismo diagnóstico puede tener 400–1.000 filas en una visita. **Contar siempre
  conceptos distintos, nunca filas.**
- `condition_start_datetime`: 4,8 % en las primeras 2 h de la visita, 88,5 % después, 3,9 % después del alta,
  2,6 % antes. → Sirve para describir y explicar, **no para un modelo que prediga "al llegar"** (fuga de información).
- La duración mínima estimada con la hora del último diagnóstico es mala: en episodios con tiempo real da en
  mediana el 35 % de la duración real (p25 0,07, p75 0,87). No usar para tiempos.
- **Muchos diagnósticos están colgados de las visitas copia** (ids > 1.746.478), no de la original (ver 5.3).

### procedure_occurrence (procedimientos)
- `procedure_date` existe pero está **vacía en toda la tabla**; no existen `procedure_datetime` ni
  `procedure_type_concept_id`. → Solo conteos por visita (conceptos distintos).
- Contenido: sobre todo órdenes de laboratorio (glucosa, hemograma, creatinina, electrolitos), imágenes
  (RX, TAC), cirugías (cesárea, colecistectomía) y notas de urgencias.
- "Admission to adult intensive care unit" es la única señal de UCI de toda la base.
- 180–576 filas por visita pero solo 9–30 distintas.

### measurement (laboratorios)
- `measurement_datetime` **sí es válido**: hora de toma/recepción de la muestra (94,8 % dentro de la visita).
  Es la única tabla clínica con hora útil.
- El valor viene como texto en `measurement_source_value_extended` (informe completo; cada componente repite
  el informe → por eso pesa 15 GB). `value_as_number` casi siempre 0 (solo potasio, sodio y creatinina
  traen valores lógicos). No existen `unit_concept_id` ni `measurement_type_concept_id`.
- Cada examen aparece dos veces (SNOMED y LOINC). La mitad sin traducción.
- No hay signos vitales.
- Solo una parte de las visitas tiene laboratorios; cobertura pareja ene-2023 a abr-2026, cae a la mitad en
  may–jun 2026.
- El total de laboratorios de una visita crece con la estancia → como factor usar solo los de las primeras 6 h
  (`n_lab_6h`), nunca el total.

### concept
- `concept_id`, `concept_name`, `domain_id`, `vocabulary_id`, `concept_code`. 10 M filas, sin índices.
  Para traducir, unir solo contra el resultado ya agregado.

---

## 4. Problemas de calidad descubiertos (y cómo se resolvieron)

### 4.1 Visitas copia (≈30 % de la base)
- 512.045 de 1.706.001 visitas son copias de otra: `visit_occurrence_id = original + desfase`, con las mismas
  etapas al segundo. Desfases: 1.746.478 (259.183), 1.757.764 (211.534), 1.746.479 (23.575), y otros
  1.746.480–1.746.489. También aparecen diferencias 11.280–11.286 entre copias (copia de copia).
- Muchas veces el `person_id` de la copia es distinto (82 % en los grupos duplicados).
- Regla de detección: existe `id − desfase` **y** (misma persona **o** mismo fin **o** mismo inicio).
  Motivos: mismo fin 236.566, misma persona 234.136, solo mismo inicio 41.343.
- Además, 43.689 episodios cuyas etapas están todas (las TU/HOSP) en otra visita de id menor también son copias.
- **Prueba del 20-oct (consulta `sql/consulta_propiedad_copias.sql`, 75 pares):** en las candidatas por "mismo fin" (236.566)
  y "solo mismo inicio" (41.343) la persona es SIEMPRE distinta (diferencia mediana de `person_id` = +1, edad mediana
  21 años de diferencia, 65 % con ≥ 15 años). En la visita de id menor los diagnósticos son 100 % de su persona; en la de
  id mayor mezclan dos personas (la propia y la de la otra visita). Su línea de tiempo es idéntica al segundo a la de
  la otra visita. Conclusión: son **registros replicados entre dos personas distintas**, no copias del mismo paciente.
  Qué persona es "la real" sigue sin saberse (pregunta 1 al HUN).
- **Prueba de "pasar etapas de la copia a la original" (v3.3):** NO sube la cobertura. Solo el 12,6 % de los pares
  "raíz sin tiempo / copia con tiempo" empieza a la misma hora; el resto trae una atención de ~16 días antes. Importar
  todo mezcla atenciones distintas. Se deja solo para copias de la misma persona (`MODO_COPIAS = "importar"`).
  Borrar copias descartaba 163.878 etapas que no existen en ninguna otra visita (74 % de otra persona).
- **Regla vigente (v3.5):** solo es copia (se borra la visita) si la persona coincide (238.674 visitas). Las 311.582
  candidatas de otra persona se conservan como visitas; sus etapas idénticas a las de la visita de id menor se quitan
  en la sección 5 (319.784 visitas de otra persona quedan fuera por tener TODAS sus etapas repetidas) y lo propio de
  cada persona se queda. Si se conservaran enteras, los episodios subirían a 743.802 y el 67 % serían idénticos entre sí.
- Resultados v3.5: episodios 337.194 · espera de cama mediana 22,4 h (n = 34.537) · llegadas por día mediana 264 ·
  diagnóstico principal en 23,6 % de los episodios (antes 3 %).
- **v3.6 (estado nuevo `minimo_conocido`):** el 21,7 % de los episodios TU "medidos" terminaba en una etapa con inicio = fin,
  o sea la salida real es posterior a lo que medimos (duración truncada). Ahora `medida` exige que la ÚLTIMA etapa TU/HOSP
  esté cerrada. Estados: medida 37,3 % · minimo_conocido 7,9 % · minimo_dx 12,7 % · sin_duracion 20,4 % · sin_actividad 21,7 %.
  TU medida 38,2 % (mediana 9,5 h). La espera de cama no cambia (solo usa el inicio de la primera HOSP).
- Dx, procedimientos y laboratorios solo se pasan a la raíz desde copias de la MISMA persona (`misma_persona` en copias.csv).
  Pendiente opcional: re-exportar las consultas 2–4 filtrando `co.person_id = vo.person_id` para quitar los registros
  que una visita tiene de otra persona.
- Los diagnósticos, procedimientos y laboratorios de las copias deben pasarse a la original (v3.2 ya lo hace).

### 4.2 Etapas abiertas
- ~2.053 etapas tienen `visit_detail_end_datetime` con **milisegundos** (p. ej. 2026-07-18 05:42:56.741),
  todas en julio 2026: el fin es la fecha de extracción (pacientes aún en el hospital). El resto de la base no
  tiene milisegundos. Filtro: `visit_detail_end_datetime = date_trunc('second', visit_detail_end_datetime)`.
- Quedan ~2.200 etapas TU de 7–30 días sin milisegundos, sospechosas pero no corregidas.

### 4.3 Etapas TU sin hora de fin (dato faltante real)
- Prueba cruda en la base (etapas 3045729 con inicio = fin / total): 2023 148.592/356.782 (41,6 %);
  2024 134.372/350.357 (38,4 %); 2025 113.382/316.429 (35,8 %); 2026 47.013/128.623 (36,6 %).
- Por eso ~58 % de los episodios no tienen hora de salida. **No son atenciones cortas:** la distribución es
  bimodal (casi nada entre 15 min y 1 h); o la TU tiene duración real o tiene inicio = fin. Patrón típico:
  ER de 2–5 min y luego TU con inicio = fin. Estable 54–67 % en todos los trimestres.
- Todo lo que termina en hospitalización está medido al 100 %. El faltante es la hora de salida de quienes se
  van de alta desde urgencias.

### 4.4 Visitas "partidas" (varias atenciones bajo un mismo id) y el "desfase de 16 días"
- Histograma de huecos entre etapas antes de quitar copias: pico enorme en 14–30 días (64.972).
  **Después de quitar copias, ese pico desaparece** (246): el "desfase de 16 días" vivía en las copias.
- Se corta un episodio nuevo cuando pasan más de 168 h sin etapas (quedan solo 554 visitas partidas;
  con 72 h serían 2.046, con 336 h 250).
- Hipótesis descartada: corrimiento de fechas por anonimización.

### 4.5 Otros
- Visitas solo con ER (48.489 episodios): 83,5 % sin diagnósticos ni procedimientos (puede bajar al pasar la
  actividad de las copias). Probablemente pacientes que se fueron sin atención o registros administrativos.
- El 25,8 % de episodios "sin actividad" puede estar inflado por la actividad colgada de copias.

### 4.6 Estancias gemelas en cama (22-oct-2026) — cambia las cifras de espera, ingresos y ocupación
- **Hallazgo:** 14.615 de 35.322 episodios con hospitalización (41,4 %) comparten exactamente `ini_hosp` y `fin_hosp`
  con otro episodio. Son la MISMA estancia registrada en DOS PERSONAS: en los pares el `person_id` difiere en ≤ 2 en el 78 %
  (al azar sería 0,005 %), y los `visit_occurrence_id` difieren por los desfases de copia conocidos (1.746.478–89) en ~90 %.
  Las esperas de los dos miembros casi coinciden (diferencia p90 = 0,8 h). Es el mismo fenómeno de la sección 4.1, pero en
  la hospitalización sobrevive a la regla v3.5 porque esa solo quita episodios con TODAS sus etapas repetidas.
- **Decisión (regla v3.7 de análisis, no del pipeline de limpieza):** cada estancia se cuenta UNA vez, deduplicando por
  (`ini_hosp`, `fin_hosp`) y quedándose con el episodio de menor `visit_occurrence_id`. Elegir uno u otro no cambia la
  espera (casi idéntica). No se sabe cuál de las dos personas es la real (pregunta 1 al HUN); para tiempos y camas no importa.
- **Dónde se aplica:** `src/construir_segmentos.py` (v1.1, `DEDUP=0` para desactivarlo) y `src/exportar_para_equipo.py` (v2:
  `estancias_hospitalizacion.csv` trae una fila por estancia con `n_registros`, y `panel_diario.csv` cuenta ingresos, altas,
  hospitalizados, espera y ocupación con estancias únicas). **También en el pipeline (23-oct):** `analisis_etapas.py` v3.7 marca cada episodio con `ini_hosp`, `fin_hosp`, `estancia_gemela` y
  `estancia_unica` (14.614 gemelos de 35.343 hospitalizados; 27.956 estancias únicas; no se borra ningún episodio) y
  `preparar_variables.py` v2.1 usa solo estancias únicas para la ocupación, los ingresos y las series. Resultado del pipeline:
  `espera_cama.csv` 27.162 estancias con mediana 18,0 h (antes 34.537 y 22,4 h), ocupación media 112,9 camas (antes 146,7),
  22,0 llegadas por día que se hospitalizan (antes 28,0); las llegadas totales no cambian (265 por día). `tabla_episodios` conserva
  todos los episodios con la marca `estancia_unica`: para espera, camas e ingresos filtrar `estancia_unica == True`. Pendiente:
  la ocupación de TU (`ocup_tu`) y la cobertura por ruta siguen contando todos los episodios.
- **Efecto (ene-2023 a jun-2026):**

| | Antes (sin deduplicar) | Después (una vez por estancia) |
|---|---|---|
| Estancias con cama | 35.322 | 27.934 |
| Ingresos a cama por día | 27,7 | **21,9** |
| Camas ocupadas en promedio | ~146 | **~113** |
| Espera de cama mediana / p75 / p90 | 22,4 / 42,4 / 77,5 h | **18,0 / 37,2 / 71,5 h** |
| Espera de cama mayor a 24 h | 47,9 % | 42,7 % |
| Hueco sin etapa, como % de la espera | 17 % | 23 % |

  La coincidencia de la ley de Little (27,7 × 5,2 ≈ 144) con la ocupación observada (145) era real, pero las dos cifras
  estaban infladas por lo mismo. Q4 (intervalos distintos por etapa) da ~100 camas; el nivel absoluto depende del método
  (100–113) y el número real de camas lo tiene que dar el HUN.
- **Lo que NO cambia:** los peores casos siguen empeorando de 2023 a 2026 (espera de cama p90 de 61 h en 2023 a 80 h en 2026
  con estancias únicas; la mediana se queda en 17–20 h), y urgencias antes de la cama sigue siendo el componente que más horas pierde (77 % de la espera).
- **Llegadas (medido el 22-oct, cota inferior):** 13.615 pares de episodios empiezan en el mismo segundo, con personas de
  `person_id` cercano (≤ 10) y `visit_occurrence_id` a un desfase de copia conocido: ≥ 4 % de las llegadas (4.0 % del total)
  son réplicas (20,8 % de los episodios con cama, 6,6 % de los demás). La cifra real es mayor (solo se contaron pares
  exactos). Afecta al Modelo A (demanda por día) y a `llegadas_6h_previas`, que se usa como medida RELATIVA de carga
  (su nivel está algo inflado, su variación no). Falta decidir si se deduplican las llegadas.

---

### 4.7 Sesión con el HUN del 29-oct-2026 y regla de estancia única v3.8 (lo que dijeron y qué cambió)
Respuestas (tomadas en la reunión, sin documento escrito; no habrá más sesiones):
- **Camas:** 106 camas de hospitalización (piso y UCI: Adultos 64, Pediátrica 8, TPR 4, Intermedia Adultos 6, Intensiva Adultos 14, incubadoras neonatales 6 + 3 + 1) y **58 camillas de urgencias**
  (Observación Pediátrica 14, Adultos Hombres 18, Adultos Mujeres 26; primero dijeron 68 y corrigieron). No dijeron a qué fecha corresponde la lista.
  **Confirmado el 8-nov-2026 con una tabla del HUN** (mismos números, con el desglose completo por tipo): este desglose se usa en A5 (`docs/modelo_camas.md`) para simular la ocupación por el proxy niños (pediátrica+neonatal=18) / adultos (64+6+14+4=88), ya que la base no distingue servicio/piso/cama.
- **Cuándo se registra la hospitalización (9201):** cuando **se asigna la cama**; el traslado físico tarda solo un par de minutos. Nuestra "espera de cama" es, por tanto, llegada hasta asignación de cama
  (sigue sin poder separarse la atención clínica de la espera de cama dentro de urgencias).
- **Estancias gemelas:** "lo más probable es que sean duplicados"; elegir el registro que tenga la información clínica (condición, procedimiento, etc.).
- **Altas:** sí hay horarios y costumbres para dar de alta (consistente con el 61,5 % de altas entre las 14:00 y las 18:59; no dieron más detalle).
- **Choque con nuestros datos (RESUELTO el 1-nov, ver 4.8):** la ocupación estimada con la regla v3.7 (media 112 en HOSP) superaba las 106 camas. Era un error nuestro: quedaban estancias duplicadas sin detectar. Con la regla v3.8 la ocupación media es 94 (2023), 101 (2024) y 105 (2025), coherente con las 106 camas. La ocupación de urgencias (TU, 110 contra 58 camillas) sigue sin cuadrar y se trata solo como medida relativa.
- **Regla de selección por información (29-oct, `preparar_variables.py` sección 4b):** de cada estancia gemela se conserva el registro con más tipos de información (diagnóstico, procedimiento, laboratorio) y recibe lo que le falte del gemelo
  (`FUSIONAR_INFO=0` lo desactiva). Antes: el de menor `visit_occurrence_id`, que solo tenía diagnóstico en 163 de 6.414 pares en que uno solo lo tenía. Efecto: con diagnóstico 38,3 % → 61,2 % de las estancias, con laboratorio
  44,6 % → 65,4 %, espera mediana 17,99 → 18,10 h; ingresos, camas y panel diario no cambian; R² de la espera 12 % → 13,8 %. Advertencia: el diagnóstico puede ser de la otra persona del par. `exportar_para_equipo.py` usa la marca
  `estancia_unica` de `tabla_episodios`; `construir_segmentos.py` (cuellos de botella) sigue con el de id menor porque solo usa tiempos.

### 4.8 Regla de estancia única v3.8 (1-nov-2026): la ocupación superaba las 106 camas por duplicados que faltaban
**Problema:** con la regla v3.7 la ocupación media de 2025 era 118,6 camas, y el HUN dice que tiene 106. Si hay un total de camas, la ocupación media no puede superarlo, así que
había que decidir si fallaba el dato del HUN o nuestro conteo. Pruebas hechas (todas con los datos que ya teníamos):
- Descartadas como causa: estancias casi idénticas (solo ~216 pares, 1 cama), estancias largas que seguirían "en cama" sin estarlo (los laboratorios llegan hasta ~1,6 días antes del alta; recortarlas baja 0,1 camas),
  huecos entre etapas (bloques reales de HOSP dan lo mismo), pacientes esperando en urgencias (el HUN dice que la hospitalización se registra al asignar la cama).
- **Medida independiente:** contar directo sobre `visit_detail` los intervalos HOSP distintos (inicio, fin) (consulta Q4, `sql/consultas_cuellos_botella.sql`) daba 94 / 101 / 105 camas en 2023 / 2024 / 2025, frente a 105 / 113 / 119 del pipeline.
- **Causa:** la regla v3.7 llamaba gemelas solo a los registros con el mismo inicio Y el mismo fin de cama. Pero en 3.845 estancias uno de los dos registros trae una etapa HOSP adicional al comienzo: el inicio total difiere,
  pero comparten al menos un intervalo HOSP idéntico al segundo (dos pacientes distintos no comparten un intervalo idéntico por casualidad; en el 96 % de esos pares también coincide el fin y en el 97 % los `person_id` son vecinos, nunca la misma persona).
**Regla v3.8** (`src/analisis_etapas.py`): una estancia es el conjunto de episodios conectados por compartir el (inicio, fin) de cama **o** algún intervalo HOSP idéntico (union-find). Columnas nuevas en `episodios.csv` y `tabla_episodios`:
`estancia_id`, `n_registros_estancia`, `ini_hosp_est`, `fin_hosp_est` (mínimo y máximo entre los registros) e `ini_est` (llegada más temprana). **La espera de cama es la de la estancia** (`ini_hosp_est - ini_est`), así no depende de cuál registro se conserve
(antes sí: la mediana cambiaba hasta 1,4 h según el registro). Se sigue conservando el registro con más información clínica (4.7); la ocupación, los ingresos y las series usan el inicio y fin de toda la estancia.
Resultado: 35.343 episodios hospitalizados → **25.777 estancias** (antes 27.956; 2.179 duplicados más).

| | Antes (v3.7, 29-oct) | **Ahora (v3.8, 1-nov)** |
|---|---|---|
| Estancias únicas | 27.956 | **25.777** |
| Ingresos a cama por día | 21,8 (2023-24: 22,3 / 22,6) | **20,2** (20,6 / 20,8 / 19,8 en 2023 / 2024 / 2025; promedio hasta el 9-abr-2026) |
| Camas ocupadas, media 2023 / 2024 / 2025 | 105 / 113 / 119 | **94 / 101 / 105** (máximo 143 → 123) |
| Estancia media 2023 → 2025 | 4,70 → 5,46 días (+16 %) | **4,57 → 5,31 días (+16 %)** |
| Espera de cama mediana / p75 / p90 | 18,0 / 37,2 / 71,5 h | **18,6 / 37,9 / 73,9 h** |
| Espera de cama > 24 h | 42,7 % | **43,7 %** |
| Exceso medio de espera por episodio, 2023 → 2026 | 16,4 → 22,9 h (+40 %) | **17,3 → 23,8 h (+38 %)** |
| Reparto de las horas de espera: urgencias / hueco sin etapa | 77 % / 23 % | ~~80 % / 21 %~~ **corregido el 7-nov: 98 % / 3 % (99 % / 1 % hasta el 9-abr-2026), ver 4.12** |
| Altas entre 14:00 y 18:59 / antes del mediodía | 61,5 % / 15 % | **62,7 % / 14 %** |
| Escenario de altas (30 % de la tarde pasa a la mañana) | 5,5 camas libres a las 12 h | **5,1** (con ~103 camas ocupadas a esa hora) |
| Ley de Little: ingresos × estancia | 21,7 × 5,46 ≈ 119 | **19,8 × 5,31 ≈ 105** |
| R² de los factores de la espera | 13,8 % | **15,8 %** (tras la regla v4.0 de la persona real, 4.10) |

Lo que **no cambia** (no depende de las estancias): llegadas por día, calendario, pronóstico de llegadas, días atípicos de llegadas, perfiles por hora de llegada, tiempos por diagnóstico en lo cualitativo.
Pendiente de revisar por quien lea esto: las cifras de las secciones 4.1 a 6b de este archivo y de los documentos de `docs/` que no aparecen en la tabla (las alertas de camas y R6 ya se recalcularon el 8-nov con la regla v3.8) pueden ser de la regla v3.7; las que
aparecen en `docs/HALLAZGOS.md`, `docs/recomendaciones.md`, `README.md` y `powerbi/` ya se actualizaron. Respaldo completo de lo anterior en `datos/procesados/respaldo_dedup_v37/` y `resultados/respaldo_dedup_v37/` (no se suben a git).
**Revisión directa en la base (2-nov-2026, `src/explorar_bd.py` + `src/conexion_bd.py`, solo lectura; los resultados están en `datos/crudos/exploracion_bd/`, fuera de git):**
- **El esquema real tiene 8 tablas** (`person`, `visit_occurrence`, `visit_detail`, `condition_occurrence`, `procedure_occurrence`, `measurement`, `concept` y `cups`). `visit_detail` solo trae id, visita, tipo de etapa, inicio, fin y `provider_id`:
  **no hay servicio, sede, piso ni cama**, así que no se puede separar camas de camillas con los datos. `concept` solo trae `concept_id`, `concept_name`, `domain_id` y `vocabulary_id` (sin `concept_code`).
- `cups` es el catálogo nacional de procedimientos (94.086 filas, columnas `codigo`, `descripcion`, `periodo`). **No se puede enlazar** con `procedure_occurrence`: sus códigos son SNOMED, LOINC o ICD9Proc, y ninguno de los 158 más frecuentes coincide con un código CUPS.
- **Duplicados que pudieran quedar:** entre las 15.946 estancias únicas con 3 o más diagnósticos, solo 1 par (de la misma persona, con 916 h de diferencia) comparte la misma huella de diagnósticos (cantidad y primera/última hora). Quitarla no cambia la ocupación (105,0). Con esto, **los duplicados residuales son despreciables**.
- **Diagnósticos con código por semana** (`condition_occurrence`, directo de la base): ~160 mil filas con código por semana hasta el 20-abr, 110 mil la semana del 27-abr, 36 mil la del 4-may y **cero desde el 11-may**. Las filas sin código (concepto 0) se mantienen en ~70–85 mil por semana. Confirma en la base lo que se veía en los CSV: el código estándar se pierde a inicios de mayo de 2026.
**Sobre la ocupación de camas (conclusión):** la media de 2025 (105) es casi la capacidad (106), pero no es un error: un hospital con 18 h de espera mediana por una cama está saturado, y eso es justo lo que se espera de un hospital con las camas casi siempre llenas. Los picos hasta 123 serían camas
de apoyo o camillas; no se puede comprobar. **Sobre urgencias:** la ocupación de TU no es comparable con las 58 camillas, porque TU incluye a todo paciente en atención en urgencias (consultorios, sillas, observación), no solo camillas. Con intervalos distintos (cuenta directa de la base, Q4) la media de TU de 2025 es 103;
con el pipeline (que aún cuenta los episodios de cada gemelo) sale 126; con estancias únicas, 118. **Hecho el 3-nov (`preparar_variables.py` v2.5): `ocup_tu` cuenta cada intervalo TU distinto una vez; la media de 2025 pasa de 125,7 a 111,0** (sigue por encima de las 58 camillas porque TU incluye más que camillas). 
Hay 1.762 estancias cuyas etapas HOSP vienen de copias y no de su propia visita (aportan ~4 camas en 2025 con la regla v3.7; no se pudo comprobar si son reales).

### 4.9 Auditoría directa en la base (2-nov-2026): el quiebre de mayo está en el DETALLE, no en las visitas (`src/auditoria_bd.py`, resultados en `datos/crudos/auditoria_bd/`, fuera de git)
Lote 1 (23 consultas de solo lectura, 4,7 min). Lo que confirma y lo que cambia:
- **El quiebre de abril–mayo de 2026 está en `visit_detail` (las etapas), no en `visit_occurrence` (las visitas).** Visitas de urgencias (cabecera, `visit_concept_id` 9203) por mes: 12.8 mil (ene), 11.8 mil (feb), 13.5 mil (mar), 16.8 mil (abr), 14.1 mil (may), 12.7 mil (jun);
  frente a 2025: ene −2 %, feb +4 %, mar +4 %, abr +35 %, **may +2 %**. En cambio las etapas ER caen 64 % en mayo frente a mayo de 2025, las TU 46 % y las HOSP 45 %. La razón etapas ER / visitas ER pasa de ~0,80–0,84 (hasta marzo) a 0,59 (abril), 0,28 (mayo) y 0,30 (junio).
  Los laboratorios también bajan (filas −46 %, visitas con laboratorio −51 %) y los diagnósticos con código llegan a 0 desde el 11-may. **Todo apunta a detalle incompleto desde el 29-abr, no a menos pacientes.**
- **La baja ya venía antes en las etapas TU:** −15 % en enero, −14 % febrero, −13 % marzo y −17 % abril frente al mismo mes de 2025, con las visitas y las etapas ER planas. Eso explica la caída de "llegadas con atención" (que depende de TU) desde enero de 2026; puede ser un artefacto de registro.
- **Validan nuestros números (independiente del pipeline):** altas por hora: 61,3 % entre 14:00 y 18:59 y 15,3 % antes del mediodía (pipeline: 62,5 % y 14 %); ingresos a cama por hora, mismo perfil; copias de la misma persona por desfase de id ~250 mil (concuerda con 4.1);
  horas redondas en inicio y fin de HOSP: 36 de 104.600 (no hay marcas administrativas); años de nacimiento imposibles: 87 personas de 912 mil (despreciable).
- **Camas:** (a) en 2025 hay 438 intervalos HOSP de una misma persona que se solapan con otro suyo (19.375 horas, ~2,2 camas de doble conteo; 2023: 1,7; 2024: 1,8); no corregido, menor. (b) La repetición de intervalos TU en la base es 2,6 veces (708.832 filas cerradas, 271.087 intervalos distintos), y de HOSP 2,6 veces (104.600 por visita, 40.064 distintos), coherente con las gemelas.
  (c) Los laboratorios de la visita conservada llegan hasta una mediana de 23 h antes del alta (34 h en estancias de 48 h o más): puede indicar altas registradas tarde, pero esa consulta solo vio los laboratorios de UNA de las visitas gemelas (17,9 % de las estancias tenían alguno); el lote 2 la repite con todas.
- Diagnóstico: hay 2 filas por trimestre con fecha futura (de 2026 a 2033) en una sola visita (error de dato, despreciable). Las comparaciones de espera "a nivel de visita" sin cortar episodios dan resultados distintos (mediana 29 h) y no sirven de contraste; el lote 2 incluye el corte de 168 h.
**Lote 2 (6 consultas, 2,3 min) — el registro se degrada desde el 10-abr-2026, no desde mayo:**
- **Fechas del quiebre (visitas de urgencias de cabecera, por día):** hasta el 9-abr, el 65 % de las visitas tiene etapa ER, ~75 % tiene etapa TU y ~10 % ninguna etapa (estable desde 2025). **Desde el 10-abr** la proporción con etapa ER baja a ~52 % y las visitas diarias suben ~40 % (de ~490 a ~700 en días de semana; semanas de 4,6 mil visitas contra 3,2 mil), con más visitas sin ninguna etapa (14–17 %). **Desde el 29-abr** la etapa ER cae a ~30 % y las visitas sin etapa a ~22 %.
  Mensual (visitas de urgencias): % con etapa ER 65,7 (ene) / 64,7 (feb) / 64,6 (mar) / 54,0 (abr) / 28,4 (may) / 29,6 (jun); % sin ninguna etapa 9,7 / 10,5 / 10,3 / 13,5 / 22,2 / 23,4.
- **El 28 y 29 de marzo son una caída de TODO el registro (no solo de nuestras etapas):** solo 14 visitas el 28-mar y 118 el 29-mar (lo normal son 400–600). Es un corte del sistema o de la extracción; excluir esos días es correcto.
- **Las personas se reducen a la mitad y repiten más:** visitas por persona y mes ~2,0 hasta marzo; 2,70 en abril; 2,99 en mayo; 3,05 en junio. Personas distintas con visita: 19.069 (mar) → 11.806 (may), −48 % frente a mayo de 2025. Las personas nuevas por mes se mantienen (4–6 mil).
- **Validación independiente de la espera de cama** (con corte de episodios de 168 h, sin pipeline): mediana 17,2 h, p75 36,6, p90 71,0, 42 % con más de 24 h (2023: 17,9 h; 2024: 15,9; 2025: 17,0; 2026: 18,7; p90 60 → 63 → 79 → 80). Coincide con el pipeline (18,6 / 37,9 / 73,9) y confirma que los peores casos empeoran.
- **Altas y laboratorios:** el último diagnóstico de cada estancia cae una mediana de 1 h antes del alta registrada (p90: 4 h), así que la hora de alta coincide con el cierre clínico; el último laboratorio, ~27 h antes (34 h en estancias de 72 h o más), compatible con laboratorios de la mañana y altas de la tarde del día siguiente. **No hay evidencia de que las altas se registren tarde**; no se corrige la ocupación.
- Repetición: cada intervalo de cama distinto aparece en 2,4 visitas (el 76 % de las estancias está en 2 o más visitas), coherente con las gemelas ya tratadas. Cobertura de laboratorios por estancia (con todas las gemelas): 69 % (pipeline 69,3 %).
**Cambios hechos el 2-nov por esta conclusión:** `src/modelo_pronostico.py` (`FIN_CONFIABLE = "2026-04-09"`, `INICIO_QUIEBRE = "2026-04-10"`) entrena el calendario y el nivel solo hasta el 9-abr y no cuenta los destinos desde el 10-abr en el error ni en la banda; `cargar_panel(limpiar=True)` deja vacíos esos días.
`pronostico_con_banda(..., desde=)` permite pronosticar desde cualquier fecha con el nivel del último dato confiable (los `dias_adelante` cuentan desde el 9-abr, así que la banda es la de ~7 meses). El dashboard (`dashboard/app.py` v4) **parte de mañana**, dibuja el real SIN limpiar con la zona 10-abr a 31-may marcada como "registro incompleto" y ya no compara con el supuesto "reciente".
Resultados con el corte nuevo (antes del 10-abr): error de llegadas con atención 7,9 % a 1–7 días y 11,5 % a un año; ingresos a cama 17,8 % a 1–7 días y 19,3 % a un año. Tablas rehechas: `evaluacion_modelo.csv`, `pronostico_futuro.csv` (365 días desde mañana), `pruebas_pronostico_resumen.csv`, `prueba_2026.csv`, `prueba_mes_conocido.csv`.
Sin rehacer (exploratorios con el corte anterior): `comparacion_banda_caida.py` y `grafico_comparacion_banda.py`, y la v1.3 `pronostico_demanda.py` (prueba de ene–abr 2026, que incluye 20 días degradados).
**Conclusión de la auditoría:** el periodo confiable de las etapas va de feb-2023 al **9-abr-2026**. Del 10-abr en adelante (visitas inflada +40 %, etapas ER y personas en caída) y, sobre todo, del 29-abr, los datos son estructuralmente distintos y no deben usarse para estimar nivel ni evaluar modelos; marzo-2026 conserva el corte del 28–29-mar (excluido).

### 4.10 Las gemelas son dos personas sin relación; se conserva la persona real (regla v4.0, 3-nov-2026)
**Hallazgo (al armar A1):** los dos registros de una estancia gemela coinciden en el sexo el 51,7 % de las veces (el azar da 51 %) y en la edad, dentro de 2 años, el 6,3 % (diferencia mediana: 25 años); nunca son la misma persona. Una es la real y la otra es un duplicado con los datos de otra persona.
Como la edad y el sexo de cada episodio salen del `person_id` de ese registro, **en las estancias gemelas (36 % de las estancias) la edad y el sexo eran de la persona equivocada** cuando se conservaba el registro equivocado.
**Cómo se identifica la persona real** (`src/auditoria_bd.py --lote 4`, consulta de solo lectura que devuelve el `person_id` de las filas de diagnósticos, laboratorios y procedimientos de las visitas con hospitalización; resultados en `datos/crudos/auditoria_bd/P01..P04`):
- Las filas de diagnósticos son de la persona propia de la visita en el 91 %; las de laboratorios, en el 56 %; las de procedimientos, en el 52 % (los procedimientos cuelgan sobre todo del OTRO registro: el 88 % de las veces no es el conservado).
- En 93 % de las estancias gemelas la persona dominante de los diagnósticos y la de los laboratorios coinciden, y siempre es una de las dos personas de las visitas. **La persona real = la dominante en diagnósticos (o, si no hay, en laboratorios).** Se identifica en el 97,6 % de las estancias gemelas.
- Con la regla de "más información" el registro conservado era el de la persona real en ~81 % (diagnósticos) o ~85 % (laboratorios) de los casos.
**Regla v4.0 (`preparar_variables.py` v2.4, sección 4b):** entre los registros de una estancia se conserva primero el de la persona real; si no se pudo identificar, el de más información clínica (4.7). La información clínica sigue fusionándose entre gemelos (los diagnósticos y laboratorios son casi todos de la persona real). Resultado: el registro conservado es el de la persona real en el 99,7 % de las gemelas identificadas.
**Efectos:** edad y sexo de las estancias corregidos; el R² de los factores de la espera sube de 14,8 % a 15,8 % ("edad y sexo": 4,1 puntos); los perfiles de A1 (`docs/perfiles_pacientes.md`) y el análisis A3 se rehicieron. **Sin cambios:** tiempos, ocupación, ingresos y camas (la estancia es la misma). Pendiente: A2 y A2b deben partir de esta tabla.
**Hallazgo abierto de A1:** las mujeres esperan cama +27 % más (IC 23 a 31 %) controlando edad, tipo de visita, franja y año, y +36 % dentro de cada grupo de diagnóstico; no es error de asignación (se mantiene tras la corrección). Hipótesis sin comprobar: camas agrupadas por sexo.


### 4.11 Exploraciones adicionales (4-nov-2026): ocupación por zona, capacidad efectiva, camas de baja actividad, fin de semana, supervivencia en urgencias
Documentos: `docs/ocupacion_por_zona.md`, `docs/capacidad_efectiva.md`, `docs/dias_cama_baja_actividad.md`, `docs/efecto_fin_de_semana.md` (scripts `src/ocupacion_por_zona.py`, `capacidad_efectiva.py`, `dias_cama_baja_actividad.py`, `efecto_fin_de_semana.py`).
- **Zona:** el exceso sobre las camas está en los adultos (88 % de las 88 camas de adultos en 2023, 101 % en 2025; 57,5 % de las horas de 2025 sobre 88); los niños (<15) se mantienen en 83–99 % de las 18 camas. El desglose pediátrica 8 / neonatal 10 no se puede comprobar con la edad. En urgencias hay siempre más pacientes que camillas (cota inferior). **La brecha de espera por sexo no se explica por la saturación del momento ni por obstetricia** (a igual saturación las mujeres esperan 2–8 h más; sin embarazo ni ginecología, 27,9 h frente a 16,0 h de los hombres): sigue como hallazgo abierto.
- **Capacidad efectiva:** la cola de pacientes esperando cama nunca es cero (media de 26) y no depende de la ocupación (correlación −0,16 a 0,01): no se puede estimar un techo. La mediana de la espera no cambió (19,5 → 17,4 h) mientras la ocupación subió ~11 camas; solo el p90 empeora.
- **Camas de baja actividad:** ~6 camas (6–8 % de los días-cama), sin crecer; el aumento de ocupación es de pacientes con actividad clínica. Una recomendación de «días evitables» no tiene respaldo fuerte.
- **Supervivencia en urgencias (`docs/supervivencia_urgencias.md`):** quedarse con los episodios con hora de salida subestima la duración: mediana 9,6 h y p90 45 h frente a 11,2 h y 81 h con Kaplan-Meier (71 h ponderado). El 50 % de los episodios no tiene ningún tiempo en urgencias y no hay método que lo recupere (cotas de 0 a 24 h de mediana). Tener información depende de laboratorios, tipo de visita y edad (AUC 0,70).
- **Fin de semana:** altas por 100 camas −27 % el domingo y −34 % en festivos; la estancia de quien entra a cama en sábado es +12 %; efecto estimado de ~1–2 camas equivalentes (cota alta); las esperas largas no mejoran en fin de semana.

### 4.12 Corrección del «hueco sin etapa» antes de la cama (7-nov-2026)
**Qué se creía:** que el 21 % de las horas de espera de cama (18–24 % de los hospitalizados) era tiempo sin ninguna etapa registrada justo antes de la hospitalización.
**Qué era:** un artefacto de las estancias gemelas. El hueco se calcula como (inicio de cama de la estancia) − (fin de la última etapa de urgencias del registro). En el registro de la
**persona real** (el conservado, v4.0) la etapa de urgencias termina en el mismo instante en que empieza la cama (hueco de 1 minuto o menos en el 97,7 % de las estancias). En los registros
gemelos de la **otra** persona el hueco existe en el 62,5 %, porque la hospitalización replicada cae sobre una visita de urgencias ajena que terminó antes.
**Dónde estaba el error:** (1) `preparar_variables.py` copiaba el hueco del registro de id menor (la otra persona) al conservado en el 16,5 % de las estancias; (2) `construir_segmentos.py`
tomaba la estancia conservada de `episodios.csv` (id menor) y no de `tabla_episodios.parquet` (persona real). Corregidos: `preparar_variables.py` v2.6 y `construir_segmentos.py` v1.3.
**Medida correcta (periodo confiable, 22.819 estancias):** hueco > 1 h en el **1,7 %** de las estancias y **1,1 %** de las horas de espera; urgencias antes de la cama, 98,9 %. En todo el periodo
(con los meses desde el 10-abr-2026) es 3,0 % de las horas; desde el 10-abr sube a 31 % de las estancias porque el registro de etapas está degradado (4.9).
**Qué NO cambia:** la espera de cama (mediana 18,6 h, p90 73,9 h): es la misma con el registro propio o con el de la estancia (17,6 y 17,7 h en el chequeo con todos los registros). El exceso medio
de espera, 17,1 h (2023) a 23,7 h (2026), cambia en una décima. Urgencias antes de la cama sigue liderando todas las referencias y cortes.
**Qué cambia:** el cuello de botella es casi por completo **urgencias antes de que se asigne la cama** (98 %), no una mezcla con tiempo sin registro; las preguntas 5 y 11 al HUN pierden sentido.
Respaldo de los resultados anteriores en `resultados/respaldo_antes_hueco/` y `datos/procesados/respaldo_antes_hueco/` (no se suben a git).

### 4.13 Cierre de C2/C4 y exploraciones A8 6, 8 y 10 (8-nov-2026)
Documentos: `docs/c4_reingresos_huecos_llegadas.md`, `docs/quincenas_y_datos_externos.md`, `docs/espera_con_labs_y_severidad.md` (scripts `src/c4_reingresos_huecos_llegadas.py`, `prueba_quincenas.py`, `espera_con_labs.py`, `severidad_labs.py`; consultas `sql/espera_labs_y_texto.sql`, `sql/severidad_labs_6h.sql`).
- **C2:** la base da 566.004 filas de `dx_por_visita` y 662.783 de `proc_por_visita`, con las mismas sumas que los CSV (38.636.063 y 47.042.032) y 1 visita vacía en cada una: `sql/exportaciones_base.sql` queda verificado.
- **Reingresos depurados** (sin registros gemelos, sin traslapes): **5,3 % en 72 h y 14,1 % en 30 días** (la columna del pipeline da 6,6 % y 15,4 %, que cuenta traslapes). Hueco TU a TU: 2,6 % de las horas de TU, sin efecto.
- **Réplicas de llegadas: 4,3 %** (12,2 % de los episodios con cama). Proporción estable (correlación 0,998 con la serie sin réplicas): **no se deduplican las llegadas**; al citar un nivel absoluto, decir «~4 % menos, cota inferior».
- **Quincenas** no mejoran el pronóstico (±0,15 puntos de WAPE). Dengue y lluvia: sin datos abiertos de 2023–2026, descartados.
- **Laboratorios en la espera:** solo el 38 % de las estancias tiene alguna toma durante la espera, y las tomas por día bajan de 14,8 (espera < 6 h) a 2,0 (> 72 h). No separa atención de espera pura. **(Corregido el 10-nov: el 38 % salía de un cruce que dejaba fuera los laboratorios que cuelgan de visitas copia. Con las copias llevadas a su visita raíz y filtrando por la persona real, ~70 % de las estancias tiene alguna toma en la espera: `docs/caracterizacion_tu.md`.)**
- **Severidad desde el texto de los laboratorios (primeras 6 h):** la hospitalización va de 20 % (0 banderas) a 57 % (3 o más); AUC de 0,58 a 0,65 entre quienes tienen laboratorio. Sube la estancia (+29 % con 3 o más banderas). La suma **no cambia la espera de cama** porque junta efectos opuestos: troponina alta −41 %, lactato y BUN altos ~−18 % (cama antes), PCR alta +13 %; las banderas por separado mejoran la predicción del tiempo restante (R² de 12 % a 17 % a las 6 h de espera).

## 5. Decisiones de método (ya tomadas, no reabrir sin un motivo nuevo)

1. Unidad de análisis: **episodio** = atención continua de un paciente dentro de una visita
   (corte por hueco > 168 h sin etapas).
2. Etapas usadas: ER, TU, HOSP. AMB fuera. Etapas abiertas fuera.
3. Ruta = secuencia de bloques (`ER > TU > HOSP`). `ruta_simple` quita la ER inicial (dura minutos).
   `hospitalizado` = el episodio tiene HOSP.
4. **Estado de cada episodio:**
   - `medida`: alguna etapa TU o HOSP con fin > inicio Y la última etapa TU/HOSP también cerrada → duración confiable.
   - `minimo_conocido` (v3.6): tiene etapas con tiempo pero la última no tiene fin → la duración es solo un mínimo.
   - `minimo_dx`: sin fin real, con un diagnóstico que da una duración mínima (no usar para tiempos).
   - `sin_duracion`: sin fin, pero con diagnósticos o procedimientos.
   - `sin_actividad`: sin fin y sin nada clínico.
   No se descartan los cortos: todos cuentan para llegadas y cobertura; solo los `medida` entran a tiempos.
5. **Atípicos:** sin IQR (marcaba demasiados casos por la asimetría). Los errores se quitan con reglas
   (copias, etapas abiertas, corte de episodios, tope MAX_H = 2.160 h = 90 días). Se reportan mediana,
   p25, p75, p90 y media recortada 5–95 %.
6. **Espera de cama** = inicio del episodio → inicio de la primera HOSP. Incluye el "hueco sin etapa"
   justo antes de la HOSP (que, medido en el registro de la persona real, es ~1 % de las horas: ver 4.12). La etapa previa a la HOSP es TU en el 99,9 % de los casos y el
   bloque TU termina en el mismo instante en que empieza la HOSP, por eso "desde el fin de la etapa previa" daría 0 y no sirve como espera.
7. Diagnóstico principal = primer diagnóstico con concepto ≠ 0 por `condition_start_datetime`.
8. Ocupación al llegar = cuántos bloques HOSP (o TU con duración) están abiertos en ese momento,
   calculada con las mismas etapas. Poco confiable fuera de feb-2023 a may-2026.
9. Reingreso: llegada ≤ 72 h / ≤ 30 días tras un episodio anterior **con atención** (no cuenta un registro
   solo-ER sin actividad).
10. **Estancia única (22-oct):** en análisis de espera de cama, camas e ingresos, cada estancia en cama (mismo `ini_hosp`
    y `fin_hosp`) se cuenta una vez. Motivo y efecto en la sección 4.6.
11. **Cuello de botella (21-oct):** segmento de espera con exceso sobre una referencia de "cuando funciona bien", impacto
    alto (volumen × retraso) que se agrava con la carga. Definición completa y fases en `docs/plan_de_accion.md`, sección 0.

---

## 6. Resultados actuales (corrida v3, 20-oct; pueden cambiar con v3.3)

> **Aviso (22-oct):** las cifras de espera de cama, ingresos por día y ocupación de esta sección y de "Pruebas de modelos"
> cuentan dos veces las estancias gemelas (sección 4.6) y son históricas (corrida v3, 20-oct). Valores vigentes (v3.8, 4.8): espera de cama mediana 18,6 h, ~20 ingresos/día,
> 94 / 101 / 105 camas ocupadas en 2023 / 2024 / 2025.

- Etapas: 3.281.613 → quitando AMB (1.539.340) y abiertas (2.053) quedan 1.740.220.
- Visitas que quedan sin copias: 1.193.956; con alguna etapa: 338.925. **Episodios: 295.790** (164.954 pacientes).
- Estados: medida 42,0 % · minimo_dx 10,8 % · sin_duracion 21,4 % · sin_actividad 25,8 %.
- Cobertura por ruta: TU 223.220 (44,9 % medida) · ER 48.489 (0 % medida, 83,5 % sin actividad) ·
  TU > HOSP 23.116 (100 %) · HOSP 952 (99,6 %).

| Ruta | n medidos | Mediana | p75 | p90 |
|---|---|---|---|---|
| TU (alta desde urgencias) | 100.171 | 8,5 h | 15,9 h | 41,8 h |
| TU > HOSP total | 23.111 | 104 h | 190 h | 322 h |
| — TU antes de la cama | 23.111 | 11,3 h | 29,3 h | 54,5 h |
| — HOSP | 23.111 | 71,4 h | 144 h | 279 h |
| HOSP directo | 948 | 42,8 h | 91,5 h | 196 h |
| **Espera de cama** | 23.207 | **23,1 h** | 42,3 h | 76,1 h |

- Espera de cama: 48,7 % > 24 h, 83,4 % > 6 h; 35 % tiene > 1 h sin ninguna etapa justo antes de la HOSP.
  Por tipo de visita: urgencias 25,2 h, treatment urgency 13,0 h, ambulatorio 11,2 h.
- Visitas tipo "Treatment urgency" no hospitalizadas: mediana 43 h (frente a 8,3 h en urgencias) → otro servicio.
- Extremos: máximo 2.867,8 h (id de visita omitido por privacidad); 3 episodios > 90 días; 370 TU > HOSP > 30 días.
- Llegadas: mediana 229 episodios/día (p10 168, p90 289). Pico 9–11 am (~19/h), mínimo 3–4 am.
  Lunes el día más cargado; fin de semana ~30 % menos. A las 19 h baja (posible cambio de turno).
- Pacientes: 54 % mujeres; 22 % menores de 15 años.
- Factores de espera de cama (asociaciones, no causas):
  - **Hora de llegada:** madrugada 16,6 h (31,8 % > 24 h) · mañana 20,4 h · **tarde 27,1 h (57 % > 24 h)** · noche 22,2 h.
  - Congestión de urgencias (llegadas de las 6 h previas) mueve la mediana 11,7 h.
  - **Ocupación de camas por quintil: plana (22–24 h).** Ojo: nuestra "ocupación" solo cuenta pacientes de esta
    base (59–117), probablemente no es el total del hospital.
  - Laboratorios totales parecían el factor nº 1, pero es causalidad inversa → usar `n_lab_6h`.
- Hipótesis principal para recomendaciones: las altas se dan tarde y quien llega en la tarde espera cama
  hasta el día siguiente. Se prueba con la sección 7b de `preparar_variables.py` (hora de alta frente a hora
  de ingreso a cama).
- Reingresos (v1, sin depurar): 6,9 % en 72 h, 15,9 % en 30 días. **Depurados el 8-nov (4.13): 5,3 % y 14,1 %.**

---

### Pruebas de modelos (21-oct) — por qué cambió el plan de modelos
- Predecir `espera_mas_24h` solo con variables al llegar (train 2023-02/2025-06, test 2026-01/06): AUC 0,60 (logística) y
  0,61 (árboles); con dx y laboratorios (no permitido) 0,64. Solo hora de llegada: 0,56. No sirve como alerta individual.
- Espera mediana diaria frente a altas e ingresos del día o de los días previos: correlación de Spearman entre −0,02 y −0,10;
  R² negativo en 2026. La hipótesis de las altas tardías no se sostiene a nivel diario.
- Estancia en cama por paciente: R² ≈ 0,00–0,02 aun con dx provisional y laboratorios de 6 h; error igual a decir la mediana (47 h).
- Ley de Little: 27,7 ingresos/día × 5,2 días de estancia media = 144 camas; ocupación observada media 145. El modelo
  de capacidad (ingresos × distribución de estancias) es coherente con los datos. **(22-oct: ambas cifras estaban
  infladas por las estancias gemelas; con estancias únicas son ~22 ingresos/día y ~113 camas. Ver 4.6.)**
- Solo ~13 % de los episodios atendidos (sin solo-ER) termina hospitalizado: un modelo "al llegar" que use solo hospitalizados
  no es aplicable a la entrada.
- Decisión: Modelo A ampliado (llegadas e ingresos), modelo de camas y simulación, días atípicos y regresión logística
  solo como análisis explicativo. Detalle en `docs/fichas_de_tareas.md`.

---

## 6b. Cuellos de botella: resultados (cifras actualizadas al 3-nov con la regla de estancia única v3.8 y la persona real v4.0; detalle en 4.8 y `docs/HALLAZGOS.md` 4; fases 2 a 5 de `docs/plan_de_accion.md`)

- **Segmentos candidatos** (25.373 estancias con espera): espera de cama (mediana 18,6 h, p90 73,9 h), urgencias antes de la cama
  (~98 % de las horas de espera) y hueco sin etapa antes de la cama (**corregido el 7-nov, ver 4.12**: solo el 1,7 % de las estancias lo tiene en el periodo confiable y es el 1,1 % de las horas;
  antes decíamos 21 %). La estancia en cama es servicio (va a la simulación) y urgencias sin hospitalizar solo
  es descriptiva (38 % medida, sesgada por tipo de visita, edad y año).
- **Ranking:** el 64 % de las horas de espera de cama queda por encima de la referencia de carga baja (518 mil de 812 mil
  horas-paciente; cifra de HALLAZGOS 4.2). Urgencias antes de la cama lidera con las 4 referencias y los 3 cortes de episodio (72, 168, 336 h);
  el peso del hueco (corregido el 7-nov) es de 1,9 % con el corte de 72 h, 3,0 % con 168 h y 5,4 % con 336 h (incluye los meses posteriores al 9-abr-2026, donde el hueco sube a 31 % por el registro degradado).
- **Tendencia:** exceso medio por episodio de 17,3 h (2023) a 23,8 h (2026), +38 %; el p90 sube de 61,6 a 81,9 h; la mediana
  se queda en 17–20 h. Empeoran los peores casos.
- **Carga (Fase 4):** la mediana de espera sube de 14,2 h (decil con menos llegadas en 6 h) a 25,9 h (decil con más), +2,5 %
  por decil controlando edad, año y hora. La ocupación pesa poco y las llegadas de 24 h casi nada.
- **Hora de llegada:** mediana de 12–15 h de madrugada y ~25 h al llegar entre las 13 y las 16 h (salto a las 13:00). La carga
  explica unos dos quintos del efecto de la tarde; el resto no.
- **Altas tardías (Fase 5, hipótesis sostenida descriptivamente, 4 de 4 criterios):** el 62,7 % de las altas ocurre entre las
  14:00 y las 18:59 y solo el 14 % antes del mediodía (estable 13–16 % por año). La cama se asigna con mediana a las 17–18 h
  sin importar la hora de llegada (7 a 21 h). Quien llega a las 8 h recibe cama al día siguiente en el 50 %; a las 16 h, en el
  72 %. Los ingresos a cama siguen a las altas en la misma hora (correlación cruzada 0,17 sin el patrón horario). La prueba a nivel
  diario del 21-oct fallaba porque el mecanismo es dentro del día. Asociación, no causa: el efecto de adelantar altas se
  estima en la simulación de camas (Fase 6).
- **Factores de la espera** (modelo sobre log(espera+1), R² = 16,0 % tras la regla de la persona real (4.10) y el mapeo final, rehecho el 8-nov: el 84 % de la variación no se explica con lo observado):
  diagnóstico 7,2 puntos de R² (ojo: dato administrativo, registrado tarde y que puede venir del registro gemelo), edad y sexo 4,1, tipo de
  visita 2,0 (quien entra por urgencias espera más: ambulatorio −31 %, treatment urgency −39 %), hora 0,6,
  año y carga 0,1 cada uno, laboratorios de 6 h 0,2, calendario ~0.
- **Ocupación y escenario de altas (Fase 6, `simulacion_altas.py`):**
  - La ocupación sube de 94 camas (2023) a 105 (2025) y 103 (ene–9 abr 2026); es **por la estancia** (media de 4,57 a 5,31
    días, +16 %), no por más ingresos (20,6 → 19,8 por día). Con Little: volver a la estancia de 2023
    liberaría ~15 camas; bajar la estancia 5 % ~5; subir los ingresos 10 % añadiría ~10.
  - El orden de llegada casi no predice el orden de cama (53 % de pares consecutivos en orden, azar 50 %): una fila FIFO no
    está respaldada por los datos y no se simula.
  - Con el 30 % de las altas de la tarde pasando a las 9–12 h
    quedan hasta 5,1 camas libres adicionales a las 12 h (~34 horas-cama por día; con ~103 camas ocupadas a esa hora).
  - Traducido a espera, **como máximo ~8 % del exceso de espera (451 horas-paciente por día)** y una estimación de ~3 %
    (cada alta extra se vuelve a ocupar con ~0,35 ingresos en 6 h). Adelantar el 100 % de las altas de la tarde: máximo 27 %.
    Adelantar altas ayuda pero no resuelve: el 83 % de las horas de espera viene de esperas de más de 24 h y el 57 % de esperas
    de más de 48 h (el 19 % de los pacientes), y unas horas menos no deshacen esperas de varios días.
  - Supuestos: el alta de los demás no cambia y la capacidad total (camas) se desconoce; es una cota, no una predicción.
- **Tendencia de la espera, con la caída de 2026 aparte:** exceso medio de espera por episodio 17,3 h (2023), 18,6 (2024),
  23,8 (2025) y 23,8 (ene–abr 2026), así que el empeoramiento (+38 %) se ve en periodos completos. Desde el 10-abr-2026 el registro está degradado (4.9), así que lo que muestra la espera en esos meses no es confiable.
- **Pronóstico de demanda (versión previa al 2-nov; el modelo vigente es `src/modelo_pronostico.py`, con error 7,9 % a 1–7 días y 11,5 % a un año en llegadas con atención, ver 4.9; lo que sigue es `pronostico_demanda.py` v1.3 y se conserva como referencia; entrenado hasta 2025-12, probado en ene–abr 2026, método
  elegido con la validación de 2025-07 a 2025-12 sin mirar la prueba):**
  - **Llegadas por día:** regresión de Poisson con día de la semana, festivos (entre semana y fin de semana por separado), semana
    santa, 24/31 de diciembre y 25 de diciembre/1 de enero por separado, **Carnaval de Barranquilla** (~16 % menos llegadas),
    nivel de los últimos 28 días y la "sorpresa" del último día conocido. Error relativo **7,5 % a 1 día** (MAE 18 personas por día) y
    8,8 % a 7 días, contra 9,9 % y 10,5 % de la mejor referencia (día de la semana × nivel reciente). Por hora: 26,5 % frente a 28,8 %.
    El fin de año se confirma en la validación de 2025; el Carnaval se descubrió en los residuos de 2024–2025 (ver
    `docs/dias_atipicos.md`) y 2026 solo lo confirma. Se asume que el HUN está en Barranquilla.
  - **Ingresos a cama por día:** ningún método mejora a "día de la semana × nivel reciente" (error ~22,5–23,3 % con todos; la
    varianza de los ingresos es igual a su media, es ruido de conteo y su piso teórico es ~18 %). **Por semana el error baja a 9,5 %**
    (frente a 14,7 % de repetir la semana anterior, 16 semanas): para planear camas usar el pronóstico semanal. Llegadas por
    semana: 6,1 %, sin ventaja sobre repetir la semana anterior (5,2 %).
  - **Bandas del 80 %** con los errores de los 60 días conocidos más recientes: cobertura 79 % (1 d) y 81 % (7 d) en llegadas; en
    ingresos solo ~71 % (siguen angostas).
  - **Alerta de día congestionado un día antes** (llegadas > percentil 90 del mismo día de la semana en 12 semanas; clasificador
    logístico, corte elegido en validación): AUC 0,79 a 1 día y 0,74 a 7 días (0,61 la referencia). A 1 día: 27 alertas, 10
    aciertos (precisión 37 %, detección 56 %, 17 falsas alarmas); a 7 días: 59 alertas, 12 aciertos (precisión 20 %, detección 67 %,
    47 falsas alarmas). Es un aviso débil; la alerta a media jornada (A, abajo) es mucho mejor.
  - **Probado y descartado:** nivel con mediana de 28 días (empeora) y cambiar la ventana del nivel (casi no cambia).
    **No probado:** modelar los ingresos como fracción de las llegadas pronosticadas.
  - **Limitaciones:** en mayo 2026 el modelo sobrestima las llegadas 11 % (a 1 día) y 33 % (a 7 días) y los ingresos ~30 % por la
    caída no anticipada (la banda a 7 días cubre solo 58 % en mayo); no anticipa brotes, cortes de sistema (28-mar-2026: 88
    llegadas y 1 ingreso a cama) ni cambios de registro. Las llegadas incluyen ≥ 4 % de réplicas (4.6).
- **Días atípicos (ficha D.2, `dias_atipicos.py`, `docs/dias_atipicos.md`):** con |z| > 3 frente al pronóstico: 14 días de llegadas,
  9 de ingresos y 7 de espera (3 esperados por azar). Casi todos son de menos actividad. Con el calendario ya modelado, solo 3 de 14
  tienen causa de calendario. Los dos más extremos (sábados 28-mar-2026 y 15-jun-2024) tienen caídas simultáneas de llegadas e
  ingresos: parecen cortes de registro o sistema, hipótesis sin comprobar. **Ningún día tuvo espera más alta de lo esperado**: el
  problema de la espera es crónico y de cola larga, no de días puntuales.
- **Alertas (Fase 7, `alertas.py`; cortes elegidos con 2025-07 a 2025-12, prueba en ene–abr 2026 reproduciendo los días):**
  - **A. Día congestionado en tiempo real** (llegadas del día > percentil 90 del mismo día de la semana en 12 semanas): estimar el
    total del día con lo que ya llegó, mezclado con el pronóstico. Con el corte elegido en validación, **a las 12 h** AUC 0,94,
    25 alertas (0,25 por día), 13 aciertos: precisión 52 %, detección 87 %; a las 15 h: 12 alertas, 9 aciertos (75 % y 60 %);
    a las 9 h: 7 alertas, 4 aciertos (57 % y 27 %). **Un día antes** (solo pronóstico): AUC 0,61, 7 alertas, 3 aciertos (43 % y 20 %).
    Avisa a media jornada, no con un día de margen. Solo 15 días congestionados en la prueba (18 en la validación): las cifras se mueven. *(Recalculado el 8-nov con la regla v3.8.)*
  - **B. Camas a 24 h desde las 12 h:** la proyección (camas ahora − altas esperadas + ingresos esperados) **no mejora a la
    persistencia** ("lo mismo que ahora"): error 3,7 contra 3,2 camas (prueba 2026). Las altas esperadas tienen sesgo de +2,0 camas (20,1 esperadas
    contra 18,1 reales) y correlación de 0,10 con las reales (posible causa sin comprobar: las estancias del entrenamiento son más
    cortas que las de 2026). La alerta de "ocupación alta" (≥ percentil 80 de las 12 h del entrenamiento: 107 camas en validación y 109 en prueba; 25 de los
    99 días de la prueba) funciona mejor con la persistencia: AUC 0,82, precisión 48 %, detección 76 %, 0,4 alertas por día (la proyección: AUC 0,78, 40 % y 84 %, 0,5 por día). Se recomienda
    la persistencia y reportar las altas esperadas solo como orden de magnitud (~20 camas se liberan por día).
  - **C. Paciente sin cama** (solo los que luego se hospitalizan; cota inferior de la carga real): alerta a las 24 h, 8,6 por día,
    24 % termina esperando más de 72 h; a las 36 h, 5,3 por día, 39 %; **a las 48 h, 4,0 por día, 52 %, con 24 h de margen**; a las 60 h,
    2,6 por día, 80 %, con 12 h de margen. Más anticipación = más alertas y menos precisión.
  - **Carga total con el diseño recomendado** (A a las 12 h, B persistencia, C a las 48 h): ~4,6 alertas por día, casi todas del
    tipo C. La ocupación cae de ~115 camas a mediados de abril 2026 a 87 el 29-abr: coincide con la caída de datos de
    abril–mayo (pregunta 14) y no se interpreta como un cambio real.
- Scripts: `construir_segmentos.py`, `ranking_cuellos.py`, `dependencia_carga.py`, `altas_y_factores.py`, `simulacion_altas.py`,
  `pronostico_demanda.py`, `alertas.py`, `dias_atipicos.py`.

---

## 7. Scripts y archivos de la carpeta

Orden: `src/analisis_etapas.py` → `src/preparar_variables.py` → `src/exportar_para_equipo.py` (tablas para el drive).
Cuellos de botella (22-oct): `sql/consultas_cuellos_botella.sql` (Q0–Q4, Q3b; se guardan en `datos/crudos/`) →
`src/construir_segmentos.py` (episodios de Q3 → `segmentos.csv`, inventario, sesgo de medición) →
`src/ranking_cuellos.py` (referencias, exceso, ranking y gráfico). Q3 es una versión simplificada de la limpieza
(337 mil episodios, casi igual al pipeline); `SUFIJO=_u72` o `_u336` repite todo con otro corte de episodios. (`archivo/Revision_inicial.py` es una versión vieja: no usar.)

### CSV de entrada (exportados de DBeaver)
| Archivo | Columnas | Origen |
|---|---|---|
| visit_detail.csv | visit_detail_id, visit_occurrence_id, visit_detail_concept_id, visit_detail_start_datetime, visit_detail_end_datetime | tabla completa (3,28 M) |
| visit_occurrence.csv | visit_occurrence_id, person_id, visit_concept_id | tabla completa (1,7 M) |
| dx_por_visita.csv | visit_occurrence_id, n_dx, dx_min, dx_max | conteo y primera/última hora de diagnóstico por visita (566 mil) |
| proc_por_visita.csv | visit_occurrence_id, n_proc | conteo por visita |
| person.csv | person_id, year_of_birth, sexo | consulta 1 de consultas_semana1.sql |
| diagnosticos_por_visita.csv | visit_occurrence_id, dx_concept_id, dx_nombre, dx_vocabulario, n_dx_distintos | consulta 2 (326 mil, solo concepto ≠ 0) |
| procedimientos_por_visita.csv | visit_occurrence_id, n_proc_distintos | consulta 3 (opcional) |
| laboratorios_por_visita.csv | visit_occurrence_id, n_lab, n_lab_distintos, n_lab_6h, n_lab_antes_hosp | consulta 4 v2 (la vieja solo trae n_lab y n_lab_distintos) |

### analisis_etapas.py (v3.6)
Secciones: 1 carga · 2 limpieza (AMB, abiertas) · 3 copias · 4 huecos y episodios · 5 etapas repetidas en otra
visita · 6 bloques y episodios · 7 estado · 8 cobertura · 9 tiempos · 10 espera de cama · 11 extremos ·
12 estimación por diagnósticos.
Salidas: episodios.csv, bloques.csv, copias.csv (copia → original, con raiz_id), espera_cama.csv,
resumen_por_ruta.csv, resumen_por_etapa.csv, cobertura_por_ruta.csv, cobertura_por_tipo_visita.csv,
resultados_finales.xlsx, boxplot_rutas.png, cobertura_por_ruta.png.
Parámetro `MODO_COPIAS` ("importar" por defecto; "cerrar" solo toma el fin de etapas iguales sin cierre).
Estructura: scripts en `src/`, consultas en `sql/`, CSV de la base en `datos/crudos/`, tablas generadas en
`datos/procesados/` y `resultados/` (todo eso NO se sube a git; ver `.gitignore`). Correr: `python3 src/analisis_etapas.py`
y luego `python3 src/preparar_variables.py`.

### preparar_variables.py (v2)
Agrega por episodio: calendario (hora, día, festivo de Colombia con `holidays`), edad, sexo, diagnóstico
principal y su grupo, complejidad (diagnósticos, procedimientos, laboratorios), ocupación al llegar,
llegadas de las 6/24 h previas, reingresos. Pasa a la original lo colgado de copias (usa copias.csv).
Salidas: tabla_episodios.csv/.parquet, serie_horaria.csv, serie_diaria.csv, mapa_calor_llegadas.csv,
factores_espera_cama.csv, factores_duracion_tu.csv, altas_ingresos_por_hora.csv, dx_frecuencias.csv,
variables_semana1.xlsx y gráficos.
Pendiente: `mapeo_dx.csv` (columnas dx_nombre, categoria_dx) a partir de dx_frecuencias.csv.

---

## 8. Preguntas enviadas al HUN (no inventar respuestas)

**Estado (23-oct): el correo se envió y no hubo respuesta; el HUN abrirá una sesión de preguntas.** Las preguntas priorizadas y el espacio para
anotar las respuestas están en **`docs/hun/sesion_de_preguntas.md`**. Mientras tanto ningún paso del plan depende de ellas: cada incógnita (número
de camas, meta de tiempos, causa de la caída de llegadas desde abril, persona real en las estancias gemelas) se trabaja con
escenarios y supuestos escritos y se declara como limitación en el documento final.

1. ¿Las visitas con id = otra + 1.746.478…1.746.489 o + 1.757.764 son duplicados de extracción/anonimización?
   ¿Cuál es el paciente correcto si el person_id difiere? (se enviaron ejemplos al HUN; ids omitidos del repositorio)
2. Etapas 3045729 con inicio = fin (ejemplo enviado al HUN; id omitido): ¿falta la hora de salida? ¿hay otra fecha de alta?
3. Visitas solo con 9203 y sin nada clínico (ejemplo enviado al HUN; id omitido): ¿se fueron sin atención?
4. ¿Qué proceso es 9203 y cuál 3045729? ¿El paso a 9201 es la asignación de cama o la llegada al piso?
5. (Casi disuelta el 7-nov, ver 4.12: el hueco era un artefacto de las estancias duplicadas; en el registro de la persona real solo el 1,7 % tiene > 1 h sin etapa.) > 1 h sin etapa antes de 9201 en el 35 %: ¿dónde está el paciente? ¿se registra la asignación de cama?
6. Fines con milisegundos en julio 2026: ¿pacientes aún hospitalizados al extraer?
7. ¿Qué significa `visit_concept_id`? (ambulatorias con hospitalización; 3045729 con 43 h de mediana)
8. Columnas del instructivo ausentes o vacías: ¿habrá versión actualizada?
9. Número de camas y cubículos de urgencias por año (para ocupación en %).
10. Rúbrica de evaluación, repo público, Power BI con datos agregados.
11. (Casi disuelta el 7-nov: era ~1,7 % y no ~1 de cada 4, ver 4.12.) ~1 de cada 4 hospitalizados tiene tiempo sin ninguna etapa antes de la cama (mediana 19,7 h entre ellos): ¿dónde está
    el paciente y se registra la asignación de cama? (ampliación de la 5)
12. Hay episodios de varios días en urgencias (TU) sin hospitalización registrada (ej. una visita de enero de 2023 con 177 h): ¿esperan
    cama sin que se registre, observación prolongada o error?
13. Estancias gemelas (4.6): ¿cuál es la persona real cuando la misma estancia aparece en dos pacientes? (ampliación de la 1)
14. (Respondida por la auditoría del 2-nov: es el registro de etapas, no la demanda; ver 4.9.) Desde abril de 2026 las llegadas bajan ~25–35 % (y los ingresos ~20–30 %) y los laboratorios caen a la mitad en may–jun:
    ¿cambió el volumen real (cierre de servicio, cambio de triage) o el registro, o la extracción está incompleta en los
    últimos meses?

---

## 9. Plan de acción y estado (actualizado 23-oct-2026)

| Frente | Estado | Dónde |
|---|---|---|
| Limpieza, copias y episodios (v3.7, con estancias gemelas) | **Hecho** | `src/analisis_etapas.py`, 4.1 y 4.6 |
| Componente 1: flujo del paciente | **Hecho** | `docs/HALLAZGOS.md` 3 |
| Componente 2: cuellos de botella (fases 0 a 5) | **Hecho** | 6b, `docs/plan_de_accion.md` |
| Componente 3: pronóstico, alertas, simulación de camas, días atípicos | **Hecho** | 6b, `docs/dias_atipicos.md` |
| Componente 4: recomendaciones | **Borrador hecho**; Persona 3 debe revisar las fuentes originales | `docs/recomendaciones.md` |
| **Reparto completo de lo que falta** | Ver **`docs/pendientes_y_reparto.md`** (Daniela: perfiles, factores de la estancia, `mapeo_dx.csv`; Anthony: explicar retrasos y Monte Carlo de camas; Samuel: Power BI y recomendaciones) | `docs/pendientes_y_reparto.md` |
| Perfiles de pacientes (A1) | **Hecha** (`docs/perfiles_pacientes.md`) | A1 |
| Factores de la estancia | **Hecha** (`docs/factores_estancia.md`) | A2 |
| Explicar mejor los retrasos | **Hecho el 8-nov-2026** (AUC 0,68-0,70, techo bajo confirmado con y sin "trampa" de diagnóstico; no sirve para alertar individualmente) | A4, `docs/modelo_espera.md` |
| Simulación Monte Carlo de camas | **Hecho el 9-nov-2026, bootstrap suavizado el 10-nov** (backtest con 78,8 % de cobertura; probabilidad de saturar 106 camas 65,4 % en el horizonte de 180 días, concentrada en adultos: 70,6 % contra 34,5 % en niños; escenario de −5 % estancia casi iguala al de +10 % ingresos en efecto sobre la ocupación) | A5, `docs/modelo_camas.md`, `docs/simulacion.md` |
| Qué comparten las estancias que se disparan (idea de Anthony) | **Hecha** (`docs/estancias_disparadas.md`) | A2b |
| Sistema repetible de diagnóstico de cuellos de botella | **Hecho** (`src/diagnostico_cuello_botella.py`, `docs/diagnostico_cuello_botella.md`); falta sumarle Monte Carlo (A5) | A7 |
| Dashboard de Power BI (**va de último**, datos parciales; guía para su Claude en `powerbi/CLAUDE.md`) y verificar fuentes de las recomendaciones | B2 (verificar fuentes de las recomendaciones) **hecha** (PR #1 de Samuel, mergeado el 8-nov-2026; falta recalcular las ~11 horas-paciente de R6 y la alerta de ocupación de R3). B1 (dashboard) pendiente — **adelanto del 10-nov (Anthony):** las 4 páginas que ya existían (pronóstico, A6, A5, perfiles y picos) se unieron en un solo proceso Dash (`dashboard/main.py`, puerto 8050, patrón multipágina `use_pages=True`, cada página en `dashboard/pages/`); las 5 apps sueltas anteriores se retiraron. Es la base técnica para que Samuel construya encima la estructura completa de `docs/estructura_dashboard.md` (0 a 5, con subpáginas), que sigue siendo B1 | B1 y B2 |
| `mapeo_dx.csv` (grupos de diagnóstico) y tiempos por diagnóstico | **Hecho como borrador** (falta validación clínica); `docs/diagnosticos_y_tiempos.md` | A3 |
| Estimar tiempos de atención (componente 3) | **Hecho el 7-nov** (`docs/estimador_tiempos.md`): la espera es individual; modelo de tiempo restante con historial y recorrido en urgencias, reentrenado cada mes con más peso en lo reciente (8,9 % de mejora al llegar, 11,3 % a las 3 h y 11,7 % a las 6 h, con la persona real de P02 y P03 y, desde las 6 h, las banderas de laboratorio de Daniela; el modelo de consulta se entrena con todos los datos hasta el 9-abr-2026); salidas de uso diario (ventanas del día, censo para la reunión de camas, alerta a las 12 h) en `src/utilidad_estimador.py` y página `dashboard/estimador.py`; función de consulta `src/estimador_tiempo_restante.py` | A6 |
| README y reproducibilidad desde cero | README y `requirements.txt` hechos; falta probar desde cero con alguien que no tiene los datos | `README.md` |
| Documento final y presentación | Pendiente (plazo: fin de noviembre de 2026) | — |
| Sesión de preguntas con el HUN | **Por agendar**: el correo no tuvo respuesta; preguntas listas | `docs/hun/sesion_de_preguntas.md`, sección 8 |

Reglas para los modelos:
- Un modelo "al llegar" solo puede usar lo que se sabe al llegar: hora, día, festivo, edad, sexo,
  congestión y ocupación. **No** diagnósticos ni laboratorios posteriores.
- No modelar la duración de los pacientes de alta desde urgencias (solo ~38 % tiene hora de fin → sesgo).
  Sí la espera de cama (100 % medida en hospitalizados) y las llegadas (100 % de los episodios).
- Validación temporal (entrenar con pasado, probar con futuro), nunca aleatoria.

Limitaciones a declarar en el documento: copias (30 %) y estancias gemelas (41 % de los hospitalizados), etapas TU sin hora de fin
(36–42 %), diagnósticos tardíos y sin jerarquía, número de camas desconocido, procedimientos sin fecha, sin signos vitales, registro de etapas degradado
desde el 10 de abril de 2026 (causa sin explicar), y que casi todo son asociaciones.

Documento del equipo (Claude Docs): "Exploración BD — Data Challenge HUN 2026".**Revisión final de la ocupación (2-nov-2026, tarde):**
- **El doble conteo de una misma persona es 0,2 camas, no 2,2** (corrijo lo dicho antes: las 19.375 horas del lote 1 de la auditoría incluían intervalos solapados *dentro* de una misma estancia). Entre las 25.777 estancias únicas solo 96 se solapan con otra de la misma persona (4.556 horas en total); fusionarlas baja la ocupación de 2025 de 105,0 a 104,8. No se corrigió en el pipeline por ser despreciable.
- **Ocupación por tipo de paciente, 2025 (media / p95 / máximo):** adultos de 15 años o más 88,3 / 97 / 106 frente a 88 camas de adultos que dio el HUN (64 de piso, 6 intermedio, 14 UCI, 4 TPR); niños de 1 a 14 años 14,5 / 22 / 27 y menores de 1 año 2,2 / 6 / 8, que juntos (16,7) frente a las 18 camas pediátricas y neonatales (8 + 10).
  Los adultos operan, en promedio, al 100 % de su capacidad, y el máximo llega a 106 (+18 sobre las 88). Es coherente con un hospital que hace esperar una mediana de 18,6 h por una cama.
- **Los picos no son artefactos:** en 2025 solo 96 horas (1,1 %) superan 118 camas, repartidas en 13 días de julio a octubre, y casi todas entre martes y viernes; ningún inicio ni fin de cama se repite en el mismo segundo más de 2 veces (no hay cargas en lote). Censo a medianoche: media de 105,1; al mediodía: 106,9; máximo 121.
- **Ventana:** desde la regla v3.9 del 2-nov, las series de ocupación, ingresos, altas y escenarios terminan el 9-abr-2026 (`OCUP_HASTA = 2026-04-10`); la ocupación de 2026 (103,2) es de enero al 9 de abril.
- **El exceso sobre las 106 camas es reciente y viene de las estancias largas:** % de horas por encima de 106 camas: 2023 1,9 % (máximo 111, o sea que ese año sí respeta el techo), 2024 21,5 %, 2025 41,8 %, 2026 (ene–9 abr) 31,0 %. De las 11 camas que sube la ocupación media entre 2023 (94) y 2025 (105), +6,9 vienen de estancias de más de 30 días (63 → 117 estancias por año; 6,4 → 13,3 camas), +3,6 de 14 a 30 días y +2,9 de 7 a 14 días; las de hasta 7 días bajan 2,5.
  En 2025 las estancias de más de 14 días (7,3 % de las estancias en 2025, `docs/factores_estancia.md`; corregido el 8-nov, antes decía 3 %) ocupan unas 36 camas (34 % de la ocupación). Son pacientes activos (los laboratorios llegan hasta ~1,6 días antes del alta en las de más de 30 días), no camas fantasma. Dos explicaciones coherentes: (A) la capacidad real creció después de 2023 y los 106 son un número anterior o parcial; (B) el hospital opera por encima de sus camas habilitadas con camas adicionales o camillas (sobreocupación), lo que cuadra con que el p90 de la espera pasara de 60 a 80 h en el mismo periodo. Con los datos no se distinguen; (A) choca con que el HUN dio 106 como el dato actual.
  Para el documento: presentar la ocupación frente a 106 (89 % en 2023, 95 % en 2024, 99 % en 2025 en promedio, con 42 % de las horas de 2025 por encima) y llamarla "sobreocupación o capacidad real mayor", sin afirmar cuál.
- **Prueba de actividad por estancia en la base (lote 3, 26.676 estancias distintas, `datos/crudos/auditoria_bd/S01_actividad_por_estancia.csv`):** las estancias de más de 30 días son pacientes hospitalizados reales: el 97,5 % tiene laboratorios (mediana: laboratorio en el 59 % de los días de la estancia), el 33 % tiene el procedimiento "Admission to adult intensive care unit" y el 49 % el de nutrición hospitalaria; solo 2 de 393 no tienen ninguna huella.
  Por duración, la presencia de laboratorio sube de 62 % (hasta 7 días) a 93 % (7–14), 96 % (14–30) y 97 % (más de 30). Los días-cama con laboratorio pasan de 46 % (2023) a 52 % (2024) y 56 % (2025). El 30 % de las estancias (8.004, casi todas de 7 días o menos) no tiene ninguna huella (ni laboratorio, ni UCI, ni nutrición): equivalen a 12 camas en 2025; son estancias cortas (partos, observación, procedimientos) y no se puede decir que no sean camas.
  **Conclusión:** no hay evidencia de que el exceso sobre 106 camas sea registros falsos; viene de pacientes con actividad diaria de hospitalización, sobre todo de estancias largas. La visita de tipo "Treatment urgency" (sin etapa ER, ~30 % se hospitaliza) pasó de 41 a 263 estancias por año entre 2023 y 2025 en este conteo (269 a 958 en el del pipeline, que cuenta cada estancia por su registro conservado).
**Pendiente real:** no hay dato interno que contraste los 106 camas; el pico de 106 a 123 en adultos sería sobreocupación con camas adicionales o camillas (no comprobable). La ocupación de urgencias (TU) sigue sin compararse con las 58 camillas.

