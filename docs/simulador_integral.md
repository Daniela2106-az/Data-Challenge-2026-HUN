# Simulador integral del hospital (Fase 1, 14-nov-2026)

**Qué es:** un solo motor de agentes que sigue a cada paciente sintético por todo su recorrido — llega al
hospital, espera cama, la ocupa y sale de alta — y emite **tres vistas sincronizadas del mismo paciente**:
la demanda (llegadas por día), la cola de espera de cama (cuántos esperan a la vez, con perfiles) y la
ocupación de camas con sus altas diarias. Antes esas vistas vivían en tres herramientas separadas
(/pronostico, /paciente y /camas del dashboard); el simulador las une **sobre un motor único**, sin encadenar
los tres modelos en serie.

Código: `src/simulador_integral.py` (motor) y `dashboard/pages/simulador.py` (página `/simulador`).
Tablas: `resultados/tablas/simint_*.csv`; gráfico: `resultados/graficos/simint_resultados.png`.
Es la **Fase 1** del plan de Samuel (simulador → alertas operativas → motor de recomendaciones).

## Evolución del 16-nov-2026 (seis etapas sobre la base del 14/15-nov)

Construido en orden, cada etapa usable por sí sola y sin romper la puerta de validación (el backtest se
re-corrió después de cada cambio que tocó el motor; sigue CUMPLIENDO):

1. **Composición por perfil + "Radiografía del día"** (`con_composicion=True`): el motor acumula, sin consumir
   números aleatorios (regresión de semilla intacta, verificado), cuántos pacientes de cada uno de los 21
   perfiles (edad × ruta) hay cada día en 5 etapas (llegan, esperando, entran a cama, en cama, salen de alta).
   La página muestra un panel de pictogramas (1 figura = N pacientes según el tamaño del grupo) con los 3
   perfiles dominantes comparados contra lo típico del horizonte, actualizado al pasar el cursor por el gráfico.
2. **Cinta de reproducción**: botones ▶/⏸ y velocidad (1 día o 1 semana por tick, puro `dcc.Interval` +
   clientside), que mueve un velo translúcido sobre el "futuro" de los 3 paneles (vía `Plotly.relayout`, sin
   redibujar trazas) y sincroniza la radiografía del día con el cursor.
3. **Tablero de camas**: grid de 106 celdas (88 adultos + 18 niños) que se llena según la mediana simulada del
   día del cursor; una fila roja adicional crece cuando el censo supera la capacidad — la sobreocupación se ve,
   no se lee en una nota.
4. **Alertas durante la reproducción**: se precomputa `prob_sat_48h` (fracción de repeticiones que saturan 106
   camas dos días después de cada día, costo cero al simular); si cruza 60 % mientras se reproduce, la cinta se
   pausa sola con un banner de alerta — primer brote de la Fase 2 (alertas operativas) montado sobre el motor.
5. **Palancas de hallazgos + preset + intervenir**: cuatro controles nuevos, todos neutros por defecto
   (verificado: con 0/None el motor es bit-idéntico al de antes):
   - **Recortar estancias largas (R7)**: reduce un % SOLO a las estancias sorteadas de más de 14 días (gestión
     de casos, no un recorte parejo). 15 % libera ~4,4 camas en la prueba (ley de Little/R7: 3-6 esperadas).
   - **Adelantar altas a la mañana (escenario A)**: inyecta el efecto YA MEDIDO en `simulacion_altas.py`
     (0,1 % de espera menos por punto de adelanto) como reducción de la espera sorteada — declarado como
     estimación inyectada, no mecánica interna (las esperas del motor se sortean, no se derivan de la
     disponibilidad de camas). 30 % de adelanto baja la cola ~3 % sin casi tocar la ocupación (coherente con
     "suaviza el pico, no baja el nivel").
   - **Mezcla de estrés** (`mezcla_edad`/`mezcla_ruta` sobre las LLEGADAS, mismo espíritu que el escenario D de
     `/camas`): sustituye los marginales de edad/ruta de quienes llegan; P(cama\|perfil) no cambia.
   - **Capacidad hipotética**: un slider que mueve la franja de 106 y el % de días saturados leyendo
     `sat_por_capacidad` (precomputado para 96-130 camas) sin volver a simular — mismo patrón que
     `curva_capacidad` de A5.
   - **Preset "Operación óptima"** (R7 15 % + adelanto 30 %, sin tocar la estancia uniforme para no contar dos
     veces el recorte) y **comparación "hoy"**: superpone en los 3 paneles una corrida neutra con la misma
     semilla (líneas punteadas grises). El botón **Intervenir** del banner de alerta aplica el mismo preset.
