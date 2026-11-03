# Roadmap del dashboard de Power BI (23-oct-2026)

Plan para construir el dashboard interactivo que pide el instructivo (*"Enlace de acceso al dashboard interactivo desarrollado en Power BI"*; se valora la
**visualización efectiva** y la **comunicación clara** de hallazgos complejos como recomendaciones comprensibles). Responsable: **Samuel**. Apoyo de datos y
especificación: Daniela con Claude. Hallazgos y cifras: `docs/HALLAZGOS.md`. Reparto general: `docs/pendientes_y_reparto.md` (B1).

> **Power BI va de ÚLTIMO (decisión del 23-oct).** Los datos de hoy son una **versión parcial**: faltan perfiles (A1), factores de la estancia (A2, A2b), explicar mejor los retrasos (A4),
> Monte Carlo de camas (A5), estimador (A6) y recomendaciones verificadas (B2). Las páginas 1–7 y 10 se pueden armar con lo que hay; las 8, 9, 11 y las bandas Monte Carlo de la 7 quedan como
> «Pendiente» hasta que esos análisis entreguen. Detalle por página: `especificacion_paginas.md` («Estado de datos»). Guía para el Claude de Samuel: `CLAUDE.md` de esta carpeta.

> **Regla del repo:** el `.pbix` lleva datos incrustados y **no se sube a git**. Se sube la plantilla `.pbit` (sin datos), este roadmap, `medidas_dax.md`, el tema
> de colores y capturas.

---

## 0. Decisiones antes de empezar (checklist)

| # | Decisión | Por qué importa | Recomendación |
|---|---|---|---|
| D1 | **Entorno:** Power BI Desktop **solo corre en Windows**. Daniela tiene Mac | Sin Desktop no se construye bien el modelo ni las medidas | Samuel (o Anthony) construye en Windows; el resto prepara datos y especificación. En Mac solo el navegador (Power BI Service), que sirve para ver y retocar, no para modelar |
| D2 | **Cómo se comparte el enlace.** "Publicar en la web" crea un enlace **público** para cualquiera; compartir por el Service requiere cuentas y licencias de quien lo ve | El instructivo pide un enlace de acceso; los datos son clínicos | Verificar la licencia institucional de Uninorte. No usar el enlace público con filas de pacientes. Preguntar a los organizadores (D2 y D3 de `docs/hun/sesion_de_preguntas.md`) |
| D3 | **Nivel de detalle de los datos publicados:** filas por estancia o solo tablas agregadas | Una tabla con una fila por estancia, aunque sin ids, es información a nivel de paciente | Construir con la tabla de estancias **generalizada** (sin ids y con la fecha solo a mes) y **publicar con tablas agregadas** si los organizadores no autorizan filas |
| D4 | **Idioma y nombres:** español, mismos términos que `docs/HALLAZGOS.md` | Que un gerente entienda sin glosario | Un título por página con la conclusión, no con el nombre del gráfico |
| D5 | **Cifras de control:** el dashboard debe dar los mismos números que `docs/HALLAZGOS.md` (sección 8 de este roadmap) | Evita contradicciones entre documento y dashboard | Verificarlas antes de publicar |

---

## 1. Qué mostramos: mensaje central y páginas

**Tres mensajes que el dashboard debe dejar claros:**
1. **La espera de cama es el cuello de botella y es crónica:** mediana de 18,6 h, percentil 90 de 73,9 h, y los peores casos empeoran (61 h a 80 h).
2. **La causa operativa visible son las altas tardías y la estancia:** el 62,7 % de las altas es de 14 a 19 h, y la ocupación sube por la estancia (+16 %), no por los ingresos.
3. **Se puede anticipar y avisar:** pronóstico de llegadas (7,5 % de error), alertas a media jornada y un simulador para probar escenarios.

