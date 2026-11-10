# ¿Qué pasa en urgencias mientras se espera la cama? (9-nov-2026)

> **Corrección (9-nov, misma tarde):** este documento mira la espera como un solo bloque, que es como la junta nuestro pipeline. En la base cada estancia tiene **varias etapas TU** seguidas (2,5 en promedio), y la caracterización por etapa está en `docs/caracterizacion_etapas_tu.md`. Donde este documento diga que «hay un solo bloque TU» o que «no hay tipos de TU que caracterizar», vale lo del documento nuevo.

Script: `src/caracterizar_tu.py`. Tablas `tu_*.csv` en `resultados/tablas/` (fuera de git). Consulta a la base: `sql/espera_labs_dx_con_hora.sql` (laboratorios y diagnósticos con su hora, 9-nov, 4,2 min).
Periodo confiable (1-feb-2023 a 9-abr-2026, sin el 28 y 29 de marzo de 2026), estancias únicas con espera medida: **22.801**.

**Pregunta de Daniela:** el tiempo antes de la cama es casi todo urgencias (etapas TU). ¿Quienes esperan mucho hacen algo distinto allí (más pruebas, más bloques de atención), o solo esperan más en el mismo estado?

## Cómo se hizo (y sus límites)
- Las etapas TU **no traen diagnóstico ni laboratorio propios**: esa información cuelga de la visita. Se caracteriza entonces la **ventana de espera** (de la llegada a la asignación de cama), que es casi toda TU.
- Solo se usan filas de la **persona real** de la estancia y solo las que caen dentro de esa ventana. Los procedimientos no tienen hora y no entran.
- Grupos por espera: **A** menos de 6 h (5.443 estancias), **B** 12–48 h (9.348), **C** más de 72 h (2.327), y 6–12 h (3.464) y 48–72 h (2.219) como apoyo.
- Una espera larga acumula más tomas por tener más tiempo. Por eso se comparan **tasas**, las **primeras horas** (misma ventana para todos) y el **tiempo sin laboratorio antes de la cama**.
- El diagnóstico **no sirve para medir inactividad**: el primero se registra al minuto de llegar (mediana 0,02 h) y el último, a unos 20–30 minutos de la cama (mediana 0,2–0,5 h) en todos los grupos.

## Resultados

**1. (Corregido) Los bloques TU son 1,0 en todos los grupos porque el pipeline junta las etapas TU seguidas.** Las etapas crudas sí son varias y sí se diferencian: ver `docs/caracterizacion_etapas_tu.md`.

**2. Los que esperan mucho son algo distintos de entrada** (no son un TU distinto, son pacientes distintos):

| Grupo | Edad mediana | Con laboratorio en la espera | Con diagnóstico | En las primeras 6 h: tomas promedio |
|---|---|---|---|---|
| A < 6 h | 29 | 23,1 % | 43,7 % | — |
| B 12–48 h | 33 | 37,4 % | 40,4 % | 1,94 |
| C > 72 h | 52 | 46,2 % | 47,5 % | 2,75 |

En las primeras 6 h (misma ventana), C tiene más laboratorio (39 % frente a 31 %) y algo más de diagnósticos distintos (0,88 frente a 0,69). Son más mayores y algo más complejos.

**3. La actividad de laboratorio se concentra al principio y luego casi se apaga, igual en todos los grupos.** Tomas por 10 horas-paciente, entre los que siguen esperando:

| Tramo de la espera | Grupo B | Grupo C |
|---|---|---|
| 0–6 h | 3,2 | 4,6 |
| 6–12 h | 1,1 | 1,6 |
| 12–24 h | 0,8 | 1,1 |
| 24–48 h | 0,4 | 0,5 |
| 48–72 h | — | 0,4 |
| 72–120 h | — | 0,4 |

Después de las primeras 12 h la intensidad cae unas diez veces y se queda plana, también en quienes esperan más de 72 h. En cada tramo C tiene un poco más que B, pero el perfil es el mismo.

**4. Entre quienes tienen laboratorio, esperan mucho tiempo sin ninguno antes de la cama:**

| Grupo | Espera mediana | Horas desde la última toma hasta la cama (mediana) | Con más de 12 h sin laboratorio | Con más de 24 h sin laboratorio |
|---|---|---|---|---|
| A < 6 h | 3,4 h | 0,5 | 0 % | 0 % |
| B 12–48 h | 27,2 h | 10,3 | 43,9 % | 16,1 % |
| C > 72 h | 98,8 h | 31,2 | 71,7 % | 57,2 % |

