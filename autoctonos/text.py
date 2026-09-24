"""Normalización de texto compartida entre apps.

Vive en el paquete del proyecto y no en una app porque la usan tanto `shipping`
(emparejar municipios del tarifario contra la DB) como `products` (emparejar el campo
libre `fabricante` contra `producers.Productor`), y ninguna de las dos debería importar
de la otra.
"""

import unicodedata


def normalizar(texto):
    """NFKD → ASCII → minúsculas → espacios colapsados.

    «Güicán de la Sierra » y «GUICAN DE LA SIERRA» normalizan al mismo string.
    """
    if texto is None:
        return ''
    plano = unicodedata.normalize('NFKD', str(texto))
    plano = plano.encode('ascii', 'ignore').decode('ascii')
    return ' '.join(plano.lower().split())
