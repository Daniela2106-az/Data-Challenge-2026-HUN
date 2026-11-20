# Modelo de camas: simulación de Monte Carlo (ficha A5 / 3.1, 9-nov-2026; mejora del 9-nov; bootstrap suavizado del 10-nov)

**Qué pide el instructivo (componente 3):** "modelos de simulación". Hasta ahora el proyecto solo tenía
`src/simulacion_altas.py`, un **análisis de escenarios sobre datos históricos** (determinista) — esta ficha
construye la primera simulación **estocástica**, con bandas de probabilidad en vez de un solo número.

Código: `src/simulacion_camas_montecarlo.py`. Tablas: `resultados/tablas/simcamas_*.csv`; gráfico:
`resultados/graficos/simcamas_resultados.png`.

## Cómo se midió

- **Datos:** `estancias_hospitalizacion.csv` (25.777 estancias únicas). No hizo falta `panel_diario.csv`: sus
  columnas `ingresos_a_cama` y `ocup_hosp_media/max` se calculan, en `src/exportar_para_equipo.py`, directamente
  desde `estancias_hospitalizacion.csv` — se reprodujo la misma fórmula aquí y coincide con `docs/CONTEXTO_TECNICO.md` 4.8
  (ingresos 20,5/20,8/19,8 por día y ocupación 93,9/101,1/105,0 para 2023/2024/2025, contra 20,6/20,8/19,8 y
  94/101/105 documentados).
- **Motor de Monte Carlo** (1.000 repeticiones): cada día futuro, los ingresos a cama salen de una distribución
  de Poisson alrededor del pronóstico puntual de `src/modelo_pronostico.py` (el modelo vigente del proyecto,
  entrenado solo hasta el 9-abr-2026 por el registro degradado, `docs/CONTEXTO_TECNICO.md` 4.9). A cada ingreso simulado se le
  asigna un **perfil conjunto** (grupo de edad × ruta de llegada — Urgencias/Treatment urgency/Ambulatorio,
  mezcla real de 2025, conserva la correlación real entre edad y ruta) y una estancia por **bootstrap empírico**
  de ese mismo perfil (se saca al azar una `horas_hosp` real de un paciente con esa edad y esa ruta). El censo
  diario sale de acumular eventos de ingreso (+1) y alta (−1), igual técnica que ya usa `src/simulacion_altas.py`
  con datos reales.
- **Mejora del 9-nov — bootstrap por perfil, no solo por edad:** la versión original solo estratificaba por
  edad; como Treatment urgency se queda 63 % más tiempo que Urgencias con la misma edad
  (`docs/factores_estancia.md`), mezclar las estancias de las dos rutas bajo el mismo balde de edad diluía esa
  diferencia. Ahora el bootstrap usa 21 celdas (7 grupos de edad × 3 rutas; la ruta "Inpatient", <1 % de los
  casos, se pliega a Urgencias); solo 2 de 28 celdas posibles tenían menos de 30 casos en la ventana 2024-2025
  y caen de vuelta al bootstrap de solo-edad como respaldo.
- **Dos parámetros nuevos, opcionales e independientes:** `mezcla_edad` y `mezcla_ruta` (diccionarios
  `{categoría: probabilidad}`) permiten sustituir la mezcla real de 2025 en un escenario — por ejemplo, simular
  que la ruta Treatment urgency siga creciendo (ya pasó de 3,8 % a 13,5 % de las estancias entre 2023 y 2025,
  `docs/factores_estancia.md`). Si no se tocan, se muestrea el perfil conjunto real; si se fija alguno de los
  dos, edad y ruta se muestrean por separado en ese escenario (se pierde la correlación real solo ahí, nunca en
  el "hoy" por defecto — simplificación declarada). Son parámetros independientes de `ajuste_ingresos` y
  `ajuste_estancia`, así que cualquier combinación funciona sin código adicional — pensado para conectarse
  directo a controles de un dashboard (B1, ver "Para B1" más abajo).
