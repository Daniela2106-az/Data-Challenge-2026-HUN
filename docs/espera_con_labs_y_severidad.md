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
- **Espera de cama: la puntuación sumada no la cambia** (−5 %, +1 %, −9 %; R² de 8,2 % a 8,3 %), medida solo en esperas de 6 h o más, para que todos los laboratorios de la ventana caigan antes de la cama. **Pero no es que la gravedad no importe: la suma junta efectos opuestos** (ver abajo). El cuadro completo con esperas más cortas mostraba −38 % para 3 o más puntos, pero era un artefacto: en esperas cortas la ventana de 6 h incluye laboratorios de después de asignar la cama.

**Efecto de cada bandera sobre la espera** (esperas de 6 h o más, controlando edad, sexo, tipo de visita, franja y año; % frente a no tenerla, IC 95 %):

| Bandera | Estancias | Efecto en la espera |
|---|---|---|
| Troponina alta | 316 | **−41 %** (−47 a −36) |
| Lactato alto | 356 | **−19 %** (−26 a −10) |
| BUN alto | 406 | **−18 %** (−26 a −9) |
| Potasio alto | 110 | −18 % (−32 a −1) |
| Leucopenia | 165 | −15 % (−25 a −5) |
| PCR alta | 1.458 | **+13 %** (+7 a +19) |
| Leucocitos altos, anemia, creatinina alta, sodio | | sin efecto claro |

**Lectura:** los cuadros con señales de gravedad aguda (troponina, lactato, BUN, potasio) reciben cama **antes**, probablemente porque van a cardiología o cuidados críticos (coincide con A6: UCI, mediana de 2,7 h); en cambio los cuadros inflamatorios o infecciosos (PCR alta) esperan **más**. La puntuación sumada no cambia la espera porque junta efectos de signo contrario. Quedan dos conclusiones: la prioridad clínica existe para algunos cuadros, y la espera larga se concentra en pacientes sin esas señales (hospitalización clínica general). Asociación, no causa.

**Límites:** solo se mide en quienes tienen laboratorio en las primeras 6 h (la decisión de pedirlo ya indica gravedad); los puntos de corte son genéricos y deben ser validados por un clínico; en estancias gemelas los laboratorios pueden ser de la otra persona del par; las 6 h no se conocen «al llegar», así que sirve para un estimador que se actualiza a las pocas horas (A6, que hoy usa solo el número de laboratorios), no para la entrada. El aporte al modelo es modesto: la explicación de la estancia pasa de ~4 % a ~7 %, y el 90 % de la variación sigue sin explicarse.

**Para A6 (Samuel), prueba hecha** (`severidad_labs.py`, sección 3: entre las 7.065 estancias con espera de más de 6 h, entrenamiento hasta 2025-06 y prueba desde 2025-07, modelo de gradiente como en A6): predecir el tiempo restante con edad, sexo, tipo de visita, hora, ocupación y carga tiene R² de **12,1 %** en la prueba; **agregar las banderas lo sube a 16,9 %** (el error baja con intervalo 95 % de −0,11 a −0,04 en escala logarítmica, que excluye el cero); agregar solo la puntuación sumada no mejora (12,6 %, intervalo que incluye el cero). Es una mejora real pero **no comparada con el estimador A6 completo** (que ya usa historial y recorrido en urgencias, y esas variables podrían captar parte de lo mismo): corresponde a Samuel probar las banderas dentro de A6 a partir de las 6 h de espera. Solo aplican a quien tiene laboratorio en las primeras 6 h (en la prueba, 7.065 de ~9.500 estancias con espera de 6 h o más).
