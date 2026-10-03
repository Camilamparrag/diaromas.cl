"""Vistas del carrito, checkout y puente a WhatsApp."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalogo.models import Producto

from .cart import Carrito
from .forms import CheckoutForm
from .models import Pedido
from .services import (
    construir_mensaje_whatsapp,
    crear_pedido_desde_carrito,
    enlace_whatsapp,
    pedido_accesible,
    registrar_pedido_en_sesion,
)


def _volver_a(request, destino: str):
    """Redirige de vuelta a la página de origen de forma segura."""
    permitido = destino.startswith("/") and not destino.startswith("//")
    return redirect(destino if permitido and "?" not in destino else "pedidos:carrito")


# --- Carrito ----------------------------------------------------------------
def detalle_carrito(request):
    """Muestra el contenido del carrito."""
    carro = Carrito(request)
    return render(
        request,
        "pedidos/carrito.html",
        {"items": carro.items()},
    )


@require_POST
def agregar_al_carrito(request, producto_id):
    """Agrega un producto al carrito y vuelve al lugar de origen."""
    producto = get_object_or_404(Producto, pk=producto_id, activo=True)

    if producto.stock < 1:
        messages.warning(request, f"'{producto.nombre}' está agotado por ahora.")
        return _volver_a(request, request.POST.get("volver", ""))

    try:
        cantidad = int(request.POST.get("cantidad", 1))
    except (TypeError, ValueError):
        cantidad = 1

    carro = Carrito(request)
    carro.agregar(producto, cantidad)

    if request.POST.get("ir_al_carrito") == "1":
        messages.success(request, f"'{producto.nombre}' se agregó a tu carrito.")
        return redirect("pedidos:carrito")

    messages.success(request, f"'{producto.nombre}' se agregó a tu carrito.")
    return _volver_a(request, request.POST.get("volver", ""))


@require_POST
def actualizar_carrito(request):
    """Actualiza las cantidades enviadas desde la vista del carrito."""
    carro = Carrito(request)
    cantidades = request.POST.getlist("cantidad[]") or request.POST.getlist("cantidad")
    ids = request.POST.getlist("producto_id[]") or request.POST.getlist("producto_id")

    actualizados = 0
    for indice, producto_id in enumerate(ids):
        try:
            cantidad = int(cantidades[indice])
        except (IndexError, TypeError, ValueError):
            continue
        carro.actualizar(producto_id, cantidad)
        actualizados += 1

    if actualizados:
        messages.success(request, "Carrito actualizado.")
    else:
        messages.warning(request, "No pudimos actualizar el carrito.")

    return redirect("pedidos:carrito")


@require_POST
def quitar_del_carrito(request, producto_id):
    """Elimina una línea del carrito."""
    carro = Carrito(request)
    producto = carro.productos().get(int(producto_id)) if str(producto_id).isdigit() else None
    carro.quitar(producto_id)
    if producto:
        messages.info(request, f"'{producto.nombre}' salió del carrito.")
    return redirect("pedidos:carrito")


@require_POST
def vaciar_carrito(request):
    Carrito(request).vaciar()
    messages.info(request, "Vaciamos tu carrito.")
    return redirect("catalogo:listar")


# --- Checkout ---------------------------------------------------------------
def checkout(request):
    """Formulario de datos del cliente y creación del pedido."""
    carro = Carrito(request)

    if carro.es_vacio:
        messages.warning(request, "Tu carrito está vacío.")
        return redirect("catalogo:listar")

    if request.method == "POST":
        form = CheckoutForm(request.POST, usuario=request.user)
        if form.is_valid():
            try:
                pedido = crear_pedido_desde_carrito(
                    carro,
                    form.cleaned_data,
                    user=request.user if request.user.is_authenticated else None,
                )
            except ValueError as error:
                messages.error(request, str(error))
                return redirect("pedidos:carrito")

            carro.vaciar()
            registrar_pedido_en_sesion(request, pedido)
            return redirect("pedidos:confirmacion", code=pedido.code)
        messages.error(request, "Revisa los datos para completar el pedido.")
    else:
        form = CheckoutForm(usuario=request.user)

    return render(
        request,
        "pedidos/checkout.html",
        {"form": form, "items": carro.items()},
    )


def confirmacion(request, code):
    """Resumen del pedido + redirección automática a WhatsApp."""
    pedido = get_object_or_404(Pedido, code=code.upper())

    if not pedido_accesible(request, pedido):
        messages.error(request, "No tienes acceso a ese pedido.")
        return redirect("pedidos:mis_pedidos")

    return render(
        request,
        "pedidos/confirmacion.html",
        {
            "pedido": pedido,
            "mensaje_whatsapp": construir_mensaje_whatsapp(pedido),
            "enlace_whatsapp": enlace_whatsapp(pedido),
        },
    )


def whatsapp_pedido(request, code):
    """Registra que se abrió WhatsApp y redirige al chat del negocio."""
    pedido = get_object_or_404(Pedido, code=code.upper())

    if not pedido_accesible(request, pedido):
        messages.error(request, "No tienes acceso a ese pedido.")
        return redirect("pedidos:mis_pedidos")

    pedido.marcar_whatsapp_enviado()
    return redirect(enlace_whatsapp(pedido))


# --- Pedidos del usuario ----------------------------------------------------
@login_required
def mis_pedidos(request):
    """Historial de pedidos del cliente registrado."""
    pedidos = Pedido.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "pedidos/mis_pedidos.html", {"pedidos": pedidos})


def detalle_pedido(request, code):
    """
    Detalle de un pedido propio. También accesible para un cliente invitado
    mientras su código siga guardado en la sesión del navegador.
    """
    pedido = get_object_or_404(Pedido.objects.prefetch_related("items"), code=code.upper())

    if not pedido_accesible(request, pedido):
        messages.error(request, "Ese pedido no está asociado a tu cuenta.")
        return redirect("pedidos:mis_pedidos")

    return render(
        request,
        "pedidos/detalle.html",
        {
            "pedido": pedido,
            "mensaje_whatsapp": construir_mensaje_whatsapp(pedido),
            "enlace_whatsapp": enlace_whatsapp(pedido),
        },
    )