| Pág. | Título (mensaje) | Pregunta que responde | Visuales interactivos | Fuente |
|---|---|---|---|---|
| 1 | **Resumen:** la espera de cama es larga y se alarga | ¿Cómo está el hospital hoy? | 6 tarjetas (espera mediana y p90, % con más de 48 h, ingresos por día, camas ocupadas, estancia media), tendencia anual, filtro de año | `bi_estancias`, `panel_diario`, `ocupacion_por_anio` |
| 2 | **Llegadas:** cuándo llega la gente | ¿Cuándo hay más demanda? | Mapa de calor día de la semana × hora (matriz con formato condicional), serie diaria con festivos y Carnaval marcados; filtros de año, tipo de visita y edad | `bi_llegadas`, `panel_diario` |
| 3 | **Flujo del paciente:** qué ruta sigue y cuánto dura | ¿Por dónde pasan los pacientes? | Rutas (69 % urgencias con alta, 19 % solo llegada, 10 % urgencias y cama...) con diagrama de flujo o árbol de descomposición; tiempos por ruta (p25, mediana, p75, p90) y **% con duración medida** | `cobertura_por_ruta`, `resumen_por_ruta` |
| 4 | **Espera de cama:** quién espera más y cuándo | ¿Qué factores se asocian a esperar más? | Histograma de la espera por tramos; mediana y p90 por **hora de llegada**; **% que recibe cama al día siguiente** por hora; por edad y tipo de visita; **urgencias vs hueco**; filtros sincronizados. Nota fija: "asociación, no causa" | `bi_estancias`, `asignacion_cama_por_hora_llegada`, `importancia_factores` |
| 5 | **Altas tardías y camas:** el mecanismo | ¿Por qué se espera hasta la tarde? | Líneas por hora del día de altas, ingresos a cama y llegadas; ocupación por hora; ocupación = ingresos × estancia por año | `altas_ingresos_llegadas_por_hora`, `escenario_camas_por_hora`, `ocupacion_por_anio` |
| 6 | **Pronóstico y alertas** | ¿Qué viene y cuándo avisar? | Real vs pronóstico con banda del 80 % (selector de horizonte 1 o 7 días), pronóstico semanal de ingresos, tabla de alertas con precisión y detección, **tabla de días atípicos** con detalle (drill-through) | `pronostico_*`, `alertas_*`, `dias_atipicos` |
| 7 | **Simulador de camas:** ¿qué pasa si...? | ¿Qué efecto tiene cambiar ingresos, estancia o altas? | **Tres controles deslizantes** (what-if): ingresos (−20 a +20 %), estancia (−20 a +10 %) y % de altas de la tarde adelantadas (0 a 100 %). Resultados: camas ocupadas, camas libres a las 12 h y espera evitada (cota y estimación). Más adelante, las bandas Monte Carlo de Anthony (A5) | `escenarios_little`, `escenario_altas_antes`, `escenario_camas_por_hora` |
| 8 | **Estimador de espera** (A6, de Samuel) | ¿Cuánto esperaría un paciente como este? | Elegir hora de llegada, grupo de edad y tipo de visita y ver el **rango típico** (p25, mediana, p75, p90) con el n de casos y la advertencia de que no es una predicción individual | `bi_estancias` |
| 9 | **Recomendaciones** | ¿Qué se hace con esto? | Tabla de las 7 recomendaciones (prioridad, impacto, límite, fuente) con filtro por prioridad y vínculo a la página de evidencia | `docs/recomendaciones.md` (B2) |
| 10 | **Metodología y límites** | ¿Qué tan confiable es? | Embudo de datos (3,28 M etapas a 337 mil episodios), problemas de calidad, lo que no se sabe | `docs/HALLAZGOS.md` 2 y 7 |
| 11 *(cuando existan)* | **Perfiles y estancias largas** | ¿Qué tipo de pacientes esperan o se quedan más? | Comparación por perfil; meses y características de las estancias disparadas | salidas de A1, A2 y A2b (Daniela) |

Máximo 8 a 10 páginas visibles. Si el tiempo aprieta, el orden de prioridad es **1, 4, 5, 7, 6, 2, 9, 3, 10, 8**.

---

