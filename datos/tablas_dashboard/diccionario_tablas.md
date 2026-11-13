# Diccionario de tablas de datos del dashboard (23-oct-2026)

Describe las columnas de las tablas que alimentan el dashboard en Dash y las recomendaciones (`../../docs/pendientes_y_reparto.md`). Todos los nombres de columna están en minúsculas, sin `%`, paréntesis ni espacios (`WAPE_%` pasó a `wape_pct`).
Las columnas `*_pct` están en escala 0 a 100. Las duraciones están en **horas** salvo que el nombre diga días.

## Tablas de datos del dashboard

| Archivo | Grano (una fila es...) | Filas | Columnas clave |
|---|---|---|---|
| `bi_estancias.csv` | una **estancia en cama**, sin ids ni fecha exacta | 25.777 | `anio`, `mes`, `anio_mes`, `dia_semana_num`, `dia_semana`, `hora_llegada`, `franja`, `grupo_edad`, `sexo`, `tipo_visita`, `espera_h`, `hueco_h`, `urgencias_antes_h`, `estancia_h`, `hora_ingreso_cama`, `hora_alta`, `espera_mas_24h`, `espera_mas_48h`, `sin_espera_medida`, `periodo_caida_de_datos` |
| `bi_llegadas.csv` | una combinación de año, día, hora, tipo de visita y edad | ~19 mil | `anio`, `dia_semana_num`, `dia_semana`, `hora`, `tipo_visita`, `grupo_edad`, `llegadas`, `llegadas_con_atencion`, `hospitalizados_unicos` |
| `bi_calendario.csv` | una fecha (2023-01-01 a 2026-07-31) | 1.308 | `fecha`, `anio`, `mes`, `nombre_mes`, `anio_mes`, `dia_semana_num`, `dia_semana`, `es_fin_de_semana`, `festivo`, `semana_santa`, `carnaval`, `fin_anio_24_31_dic`, `fin_anio_25_dic_1_ene`, `periodo_caida_de_datos` |
| `bi_escenario_altas.csv` | un % de altas adelantadas (0 a 100, de 5 en 5) | 21 | `proporcion_pct`, `altas_movidas_por_dia`, `horas_cama_liberadas_por_dia`, `cota_pct_del_exceso`, `estimacion_pct_del_exceso`, `estimacion_pct_de_la_espera` |
| `bi_escenario_camas_hora.csv` | una hora del día | 24 | `hora`, `ocupacion_base`, `camas_libres_100pct` (multiplicar por la proporción elegida: 0 a 1) |
| `dim_hora.csv`, `dim_dia_semana.csv`, `dim_edad.csv`, `dim_tipo_visita.csv` | valores de cada dimensión con su orden | 24, 7, 8, 4 | `hora`/`etiqueta`/`franja`/`orden_franja`; `dia_semana_num`/`dia_semana`/`tipo_dia`; `grupo_edad`/`orden`; `tipo_visita`/`orden` |
| `cifras_de_control.csv` | una cifra de control | 20 | `cifra`, `valor`, `esperado`, `tolerancia`, `ok` |

**Cosas que hay que saber de `bi_estancias`:**
- `espera_h` está vacía en 794 estancias (779 con hospitalización directa: la primera etapa ya era cama). Los percentiles de Power BI ignoran los vacíos.
- `estancia_h` y `hora_alta` solo existen si el alta es posterior a la extracción de datos (`alta_completa`).
- `urgencias_antes_h` + `hueco_h` = `espera_h`. Urgencias mezcla atención y espera de cama: no se pueden separar con los datos.
- `periodo_caida_de_datos = 1` marca llegadas desde el 1-may-2026 (el registro de etapas está degradado desde el 10-abr-2026, no es menos demanda; la marca no se movió para no cambiar el paquete). Las cifras de control incluyen esas filas; sin ellas la
  espera mediana es 18,5 h y el percentil 90 es 72,6 h. Los documentos del proyecto citan 18,6 y 73,9 (`construir_segmentos.py`, con los episodios de Q3); este paquete da 18,8 y 73,3 (pipeline), una diferencia de décimas.
