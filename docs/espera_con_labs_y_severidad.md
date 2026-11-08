# Qué pasa durante la espera de cama y severidad desde los laboratorios (A8 puntos 6 y 10, 8-nov-2026)

Scripts: `src/espera_con_labs.py` y `src/severidad_labs.py`. Consultas: `sql/espera_labs_y_texto.sql` y `sql/severidad_labs_6h.sql` (resultados en `datos/crudos/consultas/`, fuera de git).
Periodo confiable (feb-2023 a 9-abr-2026). Todo son asociaciones.

## 6. Laboratorios dentro de la espera de cama
Se contaron las tomas de laboratorio entre la primera etapa y la asignación de cama (22.819 estancias únicas; 37,8 % tiene al menos una toma).

| Espera | Estancias | Con algún laboratorio | Tomas por 24 h | Horas de la espera con una toma |
|---|---|---|---|---|
| < 6 h | 5.446 | 26 % | 14,8 | 14 % |
| 6–12 h | 3.465 | 39 % | 8,1 | 12 % |
| 12–24 h | 3.960 | 37 % | 4,5 | 7 % |
| 24–48 h | 5.398 | 42 % | 3,3 | 5 % |
| 48–72 h | 2.220 | 45 % | 2,5 | 4 % |
| > 72 h | 2.330 | 48 % | 2,0 | 3 % |

- Las tomas por día **bajan** con la espera: la atención con exámenes se concentra al inicio y después hay pocas tomas. En las esperas de más de 72 h la última toma cae en mediana 32 h antes de asignar la cama.
- De las esperas de más de 24 h que tienen algún laboratorio, en el 65 % la última toma fue más de 12 h antes de la cama y en el 42 % más de 24 h antes.
- **Límite:** que no haya laboratorio no prueba que no haya atención (medicamentos, vigilancia y valoraciones no dejan huella aquí; solo el 65 % de las estancias tiene laboratorio en toda la hospitalización). **No separa la atención de la espera pura**, que era el objetivo. Lo que sí dice: las esperas largas son, en lo que se ve, más pasivas en estudios que las cortas.

## 10. Severidad desde el texto de los laboratorios
El texto trae valor, unidad y rango de referencia, y se puede leer. De las primeras 6 h se extrajeron (con expresiones regulares) leucocitos, hemoglobina, creatinina, BUN, lactato, potasio, sodio, troponina I y PCR, y se marcó cada valor fuera de un punto de corte genérico (leucocitos > 12 o < 4; hemoglobina < 10; creatinina > 1,5; BUN > 40; lactato > 2,2; potasio > 5,5; sodio < 130 o > 150; troponina > 1,0; PCR > 50). La **puntuación** es el número de banderas. El 81 % de las visitas con laboratorio son copias: los valores se pasaron a la visita original cuando la copia es de la misma persona.

**Hospitalización** (31.266 episodios con atención y laboratorio en las primeras 6 h; el 27,9 % se hospitaliza, más que el 10 % general porque a los más graves les piden más exámenes):

| Puntos | Episodios | Se hospitalizan |
|---|---|---|
| 0 | 16.156 | 20,3 % |
| 1 | 9.331 | 28,9 % |
| 2 | 3.590 | 41,7 % |
| 3 o más | 2.189 | 57,2 % |

Los más asociados: lactato alto (60 % se hospitaliza contra 26 % sin la bandera), potasio alto (62 %), BUN alto (54 %), creatinina alta (45 %). Un modelo logístico con edad, sexo, tipo de visita y hora tiene AUC de 0,58 entre quienes tienen laboratorio (entrenado hasta 2025-06, probado de 2025-07 a 2026-04); **con las banderas sube a 0,65**.

**Estancia en cama y espera** (9.545 estancias hospitalizadas con laboratorio):
- Estancia: +16 % con 2 puntos y +29 % con 3 o más frente a 0 puntos; R² de 4,1 % a 4,8 % (con puntos) o 6,5 % (con las banderas por separado).
- **Espera de cama: sin efecto** (−5 %, +1 %, −9 %; R² de 8,2 % a 8,3 %), medida solo en esperas de 6 h o más, para que todos los laboratorios de la ventana caigan antes de la cama. El cuadro completo con esperas más cortas mostraba −38 % para 3 o más puntos, pero era un artefacto: en esperas cortas la ventana de 6 h incluye laboratorios de después de asignar la cama.

**Lectura:** la gravedad que se ve en los laboratorios predice si se hospitaliza y, algo, cuánto se queda, pero **no cambia cuánto se espera la cama**. Es coherente con que la espera es de organización (disponibilidad de camas y altas) y no de prioridad clínica; no hay evidencia de que los más graves reciban cama antes.

**Límites:** solo se mide en quienes tienen laboratorio en las primeras 6 h (la decisión de pedirlo ya indica gravedad); los puntos de corte son genéricos y deben ser validados por un clínico; en estancias gemelas los laboratorios pueden ser de la otra persona del par; las 6 h no se conocen «al llegar», así que sirve para un estimador que se actualiza a las pocas horas (A6, que hoy usa solo el número de laboratorios), no para la entrada. El aporte al modelo es modesto: la explicación de la estancia pasa de ~4 % a ~7 %, y el 90 % de la variación sigue sin explicarse.

**Para A6 (Samuel):** si se quiere probar, las banderas de las 6 h se pueden agregar al estimador de tiempo restante; esperable una mejora pequeña en la estancia y nula en la espera.