## 2. Recursos de interactividad que conviene usar
- **Segmentadores sincronizados** entre páginas (año, tipo de visita, grupo de edad) con un botón "Restablecer filtros".
- **Información sobre herramientas** (tooltips) con una página pequeña: al pasar sobre una hora se ve el n de casos, la mediana y el percentil 90.
- **Profundizar (drill-through)** de un día atípico o de una hora hacia el detalle.
- **Parámetros "what-if"** para el simulador (página 7).
- **Marcadores (bookmarks)** para alternar vistas, por ejemplo "mediana / percentil 90" o "mostrar solo el periodo de prueba del pronóstico".
- **Formato condicional** en el mapa de calor y en la tabla de alertas.
- **Parámetros de campos** para cambiar la medida de un gráfico (espera, urgencias antes de la cama, hueco).
- *Opcional:* visual de "Influencers clave" (de IA) sobre `espera > 24 h` como complemento a la página 4. **Ojo:** explica asociaciones y debe llevar la misma advertencia que el modelo explicativo (explica poco).
- Visuales personalizados (diagrama Sankey, diagrama de cajas) vienen de AppSource y pueden estar bloqueados en la cuenta institucional: **plan B** con barras apiladas y la tabla de percentiles.

---

## 3. Qué recursos y archivos necesita (y cuáles no)

**No necesita la base de datos ni el pipeline.** Todo sale de tablas ya calculadas que Daniela entrega por el drive privado. Tampoco el repositorio es obligatorio, pero sí le sirven estos archivos de él: este roadmap, `docs/HALLAZGOS.md` (cifras de control y textos), `docs/recomendaciones.md` y los gráficos de `resultados/graficos/` como referencia visual.

| Tabla para Power BI | Qué contiene | Filas aprox. | Sale de | Estado |
|---|---|---|---|---|
| `panel_diario.csv` | Un día por fila: llegadas, ingresos a cama, altas, ocupación, espera, festivo | 1.216 | `src/exportar_para_equipo.py` | **Existe** |
| `serie_horaria.csv` | Una hora por fila: llegadas, ocupación | ~29 mil | `src/preparar_variables.py` | **Existe** (volver a descargar: antes del 23-oct tenía estancias duplicadas) |
| `bi_estancias.csv` | Una estancia por fila **sin ids**: año, mes, día de la semana, hora de llegada, grupo de edad, sexo, tipo de visita, espera, urgencias antes de la cama, hueco, estancia | 25.777 | `src/exportar_para_powerbi.py` | **Listo** (paquete parcial `powerbi.zip`) |
| `bi_llegadas.csv` | Llegadas agregadas: año, mes, día de la semana, hora, tipo de visita, grupo de edad → n | ~100 a 200 mil | `src/exportar_para_powerbi.py` | **Listo** |
| Tablas de resultados de `resultados/tablas/` | Ranking, espera por hora, altas por hora, ocupación por año, escenarios, pronóstico, alertas, días atípicos, cobertura y tiempos por ruta, importancia de factores | 5 a 1.200 cada una | Scripts de `src/` | **Existen** (~25 archivos, menos de 1 MB en total) |
| Calendario | Fechas, año, mes, día, festivo | — | Se crea dentro de Power BI con DAX (`CALENDAR`) | Samuel |

Tamaño total pequeño (unos pocos MB). La tabla `estancias_hospitalizacion.csv` actual trae ids y fechas completas: **no usarla en el dashboard**, usar `bi_estancias.csv`.

**Software y cuentas:** Power BI Desktop (Windows), cuenta de Power BI Service con permiso para publicar y compartir (verificar con Uninorte), y acceso al drive del equipo.

---

## 4. Modelo de datos (esquema en estrella)

```
Calendario (fecha, año, mes, día de la semana, festivo, carnaval)
   ├── panel_diario            (1 fila por día)
   ├── pronostico_diario       (1 fila por día de prueba)
   ├── dias_atipicos           (1 fila por día)
   └── bi_estancias            (por año y mes; sin fecha exacta)
Dimensiones pequeñas (compartidas por los segmentadores):
   Edad (grupo_edad)   TipoVisita   Hora (0 a 23, franja)   DiaSemana
   ├── bi_estancias   ├── bi_llegadas   └── tablas de resultados con esas columnas
Tablas sueltas para el simulador: escenarios_little, escenario_altas_antes (con una rejilla de 0 a 100 %), escenario_camas_por_hora
```
Regla: una tabla de hechos por tema, relaciones de uno a varios desde las dimensiones, filtro en una sola dirección, y las medidas se escriben en una tabla `Medidas` aparte.

