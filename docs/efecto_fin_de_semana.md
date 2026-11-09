# Exploración 4 · Efecto del fin de semana y de los festivos (4-nov-2026)

Código: `src/efecto_fin_de_semana.py`. Tablas (fuera de git): `resultados/tablas/fin_de_semana_*.csv`. Gráfico: `resultados/graficos/efecto_fin_de_semana.png`. Periodo: 1-feb-2023 a 9-abr-2026, sin el 28 y 29 de marzo de 2026.

## Resultados
**1. Menos altas en fin de semana y en festivos** (altas por cada 100 camas ocupadas): día hábil 21,7; sábado 19,5 (−10 %); **domingo 15,8 (−27 %)**; festivo entre semana 14,4 (**−34 %**). Los ingresos a cama también bajan, pero menos: fin de semana −9 %, festivo −28 %. La ocupación es casi plana en la semana (100–101 camas): lo que cambia es el flujo, no el nivel.

**2. Dentro de la semana, los días con más altas son miércoles y viernes** (23,4 y 23,2 por día) y el lunes tiene pocas (18,6): **no se ve un «desquite» el lunes** de las altas que no ocurrieron el fin de semana.

**3. Espera de cama por día de llegada:** la mediana es más baja en fin de semana (domingo 15,5 h, sábado 17,2 h frente a 20,7 h del lunes), pero el **percentil 90 no mejora** (74–77 h, igual o peor que entre semana): las esperas largas no bajan aunque lleguen menos pacientes.

**4. Estancia según el día en que entra a cama** (modelo sobre log de la estancia con tipo de visita, año y edad, frente al martes): **sábado +12 % (IC 95 % 6,8 a 17,4 %)**, el único día con efecto claro; viernes +2,8 % (no significativo), lunes −4 % (no significativo). Quien ingresa a cama un sábado se queda, en promedio, 12 % más tiempo.

**5. Orden de magnitud (con un supuesto fuerte):** si cada alta que «falta» el sábado y el domingo (frente a un día hábil) se trasladara al lunes, serían ~8 altas por fin de semana y ~10 días-cama extra por semana, **del orden de 1,5 camas**. El supuesto no se sostiene del todo (el lunes no muestra desquite), así que es una cota alta de lo que costaría el retraso del fin de semana y, en cualquier caso, **es pequeña frente a las ~20 camas que libera adelantar las altas de la tarde** (ver el escenario de altas).

## Qué se puede decir
- Hay un efecto de fin de semana y festivo en las altas (−27 % el domingo, −34 % en festivos) y en la estancia de los que entran el sábado (+12 %).
- **No** explica por sí solo el cuello de botella: el efecto en camas es de ~1–2 camas equivalentes, y las esperas largas no cambian con el día.
- Recomendación respaldada con matiz: **altas en fin de semana y festivos** como mejora de bajo costo, con impacto pequeño en camas.

## Límites
Altas = fin de estancia registrado; hay horarios y costumbres de alta (HUN) sin detalle; el orden de magnitud supone el traslado al lunes; asociación, no causa; los festivos cuentan 53 días.
