#!/usr/bin/env bash
# start.sh — Script de arranque para Render
# Aplica migraciones pendientes ANTES de iniciar gunicorn.
# Esto garantiza que cualquier nueva tabla esté creada
# antes de que el servidor empiece a recibir tráfico.

set -e  # Detener si cualquier comando falla

echo "==> Aplicando migraciones de base de datos..."
flask --app wsgi db upgrade
echo "==> Migraciones aplicadas correctamente."

echo "==> Iniciando servidor gunicorn..."
exec gunicorn wsgi:app
