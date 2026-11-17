# CLAUDE.md — Data Challenge HUN 2026 (núcleo de instrucciones)

**Última actualización:** 17-nov-2026 · **Período confiable:** feb-2023 a 9-abr-2026 (después datos degradados) · **Vigentes (1-nov v3.8/v4.0):** espera mediana 18,6 h, ingresos ~20/día, camas 94–105 (2023–2025)

---

## Cómo trabajar conmigo (preferencias del equipo)

- **Español explícito.** Si mi idea es mala, dilo y explica por qué.
- **Código completo**, nunca fragmentos. Verifica que funciona antes de confirmar.
- **Nunca** credenciales en chat. Consultas a BD: dame UNA consulta SQL lista (costos 10–30 min de espera).
- **Sin formación médica:** explica términos clínicos en palabras simples.
- **Contesta desde documentos:** si una cifra no está escrita, di que no se sabe. Señala qué script la produce.
- **Cita archivo y sección** de cada dato. Distingue asociación de causa. Declara limitaciones.

---

## El reto

**Data Challenge HUN 2026:** optimizar flujo de pacientes del Hospital Universidad del Norte (Uninorte). Detectar cuellos de botella, modelar demanda, alertar de saturación, proponer acciones.
**Entregables:** documentación, repositorio GitHub, dashboard Dash (fin de noviembre 2026).

---

## Acceso a la base de datos

- **PostgreSQL** detrás de VPN, esquema `uninorte_omop` (público vacío). Solo lectura: no `CREATE TEMP TABLE`; usar `WITH` (CTE).
- **Tablas:** person (912k), visit_occurrence (1,7M), visit_detail (3,3M), condition_occurrence (38,6M), procedure_occurrence (47M), measurement (16,6M), concept (10M). Sin índices (solo PK).
- **Lo que falta:** no hay `person_id` en visit_detail, ni servicio/piso/cama, ni `procedure_datetime`, ni CIE-10 (solo SNOMED), ni signos vitales.
- **Período confiable:** 2023-02 a 2026-04-09. Del 10-abr datos degradados (etapas ER −52 %, personas −48 %); no entrenar modelos después.
- **Consultar:** ver `docs/conexion_bd.md` (VPN, timeout, credenciales en `~/.pgpass`).

**Esquema esencial (tipos de etapa, desfases de copias, columnas clave):** `.claude/rules/hun_db_essentials.md` (cargado automáticamente si editas `src/*.py` o `sql/*.sql`).

---

## Decisiones de método (ya tomadas, no reabrir sin motivo nuevo)

1. **Unidad:** episodio = atención continua (corte 168h sin etapas).
2. **Etapas:** ER (triage, 3 min), TU (atención urgencias, 1,2 h), HOSP (cama, 46 h). Sin AMB (duración 0) ni etapas abiertas.
3. **Estancia única:** misma cama (inicio/fin idéntico) O intervalo HOSP idéntico = 1 estancia (regla v3.8).
4. **Espera de cama:** llegada → asignación de cama (el HUN confirmó que la hospitalización se registra al asignar cama).
5. **Persona real en estancias gemelas:** se conserva el registro con más diagnósticos propios (regla v4.0, 99,7 % exactitud).
6. **Reingreso:** llegada ≤72h/≤30 días tras episodio anterior con atención (no solo-ER sin actividad).
7. **Validación de modelos:** siempre temporal (pasado→futuro), nunca aleatoria. Un modelo "al llegar" solo usa lo que se sabe al llegar (no diagnósticos/laboratorios posteriores).

---

## Mapa de dónde está cada respuesta

| Pregunta | Archivo |
|----------|---------|
| Espera de cama, cuellos de botella, factores, alertas, pronóstico | `docs/HALLAZGOS.md` |
| Calidad de datos: copias, estancias gemelas, persona real, período degradado | `docs/HALLAZGOS_CALIDAD_DATOS.md` |
| Esquema OMOP, tipos de etapa, columnas que faltan | `.claude/rules/hun_db_essentials.md` |
| Recomendaciones (fuentes verificadas 6-nov) | `docs/recomendaciones.md` |
| Cómo consultar la BD (VPN, credenciales, timeout) | `docs/conexion_bd.md` |
| Plan de acción, fases, definición de cuello de botella | `docs/plan_de_accion.md` |
| Cómo reproducir desde cero | `README.md` |
| Qué falta y quién lo hace | `docs/pendientes_y_reparto.md` |
| Preguntas enviadas al HUN y respuestas | `docs/hun/sesion_de_preguntas.md` |
| Histórico completo de auditorías (si lo anterior no basta) | `docs/CLAUDE_respaldo_17nov2026.md` |

---

## Lo que NO hay en el repositorio

- **Datos clínicos:** `datos/` y `resultados/tablas/` están fuera de git (privacidad). Solo código, SQL, docs, `resultados/graficos/`.
- **Contraseña:** nunca la pidas ni la escribas. Vive en `~/.pgpass` y `~/.hun_db.json`.

---

## Cifras: obsoletas vs. vigentes

**NO usar** (estaban infladas por estancias gemelas sin deduplicar): espera 22,4 h, ingresos 27,7/día, camas ~145.

| Métrica | Obsoleta | **Vigente (v3.8/v4.0, 1–3-nov-2026)** |
|---|---|---|
| Espera de cama mediana | 22,4 h | **18,6 h** |
| Ingresos/día a cama | 27,7 | **20,2** |
| Camas ocupadas (prom. 2023/2024/2025) | ~146 / — / — | **94 / 101 / 105** |
| Estancias con cama (dedup) | 35.322 | **25.777** |

Detalle completo de por qué cambiaron: `docs/HALLAZGOS_CALIDAD_DATOS.md`.

---

## Avisos activos

- **Registro degradado desde 10-abr-2026:** causa desconocida (no es menos demanda). No usar ese período para entrenar ni evaluar modelos.
- **106 camas / 58 camillas confirmadas por el HUN** (29-oct), pero el exceso sobre 106 en 2024–2025 (hasta 123) no se explica del todo: puede ser sobreocupación real o que 106 sea un número parcial. Ver `docs/HALLAZGOS_CALIDAD_DATOS.md`.
- **No habrá más sesiones de preguntas con el HUN:** lo no respondido se trabaja como supuesto documentado, no se inventa.
