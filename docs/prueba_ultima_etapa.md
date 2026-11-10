# ¿Mejora el estimador si se le suman los laboratorios dentro de la etapa TU actual? (10-nov-2026; con estabilidad por periodo; corregido con los laboratorios completos)

Script: `src/prueba_ultima_etapa.py` (tabla `ultima_etapa_estabilidad.csv` en `resultados/tablas/`, fuera de git). Camino 3 de la propuesta de mejora tras `docs/caracterizacion_etapas_tu.md`.

**Idea:** la espera larga está en la **última etapa TU**, una etapa silenciosa (casi sin laboratorios), y cada etapa nueva arranca con una ráfaga de tomas. El estimador A6 ya usa el tiempo desde el último cambio de etapa, el número de etapas y la hora del reloj. Lo que no usaba, y aquí se suma, son variables observables en el momento de la consulta `c`:
- tomas de laboratorio desde la llegada hasta `c`;
- horas desde la última toma;
- tomas en las 3 h anteriores;
- **tomas desde que empezó la etapa TU actual**;
- diagnósticos distintos registrados hasta `c`.

No se usa «estar en la última etapa», porque en tiempo real no se sabe cuál será la última.

**Diseño** (igual que `comparar_estimadores.py`): entrenamiento feb-2023 a jun-2025, prueba jul-2025 a 9-abr-2026 (5.430 estancias), un modelo por momento con y sin las variables nuevas, mismos hiperparámetros, con más peso a lo reciente (vida media de 6 meses). IC 95 % por bootstrap de semanas.

## Corrección del 10-nov (importante)
La primera versión de esta prueba (resultados del 9 y 10-nov por la mañana) **omitía los laboratorios que cuelgan de visitas copia**, así que a cada estancia le llegaba menos de la mitad de sus tomas (cobertura de ~36 % en lugar de ~70 %). Con los laboratorios completos las conclusiones cambian: **la mejora es más grande y positiva en todos los horarios y periodos**, no solo a las 9 y 12 h. Lo de abajo es la versión corregida.

## Resultados (mejora frente al mismo rango para todos)
Origen B: entrenar hasta jun-2025, probar jul-2025 a 9-abr-2026 (5.430 estancias):

| Horas de espera | Estimador final | + laboratorios en la etapa | Diferencia pareada (IC 95 %) |
|---|---|---|---|
| 3 h | 10,67 % | 11,65 % | **+1,10** (+0,62 a +1,55) |
| 6 h | 9,99 % | 11,10 % | **+1,23** (+0,55 a +1,92) |
| 9 h | 9,05 % | 10,53 % | **+1,63** (+0,81 a +2,48) |
| 12 h | 7,03 % | 7,97 % | **+1,02** (+0,33 a +1,86) |
| 24 h | 5,01 % | 5,75 % | **+0,78** (+0,16 a +1,41) |

## Estabilidad por periodo (dos orígenes de entrenamiento y los dos semestres de prueba)
Origen A: entrenar hasta dic-2024 y probar ene–jun 2025 (3.370 estancias). Origen B: ver arriba, y por separado jul–dic 2025 y ene–9 abr 2026. Puntos de mejora que suman los laboratorios en la etapa (IC 95 % pareado):

| Horas de espera | A: ene–jun 2025 | B: jul–dic 2025 | B: ene–9 abr 2026 |
|---|---|---|---|
| 3 h | **+0,51** (+0,01 a +1,00) | **+1,34** (+0,75 a +1,96) | **+0,65** (+0,10 a +1,37) |
| 6 h | +0,68 (−0,19 a +1,58) | **+1,64** (+0,88 a +2,39) | +0,44 (−0,81 a +1,57) |
| 9 h | +0,27 (−0,46 a +0,97) | **+1,73** (+0,71 a +2,85) | **+1,44** (+0,26 a +2,85) |
| 12 h | **+1,17** (+0,47 a +1,88) | **+1,20** (+0,22 a +2,21) | +0,67 (−0,51 a +1,88) |
| 24 h | +0,44 (−0,49 a +1,28) | **+0,96** (+0,14 a +1,74) | +0,43 (−0,82 a +1,45) |

## Lectura
- **Las 15 diferencias son positivas** (de +0,27 a +1,73 puntos). Se distinguen de cero en 9 de las 15 (en negrita) y en todos los horarios con el origen B completo. Entre +0,4 y +1,7 puntos según el periodo, algo más en jul–dic 2025 que en 2026.
- La mejora es **real y estable en el signo, pero pequeña**: ~1 punto sobre un estimador que ya mejora 7–10 %.
- **El techo no se mueve.** Saber qué laboratorios hay en la etapa actual ayuda un poco en todos los horarios y no cambia el orden de magnitud.
- Ahora ~70 % de las estancias tiene laboratorio en la espera (antes se creía 38 %); para el resto las variables nuevas no aportan.

## Recomendación
- Sí vale la pena integrarlo como mejora **opcional** del estimador (para pacientes de cualquier horario de espera), declarando que exige las horas de toma de los laboratorios del paciente en el momento de la consulta (existen en la base: `measurement_datetime`).
- Es un aporte de bajo valor (~1 punto). No sustituye pedir la gravedad y el servicio.
- La recomendación anterior («integrarlo solo a las 9–12 h») era un efecto de los laboratorios incompletos.

## Limitaciones
- Hiperparámetros fijos, sin ajuste; una sola partición de semestres.
- Con 5 horarios y 3 periodos hay 15 comparaciones: las que salen significativas de forma aislada pueden ser azar.
- Las «ventanas de asignación» (probabilidad de cama en cada franja del día) no se volvieron a probar aquí: la hora del reloj ya está en el modelo y su calibración se evaluó en `src/utilidad_estimador.py`.
- No se usa «estar en la última etapa», porque en tiempo real no se sabe cuál será la última.
- Los estimadores de Samuel (`a6-utilidad`) usan las banderas de laboratorio de `sev_*.csv`: conviene verificar que ese cruce no tenga el mismo problema de visitas copia.
- Son asociaciones, no causas.
