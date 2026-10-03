"""Filtros y etiquetas de plantilla de Diaromas."""

from django import template

register = template.Library()


@register.filter(name="clp")
def clp(valor) -> str:
    """$18.990 (punto como separador de miles, estilo Chile)."""
    try:
        return "$" + f"{float(valor):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return str(valor)


@register.filter(name="notas_lista")
def notas_lista(notas_aroma: str) -> list[str]:
    """Convierte 'Lavanda · Bergamota' en una lista para iterar en el template."""
    if not notas_aroma:
        return []
    return [nota.strip() for nota in notas_aroma.split("·") if nota.strip()]