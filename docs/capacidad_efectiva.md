# Exploración 2 · ¿Se puede sacar la capacidad de camas de los propios datos? (4-nov-2026)

Código: `src/capacidad_efectiva.py`. Tablas (fuera de git): `resultados/tablas/capacidad_efectiva_*.csv`. Gráfico: `resultados/graficos/capacidad_efectiva.png`.

**Idea:** si hay una cola de pacientes esperando cama, las camas están llenas; en esas horas la ocupación debería acercarse a la capacidad real de operación. Se calcula hora por hora la ocupación (O, estancias únicas) y la **cola** (Q: pacientes que ya llegaron, se hospitalizarán y aún no tienen cama; desde el inicio del episodio hasta el inicio de la cama) y se busca una «rodilla»: un nivel de O donde Q despega.

## Resultado: el método no identifica un techo, y eso también es un hallazgo
- **La cola nunca es cero:** en las 27.936 horas del periodo hay siempre pacientes en espera (media 26, percentil 90 de 34, 0 % de horas sin cola). Es lo esperable por la ley de Little: ~20 ingresos por día × ~29 h de espera media ≈ 24–26 pacientes en cola permanente.
- **La cola no depende de la ocupación:** la pendiente es de 0,06 pacientes en cola por cada cama ocupada adicional y la correlación entre O y Q por año va de −0,16 a 0,01. No hay rodilla: con 80–90 camas ocupadas la cola es igual que con 110–115.
- **Lectura:** la espera típica no se mueve con cuán llenas estén las camas en ese momento. Se confirma lo ya visto (la ocupación pesa poco en la espera; `docs/CONTEXTO_TECNICO.md` 6b) y apoya que la espera sea de **proceso** (hora de las altas, asignación de camas por la tarde) más que de un conteo de camas.
- **Un dato que sí se mueve:** con la cola presente, la ocupación mediana sube cada año: ~95 camas (2023), ~101–102 (2024), ~105–106 (2025). Mientras tanto la **mediana de la espera casi no cambia** (19,5 → 18,3 → 17,4 h) aunque la ocupación sube ~11 camas, y solo el percentil 90 empeora. Es decir, tener 11 camas más ocupadas no alargó la espera típica.

## Qué se puede y qué no decir
- **No se puede** estimar la capacidad real a partir de la cola (no hay horas sin cola con las que comparar).
- **Se puede decir** que la ocupación media de 2025 (~105) coincide con las 106 camas que dio el HUN, que la ocupación media de 2023 era ~94 con una cola igual de larga, y que la mediana de la espera no cambió mientras la ocupación crecía. Eso es coherente tanto con una capacidad real que creció como con camas adicionales usadas desde 2024; **los datos no distinguen entre ambas**.
- La cola es una cota inferior (solo cuenta a quienes luego se hospitalizan) y empieza en la llegada, no en la solicitud de cama: una parte es atención clínica en urgencias, no espera de cama.

## Para el modelo de camas
No usar la ocupación como medida de saturación de la espera; usar la hora de las altas y de la asignación de cama. Sigue siendo válido comparar la ocupación con las 106 camas como referencia, con la nota de que su fecha no se conoce.
