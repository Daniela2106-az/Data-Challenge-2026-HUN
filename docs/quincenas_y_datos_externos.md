# Datos externos para el pronóstico: quincenas, dengue y lluvia (A8 punto 8, 8-nov-2026)

Script de las quincenas: `src/prueba_quincenas.py` (tabla `resultados/tablas/prueba_quincenas.csv`, fuera de git).

## Quincenas (días de pago): no mejoran el pronóstico
Se agregó al calendario de `modelo_pronostico.py` una variable `quincena` (días 15, 16, 30, 31 y 1) y otra `fin_mes` (días 29 a 31), y se repitió el mismo retroceso (backtest) de `elegir_tau.py`. Error WAPE (%):

| Serie | Calendario | Validación 1-7 d | Validación 8-30 d | Prueba 1-7 d | Prueba 8-30 d |
|---|---|---|---|---|---|
| Llegadas | base | 7,20 | 7,72 | 6,55 | 7,65 |
| Llegadas | + quincena | 7,16 | 7,73 | 6,70 | 7,60 |
| Llegadas con atención | base | 7,92 | 8,29 | 7,40 | 7,85 |
| Llegadas con atención | + quincena | 7,91 | 8,30 | 7,43 | 7,85 |
| Ingresos a cama | base | 18,01 | 19,19 | 16,29 | 20,43 |
| Ingresos a cama | + quincena | 17,95 | 19,19 | 16,27 | 20,35 |

Las diferencias son de 0,15 puntos o menos y van en ambos sentidos. Los residuos del modelo base por día del mes son de ±2 a 3 % (con ~40 observaciones por día), que es el ruido esperable; los días 29 y 30 salen algo más bajos (−2,5 y −3,2 % en llegadas) sin ser un patrón de pago claro. **Decisión: no se agregan al modelo.** No se probó la prima de junio y diciembre (diciembre ya está modelado).

## Dengue y lluvia: no hay datos abiertos que cubran 2023–2026
- Dengue en Barranquilla: la serie abierta que se encontró (SIVIGILA, 2007–2022) termina antes de que empiecen nuestros datos (feb-2023). Lo posterior solo está en boletines semanales del INS en PDF, provisionales y que se revisan después.
- Lluvia: la serie semanal de IDEAM para Barranquilla que se encontró cubre 2000–2022. Lo posterior son boletines diarios en PDF con muchos valores no disponibles.
- **Decisión: se descartan.** Armarlas a mano desde PDF costaría más que lo que aportarían, y el efecto esperable sobre las llegadas diarias de un hospital es pequeño frente al ruido de conteo. Queda como trabajo futuro si el HUN entrega series propias.
