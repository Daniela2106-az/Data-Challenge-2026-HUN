# Pendientes y reparto del equipo (23-oct-2026)

Lista de lo que falta para cubrir el instructivo del Data Challenge (`docs/DATA CHALLENGE HUN 2026 (2).pdf`), con responsable, qué hay que entregar y
con qué insumos. **Prioridad actual: cubrir primero los huecos de análisis, modelos y predicciones; los entregables (dashboard, documento final,
presentación) van al final.**

**Equipo:** **Daniela** (coordina, scripts de datos y análisis, lleva Claude Code), **Samuel** (Persona 2) y **Anthony** (Persona 3). Anthony también
usa Claude Code: su Claude debe leer `README.md` → `docs/HALLAZGOS.md` → este documento → la ficha de su tarea en `docs/fichas_de_tareas.md`.

**Qué ya está hecho** (no repetir): limpieza y episodios, flujo del paciente, cuellos de botella (fases 0 a 5), ocupación y escenario de altas, pronóstico de
demanda, alertas, días atípicos, borrador de recomendaciones y un repositorio reproducible. Todo con cifras en `docs/HALLAZGOS.md`.

---

## Resumen del reparto

| Persona | Pendientes | Prioridad |
|---|---|---|
| **Daniela** | A1 perfiles de pacientes, A2 factores de la estancia hospitalaria (con la ampliación A2b: qué comparten las estancias que se disparan), A3 `mapeo_dx.csv`, y la coordinación (C1 a C3) | Ahora |
| **Anthony** | A4 explicar mejor los retrasos, A5 simulación Monte Carlo de camas | Ahora |
| **Samuel** | B1 dashboard de Power BI, B2 recomendaciones (verificar fuentes y dejarlas finales), **A6 estimar tiempos de atención** | Al final (B2 puede empezar antes; A6 después de los análisis A) |
| Por decidir más adelante | A7 sistema repetible de diagnóstico de cuellos de botella, B3 documento final, B4 presentación | Después |

---

## A. Análisis, modelos y predicciones (ahora)

### A1. Perfiles de pacientes · **Daniela**
- **Qué pide el instructivo:** "cómo se comportan distintos perfiles de pacientes". Hoy solo hay cortes sueltos por edad, tipo de visita y diagnóstico.
- **Qué hacer:** definir perfiles (edad × sexo × tipo de visita, y grupo de diagnóstico cuando exista A3) y comparar por perfil: cuántos llegan, ruta que siguen,
  % que se hospitaliza, espera de cama, estancia y reingreso. Opcional: agrupar trayectorias parecidas.
- **Qué ya sabemos:** el 10,5 % de los episodios con atención se hospitaliza cada año; por edad va de 9 % (15 a 29 años) a 14 % (75 o más) y la estancia mediana de
  65 h (5 a 14 años) a 92 h (75 o más). La duración de urgencias sin hospitalizar está sesgada por tipo de visita y edad.
- **Entrega:** `src/perfiles_pacientes.py`, `docs/perfiles_pacientes.md` (con la limitación de cada hallazgo) y un gráfico en `resultados/graficos/`.
- **Terminado cuando:** hay una tabla de perfiles con un mínimo de pacientes por celda, cada diferencia dice si es grande o ruido, y se contesta "qué perfiles
  esperan más y por qué podría ser".
- **Insumos:** `tabla_episodios.parquet` (filtrar `estancia_unica == True` para espera y estancia), `segmentos.csv`.
- **Depende de:** A3 para el diagnóstico (se puede empezar sin él).
- **Nota de la sugerencia de Anthony (23-oct):** los perfiles también deben servir para A2b y A7: dejar la tabla de perfiles con el mismo identificador de estancia que usará A2b, para poder cruzar "perfil" con "estancia disparada".

