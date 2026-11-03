# Diagnósticos y tiempos de atención (tarea A3, 26-oct-2026; recalculado el 29-oct y el 1-nov con la regla de estancia única v3.8)

**Qué pide el instructivo:** usar `CONDITION_OCCURRENCE` y `PROCEDURE_OCCURRENCE` para "analizar diagnósticos y procedimientos asociados a los tiempos de atención y la complejidad
clínica de las visitas", y entender "qué características están asociadas a retrasos". Esta tarea lo hace por **grupo de diagnóstico**.
Código: `src/generar_borrador_mapeo_dx.py` (agrupación) y `src/diagnosticos_y_tiempos.py` (análisis). Tablas en `resultados/tablas/`, gráfico `resultados/graficos/tiempos_por_dx.png`.

## 1. Cómo se agrupó
- Los diagnósticos vienen en SNOMED en inglés, sin jerarquía y con el 37 % de las filas sin traducir. Se agruparon por palabras del nombre en 16 grupos clínicos más "Recién nacido" y
  "Otros / sin clasificar" (`datos/referencia/mapeo_dx.csv`). Cubre los 2.404 diagnósticos con diagnóstico principal; **0,9 % de los episodios queda sin clasificar**.
- Es un **borrador por reglas**, revisado a mano en los 300 más frecuentes (85 % de los episodios con diagnóstico). Falta que alguien del área de salud lo valide. Correcciones: `datos/referencia/mapeo_dx_correcciones.csv`.
- Diagnóstico principal = primer diagnóstico traducido por fecha (no sabemos cuál es el principal real: `condition_type_concept_id` siempre vale 0).

## 2. Qué estancia en cama se conserva (cambio del 29-oct-2026) y el sesgo del diagnóstico
La misma estancia en cama aparece en dos registros (estancias gemelas, `CLAUDE.md` 4.6). El HUN confirmó en la sesión del 29-oct que lo más probable es que sean **duplicados** y que hay que quedarse con
el registro que trae la información clínica. Antes se conservaba el de menor `visit_occurrence_id`, que casi nunca era el que tenía diagnóstico (solo 163 de los 6.414 pares en que uno solo lo tenía).
Ahora `preparar_variables.py` (v2.2, sección 4b) conserva el que tiene **más tipos de información** (diagnóstico, procedimiento, laboratorio), y si le falta algo lo **hereda del gemelo** (los dos se reparten la
información: uno trae diagnósticos y laboratorios, el otro procedimientos). Edad, sexo y `person_id` son los del registro conservado. `FUSIONAR_INFO=0` desactiva la herencia.

| Estancias únicas (25.777) | Regla anterior (id menor) | Regla nueva |
|---|---|---|
| Con diagnóstico | 35,8 % | **65,2 %** |
| Con laboratorio | 40,6 % | **69,3 %** |
| Con procedimiento | 90,4 % | 90,8 % |
| Espera de cama mediana | 20,4 h | 18,8 h (con la regla v3.8 la espera es la de la estancia y no depende del registro conservado) |

Los tiempos, ingresos y camas no cambian (la estancia es la misma). Cambia quién describe al paciente.

**El sesgo de registro casi desapareció.** Porcentaje de hospitalizados con diagnóstico según su espera (`dx_registrado_segun_espera.csv`):

| Espera de cama | 0–3 h | 3–6 h | 6–12 h | 12–24 h | 24–48 h | 48–72 h | más de 72 h |
|---|---|---|---|---|---|---|---|
| Regla anterior | 60,5 | 60,2 | 43,3 | 34,4 | 27,5 | 29,0 | 27,5 |
| **Regla nueva (v3.8)** | 63,8 | 74,5 | 62,7 | 61,3 | 64,2 | 69,9 | 70,6 |

La espera mediana con diagnóstico es 19,6 h y sin diagnóstico 17,6 h (antes 10,2 y 24,5): el sesgo hacia esperas cortas ya no está. Como los diagnósticos de los dos registros se unen, **el diagnóstico de
una estancia puede ser de la otra persona** (prueba del 20-oct): se asume que son duplicados, como dijo el HUN. Falta aún el 35 % de los hospitalizados sin diagnóstico traducido y el 80 % de los no hospitalizados.
**Pregunta B9 (cuándo se registra el diagnóstico)** sigue sin respuesta y no habrá más sesiones: se declara como limitación.

## 3. Qué grupos esperan más cama (entre quienes tienen diagnóstico)
Mediana de espera de cama (h) y estancia en cama (h), solo grupos con n ≥ 30. Referencia: hospitalizados con diagnóstico, espera 19,6 h y estancia 70,5 h.

