# Factores de la estancia hospitalaria (tarea A2, 3-nov-2026)

**Qué pide el instructivo (componente 2):** «factores asociados a incrementos en [...] la duración de las estancias hospitalarias». Y una pregunta concreta del equipo: la estancia media pasó de **4,57 a 5,31 días** entre 2023 y 2025 (+16 %); ¿por un cambio en el **tipo de pacientes** o porque **cada tipo se quedó más tiempo**?
Código: `src/factores_estancia.py`. Tablas: `resultados/tablas/factores_estancia_*.csv`; gráfico: `resultados/graficos/factores_estancia.png`.

## Cómo se midió
- **Estancias** del periodo confiable (empiezan del 1-feb-2023 al 9-abr-2026) con alta registrada antes del 10-abr: 23.405 estancias, una fila por estancia (registro conservado, `estancia_id`). Estancia media 4,93 días, mediana 69 h, p90 265 h.
- **Edad y sexo** son los de la persona real (`docs/CONTEXTO_TECNICO.md` 4.10).
- **Modelo explicativo (no predictivo)** sobre el logaritmo de la estancia en horas. Factores permitidos: edad y sexo, tipo de visita, franja y año de llegada, espera de cama, laboratorios de las primeras 6 horas y ocupación al llegar. Se excluyen los totales de diagnósticos, procedimientos y laboratorios porque crecen con la estancia (causalidad inversa).
  Un segundo modelo (B), solo entre quienes tienen diagnóstico (68 % de las estancias, hasta el 30 de abril), suma el grupo de diagnóstico.

## 1. Qué tan larga es la estancia, por año

| Año de ingreso | Estancias | Media (días) | Mediana (h) | p90 (h) | Más de 14 días | Más de 30 días | Media sin las de más de 30 d |
|---|---|---|---|---|---|---|---|
| 2023 | 6.838 | 4,57 | 67,0 | 246 | 5,5 % | 0,8 % | 4,29 |
| 2024 | 7.599 | 4,90 | 68,3 | 264 | 6,6 % | 1,2 % | 4,49 |
| 2025 | 7.220 | 5,31 | 72,4 | 285 | 7,3 % | 1,6 % | 4,70 |

La **mediana** casi no se mueve (+8 %: de 67 a 72 h); lo que sube es la **cola larga**: las estancias de más de 30 días pasan de 54 a 117 por año.

## 2. Qué explica la estancia (con honestidad sobre cuánto)

**Los factores observables explican poco:** R² de **7,9 %** (modelo A, todas las estancias) y **10,8 %** (modelo B, con diagnóstico). El 90 % de la variación de la estancia no se explica con lo que se sabe al ingresar. (Por eso un modelo que prediga la estancia de cada paciente no sirve; aquí solo se explica.)

Pérdida de R² al quitar cada factor (puntos):

| Factor | Modelo A | Modelo B |
|---|---|---|
| Grupo de diagnóstico | — | 3,2 |
| Tipo de visita | 2,9 | 1,2 |
| Edad y sexo | 1,8 | 2,9 |
| Espera de cama | 0,7 | 0,3 |
| Laboratorios de 6 h | 0,2 | 0,2 |
| Hora y año de llegada | 0,1 | 0,0 |
| Ocupación al llegar | 0,0 | 0,0 |

