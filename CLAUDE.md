# CLAUDE.md — Data Challenge HUN 2026 (contexto completo del proyecto)

Este archivo resume TODO lo que ya se averiguó de la base de datos en semanas de consultas.
**Léelo completo antes de proponer consultas nuevas.** La base es lenta (consultas pesadas de 10–30 min
que traban el computador), así que antes de pedir una consulta comprueba aquí si la respuesta ya existe.
Última actualización: 22-oct-2026. (Cambio del 22-oct: las estancias en cama replicadas entre dos personas se cuentan
una sola vez; ver sección 4.6. Las cifras de espera de cama, ingresos y ocupación anteriores a esa fecha están infladas.)

---

## 0. Cómo trabajar conmigo (preferencias del equipo)

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

- PostgreSQL detrás de VPN, esquema **`uninorte_omop`** (el esquema `public` está vacío).
- Conexión **de solo lectura**: `CREATE TEMP TABLE` falla ("read-only transaction"). Usar `WITH` (CTE).
- Solo existen índices de llave primaria. `concept` no tiene ningún índice. Las tablas grandes no tienen
  índice por `visit_occurrence_id` ni `person_id`.
- Antes de consultas pesadas: `SET statement_timeout = 0;` (o `'30min'`).
- DBeaver muestra por defecto 200 filas: subir el límite o exportar con "Exportar datos > CSV"
  (que vuelve a correr la consulta completa). Ojo: copiar desde la grilla exporta solo lo cargado.
- Periodo de datos: **enero 2023 a junio 2026 completos**; julio 2026 parcial (último día con datos:
  2026-07-17); agosto casi vacío. Tendencias y pronósticos se cortan en junio 2026.
  **Aviso (22-oct): las llegadas bajan de forma sostenida desde abril de 2026** (por día: 244 en ene–abr, 186 en mayo, 171 en
  junio, 158 en 1–16 de julio) y los ingresos a cama también (~19–22 en ene–abr, 15,6 en mayo). Coincide con la caída de laboratorios
  de may–jun. Puede ser carga de datos incompleta o menos demanda real: no se sabe (pregunta 14). Mayo–julio 2026 se tratan
  con cautela y no se usan para evaluar modelos.

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
  hospitalizados, espera y ocupación con estancias únicas). **NO se aplica todavía** en `analisis_etapas.py`,
  `preparar_variables.py` ni `tabla_episodios`: ahí cada episodio gemelo sigue contando.
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
   justo antes de la HOSP.
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
> cuentan dos veces las estancias gemelas (sección 4.6). Valores vigentes: espera de cama mediana 18,0 h, ~22 ingresos/día,
> ~113 camas ocupadas.

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
- Extremos: máximo 2.867,8 h (visita 1409498); 3 episodios > 90 días; 370 TU > HOSP > 30 días.
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
- Reingresos (v1, sin depurar): 6,9 % en 72 h, 15,9 % en 30 días.

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

## 6b. Cuellos de botella: resultados (22-oct, estancias únicas; fases 2 a 5 de `docs/plan_de_accion.md`)

- **Segmentos candidatos** (27.167 estancias): espera de cama (mediana 18,0 h, p90 71,5 h), urgencias antes de la cama
  (77 % de las horas de espera) y hueco sin etapa antes de la cama (lo tiene ~24 % de los hospitalizados, mediana 19,7 h
  entre ellos; 23 % de las horas). La estancia en cama es servicio (va a la simulación) y urgencias sin hospitalizar solo
  es descriptiva (38 % medida, sesgada por tipo de visita, edad y año).
- **Ranking:** el 64 % de las horas de espera de cama queda por encima de la referencia de carga baja (518 mil de 812 mil
  horas-paciente). Urgencias antes de la cama lidera con las 4 referencias y los 3 cortes de episodio (72, 168, 336 h);
  el peso del hueco (17–24 %) depende del corte.
- **Tendencia:** exceso medio por episodio de 16,4 h (2023) a 22,9 h (2026), +40 %; el p90 sube de 61 a 80 h; la mediana
  se queda en 17–20 h. Empeoran los peores casos.
- **Carga (Fase 4):** la mediana de espera sube de 14,2 h (decil con menos llegadas en 6 h) a 25,9 h (decil con más), +2,5 %
  por decil controlando edad, año y hora. La ocupación pesa poco y las llegadas de 24 h casi nada.
- **Hora de llegada:** mediana de 12–15 h de madrugada y ~25 h al llegar entre las 13 y las 16 h (salto a las 13:00). La carga
  explica unos dos quintos del efecto de la tarde; el resto no.