| Grupo | Hospitalizados con espera medida | Espera mediana | Espera p90 | Estancia mediana | Estancia p90 |
|---|---|---|---|---|---|
| Musculoesquelético y dolor | 422 | 39,0 | 108,1 | 114,3 | 369 |
| Renal y urinario | 1.577 | 35,0 | 93,1 | 70,4 | 223 |
| Cáncer y tumores | 251 | 32,7 | 107,1 | 114,6 | 489 |
| Digestivo | 2.348 | 29,1 | 76,8 | 87,2 | 259 |
| Trauma y lesiones | 1.662 | 23,8 | 73,4 | 52,4 | 218 |
| Infecciosas | 1.072 | 17,7 | 105,4 | 95,4 | 400 |
| Embarazo, parto y ginecología | 2.009 | 16,8 | 39,1 | 46,5 | 124 |
| Salud mental | 526 | 12,1 | 77,0 | 72,3 | 399 |
| Cardiovascular | 2.302 | 9,5 | 56,7 | 76,8 | 277 |
| Neurológico | 732 | 9,3 | 59,4 | 90,9 | 386 |
| Respiratorio | 1.300 | 8,9 | 61,1 | 70,2 | 280 |

(Las tablas completas, con los 18 grupos, están en `tiempos_por_dx.csv`.)

- **El patrón se mantiene con controles.** Con tipo de visita, franja horaria, año y edad en el modelo (sobre log(espera + 1), `efecto_dx_espera.csv`), frente a Digestivo: Cardiovascular −66 % (IC 95 %: −68 a −64),
  Neurológico −61 %, Respiratorio −37 %; Renal y urinario +15 % (+8 a +23) y Musculoesquelético +17 % (+5 a +31). El grupo de diagnóstico sube el R² de 8,7 % a 18,8 % (solo entre quienes tienen diagnóstico).
  Es estable por año: urgentes (cardiovascular, neurológico, respiratorio) 6,5–9,8 h; quirúrgicos y urológicos (musculoesquelético, renal, digestivo, cáncer) 29–36 h.
- **Cambió con la regla nueva:** los grupos "urgentes" esperan unas 9 h (antes 4 h) y los demás 29–39 h (antes 22–32 h). Las cifras anteriores estaban sesgadas hacia quien recibía cama rápido. El orden de los grupos casi no cambió.
- **Lectura posible (hipótesis, sin comprobar):** quien llega con infarto, ACV o dificultad respiratoria recibe cama más rápido (prioridad clínica), y la espera larga se concentra en pacientes de **cirugía, urología y
  ortopedia** (cólico renal 40 h, colecistitis 38–42 h). Eso apunta a una cola por tipo de cama o servicio, no a una cola general. No tenemos servicio, piso ni cama en la base, y no habrá más sesiones
  con el HUN para confirmarlo.
- **Estancia:** las más largas son las de recién nacido (136 h, solo 42 casos), cáncer (115 h), endocrino (118 h) y musculoesquelético (115 h); las más cortas, embarazo (47 h), trauma (53 h) y dolor/síntomas (53 h). Sepsis (190 h, p90 de 597 h)
  y colecistitis (137–142 h) están entre los diagnósticos frecuentes con estancias largas (`tiempos_por_dx_detalle.csv`).
- **Embarazo/parto y recién nacido** tienen una estancia corta y espera baja: seguramente son otro flujo (obstetricia), no comparable con medicina interna.

## 4. Urgencias sin hospitalización y complejidad
- La duración de urgencias de quienes no se hospitalizan solo existe en ~38 % de los episodios y está sesgada (`sesgo_medicion_urgencias.csv`); se reporta en `tiempos_por_dx.csv` (`urgencias_sin_hosp_mediana_h`) con su n y **no se usa para conclusiones**.
- **Complejidad:** casi todos los episodios tienen 1 diagnóstico traducido y 1–2 procedimientos distintos (mediana); solo endocrino y cáncer llegan a 2 diagnósticos. Esas cifras casi no discriminan entre grupos
  y crecen con la estancia (causalidad inversa), por eso se muestran solo como descripción. Los procedimientos no tienen fecha (`procedure_date` vacía), así que no se pueden ubicar en el tiempo.

## 5. Qué se hace con esto
- **Para el dashboard y la recomendación R6:** una parte del problema parece concentrarse en pacientes de cirugía, urología y ortopedia. Una acción posible (a validar con el HUN) es
  gestionar camas de esos servicios por separado. Hoy no se puede cuantificar.
- **Para A1 y A2:** usar el grupo de diagnóstico **solo entre quienes lo tienen** y reportar siempre la cobertura; no usarlo para decir "el diagnóstico causa la espera".
- **Para A2b (estancias que se disparan):** la extracción de diagnósticos por visita con `person_id` igual al de la visita (`sql/estancias_perfil.sql`) también ayudará a ver si el registro tardío cambia el panorama.

## 6. Límites
Asociación, no causa. Grupos por palabras clave (sin validación clínica). Cobertura de diagnóstico del 65 % en hospitalizados (se unió la información de los dos registros duplicados; el diagnóstico puede ser de la otra persona). Diagnóstico principal elegido por fecha, no por el hospital.
