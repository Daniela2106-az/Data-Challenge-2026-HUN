# Perfiles de pacientes (tarea A1, 3-nov-2026)

**Qué pide el instructivo:** «cómo se comportan distintos perfiles de pacientes». Un **perfil** es una combinación de grupo de edad × sexo × tipo de visita (42 perfiles).
Código: `src/perfiles_pacientes.py`. Tablas en `resultados/tablas/perfiles_*.csv`; gráfico `resultados/graficos/perfiles_pacientes.png`.

## Cómo se midió
- **Periodo confiable:** llegadas del 1-feb-2023 al 9-abr-2026 (el registro de etapas se degrada desde el 10-abr; `CLAUDE.md` 4.9). 309.378 episodios, 250.910 con atención y 23.245 estancias únicas.
- **«Con atención»:** el episodio no es solo la etapa de admisión (ER). Los porcentajes de hospitalización se calculan sobre los episodios con atención.
- **Espera y estancia en cama:** una fila por estancia (registro conservado, `estancia_id`). La espera es la de la estancia. Referencia total: se hospitaliza el 9,3 %, espera mediana 18,5 h, estancia mediana 69,5 h, reingreso a 72 h 7,5 %.
- **Edad y sexo son los de la persona real de la estancia** (ver «Una corrección importante» más abajo).
- **Cada diferencia frente al total se clasifica:** *grande* (el intervalo de confianza del 95 % no incluye el total y la diferencia relativa es de 20 % o más), *pequeña* (fuera del intervalo pero menos de 20 %) o *ruido*. Las celdas con menos de 100 episodios con atención, o de 30 estancias para esperas y estancias, no se interpretan (3 de 42 perfiles tienen menos de 30 estancias).

## Resultados por una dimensión

**Por edad**

| Grupo | Episodios | Llegan por día | Reciben atención | Se hospitalizan | Espera de cama (mediana, h) | Estancia (mediana, h) | Reingreso en 72 h |
|---|---|---|---|---|---|---|---|
| 0-4 | 25,716 | 22,1 | 91,1 % | 10,1 % | 7,8 | 67 | 6,2 % |
| 5-14 | 36,252 | 31,1 | 89,3 % | 7,1 % | 12,3 | 52 | 6,0 % |
| 15-29 | 92,182 | 79,2 | 76,1 % | 7,9 % | 17,2 | 58 | 9,2 % |
| 30-44 | 65,338 | 56,1 | 74,7 % | 7,6 % | 24,4 | 68 | 7,8 % |
| 45-59 | 41,364 | 35,5 | 79,8 % | 9,3 % | 27,1 | 77 | 6,8 % |
| 60-74 | 30,825 | 26,5 | 87,5 % | 12,9 % | 25,0 | 92 | 6,7 % |
| 75+ | 17,701 | 15,2 | 91,5 % | 17,2 % | 27,1 | 103 | 6,4 % |

**Por sexo**

| Grupo | Episodios | Llegan por día | Reciben atención | Se hospitalizan | Espera de cama (mediana, h) | Estancia (mediana, h) | Reingreso en 72 h |
|---|---|---|---|---|---|---|---|
| Hombre | 136,470 | 117,2 | 78,5 % | 8,8 % | 14,3 | 69 | 7,4 % |
| Mujer | 172,908 | 148,6 | 83,1 % | 9,6 % | 22,3 | 70 | 7,5 % |

**Por tipo de visita**

| Grupo | Episodios | Llegan por día | Reciben atención | Se hospitalizan | Espera de cama (mediana, h) | Estancia (mediana, h) | Reingreso en 72 h |
|---|---|---|---|---|---|---|---|
| Ambulatorio | 7,146 | 6,1 | 98,2 % | 15,3 % | 11,3 | 44 | 1,9 % |
| Treatment urgency | 8,772 | 7,5 | 100,0 % | 24,6 % | 9,8 | 112 | 9,8 % |
| Urgencias | 293,460 | 252,1 | 80,1 % | 8,5 % | 20,8 | 69 | 7,5 % |

## Lo que muestran

1. **Los adultos mayores se hospitalizan más y se quedan más:** de 60 años en adelante se hospitaliza el 13–17 % (contra 7–8 % de los 5 a los 44) y la estancia mediana es de 92–103 h (contra 52–68 h). Las diferencias son grandes.
2. **Los niños esperan mucho menos cama:** 7,8 h de mediana en los de 0 a 4 años y 12,3 h de 5 a 14, contra 24–27 h de los 30 años en adelante. Es la diferencia más clara de espera y se parece a lo esperable: los servicios pediátricos tienen pocas camas, pero también pocos pacientes.
3. **Las mujeres esperan más cama que los hombres:** mediana de 22,3 h contra 14,3 h, y el hueco aparece en cada grupo de edad desde los 5 años (por ejemplo, 75 años o más: 30,1 h contra 16,0 h). **No es un efecto de mezcla:** con edad, tipo de visita, franja horaria y año en el modelo, las mujeres esperan un 27 % más (IC 23 a 31 %); dentro de cada grupo de diagnóstico, un 36 % más (IC 31 a 41 %). Se mantuvo igual después de corregir la persona de cada estancia, así que no es un error de asignación.
   Es una **asociación sin explicación** en los datos. Una hipótesis (sin comprobar, no hay datos de habitaciones): las camas de hospitalización suelen agruparse por sexo, y la oferta para mujeres sería más ajustada. También puede deberse a otro servicio. Hay que declararlo como hallazgo abierto.
