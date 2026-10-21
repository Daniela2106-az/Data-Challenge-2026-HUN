# Plan de acción — Data Challenge HUN 2026 (actualizado 20-oct-2026)

Equipo de 3. Solo una persona tiene Claude (**Daniela**); las otras dos trabajan con lo que ella les pasa
(tablas agregadas por un drive privado, nunca por git) y con las herramientas que ya tengan.

## 1. Qué problemas encontramos (en palabras simples)

| # | Problema | Qué significa | Qué hicimos |
|---|---|---|---|
| 1 | **Visitas repetidas** (~30 % de la base) | Muchas visitas aparecen dos veces con las mismas etapas, a la misma hora al segundo. Si se cuentan todas, el hospital parece tener el triple de llegadas. | Se borran solo cuando el paciente es el mismo. Cuando el paciente es otro, se conserva la visita pero se quitan las etapas repetidas. |
| 2 | **Dos personas con la misma línea de tiempo** | En unas 280.000 visitas, dos pacientes distintos (edades muy diferentes, ids casi consecutivos) tienen exactamente los mismos pasos. Parece un registro que se replicó de una persona a otra. No sabemos cuál es la "real". | Probado con una consulta a la base (75 pares). Pregunta enviada al HUN. |
| 3 | **Falta la hora de salida** | A ~55 % de quienes se van de alta desde urgencias no se les registró cuándo terminó la atención. No es error nuestro: el dato no existe. Quien se hospitaliza sí tiene todos los tiempos. | Esos casos se marcan "sin duración", no como "0 horas". No se mide la duración de urgencias; se mide la espera de cama. |
| 4 | **Diagnósticos tardíos y sin agrupar** | El 88 % se anota después de las primeras 2 h, y vienen en un código (SNOMED) sin grupos. | Sirven para explicar, no para predecir "al llegar". Hay que agruparlos a mano (`mapeo_dx.csv`). |
| 5 | **El tipo de visita no es confiable** | Visitas "ambulatorias" incluyen urgencias y hospitalización. | Usamos las etapas, no el tipo de visita. |
| 6 | **Ocupación incompleta** | Solo vemos a los pacientes de esta base; no sabemos cuántas camas tiene el hospital. La ocupación casi no cambia la espera, pero puede ser por esto. | Se pide al HUN el número de camas. |

Resultado actual: 337.194 episodios; 37 % con duración medida y 8 % con un mínimo conocido (v3.6); **espera de cama: mediana 22,4 h, 48 % espera más de 24 h**;
la espera es más larga si se llega en la tarde (26,8 h) que de madrugada (16,0 h).

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
| **Capacidad de camas, simulación, modelo explicativo y recomendaciones** | **Persona 3** | `notebooks/modelos/`, `notebooks/simulacion/`, `docs/` | Proyección de camas ocupadas con alerta de saturación, simulación de escenarios, análisis de los factores de la espera y recomendaciones con números |
| **Dashboard Power BI y contacto con el HUN** | **Persona 2** | `powerbi/`, `docs/hun/` | Dashboard de 6 páginas, plantilla `.pbit`, sección "Dashboard" del documento y correo al HUN |
| **Modelo A (llegadas e ingresos), días atípicos, datos y documento** | **Daniela con Claude** | `src/`, `sql/`, `docs/`, `datos/referencia/` | Pronóstico de demanda con alerta, días atípicos, scripts y tablas, consultas en DBeaver, revisión de *pull requests*, commits y documento final |

Todos los frentes se alimentan de las tablas que Daniela exporta al drive privado dos veces por semana
(`src/exportar_para_equipo.py`). Qué hace cada modelo y por qué cambiaron: `docs/fichas_de_tareas.md`.

## 4. Calendario

| Semana | Daniela + Claude | Persona 2 (Power BI y HUN) | Persona 3 (camas, simulación, recomendaciones) | Entregable |
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
