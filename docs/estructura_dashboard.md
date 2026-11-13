# Estructura del dashboard (Dash) · Data Challenge HUN 2026

**Para:** Samuel · **De:** Daniela · **Versión:** 3-nov-2026 (reescrita: solo estructura, sin cifras)

Este documento dice **cómo está organizado el dashboard y qué lleva cada sección**. No trae los datos ni los resultados: esos están en los documentos del repositorio y en las tablas (`resultados/tablas/`); aquí se dice **qué va en cada página, qué controles tiene, qué gráficas y de qué archivo salen**. Las cifras que debe mostrar cada gráfica se toman de los documentos fuente (columna «Fuente»), para que haya una sola versión de cada número.

**Herramienta: Dash (Python + Plotly), solo Dash.** Los organizadores lo aceptaron. El dashboard NO se conecta a la base del hospital: lee tablas agregadas.

**Esqueleto técnico del 10-nov (Anthony):** `dashboard/main.py` es ahora el único punto de entrada (un solo
proceso, un solo puerto 8050, patrón multipágina de Dash `use_pages=True`); cada página vive en
`dashboard/pages/*.py` con `dash.register_page()` y la barra de navegación se arma sola desde
`dash.page_registry`. Hoy solo tiene 4 páginas (pronóstico, paciente en espera/A6, planeación de camas/A5,
perfiles y picos) — es el patrón técnico para que Samuel extienda con el resto de la estructura de abajo
(0 a 5), no la estructura completa en sí. Las 5 apps sueltas anteriores (`app.py`, `estimador.py`, `camas.py`,
`perfiles.py`, `menu.py`) se retiraron a favor de este único proceso.

---

## 1. Orden del dashboard (de lo general a lo específico)

Menú lateral con cinco partes, en este orden. El orden cuenta la historia: primero qué problema es y qué datos hay, luego qué encontramos, luego qué podemos anticipar, y al final qué proponemos.

| Parte | Qué responde | Páginas |
|---|---|---|
| **0. Inicio** | ¿De qué trata esto? | Portada |
| **1. Contexto** | ¿Qué datos hay y qué tan confiables son? | 1.1 a 1.6 |
| **2. Resultados** | ¿Qué está pasando en el hospital? | 2.1 a 2.8 |
| **3. Predicción y anticipación** | ¿Qué podemos prever y avisar? | 3.1 a 3.5 |
| **4. Recomendaciones** | ¿Qué hacemos con esto? | 4.1 |
| **5. Anexos** | Límites, glosario, repositorio | 5.1 a 5.3 |

---

## 2. Plantilla de cada página

Todas las páginas se ven igual, para que el usuario no se pierda:

1. **Título = la conclusión** de la página (no el nombre del tema).
2. **Pregunta** en una línea debajo del título.
3. **Controles** en una fila arriba (máximo tres).
4. **Gráficas** (una a tres). Cada una con su n de casos visible y un tooltip.
5. **Panel de contexto** al lado: *Qué estás viendo* · *Cómo se calculó* · *Qué significa para el hospital* · *Qué NO dice*.
6. **Pie:** fuente del dato (archivo y script) y fecha.
7. **Enlaces:** «Cómo se calculó» lleva a la página de metodología; «Ver el análisis completo» lleva al documento del repositorio.

Las páginas de la Parte 1 y la Parte 5 son de **texto, tablas y figuras fijas**; las de las Partes 2 a 4 son **interactivas**.

---

## 3. Reglas que valen para todo el dashboard

