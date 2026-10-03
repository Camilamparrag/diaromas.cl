"""Modelos de cuentas: perfil asociado al usuario de Django."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    """Datos extra del cliente, útiles para el pedido por WhatsApp."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
        verbose_name="usuario",
    )
    telefono = models.CharField(
        max_length=30,
        blank=True,
        help_text="Incluye el código de país, por ejemplo +56 9 1234 5678",
    )
    fecha_nacimiento = models.DateField(null=True, blank=True)
    aromas_favoritos = models.CharField(
        max_length=200,
        blank=True,
        help_text="Notas de aroma o familias que prefieres (opcional)",
    )
    recibe_novedades = models.BooleanField(
        default=False, verbose_name="Quiero recibir novedades"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfiles"

    def __str__(self) -> str:
        return f"Perfil de {self.user.get_username()}"

    @property
    def nombre_para_pedido(self) -> str:
        nombre = (self.user.first_name or "").strip()
        apellido = (self.user.last_name or "").strip()
        completo = f"{nombre} {apellido}".strip()
        return completo or self.user.get_username()

    @property
    def necesita_datos(self) -> bool:
        """True si aún no tenga datos suficientes para cerrar un pedido."""
        return not self.telefono or not (self.user.first_name or self.user.last_name)

    @property
    def antiguedad(self) -> str:
        dias = (timezone.now() - self.creado_en).days
        if dias < 1:
            return "Hoy"
        if dias == 1:
            return "Ayer"
        return f"Desde hace {dias} días"