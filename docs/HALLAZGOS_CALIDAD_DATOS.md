# Hallazgos de calidad de datos (auditoría 4.1–4.13, síntesis ejecutiva)

**Última actualización:** 11-nov-2026 · **Período confiable:** feb-2023 a 9-abr-2026 · **Datos antes del 10-abr-2026 recomendados; después, solo descriptivo**

## Resumen ejecutivo

La base tiene tres problemas estructurales que se detectaron y se corrigieron iterativamente:

| Problema | Hallazgo | Impacto | Solución |
|---|---|---|---|
| **Visitas copia** (~30 %) | 512.045 registros duplicados por desfase fijo en `visit_occurrence_id` | Episodios inflados 2.1x; muchas copias con `person_id` distinto (82 %) | Regla v3.5 (eliminadas las 238k de la misma persona; replicadas de otra persona conservadas) |
| **Estancias gemelas** (41 % de hospitalizados) | 14.615 parejas: misma cama, dos personas, `person_id` vecino (78 %) | Espera, ingresos y ocupación infladas en promedio 15–20 % | Regla v3.8 (una estancia = conjunto de episodios conectados por intervalo HOSP idéntico; contar una vez) |
| **Persona equivocada en gemelas** (36 % de estancias) | Edad y sexo de la persona "real" perdidos; diagnóstico del "otro" paciente colgando de la estancia | Análisis por edad/sexo/diagnóstico sesgados | Regla v4.0 (3-nov): conservar el registro dominante en diagnósticos; corregida en 99,7 % de casos |

## Cambio de cifras (ante/después v3.8, 1-nov-2026)

| Métrica | Inflada (v3.5) | Vigente (v3.8) | Cambio |
|---|---|---|---|
| Espera de cama mediana | 22,4 h | **18,6 h** | −18,5 % |
| Ingresos/día a cama | 27,7 | **20,2** | −27,1 % |
| Camas ocupadas (prom. 2025) | 119 | **105** | −11,8 % |
| Estancias con cama contadas | 35.322 | **25.777** | 2.179 duplicados menos |

**Vigentes desde 1-nov-2026 (v3.8/v4.0):** espera mediana 18,6 h, ingresos ~20/día, ocupación 94–105 camas (2023–2025).

## Problemas menores (detectados, no corregidos o impacto despreciable)

- **Etapas abiertas (2,053):** pacientes aún en hospital al extraer (jul-2026). Retiradas del análisis.
- **TU sin hora de fin (36–42 %):** ~58 % de episodios de urgencia sin salida registrada. No usar para tiempos, solo para llegadas.
- **Visitas partidas (554):** corte en 168h sin etapas por copias. Después de quitar copias, casi todas se reconectan.
- **Doble registro en la misma persona (0,2 camas/año):** 438 intervalos HOSP solapados del mismo paciente. Despreciable.

## Período confiable: recorte de abril-mayo 2026

**Hallazgo (auditoría 4.9, 2-nov-2026):** desde el **10-abr-2026** el registro de etapas (`visit_detail`) se degrada:
- Etapas ER caen 64 % en mayo vs. mayo 2025
- Etapas TU caen 46 %; HOSP 45 %
- Visitas registradas suben +40 % (infladas en personas/día)
- Diagnósticos con código llegan a 0 desde 11-may

**Causas probables:** cambio en el sistema de registro, error de extracción o cambio de proceso. Visitas reales no bajaron (apenas +2 % en urgencias).

**Decisión:** **Período confiable = 2023-02-01 a 2026-04-09**. Después no se usa para entrenar modelos, estimar nivel ni evaluar error. Del 29-abr empeora aún más.

Referencia: `src/modelo_pronostico.py` (FIN_CONFIABLE = "2026-04-09", INICIO_QUIEBRE = "2026-04-10").

## Detalles de las reglas de limpieza

### Regla v3.5 (Visitas copia)
Desfases de `visit_occurrence_id`: +1.746.478 (259k), +1.757.764 (211k), +1.746.479 (23k), otros +1.746.480–89.
- Detecta como copia si `id − desfase` existe **Y** (misma persona **O** mismo fin **O** mismo inicio).
- Elimina solo si misma persona (238k). Las 311k de otra persona se conservan; sus etapas idénticas se quitan en etapa 5.
- Efecto: episodios de 1.19M a 295k; diagnóstico principal cubre 23,6 % (antes 3 %).

Implementación: `src/analisis_etapas.py` v3.6, sección 3.

### Regla v3.8 (Estancias gemelas)
Una "estancia en cama" es el conjunto de episodios que comparten:
- El mismo (inicio, fin) de hospitalización HOSP, **O**
- Algún intervalo HOSP idéntico (hay 3.845 casos donde uno tiene una etapa extra al comienzo)

Conexión con union-find. Resultado: 35.343 episodios HOSP → 25.777 estancias únicas.

**Espera de cama de la estancia** = llegada más temprana → inicio HOSP más temprano (no depende del registro conservado).

Implementación: `src/analisis_etapas.py` v3.8, sección 4.

### Regla v4.0 (Persona real de las gemelas)
En un par gemelo:
- La persona "real" tiene más diagnósticos que cuelguen de ella (91 % en dominio propio vs. 56 % en laboratorios, 52 % en procedimientos).
- En 93 % de las parejas, la dominante en diagnósticos = dominante en laboratorios → persona real.

Se identifica en 97,6 % de las estancias gemelas. Con esta regla, registro conservado es de la persona real en 99,7 % de los casos.

Efecto: edad y sexo corregidos; R² de espera sube de 14,8 % a 15,8 % (sube 4,1 puntos por sexo/edad).

Implementación: `src/preparar_variables.py` v2.4, sección 4b.

---

## Para profundizar

- **Histórico completo:** secciones 4.1–4.13 de `docs/CONTEXTO_TECNICO.md` (respaldo: `docs/CONTEXTO_TECNICO.md`)
- **Auditoría directa en BD:** `src/auditoria_bd.py` (consultas de solo lectura; resultados en `datos/crudos/auditoria_bd/`)
- **Exploración de esquema:** `src/explorar_bd.py` (8 tablas, sin índices, sin servicio/piso/cama)
- **Referencias de scripts:** `src/analisis_etapas.py` (limpieza), `src/preparar_variables.py` (variables), `src/construir_segmentos.py` (cuellos botella)
