from django import forms
from .models import Producto
from locations.models import Municipio


class ProductoForm(forms.ModelForm):
    image = forms.ImageField(
        required=False, widget=forms.FileInput(attrs={"class": "form-control"})
    )

    id_municipio = forms.ModelChoiceField(
        queryset=Municipio.objects.select_related('id_departamento').all().order_by('id_departamento__nombre', 'nombre'),
        required=True,
        widget=forms.Select(attrs={"class": "form-control", "id": "id_municipio"}),
        label="Municipio",
        empty_label="Seleccione un municipio"
    )

    class Meta:
        model = Producto
        fields = [
            "id_categoria",
            "nombre",
            "descripcion",
            "precio",
            "stock",
            "presentacion",
            "cantidad_presentacion",
            "id_municipio",
            "fabricante",
            "es_promocionado",
            "porcentaje_descuento",
            "estado",
        ]
        labels = {
            "id_categoria": "Categoría",
            "nombre": "Nombre",
            "descripcion": "Descripción",
            "precio": "Precio Original",
            "stock": "Stock",
            "presentacion": "Unidad de venta",
            "cantidad_presentacion": "Cantidad por presentación",
            "id_municipio": "Municipio",
            "fabricante": "Fabricante",
            "es_promocionado": "Promocionado",
            "porcentaje_descuento": "Porcentaje de Descuento (%)",
            "estado": "Estado",
        }
        widgets = {
            "id_categoria": forms.Select(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(
                attrs={"rows": 4, "class": "form-control"}
            ),
            "precio": forms.TextInput(attrs={"class": "form-control", "type": "text", "inputmode": "numeric"}),
            "stock": forms.NumberInput(attrs={"class": "form-control"}),
            "presentacion": forms.Select(attrs={"class": "form-control"}),
            "cantidad_presentacion": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Ej: 200 (gramos), 1.5 (litros)",
                }
            ),
            "fabricante": forms.TextInput(attrs={"class": "form-control", "maxlength": "200"}),
            "es_promocionado": forms.CheckboxInput(attrs={"class": "form-control", "id": "id_es_promocionado"}),
            "porcentaje_descuento": forms.NumberInput(attrs={"class": "form-control", "id": "id_porcentaje_descuento", "step": "0.01", "min": "0", "max": "100"}),
            "estado": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['id_categoria'].required = True
        self.fields['nombre'].required = True
        self.fields['descripcion'].required = True
        self.fields['precio'].required = True
        self.fields['stock'].required = True
        self.fields['presentacion'].required = True
        self.fields['cantidad_presentacion'].required = False
        self.fields['fabricante'].required = True
        self.fields['estado'].required = True
        self.fields['porcentaje_descuento'].required = False
        
        self.fields['id_municipio'].queryset = Municipio.objects.select_related('id_departamento').all().order_by('id_departamento__nombre', 'nombre')
        
        self.fields['id_municipio'].label_from_instance = lambda obj: f"{obj.nombre} ({obj.id_departamento.nombre})"

