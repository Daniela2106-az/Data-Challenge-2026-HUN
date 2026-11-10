# Las etapas TU antes de la cama, una por una (9-nov-2026)

Script: `src/caracterizar_etapas_tu.py` (tablas `tu_etapas_*.csv` en `resultados/tablas/`, fuera de git). Continúa `docs/caracterizacion_tu.md`, que miraba la espera como un solo bloque.
Periodo confiable, estancias únicas con espera medida; **22.466 estancias con 55.457 etapas TU crudas** antes de la cama (del registro de la persona real).

**Por qué:** en `visit_detail` cada estancia tiene **varias etapas TU** pegadas una tras otra (el fin de una es el inicio de la siguiente); el pipeline las junta en un bloque, y eso escondía la estructura. Aquí se miran sin juntar, y cada una se caracteriza por lo que cae dentro de su intervalo: **laboratorios** (hora de toma, confiable) y **diagnósticos** (hora del primer registro). Los procedimientos no tienen hora y no se pueden asociar a una etapa.

## Resultados

**1. Hay varias etapas, y su número casi no crece con la espera** (promedio por estancia): 1,28 en el grupo A (menos de 6 h), 2,94 en B (12–48 h) y 3,30 en C (más de 72 h). Pasar de 2 h a 100 h de espera añade apenas dos etapas.

**2. El tiempo extra de las esperas largas está en la ÚLTIMA etapa.** Duración mediana por posición (en estancias con 2 o más etapas):

| Grupo | Primera | Intermedias | Última | % de la espera en la última |
|---|---|---|---|---|
| A < 6 h | 1,3 h | 0,9 h | 1,8 h | 53 % |
| B 12–48 h | 1,9 h | 5,5 h | 14,9 h | 63 % |
| C > 72 h | 2,0 h | 10,6 h | 69,3 h | 78 % |

La primera etapa dura unas 2 h en todos los grupos. La última etapa empieza a las 1,6 h de la llegada en A, a las 8,5 h en B y a las 16,4 h en C (p75: 47 h), y dura 1,8 h, 14,9 h y 69,3 h. Es decir, el tiempo antes de la última etapa se multiplica por 10 y el tiempo dentro de ella por 38.

**3. Cada etapa tiene un perfil de actividad distinto** (estancias con al menos una toma de laboratorio):

| Posición | % de etapas con alguna toma | Tomas por 10 h de etapa | Duración mediana |
|---|---|---|---|
| Única (solo una etapa) | 97,5 % | 9,3 | 4,2 h |
| Primera | 32,9 % | 5,7 | 1,9 h |
| Intermedia | 66,3 % | 3,8 | 6,5 h |
| Última | 66,2 % | 1,75 | 16,2 h |

- En la primera etapa casi no hay tomas en la primera hora (0,11 por etapa) y sí después: se evalúa primero y se piden exámenes luego.
- **Cada etapa nueva (intermedia o última) arranca con una ráfaga de tomas:** 0,87 en su primera hora frente a 0,21 por hora en el resto, 4,1 veces más.
- **La última etapa se vuelve silenciosa en las esperas largas:** tomas por 10 h de etapa de **19,9 en A, 2,2 en B y 1,05 en C**. Quien recibe cama pronto sigue en trabajo activo hasta el final; quien espera mucho pasa su última etapa casi sin laboratorios (una toma cada ~10 h).

**4. Los diagnósticos se registran en la primera etapa.** El 73,1 % de los diagnósticos distintos se registra por primera vez en la primera etapa y el 17,2 % en la única; solo el 5,6 % en la última, aunque esa etapa concentra el **60,5 %** de las horas de TU.

**5. La hora del cambio de etapa** no sigue claramente los cambios de turno: se reparte durante el día, con picos a las 17–18 h (6–7 %) y entre las 22 y la 1 h (5–6 %). La última etapa empieza con mayor frecuencia a las 18 h (6,7 %), a las 0–1 h y a las 22–23 h. Es parecido a las dos olas de asignación de cama (15–17 h y 20–23 h) de `docs/saturacion_y_espera.md`.

## Lectura
- Las etapas parecen una **secuencia de fases**: una primera etapa de ~2 h (valoración inicial, donde se registra el diagnóstico), etapas intermedias (reevaluaciones con nuevos exámenes) y una **última etapa** de duración variable.
- **El cuello de botella está en la última etapa TU** (62–78 % de la espera), y en las esperas largas es una etapa de **poca actividad clínica registrada** (laboratorios ~1 por 10 h, casi ningún diagnóstico nuevo). Eso es consistente con **espera con poca atención nueva** (por ejemplo, con la hospitalización ya decidida y sin cama), no con atención demorada. Es una **hipótesis**: la base no dice qué significa cada etapa.
- Junto con `docs/saturacion_y_espera.md`: la mediana de la espera no sube con la ocupación, pero la cama se asigna en dos olas; la última etapa de las esperas largas es una espera con poca actividad. Todo apunta a un **límite de proceso y de horario de asignación** además de la saturación de la cola larga.

## Limitaciones
- No sabemos qué es cada etapa (la base no trae servicio, ubicación ni profesional: `provider_id` siempre vale 0). La lectura es por intervalo y actividad, no por significado.
- La **cobertura** de laboratorio es del 38 % de las estancias; los diagnósticos se registran en la primera etapa y justo antes de la cama; los procedimientos no se pueden fechar. Una etapa sin tomas puede estar siendo atendida (enfermería, imágenes, interconsultas) sin que quede en la base.
- Las etapas sin hora de fin (2,9 % de las etapas antes de la cama) se llevaron hasta la asignación de cama.
- La comparación entre etapas «última» e «intermedia» solo se puede hacer en estancias con 2 o más etapas (el 74 % de las estancias).
- El número de etapas crece con la espera en parte por construcción (más tiempo, más cambios).
- Son asociaciones, no causas.
