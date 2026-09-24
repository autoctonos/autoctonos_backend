from django import forms
from .models import Producto
from locations.models import Municipio
from producers.models import Productor


class ProductoForm(forms.ModelForm):
    image = forms.ImageField(
        required=False, widget=forms.FileInput(attrs={"class": "form-control"})
    )

    id_productor = forms.ModelChoiceField(
        queryset=Productor.objects.select_related('id_municipio').all().order_by('nombre'),
        required=True,
        widget=forms.Select(attrs={"class": "form-control", "id": "id_productor"}),
        label="Productor",
        empty_label="Seleccione un productor",
    )

    # Override opcional: por defecto el envío sale del municipio del productor.
    id_municipio = forms.ModelChoiceField(
        queryset=Municipio.objects.select_related('id_departamento').all().order_by('id_departamento__nombre', 'nombre'),
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "id": "id_municipio"}),
        label="Municipio de origen (opcional)",
        empty_label="Igual al del productor"
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
            "peso_kg",
            "requiere_frio_override",
            "id_productor",
            "id_municipio",
            "fabricante",
            "es_promocionado",
            "porcentaje_descuento",
        ]
        labels = {
            "id_categoria": "Categoría",
            "nombre": "Nombre",
            "descripcion": "Descripción",
            "precio": "Precio Original",
            "stock": "Stock",
            "presentacion": "Unidad de venta",
            "cantidad_presentacion": "Cantidad por presentación",
            "peso_kg": "Peso de despacho (kg)",
            "requiere_frio_override": "Cadena de frío",
            "id_productor": "Productor",
            "id_municipio": "Municipio de origen (opcional)",
            "fabricante": "Fabricante",
            "es_promocionado": "Promocionado",
            "porcentaje_descuento": "Porcentaje de Descuento (%)",
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
            "peso_kg": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.001",
                    "min": "0.001",
                    "placeholder": "Ej: 0.800 para un queso de 800 g",
                }
            ),
            "requiere_frio_override": forms.Select(
                attrs={"class": "form-control"},
                choices=[(None, "Heredar de la categoría"), (True, "Sí"), (False, "No")],
            ),
            "fabricante": forms.TextInput(attrs={"class": "form-control", "maxlength": "200"}),
            "es_promocionado": forms.CheckboxInput(attrs={"class": "form-control", "id": "id_es_promocionado"}),
            "porcentaje_descuento": forms.NumberInput(attrs={"class": "form-control", "id": "id_porcentaje_descuento", "step": "0.01", "min": "0", "max": "100"}),
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
        self.fields['peso_kg'].required = False
        self.fields['requiere_frio_override'].required = False
        self.fields['fabricante'].required = False
        self.fields['id_productor'].required = True
        self.fields['id_municipio'].required = False
        self.fields['porcentaje_descuento'].required = False
        
        self.fields['id_municipio'].queryset = Municipio.objects.select_related('id_departamento').all().order_by('id_departamento__nombre', 'nombre')
        
        self.fields['id_municipio'].label_from_instance = lambda obj: f"{obj.nombre} ({obj.id_departamento.nombre})"

        self.fields['id_productor'].queryset = Productor.objects.select_related('id_municipio').all().order_by('nombre')
        self.fields['id_productor'].label_from_instance = (
            lambda obj: f"{obj.nombre} ({obj.id_municipio.nombre})" if obj.id_municipio else f"{obj.nombre} (sin municipio)"
        )

