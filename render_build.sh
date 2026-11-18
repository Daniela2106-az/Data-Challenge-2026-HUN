#!/usr/bin/env bash
# render_build.sh  -  construccion del dashboard en Render (rama «render»; 17-nov-2026)
# 1) Instala las dependencias y gunicorn.
# 2) Baja los datos del dashboard desde un repositorio PRIVADO aparte (no estan en este repositorio: son datos clinicos) y los copia a las
#    rutas que espera el codigo (datos/procesados y resultados/tablas). Solo existen en el servidor de Render; no se suben a este repo.
# Variables de entorno en Render (Environment): DATOS_REPO = usuario/nombre del repo privado de datos; DATOS_TOKEN = token de GitHub de
# solo lectura sobre ese repo (secreto: se pega en Render, nunca en un archivo).
set -euo pipefail
pip install -r requirements.txt gunicorn
: "${DATOS_REPO:?Falta la variable DATOS_REPO}"
: "${DATOS_TOKEN:?Falta la variable DATOS_TOKEN}"
rm -rf /tmp/hun-datos
git clone --depth 1 "https://x-access-token:${DATOS_TOKEN}@github.com/${DATOS_REPO}.git" /tmp/hun-datos
mkdir -p datos/procesados resultados/tablas
cp -r /tmp/hun-datos/procesados/. datos/procesados/
cp -r /tmp/hun-datos/tablas/. resultados/tablas/
rm -rf /tmp/hun-datos
echo "Datos del dashboard copiados."
