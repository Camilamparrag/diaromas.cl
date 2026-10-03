"""Tests del carrito, del checkout y del mensaje de WhatsApp."""

from decimal import Decimal

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import TestCase
from django.urls import reverse

from apps.catalogo.models import Categoria, Producto
from apps.pedidos.cart import Carrito
from apps.pedidos.models import Pedido
from apps.pedidos.services import (
    construir_mensaje_whatsapp,
    crear_pedido_desde_carrito,
    enlace_whatsapp,
    formatear_monto,
    formatear_telefono,
)


def crear_producto(nombre="Difusor Test", precio="18990", stock=10, activo=True):
    """Producto de prueba en la categoría Difusores."""
    categoria, _ = Categoria.objects.get_or_create(
        slug="difusores", defaults={"nombre": "Difusores", "orden": 1}
    )
    return Producto.objects.create(
        nombre=nombre,
        categoria=categoria,
        descripcion_corta="Producto de prueba",
        precio=Decimal(precio),
        stock=stock,
        activo=activo,
    )


def request_con_sesion():
    """HttpRequest mínima con sesión disponible."""
    request = HttpRequest()
    SessionMiddleware(lambda r: None).process_request(request)
    return request


# --- Formateo --------------------------------------------------------------
class FormateoTests(TestCase):
    def test_montos_en_pesos_chilenos(self):
        self.assertEqual(formatear_monto(18990), "$18.990")
        self.assertEqual(formatear_monto(Decimal("1500000")), "$1.500.000")
        self.assertEqual(formatear_monto(0), "$0")

    def test_telefono_chileno(self):
        self.assertEqual(formatear_telefono("+56912345678"), "+56 9 1234 5678")
        self.assertEqual(formatear_telefono(""), "No informado")


# --- Carrito ---------------------------------------------------------------
class CarritoTests(TestCase):
    def setUp(self):
        self.producto = crear_producto()

    def test_agregar_y_guardar_en_sesion(self):
        request = request_con_sesion()
        carro = Carrito(request)
        carro.agregar(self.producto, 2)

        self.assertEqual(carro.cantidad_de(self.producto), 2)
        self.assertEqual(request.session["carrito"], {str(self.producto.pk): 2})
        self.assertEqual(carro.unidades, 2)
        self.assertEqual(carro.subtotal, Decimal("37980"))

    def test_no_excede_el_stock(self):
        producto = crear_producto(nombre="Producto Escaso", stock=3)
        carro = Carrito(request_con_sesion())
        carro.agregar(producto, 10)
        self.assertEqual(carro.cantidad_de(producto), 3)

    def test_actualizar_a_cero_quita_el_producto(self):
        carro = Carrito(request_con_sesion())
        carro.agregar(self.producto, 2)
        carro.actualizar(self.producto.pk, 0)

        self.assertEqual(carro.articulos, 0)
        self.assertTrue(carro.es_vacio)

    def test_ignora_productos_inactivos(self):
        producto = crear_producto(nombre="Inactivo", activo=False)
        carro = Carrito(request_con_sesion())
        carro.carrito = {str(producto.pk): 2}
        carro.guardar()

        self.assertEqual(carro.items(), [])
        self.assertEqual(carro.subtotal, Decimal("0"))

    def test_carrito_vacio(self):
        carro = Carrito(request_con_sesion())
        self.assertTrue(carro.es_vacio)
        self.assertEqual(carro.unidades, 0)
        self.assertEqual(carro.subtotal, Decimal("0"))


