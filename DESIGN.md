---
name: Autóctonos · Panel del productor
description: Panel server-rendered donde cada productor carga sus productos viendo cómo los verá el comprador.
colors:
  crema: "#F2E8CF"
  crema-hondo: "#E9DCBA"
  verde: "#386641"
  verde-hover: "#2E5536"
  verde-medio: "#6A994E"
  verde-claro: "#A7C957"
  verde-texto: "#4F7A38"
  crema-tinta: "#6B5A30"
  rojo: "#BC4749"
  rojo-texto: "#9A3335"
  tinta: "#111111"
  tinta-2: "#4A4A44"
  tinta-3: "#66665D"
  linea: "rgba(56, 102, 65, 0.14)"
  linea-fuerte: "rgba(17, 17, 17, 0.2)"
  superficie: "rgba(255, 255, 255, 0.82)"
  campo: "#FFFFFF"
  revision-fondo: "#FFF1CF"
  revision-texto: "#7A4F00"
  aprobado-fondo: "rgba(167, 201, 87, 0.32)"
  aprobado-texto: "#24452B"
  rechazado-fondo: "rgba(188, 71, 73, 0.13)"
  exito-fondo: "#EEF5E2"
  error-fondo: "#FBECEC"
  info-fondo: "#FFF1CF"
  info-texto: "#7A4F00"
typography:
  display:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.6rem, 1.2rem + 1.6vw, 2.25rem)"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  title:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  body:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 650
    lineHeight: 1.55
  micro:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 650
    lineHeight: 1.3
  help:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
rounded:
  campo: "12px"
  boton: "14px"
  zona: "16px"
  tarjeta: "18px"
  seccion: "20px"
  pastilla: "999px"
spacing:
  campo-gap: "6px"
  rejilla: "18px"
  ficha: "20px"
  seccion: "24px"
  mesa-movil: "28px"
  mesa: "36px"
  inventario: "56px"
components:
  button-primary:
    backgroundColor: "{colors.verde}"
    textColor: "{colors.campo}"
    rounded: "{rounded.boton}"
    padding: "0 22px"
    height: "52px"
  button-primary-hover:
    backgroundColor: "{colors.verde-hover}"
  button-soft:
    backgroundColor: "{colors.campo}"
    textColor: "{colors.verde}"
    rounded: "{rounded.boton}"
    padding: "0 22px"
    height: "44px"
  input:
    backgroundColor: "{colors.campo}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.campo}"
    padding: "11px 14px"
    height: "48px"
  input-affix:
    backgroundColor: "{colors.crema}"
    textColor: "{colors.tinta-2}"
    width: "48px"
  section:
    backgroundColor: "{colors.superficie}"
    rounded: "{rounded.seccion}"
    padding: "24px"
  product-card:
    backgroundColor: "{colors.superficie}"
    rounded: "{rounded.tarjeta}"
    padding: "10px 12px 12px"
  chip-revision:
    backgroundColor: "{colors.revision-fondo}"
    textColor: "{colors.revision-texto}"
    rounded: "{rounded.pastilla}"
    padding: "4px 11px"
  chip-aprobado:
    backgroundColor: "{colors.aprobado-fondo}"
    textColor: "{colors.aprobado-texto}"
    rounded: "{rounded.pastilla}"
    padding: "4px 11px"
  chip-rechazado:
    backgroundColor: "{colors.rechazado-fondo}"
    textColor: "{colors.rojo-texto}"
    rounded: "{rounded.pastilla}"
    padding: "4px 11px"
---

# Design System: Autóctonos · Panel del productor

## Overview

**Creative North Star: "La mesa del mercado"**

El panel es la trastienda de la tienda Autóctonos y habla su mismo idioma visual: fondo crema, tarjetas blancas translúcidas con borde verde muy tenue, verde oscuro para actuar. El productor trabaja sobre una mesa (formulario a la izquierda) mientras ve, a la derecha, la tarjeta real de la tienda tomando forma. Todo lo que no es esa tarjeta es funcional: campos grandes, ayudas en lenguaje simple, estados con color y punto.

La densidad es baja a propósito. Campos de 48 px, botones de 52 px, texto de campo nunca por debajo de 16 px y una ayuda bajo cada campo, porque quien lo usa tiene poca soltura con formularios y la mitad entra desde el celular. Solo tema claro (`color-scheme: light`).

