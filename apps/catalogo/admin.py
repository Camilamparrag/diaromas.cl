"""Administración del catálogo."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Categoria, ImagenProducto, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "orden", "activa", "total_productos")
    list_filter = ("activa",)
    search_fields = ("nombre",)
    prepopulated_fields = {"slug": ("nombre",)}
    ordering = ("orden", "nombre")

    @admin.display(description="Productos")
    def total_productos(self, obj) -> int:
        return obj.productos.count()


class ImagenProductoInline(admin.TabularInline):
    model = ImagenProducto
    extra = 1
    fields = ("imagen", "orden", "es_principal")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "miniatura",
        "nombre",
        "categoria",
        "precio",
        "precio_anterior",
        "stock",
        "activo",
        "destacado",
    )
    list_filter = ("activo", "destacado", "categoria", "stock")
    search_fields = ("nombre", "descripcion_corta", "descripcion", "notas_aroma")
    prepopulated_fields = {"slug": ("nombre",)}
    inlines = [ImagenProductoInline]
    list_select_related = ("categoria",)
    ordering = ("-destacado", "nombre")
    fieldsets = (
        ("Identificación", {"fields": ("nombre", "slug", "categoria", "descripcion_corta")}),
        ("Detalle", {"fields": ("descripcion", "notas_aroma", "volumen_ml", "duracion_horas")}),
        ("Precio e inventario", {"fields": ("precio", "precio_anterior", "stock")}),
        ("Visibilidad", {"fields": ("imagen", "activo", "destacado")}),
    )
    actions = ("marcar_destacado", "desactivar_productos")

    @admin.display(description="Imagen")
    def miniatura(self, obj):
        if not obj.imagen:
            return "—"
        return format_html(
            '<img src="{}" style="height:48px;border-radius:8px;object-fit:cover;">',
            obj.imagen.url,
        )

    @admin.action(description="Marcar como destacado")
    def marcar_destacado(self, request, queryset):
        total = queryset.update(destacado=True)
        self.message_user(request, f"{total} producto(s) marcados como destacado.")

    @admin.action(description="Desactivar productos")
    def desactivar_productos(self, request, queryset):
        total = queryset.update(activo=False)
        self.message_user(request, f"{total} producto(s) desactivados.")