# Modelo explicativo de la espera de cama (ficha A4 / 3.3, 8-nov-2026)

**Qué pide el instructivo (componente 2):** «qué características están asociadas a mayores tiempos de espera». Una prueba rápida del 21-oct (sin validación en tres tramos, sin razones de probabilidades) ya daba **AUC 0,60** "al llegar" (0,64 "con trampa", usando diagnóstico y laboratorios) — casi no sirve para alertar a un paciente individual (`docs/fichas_de_tareas.md:12-13`). Esta ficha formaliza ese resultado con el rigor que pide 3.3 (validación temporal en tres tramos, razones de probabilidades con intervalo, AUC y Brier sin esconderlos) y agrega lo que no existía en esa prueba: los perfiles de A1 y el diagnóstico agrupado de A3.

Código: `src/modelo_espera_explicativo.py` (una regresión logística ajustada a mano con Newton-Raphson/IRLS, sin `scikit-learn` ni `statsmodels` — mismo estilo que `ols()` en `src/dependencia_carga.py` y `src/altas_y_factores.py`). Tablas en `resultados/tablas/modelo_espera_*.csv`.

## Cómo se midió
- **Datos:** `tabla_episodios.parquet`, filtrado a `estancia_unica & hospitalizado & espera_cama_h` medida → **24.990 episodios**. Cifras de control: mediana 18,8 h, p90 73,3 h, 43,9 % > 24 h — coinciden con `docs/CONTEXTO_TECNICO.md` (18,6 / 73,9 / 43,7 %).
- **Objetivo:** `espera_mas_24h` (¿la espera de cama superó las 24 h?).
- **Tres tramos temporales** (nunca al azar): entrenamiento 2023-02-01 a 2025-06-30 (17.389 episodios), validación 2025-07-01 a 2025-12-31 (3.603), **prueba** 2026-01-01 a **2026-04-09** (1.827). La ficha original pedía prueba hasta 2026-05-31; se corta en el 9-abr-2026 porque el registro de etapas se degrada desde esa fecha (`docs/CONTEXTO_TECNICO.md` 4.9) — usar datos posteriores habría contaminado la evaluación.
- **Variables permitidas** (se conocen al llegar; nunca `categoria_dx`, `dx_*`, `n_lab*`, `horas_*`, `ruta*` — se registran después y filtran la respuesta): `franja`, `dia_semana_num`, `mes`, `festivo`, `grupo_edad`, `sexo`, `tipo_visita`, `ocup_hosp`, `ocup_tu`, `llegadas_6h_previas`, `llegadas_24h_previas`, `n_episodios_previos`, `reingreso_72h`, `reingreso_30d`. Categóricas como variables dummy (categoría de referencia fijada con el tramo de entrenamiento); numéricas estandarizadas con media/desvío de entrenamiento (nunca con información de validación o prueba). Dos variables de la lista de la ficha se dejaron fuera por ser redundantes con otras ya incluidas: `edad` continua (ya está `grupo_edad`) y `dia_no_habil` (ya es `fin_de_semana OR festivo`, y `festivo` + los indicadores de día de la semana cubren lo mismo).

## 1. Modelo base — qué factores pesan (38 parámetros, razones de probabilidades)

