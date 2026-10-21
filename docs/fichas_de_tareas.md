# Fichas de tareas (actualizado 20-oct-2026)

Cada ficha dice qué se entrega, con qué datos, qué reglas no se pueden romper y cómo sabemos que está terminada.
Las fichas de la Persona 3 están escritas para pasarlas tal cual a la herramienta de IA que use.
Contexto del proyecto y decisiones de método: `CLAUDE.md`.

## Reglas comunes
- Los datos viven en el **drive privado del equipo**, nunca en git. Si un notebook los usa, se sube **sin salidas**.
- Validación **temporal**: entrenar con el pasado y probar con el futuro. Nada de separar al azar.
- Periodo confiable: enero 2023 a junio 2026. Julio 2026 está incompleto: no se usa para evaluar.
- Cada resultado se acompaña de una frase en español simple que un médico o un gerente entienda.
- Una rama por persona; *pull request* hacia `main`.

---

## PERSONA 3 — Modelo B, simulación y recomendaciones (carpetas `notebooks/modelos/`, `notebooks/simulacion/`, `docs/`)

### Ficha 3.1 — Modelo B: riesgo de esperar más de 24 h por una cama
**Datos:** `tabla_episodios.parquet` (una fila por episodio; 59 columnas). Usar solo filas con `espera_cama_h` no nula
(34.537 episodios, 2023-2026). **Objetivo:** columna `espera_mas_24h` (1 si esperó más de 24 h).
**Variables permitidas (se conocen al llegar):** `hora`, `dia_semana_num`, `mes`, `festivo`, `dia_no_habil`, `edad`,
`grupo_edad`, `sexo`, `tipo_visita`, `ocup_hosp`, `ocup_tu`, `llegadas_6h_previas`, `llegadas_24h_previas`,
`n_episodios_previos`, `dias_desde_anterior`, `reingreso_72h`, `reingreso_30d`.
**Prohibidas (se registran después de llegar; filtran la respuesta):** `categoria_dx`, `dx_*`, `n_dx_distintos`,
`n_proc_distintos`, `n_lab*`, `horas_*`, `hueco_antes_hosp_h`, `ruta*`, `fin`, `dias_hasta_siguiente`, `vuelve_en_30d`.
**Tarea:**
1. Separación temporal: entrenar con 2023-01 a 2025-06, validar con 2025-07 a 2025-12, probar con 2026-01 a 2026-06.
2. Un modelo **interpretable** (regresión logística) y uno más flexible (árboles con gradiente). Reportar AUC, PR-AUC,
   Brier y la curva de calibración; comparar contra la tasa base (48 %).
3. Explicar qué variables pesan (coeficientes y SHAP o importancia por permutación) y cuánto cambia el riesgo si se llega
   de madrugada frente a la tarde, con congestión alta frente a baja.
4. Una segunda versión opcional con `ocupacion_confiable == True` para ver si cambia algo.
**Entrega:** notebook `modelo_B_espera.ipynb`; `modelo_B_predicciones.csv` (`visit_occurrence_id, episodio, ini,
espera_mas_24h, prob`) al drive; `docs/modelo_B.md` con métricas, gráficos y 5 frases de interpretación.
**Terminado cuando:** el modelo supera claramente la tasa base en 2026, está calibrado y las frases de interpretación
dicen algo accionable (por ejemplo, "llegar entre las 12 y las 17 h sube el riesgo de 48 % a X %").
**Aviso:** `tipo_visita` no describe bien por dónde pasó el paciente (ver `CLAUDE.md`, sección 3), pero sí se conoce
al llegar y puede usarse como variable; no debe interpretarse como "ruta".

### Ficha 3.2 — Simulación de escenarios (semana 10-16 nov)
**Datos:** `modelo_B_predicciones.csv`, `altas_ingresos_por_hora.csv`, `espera_cama.csv` (del drive).
**Tarea:** una simulación sencilla (por ejemplo, una cola con cupos de cama que se liberan según la hora de alta) que
responda: si el 30 % de las altas pasara de la tarde a antes del mediodía, ¿cuánto bajaría la espera mediana y el
porcentaje que espera más de 24 h?
**Entrega:** `notebooks/simulacion/` y una tabla de escenarios (`docs/simulacion.md`) con supuestos explícitos.

