from django import forms
from .models import Producto


class ProductoForm(forms.ModelForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = Producto
        fields = ['id_categoria', 'nombre', 'descripcion', 'precio', 'stock', 'estado']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
        }