El sistema extiende los tokens de marca de `astro_frontend/src/styles/global.css` con tokens funcionales propios del panel (tintas secundarias, líneas, superficie, chips de estado, anillo de foco). La tipografía es la sans del sistema, igual que lo que la tienda renderiza en la práctica.

**Key Characteristics:**
- Crema como lienzo, blanco translúcido como superficie, verde oscuro como única voz de acción.
- Bloques numerados (1–4) que se rellenan de verde al completarse.
- Vista previa en vivo con la tarjeta de la tienda; en celular baja a franja compacta y la acción a una barra fija inferior.
- Cifras tabulares en todo precio, peso y contador.
- Sombras suaves teñidas de verde, nunca duras.

## Colors

Paleta de la tienda, cálida y agrícola, con verdes en tres pesos y un rojo reservado.

### Primary
- **Verde Monte** (`verde`): botones principales, enlaces, avatar, círculo de paso completo, insignia de portada y de descuento, precios. Al pasar el cursor baja a **Verde Monte Hondo** (`verde-hover`).

### Secondary
- **Verde Hoja** (`verde-medio`): borde de campo enfocado, barra de progreso, ícono de requisito cumplido, contorno de destino al reordenar fotos, anillo del producto que se está editando.

### Tertiary
- **Verde Brote** (`verde-claro`): solo en transparencias: fondo del chip «Publicado», hover de la zona de fotos y del botón suave, selección de texto.
- **Rojo Achiote** (`rojo`): borde de campo con error y hover de «quitar foto». Su versión legible **Rojo Achiote Hondo** (`rojo-texto`) lleva el texto de error, el aviso de error y el chip «No aprobado».

### Neutral
- **Crema Panela** (`crema`): fondo de página, barra superior (al 90 % con desenfoque), afijos de campo ($, kg, %), fondo de la foto vacía en la vista previa.
- **Crema Tostada** (`crema-hondo`): fondo del recuadro de foto en las tarjetas del inventario.
- **Tinta** (`tinta`): texto principal. **Tinta 2** (`tinta-2`): ayudas, subtítulos, metadatos. **Tinta 3** (`tinta-3`): «(opcional)», contadores, ítems ya hechos.
- **Línea** (`linea`): borde de secciones, tarjetas, avisos y separadores internos. **Línea fuerte** (`linea-fuerte`): borde de campos y afijos.
- **Superficie** (`superficie`): fondo de secciones, tarjetas de inventario y lista de pendientes. **Campo** (`campo`): fondo de inputs, de la tarjeta de vista previa y del botón suave.

### Estados
- **Revisión** (`revision-fondo` / `revision-texto`), **Aprobado** (`aprobado-fondo` / `aprobado-texto`), **Rechazado** (`rechazado-fondo` / `rojo-texto`): los tres chips de estado del producto. El mismo ámbar de `revision-texto` marca «Falta: …» en el inventario.
- **Avisos**: éxito (`exito-fondo`, texto `aprobado-texto`), error (`error-fondo`, texto `rojo-texto`), info (`info-fondo` / `info-texto`).

### Named Rules
**The Una Sola Voz Rule.** El verde oscuro es la única voz de acción: todo lo que se pulsa para avanzar es `verde` sólido o `verde` sobre blanco. Ningún otro color rellena un botón.

**The Rojo Reservado Rule.** El rojo solo aparece para error, rechazo o quitar. Nunca decora ni marca precios o descuentos (el descuento va en verde).

## Typography

**Display Font:** sans del sistema (`ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`)
**Body Font:** la misma
**Label/Mono Font:** la misma, con `font-variant-numeric: tabular-nums` para cifras

**Character:** Una sola familia, jerarquía por peso (400 / 600 / 650 / 700) y tamaño. Directa y legible en cualquier celular, sin descargas.

### Hierarchy
- **Display** (700, `clamp(1.6rem, 1.2rem + 1.6vw, 2.25rem)`, 1.2, −0.02em): el saludo o «Editar «…»» que abre la página; uno por vista. Su párrafo de apoyo va a 17 px en `tinta-2`, máximo 46rem.
- **Headline** (700, 1.5rem, −0.01em): «Mis productos» / título del inventario.
- **Title** (700, 1.25rem, −0.01em): título de cada sección numerada. El título de la columna de vista previa baja a 1.05rem.
- **Body** (400, 16 px, 1.55): texto corrido y valor de los campos (16 px fijo, evita el zoom de iOS).
- **Label** (650, 15 px): etiqueta de campo, encabezado de pendientes, interruptor.
- **Help** (400, 14 px, `tinta-2`): ayuda bajo cada campo, consejos, estado de fotos. Los metadatos de tarjeta bajan a 13 px.

