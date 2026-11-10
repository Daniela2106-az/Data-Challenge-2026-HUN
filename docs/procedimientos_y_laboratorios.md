# Procedimientos y laboratorios: qué va con qué (10-nov-2026)

Script: `src/procedimientos_y_laboratorios.py`. Tablas (fuera de git): `proc_lab_estancias.csv`, `proc_lab_orden_vs_resultado.csv`, `proc_lab_no_laboratorio_asociacion.csv`.
**Pregunta de Daniela:** los procedimientos no tienen hora, pero los laboratorios sí; ¿qué procedimientos se asocian con qué laboratorios, y puede haber procedimiento sin laboratorio o laboratorio sin procedimiento?

## Hallazgo de partida
**Muchos procedimientos son las mismas órdenes que luego aparecen como laboratorio.** Hemograma, creatinina, urea, glucosa, tiempo de protrombina, troponina, cultivos... comparten el mismo código de concepto en `procedure_occurrence` y en `measurement`. Hay 156 procedimientos distintos en las visitas con hospitalización y 52 de ellos son también conceptos de laboratorio. Por eso se puede cruzar **orden frente a resultado** por concepto.

## Cómo se hizo
- Estancias con **estancia en cama de 48 h o menos** y alta registrada (8.162 de 22.801): la ventana de laboratorios (espera + primeras 48 h de cama, que es lo que se extrajo con hora) cubre **toda** su visita, así que no se pierde nada por truncamiento.
- Procedimientos: unión de las visitas de la estancia (los de una estancia gemela cuelgan sobre todo del otro registro; no se filtra por persona). Laboratorios: solo los de la persona real.

## 1. ¿Procedimiento sin laboratorio, o laboratorio sin procedimiento? (estancias cortas, n = 8.162)
| Estancias | % |
|---|---|
| Con algún procedimiento | 86,2 % |
| Con alguna toma de laboratorio (traducida o no) | 77,1 % |
| Con laboratorio **traducido** (concepto ≠ 0) | 29,1 % |
| **Procedimiento SIN ninguna toma de laboratorio** | **20,6 %** |
| **Toma de laboratorio SIN ningún procedimiento** | **11,5 %** |
| Orden de examen SIN ningún laboratorio traducido | 49,1 % |
| Laboratorio traducido SIN ninguna orden de examen | 0,3 % |
| Ni procedimiento ni laboratorio | 2,4 % |

**Sí puede haber las dos cosas.** Pero hay una asimetría clave: casi todo resultado traducido tiene su orden (99,7 %), mientras que la mitad de las estancias con una orden de examen no tiene ese examen traducido como laboratorio.

## 2. La misma prueba: orden frente a resultado
Por concepto, de cada 100 estancias con la **orden**, tienen el **resultado traducido** en la base: hemograma 39, creatinina 36, urea 36, tiempo de protrombina 37, PCR 34, sodio 36, glucosa 34, gases arteriales 38, troponina 33, cultivo de sangre aerobio 19, TSH 11, grupo sanguíneo 2. **En conjunto, 32 de cada 100 órdenes de examen tienen su resultado traducido.** En sentido contrario, el 99 % de los resultados traducidos tiene su orden.
Esto explica por qué el 58 % de las filas de laboratorio dentro de la espera tiene concepto 0 (sin traducir): **el resultado existe (hay una toma con hora) pero no se sabe de qué examen**, y su orden figura en los procedimientos.

## 3. Procedimientos que no son exámenes: qué laboratorios los acompañan
Aumento de la probabilidad de tener cada laboratorio si la estancia tiene el procedimiento, frente a las que no (n ≥ 100 estancias):
- **Radiografía de tórax** → troponina ×23 y péptido natriurético (BNP) ×16; **electrocardiograma continuo** → troponina ×12. Son los estudios del dolor de pecho y la falla cardíaca.
- **Tinción de Gram** → antibiograma ×48, uroanálisis ×14, hemocultivo aerobio ×9,5: el paquete de infecciones.
- **Monitoreo fetal intraparto** → serología de toxoplasma ×17; **perfil biofísico fetal** → toxoplasma ×11; **cesárea** → toxoplasma ×6 y VIH ×5: el control prenatal.
- **Consulta de urgencias** (nota) → uroanálisis ×11 y urea ×7; **«otra consulta»** → BNP ×42 y troponina ×23.
- **TAC de cabeza** → calcio iónico ×6 y colesterol ×4 (pocos datos).

## Lectura y uso
- **Para ubicar un procedimiento en una etapa TU** hay que hacerlo de forma **indirecta**: si una estancia tiene, por ejemplo, radiografía de tórax y se tomó troponina en la segunda etapa, es probable (no seguro) que la radiografía haya caído en esa etapa. Es una probabilidad, no una asignación.
- **Los laboratorios sin traducir (58 %) son los que más información esconden**: sus órdenes están en los procedimientos, pero sin hora no se cruzan una por una.
- Para saber qué procedimientos se repiten en estancias largas, ver `docs/estancias_disparadas.md` (acceso venoso prolongado, nutrición, transfusión, curaciones).

## 4. ¿Se pueden ubicar los procedimientos en el tiempo con el orden de sus identificadores? **No** (prueba del 10-nov)
**Idea:** que el orden de `procedure_occurrence_id` siga el orden en que se registraron, para ordenar los procedimientos entre sí y, con las órdenes de laboratorio como ancla (misma prueba, con hora de toma), ubicarlos entre dos anclas, o sea, en una etapa TU aproximada.
**Prueba** (`src/prueba_ids_procedimientos.py`, con `sql/ids_procedimientos.sql`: 775.779 filas de procedimientos de 48.460 visitas y 434.135 filas de laboratorio de 31.788 visitas):

| Comprobación | Resultado |
|---|---|
| Laboratorios (donde la hora sí se conoce): correlación entre `measurement_id` y la hora de toma, por visita | Spearman **mediana 0,12**; solo el 3,5 % de las visitas pasa de 0,8 |
| Lo mismo solo en visitas cuyos ids están en un bloque estrecho (todas las visitas: rango mediano de 75 ids) | Igual: mediana 0,12 |
| Procedimientos: id de la orden frente a la hora de toma del mismo examen (124.246 anclas en 14.387 visitas) | Spearman **mediana 0,14**; el 6,0 % pasa de 0,8 y el 22,5 % de 0,5 |
| Procedimientos: ¿cargas mezcladas? | El 50,6 % de los (visita, procedimiento) tiene ids que abarcan más de 1.000.000 (varias cargas) |
| Ids de laboratorio por mes | Suben en general con la fecha (13,8 M en feb-2023 a ~24 M en 2025), con altibajos |

**Conclusión:** los identificadores vienen en bloques por visita y, en general, crecen con la fecha de la visita, pero **dentro de una visita su orden no sigue la hora** (ni siquiera en laboratorios, donde se puede verificar). Por eso **no sirven para ubicar un procedimiento en una etapa TU**. Queda cerrado el camino: la única relación entre procedimientos y etapas es la indirecta por asociación con laboratorios (sección 3).

## Límites
- Solo estancias cortas (≤ 48 h en cama): las largas tienen laboratorios después de las 48 h que no se extrajeron con hora.
- La orden y el resultado se cruzan por la presencia en la estancia, no por la hora (la orden no tiene hora).
- Una orden sin resultado traducido puede tener resultado con concepto 0, o no tener resultado registrado: la base no lo distingue.
- Son asociaciones, no causas.
