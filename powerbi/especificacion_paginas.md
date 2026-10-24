# Especificación de páginas (versión parcial, 23-oct-2026)

Cada página: **mensaje (título)**, pregunta, **estado de datos**, visuales con los campos exactos del paquete (`diccionario_tablas.md`), segmentadores, interacciones y nota fija.
Medidas en `medidas_dax.md` (entre corchetes, p. ej. `[Espera mediana h]`). Estado: **LISTO** = se puede construir hoy; **PARCIAL** = se construye pero falta una parte; **ESPERA** = dejar marcador "Pendiente: ..." y no inventar.
**Power BI va de último:** empezar solo cuando los análisis A1, A2, A2b, A4, A5 y B2 estén entregados (ver `roadmap_powerbi.md`). Las páginas LISTO se pueden ir armando antes si Samuel tiene tiempo.

Reglas comunes: segmentadores sincronizados (Año, Tipo de visita, Grupo de edad) con botón "Restablecer"; mostrar `[Estancias]` (n) junto a toda mediana o percentil; ocultar grupos con n < 30;
título = conclusión; tema `tema.json`; azul = espera, naranja = referencia o escenario.

## Página 1 — «La espera de cama es larga y se alarga» — LISTO
- Pregunta: ¿cómo está el hospital?
- Tarjetas: `[Espera mediana h]` (18,0), `[Espera p90 h]` (71,5), `[% espera > 48 h]` (19 %), `[Ingresos por día]` (~22), `[Camas ocupadas]` (~113), `[Estancia media días]`.
- Gráfico de líneas: eje `bi_estancias[anio_mes]`, valores `[Espera mediana h]` y `[Espera p90 h]` (la mediana plana, el p90 sube de 61 a 80 h). Marcar el tramo `periodo_caida_de_datos = 1` en gris.
- Segmentador: Año. Nota fija: «Desde mayo 2026 las llegadas bajan 25–35 %: posible carga incompleta».

## Página 2 — «Cuándo llega la gente» — LISTO
- Matriz (mapa de calor): filas `dim_dia_semana[dia_semana]` (ordenar por `dia_semana_num`), columnas `dim_hora[hora]`, valor `[Llegadas por día]` (o suma de `bi_llegadas[llegadas]`), formato condicional de color.
- Serie diaria: eje `bi_calendario[fecha]`, valor `serie_diaria` llegadas; marcar `festivo`, `carnaval`, `semana_santa` con marcadores.
- Segmentadores: Año, Tipo de visita, Grupo de edad. Mensaje de apoyo: pico 9–11 h, lunes el día más cargado, fin de semana ~30 % menos, Carnaval ~−17 %.

## Página 3 — «Qué ruta sigue el paciente y cuánto dura» — PARCIAL
- Tabla/barras: `cobertura_por_ruta` (`ruta_simple`, `total`, `pct_medida`) y `resumen_por_ruta` (`n`, `p25_h`, `mediana_h`, `p75_h`, `p90_h`; usar solo `confiable = True`).
- Siempre mostrar **% con duración medida**: solo ~38 % de los pacientes de alta desde urgencias tiene hora de salida; no comparar rutas sin decirlo.
- PARCIAL porque la ruta no se puede filtrar por año/edad (las tablas ya vienen agregadas). Perfiles por ruta llegan con A1.

## Página 4 — «Quién espera más y cuándo» — LISTO (la parte explicativa mejora con A4)
- Histograma: tramos de `bi_estancias[espera_h]` (0–6, 6–12, 12–24, 24–48, 48–72, >72) con `[Estancias]`.
- Líneas/columnas: por `bi_estancias[hora_llegada]` `[Espera mediana h]` y `[Espera p90 h]`; segunda vista `asignacion_cama_por_hora_llegada[pct_cama_dia_siguiente_o_mas]` (tarde ≈ la mitad recibe cama al día siguiente).
- Barras: por `grupo_edad` y `tipo_visita`. Apiladas: `[Horas urgencias]` vs `[Horas hueco]` (77 % / 23 %).
- Barras horizontales: `importancia_factores[perdida_r2_si_se_quita]` por `factor`. **Nota fija obligatoria:** «Asociación, no causa. Los factores explican solo el 12 % de la variación».
- A4 (Anthony) puede reemplazar el modelo explicativo: ESPERA, no inventar.