1. **Asociación, no causa.** La advertencia va junto al hallazgo, no en un anexo.
2. **Mostrar siempre el n** y **ocultar los grupos con menos de 30 casos**.
3. **Periodo confiable de las etapas:** del 1-feb-2023 al 9-abr-2026 (explicación en la página 1.3). Lo posterior se dibuja en gris con la etiqueta «registro incompleto» o no se dibuja.
4. **Una estancia = una vez** (las duplicadas ya vienen resueltas en las tablas).
5. **Cifras vigentes:** las de `docs/HALLAZGOS.md` y de `CLAUDE.md` secciones 4.8 a 4.10. Las de documentos viejos (por ejemplo, las del 22-oct) están superadas.
6. **Términos clínicos en palabras simples:** cada término raro lleva su explicación (glosario, página 5.2).
7. **Privacidad:** solo tablas agregadas. Nada con una fila por paciente se publica ni se sube a GitHub. Nunca contraseñas en el código.
8. **Una sola escala por gráfico** (sin dos ejes y), eje desde 0 en barras, azul = lo observado, naranja = referencia o escenario, gris = periodo no confiable.
9. **No inventar:** lo que depende de un análisis que no existe se deja con el marcador «Pendiente: …».

---

# PARTE 0 — INICIO

## 0.1 Portada
- **Contenido:** nombre del reto y del equipo; la pregunta central del reto; una frase de qué se hizo; tarjetas con las cinco cifras principales (espera de cama, ingresos por día, camas ocupadas frente a las 106 del hospital, estancia media, error del pronóstico); tres o cuatro hallazgos principales en una frase; botones a cada parte.
- **Fuente:** `docs/HALLAZGOS.md`.

---

# PARTE 1 — CONTEXTO (texto, tablas y figuras)

Es la parte que explica **todo lo que no se ve en las gráficas pero que las sostiene**. Cada página es un documento corto con figuras; el contenido se arma ordenando y acortando los documentos del repositorio, no hay que redactar desde cero.

## 1.1 El reto y el alcance
- **Lleva:** la pregunta central; los cuatro componentes del instructivo y **en qué página se contesta cada uno**; el equipo; las fechas.
- **Figura:** línea de tiempo de la ruta del paciente (llegada → admisión → atención en urgencias → cama → alta) con el nombre que damos a cada etapa.
- **Fuente:** `CLAUDE.md` sección 1; `docs/DATA CHALLENGE HUN 2026 (2).pdf`.

## 1.2 La base de datos y su exploración
- **Lleva:**
  - Qué tablas hay (8), de qué trata cada una y su volumen; diagrama de tablas y llaves.
  - **Qué columnas existen de verdad** frente a las que decía el instructivo (varias no existen o están vacías) y qué falta (servicio, piso, cama, signos vitales, hora de los procedimientos, diagnóstico principal).
  - Las cuatro etapas de `visit_detail` y qué significa cada una; cuándo se registra la hospitalización (lo confirmó el HUN).
  - **Cómo se exploró:** consultas de solo lectura, la auditoría directa en la base y qué dudas resolvió.
- **Figuras:** diagrama de tablas; barras de volumen por tabla; diagrama de las cuatro etapas.
- **Fuente:** `CLAUDE.md` secciones 2 y 3; `docs/Diccionario_datos.md`; `docs/conexion_bd.md`.

