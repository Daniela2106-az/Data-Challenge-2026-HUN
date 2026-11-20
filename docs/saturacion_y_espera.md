# ¿La espera de cama sube cuando las camas están saturadas? (9-nov-2026)

Script: `src/saturacion_y_espera.py` (tablas `saturacion_*.csv` en `resultados/tablas/`, fuera de git). Periodo confiable: 1-feb-2023 a 9-abr-2026, sin el 28 y 29 de marzo de 2026. 25.777 estancias únicas; 22.801 con espera medida (adultos 18.166, niños 4.635). No se usó la VPN.

**Pregunta de Daniela:** si la espera aumenta cuando hay saturación, el cuello de botella son las camas y no hace falta caracterizar las etapas TU; si no, el tiempo se va en las etapas TU de antes de la cama y hay que caracterizarlas.

**Cómo se mide la saturación, hora por hora:** *cola* = estancias que ya llegaron y todavía no reciben cama (solo las que luego se hospitalizan, una cota inferior) y *ocupación* = estancias en cama. Por zona: adultos (88 camas del HUN), niños (18) y total (106). La cola y la espera casi se explican entre sí (ley de Little: cola = llegadas × espera), así que la cola sola no prueba saturación; la ocupación sí es una medida independiente de la espera.

## 1. El hospital está saturado casi siempre
| Zona | Horas con cola vacía | Cola mediana (p10–p90) | Ocupación mediana (p10–p90) | Horas con ≥ 90 % de las camas | Horas sobre las camas |
|---|---|---|---|---|---|
| Total (106) | 0,0 % | 26 (18–34) | 101 (90–110) | 74,8 % | 23,0 % |
| Adultos (88) | 0,0 % | 23 (15–31) | 85 (74–94) | 75,6 % | 31,9 % |
| Niños (18) | 6,1 % | 3 (1–6) | 16 (10–22) | 43,7 % | 27,9 % |

En adultos **nunca hay una hora sin pacientes esperando cama**. Esa es la razón por la que esta pregunta es difícil de contestar con variación: casi no hay horas «sin saturación» con las cuales comparar.

## 2. La espera sube con la ocupación, pero poco
Efecto en la espera de cada +10 camas ocupadas al llegar el paciente, comparando la misma hora del día, el mismo día de la semana y el mismo mes (IC 95 %):

| Zona | Efecto de +10 camas ocupadas | Efecto de +10 en la cola, ya contando la ocupación |
|---|---|---|
| Adultos | **+7,2 %** (+3,5 a +11,1) | −0,1 % (−3,8 a +3,7) |
| Niños | +7,6 % (−1,5 a +17,6) | +10,5 % (−7,8 a +32,5) |
| Total | **+7,8 %** (+4,8 a +10,9) | −1,1 % (−4,1 a +2,1) |

- En adultos, entre los pacientes que llegan con la ocupación más baja (≤ 79 camas) y la más alta (> 91), la espera mediana pasa de 22,7 h a 24,9 h y el p90 de 68 h a 82 h.
- La cola sola parece subir la espera (de 17,7 h a 25,2 h), pero ese efecto desaparece al comparar la misma hora, día y mes (−1 %). Es lo esperado por la circularidad.
- En niños el efecto es parecido pero con poco dato: no se puede distinguir de cero.

## 3. ¿La cama se asigna apenas se libera otra?
Para cada alta con cola > 0, cuánto tarda en asignarse la siguiente cama a otro paciente, frente a los mismos ingresos corridos 1 a 8 semanas (sin el emparejamiento real):

| Alta (todas las camas) | Altas | Demora mediana real | Sin relación | En ≤ 1 h, real | Sin relación |
|---|---|---|---|---|---|
| Todas las horas | 21.065 | 0,47 h | 0,71 h | 68,7 % | 60,9 % |
| 6 a 12 h | 1.749 | **1,84 h** | 2,15 h | 32,7 % | 26,3 % |
| 12 a 14 h | 1.495 | 0,95 h | 1,38 h | 53,4 % | 37,8 % |
| 14 a 19 h | 13.204 | 0,37 h | 0,58 h | 74,2 % | 67,4 % |
| 19 a 24 h | 3.402 | 0,41 h | 0,57 h | 76,1 % | 71,4 % |

- Hay emparejamiento real: la cama se asigna algo más rápido que sin relación, sobre todo a mediodía. Pero la diferencia es modesta, porque en el hospital hay ~20 ingresos por día y casi siempre hay alguno a la vuelta de una hora.
- **Las camas que se liberan en la mañana (6 a 12 h) tardan una mediana de 1,8 h y un tercio tarda más de 3 h en asignarse, aunque hay ~26 pacientes esperando.** Si solo faltaran camas, esa cama se ocuparía en minutos. Esto apunta a un **límite de proceso** (la cama no se asigna hasta cierta hora), no solo de disponibilidad. Coincide con que casi nadie recibe cama entre las 6 y las 12 h.
- Esta prueba es la más débil del conjunto: no hay identificador de cama ni de servicio, así que se compara con «cualquier ingreso».