## Página 5 — «Las altas tardías y la estancia sostienen el cuello de botella» — LISTO
- Líneas por hora: `altas_ingresos_llegadas_por_hora[altas_pct]`, `[ingresos_cama_pct]`, `[llegadas_pct]` (61,5 % de las altas entre 14 y 19 h; 15 % antes de las 12).
- Línea: `bi_escenario_camas_hora[ocupacion_base]` por hora.
- Barras por año: `ocupacion_por_anio` (`ingresos_por_dia` plano, `estancia_media_dias` 4,70→5,46, `ocupacion_media` 105→119). Mensaje: la ocupación sube por la estancia (+16 %), no por los ingresos.
- Nota: el orden de llegada no se respeta (solo 53 % se atiende en orden).

## Página 6 — «Se puede anticipar y avisar» — LISTO
- Real vs pronóstico: eje `pronostico_diario_test[fecha]`, `llegadas_real`, `llegadas_pronostico_h1` (o `_h7` con parámetro de campos) y banda `llegadas_banda_baja_*`/`llegadas_banda_alta_*` (usar el truco de área apilada, ver DAX). Tarjetas: error 7,5 % (1 d) y 8,8 % (7 d) de `pronostico_metricas`.
- Ingresos: mostrar el pronóstico **semanal** (`pronostico_semanal_metricas`, error 9,5 %); el diario es ruido (~23 %). No venderlo como bueno.
- Tabla de alertas con formato condicional: `alertas_congestion`, `alertas_camas`, `alertas_paciente` (precisión, detección, alertas por día; total ~4,9/día).
- Tabla `dias_atipicos` (14 llegadas / 9 ingresos / 7 espera) con drill-through. Nota: «Prueba ene–abr 2026; mayo cae por posible carga incompleta».

## Página 7 — «Simulador de camas: ¿qué pasa si...?» — PARCIAL (falta Monte Carlo, A5)
- Parámetros what-if (ver DAX): ingresos −20…+20 %, estancia −20…+10 %, % de altas de la tarde adelantadas 0…100 %.
- Tarjetas: `[Camas ocupadas escenario]`, `[Diferencia de camas]`, `[Camas libres a las 12 h]`, `[Espera evitada cota %]`, `[Espera evitada estimación %]`.
- Control: con los deslizadores en base debe dar 118,6 camas; estancia −5 % → −5,9; ingresos +10 % → +11,9; 30 % de altas → 5,5 camas libres a las 12 h.
- Marcador: «Pendiente: bandas Monte Carlo (A5, Anthony)». Aclarar en pantalla que es un **escenario**, no una predicción.

## Página 8 — «Estimador de espera» (A6, Samuel) — ESPERA (diseño propio)
- Elegir hora de llegada, grupo de edad y tipo de visita; mostrar p25, mediana, p75, p90 con `[Estancias]`. Si n < 30 mostrar «datos insuficientes».
- Advertencia fija: «Rango típico de pacientes parecidos, no una predicción individual (el R² de los factores es 12 %)».
- Depende de la definición final de A6; construirla al final.

## Página 9 — «Qué se hace con esto» (recomendaciones) — ESPERA (B2)
- Tabla desde `recomendaciones_tabla.csv` (`prioridad`, recomendación, impacto estimado, límite, fuente, estado). Hoy es **borrador**; B2 la verifica contra `docs/recomendaciones.md` y la actualiza. No publicar impactos sin esa revisión.

## Página 10 — «Qué tan confiable es» (metodología y límites) — LISTO
- Embudo: `embudo_datos.csv` (3,28 M etapas → 337 mil episodios → 27.956 estancias únicas). Texto: copias (≈30 %), horas de salida faltantes, sin signos vitales, ocupación parcial, caída de datos desde mayo 2026. Fuente: `docs/HALLAZGOS.md` secciones 2 y 7.

## Página 11 — «Perfiles y estancias largas» — ESPERA (A1, A2, A2b)
- Solo un marcador: «Pendiente: perfiles (A1), factores de la estancia (A2) y estancias que se disparan (A2b)». No usar cifras provisionales.

## Orden de prioridad si falta tiempo
1, 4, 5, 7, 6, 2, 9, 3, 10, 8 (la 11 solo si existe A1/A2).
