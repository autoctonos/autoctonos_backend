"""Estándar de fotos de producto: validación al subir y normalización del archivo maestro.

Toda foto que entra por cualquier vía (admin, dashboard, API) termina igual:

- **Cuadrada 1:1, 1600×1600 px** (o menos si el original es más chico: nunca se agranda).
- **Fondo blanco puro.** La transparencia real se aplana sobre blanco.
- **Encuadre uniforme:** si la foto ya viene sobre fondo claro y liso, se recortan los
  márgenes vacíos y el producto se centra ocupando el ~88 % del lado. Así una ruana
  fotografiada de lejos y un queso fotografiado de cerca se ven del mismo tamaño en la grilla.
- **JPEG calidad 88, sin metadatos** (el EXIF de un celular trae GPS) y con la rotación
  del EXIF ya aplicada.

Lo que no se puede arreglar en automático se rechaza con un mensaje accionable: fotos
demasiado pequeñas, muy alargadas, formatos no soportados o el fondo de «cuadritos» de una
transparencia falsa (un PNG descargado de internet con el damero pintado en los píxeles).
"""

from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError

LADO_MAESTRO = 1600
LADO_MINIMO = 800
PESO_MAXIMO_MB = 10
PROPORCION_MAXIMA = 3.0
OCUPACION_PRODUCTO = 0.88
CALIDAD_JPEG = 88
FORMATOS = {"JPEG", "PNG", "WEBP"}
BLANCO = (255, 255, 255)

GUIA = (
    f"Ideal cuadrada de {LADO_MAESTRO}×{LADO_MAESTRO} px (mínimo {LADO_MINIMO} px en el lado más largo), "
    "producto centrado sobre fondo blanco liso, buena luz y sin textos ni marcas de agua. "
    f"JPG, PNG o WEBP de hasta {PESO_MAXIMO_MB} MB."
)

# Damero de transparencia falsa: bordes hechos de dos tonos claros neutros (255 y ~204 o
# ~238) alternados en cuadros regulares. Se analizan las cuatro franjas del borde ignorando
# los píxeles con color, porque el producto suele tocar alguna esquina.
_CLARO = 248
_GRIS_MIN, _GRIS_MAX = 185, 244
_SATURACION_NEUTRA = 14
_LADO_ANALISIS = 1000

def _abrir(archivo) -> Image.Image:
    archivo.seek(0)
    try:
        imagen = Image.open(archivo)
        imagen.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError(
            "No pudimos leer la foto. Súbela en JPG, PNG o WEBP.", code="imagen_ilegible"
        ) from exc
    finally:
        archivo.seek(0)
    return imagen