## 1.3 Calidad de los datos y limpieza
La página más importante del bloque: explica por qué las cifras del proyecto no coinciden con un conteo directo de la base. Una sección por problema, **cada una con cuatro partes: qué se vio, cuánto pesa, qué se decidió y qué efecto tuvo**.
- **Problemas a cubrir:** visitas copia · estancias gemelas (la misma estancia registrada en dos personas distintas) · cuál es la persona real · etapas de urgencias sin hora de fin · etapas abiertas · visitas partidas · diagnósticos sin traducción y sin jerarquía · procedimientos sin fecha · el «hueco sin etapa» antes de la cama (era un artefacto de las estancias duplicadas) · caída total del sistema en dos días de marzo de 2026 · **el registro de etapas que se degrada desde el 10-abr-2026**.
- **Explicación del periodo confiable (debe estar aquí, con su figura):** hasta el 9-abr-2026 el registro es estable: cerca de dos tercios de las visitas de urgencias tienen etapa de admisión (ER) y alrededor de un diez por ciento no tiene ninguna etapa. Desde el 10-abr las visitas registradas en la tabla de cabecera suben cerca de 40 % por día, pero la proporción de visitas con etapa ER baja y empeora más desde el 29-abr; los diagnósticos con código desaparecen desde mediados de mayo. Las visitas de cabecera no bajaron, por eso **no es que lleguen menos pacientes: falla el registro del detalle**. Como no se sabe la causa y los datos son estructuralmente distintos, esos días no se usan para estimar niveles, errores ni tendencias.
- **Figuras obligatorias:** (1) embudo de datos de las etapas a las estancias únicas; (2) ocupación de camas antes y después de resolver las estancias gemelas; (3) visitas de urgencias frente a etapas ER por semana, con la línea vertical del 10-abr-2026.
- **Fuente:** `CLAUDE.md` secciones 4.1 a 4.10; `docs/HALLAZGOS.md` sección 2; `datos/tablas_dashboard/embudo_datos.csv`.

## 1.4 Las variables
- **Lleva:** un **diccionario de variables** con buscador. Columnas: *nombre · qué significa en palabras simples · cómo se calculó · de qué tabla sale · se conoce al llegar (sí/no) · limitación*.
- **Grupos de variables:** unidades (visita, episodio, estancia) · tiempos (espera de cama, urgencias antes de la cama, hueco sin etapa —casi inexistente en el periodo confiable, ver 1.3—, estancia) · estado del episodio · ruta · calendario (hora, franja, día, festivos, Carnaval) · paciente (edad, sexo, tipo de visita) · carga del hospital (llegadas previas, ocupación) · clínicas (grupo de diagnóstico, laboratorios, procedimientos) · agregados diarios.
- **Dos reglas que se explican aquí:** un modelo «al llegar» solo usa lo que se sabe al llegar; los totales de laboratorios y diagnósticos de una visita crecen con la estancia y por eso no se usan como factor.
- **Fuente:** `CLAUDE.md` secciones 3, 5 y 7; `datos/tablas_dashboard/diccionario_tablas.md`.

## 1.5 Las tablas del dashboard
- **Lleva:** una tabla de todos los archivos que alimentan el dashboard: nombre · una fila por… · qué contiene · script que lo genera · en qué página se usa. Una nota de cómo se regeneran.
- **Fuente:** `resultados/tablas/`, `datos/procesados/para_equipo/panel_diario.csv`.

## 1.6 Metodología
- **Lleva:** definición de episodio y estancia; definición de **espera de cama** (llegada hasta asignación de cama; no separa la atención clínica de la espera pura); definición de **cuello de botella** (segmento con exceso sobre una referencia de «cuando funciona bien», alto impacto y que se agrava con la carga); cómo se tratan los atípicos; validación temporal (entrenar con el pasado, probar con el futuro); qué se puede y qué no se puede decir de una asociación.
- **Fuente:** `CLAUDE.md` sección 5; `docs/plan_de_accion.md` sección 0; `docs/HALLAZGOS.md` sección 3.

---

# PARTE 2 — RESULTADOS (interactivos)

## 2.1 Demanda: cuándo llega la gente
- **Controles:** año · tipo de visita · grupo de edad.
- **Gráficas:** mapa de calor día de la semana × hora; serie diaria con marcas de festivos, Semana Santa y Carnaval; barras por mes.
- **Contexto:** hora pico, día más cargado, efecto de fin de semana y de fechas especiales; qué no dice (que haya o no demanda no atendida; las llegadas incluyen algunos registros réplica; el detalle posterior al 9-abr-2026 está incompleto).
- **Fuente:** `bi_llegadas.csv`, `panel_diario.csv`, `mapa_calor_llegadas.csv`.

