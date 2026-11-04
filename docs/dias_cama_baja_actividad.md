# Exploración 3 · Días-cama de baja actividad clínica (4-nov-2026)

Código: `src/dias_cama_baja_actividad.py`. Tablas (fuera de git): `resultados/tablas/dias_cama_*.csv`. Gráfico: `resultados/graficos/dias_cama_baja_actividad.png`.

**Idea:** medir la huella clínica registrada de cada estancia (días con al menos un laboratorio sobre los días en cama, marca de UCI, atención de nutrición; `S01_actividad_por_estancia.csv`, lote 3 de la auditoría) y ver cuántas camas ocupan estancias largas con muy poca actividad: candidatas a «cama ocupada con poca actividad aguda» (esperando traslado, trámites, cuidados de baja complejidad).
**Categorías:** *sin huella* (ni laboratorio, ni UCI, ni nutrición); *baja actividad* (estancia de 7 días o más, laboratorio en menos del 25 % de los días y sin UCI); *activa* (el resto). Se une a nuestras estancias por inicio y fin de cama (coincide el 87 %: 23.248 estancias).

## Resultados
Camas equivalentes (días-cama divididos entre los días del periodo; 2026 hasta el 9-abr):

| Año | Activa | Baja actividad | Sin huella |
|---|---|---|---|
| 2023 | 69,0 | 7,0 | 16,2 |
| 2024 | 82,8 | 6,1 | 12,3 |
| 2025 | 88,5 | 5,8 | 9,9 |
| 2026 | 72,9 | 4,4 | 8,4 |

1. **La baja actividad es pequeña y no crece:** unas 6 camas (6–8 % de los días-cama) y bajando, mientras la ocupación total sube de 94 a 105. **El aumento de ocupación no viene de camas con poca actividad**: viene de camas con actividad clínica registrada (la columna «activa» sube ~20 camas).
2. **En las estancias de más de 14 días** (las que más crecieron) solo el 7–14 % es de baja actividad (2–3 camas); la mediana de días con laboratorio es del 57–65 % de los días. Son pacientes con atención casi diaria.
3. **Las estancias «sin huella» son cortas y bajan** (16 → 10 camas): partos, observación y procedimientos de pocos días, y parte de la baja puede deberse a mejor registro.
4. **Quién tiene más baja actividad entre las estancias de 7 días o más:** niños (21–22 % de 0 a 14 años frente a 9 % de 60 a 74), diagnósticos musculoesqueléticos (29 %), trauma (28 %) y digestivo (22 %); mujeres 14 % frente a 11 % de hombres. Ojo: no es causa y los grupos de niños y trauma pueden tener cuidados que no dejan laboratorios.

## Conclusión
Con este criterio, **no hay un bolsón grande de camas ocupadas sin actividad clínica**: el máximo defendible es del orden de 6 camas (~6 % de la ocupación), y no explica el crecimiento. Refuerza que el aumento de estancia es de pacientes activos. Una recomendación basada en «reducir días evitables» **no tendría respaldo fuerte en estos datos**.

## Límites
Es una cota descriptiva, no un diagnóstico de estancia evitable: un paciente puede recibir antibióticos, rehabilitación o cuidados de enfermería que no dejan laboratorios, y uno estable no necesita laboratorio diario. Los laboratorios se contaron en todas las visitas gemelas (pueden incluir los de la otra persona). La base no trae signos vitales, servicio ni notas.