6. **Vista horaria** (plazo "3 días, hora a hora"): un motor simplificado (`simular_horario`, sin modelos A9,
   casos, R7, adelanto ni mezcla — solo estancia y espera) que NO redondea a días: calcula cama = llegada +
   espera y alta = cama + estancia en horas continuas, y deja la cola sin promediar a día. Para que la hora de
   asignación de cada agente reproduzca el patrón real, se le quita a `trayectoria_para` el ruido de Silverman
   sobre la espera (parámetro `suavizar_espera=False`, nuevo y opcional — el motor diario no lo usa y queda
   bit-idéntico): sin el ruido, hora_llegada + espera de un paciente real da exactamente la hora en que ESE
   paciente recibió su cama. Validado contra el patrón real (`ingreso_cama.dt.hour`): la franja 20-23 h salió
   **29,0 % simulado contra 29,8 % real**, con el pico exacto en la misma hora (21 h) en ambos — las dos olas de
   asignación de camas (`docs/estimador_tiempos.md` 1.2) emergen solas del motor, sin programarlas.

Límite nuevo declarado: la vista horaria es un motor deliberadamente más simple (sin las palancas de
hallazgos ni A9/casos) pensado para la experiencia en vivo de corto plazo, no para análisis de escenarios.

## Decisiones de diseño (de la conversación del 14-nov; cada descarte tiene su porqué)

| Qué se consideró | Resultado | Por qué |
|---|---|---|
| Encadenar pronóstico → estimador de espera → Monte Carlo en serie | **No entra** | Cada módulo se construyó para una población distinta: el estimador A6 solo vio pacientes que recibieron cama (no sabe decir "este no necesita cama") y el ~87 % de las llegadas atendidas se va de alta desde urgencias. Encadenarlos rompía los supuestos de cada uno. |
| Llenar una cuota diaria de camas con un ranking de probabilidad | **No entra** | Reinventa una fila de prioridad que los datos rechazan: el orden de llegada casi no predice el orden de cama (53 % de pares consecutivos en orden, azar 50 %, `docs/CONTEXTO_TECNICO.md` 6b) y la espera es individual, no del momento (el día de llegada explica el 0,1 % de la espera, `docs/estimador_tiempos.md` 1.1). |
| "Pacientes sin cama" = llegadas − ingresos a cama | **No entra** | Esa resta no es la cola: es sobre todo gente que nunca iba a necesitar cama. La cola se construye agente por agente (de su llegada a su cama) y se valida contra la cola real. |
| Usar el estimador A6 como predictor dentro del motor | **No entra** | Asignar a cada agente la predicción puntual comprime la varianza y daña las bandas. La espera se **sortea** de trayectorias reales; A6 sigue siendo la consulta para pacientes reales. |
| Ingresos a cama **emergentes** de los agentes, calibrados (κ) | **Entra** | Opción B de la conversación: los conteos emergen de llegadas × P(cama\|perfil) × espera sorteada; un factor global κ los calibra contra el pronóstico validado de ingresos. κ salió ≈ 1,00 (1,002 en el backtest, 0,994 en la proyección): la P(cama\|perfil) de `tabla_episodios` ya era consistente con el pronóstico — señal de coherencia interna, no un parche. |
| Trayectoria conjunta (hora de llegada, espera y estancia del MISMO paciente real) | **Entra** | Conserva la correlación real espera-estancia (+9 % de estancia por desviación de espera, `docs/factores_estancia.md`) y reproduce sola el patrón horario de asignación de camas, sin modelarlo aparte. |

## Cómo funciona (una repetición)

1. **Llegadas** diarias ~ Poisson(pronóstico de `llegadas` de `modelo_pronostico.py`).
2. Cada llegada recibe un **perfil** (grupo de edad × ruta) de la mezcla real de llegadas de 2025 (21 perfiles).
   **Desde el 16-nov el perfil puede completarse con el sexo** (para la vista de perfiles del dashboard):
   en llegadas, sorteado con la mezcla real por perfil (`sexo_llegada`, P(mujer) de 41 a 62 % según la celda,
   global 56 %); en hospitalizados, **el del mismo paciente histórico de la trayectoria** (4.º valor de
   `trayectoria_para`), para que la etiqueta sea coherente con la espera mostrada (las mujeres esperan más:
   mediana 21,8 h contra 14,3 h en el pool 2024-2025, hallazgo abierto de A1). El sexo **no entra en ningún
   cálculo del motor** (P(cama), espera y estancia ya lo promedian dentro de cada perfil): los resultados son
   bit-idénticos con o sin él. **Raza y etnia no se asignan**: en la base la raza está 95 % sin dato y la
   etnia es casi constante ("Hispanic or Latino", `docs/CONTEXTO_TECNICO.md` sección 3); si la vista las muestra, que diga
   "Sin dato en la base".
