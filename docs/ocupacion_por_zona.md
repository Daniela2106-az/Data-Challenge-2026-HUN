# Exploración 1 · Ocupación por zona frente a las capacidades del HUN (4-nov-2026)

Código: `src/ocupacion_por_zona.py`. Tablas (fuera de git): `resultados/tablas/ocupacion_zona_*.csv`. Gráfico: `resultados/graficos/ocupacion_por_zona.png`.

**Pregunta:** comparar toda la ocupación contra las 106 camas mezcla zonas. El HUN dio el desglose (29-oct-2026): hospitalización, adultos 88 (piso 64, intermedio 6, intensiva 14, TPR 4) y niños 18 (pediátrica 8, neonatal 10); urgencias, 58 camillas (observación pediátrica 14, adultos hombres 18, adultos mujeres 26). Con la edad y el sexo de la persona real se ve en qué zona se supera la capacidad y si el sexo ayuda a entender por qué las mujeres esperan más cama.

**Cómo se midió:** estancias únicas (intervalo completo), periodo hasta el 9-abr-2026. Urgencias: etapas TU con hora de fin, cada intervalo distinto una vez. **Solo el ~38 % de las etapas TU tiene hora de fin, así que la ocupación de urgencias es una cota inferior.**

## Resultados

**1. El exceso sobre las camas está en los adultos.** Camas de adultos ocupadas frente a las 88: 88 % de la capacidad en 2023, 98 % en 2024 y **101 % en 2025**, con el 57,5 % de las horas de 2025 por encima de 88 (en 2023, 0,8 %). Los niños (menores de 15, frente a 18 camas) se mantienen entre el 83 % y el 99 %. El aumento de ocupación de 2023 a 2025 viene de los adultos (77 → 89 camas) y no de los niños (17 → 16). Es coherente con la causa ya documentada: las estancias largas de adultos (`CLAUDE.md` 4.8).

**2. El desglose pediátrico/neonatal del HUN no se puede comprobar con edad.** Los de 1 a 14 años ocupan 12–14 camas de media frente a 8 de pediátrica (más del 150 %), y los menores de 1 año solo 2–5 frente a 10 de neonatal. O los niños ocupan camas de otras zonas, o la clasificación por edad no calza con las unidades. Solo tiene sentido comparar a los niños **juntos** frente a las 18 camas.

**3. Las camillas de urgencias no alcanzan para el conteo, aun con una cota inferior.** En todos los grupos y años hay más pacientes en atención que camillas: en 2025, mujeres 15+ 2,55 por camilla, hombres 15+ 2,01 y menores de 15 años 1,27. Confirma que urgencias atiende también en sillas, consultorios y pasillos (no solo camillas), así que la razón es una medida de presión relativa, no de ocupación de camillas.

**4. El orden de la presión coincide con el orden de la espera de cama.** Mujeres 15+ (2,22 pacientes por camilla de media, espera mediana 25,7 h), hombres 15+ (1,83 y 16,8 h) y menores de 15 (1,30 y 9,5 h). Son solo tres grupos, así que es una pista y no una prueba.

**5. Pero la saturación del momento no explica la brecha entre mujeres y hombres.**
- Dentro de cada grupo, la saturación de urgencias al llegar casi no se relaciona con la espera (correlación de Spearman de 0,03 a 0,05).
- Comparando hombres y mujeres con la **misma saturación absoluta**, las mujeres siguen esperando de 2 a 8 horas más (por ejemplo, con 1,5 a 2 pacientes por camilla: 24,1 h frente a 17,2 h; con 2,0 a 2,5: 27,4 h frente a 19,2 h).
- **No es por obstetricia:** las mujeres cuyo diagnóstico no es embarazo ni ginecología esperan 27,9 h (frente a 16,0 h de los hombres); con embarazo o ginecología, 18,4 h.
- Las mujeres ocupan más camas de adultos que los hombres (53 frente a 36 de media en 2025).

## Conclusión (con honestidad)
- La hipótesis «las mujeres esperan más porque su zona está más saturada **en ese momento**» **no se sostiene**. La hipótesis «hay una limitación estructural y permanente (menos camas o camillas para mujeres en relación con su demanda)» **no se puede probar ni descartar**: es coherente con que su razón de pacientes por camilla es siempre más alta, pero no hay datos de camas por sexo. Hay que seguir tratándola como **hallazgo abierto**.
- Para el modelo de camas conviene separar adultos y niños: el problema de capacidad es de adultos.

## Límites
Los grupos son aproximaciones por edad y sexo (no hay servicio, piso ni cama; un adulto puede estar en UCI o intermedio, un niño de 12 años en adultos); las camas del HUN no se reparten por sexo (solo las camillas) y su lista no trae fecha; la ocupación de urgencias es una cota inferior; todo son asociaciones.
