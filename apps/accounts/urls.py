"""URLs de cuentas."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "registro/",
        views.RegistroView.as_view(),
        name="registro",
    ),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    # Django 5+ solo permite el cierre de sesión por POST (protección CSRF)
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("perfil/", views.perfil, name="perfil"),
]