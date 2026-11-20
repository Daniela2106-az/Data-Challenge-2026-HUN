# Dashboard del flujo de pacientes del HUN

Panel interactivo del Data Challenge HUN 2026 (Hospital Universidad del Norte y Ciencia de Datos, Uninorte). Muestra cómo llegan, esperan y se hospitalizan los pacientes, dónde se pierde el tiempo, qué se espera hacia adelante y qué acciones se recomiendan.

**Versión publicada:** https://data-challenge-hun.onrender.com/ (puede tardar un minuto en abrir si estuvo un rato sin visitas). Mientras una gráfica se calcula, muestra un círculo de carga en vez de quedar en blanco.

Funciona en tu propio computador y se abre en el navegador. No necesita conexión a internet una vez instalado; solo el asistente de preguntas (opcional, ver abajo) la necesita.

## Qué necesitas

- Un computador con Windows, macOS o Linux.
- **Python 3.10 o más reciente** (el proyecto se probó con Python 3.14). Descárgalo en https://www.python.org/downloads/ si no lo tienes. En Windows, marca la casilla «Add Python to PATH» al instalarlo.
- **Git** (https://git-scm.com/downloads), o bien puedes descargar el proyecto como archivo ZIP, como se explica abajo.
- La carpeta de datos del hospital (`datos/procesados`). No viene en el repositorio porque son datos del hospital: pídesela a quien te compartió el proyecto.

## 1. Descargar el proyecto

**Con Git** (abre una terminal o la «Línea de comandos» en la carpeta donde quieras guardarlo):

```
git clone https://github.com/Daniela2106-az/Data-Challenge-2026-HUN.git
cd Data-Challenge-2026-HUN
```

**Sin Git:** entra a https://github.com/Daniela2106-az/Data-Challenge-2026-HUN, pulsa el botón verde **Code**, elige **Download ZIP**, descomprime el archivo y abre una terminal dentro de la carpeta descomprimida.

Después de descargarlo, copia la carpeta `datos/procesados` que te entregaron dentro de la carpeta `datos` del proyecto.

## 2. Instalar

Todos los comandos se escriben dentro de la carpeta del proyecto.

1. Crea un entorno aparte para el proyecto:

   - Windows: `python -m venv venv`
   - macOS o Linux: `python3 -m venv venv`

2. Actívalo:

   - Windows: `venv\Scripts\activate`
   - macOS o Linux: `source venv/bin/activate`

   Sabrás que quedó activo porque la línea de la terminal empieza con `(venv)`.

3. Instala lo que el dashboard necesita (tarda unos minutos):

   ```
   pip install -r requirements.txt
   ```

## 3. Ponerlo a funcionar

1. Con el entorno activado, inicia el dashboard:

   - Windows: `python dashboard\main.py`
   - macOS o Linux: `python3 dashboard/main.py`

2. Espera a que la terminal deje de mostrar mensajes de carga (puede tardar medio minuto la primera vez).

3. Abre el navegador y entra a:

   **http://127.0.0.1:8050**

El dashboard usa el **puerto 8050**. Si otro programa ya lo está usando, ciérralo antes de iniciar.

Para detenerlo, vuelve a la terminal y presiona `Ctrl + C`. La próxima vez solo repite los pasos 2.2 (activar el entorno) y 3.

## El asistente de preguntas (opcional)

**Cómo moverte:** arriba del menú lateral está el botón azul **Simular**, que abre «¿Qué quieres hacer hoy?» con los cinco módulos interactivos: Simulador integral, Pronosticador, Planeación de camas, Paciente en espera y Paciente en cama. Cada tarjeta dice en una frase qué permite hacer y muestra una animación al pasar el mouse. El resto del menú agrupa las páginas de resultados por categoría (Contexto, Flujo, Capacidad, Clínico, Riesgo y Conclusiones).

El dashboard trae un asistente donde se pregunta en lenguaje natural sobre el análisis (página «Asistente HUN», o el botón de la esquina de cada página). Para activarlo hace falta una clave de la API de Anthropic:

1. Crea un archivo llamado `.env` en la carpeta del proyecto, con una sola línea: `ANTHROPIC_API_KEY=tu-clave`. Ese archivo no se sube a GitHub. Si publicas el dashboard en un servicio como Render, pon la clave en sus variables de entorno, nunca en el repositorio.
2. Opcional: `ASISTENTE_HASTA=2026-12-01` es el día desde el que el asistente deja de responder (ese es el valor por defecto).
3. Inicia el dashboard como siempre. Sin la clave, todo lo demás funciona y la página del asistente avisa que no está configurado.

El asistente solo lee `docs/asistente/conocimiento.md` (documentación, sin datos de pacientes). Si cambias la documentación, vuelve a armarlo con `python3 src/armar_conocimiento.py`. Más detalle, costos y límites: `docs/asistente.md`.

## Si algo no funciona

- **«python no se reconoce como un comando»:** reinstala Python marcando «Add Python to PATH», o usa `py` en lugar de `python` en Windows.
- **El dashboard no abre o muestra un error al iniciar con un archivo que no se encuentra:** falta la carpeta `datos/procesados` o está en otro lugar. Debe quedar en `datos/procesados`, dentro de la carpeta del proyecto.
- **La página no carga en el navegador:** confirma que la terminal sigue abierta y sin errores, y que escribiste exactamente `http://127.0.0.1:8050`.
