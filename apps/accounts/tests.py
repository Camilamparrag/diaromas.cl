"""Tests de cuentas: registro, inicio de sesión, perfil y perfil automático."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Profile

User = get_user_model()


class RegistroTests(TestCase):
    def test_crear_cuenta_crea_perfil_y_inicia_sesion(self):
        respuesta = self.client.post(
            reverse("accounts:registro"),
            {
                "username": "nueva",
                "first_name": "Camila",
                "last_name": "Pérez",
                "email": "camila@email.cl",
                "telefono": "+56 9 8888 7777",
                "password1": " aroma-muy-seguro-99",
                "password2": " aroma-muy-seguro-99",
                "acepta_terminos": "on",
            },
        )

        self.assertRedirects(respuesta, reverse("home"))
        usuario = User.objects.get(username="nueva")
        self.assertEqual(usuario.email, "camila@email.cl")
        self.assertTrue(Profile.objects.filter(user=usuario).exists())
        self.assertEqual(usuario.perfil.telefono, "+56 9 8888 7777")

        respuesta = self.client.get(reverse("home"))
        self.assertTrue(respuesta.wsgi_request.user.is_authenticated)

    def test_email_duplicado_no_permite_registro(self):
        User.objects.create_user(
            username="existente", password="clave-segura-123", email="dup@email.cl"
        )
        respuesta = self.client.post(
            reverse("accounts:registro"),
            {
                "username": "otro",
                "first_name": "Otro",
                "last_name": "Usuario",
                "email": "dup@email.cl",
                "password1": " aroma-muy-seguro-99",
                "password2": " aroma-muy-seguro-99",
                "acepta_terminos": "on",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("email", respuesta.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_terminios_obligatorios(self):
        respuesta = self.client.post(
            reverse("accounts:registro"),
            {
                "username": "sin-terminos",
                "first_name": "Sin",
                "last_name": "Terminos",
                "email": "sin@email.cl",
                "password1": " aroma-muy-seguro-99",
                "password2": " aroma-muy-seguro-99",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("acepta_terminos", respuesta.context["form"].errors)
        self.assertFalse(User.objects.filter(username="sin-terminos").exists())

    def test_usuario_logueado_no_ve_el_registro(self):
        User.objects.create_user(username="ya", password="clave-segura-123")
        self.client.force_login(User.objects.get(username="ya"))
        respuesta = self.client.get(reverse("accounts:registro"))
        self.assertRedirects(respuesta, reverse("home"))


class SesionTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username="pedro", password="clave-segura-123", email="pedro@email.cl"
        )

    def test_login_exitoso(self):
        respuesta = self.client.post(
            reverse("accounts:login"),
            {"username": "pedro", "password": "clave-segura-123"},
        )
        self.assertRedirects(respuesta, reverse("home"))

    def test_login_incorrecto(self):
        respuesta = self.client.post(
            reverse("accounts:login"), {"username": "pedro", "password": "mala"}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Usuario o contraseña incorrectos")

    def test_logout_requiere_post(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse("accounts:logout"))
        self.assertEqual(respuesta.status_code, 405)

        respuesta = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(respuesta, reverse("home"))

        self.assertFalse(
            self.client.get(reverse("home")).wsgi_request.user.is_authenticated
        )


class PerfilTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username="maria", password="clave-segura-123", email="maria@email.cl"
        )
        self.perfil = Profile.objects.get(user=self.usuario)

    def test_requiere_login(self):
        respuesta = self.client.get(reverse("accounts:perfil"))
        self.assertEqual(respuesta.status_code, 302)

    def test_actualiza_datos(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.post(
            reverse("accounts:perfil"),
            {
                "first_name": "María",
                "last_name": "Pérez",
                "email": "maria.nueva@email.cl",
                "telefono": "+56 9 1234 5678",
                "aromas_favoritos": "Lavanda",
                "recibe_novedades": "on",
            },
        )

        self.assertRedirects(respuesta, reverse("accounts:perfil"))
        self.usuario.refresh_from_db()
        self.perfil.refresh_from_db()
        self.assertEqual(self.usuario.first_name, "María")
        self.assertEqual(self.usuario.email, "maria.nueva@email.cl")
        self.assertEqual(self.perfil.telefono, "+56 9 1234 5678")
        self.assertTrue(self.perfil.recibe_novedades)

    def test_necesita_datos(self):
        self.assertTrue(self.perfil.necesita_datos)
        self.perfil.telefono = "+56 9 1234 5678"
        self.perfil.user.first_name = "María"
        self.perfil.user.last_name = "Pérez"
        self.perfil.user.save()
        self.assertFalse(self.perfil.necesita_datos)

    def test_señal_crea_perfil_automaticamente(self):
        nuevo = User.objects.create_user(username="nuevo", password="clave-segura-123")
        self.assertTrue(Profile.objects.filter(user=nuevo).exists())