# Plan de acción — Data Challenge HUN 2026 (actualizado 23-oct-2026)

> **Pendientes y reparto actual: `docs/pendientes_y_reparto.md`** (quién hace qué, con entrega y criterio de terminado).

> **Estado:** las fases 0 a 7 del análisis de cuellos de botella están hechas (ver `CLAUDE.md` sección 9 y `docs/HALLAZGOS.md`). Quedan el dashboard, los notebooks del equipo, el documento final y la presentación. Esta página conserva el plan original; las secciones 2 a 5 (revisiones posibles, reparto y calendario) son de antes de terminar el análisis.

Equipo de 3: **Daniela**, **Samuel** (Persona 2) y **Anthony** (Persona 3). Daniela y Anthony usan Claude Code; Samuel trabaja con lo que ellos le pasan
(tablas agregadas por un drive privado, nunca por git) y con las herramientas que ya tengan.

## 0. Cuello de botella: definición congelada (21-oct-2026)

> **Cuello de botella** = segmento del recorrido donde el paciente espera un recurso, que muestra un exceso de
> tiempo frente a una referencia de "cuando funciona bien", con impacto alto (volumen × retraso) y que se agrava
> con la carga.

Por qué esta definición (para no reabrirla): un **atípico** es un caso raro; un **cuello de botella** es un retraso
que le pasa a muchos. El promedio no sirve como referencia porque el propio cuello de botella lo infla. Por eso:

1. **Segmento** = duración de una etapa (TU, HOSP), hueco entre dos etapas consecutivas, o tiempo entre dos hitos
   (inicio del episodio → inicio de la primera HOSP = espera de cama). Las etapas van pegadas, así que parte de la
   espera está *dentro* de TU. No se comparan segmentos de tipos distintos entre sí (HOSP es servicio clínico).
2. **Referencia** (tres, y el ranking debe ser el mismo con las tres): (a) mediana del mismo segmento con baja
   carga (quintil más bajo de llegadas de las 6 h previas); (b) percentil 25 del segmento; (c) meta del HUN, si
   la dan. Se calculan por estrato (hospitalizado o no × adulto/niño).
3. **Impacto** = Σ `max(0, horas − referencia)` = horas-paciente perdidas; más el % de episodios con exceso mayor
   a 6 h y a 24 h ("le pasa a todos").
4. **Dependencia de la carga:** el tiempo del segmento dividido entre su referencia, por decil de carga (llegadas
   de 6 h, ocupación, hora, día). Sube fuerte con la carga → falta capacidad; varía por hora pero no por carga →
   proceso o turnos; plano pero largo → proceso lento. No todo aumento con la carga es cuello de botella: se compara
   la pendiente entre segmentos.
5. **Dos niveles de alerta:** de sistema (ocupación proyectada mayor al umbral) y de paciente (tiempo mayor al p90
   de su referencia). Los atípicos sirven a la alerta, no definen el cuello de botella.
6. **Agrupar por ruta:** solo de forma gruesa (`ruta_simple`) para comparar parejo; nunca por cadena exacta
   (se fragmenta, y la ruta se conoce solo al final).

Límites que se declaran: la referencia es interna al hospital; la espera dentro de TU no se separa de la atención;
la duración de TU de quienes se van de alta no se mide (~58 % sin hora de salida); el número de camas no está en
la base.

### Fases y consultas (`sql/consultas_cuellos_botella.sql`)

| Fase | Qué se hace | Consulta | Puerta de decisión |
|---|---|---|---|
| 0 | Enviar al HUN: número de camas por año y meta de tiempo | — | — |
| 1 | Cuadrar la base y confirmar dónde está el tiempo muerto entre etapas | Q0, Q1, Q2 | Q0 cuadra con CLAUDE.md; Q1 y Q2 dentro de los rangos esperados |
| 2 | Construir episodios y segmentos; inventario: n, % medido, percentiles, sesgo de medición | Q3 | Elegir segmentos candidatos (≥ ~50 % medidos, sin sesgo claro) |
| 3 | Referencias, exceso, impacto y ranking (con las tres referencias) | Q3 | ¿El orden se mantiene entre referencias? |
| 4 | Dependencia de la carga y controles por edad y diagnóstico | Q3, Q4 | Clasificar cada segmento (capacidad, turnos, proceso) |
| 5 | Altas tardías por hora; factores del exceso | Q3 (+ dx y laboratorios ya exportados) | ¿Se sostiene la hipótesis de altas tardías? |
| 6 | Demanda, estancias, simulación de camas, escenarios | Q3, Q4 | La diferencia ocupación por horas (~100) frente a Little (~144) ya tiene explicación (21-oct): el 41 % de los episodios hospitalizados tiene una estancia "gemela" replicada entre dos personas. **Decidido el 22-oct: se cuenta cada estancia una vez** (~113 camas, ~22 ingresos/día; CLAUDE.md 4.6). Falta medir si las llegadas también están infladas |
| 7 | Alertas de sistema y de paciente, probadas sobre días pasados | Q3, Q4 | Pocas alertas por día y con anticipación |
| 8 | Power BI, documento, README | — | — |

