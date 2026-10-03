"""Modelos del catálogo: categorías y productos aromatizantes."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.templatetags.static import static
from django.urls import reverse
from django.utils.text import slugify


class Categoria(models.Model):
    """Familia de productos (Difusores, Aromatizantes, Kits...)."""

    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveSmallIntegerField(
        default=0, help_text="Orden en que aparece en el menú (menor primero)."
    )
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["orden", "nombre"]

    def __str__(self) -> str:
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        return super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return f"{reverse('catalogo:listar')}?categoria={self.slug}"


class Producto(models.Model):
    """Producto del catálogo. El precio incluye IVA."""

    nombre = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos",
        verbose_name="categoría",
    )
    descripcion_corta = models.CharField(
        max_length=200,
        help_text="Texto breve que aparece en la tarjeta del producto.",
    )
    descripcion = models.TextField(
        blank=True, help_text="Descripción completa (material, uso y cuidado)."
    )
    notas_aroma = models.CharField(
        max_length=200,
        blank=True,
        help_text="Notas de aroma, por ejemplo: Lavanda · Bergamota · Vainilla",
    )
    volumen_ml = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="volumen (ml)"
    )
    duracion_horas = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="duración (horas)"
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        validators=[MinValueValidator(Decimal("1"))],
        help_text="Precio en CLP con IVA incluido.",
    )
    precio_anterior = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text="Precio antes de la promoción (opcional, para mostrar descuento).",
    )
    imagen = models.ImageField(
        upload_to="productos/%Y/%m/", blank=True, null=True, verbose_name="imagen"
    )
    stock = models.PositiveIntegerField(default=20)
    activo = models.BooleanField(default=True)
    destacado = models.BooleanField(
        default=False, help_text="Aparece en la portada dentro de 'Destacados'."
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["-destacado", "nombre"]
        indexes = [
            models.Index(fields=["activo", "categoria"]),
        ]

    def __str__(self) -> str:
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nombre)[:150] or "producto"
            slug = base
            contador = 2
            while Producto.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{contador}"
                contador += 1
            self.slug = slug
        return super().save(*args, **kwargs)

    def clean(self):
        errors = {}
        if (
            self.precio_anterior
            and self.precio
            and self.precio_anterior <= self.precio
        ):
            errors["precio_anterior"] = (
                "El precio anterior debe ser mayor que el precio actual."
            )
        if self.volumen_ml is not None and self.volumen_ml < 0:
            errors["volumen_ml"] = "El volumen no puede ser negativo."
        if errors:
            raise ValidationError(errors)

    def get_absolute_url(self) -> str:
        return reverse("catalogo:detalle", kwargs={"slug": self.slug})

    @property
    def imagen_url(self) -> str:
        """
        URL de la imagen: la foto subida por el admin o, si no hay, una
        ilustración estática asociada al slug del producto.
        """
        if self.imagen:
            return self.imagen.url
        return static(f"img/productos/{self.slug}.svg")

    @property
    def disponible(self) -> bool:
        return self.activo and self.stock > 0

    @property
    def agotado(self) -> bool:
        return self.stock == 0

    @property
    def porcentaje_descuento(self) -> int:
        if not self.precio_anterior or self.precio_anterior <= self.precio:
            return 0
        descuento = (self.precio_anterior - self.precio) / self.precio_anterior * 100
        return int(descuento)

    @property
    def etiqueta_volumen(self) -> str:
        if self.volumen_ml:
            if self.volumen_ml >= 1000:
                return f"{self.volumen_ml / 1000:g} L"
            return f"{self.volumen_ml} ml"
        return ""

    @property
    def etiqueta_duracion(self) -> str:
        if not self.duracion_horas:
            return ""
        if self.duracion_horas >= 24:
            horas = self.duracion_horas / 24
            return f"{horas:g} días de duración"
        return f"{self.duracion_horas} h de duración"

    @property
    def lista_notas(self) -> list[str]:
        if not self.notas_aroma:
            return []
        return [nota.strip() for nota in self.notas_aroma.split("·") if nota.strip()]


class ImagenProducto(models.Model):
    """Imágenes adicionales de un producto (galería)."""

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="galeria"
    )
    imagen = models.ImageField(upload_to="productos/%Y/%m/")
    orden = models.PositiveSmallIntegerField(default=0)
    es_principal = models.BooleanField(default=False)

    class Meta:
        verbose_name = "imagen de producto"
        verbose_name_plural = "imágenes de producto"
        ordering = ["orden", "id"]

    def __str__(self) -> str:
        return f"Imagen de {self.producto.nombre}"

    def save(self, *args, **kwargs):
        if self.es_principal:
            ImagenProducto.objects.filter(producto=self.producto).exclude(
                pk=self.pk
            ).update(es_principal=False)
        return super().save(*args, **kwargs)