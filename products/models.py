from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal
from users.models import Usuario
from locations.models import Municipio

estado_choices = [
    ('aprobado', 'Aprobado'),
    ('rechazado', 'Rechazado'),
    ('revisión', 'Revisión'),
]

presentacion_choices = [
    ('Lb', 'Libras (Lb)'),
    ('Kg', 'Kilogramos (Kg)'),
    ('Un', 'Unidad (Un)'),
    ('Paq', 'Paquete (Paq x12)'),
    ('Gr', 'Gramos (Gr)'),
    ('Oz', 'Onzas (Oz)'),
    ('Lt', 'Litros (Lt)'),
    ('Ml', 'Mililitros (Ml)'),
    ('Dz', 'Docena (Dz)'),
    ('Bt', 'Botella (Cm3)'),
]


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False, unique=True)
    requiere_frio = models.BooleanField(
        default=False,
        verbose_name="Requiere cadena de frío",
        help_text="Default para los productos de la categoría. Cada producto puede sobreescribirlo.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre']


class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=False)
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.TextField(null=False)
    precio = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    stock = models.IntegerField(null=False)
    presentacion = models.CharField(max_length=10, choices=presentacion_choices, default='Un', null=False)
    cantidad_presentacion = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cantidad por presentación",
        help_text="Ej: 200 para 200 g, 1.5 para 1.5 L. Opcional.",
    )
    peso_kg = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name="Peso de despacho (kg)",
        help_text="Peso real de despacho con empaque. Sin él el producto no se puede cotizar.",
    )
    requiere_frio_override = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name="Cadena de frío (override)",
        help_text="Vacío: hereda de la categoría.",
    )
    id_productor = models.ForeignKey(
        'productores.Productor',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='productos',
        verbose_name="Productor",
        help_text=(
            "Quien despacha. Define el origen del envío y agrupa los fletes del pedido. "
            "Sin él el producto no se puede cotizar."
        ),
    )
    id_municipio = models.ForeignKey(
        Municipio, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos',
        verbose_name="Municipio de origen (override)",
        help_text="Vacío: se despacha desde el municipio del productor.",
    )
    fabricante = models.CharField(max_length=200, null=True, blank=True)
    es_promocionado = models.BooleanField(default=False, verbose_name="Promocionado")
    porcentaje_descuento = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0, verbose_name="Porcentaje de Descuento (%)")
    estado = models.CharField(max_length=10, choices=estado_choices, default='revisión', verbose_name="Estado")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-created_at']

    @property
    def requiere_frio(self):
        if self.requiere_frio_override is not None:
            return self.requiere_frio_override
        return self.id_categoria.requiere_frio

    @property
    def municipio_origen(self):
        """Desde dónde sale el paquete: el override del producto y, si no, el municipio
        del productor. Única fuente de la tarifa de origen."""
        if self.id_municipio_id is not None:
            return self.id_municipio
        if self.id_productor_id is not None:
            return self.id_productor.id_municipio
        return None

    @property
    def es_despachable(self):
        """Tiene los datos mínimos para cotizar un envío."""
        return self.peso_kg is not None and self.municipio_origen is not None

    def precio_con_descuento(self):
        """Calcula el precio con descuento si el producto está promocionado"""
        if self.es_promocionado and self.porcentaje_descuento:
            descuento = self.precio * (self.porcentaje_descuento / Decimal('100'))
            precio_final = self.precio - descuento
            # Redondear a 2 decimales para mantener consistencia con el campo precio
            return precio_final.quantize(Decimal('0.01'))
        return self.precio
    
    def precio_original(self):
        """Retorna el precio original (siempre el precio base)"""
        return self.precio

    def get_presentacion_completa(self):
        """Ej: '200 Gr', '1.5 Lt' o 'Unidad (Un)' si no hay cantidad. Sin notación científica."""
        if self.cantidad_presentacion is not None:
            d = self.cantidad_presentacion
            if d == d.to_integral_value():
                cantidad_str = str(int(d))
            else:
                cantidad_str = f"{d:.2f}".rstrip("0").rstrip(".")
            return f"{cantidad_str} {self.presentacion}"
        return self.get_presentacion_display()


class ImagenProducto(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=False)
    url_imagen = models.ImageField(upload_to='productos_imagenes/', null=True, blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return f"Imagen {self.id_imagen} - {self.id_producto.nombre}"

    class Meta:
        verbose_name = "Imagen de Producto"
        verbose_name_plural = "Imágenes de Productos"

class Post(models.Model):
    id_post = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=False)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=False)
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.TextField(null=False)
    precio = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    stock = models.IntegerField(null=False)
    estado = models.CharField(max_length=10, choices=estado_choices, default='revisión')
    mensaje = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(default=None, null=True)
    producto = models.OneToOneField(Producto, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Post: {self.nombre} ({self.estado})"

    class Meta:
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        ordering = ['-created_at']