### A2. Factores de la estancia hospitalaria · **Daniela**
- **Qué pide el instructivo:** componente 2: "factores asociados a incrementos en [...] la duración de las estancias hospitalarias". Hoy solo describimos la estancia.
- **Qué hacer:** explicar la estancia en cama (mediana 71 h, percentil 90 de 280 h) con edad, sexo, diagnóstico, ruta, tipo de visita y laboratorios de las primeras 6 h.
  Responder además una pregunta concreta: la estancia media subió de 4,70 a 5,46 días (2023 a 2025), **¿por un cambio en el tipo de pacientes o dentro de cada tipo?**
  (descomposición por composición).
- **Entrega:** `src/factores_estancia.py` y `docs/factores_estancia.md`.
- **Terminado cuando:** se dice qué se asocia a estancias largas y qué parte del +16 % se explica por el tipo de pacientes. Se reporta el R² sin esconderlo
  (la prueba del 21-oct dio R² cercano a 0 al predecir la estancia por paciente: aquí el objetivo es explicar, no predecir).
- **Insumos:** `tabla_episodios.parquet`, `estancias_hospitalizacion.csv`.
- **Depende de:** A3 para el diagnóstico.
- **Nota de la sugerencia de Anthony (23-oct):** al terminar A2, seguir con A2b (qué comparten las estancias que se disparan); es la misma pregunta con más variables (procedimientos y laboratorios). Reutilizar la definición de "estancia disparada" entre ambas.

### A2b. Qué tienen en común las estancias que se "disparan" · **Daniela** (ampliación de A2, idea de Anthony del 23-oct)
- **La idea:** ya sabemos que el problema está en las camas y que la estancia sube (4,70 a 5,46 días). Falta preguntar: **¿cuándo se disparan las estancias y qué
  comparten las que se disparan?** (edad, sexo, diagnóstico, procedimientos, laboratorios, ruta). La respuesta convierte "hay un cuello de botella" en "este tipo
  de estancias lo causa".
- **Qué hacer:**
  1. **Localizar en el tiempo:** estancia mediana, percentil 90 y % de estancias de más de 7 días **por mes** (2023 a abr 2026, estancias únicas). Definir "estancia
     disparada" (por ejemplo, más de 280 h = percentil 90) y ver si se concentra en ciertos meses o se da todo el año. Esto también acota el universo si hace falta.
  2. **Nueva extracción de la base** (hoy solo tenemos el primer diagnóstico y conteos): para las ~28 mil visitas con hospitalización, los diagnósticos, los procedimientos
     y los laboratorios distintos de cada una. **Filtrar `person_id` igual al de la visita** para no mezclar las dos personas de las estancias duplicadas. Son tablas de
     38 M, 47 M y 16,6 M de filas sin índices: 10 a 30 min por consulta; Daniela las corre en DBeaver. Nuevo archivo: `sql/estancias_perfil.sql`.
  3. **Comparar disparadas contra no disparadas** con todas esas variables, midiendo el tamaño de cada diferencia (razón de probabilidades con intervalo) y cuidando la
     confusión (los mayores de edad tienen más diagnósticos). Ver si el patrón explica el aumento de 2023 a 2025.
- **Ojo:** `race_concept_id` está 95 % vacío y la etnia es casi toda la misma: no sirven para este análisis. Las acciones que salgan deben ser de **proceso** (por ejemplo,
  preparar el alta con anticipación en los perfiles de estancia larga), no excluir tipos de pacientes. Los laboratorios sirven como "qué exámenes se pidieron": casi no
  tienen valores numéricos. Todo es asociación, no causa.
- **Entrega:** se suma a `src/factores_estancia.py` y `docs/factores_estancia.md`, más `sql/estancias_perfil.sql`.
- **Estado:** anotada, sin empezar. Cuándo hacerla se decide después de A3 y A1.