# --- Vistas del carrito ----------------------------------------------------
class VistasCarritoTests(TestCase):
    def setUp(self):
        self.producto = crear_producto()

    def test_agregar_desde_la_tienda(self):
        respuesta = self.client.post(
            reverse("pedidos:agregar", args=[self.producto.pk]),
            {"cantidad": 2, "volver": "/catalogo/"},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.client.session["carrito"], {str(self.producto.pk): 2})

    def test_agregar_sin_stock_muestra_aviso(self):
        producto = crear_producto(nombre="Sin Stock", stock=0)
        self.client.post(reverse("pedidos:agregar", args=[producto.pk]), {"cantidad": 1})
        self.assertNotIn(str(producto.pk), self.client.session.get("carrito", {}))

    def test_carrito_vacio_muestra_mensaje(self):
        respuesta = self.client.get(reverse("pedidos:carrito"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["carrito"].es_vacio)

    def test_carrito_con_items_se_renderiza(self):
        self.client.post(
            reverse("pedidos:agregar", args=[self.producto.pk]), {"cantidad": 2}
        )

        respuesta = self.client.get(reverse("pedidos:carrito"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.producto.nombre)
        self.assertContains(respuesta, "$18.990")
        self.assertContains(respuesta, "$37.980")
        self.assertContains(respuesta, "2 unidades listas")
        # La ilustración estática del producto se usa como imagen
        self.assertContains(respuesta, f"img/productos/{self.producto.slug}.svg")
        # Badge del carrito en el encabezado
        self.assertContains(respuesta, 'data-carrito-cantidad')
        self.assertContains(respuesta, ">2</span>")

    def test_actualizar_cantidades(self):
        self.client.post(
            reverse("pedidos:agregar", args=[self.producto.pk]), {"cantidad": 1}
        )
        respuesta = self.client.post(
            reverse("pedidos:actualizar"),
            {"producto_id[]": [str(self.producto.pk)], "cantidad[]": ["3"]},
        )
        self.assertRedirects(respuesta, reverse("pedidos:carrito"))
        self.assertEqual(self.client.session["carrito"], {str(self.producto.pk): 3})

    def test_quitar_item(self):
        self.client.post(
            reverse("pedidos:agregar", args=[self.producto.pk]), {"cantidad": 1}
        )
        respuesta = self.client.post(reverse("pedidos:quitar", args=[self.producto.pk]))
        self.assertRedirects(respuesta, reverse("pedidos:carrito"))
        self.assertEqual(self.client.session["carrito"], {})

    def test_agregar_exige_post(self):
        respuesta = self.client.get(reverse("pedidos:agregar", args=[self.producto.pk]))
        self.assertEqual(respuesta.status_code, 405)


# --- Checkout y creación de pedidos ---------------------------------------
class CheckoutTests(TestCase):
    def setUp(self):
        self.producto = crear_producto()
        self.datos = {
            "cliente_nombre": "María Pérez",
            "cliente_email": "maria@email.cl",
            "cliente_telefono": "+56912345678",
            "entrega": Pedido.Entrega.ENVIO,
            "direccion": "Calle Falsa 123",
            "comuna": "Providencia",
            "region": "Metropolitana",
            "notas": "Entregar en la tarde",
        }

    def _agregar_al_carrito(self, cantidad=2):
        self.client.post(
            reverse("pedidos:agregar", args=[self.producto.pk]), {"cantidad": cantidad}
        )

    def test_crea_pedido_y_descuenta_stock(self):
        self._agregar_al_carrito(2)
        stock_inicial = self.producto.stock

        respuesta = self.client.post(reverse("pedidos:checkout"), self.datos)

        pedido = Pedido.objects.get()
        self.assertEqual(pedido.cliente_nombre, "María Pérez")
        self.assertEqual(pedido.subtotal, Decimal("37980"))
        self.assertEqual(pedido.total, Decimal("37980"))
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE)
        self.assertEqual(pedido.items.count(), 1)
        self.assertEqual(pedido.items.first().cantidad, 2)
        self.assertTrue(pedido.code.startswith("DR-"))

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, stock_inicial - 2)

        self.assertRedirects(respuesta, reverse("pedidos:confirmacion", args=[pedido.code]))
        # El carrito queda vacío tras confirmar
        self.assertEqual(self.client.session["carrito"], {})

    def test_exige_direccion_si_el_entrega_es_envio(self):
        self._agregar_al_carrito()
        datos = {**self.datos, "direccion": "", "comuna": ""}

        respuesta = self.client.post(reverse("pedidos:checkout"), datos)

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Pedido.objects.exists())
        self.assertIn("direccion", respuesta.context["form"].errors)

    def test_retiro_no_exige_direccion(self):
        self._agregar_al_carrito()
        datos = {
            **self.datos,
            "entrega": Pedido.Entrega.RETIRO,
            "direccion": "",
            "comuna": "",
        }

        self.client.post(reverse("pedidos:checkout"), datos)

        pedido = Pedido.objects.get()
        self.assertEqual(pedido.entrega, Pedido.Entrega.RETIRO)
        self.assertFalse(pedido.es_envio)

    def test_sin_stock_devuelve_error_y_no_crea_pedido(self):
        self._agregar_al_carrito(2)
        # Otra compra se lleva el stock entre medio
        Producto.objects.filter(pk=self.producto.pk).update(stock=1)

        respuesta = self.client.post(reverse("pedidos:checkout"), self.datos)

        self.assertRedirects(respuesta, reverse("pedidos:carrito"))
        self.assertFalse(Pedido.objects.exists())

    def test_checkout_con_carrito_vacio_redirige(self):
        respuesta = self.client.get(reverse("pedidos:checkout"))
        self.assertRedirects(respuesta, reverse("catalogo:listar"))

    def test_servicio_rechaza_carrito_vacio(self):
        carro = Carrito(request_con_sesion())
        with self.assertRaises(ValueError):
            crear_pedido_desde_carrito(carro, self.datos)

    def test_pedido_asociado_a_usuario_registrado(self):
        from django.contrib.auth import get_user_model

        usuario = get_user_model().objects.create_user(
            username="maria", password="clave-segura-123", email="maria@email.cl"
        )
        self.client.force_login(usuario)
        self._agregar_al_carrito(1)

        self.client.post(reverse("pedidos:checkout"), self.datos)

        pedido = Pedido.objects.get()
        self.assertEqual(pedido.user, usuario)