**Efecto sobre la estancia** (modelo A, frente a la categoría de referencia; intervalo de confianza del 95 % entre paréntesis):
- **Edad** (frente a 15–29 años): 45–59 años **+25 %** (19 a 30), 60–74 años **+33 %** (28 a 39), 75 años o más **+46 %** (40 a 53); los de 5–14 años −7 %.
- **Tipo de visita** (frente a urgencias): **Treatment urgency +63 %** (56 a 71); ambulatoria −35 %.
- **Sexo:** sin diferencia (hombres −2 %, IC −5 a +0,4): al revés que en la espera de cama, aquí no hay diferencia entre sexos.
- **Espera de cama:** por cada desviación estándar más de espera, la estancia es **9 % mayor** (8 a 11). Asociación; los que esperan más pueden estar más enfermos.
- **Año de ingreso:** sin efecto una vez controlado lo demás (2025 frente a 2024: +0,8 %, IC −2,5 a +4,2). **El aumento no es de las estancias típicas.**
- Diagnóstico (modelo B, frente a la referencia): estancias más largas en recién nacidos (+67 %, solo 36 casos), infecciosas (+31 %), cáncer (+29 %), musculoesquelético (+28 %) y piel (+25 %); más cortas en dolor y síntomas generales (−29 %), embarazo y parto (−28 %), cardiovascular (−20 %), trauma (−19 %) y renal (−16 %).
- **Estancia de más de 14 días** (regresión logística, 6,5 % de las estancias, AUC 0,69): razón de probabilidades de 2,8 en los de 75 años o más (IC 2,4 a 3,4), 2,4 en los de 60–74 y 2,5 en las visitas «Treatment urgency» (2,1 a 2,8); los hombres, 1,19 (1,07 a 1,33).

## 3. ¿Cambió el tipo de pacientes o cada tipo se quedó más? (descomposición 2023 → 2025: +0,745 días)

La respuesta depende de cómo se defina «tipo de paciente»:

| Definición de «tipo» | Por composición | Dentro de cada tipo |
|---|---|---|
| Edad (7 grupos) | 0,06 d (8 %) | 0,69 d (92 %) |
| Edad × tipo de visita (28 grupos) | **0,42 d (57 %)** | 0,32 d (43 %) |
| Edad × sexo × tipo de visita (56 grupos) | 0,40 d (53 %) | 0,35 d (47 %) |
| Edad × tipo de visita × diagnóstico (316 grupos) | 0,26 d (34 %) | 0,42 d (56 %) (+0,07 d en grupos sin comparación) |

- **Con la edad sola casi todo es «dentro de cada tipo»** (los grupos de edad casi no cambiaron de peso). **Al sumar el tipo de visita, la mitad es composición:** las visitas «Treatment urgency» pasaron del 3,8 % al 13,5 % de las estancias, y se quedan unos 7 días (contra 4,9 de urgencias normales).
- **La mitad del aumento viene de las estancias de más de 30 días:** aportan 0,31 días a la media de 2023 y 0,69 a la de 2025 (+0,38 d, el 51 % del aumento). Sin ellas, la media pasa de 4,29 a 4,70 días (+9,6 % en vez de +16,3 %), y la descomposición vuelve a ser sobre todo composición (0,30 d) y menos «dentro» (0,11 d).
- **Resumen:** del +16 % de estancia media, aproximadamente **la mitad es la cola de estancias de más de 30 días** (de 54 a 117 por año) y, del resto, una parte importante es la **llegada de pacientes «Treatment urgency»**. La estancia típica casi no cambió (mediana +8 %).

## Qué significa para el hospital
- Para bajar la estancia media, lo que más pesa son las **estancias largas**: unas 117 estancias de más de 30 días al año ocupan 13 camas (`docs/CONTEXTO_TECNICO.md` 4.8).
- El **flujo «Treatment urgency»** (sin etapa de admisión, 25–37 % se hospitaliza) crece rápido y se queda 60 % más que el resto, con la misma edad: merece revisión propia.
- La **edad** es el factor que más se asocia a la estancia larga: los mayores de 60 años se quedan 33–46 % más.

## Límites
- Asociación, no causa. Sin servicio, sede, piso ni cama no se puede explicar *por qué* se quedan más ciertos pacientes.
- R² de 8–11 %: gran parte de la estancia depende de lo que pasa dentro del hospital y no se observa.
- Diagnóstico solo en el 68 % de las estancias, registrado durante la estancia (parcialmente consecuencia de ella).
- Las estancias de 2026 (hasta el 9-abr) son pocas (1.748); las altas posteriores al 10-abr no se usan.
- La descomposición cambia según la definición de «tipo»: se reportan las cuatro.

## Para A2b
Sigue la pregunta «qué comparten las estancias que se disparan» (estancias de más de 14 o 30 días): ya se ve que son sobre todo mayores de 60 años y visitas «Treatment urgency», y que aumentan con el tiempo. Falta cruzar con los procedimientos y laboratorios de cada estancia.
