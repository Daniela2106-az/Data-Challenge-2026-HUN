# A6 · Estimación de los tiempos de espera (7-nov-2026)

**Qué pide el instructivo (componente 3):** «modelos analíticos o predictivos que permitan estimar tiempos de atención». La pregunta concreta: **cuando un paciente espera cama, ¿cuánto le falta?**

## Resumen
1. **El estimador elegido es un modelo de tiempo restante** (supervivencia por hora). Para un paciente que espera cama da el rango de lo que le falta (percentiles 25, 50, 75 y 90) y la probabilidad de recibirla en las próximas 6, 12 y 24 horas, y se puede recalcular en cualquier momento de la espera. Solo usa datos que el hospital conoce en el momento. Se consulta con la función `estimar_tiempo_restante()`.
2. **Se probaron cinco enfoques en la misma prueba**, con meses que ningún modelo había visto (jul-2025 a 9-abr-2026): este modelo, un modelo de cuantiles al llegar, dos modelos de cola y una tabla de perfiles. El de tiempo restante gana o empata en todos los momentos y es el que mejor acierta los percentiles. La diferencia con los demás está medida con intervalos de confianza.
3. **Ningún método achica mucho el rango:** el mejor mejora un 6–7 % frente a darle el mismo rango a todos. La espera depende sobre todo de lo que la base no registra: el triage, el servicio, el tipo de cama y la hora de la orden de hospitalización.
4. **La gravedad haría la diferencia.** Con una aproximación a la gravedad al llegar (el grupo de diagnóstico), la mejora casi se duplica, de 6,6 % a 12,3 %. Registrar el triage en la base es la mejora de datos que más ayudaría a estimar la espera de cada paciente.
5. **Lo que más decide cuándo llega la cama es la hora del reloj.** Entre las 6 y las 12 h casi nadie recibe cama; las asignaciones se concentran entre las 15 y las 17 h y entre las 20 y las 23 h.

## Por qué un rango y no un número
Ya se sabía que el tiempo de un paciente no se puede predecir con lo que se conoce al llegar: esperar más de 24 h tiene AUC 0,60 y la estancia, R² cercano a 0 (`CLAUDE.md` 6b). Por eso el estimador da el **rango de pacientes parecidos**. Por ejemplo: «la mitad de los pacientes en su situación recibe cama en menos de X horas, y 1 de cada 4 tarda más de Y».

**Qué se mide:** la espera de cama va de la llegada a la asignación de cama, como confirmó el HUN (`CLAUDE.md` 4.7). Se usan las estancias únicas del periodo confiable, del 1-feb-2023 al 9-abr-2026 (22.819 estancias). En total, la mediana es 18,5 h, el p25 6,4 h, el p75 37,8 h y el p90 72,9 h, coherente con `HALLAZGOS.md` 4.2.

## El estimador: modelo de tiempo restante
Código: `src/estimador_tiempo_restante.py` (función de consulta) y `src/comparar_estimadores.py` (cómo se eligió).

**Cómo funciona.** Para cada hora de espera, el modelo estima la probabilidad de recibir cama en la hora siguiente. Usa:
- **Cuánto lleva esperando** el paciente.
- **La hora del reloj y el día de la semana.**
- **Las camas ocupadas en su zona:** adultos (15 años o más) o niños.
- **Edad, sexo y tipo de visita.**

Multiplicando esas probabilidades hora por hora se obtiene la probabilidad de seguir esperando, y de ahí los percentiles. El modelo usa árboles de gradiente (`HistGradientBoostingClassifier`), entrenados con una fila por paciente y por hora de espera. Para estimar hacia adelante, la ocupación se deja fija en su último valor conocido.

**Por qué no usa la cola.** Contar cuántos pacientes esperan cama a cada hora requiere saber quién terminará hospitalizado, algo que en el momento no se conoce del todo. Se probó con y sin la cola, y la cola no mejora nada: 6,5 % con cola frente a 6,6 % sin ella al llegar, con intervalos superpuestos en todos los momentos. Por eso el modelo final va sin ella.

**Cómo se consulta.** El modelo se entrena con todo el periodo confiable y se guarda fuera del proyecto, en `HUN_PROCESADOS/modelos/` (sale de datos clínicos). Si no existe, se entrena al primer uso.
```python
from estimador_tiempo_restante import estimar_tiempo_restante
estimar_tiempo_restante(edad=67, sexo="Mujer", tipo_visita="Urgencias", horas_esperando=10, ahora="2026-03-04 19:00")
```
La función devuelve los percentiles de lo que falta, la hora estimada en que la mitad de los pacientes parecidos ya tendría cama y la probabilidad de recibir cama en 6, 12 y 24 horas. La ocupación de la zona es opcional: si no se da, se usa la mediana de los últimos 90 días de datos confiables (85 camas de adultos y 17 de niños).