## Lectura
- **No es «camas sí» o «camas no».** El hospital está estructuralmente saturado (cola siempre > 0, 75 % de las horas con ≥ 90 % de las camas), y eso explica por qué la espera es larga **en nivel**. Pero esa saturación casi no varía, y lo que varía (unas decenas de camas arriba o abajo) mueve la espera solo ~7–8 % por cada 10 camas.
- La saturación del momento **no explica la mayor parte de la espera**. Con la mediana de 18,6 h, un efecto de ~8 % por 10 camas es pequeño frente a la dispersión entre pacientes (los factores observados explican 16 %).
- Hay señal de un **límite de proceso** (las camas liberadas en la mañana no se asignan rápido).
- **Conclusión para el plan:** por la regla de Daniela, el resultado no permite descartar los TU. Camas y TU no son excluyentes: el tiempo en TU antes de la cama es esencialmente la espera, y dentro de él no se puede separar atención clínica de espera de cama con estos datos. Sí conviene caracterizar los TU, con foco en **qué hace diferente a los pacientes que esperan mucho**, no en todos.

## 4. ¿Las 106 camas son un tope? ¿A qué horas se asigna la cama?
**La ocupación pasa de 106 y no se aplasta contra ese número.** Media por año: 94 (2023), 101 (2024), 105 (2025) y 103 (2026, ene–9 abr); máximo 111, 123, 122 y 117; p95 de 113.

| Ocupación total | % de las horas | Ingresos por hora (frente a lo normal de esa hora del día) | Altas por hora (ídem) |
|---|---|---|---|
| ≤ 90 | 10,8 | 1,14 | 0,90 |
| 91–95 | 14,4 | 1,09 | 0,94 |
| 96–100 | 22,7 | 1,01 | 0,94 |
| 101–105 | 24,6 | 0,98 | 1,02 |
| 106 | 4,5 | 0,97 | 1,02 |
| 107–110 | 13,5 | 0,91 | 1,08 |
| 111–115 | 8,0 | 0,90 | 1,13 |
| > 115 | 1,6 | 0,82 | 1,37 |

- El 23 % de las horas está **por encima de las 106 camas** y solo el 4,5 % exactamente en 106. Si fuera un tope duro, habría una acumulación en 106 y los ingresos se frenarían ahí. No ocurre: los ingresos bajan de forma gradual (1,14 a 0,82) y las altas suben cuando el hospital está lleno (0,90 a 1,37), como si se acelerara el alta con la presión.
- **La espera mediana casi no cambia con la ocupación** (18,7 h con ≤ 90; 18,6 h con 91–100; 19,8 h con > 115; incluso 16,7 h con 106–110). Lo que sube es la **cola larga**: el p90 pasa de 60 h a 80 h.
- Las explicaciones posibles de pasar de 106: (A) la capacidad real es mayor que la del HUN, (B) el hospital usa camas adicionales o camillas, (C) un artefacto de registro (pacientes con cama asignada que físicamente siguen en urgencias). Con estos datos no se distinguen. Para (C) hay un indicio en contra: la auditoría del 2-nov (`docs/CONTEXTO_TECNICO.md` 4.9) no halló horas redondas ni cargas en lote en los inicios y fines de cama. Que el techo se pase **no cambia las pruebas 2 y 3** (usan la variación, no el número 106), pero sí obliga a no decir «las camas están llenas al 100 %»: con 106 como referencia es una convención.

**La cama se asigna en dos olas.**

| Hora del ingreso a cama | % de las camas asignadas |
|---|---|
| 0–5 h | 16,1 |
| 6–11 h | 8,9 |
| 12–14 h | 7,5 |
| 15–17 h | 23,8 |
| 18–19 h | 6,1 |
| 20–23 h | 37,5 |

El 61 % de las camas se asigna entre las 15 y las 17 h o entre las 20 y las 23 h, y solo el 9 % entre las 6 y las 11 h. Esto cuadra con el resto de lo medido: la mediana de la espera casi no depende de cuántas camas hay ocupadas, pero la cama llega según la hora del día (la cama se asigna con mediana a las 17–18 h sin importar la hora de llegada, `HALLAZGOS.md` 4).

## Lectura final
Las dos cosas pesan, en distintas partes de la espera:
- **La cola larga (p90) sí depende de la saturación** (+33 % entre la ocupación más baja y la más alta), y la tendencia de 2023 a 2026 va con la subida de la ocupación (94 a 105).
- **La mediana depende de la hora a la que se asignan las camas** (las olas de la tarde y la noche), no del número de camas ocupadas.
- Lo que no se puede separar: cuánto de la asignación en dos olas es una costumbre real del hospital (altas por la tarde, camas listas después) y cuánto es la hora en que se digita en el sistema.

## Limitaciones
- La cola cuenta solo a quienes luego se hospitalizan (cota inferior de la carga real).
- La zona (adultos o niños) se define por la edad; no hay servicio ni cama.
- La ocupación al llegar es un instante: no mide la saturación durante toda la espera.
- Son asociaciones: la ocupación puede subir justo cuando llegan casos pesados.
