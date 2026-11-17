from django import forms

from .iconos import COLECCION, ICONIFY_API


class SelectorIconoCategoria(forms.TextInput):
    """Combobox tipo select sobre el catálogo completo de Lucide (API pública de Iconify).

    Por debajo es un `<input>` de texto con el slug: sin JS (o sin red) se puede escribir
    el nombre a mano y el form lo valida igual al descargar el SVG.
    """

    template_name = "products/widgets/selector_icono.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["iconify_api"] = ICONIFY_API
        context["widget"]["coleccion"] = COLECCION
        return context
