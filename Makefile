# ---------------------------------------------------------------------------
# Diaromas - Django + PostgreSQL
#   make up     levanta web (8000) y base de datos (5432)
#   make seed   carga el catálogo inicial desde data/productos.json
# ---------------------------------------------------------------------------
.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help env up up-build down logs shell psql migrate makemigrations superuser seed test lint fmt check

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

env: ## Crea .env a partir de .env.example si no existe
	@test -f .env || (cp .env.example .env && echo "-> .env creado desde .env.example (revisa WHATSAPP_NUMBER)")

up: env ## Levanta web + db en segundo plano
	$(COMPOSE) up -d --build
	@echo "-> Web: http://localhost:8000  |  Admin: http://localhost:8000/admin/"

up-build: env ## Levanta reconstruyendo la imagen
	$(COMPOSE) up -d --build

down: ## Detiene los contenedores (conserva los volúmenes)
	$(COMPOSE) down

logs: ## Muestra los logs en vivo
	$(COMPOSE) logs -f web

shell: ## Abre una shell de Python dentro del contenedor web
	$(COMPOSE) exec web python manage.py shell

psql: ## Abre psql conectado a la base de datos
	$(COMPOSE) exec db sh -c 'psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}'

migrate: ## Aplica las migraciones
	$(COMPOSE) exec web python manage.py migrate

makemigrations: ## Genera migraciones nuevas (apps/*)
	$(COMPOSE) exec web python manage.py makemigrations

superuser: ## Crea un usuario administrador
	$(COMPOSE) exec web python manage.py createsuperuser

seed: ## Crea/actualiza productos y categorías desde data/productos.json
	$(COMPOSE) exec web python manage.py cargar_catalogo

test: ## Corre los tests dentro del contenedor
	$(COMPOSE) exec web python manage.py test

lint: ## Revisa estilo y errores con ruff
	.venv/bin/ruff check . || ruff check .

fmt: ## Formatea el código con ruff
	.venv/bin/ruff format . || ruff format .

check: ## Verificación de Django (sistema y despliegue)
	$(COMPOSE) exec web python manage.py check
	$(COMPOSE) exec web python manage.py check --deploy