# Revisión del mapeo de diagnósticos (`datos/referencia/mapeo_dx.csv`) · 3-nov-2026

**Qué se hizo:** se leyeron los 2.404 diagnósticos del mapeo, uno por uno, agrupados por la categoría que les habían dado las reglas por palabras clave de `src/generar_borrador_mapeo_dx.py`. Se corrigieron **562** (el 23 %) y se dejaron en `datos/referencia/mapeo_dx_correcciones.csv`, que gana sobre las reglas.

**Quién lo revisó:** Claude (un modelo de lenguaje), con el criterio de los capítulos de la CIE-10 y su conocimiento médico general. **No fue un profesional de la salud y no se buscó cada diagnóstico en una fuente externa.** Esto mejora el borrador, pero sigue sin ser una validación clínica: se declara como limitación.

## Convenciones usadas (para que quien revise sepa por qué quedó donde quedó)
- **Por el sistema u órgano que se afecta**, como en la CIE-10. Por eso: ictus y hemorragias cerebrales → Cardiovascular (capítulo circulatorio); gastroenteritis y hepatitis → Digestivo; tuberculosis pulmonar y gripe → Respiratorio; infecciones generales (sepsis, dengue, VIH, sífilis, ITS, parásitos) → Infecciosas.
- **Trauma y lesiones** incluye quemaduras, intoxicaciones, envenenamientos, efectos tóxicos, reacciones a fármacos, complicaciones de la atención y accidentes de tránsito (capítulo de lesiones y causas externas de la CIE-10).
- **Leucemias, linfomas, mieloma y síndromes mielodisplásicos** → Cáncer y tumores.
- **Códigos de control o administrativos** (examen general, seguimiento, "atención a gastrostomía", consejería, problemas sociales, muerte sin atender) → Otros / sin clasificar, porque no describen una enfermedad.
- **Síntomas sueltos** (fiebre, dolor, edema, desorientación) → Dolor y síntomas generales: no dicen la causa.

## Errores sistemáticos que había (y su causa)
| Error | Causa en las reglas |
|---|---|
| Todo lo "congénito" (labio, pie plano, sífilis, microcefalia, etc.) estaba en Renal y urinario | La palabra "congenital" contiene "genital" |
| Quistes de órganos distintos (ovario, bazo, colédoco, rodilla, mandíbula) estaban en Piel | La regla de "cyst" iba antes que la del órgano |
| Hepatopatía alcohólica estaba en Salud mental | Regla de "alcohol" |
| Fiebre/neonatales/embarazo mezclados: recién nacido con ictericia en Digestivo, trastornos del feto en Embarazo | Reglas por palabra de órgano antes que las de edad |
| Cultivos/hemorragias cerebrales repartidas entre Neurológico y Cardiovascular | No había una convención |
| 291 diagnósticos sin regla (neumotórax, bocio, úlcera péptica, mieloma, accidentes de tránsito, trastornos de ansiedad y consumo...) | Faltaban palabras clave |

## Efecto en los resultados (se recalcularon A3, A1, A2 y A2b)
- Quedan **40 sin clasificar** (antes 291; entre los 300 más frecuentes, 4). Los 300 más frecuentes cubren casi todos los episodios con diagnóstico.
- Las cifras por grupo cambiaron poco, no el patrón: cardiovascular, neurológico y respiratorio esperan cama ~9–13 h; musculoesquelético, renal, cáncer y digestivo, 29–39 h (`docs/diagnosticos_y_tiempos.md`, sección 3). Cardiovascular −68 % frente a digestivo (antes −66 %).
- El R² de los factores de la espera casi no cambia (15,8 %).
- En las estancias largas (A2b), los grupos con más largas pasan a ser cáncer (2,8 veces), infecciosas (2,7) y salud mental (2,6).

## Lo que sigue pendiente
Una revisión de una persona del área de salud, empezando por: los grupos de **Dolor y síntomas** y **Otros**, los límites entre **Infecciosas** y los grupos por órgano (gastroenteritis, hepatitis, tuberculosis) y la decisión de poner el **ictus** en Cardiovascular y no en Neurológico (cambia las cifras de ambos).
