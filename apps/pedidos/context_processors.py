"""Context processor: datos globales del carrito y del contacto de WhatsApp."""

from django.conf import settings

from .cart import Carrito
from .services import ICONOS, formatear_telefono


def carrito(request):
    carro = Carrito(request)
    numero = "".join(ch for ch in settings.WHATSAPP_NUMBER if ch.isdigit())
    return {
        "carrito": carro,
        "carrito_unidades": carro.unidades,
        "carrito_subtotal": carro.subtotal,
        # Contacto del negocio (sin mensaje) para el pie de página
        "whatsapp_contacto": f"https://wa.me/{numero}",
        "whatsapp_numero": formatear_telefono(settings.WHATSAPP_NUMBER),
        "negocio_nombre": settings.NOMBRE_NEGOCIO,
        "icono_whatsapp": ICONOS["encabezado"],
    }