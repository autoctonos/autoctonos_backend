from django import template
import re

register = template.Library()

@register.filter(name='format_precio')
def format_precio(value):
    if value is None:
        return ''
    try:
        precio_entero = int(float(value))
    except (ValueError, TypeError):
        return str(value) if value else ''
    # Convertir a string
    precio_str = str(precio_entero)

    precio_formateado = re.sub(r'\B(?=(\d{3})+(?!\d))', '.', precio_str)

    return precio_formateado



# Símbolos del panel (ver `forms.UNIDADES_PANEL`): «500 g», «1 L», nunca «500 Gr» / «1 Lt».
_SIMBOLOS = {"Gr": "g", "Kg": "kg", "Lb": "lb", "Oz": "oz", "Lt": "L", "Ml": "ml", "Bt": "cm³"}
_SIN_CANTIDAD = {"Un": "Unidad", "Paq": "Paquete x12", "Dz": "Docena"}


@register.filter(name='presentacion_panel')
def presentacion_panel(producto):
    codigo = producto.presentacion
    if codigo in _SIN_CANTIDAD or producto.cantidad_presentacion is None:
        return _SIN_CANTIDAD.get(codigo, _SIMBOLOS.get(codigo, codigo))
    d = producto.cantidad_presentacion
    cantidad = str(int(d)) if d == d.to_integral_value() else f"{d:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{cantidad} {_SIMBOLOS.get(codigo, codigo)}"
