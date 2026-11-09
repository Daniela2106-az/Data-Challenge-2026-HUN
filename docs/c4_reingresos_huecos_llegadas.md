# C4: reingresos depurados, huecos entre etapas y réplicas de llegadas (8-nov-2026)

Script: `src/c4_reingresos_huecos_llegadas.py`. Tablas: `resultados/tablas/c4_*.csv` (fuera de git).
Periodo: 1-feb-2023 a 9-abr-2026, sin el 28 y 29 de marzo de 2026. Todo son medidas descriptivas; no cambia ninguna tabla que ya tiene el equipo.

## 1. Reingresos depurados

Un **reingreso** es un episodio que empieza dentro de las 72 h (o 30 días) después del fin de un episodio anterior de la misma persona. La versión del pipeline contaba también los episodios que empiezan **antes** de que termine el anterior (traslapes, 1,8 %), que no son un regreso.

| Versión | Episodios | Reingreso 72 h | Reingreso 30 d |
|---|---|---|---|
| A. Pipeline (todos los episodios, con traslapes) | 309.491 | 8,2 % | 17,7 % |
| B. Solo episodios con atención | 270.654 | 7,2 % | 16,6 % |
| C. Con atención y sin registros gemelos | 261.440 | 7,0 % | 15,9 % |
| **C sin traslapes (cifra recomendada)** | 261.440 | **5,3 %** | **14,1 %** |

- Después de una hospitalización, el 28,6 % de los episodios vuelve en menos de 30 días (31,1 % si el episodio anterior tiene hora de fin real). Incluye controles programados: no se distingue un regreso por complicación de uno planeado.
- Limitación: si el fin del episodio anterior es solo un mínimo (no `medida`), el intervalo real hasta el regreso es menor o igual al calculado.
- Lo que se debe citar: **5,3 % en 72 h y 14,1 % en 30 días**. Las columnas `reingreso_72h` y `reingreso_30d` de `tabla_episodios` (6,6 % y 15,4 % en el periodo; excluyen solo el episodio anterior solo-ER sin actividad) cuentan traslapes y registros gemelos; la fila A de arriba es más ancha porque tampoco excluye ese caso.

## 2. Huecos entre etapas

**Entre bloques de un mismo episodio** (episodios conservados): el tiempo sin ninguna etapa suma 34.380 h, el **0,6 %** del tiempo de esos episodios. Los huecos importantes son:

| Transición | Transiciones | Con hueco > 1 h | Mediana si hay hueco |
|---|---|---|---|
| ER > TU | 121.063 | 0,9 % | 1,3 h |
| TU > HOSP | 23.258 | 2,5 % | 9,1 h |
| TU > ER (llegada nueva dentro del episodio) | 6.693 | 9,8 % (39 % se traslapan) | 0,4 h |

TU > HOSP es el único con peso (47 % de las horas de hueco) y coincide con 4.12 (hueco antes de la cama en 1,7–2,5 % de las estancias).

**Entre etapas TU de una misma visita** (las TU seguidas se juntan en un bloque, así que se miden sobre las etapas crudas):

| Hueco | Pares | % de pares | Horas |
|---|---|---|---|
| Pegadas (±1 min) | 141.932 | 96,9 % | 1 |
| 1 min a 1 h | 513 | 0,4 % | 224 |
| 1 a 6 h | 1.455 | 1,0 % | 4.893 |
| 6 a 168 h | 2.561 | 1,7 % | 65.642 |

El hueco TU a TU es el **2,6 %** de las horas de TU y afecta a 3.954 de 131.989 visitas (3,0 %). **Conclusión: no cambia ninguna cifra** (es menos del 3 % del tiempo y los huecos largos son probablemente atenciones separadas dentro de la misma visita).

## 3. Réplicas de llegadas

Réplica = episodio que empieza en el mismo segundo que otro, de una persona con `person_id` a ≤ 10 y con `visit_occurrence_id` a un desfase de copia conocido (se cuenta como réplica el de id mayor). Es una **cota inferior**.

- **13.252 réplicas = 4,3 % de las llegadas** (12,2 % de los episodios con hospitalización, 3,4 % de los demás). La cifra coincide con la medida del 22-oct (≥ 4 %).
- Por año (promedio diario, llegadas totales → sin réplicas): 2023 282,0 → 270,2; 2024 262,7 → 251,3; 2025 260,5 → 249,0; 2026 248,0 → 238,6. Las réplicas son 3,8–4,4 % por año y 4,1–4,6 % por día de la semana.
- **Con atención** (TU u hospitalización) las réplicas son 4,4–5,1 %.
- La razón sin réplicas / total es estable: desviación estándar diaria de 1,3 puntos y correlación de 0,9976 entre las dos series. Por eso el calendario, los días atípicos y la forma del pronóstico **no cambian**; solo baja el nivel absoluto ~4,3 %.

**Decisión recomendada: NO deduplicar las llegadas en el pipeline ni en el pronóstico.**
- Las réplicas son un 4 % estable y proporcional, así que el pronóstico (que explica variaciones relativas) no mejora.
- Quitarlas cambiaría el nivel de `panel_diario.csv`, de las alertas y de las tablas que ya usan Samuel y Anthony, por un efecto pequeño.
- En su lugar: cuando se cite un nivel absoluto, decir «alrededor de 250 llegadas por día, ~4 % menos si se quitan las réplicas (cota inferior)». Se declara como limitación.
