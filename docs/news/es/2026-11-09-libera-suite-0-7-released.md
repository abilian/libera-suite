---
date: 2026-11-09
description: Con Libera Suite 0.7 puedes comentar, rellenar y reordenar los PDF, mantener los documentos bajo su contraseña, y leer y crear firmas digitales. Sus componentes se instalan ahora con ella.
---

# Libera Suite 0.7: PDF, contraseñas y firmas

Libera Suite 0.7 ya está disponible. Ahora puedes comentar, rellenar y reordenar los PDF, abrir y guardar documentos protegidos con contraseña, y leer y crear firmas digitales.

Libera Suite es una suite ofimática libre y de código abierto para Windows, macOS y Linux: Libera Words para textos, Libera Tables para hojas de cálculo, Libera Slides para presentaciones, Libera PDF para los PDF y Libera Diagrams, un visor de dibujos de Visio. Abre y guarda los formatos de Microsoft Office y de LibreOffice, en tu propio ordenador, sin cuenta ni servicio en la nube.

[Instalar Libera Suite](../main/install.md){ .md-button .md-button--primary }

¿Ya la usas? Cierra Libera Suite si está abierta y vuelve a ejecutar el instalador o la orden de instalación, o `brew upgrade libera` si usas Homebrew. Con pip, pipx o Homebrew, los componentes se instalan ahora con la aplicación, unos 100 MB, así que en el primer inicio no se descarga nada. La ventana de inicio ofrece una vez borrar lo que descargaron las versiones anteriores, y `libera --payload-remove` lo hace en cualquier momento.

## PDF

![Libera PDF con un PDF abierto, la pestaña Comentario mostrando sus herramientas y un comentario en la página listado en el panel Comentarios.](../assets/pdf.png)

Un PDF se abre en Libera PDF. Puedes añadir comentarios, resaltados, dibujos y cuadros de texto, hacer pequeñas correcciones de texto, y añadir, eliminar, girar y mover páginas. También puedes rellenar formularios: un Cerfa francés y los formularios del IRS estadounidense están entre los que hemos probado.

Al guardar, tus cambios se añaden después del original, que queda en el archivo tal como estaba. Por eso una página que eliminas o un texto que corriges todavía se pueden recuperar del archivo guardado: no cuentes con ninguno de los dos para quitar algo confidencial de un PDF que envías.

El texto editado no se recompone. Un PDF certificado contra cualquier cambio no se puede guardar: el guardado falla y el archivo queda como estaba. Todavía no puedes crear un formulario ni convertir un PDF en un documento. Libera Suite se ofrece en *Abrir con* para un PDF, nunca como opción predeterminada. [Trabajar con documentos](../guide/documents.md#pdfs) tiene el detalle.

## Contraseñas

Un archivo de Word, Excel, PowerPoint, OpenDocument o PDF protegido con contraseña la pide al abrirse, y al guardar sigue protegido. Archivo ▸ Proteger añade, cambia y elimina la contraseña de un documento. Guardar en un formato que no puede conservar una contraseña (texto, CSV, RTF, HTML, Markdown, EPUB) pregunta antes. Un documento protegido que ha sido manipulado se rechaza, gracias a una corrección de ElixirOffice.

Por omisión, LibreOffice 26 cifra los archivos OpenDocument de una forma que Libera Suite todavía no sabe leer, y Libera Suite lo dice en lugar de pedir la contraseña. Mientras un documento protegido está abierto, su copia de trabajo en tu disco no está cifrada, para que un fallo no te haga perder tus cambios. [Trabajar con documentos](../guide/documents.md#passwords) tiene el detalle.

## Firmas digitales

Un documento de Word, Excel o PowerPoint firmado muestra sus firmas al abrirse, cada una válida o no, y se abre en solo lectura. *Protección* ▸ *Firma* firma uno con un archivo de clave (PKCS#12 o PEM) y su frase de contraseña, y puedes eliminar firmas. Hemos comprobado con Microsoft Office y LibreOffice las firmas hechas en Libera Suite, y en Libera Suite las firmas hechas por ambos.

*Válida* significa que el documento no ha cambiado desde que se firmó: todavía no se comprueba quién emitió el certificado ni si ha caducado. Todavía no se puede firmar un documento protegido, un archivo OpenDocument ni un PDF. [Trabajar con documentos](../guide/documents.md#signatures) tiene el detalle.

## Otros cambios

- **Los documentos de Word 97-2003 se abren.** Ningún archivo `.doc` se había abierto nunca. Ahora se abren también los archivos web (`.mht`), FictionBook (`.fb2`) y los libros EPUB.
- **El conversor arranca en aproximadamente la mitad de tiempo**, así que cada apertura y cada guardado son algo más rápidos.
- **Soltar un archivo en una ventana funciona en Linux**: un documento se abre en su propia ventana, y una imagen entra en el documento. El Flatpak también puede abrir ahora archivos en memorias USB y unidades montadas.
- **Un documento que otra persona tiene abierto ahora lo dice, se abra en la ventana que se abra.** Cada ventana recibía el estado de la primera.
- **En Windows, una ventana ya no se abre más grande que la pantalla.**

## Seguridad

Todas las versiones anteriores tienen estos problemas, así que actualiza, por favor.

- **Un documento ya no puede copiar en sí mismo imágenes de tu disco.** Una imagen enlazada a una ruta de tu disco se copiaba en cada documento guardado o convertido a partir de él, así que al devolver el documento se enviaba también la imagen. Ahora una imagen enlazada solo se lee desde una dirección web.
- **Se han cerrado tres fallos de cross-site scripting (XSS).** Un documento preparado podía ejecutar un script en el editor cuando seleccionabas un cambio con seguimiento, abrías el Asistente de funciones o hacías clic en un enlace `javascript:`. Los tres se muestran ahora como texto o se rechazan. La página del editor además solo carga imágenes desde Libera Suite, así que un script ya no puede enviar nada fuera en la dirección de una imagen.
- **El conversor ya no escribe trozos de su propia memoria en los archivos que crea.**
- **Un documento pequeño ya no puede llevar al conversor a gigabytes de memoria.**

## Descargas firmadas y código fuente

Los paquetes Flatpak están firmados con nuestra clave OpenPGP, y [Otras formas de instalar](../main/alt-install.md) explica cómo comprobar uno. El instalador de Windows y `Libera.app` aún no están firmados. [Instalar](../main/install.md) explica cómo pasar el aviso sobre el instalador; la orden de PowerShell de una línea, pip, pipx y Homebrew no encuentran ninguno.

El código fuente de los wheels del conversor es el paquete fuente `libera-core` en PyPI: los commits de origen que fija, nuestros parches y los scripts de compilación. El código fuente de la aplicación es la etiqueta `0.7.0` de [abilian/libera-suite](https://github.com/abilian/libera-suite).

## Sin cambios

- **Linux en arm64** sigue instalando la 0.4.1: aún no hay compilación arm64 de la 0.7.

[Qué funciona hoy](../main/status.md) indica qué está hecho, qué está a medias y qué no se ha empezado todavía, y [la hoja de ruta](/en/develop/roadmap/), en inglés, dice qué viene después.

## Cuéntanos

Libera Suite es joven: cada informe cuenta. El más útil es un documento que sale mal, adjunto a tu mensaje con la salida de `libera --diagnose`. [Comentarios](../feedback.md) explica cómo contactar con nosotros.

*Abilian*
