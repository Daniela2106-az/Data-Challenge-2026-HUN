# Simulación de escenarios de camas (ficha A5 / 3.2, 9-nov-2026)

**Qué pide el instructivo:** "¿qué efecto tendrían cambios operativos sobre la ocupación y la disponibilidad de
camas?" Tres escenarios mínimos, cada uno con sus supuestos escritos. Motor: `src/simulacion_camas_montecarlo.py`
(ver `docs/modelo_camas.md` para el método y el backtest). **Cuidado:** esto NO demuestra que ninguno de estos
cambios vaya a ocurrir en la práctica — son proyecciones condicionadas a que el patrón histórico se mantenga.
Todo lo que sigue es ocupación proyectada desde el 9-abr-2026, 180 días, comparada contra las 106/18/88 camas
que dio el HUN (total/niños/adultos).

## Los tres escenarios

| Escenario | Supuesto | Ocupación media (total) | % de días-repetición saturados (total / niños / adultos) | Frase para un gerente |
|---|---|---|---|---|
| **A: altas antes del mediodía** | 30 % de las altas de la tarde pasan a las 9-12 h del mismo día (no cambia la estancia en días, solo la hora de salida) | *No recalculado — citado de `src/simulacion_altas.py` (22-oct-2026)* | — | Libera hasta 5,1 camas adicionales a las 12 h; evita **como máximo el 8 % del exceso de espera** (estimación ~3 %). Ayuda, pero no resuelve: el 83 % de las horas de espera viene de esperas de más de 24 h, que unas horas de adelanto no deshacen |
| **B: ingresos +10 %** | Un aumento sostenido de demanda (ej. brote, temporada alta) | **117,9** (+10,3 sobre el base de 107,6) | 83,8 % / 43,9 % / 86,1 % | Un 10 % más de pacientes llevaría al hospital a estar saturado más de 8 de cada 10 días — el escenario más costoso de los tres |
| **C: estancia −5 %** | Más eficiencia clínica (altas más tempranas, procesos más rápidos) | **102,9** (−4,7 sobre el base) | 36,1 % / 23,5 % / 44,1 % | Bajar la estancia 5 % reduce la saturación a la mitad frente a hoy, sin necesitar una sola cama más |

**Referencia (hoy, sin cambios):** ocupación media 107,6 camas; 53,2 % / 29,5 % / 60,0 % de días-repetición
saturados (total / niños / adultos) — ver `docs/modelo_camas.md`.

## Lectura conjunta

**La estancia pesa más que el volumen de ingresos**, y por un margen amplio: C (−5 % estancia) mueve la
ocupación casi tanto como B (+10 % ingresos), con un cambio porcentual mucho menor (5 % contra 10 %). Esto
confirma, con un método distinto (simulación estocástica en vez de la ley de Little), algo que el proyecto ya
había encontrado: la ocupación subió por la **estancia** (+16 % 2023→2025), no por más ingresos (~20 por día,
estables). La recomendación **R7** del equipo (`docs/recomendaciones.md`, "Revisar las estancias largas") ya
estimaba con la ley de Little que bajar la estancia 5 % libera ~5 camas — la simulación lo reproduce casi exacto
de forma independiente (107,6 → 102,9, una diferencia de 4,7 camas). Dos métodos distintos llegando al mismo
número no es casualidad: da confianza en la cifra.

**Dónde mirar para lograr ese −5 % de estancia** (de `docs/factores_estancia.md`, ya documentado, no inventado
aquí): la ruta "Treatment urgency" se queda 63 % más tiempo que quien entra por urgencias normales y creció
rápido (3,8 % → 13,5 % de las estancias 2023-2025); los mayores de 60 años se quedan 33-46 % más; y la mitad del
aumento de estancia viene de la cola de más de 30 días (54 → 117 estancias por año). **Límite honesto:** la base
no tiene campo de servicio, piso ni información de proceso interno — dice **dónde** concentrar la revisión
(geriatría, la ruta Treatment urgency, estancias largas), no **por qué** se alargan ni qué proceso específico
corregir; eso requiere revisión clínica dentro del hospital (mismo límite que ya declaraba R7).

## Supuestos y límites de cada escenario
- **A:** la hora de alta de los demás pacientes no cambia; la capacidad total de camas se desconocía al momento
  de ese análisis (ahora se sabe: 106); es una cota superior, no una predicción (`CLAUDE.md` 6b).
- **B y C:** se aplican como un ajuste uniforme sobre todo el horizonte simulado (no varían por mes ni se
  combinan con un escenario de calendario distinto); no modelan que un aumento de ingresos pudiera, a su vez,
  cambiar la duración de la estancia (por ejemplo, por saturación de personal) — se tratan como independientes.
- Ningún escenario toca la capacidad física (106/18/88): esas cifras son fijas, las dio el HUN.
- Asociación, no causa; todo lo de siempre del proyecto.

## Gráfico
Panel derecho de `resultados/graficos/simcamas_resultados.png` ("Ocupación media por escenario"): compara las
tres barras (hoy / B / C) contra la línea de 106 camas.

## Entregables
- `resultados/tablas/simcamas_escenarios.csv` (B y C, con el desglose niños/adultos).
- Este documento. El código y el backtest del motor están en `docs/modelo_camas.md`.
