# Fichas de tareas (actualizado 21-oct-2026)

Cada ficha dice **qué pregunta responde, con qué datos, qué se hace paso a paso, qué se entrega y cuándo está terminada**.
Las de Persona 3 están escritas para pasarlas tal cual a la herramienta de IA que use.
Contexto y decisiones de método: `CLAUDE.md`. Reparto y calendario: `docs/plan_de_accion.md`.

## Por qué cambiaron los modelos (pruebas del 21-oct)
Se probó el plan anterior con los datos y se ajustó:

| Prueba | Resultado | Consecuencia |
|---|---|---|
| Predecir si un paciente espera más de 24 h usando solo lo que se sabe al llegar | AUC 0,60 (0,5 = azar) | No sirve como alerta individual; queda como análisis **explicativo** |
| Lo mismo, usando diagnóstico y laboratorios | AUC 0,64 | Ni haciendo trampa mejora mucho |
| ¿Cuántas altas hubo en el día explica la espera de ese día? | Correlación cercana a −0,06 | No se confirma a nivel diario. **(22-oct) Sí se sostiene dentro del día:** el 61 % de las altas es de 14 a 18:59 y la cama se asigna a las 17–18 h (ver `CLAUDE.md`, sección 6b) |
| Predecir cuánto se queda hospitalizado cada paciente | R² cercano a 0 | No se predice por paciente; se usa la **distribución real** |
| Ley de Little: ingresos por día × estancia media = camas ocupadas | 27,7 × 5,2 días = 144 camas; observado 145. **(22-oct) Esas cifras contaban dos veces las estancias replicadas entre dos personas.** Con estancias únicas: ~22 × 5,2 ≈ 100 camas; observado 113 | **El modelo de camas es coherente con los datos** (con los números corregidos) |

Lo que sí es predecible son las llegadas y los ingresos (patrón por hora, día y festivo) y la ocupación como
resultado de ingresos y estancias. Por eso los modelos pasan a ser de **demanda y capacidad**.

## Reglas comunes
- Los datos viven en el **drive privado del equipo**, nunca en git. Un notebook que los use se sube **sin salidas**.
- Validación **temporal**: entrenar con el pasado y probar con el futuro; nunca separar al azar.
- Periodo confiable: **2023-02-01 a 2026-05-31**. Julio 2026 está incompleto y no se usa para evaluar.
- Cada resultado lleva **una frase en español simple** que un médico o un gerente entienda, y su limitación al lado.
- Una rama por persona (`modelos`, `powerbi`, `docs`) y *pull request* hacia `main`; Daniela revisa.
- Nada de afirmar causas: lo que mostramos son asociaciones y escenarios con supuestos explícitos.

## Tablas que se comparten por el drive (las genera `src/exportar_para_equipo.py`)
- `panel_diario.csv`: una fila por día (2023-02 a 2026-05): `llegadas, hospitalizados, ingresos_a_cama, altas,
  altas_antes_mediodia, ocup_hosp_media, ocup_hosp_max, espera_cama_mediana_h, n_espera, dia_semana_num, mes, festivo,
  dia_no_habil`.
- `estancias_hospitalizacion.csv`: una fila por **estancia en cama** (25.777, v2 del 22-oct): `ingreso_cama, alta, horas_hosp,
  alta_completa, n_registros, llegada, hora_llegada, edad, grupo_edad, sexo, tipo_visita, categoria_dx, espera_cama_h, ...`.
  La misma estancia replicada entre dos personas (41 % de los episodios hospitalizados) se cuenta **una vez**
  (`n_registros` dice cuántos registros tenía). Usar solo `alta_completa == True` para estancias.
  **Descargar de nuevo: la versión anterior (35.343 filas) tenía las estancias duplicadas.**
- `serie_horaria.csv`: una fila por hora: `hora_inicio, llegadas, llegadas_que_se_hospitalizan, ocup_hosp, ocup_tu`.
  **(23-oct)** `llegadas_que_se_hospitalizan` y `ocup_hosp` ya cuentan cada estancia una vez (~100 camas, ~20 por día). `ocup_tu` y
  `llegadas` siguen contando todos los episodios. Si descargaron esta tabla antes del 23-oct, **descargarla de nuevo**.
