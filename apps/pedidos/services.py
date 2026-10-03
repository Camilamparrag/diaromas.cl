"""
Servicios del flujo de pedido por WhatsApp.

Aquí vive la lógica que transforma el carrito en un pedido persistido y luego en
un mensaje de WhatsApp listo para enviar (con el enlace wa.me).
"""

from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.db.models import F

from apps.catalogo.models import Producto

from .cart import Carrito
from .models import ItemPedido, Pedido

# Límite práctico de WhatsApp para un mensaje de texto (~4096 caracteres)
MAX_LARGO_MENSAJE = 3500

ICONOS = {
    "encabezado": "\U0001F56F",   # vela
    "cliente": "\U0001F464",      # persona
    "telefono": "\U0001F4DE",     # teléfono
    "email": "\U0001F4E7",        # correo
    "entrega": "\U0001F48D",      # paquete
    "carrito": "\U0001F6D2",      # carrito
    "total": "\U00002705",        # check
    "nota": "\U0001F4CC",         # nota
    "pedido": "\U0001F4E4",       # sobre
}


def formatear_monto(valor: Decimal | int | float) -> str:
    """CLP sin decimales y con punto como separador de miles: $18.990."""
    return "$" + f"{Decimal(valor):,.0f}".replace(",", ".")


def formatear_telefono(telefono: str) -> str:
    """Deja el teléfono legible: +56 9 1234 5678."""
    digitos = "".join(ch for ch in telefono if ch.isdigit())
    if digitos.startswith("56") and len(digitos) == 11:
        return f"+56 {digitos[2:3]} {digitos[3:7]} {digitos[7:]}"
    return telefono.strip() or "No informado"


@transaction.atomic
def crear_pedido_desde_carrito(carrito: Carrito, datos: dict, user=None) -> Pedido:
    """
    Convierte el carrito en un `Pedido` persistente y descuenta el stock.

    Lanza `ValueError` si algún producto ya no tiene stock suficiente.
    """
    items = carrito.items()
    if not items:
        raise ValueError("El carrito está vacío.")

    # Bloqueo de filas para evitar sobreventa con compras simultáneas
    ids = [item["producto"].pk for item in items]
    productos = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=ids)}

    for item in items:
        producto_bloqueado = productos.get(item["producto"].pk)
        if producto_bloqueado is None or not producto_bloqueado.activo:
            raise ValueError(f"'{item['producto'].nombre}' ya no está disponible.")
        if producto_bloqueado.stock < item["cantidad"]:
            raise ValueError(
                f"Solo quedan {producto_bloqueado.stock} unidades de "
                f"'{producto_bloqueado.nombre}'."
            )

    subtotal = sum((item["subtotal"] for item in items), Decimal("0"))

    pedido = Pedido.objects.create(
        user=user if (user and user.is_authenticated) else None,
        cliente_nombre=datos.get("cliente_nombre", "").strip(),
        cliente_email=datos.get("cliente_email", "").strip(),
        cliente_telefono=datos.get("cliente_telefono", "").strip(),
        entrega=datos.get("entrega", Pedido.Entrega.ENVIO),
        direccion=datos.get("direccion", "").strip(),
        comuna=datos.get("comuna", "").strip(),
        region=datos.get("region", "").strip(),
        notas=datos.get("notas", "").strip(),
        subtotal=subtotal,
        total=subtotal,
        moneda=settings.CURRENCY,
    )

   # Se crean todas las líneas del pedido de una sola vez
    lineas = []
    for item in items:
        producto = productos[item["producto"].pk]
        lineas.append(
            ItemPedido(
                pedido=pedido,
                producto=producto,
                producto_nombre=producto.nombre,
                producto_slug=producto.slug,
                precio_unitario=producto.precio,
                cantidad=item["cantidad"],
            )
        )
        Producto.objects.filter(pk=producto.pk).update(stock=F("stock") - item["cantidad"])

    ItemPedido.objects.bulk_create(lineas)
    return pedido


