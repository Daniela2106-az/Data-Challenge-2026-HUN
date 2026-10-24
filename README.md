# Data Challenge HUN 2026: flujo de pacientes y cuellos de botella

Proyecto del **Data Challenge HUN 2026** (Hospital Universidad del Norte + pregrado de Ciencia de Datos, Uninorte). La pregunta central:
*comprender, predecir y optimizar el flujo de pacientes dentro del hospital, identificando cuellos de botella, patrones operacionales y
oportunidades de mejora en los tiempos de atención.* Entregables: documentación, este repositorio y un dashboard de Power BI.

## Empieza aquí

**Si vas a usar Claude Code en la terminal** (la forma más rápida de entender el proyecto):

```bash
git clone https://github.com/Daniela2106-az/Data-Challenge-2026-HUN.git
cd Data-Challenge-2026-HUN
claude
```

Claude Code lee `CLAUDE.md` solo al abrir la carpeta. Ese archivo le dice en qué orden leer los documentos y cómo contestar. Ejemplos de
preguntas que puedes hacerle:

- "Resúmeme los hallazgos del proyecto en 5 puntos."
- "¿Cuál es el principal cuello de botella y cómo se midió?"
- "¿Por qué se descartaron estancias como duplicadas?"
- "¿Adelantar las altas antes del mediodía resolvería la espera? ¿Cuánto?"
- "¿Qué alertas se proponen y qué tan confiables son?"
- "¿Qué falta por hacer y quién lo tiene?"
- "¿Qué limitaciones tienen los datos?"

**Si prefieres leer tú:** [`docs/HALLAZGOS.md`](docs/HALLAZGOS.md) (todo con cifras y fuentes, glosario y preguntas frecuentes).

> **Importante:** los **datos clínicos no están en el repositorio** (ni las tablas de resultados). Hay código, consultas SQL, documentos y gráficos.
> Un Claude o una persona que abra el repo puede contestar desde los documentos, pero no puede recalcular nada sin los datos.

## Los hallazgos principales (resumen)

1. **El cuello de botella es la espera de cama:** mediana de **18 h** y percentil 90 de **71,5 h** desde que llega el paciente hasta que
   entra a cama. El 77 % de ese tiempo es en urgencias y el 23 % es tiempo sin ninguna etapa registrada.
2. **Los peores casos empeoran:** el percentil 90 de la espera sube de 61 h (2023) a 80 h (2026); la mediana casi no cambia.
3. **Las altas son tardías:** 61,5 % entre las 14:00 y las 18:59 y solo 15 % antes del mediodía; las camas se asignan a las 17–18 h.
   Quien llega a media tarde espera más.
4. **Adelantar altas ayuda poco:** pasar el 30 % de las altas de la tarde a la mañana libera hasta 5,5 camas, pero evita como máximo ~8 % del
   exceso de espera (estimación central ~3 %).
5. **La ocupación sube por la estancia, no por más pacientes:** de 105 a 119 camas ocupadas (2023 a 2025) con estancia de 4,7 a 5,5 días e
   ingresos estables (~22 por día).
6. **Se puede pronosticar la demanda:** llegadas por día con error de 7,5 %; los ingresos solo por semana (9,5 %). El Carnaval de
   Barranquilla baja las visitas ~17 %.
7. **Alertas probadas:** "día congestionado" a las 12 h detecta 83 % de esos días; ~5 alertas por día en total con el diseño recomendado.
8. **Problemas de datos clave:** ~30 % de visitas copiadas, **41 % de las estancias en cama duplicadas entre dos personas**, y desde
   abril de 2026 las llegadas caen 25–35 % (posible carga incompleta).
9. **Qué no se sabe:** el número de camas del hospital, la meta de tiempos y la causa de la caída de 2026. Todo son asociaciones y escenarios,
   no causas probadas.

## Estado del proyecto (23-oct-2026)