3. Cada llegada **se hospitaliza** con probabilidad κ × P(cama|perfil), donde P viene de `tabla_episodios`
   (hospitalizado y `estancia_unica` entre TODOS los episodios de 2025: global 7,6 %; va de 5,1 % en adultos
   jóvenes por urgencias a 35,6 % en los de 75+ por Treatment urgency) y κ calibra el nivel contra el
   pronóstico de ingresos a cama del mismo horizonte.
4. A cada futuro hospitalizado se le **sortea una trayectoria real** de un paciente de su mismo perfil
   (hora de llegada, espera y estancia del MISMO paciente histórico, ventana 2024-2025, 14.287 estancias,
   20 de 21 celdas con ≥ 30 casos), suavizada con ruido de Silverman (misma técnica que el motor A5).
   **Desde el 16-nov**, la espera sorteada se ajusta por la **carga de llegadas del día simulado**
   (ver la subsección del backtest; `HUN_SIMINT_CARGA=0` lo desactiva).
5. **cama = llegada + espera; alta = cama + estancia.** La ocupación se acumula por día (misma convención
   validada de A5); la cola de espera por HORA y se promedia por día, igual que la cola real observada.
6. **Siembra** en el corte: el censo real en cama (~100) y la cola real (~21-36) de ese día.

La cola real observada (censo horario entre `llegada` e `ingreso_cama` de las estancias únicas) da media
**25,8 pacientes** — reproduce la referencia de `docs/capacidad_efectiva.md` (~26) con un cálculo independiente.

## Backtest integrado (puerta de validación): ene a 9-abr-2026, entrenado hasta dic-2025

La puerta era doble: no empeorar el backtest de ocupación del motor A5 (tolerancia: MAE hasta 1 cama peor,
cobertura dentro de la meta 70-90 %) y reproducir la cola y las altas, que A5 no emitía. **Cumple.**

| Serie | MAE | Sesgo | Cobertura 10-90 % | Nota |
|---|---|---|---|---|
| Ocupación (camas) | 9,3 | +7,8 | **74,7 %** | A5: 8,6 / +7,0 / 78,8 % — dentro de tolerancia |
| Cola de espera | 4,3 | −2,4 | 70,7 % | real medio del periodo: 27,4 — la reproduce |
| Ingresos a cama/día (emergentes) | 4,0 | +0,7 | 79,8 % | los conteos que emergen de los agentes cuadran |
| Altas/día | 4,7 | +0,5 | 68,7 % | — |
| Llegadas/día | 18,8 | +11,7 | 58,8 % | banda angosta: solo ruido Poisson, no error del pronóstico (límite heredado de A5) |

### Validación directa de distribuciones (15-nov-2026, sección 5b del script)

La validación por agregados es indirecta (la cola es la huella de la espera y la ocupación la de la estancia,
ley de Little). Para cerrar el argumento se compararon **de frente** los percentiles de los tiempos que reciben
los agentes (100.000 sorteos con el mismo mecanismo: perfil ponderado por P(cama) y `trayectoria_para`) contra
los reales del periodo de backtest (`resultados/tablas/simint_distribuciones.csv`):

| Serie | n real | Mediana sim / real | p75 sim / real | p90 sim / real | Media sim / real |
|---|---|---|---|---|---|
| Espera de cama (h) | 1.810 | 18,9 / 17,0 | 40,3 / 45,1 | 74,7 / 79,6 | 31,7 / 33,8 |
| Estancia (h) | 1.756 | 75,2 / 69,6 | 149,1 / 141,6 | 283,8 / 260,6 | 125,9 / 116,9 |

Los percentiles casi se calcan. Dos sesgos chicos y explicables: la cola alta de la **espera** real de 2026 es
algo peor que el pool 2024-2025 (coherente con que los peores casos empeoran año a año, `docs/CONTEXTO_TECNICO.md` 6b), y la
cola alta de la **estancia** real está algo recortada porque las estancias largas que entraron en el backtest y
aún no tenían alta registrada quedan fuera del lado real (censura, no error del simulador).

### Ajuste de la espera por carga de llegadas del día (16-nov-2026, sección 1b del script)

