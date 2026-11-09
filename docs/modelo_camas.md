# Modelo de camas: simulación de Monte Carlo (ficha A5 / 3.1, 9-nov-2026)

**Qué pide el instructivo (componente 3):** "modelos de simulación". Hasta ahora el proyecto solo tenía
`src/simulacion_altas.py`, un **análisis de escenarios sobre datos históricos** (determinista) — esta ficha
construye la primera simulación **estocástica**, con bandas de probabilidad en vez de un solo número.

Código: `src/simulacion_camas_montecarlo.py`. Tablas: `resultados/tablas/simcamas_*.csv`; gráfico:
`resultados/graficos/simcamas_resultados.png`.

## Cómo se midió

- **Datos:** `estancias_hospitalizacion.csv` (25.777 estancias únicas). No hizo falta `panel_diario.csv`: sus
  columnas `ingresos_a_cama` y `ocup_hosp_media/max` se calculan, en `src/exportar_para_equipo.py`, directamente
  desde `estancias_hospitalizacion.csv` — se reprodujo la misma fórmula aquí y coincide con `CLAUDE.md` 4.8
  (ingresos 20,5/20,8/19,8 por día y ocupación 93,9/101,1/105,0 para 2023/2024/2025, contra 20,6/20,8/19,8 y
  94/101/105 documentados).
- **Motor de Monte Carlo** (1.000 repeticiones): cada día futuro, los ingresos a cama salen de una distribución
  de Poisson alrededor del pronóstico puntual de `src/modelo_pronostico.py` (el modelo vigente del proyecto,
  entrenado solo hasta el 9-abr-2026 por el registro degradado, `CLAUDE.md` 4.9). A cada ingreso simulado se le
  asigna un grupo de edad (mezcla real de 2025) y una estancia por **bootstrap empírico** de ese grupo (se saca
  al azar una `horas_hosp` real). El censo diario sale de acumular eventos de ingreso (+1) y alta (−1), igual
  técnica que ya usa `src/simulacion_altas.py` con datos reales.
- **Dos correcciones hechas durante la construcción** (se dejan documentadas porque cambiaron el resultado):
  1. El bootstrap de estancias se restringió a **2024-2025** (no toda la historia): la mediana de estancia sube
     con el año en casi todos los grupos de edad (p. ej. 75+: 96,1 h en 2023 → 110,9 h en 2025,
     `docs/factores_estancia.md`); usar toda la historia subestimaba la ocupación simulada.
  2. La simulación se **siembra** con el censo real del día de corte (en vez de arrancar con el hospital
     vacío): sin esto, la ocupación simulada tardaba ~3-4 semanas en "llenarse", un arranque que no existe en
     la realidad (el hospital ya tiene pacientes en cama el día 1 de cualquier simulación).
- **Capacidad del HUN** (tabla compartida el 8-nov-2026, consistente con los 106/58 ya documentados el
  29-oct en `CLAUDE.md` 4.7): 106 camas en total. Como la base no tiene campo de servicio/piso/cama
  (`CLAUDE.md` 4.8), se reusa el proxy de edad que el equipo ya validó una vez a mano: **niños** (`grupo_edad`
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
| Error absoluto medio | 7,0 camas | — |
| Sesgo (simulada − real) | +3,8 camas | — |
| % de días con la ocupación real dentro de la banda 10-90 % | **85,9 %** | entre 70 % y 90 % |

**Cumple la puerta de decisión.** El error relativo (~6-7 % sobre una ocupación de ~100-108) es razonable para
un modelo que proyecta 3-4 meses hacia adelante sin ver esos datos. A diferencia del modelo de A4 (AUC 0,68-0,70,
apenas mejor que el azar para un paciente individual), este sí funciona bien para su propósito — porque predice
un número **agregado** (cuántas camas ocupadas hay en todo el hospital), donde el ruido de cada paciente
individual se compensa entre sí; no es que este modelo esté "mejor construido", es una pregunta estadísticamente
más predecible.

## 3. Proyección y alerta de saturación (desde el 9-abr-2026, 180 días)

| Grupo | Umbral | Valor | Prob. media del horizonte | Día 30 | Día 60 | Día 90 |
|---|---|---|---|---|---|---|
| Total | 106 camas (HUN) | 106 | **53,2 %** | 58,5 % | 38,1 % | 58,4 % |
| Total | p90 histórico | 109,5 | 42,4 % | 45,6 % | 28,8 % | 45,1 % |
| Niños | 18 camas (HUN) | 18 | 29,5 % | 33,1 % | 21,5 % | 30,2 % |
| **Adultos** | **88 camas (HUN)** | 88 | **60,0 %** | 63,8 % | 47,7 % | 63,5 % |

Los valores de un día puntual (30/60/90) oscilan más que el promedio del horizonte — dependen de qué día de la
semana cae esa fecha (el patrón semanal de ingresos se nota en la ocupación); por eso el promedio del horizonte
es la cifra más estable para citar.

**Dos umbrales para el total, a propósito:** la capacidad que dio el HUN (106) y, de forma independiente, el
percentil 90 de la ocupación **real** observada en el entrenamiento (109,5 — "lo que el propio hospital ya
consideraría un día lleno, sin mirar la cifra del HUN"). Ambos dan una probabilidad alta (53,2 % y 42,4 %), lo
que le da robustez al hallazgo: no depende de confiar en un solo número.

**El riesgo no está repartido parejo:** 60,0 % de probabilidad de saturar las 88 camas de adultos, contra 29,5 %
en las 18 de niños y neonatal — coherente con `CLAUDE.md` 4.8 ("los adultos operan, en promedio, al 100 % de su
capacidad"), ahora expresado como riesgo proyectado hacia adelante, no solo como hecho ya ocurrido.

Gráfico (`resultados/graficos/simcamas_resultados.png`, 4 paneles): backtest, zoom de corto plazo (30-60 días,
con la probabilidad de saturar 106 marcada en cada corte), proyección completa de 180 días, y comparación de
escenarios (ver `docs/simulacion.md`).

## Qué significa para el hospital

- El hospital opera, en el escenario típico de los próximos meses, **justo al borde de su capacidad declarada**
  (106 camas) — no por debajo con margen, sino oscilando alrededor de ella.
- El riesgo de saturación se concentra en el lado de **adultos**, no en pediatría/neonatal — si se va a invertir
  en capacidad adicional o en mejorar procesos para bajar el riesgo de saturación, ahí está el mayor margen.
- La banda de incertidumbre es ancha a propósito: refleja variabilidad real (cuántos ingresan, cuánto se queda
  cada uno), no un defecto del modelo — angostarla artificialmente sería dar una falsa sensación de certeza.

## Límites
- El proxy niños/adultos usa los bins de `grupo_edad` disponibles (0-4/5-14 vs. 15-29+), más grueso que el
  corte "menor de 1 año" que el equipo usó una vez directamente sobre la base (`CLAUDE.md` 4.8).
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

## Entregables
- `src/simulacion_camas_montecarlo.py`.
- `resultados/tablas/`: `simcamas_backtest.csv`, `simcamas_saturacion.csv`, `simcamas_proyeccion.csv`,
  `simcamas_escenarios.csv`.
- `resultados/graficos/simcamas_resultados.png`.
- Este documento y `docs/simulacion.md` (escenarios A/B/C).
