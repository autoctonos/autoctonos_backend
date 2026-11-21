import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError

from .imagenes import GUIA as GUIA_FOTOS, validar_imagen_producto
from .models import Producto, estado_choices
from locations.models import Municipio
from producers.models import Productor

# Mismo estándar que el inline del admin (`ImagenProductoInline`): si el panel dejara
# guardar menos, el admin rechazaría después cualquier edición de ese producto.
FOTOS_MIN = 2
FOTOS_MAX = 4

# Etiquetas del panel con los símbolos que se usan en todas partes (g, kg, L, ml): el
# modelo guarda los códigos de siempre («Gr», «Lt»), solo cambia cómo se muestran aquí.
UNIDADES_PANEL = [
    ("Un", "Unidad (una pieza)"),
    ("Gr", "Gramos (g)"),
    ("Kg", "Kilos (kg)"),
    ("Lb", "Libras (lb)"),
    ("Oz", "Onzas (oz)"),
    ("Lt", "Litros (L)"),
    ("Ml", "Mililitros (ml)"),
    ("Bt", "Botella (cm³)"),
    ("Paq", "Paquete x12"),
    ("Dz", "Docena"),
]

FRIO_CHOICES = [
    ("", "Lo que indique la categoría"),
    ("True", "Sí, necesita frío"),
    ("False", "No, aguanta temperatura ambiente"),
]


class FotosInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class FotosField(forms.FileField):
    """Varias fotos en un solo campo. Cada una pasa por el estándar de `imagenes.py`; el
    error dice cuál foto falló para que el productor sepa cuál cambiar."""

    widget = FotosInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        archivos = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        limpios, errores = [], []
        for archivo in archivos:
            try:
                archivo = super().clean(archivo, initial)
                validar_imagen_producto(archivo)
            except ValidationError as exc:
                nombre = getattr(archivo, "name", "foto")
                errores.extend(f"«{nombre}»: {m}" for m in exc.messages)
                continue
            limpios.append(archivo)
        if errores:
            raise ValidationError(errores)
        return limpios


class PrecioField(forms.CharField):
    """Pesos enteros. Acepta lo que escribe la gente («12.000», «$ 12 000», «12000») y
    nunca interpreta el punto de miles como decimal."""

    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return None
        digitos = "".join(c for c in value if c.isdigit())
        if not digitos:
            raise ValidationError("Escribe el precio solo con números, por ejemplo 18.000.")
        try:
            return Decimal(digitos)
        except InvalidOperation:
            raise ValidationError("Escribe el precio solo con números, por ejemplo 18.000.")


class DecimalComaField(forms.DecimalField):
    """En Colombia se escribe «0,6». Acepta coma o punto como separador decimal."""

    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip().replace(" ", "").replace(",", ".")
        return super().to_python(value)


# Celular colombiano: 10 dígitos, prefijos 30x, 31x, 32x, 33x o 35x. Misma regla que el
# checkout (`astro_frontend/src/lib/validation/checkout.ts`, `commerce/serializers.py`).
CELULAR_RE = re.compile(r"^3[0-35]\d{8}$")
ERROR_CELULAR = "El celular debe tener 10 dígitos y empezar por 30, 31, 32, 33 o 35. Ejemplo: 300 123 4567."


def normalizar_celular(valor):
    """Solo dígitos, sin el indicativo +57."""
    digitos = "".join(c for c in valor or "" if c.isdigit())
    if digitos.startswith("57") and len(digitos) == 12:
        digitos = digitos[2:]
    return digitos


# Presentaciones que ya dicen cuánto traen: no llevan «cantidad en cada unidad».
PRESENTACIONES_SIN_CANTIDAD = {"Un", "Paq", "Dz"}