### Named Rules
**The Cifra Tabular Rule.** Todo precio, peso, porcentaje y contador lleva `tabular-nums`; los números en vivo (`dato-vivo`) van en `verde` 600.

**The Nada Bajo 16 Rule.** Ningún texto que el productor escriba o deba leer para completar un campo baja de 16 px; 14 px es solo para ayudas secundarias.

## Layout

Contenedor centrado de 1240 px con 20 px de margen lateral; `main` con 28 px arriba y 64 px abajo. Barra superior pegajosa (sticky) con emblema a la izquierda y el productor (avatar + nombre + municipio) a la derecha; staff ve ahí el selector de productor y accesos.

La «mesa» es una grilla de dos columnas desde 1024 px: formulario fluido + columna de vista previa de 360 px (392 px desde 1200 px), separadas por 36 px; la columna derecha es sticky a 84 px del borde. Dentro del formulario, secciones apiladas a 20 px y campos en rejilla de dos columnas desde 640 px con 18 px de separación; descripción y campos anchos ocupan ambas.

Por debajo de 1024 px la mesa se invierte (`column-reverse`): la tarjeta queda arriba como franja horizontal (foto de 112 px + texto), se ocultan pendientes y botón lateral, y aparece una barra de acción fija abajo (fondo blanco 96 %, respetando `safe-area-inset-bottom`) con el estado y el botón. Por debajo de 640 px las secciones bajan a 20 × 16 px de padding.

El inventario va 56 px debajo, en grilla `auto-fill` de mínimo 150 px (232 px desde 640 px).

## Elevation & Depth

Híbrido: capas tonales (crema → blanco translúcido → blanco) más sombras suaves de doble capa teñidas de verde. Las sombras son ambientales y largas, nunca duras ni desplazadas.

### Shadow Vocabulary
- **Reposo** (`box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 10px 32px -14px rgba(56,102,65,.22)`): secciones del formulario y la franja de vista previa en celular.
- **Alta** (`box-shadow: 0 2px 4px rgba(0,0,0,.05), 0 22px 48px -20px rgba(56,102,65,.35)`): la tarjeta de vista previa en escritorio y el hover de tarjetas del inventario.
- **Botón** (`box-shadow: 0 6px 16px -8px rgba(56,102,65,.8)`): solo el botón principal.
- **Barra inferior** (`box-shadow: 0 -8px 24px -12px rgba(0,0,0,.2)`): la barra de acción fija en celular.

### Named Rules
**The Una Tarjeta Elevada Rule.** La sombra alta es de la vista previa: es el objeto que el productor está construyendo. Lo demás descansa en sombra de reposo o sin sombra, y solo se eleva al hover.

## Shapes

Esquinas generosas y redondas, heredadas de las tarjetas de la tienda, que crecen con el tamaño del contenedor: campos 12 px, botones, avisos y miniaturas 14 px, zona de fotos 16 px, tarjetas y pendientes 18 px, secciones 20 px. Chips, insignias, interruptor y progreso son pastillas (999 px); avatar, pasos y botones de miniatura son círculos. Bordes de 1 px (`linea`) en contenedores y de 1.5 px (`linea-fuerte`) en campos; las zonas de soltar usan borde discontinuo de 2 px.

## Components

### Buttons
Sólidos y grandes, pensados para el pulgar.
- **Shape:** curva suave (14 px).
- **Primary:** fondo `verde`, texto blanco 17 px / 700, alto mínimo 52 px, padding horizontal 22 px, sombra de botón.
- **Hover / Focus / Active:** hover a `verde-hover`; foco con el anillo global (`0 0 0 3px rgba(106,153,78,.45)`); al pulsar `scale(.98)`; en envío `aria-busy` baja a 75 % de opacidad.
- **Suave:** fondo blanco, texto `verde`, borde 1.5 px `rgba(56,102,65,.3)`, alto 44 px, 15 px, sin sombra; hover con `verde-claro` al 15 %. Para acciones secundarias (paginación, exportar, admin).

