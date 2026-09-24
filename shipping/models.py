from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from locations.models import Municipio

trayecto_choices = [
    ('urbano', 'Urbano'),
    ('zonal', 'Zonal'),
    ('nacional', 'Nacional'),
    ('territorial', 'Territorial'),
    ('especial', 'Especial'),
]


class Trayecto(models.Model):
    """Tarifa de la transportadora. La jerarquía es única: MAX(origen, destino) debe
    resolver a una sola tarifa."""

    id_trayecto = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=20, unique=True, choices=trayecto_choices, verbose_name="Código")
    nombre = models.CharField(max_length=50, verbose_name="Nombre")
    jerarquia = models.PositiveSmallIntegerField(
        unique=True,
        verbose_name="Jerarquía",
        help_text="Mayor jerarquía gana cuando origen y destino difieren.",
    )
    valor_kilo_inicial = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Valor kilo inicial",
    )
    valor_kilo_adicional = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Valor kilo adicional",
    )
    sobreflete_minimo = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('800.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Sobreflete mínimo",
    )
    porcentaje_sobreflete = models.DecimalField(
        max_digits=6, decimal_places=4, default=Decimal('0.0200'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Porcentaje de sobreflete",
        help_text="Fracción sobre el subtotal del grupo. 0.0200 = 2%.",
    )
    cobrar_kilo_adicional_en_1kg = models.BooleanField(
        default=False,
        verbose_name="Cobrar kilo adicional en envíos de 1 kg",
        help_text=(
            "OBSOLETO: el tarifario vigente usa `SI(peso>=1; peso-1; peso)`, que nunca "
            "cobra adicional en 1 kg. El cálculo ya no lo lee; la columna se elimina en "
            "el próximo release."
        ),
    )
    dias_entrega_min = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Días hábiles (mínimo)",
        help_text="Hoja «Convenciones» del tarifario. Se resuelve con el trayecto aplicado.",
    )
    dias_entrega_max = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Días hábiles (máximo)",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} (jerarquía {self.jerarquia})"

    @property
    def etiqueta_entrega(self):
        """«1 día hábil» o «1-3 días hábiles»."""
        if self.dias_entrega_min == self.dias_entrega_max:
            unidad = "día hábil" if self.dias_entrega_min == 1 else "días hábiles"
            return f"{self.dias_entrega_min} {unidad}"
        return f"{self.dias_entrega_min}-{self.dias_entrega_max} días hábiles"

    class Meta:
        verbose_name = "Trayecto"
        verbose_name_plural = "Trayectos"
        ordering = ['jerarquia']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(dias_entrega_max__gte=models.F('dias_entrega_min')),
                name='trayecto_dias_entrega_coherentes',
            ),
        ]


class CoberturaMunicipio(models.Model):
    """Un municipio dentro de la red de envíos. Ausencia de fila = municipio no
    soportado, ni como origen ni como destino."""

    id_cobertura = models.AutoField(primary_key=True)
    municipio = models.OneToOneField(
        Municipio, on_delete=models.PROTECT, related_name='cobertura', verbose_name="Municipio"
    )
    trayecto_origen = models.ForeignKey(
        Trayecto, on_delete=models.PROTECT, null=True, blank=True,
        related_name='coberturas_origen', verbose_name="Trayecto como origen",
        help_text="Vacío: no se despacha mercancía desde este municipio.",
    )
    trayecto_destino = models.ForeignKey(
        Trayecto, on_delete=models.PROTECT, null=True, blank=True,
        related_name='coberturas_destino', verbose_name="Trayecto como destino",
        help_text="Vacío: el municipio no aparece como destino en el checkout.",
    )
    provincia = models.CharField(max_length=100, blank=True, default='', verbose_name="Provincia")
    distancia_km_tunja = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
        verbose_name="Distancia a Tunja (km)", help_text="Informativa, no interviene en el cálculo.",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.municipio)

    class Meta:
        verbose_name = "Cobertura de municipio"
        verbose_name_plural = "Cobertura de municipios"
        ordering = ['municipio__id_departamento__nombre', 'municipio__nombre']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(trayecto_origen__isnull=False) | models.Q(trayecto_destino__isnull=False),
                name='cobertura_al_menos_un_trayecto',
            ),
        ]


class ConfiguracionEmpaque(models.Model):
    """Costo del empaque refrigerado. Singleton: una sola fila activa."""

    id_configuracion = models.AutoField(primary_key=True)
    capacidad_kg = models.DecimalField(
        max_digits=7, decimal_places=3, default=Decimal('6.000'),
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name="Capacidad por nevera (kg)",
    )
    costo_nevera = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('12000.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Costo por nevera",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Nevera de {self.capacidad_kg} kg — ${self.costo_nevera}"

    class Meta:
        verbose_name = "Configuración de empaque"
        verbose_name_plural = "Configuración de empaque"
        constraints = [
            models.UniqueConstraint(
                fields=['activo'], condition=models.Q(activo=True), name='empaque_configuracion_unica_activa'
            ),
        ]


class PromocionEnvio(models.Model):
    """Envío gratis por monto. Singleton: una sola fila activa."""

    id_promocion = models.AutoField(primary_key=True)
    umbral_subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('200000.00'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Umbral de subtotal",
        help_text="Subtotal de productos a partir del cual se cubre el flete.",
    )
    jerarquia_maxima_cubierta = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Jerarquía máxima cubierta",
        help_text="Vacío: cubre cualquier destino. 2: sólo urbano y zonal.",
    )
    tope_cubierto = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Tope cubierto", help_text="Vacío: sin tope.",
    )
    cubre_sobreflete = models.BooleanField(
        default=True, verbose_name="Cubre el sobreflete",
        help_text=(
            "OBSOLETO: el sobreflete es la garantía del producto y siempre se cobra. "
            "El cálculo ya no lo lee; la columna se elimina en el próximo release."
        ),
    )
    cubre_empaque = models.BooleanField(default=False, verbose_name="Cubre el empaque refrigerado")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Flete gratis desde ${self.umbral_subtotal}"

    class Meta:
        verbose_name = "Promoción de envío"
        verbose_name_plural = "Promociones de envío"
        constraints = [
            models.UniqueConstraint(
                fields=['activo'], condition=models.Q(activo=True), name='promocion_envio_unica_activa'
            ),
        ]
