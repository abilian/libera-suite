---
date: 2026-10-20
description: Libera Suite 0.5 habla tu idioma, muestra los documentos con las fuentes instaladas en tu ordenador, los abre antes y limpia tras sus propias actualizaciones.
---

# Libera Suite 0.5: en tu idioma, con tus fuentes

Libera Suite 0.5 ya está disponible. Ahora sigue el idioma de tu sistema y muestra un documento con las fuentes instaladas en tu ordenador.

Libera Suite es una suite ofimática libre y de código abierto para Windows, macOS y Linux: Libera Words para textos, Libera Tables para hojas de cálculo, Libera Slides para presentaciones y Libera Diagrams, un visor de dibujos de Visio. Abre y guarda los formatos de Microsoft Office y de LibreOffice, en tu propio ordenador, sin cuenta ni servicio en la nube.

[Instalar Libera Suite](../main/install.md){ .md-button .md-button--primary }

¿Ya la usas? Cierra Libera Suite si está abierta y vuelve a ejecutar el instalador o la orden de instalación, o `brew upgrade libera` si usas Homebrew. Esta versión instala componentes nuevos, una descarga única de unos 90 MB.

## En tu idioma

Hasta ahora, Libera Suite solo hablaba inglés. Sus cuatro aplicaciones siguen ahora el idioma de tu sistema, y la línea `ui_language` del [archivo de configuración](../guide/documents.md#your-name-in-documents) elige otro. En español, francés, alemán e italiano también lo siguen la barra de menús, la ventana de inicio y los cuadros de diálogo, y la Ayuda abre esta documentación en el mismo idioma.

Un documento nuevo parte de una página en blanco para tu idioma y tu región: papel A4 en todas partes salvo en Estados Unidos, donde hasta ahora era US Letter para todos, y con la ortografía revisada en tu idioma.

## Con tus fuentes

Un documento compuesto con una fuente que tienes instalada se muestra ahora con ella, en pantalla y en su PDF, donde antes recibía una sustituta. Libera Suite hace la lista de tus fuentes al instalar sus componentes, y de nuevo cada vez que instalas o quitas una; no se copia nada. La línea `installed_fonts = false` la limita a las fuentes que trae Libera Suite.

## Antes en pantalla

La ventana de un documento se abre ahora enseguida, mientras el documento aún se prepara. En nuestro Mac, un documento de texto pequeño aparece alrededor de un segundo antes. Un archivo que Libera Suite no puede leer abre ahora una ventana que lo indica, y luego la cierra.

## Otros cambios

- **Componentes actualizados**, de octubre, con las correcciones del proyecto original hechas desde la versión anterior.
- **Una política de seguridad más estricta.** Los componentes no pueden cargar ni enviar nada a ningún sitio salvo a la propia Libera Suite. La excepción es una imagen que un documento enlaza por su dirección web, que se descarga como en cualquier suite ofimática.
- **Las macros están desactivadas, y se conservan.** Las macros de los componentes son JavaScript y no ejecutan el VBA de los documentos de Microsoft Office, así que están desactivadas. Las macros de un documento se conservan: guardar un `.docm`, un `.xlsm` o un `.pptm` deja su VBA como estaba, y Libera Words ahora abre y guarda `.docm`.
- **Los componentes antiguos se eliminan.** Cada actualización dejaba la versión anterior en el disco, unos 400 MB cada una. Una versión que nada ha usado en cuatro semanas se elimina ahora.
- **Correcciones.** El menú de fuentes muestra cada nombre completo. Un libro `.xlsb` se abre, en lugar de abrirse como una presentación vacía. En macOS, salir con Cmd-Q ya no deja documentos bloqueados. En Windows, la lista Recientes muestra el nombre de cada documento y ya no pierde sus entradas.

## Lo que desaparece

- **Guardar como `.xlsb`.** Escribir uno fallaba en Linux. Guarda como `.xlsx`; Excel abre los dos.
- **Linux en arm64, por ahora.** No hay compilación arm64 de la 0.5. El script de instalación instala la 0.4.1 en esas máquinas; una versión posterior volverá a admitir arm64.

[Qué funciona hoy](../main/status.md) indica qué está hecho, qué está a medias y qué no se ha empezado todavía.

## Cuéntanos

Libera Suite es joven, y cada informe cuenta. El más útil sigue siendo un documento que sale mal, adjunto a tu mensaje con la salida de `libera --diagnose`. [Comentarios](../feedback.md) explica cómo contactar con nosotros.

*Abilian*
