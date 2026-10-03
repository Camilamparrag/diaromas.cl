"""Vistas del catálogo: portada, listado con filtros y detalle de producto."""

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db.models import Count, Q, QuerySet
from django.shortcuts import get_object_or_404, render

from .models import Categoria, Producto

ORDENES = {
    "relevancia": ("-destacado", "nombre"),
    "precio-asc": ("precio", "nombre"),
    "precio-desc": ("-precio", "nombre"),
    "nuevos": ("-creado_en",),
}

PRECIOS_CHOICE = {
    "0": Decimal("0"),
    "10000": Decimal("10000"),
    "20000": Decimal("20000"),
    "30000": Decimal("30000"),
}


def productos_activos() -> QuerySet[Producto]:
    """Base de consulta: solo productos visibles para el público."""
    return Producto.objects.filter(activo=True).select_related("categoria")


def _precio_filtrado(valor: str | None) -> Decimal | None:
    if not valor:
        return None
    try:
        return PRECIOS_CHOICE[valor]
    except (KeyError, InvalidOperation):
        return None


def home(request):
    """Portada: categorías, destacados y llamada a la acción de WhatsApp."""
    categorias = (
        Categoria.objects.filter(activa=True)
        .annotate(total=Count("productos", filter=Q(productos__activo=True)))
        .order_by("orden", "nombre")
    )
    destacados = productos_activos().filter(destacado=True)[:8]
    nuevos = productos_activos().order_by("-creado_en")[:4]

    return render(
        request,
        "catalogo/home.html",
        {
            "categorias": categorias,
            "destacados": destacados,
            "nuevos": nuevos,
            "total_productos": productos_activos().count(),
        },
    )


def lista_productos(request):
    """Listado con búsqueda por texto, filtro por categoría, precio y orden."""
    consulta = request.GET.get("q", "").strip()
    slug_categoria = request.GET.get("categoria", "").strip()
    orden = request.GET.get("orden", "relevancia")
    precio_max = _precio_filtrado(request.GET.get("precio"))

    productos = productos_activos()

    if consulta:
        productos = productos.filter(
            Q(nombre__icontains=consulta)
            | Q(descripcion_corta__icontains=consulta)
            | Q(descripcion__icontains=consulta)
            | Q(notas_aroma__icontains=consulta)
            | Q(categoria__nombre__icontains=consulta)
        )

    categoria = None
    if slug_categoria:
        categoria = get_object_or_404(Categoria, slug=slug_categoria, activa=True)
        productos = productos.filter(categoria=categoria)

    if precio_max is not None:
        productos = productos.filter(precio__lte=precio_max)

    productos = productos.order_by(*ORDENES.get(orden, ORDENES["relevancia"]))

    categorias = (
        Categoria.objects.filter(activa=True, productos__activo=True)
        .annotate(total=Count("productos", filter=Q(productos__activo=True)))
        .distinct()
    )

    # Se conservan los filtros al paginar
    params = request.GET.copy()

    return render(
        request,
        "catalogo/lista.html",
        {
            "productos": productos,
            "categorias": categorias,
            "categoria": categoria,
            "consulta": consulta,
            "orden": orden,
            "precio_max": request.GET.get("precio", ""),
            "rangos_precio": PRECIOS_CHOICE,
            "params": params,
        },
    )


def detalle_producto(request, slug: str):
    """Ficha de un producto con productos relacionados."""
    producto = get_object_or_404(
        productos_activos().prefetch_related("galeria"), slug=slug
    )

    relacionados = (
        productos_activos()
        .filter(categoria=producto.categoria)
        .exclude(pk=producto.pk)[:4]
    )

    from apps.pedidos.cart import Carrito

    carrito = Carrito(request)
    cantidad_en_carrito = carrito.cantidad_de(producto)

    return render(
        request,
        "catalogo/detalle.html",
        {
            "producto": producto,
            "relacionados": relacionados,
            "cantidad_en_carrito": cantidad_en_carrito,
            "precio_con_iva": producto.precio,
            "iva_rate": settings.IVA_RATE,
        },
    )