| Frente | Estado |
|---|---|
| Limpieza de datos y episodios | Hecho |
| Flujo del paciente (componente 1) | Hecho |
| Cuellos de botella (componente 2) | Hecho |
| Modelos: pronóstico, alertas, simulación, días atípicos (componente 3) | Hecho |
| Recomendaciones (componente 4) | Borrador (falta revisar las fuentes originales) |
| Dashboard de Power BI | Pendiente |
| Notebooks de camas y escenarios | Pendiente |
| `mapeo_dx.csv` (grupos de diagnóstico) | Pendiente |
| Sesión de preguntas con el HUN | Preguntas listas (`docs/hun/`); falta la sesión |
| Documento final y presentación | Pendiente (fin de noviembre de 2026) |

## Qué hay en cada carpeta

| Ruta | Contenido |
|---|---|
| `CLAUDE.md` | Contexto completo del proyecto: la base de datos, problemas de calidad, decisiones de método y resultados (lo lee Claude Code solo) |
| `docs/HALLAZGOS.md` | **Hallazgos con cifras y fuentes**, glosario, preguntas frecuentes y mapa de archivos |
| `docs/plan_de_accion.md` | Definición de cuello de botella y fases del análisis |
| `docs/recomendaciones.md` | Siete recomendaciones con sus números, límites y fuentes (borrador) |
| `docs/dias_atipicos.md` | Días que se salieron del patrón y por qué |
| `docs/fichas_de_tareas.md` | Reparto de tareas del equipo |
| `docs/hun/sesion_de_preguntas.md` | Preguntas para la sesión con el HUN y espacio para anotar las respuestas |
| `docs/Diccionario_datos.md` | Diccionario de las tablas OMOP |
| `docs/DATA CHALLENGE HUN 2026 (2).pdf` | Instructivo oficial del reto |
| `sql/` | Consultas para la base (`consultas_cuellos_botella.sql` Q0 a Q5 y Q3b; `consultas_semana1.sql`) |
| `src/` | Scripts de Python (ver el orden abajo) |
| `resultados/graficos/` | Gráficos (sí están en git) |
| `notebooks/`, `powerbi/` | Carpetas del equipo (pendientes) |
| `datos/`, `resultados/tablas/`, `resultados/excel/` | **No están en git** (datos clínicos) |

## Cómo reproducirlo (requiere acceso a los datos)

1. `pip install -r requirements.txt` (Python 3.14; probado con pandas 3, numpy 2.5).
2. Exportar de la base (PostgreSQL, esquema `uninorte_omop`, solo lectura, con VPN) a `datos/crudos/`:
   `visit_detail.csv`, `visit_occurrence.csv`, `person.csv` y los demás de `sql/consultas_semana1.sql`.
   **Nunca se guarda la contraseña en el repositorio.**
3. Correr en este orden:
   ```bash
   python3 src/analisis_etapas.py          # limpia, arma episodios, marca estancias gemelas
   python3 src/preparar_variables.py       # variables, ocupación y series
   python3 src/exportar_para_equipo.py     # tablas para el equipo y Power BI
   python3 src/generar_q3_q4_desde_csv.py  # (alternativa a correr Q3 y Q4 en DBeaver; requiere duckdb)
   python3 src/construir_segmentos.py
   python3 src/ranking_cuellos.py
   python3 src/dependencia_carga.py
   python3 src/altas_y_factores.py
   python3 src/simulacion_altas.py
   python3 src/pronostico_demanda.py
   python3 src/alertas.py
   python3 src/dias_atipicos.py
   ```
4. Las salidas quedan en `datos/procesados/` y `resultados/` (fuera de git, salvo los gráficos).

## Reglas del repositorio

- **Nada de datos de la base en git** (ni CSV a nivel de paciente o visita, ni `.pbix`). Se comparten tablas agregadas por un drive privado.
- Mensajes de commit en español y sin datos. Una rama por persona y *pull request* hacia `main`.
- Cada hallazgo lleva su limitación al lado.

## Limitaciones (resumen)

Copias y réplicas de registros, etapas de urgencias sin hora de salida (36–42 %), diagnósticos tardíos y sin jerarquía, número de camas
desconocido, procedimientos sin fecha, sin signos vitales y la caída de llegadas desde abril de 2026. Detalle en `docs/HALLAZGOS.md`, sección 7.