### A3. Agrupar diagnósticos (`datos/referencia/mapeo_dx.csv`) · **Daniela**
- **Qué:** los diagnósticos vienen en SNOMED sin jerarquía; agrupar los ~300 más frecuentes (`dx_nombre`, `categoria_dx`). El 62 % de las estancias no tiene
  diagnóstico traducido y el 88 % se registra tarde: sirve para explicar, no para predecir al llegar.
- **Entrega:** `datos/referencia/mapeo_dx.csv` (sí se sube a git: no tiene datos de pacientes). Claude deja el borrador a partir de `dx_frecuencias.csv`; hay que
  revisarlo con el navegador de SNOMED o con alguien del área de salud.
- **Habilita:** A1, A2 y A4.
- **Estado (26-oct): HECHA como borrador + análisis.** Mapeo por reglas (`src/generar_borrador_mapeo_dx.py`, 0,9 % sin clasificar) y análisis de tiempos por grupo (`src/diagnosticos_y_tiempos.py`, `docs/diagnosticos_y_tiempos.md`). Hallazgos: cardiovascular y neurológico reciben cama en ~4 h, musculoesquelético, renal, digestivo y cáncer esperan 22–32 h; y el diagnóstico se registra más cuando la cama llega rápido (sesgo; pregunta B9 al HUN). **Falta:** validación clínica del mapeo por alguien del área de salud.

### A4. Explicar mejor los retrasos (modelo explicativo de la espera) · **Anthony**
- **Qué pide el instructivo:** "qué características están asociadas a retrasos". Hoy todos los factores juntos explican solo el **12 %** de la variación de la espera.
- **Qué hacer:** ficha 3.3 de `docs/fichas_de_tareas.md` (regresión logística de `espera_mas_24h` con variables que se conocen al llegar, validación temporal,
  razones de probabilidades con intervalo, AUC y Brier sin esconderlos). Intentar mejorar sobre el 12 %: perfiles (A1), diagnóstico agrupado (A3), reingreso,
  interacciones (por ejemplo hora × edad). Reportar **qué suma cada variable nueva**. Si no sube, decirlo: es un hallazgo (el resto depende de procesos que la
  base no registra).
- **Entrega:** `notebooks/modelos/modelo_espera_explicativo.ipynb` (sin salidas) y `docs/modelo_espera.md`.
- **Terminado cuando:** la página dice qué factores pesan, cuánto explica el modelo y por qué **no** sirve para alertar a un paciente individual.
- **Insumos:** `tabla_episodios.parquet` filtrada a `estancia_unica == True`; variables permitidas y prohibidas: ficha 3.3. Resultados actuales: `CLAUDE.md` 6b y `docs/HALLAZGOS.md` 4.5.

### A5. Simulación Monte Carlo de camas · **Anthony**
- **Qué pide el instructivo:** "modelos de simulación". Lo que hay hoy (`src/simulacion_altas.py`) es un **análisis de escenarios sobre datos históricos**, no una simulación
  estocástica.
- **Qué hacer** (fichas 3.1 y 3.2): para cada día futuro, sacar cuántos ingresos llegan (del pronóstico semanal de `src/pronostico_demanda.py`, con su incertidumbre),
  asignar a cada uno una estancia tomada de las estancias reales (por edad si ayuda) y contar las camas ocupadas, repitiendo 1.000 veces para obtener una banda.
  Probar hacia atrás en ene–abr 2026 entrenando hasta dic 2025. Escenarios: **A** (altas antes del mediodía, ya resuelto en `src/simulacion_altas.py`: reusar), **B**
  (+10 % de ingresos) y **C** (−5 % de estancia). Idea de Anthony para enriquecerla: que cada llegada tenga un **tipo de recorrido** (alta desde urgencias u
  hospitalización) según patrones por edad y hora; los datos muestran que la mezcla es estable (10,5 %), así que ayuda sobre todo a probar escenarios.