## 1. Qué problemas encontramos (en palabras simples)

| # | Problema | Qué significa | Qué hicimos |
|---|---|---|---|
| 1 | **Visitas repetidas** (~30 % de la base) | Muchas visitas aparecen dos veces con las mismas etapas, a la misma hora al segundo. Si se cuentan todas, el hospital parece tener el triple de llegadas. | Se borran solo cuando el paciente es el mismo. Cuando el paciente es otro, se conserva la visita pero se quitan las etapas repetidas. |
| 2 | **Dos personas con la misma línea de tiempo** | En unas 280.000 visitas, dos pacientes distintos (edades muy diferentes, ids casi consecutivos) tienen exactamente los mismos pasos. Parece un registro que se replicó de una persona a otra. No sabemos cuál es la "real". | Probado con una consulta a la base (75 pares). Pregunta enviada al HUN. |
| 3 | **Falta la hora de salida** | A ~55 % de quienes se van de alta desde urgencias no se les registró cuándo terminó la atención. No es error nuestro: el dato no existe. Quien se hospitaliza sí tiene todos los tiempos. | Esos casos se marcan "sin duración", no como "0 horas". No se mide la duración de urgencias; se mide la espera de cama. |
| 4 | **Diagnósticos tardíos y sin agrupar** | El 88 % se anota después de las primeras 2 h, y vienen en un código (SNOMED) sin grupos. | Sirven para explicar, no para predecir "al llegar". Hay que agruparlos a mano (`mapeo_dx.csv`). |
| 5 | **El tipo de visita no es confiable** | Visitas "ambulatorias" incluyen urgencias y hospitalización. | Usamos las etapas, no el tipo de visita. |
| 6 | **Ocupación incompleta** | Solo vemos a los pacientes de esta base; no sabemos cuántas camas tiene el hospital. La ocupación casi no cambia la espera, pero puede ser por esto. | Se pide al HUN el número de camas. |

Resultado actual (23-oct, con estancias en cama contadas una sola vez): 337.194 episodios; **espera de cama: mediana 18 h, percentil 90 de 71,5 h, 43 % espera más de 24 h**;
la espera es más larga si se llega a media tarde (mediana ~25 h entre las 13 y las 16 h) que de madrugada (12–15 h). Todos los hallazgos con cifras y fuentes: `docs/HALLAZGOS.md`.

## 2. Qué más podemos revisar (en orden de utilidad)

1. **¿Los casos sin hora de salida se parecen a los que sí la tienen?** (edad, hora, día). Si se parecen, podemos
   hablar de la duración en urgencias con confianza. Solo requiere los datos que ya tenemos. *(Claude, 1 día)*
2. **Hora del último laboratorio como piso de la hora de salida.** Una consulta pesada (10–30 min) agregando
   `MIN` y `MAX` de `measurement_datetime` por visita. Daniela la corre una vez. *(Opcional; solo si 1 sale bien.)*
3. **Quitar de diagnósticos, procedimientos y laboratorios los registros que una visita tiene de otra persona**
   (filtro `person_id` igual al de la visita). Consultas pesadas; hacerlo solo si el tiempo alcanza.
4. **Mapeo de diagnósticos** (`mapeo_dx.csv`): bloquea las gráficas por diagnóstico.

No hace falta bajar otras tablas por ahora.

## 3. Qué piden los organizadores y cómo lo repartimos

Los entregables son tres: **documentación**, **repositorio en GitHub** y **dashboard en Power BI**. Se valora:
hallazgos estratégicos, interpretabilidad, visualización efectiva y comunicación clara. Las propuestas pueden incluir
modelos predictivos, dashboards, sistemas de alerta temprana, análisis de patrones y **modelos de simulación**.
Cada persona es dueña de un frente y de una carpeta del repo, para trabajar a la vez sin conflictos.
**Las tareas detalladas, con datos, reglas y criterio de terminado, están en `docs/fichas_de_tareas.md`.**

