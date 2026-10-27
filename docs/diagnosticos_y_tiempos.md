# Diagnósticos y tiempos de atención (tarea A3, 26-oct-2026)

**Qué pide el instructivo:** usar `CONDITION_OCCURRENCE` y `PROCEDURE_OCCURRENCE` para "analizar diagnósticos y procedimientos asociados a los tiempos de atención y la complejidad
clínica de las visitas", y entender "qué características están asociadas a retrasos". Esta tarea lo hace por **grupo de diagnóstico**.
Código: `src/generar_borrador_mapeo_dx.py` (agrupación) y `src/diagnosticos_y_tiempos.py` (análisis). Tablas en `resultados/tablas/`, gráfico `resultados/graficos/tiempos_por_dx.png`.

## 1. Cómo se agrupó
- Los diagnósticos vienen en SNOMED en inglés, sin jerarquía y con el 37 % de las filas sin traducir. Se agruparon por palabras del nombre en 16 grupos clínicos más "Recién nacido" y
  "Otros / sin clasificar" (`datos/referencia/mapeo_dx.csv`). Cubre los 2.404 diagnósticos con diagnóstico principal; **0,9 % de los episodios queda sin clasificar**.
- Es un **borrador por reglas**, revisado a mano en los 300 más frecuentes (85 % de los episodios con diagnóstico). Falta que alguien del área de salud lo valide. Correcciones: `datos/referencia/mapeo_dx_correcciones.csv`.
- Diagnóstico principal = primer diagnóstico traducido por fecha (no sabemos cuál es el principal real: `condition_type_concept_id` siempre vale 0).

## 2. Primero la advertencia: el diagnóstico se registra más cuando la cama llega rápido
Entre los hospitalizados (estancias únicas con espera medida), tiene diagnóstico traducido:

| Espera de cama | 0–3 h | 3–6 h | 6–12 h | 12–24 h | 24–48 h | 48–72 h | más de 72 h |
|---|---|---|---|---|---|---|---|
| % con diagnóstico | 60,5 | 60,2 | 43,3 | 34,4 | 27,5 | 29,0 | 27,5 |

(`dx_registrado_segun_espera.csv`.) La espera mediana con diagnóstico es 10,2 h y sin diagnóstico 24,5 h. Consecuencias:
1. **Los grupos de diagnóstico no representan a todos los hospitalizados:** solo el 38,3 % de los hospitalizados y el 20,4 % de los demás tiene diagnóstico traducido, y quien lo tiene
   tiende a haber esperado menos. Los niveles absolutos de espera por grupo están subestimados; solo son comparables **entre grupos, dentro de quienes tienen diagnóstico**.
2. El "diagnóstico explica 3,9 puntos de R²" de `HALLAZGOS.md` 4.5 está en parte inflado por este efecto (tener diagnóstico ya se asocia a esperar menos). No es una causa.
3. **Pregunta nueva al HUN (B9):** ¿cuándo y dónde se registra el diagnóstico (en urgencias, al ingresar a piso, al alta)? Si es al llegar a piso, quien espera más tiempo en urgencias
   simplemente no lo tiene aún.

## 3. Qué grupos esperan más cama (dentro de quienes tienen diagnóstico)
Mediana de espera de cama (h) y estancia en cama (h), solo grupos con n ≥ 30 (todos cumplen). Referencia: hospitalizados con diagnóstico, espera 10,2 h y estancia 69,2 h.

| Grupo | Hospitalizados con espera medida | Espera mediana | Espera p90 | Estancia mediana | Estancia p90 |
|---|---|---|---|---|---|
| Musculoesquelético y dolor | 233 | **32,0** | 91,0 | 95,5 | 346 |
| Cáncer y tumores | 150 | 23,7 | 90,5 | 113,1 | 503 |
| Renal y urinario | 873 | 22,9 | 80,7 | 70,2 | 222 |
| Digestivo | 1.235 | 22,2 | 63,8 | 71,2 | 259 |
| Trauma y lesiones | 1.198 | 18,0 | 55,2 | 48,1 | 207 |
| Embarazo, parto y ginecología | 768 | 12,9 | 37,0 | 48,2 | 165 |
| Salud mental | 450 | 9,8 | 58,9 | 68,4 | 379 |
| Infecciosas | 748 | 8,5 | 73,3 | 85,4 | 352 |
| Respiratorio | 1.069 | 6,8 | 34,1 | 66,0 | 222 |
| Neurológico | 560 | **3,8** | 47,4 | 87,1 | 395 |
| Cardiovascular | 1.694 | **3,8** | 39,6 | 77,7 | 274 |

- **El patrón es fuerte y se mantiene con controles.** Con tipo de visita, franja horaria de llegada, año y edad en el modelo (sobre log(espera + 1), `efecto_dx_espera.csv`),
  frente a Digestivo: Cardiovascular −71 % (IC 95 %: −73 a −69), Neurológico −66 %, Respiratorio −42 %; Renal y urinario +14 % (+4 a +26) y Musculoesquelético +28 % (+10 a +49).
  El grupo de diagnóstico sube el R² de 5,5 % a 18,0 % (solo entre quienes tienen diagnóstico). Es estable por año: urgentes (cardiovascular, neurológico, respiratorio) 4,7–5,6 h
  todos los años; quirúrgicos y urológicos (musculoesquelético, renal, digestivo, cáncer) 21–27 h.
- **Lectura posible (hipótesis, sin comprobar):** quien llega con infarto, ACV o dificultad respiratoria recibe cama en pocas horas (prioridad clínica), y la espera larga se concentra
  en pacientes de **cirugía, urología y ortopedia** (cólico renal 35 h, apendicitis 22 h). Eso apunta a una cola por tipo de cama o servicio, no a una cola general. No tenemos servicio, piso ni cama
  en la base (pregunta C3 al HUN), así que no se puede confirmar.
- **Estancia:** las más largas son las de cáncer (113 h), recién nacido (137 h), endocrino (114 h) y musculoesquelético (95 h); las más cortas, trauma y embarazo (48 h). Sepsis (176 h, p90 de 555 h), ACV (101 h)
  e insuficiencia cardiaca (98 h) están entre los diagnósticos frecuentes con estancias largas (`tiempos_por_dx_detalle.csv`).
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
Asociación, no causa. Grupos por palabras clave (sin validación clínica). Cobertura de diagnóstico del 38 % en hospitalizados, con sesgo hacia esperas cortas. Diagnóstico principal elegido por fecha, no por el hospital.