- **Entrega:** `notebooks/simulacion/escenarios.ipynb` (sin salidas), `docs/simulacion.md` y una tabla de escenarios que Daniela sube al drive.
- **Terminado cuando:** el backtest tiene error reportado frente a la persistencia, entre 70 % y 90 % de los días caen dentro de la banda del 80 %, y cada escenario
  tiene supuestos, resultado y una frase para un gerente. Limitación: se desconoce el número de camas.
- **Insumos:** `estancias_hospitalizacion.csv`, `panel_diario.csv`; referencias: `src/simulacion_altas.py`, `src/pronostico_demanda.py`, `docs/HALLAZGOS.md` 4.6 y 5.1.
- **Ojo:** la ocupación observada debe salir de estancias únicas (~113 camas), no de `serie_horaria.csv` viejo.

### A6. Estimar tiempos de atención (componente 3) · **Samuel** (asignado por Daniela el 23-oct; queda para después de los análisis A)
- **Qué pide el instructivo:** "modelos analíticos o predictivos que permitan estimar tiempos de atención". Es decir: cuando llega un paciente, ¿cuántas horas va a estar
  en urgencias, cuánto va a esperar cama o cuánto se va a quedar hospitalizado?
- **Dónde estamos:** por paciente no se logra (esperar más de 24 h: AUC 0,60; estancia: R² cercano a 0; duración de urgencias de quien se va de alta: solo el 38 % tiene
  hora de salida). Lo que sí funciona es pronosticar la demanda y avisar de congestión.
- **Sinergia con Power BI:** la opción 1 (rango por perfil y hora) se puede hacer **dentro del dashboard** como una página "Estimador de espera" (ver `powerbi/roadmap_powerbi.md`, página 8).
- **Opciones para cuando se retome:** (1) dar el tiempo como **rango por perfil y hora** (percentiles) en vez de un número; (2) un modelo de **tiempo restante** que se
  actualice durante la visita con diagnóstico y laboratorios de las primeras horas; (3) estimar la probabilidad de hospitalización al llegar. Cualquiera debe declarar que
  la duración de urgencias está sesgada.

### A7. Sistema repetible de diagnóstico de cuellos de botella · **Por decidir** (idea de Anthony del 23-oct)
- **La idea:** que la lógica con la que encontramos que el cuello de botella eran las camas se pueda **repetir sobre datos nuevos** y diga si el cuello de botella
  sigue siendo ese u otro: (1) detectar cuál segmento tiene más exceso, (2) con la simulación ver qué se dispara, (3) sacar los registros que se disparan,
  (4) caracterizarlos (A2b y A1) y (5) explicar qué hacer. No hay datos en tiempo real: se haría **repitiendo el análisis en una ventana nueva** (reproducir un periodo).
- **Qué ya existe:** el paso 1 (`src/ranking_cuellos.py`, `src/alertas.py`); falta el 2 (A5, Anthony), el 4 (A2b, Daniela) y juntarlos en un solo flujo.
- **Entrega futura:** `src/diagnostico_cuello_botella.py` que reciba un periodo y devuelva un reporte (cuello de botella, qué se dispara, qué tienen en común).
- **Encaja con el instructivo:** "sistemas de alerta temprana" y "herramientas de apoyo a decisiones". **Depende de** A2b, A1 y A5. Se decide después de ellas.

---

## B. Entregables (al final)

### B1. Dashboard de Power BI · **Samuel** — **va de último** (roadmap: `powerbi/roadmap_powerbi.md`; guía para su Claude: `powerbi/CLAUDE.md`)
- **Estado de los datos (23-oct):** el paquete actual es una **versión parcial**. Sirve para las páginas 1 a 7 y 10; las páginas 8 (A6), 9 (B2) y 11 (A1, A2, A2b) y las bandas Monte Carlo de la 7 (A5) esperan análisis pendientes. Empieza cuando A1 a A5 y B2 estén entregados (análisis cerrados hacia el 13-nov); lo que ya está listo se puede ir armando antes. Regenerar el paquete: `python3 src/exportar_para_powerbi.py`.
- **Qué:** ficha de Persona 2: 6 páginas (llegadas, rutas y tiempos, espera de cama, pronóstico y alertas, camas y escenarios, recomendaciones), plantilla `.pbit`, medidas DAX
  y enlace de acceso. El `.pbix` no se sube a git.
