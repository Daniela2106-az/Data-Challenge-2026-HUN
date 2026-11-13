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

1. **El cuello de botella es la espera de cama:** mediana de **18,6 h** y percentil 90 de **73,9 h** desde que llega el paciente hasta que
   entra a cama. Casi todo ese tiempo (98 %) es en urgencias antes de que se asigne la cama; el tiempo sin ninguna etapa registrada es ~1 % (corregido el 7-nov, `CLAUDE.md` 4.12).
2. **Los peores casos empeoran:** el percentil 90 de la espera sube de 61 h (2023) a 80 h (2026); la mediana casi no cambia.
3. **Las altas son tardías:** 62,7 % entre las 14:00 y las 18:59 y solo 14 % antes del mediodía; las camas se asignan a las 17–18 h.
   Quien llega a media tarde espera más.
4. **Adelantar altas ayuda poco:** pasar el 30 % de las altas de la tarde a la mañana libera hasta 5,1 camas, pero evita como máximo ~8 % del
   exceso de espera (estimación central ~3 %).
5. **La ocupación sube por la estancia, no por más pacientes:** de 94 a 105 camas ocupadas (2023 a 2025) con estancia de 4,6 a 5,3 días e
   ingresos estables (~20 por día).
6. **Se puede pronosticar la demanda:** llegadas por día con error de 7,5 %; los ingresos solo por semana (9,5 %). El Carnaval de
   Barranquilla baja las visitas ~17 %.
7. **Alertas probadas:** "día congestionado" a las 12 h detecta 83 % de esos días; ~5 alertas por día en total con el diseño recomendado.
8. **Problemas de datos clave:** ~30 % de visitas copiadas, **41 % de las estancias en cama duplicadas entre dos personas**, y desde
   el 10 de abril de 2026 el registro de las etapas se degrada (las visitas de urgencias no bajan; baja el detalle registrado): esos días no se usan.
9. **Qué no se sabe:** el número de camas del hospital, la meta de tiempos y la causa de la caída de 2026. Todo son asociaciones y escenarios,
   no causas probadas.

## Estado del proyecto (23-oct-2026)

| Frente | Estado |
|---|---|
| Limpieza de datos y episodios | Hecho |
| Flujo del paciente (componente 1) | Hecho |
| Cuellos de botella (componente 2) | Hecho |
| Modelos: pronóstico, alertas, simulación, días atípicos (componente 3) | Hecho |
| Perfiles de pacientes y factores de la estancia (instructivo: perfiles y duración de estancias) | **Pendiente (Daniela)** |
| Explicar mejor los retrasos y simulación Monte Carlo de camas | **Pendiente (Anthony)** |
| Recomendaciones (componente 4) | Completas; pendientes de la revisión de Daniela |
| Dashboard de Power BI | Pendiente (Samuel; va de último, guía en `powerbi/`) |
| `mapeo_dx.csv` (grupos de diagnóstico) | Pendiente (Daniela) |
| Estimar tiempos de atención (componente 3) | **Hecho**: modelo de tiempo restante (`docs/estimador_tiempos.md`; en revisión de Daniela) |
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
| `docs/pendientes_y_reparto.md` | **Qué falta para cubrir el instructivo y quién lo hace** (Daniela, Samuel, Anthony) |
| `docs/fichas_de_tareas.md` | Fichas detalladas de cada tarea |
| `docs/hun/sesion_de_preguntas.md` | Preguntas para la sesión con el HUN y espacio para anotar las respuestas |
| `docs/Diccionario_datos.md` | Diccionario de las tablas OMOP |
| `docs/DATA CHALLENGE HUN 2026 (2).pdf` | Instructivo oficial del reto |
| `sql/` | Consultas para la base: `exportaciones_base.sql` y `consultas_semana1.sql` (los 8 CSV de entrada) y `consultas_cuellos_botella.sql` (Q0 a Q5 y Q3b) |
| `src/` | Scripts de Python (ver el orden abajo) |
| `resultados/graficos/` | Gráficos (sí están en git) |
| `powerbi/` | Guía, especificación y medidas del dashboard (`powerbi/CLAUDE.md` para el Claude de Samuel) |
| `notebooks/` | Carpeta del equipo (pendiente) |
| `datos/`, `resultados/tablas/`, `resultados/excel/` | **No están en git** (datos clínicos) |

## Consultar la base de datos

Si tienes acceso a la VPN de Uninorte y a las credenciales de la base, **`docs/conexion_bd.md`** explica paso a paso cómo conectarte (solo lectura, con SQLAlchemy), cómo correr consultas en segundo plano para que la VPN no te deje sin internet, qué hay en la base y qué trampas tiene. Las credenciales nunca van en el repositorio.

## Cómo reproducirlo (requiere acceso a los datos)

