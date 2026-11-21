"""Panel de carga de productos.

Dos puertas, una sola pantalla (`products/panel.html`):

- **Formulario abierto** — `/panel/`. Sin cuenta: quien lo llena se elige de la lista de
  productores (o deja sus datos si no aparece). Solo crea; todo queda en `revisión` y
  staff decide en el admin si se publica. Los productos del productor elegido se ven
  solo para consulta (`/panel/productos/`): sin login no hay forma segura de editar.
- **Staff** — `/dashboard/`. Login de admin. Crea y edita, elige productor y estado, y
  filtra la lista por productor.
"""

from django.contrib import messages
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.views.decorators.cache import never_cache
from functools import wraps

from producers.models import Productor

from .forms import FOTOS_MAX, FOTOS_MIN, ProductoForm, ProductoPublicoForm
from .models import Categoria, ImagenProducto, Producto

POR_PAGINA = 24
# Envíos del formulario abierto por IP y por hora: frena abusos sin estorbar a nadie real.
ENVIOS_POR_HORA = 30
# Canal para pedir cambios a un producto ya enviado (el formulario abierto no edita). Es
# el mismo correo que publica la tienda en /contacto.
CONTACTO_EMAIL = "productos.autoctonos25@gmail.com"


def _productos(productor=None):
    qs = (
        Producto.objects.filter(deleted_at__isnull=True)
        .select_related("id_categoria", "id_productor__id_municipio__id_departamento", "id_municipio__id_departamento")
        .prefetch_related("imagenproducto_set")
        .order_by("-created_at")
    )
    return qs.filter(id_productor=productor) if productor is not None else qs


def en_espanol(vista):
    """El sitio corre en `en-us` (admin incluido); el panel es para productores y sus
    mensajes de validación de Django («This field is required») deben salir en español."""
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        with translation.override("es"):
            response = vista(request, *args, **kwargs)
            if hasattr(response, "render") and not getattr(response, "is_rendered", True):
                response.render()
            return response
    return envoltura


def faltantes(producto):
    """Lo que le impide a un producto venderse bien, en palabras del productor."""
    fotos = len(producto.imagenproducto_set.all())  # usa el prefetch
    pendientes = []
    if fotos < FOTOS_MIN:
        pendientes.append(f"{fotos} de {FOTOS_MIN} fotos")
    if producto.peso_kg is None:
        pendientes.append("peso del paquete")
    if producto.municipio_origen is None:
        pendientes.append("municipio de despacho")
    if not producto.stock:
        pendientes.append("sin unidades disponibles")
    return pendientes


@transaction.atomic
def guardar_producto(form, productor=None):
    """Guarda el producto y sus fotos (altas, bajas y orden) en una sola transacción.

    Con `productor` (formulario abierto) el producto queda a su nombre y siempre en
    `revisión`, diga lo que diga la petición."""
    producto = form.save(commit=False)
    if productor is not None:
        if productor.pk is None:
            productor.save()
        producto.id_productor = productor
        producto.estado = "revisión"
    producto.save()

    quitar = form.cleaned_data.get("quitar_fotos_ids") or set()
    if quitar:
        ImagenProducto.objects.filter(id_producto=producto, pk__in=quitar).delete()
    nuevas = [
        ImagenProducto.objects.create(id_producto=producto, url_imagen=archivo)
        for archivo in form.cleaned_data.get("fotos") or []
    ]
    for i, imagen in enumerate(form.orden_final(nuevas)):
        if imagen.orden != i:
            imagen.orden = i
            imagen.save(update_fields=["orden"])
    return producto


def _con_extras(page):
    for p in page.object_list:
        p.panel_faltantes = faltantes(p)
        p.panel_portada = next(iter(p.imagenproducto_set.all()), None)
    return page


def _inventario(request, productor, staff):
    """Contexto de la lista de productos. Sin productor en el formulario abierto no hay lista."""
    if productor is None and not staff:
        return {"page": None, "total": 0, "resumen": {}}
    lista = _productos(productor)
    page = _con_extras(Paginator(lista, POR_PAGINA).get_page(request.GET.get("page", 1)))
    resumen = {"revisión": 0, "aprobado": 0, "rechazado": 0}
    for estado in lista.values_list("estado", flat=True):
        resumen[estado] = resumen.get(estado, 0) + 1
    return {"page": page, "total": page.paginator.count, "resumen": resumen}


def _motivos_error(form):
    """[(campo, mensaje)] para explicar en el aviso flotante por qué no se guardó."""
    if not form.is_bound or not form.errors:
        return []
    # En el orden en que aparecen en la página (Django pone al final los campos que el
    # formulario público agrega, como el productor del paso 1).
    orden = ["__all__", "id_productor", "nuevo_nombre", "nuevo_telefono", "nuevo_municipio", "fotos",
             "id_categoria", "nombre", "descripcion", "presentacion", "cantidad_presentacion",
             "precio", "stock", "porcentaje_descuento", "peso_kg", "requiere_frio_override", "id_municipio"]
    posicion = {n: i for i, n in enumerate(orden)}
    motivos = []
    for nombre, errores in sorted(form.errors.items(), key=lambda kv: posicion.get(kv[0], len(orden))):
        campo = form.fields.get(nombre)
        if campo is not None and campo.widget.is_hidden:
            continue
        etiqueta = "" if nombre == "__all__" or campo is None else str(campo.label)
        motivos.extend((etiqueta, str(e)) for e in errores)
    return motivos[:8]