def _franja_es_damero(franja: Image.Image) -> bool:
    ancho, alto = franja.size
    pixeles = list(franja.getdata())
    neutros = 0
    claros = grises = 0
    cambios = largo = 0
    for y in range(0, alto, 2):
        anterior = None
        for x in range(ancho):
            r, g, b = pixeles[y * ancho + x]
            if max(r, g, b) - min(r, g, b) > _SATURACION_NEUTRA:
                anterior = None  # Producto: corta la racha, no cuenta como cambio de cuadro.
                continue
            neutros += 1
            v = (r + g + b) // 3
            if v >= _CLARO:
                claros += 1
                tono = True
            elif _GRIS_MIN <= v <= _GRIS_MAX:
                grises += 1
                tono = False
            else:
                anterior = None
                continue
            if anterior is not None:
                largo += 1
                cambios += tono != anterior
            anterior = tono
    total = (ancho * ((alto + 1) // 2)) or 1
    if neutros < total * 0.4 or claros < neutros * 0.2 or grises < neutros * 0.2:
        return False
    if claros + grises < neutros * 0.85 or not largo:  # Margen para el ringing del JPEG.
        return False
    # Cuadros de ~4 a ~80 px (ya escalado a 1000 px): entre 1 cambio cada 80 px y 1 cada
    # 4 px. Un degradado o una sombra cambian una vez; el ruido JPEG de un fondo liso no
    # llega a la banda gris.
    return 1 / 80 <= cambios / largo <= 1 / 4


def tiene_fondo_damero(imagen: Image.Image) -> bool:
    """True si al menos dos bordes son el damero gris/blanco de una transparencia falsa."""
    rgb = imagen.convert("RGB")
    if max(rgb.size) > _LADO_ANALISIS:
        # NEAREST conserva los bordes duros del damero (un promedio los volvería gris liso).
        escala = _LADO_ANALISIS / max(rgb.size)
        rgb = rgb.resize((round(rgb.width * escala), round(rgb.height * escala)), Image.Resampling.NEAREST)
    ancho, alto = rgb.size
    grosor = max(8, min(ancho, alto) // 10)
    if min(ancho, alto) < grosor * 3:
        return False
    franjas = [
        rgb.crop((0, 0, ancho, grosor)),
        rgb.crop((0, alto - grosor, ancho, alto)),
        rgb.crop((0, 0, grosor, alto)).transpose(Image.Transpose.ROTATE_90),
        rgb.crop((ancho - grosor, 0, ancho, alto)).transpose(Image.Transpose.ROTATE_90),
    ]
    return sum(_franja_es_damero(f) for f in franjas) >= 2


def validar_imagen_producto(archivo) -> None:
    """Validador de campo: rechaza lo que la normalización no puede arreglar."""
    if archivo is None or getattr(archivo, "_committed", False):
        return  # Archivo ya guardado (edición sin cambiar la foto) o URL de seeder.
    if archivo.size and archivo.size > PESO_MAXIMO_MB * 1024 * 1024:
        raise ValidationError(
            f"La foto pesa más de {PESO_MAXIMO_MB} MB. Expórtala en JPG con menor calidad.",
            code="imagen_pesada",
        )
    imagen = _abrir(archivo)
    if imagen.format not in FORMATOS:
        raise ValidationError(
            f"Formato {imagen.format or 'desconocido'} no soportado. Súbela en JPG, PNG o WEBP "
            "(las fotos HEIC del iPhone se pueden exportar como JPG).",
            code="imagen_formato",
        )
    ancho, alto = ImageOps.exif_transpose(imagen).size
    # Se mide el lado largo: el maestro es un cuadrado de ese lado (la foto se centra sobre
    # blanco), así que una foto de 1200×800 rinde un maestro de 1200×1200 sin agrandar nada.
    if max(ancho, alto) < LADO_MINIMO:
        raise ValidationError(
            f"La foto mide {ancho}×{alto} px y su lado más largo debe tener al menos "
            f"{LADO_MINIMO} px: se vería borrosa. Usa la foto original de la cámara, no una captura ni una "
            "imagen de WhatsApp.",
            code="imagen_pequena",
        )
    if max(ancho, alto) / min(ancho, alto) > PROPORCION_MAXIMA:
        raise ValidationError(
            f"La foto es muy alargada ({ancho}×{alto} px): el producto quedaría diminuto en "
            "la tienda. Recórtala más cerca de cuadrada.",
            code="imagen_alargada",
        )
    if tiene_fondo_damero(imagen):
        raise ValidationError(
            "La foto tiene un fondo de cuadritos grises (transparencia falsa, típica de "
            "imágenes descargadas de internet). Sube una foto con fondo blanco liso.",
            code="imagen_damero",
        )
    # Sobre fondo blanco el maestro se arma alrededor del producto y nunca se agranda: si el
    # producto mide poco en píxeles (foto tomada de lejos), el resultado saldría borroso.
    plana = _aplanar_sobre_blanco(ImageOps.exif_transpose(imagen))
    recorte = _recortar_margen_claro(plana)
    if recorte is not plana and max(recorte.size) < LADO_MINIMO * OCUPACION_PRODUCTO:
        raise ValidationError(
            f"El producto se ve muy pequeño en la foto (ocupa {recorte.width}×{recorte.height} px). "
            "Acércate o recorta la foto alrededor del producto.",
            code="imagen_producto_lejano",
        )


def _aplanar_sobre_blanco(imagen: Image.Image) -> Image.Image:
    if imagen.mode in ("RGBA", "LA") or (imagen.mode == "P" and "transparency" in imagen.info):
        rgba = imagen.convert("RGBA")
        fondo = Image.new("RGB", rgba.size, BLANCO)
        fondo.paste(rgba, mask=rgba.getchannel("A"))
        return fondo
    return imagen.convert("RGB")


def _recortar_margen_claro(imagen: Image.Image) -> Image.Image:
    """Recorta el margen liso si el fondo es claro; si no, deja la foto como está."""
    ancho, alto = imagen.size
    esquinas = [imagen.getpixel(p) for p in ((0, 0), (ancho - 1, 0), (0, alto - 1), (ancho - 1, alto - 1))]
    if any(min(px) < 235 for px in esquinas):
        return imagen  # Fondo no blanco (foto ambientada): no se adivina dónde está el producto.
    diferencia = ImageChops.difference(imagen, Image.new("RGB", imagen.size, BLANCO)).convert("L")
    caja = diferencia.point(lambda v: 255 if v > 18 else 0).getbbox()
    if not caja:
        return imagen
    recorte = imagen.crop(caja)
    # Un recorte minúsculo es ruido (polvo, sombra), no el producto.
    return recorte if recorte.width * recorte.height >= ancho * alto * 0.002 else imagen


def normalizar_imagen_producto(archivo) -> ContentFile:
    """Devuelve el JPEG maestro cuadrado sobre blanco listo para guardar."""
    imagen = _aplanar_sobre_blanco(ImageOps.exif_transpose(_abrir(archivo)))
    recortada = _recortar_margen_claro(imagen)
    if recortada is not imagen:
        lado_producto = max(recortada.size)
        lado = round(lado_producto / OCUPACION_PRODUCTO)
    else:
        lado = max(imagen.size)  # Foto ambientada: sólo se completa a cuadrado.
    lienzo = Image.new("RGB", (lado, lado), BLANCO)
    lienzo.paste(recortada, ((lado - recortada.width) // 2, (lado - recortada.height) // 2))
    if lado > LADO_MAESTRO:
        lienzo = lienzo.resize((LADO_MAESTRO, LADO_MAESTRO), Image.Resampling.LANCZOS)

    salida = BytesIO()
    lienzo.save(salida, format="JPEG", quality=CALIDAD_JPEG, optimize=True, progressive=True)
    nombre = f"{Path(getattr(archivo, 'name', '') or 'producto').stem}.jpg"
    return ContentFile(salida.getvalue(), name=nombre)