En los días con más llegadas la espera **típica** de cama es más larga: coeficiente de log(espera+1) sobre las
llegadas estandarizadas del día de llegada = **+4,7 % por desviación** (~48 llegadas; se 0,011, t ≈ 4,5,
14.289 estancias de 2024-2025). Desde el 16-nov cada día simulado multiplica las esperas sorteadas de sus
llegadas por `exp(β·z)/C`, con z acotado a ±3 (soporte histórico) y C un centrado medido entre hospitalizados
que deja la **media poblacional de la espera sin cambio**. Verificación (puerta: no distorsionar el backtest y
conservar el promedio — **cumple**):

| Métrica | Sin ajuste (base 15-nov) | Con ajuste (16-nov) |
|---|---|---|
| Backtest ocupación MAE / cobertura | 9,32 / 74,7 % | 9,38 / 75,8 % |
| Backtest cola MAE / sesgo / cobertura | 4,33 / −2,37 / 70,7 % | 4,34 / −2,44 / 70,7 % |
| Cola media simulada (demo misma semilla) | 25,29 | 25,21 |
| Corr(llegadas, cola) día a día simulada | 0,260 | **0,264** (real: 0,289) |
| Proyección 180 d: ocupación / % saturación | 112,2 / 69,1 % | 112,2 / 69,2 % |

Qué hace y qué no (medido antes de implementarlo, decisión de la conversación del 16-nov):
- **Se descartó condicionar por decil de llegadas del día con multiplicadores de la media**: salen 0,95–1,09
  **sin patrón monótono** (el decil más cargado da 0,99) — a esa granularidad la espera MEDIA es plana; solo la
  típica (mediana/escala log) sube. El ajuste implementado usa la escala log, y por eso **redistribuye** la
  espera típica entre días cargados y tranquilos sin cambiar las horas totales.
- El gradiente fuerte de la Fase 4 (14 → 26 h por decil de llegadas de las **6 h previas**) vive dentro del día
  y **ya estaba embebido**: las trayectorias sortean hora y espera juntas del mismo paciente real, así que el
  patrón por franja (madrugada 13,7 h / tarde 24,3 h de mediana) se reproduce solo.
- **La retroalimentación ocupación → espera NO se modela**: no es estimable del histórico (espera plana por
  quintil de ocupación, Fase 4; cola sin correlación con la ocupación, `docs/capacidad_efectiva.md`). El
  hospital nunca operó holgado, así que no hay contraste para medirla; se declara como límite.

## Proyección integrada (180 días desde el 9-abr-2026, 1.000 repeticiones)

| Vista | Media | p10-p90 medio |
|---|---|---|
| Llegadas al hospital/día | 260 | 240-281 |
| Ingresos a cama/día | 19,7 | 14-26 |
| Altas/día | 19,6 | 14-25 |
| Pacientes esperando cama a la vez | **25,4** | 20-31 |
| Camas ocupadas | **112,2** | 99-126 |
| % días-repetición sobre 106 camas | **69,1 %** | — |

Coherente con el motor A5 (111,1 camas y 65,4 %, `docs/modelo_camas.md`); la diferencia (~1 cama) viene de que
las estancias ahora se sortean junto con la espera del mismo paciente y de la siembra de la cola.

## La página del dashboard (`/simulador`)

Mismo patrón que `/camas`: panel de sliders a la izquierda (botón **Simular**, 200 repeticiones en vivo),
tarjetas de métricas y un gráfico de **tres paneles apilados con el mismo eje de tiempo** (flujo diario /
camas ocupadas frente a 106 / cola de espera), más los paneles "¿Cómo se interpreta?" y "Ficha técnica".
Sliders: **demanda** (escala llegadas y, vía los agentes, los ingresos), **estancia** (escenario C) y
**espera** (palanca nueva: mueve la cola pero NO la ocupación — la cama se ocupa igual, solo que antes o
después; la nota de la página lo advierte para que nadie lea "menos espera = camas libres").

## Límites (declarados también en la página)

- **La cola es cota inferior:** solo contiene futuros hospitalizados. La congestión completa de urgencias no
  se puede simular (36-42 % de las etapas TU sin hora de fin, `docs/CONTEXTO_TECNICO.md` 4.3).
- **Fidelidad estadística, no bola de cristal:** reproduce patrones (cuántos, qué perfiles, qué tan lleno),
  no días concretos ni pacientes concretos.
- P(cama|perfil) constante por día; κ global por corrida (no por día de semana). El patrón semanal de los
  ingresos emergentes hereda el de las llegadas suavizado por la espera (el backtest muestra que alcanza).