- **Altas tardías (Fase 5, hipótesis sostenida descriptivamente, 4 de 4 criterios):** el 61,5 % de las altas ocurre entre las
  14:00 y las 18:59 y solo el 15 % antes del mediodía (estable 13–16 % por año). La cama se asigna con mediana a las 17–18 h
  sin importar la hora de llegada (7 a 21 h). Quien llega a las 8 h recibe cama al día siguiente en el 50 %; a las 16 h, en el
  72 %. Los ingresos a cama siguen a las altas en la misma hora (correlación cruzada 0,17 sin el patrón horario). La prueba a nivel
  diario del 21-oct fallaba porque el mecanismo es dentro del día. Asociación, no causa: el efecto de adelantar altas se
  estima en la simulación de camas (Fase 6).
- **Factores de la espera** (modelo sobre log(espera+1), R² = 12 %: casi toda la variación no se explica con lo observado):
  diagnóstico 3,9 puntos de R² (ojo: depende de si hay diagnóstico traducido, dato administrativo y registrado tarde), tipo de
  visita 2,3 (quien entra por urgencias espera más: ambulatorio −39 %, treatment urgency −42 %), edad y sexo 1,2, hora 0,6,
  laboratorios de 6 h 0,4, año 0,2, carga 0,1, calendario ~0.
- **Ocupación y escenario de altas (Fase 6, `simulacion_altas.py`):**
  - La ocupación sube de 105 camas (2023) a 119 (2025) y 117 (ene–abr 2026); es **por la estancia** (media de 4,70 a 5,46
    días, +16 %), no por más ingresos (22,3 → 21,7 por día; 20,4 en ene–abr 2026). Con Little: volver a la estancia de 2023
    liberaría ~16 camas; bajar la estancia 5 % ~6; subir los ingresos 10 % añadiría ~12.
  - El orden de llegada casi no predice el orden de cama (53 % de pares consecutivos en orden, azar 50 %): una fila FIFO no
    está respaldada por los datos y no se simula.
  - Por la tarde la ocupación baja de 115 a 108 camas (las altas). Con el 30 % de las altas de la tarde pasando a las 9–12 h
    quedan hasta 5,5 camas libres adicionales a las 12 h (~37 horas-cama por día).
  - Traducido a espera, **como máximo ~8 % del exceso de espera (448 horas-paciente por día)** y una estimación de ~3 %
    (cada alta extra se vuelve a ocupar con ~0,35 ingresos en 6 h). Adelantar el 100 % de las altas de la tarde: máximo 27 %.
    Adelantar altas ayuda pero no resuelve: el 83 % de las horas de espera viene de esperas de más de 24 h y el 57 % de esperas
    de más de 48 h (el 19 % de los pacientes), y unas horas menos no deshacen esperas de varios días.
  - Supuestos: el alta de los demás no cambia y la capacidad total (camas) se desconoce; es una cota, no una predicción.
- **Tendencia de la espera, con la caída de 2026 aparte:** exceso medio de espera por episodio 16,4 h (2023), 17,6 (2024),
  21,5 (2025) y 22,3 (ene–abr 2026), así que el empeoramiento (+36 %) se ve en periodos completos. En may–jul 2026 la espera
  mediana sube a 24 h (antes 15–18 h) mientras llegan 25 % menos pacientes: no se puede separar un efecto real de uno de registro.
