# Usar Libera Suite

Libera Suite abre un documento en una ventana y te permite editarlo y guardarlo. Words, Tables y Slides funcionan todos así; Diagrams abre documentos de Visio para leerlos.

Empieza por [Instalar](../main/install.md). Estas tres páginas están pensadas para leerse en orden:

1. [Instalar](../main/install.md): llevarla a tu máquina, con un comando.
2. [Trabajar con documentos](documents.md): abrir, guardar, exportar, imprimir.
3. [Qué funciona hoy](../main/status.md): qué está hecho y los problemas que ya conocemos.

Cada aplicación tiene su propio color. Por lo demás, la ventana es la misma:

![Libera Tables con una hoja de cálculo vacía; la barra de herramientas es del verde azulado de Libera Tables.](../assets/tables.png)

![Libera Slides con una diapositiva de título; la barra de herramientas es del dorado de Libera Slides.](../assets/slides.png)

## Cómo está hecha

Libera Suite consta de dos partes, empaquetadas por separado.

**La aplicación** es un pequeño paquete de Python de unos cientos de kilobytes: la ventana, la línea de comandos y la aplicación anfitriona con la que hablan los componentes.

**Los componentes** son todo lo demás: el motor de documentos, los componentes de edición, las fuentes. La línea de comandos los llama el *payload*. Ocupan unos 90 MB comprimidos, en dos paquetes de Python propios, `libera-core` y `libera-web`.

Las dos partes tienen números de versión distintos. La aplicación comprueba que los componentes que encuentra son los que espera. Una corrección de la aplicación no obliga, por tanto, a volver a descargar los componentes.

Todas las formas de instalar traen las dos. El instalador de Windows y el Flatpak de Linux las contienen, y pip instala los componentes con la aplicación, que los requiere.

## Qué no es

Libera Suite no habla con ningún servidor, no necesita cuenta y nunca sube tus documentos. Los componentes funcionan como contenido web local, servido en `127.0.0.1` a una ventana de tu propia máquina. No hay colaboración, almacenamiento en la nube ni telemetría, porque nada de eso está hecho.