- `tabla_episodios.parquet`: una fila por episodio (337.194), 63 columnas. Incluye los episodios gemelos con la marca
  `estancia_unica`: para espera de cama, camas e ingresos usar `estancia_unica == True` (`espera_cama_h` ya viene vacía en los gemelos).

---

## PERSONA 3 (Anthony) — Capacidad de camas, simulación y modelo explicativo
*(La ficha 3.4 de recomendaciones pasó a Samuel el 23-oct. Pendientes de Anthony: A4 y A5 de `docs/pendientes_y_reparto.md`.)*
Carpetas: `notebooks/modelos/`, `notebooks/simulacion/`, `docs/`.

### Ficha 3.1 — Modelo de camas: ¿cuántas camas habrá ocupadas los próximos días?
**Pregunta:** con las hospitalizaciones esperadas y el tiempo que suele quedarse cada paciente, ¿cuántas camas ocupadas
habrá cada día y con qué probabilidad se superará un nivel de saturación?
**Datos:** `estancias_hospitalizacion.csv` y `panel_diario.csv`.
**Pasos:**
1. **Describir las estancias:** distribución de `horas_hosp` (mediana 71 h, media 5,2 días, cola larga) en total y por
   `grupo_edad`, `sexo` y `categoria_dx`. Ajustar una distribución (por ejemplo, log-normal o empírica).
2. **Ingresos por día:** usar `ingresos_a_cama` del panel. Al inicio, el promedio por día de la semana; cuando Daniela
   entregue el Modelo A, el pronóstico de ingresos.
3. **Simulación de Monte Carlo:** para cada día futuro, tomar los ingresos esperados, asignar a cada uno una estancia
   sacada de la distribución del paso 1 y contar cuántas camas están ocupadas cada día (censo). Repetir 1.000 veces para
   obtener una banda (por ejemplo, 10 % a 90 %).
4. **Prueba hacia atrás (backtest):** simular enero a mayo de 2026 con datos solo hasta diciembre de 2025 y comparar con
   `ocup_hosp_media` del panel. Reportar el error absoluto medio y qué porcentaje de días cae dentro de la banda.
5. **Alerta de saturación:** definir "día saturado" como ocupación por encima del percentil 90 del periodo de
   entrenamiento y calcular la probabilidad de saturación para cada día futuro.
**Entrega:** `notebooks/modelos/modelo_camas.ipynb`, `docs/modelo_camas.md` (método en lenguaje simple, gráfico de
ocupación real contra proyectada con su banda, métricas) y `modelo_camas_proyeccion.csv` al drive.
**Terminado cuando:** el backtest de 2026 tiene error reportado y entre 70 % y 90 % de los días caen dentro de la banda
del 80 %; la alerta indica su acierto y sus falsas alarmas.
**Limitación a escribir:** la ocupación es solo de los pacientes de esta base (se desconoce el total de camas del hospital).

