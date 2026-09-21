"""Marca como `cancelado` los Pedido pendientes que nadie terminó de pagar.

`crear_pedido_pendiente` (services/order_creation.py) persiste el Pedido ANTES de que el
comprador llegue a PayU: si abandona el checkout, cierra la pestaña, o el precio le
cambió y nunca confirmó, el Pedido queda en `pendiente` para siempre — nadie vuelve a
tocarlo porque el webhook de confirmación (`payu_confirmation.py`) sólo llega si el
comprador de verdad completa el pago en PayU.

Sólo reporta por defecto. Escribe con `--apply`. Pensado para correr por cron
(diariamente basta: un pedido "pendiente" con más de un día casi seguro fue abandonado).
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import Pedido


class Command(BaseCommand):
    help = "Cancela los Pedido pendientes más viejos que --horas (abandonados en el checkout)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--horas', type=int, default=24,
            help="Antigüedad mínima en horas para considerar un pedido abandonado (default: 24).",
        )
        parser.add_argument(
            '--apply', action='store_true',
            help="Escribe los cambios. Sin esta bandera sólo reporta.",
        )

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(hours=options['horas'])
        candidatos = Pedido.objects.filter(estado='pendiente', created_at__lt=limite)
        total = candidatos.count()

        if not options['apply']:
            self.stdout.write(self.style.WARNING(
                f"Dry-run: {total} pedido(s) pendientes de hace más de {options['horas']}h "
                "se cancelarían. Corre con --apply para escribir."
            ))
            return

        actualizados = candidatos.update(estado='cancelado')
        self.stdout.write(self.style.SUCCESS(
            f"{actualizados} pedido(s) pendientes marcados como cancelados."
        ))
