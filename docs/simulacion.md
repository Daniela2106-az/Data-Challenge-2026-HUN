# Simulación de escenarios de camas (ficha A5 / 3.2, 9-nov-2026; mejora del 9-nov; bootstrap suavizado del 10-nov)

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
| **B: ingresos +10 %** | Un aumento sostenido de demanda (ej. brote, temporada alta) | **121,9** (+10,8 sobre el base de 111,1) | 90,9 % / 50,2 % / 92,0 % | Un 10 % más de pacientes llevaría al hospital a estar saturado casi 9 de cada 10 días — el escenario más costoso de los tres |
| **C: estancia −5 %** | Más eficiencia clínica (altas más tempranas, procesos más rápidos) | **106,2** (−4,9 sobre el base) | 48,1 % / 28,2 % / 55,1 % | Bajar la estancia 5 % sigue reduciendo la saturación de forma importante frente a hoy, sin necesitar una sola cama más |

**Referencia (hoy, sin cambios):** ocupación media 111,1 camas; 65,4 % / 34,5 % / 70,6 % de días-repetición
saturados (total / niños / adultos) — ver `docs/modelo_camas.md`. (Cifras del 10-nov con el bootstrap suavizado;
antes eran 109,0 / 58,4 % / 32,0 % / 64,4 %, ver nota de la mejora en `docs/modelo_camas.md`.)

## Mejora del 9-nov: mezcla de ruta ajustable (escenario de ejemplo, no uno de los 3 mínimos)

Además de ingresos y estancia, ahora se puede simular un cambio en **qué proporción** de los ingresos llega por
cada ruta (Urgencias / Treatment urgency / Ambulatorio) — sin tocar el resto del motor, porque el bootstrap de
estancias ya está separado por ruta (ver `docs/modelo_camas.md`). Ejemplo con base real: la ruta Treatment
urgency **ya duplicó su peso** entre 2023 y 2025 (3,8 % → 13,5 % de las estancias, `docs/factores_estancia.md`,
y se queda 63 % más tiempo que Urgencias). Si ese crecimiento se duplica otra vez (13,5 % → 27 %):

| Escenario | Ocupación media (total) | % días-repetición saturados (total) |
|---|---|---|
| Hoy (13,5 % Treatment urgency) | 111,1 | 65,4 % |
| Treatment urgency al 27 % | **118,1** (+7,0) | **84,6 %** |

No es un escenario hipotético sin base: es la misma tendencia que A2 ya documentó, proyectada hacia adelante.
`mezcla_edad` funciona igual para probar, por ejemplo, un escenario de envejecimiento de la población atendida.

## Lectura conjunta

**La estancia pesa más que el volumen de ingresos**, y por un margen amplio: C (−5 % estancia) mueve la
ocupación casi tanto como B (+10 % ingresos), con un cambio porcentual mucho menor (5 % contra 10 %). Esto
confirma, con un método distinto (simulación estocástica en vez de la ley de Little), algo que el proyecto ya
había encontrado: la ocupación subió por la **estancia** (+16 % 2023→2025), no por más ingresos (~20 por día,
estables). La recomendación **R7** del equipo (`docs/recomendaciones.md`, "Revisar las estancias largas") ya
estimaba con la ley de Little que bajar la estancia 5 % libera ~5 camas — la simulación lo reproduce casi exacto
de forma independiente (111,1 → 106,2, una diferencia de 4,9 camas, igual que con los motores anteriores: 109,0
→ 104,3 con el bootstrap por perfil sin suavizar). Tres versiones del motor llegando al mismo número no es
casualidad: da confianza en la cifra.

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
Cuarto panel de `resultados/graficos/simcamas_resultados.png` ("Ocupación media por escenario"): compara las
tres barras (hoy / B / C) contra la línea de 106 camas. El quinto panel (curva de capacidad) está documentado
en `docs/modelo_camas.md`, sección 4.

## Entregables
- `resultados/tablas/simcamas_escenarios.csv` (B y C, con el desglose niños/adultos).
- Este documento. El código, el backtest y la curva de capacidad están en `docs/modelo_camas.md`.
