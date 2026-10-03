"""URLs raíz del proyecto Diaromas."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.catalogo.views import home

urlpatterns = [
    # La portada vive fuera del namespace de catálogo para poder usarla como
    # 'home' (LOGIN_REDIRECT_URL, redirecciones, etc.).
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("cuentas/", include("apps.accounts.urls")),
    path("", include("apps.catalogo.urls")),
    path("", include("apps.pedidos.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = "config.views.pagina_no_encontrada"
handler500 = "config.views.error_servidor"