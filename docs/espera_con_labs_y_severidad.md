# Qué pasa durante la espera de cama y severidad desde los laboratorios (A8 puntos 6 y 10, 8-nov-2026; severidad rehecha el 11-nov)

> **Corrección del 10 y 11-nov.** (1) La cobertura de laboratorio durante la espera (38 %, sección 6) salía de un cruce que omitía los laboratorios de las visitas copia; con la corrección, ~70 % de las estancias tiene alguna toma (`docs/caracterizacion_tu.md`). (2) **La sección 10 se rehízo con el cruce por persona real** (`sql/severidad_labs_6h_persona.sql`, `src/severidad_labs.py` v2): la versión del 8-nov cruzaba los valores por visita, mezclaba los laboratorios de las dos personas de una estancia gemela y solo llevaba a la visita raíz las copias de la misma persona, así que dejaba sin laboratorio al 60 % de las estancias. Con la persona real la cobertura de las primeras 6 h pasa de **40 % a 52 %** de las estancias (3.143 recuperan sus propios laboratorios; 554 solo tenían los de la otra persona). Las conclusiones de fondo no cambian; cambian las cifras y aparece un efecto nuevo (creatinina alta: +13 % de espera). (3) En el computador de Daniela las banderas **no estaban entrando al estimador** (buscaba los archivos en otra carpeta): corregido, resultados en `docs/estimador_tiempos.md` 3.3.

Scripts: `src/espera_con_labs.py`, `src/severidad_labs.py` (v2) y `src/prueba_banderas_persona.py`. Consultas: `sql/espera_labs_y_texto.sql`, `sql/severidad_labs_6h.sql` (cruce viejo, solo para comparar) y `sql/severidad_labs_6h_persona.sql` (resultados `sevp_*.csv` en `datos/crudos/consultas/`, fuera de git).
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

## 10. Severidad desde el texto de los laboratorios (rehecho el 11-nov con el cruce por persona real)
El texto trae valor, unidad y rango de referencia, y se puede leer. De las primeras 6 h se extrajeron (con expresiones regulares) leucocitos, hemoglobina, creatinina, BUN, lactato, potasio, sodio, troponina I y PCR, y se marcó cada valor fuera de un punto de corte genérico (leucocitos > 12 o < 4; hemoglobina < 10; creatinina > 1,5; BUN > 40; lactato > 2,2; potasio > 5,5; sodio < 130 o > 150; troponina > 1,0; PCR > 50). La **puntuación** es el número de banderas.

**Cómo se cruza (v2):** la consulta devuelve los valores por visita **y por persona** de cada fila de laboratorio. Las filas de las visitas copia (el 81 % de las que tienen laboratorio) se llevan a su visita raíz, **todas**, y de ahí a la estancia; se conserva solo lo de la **persona real** de la estancia (`persona_real` de la tabla de episodios o, si no se identificó, la del registro conservado) y, en los episodios sin cama, lo de la persona del propio registro. Frente al cruce del 8-nov (por visita, sin persona, copias solo de la misma persona), de las 22.819 estancias del periodo confiable con laboratorio en las 6 h pasan del **40,3 % al 51,6 %**; entre las que tenían valor en los dos cruces (8.845) solo 34 cambian alguna bandera, así que el problema del cruce viejo era de **cobertura** (dejaba fuera los laboratorios propios colgados de copias de «otra persona»), no de valores equivocados. Tabla: `severidad_labs_cruce_persona.csv`.

**Hospitalización** (56.109 episodios con atención y laboratorio propio en las primeras 6 h; el 21,1 % se hospitaliza, más que el ~10 % general porque a los más graves les piden más exámenes):

| Puntos | Episodios | Se hospitalizan |
|---|---|---|
| 0 | 29.854 | 15,2 % |
| 1 | 16.905 | 22,4 % |
| 2 | 5.973 | 32,3 % |
| 3 o más | 3.377 | 47,2 % |

Los más asociados: potasio alto (52 % se hospitaliza contra 21 % sin la bandera), lactato alto (50 %), BUN alto (45 %), creatinina alta (37 %). Un modelo logístico con edad, sexo, tipo de visita y hora tiene AUC de 0,58 entre quienes tienen laboratorio (entrenado hasta 2025-06, probado de 2025-07 a 2026-04); **con las banderas sube a 0,66**.

