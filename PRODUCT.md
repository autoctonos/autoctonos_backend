# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Productores rurales colombianos** (queseros, caficultores, artesanos, etc.) que cargan y mantienen sus propios productos en el panel del backend. Poca comodidad con formularios web: necesitan guía paso a paso, lenguaje simple y ejemplos concretos en cada campo. Usan celular y computador más o menos por igual; las fotos suelen tomarse con el celular.
- **Equipo de Autóctonos (staff)**: revisa lo que suben los productores y decide qué se publica, cambiando el estado de `revisión` a `aprobado` en el admin de Django.

## Product Purpose

Autóctonos es un marketplace de productos autóctonos colombianos (productosautoctonos.shop). El panel de productor existe para que cada productor suba y mantenga sus productos con datos completos y fotos que cumplan el estándar, sin depender del equipo. Éxito: productos cargados completos (peso de despacho, presentación, fotos buenas) que staff solo tenga que aprobar.

## Operating Context

- Formulario abierto en `/panel/` (sin cuenta): quien lo llena se elige de la lista de productores o deja sus datos si es nuevo. Solo crea productos; ve los del productor elegido solo para consulta.
- Todo producto que entra por el formulario queda en `revisión`; solo staff lo publica y solo staff edita (`/dashboard/` y admin).
- Las fotos pasan por el estándar de `products/imagenes.py` (se normalizan a cuadrado 1600 px sobre blanco; se rechazan las pequeñas, muy alargadas, con damero falso). El productor necesita entender por qué una foto se rechaza.
- El envío se cotiza con el peso de despacho y el municipio de origen del productor: sin peso el producto no se puede vender.

## Capabilities and Constraints

- Plantillas Django server-rendered con CSS/JS vanilla inline; sin build step en el backend.
- Varias fotos por producto, con orden; la primera es la principal en la tienda.
- Precios en pesos colombianos sin decimales visibles; separador de miles con punto.

## Brand Commitments

Misma marca que la tienda (`astro_frontend`): logo/emblema de `static/brand/`, paleta crema `#F2E8CF`, verdes `#386641` / `#6A994E` / `#A7C957`, rojo `#BC4749`, negro `#111111`. Tipografía: la sans del sistema (la tienda declara Inter pero no la carga, así que en la práctica renderiza en la del sistema; el panel usa la misma). Voz: español colombiano, cercano y claro, tuteo.

## Evidence on Hand

No hay testimonios, métricas ni fotos de productores en el repo para usar como contenido de marketing; no inventarlos.

## Product Principles

1. Guiar, no exigir: cada campo explica qué es y da un ejemplo real del campo colombiano.
2. Nada técnico sin traducir (peso de despacho, cadena de frío, presentación).
3. El productor siempre sabe en qué estado está cada producto y qué le falta.
4. El formulario abierto no edita: sin login no hay forma segura de saber quién cambia qué.

## Accessibility & Inclusion

Usuarios con baja alfabetización digital: objetivos táctiles grandes, texto legible (≥16 px en campos), errores junto al campo en lenguaje simple, funciona en conexiones lentas.
