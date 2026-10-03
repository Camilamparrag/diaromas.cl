"""
Carrito de compras basado en la sesión.

La sesión guarda únicamente un diccionario ``{id_producto: cantidad}``, de modo
que los datos reales (precio, nombre, stock) siempre se leen de la base de
datos y el carrito nunca queda desincronizado con el catálogo.
"""

from decimal import Decimal

from apps.catalogo.models import Producto

CARRITO_SESSION_KEY = "carrito"
MAX_CANTIDAD_POR_ITEM = 99


class Carrito:
    """Fachada del carrito para una request concreta."""

    def __init__(self, request):
        self.session = request.session
        self.carrito: dict[str, int] = self.session.get(CARRITO_SESSION_KEY, {}) or {}

    # --- Persistencia --------------------------------------------------------
    def guardar(self) -> None:
        limpio = {}
        for clave, cantidad in self.carrito.items():
            try:
                cantidad = int(cantidad)
            except (TypeError, ValueError):
                continue
            if cantidad > 0:
                limpio[str(clave)] = min(cantidad, MAX_CANTIDAD_POR_ITEM)
        self.session[CARRITO_SESSION_KEY] = limpio
        self.session.modified = True
        self.carrito = limpio

    # --- Mutaciones ----------------------------------------------------------
    def agregar(self, producto: Producto, cantidad: int = 1) -> None:
        clave = str(producto.pk)
        actual = int(self.carrito.get(clave, 0))
        nueva = min(actual + max(int(cantidad), 1), self._limite(producto))
        self.carrito[clave] = max(nueva, 1)
        self.guardar()

    def actualizar(self, producto_id, cantidad: int) -> None:
        clave = str(producto_id)
        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            cantidad = 0
        producto = self._producto(clave)
        if producto is None:
            self.carrito.pop(clave, None)
        elif cantidad <= 0:
            self.carrito.pop(clave, None)
        else:
            self.carrito[clave] = min(cantidad, self._limite(producto))
        self.guardar()

    def quitar(self, producto_id) -> None:
        self.carrito.pop(str(producto_id), None)
        self.guardar()

    def vaciar(self) -> None:
        self.session[CARRITO_SESSION_KEY] = {}
        self.session.modified = True
        self.carrito = {}

    # --- Lecturas ------------------------------------------------------------
    def productos(self) -> dict[int, Producto]:
        """Productos vigentes del carrito indexados por id (ignora los borrados)."""
        ids = [int(clave) for clave in self.carrito if str(clave).isdigit()]
        if not ids:
            return {}
        return {
            producto.pk: producto
            for producto in Producto.objects.filter(pk__in=ids, activo=True)
        }

    def items(self) -> list[dict]:
        """Detalle del carrito listo para el template."""
        productos = self.productos()
        detalle = []
        for clave, cantidad in self.carrito.items():
            producto = productos.get(int(clave)) if str(clave).isdigit() else None
            if producto is None:
                continue
            cantidad = max(int(cantidad), 1)
            detalle.append(
                {
                    "producto": producto,
                    "cantidad": cantidad,
                    "subtotal": producto.precio * cantidad,
                }
            )
        detalle.sort(key=lambda item: item["producto"].nombre.lower())
        return detalle

    def cantidad_de(self, producto: Producto) -> int:
        return int(self.carrito.get(str(producto.pk), 0))

    @property
    def articulos(self) -> int:
        """Cantidad de líneas de producto distintas."""
        return len(self.items())

    @property
    def unidades(self) -> int:
        """Cantidad total de unidades."""
        return sum(item["cantidad"] for item in self.items())

    @property
    def subtotal(self) -> Decimal:
        """Suma de los subtotales (IVA incluido)."""
        return sum((item["subtotal"] for item in self.items()), Decimal("0"))

    @property
    def es_vacio(self) -> bool:
        return not self.items()

    # --- Utilidades ----------------------------------------------------------
    def _limite(self, producto: Producto) -> int:
        """No permite agregar más que el stock disponible."""
        return max(min(producto.stock, MAX_CANTIDAD_POR_ITEM), 1)

    def _producto(self, clave: str) -> Producto | None:
        if not str(clave).isdigit():
            return None
        return Producto.objects.filter(pk=int(clave), activo=True).first()