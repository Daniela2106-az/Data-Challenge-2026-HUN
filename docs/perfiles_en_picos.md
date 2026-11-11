# Perfiles y picos de demanda (10-nov-2026)

**No es una ficha A# del reparto del equipo** (`docs/pendientes_y_reparto.md`): es una ampliación de A1 hecha
para el dashboard, que cruza perfil de paciente con momento de carga — algo que ni A1 ni los análisis nuevos de
Daniela (`docs/saturacion_y_espera.md`, `docs/pronostico_espera_sistema.md`, `docs/caracterizacion_tu.md`,
`docs/caracterizacion_etapas_tu.md`) hacían, porque A1 mide perfil sin condicionar por carga y los otros cuatro
miden carga a nivel de sistema o de grupo de duración, no por perfil demográfico.

Script: `src/perfiles_en_picos.py`. Tablas: `resultados/tablas/perfiles_en_picos_llegadas.csv`,
`perfiles_en_picos_ocupacion.csv`, `dias_alta_demanda.csv` (fuera de git). Mismas reglas de A1 (periodo
confiable 1-feb-2023 a 9-abr-2026, perfil = grupo_edad × sexo × tipo_visita, 42 perfiles, mínimos de 100
episodios con atención y 30 estancias, clasificación GRANDE/pequeña/ruido con intervalo de confianza del 95 %
y diferencia relativa de al menos 20 %).

## Por qué se esperaba un resultado débil (y no se forzó uno distinto)

Tres análisis independientes ya apuntaban a que el momento importa poco frente a quién es el paciente:
`docs/estimador_tiempos.md` 1.1 (el día de llegada explica 0,1 % de la espera individual más allá del azar),
`docs/pronostico_espera_sistema.md` camino 3 (la saturación real al llegar suma 3,7 puntos de R², frente a 7,0
de edad+sexo+tipo de visita) y `docs/saturacion_y_espera.md` (en adultos la cola de espera nunca está vacía:
0,0 % de las horas) — el sistema está saturado casi siempre, así que hay poco contraste real entre "pico" y
"no pico" con el que comparar.

## Resultado: ni nulo ni generalizado — concentrado en perfiles grandes y comunes

**Criterio 1 (llegadas en las 6 h previas, decil 10 contra el resto):** 6 de 42 perfiles con contraste GRANDE
en la espera, todos con más llegadas que lo normal = más espera, y todos perfiles de **Urgencias**, con
tamaño de muestra alto (84 a 269 estancias en el decil de pico):

| Perfil | Espera en pico | Espera en resto | Diferencia |
|---|---|---|---|
| 45-59, Hombre, Urgencias | 28,6 h | 21,1 h | +35 % |
| 30-44, Hombre, Urgencias | 29,6 h | 22,3 h | +33 % |
| 15-29, Mujer, Urgencias | 27,4 h | 19,9 h | +38 % |
| 60-74, Hombre, Urgencias | 27,7 h | 19,8 h | +40 % |
| 15-29, Hombre, Urgencias | 26,7 h | 15,4 h | +73 % |
| 5-14, Hombre, Urgencias | 23,6 h | 13,8 h | +71 % |

**Criterio 2 (ocupación del hospital al llegar, decil 10 contra el resto):** 4 de 42 perfiles con contraste
GRANDE, con el mismo patrón (adultos y niños de Urgencias esperan más si llegan con el hospital casi lleno:
60-74 y 75+ mujeres pasan de ~30 h a ~36 h; 75+ hombres de 14,4 h a 30,2 h).

**Lectura:**
- **No es un efecto nulo**, como sugerían los tres análisis previos a nivel de sistema o individual puro —
  pero tampoco es generalizado: solo 6 de 42 perfiles (14 %) muestran un contraste GRANDE en espera, y
  **ninguno de esos 6 perfiles está sobrerrepresentado en los picos** (`sobrerrepresentado_en_picos = False`
  en los seis). Es decir: estos perfiles no llegan más seguido en los picos, pero cuando sí llegan en un
  momento de carga alta, esperan sensiblemente más.
- El efecto se concentra en perfiles de **Urgencias** (nunca Treatment urgency ni Ambulatorio con suficientes
  datos para decidir) y en los perfiles más numerosos — es la combinación esperada: para detectar un
  contraste con el mínimo de 30 estancias por lado, se necesita un perfil con volumen suficiente en ambos
  grupos.
- La **estancia** casi no cambia con la carga (solo 1 de 42 perfiles con contraste GRANDE) — coherente con que
  la estancia depende del paciente y del proceso clínico, no del momento de llegada.
- Conclusión para el dashboard: el titular correcto no es "los picos son peores para todos" ni "la carga no
  importa" — es **"la carga alarga la espera en los perfiles de Urgencias más comunes (adultos, niños
  escolares), en 30-70 %, pero no cambia quién llega ni cuánto se queda en cama"**. Es un hallazgo más matizado
  que una confirmación limpia de cualquiera de las dos hipótesis extremas, y así se presenta.

## Lista de días de alta demanda (para la página del dashboard)

**Definición** (reutiliza la Alerta A de `src/alertas.py`): llegadas de ese día > percentil 90 del mismo día de
la semana en las 12 semanas anteriores. **199 de 1.164 días (17 %)** califican — no es un evento raro, es
alrededor de 1 de cada 6 días. Por eso se presenta como **lista**, no como marcadores aislados en un gráfico
(que sugerirían algo excepcional que no lo es).

**Advertencia que debe ir al lado de la lista, siempre, no en letra pequeña:** `docs/dias_atipicos.md` ya
probó que **ningún día tuvo una espera más alta de lo esperado** — el problema de la espera es crónico y de
cola larga, no de días puntuales. Esta lista dice únicamente "ese día llegaron más pacientes de lo normal para
ese día de la semana"; nunca debe presentarse como "día de cuello de botella" ni insinuar que la espera empeoró
ese día — el propio proyecto ya midió que no es así.

## Límites
- Los dos criterios de carga (llegadas 6h, ocupación) son los mismos de `src/dependencia_carga.py`; no se
  inventó un umbral nuevo.
- La clasificación GRANDE/pequeña/ruido depende de tener ≥ 30 estancias en el decil de pico Y en el resto; por
  eso Treatment urgency y Ambulatorio casi no aparecen con veredicto (quedan en "sin datos suficientes").
- Asociación, no causa; mismo límite que el resto del proyecto.

## Entregables
`src/perfiles_en_picos.py`, este documento, `resultados/tablas/perfiles_en_picos_llegadas.csv`,
`perfiles_en_picos_ocupacion.csv`, `dias_alta_demanda.csv`. Página del dashboard: `dashboard/perfiles.py`.