class ProductoPanelForm(forms.ModelForm):
    """Lo que llena el productor desde su link privado. El productor, el estado y el
    fabricante no se eligen aquí: los fija la vista."""

    fotos = FotosField(label="Fotos", help_text=GUIA_FOTOS)
    # Fotos ya guardadas y su orden final. Tokens «e<id>» (existente) y «n<i>» (i-ésima
    # foto nueva del campo `fotos`), separados por comas. Lo arma el JS al arrastrar.
    orden_fotos = forms.CharField(required=False, widget=forms.HiddenInput)
    quitar_fotos = forms.CharField(required=False, widget=forms.HiddenInput)

    precio = PrecioField(
        label="Precio de venta",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off", "placeholder": "Ej.: 18.000"}),
    )
    requiere_frio_override = forms.TypedChoiceField(
        label="¿Necesita frío durante el viaje?",
        choices=FRIO_CHOICES,
        coerce=lambda v: v == "True",
        empty_value=None,
        required=False,
    )
    id_municipio = forms.ModelChoiceField(
        queryset=Municipio.objects.none(),
        required=False,
        label="Municipio desde donde se despacha",
        empty_label="El mismo municipio del productor",
    )

    peso_kg = DecimalComaField(
        label="Peso del paquete listo para enviar (kg)",
        max_digits=7, decimal_places=3, min_value=Decimal("0.001"),
        widget=forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off", "placeholder": "Ej.: 0,6"}),
    )
    cantidad_presentacion = DecimalComaField(
        label="Cantidad en cada unidad",
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False,
        widget=forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off", "placeholder": "Ej.: 500"}),
    )

    fotos_minimas = FOTOS_MIN

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
            "id_municipio",
            "es_promocionado",
            "porcentaje_descuento",
        ]
        labels = {
            "id_categoria": "Categoría",
            "nombre": "Nombre del producto",
            "descripcion": "Descripción",
            "stock": "Unidades disponibles",
            "presentacion": "Se vende por",
            "cantidad_presentacion": "Cantidad en cada unidad",
            "peso_kg": "Peso del paquete listo para enviar (kg)",
            "es_promocionado": "Ponerlo en oferta",
            "porcentaje_descuento": "Descuento (%)",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"maxlength": "100", "placeholder": "Ej.: Queso campesino doble crema"}),
            "descripcion": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Ej.: Hecho con leche de nuestras vacas en Ubaté. Suave y cremoso, ideal para arepas. Dura 15 días en nevera.",
            }),
            "stock": forms.NumberInput(attrs={"min": "0", "inputmode": "numeric", "placeholder": "Ej.: 20"}),
            "porcentaje_descuento": forms.NumberInput(attrs={"step": "1", "min": "1", "max": "90", "placeholder": "Ej.: 10"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre in ("id_categoria", "nombre", "descripcion", "precio", "stock", "presentacion", "peso_kg"):
            self.fields[nombre].required = True
        self.fields["id_categoria"].empty_label = "Elige una categoría"
        self.fields["presentacion"].choices = UNIDADES_PANEL
        self.fields["id_municipio"].queryset = (
            Municipio.objects.select_related("id_departamento").order_by("id_departamento__nombre", "nombre")
        )
        self.fields["id_municipio"].label_from_instance = (
            lambda m: f"{m.nombre} ({m.id_departamento.nombre})" if m.id_departamento_id else m.nombre
        )
        self.fields["porcentaje_descuento"].required = False
        for nombre, campo in self.fields.items():
            campo.widget.attrs.setdefault("aria-describedby", f"id_{nombre}-ayuda")
        if self.instance.pk and self.instance.precio is not None:
            self.initial["precio"] = f"{int(self.instance.precio):,}".replace(",", ".")
        if self.instance.pk:
            # «500.00» o «0.600» confunden: se muestran sin ceros de relleno.
            for nombre in ("cantidad_presentacion", "peso_kg", "porcentaje_descuento"):
                valor = getattr(self.instance, nombre)
                if valor is not None:
                    texto = format(valor.normalize(), "f")
                    self.initial[nombre] = texto if nombre == "porcentaje_descuento" else texto.replace(".", ",")
            frio = self.instance.requiere_frio_override
            self.initial["requiere_frio_override"] = "" if frio is None else str(frio)

    # ---- fotos ---------------------------------------------------------------------

    def full_clean(self):
        super().full_clean()
        for nombre in self.errors:
            if nombre in self.fields:
                self.fields[nombre].widget.attrs["aria-invalid"] = "true"

    def fotos_existentes(self):
        if not self.instance.pk:
            return []
        return list(self.instance.imagenproducto_set.all())

    def _ids(self, campo):
        return {int(t) for t in (self.cleaned_data.get(campo) or "").split(",") if t.strip().isdigit()}

    def clean(self):
        cleaned = super().clean()

        if cleaned.get("presentacion") in PRESENTACIONES_SIN_CANTIDAD:
            cleaned["cantidad_presentacion"] = None

        if cleaned.get("es_promocionado"):
            pct = cleaned.get("porcentaje_descuento")
            if not pct:
                self.add_error("porcentaje_descuento", "Escribe cuánto descuento das, por ejemplo 10.")
            elif not (1 <= pct <= 90):
                self.add_error("porcentaje_descuento", "El descuento debe estar entre 1 % y 90 %.")
        else:
            cleaned["porcentaje_descuento"] = Decimal("0")

        existentes = {img.pk for img in self.fotos_existentes()}
        quitar = self._ids("quitar_fotos") & existentes
        cleaned["quitar_fotos_ids"] = quitar
        nuevas = cleaned.get("fotos") or []
        total = len(existentes - quitar) + len(nuevas)
        if "fotos" not in self.errors:
            if total > FOTOS_MAX:
                self.add_error("fotos", f"Puedes tener máximo {FOTOS_MAX} fotos; quita {total - FOTOS_MAX}.")
            elif total < self.fotos_minimas:
                faltan = self.fotos_minimas - total
                self.add_error(
                    "fotos",
                    f"Sube al menos {self.fotos_minimas} fotos del producto "
                    f"(te falta{'n' if faltan > 1 else ''} {faltan}).",
                )
        return cleaned

    def orden_final(self, nuevas_imagenes):
        """Imágenes (existentes conservadas + nuevas ya creadas) en el orden pedido. Lo
        que el token no menciona va al final, en orden de subida."""
        conservadas = {
            img.pk: img for img in self.fotos_existentes() if img.pk not in self.cleaned_data["quitar_fotos_ids"]
        }
        ordenadas = []
        for token in (self.cleaned_data.get("orden_fotos") or "").split(","):
            token = token.strip()
            if token[:1] == "e" and token[1:].isdigit():
                img = conservadas.pop(int(token[1:]), None)
            elif token[:1] == "n" and token[1:].isdigit() and int(token[1:]) < len(nuevas_imagenes):
                img = nuevas_imagenes[int(token[1:])]
            else:
                img = None
            if img is not None and img not in ordenadas:
                ordenadas.append(img)
        resto = sorted(conservadas.values(), key=lambda i: (i.orden, i.pk))
        resto += [i for i in nuevas_imagenes if i not in ordenadas]
        return ordenadas + [i for i in resto if i not in ordenadas]


class ProductoForm(ProductoPanelForm):
    """Versión de staff (`/dashboard/`): además elige productor, estado y fabricante, y
    no exige el mínimo de fotos para poder corregir productos viejos."""

    id_productor = forms.ModelChoiceField(
        queryset=Productor.objects.none(),
        required=True,
        label="Productor",
        empty_label="Elige el productor",
    )
    estado = forms.ChoiceField(choices=estado_choices, label="Estado en la tienda", initial="revisión")

    fotos_minimas = 0

    class Meta(ProductoPanelForm.Meta):
        fields = ProductoPanelForm.Meta.fields + ["id_productor", "fabricante", "estado"]
        labels = {**ProductoPanelForm.Meta.labels, "fabricante": "Fabricante (texto libre, heredado)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["id_productor"].queryset = (
            Productor.objects.select_related("id_municipio").order_by("nombre")
        )
        self.fields["id_productor"].label_from_instance = (
            lambda p: f"{p.nombre} ({p.id_municipio.nombre})" if p.id_municipio_id else f"{p.nombre} (sin municipio)"
        )
        self.fields["fabricante"].required = False


class ProductoPublicoForm(ProductoPanelForm):
    """Formulario abierto (`/panel/`): sin cuenta ni link. Quien lo llena se elige de la
    lista de productores o, si no aparece, deja sus datos y el equipo los revisa junto
    con el producto. Todo lo que entra por aquí queda en `revisión`."""

    id_productor = forms.ModelChoiceField(
        queryset=Productor.objects.none(),
        required=False,
        label="Productor",
        empty_label="Elige el productor",
    )
    no_estoy = forms.BooleanField(required=False, label="El productor no está en la lista")
    nuevo_nombre = forms.CharField(
        max_length=100, required=False, label="Nombre del productor",
        widget=forms.TextInput(attrs={"autocomplete": "organization", "placeholder": "Ej.: Lácteos La Esperanza"}),
    )
    nuevo_telefono = forms.CharField(
        max_length=20, required=False, label="Celular del productor",
        widget=forms.TextInput(attrs={
            "type": "tel", "inputmode": "numeric", "autocomplete": "tel-national",
            "maxlength": "16", "placeholder": "Ej.: 300 123 4567",
        }),
    )
    nuevo_municipio = forms.ModelChoiceField(
        queryset=Municipio.objects.none(), required=False, label="Municipio del productor",
        empty_label="Elige tu municipio",
    )
    # Trampa para bots: invisible para personas; si llega con algo, se descarta el envío.
    sitio_web = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["id_productor"].queryset = (
            Productor.objects.select_related("id_municipio__id_departamento").order_by("nombre")
        )
        self.fields["id_productor"].label_from_instance = (
            lambda p: f"{p.nombre} — {p.ubicacion_completa}" if p.id_municipio_id else p.nombre
        )
        municipios = Municipio.objects.select_related("id_departamento").order_by("nombre")
        self.fields["nuevo_municipio"].queryset = municipios
        self.fields["nuevo_municipio"].label_from_instance = self.fields["id_municipio"].label_from_instance
        for nombre in ("id_productor", "no_estoy", "nuevo_nombre", "nuevo_telefono", "nuevo_municipio"):
            self.fields[nombre].widget.attrs.setdefault("aria-describedby", f"id_{nombre}-ayuda")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("sitio_web"):
            raise ValidationError("No pudimos procesar el envío.", code="bot")
        if cleaned.get("no_estoy"):
            if not (cleaned.get("nuevo_nombre") or "").strip():
                self.add_error("nuevo_nombre", "Escribe el nombre del productor.")
            telefono = normalizar_celular(cleaned.get("nuevo_telefono"))
            if not CELULAR_RE.match(telefono):
                self.add_error("nuevo_telefono", ERROR_CELULAR)
            cleaned["nuevo_telefono"] = telefono
            if not cleaned.get("nuevo_municipio"):
                self.add_error("nuevo_municipio", "Elige el municipio del productor.")
            cleaned["id_productor"] = None
        elif not cleaned.get("id_productor"):
            self.add_error("id_productor", "Elige el productor de la lista, o marca «El productor no está en la lista».")
        return cleaned

    def productor(self):
        """El productor elegido, o uno nuevo con los datos escritos (sin guardar aún)."""
        if self.cleaned_data.get("no_estoy"):
            return Productor(
                nombre=self.cleaned_data["nuevo_nombre"].strip(),
                telefono=self.cleaned_data["nuevo_telefono"],
                id_municipio=self.cleaned_data["nuevo_municipio"],
                descripcion="Registrado desde el formulario de productos. Revisar y completar.",
            )
        return self.cleaned_data["id_productor"]