**Hay 10 archivos que no se pueden regenerar con los scripts:** salen de la base (PostgreSQL, esquema `uninorte_omop`, solo lectura, con VPN). Todo lo demás
(`datos/procesados/`, `resultados/tablas/`, los `q3_*` y `q4_*`) lo producen los scripts.
**Probado el 8-nov-2026 en un clon limpio de GitHub** (entorno nuevo con `pip install -r requirements.txt`, solo con esos 10 archivos): `tabla_episodios.parquet` sale **idéntica
columna por columna** a la del proyecto, y de 57 tablas comparadas salen iguales todas (las diferencias de texto en fechas de los `.csv` desaparecen al leerlas como fechas).

| Archivo en `datos/crudos/` | Consulta o script que lo exporta |
|---|---|
| `visit_detail.csv`, `visit_occurrence.csv`, `dx_por_visita.csv`, `proc_por_visita.csv` | `sql/exportaciones_base.sql` (verificado contra la base el 8-nov: 566.004 y 662.783 filas) |
| `person.csv`, `diagnosticos_por_visita.csv`, `procedimientos_por_visita.csv`, `laboratorios_por_visita.csv` | consultas 1 a 4 de `sql/consultas_semana1.sql` |
| `auditoria_bd/P02_persona_de_los_diagnosticos.csv`, `auditoria_bd/P03_persona_de_los_laboratorios.csv` | `python3 src/auditoria_bd.py --esperar 120 --lote 4` (ver `docs/conexion_bd.md`) |

**Los dos últimos son indispensables:** dicen cuál es la persona real en las estancias duplicadas (`CLAUDE.md` 4.10). Sin ellos los scripts **no fallan, pero cambian los resultados**
(`preparar_variables.py` avisa «faltan los CSV del lote 4» y conserva otro registro: cambian la edad y el sexo de las estancias gemelas, la espera de ~3.300 estancias y la persona real de todas).

1. `pip install -r requirements.txt` (Python 3.14; probado con pandas 3, numpy 2.5).
2. Poner los 10 archivos en `datos/crudos/`. **Nunca se guarda la contraseña de la base en el repositorio** (`docs/conexion_bd.md`).
3. Correr en este orden (cada uno tarda de segundos a un par de minutos en total):
   ```bash
   python3 src/analisis_etapas.py          # limpia, arma episodios, marca estancias gemelas
   python3 src/preparar_variables.py       # variables, ocupación, persona real y series
   python3 src/exportar_para_equipo.py     # tablas para el equipo
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
   Los análisis posteriores (perfiles, factores de la estancia, estancias que se disparan, diagnóstico repetible, estimador A6, exploraciones A8, C4, severidad de laboratorios)
   cada uno tiene su script y su documento en `docs/` (mapa en `docs/HALLAZGOS.md`, sección 9). Los que usan las consultas de `sql/espera_labs_y_texto.sql`, `sql/severidad_labs_6h.sql`, `sql/severidad_labs_6h_persona.sql` (banderas por persona real, la vigente)
   y `sql/nombres_*.sql` necesitan correrlas antes con `src/ejecutar_consultas.py` (VPN; `docs/conexion_bd.md`).
4. Opcional, prueba de sensibilidad al corte de episodios: `python3 src/generar_q3_q4_desde_csv.py --umbral 72` y luego
   `SUFIJO=_u72 python3 src/construir_segmentos.py` y `SUFIJO=_u72 python3 src/ranking_cuellos.py` (igual con 336).
5. Las salidas quedan en `datos/procesados/` y `resultados/` (fuera de git, salvo los gráficos).

**Sin esos archivos** no se puede recalcular nada. Alternativa para quien solo quiera consultar resultados: pedir las tablas agregadas
(`resultados/tablas/`, `resultados/excel/`, `datos/procesados/para_equipo/panel_diario.csv`, `datos/procesados/serie_*.csv`) al equipo y
dejarlas en esas mismas rutas. El dashboard (`python3 dashboard/main.py`, puerto 8050) también las necesita: sin ellas termina con `FileNotFoundError`.

## Reglas del repositorio

- **Nada de datos de la base en git** (ni CSV a nivel de paciente o visita, ni `.pbix`). Se comparten tablas agregadas por un drive privado.
- Mensajes de commit en español y sin datos. Una rama por persona y *pull request* hacia `main`.
- Cada hallazgo lleva su limitación al lado.

## Limitaciones (resumen)

Copias y réplicas de registros, etapas de urgencias sin hora de salida (36–42 %), diagnósticos tardíos y sin jerarquía, número de camas
desconocido, procedimientos sin fecha, sin signos vitales y el registro de etapas degradado desde el 10 de abril de 2026. Detalle en `docs/HALLAZGOS.md`, sección 7.