| Variable | OR | IC 95 % | Lectura |
|---|---|---|---|
| Mañana (6-11h) vs. madrugada | 1,81 | 1,59–2,05 | |
| Grupo de edad 45-59 vs. 15-29 | 1,80 | 1,62–2,00 | |
| Tarde (12-17h) vs. madrugada | 1,68 | 1,43–1,97 | |
| Grupo de edad 30-44 vs. 15-29 | 1,60 | 1,45–1,77 | |
| Grupo de edad 60-74 vs. 15-29 | 1,53 | 1,38–1,70 | |
| Grupo de edad 75+ vs. 15-29 | 1,52 | 1,36–1,70 | |
| **Mujer vs. hombre** | **1,37** | 1,28–1,46 | coherente con `docs/CONTEXTO_TECNICO.md` 4.10 (+27 % en el modelo lineal) |
| Llegadas 6 h previas (por 1 desvío) | 1,25 | 1,18–1,32 | congestión reciente sí pesa |
| Noche (18-23h) vs. madrugada | 1,20 | 1,04–1,39 | |
| Ocupación en TU al llegar | 1,08 | 1,03–1,13 | |
| n_episodios_previos | 1,07 | 1,03–1,11 | |
| Ocupación en cama al llegar | 1,06 | 1,02–1,10 | |
| Llegadas 24 h previas | 0,97 | 0,92–1,02 | **no significativo** (p=0,22) |
| reingreso_72h | 0,85 | 0,73–1,00 | p=0,045, dirección inesperada (ver límites) |
| Treatment urgency vs. urgencias | 0,65 | 0,57–0,73 | coherente con `docs/CONTEXTO_TECNICO.md` 6b (−39 %) |
| Grupo de edad 5-14 vs. 15-29 | 0,64 | 0,56–0,72 | |
| **Grupo de edad 0-4 vs. 15-29** | **0,40** | 0,35–0,46 | coherente con `docs/perfiles_pacientes.md` ("los niños esperan mucho menos") |
| Ambulatorio vs. urgencias | 0,16 | 0,13–0,19 | coherente con `docs/CONTEXTO_TECNICO.md` 6b (−31 %) |
| `mes_*`, `dia_semana_num_*` | — | — | casi ninguno significativo — coherente con "calendario ~0" (`docs/CONTEXTO_TECNICO.md` 6b) |

Tabla completa (38 variables): `resultados/tablas/modelo_espera_coeficientes_base.csv`. Cada coeficiente es **validación cruzada con hallazgos ya documentados por otros caminos** (factores de la espera de `altas_y_factores.py`, perfiles de A1): da confianza de que el modelo no está inventando nada, solo cuantificando con más precisión patrones ya conocidos.

**Un matiz importante (controlado vs. crudo):** en crudo, la tarde sigue siendo la franja con peor espera (mediana 25,0 h, 52,2 % > 24 h, frente a 16,4 h / 44,8 % de la mañana) — eso no cambia. Lo que se invierte es solo el coeficiente *residual*: la tarde arrastra casi el doble de carga reciente que la mañana (110 vs. 60 llegadas en las 6 h previas), y esa carga ya se le "cobra" por separado a `llegadas_6h_previas`; a la mañana, con menos carga, le queda relativamente más penalización sin explicar. Ambas lecturas son correctas, responden preguntas distintas.

## 2. AUC y Brier del modelo base

| Tramo | n | % > 24h real | AUC | Brier |
|---|---|---|---|---|
| Entrenamiento | 17.389 | 44,1 % | 0,692 | 0,2193 |
| Validación | 3.603 | 41,2 % | 0,692 | 0,2189 |
| Prueba | 1.827 | 43,7 % | 0,678 | 0,2236 |

Brier de la línea base ingenua (predecir siempre la tasa general): 0,2465. El modelo mejora sobre esa línea base, pero poco — coherente con el AUC.

## 3. Intentos de mejora (siempre decididos en validación, nunca mirando la prueba)

| Modelo | n parámetros | AUC train | AUC val | Brier train | Brier val |
|---|---|---|---|---|---|
| Base | 38 | 0,692 | 0,692 | 0,2193 | 0,2189 |
| **A: perfil conjunto** (grupo_edad × sexo × tipo_visita en una sola variable, 40 niveles) | 68 | 0,696 | **0,697** | 0,2183 | **0,2174** |
| B: + interacción franja × grupo_edad | 56 | 0,694 | 0,692 | 0,2189 | 0,2189 |
| C: perfil + interacción | 86 | 0,697 | 0,697 | 0,2178 | 0,2174 |
| Sin `reingreso_72h`/`30d` | 36 | 0,692 | 0,692 | 0,2194 | 0,2188 |
| Sin `n_episodios_previos` | 37 | 0,692 | 0,692 | 0,2195 | 0,2188 |

