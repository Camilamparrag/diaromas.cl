"""URLs del catálogo."""

from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("catalogo/", views.lista_productos, name="listar"),
    path("producto/<slug:slug>/", views.detalle_producto, name="detalle"),
]