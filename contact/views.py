from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ContactThrottle(AnonRateThrottle):
    rate = '5/hour'


class ContactView(APIView):
    throttle_classes = [ContactThrottle]
    permission_classes = []

    def post(self, request):
        data = request.data

        nombre = data.get('nombre', '').strip()
        email = data.get('email', '').strip()
        telefono = data.get('telefono', '').strip()
        asunto = data.get('asunto', '').strip()
        mensaje = data.get('mensaje', '').strip()

        # Validaciones básicas
        errors = {}
        if not nombre:
            errors['nombre'] = 'El nombre es requerido.'
        if not email:
            errors['email'] = 'El email es requerido.'
        elif '@' not in email:
            errors['email'] = 'Ingresa un email válido.'
        if not asunto:
            errors['asunto'] = 'El asunto es requerido.'
        if not mensaje:
            errors['mensaje'] = 'El mensaje es requerido.'
        elif len(mensaje) < 10:
            errors['mensaje'] = 'El mensaje debe tener al menos 10 caracteres.'

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        cuerpo = f"""
Nuevo mensaje de contacto recibido desde Autóctonos

─────────────────────────────────────
Nombre:    {nombre}
Email:     {email}
Teléfono:  {telefono or 'No proporcionado'}
─────────────────────────────────────
Asunto: {asunto}

Mensaje:
{mensaje}
─────────────────────────────────────
        """.strip()

        try:
            send_mail(
                subject=f'[Autóctonos - Contacto] {asunto}',
                message=cuerpo,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            return Response(
                {'message': 'Tu mensaje fue enviado con éxito. Te contactaremos pronto.'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f'Error enviando email de contacto: {e}')
            return Response(
                {'message': 'Hubo un error al enviar el mensaje. Intenta de nuevo más tarde.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
