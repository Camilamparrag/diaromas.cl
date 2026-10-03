"""URLs de carrito, checkout y pedidos."""

from django.urls import path

from . import views

app_name = "pedidos"

urlpatterns = [
    # Carrito
    path("carrito/", views.detalle_carrito, name="carrito"),
    path("carrito/agregar/<int:producto_id>/", views.agregar_al_carrito, name="agregar"),
    path("carrito/actualizar/", views.actualizar_carrito, name="actualizar"),
    path("carrito/quitar/<int:producto_id>/", views.quitar_del_carrito, name="quitar"),
    path("carrito/vaciar/", views.vaciar_carrito, name="vaciar"),
    # Checkout y WhatsApp
    path("pedido/confirmar/", views.checkout, name="checkout"),
    path("pedido/<str:code>/confirmacion/", views.confirmacion, name="confirmacion"),
    path("pedido/<str:code>/whatsapp/", views.whatsapp_pedido, name="whatsapp"),
    # Historial
    path("mis-pedidos/", views.mis_pedidos, name="mis_pedidos"),
    path("mis-pedidos/<str:code>/", views.detalle_pedido, name="detalle"),
]