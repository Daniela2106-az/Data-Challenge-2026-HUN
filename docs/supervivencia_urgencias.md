# Exploración 5 · Duración en urgencias con métodos de supervivencia (4-nov-2026)

Código: `src/supervivencia_urgencias.py`. Tablas (fuera de git): `resultados/tablas/supervivencia_urgencias_*.csv`. Gráfico: `resultados/graficos/supervivencia_urgencias.png`.

**Problema:** de los 218.468 episodios de urgencias que no se hospitalizan (con alguna etapa TU, 1-feb-2023 a 9-abr-2026), solo el 38,1 % tiene hora de salida (`medida`). El 11,4 % tiene etapas con tiempo pero la última sin cierre (`minimo_conocido`: la duración es **al menos** lo observado) y el 50,5 % no tiene ningún tiempo en urgencias (la etapa tiene inicio = fin). Mirar solo los `medida` sesga hacia abajo.

**Qué se hizo:** Kaplan-Meier (estimador de supervivencia que usa a los censurados), con los `medida` como evento y los `minimo_conocido` como censurados en lo observado; una versión ponderada por la probabilidad de tener información; y cotas extremas.

## Resultados

| Método | Mediana (h) | p75 (h) | p90 (h) | n |
|---|---|---|---|---|
| Ingenua: solo `medida` | 9,6 | 17,0 | 45,2 | 83.258 |
| Kaplan-Meier (`medida` + `minimo_conocido`) | **11,2** | 27,1 | **80,6** | 108.079 |
| Kaplan-Meier ponderado por la probabilidad de tener información | 10,5 | 22,7 | 70,7 | 108.079 |
| Cota baja (los 110 mil sin información duraron 0 h) | 0 | 11,1 | 37,4 | 218.468 |
| Cota alta (los sin información duraron 24 h) | 24 | 24 | 27,1 | 218.468 |

1. **Quedarse con los `medida` subestima la duración:** la mediana pasa de 9,6 a 10,5–11,2 h (+10 a +17 %) y el **percentil 90 de 45 a 71–81 h** (+57 a +78 %). Los que se quedan mucho tiempo son justo los que no tienen cierre. Esto corrige lo que hasta ahora se reportaba para urgencias sin hospitalización.
2. **Tener información no es al azar** (AUC 0,70): se asocia sobre todo con tener laboratorios (87 % frente a 41 %), con las visitas de tipo «Treatment urgency» (71 % frente a 49 % de urgencias normales) y con la edad (60 % en 75 años o más frente a 39 % en 0–4). No depende del año (47–51 %) ni de la franja horaria. Ponderar por estas variables baja un poco el resultado (11,2 → 10,5 h; p90 81 → 71 h).
3. **Por grupo, el patrón no cambia:** la corrección sube la mediana 1 a 2,5 h en casi todos los grupos; las visitas «Treatment urgency» (47 h) siguen siendo un flujo aparte.

## Lo que NO resuelve (corrección a lo que se dijo antes)
- **Los 110 mil episodios sin ningún tiempo en urgencias siguen sin información.** Ningún método la inventa: las cotas van de 0 h a 24 h de mediana, es decir, **no se puede estimar la duración de todos los pacientes que se van de urgencias**. Lo que se corrige es el sesgo dentro del grupo con información, no la falta del resto.
- La ponderación solo corrige diferencias visibles en las variables observadas. Si el hecho de no tener cierre depende de cuánto duró el paciente, el sesgo sigue. Además, los laboratorios son a la vez causa y consecuencia de una estancia larga en urgencias.
- Kaplan-Meier supone que la censura es independiente del tiempo. Aquí los `minimo_conocido` no son censura administrativa por el corte de la extracción (ocurren todos los años), así que el supuesto es discutible.

## Qué cambia para el proyecto
- La duración en urgencias sin hospitalización debe reportarse como **«entre quienes tienen hora de salida o un mínimo conocido»**, con Kaplan-Meier (mediana ~11 h, p90 ~71–81 h) y no con la mediana de los `medida`.
- Para A6 (estimar tiempos de atención): sirve como **rango por perfil y hora** con percentiles de Kaplan-Meier para quienes tienen información, y debe decir siempre que la mitad de los pacientes no tiene tiempo registrado.
- No modifica la espera de cama (100 % medida en los hospitalizados).
