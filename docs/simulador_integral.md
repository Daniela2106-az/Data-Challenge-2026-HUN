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

## Decisiones de diseño (de la conversación del 14-nov; cada descarte tiene su porqué)

| Qué se consideró | Resultado | Por qué |
|---|---|---|
| Encadenar pronóstico → estimador de espera → Monte Carlo en serie | **No entra** | Cada módulo se construyó para una población distinta: el estimador A6 solo vio pacientes que recibieron cama (no sabe decir "este no necesita cama") y el ~87 % de las llegadas atendidas se va de alta desde urgencias. Encadenarlos rompía los supuestos de cada uno. |
| Llenar una cuota diaria de camas con un ranking de probabilidad | **No entra** | Reinventa una fila de prioridad que los datos rechazan: el orden de llegada casi no predice el orden de cama (53 % de pares consecutivos en orden, azar 50 %, `CLAUDE.md` 6b) y la espera es individual, no del momento (el día de llegada explica el 0,1 % de la espera, `docs/estimador_tiempos.md` 1.1). |
| "Pacientes sin cama" = llegadas − ingresos a cama | **No entra** | Esa resta no es la cola: es sobre todo gente que nunca iba a necesitar cama. La cola se construye agente por agente (de su llegada a su cama) y se valida contra la cola real. |
| Usar el estimador A6 como predictor dentro del motor | **No entra** | Asignar a cada agente la predicción puntual comprime la varianza y daña las bandas. La espera se **sortea** de trayectorias reales; A6 sigue siendo la consulta para pacientes reales. |
| Ingresos a cama **emergentes** de los agentes, calibrados (κ) | **Entra** | Opción B de la conversación: los conteos emergen de llegadas × P(cama\|perfil) × espera sorteada; un factor global κ los calibra contra el pronóstico validado de ingresos. κ salió ≈ 1,00 (1,002 en el backtest, 0,994 en la proyección): la P(cama\|perfil) de `tabla_episodios` ya era consistente con el pronóstico — señal de coherencia interna, no un parche. |
| Trayectoria conjunta (hora de llegada, espera y estancia del MISMO paciente real) | **Entra** | Conserva la correlación real espera-estancia (+9 % de estancia por desviación de espera, `docs/factores_estancia.md`) y reproduce sola el patrón horario de asignación de camas, sin modelarlo aparte. |

## Cómo funciona (una repetición)

1. **Llegadas** diarias ~ Poisson(pronóstico de `llegadas` de `modelo_pronostico.py`).
2. Cada llegada recibe un **perfil** (grupo de edad × ruta) de la mezcla real de llegadas de 2025 (21 perfiles).
3. Cada llegada **se hospitaliza** con probabilidad κ × P(cama|perfil), donde P viene de `tabla_episodios`
   (hospitalizado y `estancia_unica` entre TODOS los episodios de 2025: global 7,6 %; va de 5,1 % en adultos
   jóvenes por urgencias a 35,6 % en los de 75+ por Treatment urgency) y κ calibra el nivel contra el
   pronóstico de ingresos a cama del mismo horizonte.
4. A cada futuro hospitalizado se le **sortea una trayectoria real** de un paciente de su mismo perfil
   (hora de llegada, espera y estancia del MISMO paciente histórico, ventana 2024-2025, 14.287 estancias,
   20 de 21 celdas con ≥ 30 casos), suavizada con ruido de Silverman (misma técnica que el motor A5).
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
  se puede simular (36-42 % de las etapas TU sin hora de fin, `CLAUDE.md` 4.3).
- **Fidelidad estadística, no bola de cristal:** reproduce patrones (cuántos, qué perfiles, qué tan lleno),
  no días concretos ni pacientes concretos.
- P(cama|perfil) constante por día; κ global por corrida (no por día de semana). El patrón semanal de los
  ingresos emergentes hereda el de las llegadas suavizado por la espera (el backtest muestra que alcanza).
- Los sembrados reciben tiempos completos del bootstrap (sin corregir el sesgo de selección); solo afecta los
  primeros días.
- Las llegadas incluyen ~4 % de réplicas (cota conocida, `CLAUDE.md` 4.13).
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