**Ejemplos** (miércoles 4-mar-2026, ocupación típica):

| Paciente | Faltan: p25 / mediana / p75 / p90 | Prob. de cama en 6 h / 12 h / 24 h |
|---|---|---|
| Mujer de 67 años, urgencias, recién llegada a las 9:00 | 12,4 / 33,0 / 60,1 / 87,8 h | 14 % / 24 % / 39 % |
| La misma, 10 h después (19:00) | 18,2 / 27,5 / 52,2 / 97,3 h | 18 % / 23 % / 38 % |
| Hombre de 35 años, urgencias, lleva 2 h (16:00) | 8,4 / 28,2 / 52,7 / 79,9 h | 18 % / 31 % / 41 % |
| Niña de 8 años, urgencias, recién llegada a las 22:00 | 4,5 / 14,0 / 23,4 / 43,5 h | 32 % / 46 % / 77 % |

**Lo que aprendió el modelo: la hora del reloj manda.** Para un paciente que sigue esperando, la probabilidad de recibir cama en la hora siguiente es:
- ~1 % entre las 6 y las 12 h;
- 5–8 % entre las 15 y las 17 h;
- 1 % a las 18 h;
- 8–10 % entre las 20 y las 22 h.

Los datos crudos muestran lo mismo: el 24 % de las camas se asigna entre las 15 y las 17 h y el 37 % entre las 20 y las 23 h. Es coherente con las altas tardías (`CLAUDE.md` 6b). La subida de la noche no se había descrito antes; podría ser la hora en que se registra la asignación más que la del traslado.

## Qué tan bien funciona
**La prueba.** Los modelos se entrenaron con llegadas de feb-2023 a jun-2025 y se probaron con las 5.430 estancias de jul-2025 a 9-abr-2026. Se miden dos cosas:
- **La mejora frente al rango general**, es decir, frente a darle a todos los mismos percentiles. Se mide con la pérdida de cuantiles, el error estándar para percentiles.
- **Si los percentiles aciertan:** lo ideal es que el 25 / 50 / 75 / 90 % de los casos nuevos quede por debajo de cada uno.

Los intervalos del 95 % salen de un bootstrap por semanas (1.000 repeticiones): se remuestrean semanas completas porque los pacientes de una misma semana se parecen entre sí.

**Al llegar:**

| Método | Mejora (IC 95 %) | Error de la mediana | Debajo de p25 / p50 / p75 / p90 |
|---|---|---|---|
| **Tiempo restante (elegido)** | **6,6 % (5,5 a 7,5)** | 24,0 h | 26,8 / 52,9 / 76,0 / 89,2 % |
| Cuantiles al llegar (M2) | 6,3 % (5,5 a 7,2) | 24,0 h | 27,0 / 52,1 / 73,7 / 86,8 % |
| Tabla de perfiles | 5,8 % (4,9 a 6,7) | 24,2 h | 27,9 / 52,0 / 73,1 / 87,0 % |
| Cola en orden aleatorio (M3a) | −0,3 % (−1,5 a 0,8) | 25,7 h | 31,3 / 53,9 / 74,8 / 87,4 % |
| Cola en orden de llegada (M3b) | −17,9 % (−19,6 a −16,4) | 28,0 h | 59,1 / 65,7 / 70,7 / 75,6 % |

**Durante la espera** (lo que le falta a quien sigue sin cama), mejora frente al rango general en las mismas condiciones:

| Horas esperando | Tiempo restante | Tabla de perfiles | Cola, orden aleatorio | Cola, orden de llegada |
|---|---|---|---|---|
| 6 h | **6,9 % (5,8 a 8,0)** | 5,5 % (4,6 a 6,3) | 0,4 % | −16,9 % |
| 12 h | **6,1 % (4,8 a 7,3)** | 3,7 % (2,8 a 4,6) | 0,5 % | −15,6 % |
| 24 h | **4,9 % (3,4 a 6,3)** | 2,2 % (1,3 a 2,9) | 1,4 % | −14,2 % |
| 48 h | **1,8 % (0,4 a 3,1)** | −0,9 % (−1,8 a 0,0) | −2,4 % | −18,3 % |

**Cómo leerlo:**
- **Contra la tabla de perfiles, la ventaja es real en todos los momentos.** El intervalo de la diferencia nunca incluye el 0: va de +0,2 a +1,4 puntos al llegar y de +1,6 a +4,0 a las 24 h.
- **Al llegar, el de tiempo restante y el de cuantiles empatan** (diferencia de −0,2 a +0,7 puntos). Se elige el primero porque acierta mejor los percentiles altos (89 % frente a 87 % debajo del p90) y porque es el único que sirve durante la espera.
- **El p90 queda algo corto en todos los métodos** (87–89 % en vez de 90 %), porque los peores casos siguen empeorando (`HALLAZGOS.md` 4.3). Conviene leerlo como un piso.
- **El modelo de cola no funciona.** En orden de llegada falla mucho, lo que confirma que el orden de llegada casi no predice el orden de cama (`CLAUDE.md` 6b). En orden aleatorio no mejora al rango general, porque la cola casi no cambia la espera (`docs/capacidad_efectiva.md`).

