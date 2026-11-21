# Publicar el dashboard en Render (plan gratuito) — notas de rendimiento (20-nov-2026)

**Enlace público:** https://data-challenge-hun.onrender.com/

El servicio despliega la rama `render`. Desde el 20-nov-2026 `render` y `main` son **la misma rama** (mismos commits; `render_build.sh`, que baja los datos desde un repositorio privado, ya vive en `main`). Para actualizarlo: empujar a `main` y luego `git push origin main:render` (Auto-Deploy en *On Commit*). Si alguna vez se separan, `git checkout render && git merge --ff-only main`.

## Qué viaja y qué no
- **Repositorio del proyecto:** solo código y documentación. Ningún dato clínico.
- **Repositorio privado de datos** (variables `DATOS_REPO` y `DATOS_TOKEN` en Render → Environment): `procesados/` (incluida `tabla_episodios.parquet` y `procesados/modelos/`) y `tablas/`. `render_build.sh` lo clona **solo al construir**: un cambio en ese repositorio no despliega nada hasta hacer *Manual Deploy → Clear build cache & deploy*.
- **Modelos de «Paciente en espera» y «Paciente en cama»:** `procesados/modelos/m1_tiempo_restante.joblib` (v10) y `m1_estancia_restante.joblib` (v2). Si falta uno, o está guardado con otra versión de scikit-learn, el servidor intenta reentrenar, necesita datos crudos que no están en Render y la página no dibuja nada. Cada vez que se reentrene un modelo en local, hay que subir el `.joblib` nuevo al repositorio de datos y redesplegar.
- **scikit-learn fijado en `==1.9.1`** en `requirements.txt`: es la versión con la que se guardaron los modelos; otra versión da `Can't get attribute '_RemainderColsList'`.

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

## Si «Paciente en espera» o «Paciente en cama» no dibujan nada
La respuesta del servidor es `200` y el error queda en el texto del callback, no en los *Logs*. Se ve enviando la misma petición que hace «Estimar» a `/_dash-update-component` (salida `pac-nota`): si dice `No se pudo estimar: …`, ese es el motivo. Causas vistas: `.joblib` ausente o de otra versión, y scikit-learn distinto del de los modelos.

## Si sigue lento
En Render → Logs, buscar `WORKER TIMEOUT` (tiempo) o `out of memory` (memoria). La solución completa es un plan de pago con más procesador. Antes de una presentación, abrir la página unos minutos antes: tras un rato sin visitas el plan gratuito duerme el servicio y la primera carga tarda.