- Filas mezcladas al azar para que no sigan el orden de llegada. Es información sensible: ver `../docs/hun/sesion_de_preguntas.md` (D2 y D3) antes de publicarla.
- `grupo_edad = "sin dato"` solo aparece en `bi_llegadas` (21 episodios con edad imposible).

## Tablas que ya existían (copiadas con columnas limpias)

| Archivo | Qué contiene | Filas |
|---|---|---|
| `panel_diario.csv` | un día (feb-2023 a may-2026): `llegadas`, `hospitalizados`, `ingresos_a_cama`, `altas`, `altas_antes_mediodia`, `ocup_hosp_media`, `ocup_hosp_max`, `espera_cama_mediana_h`, `n_espera`, `festivo`, `dia_no_habil` | 1.216 |
| `serie_horaria.csv` | una hora: `hora_inicio`, `llegadas`, `llegadas_que_se_hospitalizan`, `ocup_hosp`, `ocup_tu`, `ocupacion_confiable` (usar solo `True` para ocupación) | 31.052 |
| `serie_diaria.csv` | una fecha hasta julio 2026 con llegadas y ocupación | 1.294 |
| `ranking_cuellos.csv` | exceso de espera por `segmento` y `referencia` (a20, a10, b25, b10): `horas_totales`, `exceso_total_h`, `exceso_medio_h`, `pct_exceso_mas_24h` | 12 |
| `exceso_por_anio.csv`, `exceso_por_franja.csv` | exceso y mediana por año o por franja de llegada (referencias a20 y b25) | 24 c/u |
| `inventario_segmentos.csv` | n, % medido y percentiles de cada segmento | 6 |
| `descomposicion_espera.csv` | horas de urgencias y de hueco como % de la espera de cama | 3 |
| `urgencias_antes_cama_por_anio.csv` | p50, p75 y p90 por año (urgencias antes de la cama y espera) | 8 |
| `carga_por_decil.csv` | espera por decil de carga (`carga` = llegadas 6 h, 24 h, pacientes en cama o en TU) | 120 |
| `carga_efectos.csv`, `hora_efectos.csv` | efecto de la carga y de la franja de llegada (% de cambio) | 12, 18 |
| `hora_llegada.csv` | mediana y p90 de la espera por hora de llegada | 24 |
| `asignacion_cama_por_hora_llegada.csv` | por hora de llegada: `pct_cama_el_mismo_dia`, `pct_cama_dia_siguiente_o_mas`, `espera_p50_h`, `hora_asignacion_mediana` | 24 |
| `altas_ingresos_llegadas_por_hora.csv` | `altas_pct`, `ingresos_cama_pct`, `llegadas_pct` por hora | 24 |
| `acople_altas_ingresos.csv` | ingresos a cama que siguen a una alta extra, por retraso en horas | 7 |
| `importancia_factores.csv`, `coeficientes_espera_cama.csv` | qué explica la espera (R²) y el efecto de cada nivel (%); **explican solo el 16 %** | 8, 29 |
| `sesgo_medicion_urgencias.csv` | quién tiene duración medida en urgencias sin hospitalizar | 22 |
| `ocupacion_por_anio.csv` | `ingresos_por_dia`, `estancia_media_dias`, `ocupacion_media` e índices (2023 = 100) | 4 |
| `escenarios_little.csv`, `escenario_altas_antes.csv` | escenarios de camas (ley de Little) y de altas adelantadas (5 puntos) | 5, 5 |
| `tendencia_mensual.csv` | llegadas e ingresos por día, promedio mensual (`fecha` es texto "2023-03") | 40 |
| `pronostico_diario_test.csv` | por día (ene–may 2026): `*_real`, `*_pronostico_h1` y `_h7`, `*_banda_baja_*`, `*_banda_alta_*` (llegadas e ingresos) | 151 |
| `pronostico_metricas.csv`, `pronostico_semanal_metricas.csv`, `pronostico_horario_metricas.csv` | error de cada método (columnas `mae`, `wape_pct`, `sesgo_pct`, `elegido_en_validacion`) | 28, 2, 4 |
| `alertas_congestion.csv`, `alertas_camas.csv`, `alertas_camas_dias.csv`, `alertas_paciente.csv`, `alertas_carga_diaria.csv` | resultados de las alertas A, B y C | 4, 2, 120, 5, 4 |
| `dias_atipicos.csv`, `dias_atipicos_resumen.csv` | días fuera del patrón (`variable`, `real`, `esperado`, `z`, `causa_calendario`) y su resumen | 30, 3 |
| `cobertura_por_ruta.csv`, `resumen_por_ruta.csv` | rutas de los episodios, `total`, `pct_medida` y percentiles de duración (`confiable`) | 36, 28 |