## 2.2 Ocupación de camas e ingresos
- **Controles:** año · rango de fechas · casilla «mostrar línea de las 106 camas del HUN».
- **Gráficas:** camas ocupadas por día (media y máximo) con la línea de 106 y el periodo no confiable en gris; barras por año de ingresos por día, estancia media y ocupación media; % de horas por encima de 106; ocupación por tipo de paciente (adultos, niños, menores de 1 año) frente a las camas que dio el HUN; descomposición del aumento de ocupación por duración de estancia.
- **Contexto:** la ocupación sube por la estancia, no por más ingresos; ley de Little en palabras simples; **las dos explicaciones posibles del exceso sobre 106 camas** (capacidad real mayor u operación con camas adicionales/camillas) y que los datos no las distinguen; las estancias largas son pacientes con actividad real; qué no dice (cuántas camas hay realmente; urgencias no se compara con las camillas).
- **Fuente:** `panel_diario.csv`, `ocupacion_por_anio.csv`, `escenarios_little.csv`; `docs/factores_estancia.md`; `CLAUDE.md` 4.8.

## 2.3 Espera de cama y cuello de botella
- **Controles:** año · tipo de visita · grupo de edad.
- **Gráficas:** tarjetas (mediana, percentil 90, % que espera más de 24 y de 48 h); línea mensual de mediana y percentil 90; histograma por tramos de espera; barras apiladas del reparto de la espera (urgencias antes de la cama / hueco sin etapa; el hueco es ~1–3 %); ranking de segmentos con las cuatro referencias; exceso medio por año.
- **Contexto:** qué es el exceso y la referencia; de dónde viene la mayor parte de las horas (cola larga); los peores casos empeoran y la mediana no; qué no dice (si la espera es clínica o por falta de cama).
- **Fuente:** `bi_estancias.csv`, `ranking_cuellos.csv`, `descomposicion_espera.csv`, `exceso_por_anio.csv`.

## 2.4 Hora de llegada y altas tardías
- **Controles:** año · tipo de visita.
- **Gráficas:** líneas por hora de altas, ingresos a cama y llegadas; espera por hora de llegada; % que recibe cama al día siguiente según la hora de llegada; ocupación por hora del día.
- **Contexto:** cuándo se dan las altas y cuándo se asigna la cama; el mecanismo ocurre dentro del día (no aparece a nivel diario); el orden de llegada casi no predice el orden de cama; qué no dice (que adelantar altas lo arregle: ver el simulador 3.4).
- **Fuente:** `altas_ingresos_llegadas_por_hora.csv`, `asignacion_cama_por_hora_llegada.csv`, `hora_llegada.csv`, `hora_efectos.csv`.

## 2.5 Qué influye en la espera de cama
- **Controles:** ninguno (es explicativo); opcional: todas las estancias o solo las que tienen diagnóstico.
- **Gráficas:** barras horizontales de cuánto explica cada factor; efectos del modelo con su intervalo; espera por nivel de carga (decil de llegadas); espera por tipo de visita y edad.
- **Contexto (en grande):** los factores observados explican una parte pequeña de la variación; el resto depende de lo que no está en la base (servicio, tipo de cama, gravedad); un modelo para predecir la espera de un paciente individual no sirve; el diagnóstico es un dato administrativo, tardío y puede venir del registro gemelo.
- **Fuente:** `importancia_factores.csv`, `coeficientes_espera_cama.csv`, `carga_por_decil.csv`, `carga_efectos.csv`.

## 2.6 Perfiles de pacientes (A1)
- **Controles:** dimensión (edad / sexo / tipo de visita / combinación) · indicador (llegan por día, % se hospitaliza, espera, estancia, reingreso a 72 h).
- **Gráficas:** barras del indicador por perfil con intervalo y línea del total; tabla de perfiles con la columna que clasifica cada diferencia como *grande / pequeña / ruido*; trayectorias más frecuentes.
- **Contexto:** qué perfiles se hospitalizan más, cuáles esperan más y cuáles menos; **hallazgo abierto: las mujeres esperan más cama que los hombres sin explicación en los datos** (hipótesis sin comprobar); los reingresos no están validados; ocultar celdas con pocos casos.
- **Fuente:** `perfiles_*.csv`; `docs/perfiles_pacientes.md`.

