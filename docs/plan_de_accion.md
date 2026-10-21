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

Resultado actual: 337.194 episodios; 45 % con duración medida; **espera de cama: mediana 22,4 h, 48 % espera más de 24 h**;
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

## 3. Quién hace qué

### Daniela (con Claude): datos, modelos y repo
- Mantener los scripts (`src/`), correr consultas en DBeaver y exportar.
- Revisión 1 y 2 de la sección anterior.
- **Modelo A** (llegadas por día y hora) y **Modelo B** (riesgo de esperar más de 24 h), validación temporal.
- Exportar las tablas agregadas para Power BI y compartirlas por el drive privado.
- Commits (sin datos de la base) y el README para reproducir todo.

### Persona 2: Power BI (dashboard)
- Semana 1: aprender la estructura de los datos con `docs/` y `CLAUDE.md`; armar el modelo en Power BI con
  `serie_diaria`, `mapa_calor_llegadas`, `factores_espera_cama` (que entrega Daniela).
- Páginas: (1) llegadas por hora y día, (2) rutas del paciente, (3) espera de cama por hora, edad y diagnóstico,
  (4) resultados del modelo, (5) recomendaciones.
- Criterio de calidad: que cada página responda una pregunta del hospital en una frase.

### Persona 3: documento, HUN y recomendaciones
- **Enviar el correo al HUN esta semana** (preguntas 1–10 de `CLAUDE.md`, sección 8) y seguir las respuestas.
- Armar el documento: contexto, metodología (en español claro), limitaciones (tabla de la sección 1) y hallazgos.
- Revisar con apoyo de fuentes públicas el `mapeo_dx.csv` que prepare Claude (nadie del equipo es médico:
  usar el navegador de SNOMED o consultar a un docente de salud).
- Investigar prácticas conocidas para reducir esperas de cama (altas antes del mediodía, gestión de camas) para
  respaldar las recomendaciones.

## 4. Calendario

| Semana | Daniela + Claude | Persona 2 | Persona 3 | Entregable |
|---|---|---|---|---|
| **20–26 oct** | Scripts v3.5 listos (hecho). Revisión 1. `mapeo_dx.csv` borrador. Exportar tablas para Power BI | Instalar Power BI y conectar las tablas de ejemplo | **Enviar correo al HUN.** Esqueleto del documento | Repo |
| **27 oct–2 nov** | Componentes 1 y 2: rutas, llegadas, espera según hora/congestión/edad/diagnóstico; probar altas tardías | Páginas 1–3 del dashboard | Redactar metodología y limitaciones | Doc + primeras páginas de Power BI |
| **3–9 nov** | Modelo A y B; entrenar 2023–2025, probar 2026 | Página 4 (modelo) | Redactar resultados del componente 2 | Repo + doc |
| **10–16 nov** | Cuantificar recomendaciones ("si las altas fueran antes del mediodía, la espera bajaría X h") | Página 5 y pulido visual | Recomendaciones y respuestas del HUN | Power BI + doc |
| **17–23 nov** | README; reproducir todo desde cero en otra máquina | Publicar el enlace de Power BI | Documento final | Los 3 entregables |
| **24–30 nov** | Colchón y presentación | Colchón | Colchón | — |

## 5. Reglas del equipo
- **Nada de datos de la base en git.** Las carpetas `datos/` y `resultados/tablas|excel` están ignoradas. Las tablas
  agregadas se comparten por un drive privado del equipo.
- Las decisiones de método viven en `CLAUDE.md` (sección 5); si alguien quiere cambiar una, se discute primero.
- Cada hallazgo en el documento lleva su limitación al lado (por ejemplo, la falta de hora de salida).
- No pulir más la limpieza: lo que queda no cambia las medianas.
