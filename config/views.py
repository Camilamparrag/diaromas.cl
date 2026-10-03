"""Vistas de error rameadas por config.urls (handler404 / handler500)."""

from django.shortcuts import render


def pagina_no_encontrada(request, exception=None):
    return render(request, "404.html", status=404)


def error_servidor(request):
    return render(request, "500.html", status=500)