### Ficha 3.2 — Simulación de escenarios: ¿qué pasaría si cambiamos algo?
**Pregunta:** ¿qué efecto tendrían cambios operativos sobre la ocupación y la disponibilidad de camas?
**Datos:** el modelo de la ficha 3.1, `estancias_hospitalizacion.csv` y `altas_ingresos_por_hora.csv` (hora de las altas).
**Escenarios mínimos (cada uno con sus supuestos escritos):**
- **A.** El 30 % de las altas pasa de la tarde a antes del mediodía (cambia la hora de salida, no la estancia en días).
- **B.** Los ingresos aumentan 10 % (por ejemplo, brote de dengue o temporada alta).
- **C.** La estancia baja 5 % (más eficiencia en cuidados).
**Qué se reporta por escenario:** ocupación media y máxima, número de días saturados, y camas libres por hora del día.
**Cuidado:** hoy **no** se demuestra que adelantar las altas reduzca la espera; solo se mostrará cuántas camas
quedarían libres antes. Si se quiere traducir eso en horas de espera, hay que decir claramente que es un supuesto.
**Ya hecho por Daniela (22-oct, `src/simulacion_altas.py`):** el escenario A con la hora del día y una cota de la espera
evitada. Con el 30 % de las altas de la tarde antes del mediodía salen ~37 horas-cama liberadas por día (hasta 5,1 camas
libres adicionales a las 12 h), lo que evitaría **como máximo ~8 % del exceso de espera** (estimación ~3 %). La ocupación de
2025 es 12 % mayor que la de 2023 por la **estancia** (+16 %), no por más ingresos. Las tablas `escenario_altas_antes.csv`,
`escenario_camas_por_hora.csv` y `escenarios_little.csv` (Daniela las sube al drive). **No repetir el escenario A: construir B y C y
la tabla de escenarios sobre eso.**
**Entrega:** `notebooks/simulacion/escenarios.ipynb` y `docs/simulacion.md` con una tabla de escenarios.
**Terminado cuando:** cada escenario tiene supuestos, resultado y una frase de lectura para un gerente.

### Ficha 3.3 — Modelo explicativo de la espera (antes "Modelo B")
**Pregunta:** ¿qué factores se asocian a esperar más de 24 h, separando el efecto de cada uno?
**Datos:** `tabla_episodios.parquet`, solo filas con `espera_cama_h` no nula **y que estén en `estancias_hospitalizacion.csv`**
(estancias únicas, ~27 mil; sin ese filtro cada estancia replicada entra dos veces). **Objetivo:** `espera_mas_24h`.
**Variables permitidas (se conocen al llegar):** `hora`, `dia_semana_num`, `mes`, `festivo`, `dia_no_habil`, `edad`,
`grupo_edad`, `sexo`, `tipo_visita`, `ocup_hosp`, `ocup_tu`, `llegadas_6h_previas`, `llegadas_24h_previas`,
`n_episodios_previos`, `reingreso_72h`, `reingreso_30d`.
**Prohibidas (se registran después y filtran la respuesta):** `categoria_dx`, `dx_*`, `n_dx_distintos`, `n_proc_distintos`,
`n_lab*`, `horas_*`, `hueco_antes_hosp_h`, `ruta*`, `fin`, `dias_hasta_siguiente`, `vuelve_en_30d`.
**Pasos:**
1. Regresión logística con variables estandarizadas, entrenando con 2023-02 a 2025-06, validando con 2025-07 a 2025-12 y
   probando con 2026-01 a 2026-05.