- **Se adopta A (perfil conjunto):** mejora en entrenamiento *y* validación por igual (+0,005 AUC, −0,0015 Brier) — señal de que es una mejora real, no sobreajuste. Trata la combinación de edad, sexo y tipo de visita de forma no aditiva (p. ej. "niño y llega por ambulatorio" puede tener un efecto propio, no solo la suma de "efecto niño" + "efecto ambulatorio").
- **Se descarta B (interacción franja × edad):** mejora solo en entrenamiento (0,692→0,694) y nada en validación (se queda en 0,692) — firma clásica de sobreajuste (memoriza combinaciones específicas que no generalizan). C confirma que la interacción no aporta nada ni siquiera junto con el perfil.
- **Reingreso y n_episodios_previos se mantienen:** quitarlos no mueve el AUC/Brier casi nada, pero ambos son individualmente significativos en la tabla de la sección 1 (asociaciones reales y pequeñas, no redundantes entre sí — correlación de 0,58 entre `reingreso_72h` y `reingreso_30d`, de 0,40 entre `reingreso_30d` y `n_episodios_previos`).

Tabla completa: `resultados/tablas/modelo_espera_mejoras.csv`.

## 4. Techo real con "trampa" (extensión exploratoria, nunca usada en el modelo final)

`categoria_dx` (A3, 19 grupos) se registra **después** de la llegada (88 % tras las primeras 2 h, `docs/CONTEXTO_TECNICO.md`) y en parte depende de cuánto duró la espera (causalidad inversa parcial) — por eso nunca entra al modelo "al llegar". Se probó aparte, solo para medir el techo máximo si se permitiera usarla:

| Modelo | AUC val | Brier val |
|---|---|---|
| Base, permitido | 0,692 | 0,2189 |
| + categoria_dx (fuga) | **0,730** (+0,038) | 0,2073 |
| A (perfil), permitido | 0,697 | 0,2174 |
| A + categoria_dx (fuga) | **0,734** (+0,037) | 0,2058 |

La ganancia (+0,037/+0,038) **reproduce casi exactamente** la ya documentada en la prueba del 21-oct (0,60 → 0,64, +0,04), con una metodología totalmente distinta — confirma que ese "techo con trampa" es un número real y estable, no un accidente de la prueba original. **Conclusión clave:** incluso regalándole al modelo la información más generosa posible (que ni debería poder usar), el techo absoluto sigue siendo bajo (0,73, no 0,90+). Esto descarta la hipótesis de "nos falta una variable clave" — la mayoría de por qué un paciente espera lo que espera no está en ningún campo de esta base.

Algunos grupos de diagnóstico, solo para describir (razón de probabilidades frente a "Sin diagnóstico"): esperan **menos** Cardiovascular (OR 0,36), Dolor y síntomas generales (0,18), Recién nacido (0,30), Respiratorio (0,51), Neurológico (0,57) — coincide con `docs/diagnosticos_y_tiempos.md` ("cardiovascular y neurológico reciben cama en ~4 h"). Esperan **más** Musculoesquelético y dolor (OR 2,71), Renal y urinario (1,78), Digestivo (1,46) — también coincide. Tabla completa: `resultados/tablas/modelo_espera_coeficientes_dx.csv`.

## 5. Evaluación final en prueba (tocada una sola vez)

| Modelo | AUC train | AUC val | **AUC prueba** | Brier train | Brier val | **Brier prueba** |
|---|---|---|---|---|---|---|
| Base | 0,692 | 0,692 | 0,678 | 0,2193 | 0,2189 | 0,2236 |
| **A (elegido)** | 0,696 | 0,697 | **0,684** | 0,2183 | 0,2174 | **0,2218** |

Caída pequeña y esperable de validación a prueba (−0,013), consistente con un periodo distinto y menos casos (1.827). El modelo A sigue por encima del base en los tres tramos — la mejora del perfil conjunto no era un espejismo de validación.

**Calibración** (¿la probabilidad que da el modelo se parece a lo que de verdad pasa?):

| Probabilidad media predicha | % real que esperó > 24 h |
|---|---|
| 21,8 % | 20,2 % |
| 37,4 % | 37,8 % |
| 47,6 % | 38,6 % |
| 56,4 % | 55,6 % |
| 66,6 % | 66,4 % |

