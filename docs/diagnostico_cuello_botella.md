# A7 · Diagnóstico repetible de cuellos de botella (3-nov-2026)

Idea de Anthony (23-oct): que la lógica con la que se encontró el cuello de botella se pueda **repetir sobre cualquier periodo** y diga si sigue siendo el mismo o cambió. Script: `src/diagnostico_cuello_botella.py` (no necesita la base: lee `datos/procesados/tabla_episodios.parquet`).

```
python3 src/diagnostico_cuello_botella.py                                   # periodo confiable completo
python3 src/diagnostico_cuello_botella.py --desde 2025-01-01 --hasta 2025-12-31 --ref-desde 2023-02-01 --ref-hasta 2023-12-31
```
Salidas (solo agregados, en `resultados/tablas/`): `cuello_botella_<desde>_<hasta>.md` (el reporte), `.csv` (indicadores) y `_perfil.csv` (qué comparten).

## Los cinco pasos (el reporte sale en este orden)
1. **Dónde está el cuello de botella.** De los dos componentes de la espera de cama (urgencias antes de la cama y hueco sin etapa), el que acumula más horas por encima de la referencia de «cuando funciona bien» (mediana cuando las llegadas de las 6 h previas están en el 20 % más bajo, por niños y adultos, calculada con el **periodo de referencia**: así dos periodos se comparan con la misma vara). Dice si el cuello de botella **cambió** frente a la referencia.
2. **Qué se dispara.** Qué parte de las horas en exceso viene de las esperas de más de 24, 48 y 72 h; ocupación de camas frente a las 106 del HUN; ley de Little (ingresos × estancia); porcentaje de altas por la tarde.
3. **Qué registros se disparan.** Estancias con espera mayor al percentil 90 de la referencia; estancias de más de 14 días.
4. **Qué comparten.** Edad, tipo de visita, franja, sexo y grupo de diagnóstico de las disparadas frente al resto, con la razón entre ambos (solo grupos con 30 o más casos).
5. **Qué hacer.** Frases condicionadas por las cifras del periodo y ligadas a `docs/recomendaciones.md`; si una cifra no activa la regla, la frase no sale.

## Pruebas hechas
- **Periodo confiable completo:** cuello de botella = urgencias antes de la cama (72 % del exceso de los dos componentes); las esperas de más de 48 h son el 20 % de los pacientes y el 75 % de las horas en exceso; 62,6 % de las altas entre las 14 y las 19 h; la ocupación supera las 106 camas el 23 % de las horas.
- **2025 frente a la referencia de 2023:** el cuello de botella **no cambió**; el exceso medio por estancia pasa de 16,9 a 22,6 h; las disparadas son el 14,7 % (en la referencia serían el 10 %); la ocupación supera 106 camas el 42 % de las horas, coincidente con `CLAUDE.md` 4.8.

## Límites (declararlos siempre)
- **No es tiempo real:** se corre sobre un periodo que se le pasa («reproducir un periodo»).
- **Falta la simulación Monte Carlo de camas (A5, Anthony):** el paso 2 usa la ocupación observada, la ley de Little y el escenario de altas de `simulacion_altas.py`. Cuando A5 exista, se agrega ahí.
- **El paso 4 es asociación, no causa**; el diagnóstico se registra tarde y puede ser de la otra persona de un par duplicado.
- **Referencia de «cuando funciona bien»:** es una elección (se probaron cuatro en `ranking_cuellos.py`), no una meta del hospital; el HUN no dio una meta de tiempos.
- Si el periodo incluye días posteriores al 9-abr-2026, el reporte avisa que el registro está degradado.
- La causa individual de una espera (servicio, tipo de cama, gravedad) no está en la base.