**Agosto y septiembre de 2025.** Según el equipo, el HUN tuvo sobredemanda porque los hospitales cercanos fueron intervenidos por el Estado y quedó como la única opción de la zona. En los datos se ve poco: un 6–7 % más de llegadas que en los mismos meses de 2024, con ingresos a cama y espera mediana normales. Evaluados aparte, el modelo de tiempo restante mejora 6,3 % en esos meses y 6,7 % en el resto, con percentiles igual de bien calibrados. El resultado se sostiene.

## Cuánto ayudaría conocer la gravedad (triage)
Código: `src/triage_aproximado.py`.

En urgencias, la prioridad se define con el triage: I (inmediata, riesgo vital), II (muy alta), III (media), IV (baja) y V (muy baja). **La base no trae el nivel de triage.** No está en ninguna de las 8 tablas, la etapa 9203 solo trae la hora, y entre los nombres de los diagnósticos no aparece ningún triage ni prioridad. Se probaron dos aproximaciones dentro del modelo elegido, y ninguna es el triage:
- **Laboratorios de las primeras 6 h:** se conocen a las 6 h. El 48 % de las estancias tiene alguno.
- **Grupo de diagnóstico:** los pacientes cardiovasculares y neurológicos reciben cama mucho antes (`HALLAZGOS.md` 4.5b), lo que sugiere que el hospital ya prioriza por gravedad. Pero el 88 % de los diagnósticos se registra tarde y el 35 % de las estancias no tiene ninguno. Por eso se usa como **escenario**: «¿cuánto mejoraría si el HUN registrara la gravedad al llegar?».

| Horas esperando | Sin gravedad | + laboratorios de 6 h | + grupo de diagnóstico (escenario) |
|---|---|---|---|
| 0 h (al llegar) | 6,6 % | 7,2 % (no válido: se conocen a las 6 h) | **12,3 %** |
| 6 h | 6,9 % | 7,2 % | **10,8 %** |
| 12 h | 6,1 % | 6,3 % | 9,0 % |
| 24 h | 4,9 % | 4,7 % | 6,5 % |
| 48 h | 1,8 % | 2,1 % | 2,5 % |

**Qué significa:**
1. **Los laboratorios tempranos casi no ayudan** (−0,2 a +0,6 puntos).
2. **Una medida de gravedad al llegar casi duplicaría la mejora**, y eso que el diagnóstico es una aproximación tosca y tardía; un triage real debería servir más. Es un argumento concreto para la recomendación R1 (`docs/recomendaciones.md`): **registrar el nivel de triage en la base.**
3. **Pasados los 2 días, la gravedad casi no cambia la estimación.** Las esperas muy largas dependen de otras cosas.

## Alternativas probadas
**1. Tabla de perfiles** (`src/estimador_tiempos.py`). El rango de cada combinación de bloque de 3 horas, grupo de edad, tipo de visita y sexo (336 perfiles), pasando al perfil más general cuando hay menos de 30 casos. Es la versión más simple de explicar y la única que cubre las otras medidas de tiempo:
- **Probabilidad de hospitalizarse:** 9,6 % en total; AUC 0,62 en la prueba y bien calibrada (estimó 9,85 %, fue 10,1 %).
- **Estancia en cama:** mediana 69,5 h. El perfil mejora el rango solo un 2 %.
- **Urgencias sin hospitalizar:** Kaplan-Meier, mediana 11,2 h y p90 80,6 h, coherente con `docs/supervivencia_urgencias.md`.

Para la espera de cama queda por debajo del modelo de tiempo restante. Consulta: `estimar(hora, grupo_edad, tipo_visita, sexo)`.

**2. La espera en dos series: sin cama y demora del servicio** (`src/espera_dos_series.py`). Cada hora se cuentan las camas ocupadas por zona frente a las capacidades del HUN (88 de adultos y 18 de niños, `CLAUDE.md` 4.7). La espera de cada paciente se reparte en horas con la zona llena (**sin cama**) y horas con camas libres en el conteo (**demora del servicio**).

| Año | % de horas con adultos llenos | Espera media | Sin cama | Demora del servicio |
|---|---|---|---|---|
| 2023 | 1,6 % | 28,0 h | 2,3 h (8 %) | 25,7 h |
| 2024 | 37,5 % | 29,2 h | 10,9 h (37 %) | 18,3 h |
| 2025 | 58,3 % | 33,4 h | 18,8 h (56 %) | 14,6 h |