- Los sembrados reciben tiempos completos del bootstrap (sin corregir el sesgo de selección); solo afecta los
  primeros días.
- Las llegadas incluyen ~4 % de réplicas (cota conocida, `docs/CONTEXTO_TECNICO.md` 4.13).
- El ajuste por carga del día (16-nov) mueve la espera típica, no la media por día (que es plana en los datos);
  la retroalimentación ocupación → espera no se modela porque no es estimable del histórico (ver la subsección
  del backtest). Si la simulación sale muy lejos del régimen histórico de ocupación, las esperas no se alargan
  solas: el resultado de esos escenarios es la presión sobre camas, no la espera individual.
- Asociación, no causa; periodo confiable hasta el 9-abr-2026; 106 camas es la cifra del HUN sin fecha.

## Fases siguientes (plan de Samuel)

- **Fase 2 (alertas operativas):** umbrales sobre las series simuladas (p. ej. probabilidad de cola > X o de
  saturar 106 en los próximos 7 días) — las series ya existen, falta definir los cortes con validación.
- **Fase 3 (motor de recomendaciones):** ligar cada alerta a la palanca que la mueve (estancia → camas;
  espera → cola; demanda → todo), reutilizando la evidencia de `docs/recomendaciones.md`.

## Entregables
- `src/simulador_integral.py` (motor; `python src/simulador_integral.py` corre backtest + proyección).
- `dashboard/pages/simulador.py` (página `/simulador`, registrada en `dashboard/navegacion.py`).
- `resultados/tablas/simint_backtest.csv`, `simint_resumen.csv`, `simint_proyeccion.csv`.
- `resultados/graficos/simint_resultados.png` (6 paneles: 3 de backtest, 3 de proyección).

## Modelos de la ficha A9 y casos (15-nov-2026)

En el panel de la izquierda hay controles nuevos. Cambian el pronóstico de llegadas y de ingresos a cama, del que salen las tres gráficas
(demanda, cola de espera y ocupación), así que las tres se mueven a la vez y se actualizan solas. Sin nada marcado, el motor es el de siempre.

- **Entrenar el pronóstico con (ficha A9):** casillas para marcar, uno por uno, los modelos de la ficha A9. Cada uno entra solo en la serie
  donde A9 lo probó: dengue y lluvia en las llegadas; curva suave del año, infecciones respiratorias y diarreas en los ingresos a cama. Al
  marcar uno se muestra su error en la prueba frente a «sin modelo».
- **Casos:** solo aparecen los de los modelos marcados (la curva del año no tiene caso). Cada caso tiene **su propia escala**, sacada de lo
  que de verdad pasó en las semanas de 2023-2025 frente a lo normal de esa época del año (`casos_escala.csv`): muy bajo (una semana más baja
  que 19 de cada 20), bajo (más baja que 3 de cada 4), normal, alto (más alta que 3 de cada 4), muy alto (9 de cada 10), grave (19 de cada
  20) y récord (la más alta). Solo aparecen los niveles que existieron en ese caso. El caso se aplica a todo el horizonte simulado.

| Caso | Muy bajo | Bajo | Alto | Muy alto | Grave | Récord |
|---|---|---|---|---|---|---|
| Dengue | −47 % | — | +216 % | +309 % | +369 % | +492 % |
| Infecciones respiratorias | — | — | +44 % | +63 % | +78 % | +113 % |
| Diarreas | −27 % | −6 % | +24 % | +35 % | +41 % | +92 % |
| Lluvias | −79 % | −61 % | +92 % | +195 % | +479 % | +1.570 % |

  (% sobre lo normal de esa semana en 2016-2022; «—» = ese nivel no se dio. Las respiratorias estuvieron casi siempre por encima de lo
  normal prepandemia, por eso no tienen niveles bajos. 2023-2025 fueron años de mucho dengue.)

**Error de cada modelo** (`src/medir_casos.py`; entrenado hasta el 30-jun-2025, WAPE diario):

| Serie | Modelo | Validación (jul–dic 2025) | Prueba (ene–9 abr 2026) |
|---|---|---|---|
| Llegadas | Sin modelo | 7,8 % | 6,9 % |
| Llegadas | Dengue | 7,3 % | 7,1 % |
| Llegadas | Lluvia | 7,6 % | 6,8 % |
| Ingresos a cama | Sin modelo | 16,7 % | 20,1 % |
| Ingresos a cama | Curva del año | 16,8 % | 19,8 % |
| Ingresos a cama | Respiratorias | 16,6 % | 20,0 % |
| Ingresos a cama | Diarreas | 17,0 % | 20,0 % |