def construir_mensaje_whatsapp(pedido: Pedido) -> str:
    """
    Arma el resumen del pedido en texto plano con formato de WhatsApp.

    Usa *negrita* de WhatsApp y emojis para que se lea bien en el celular.
    """
    lineas: list[str] = []

    lineas.append(f"{ICONOS['encabezado']} *NUEVO PEDIDO {settings.NOMBRE_NEGOCIO.upper()}*")
    lineas.append(f"{ICONOS['pedido']} Código: *{pedido.code}*")
    lineas.append("")

    # --- Datos del cliente ---
    lineas.append(f"{ICONOS['cliente']} *Cliente:* {pedido.cliente_nombre}")
    lineas.append(
        f"{ICONOS['telefono']} *Teléfono:* {formatear_telefono(pedido.cliente_telefono)}"
    )
    if pedido.cliente_email:
        lineas.append(f"{ICONOS['email']} *Email:* {pedido.cliente_email}")

    # --- Entrega ---
    lineas.append("")
    lineas.append(f"{ICONOS['entrega']} *Entrega:* {pedido.entrega_label}")
    if pedido.es_envio and pedido.direccion_completa:
        lineas.append(f"   {pedido.direccion_completa}")

    # --- Detalle de productos ---
    items = list(pedido.items.all())
    lineas.append("")
    plural = "s" if len(items) != 1 else ""
    lineas.append(f"{ICONOS['carrito']} *Productos ({len(items)} línea{plural}):*")
    for indice, item in enumerate(items, start=1):
        variantes = []
        if getattr(item.producto, "etiqueta_volumen", ""):
            variantes.append(item.producto.etiqueta_volumen)
        lineas.append(f"{indice}. *{item.producto_nombre}*")
        if variantes:
            lineas.append(f"   {' · '.join(variantes)}")
        lineas.append(
            f"   {item.cantidad} × {formatear_monto(item.precio_unitario)}"
            f" = {formatear_monto(item.subtotal)}"
        )

    # --- Totales ---
    lineas.append("")
    lineas.append("—————————————")
    lineas.append(f"Subtotal: *{formatear_monto(pedido.subtotal)}*")
    if settings.IVA_INCLUDED:
        pct = (settings.IVA_RATE * 100).quantize(Decimal("1"))
        lineas.append(f"(IVA {pct}% incluido en los precios)")
    lineas.append(f"Envío: {settings.CONDICION_ENVIO}")
    lineas.append(f"{ICONOS['total']} *TOTAL: {formatear_monto(pedido.total)}*")

    if pedido.notas:
        lineas.append("")
        lineas.append(f"{ICONOS['nota']} *Notas del cliente:* {pedido.notas}")

    lineas.append("")
    lineas.append(f"Generado desde {settings.NOMBRE_NEGOCIO} 🕯️")

    mensaje = "\n".join(lineas)
    if len(mensaje) > MAX_LARGO_MENSAJE:
        mensaje = mensaje[:MAX_LARGO_MENSAJE].rsplit("\n", 1)[0] + "\n…"
    return mensaje


def enlace_whatsapp(pedido: Pedido) -> str:
    """URL wa.me con el mensaje del pedido ya codificado."""
    numero = "".join(ch for ch in settings.WHATSAPP_NUMBER if ch.isdigit())
    mensaje = quote(construir_mensaje_whatsapp(pedido))
    return f"https://wa.me/{numero}?text={mensaje}"


def registrar_pedido_en_sesion(request, pedido: Pedido) -> None:
    """
    Guarda el código del pedido en la sesión para que un cliente invitado
    (sin cuenta) pueda volver a la confirmación o al resumen.
    """
    historial = request.session.get("pedidos", [])
    historial = [codigo for codigo in historial if codigo != pedido.code]
    historial.insert(0, pedido.code)
    request.session["pedidos"] = historial[:20]
    request.session.modified = True


def pedido_accesible(request, pedido: Pedido) -> bool:
    """El usuario dueño o un invitado que creó el pedido en esta sesión."""
    if request.user.is_authenticated:
        return pedido.user_id == request.user.pk
    return pedido.code in request.session.get("pedidos", [])