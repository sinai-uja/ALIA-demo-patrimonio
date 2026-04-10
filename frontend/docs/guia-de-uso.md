# Guia de uso — ALIA Patrimonio de Andalucia

Guia de usuario para la aplicacion web **ALIA Patrimonio de Andalucia**, el asistente conversacional de patrimonio del Instituto Andaluz de Patrimonio Historico (IAPH).

---

## Indice

1. [Inicio de sesion](#1-inicio-de-sesion)
2. [Pagina principal](#2-pagina-principal)
3. [Busqueda semantica](#3-busqueda-semantica)
4. [Rutas virtuales](#4-rutas-virtuales)
5. [Detalle de ruta](#5-detalle-de-ruta)
6. [Panel de administracion](#6-panel-de-administracion)
7. [Navegacion general](#7-navegacion-general)

---

## 1. Inicio de sesion

![Pantalla de login](images/01-login.png)

Al acceder a la aplicacion se muestra la pantalla de **Iniciar sesion**. Todas las secciones de la aplicacion requieren autenticacion.

**Como iniciar sesion:**

1. Introduce tu **usuario** en el campo "Tu usuario".
2. Introduce tu **contrasena** en el campo "Tu contrasena".
3. Pulsa el boton **Entrar**.

Si las credenciales son incorrectas, aparecera un mensaje de error en rojo debajo del formulario. Contacta con el administrador si no dispones de credenciales.

> **Nota**: La sesion se mantiene activa mediante tokens JWT. Si la sesion caduca, seras redirigido automaticamente a esta pantalla.

---

## 2. Pagina principal

![Pagina principal](images/02-home.png)

Tras iniciar sesion accedes a la pagina principal, que presenta:

- **Cabecera hero** con una imagen panoramica de Andalucia y el titulo "Patrimonio Historico Andaluz".
- **Subtitulo**: "Explora, pregunta y descubre el rico patrimonio cultural de Andalucia con ayuda de inteligencia artificial".
- **Dos tarjetas de acceso rapido**:
  - **Busqueda Semantica** — Accede directamente al buscador de bienes patrimoniales. Enlace: "Buscar patrimonio".
  - **Rutas Virtuales** — Genera rutas culturales personalizadas. Enlace: "Crear mi ruta".

### Barra de navegacion

La barra superior esta presente en todas las paginas e incluye:

- **Logo ALIA + "Patrimonio de Andalucia"** — click para volver al inicio.
- **Busqueda** — acceso a la busqueda semantica.
- **Rutas** — acceso al generador de rutas virtuales.
- **Admin** — solo visible para usuarios administradores.
- **Nombre de usuario** y **tipo de perfil** a la derecha.
- **Cerrar sesion** — cierra la sesion actual.

---

## 3. Busqueda semantica

### Vista inicial

![Busqueda vacia](images/03-search-empty.png)

La pagina de busqueda muestra:

- **Titulo**: "Busqueda por Similaridad".
- **Barra de busqueda** central con el placeholder "Buscar en el patrimonio historico andaluz...".
- **Panel de filtros** colapsable a la izquierda (icono de embudo).

### Como buscar

1. **Escribe tu consulta** en lenguaje natural. Por ejemplo: "Alhambra de Granada", "iglesias goticas de Sevilla" o "pinturas rupestres en Jaen".
2. **Deteccion de entidades**: el sistema analiza automaticamente tu consulta y detecta nombres de provincias, municipios o tipos de patrimonio.

![Deteccion de entidades](images/04-search-results.png)

   - Si se detectan entidades, aparece un panel de clarificacion preguntando si quieres aplicarlas como filtros (por ejemplo: "He detectado **granada** en tu consulta. Te refieres a... Provincia: Granada / Municipio: Granada / Ambos / Ninguno").
   - Puedes elegir la opcion que corresponda o pulsar **"Buscar directamente"** para buscar sin filtros.

3. **Resultados**: se muestran como tarjetas con:
   - Etiqueta de color segun el tipo de patrimonio (verde = inmueble, morado = mueble, turquesa = inmaterial, azul = paisaje cultural).
   - Titulo del bien patrimonial (enlace a la ficha del IAPH).
   - Ubicacion (provincia y municipio).
   - Fragmento descriptivo.
   - Puntuacion de relevancia.
4. **Paginacion**: 10 resultados por pagina, con controles de navegacion en la parte inferior.

### Filtros

Despliega el panel de filtros (icono de embudo en la esquina superior izquierda) para refinar por:

- **Tipo de patrimonio**: Patrimonio Inmueble, Mueble, Inmaterial o Paisaje Cultural.
- **Provincia**: cualquiera de las 8 provincias andaluzas.
- **Municipio**: se carga dinamicamente segun la provincia seleccionada.

Los filtros activos se muestran como **chips** encima de los resultados y se pueden eliminar individualmente o limpiar todos a la vez.

### Detalle de un bien patrimonial

Al hacer click en una tarjeta de resultado, se abre un **panel lateral derecho** (o pantalla completa en movil) con informacion detallada:

- Galeria de imagenes con autor y fecha.
- Mapa interactivo con la ubicacion del bien (Leaflet).
- Metadatos desplegables: codigo, caracterizacion, proteccion, estilos, periodos, etc.
- Bibliografia y bienes relacionados.

---

## 4. Rutas virtuales

![Pagina de rutas](images/05-routes.png)

La pagina de rutas permite generar itinerarios culturales personalizados y consultar rutas generadas anteriormente.

### Generar una nueva ruta

1. **Escribe una descripcion** de la ruta que deseas. Por ejemplo: "Ruta de arte rupestre por Jaen" o "Monumentos renacentistas de Ubeda y Baeza".
2. **Selecciona el numero de paradas** (de 2 a 15, por defecto 5) usando los botones a la derecha del campo de texto.
3. **Aplica filtros opcionales** (mismos que en busqueda: tipo de patrimonio, provincia, municipio).
4. Pulsa el **boton de enviar** (flecha verde).
5. El sistema genera la ruta usando IA. Aparecera un spinner de carga durante el proceso.
6. Una vez generada, se muestra un resumen de la ruta y puedes acceder al detalle.

### Rutas anteriores

Debajo del generador se muestra el listado de **Rutas anteriores** con:

- **Buscador** para filtrar rutas por titulo.
- **Tarjetas de ruta** que muestran: imagen de portada, titulo, provincia, numero de paradas, duracion estimada y descripcion resumida.
- **Botones de feedback** (pulgar arriba/abajo) para valorar cada ruta.
- **Boton eliminar** para borrar rutas que ya no interesan.
- **Paginacion**: 6 rutas por pagina.

---

## 5. Detalle de ruta

![Detalle de ruta](images/06-route-detail.png)

Al acceder a una ruta se muestra su pagina de detalle con:

### Cabecera

- **Enlace "Todas las rutas"** para volver al listado.
- **Titulo de la ruta** (por ejemplo: "Ruta de la Pintura Rupestre en Jaen: Un Viaje al Pasado").
- **Metadatos**: provincia, numero de paradas, duracion estimada.
- **Descripcion general**: texto narrativo generado por IA que introduce la ruta.

### Paradas

La ruta presenta sus paradas en un **formato intercalado** (narrativa + tarjeta):

- Cada parada incluye:
  - **Imagen** del bien patrimonial.
  - **Nombre** del bien.
  - **Etiquetas**: tipo de patrimonio, provincia, municipio, duracion sugerida.
  - **Descripcion narrativa** contextualizada.
- Entre paradas se intercala **texto narrativo de transicion** que conecta los diferentes puntos del recorrido.

### Guia interactivo

En la esquina inferior derecha hay un **boton flotante** (icono de chat verde) que abre el **guia interactivo**:

- Es un chatbot contextualizado a la ruta actual.
- Puedes hacer preguntas sobre los bienes patrimoniales de la ruta, pedir mas informacion o hacer consultas especificas.
- Las respuestas se generan con IA teniendo en cuenta toda la informacion de la ruta.

### Panel de detalle de parada

Al hacer click en una parada, se abre el **panel de detalle lateral** (igual que en busqueda) con toda la informacion del bien patrimonial: galeria de imagenes, mapa, metadatos y bibliografia.

---

## 6. Panel de administracion

![Panel de administracion](images/08-admin.png)

El panel de administracion es accesible **solo para usuarios con rol de administrador** a traves del enlace "Admin" en la barra de navegacion.

Se organiza en dos secciones:

### Usuarios

- **Tabla de usuarios** con columnas: Usuario, Perfil, Acciones.
- **Nuevo usuario**: boton verde que abre un formulario para crear usuarios (nombre de usuario, contrasena, tipo de perfil).
- **Editar usuario** (icono de lapiz): permite cambiar la contrasena y el tipo de perfil.
- **Eliminar usuario** (icono de papelera): pide confirmacion antes de eliminar.

### Tipos de perfil

- **Tabla de perfiles** con columnas: Nombre, Usuarios (cuantos usuarios tienen ese perfil), Acciones.
- **Anadir**: boton verde para crear un nuevo tipo de perfil.
- **Editar** (icono de lapiz): renombrar un tipo de perfil existente.
- **Eliminar** (icono de papelera): solo si no hay usuarios asignados.

Los tipos de perfil definen categorias de usuario (por ejemplo: Admin, Ciudadano, Investigador) y pueden utilizarse para personalizar la experiencia.

---

## 7. Navegacion general

### Atajos de teclado

- **Enter** en cualquier campo de busqueda: ejecuta la busqueda o genera la ruta.

### Comportamiento responsive

La aplicacion es completamente responsive:

- En **escritorio**: los paneles de filtros y detalle se muestran como barras laterales.
- En **movil**: los filtros se muestran como un drawer colapsable y los paneles de detalle ocupan toda la pantalla.
- La barra de navegacion se convierte en un **menu hamburguesa** en pantallas pequenas.

### Feedback

En las tarjetas de rutas y en el detalle de ruta puedes dar feedback con los **botones de pulgar arriba/abajo**. Este feedback se envia al sistema para mejorar la calidad de las recomendaciones.

### Sesion y autenticacion

- La sesion se refresca automaticamente mientras usas la aplicacion.
- Si la sesion caduca, seras redirigido al login.
- Pulsa **"Cerrar sesion"** en la barra de navegacion para salir manualmente.

---

## Glosario

| Termino | Significado |
|---------|-------------|
| **Patrimonio Inmueble** | Edificios, yacimientos arqueologicos, monumentos |
| **Patrimonio Mueble** | Objetos, obras de arte, documentos |
| **Patrimonio Inmaterial** | Festividades, oficios, saberes tradicionales |
| **Paisaje Cultural** | Paisajes con valor historico-cultural |
| **Busqueda semantica** | Busqueda basada en el significado del texto, no solo en palabras clave |
| **Deteccion de entidades** | Reconocimiento automatico de nombres de lugares o tipos en tu consulta |
| **Guia interactivo** | Chatbot contextualizado disponible dentro de cada ruta |

---

*Documentacion generada a partir de la version actual de la aplicacion (abril 2026).*