Las diferencias son de décimas: ningún modelo cambia mucho el error diario. Su valor está en el ritmo del año a varios meses (ficha A9).

**Cómo se midió el efecto de los casos** (`src/medir_casos.py` → `casos_efecto.csv`, fuera del repositorio). Es el efecto **propio** de cada
caso, en porcentaje, y vale igual en cualquier mes:
- Para cada caso y cada semana epidemiológica se calcula cuánto está por encima o por debajo de **lo normal para esa semana del año** (la media
  de esa semana en 2016-2022 para dengue, IRA y EDA de Barranquilla; 2005-2022 para la lluvia). Así un brote de dengue en julio cuenta como
  brote aunque julio no sea temporada, y la baja de pacientes de diciembre no se confunde con el dengue.
- La demanda de cada semana se compara contra lo esperado por el calendario, el nivel de cada año y las formas del año de esa serie.
- Una regresión con las 151 semanas de feb-2023 a dic-2025 y los cuatro casos juntos da una elasticidad por caso y serie: si el caso está X %
  por encima de lo normal, la demanda cambia (1 + X/100)^b − 1. El simulador aplica esa fórmula al valor del deslizador.

| Caso | Alto: llegadas / ingresos | Grave: llegadas / ingresos | Récord: llegadas / ingresos |
|---|---|---|---|
| Infecciones respiratorias | **+3,2 %** / +1,1 % | **+5,1 %** / +1,7 % | **+6,7 %** / +2,3 % |
| Dengue | +0,2 % / +0,1 % | +0,2 % / +0,1 % | +0,2 % / +0,1 % |
| Diarreas | −0,2 % / +0,0 % | −0,3 % / +0,1 % | −0,5 % / +0,1 % |
| Lluvias | −0,2 % / −0,2 % | −0,6 % / −0,6 % | −1,0 % / −1,0 % |

En negrita, el único efecto cuyo intervalo del 95 % no incluye el cero. **Lo que dicen los datos:** en 2023-2025, las semanas con más
infecciones respiratorias que lo normal traen más pacientes al hospital; las semanas con más dengue, diarreas o lluvia que lo normal casi
no cambian la demanda, ni siquiera en las semanas de más dengue. El efecto del dengue que se ve al mirar el año completo es de temporada
(su pico coincide con diciembre y enero) y lo aplica el modelo de dengue al marcarlo, no el caso. Como cada nivel salió de semanas reales,
ningún nivel se sale de los datos.

**Límites:** son asociaciones; las semanas altas son pocas (12 a 14 para IRA y EDA); los datos externos llegan a 2025 y la simulación parte
de abril de 2026; el efecto se aplica parejo durante todo el horizonte.

Código: `src/simulador_integral.py` (sección «Modelos de la ficha A9 y casos»: `MODELOS_A9`, `CASOS`, `EFECTO_CASOS`, `ERROR_MODELOS`,
`pronostico_entrenado`, `efecto_aplicado`, `factor_casos`; `simular_integral(..., modelos=, casos=)`), `src/medir_casos.py` y
`dashboard/pages/simulador.py`. Si `casos_efecto.csv` y `modelos_error.csv` no están, el motor usa los valores de la última corrida.

## Alertas y operación óptima durante la simulación (18-nov-2026)

La simulación se reproduce siempre como «hoy». Mientras corre, salta una tarjeta arriba del gráfico (dentro del flujo de la página, sin tapar nada) con la etiqueta **Alerta**, su gravedad, **qué pasó** y la **recomendación** (con su primer paso). Tiene flechas ◀ ▶ para recorrer las alertas anteriores sin interrumpir la reproducción, y enlaces a **la alerta** (`/alertas#alerta-A2`) y a **la recomendación** (`/recomendaciones#rec-R4`) que abren la página y llevan a esa tarjeta, resaltada un momento.

**Calibración.** En un caso normal de la propia simulación (90 días, sin palancas) la probabilidad de superar las 106 camas tiene mediana 68 % y casi nunca pasa de 84 %; las camas ocupadas, mediana 111 y p90 114,5; la cola, mediana 25 y p99 28. Superar las 106 camas es lo normal en esta simulación: por eso esa condición avisa **una sola vez** y lo que **frena** la simulación es lo crítico, por encima de lo típico. Los primeros 7 días (4 si el plazo es de 2 semanas o menos; 12 horas en la vista horaria), que vienen de la siembra con el censo real, no generan alertas. Si los controles mejoran claramente al hospital (por ejemplo, estancia −10 %), no saltan alertas porque ya no hay riesgo.