## 2.7 La estancia y las estancias que se disparan (A2 y A2b)
- **Controles:** umbral de estancia larga (más de 14 o de 30 días) · año.
- **Gráficas:** estancia por año (media, mediana, percentil 90, % de estancias largas); qué explica la estancia; efectos por edad y tipo de visita; **cuándo** se disparan (línea mensual); **quién** (barras por edad y tipo de visita); **qué les pasa** (procedimientos y laboratorios más asociados, con el nombre del concepto).
- **Contexto:** respuesta a la pregunta del equipo (por qué subió la estancia media: por la cola de estancias muy largas y no por cada tipo de paciente); qué no dice (un cultivo temprano indica sospecha, no causa; los procedimientos tienen sesgo de duración).
- **Fuente:** `factores_estancia_*.csv`, `disparadas_*.csv`; `docs/factores_estancia.md`, `docs/estancias_disparadas.md`.

## 2.8 Diagnósticos (A3)
- **Controles:** grupo de diagnóstico · indicador (espera / estancia / % se hospitaliza).
- **Gráficas:** barras ordenadas por espera; tabla por grupo con n; efecto del grupo con controles; cobertura del diagnóstico.
- **Contexto:** grupos «urgentes» frente a «quirúrgicos y urológicos»; hipótesis sin comprobar (la cola larga en cirugía, urología y ortopedia); **el agrupamiento no tiene validación clínica**; el ACV se agrupa en Cardiovascular.
- **Fuente:** `tiempos_por_dx.csv`, `efecto_dx_espera.csv`, `mapeo_dx.csv`; `docs/diagnosticos_y_tiempos.md`, `docs/revision_mapeo_dx.md`.

---

# PARTE 3 — PREDICCIÓN Y ANTICIPACIÓN

## 3.1 Pronóstico de demanda (ya construido)
- **Controles (solo dos):** hasta cuándo (7 días, 30 días, 6 meses, 1 año) · qué ver (ingresos al hospital o ingresos a cama).
- **Gráfica:** pronóstico desde el día en que se abre el dashboard, con la banda del 80 %. Tarjetas: se espera por día, rango probable, total esperado, error típico.
- **Contexto:** cómo funciona el modelo en palabras simples; por qué la banda es ancha (el último dato confiable es de abril: una banda ancha no significa un modelo malo); para planear camas conviene el pronóstico semanal; los ingresos diarios son ruido de conteo.
- **Cómo se eligió el modelo:** enlace a la página 3.6.
- **Fuente:** `dashboard/pages/pronostico.py`, `src/modelo_pronostico.py`, `panel_diario.csv`.

## 3.2 Alertas
- **Controles:** tipo de alerta (día congestionado / camas a 24 h / paciente sin cama) · hora o anticipación del aviso.
- **Gráficas:** tabla de alertas con precisión, detección y alertas por día; curva de «más anticipación = más alertas y menos precisión»; carga total de alertas con el diseño recomendado.
- **Contexto:** la alerta de día congestionado avisa a media jornada, no con un día de margen; para camas gana la persistencia a la proyección; se probó reproduciendo días de 2026, no en tiempo real.
- **Fuente:** `alertas_*.csv`; `src/alertas.py`.

## 3.3 Días atípicos
- **Controles:** variable (llegadas / ingresos / espera).
- **Gráficas:** calendario o línea con los días atípicos marcados y su causa (calendario, caída de datos o sin causa aparente).
- **Contexto:** cómo se define un día atípico; el calendario explica una parte; el problema de la espera es crónico y de cola larga, no de días puntuales.
- **Fuente:** `dias_atipicos.csv`, `dias_atipicos_resumen.csv`; `docs/dias_atipicos.md`.

