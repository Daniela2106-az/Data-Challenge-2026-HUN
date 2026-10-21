# Plan de acción — Data Challenge HUN 2026 (actualizado 20-oct-2026)

Equipo de 3. Solo una persona tiene Claude (**Daniela**); las otras dos trabajan con lo que ella les pasa
(tablas agregadas por un drive privado, nunca por git) y con las herramientas que ya tengan.

## 1. Qué problemas encontramos (en palabras simples)

| # | Problema | Qué significa | Qué hicimos |
|---|---|---|---|
| 1 | **Visitas repetidas** (~30 % de la base) | Muchas visitas aparecen dos veces con las mismas etapas, a la misma hora al segundo. Si se cuentan todas, el hospital parece tener el triple de llegadas. | Se borran solo cuando el paciente es el mismo. Cuando el paciente es otro, se conserva la visita pero se quitan las etapas repetidas. |
| 2 | **Dos personas con la misma línea de tiempo** | En unas 280.000 visitas, dos pacientes distintos (edades muy diferentes, ids casi consecutivos) tienen exactamente los mismos pasos. Parece un registro que se replicó de una persona a otra. No sabemos cuál es la "real". | Probado con una consulta a la base (75 pares). Pregunta enviada al HUN. |
| 3 | **Falta la hora de salida** | A ~55 % de quienes se van de alta desde urgencias no se les registró cuándo terminó la atención. No es error nuestro: el dato no existe. Quien se hospitaliza sí tiene todos los tiempos. | Esos casos se marcan "sin duración", no como "0 horas". No se mide la duración de urgencias; se mide la espera de cama. |
| 4 | **Diagnósticos tardíos y sin agrupar** | El 88 % se anota después de las primeras 2 h, y vienen en un código (SNOMED) sin grupos. | Sirven para explicar, no para predecir "al llegar". Hay que agruparlos a mano (`mapeo_dx.csv`). |
| 5 | **El tipo de visita no es confiable** | Visitas "ambulatorias" incluyen urgencias y hospitalización. | Usamos las etapas, no el tipo de visita. |
| 6 | **Ocupación incompleta** | Solo vemos a los pacientes de esta base; no sabemos cuántas camas tiene el hospital. La ocupación casi no cambia la espera, pero puede ser por esto. | Se pide al HUN el número de camas. |

Resultado actual: 337.194 episodios; 37 % con duración medida y 8 % con un mínimo conocido (v3.6); **espera de cama: mediana 22,4 h, 48 % espera más de 24 h**;
la espera es más larga si se llega en la tarde (26,8 h) que de madrugada (16,0 h).

## 2. Qué más podemos revisar (en orden de utilidad)

1. **¿Los casos sin hora de salida se parecen a los que sí la tienen?** (edad, hora, día). Si se parecen, podemos
   hablar de la duración en urgencias con confianza. Solo requiere los datos que ya tenemos. *(Claude, 1 día)*
2. **Hora del último laboratorio como piso de la hora de salida.** Una consulta pesada (10–30 min) agregando
   `MIN` y `MAX` de `measurement_datetime` por visita. Daniela la corre una vez. *(Opcional; solo si 1 sale bien.)*
3. **Quitar de diagnósticos, procedimientos y laboratorios los registros que una visita tiene de otra persona**
   (filtro `person_id` igual al de la visita). Consultas pesadas; hacerlo solo si el tiempo alcanza.
4. **Mapeo de diagnósticos** (`mapeo_dx.csv`): bloquea las gráficas por diagnóstico.

No hace falta bajar otras tablas por ahora.

## 3. Qué piden los organizadores y cómo lo repartimos

Los entregables son tres: **documentación**, **repositorio en GitHub** y **dashboard en Power BI**. Se valora:
hallazgos estratégicos, interpretabilidad, visualización efectiva y comunicación clara. Las propuestas pueden incluir
modelos predictivos, dashboards, sistemas de alerta temprana, análisis de patrones y **modelos de simulación**.
Cada persona es dueña de un entregable y de una carpeta del repo, para trabajar a la vez sin conflictos.

| Entregable | Responsable | Carpeta del repo | Qué entrega |
|---|---|---|---|
| **Datos + modelos** (alimenta a los tres) | **Daniela con Claude** | `src/`, `sql/`, `notebooks/modelos/` | Scripts, tabla de episodios, Modelo A (llegadas) y Modelo B (riesgo de esperar > 24 h), tablas agregadas para Power BI y documento |
| **Dashboard Power BI** | **Persona 2** | `powerbi/` | Dashboard de 5 páginas, plantilla `.pbit` (sin datos), lista de medidas DAX y capturas |
| **Documentación y propuestas** | **Persona 3** | `docs/`, `docs/hun/`, `datos/referencia/`, `notebooks/simulacion/` | Documento final, README, correspondencia con el HUN, `mapeo_dx.csv`, recomendaciones y simulación de escenarios |

