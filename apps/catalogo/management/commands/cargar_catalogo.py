"""
Carga (o actualiza) el catálogo inicial desde data/productos.json.

Es idempotente: los productos se identifican por `slug`, así que puedes
ejecutarlo las veces que quieras sin duplicar registros.

    python manage.py cargar_catalogo
    python manage.py cargar_catalogo --archivo data/otro.json --desactivar
"""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.catalogo.models import Categoria, Producto

ARCHIVO_POR_DEFECTO = Path(__file__).resolve().parents[4] / "data" / "productos.json"


class Command(BaseCommand):
    help = "Crea o actualiza categorías y productos desde un archivo JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--archivo",
            type=Path,
            default=ARCHIVO_POR_DEFECTO,
            help="Ruta del JSON con el catálogo (por defecto data/productos.json).",
        )
        parser.add_argument(
            "--desactivar",
            action="store_true",
            help="Desactiva los productos que no estén en el JSON.",
        )
        parser.add_argument(
            "--vaciar",
            action="store_true",
            help="Elimina los productos del JSON antes de recrearlos.",
        )

    def handle(self, *args, **options):
        archivo: Path = options["archivo"]

        if not archivo.exists():
            raise CommandError(f"No existe el archivo: {archivo}")

        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise CommandError(f"JSON inválido en {archivo}: {error}") from error

        categorias = datos.get("categorias", [])
        productos = datos.get("productos", [])
        if not isinstance(categorias, list) or not isinstance(productos, list):
            raise CommandError(
                "El JSON debe tener las claves 'categorias' y 'productos' como listas."
            )

        with transaction.atomic():
            mapa_categorias = self._sincronizar_categorias(categorias)
            slugs = self._sincronizar_productos(
                productos, mapa_categorias, options
            )

            if options["desactivar"]:
                desactivados = Producto.objects.exclude(slug__in=slugs).update(activo=False)
                self.stdout.write(
                    f"   {desactivados} producto(s) desactivados por --desactivar"
                )

        self.stdout.write(self.style.SUCCESS(f"\n-> Listo. {len(slugs)} producto(s) en catálogo."))
        self.stdout.write("-> Siguiente paso: python manage.py createsuperuser")

    # --- Helpers -------------------------------------------------------------
    @transaction.atomic
    def _sincronizar_categorias(self, definiciones: list[dict]) -> dict[str, Categoria]:
        mapa: dict[str, Categoria] = {}
        self.stdout.write(f"\nCategorías ({len(definiciones)}):")

        for orden, definicion in enumerate(definiciones, start=1):
            nombre = (definicion.get("nombre") or "").strip()
            if not nombre:
                continue
            slug = definicion.get("slug") or slugify(nombre)
            categoria, creado = Categoria.objects.update_or_create(
                slug=slug,
                defaults={
                    "nombre": nombre,
                    "descripcion": definicion.get("descripcion", ""),
                    "orden": definicion.get("orden", orden),
                    "activa": definicion.get("activa", True),
                },
            )
            mapa[slug] = categoria
            self.stdout.write(
                f"   + {categoria.nombre} ({'nueva' if creado else 'actualizada'})"
            )

        return mapa

    @transaction.atomic
    def _sincronizar_productos(
        self,
        definiciones: list[dict],
        mapa_categorias: dict[str, Categoria],
        opciones: dict,
    ) -> list[str]:
        self.stdout.write(f"\nProductos ({len(definiciones)}):")
        slugs: list[str] = []

        for definicion in definiciones:
            nombre = (definicion.get("nombre") or "").strip()
            slug = definicion.get("slug") or slugify(nombre)
            if not nombre:
                continue

            slug_categoria = definicion.get("categoria") or ""
            categoria = mapa_categorias.get(slug_categoria)
            if categoria is None:
                categoria = Categoria.objects.filter(slug=slug_categoria).first()
            if categoria is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"   ! {nombre}: categoría '{slug_categoria}' no encontrada, se omite."
                    )
                )
                continue

            defaults = {
                "nombre": nombre,
                "categoria": categoria,
                "descripcion_corta": definicion.get("descripcion_corta", ""),
                "descripcion": definicion.get("descripcion", ""),
                "notas_aroma": definicion.get("notas_aroma", ""),
                "volumen_ml": definicion.get("volumen_ml"),
                "duracion_horas": definicion.get("duracion_horas"),
                "precio": self._precio(definicion, "precio"),
                "precio_anterior": self._precio(definicion, "precio_anterior"),
                "imagen": definicion.get("imagen") or "",
                "stock": definicion.get("stock", 20),
                "activo": definicion.get("activo", True),
                "destacado": definicion.get("destacado", False),
            }

            if opciones["vaciar"]:
                Producto.objects.filter(slug=slug).delete()

            _producto, creado = Producto.objects.update_or_create(slug=slug, defaults=defaults)
            slugs.append(slug)
            icono = "nuevo" if creado else "actualizado"
            self.stdout.write(
                f"   + {nombre} — ${defaults['precio']:,.0f}".replace(",", ".")
                + f" ({icono})"
            )

        return slugs

    def _precio(self, definicion: dict, clave: str) -> Decimal:
        valor = definicion.get(clave)
        if valor in (None, ""):
            return Decimal("0") if clave == "precio" else None
        try:
            return Decimal(str(valor)).quantize(Decimal("1"))
        except (InvalidOperation, ValueError) as error:
            raise CommandError(
                f"'{clave}' inválido ({valor!r}) en el producto "
                f"{definicion.get('nombre', definicion.get('slug'))}"
            ) from error