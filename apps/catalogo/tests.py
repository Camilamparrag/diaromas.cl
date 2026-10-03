"""Tests del catálogo: portada, listado, detalle y carga de datos."""

import io
import json
import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Producto


class PortadaTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Difusores", orden=1)
        self.producto = Producto.objects.create(
            nombre="Difusor Lavanda",
            categoria=self.categoria,
            descripcion_corta="Relaxante",
            precio=Decimal("18990"),
            stock=5,
            destacado=True,
        )

    def test_portada_muestra_destacados(self):
        respuesta = self.client.get(reverse("home"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Difusor Lavanda")
        self.assertContains(respuesta, "$18.990")
        self.assertContains(respuesta, "Difusores")

    def test_portada_sin_productos(self):
        Producto.objects.all().delete()
        respuesta = self.client.get(reverse("home"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "cargar_catalogo")


class ListadoTests(TestCase):
    def setUp(self):
        self.difusores = Categoria.objects.create(nombre="Difusores", slug="difusores", orden=1)
        self.aceites = Categoria.objects.create(nombre="Aceites", slug="aceites", orden=2)
        self.barato = Producto.objects.create(
            nombre="Set de Varillas",
            categoria=self.difusores,
            descripcion_corta="Repuesto",
            precio=Decimal("4990"),
            notas_aroma="Madera",
        )
        self.caro = Producto.objects.create(
            nombre="Vela Sándalo",
            categoria=self.aceites,
            descripcion_corta="Cera vegetal",
            precio=Decimal("24990"),
        )

    def test_filtro_por_categoria(self):
        respuesta = self.client.get(
            reverse("catalogo:listar"), {"categoria": "aceites"}
        )
        self.assertEqual(list(respuesta.context["productos"]), [self.caro])

    def test_busqueda_por_nombre(self):
        respuesta = self.client.get(reverse("catalogo:listar"), {"q": "sándalo"})
        self.assertEqual(list(respuesta.context["productos"]), [self.caro])

    def test_busqueda_por_notas_de_aroma(self):
        respuesta = self.client.get(reverse("catalogo:listar"), {"q": "madera"})
        self.assertEqual(list(respuesta.context["productos"]), [self.barato])

    def test_orden_por_precio(self):
        respuesta = self.client.get(reverse("catalogo:listar"), {"orden": "precio-asc"})
        self.assertEqual(
            [p.pk for p in respuesta.context["productos"]], [self.barato.pk, self.caro.pk]
        )

    def test_filtro_por_precio_maximo(self):
        respuesta = self.client.get(reverse("catalogo:listar"), {"precio": "10000"})
        self.assertEqual(list(respuesta.context["productos"]), [self.barato])

    def test_categoria_inexistente_devuelve_404(self):
        respuesta = self.client.get(
            reverse("catalogo:listar"), {"categoria": "no-existe"}
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_no_muestra_productos_inactivos(self):
        self.barato.activo = False
        self.barato.save()
        respuesta = self.client.get(reverse("catalogo:listar"))
        self.assertNotContains(respuesta, "Set de Varillas")


class DetalleTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Difusores", slug="difusores")
        self.producto = Producto.objects.create(
            nombre="Difusor Lavanda",
            categoria=self.categoria,
            descripcion_corta="Relaxante",
            descripcion="Frasco de vidrio con varillas de ratán.",
            notas_aroma="Lavanda · Vainilla",
            volumen_ml=200,
            precio=Decimal("18990"),
            precio_anterior=Decimal("21990"),
            stock=4,
        )
        self.relacionado = Producto.objects.create(
            nombre="Difusor Menta",
            categoria=self.categoria,
            descripcion_corta="Fresco",
            precio=Decimal("17990"),
        )

    def test_detalle_muestra_datos(self):
        respuesta = self.client.get(self.producto.get_absolute_url())

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Difusor Lavanda")
        self.assertContains(respuesta, "$21.990")  # precio anterior
        self.assertContains(respuesta, "200 ml")
        self.assertContains(respuesta, "Lavanda")
        self.assertContains(respuesta, self.relacionado.nombre)

    def test_lista_notas_de_aroma(self):
        self.assertEqual(
            self.producto.lista_notas, ["Lavanda", "Vainilla"]
        )

    def test_porcentaje_de_descuento(self):
        self.assertEqual(self.producto.porcentaje_descuento, 13)

    def test_agregar_al_carrito_desde_el_detalle(self):
        respuesta = self.client.post(
            reverse("pedidos:agregar", args=[self.producto.pk]),
            {"cantidad": 2, "volver": self.producto.get_absolute_url()},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.client.session["carrito"], {str(self.producto.pk): 2})

    def test_producto_inexistente_404(self):
        respuesta = self.client.get(reverse("catalogo:detalle", args=["no-existe"]))
        self.assertEqual(respuesta.status_code, 404)

    def test_imagen_url_usa_placeholder_estatico(self):
        self.assertIn(self.producto.slug, self.producto.imagen_url)


class ProductoModelTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Difusores")

    def test_slug_se_genera_solo(self):
        producto = Producto.objects.create(
            nombre="Difusor Bergamota y Salvia",
            categoria=self.categoria,
            descripcion_corta="Cítrico",
            precio=Decimal("19990"),
        )
        self.assertEqual(producto.slug, "difusor-bergamota-y-salvia")

    def test_slugs_duplicados_no_chocan(self):
        primero = Producto.objects.create(
            nombre="Kit Relajación",
            categoria=self.categoria,
            descripcion_corta="Kit",
            precio=Decimal("29990"),
        )
        segundo = Producto.objects.create(
            nombre="Kit Relajación",
            categoria=self.categoria,
            descripcion_corta="Kit",
            precio=Decimal("29990"),
        )
        self.assertNotEqual(primero.slug, segundo.slug)

    def test_precio_anterior_debe_ser_mayor(self):
        from django.core.exceptions import ValidationError

        producto = Producto(
            nombre="Producto",
            categoria=self.categoria,
            descripcion_corta="x",
            precio=Decimal("1000"),
            precio_anterior=Decimal("500"),
        )
        with self.assertRaises(ValidationError):
            producto.full_clean()


class AdminProductoTests(TestCase):
    """El panel de administración es la herramienta real para cargar productos."""

    ARCHIVO = Path(__file__).resolve().parents[2] / "data" / "productos.json"

    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.usuario = get_user_model().objects.create_superuser(
            username="admin", email="admin@diaromas.cl", password="clave-segura-123"
        )
        self.categoria = Categoria.objects.create(nombre="Difusores", slug="difusores")

        # PNG 1x1 en memoria (Pillow valida la imagen al guardarla)
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
            b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01"
            b"\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        self.imagen = SimpleUploadedFile("producto.png", png, content_type="image/png")

    def test_crear_producto_con_imagen_desde_el_admin(self):
        self.client.force_login(self.usuario)
        producto = Producto.objects.create(
            nombre="Temporal",
            categoria=self.categoria,
            descripcion_corta="x",
            precio=Decimal("1000"),
        )
        datos = {
            "nombre": "Difusor Lavanda",
            "slug": "difusor-lavanda",
            "categoria": self.categoria.pk,
            "descripcion_corta": "Relaxante",
            "descripcion": "Frasco de vidrio.",
            "notas_aroma": "Lavanda · Vainilla",
            "volumen_ml": "200",
            "duracion_horas": "2160",
            "precio": "18990",
            "stock": "10",
            "activo": "on",
            "destacado": "on",
            "imagen": self.imagen,
            # Management form del inline de galería (extra=1, sin iniciales).
            # El navegador envía `galeria-0-orden=0` (valor por defecto del campo).
            "galeria-TOTAL_FORMS": "1",
            "galeria-INITIAL_FORMS": "0",
            "galeria-MIN_NUM_FORMS": "0",
            "galeria-MAX_NUM_FORMS": "1000",
            "galeria-0-orden": "0",
        }

        respuesta = self.client.post(
            reverse("admin:catalogo_producto_change", args=[producto.pk]), datos
        )

        # 302 = el admin guardó correctamente y redirigió al changelist
        self.assertEqual(respuesta.status_code, 302)

        producto.refresh_from_db()
        self.assertEqual(producto.slug, "difusor-lavanda")
        self.assertEqual(producto.precio, Decimal("18990"))
        self.assertTrue(producto.destacado)
        self.assertTrue(producto.imagen)  # Pillow validó el PNG
        self.assertTrue(producto.imagen.name.endswith(".png"))
        # Con imagen real ya no se usa la ilustración estática
        self.assertTrue(producto.imagen.url.startswith("/media/"))

    def test_accion_masiva_marcar_destacado(self):
        self.client.force_login(self.usuario)
        producto = Producto.objects.create(
            nombre="Para destacar",
            categoria=self.categoria,
            descripcion_corta="x",
            precio=Decimal("1000"),
        )

        self.client.post(
            reverse("admin:catalogo_producto_changelist"),
            {"action": "marcar_destacado", "_selected_action": [str(producto.pk)]},
            follow=True,
        )

        producto.refresh_from_db()
        self.assertTrue(producto.destacado)

    def test_admin_exige_iniciar_sesion(self):
        respuesta = self.client.get(reverse("admin:catalogo_producto_changelist"))
        self.assertEqual(respuesta.status_code, 302)


class CargarCatalogoTests(TestCase):
    ARCHIVO = Path(__file__).resolve().parents[2] / "data" / "productos.json"

    def test_archivo_incluido_es_json_valido(self):
        self.assertTrue(self.ARCHIVO.exists())
        datos = json.loads(self.ARCHIVO.read_text(encoding="utf-8"))
        self.assertEqual(len(datos["categorias"]), 4)
        self.assertEqual(len(datos["productos"]), 12)

    def test_carga_el_catalogo_real(self):
        call_command("cargar_catalogo", stdout=io.StringIO())

        self.assertEqual(Categoria.objects.count(), 4)
        self.assertEqual(Producto.objects.count(), 12)
        producto = Producto.objects.get(slug="difusor-varillas-lavanda-vainilla")
        self.assertEqual(producto.precio, Decimal("18990"))
        self.assertEqual(producto.categoria.slug, "difusores")
        self.assertTrue(producto.destacado)

    def test_es_idempotente(self):
        call_command("cargar_catalogo", stdout=io.StringIO())
        primera_cantidad = Producto.objects.count()

        call_command("cargar_catalogo", stdout=io.StringIO())

        self.assertEqual(Producto.objects.count(), primera_cantidad)

    def test_actualiza_precios_existentes(self):
        call_command("cargar_catalogo", stdout=io.StringIO())

        Producto.objects.filter(slug="difusor-varillas-lavanda-vainilla").update(precio=999)
        call_command("cargar_catalogo", stdout=io.StringIO())

        self.assertEqual(
            Producto.objects.get(slug="difusor-varillas-lavanda-vainilla").precio,
            Decimal("18990"),
        )

    def test_desactivar_productos_fuera_del_json(self):
        call_command("cargar_catalogo", stdout=io.StringIO())
        categoria = Categoria.objects.first()
        Producto.objects.create(
            nombre="Producto viejo",
            categoria=categoria,
            descripcion_corta="x",
            precio=Decimal("1000"),
        )

        call_command(
            "cargar_catalogo", desactivar=True, stdout=io.StringIO()
        )

        self.assertFalse(Producto.objects.get(nombre="Producto viejo").activo)

    def test_archivo_inexistente_falla(self):
        with self.assertRaises(CommandError):
            call_command("cargar_catalogo", archivo=Path("/tmp/no-existe.json"))

    def test_json_invalido_falla(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as archivo:
            archivo.write("{no es json")
            ruta = Path(archivo.name)

        with self.assertRaises(CommandError):
            call_command("cargar_catalogo", archivo=ruta)