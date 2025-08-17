from django import forms
from .models import Producto


class ProductoForm(forms.ModelForm):
    image = forms.ImageField(
        required=False, widget=forms.FileInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = Producto
        fields = [
            "id_categoria",
            "nombre",
            "descripcion",
            "precio",
            "stock",
            "estado",
        ]
        widgets = {
            "id_categoria": forms.Select(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(
                attrs={"rows": 4, "class": "form-control"}
            ),
            "precio": forms.NumberInput(attrs={"class": "form-control"}),
            "stock": forms.NumberInput(attrs={"class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-control"}),
        }