### Chips
- **Style:** pastilla, 13 px / 650, padding 4 × 11 px, con un punto de 7 px del color del texto delante.
- **State:** «En revisión» ámbar, «Publicado» verde brote, «No aprobado» rojo. El texto siempre nombra el estado; el color lo refuerza.

### Cards / Containers
- **Sección del formulario:** `superficie`, borde `linea`, 20 px de radio, 24 px de padding, sombra de reposo. Título con círculo de paso de 30 px (crema con número verde; verde sólido con número blanco cuando la sección está completa).
- **Tarjeta del inventario:** `superficie`, borde `linea`, 18 px, foto 4:3 sobre `crema-hondo`, cuerpo 10 × 12 px; hover sube 2 px con sombra alta; la que se está editando lleva un anillo de 2.5 px `verde-medio`. Toda la tarjeta es el enlace.
- **Pendientes:** `superficie`, 18 px, barra de progreso de 8 px y lista con ícono de círculo (gris) o check (`verde-medio`).

### Inputs / Fields
- **Style:** blanco, borde 1.5 px `linea-fuerte`, 12 px de radio, alto mínimo 48 px, padding 11 × 14 px, texto 16 px. Selects con chevrón verde propio. Afijos ($, kg, %, Gr) en crema pegados al campo.
- **Hover / Focus:** hover a borde verde al 50 %; foco con borde `verde-medio` + anillo de 3 px.
- **Error:** borde `rojo`, fondo `#FFFAFA` y mensaje en `rojo-texto` 600 con ícono de alerta, dentro de la misma ayuda bajo el campo.
- **Etiqueta:** encima del campo; los opcionales llevan «(opcional)» en `tinta-3`. Ayuda siempre debajo.
- **Interruptor:** pastilla de 52 × 30 px, gris al 22 % apagado, `verde` encendido, perilla blanca.

### Navigation
Barra superior pegajosa en crema al 90 % con desenfoque y borde inferior `linea`: emblema de 36 px + «Autóctonos» 700, y a la derecha avatar circular verde con la inicial. «Volver» es un enlace verde 600 con chevrón. Divulgaciones (`details`) usan un resumen verde 650 de 40 px de alto con chevrón que gira 90°.

### Vista previa en vivo (componente firma)
Réplica de la tarjeta de producto de la tienda: blanca, 18 px, padding 12 px, foto 4:3 con radio 12 px, categoría, nombre (2 líneas), presentación, precio en `verde` 18 px con el anterior tachado, y un botón «Añadir al carrito» inerte. Se actualiza con cada tecla y cada foto, y hace un pulso (sube 3 px y escala 1.012 en 450 ms) al cambiar. Mientras está vacía muestra textos guía en gris claro.

### Zona de fotos
Recuadro con borde discontinuo verde al 35 % sobre crema al 45 %, 16 px, ícono de cámara en círculo verde de 52 px. Al arrastrar encima se tiñe de `verde-claro` y escala 1.01. Las miniaturas son cuadradas (14 px), en 2 columnas (4 desde 560 px), con insignia «Portada» en la primera y botones circulares blancos de 36 px para mover y quitar.

## Do's and Don'ts

### Do:
- **Do** usar `crema` como fondo de página y `superficie` translúcida con borde `linea` para todo contenedor.
- **Do** darle a cada campo etiqueta arriba, ayuda con ejemplo real debajo y error en la misma línea de ayuda, en `rojo-texto`.
- **Do** mantener campos de 48 px y botones de 52 px de alto mínimo, con 16 px de texto en campos.
- **Do** mostrar el estado de un producto siempre con chip de texto + punto, nunca solo con color.
- **Do** usar el anillo de foco global (`0 0 0 3px rgba(106,153,78,.45)`) en todo lo interactivo, sin `outline` del navegador.
- **Do** usar íconos SVG de trazo (24 × 24, trazo 2, `currentColor`) en línea.
- **Do** respetar `prefers-reduced-motion`: sin transiciones ni animaciones.

### Don't:
- **Don't** usar rojo para precios, descuentos ni decoración: solo error, rechazo y quitar.
- **Don't** rellenar botones con un color distinto de `verde` (o blanco en el botón suave).
- **Don't** usar sombras duras desplazadas ni negras opacas; las sombras del panel son difusas y teñidas de verde.
- **Don't** agregar tema oscuro: el panel es solo claro, igual que la tienda.
- **Don't** cargar una fuente web: la marca renderiza en la sans del sistema.
