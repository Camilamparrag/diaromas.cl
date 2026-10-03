<div align="center">

# Diaromas

**Aromatizantes, difusores y aceites esenciales.**

Tienda web de comercio electrónico con Django + PostgreSQL + Docker.
El carrito vive en la sesión, el pedido se guarda en la base de datos y el cierre de
compra se completa por **WhatsApp** (enlace `wa.me`), sin pasarela de pago.

![Django](https://img.shields.io/badge/Django-6.1-4a4e2d) ![Python](https://img.shields.io/badge/Python-3.13-a47c62)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4a4e2d) ![Docker](https://img.shields.io/badge/Docker-compose-a47c62)

</div>

---

## 1. Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.13 · Django 6.1 · psycopg 3 |
| Base de datos | PostgreSQL 16 (Docker) |
| Estilos | CSS puro con variables CSS (sin frameworks) |
| Interfaz | Templates de Django + JavaScript progresivo |
| Archivos estáticos | WhiteNoise (hash y compresión) |
| Producción | Gunicorn + variables de entorno |

---

## 2. Inicio rápido

Requisitos: **Docker** y **Docker Compose**. Para trabajar en el código con IDE,
lint o tests también se recomienda **Python 3.12+**.

```bash
# 1. Crear el archivo de variables de entorno
cp .env.example .env
#    👉 edita WHATSAPP_NUMBER con el número real del negocio (solo dígitos, sin +)

# 2. Levantar web + base de datos
make up          # o: docker compose up -d --build

# 3. Crear el administrador
make superuser

# 4. Abrir
#    Tienda  → http://localhost:8000
#    Admin   → http://localhost:8000/admin/
```

El `entrypoint` del contenedor espera a la base de datos, aplica las migraciones y
carga el catálogo inicial de `data/productos.json` automáticamente
(desactívalo con `DJANGO_SEED_ON_START=0`).

### Comandos shortcuts (`make`)

| Comando | Qué hace |
|---|---|
| `make up` | Levanta `web` + `db` en segundo plano |
| `make down` | Detiene los contenedores (conserva datos) |
| `make logs` | Muestra los logs de Django en vivo |
| `make shell` | Shell de Python con el proyecto cargado |
| `make psql` | Consola `psql` sobre la base de datos |
| `make migrate` | Aplica migraciones |
| `make makemigrations` | Genera migraciones nuevas |
| `make seed` | Carga/actualiza el catálogo desde JSON |
| `make superuser` | Crea un usuario administrador |
| `make test` | Corre los tests |
| `make lint` / `make fmt` | ruff: revisión y formateo |

### Entorno virtual local (opcional)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# para que el .venv se conecte a la BD que corre en Docker:
export POSTGRES_HOST=localhost
python manage.py migrate
python manage.py runserver
```

---

## 3. Estructura del proyecto

```
diaromas.cl/
├── config/                     # proyecto Django (settings, urls, wsgi/asgi)
├── apps/
│   ├── accounts/               # registro, login/logout, perfil
│   ├── catalogo/               # categorías, productos, comando de carga
│   └── pedidos/                # carrito, pedidos y mensaje de WhatsApp
├── data/
│   └── productos.json          # catálogo inicial (JSON)
├── static/
│   ├── css/style.css           # paleta corporativa en variables CSS
│   ├── js/main.js              # menú, cantidades, avisos
│   └── img/productos/*.svg     # ilustraciones de ejemplo
├── templates/
│   ├── base.html  partials/  404.html  500.html
│   ├── catalogo/  pedidos/  accounts/
├── docker/entrypoint.sh        # espera BD + migrate + seed
├── docker-compose.yml  Dockerfile  Makefile
├── requirements.txt  requirements-dev.txt
└── .env.example  .gitignore  .dockerignore
```

---

## 4. Paleta de diseño

Definida en variables CSS al inicio de `static/css/style.css`:

| Rol | Variable | Color | Uso |
|---|---|---|---|
| Primario | `--color-primario` | `#4a4e2d` | Botones principales, títulos, pie |
| Primario oscuro | `--color-primario-oscuro` | `#3a3d22` | Hover del primario |
| Primario tenue | `--color-primario-tenue` | `#e9eade` | Fondos suaves, badges |
| Secundario | `--color-secundario` | `#dddad2` | Bordes, fondos de tarjetas |
| Fondo | `--color-fondo` | `#f9f7f5` | Fondo general (off-white) |
| Superficie | `--color-superficie` | `#ffffff` | Tarjetas y formularios |
| Acento | `--color-acento` | `#a47c62` | Precios y llamados a la acción |
| Acento tenue | `--color-acento-tenue` | `#f3e9e2` | Fondos de apoyo |

Tipografías: *Cormorant Garamond* (títulos) e *Inter* (texto).

---

## 5. Variables de entorno (`.env`)

```bash
DJANGO_SECRET_KEY=...            # obligatorio cambiarlo en producción
DJANGO_DEBUG=True                # False en producción
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://diaromas.cl

POSTGRES_DB=diaromas
POSTGRES_USER=diaromas
POSTGRES_PASSWORD=cambia-esto
POSTGRES_HOST=db                 # "localhost" si Django corre fuera de Docker
POSTGRES_PORT=5432
POSTGRES_CONNECT_TIMEOUT=5       # evita que la app se cuelgue si la BD no responde

WHATSAPP_NUMBER=56987654321      # solo dígitos, formato internacional
CURRENCY=CLP
IVA_RATE=0.19
IVA_INCLUDED=True                # los precios del catálogo ya incluyen IVA
NOMBRE_NEGOCIO=Diaromas
CONDICION_ENVIO=Envío a coordinar con el negocio

DJANGO_SEED_ON_START=1           # carga data/productos.json al arrancar
DJANGO_COLLECTSTATIC=0
```

También se acepta `DATABASE_URL=postgresql://usuario:clave@host:5432/db`, que tiene
prioridad sobre las variables `POSTGRES_*`.

> **¿La web se queda en “esperando a PostgreSQL”?**
> Si el contenedor de Django no logra conectarse al servicio `db`, puede ser que el
> entorno tenga bloqueado el tráfico entre contenedores. El compose publica el puerto
> 5432 y agrega `host.docker.internal`, así que basta con cambiar en tu `.env`:
> ```bash
> POSTGRES_HOST=host.docker.internal
> ```
> y volver a levantar con `docker compose up -d`.

---

## 6. Catálogo en JSON

`data/productos.json` tiene dos listas: `categorias` y `productos`. Cada producto se
identifica por `slug`, así que el comando se puede ejecutar cuantas veces quieras:

```bash
make seed                                   # crea o actualiza
python manage.py cargar_catalogo --desactivar  # desactiva los que no estén en el JSON
python manage.py cargar_catalogo --archivo data/otro.json
```

```json
{
  "nombre": "Difusor Varillas Lavanda y Vainilla",
  "slug": "difusor-varillas-lavanda-vainilla",
  "categoria": "difusores",
  "descripcion_corta": "Relaxante y envolvente, ideal para dormir.",
  "notas_aroma": "Lavanda · Vainilla · Almizclado",
  "volumen_ml": 200,
  "duracion_horas": 2160,
  "precio": 18990,
  "precio_anterior": null,
  "stock": 24,
  "destacado": true,
  "activo": true
}
```

---

## 7. Cómo funciona la compra

```
Catálogo  →  carrito (sesión)  →  datos de entrega  →  pedido en BD  →  WhatsApp
```

1. El carrito se guarda en la sesión como `{id_producto: cantidad}`; los precios
   siempre se leen de la base de datos (`apps/pedidos/cart.py`).
2. El checkout valida stock, dirección y teléfono (`apps/pedidos/forms.py`).
3. `crear_pedido_desde_carrito()` crea el `Pedido` + `ItemPedido` en una transacción
   y descuenta el stock con bloqueo de fila.
4. `construir_mensaje_whatsapp()` arma el resumen en texto y `enlace_whatsapp()`
   devuelve la URL `https://wa.me/<WHATSAPP_NUMBER>?text=...`.
5. La página de confirmación redirige automáticamente a WhatsApp y, si el navegador
   lo bloquea, muestra el botón manual. El cliente también puede **reenviar** el
   pedido desde «Mis pedidos».

```
🕯️ NUEVO PEDIDO DIAROMAS
Código: DR-8F3A21

👤 Cliente: María Pérez
📞 Teléfono: +56 9 1234 5678
📧 Email: maria@email.cl

📦 Entrega: Envío a domicilio
   Calle Falsa 123 · Providencia · Metropolitana

🛒 Productos (2 líneas):
1. Difusor Varillas Lavanda y Vainilla
   2 × $18.990 = $37.980
2. Vela Aromática Cera Vegetal Sándalo
   1 × $24.990 = $24.990

—————————————
Subtotal: $62.980
(IVA 19% incluido en los precios)
Envío: Envío a coordinar con el negocio
✅ TOTAL: $62.980
```

---

## 8. Modelos

**`catalogo`**
- `Categoria`: nombre, slug, descripción, orden, activa.
- `Producto`: nombre, slug, categoría, descripciones, notas de aroma, volumen,
  duración, precio (IVA incluido), precio anterior, imagen, stock, activo, destacado.
- `ImagenProducto`: galería del producto.

**`pedidos`**
- `Pedido`: código (`DR-XXXXXX`), usuario (opcional), datos del cliente, entrega,
  dirección, subtotal, total, estado y fecha de envío de WhatsApp.
  Estados: `PENDIENTE → CONFIRMADO → EN_PREPARACION → ENVIADO → ENTREGADO` (+ `CANCELADO`).
- `ItemPedido`: copia del nombre y del precio del producto en el momento de la
  compra, para que los pedidos históricos no cambien.

**`accounts`**
- `Profile`: teléfono, fecha de nacimiento, aromas favoritos (se crea por señal).

---

## 9. Tests y calidad

```bash
make test          # dentro del contenedor
# o con el .venv local:
.venv/bin/python manage.py test
.venv/bin/ruff check .
```

Cobertura actual: carrito (sesión, stock, vaciado), vistas del carrito, checkout,
creación de pedidos, mensaje y enlace de WhatsApp, catálogo (filtros, búsqueda,
orden), comando `cargar_catalogo` y cuentas (registro, login, perfil).

---

## 10. Producción

```bash
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<clave larga y aleatoria>
DJANGO_ALLOWED_HOSTS=diaromas.cl
CSRF_TRUSTED_ORIGINS=https://diaromas.cl
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_COOKIES=True
DJANGO_HSTS_SECONDS=31536000
DJANGO_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_HSTS_PRELOAD=True
DJANGO_TRUST_PROXY=True      # detrás de Nginx/Caddy/Cloudflare
DJANGO_COLLECTSTATIC=1
```

```bash
docker compose build web
docker compose run --rm web gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

El `Dockerfile` ya incluye WhiteNoise para servir los estáticos. En producción se
recomienda poner un proxy inverso (Caddy/Nginx) con HTTPS y respaldar el volumen
`pgdata`. Con esas variables `manage.py check --deploy` no reporta ningún aviso.

---

## 11. Git

```bash
git add .
git commit -m "chore: tienda Diaromas con Django, PostgreSQL y checkout por WhatsApp"
git branch -M main
git remote add origin https://github.com/<tu-usuario>/diaromas.cl.git
git push -u origin main
```

`.gitignore` ya excluye `.env`, `.venv/`, `media/`, `staticfiles/` y la base de datos
local.

---

<div align="center">
  <sub>Hecho con calma, como una vela bien encendida.</sub>
</div>