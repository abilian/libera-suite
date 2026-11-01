---
date: 2026-10-12
description: Libera Suite 0.4 señala un documento ya abierto en otro sitio, en Libera Suite o en LibreOffice, reproduce con más fidelidad los archivos OpenDocument y añade arrastrar y soltar, un diccionario personal y la conversión desde la línea de órdenes.
---

# Libera Suite 0.4: más segura en una carpeta compartida, más fiel a OpenDocument

Libera Suite 0.4 ya está disponible. Protege un documento que otra persona tiene abierto, en Libera Suite o en LibreOffice. Sus editores leen y escriben con más exactitud los formatos OpenDocument.

[Actualizar Libera Suite](../main/install.md#update){ .md-button .md-button--primary }

Cierra Libera Suite y vuelve a ejecutar el instalador o la orden de instalación, o `brew upgrade libera`. Esta versión instala editores nuevos, una descarga única de unos 100 MB.

## El bloqueo de documentos

Hasta ahora, nada impedía que dos ventanas editaran el mismo documento: la última en guardar sobrescribía el trabajo de la otra. La beta lo incluía entre sus límites. La 0.4 lo elimina entre dos ventanas de Libera Suite y también entre Libera Suite y LibreOffice. Microsoft Office todavía no ve estos bloqueos: un documento abierto en Word sigue expuesto.

- **Libera Suite pone un bloqueo en el formato de LibreOffice.** Al abrir un documento, crea a su lado el pequeño archivo de bloqueo que usa LibreOffice. También respeta los bloqueos que pone LibreOffice. Un documento ya abierto en otro sitio se abre en modo *locked for editing*: puedes leerlo y cambiarlo, pero al guardar se pide otro lugar. El original queda intacto.
- **Volver a abrir un documento trae su ventana al frente**, sin abrir una segunda.
- **Una ventana indica los cambios sin guardar**: un punto en el botón de cerrar en macOS, un `*` delante del título en Linux y Windows.

## Más fidelidad a los formatos OpenDocument

Los editores de la 0.4 incluyen **68 correcciones para los formatos OpenDocument** (`.odt`, `.ods`, `.odp`), cada una encontrada con los documentos de prueba del propio LibreOffice. También desaparecen dos defectos de los archivos CSV. Un emoji impedía guardar un CSV; un CSV grande perdía un carácter de cada 500 000 al leerlo.

## El aviso de nuevas versiones

Novedad de la 0.4: como mucho una vez al día, Libera Suite lee en nuestro servidor de descargas el número de la última versión. Si es más reciente que la tuya, te lo dice una vez, con los pasos para tu forma de instalación. No descarga nada y no envía nada sobre ti ni sobre tus documentos; sin conexión, no hace nada. La línea `check_updates = false` en el [archivo de configuración](../guide/documents.md#your-name-in-documents) lo desactiva.

## Otras novedades

- **Arrastrar y soltar.** Un documento soltado en una ventana se abre; una imagen soltada en un documento se inserta en él.
- **El diccionario personal.** Una palabra añadida con *Add to dictionary* se conserva, para todos los documentos y todos los idiomas.
- **Tu nombre en el control de cambios y los comentarios**, fijado con `user_name` en el archivo de configuración.
- **Ctrl-N, Ctrl-O y Ctrl-W** en Linux y Windows.
- **Imprimir** pregunta dónde guardar el PDF, empezando en la carpeta del documento.
- **La conversión desde la línea de órdenes**: `libera --convert *.docx -t pdf` escribe un PDF junto a cada documento, sin abrir ninguna ventana.
- **La ventana About** muestra la versión instalada, el primer dato que dar en un informe de error.

Los límites que quedan, entre ellos la falta de pestañas y un instalador de Windows aún sin firmar, están en [la página de estado](../main/status.md).

## Informa de los problemas

El informe más útil sigue siendo un documento que sale mal, adjunto a tu mensaje junto con la salida de `libera --diagnose`. [Comentarios](../feedback.md) explica cómo escribirnos.

*Abilian*