En el grupo C, la última toma cae a las ~67 h de una espera de ~99 h: el último tercio de la espera ocurre sin laboratorios registrados. Lo mismo dentro de un mismo diagnóstico, por ejemplo digestivo: 13,5 h sin laboratorio en B frente a 32,6 h en C; cardiovascular, 8,6 h frente a 18,4 h.

## 7. Con el TU como un bloque: espera según la cantidad de actividad (9-nov, tarde)
Entre las estancias que siguen esperando a las 6 h (n = 17.358), espera **restante** (más allá de las 6 h) según lo que ya se hizo en esas 6 h:

| Medida de actividad | Franja | n | Restante: mediana | p90 | % con más de 24 h | Edad mediana |
|---|---|---|---|---|---|---|
| Tomas de laboratorio en las 6 h | 0 | 11.560 | 21,0 h | 72,7 | 44,0 | 33 |
| | 1–2 | 778 | 18,4 h | 58,0 | 38,8 | 25 |
| | 3–5 | 2.110 | 23,1 h | 75,2 | 48,0 | 37 |
| | 6 o más | 2.910 | 26,1 h | 92,2 | 53,9 | 55 |
| Diagnósticos distintos en las 6 h | 0 | 10.011 | 21,4 h | 73,0 | 44,8 | 34 |
| | 1 | 3.878 | 22,9 h | 75,3 | 47,8 | 38 |
| | 2 o más | 3.469 | 22,7 h | 80,2 | 47,1 | 40 |
| Procedimientos distintos de la **visita** (incluye la hospitalización: no se puede fechar) | 0–5 | 2.482 | 7,1 h | 33,6 | 16,1 | 14 |
| | 6–9 | 1.688 | 15,9 h | 50,0 | 34,2 | 27 |
| | 10–14 | 3.727 | 21,8 h | 64,0 | 44,8 | 31 |
| | 15 o más | 9.461 | 26,9 h | 94,2 | 56,3 | 48 |

- **Más actividad inicial no significa más espera restante cuando se controla la edad.** Controlando edad, tipo de visita, hora de llegada y mes, cada toma de laboratorio en las 6 h cambia la espera restante en **−0,2 % (−0,8 a +0,5)** y cada diagnóstico en **−2,6 % (−4,5 a −0,6)**. El gradiente de los laboratorios (21 h a 26 h) es de edad (33 a 55 años).
- Los procedimientos sí se asocian fuerte, pero **cuentan toda la visita, incluida la hospitalización**: quien se queda más días acumula más. No sirven para predecir y no se pueden poner en el tiempo (sin fecha).
- Lectura: una mayor carga de estudios al inicio no explica una espera más larga. Es coherente con que el tiempo largo es espera y no trabajo clínico (sección anterior y `docs/caracterizacion_etapas_tu.md`).

## Lectura
- **Apunta a «espera con poca actividad», no a «atención demorada».** Quienes esperan más de 72 h tienen la misma ráfaga inicial de laboratorios que los demás, un solo bloque TU y después horas o días sin tomas. Si el tiempo largo fuera atención clínica intensa, se vería más actividad a medida que pasa el tiempo, y no menos.
- **Lo que esto no prueba:**
  - Solo el **38 % de las estancias tiene laboratorio** en la ventana; en el resto no se puede decir nada sobre la actividad (más de la mitad de B y C no tiene ninguna toma ni diagnóstico registrado, en parte por la cobertura de la base).
  - La atención de enfermería, las interconsultas, las imágenes y los procedimientos **no tienen hora o no están en la base**. Un paciente sin laboratorios puede estar siendo atendido.
  - El tiempo sin laboratorio no equivale a «sin cama disponible»: puede ser un paciente estable que espera cupo en un servicio.
- **Con las pruebas de saturación y espera** (`docs/saturacion_y_espera.md`): la mediana depende de la hora a la que se asignan las camas y no de la ocupación; los datos de aquí cuadran con eso (tiempo de espera sin actividad clínica registrada) pero no lo demuestran.
- **(Corregido)** Sí se pueden caracterizar las etapas crudas, una por una, por lo que cae dentro de su intervalo (laboratorios y diagnósticos con hora): `docs/caracterizacion_etapas_tu.md`.

## Limitaciones
- Cobertura de laboratorio del 38 %; la mitad de los conceptos de laboratorio vienen sin traducción (concepto 0), así que no se analizó qué examen es.
- El diagnóstico se registra al llegar y justo antes de la cama; no dice cuándo se supo.
- Las estancias gemelas se resolvieron con la persona real (`persona_real`; si no se pudo identificar, el registro conservado), con la advertencia de CLAUDE.md 4.10.
- Son asociaciones, no causas.
