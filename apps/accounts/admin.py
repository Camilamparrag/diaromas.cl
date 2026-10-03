"""Administración de perfiles y pedidos de clientes."""

from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "telefono", "recibe_novedades", "creado_en")
    list_filter = ("recibe_novedades",)
    search_fields = ("user__username", "user__email", "user__first_name", "telefono")
    autocomplete_fields = ("user",)