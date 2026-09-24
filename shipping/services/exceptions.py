"""Errores de negocio de la cotización. La vista los traduce a HTTP 422."""


class ErrorCotizacion(Exception):
    code = 'error_cotizacion'

    def __init__(self, detail, contexto=None):
        super().__init__(detail)
        self.detail = detail
        self.contexto = contexto or {}

    def as_dict(self):
        return {'code': self.code, 'detail': self.detail, 'contexto': self.contexto}


class CarritoVacio(ErrorCotizacion):
    code = 'carrito_vacio'


class DestinoNoSoportado(ErrorCotizacion):
    code = 'destino_no_soportado'


class ProductoNoDisponible(ErrorCotizacion):
    code = 'producto_no_disponible'


class ProductoSinPeso(ErrorCotizacion):
    code = 'producto_sin_peso'


class ProductoSinOrigen(ErrorCotizacion):
    code = 'producto_sin_origen'


class OrigenNoSoportado(ErrorCotizacion):
    code = 'origen_no_soportado'


class EmpaqueNoConfigurado(ErrorCotizacion):
    code = 'empaque_no_configurado'


class ProductoSinProductor(ErrorCotizacion):
    code = 'producto_sin_productor'