# --- Mensaje de WhatsApp ---------------------------------------------------
class MensajeWhatsAppTests(TestCase):
    def setUp(self):
        self.producto = crear_producto()
        self.carrito = Carrito(request_con_sesion())
        self.carrito.agregar(self.producto, 2)
        self.pedido = crear_pedido_desde_carrito(
            self.carrito,
            {
                "cliente_nombre": "María Pérez",
                "cliente_email": "maria@email.cl",
                "cliente_telefono": "+56912345678",
                "entrega": Pedido.Entrega.ENVIO,
                "direccion": "Calle Falsa 123",
                "comuna": "Providencia",
                "region": "Metropolitana",
                "notas": "Entregar en la tarde",
            },
        )

    def test_mensaje_contiene_datos_clientes_y_productos(self):
        mensaje = construir_mensaje_whatsapp(self.pedido)

        self.assertIn("NUEVO PEDIDO DIAROMAS", mensaje)
        self.assertIn(self.pedido.code, mensaje)
        self.assertIn("María Pérez", mensaje)
        self.assertIn("+56 9 1234 5678", mensaje)
        self.assertIn("maria@email.cl", mensaje)
        self.assertIn(self.producto.nombre, mensaje)
        self.assertIn("2 × $18.990 = $37.980", mensaje)
        self.assertIn("TOTAL: $37.980", mensaje)
        self.assertIn("IVA 19%", mensaje)
        self.assertIn("Entregar en la tarde", mensaje)

    def test_enlace_wa_me_usa_numero_configurado(self):
        from django.conf import settings

        enlace = enlace_whatsapp(self.pedido)
        numero = "".join(ch for ch in settings.WHATSAPP_NUMBER if ch.isdigit())

        self.assertTrue(enlace.startswith(f"https://wa.me/{numero}?text="))
        self.assertIn("%2A", enlace)  # el asterisco de *negrita* va codificado
        self.assertNotIn(" ", enlace.split("?text=")[1].replace("%20", ""))

    def test_pedido_guarda_copia_del_nombre_del_producto(self):
        self.producto.nombre = "Nombre que cambió"
        self.producto.save()

        item = self.pedido.items.first()
        self.assertNotEqual(item.producto_nombre, "Nombre que cambió")

    def test_estado_paso_de_la_linea_de_tiempo(self):
        self.assertEqual(self.pedido.estado_paso, 0)
        self.pedido.estado = Pedido.Estado.ENVIADO
        self.assertEqual(self.pedido.estado_paso, 3)

    def _checkout_como_invitado(self):
        """Crea un pedido como invitado y devuelve el último creado."""
        self.client.post(reverse("pedidos:agregar", args=[self.producto.pk]), {"cantidad": 1})
        self.client.post(
            reverse("pedidos:checkout"),
            {
                "cliente_nombre": "Invitado",
                "cliente_telefono": "+56911111111",
                "entrega": Pedido.Entrega.RETIRO,
            },
        )
        return Pedido.objects.order_by("-creado_en").first()

    def test_confirmacion_accesible_para_el_creador(self):
        pedido = self._checkout_como_invitado()

        # La misma sesión sí puede ver su pedido
        respuesta = self.client.get(reverse("pedidos:confirmacion", args=[pedido.code]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, pedido.code)

        # Otra sesión no
        cliente = self.client_class()
        respuesta = cliente.get(reverse("pedidos:confirmacion", args=[pedido.code]))
        self.assertEqual(respuesta.status_code, 302)

    def test_vista_whatsapp_redirige_al_wa_me(self):
        pedido = self._checkout_como_invitado()

        respuesta = self.client.get(reverse("pedidos:whatsapp", args=[pedido.code]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta["Location"].startswith("https://wa.me/"))

        pedido.refresh_from_db()
        self.assertIsNotNone(pedido.whatsapp_enviado_en)

    def test_mensaje_trunca_si_es_muy_largo(self):
        self.pedido.notas = "nota larga " * 500
        self.pedido.save()

        mensaje = construir_mensaje_whatsapp(self.pedido)

        self.assertLessEqual(len(mensaje), 3600)
        self.assertTrue(mensaje.endswith("…"))


class MisPedidosTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.usuario = get_user_model().objects.create_user(
            username="pedro", password="clave-segura-123"
        )
        self.pedido = Pedido.objects.create(
            user=self.usuario,
            cliente_nombre="Pedro Soto",
            cliente_telefono="+56922222222",
            subtotal=Decimal("18990"),
            total=Decimal("18990"),
        )

    def test_requiere_iniciar_sesion(self):
        respuesta = self.client.get(reverse("pedidos:mis_pedidos"))
        self.assertEqual(respuesta.status_code, 302)

    def test_lista_solo_sus_pedidos(self):
        otro = Pedido.objects.create(
            cliente_nombre="Ajeno", cliente_telefono="+56933333333"
        )
        self.client.force_login(self.usuario)

        respuesta = self.client.get(reverse("pedidos:mis_pedidos"))

        self.assertEqual(list(respuesta.context["pedidos"]), [self.pedido])
        self.assertNotContains(respuesta, otro.code)