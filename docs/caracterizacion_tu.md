# ¿Qué pasa en urgencias mientras se espera la cama? (9-nov-2026; corregido el 10-nov)

> **Corrección del 10-nov:** la primera versión de este documento (y de `docs/caracterizacion_etapas_tu.md`) **omitía los laboratorios y diagnósticos que cuelgan de visitas copia**, que son la mayoría de los que tienen concepto traducido. Eso hacía parecer que solo el 38 % de las estancias tenía laboratorio en la espera. Con las copias llevadas a su visita raíz (y filtrando siempre por la persona real) la cobertura es **~70 %** (15.614 de 22.466 estancias). Las conclusiones de fondo se mantienen; cambian los porcentajes de cobertura y algunas tasas, y están corregidos abajo.
>
> **Otra corrección (9-nov):** este documento mira la espera como un solo bloque, que es como la junta nuestro pipeline. En la base cada estancia tiene **varias etapas TU** seguidas (2,5 en promedio): su caracterización está en `docs/caracterizacion_etapas_tu.md`.

Script: `src/caracterizar_tu.py`. Tablas `tu_*.csv` en `resultados/tablas/` (fuera de git). Consulta a la base: `sql/espera_labs_dx_con_hora.sql` (laboratorios y diagnósticos con su hora).
Periodo confiable (1-feb-2023 a 9-abr-2026, sin el 28 y 29 de marzo de 2026), estancias únicas con espera medida: **22.801**.

**Pregunta de Daniela:** el tiempo antes de la cama es casi todo urgencias (etapas TU). ¿Quienes esperan mucho hacen algo distinto allí (más pruebas, más bloques de atención), o solo esperan más en el mismo estado?

## Cómo se hizo (y sus límites)
- Las etapas TU **no traen diagnóstico ni laboratorio propios**: esa información cuelga de la visita. Se caracteriza entonces la **ventana de espera** (de la llegada a la asignación de cama), que es casi toda TU.
- Solo se usan filas de la **persona real** de la estancia (de cualquiera de sus visitas, copias incluidas) y solo las que caen dentro de esa ventana. Los procedimientos no tienen hora y no entran.
- Grupos por espera: **A** menos de 6 h (5.443 estancias), **B** 12–48 h (9.348), **C** más de 72 h (2.327), y 6–12 h (3.464) y 48–72 h (2.219) como apoyo.
- Una espera larga acumula más tomas por tener más tiempo. Por eso se comparan **tasas**, las **primeras horas** (misma ventana para todos) y el **tiempo sin laboratorio antes de la cama**.
- El diagnóstico **no sirve para medir inactividad**: el primero se registra al minuto de llegar (mediana 0,02 h) y el último, a unos 10–30 minutos de la cama, en todos los grupos.

## Resultados

**1. (Corregido) Los bloques TU son 1,0 en todos los grupos porque el pipeline junta las etapas TU seguidas.** Las etapas crudas sí son varias y sí se diferencian: ver `docs/caracterizacion_etapas_tu.md`.

**2. Los que esperan mucho son pacientes algo distintos de entrada:**

| Grupo | Edad mediana | Con laboratorio en la espera | Con diagnóstico | En las primeras 6 h: tomas promedio |
|---|---|---|---|---|
| A < 6 h | 29 | 42,6 % | 61,2 % | — |
| B 12–48 h | 33 | 77,4 % | 58,4 % | 4,03 |
| C > 72 h | 52 | 84,7 % | 68,0 % | 4,97 |

En las primeras 6 h (misma ventana), C tiene más laboratorio (71,6 % frente a 65,6 %) y más diagnósticos distintos (1,25 frente a 1,00). Son más mayores y algo más complejos. (A tiene menos laboratorio sobre todo porque su espera es muy corta: casi no da tiempo a pedir algo.)

**3. La actividad de laboratorio se concentra al principio y luego casi se apaga, igual en todos los grupos.** Tomas por 10 horas-paciente, entre los que siguen esperando:

| Tramo de la espera | Grupo B | Grupo C |
|---|---|---|
| 0–6 h | 6,7 | 8,3 |
| 6–12 h | 2,3 | 2,9 |
| 12–24 h | 1,5 | 1,9 |
| 24–48 h | 0,8 | 0,9 |
| 48–72 h | — | 0,7 |
| 72–120 h | — | 0,7 |

Después de las primeras 12 h la intensidad cae unas diez veces y se queda plana, también en quienes esperan más de 72 h. En cada tramo C tiene un poco más que B, pero el perfil es el mismo.

**4. Entre quienes tienen laboratorio, esperan mucho tiempo sin ninguno antes de la cama:**

