# Publicar el dashboard en Render (plan gratuito) — notas de rendimiento (20-nov-2026)

**Enlace público:** https://data-challenge-hun.onrender.com/

El servicio despliega la rama `render` de este repositorio (= `main` + `render_build.sh`, que baja los datos desde un repositorio privado). Para actualizarlo: fusionar `main` en `render` y empujar (Auto-Deploy en *On Commit*).

## Por qué se atasca el plan gratuito
Medido el 20-nov-2026: la simulación de «Planeación de camas» tarda ~3 s en un computador y el dashboard completo ocupa ~420 MB (el plan gratuito tiene 512 MB). El plan gratuito da una fracción de un procesador y el servicio arranca con **un solo trabajador**: mientras calcula una simulación, todo lo demás (cambiar de página, otra simulación) queda en cola. Si el cálculo pasa del *timeout* de gunicorn, el trabajador se reinicia y el navegador se queda esperando sin gráfico.

## Qué hace el código (`dashboard/modo.py`)
- **Modo ligero:** se activa solo en Render (la variable `RENDER` la pone Render) o con `HUN_LIGERO=1`; `HUN_LIGERO=0` lo apaga. Las simulaciones interactivas usan un tercio de las repeticiones (mínimo 60). La banda del 10-90 % se ve igual, solo un poco más ruidosa. Las cifras oficiales (1.000 repeticiones) salen de `src/` y no cambian.
- **Planeación de camas:** al navegador ya solo viaja lo que se dibuja (percentiles por día, ~16 KB; antes ~3 MB por corrida), y una simulación repetida con los mismos controles se devuelve al instante.
- **Icono de carga en las gráficas (`assets/theme.css`, al final):** mientras una gráfica aún no se dibuja, o espera el resultado de un cálculo, se ve un círculo girando con «Cargando…» y la gráfica anterior atenuada, para que el blanco no parezca un error. No aparece en la reproducción del simulador, que se actualiza todo el tiempo.
- **Cambio de página:** `assets/navegacion_rapida.js` marca el enlace del menú como activo al instante y muestra una barra de progreso hasta que llega la página, para que se vea que el clic funcionó.

## Comando de inicio recomendado (Render → Settings → Start Command)
```
gunicorn --chdir dashboard main:server --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 600
```
Con `--threads 4` una simulación larga ya no bloquea el cambio de página (sigue siendo un solo proceso, así que la memoria no se multiplica), y `--timeout 600` evita que un cálculo lento mate al trabajador. No cambies el *Build Command*: ahí se bajan los datos.

## Si sigue lento
En Render → Logs, buscar `WORKER TIMEOUT` (tiempo) o `out of memory` (memoria). La solución completa es un plan de pago con más procesador. Antes de una presentación, abrir la página unos minutos antes: tras un rato sin visitas el plan gratuito duerme el servicio y la primera carga tarda.