**Gravedades y pausa.** Hay dos gravedades: aviso (media) y crítico (alta). **Las dos frenan la simulación**, para poder revisarlas y aplicar la mejora antes de que la condición escale. Una alerta salta cuando **aparece** (20-nov-2026). Si se dejó **sin corregir** (Continuar), al volver no frena otra vez: su fila comprimida queda marcada como activa (el punto late) mientras la condición se cumpla. **Vuelve a saltar** si reaparece después de aplicarle la mejora (la mejora no alcanzó) o si se agrava de aviso a crítico, aunque siga activa. Reiniciar o una corrida nueva borran esa memoria; aplicar una mejora no. Todas las alertas tienen **histéresis**: se encienden en el umbral de aviso y, ya encendidas, solo se apagan al volver claramente a lo normal (cola por debajo de 26; faltarán camas con probabilidad por debajo de 40 % y sin camas faltantes; las por paciente, en su nivel de suelta). Así un vaivén de uno o dos pacientes no cuenta como alerta nueva.

| Alerta | Aviso (gravedad media) | Crítico (gravedad alta) | Recomendación | Alerta (página Alertas, categoría Riesgo) |
|---|---|---|---|---|
| Faltarán camas (se necesitarán más de las 106: probabilidad de superar la capacidad a 48 h y camas que faltan, en la mediana) | desde 50 % o 1 cama que falta (107 ocupadas) | desde 84 % o 12 camas que faltan (118 ocupadas) | R3, R4 y R7 | A2 |
| Cola de espera larga (pacientes a la vez) | desde 28 | desde 33 (el percentil 90 real) | R5 y R6 | S1 |
| Estancias más largas de lo normal (en cama con más días que el p90 de su perfil) | desde 23 | desde 28 | R7 | A2 |
| Esperas de más de 3 días (72 h o más sin cama) | desde 10 | desde 13 | R5 y R6 | A3 |
| Ingresos con riesgo de estancia larga (% de ingresos de 7 días de 60+ o treatment urgency) | desde 47 % | desde 55 % | R7 | A2 |

La tarjeta apila sus botones de arriba abajo: Continuar, Aplicar mejora y comparar, Ver más sobre esta alerta y Ver recomendación. La reproducción nueva arranca cuando la figura nueva ya está dibujada, para que el gráfico no parpadee al reiniciar.

Los umbrales son criterios de esta página, no resultados validados como los de `docs/recomendaciones.md`. Si coinciden varias, gana la más grave.

Al aplicar la mejora, las alertas de la corrida anterior **no desaparecen**: siguen consultables, y las nuevas se suman al historial.

**Una sola acción: «Aplicar mejora y comparar».** Se frena la reproducción, el panel de configuración se abre y los controles se desplazan, uno tras otro, a la operación óptima (R7: 15 % menos en las estancias de más de 14 días; R4: 30 % de las altas de la tarde adelantadas a la mañana). El panel se enfoca en las dos palancas que cambian, se mueven una tras otra y, cuando terminan, **se cierra solo y la vista baja al gráfico**. Entonces la simulación se **repite desde el día 1** con la operación óptima a todo color y cómo iba antes («Antes de la mejora») en gris punteado, durante toda la corrida. La alerta de cola no ofrece la mejora, porque la operación óptima no la mueve directamente. «Reiniciar» devuelve los controles a cero.

## Ingresos por franja horaria (19-nov-2026)

El pronóstico de ingresos a cama ahora se reparte en cuatro franjas del día: **madrugada (0-7 h), mañana (7-14 h), tarde (14-19 h) y noche (19-24 h)**, las mismas de `src/estimador_tiempo_restante.py`.

- **Cómo:** `simular_integral` devuelve `info["ingresos_franja"]` = `{franja: {p10, p50, p90, media}}` por día. Reparte cada ingreso diario simulado con la distribución horaria **real** de asignación de cama (2024-2025), medida por día de la semana (`REPARTO_FRANJA`).
- **Por qué no sale de los agentes:** el motor diario suaviza la espera con ruido, lo que aplana la hora y daba ~25 % por franja. Lo medido es madrugada ~17 %, mañana ~12 %, tarde ~32 %, noche ~38 %.
- **Garantías:** no usa números aleatorios nuevos (las series existentes salen idénticas) y las medias de las cuatro franjas suman el total diario. Los percentiles son bandas, no suman exacto.
- **Vista horaria (72 h):** `ingresos_por_franja_horario(horas_idx, out)` agrupa las horas simuladas en las mismas franjas.
- **Límite:** el reparto es el promedio histórico; no cambia con la saturación ni con los controles del simulador.