| Frente | Responsable | Carpeta del repo | Qué entrega |
|---|---|---|---|
| **Capacidad de camas, simulación y modelo explicativo** | **Persona 3 (Anthony)** | `notebooks/modelos/`, `notebooks/simulacion/`, `docs/` | Proyección de camas ocupadas con alerta de saturación, simulación de escenarios, análisis de los factores de la espera y recomendaciones con números |
| **Dashboard Power BI, recomendaciones y contacto con el HUN** | **Persona 2 (Samuel)** | `powerbi/`, `docs/hun/` | Dashboard de 6 páginas, plantilla `.pbit`, sección "Dashboard" del documento y correo al HUN |
| **Modelo A (llegadas e ingresos), días atípicos, datos y documento** | **Daniela con Claude** | `src/`, `sql/`, `docs/`, `datos/referencia/` | Pronóstico de demanda con alerta, días atípicos, scripts y tablas, consultas en DBeaver, revisión de *pull requests*, commits y documento final |

Todos los frentes se alimentan de las tablas que Daniela exporta al drive privado dos veces por semana
(`src/exportar_para_equipo.py`). Qué hace cada modelo y por qué cambiaron: `docs/fichas_de_tareas.md`.

## 4. Calendario

| Semana | Daniela + Claude | Persona 2, Samuel (Power BI, recomendaciones y HUN) | Persona 3, Anthony (camas, simulación, modelo explicativo) | Entregable |
|---|---|---|---|---|
| **20–26 oct** | Exportar `panel_diario` y `estancias_hospitalizacion` al drive. Borrador de `mapeo_dx.csv`. Empezar ficha D.1 | **Correo al HUN.** Instalar Power BI y conectar tablas; página 1 de prueba | Ficha 3.1 pasos 1 y 2: describir estancias y ajustar la distribución | Repo |
| **27 oct–2 nov** | Terminar Modelo A (D.1); componentes 1 y 2; borrador del documento | Páginas 1 a 3 | Ficha 3.1 pasos 3 a 5: simulación, backtest y alerta | Doc + primeras páginas de Power BI |
| **3–9 nov** | Días atípicos (D.2); revisar el modelo de camas; metodología y limitaciones | Página 4 (pronóstico y atípicos) | Terminar `modelo_camas.md`; ficha 3.3 (modelo explicativo) | Repo + doc |
| **10–16 nov** | Respuestas del HUN; consolidar resultados | Página 5 (camas y escenarios) | Ficha 3.2 (escenarios) y ficha 3.4 (recomendaciones) | Power BI + doc |
| **17–23 nov** | README técnico; reproducir todo desde cero | Página 6 y pulido; publicar el enlace; sección "Dashboard" | Páginas `modelo_camas.md`, `simulacion.md`, `recomendaciones.md` | Los 3 entregables |
| **24–30 nov** | Colchón y presentación | Colchón | Colchón | — |

## 5. Cómo trabajamos a la vez en el repositorio
- **Cada quien en su carpeta** (tabla de la sección 3): casi no hay conflictos. `src/` es solo de Daniela; si alguien
  necesita un cambio, lo pide.
- **Una rama por persona** (`powerbi`, `docs`, `modelos`) y *pull request* hacia `main`; Daniela revisa. Mensajes de
  commit en español y sin datos.
- **Nada de datos de la base en git.** `datos/crudos`, `datos/procesados`, `resultados/tablas`, `resultados/excel` y los
  `.pbix` están ignorados. Antes de cada commit: `git status` y comprobar que no hay `.csv`, `.parquet`, `.xlsx` ni `.pbix`.
  La única excepción es `datos/referencia/` (listas hechas a mano, como `mapeo_dx.csv`, sin datos de pacientes).
- Las tablas agregadas se comparten por un drive privado del equipo, con el nombre y la fecha de la corrida.
- Las decisiones de método viven en `CLAUDE.md` (sección 5); para cambiar una, se discute antes.
- Cada hallazgo en el documento lleva su limitación al lado (por ejemplo, la falta de hora de salida).
- No pulir más la limpieza: lo que queda no cambia las medianas de la espera de cama.