---

## 5. Medidas DAX clave (ejemplos para `powerbi/medidas_dax.md`)

```DAX
Espera mediana (h)   = MEDIAN ( bi_estancias[espera_h] )
Espera p90 (h)       = PERCENTILE.INC ( bi_estancias[espera_h], 0.9 )
% con más de 24 h    = DIVIDE ( COUNTROWS ( FILTER ( bi_estancias, bi_estancias[espera_h] > 24 ) ), COUNTROWS ( bi_estancias ) )
Estancias            = COUNTROWS ( bi_estancias )
Ingresos por día     = DIVIDE ( SUM ( panel_diario[ingresos_a_cama] ), COUNTROWS ( panel_diario ) )
Camas ocupadas (esc) = [Camas base] * ( 1 + [Delta ingresos] ) * ( 1 + [Delta estancia] )      -- Little; los deltas son parámetros what-if
Camas libres a las 12 h = LOOKUPVALUE ( escenario_camas_por_hora[camas_libres_adicionales], escenario_camas_por_hora[hora], 12 )
Espera evitada (cota) = LOOKUPVALUE ( escenario_altas_antes[cota_superior_pct_del_exceso], escenario_altas_antes[proporcion_movida], [Proporcion altas] )
```
Mostrar siempre el **n de casos** junto a una mediana o un percentil y ocultar los grupos con menos de 30 casos.

---

## 6. Diseño visual
- **Tema** con paleta de la guía de visualización del proyecto: azul `#2a78d6`, naranja `#eb6834`, aqua `#1baf7a`, grises `#52514e` y `#e5e4df`, fondo `#fcfcfb`. Un archivo `powerbi/tema.json` (Claude lo prepara).
- Una idea por página, título con la conclusión, tarjetas arriba, filtros a la izquierda o arriba **en una sola fila**, rejilla y ejes discretos.
- Mismo color para la misma cosa en todo el dashboard (azul = espera, naranja = referencia o escenario).
- Leyenda siempre que haya dos o más series; etiquetas directas solo en lo importante.
- Nota fija en las páginas explicativas: *"Asociación, no causa"*, y en el pronóstico: *"Prueba en ene–abr 2026; mayo cae por posible carga incompleta"*.
- Probar en pantalla de proyector y con modo de alto contraste; no usar solo el color para distinguir.

---

## 7. Roadmap por etapas

> **Calendario tentativo (Power BI va de último):** análisis A1–A5 y B2 cerrados hacia el **13-nov**; construcción del dashboard **16–27 nov**; colchón 28–30 nov. Riesgo: son ~2 semanas para 10 páginas.
> Mitigación: las decisiones D1–D3 (Windows, licencia, nivel de detalle) y el modelo con las páginas 1–7 y 10 se adelantan mientras llegan los análisis; las fechas de la tabla son las del plan original y se corren en esa medida.