- **Bootstrap suavizado (10-nov):** cada valor de `horas_hosp` remuestreado se desplaza con ruido gaussiano de
  ancho de Silverman (`ancho_banda_silverman()`), que crece cuando la celda (grupo_edad × ruta) tiene pocos
  casos. Evita que una celda chica repita siempre los mismos valores exactos o deje un valor atípico con una
  probabilidad fija de 1/n. El ancho va de 8,2 h (celdas grandes) a 47,1 h (celdas chicas). Sube un poco todas
  las cifras de ocupación y riesgo frente a la versión sin suavizar (por ejemplo, el riesgo de saturar 106 en
  el escenario base pasa de 58,4 % a 65,4 %) porque el suavizado ensancha ligeramente la cola alta de la
  estancia simulada — dirección esperada, no un error; los números de este documento ya son los suavizados.
- **Dos correcciones hechas durante la construcción** (se dejan documentadas porque cambiaron el resultado):
  1. El bootstrap de estancias se restringió a **2024-2025** (no toda la historia): la mediana de estancia sube
     con el año en casi todos los grupos de edad (p. ej. 75+: 96,1 h en 2023 → 110,9 h en 2025,
     `docs/factores_estancia.md`); usar toda la historia subestimaba la ocupación simulada.
  2. La simulación se **siembra** con el censo real del día de corte (en vez de arrancar con el hospital
     vacío): sin esto, la ocupación simulada tardaba ~3-4 semanas en "llenarse", un arranque que no existe en
     la realidad (el hospital ya tiene pacientes en cama el día 1 de cualquier simulación).
- **Capacidad del HUN** (tabla compartida el 8-nov-2026, consistente con los 106/58 ya documentados el
  29-oct en `docs/CONTEXTO_TECNICO.md` 4.7): 106 camas en total. Como la base no tiene campo de servicio/piso/cama
  (`docs/CONTEXTO_TECNICO.md` 4.8), se reusa el proxy de edad que el equipo ya validó una vez a mano: **niños** (`grupo_edad`
  0-4 y 5-14) frente a pediátrica + neonatal agrupadas (8+6+3+1 = **18 camas**); **adultos** (15-29 en adelante)
  frente a las camas de adultos agrupadas (64+6+14+4 = **88 camas**). Es una aproximación más gruesa que el
  corte "menor de 1 año" que usó esa revisión puntual de la base — se declara como límite.

## 1. Distribución de estancias (la que usa el bootstrap, 2024-2025)

| Grupo de edad | n | Mediana (h) | p90 (h) |
|---|---|---|---|
| 0-4 | 1.383 | 66,7 | 192,6 |
| 5-14 | 1.448 | 54,4 | 190,2 |
| 15-29 | 3.535 | 59,0 | 212,7 |
| 30-44 | 2.421 | 68,5 | 258,1 |
| 45-59 | 2.011 | 76,1 | 308,5 |
| 60-74 | 2.210 | 94,0 | 352,2 |
| 75+ | 1.810 | 100,1 | 356,8 |

La estancia sube con la edad y tiene cola larga en todos los grupos — coherente con `docs/factores_estancia.md`.

## 2. Backtest (puerta de decisión de la ficha 3.1): enero a 9-abr-2026, entrenado solo hasta dic-2025

| Métrica | Resultado | Meta de la ficha |
|---|---|---|
| Error absoluto medio | 8,6 camas | — |
| Sesgo (simulada − real) | +7,0 camas | — |
| % de días con la ocupación real dentro de la banda 10-90 % | **78,8 %** | entre 70 % y 90 % |

(Antes del bootstrap suavizado (10-nov): 7,6 camas, +4,9 de sesgo, 83,8 % de cobertura; antes de la mejora del
bootstrap por perfil (9-nov): 7,0 camas, +3,8 de sesgo, 85,9 % de cobertura. Cada mejora sube un poco el sesgo
porque ensancha o afina la cola alta de la estancia simulada — sigue dentro de la meta de cobertura en los tres
casos; ver "Qué significa para el hospital" sobre por qué el sesgo sube un poco.)

**Cumple la puerta de decisión.** El error relativo (~6-7 % sobre una ocupación de ~100-108) es razonable para
un modelo que proyecta 3-4 meses hacia adelante sin ver esos datos. A diferencia del modelo de A4 (AUC 0,68-0,70,
apenas mejor que el azar para un paciente individual), este sí funciona bien para su propósito — porque predice
un número **agregado** (cuántas camas ocupadas hay en todo el hospital), donde el ruido de cada paciente
individual se compensa entre sí; no es que este modelo esté "mejor construido", es una pregunta estadísticamente
más predecible.