| Grupo | Espera mediana | Horas desde la última toma hasta la cama (mediana) | Con más de 12 h sin laboratorio | Con más de 24 h sin laboratorio |
|---|---|---|---|---|
| A < 6 h | 3,4 h | 0,5 | 0 % | 0 % |
| B 12–48 h | 26,9 h | 10,5 | 43,8 % | 16,3 % |
| C > 72 h | 100,5 h | 31,1 | 71,9 % | 57,1 % |

En el grupo C la última toma cae a las ~68 h de una espera de ~100 h: el último tercio ocurre sin laboratorios registrados. Lo mismo dentro de un mismo diagnóstico, por ejemplo digestivo: 13,2 h sin laboratorio en B frente a 31,0 h en C; cardiovascular, 8,7 h frente a 18,4 h.

## 7. Con el TU como un bloque: espera según la cantidad de actividad
Entre las estancias que siguen esperando a las 6 h (n = 17.358), espera **restante** (más allá de las 6 h) según lo que ya se hizo en esas 6 h:

| Medida de actividad | Franja | n | Restante: mediana | p90 | % con más de 24 h | Edad mediana |
|---|---|---|---|---|---|---|
| Tomas de laboratorio en las 6 h | 0 | 5.817 | 19,2 h | 70,1 | 41,0 | 29 |
| | 1–2 | 1.633 | 19,5 h | 58,6 | 40,7 | 26 |
| | 3–5 | 4.183 | 22,7 h | 75,3 | 47,5 | 36 |
| | 6 o más | 5.725 | 24,6 h | 85,5 | 51,2 | 49 |
| Diagnósticos distintos en las 6 h | 0 | 6.782 | 20,5 h | 69,9 | 42,7 | 27 |
| | 1 | 5.571 | 23,4 h | 76,2 | 48,6 | 44 |
| | 2 o más | 5.005 | 22,7 h | 78,3 | 47,3 | 45 |
| Procedimientos distintos de la **visita** (incluye la hospitalización: no se puede fechar) | 0–5 | 2.482 | 7,1 h | 33,6 | 16,1 | 14 |
| | 6–9 | 1.688 | 15,9 h | 50,0 | 34,2 | 27 |
| | 10–14 | 3.727 | 21,8 h | 64,0 | 44,8 | 31 |
| | 15 o más | 9.461 | 26,9 h | 94,2 | 56,3 | 48 |

- **Más actividad inicial no significa más espera restante cuando se controla la edad.** Controlando edad, tipo de visita, hora de llegada y mes, cada toma de laboratorio en las 6 h cambia la espera restante en **−0,8 % (−1,3 a −0,2)** y cada diagnóstico en **−3,1 % (−4,6 a −1,6)**: más estudios al inicio se asocian con algo menos de espera, no más. El gradiente crudo de los laboratorios (19 h a 25 h) es de edad (29 a 49 años).
- Los procedimientos sí se asocian fuerte, pero **cuentan toda la visita, incluida la hospitalización**: quien se queda más días acumula más. No sirven para predecir y no se pueden poner en el tiempo (sin fecha).

## Lectura
- **Apunta a «espera con poca actividad», no a «atención demorada».** Quienes esperan más de 72 h tienen la misma ráfaga inicial de laboratorios que los demás y después horas o días sin tomas. Si el tiempo largo fuera atención clínica intensa, se vería más actividad con el tiempo, no menos.
- **Lo que esto no prueba:**
  - Hay ~30 % de estancias sin ninguna toma de laboratorio en la espera, y más de la mitad de las tomas que sí hay vienen sin traducir (sin concepto).
  - La atención de enfermería, las interconsultas, las imágenes y los procedimientos **no tienen hora o no están en la base**. Un paciente sin laboratorios puede estar siendo atendido.
  - El tiempo sin laboratorio no equivale a «sin cama disponible»: puede ser un paciente estable que espera cupo en un servicio.
- Con las pruebas de saturación y espera (`docs/saturacion_y_espera.md`): la mediana depende de la hora a la que se asignan las camas y no de la ocupación; los datos de aquí cuadran con eso pero no lo demuestran.
- **(Corregido)** Sí se pueden caracterizar las etapas crudas, una por una, por lo que cae dentro de su intervalo (laboratorios y diagnósticos con hora): `docs/caracterizacion_etapas_tu.md`.

## Limitaciones
- Cobertura de laboratorio ~70 % de las estancias; el 58 % de las filas de laboratorio dentro de la espera viene sin traducir (concepto 0), así que no siempre se sabe qué examen fue.
- El diagnóstico se registra al llegar y justo antes de la cama; no dice cuándo se supo.
- Las estancias gemelas se resolvieron con la persona real (`persona_real`; si no se pudo identificar, el registro conservado), con la advertencia de docs/CONTEXTO_TECNICO.md 4.10.
- Son asociaciones, no causas.