## Confirmación verde al aplicar una mejora y pico de llegadas de la tarde (19-nov-2026)

- **Pacientes de ejemplo:** `simular_integral(..., registrar_rep=0)` devuelve `info["pacientes"]` con los pacientes de **una** repetición (perfil, sexo, llegada, espera, estancia, día de cama y de alta; los que ya estaban en cama el día 0 aparte). No usa números aleatorios del motor: las series salen idénticas con o sin el registro. El sexo de los sembrados en cama sale de un generador aparte.
- **Panel verde (`dashboard/pacientes_alerta.py`):** al pulsar «Aplicar mejora y comparar», los controles se mueven y la simulación **queda en pausa** con un panel verde hasta pulsar «Continuar con la mejora».
  - *Faltarán camas:* las altas del día (llegada + espera + estancia) y el 30 % de ellas que pasaría a la mañana (se sortea con semilla fija, así que el mismo día da el mismo resultado); y los pacientes de 14 días o más, separados en «ya llevan 14 días o más en cama» y «estimados de 14 días o más».
  - *Cola de espera:* para 48 h y para 72 h, «esperando ese tiempo o más ahora mismo» (al cierre del día) y «estimados» (llevan menos, pero su espera asignada es de ese tiempo o más).
- **Límites:** las tablas son una corrida, no el promedio; la cifra del texto de la recomendación (~34) sale de promedios y puede diferir. Los pacientes que ya estaban en cama el día 0 no tienen fecha de ingreso, así que solo entran en «estimados». Las estancias y esperas «estimadas» son las del simulador según el perfil, no las del modelo de «Paciente en espera». La vista horaria no tiene estas tablas.
- **R3 («Reunión de camas»):** ya no repite las camas esperadas, que están en «Qué pasó».
- **Estancia y espera acopladas (supuesto):** con `acoplar_estancia=True` (lo usa el dashboard) la espera de cada paciente sube en la misma proporción que la estancia. No está calibrado con datos.
- **Pico de llegadas de la tarde:** la alerta de cola también salta si las llegadas de 14 a 19 h llegan a 81 o más ese día (percentil 90 de los datos reales; promedio 65) y la cola ya es de al menos el 80 % del umbral (22 de 28). Con la operación normal del simulador nunca se supera (máximo 76,7 en 90 días); con 15 % más de llegadas se supera 19 de 90 días. Es un indicador del volumen del día, no una medida independiente, porque el reparto por franja es fijo por día de la semana.
- **Alertas:** una alerta salta cuando **aparece**; si ya estaba activa no vuelve a saltar, y si se va y reaparece salta de nuevo. Las que coinciden el mismo día se encolan y se muestran una tras otra.

## Alertas comprimidas y alertas por paciente (19 y 20-nov-2026)

- **Alertas comprimidas (`dashboard/assets/simint_compacto.js`):**
  - Al pulsar Continuar o Aplicar mejora, la tarjeta se comprime en una fila con punto de color, título y fecha.
  - Las filas se acumulan en el lugar de la tarjeta, en columnas: Críticas, Avisos y Con mejora.
  - Un clic en una fila abre la tarjeta completa, y la ✕ la vuelve a comprimir.
  - En las alertas con mejora, «Ver listas de pacientes» cambia la tarjeta por las tablas, y la flecha vuelve a la tarjeta. Los cambios de tamaño tienen una transición de altura.
  - Las flechas para recorrer el historial se quitaron.
- **Desplazamientos (`dashboard/assets/simint_scroll.js`):**
  - Al saltar una alerta, su encabezado queda en el primer cuarto de la pantalla.
  - Al aplicar la mejora, la ventana de configuración queda centrada y se abre solo el grupo del control que se mueve.
  - Al continuar, el gráfico queda centrado sin cortar el botón de reproducir.
- **Configuración en acordeón:** solo se ven los encabezados de los grupos, y cada grupo se abre con un clic.
- **Tres alertas por paciente:**
  - Son estancias más largas de lo normal, esperas de más de 3 días e ingresos con riesgo de estancia larga.
  - Se cuentan día a día sobre los pacientes de la repetición registrada (`pacientes_alerta.series_alertas`).
  - Tienen histéresis: una vez activas, siguen activas hasta bajar de un nivel de suelta.
  - Calibración, justificación e ideas descartadas: `docs/alertas_por_paciente.md`.
  - No existen en la vista horaria, que no registra pacientes.