def _render(request, *, form, producto, productor, staff, urls):
    categorias = Categoria.objects.only("pk", "nombre", "requiere_frio")
    response = render(request, "products/panel.html", {
        "form": form,
        "producto": producto,
        "productor": productor,
        "staff": staff,
        "urls": urls,
        **_inventario(request, productor, staff),
        "fotos_existentes_json": [
            {"id": img.pk, "url": img.url_imagen.url} for img in form.fotos_existentes() if img.url_imagen
        ],
        "fotos_min": form.fotos_minimas,
        "fotos_max": FOTOS_MAX,
        "categorias_json": {str(c.pk): {"nombre": c.nombre, "frio": c.requiere_frio} for c in categorias},
        "municipio_productor": productor.ubicacion_completa if productor else "",
        "contacto_email": CONTACTO_EMAIL,
        # El navegador no puede volver a llenar un <input type=file>: si el envío falló,
        # hay que decirle a quien lo llena que vuelva a elegir las fotos nuevas.
        "fotos_perdidas": len(request.FILES.getlist("fotos")) if form.is_bound and form.errors else 0,
        "creado": request.session.pop("panel_creado", None),
        "motivos_error": _motivos_error(form),
    })
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


def _procesar(request, form_class, *, instance, exito_url, publico=False, form_kwargs=None):
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=instance, **(form_kwargs or {}))
        if form.is_valid():
            producto = guardar_producto(form, productor=form.productor() if publico else None)
            if instance is None:
                # Datos para el aviso flotante de la siguiente página (se lee una sola vez).
                portada = producto.imagenproducto_set.first()
                request.session["panel_creado"] = {
                    "nombre": producto.nombre,
                    "foto": portada.url_imagen.url if portada and portada.url_imagen else "",
                    "publico": publico,
                }
            if publico:
                messages.success(
                    request,
                    f"¡Listo! «{producto.nombre}» quedó en revisión. El equipo de Autóctonos lo "
                    "revisa y lo publica en la tienda.",
                )
            elif instance is None:
                messages.success(request, f"«{producto.nombre}» creado.")
            else:
                messages.success(request, f"Guardamos los cambios de «{producto.nombre}».")
            return form, redirect(exito_url(producto))
        messages.error(request, "Revisa los campos marcados en rojo.")
        return form, None
    return form_class(instance=instance, **(form_kwargs or {})), None


# ---- Formulario abierto ---------------------------------------------------------------


def _ip(request):
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return reenviada.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")


def _supera_limite(request):
    clave = f"panel-envios:{_ip(request)}"
    cache.add(clave, 0, timeout=3600)
    try:
        return cache.incr(clave) > ENVIOS_POR_HORA
    except ValueError:
        return False


def _productor_de_query(request):
    pid = request.GET.get("productor", "")
    if not pid.isdigit():
        return None
    return Productor.objects.select_related("id_municipio__id_departamento").filter(pk=pid).first()


@never_cache
@en_espanol
def formulario_productor(request):
    if request.method == "POST" and _supera_limite(request):
        return HttpResponse(
            "Recibimos muchos envíos desde tu conexión. Intenta de nuevo en una hora.", status=429,
        )
    inicio = reverse("panel-productor")
    elegido = _productor_de_query(request)
    form, redireccion = _procesar(
        request, ProductoPublicoForm, instance=None, publico=True,
        exito_url=lambda p: f"{inicio}?productor={p.id_productor_id}#productos",
        form_kwargs={"initial": {"id_productor": elegido.pk}} if elegido else None,
    )
    if redireccion:
        return redireccion
    if form.is_bound:
        elegido = form.cleaned_data.get("id_productor") if hasattr(form, "cleaned_data") else None
    return _render(request, form=form, producto=None, productor=elegido, staff=False,
                   urls={"inicio": inicio})


@never_cache
@en_espanol
def productos_de_productor(request):
    """Fragmento HTML (solo consulta) con los productos de un productor, para el
    formulario abierto. Sin edición: cualquiera con la URL puede verlo."""
    productor = _productor_de_query(request)
    return render(request, "products/_inventario.html", {
        "productor": productor, "staff": False, "contacto_email": CONTACTO_EMAIL,
        **_inventario(request, productor, False),
    })


# ---- Staff ---------------------------------------------------------------------------


def _staff_o_403(request):
    return None if request.user.is_staff else HttpResponseForbidden()


def _filtro_productor(request):
    pid = request.GET.get("productor", "")
    return Productor.objects.filter(pk=pid).first() if pid.isdigit() else None


@login_required(login_url="/admin/login/")
@never_cache
@en_espanol
def product_dashboard(request):
    if (denegado := _staff_o_403(request)):
        return denegado
    filtro = _filtro_productor(request)
    inicio = reverse("product-dashboard")
    form, redireccion = _procesar(
        request, ProductoForm, instance=None,
        exito_url=lambda p: f"{inicio}?productor={p.id_productor_id}#productos",
        form_kwargs={"initial": {"id_productor": filtro.pk}} if filtro else None,
    )
    if redireccion:
        return redireccion
    return _render(request, form=form, producto=None, productor=filtro, staff=True,
                   urls={"inicio": inicio, "editar": "product-update",
                         "productores": Productor.objects.order_by("nombre").only("pk", "nombre")})


@login_required(login_url="/admin/login/")
@never_cache
@en_espanol
def product_update(request, pk):
    if (denegado := _staff_o_403(request)):
        return denegado
    producto = get_object_or_404(Producto, pk=pk)
    inicio = reverse("product-dashboard")
    form, redireccion = _procesar(
        request, ProductoForm, instance=producto,
        exito_url=lambda p: f"{inicio}?productor={p.id_productor_id}#productos",
    )
    if redireccion:
        return redireccion
    return _render(request, form=form, producto=producto, productor=producto.id_productor, staff=True,
                   urls={"inicio": inicio, "editar": "product-update",
                         "productores": Productor.objects.order_by("nombre").only("pk", "nombre")})