## 3.4 Simulador de camas: ¿qué pasa si…?
- **Controles (deslizadores):** cambio en los ingresos · cambio en la estancia · % de altas de la tarde adelantadas antes del mediodía.
- **Gráficas:** tarjetas de camas ocupadas del escenario, diferencia de camas y camas libres a las 12 h; ocupación por hora del escenario frente a la base, con la línea de 106; espera evitada (cota y estimación).
- **Contexto obligatorio:** es un **escenario** con supuestos escritos, no una predicción; adelantar altas ayuda pero no resuelve esperas de varios días.
- **Pendiente:** bandas de incertidumbre de la simulación Monte Carlo (A5, Anthony); dejar el marcador «Pendiente».
- **Fuente:** `escenarios_little.csv`, `escenario_camas_por_hora.csv`, `escenario_altas_antes.csv`; `src/simulacion_altas.py`.

## 3.5 Diagnóstico de cuello de botella para cualquier periodo (A7)
- **Qué es:** una página donde el usuario **elige un periodo** (desde, hasta) y, opcionalmente, un periodo de referencia, y el dashboard muestra el reporte que produce `src/diagnostico_cuello_botella.py` en cinco pasos: dónde está el cuello de botella, qué se dispara, qué registros se disparan, qué comparten y qué hacer; y dice si el cuello de botella cambió frente a la referencia.
- **Controles:** rango de fechas · rango de referencia · botón «Diagnosticar».
- **Gráficas:** barras de exceso por segmento (periodo y referencia); tabla de esperas largas; tabla de qué comparten; lista de acciones.
- **Contexto:** es el flujo repetible del proyecto; no es tiempo real; no incluye todavía la simulación Monte Carlo.
- **Fuente:** `src/diagnostico_cuello_botella.py`, `docs/diagnostico_cuello_botella.md`. **Nota:** el script lee las tablas por episodio (no públicas); para el dashboard hay que generar de antemano los reportes de los periodos que se quieran ofrecer (por año o semestre), que sí son agregados.

## 3.6 Cómo se eligieron los modelos
- **Lleva:** una tabla de «alternativas probadas → resultado → decisión» por cada modelo: pronóstico de demanda, alertas, modelos explicativos, escenarios de camas, días atípicos. Incluye el piso de ruido de los conteos, las pruebas con meses conocidos y con 2026, la comparación de bandas con y sin la caída, y lo que se descartó.
- **Fuente:** `src/modelo_pronostico.py`, `src/evaluacion_modelo.py`, `src/pruebas_ruido_pronostico.py`, `src/prueba_mes_conocido.py`, `src/prueba_2026.py`, `src/elegir_tau.py`; tablas `evaluacion_modelo.csv`, `pruebas_pronostico_resumen.csv`, `prueba_2026.csv`; `CLAUDE.md` 4.9 y 6b.

---

# PARTE 4 — RECOMENDACIONES

## 4.1 Qué hacemos con esto
- **Lleva:** tabla con prioridad, recomendación, qué dicen **nuestros datos**, qué dice la **literatura**, impacto estimado, cómo medirla, qué tan firme es y estado. Cada fila enlaza a la página que la respalda.
- **Estado:** B2 hecha (Samuel, mergeado el 8-nov-2026): las 12 fuentes se verificaron. **Pendiente antes de publicar impactos:** recalcular las ~11 horas-paciente de R6 y la alerta de ocupación de R3.
- **Fuente:** `docs/recomendaciones.md`, `datos/tablas_dashboard/recomendaciones_tabla.csv`.

---

# PARTE 5 — ANEXOS

