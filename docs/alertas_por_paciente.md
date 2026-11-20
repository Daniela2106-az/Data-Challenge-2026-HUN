# Alertas por paciente del simulador integral (20-nov-2026)

Tres alertas nuevas del simulador integral (`dashboard/pages/simulador.py`, `_alertas_paciente`) que miran a los pacientes uno por uno, no a los totales del día.
Se cuentan sobre los pacientes de **una** repetición de la simulación, que son los mismos de las tablas de pacientes (`dashboard/pacientes_alerta.py`, `series_alertas`).
Los umbrales están en `dashboard/umbrales_alertas.py`.

## Cómo se calibraron

Se hicieron corridas de 90 días desde el 9-abr-2026 en cuatro escenarios: operación normal, estancia +15 %, espera +20 % y 20–40 % de perfiles de estrés.
Para cada conteo diario se midieron la mediana, el percentil 90 y el máximo. Los umbrales quedan por encima de lo normal: el aviso está cerca del máximo de la operación normal y el crítico, en lo que solo se alcanza con una palanca en contra.
Las alertas tienen **histéresis**: una alerta que ya saltó sigue activa hasta que el conteo baja de un nivel de suelta. Sin ella, el conteo cruzaba el umbral una y otra vez (hasta 10 avisos por corrida). Con ella, en operación normal cada alerta salta 1 o 2 veces en 90 días.

| Conteo diario (una repetición) | Normal: mediana / p90 / máx | Con la palanca en contra | Aviso | Crítico | Suelta |
|---|---|---|---|---|---|
| En cama por encima del p90 de su perfil | 15 / 21 / 23 | estancia +15 %: 20 / 28 / 30 | 23 | 28 | 19 |
| Esperando 72 h o más | 5 / 8 / 12 | espera +20 %: 8 / 12 / 14 | 10 | 13 | 7 |
| % de ingresos (7 días) de perfil de riesgo | 37 / 42 / 46 | 20 % de estrés: 56 / 62 / 64 | 47 | 55 | 42 |

Correlaciones en operación normal: «esperando 72 h o más» con la cola total, 0,35; «por encima del p90 del perfil» con las camas ocupadas, 0,49. Las dos alertas miden algo distinto de las que ya había.

## Alertas aprobadas

### Estancias más largas de lo normal (Sim 3, idea del equipo, ajustada)
- **Qué mide:** los pacientes en cama que ya llevan más días que 9 de cada 10 pacientes de su mismo perfil (edad × tipo de visita), según las estancias reales de 2023–2026 (`si.TRAY_PERFIL`).
- **Por qué aporta:** la ocupación sube por la estancia y no por la demanda (Ocupación de camas, resultados 1 y 2). La revisión de estancias largas (R7) empieza a los 14 días y no ve a los pacientes de perfiles cortos que ya se alargaron; son unos 3 de los 15 de un día normal.
- **Ajuste a la idea original:** el proyecto no tiene un «estimador de estancia», y predecir la estancia de un paciente al ingresar no funcionó (R² ≈ 0, HALLAZGOS 5.3). Por eso la alerta compara **cuánto lleva** cada paciente con lo normal de su perfil, en vez de intentar adivinar cuánto le falta.
- **Estancias de más de 30 días** (página Estancias largas): no quedan como alerta aparte. En la simulación son 2 a 4 pacientes, con mucho ruido, y su correlación con las camas es de 0,19. Aparecen como dato dentro de esta tarjeta.
- **Mejora:** R7, gestión de casos con una dosis calculada según cuánto se pasa el conteo de lo normal (recorte de las estancias de más de 14 días, entre 10 y 30 %).

### Esperas de más de 3 días (Sim 4, idea del equipo, ajustada)
- **Qué mide:** los pacientes que llevan 72 h o más sin cama. El percentil 90 real de la espera es 73,9 h, y los peores casos son los que empeoran (Espera de cama, resultado 2).
- **Por qué aporta:** la cola total puede verse normal mientras se acumulan los peores casos; la correlación entre las dos es solo de 0,35.
- **Resultados 3 y 5 (quién espera más):** se usan para **describir** a los pacientes (cuántos son mayores de 60 por urgencias y cuántos llegaron en la mañana), no para darles prioridad.
  - **Se rechazó** la idea de dar atención o cama prioritaria por perfil. Lo que se sabe del paciente explica solo el 16 % de su espera. Ordenar la fila por riesgo al llegar obligaría a marcar al 44 % de los pacientes, con 4 de cada 10 falsas alarmas (recomendaciones, sección 4).
  - Priorizar por sexo no tiene una causa conocida que lo justifique.
  - Lo que sí es accionable del resultado 5 es la llegada en la mañana: esos pacientes dependen de la asignación de camas de las 15 a 17 h.
- **Recomendación:** R5 (un responsable revisa cada caso) y R6 (dejar lista la solicitud de cama antes de las 15 h; en la simulación, espera −5 %). Para los pacientes que van en camino a 72 h, se sugiere el estimador de «Paciente en espera» a las 12 h, que existe y está validado (acierta 1 de cada 2).

### Ingresos con riesgo de estancia larga (Sim 5, propuesta nueva)
- **Qué mide:** el porcentaje de quienes recibieron cama en los últimos 7 días que son mayores de 60 o «treatment urgency». Son los perfiles con 2 a 3 veces más riesgo de pasar de 14 días (Estancias largas, resultados 3 y 4).
- **Por qué pasaría desapercibido:** las camas reflejan ese cambio en la mezcla de pacientes una o dos semanas después, cuando las estancias se alargan.
- **Límite:** en el simulador solo salta con los perfiles de estrés. Si se suben desde el inicio de la corrida, coincide con «Faltarán camas» y no da tiempo extra; el adelanto solo se ve si la mezcla cambia a mitad de la corrida.
- **Mejora:** plan de alta desde el ingreso (R7 temprano; en la simulación, recorte de 15 %).

## Ideas evaluadas y descartadas

| Idea | Por qué no |
|---|---|
| Atención o cama prioritaria por perfil (resultado 3) o por sexo (resultado 5) | Ver Sim 4: con los datos no se puede saber al llegar quién esperará mucho, y por sexo no hay causa conocida. |
| Estancias de más de 30 días como alerta propia | Ver Sim 3: pocos casos y mucho ruido en la simulación; queda como dato en la tarjeta. |
| Reingresos a 72 h (5,3 %) | El simulador no los modela: la alerta sería inventada. |
| Días de la semana y fines de semana | El día de la semana y los festivos casi no cambian la espera (Qué influye en la espera, resultado 1). |
| Desbalance de ingresos y altas en varios días | El balance diario es casi todo azar, y la proyección de camas a 24 h no le gana a «mañana igual que hoy» (`src/alertas.py`). |
| Días-cama de baja actividad | Son unos 6 y no crecen (`docs/dias_cama_baja_actividad.md`). |

## Pendiente que se notó al calibrar
La alerta que ya existía de «Cola de espera larga» salta 12 o 13 veces en 90 días cuando se sube la espera o la estancia. Se le puede aplicar la misma histéresis.