## 3. Proyección y alerta de saturación (desde el 9-abr-2026, 180 días)

| Grupo | Umbral | Valor | Prob. media del horizonte | Día 30 | Día 60 | Día 90 |
|---|---|---|---|---|---|---|
| Total | 106 camas (HUN) | 106 | **65,4 %** | 72,0 % | 51,8 % | 72,8 % |
| Total | p90 histórico | 109,5 | 55,0 % | 61,5 % | 41,0 % | 61,5 % |
| Niños | 18 camas (HUN) | 18 | 34,5 % | 39,0 % | 26,5 % | 38,2 % |
| **Adultos** | **88 camas (HUN)** | 88 | **70,6 %** | 76,1 % | 58,5 % | 75,9 % |

(Con el bootstrap suavizado (10-nov), el riesgo proyectado sube frente a la versión sin suavizar — 65,4 %
contra 58,4 % en total — porque el ruido gaussiano ensancha la cola alta de la estancia simulada. Con el
bootstrap por perfil (9-nov), que separa mejor las estancias largas de Treatment urgency de las cortas de
Ambulatorio dentro de cada grupo de edad, ya había subido frente a la primera versión — 58,4 % contra 53,2 % —
porque la versión original diluía esa diferencia. Las dos mejoras empujan en la misma dirección, no son
contradictorias.)

Los valores de un día puntual (30/60/90) oscilan más que el promedio del horizonte — dependen de qué día de la
semana cae esa fecha (el patrón semanal de ingresos se nota en la ocupación); por eso el promedio del horizonte
es la cifra más estable para citar.