- **Pronóstico de demanda (Modelo A, `pronostico_demanda.py` v1.3; entrenado hasta 2025-12, probado en ene–abr 2026, método
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
    28 alertas (0,23 por día), 15 aciertos: precisión 54 %, detección 83 %; a las 15 h: 15 alertas, 11 aciertos (73 % y 61 %);
    a las 9 h: 8 alertas, 5 aciertos (62 % y 28 %). **Un día antes** (solo pronóstico): AUC 0,61, 7 alertas, 3 aciertos (43 % y 17 %).
    Avisa a media jornada, no con un día de margen. Solo 18 días congestionados en la prueba: las cifras se mueven.
  - **B. Camas a 24 h desde las 12 h:** la proyección (camas ahora − altas esperadas + ingresos esperados) **no mejora a la
    persistencia** ("lo mismo que ahora"): error 4,3 contra 3,5 camas. Las altas esperadas tienen sesgo de +2,6 camas (22,4 esperadas
    contra 19,8 reales) y correlación de 0,17 con las reales (posible causa sin comprobar: las estancias del entrenamiento son más
    cortas que las de 2026). La alerta de "ocupación alta" (≥ percentil 80 de las 12 h del entrenamiento, 123 camas; 42 % de los
    días de 2026) funciona mejor con la persistencia: AUC 0,92, precisión 75 %, detección 90 %, 0,5 alertas por día. Se recomienda
    la persistencia y reportar las altas esperadas solo como orden de magnitud (~20 camas se liberan por día).
  - **C. Paciente sin cama** (solo los que luego se hospitalizan; cota inferior de la carga real): alerta a las 24 h, 9,1 por día,
    23 % termina esperando más de 72 h; a las 36 h, 5,5 por día, 38 %; **a las 48 h, 4,1 por día, 51 %, con 24 h de margen**; a las 60 h,
    2,7 por día, 79 %, con 12 h de margen. Más anticipación = más alertas y menos precisión.
  - **Carga total con el diseño recomendado** (A a las 12 h, B persistencia, C a las 48 h): ~4,9 alertas por día, casi todas del
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

**Estado (22-oct): el correo ya se envió y NO se espera respuesta.** Ningún paso del plan depende de ella: cada incógnita (número
de camas, meta de tiempos, causa de la caída de llegadas desde abril, persona real en las estancias gemelas) se trabaja con
escenarios y supuestos escritos y se declara como limitación en el documento final.

1. ¿Las visitas con id = otra + 1.746.478…1.746.489 o + 1.757.764 son duplicados de extracción/anonimización?
   ¿Cuál es el paciente correcto si el person_id difiere? (ej. 1091701, 2838179, 2849465)
2. Etapas 3045729 con inicio = fin (ej. 1037555): ¿falta la hora de salida? ¿hay otra fecha de alta?
3. Visitas solo con 9203 y sin nada clínico (ej. 1013223): ¿se fueron sin atención?
4. ¿Qué proceso es 9203 y cuál 3045729? ¿El paso a 9201 es la asignación de cama o la llegada al piso?
5. > 1 h sin etapa antes de 9201 en el 35 %: ¿dónde está el paciente? ¿se registra la asignación de cama?
6. Fines con milisegundos en julio 2026: ¿pacientes aún hospitalizados al extraer?
7. ¿Qué significa `visit_concept_id`? (ambulatorias con hospitalización; 3045729 con 43 h de mediana)
8. Columnas del instructivo ausentes o vacías: ¿habrá versión actualizada?
9. Número de camas y cubículos de urgencias por año (para ocupación en %).
10. Rúbrica de evaluación, repo público, Power BI con datos agregados.
11. ~1 de cada 4 hospitalizados tiene tiempo sin ninguna etapa antes de la cama (mediana 19,7 h entre ellos): ¿dónde está
    el paciente y se registra la asignación de cama? (ampliación de la 5)
12. Hay episodios de varios días en urgencias (TU) sin hospitalización registrada (ej. visita 2405100, 177 h): ¿esperan
    cama sin que se registre, observación prolongada o error?
13. Estancias gemelas (4.6): ¿cuál es la persona real cuando la misma estancia aparece en dos pacientes? (ampliación de la 1)
14. Desde abril de 2026 las llegadas bajan ~25–35 % (y los ingresos ~20–30 %) y los laboratorios caen a la mitad en may–jun:
    ¿cambió el volumen real (cierre de servicio, cambio de triage) o el registro, o la extracción está incompleta en los
    últimos meses?

---

## 9. Plan de acción

| Semana | Trabajo | Entregable |
|---|---|---|
| 20–26 oct | v3.3 de copias; correr preparar_variables v2; mapeo_dx.csv; enviar preguntas al HUN | Repo |
| 27 oct–2 nov | Componentes 1 y 2: rutas, llegadas, perfiles; espera de cama según hora, congestión, edad, diagnóstico; altas tardías | Doc + Power BI |
| 3–9 nov | Componente 3: modelo A (llegadas por día/hora, saturación) y modelo B (riesgo de espera de cama > 24 h). Entrenar 2023–2025, probar 2026 | Repo + doc |
| 10–16 nov | Componente 4: recomendaciones cuantificadas; Power BI completo | Power BI + doc |
| 17–23 nov | Documento final, README, reproducibilidad desde cero | Los 3 |
| 24–30 nov | Colchón y presentación | — |

Reglas para los modelos:
- Un modelo "al llegar" solo puede usar lo que se sabe al llegar: hora, día, festivo, edad, sexo,
  congestión y ocupación. **No** diagnósticos ni laboratorios posteriores.
- No modelar la duración de los pacientes de alta desde urgencias (solo ~45 % tiene hora de fin → sesgo).
  Sí la espera de cama (100 % medida en hospitalizados) y las llegadas (100 % de los episodios).
- Validación temporal (entrenar con pasado, probar con futuro), nunca aleatoria.

Limitaciones a declarar en el documento: copias (30 %), TU sin hora de fin (~38 % de las etapas TU),
diagnósticos tardíos y sin jerarquía, ocupación parcial, procedimientos sin fecha, sin signos vitales.

Documento del equipo (Claude Docs): "Exploración BD — Data Challenge HUN 2026".