### Ficha 3.3 — Recomendaciones con números (componente 4, semana 10-16 nov)
**Datos:** resultados del Modelo B y de la simulación; `factores_espera_cama.csv` y `altas_ingresos_por_hora.csv` (drive).
**Tarea:**
1. Investigar 5 a 8 prácticas conocidas para reducir la espera de cama (altas antes del mediodía, gestión diaria de camas,
   unidades de decisión de ingreso, alertas tempranas de saturación) y anotar la fuente de cada una.
2. Para cada práctica, indicar **qué se cambiaría**, **qué métrica del hospital lo mediría** y **cuánto bajaría la espera**
   según la simulación (o por qué no se puede estimar).
**Entrega:** `docs/recomendaciones.md` con una tabla (práctica, fuente, métrica, impacto estimado, limitaciones).
**Terminado cuando:** cada recomendación tiene un número o una razón clara de por qué no se puede calcular.

---

## PERSONA 2 — Power BI (carpeta `powerbi/`)
1. **Semana 20-26 oct:** instalar Power BI y conectar `serie_diaria`, `serie_horaria`, `mapa_calor_llegadas`,
   `factores_espera_cama` (drive). Probar una página de llegadas por hora y día.
2. **27 oct-2 nov:** páginas 1 a 3 (llegadas, rutas, espera de cama por hora/edad/diagnóstico).
3. **3-9 nov:** página 4 con las predicciones de los modelos A (Daniela) y B (Persona 3), cuando las entreguen.
4. **10-16 nov:** página 5 (recomendaciones) y pulido visual.
5. **Esta semana:** enviar el correo al HUN con las preguntas de `CLAUDE.md` sección 8 y guardar sus respuestas en
   `docs/hun/` (Daniela las revisa con Claude).
6. **Todas las semanas:** guardar en el repo `powerbi/medidas_dax.md` y capturas; el `.pbix` NO se sube.
7. **Documento:** escribir la sección "Dashboard" (qué responde cada página) y colocar las capturas.
**Terminado cuando:** cada página responde una pregunta del hospital en una frase y el enlace público abre sin pedir datos.

---

## DANIELA (con Claude) — Datos, coordinación y documento
1. **Datos:** correr los scripts y las consultas en DBeaver; exportar cada martes y viernes las tablas al drive
   (`tabla_episodios.parquet`, series, factores, mapa de calor) con fecha en el nombre.
2. **Consultas pesadas** que pida Claude (la de laboratorios con hora mínima y máxima; consultas filtradas por persona).
3. **Modelo A** (ficha D.1, abajo): Claude lo construye y Daniela lo corre, revisa y sube; usa solo tablas agregadas.
4. **Repo:** revisar los *pull requests*, mantener `.gitignore`, hacer los commits de cierre sin datos.
5. **Documento:** Claude redacta los borradores de contexto, metodología, limitaciones y componentes 1 y 2 a partir de los
   scripts; Daniela revisa y corrige.
6. **`mapeo_dx.csv`:** Claude deja el borrador; Daniela lo revisa con el navegador de SNOMED o con un docente de salud.

### Ficha D.1 — Modelo A: pronóstico de llegadas y alerta de saturación
**Datos:** `serie_horaria.csv` (llegadas por hora: `hora_inicio, llegadas, llegadas_que_se_hospitalizan, ocup_hosp,
ocup_tu, ocupacion_confiable`) y `serie_diaria.csv` (`fecha, llegadas, ..., dia_semana`).
**Tarea:**
1. Pronosticar las llegadas por **día** y por **hora**. Entrenar con 2023-01 a 2025-12; evaluar con 2026-01 a 2026-06.
2. Comparar contra dos referencias simples: (a) el promedio histórico de la misma combinación día de la semana × hora,
   (b) el mismo día de la semana de la semana anterior. Un modelo solo vale si las mejora.
3. Usar el calendario como variables: día de la semana, hora, mes, festivos de Colombia (librería `holidays`).
4. Definir **día congestionado** = llegadas del día por encima del percentil 90 del periodo de entrenamiento y construir
   una **alerta**: la probabilidad de que mañana sea un día congestionado.
**Entrega:** notebook `modelo_A_llegadas.ipynb`; `modelo_A_predicciones.csv` (`fecha_hora, real, pred, lim_inferior,
lim_superior`) al drive; una página `docs/modelo_A.md` con métricas (MAE y MAPE por día y por hora, aciertos de la alerta),
gráfico de real contra pronóstico y la regla de la alerta en lenguaje simple.
**Terminado cuando:** el modelo mejora las dos referencias en 2026 y la alerta reporta precisión y cobertura.