**Estancia en cama y espera** (11.780 estancias hospitalizadas con laboratorio de la persona real):
- Estancia: +24 % con 2 puntos y +38 % con 3 o más frente a 0 puntos; R² de 4,0 % a 5,4 % (con puntos) o 7,1 % (con las banderas por separado).
- **Espera de cama: la puntuación sumada no la cambia** (−1 %, +6 %, +1 %; R² de 5,1 % a 5,1 %), medida solo en esperas de 6 h o más (8.652), para que todos los laboratorios de la ventana caigan antes de la cama. **Pero no es que la gravedad no importe: la suma junta efectos opuestos** (ver abajo); con las banderas por separado el R² sube a 8,0 %. El cuadro con esperas más cortas mostraba −38 % para 3 o más puntos, pero era un artefacto: en esperas cortas la ventana de 6 h incluye laboratorios de después de asignar la cama.

**Efecto de cada bandera sobre la espera** (esperas de 6 h o más, controlando edad, sexo, tipo de visita, franja y año; % frente a no tenerla, IC 95 %; entre paréntesis, el valor del 8-nov con el cruce viejo):

| Bandera | Estancias | Efecto en la espera |
|---|---|---|
| Troponina alta | 355 | **−42 %** (−46 a −36) (antes −41 %) |
| BUN alto | 482 | **−17 %** (−25 a −9) (antes −18 %) |
| Leucopenia | 166 | **−17 %** (−27 a −6) (antes −15 %) |
| Lactato alto | 432 | **−16 %** (−23 a −8) (antes −19 %) |
| Potasio alto | 131 | −15 % (−28 a +2): ya no es claro (antes −18 %) |
| Leucocitos altos | 2.897 | −4 % (−8 a 0) |
| **Creatinina alta** | 1.337 | **+13 %** (+7 a +20): **nuevo** (antes +1 %, sin efecto) |
| PCR alta | 1.802 | **+16 %** (+11 a +22) (antes +13 %) |
| Anemia, sodio bajo, sodio alto | | sin efecto claro |

**Lectura:** los cuadros con señales de gravedad aguda (troponina, lactato, BUN) reciben cama **antes**, probablemente porque van a cardiología o cuidados críticos (coincide con A6: UCI, mediana de 2,7 h); en cambio los cuadros inflamatorios o infecciosos (PCR alta) y los de **función renal alterada (creatinina alta)** esperan **más**: son hospitalizaciones de medicina interna general, que es donde se concentra la espera larga. La puntuación sumada no cambia la espera porque junta efectos de signo contrario. Quedan dos conclusiones: la prioridad clínica existe para algunos cuadros, y la espera larga se concentra en pacientes sin esas señales de urgencia vital (hospitalización clínica general). Asociación, no causa.

**Límites:** solo se mide en quienes tienen laboratorio en las primeras 6 h (la decisión de pedirlo ya indica gravedad; además la consulta solo lee hemograma y la química básica, así que «sin valor» no es «sin laboratorio»: con cualquier toma la cobertura es ~61 %); los puntos de corte son genéricos y deben ser validados por un clínico; en el 2,4 % de las estancias gemelas no se identificó la persona real y se usa la del registro conservado; las 6 h no se conocen «al llegar», así que sirve para un estimador que se actualiza a las pocas horas (A6), no para la entrada. El aporte al modelo es modesto: la explicación de la estancia pasa de ~4 % a ~7 % y la de la espera de ~5 % a ~8 %; más del 90 % de la variación sigue sin explicarse.

**Para A6, prueba hecha dentro del estimador** (`src/prueba_banderas_persona.py`, 11-nov; antes solo había una prueba sencilla, sección 3 de `severidad_labs.py`, que con el cruce nuevo da R² de 6,9 % a 12,4 % entre las 8.652 estancias con espera de más de 6 h). Dentro del estimador completo (historial, recorrido, hora, ocupación), con el modelo fijo entrenado hasta jun-2025 y probado de jul-2025 a abr-2026, las banderas suman **+1,4 puntos a las 6 h de espera** (IC 95 % +0,9 a +1,9; +2,4 entre quienes tienen laboratorio) y desde las 12 h su aporte queda dentro del azar (+0,4 a +0,9) y en el periodo ene-jun 2025 incluso resta (−0,8 a −1,0, con el 0 dentro). El cruce nuevo y el viejo estiman igual de bien (diferencias entre −0,6 y +0,3 puntos): el error del cruce viejo era de cobertura. Detalle y tablas en `docs/estimador_tiempos.md` 3.3.
