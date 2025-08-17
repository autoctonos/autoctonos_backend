import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from faker import Faker
from commerce.models import DetallePedido, Envio, Pago, Pedido
from products.models import Categoria, ImagenProducto, Producto
from users.models import Usuario


class Command(BaseCommand):
    help = "Genera datos de prueba"

    def handle(self, *args, **kwargs):
        fake = Faker()
        self.create_usuarios(fake)
        self.create_categorias()
        self.create_productos(fake)
        self.create_imagenes_producto(fake)
        self.stdout.write(self.style.SUCCESS('✅ Datos de prueba creados con éxito'))

    
    def create_categorias(self):
        categorias = [
            "QUESOS",
            "BEBIDAS",
            "AMASIJOS",
            "CAFÉ",
            "TEJIDOS",
            "COLACIONES",
            "CESTERIA",
            "ARTESANIAS",
            "EMBUTIDOS Y ENCURTIDOS",
            "SALUD",
            "MUEBLES"
        ]
        for nombre in categorias:
            Categoria.objects.get_or_create(nombre=nombre)
        self.stdout.write(self.style.SUCCESS("11 categorías creadas"))

    def create_productos(self, fake):
        categorias = list(Categoria.objects.all())
        for _ in range(10):
            Producto.objects.create(
                nombre=fake.sentence(nb_words=3),
                descripcion=fake.paragraph(),
                precio=round(random.uniform(10, 500), 2),
                stock=random.randint(1, 100),
                id_categoria=random.choice(categorias)
            )
        self.stdout.write(self.style.SUCCESS('✅ 10 productos creados'))
    
    def create_imagenes_producto(self, fake):
        productos = list(Producto.objects.all())
        for producto in productos[:10]:
            ImagenProducto.objects.create(
                id_producto=producto,
                url_imagen="https://picsum.photos/400/300"
            )
        self.stdout.write(self.style.SUCCESS('✅ 10 imágenes de producto creadas'))

    def create_usuarios(self, fake):
        for _ in range(30):
            Usuario.objects.create(
                username=fake.user_name(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                second_name=fake.first_name() if random.choice([True, False]) else "",
                second_last_name=fake.last_name() if random.choice([True, False]) else "",
                address=fake.address() if random.choice([True, False]) else None,
                phone=fake.numerify("##########") if random.choice([True, False]) else None
            )
        self.stdout.write(self.style.SUCCESS('✅ 10 usuarios creados'))

    def create_detalle_pedidos(self, fake):
        for _ in range(10):
            DetallePedido.objects.create(
                cantidad=random.randint(1, 10),
                precio=round(random.uniform(10, 500), 2)
            )
        self.stdout.write(self.style.SUCCESS('✅ 10 detalles de pedido creados'))

    def create_envios(self, fake):
        for _ in range(10):
            Envio.objects.create(
                direccion=fake.address(),
                ciudad=fake.city(),
                codigo_postal=fake.postcode(),
                pais=fake.country(),
                telefono=fake.phone_number(),
                estado=random.choice(['preparación', 'camino', 'entregado'])
            )
        self.stdout.write(self.style.SUCCESS('✅ 10 envíos creados'))

    def create_pagos(self, fake):
        for _ in range(10):
            Pago.objects.create(
                metodo_pago=random.choice(['tarjeta', 'transferencia', 'efectivo']),
                estado=random.choice(['pendiente', 'aprobado', 'rechazado'])
            )
        self.stdout.write(self.style.SUCCESS('✅ 10 pagos creados'))

    def create_pedidos(self, fake):
        for _ in range(10):
            Pedido.objects.create(
                estado=random.choice(['pendiente', 'enviado', 'entregado', 'cancelado'])
            )
        self.stdout.write(self.style.SUCCESS('✅ 10 pedidos creados'))