## Tablas agregadas de las páginas de contexto y resultados (13-nov-2026)

Las genera `python dashboard/preparar_datos.py` en `datos/procesados/dashboard/` (fuera de git; ~2 min). Ninguna tiene una fila por paciente y
los grupos con menos de 30 estancias salen vacíos. Periodo: 1-feb-2023 a 9-abr-2026. Si falta alguna, su página muestra un aviso en vez de fallar.

| Archivo | Grano (una fila es...) | Filas | Columnas | Página |
|---|---|---|---|---|
| `espera_cubo.csv` | año × tipo de visita × grupo de edad (cada uno con «Todos») | 80 | `n`, `mediana`, `p25`, `p75`, `p90`, `pct_24`, `pct_48`, `tramo_0` a `tramo_6` (% en 0–6, 6–12, 12–24, 24–48, 48–72, 72–120 y > 120 h) | `/espera` |
| `espera_por_mes.csv` | un mes de llegada | 39 | `mes`, `n`, `mediana`, `p90` | `/espera` |
| `espera_por_hora.csv` | año × hora de llegada | 116 | `hora`, `n`, `mediana`, `p90`, `anio` | `/altas` |
| `camas_por_hora.csv` | año × hora del día | 120 | `pct_ingresos_a_cama`, `pct_altas` (% del total del día), `n_ingresos`, `n_altas` | `/altas` |
| `llegadas_calor.csv` | un día de la semana (columnas `0` a `23`: llegadas promedio en esa hora) | 7 | `dia`, `0` … `23` | `/demanda` |
| `panel_diario.csv` | un día (copia del panel diario) | 1.164 | `llegadas`, `ingresos_a_cama`, `altas`, `ocup_hosp_media`, `dia_semana_num`, … | `/demanda`, `/ocupacion` |
| `estacionalidad_efecto.csv` | serie × día de un año típico | 730 | `objetivo`, `dia_del_anio`, `mes`, `dia`, `efecto_pct` (cuánto sube o baja el pronóstico frente al promedio del año) | `/estacionalidad` |
| `estacionalidad_error.csv` | serie × horizonte | 10 | `objetivo`, `tramo_dias`, `wape_con`, `wape_sin` (error del backtest con y sin la forma del año), `orden` | `/estacionalidad` |

## Tablas que se escriben a mano (en esta carpeta del repo)
- `embudo_datos.csv`: de 3,28 M de etapas a 337 mil episodios (página 10).
- `recomendaciones_tabla.csv`: las 7 recomendaciones (página `/recomendaciones` del dashboard). Actualizada el 13-nov con `../../docs/recomendaciones.md` (35 fuentes verificadas; todas con firmeza media o alta). Columnas: `prioridad`, `recomendacion`, `impacto_estimado` (lo que dicen nuestros datos), `evidencia_externa`, `firmeza`, `limite`, `como_medir` (nueva), `fuente_datos`, `estado`. Tabla escrita a mano, sin datos por paciente.

## Tablas que faltan (dependen de análisis pendientes)
Perfiles de pacientes (A1), factores de la estancia y estancias que se disparan (A2, A2b), modelo explicativo mejorado (A4) y bandas Monte Carlo de camas (A5). Cada una se agregará al paquete
con su propio script; el diccionario se actualiza entonces.