- **Insumos:** tablas del drive (`panel_diario.csv`, `serie_horaria.csv`, `serie_diaria.csv`, `estancias_hospitalizacion.csv`, tablas de `resultados/tablas/`). **Volver a descargarlas:
  las versiones anteriores al 23-oct tienen estancias duplicadas.**
- **Terminado cuando:** cada página responde una pregunta del hospital en una frase y el enlace abre sin pedir datos.

### B2. Recomendaciones (componente 4) · **Samuel** *(antes estaba asignada a Anthony; Daniela la reasignó el 23-oct)*
- **Qué:** `docs/recomendaciones.md` es un borrador con 7 recomendaciones, sus números y sus límites. Falta **verificar las fuentes** (solo se leyeron resúmenes de búsqueda),
  ampliar si hace falta y comprobar que cada cifra coincide con `docs/HALLAZGOS.md`.
- **Terminado cuando:** cada recomendación tiene fuente verificada y una cifra o una razón clara de por qué no se puede calcular. Puede empezar antes de que termine A.

### B3. Documento final · **Por decidir (más adelante)**
Estructura sugerida (la del instructivo): contexto, datos y calidad, componentes 1 a 4, modelos y alertas, recomendaciones, limitaciones. Casi todo el contenido ya está en
`docs/HALLAZGOS.md`.

### B4. Presentación · **Por decidir (más adelante)**

---

## C. Datos y coordinación

| # | Tarea | Responsable | Notas |
|---|---|---|---|
| C1 | **Sesión de preguntas con el HUN**: ir con `docs/hun/sesion_de_preguntas.md`, anotar respuestas y actualizar el proyecto con su sección E | Samuel (contacto con el HUN) y Daniela | Las preguntas A1 a A5 de ese documento son las que más cambian los resultados. Por confirmar quién asiste |
| C2 | Correr en DBeaver `sql/exportaciones_base.sql` y verificar que `dx_por_visita` da 566.004 filas y `proc_por_visita` 662.783 (están reconstruidas y sin probar contra la base) | Daniela | |
| C3 | Subir al drive las tablas actualizadas después de cada cambio (`src/exportar_para_equipo.py` y tablas de `resultados/tablas/`) | Daniela | Avisar a Samuel y Anthony cuando haya versión nueva |
| C4 | Opcionales: reingresos depurados (existen sin validar en `tabla_episodios`), huecos TU a TU, decidir si se deduplican las llegadas, Carnaval con efecto distinto en sábado y lunes | Daniela | Solo si sobra tiempo |

---

## Dependencias entre tareas

```
A3 mapeo_dx ──► A1 perfiles ──► A5 simulación (tipo de recorrido, opcional)
      │             │
      ├──► A2 factores de la estancia ──► A5 (estancias por grupo)
      ├──► A2b qué comparten las estancias disparadas (necesita una consulta nueva a la base)
      └──► A4 explicar retrasos (usa A1 y A3)

A2b + A1 + A5 ──► A7 sistema repetible de diagnóstico
A1 a A5 ──► B3 documento final ──► B4 presentación
tablas del drive (C3) ──► B1 Power BI ;  B2 recomendaciones ◄── cifras de A4 y A5
```

## Cómo trabajamos
- Una rama por persona y *pull request* hacia `main`; Daniela revisa. Mensajes de commit en español y **sin datos de la base**.
- Los notebooks se suben **sin salidas**. Las tablas se comparten por el drive privado, nunca por git.
- Todo resultado lleva su limitación al lado y distingue asociación de causa.
- Si cambia una cifra, actualizar `docs/HALLAZGOS.md` y `CLAUDE.md` (sección 6b).