| Etapa | Fechas | Qué se hace | Responsable | Terminado cuando |
|---|---|---|---|---|
| **0. Decisiones y entorno** | 24 a 27 oct | Resolver D1 a D3: Windows, licencia y enlace, nivel de detalle. Descargar del drive las tablas actuales | Samuel y Daniela | Samuel abre Power BI Desktop y carga `panel_diario.csv` |
| **1. Datos y modelo** | 27 oct a 2 nov | Claude y Daniela crean `src/exportar_para_powerbi.py` (`bi_estancias`, `bi_llegadas`), `powerbi/tema.json` y `powerbi/medidas_dax.md`. Samuel arma el modelo en estrella y el calendario | Daniela y Claude; Samuel | Modelo cargado, relaciones correctas y las cifras de control de la sección 8 coinciden |
| **2. Páginas 1 a 4** | 3 a 9 nov | Resumen, llegadas, flujo del paciente y espera de cama, con segmentadores sincronizados | Samuel | Cada página responde su pregunta en una frase y se prueba con los filtros |
| **3. Páginas 5 a 8** | 10 a 16 nov | Altas y camas, pronóstico y alertas, **simulador what-if**, estimador de espera. Integrar Monte Carlo de A5 y A1 y A2 si ya están | Samuel (con datos de Anthony y Daniela) | El simulador reproduce `escenarios_little.csv` con los deslizadores en su valor base |
| **4. Recomendaciones y metodología** | 17 a 20 nov | Páginas 9 y 10 con las recomendaciones verificadas (B2). Control de calidad completo | Samuel; Daniela revisa | Todas las cifras de control coinciden; sin errores visuales |
| **5. Publicación y entrega** | 21 a 27 nov | Publicar, probar el enlace con una cuenta sin acceso previo, exportar `.pbit` y capturas, escribir la sección "Dashboard" del documento | Samuel y Daniela | El enlace abre y muestra datos sin pedir nada a quien lo recibe |
| **Colchón** | 28 a 30 nov | Correcciones y presentación | Todos | — |

Dependencias: las páginas 11 (perfiles y estancias) y las bandas Monte Carlo de la página 7 esperan a A1, A2, A2b y A5. Las páginas 1 a 10 **no** dependen de ellas.

---

## 8. Cifras de control (el dashboard debe dar estos números)

| Qué | Valor esperado |
|---|---|
| Estancias con espera de cama | 25.373 (Q3) o 27.162 (pipeline) |
| Espera de cama: mediana / p75 / p90 | 18,6 / 37,9 / 73,9 h |
| % con más de 24 h / más de 48 h | 43,9 % / 20 % |
| Urgencias antes de la cama / hueco, % de las horas | 79 % / 21 % |
| Ingresos a cama por día / camas ocupadas | ~20 / ~100 |
| Estancia media y camas por año | 2023: 4,57 d y 94; 2024: 4,90 d y 101; 2025: 5,31 d y 105 |
| Altas entre 14:00 y 18:59 / antes del mediodía | 62,7 % / 14 % |
| Escenario 30 % de altas adelantadas | 5,1 camas libres a las 12 h; espera evitada: máximo 8,3 %, estimación 2,9 % |
| Llegadas: error del pronóstico a 1 día / 7 días | 7,5 % / 8,8 % |
| Alerta de día congestionado a las 12 h | 28 alertas, 15 aciertos (precisión 54 %, detección 83 %) |
| Días atípicos (llegadas / ingresos / espera) | 14 / 9 / 7 |

---

## 9. Riesgos y plan B
- **Sin Windows o sin licencia para compartir:** publicar un PDF del dashboard y capturas de pantalla de cada página dentro del documento, más un video corto navegando; y mantener el `.pbit` en el repo. El instructivo pide enlace, así que resolver D1 y D2 primero.
- **Visuales personalizados bloqueados:** usar barras apiladas y tablas de percentiles.
- **Datos a nivel de fila no autorizados:** publicar solo con tablas agregadas; se pierden los percentiles dinámicos por filtro (se precalculan por año, hora y edad).
- **Cifras que cambian** (por una respuesta del HUN o por correcciones): todas salen de tablas regenerables con los scripts; actualizar y volver a cargar.
- **Dashboard demasiado cargado:** respetar el máximo de páginas y el orden de prioridad de la sección 1.

---

## 10. Qué puede preparar Claude cuando lo pidan
1. `src/exportar_para_powerbi.py` y los dos archivos `bi_*.csv` (verificados contra las cifras de control).
2. `powerbi/tema.json` y `powerbi/medidas_dax.md` completos.
3. Esquemas de cada página (qué visual va dónde) y textos de títulos y notas.
4. Revisión de lo que Samuel construya contra las cifras de control.
Claude **no puede** construir ni abrir el `.pbix` (es un archivo de Windows): esa parte la hace Samuel en Power BI Desktop.