4. **Se hospitalizan más y se quedan más los de visitas «Treatment urgency»:** el 24,6 % se hospitaliza (contra 8,5 % de urgencias normales) y la estancia mediana es de 112 h (contra 69 h), con una espera más corta (9,8 h). No pasan por la etapa de admisión y su volumen crece (ver `CLAUDE.md` 4.8). Reciben atención el 100 % de los casos.
5. **Los reingresos a 72 h** van de 2 % en las visitas ambulatorias a 10 % en «Treatment urgency»; por edad, de 6 % (niños y mayores) a 9 % (15 a 29 años). **Sin validar** (`CLAUDE.md` C4): se reportan con esa advertencia.
6. **Quién llega más:** las mujeres de 15 a 29 años por urgencias (45 por día) y las de 30 a 44 (31 por día) son los perfiles más numerosos. Los de mayor espera son las mujeres de 45 a 59 (32,7 h), de 60 a 74 (30,3 h) y de 75 o más (30,2 h) que llegan por urgencias.

**Trayectorias:** el 84,7 % de los episodios con atención termina en urgencias (`TU`), el 12,1 % pasa a hospitalización (`TU > HOSP`) y el 2,2 % vuelve a admisión y atención (`TU > ER > TU`). Las demás combinaciones suman menos del 1 %.

## Por grupo de diagnóstico (solo entre quienes lo tienen)

Cobertura: el diagnóstico existe en el 68 % de las estancias hospitalizadas hasta abril de 2026 (después del 30-abr los códigos desaparecen). El resto no se clasifica y no se puede leer como «sin enfermedad».

| Diagnóstico | Estancias | Espera mediana (h) | Estancia mediana (h) | Edad mediana | % mujeres |
|---|---|---|---|---|---|
| Musculoesqueletico y dolor | 396 | 41,0 | 116 | 47 | 65 % |
| Renal y urinario | 1533 | 34,8 | 70 | 42 | 65 % |
| Cancer y tumores | 244 | 32,2 | 115 | 62 | 67 % |
| Digestivo | 2291 | 29,6 | 89 | 45 | 69 % |
| Trauma y lesiones | 1573 | 23,9 | 52 | 30 | 47 % |
| Sangre e inmunologia | 215 | 20,0 | 72 | 36 | 69 % |
| … | | | | | |
| Neurologico | 700 | 9,5 | 93 | 55 | 56 % |
| Respiratorio | 1277 | 8,7 | 72 | 7 | 46 % |
| Dolor y sintomas generales | 453 | 7,5 | 54 | 17 | 51 % |
| Recien nacido | 34 | 0,9 | 131 | 0 | 41 % |

Hay diagnósticos con espera larga (musculoesquelético, renal, cáncer, digestivo) y con espera corta (cardiovascular, neurológico, respiratorio, dolor): el patrón del análisis A3 (`docs/diagnosticos_y_tiempos.md`), que se mantiene.

## Una corrección importante: las gemelas son dos personas distintas

Al armar estos perfiles apareció que **los dos registros de una misma estancia gemela son dos personas sin relación**: coinciden en el sexo el 51,7 % de las veces (el azar da 51 %) y en la edad, dentro de 2 años, el 6,3 % (diferencia mediana de 25 años). Una es la real; la otra es un duplicado con los datos de otra persona. La regla anterior (conservar el registro con más información) conservaba la persona real solo en ~81 % de los casos, y la edad y el sexo de esas estancias eran de la persona equivocada.
Se corrigió con los números de persona de las filas de diagnósticos y laboratorios (en el 93 % de las estancias coinciden; los procedimientos no sirven, el 88 % cuelga del otro registro). Ahora **el registro conservado es el de la persona real en el 99,7 % de las estancias gemelas con persona identificada** (97,6 % de las gemelas). Cambió el modelo de factores (el R² de la espera sube de 14,8 a 15,8 % y «edad y sexo» de 3,7 a 4,1 puntos). Detalle y regla en `CLAUDE.md` sección 4.10.

## Límites
- Asociación, no causa. Sin servicio, sede ni cama no se puede explicar por qué esperan más ciertos perfiles.
- La duración de urgencias de quienes no se hospitalizan solo existe en ~38 % de los episodios y está sesgada: no se usa para perfiles.
- El tipo de visita no es confiable para saber por dónde pasó el paciente (`CLAUDE.md` sección 3): se usa solo como etiqueta de origen.
- Reingreso sin validar. Diagnóstico con cobertura parcial y registrado tarde.
- La edad y el sexo de las estancias no gemelas y de las gemelas sin diagnóstico ni laboratorio no se pudieron verificar (el 99 % de las no gemelas es consistente por construcción).

## Para A2b y A7
`resultados/tablas/perfiles_por_estancia.csv` (una fila por estancia con su perfil, `estancia_id`, espera y estancia; no se sube a git) permite cruzar el perfil con la «estancia disparada» de A2b.