**Dos umbrales para el total, a propósito:** la capacidad que dio el HUN (106) y, de forma independiente, el
percentil 90 de la ocupación **real** observada en el entrenamiento (109,5 — "lo que el propio hospital ya
consideraría un día lleno, sin mirar la cifra del HUN"). Ambos dan una probabilidad alta (65,4 % y 55,0 %), lo
que le da robustez al hallazgo: no depende de confiar en un solo número.

**El riesgo no está repartido parejo:** 70,6 % de probabilidad de saturar las 88 camas de adultos, contra 34,5 %
en las 18 de niños y neonatal — coherente con `docs/CONTEXTO_TECNICO.md` 4.8 ("los adultos operan, en promedio, al 100 % de su
capacidad"), ahora expresado como riesgo proyectado hacia adelante, no solo como hecho ya ocurrido.

Gráfico (`resultados/graficos/simcamas_resultados.png`, 5 paneles): backtest, zoom de corto plazo (30-60 días,
con la probabilidad de saturar 106 marcada en cada corte), proyección completa de 180 días, comparación de
escenarios (ver `docs/simulacion.md`) y la curva de capacidad (sección 4 abajo).

## 4. Curva de capacidad: cuántas camas hacen falta, no "más camas ayudan" (mejora del 9-nov)

En vez de comparar un solo "+N camas" (la respuesta obvia), se barre un rango de capacidades sobre **la misma**
proyección ya simulada — la capacidad solo entra al comparar el censo contra un umbral, así que no hace falta
volver a correr el Monte Carlo (`curva_capacidad()`, `resultados/tablas/simcamas_curva_capacidad.csv`):

| Grupo | Capacidad hoy (HUN) | Mínimo para riesgo ≤ 10 % | Camas adicionales |
|---|---|---|---|
| Total | 106 | 126 | +20 |
| Niños | 18 | 22 | +4 |
| Adultos | 88 | 108 | +20 |

El umbral de riesgo (10 %) es un parámetro (`UMBRAL_RIESGO`), no un número fijo en el código — se puede recalcular
para cualquier nivel de riesgo que el hospital considere aceptable. La curva es monótona decreciente (más camas,
menos riesgo, sin saltos) en los tres grupos — es la prueba de que el cálculo está bien hecho.

## Qué significa para el hospital

- El hospital opera, en el escenario típico de los próximos meses, **al borde o por encima de su capacidad
  declarada** (ocupación media proyectada: 111 camas contra 106 declaradas) — no por debajo con margen.
- El riesgo de saturación se concentra en el lado de **adultos**, no en pediatría/neonatal — si se va a invertir
  en capacidad adicional o en mejorar procesos para bajar el riesgo de saturación, ahí está el mayor margen.
- La banda de incertidumbre es ancha a propósito: refleja variabilidad real (cuántos ingresan, cuánto se queda
  cada uno), no un defecto del modelo — angostarla artificialmente sería dar una falsa sensación de certeza.
- **Para bajar el riesgo a un nivel "tranquilo" (≤10 %) con solo capacidad, hacen falta ~20 camas más** — mucho
  más que un ajuste cosmético. Comparado con el escenario C (−5 % de estancia, `docs/simulacion.md`), que baja
  la ocupación media casi tanto como cuesta +10 camas, la conclusión de toda la ficha se mantiene: **la estancia
  sigue siendo la palanca más barata, antes de pensar en ampliar capacidad física.**
- `mezcla_edad`/`mezcla_ruta` permiten probar, por ejemplo, "¿qué pasa si la ruta Treatment urgency sigue
  creciendo?" sin tocar el resto del motor — útil para escenarios de composición de pacientes, no solo de
  volumen o duración.

## Límites
- El proxy niños/adultos usa los bins de `grupo_edad` disponibles (0-4/5-14 vs. 15-29+), más grueso que el
  corte "menor de 1 año" que el equipo usó una vez directamente sobre la base (`docs/CONTEXTO_TECNICO.md` 4.8).
- El backtest formal es solo del censo **total**; los censos de niños/adultos no tienen una serie real separada
  contra la cual compararse (la base no distingue servicio/piso/cama).
- Los ingresos se simulan con una sola fuente de aleatoriedad por día (Poisson alrededor del pronóstico puntual);
  no se remuestrea además el margen de error propio del pronóstico semanal (~9,5 % documentado) — la banda, si
  acaso, podría ser más ancha de lo que ya es, no al revés.
- A los pacientes "ya hospitalizados" el día de corte se les asigna un tiempo restante sacado del mismo bootstrap
  de estancias completas, sin corregir el sesgo de que alguien ya internado tiende a estar en una estancia más
  larga que el promedio ("inspection paradox") — es una aproximación que solo afecta a los primeros días de cada
  simulación, no a la ocupación de régimen.
- Asociación, no causa; todo lo de siempre del proyecto (duplicados tratados, periodo confiable hasta el
  9-abr-2026, 106 camas es la cifra que dio el HUN el 29-oct sin fecha de corte conocida).
- `mezcla_edad`/`mezcla_ruta` ajustadas muestrean edad y ruta por separado (pierden la correlación real entre
  las dos) — simplificación declarada, solo aplica cuando se usan, nunca al escenario "hoy".

## Para B1 (Dash)
Todos los ajustes de `simular()` (`ajuste_ingresos`, `ajuste_estancia`, `mezcla_edad`, `mezcla_ruta`) son
parámetros independientes y combinables — el backend ya está listo para conectarse a controles interactivos
(sliders) sin cambios adicionales. `curva_capacidad()` tampoco necesita volver a simular, así que un control de
"umbral de riesgo aceptable" también se puede recalcular en vivo sobre la proyección ya hecha.

**Separación con `if __name__ == "__main__":` (10-nov-2026):** el backtest, la proyección con alerta, los
escenarios B/C, la curva de capacidad y los gráficos solo corren al ejecutar el script directamente
(`python3 src/simulacion_camas_montecarlo.py`); `import simulacion_camas_montecarlo` (p. ej. desde
`dashboard/camas.py`, ya hecho) solo paga el costo de cargar los datos y construir el bootstrap (~1-2 s, antes
~1 min porque recalculaba todo lo anterior). `simular`, `curva_capacidad` y todas las variables que usan
(`serie_ingresos`, `ULTIMO_CONFIABLE`, `BOOTSTRAP_PERFIL`, `GRUPOS_HIST`, `RUTAS_HIST`, `CAPACIDAD`, etc.) siguen
disponibles al importar, sin cambiar su comportamiento ni sus cifras (verificado: mismos resultados antes y
después de la separación).

## Entregables
- `src/simulacion_camas_montecarlo.py`.
- `resultados/tablas/`: `simcamas_backtest.csv`, `simcamas_saturacion.csv`, `simcamas_proyeccion.csv`,
  `simcamas_escenarios.csv`, `simcamas_curva_capacidad.csv`.
- `resultados/graficos/simcamas_resultados.png` (5 paneles).
- Este documento y `docs/simulacion.md` (escenarios A/B/C).
