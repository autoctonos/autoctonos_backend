from django import template
import re

register = template.Library()

@register.filter(name='format_precio')
def format_precio(value):
    if value is None:
        return ''
    # Convertir a entero para eliminar decimales
    try:
        precio_entero = int(float(value))
    except (ValueError, TypeError):
        return str(value) if value else ''
    # Convertir a string
    precio_str = str(precio_entero)

    # Usar expresión regular para agregar puntos cada 3 dígitos desde la derecha
    # Esta expresión funciona para cualquier cantidad de dígitos
    precio_formateado = re.sub(r'\B(?=(\d{3})+(?!\d))', '.', precio_str)

    return precio_formateado