2. Reportar los efectos como **razones de probabilidades** con su intervalo (por ejemplo, "llegar de 12 a 17 h multiplica
   por X las probabilidades de esperar más de 24 h").
3. Reportar AUC y Brier del modelo **sin esconder que son bajos** (la prueba inicial dio AUC de 0,60).
**Entrega:** `notebooks/modelos/modelo_espera_explicativo.ipynb` y `docs/modelo_espera.md`.
**Terminado cuando:** la página dice con claridad qué factores pesan, que el modelo **no** sirve para alertar a un paciente
individual y por qué (explica poco: el resto depende de procesos que la base no registra).

### Ficha 3.4 — Recomendaciones con números (semana 10-16 nov)
**Reasignada (23-oct): la lleva Samuel (Persona 2), no Anthony** (ver `docs/pendientes_y_reparto.md`, B2). Donde dice "Persona 3", leer Samuel.
**Estado (22-oct):** Daniela dejó un borrador completo en `docs/recomendaciones.md` (7 recomendaciones con sus números, límites
y fuentes). **Persona 3 lo revisa y lo amplía:** leer las fuentes originales (el borrador solo vio resúmenes de búsqueda), añadir
5 a 8 prácticas si hacen falta y verificar que cada cifra coincide con `CLAUDE.md` 6b.
**Datos:** resultados de las fichas 3.1 a 3.3, `factores_espera_cama.csv` y `altas_ingresos_por_hora.csv`.
**Pasos:**
1. Investigar 5 a 8 prácticas conocidas (altas antes del mediodía, gestión diaria de camas, unidades de decisión de
   ingreso, alertas tempranas de saturación) y anotar la fuente de cada una.
2. Para cada una indicar qué se cambiaría, qué métrica del hospital lo mediría y qué impacto se estima con la simulación o
   por qué no se puede estimar.
**Entrega:** `docs/recomendaciones.md` con una tabla (práctica, fuente, métrica, impacto estimado, limitación).
**Terminado cuando:** cada recomendación tiene un número o una razón clara de por qué no se puede calcular.

---

## PERSONA 2 (Samuel) — Power BI, recomendaciones y contacto con el HUN
*(Pendientes de Samuel: B1 y B2 de `docs/pendientes_y_reparto.md`.)*
Carpetas: `powerbi/`, `docs/hun/`.

1. **Esta semana:**
   - Enviar el correo al HUN con las preguntas de `CLAUDE.md`, sección 8, y guardar sus respuestas en `docs/hun/`
     (Daniela las revisa con Claude).
   - Instalar Power BI y conectar `panel_diario.csv`, `serie_horaria.csv` y las tablas de factores (drive).
2. **Páginas del dashboard:**
   1. **Llegadas:** por hora y día de la semana (mapa de calor), con filtros por año y tipo de visita.
   2. **Rutas y tiempos:** rutas más frecuentes y su duración (solo episodios "medida").
   3. **Espera de cama:** por hora de llegada, edad y diagnóstico, con la nota "asociación, no causa".
   4. **Pronóstico y alertas:** llegadas y hospitalizaciones previstas y los días atípicos (modelo de Daniela).
   5. **Camas y escenarios:** ocupación proyectada con su banda y los escenarios de la simulación (Persona 3).
   6. **Recomendaciones:** tabla de acciones con su impacto estimado.
3. **Repo:** `powerbi/medidas_dax.md`, capturas y la plantilla `.pbit`. El `.pbix` **no se sube**.
4. **Documento:** escribir la sección "Dashboard" (qué pregunta responde cada página).
**Terminado cuando:** cada página responde una pregunta del hospital en una frase y el enlace abre sin pedir datos.

---

## DANIELA (con Claude) — Modelo A, días atípicos, datos y documento
Carpetas: `src/`, `sql/`, `docs/`, `datos/referencia/`, `notebooks/modelos/`.

### Ficha D.1 — Modelo A ampliado: pronóstico de llegadas e ingresos y alerta de saturación
**Pregunta:** ¿cuántas personas llegarán y cuántas se hospitalizarán cada día y cada hora, y mañana será un día congestionado?
**Datos:** `panel_diario.csv` y `serie_horaria.csv`.
**Pasos:**
1. Pronosticar **llegadas** (por día y por hora) e **ingresos a hospitalización** (por día). Entrenar 2023-02 a 2025-12;
   probar 2026-01 a 2026-05.
2. Comparar con dos referencias simples: el promedio de la misma combinación día × hora, y el mismo día de la semana
   anterior. Un modelo solo vale si las mejora.
3. Variables: día de la semana, hora, mes, festivos de Colombia y las llegadas recientes.
4. Alerta: "día congestionado" = llegadas por encima del percentil 90 del entrenamiento; probabilidad para el día siguiente.
**Entrega:** `notebooks/modelos/modelo_A_demanda.ipynb`, `docs/modelo_A.md`, `modelo_A_predicciones.csv` al drive.
**Terminado cuando:** el modelo mejora las dos referencias en 2026 y la alerta reporta su precisión y falsas alarmas.
**Hecho el 22-oct (`src/pronostico_demanda.py` v1.3, resultados en `CLAUDE.md` 6b):** las **llegadas** sí mejoran a las referencias
(error 7,5 % a 1 día) y la alerta de un día antes tiene AUC 0,79 (la de media jornada, mucho mejor, está en `src/alertas.py`). Los **ingresos a cama diarios** NO se pueden
pronosticar mejor que "día de la semana × nivel reciente" (error ~23 %, es ruido de conteo), pero **por semana el error baja a 9,5 %**:
**para el modelo de camas (ficha 3.1) usar el pronóstico semanal de ingresos, repartido por día con el patrón del día de la semana**.
Ojo: desde el 10 de abril de 2026 el registro de las etapas se degrada (no es menos demanda; `CLAUDE.md` 4.9); para el escenario base de
camas conviene usar el nivel de 2025 (~20 ingresos por día) y el nivel reciente (~19 en ene–abr 2026) como escenario bajo.
Los pronósticos de ingresos alimentan el modelo de camas de Persona 3.

### Ficha D.2 — Detección de días atípicos (lo pide el instructivo)
**Hecho el 22-oct:** `src/dias_atipicos.py`, `docs/dias_atipicos.md` y `resultados/tablas/dias_atipicos.csv` (Daniela sube el CSV al drive para la página 4 de Power BI).
**Pregunta:** ¿qué días se salieron del patrón y qué los distingue?
**Pasos:** comparar lo observado con lo que esperaba el Modelo A (residuo estandarizado) en llegadas, ingresos y
espera mediana; marcar los días fuera de ±3 desviaciones; revisar si coinciden con festivos, puentes o brotes (dengue)
y describirlos en palabras simples.
**Entrega:** `docs/dias_atipicos.md` y `dias_atipicos.csv` al drive (para la página 4 de Power BI).

### Ficha D.3 — Datos, coordinación y documento
1. Correr los scripts y exportar al drive los martes y viernes: `python3 src/analisis_etapas.py`, luego
   `preparar_variables.py` y `exportar_para_equipo.py`.
2. Correr en DBeaver las consultas pesadas que pida Claude (laboratorios con hora mínima y máxima; consultas filtradas
   por persona).
3. Revisar los *pull requests* y hacer los commits de cierre (sin datos y sin `.pbix`).
4. **Documento:** Claude redacta contexto, metodología, limitaciones y componentes 1 y 2 desde los scripts; Daniela revisa.
5. **`mapeo_dx.csv`:** Claude deja el borrador de los ~300 diagnósticos más frecuentes; Daniela lo revisa con el
   navegador de SNOMED o con un docente de salud.
6. Compilar las respuestas del HUN y ajustar las limitaciones del documento.

### Ficha D.4 — Perfiles de pacientes y factores de la estancia (A1 y A2; detalle en `docs/pendientes_y_reparto.md`)
Comparar perfiles (edad × sexo × tipo de visita, y diagnóstico agrupado cuando exista `mapeo_dx.csv`) en llegadas, ruta, % hospitalizado, espera, estancia y reingreso;
y explicar la estancia en cama, incluida la pregunta de si el +16 % (4,57 a 5,31 días) viene de un cambio en el tipo de pacientes o de dentro de cada tipo.
**Nota de la sugerencia de Anthony (23-oct):** dejar la tabla de perfiles con el mismo identificador de estancia que usará D.5 y reutilizar allí la definición de "estancia disparada".
Entrega: `src/perfiles_pacientes.py`, `src/factores_estancia.py` y sus documentos.

### Ficha D.5 — Qué comparten las estancias que se "disparan" (A2b) y sistema repetible de diagnóstico (A7, por decidir)
Idea de Anthony: ya sabemos que el problema está en las camas; falta saber **cuándo se disparan las estancias y qué comparten** (edad, sexo, diagnóstico, procedimientos,
laboratorios, ruta). Pasos: (1) estancia mediana, percentil 90 y % de más de 7 días por mes; (2) nueva extracción `sql/estancias_perfil.sql` filtrando `co.person_id = vo.person_id`
(10 a 30 min por consulta, la corre Daniela en DBeaver); (3) comparar disparadas con no disparadas con razón de probabilidades e intervalo, cuidando la confusión por edad.
`race_concept_id` está 95 % vacío: las acciones que salgan deben ser de proceso, no de exclusión de pacientes. Todo es asociación.
A7 (flujo repetible detectar → simular → extraer → caracterizar → explicar) se decide después de A2b, A1 y la simulación Monte Carlo de Anthony.