- **El cambio es de composición:** en 2025 más de la mitad de la espera ocurrió con la zona de adultos llena, coherente con la ocupación de adultos al 101 % (`docs/ocupacion_por_zona.md`).
- **Es frágil:** con capacidades 10 % mayores, la parte sin cama queda en 5–10 % todos los años. Además, la espera total casi no responde a la ocupación (`docs/capacidad_efectiva.md`).
- **La hora de llegada mueve la demora del servicio**, no la parte sin cama: 13–15 h para quien llega de noche y 19–22 h para quien llega de día.
- **No mejora el pronóstico:** pronosticar las dos series da el mismo error que una sola, unas 4,5 h por semana. Queda como una lectura descriptiva, no como estimador.

**3. Cuantiles al llegar (M2).** Árboles de gradiente por percentil, con lo que se sabe al llegar más el estado del hospital. Empata al llegar, pero no sirve durante la espera.

**4. Modelos de cola (M3a y M3b).** Descartados por los resultados de arriba.

## Límites (van junto al estimador)
- **Rango de pacientes parecidos, no una promesa para una persona.** Sirve para planear y para comunicar expectativas.
- **La espera termina en la asignación administrativa.** Mezcla la atención clínica en urgencias con la espera de cama, y no se pueden separar.
- **Cama o silla:** según el equipo, a muchos pacientes se les atiende en sillas aunque necesiten una cama, y no se sabe si eso se registra como estar en cama. La base no tiene columna de cama, silla, piso ni servicio (`CLAUDE.md` 4.8). Si se registra, la espera real hasta una cama sería más larga, la falta de camas mayor de lo que muestran los datos, y la ocupación de hospitalización incluiría puestos que no son camas (lo que explicaría que pase de las 106 camas el 42 % de las horas de 2025).
- **Edad y sexo de las estancias duplicadas:** esta corrida no tuvo los archivos `P02` y `P03` del lote 4 de `src/auditoria_bd.py`. En las estancias registradas en dos personas se conservó el registro con más información, que es el de la persona real en ~81–85 % de los casos (`CLAUDE.md` 4.10).
- **La ocupación hacia adelante se deja fija.** Si cambia mucho en las horas siguientes, la estimación no lo sabe.
- **Urgencias sin hospitalizar** (tabla de perfiles): el rango es solo de los episodios con algún tiempo registrado; la mitad no tiene ninguno.
- **Asociación, no causa.**

## Cómo reproducirlo
Los datos viven fuera del proyecto. Se indican con dos variables:
```bash
export HUN_PROCESADOS="D:/Descargas D/Datos/procesados" HUN_TABLAS="D:/Descargas D/Datos/procesados/tablas"
```
1. **Tabla de episodios:** `src/analisis_etapas.py` y `src/preparar_variables.py`, con los CSV de la base en `datos/crudos/`. Copiarlos ahí solo mientras corren y mover luego `datos/procesados/` a la carpeta externa.
2. **Tabla de perfiles:** `python3 src/estimador_tiempos.py`.
3. **Dos series:** `python3 src/espera_dos_series.py`.
4. **Comparación de métodos, con intervalos:** `python3 src/comparar_estimadores.py` (~35 s).
5. **Escenario de gravedad:** `python3 src/triage_aproximado.py` (~50 s).
6. **Consultas:** `python3 src/estimador_tiempo_restante.py 67 Mujer Urgencias 10 "2026-03-04 19:00"`. Entrena y guarda el modelo la primera vez.

Las tablas quedan en `HUN_TABLAS` y los gráficos agregados en `resultados/graficos/` (`comparacion_estimadores.png`, `espera_dos_series.png`, `estimador_tiempos.png`).

## Pendientes
- **Correcciones de datos:** pedir a Daniela `P02_persona_de_los_diagnosticos.csv` y `P03_persona_de_los_laboratorios.csv` para corregir la edad y el sexo, y volver a correr.
- **Gravedad desde los procedimientos:** con `Q01_procedimientos_por_estancia.csv` y `Q03_nombres_de_conceptos.csv` (lote 5, ya extraídos por Daniela) se puede armar una medida de gravedad (UCI, vía aérea, transfusión, reanimación) y buscar si algún concepto se llama «triage». Los procedimientos no tienen fecha, así que serviría como escenario, no al llegar.
- **Dashboard:** la estructura (`docs/estructura_dashboard.md`) no tiene página para A6. Como el dashboard está en Dash (Python), la página puede llamar directamente a `estimar_tiempo_restante()`. Falta decidir con Daniela dónde va y si el modelo guardado puede publicarse con el dashboard: contiene los cortes de los árboles, no filas de pacientes, pero sale de datos clínicos.
