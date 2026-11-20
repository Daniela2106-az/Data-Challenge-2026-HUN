# Asistente de flujo HUN (20-nov-2026)

Un asistente del dashboard donde se pregunta en lenguaje natural sobre el análisis. Es la **página de inicio** del dashboard (`/`: quien abre el enlace cae ahí) y además un botón con letrero en la esquina inferior derecha de las demás páginas; también se puede seleccionar un texto de la pantalla y pulsar «Preguntar sobre esto».

## Qué sabe y qué no
- **Solo lee `docs/asistente/conocimiento.md`**, un documento que arma `src/armar_conocimiento.py` a partir de la documentación (documento final, glosario y preguntas frecuentes, lo que los datos no respaldan, el simulador y sus alertas). Son unos 43.000 tokens, sin datos de pacientes.
- Se quita lo que repite otro documento o sirve más a quien reproduce el trabajo (columnas y variables, referencias, mapa de archivos, historia de construcción). La lista está en `FUENTES` del script; el script falla si un encabezado de esa lista deja de existir.
- Si la respuesta no está en el documento, dice «Eso no está en el análisis del proyecto» y no completa con conocimiento general. Una pregunta de otro tema se rechaza.
- Cada respuesta es una tarjeta: titular, hasta tres cifras, barras comparativas, nota de advertencia, las páginas del dashboard donde se ve lo respondido (botones que abren la página sin recargar) y dos preguntas de seguimiento. El modelo devuelve esa estructura en JSON y la interfaz la dibuja (`dashboard/assets/asistente.js`).
- Si cambia el análisis: actualizar los documentos y correr `python3 src/armar_conocimiento.py`.

## Cómo está construido
- `dashboard/asistente.py`: la llamada a la API (modelo Claude Sonnet 5.5, poco razonamiento, respuesta estructurada), las instrucciones, los límites y la fecha de apagado.
- `dashboard/asistente_ui.py`: el chat de la esquina y los callbacks. `dashboard/pages/inicio.py`: la página de inicio (el chat y la guía para explorar).
- La conversación se guarda en el navegador (sesión), no en el servidor. La caché del prompt es de 5 minutos.

## Configuración (variables de entorno)
| Variable | Qué hace |
|---|---|
| `ANTHROPIC_API_KEY` | La clave de la API. En local, un archivo `.env` en la raíz (ignorado por Git); en Render, *Environment*. Nunca en el repositorio. |
| `ASISTENTE_HASTA` | Fecha (AAAA-MM-DD) desde la que el asistente deja de responder. Por defecto `2026-12-01`, hora de Colombia. |

## Límites y costo
- 10 preguntas por persona al día y 60 para todo el sitio; 500 caracteres por pregunta. Los conteos viven en la memoria del servidor: se reinician si el servidor se reinicia.
- Costo medido el 20-nov-2026 con la base de 43.000 tokens (precios de la API a esa fecha): una pregunta con la caché vacía cuesta unos 0,12 USD y una con la caché caliente, unos 0,02 USD. Cada pregunta imprime en el log del servidor los tokens que usó (`[asistente] entrada … caché leída …`).
- El **tope real de gasto** es el límite mensual del *workspace* de la clave en la consola de Anthropic (5 USD).

## Cómo se apaga
1. **Por fecha:** desde `ASISTENTE_HASTA` el código no llama a la API y la página dice que el asistente estuvo disponible hasta el día anterior.
2. **Definitivo:** revocar la clave en la consola de Anthropic. La fecha impide usar la clave, pero no la borra.

## Límites del asistente
Puede equivocarse: la página lo avisa y cada respuesta cita su fuente. No ve datos en vivo: solo las cifras ya documentadas. Las conversaciones no se guardan en el servidor.
