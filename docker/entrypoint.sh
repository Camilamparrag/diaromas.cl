#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Entrypoint de Diaromas: espera la BD, migra y opcionalmente carga datos.
# Permite sobreescribir el comando con:  docker compose run --rm web <comando>
# ---------------------------------------------------------------------------
set -e

echo "-> [diaromas] esperando a PostgreSQL..."
python manage.py wait_for_db

echo "-> [diaromas] aplicando migraciones..."
python manage.py migrate --noinput

if [ "${DJANGO_SEED_ON_START:-0}" = "1" ]; then
  echo "-> [diaromas] cargando catálogo inicial desde data/productos.json..."
  python manage.py cargar_catalogo
fi

if [ "${DJANGO_COLLECTSTATIC:-0}" = "1" ]; then
  echo "-> [diaromas] recopilando archivos estáticos..."
  python manage.py collectstatic --noinput
fi

echo "-> [diaromas] listo: $*"
exec "$@"