# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Diaromas - imagen de la aplicación Django
#   docker build -t diaromas:dev .
# ---------------------------------------------------------------------------
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings

# build-essential/libpq-dev: solo se necesitan si una plataforma no trae wheel
# precompilado de psycopg o Pillow.
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Primero las dependencias para aprovechar la caché de capas de Docker
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usuario sin privilegios + directorios que se montan como volúmenes
RUN chmod +x /app/docker/entrypoint.sh \
    && mkdir -p /app/staticfiles /app/media /app/static/img/productos \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]