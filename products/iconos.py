"""Íconos de categoría: catálogo Lucide servido por la API pública de Iconify.

El admin elige el ícono contra Iconify (navegador → api.iconify.design). Al guardar,
Django descarga el SVG UNA vez, lo sanea y lo congela en `Categoria.icono_svg`. La
tienda pinta ese SVG guardado: no depende de Iconify en runtime ni de qué versión de
lucide-react tenga instalada (Iconify trae íconos que el paquete local todavía no).
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from xml.etree import ElementTree
from xml.sax.saxutils import quoteattr

ICONIFY_API = "https://api.iconify.design"
COLECCION = "lucide"
TIMEOUT_S = 6

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Lo único que puede sobrevivir del SVG. Todo lo demás (script, style, foreignObject,
# href, on*, …) hace fallar el saneo en vez de colarse a la tienda.
_TAGS = {"svg", "g", "path", "circle", "ellipse", "line", "polyline", "polygon", "rect"}
_ATTRS = {
    "d", "cx", "cy", "r", "rx", "ry", "x", "y", "x1", "x2", "y1", "y2", "width", "height",
    "points", "fill", "fill-rule", "clip-rule", "stroke", "stroke-width", "stroke-linecap",
    "stroke-linejoin", "stroke-miterlimit", "opacity", "fill-opacity", "stroke-opacity",
    "transform", "viewBox",
}
_VALOR_PELIGROSO = re.compile(r"url\s*\(|javascript:|expression\s*\(|<|>", re.I)


class IconoError(Exception):
    """Mensaje apto para mostrarle al admin."""


def _serializar(el: ElementTree.Element) -> str:
    tag = el.tag.split("}")[-1]
    if tag not in _TAGS:
        raise IconoError(f"El SVG trae un elemento no permitido: <{tag}>.")
    attrs = []
    for nombre, valor in el.attrib.items():
        nombre = nombre.split("}")[-1]
        if nombre not in _ATTRS or _VALOR_PELIGROSO.search(valor):
            raise IconoError(f"El SVG trae un atributo no permitido: {nombre}.")
        attrs.append(f" {nombre}={quoteattr(valor)}")
    if tag == "svg":
        attrs.insert(0, ' xmlns="http://www.w3.org/2000/svg"')
    hijos = "".join(_serializar(h) for h in el)
    return f"<{tag}{''.join(attrs)}>{hijos}</{tag}>"


def sanear_svg(svg: str) -> str:
    try:
        raiz = ElementTree.fromstring(svg)
    except ElementTree.ParseError as exc:
        raise IconoError("El SVG del ícono no es válido.") from exc
    if raiz.tag.split("}")[-1] != "svg":
        raise IconoError("El ícono no es un SVG.")
    return _serializar(raiz)


def descargar_svg(slug: str) -> str:
    """SVG saneado del ícono Lucide `slug`, listo para guardar. Lanza `IconoError`."""
    if not SLUG_RE.match(slug or ""):
        raise IconoError("Nombre de ícono inválido.")

    url = f"{ICONIFY_API}/{COLECCION}.json?" + urllib.parse.urlencode({"icons": slug})
    # Cloudflare (delante de Iconify) rechaza con 403 el User-Agent por defecto de urllib.
    peticion = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "category-icon-fetcher/1.0"}
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIMEOUT_S) as respuesta:
            datos = json.load(respuesta)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise IconoError(
            "No se pudo descargar el ícono (sin conexión con Iconify). Intenta guardar de nuevo."
        ) from exc

    icono = (datos.get("icons") or {}).get(slug)
    if not icono or not icono.get("body"):
        raise IconoError(f"El ícono «{slug}» no existe en Lucide.")

    ancho = icono.get("width") or datos.get("width") or 24
    alto = icono.get("height") or datos.get("height") or 24
    return sanear_svg(f'<svg viewBox="0 0 {int(ancho)} {int(alto)}">{icono["body"]}</svg>')
