# Días atípicos (ficha D.2, 22-oct-2026)

**Pregunta:** ¿qué días se salieron del patrón y qué los distingue? Es lo que pide el instructivo con "identificar patrones atípicos en
el flujo hospitalario". Método, scripts y limitaciones: `src/dias_atipicos.py`. Tablas: `resultados/tablas/dias_atipicos.csv`
(un día por fila) y `dias_atipicos_resumen.csv`. Gráfico: `resultados/graficos/dias_atipicos.png`.

## Cómo se marcó un día como atípico
Se compara lo observado con lo que esperaba el modelo de demanda (`src/pronostico_demanda.py`, pronóstico a 1 día) y se cuenta
cuántas "desviaciones robustas" se aleja (z). **Atípico = más de 3 desviaciones**, en tres cosas: llegadas por día, ingresos a cama por
día y mediana de espera de cama de quienes llegaron ese día (solo días con 8 o más pacientes). Con datos normales se esperarían ~3 días
por variable en 1.188; las colas pesadas dan más.

## Resultado

| Variable | Días atípicos | Más de lo esperado | Menos de lo esperado | Con causa de calendario | Sin causa aparente |
|---|---|---|---|---|---|
| Llegadas | 14 (1,2 %) | 1 | 13 | 3 | 10 (1 más en la caída de datos) |
| Ingresos a cama | 9 (0,8 %) | 3 | 6 | 1 | 7 (1 más en la caída de datos) |
| Espera de cama (mediana del día) | 7 (0,6 %) | 0 | 7 | 4 | 3 |

Casi todos los días atípicos son de **menos** actividad de la esperada, y solo 2 días lo son a la vez en llegadas e ingresos.

## Lo que encontramos

**1. El calendario explica gran parte de lo que parecía raro.** Una primera versión del modelo marcaba 21 días atípicos de llegadas,
9 de ellos en festivos y fechas especiales. Al revisarlos aparecieron dos factores que el modelo no tenía y que ahora incluye:
- **Fin de año:** el 24 y el 31 de diciembre bajan las llegadas (~37 % menos de lo normal); el 25 de diciembre y el 1 de enero se
  comportan como cualquier festivo. Antes los cuatro días iban en una sola marca y el modelo subestimaba el 25 y el 1.
- **Carnaval de Barranquilla** (sábado a martes antes del miércoles de ceniza): en 2024, 2025 y 2026 el sábado y el lunes de carnaval
  tienen menos llegadas de las esperadas (z de −5,5 a −1,8 con la primera versión del modelo); en los 12 días de esos tres carnavales la mediana de z es −1,6 y 8 de 12
  quedan por debajo de −1 (frente al 20 % del resto de días). Efecto estimado: ~16 % menos de llegadas. *Se asume que el HUN está en
  Barranquilla (por la universidad).* Con estos dos factores el error del pronóstico de llegadas a 1 día bajó de 7,9 % a 7,5 %.

**2. Los dos días más extremos parecen fallas de registro o de sistema, no menos pacientes.**
- **28-mar-2026 (sábado):** 88 llegadas contra ~221 esperadas (z = −10,8) y **un solo ingreso a cama** contra ~22 esperados.
- **15-jun-2024 (sábado):** 111 llegadas contra ~250 (z = −9,6) y 8 ingresos contra ~22.
Son los únicos días atípicos a la vez en llegadas e ingresos y caen en la misma magnitud en las dos series. *Hipótesis sin comprobar:*
un corte de sistema o de registro. No hay forma de saberlo con los datos; el HUN podría decir qué pasó esos días.

**3. Un grupo de tres días seguidos:** 5, 6 y 7 de diciembre de 2023 (martes a jueves) con 24 % a 28 % menos llegadas de las esperadas
(z de −3,8 a −3,3). El único dato de calendario es que el 7 es víspera del festivo del 8 de diciembre; no hay otra causa aparente.

**4. La espera larga NO produce días récord.** Ningún día tuvo una mediana de espera **más alta** de lo esperado: los 7 días atípicos
de espera son de espera **más corta** (3 a 5 horas contra 17–20 esperadas), casi todos domingos, festivos o Semana Santa. No es un
patrón general: los días de pocas llegadas esperan solo algo menos (mediana del día de 15,5 h en el 10 % de días con menos llegadas,
19,1 h en el 10 % con más). Es decir, **el problema de espera es crónico y de cola larga, no de días puntuales**: no se resuelve
reaccionando a "los días malos".

**5. La caída desde abril-mayo de 2026 no es un día atípico, es una tendencia.** Las llegadas bajan de forma sostenida; por eso solo 1
día de mayo quedó marcado. Se trata aparte (posible carga incompleta, pregunta 14).

## Días atípicos de llegadas (los 14)

| Fecha | Día | Real | Esperado | z | Observación |
|---|---|---|---|---|---|
| 2026-03-28 | sáb | 88 | 221 | −10,8 | con 1 solo ingreso a cama |
| 2024-06-15 | sáb | 111 | 250 | −9,6 | con 8 ingresos a cama |
| 2026-04-29 | mié | 173 | 268 | −5,2 | justo antes de la caída de mayo |
| 2026-05-09 | sáb | 126 | 186 | −4,6 | periodo de caída de datos |
| 2023-12-05 | mar | 221 | 305 | −3,8 | grupo 5–7 dic 2023 |
| 2025-03-01 | sáb | 128 | 174 | −3,6 | sábado de Carnaval |
| 2023-12-06 | mié | 200 | 269 | −3,5 | grupo 5–7 dic 2023 |
| 2023-07-03 | lun | 181 | 240 | −3,4 | festivo |
| 2025-11-01 | sáb | 168 | 223 | −3,4 | sábado de fin de semana largo (lunes 3-nov festivo); el modelo solo marca la víspera |
| 2023-12-07 | jue | 188 | 247 | −3,3 | víspera del festivo del 8-dic; grupo 5–7 dic 2023 |
| 2024-02-12 | lun | 192 | 254 | −3,3 | lunes de Carnaval |
| 2026-02-02 | lun | 229 | 301 | −3,3 | sin causa aparente |
| 2024-09-22 | dom | 158 | 204 | −3,1 | sin causa aparente |
| 2025-12-25 | jue | 212 | 161 | +3,1 | más de lo esperado (Navidad) |

## Para qué sirve
- **Dashboard (página 4):** tabla de días atípicos y su causa de calendario.
- **Calidad de datos:** los días con caídas simultáneas de llegadas e ingresos (28-mar-2026, 15-jun-2024) conviene revisarlos con el HUN
  como posibles fallas de registro.
- **Pronóstico:** cada factor encontrado (fin de año, Carnaval) mejora el modelo de demanda.

## Limitaciones
- Hasta 2025-12 los esperados son "en muestra" (el modelo vio esos días), por lo que los residuos son algo más chicos que los reales;
  desde 2026-01 son fuera de muestra.
- Una causa de calendario es una coincidencia con una fecha especial, no una causa probada.
- El umbral de 3 desviaciones es una convención; con más datos de cola pesada marca más días que los esperados por azar.
- Faltan causas externas que no están en la base (clima, brotes, eventos, cortes de sistema).