## 5.1 Limitaciones y preguntas abiertas
Lista corta y honesta (de `CLAUDE.md` sección 9 y `docs/HALLAZGOS.md`): copias y estancias gemelas · etapas de urgencias sin hora de fin · diagnósticos tardíos y sin jerarquía · mapeo de diagnósticos sin validación clínica · número de camas del hospital sin fecha ni desglose · procedimientos sin fecha · sin signos vitales ni servicio · registro degradado desde el 10-abr-2026 · casi todo son asociaciones. **Hallazgos abiertos:** la ocupación sobre las 106 camas, la espera mayor de las mujeres, el crecimiento de las estancias muy largas, las estancias cortas sin huella en la base.

## 5.2 Glosario y preguntas frecuentes
Términos en palabras simples (urgencias, estancia, espera de cama, mediana, percentil 90, ley de Little, intervalo de confianza, R², AUC, backtest, cultivo, gases arteriales, catéter central…). Preguntas frecuentes de `docs/HALLAZGOS.md`.

## 5.3 Repositorio y cómo reproducirlo
Enlace al repositorio de GitHub, `README.md` («Cómo reproducirlo»), orden de los scripts y quién hizo cada parte.

---

# 4. Cómo armarlo en Dash

- **Estructura de la app:** una app multipágina (`dash.page_registry`) con un menú lateral. Una carpeta `dashboard/` con `app.py` (menú y tema), `pages/` (una página por sección), `componentes.py` (tarjeta, panel de contexto, pie de fuente, aviso de limitación), `datos.py` (carga de las tablas una sola vez) y `assets/` (estilos y tema de colores).
- **Datos:** leer solo tablas agregadas de una carpeta `dashboard/datos/` (copia de las tablas que se publican). La app no abre la base.
- **Páginas de texto** (Parte 1 y 5): Markdown renderizado con `dcc.Markdown`, con figuras como imágenes de `resultados/graficos/` o gráficas de Plotly.
- **Panel de contexto:** un componente reutilizable con las cuatro pestañas (*qué ves, cómo se calculó, qué significa, qué no dice*) para no repetir código.
- **Publicación:** subir solo la carpeta del dashboard y las tablas agregadas; probar el enlace en un navegador distinto antes de entregarlo.

# 5. Qué depende de qué

| Página | Estado |
|---|---|
| Portada, Parte 1 y Parte 5 | Se arman con documentos que ya existen |
| 2.1 a 2.8 | Listas para construir (los análisis están hechos) |
| 3.1 | **Hecha**; falta el texto de contexto y el enlace a 3.6 |
| 3.2, 3.3, 3.6 | Listas para construir |
| 3.4 | Parcial: falta la simulación Monte Carlo (A5, Anthony) |
| 3.5 | Lista; hay que generar los reportes de antemano |
| 4.1 | Lista para construir (B2 hecha; R3 y R6 por recalcular) |

**Orden de trabajo sugerido:** esqueleto con menú y plantilla → Parte 1 (empezando por 1.3) → 2.3, 2.4, 2.2, 3.4 (el núcleo del cuello de botella y las camas) → 3.1 con su texto → 2.5 a 2.8 → 3.2, 3.3, 2.1 → 3.5 y 3.6 → Parte 5 → 4.1 cuando B2 esté lista.

# 6. Lista de verificación antes de entregar
- [ ] Cada página tiene título-conclusión, controles, gráficas, panel de contexto y pie con la fuente.
- [ ] Toda mediana o porcentaje muestra su n y se ocultan los grupos con menos de 30 casos.
- [ ] El periodo posterior al 9-abr-2026 está en gris o no se usa.
- [ ] Cada cifra mostrada coincide con la de `docs/HALLAZGOS.md` o `cifras_de_control.csv`.
- [ ] Cada hallazgo lleva su limitación al lado.
- [ ] No hay datos por paciente ni contraseñas en ningún archivo publicado ni en GitHub.
- [ ] Los términos médicos tienen explicación en el glosario.
- [ ] Las páginas pendientes (3.4, 4.1) muestran «Pendiente» en vez de inventar.
- [ ] El enlace abre sin pedir datos privados.
