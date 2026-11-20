# ¿Se puede predecir la espera de cama? Pronóstico de la espera y la cola (9-nov-2026)

Script: `src/pronostico_espera_sistema.py` (tablas `espera_*.csv` en `resultados/tablas/`, fuera de git). Estancias únicas con espera medida del periodo confiable (22.801).
**Punto de partida (Daniela):** ya pronosticamos la saturación de camas y los ingresos, pero no el tiempo de espera.

## Camino 3. ¿Cuánto de la espera se predice al llegar? (entrenamiento feb-2023 a jun-2025; prueba jul-2025 a 9-abr-2026, 5.412 estancias; hiperparámetros fijos)
Mejora frente a dar el mismo rango a todos (IC 95 % por semanas):

| Qué se sabe al llegar | Mejora | Error absoluto de la mediana |
|---|---|---|
| Nada (el mismo rango) | 0 % | 26,7 h |
| Hora, día de la semana y festivo | **0,4 %** (0,1 a 0,7) | 26,7 h |
| + saturación real al llegar (ocupación y cola de su zona) | **3,7 %** (3,2 a 4,3) | 25,9 h |
| + edad, sexo y tipo de visita | **7,0 %** (6,1 a 7,9) | 25,0 h |
| (A6 al llegar, con historial y recorrido) | 8,6–9,2 % | ~24 h |

- **La hora y el día casi no predicen la espera de un paciente** (0,4 %), aunque la mediana por hora de llegada va de 12–15 h a ~25 h. La dispersión entre pacientes es enorme y el rango que damos ya la cubre.
- **Saber la saturación suma unos 3 puntos** (y es el valor REAL al llegar: un pronóstico de saturación sería peor). Es un techo, no un pronóstico.
- Lo que aporta el paciente (edad, tipo de visita) es de un tamaño parecido a lo que aporta la saturación.
- **Conclusión:** la espera individual no se puede derivar de la saturación pronosticada. Para el individuo, lo mejor es A6.

## Camino 1. La cola y la espera del sistema
**1a. Pronóstico de la cola** (pacientes que ya llegaron y aún no tienen cama; media 28 en la prueba, desviación 6,6). Error medio absoluto en pacientes, prueba jul-2025 a 9-abr-2026:

| Horizonte | Persistencia (lo mismo que ahora) | Cola típica de la hora | **Modelo de flujo** | Lineal |
|---|---|---|---|---|
| 6 h | 3,82 | 5,21 | **2,58 (−33 %)** | 3,10 |
| 12 h | 5,47 | 5,22 | **3,48 (−36 %)** | 3,60 |
| 24 h | 4,53 | 5,22 | **4,11 (−9 %)** | 4,05 |

El modelo de flujo es: cola de ahora + llegadas esperadas − camas asignadas esperadas, por hora de la semana. **Aquí sí le gana a la persistencia**, a diferencia de la proyección de camas a 24 h (`docs/CONTEXTO_TECNICO.md` 6b).

**1b. Ley de Little:** se hospitalizan 0,85 llegadas por hora y la cola media es 25,8, así que la **espera media esperada es 30,4 h**, frente a 30,5 h reales. La relación se cumple casi exacta. Un error de 3 pacientes en la cola equivale a unas 3,5 h de espera media (3 ÷ 0,85), sobre una media de 30 h.

**1c. Semanal:** ¿la saturación de la semana explica la espera de la semana? (167 semanas con al menos 60 estancias)

| Espera de la semana | Con la ocupación | Con la cola |
|---|---|---|
| Mediana | R² 0,04 (rho −0,22; sin el efecto del año −0,08) | R² 0,02 (rho 0,13; sin año 0,32) |
| Media | R² 0,11 (rho 0,37; sin año 0,09) | R² 0,28 (rho 0,57; sin año 0,38) |
| p90 | R² 0,14 (rho 0,39; sin año 0,06) | R² 0,27 (rho 0,52; sin año 0,30) |

La ocupación no explica la espera semanal (sin el efecto del año, rho ≈ 0,06–0,09). La cola sí se asocia con la media y el p90 de la semana (R² ~0,3), pero eso es en parte circular: la cola es la espera de los pacientes contada de otra forma.

## Lectura
- **La espera del sistema se puede pronosticar a través de la cola, no de la ocupación.** Un pronóstico hora a hora de la cola con el modelo de flujo (error de 2,6–3,5 pacientes a 6–12 h) y la ley de Little dan una **espera media esperada** del sistema con unas ~3–4 horas de error sobre ~30 h.
- **La espera de un paciente concreto no se predice con la saturación** (hasta 3,7 % con la saturación real) y la hora del día casi no suma (0,4 %).
- Hay una conexión natural con lo que ya tenemos: el Monte Carlo y el pronóstico de ingresos alimentan el modelo de flujo (llegadas y camas asignadas esperadas).

## Limitaciones
- **La cola cuenta con retrospectiva:** incluye a los pacientes que luego recibieron cama, que en el momento no se conocen (no tenemos la hora de la orden de hospitalización). Con la información de ese momento la cola sería otra, más ruidosa. Es la limitación principal del camino 1.
- La saturación al llegar del camino 3 es la real, no pronosticada.
- La ocupación de la zona se define por la edad; las 106 camas no son un tope duro (`docs/saturacion_y_espera.md`).
- Periodo confiable hasta el 9-abr-2026; no se probó la estabilidad por semestre.
- Son asociaciones y pronósticos de corto plazo, no causas.
