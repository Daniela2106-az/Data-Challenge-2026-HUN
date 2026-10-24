# Medidas DAX (versión parcial, 23-oct-2026)

Nombres exactos de tablas y columnas del paquete (`diccionario_tablas.md`). Crear una tabla vacía `Medidas` y guardar ahí todas. Si Power BI pide otro separador de argumentos
(`;` en vez de `,` según la configuración regional), cámbialo; si una función no existe en la versión de Samuel, pedir a Claude una alternativa y comprobarla con las cifras de control.

## Relaciones (modelo en estrella)
- `bi_calendario[fecha]` (1) → `panel_diario[fecha]`, `pronostico_diario_test[fecha]`, `serie_diaria[fecha]` (varios). Marcar `bi_calendario` como tabla de fechas.
- `bi_estancias` solo tiene año/mes: relacionar por `anio_mes` con una columna `anio_mes` en una tabla de meses (o usar `bi_estancias[anio]` y `[mes]` como texto de eje sin relación).
- `dim_hora[hora]` → `bi_estancias[hora_llegada]`, `bi_llegadas[hora]`. `dim_dia_semana[dia_semana_num]` → ambas. `dim_edad[grupo_edad]` → ambas. `dim_tipo_visita[tipo_visita]` → ambas.
- Filtro en una sola dirección. Las tablas de resultados sueltas (ranking, escenarios, alertas) no se relacionan.
- `fecha` en `tendencia_mensual` es texto "2023-03": convertir si se usa en eje.

## Estancias y espera
```DAX
Estancias = COUNTROWS ( bi_estancias )
Estancias con espera medida = COUNTROWS ( FILTER ( bi_estancias, NOT ISBLANK ( bi_estancias[espera_h] ) ) )
Espera mediana h = MEDIAN ( bi_estancias[espera_h] )
Espera p75 h = PERCENTILE.INC ( bi_estancias[espera_h], 0.75 )
Espera p90 h = PERCENTILE.INC ( bi_estancias[espera_h], 0.9 )
% espera > 24 h = DIVIDE ( COUNTROWS ( FILTER ( bi_estancias, bi_estancias[espera_h] > 24 ) ), [Estancias con espera medida] )
% espera > 48 h = DIVIDE ( COUNTROWS ( FILTER ( bi_estancias, bi_estancias[espera_h] > 48 ) ), [Estancias con espera medida] )
Horas urgencias = SUM ( bi_estancias[urgencias_antes_h] )
Horas hueco = SUM ( bi_estancias[hueco_h] )
% horas urgencias = DIVIDE ( [Horas urgencias], [Horas urgencias] + [Horas hueco] )
Estancia mediana h = MEDIAN ( bi_estancias[estancia_h] )
Espera mediana h (n>=30) = IF ( [Estancias con espera medida] >= 30, [Espera mediana h], BLANK () )
Espera p90 h (n>=30) = IF ( [Estancias con espera medida] >= 30, [Espera p90 h], BLANK () )
```
Controles (todo el periodo, sin filtros): estancias 27.956; mediana 18,0; p75 37,2; p90 71,5; >24 h 42,7 %; >48 h 19 %; urgencias 77 %. (Valores ligeramente distintos entre Q3 y pipeline: ver `cifras_de_control.csv`.)

## Demanda y camas
```DAX
Llegadas = SUM ( bi_llegadas[llegadas] )
Llegadas por día = DIVIDE ( SUM ( panel_diario[llegadas] ), COUNTROWS ( panel_diario ) )
Ingresos por día = DIVIDE ( SUM ( panel_diario[ingresos_a_cama] ), COUNTROWS ( panel_diario ) )
Camas ocupadas = AVERAGE ( panel_diario[ocup_hosp_media] )
Estancia media días = AVERAGE ( ocupacion_por_anio[estancia_media_dias] )
```
Ojo: `panel_diario` cubre feb-2023 a may-2026; las cifras de `ocupacion_por_anio` son por año completo.

## Simulador (página 7)
Crear tres parámetros con *Modelado → Nuevo parámetro → Rango numérico* (genera tabla y medida `Valor`):
- `Delta ingresos` (−0,20 a 0,20, paso 0,01, valor 0), `Delta estancia` (−0,20 a 0,10, paso 0,01, valor 0), `Proporcion altas` (0 a 100, paso 5, valor 0; coincide con `bi_escenario_altas[proporcion_pct]`).
```DAX
Ingresos base = 21.7        -- escenarios_little, fila "hoy (2025)"
Estancia base = 5.46
Camas base = [Ingresos base] * [Estancia base]   -- 118,5 (la tabla dice 118,6 por redondeo)
Camas ocupadas escenario = [Camas base] * ( 1 + [Delta ingresos Valor] ) * ( 1 + [Delta estancia Valor] )
Diferencia de camas = [Camas ocupadas escenario] - [Camas base]
Camas libres a las 12 h =
    VAR p = [Proporcion altas Valor] / 100
    RETURN p * LOOKUPVALUE ( bi_escenario_camas_hora[camas_libres_100pct], bi_escenario_camas_hora[hora], 12 )
Espera evitada cota % =
    LOOKUPVALUE ( bi_escenario_altas[cota_pct_del_exceso], bi_escenario_altas[proporcion_pct], [Proporcion altas Valor] )
Espera evitada estimación % =
    LOOKUPVALUE ( bi_escenario_altas[estimacion_pct_del_exceso], bi_escenario_altas[proporcion_pct], [Proporcion altas Valor] )
```
Los nombres `[Delta ingresos Valor]` dependen de cómo Power BI nombre la medida generada: ajustar. Cuidado: con `Proporcion altas` = 30 deben salir 5,5 camas libres y 8,3 % / 2,9 %. Hay que decir en pantalla: «escenario, no predicción; la estimación supone que el efecto en la espera es una fracción de la cota».
Más adelante, A5 (Anthony) aportará bandas Monte Carlo: **Pendiente**.

## Pronóstico
```DAX
Llegadas real = SUM ( pronostico_diario_test[llegadas_real] )
Llegadas pronóstico = SUM ( pronostico_diario_test[llegadas_pronostico_h1] )
Banda base = SUM ( pronostico_diario_test[llegadas_banda_baja_h1] )
Banda ancho = SUM ( pronostico_diario_test[llegadas_banda_alta_h1] ) - SUM ( pronostico_diario_test[llegadas_banda_baja_h1] )
```
Truco de la banda: gráfico de áreas apiladas con `Banda base` (sin relleno) y `Banda ancho` (relleno azul claro, transparencia), y encima las líneas real y pronóstico. Para el horizonte de 7 días crear un
*parámetro de campos* que cambie entre las columnas `_h1` y `_h7`. Error del pronóstico: leer `pronostico_metricas` filtrado por el método elegido (`elegido_en_validacion`), no recalcular.

## Calidad
```DAX
% con duración medida = DIVIDE ( SUM ( cobertura_por_ruta[medida] ), SUM ( cobertura_por_ruta[total] ) )
```