Cuatro de cinco grupos quedan a 1-2 puntos; el modelo está razonablemente bien calibrado (cuando dice "alta probabilidad" suele acertar en esa proporción), aunque eso es independiente de qué tan bien separa a los pacientes (sección siguiente).

## 6. Por qué este modelo no sirve para alertar a un paciente individual

Umbrales de probabilidad sobre el tramo de prueba (modelo A, 1.827 episodios, 43,7 % con espera real > 24 h):

| Umbral | % marcados | Precisión | Detección | Falsas alarmas | Aciertos | Se escapan |
|---|---|---|---|---|---|---|
| 0,30 | 80,4 % | 49,5 % | 91,0 % | 742 | 727 | 72 |
| 0,40 | 65,6 % | 52,5 % | 78,7 % | 570 | 629 | 170 |
| **0,50** | **44,3 %** | **59,4 %** | **60,2 %** | 329 | 481 | 318 |
| 0,60 | 21,0 % | 65,8 % | 31,5 % | 131 | 252 | 547 |
| 0,70 | 4,1 % | 63,5 % | 5,9 % | 27 | 47 | 752 |

En el umbral más natural (0,50) se marcaría al 44 % de todos los pacientes que llegan, y 4 de cada 10 marcados serían falsas alarmas; bajar el umbral para no perder casos reales (0,30, detecta 91 %) implica marcar al 80 % de todos los pacientes. Es la consecuencia matemática directa de un AUC de 0,68-0,70: demasiado solapamiento entre quienes sí y quienes no esperan mucho como para trazar una línea útil entre ambos a nivel individual.

**Las alertas que sí funcionan en este proyecto no vienen de aquí.** Son `src/alertas.py` (Fase 7, construidas por Daniela), que no predicen por paciente al llegar sino con información que se acumula con el tiempo: Alerta A ("día congestionado", a mediodía, con lo que ya llegó esa mañana) AUC 0,94; Alerta B ("ocupación ya alta") AUC 0,92; Alerta C ("paciente que ya lleva 48 h sin cama") — reactiva, no predictiva. El rol de este modelo no es competir con esas alertas, es confirmar con rigor **por qué** el camino de "predecir al llegar, por paciente" no es el camino correcto para una alerta, y dejar documentados los factores que sí se asocian a la espera para que informen recomendaciones de proceso (no alertas automáticas).

## Límites
- Todo es asociación, no causa.
- El techo real (sección 4) muestra que la mayor parte de la variación de la espera no está en ningún campo de la base, con o sin diagnóstico — no es un problema de "falta una variable", es estructural.
- `reingreso_72h` sale con dirección contraintuitiva (OR 0,85, menos espera) y un valor p al límite (0,045); no se investigó más a fondo por qué — posible tema para A2b o una revisión futura.
- El tramo de prueba (2026-01-01 a 2026-04-09) es corto (1.827 episodios) por el corte del registro degradado; sus cifras tienen más incertidumbre que las de validación.
- La extensión con diagnóstico (sección 4) es descriptiva, nunca se usa para alertar ni se mezcla con el modelo permitido.

## Entregables
- `src/modelo_espera_explicativo.py`: todo el flujo (carga, filtro, splits, modelo base, mejoras, techo con trampa, evaluación final, calibración, umbrales). **Nota sobre el formato:** la ficha 3.3 pedía un notebook (`notebooks/modelos/modelo_espera_explicativo.ipynb`); se entrega como script de `src/`, igual que el resto de los modelos explicativos del proyecto (`altas_y_factores.py`, `dependencia_carga.py`, `factores_estancia.py`, `modelo_pronostico.py`) — ninguno de ellos es un notebook en la práctica, así que esto mantiene la consistencia real del repositorio en vez de la consistencia con el plan original.
- Tablas en `resultados/tablas/modelo_espera_*.csv` (coeficientes base, mejoras, techo con dx, coeficientes dx, métricas finales, calibración, umbrales).
- Este documento.

**Siguiente paso recomendado:** A5 (simulación de Monte Carlo de camas) — es la otra tarea pendiente de Anthony y bloquea A7, la página 5 del dashboard de Power BI y parte de B2 (`docs/pendientes_y_reparto.md`).
