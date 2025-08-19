# management/commands/seed_demo.py
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from faker import Faker
from django.db import transaction
from commerce.models import DetallePedido, Envio, Pago, Pedido
from products.models import Categoria, ImagenProducto, Post, Producto
from users.models import Usuario


class Command(BaseCommand):
    help = "Genera datos de prueba (usuarios, categorías, posts, productos e imágenes)"

    def handle(self, *args, **kwargs):
        fake = Faker("es_ES")

        with transaction.atomic():
            n_usuarios = self.create_usuarios(fake, total=30)
            n_categorias = self.create_categorias()
            n_productos = self.create_productos_desde_posts_aprobados()
            n_imgs = self.create_imagenes_para_posts_con_producto()

        self.stdout.write(self.style.SUCCESS(
            f"✅ Listo: {n_usuarios} usuarios, {n_categorias} categorías, "
            f"{n_posts} posts, {n_productos} productos, {n_imgs} imágenes."
        ))

    # ---------- Utilidades ----------
    @staticmethod
    def precio_decimal(min_cents=1000, max_cents=50000) -> Decimal:
        """
        Genera un Decimal con 2 decimales seguro, evitando floats.
        Por defecto: 10.00 a 500.00
        """
        cents = random.randrange(min_cents, max_cents + 1)
        return (Decimal(cents) / Decimal("100")).quantize(Decimal("0.01"))

    # ---------- Creadores ----------
    def create_categorias(self) -> int:
        nombres = [
            "QUESOS", "BEBIDAS", "AMASIJOS", "CAFÉ", "TEJIDOS",
            "COLACIONES", "CESTERIA", "ARTESANIAS", "EMBUTIDOS Y ENCURTIDOS",
            "SALUD", "MUEBLES"
        ]
        count = 0
        for nombre in nombres:
            _, created = Categoria.objects.get_or_create(nombre=nombre)
            if created:
                count += 1
        # Si ya existían todas, count podría ser 0; igualmente retornamos el total disponible
        total = Categoria.objects.count()
        self.stdout.write(self.style.SUCCESS(f"📦 Categorías disponibles: {total} (nuevas: {count})"))
        return total

    def create_usuarios(self, fake: Faker, total=30) -> int:
        for _ in range(total):
            Usuario.objects.create(
                username=fake.user_name(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                second_name=fake.first_name() if random.choice([True, False]) else "",
                second_last_name=fake.last_name() if random.choice([True, False]) else "",
                address=fake.address() if random.choice([True, False]) else None,
                phone=fake.numerify("##########") if random.choice([True, False]) else None,
            )
        self.stdout.write(self.style.SUCCESS(f"👤 {total} usuarios creados"))
        return total

    def create_posts(self, fake: Faker, total=30) -> int:
        usuarios = list(Usuario.objects.all())
        categorias = list(Categoria.objects.all())
        if not usuarios or not categorias:
            raise ValueError("Se requieren usuarios y categorías para crear posts.")

        # Ajusta estos valores si tus estado_choices usan etiquetas diferentes
        estados_validos = ["Revisión", "Aprobado", "Rechazado"]

        for _ in range(total):
            Post.objects.create(
                nombre=fake.sentence(nb_words=3).rstrip("."),
                descripcion=fake.paragraph(nb_sentences=3),
                precio=self.precio_decimal(),
                stock=random.randint(1, 100),
                estado=random.choice(estados_validos),
                mensaje=(fake.sentence() if random.choice([True, False]) else None),
                id_usuario=random.choice(usuarios),     # instancia, no id
                id_categoria=random.choice(categorias), # instancia, no id
            )
        self.stdout.write(self.style.SUCCESS(f"📝 {total} posts creados"))
        return total

    def create_productos_desde_posts_aprobados(self) -> int:
        aprobados = Post.objects.select_related("id_categoria").filter(estado="Aprobado")

        creados_o_actualizados = 0
        for post in aprobados:
            _, _created = Producto.objects.update_or_create(
                defaults={
                    "id_categoria": post.id_categoria,
                    "nombre": post.nombre,
                    "descripcion": post.descripcion,
                    "precio": post.precio,
                    "stock": post.stock,
                },
            )
            creados_o_actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f"📦 Productos creados/actualizados desde posts aprobados: {creados_o_actualizados}"
        ))
        return creados_o_actualizados

    def create_imagenes_para_posts_con_producto(self) -> int:
        # Una imagen demo por cada Post que ya tenga Producto
        posts_con_producto = Post.objects.filter(producto__isnull=False)
        creadas = 0
        for post in posts_con_producto:
            ImagenProducto.objects.get_or_create(
                defaults={"url_imagen": "https://picsum.photos/400/300"},
            )
            creadas += 1
        self.stdout.write(self.style.SUCCESS(f"🖼️ Imágenes creadas/asignadas: {creadas}"))
        return creadas

    # ----- Extras (si quieres poblar más tablas, descomenta y llama en handle) -----
    def create_detalle_pedidos(self, fake, total=10):
        for _ in range(total):
            DetallePedido.objects.create(
                cantidad=random.randint(1, 10),
                precio=self.precio_decimal(),
            )
        self.stdout.write(self.style.SUCCESS(f"🧾 {total} detalles de pedido creados"))
        return total

    def create_envios(self, fake, total=10):
        for _ in range(total):
            Envio.objects.create(
                direccion=fake.address(),
                ciudad=fake.city(),
                codigo_postal=fake.postcode(),
                pais=fake.country(),
                telefono=fake.phone_number(),
                estado=random.choice(["preparación", "camino", "entregado"]),
            )
        self.stdout.write(self.style.SUCCESS(f"🚚 {total} envíos creados"))
        return total

    def create_pagos(self, fake, total=10):
        for _ in range(total):
            Pago.objects.create(
                metodo_pago=random.choice(["tarjeta", "transferencia", "efectivo"]),
                estado=random.choice(["pendiente", "aprobado", "rechazado"]),
            )
        self.stdout.write(self.style.SUCCESS(f"💳 {total} pagos creados"))
        return total

    def create_pedidos(self, fake, total=10):
        for _ in range(total):
            Pedido.objects.create(
                estado=random.choice(["pendiente", "enviado", "entregado", "cancelado"])
            )
        self.stdout.write(self.style.SUCCESS(f"📦 {total} pedidos creados"))
        return total
