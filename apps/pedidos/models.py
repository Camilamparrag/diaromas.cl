"""Modelos de pedidos: cabecera (Order) y detalle (OrderItem)."""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


def generar_codigo() -> str:
    """Código corto y legible, por ejemplo DR-8F3A21."""
    return f"DR-{uuid.uuid4().hex[:6].upper()}"


class Pedido(models.Model):
    """Pedido generado desde el carrito y negociado por WhatsApp."""

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente por WhatsApp"
        CONFIRMADO = "CONFIRMADO", "Confirmado"
        EN_PREPARACION = "EN_PREPARACION", "En preparación"
        ENVIADO = "ENVIADO", "Enviado"
        ENTREGADO = "ENTREGADO", "Entregado"
        CANCELADO = "CANCELADO", "Cancelado"

    class Entrega(models.TextChoices):
        ENVIO = "ENVIO", "Envío a domicilio"
        RETIRO = "RETIRO", "Retiro en el local"

    code = models.CharField(max_length=12, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos",
        verbose_name="usuario",
    )

    # Datos del cliente (copia: el pedido no depende del estado del perfil)
    cliente_nombre = models.CharField(max_length=150, verbose_name="nombre del cliente")
    cliente_email = models.EmailField(blank=True)
    cliente_telefono = models.CharField(max_length=30, verbose_name="teléfono")

    # Entrega
    entrega = models.CharField(
        max_length=10, choices=Entrega.choices, default=Entrega.ENVIO
    )
    direccion = models.CharField(max_length=250, blank=True)
    comuna = models.CharField(max_length=80, blank=True)
    region = models.CharField(max_length=80, blank=True)
    notas = models.TextField(blank=True)

    # Totales (los precios del catálogo ya incluyen IVA)
    subtotal = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    total = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    moneda = models.CharField(max_length=5, default=settings.CURRENCY)

    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    whatsapp_enviado_en = models.DateTimeField(null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    confirmado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["estado", "-creado_en"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.cliente_nombre}"

    def save(self, *args, **kwargs):
        if not self.code:
            # Garantiza unicidad aunque haya colisiones improbables
            for _ in range(5):
                self.code = generar_codigo()
                if not Pedido.objects.filter(code=self.code).exists():
                    break
        if self.estado == self.Estado.CONFIRMADO and not self.confirmado_en:
            self.confirmado_en = timezone.now()
        return super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("pedidos:detalle", kwargs={"code": self.code})

    @property
    def total_items(self) -> int:
        """Número de líneas del pedido."""
        return self.items.count()

    @property
    def unidades(self) -> int:
        return sum(item.cantidad for item in self.items.all())

    @property
    def estado_label(self) -> str:
        return self.get_estado_display()

    @property
    def entrega_label(self) -> str:
        return self.get_entrega_display()

    @property
    def es_envio(self) -> bool:
        return self.entrega == self.Entrega.ENVIO

    @property
    def direccion_completa(self) -> str:
        partes = [self.direccion, self.comuna, self.region]
        return " · ".join(parte for parte in partes if parte)

    @property
    def estado_paso(self) -> int:
        """Posición del estado en la línea de tiempo (para pintar el stepper)."""
        orden = [
            self.Estado.PENDIENTE,
            self.Estado.CONFIRMADO,
            self.Estado.EN_PREPARACION,
            self.Estado.ENVIADO,
            self.Estado.ENTREGADO,
        ]
        if self.estado == self.Estado.CANCELADO:
            return 0
        try:
            return orden.index(self.estado)
        except ValueError:
            return 0

    def puede_cancelar(self) -> bool:
        return self.estado in {self.Estado.PENDIENTE, self.Estado.CONFIRMADO}

    def marcar_whatsapp_enviado(self) -> None:
        if not self.whatsapp_enviado_en:
            self.whatsapp_enviado_en = timezone.now()
            self.save(update_fields=["whatsapp_enviado_en", "actualizado_en"])


class ItemPedido(models.Model):
    """Línea de pedido con copia de los datos del producto en el momento de compra."""

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_pedido",
    )
    producto_nombre = models.CharField(max_length=160)
    producto_slug = models.CharField(max_length=180, blank=True)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=0)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "ítem de pedido"
        verbose_name_plural = "ítems de pedido"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.cantidad} × {self.producto_nombre}"

    @property
    def subtotal(self) -> Decimal:
        return self.precio_unitario * self.cantidad

    @property
    def producto_activo(self) -> bool:
        """True si el producto sigue existiendo en el catálogo."""
        return self.producto is not None and self.producto.activo