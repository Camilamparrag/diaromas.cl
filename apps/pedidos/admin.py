"""Administración de pedidos."""

from django.contrib import admin, messages
from django.utils.html import format_html

from .models import ItemPedido, Pedido
from .services import construir_mensaje_whatsapp, enlace_whatsapp


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    fields = ("producto_nombre", "precio_unitario", "cantidad", "subtotal_calculado")
    readonly_fields = ("subtotal_calculado",)

    @admin.display(description="Subtotal")
    def subtotal_calculado(self, obj):
        return f"${obj.subtotal:,.0f}".replace(",", ".")


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "cliente_nombre",
        "cliente_telefono",
        "total",
        "unidades_display",
        "estado",
        "entrega",
        "whatsapp_enviado_en",
        "creado_en",
    )
    list_filter = ("estado", "entrega", "creado_en")
    search_fields = ("code", "cliente_nombre", "cliente_email", "cliente_telefono")
    readonly_fields = ("code", "creado_en", "actualizado_en", "confirmado_en")
    inlines = [ItemPedidoInline]
    date_hierarchy = "creado_en"
    list_select_related = ("user",)
    actions = ("marcar_confirmado", "marcar_enviado", "marcar_entregado", "ver_whatsapp")

    # Los fieldsets se arman en get_fieldsets() para sumar el botón de WhatsApp
    # solo cuando ya existe el pedido.

    @admin.display(description="Unidades")
    def unidades_display(self, obj):
        return obj.unidades

    @admin.display(description="Acciones")
    def boton_whatsapp(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Abrir chat con el cliente</a>',
            enlace_whatsapp(obj),
        )

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if obj:
            base.append("boton_whatsapp")
        return base

    def get_fieldsets(self, request, obj=None):
        camposets = [
            ("Pedido", {"fields": ("code", "user", "estado", "entrega", "whatsapp_enviado_en")}),
            ("Cliente", {"fields": ("cliente_nombre", "cliente_telefono", "cliente_email")}),
            ("Entrega", {"fields": ("direccion", "comuna", "region", "notas")}),
            (
                "Totales y fechas",
                {
                    "fields": (
                        "subtotal",
                        "total",
                        "moneda",
                        "creado_en",
                        "actualizado_en",
                        "confirmado_en",
                    )
                },
            ),
        ]
        if obj:
            camposets[0][1]["fields"] = camposets[0][1]["fields"] + ("boton_whatsapp",)
        return camposets

    # --- Acciones masivas ---
    @admin.action(description="Marcar como confirmados")
    def marcar_confirmado(self, request, queryset):
        total = 0
        for pedido in queryset:
            pedido.estado = Pedido.Estado.CONFIRMADO
            pedido.save()
            total += 1
        self.message_user(request, f"{total} pedido(s) marcados como confirmados.")

    @admin.action(description="Marcar como enviados")
    def marcar_enviado(self, request, queryset):
        total = queryset.update(estado=Pedido.Estado.ENVIADO)
        self.message_user(request, f"{total} pedido(s) marcados como enviados.")

    @admin.action(description="Marcar como entregados")
    def marcar_entregado(self, request, queryset):
        total = queryset.update(estado=Pedido.Estado.ENTREGADO)
        self.message_user(request, f"{total} pedido(s) marcados como entregados.")

    @admin.action(description="Ver mensaje de WhatsApp / copiar resumen")
    def ver_whatsapp(self, request, queryset):
        if not queryset:
            return
        pedido = queryset.first()
        self.message_user(
            request,
            f"Mensaje de {pedido.code}:\n{construir_mensaje_whatsapp(pedido)}",
            level=messages.INFO,
        )


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto_nombre", "cantidad", "precio_unitario")
    search_fields = ("producto_nombre", "pedido__code")
    list_filter = ("pedido__estado",)