### Detalle por persona

**Daniela + Claude (datos y modelos)**
- Mantener `src/` y correr las consultas en DBeaver.
- Revisión: ¿se parecen los casos con y sin hora de salida? (define qué se puede afirmar sobre urgencias).
- Modelo A: pronóstico de llegadas por día y hora. Modelo B: riesgo de esperar más de 24 h por cama.
  Entrenar con 2023–2025 y probar con 2026; solo variables conocidas al llegar.
- Exportar cada martes y viernes las tablas agregadas al **drive privado** del equipo (nunca a git).
- Revisar los *pull requests* de los demás y hacer el commit final.

**Persona 2 (Power BI)**
- Semana 1: conectar `serie_diaria`, `serie_horaria`, `mapa_calor_llegadas`, `factores_espera_cama` (del drive).
- Páginas: (1) llegadas por hora y día, (2) rutas del paciente, (3) espera de cama por hora, edad y diagnóstico,
  (4) resultados del modelo, (5) recomendaciones.
- Guardar en el repo solo la plantilla `.pbit`, el archivo `powerbi/medidas_dax.md` y capturas. El `.pbix` lleva datos
  incrustados y **no se sube**.
- Criterio: cada página responde una pregunta del hospital en una frase.

**Persona 3 (documentación, HUN y propuestas)** — trabaja en paralelo desde el primer día
- **Esta semana:** enviar el correo al HUN con las preguntas de `CLAUDE.md` sección 8; guardar sus respuestas en `docs/hun/`.
- **Documento:** contexto, metodología en español claro, tabla de limitaciones (sección 1) y hallazgos. Se escribe mientras
  salen los resultados, no al final.
- **`datos/referencia/mapeo_dx.csv`:** Claude deja un borrador con los ~300 diagnósticos más frecuentes; Persona 3 lo
  revisa con el navegador de SNOMED o con un docente de salud (nadie del equipo es médico). Este archivo sí va al repo.
- **Componente 4 (propuestas):** investigar prácticas conocidas para bajar esperas de cama (altas antes del mediodía,
  gestión diaria de camas, alertas tempranas) y respaldarlas con fuentes.
- **Simulación** (`notebooks/simulacion/`): un modelo sencillo de "qué pasaría si" (por ejemplo, adelantar las altas al
  mediodía) usando las tablas agregadas que entrega Daniela. Es lo que convierte las recomendaciones en números.

## 4. Calendario

| Semana | Daniela + Claude | Persona 2 (Power BI) | Persona 3 (doc, HUN, propuestas) | Entregable |
|---|---|---|---|---|
| **20–26 oct** | Scripts v3.6 (hecho). Revisión de casos con/sin hora de salida. Borrador de `mapeo_dx.csv`. Primera exportación de tablas | Instalar Power BI, conectar tablas de ejemplo | **Correo al HUN.** Esqueleto del documento y README | Repo |
| **27 oct–2 nov** | Componentes 1 y 2: rutas, llegadas, espera según hora, congestión, edad y diagnóstico | Páginas 1–3 | Metodología y limitaciones; revisar `mapeo_dx.csv` | Doc + primeras páginas de Power BI |
| **3–9 nov** | Modelos A y B | Página 4 | Resultados del componente 2; empezar la simulación | Repo + doc |
| **10–16 nov** | Cuantificar recomendaciones con la simulación | Página 5 y pulido | Recomendaciones y respuestas del HUN | Power BI + doc |
| **17–23 nov** | README técnico; reproducir todo desde cero | Publicar el enlace de Power BI | Documento final | Los 3 entregables |
| **24–30 nov** | Colchón y presentación | Colchón | Colchón | — |

## 5. Cómo trabajamos a la vez en el repositorio
- **Cada quien en su carpeta** (tabla de la sección 3): casi no hay conflictos. `src/` es solo de Daniela; si alguien
  necesita un cambio, lo pide.
- **Una rama por persona** (`powerbi`, `docs`, `modelos`) y *pull request* hacia `main`; Daniela revisa. Mensajes de
  commit en español y sin datos.
- **Nada de datos de la base en git.** `datos/crudos`, `datos/procesados`, `resultados/tablas`, `resultados/excel` y los
  `.pbix` están ignorados. Antes de cada commit: `git status` y comprobar que no hay `.csv`, `.parquet`, `.xlsx` ni `.pbix`.
  La única excepción es `datos/referencia/` (listas hechas a mano, como `mapeo_dx.csv`, sin datos de pacientes).
- Las tablas agregadas se comparten por un drive privado del equipo, con el nombre y la fecha de la corrida.
- Las decisiones de método viven en `CLAUDE.md` (sección 5); para cambiar una, se discute antes.
- Cada hallazgo en el documento lleva su limitación al lado (por ejemplo, la falta de hora de salida).
- No pulir más la limpieza: lo que queda no cambia las medianas de la espera de cama.
