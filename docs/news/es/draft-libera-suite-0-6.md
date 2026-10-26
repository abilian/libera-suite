---
date: 2026-10-26
description: Libera Suite 0.6 habla todos los idiomas de sus aplicaciones, maqueta como Word cuando falta una fuente, conserva los títulos de Markdown y revisa la ortografía en neerlandés.
---

# Libera Suite 0.6: todos los idiomas, y páginas que se cortan como en Word

Libera Suite 0.6 ya está disponible. Sus menús y ventanas hablan ahora los 44 idiomas de sus aplicaciones, y un documento cuyas fuentes no tienes se maqueta como en Word.

Libera Suite es una suite ofimática libre y de código abierto para Windows, macOS y Linux: Libera Words para textos, Libera Tables para hojas de cálculo, Libera Slides para presentaciones y Libera Diagrams, un visor de dibujos de Visio. Abre y guarda los formatos de Microsoft Office y de LibreOffice, en tu propio ordenador, sin cuenta ni servicio en la nube.

[Instalar Libera Suite](../main/install.md){ .md-button .md-button--primary }

¿Ya la usas? Cierra Libera Suite si está abierta y vuelve a ejecutar el instalador o la orden de instalación, o `brew upgrade libera` si usas Homebrew. Esta versión instala componentes nuevos, una descarga única de unos 90 MB.

## Todos los idiomas

Desde la 0.5 las aplicaciones siguen el idioma de tu sistema, pero la barra de menús, la ventana de inicio y los diálogos solo lo hacían en español, francés, alemán e italiano. Ahora lo siguen en los 44 idiomas, del árabe al vietnamita, y en árabe, hebreo y urdu la ventana de inicio se lee de derecha a izquierda.

Solo las traducciones española, francesa, alemana e italiana las ha revisado un hablante nativo. Las demás son borradores: si una palabra en tu idioma está mal o suena rara, [escríbenos](../feedback.md), y tu corrección entrará en la próxima versión.

## Páginas que se cortan como en Word

Cuando un documento pide una fuente que tu ordenador no tiene, Libera Suite la sustituye ahora como Word:

- **Calibri, Cambria, Arial, Times New Roman y Courier New** reciben Carlito, Caladea y Liberation, que tienen los mismos anchos, así que las líneas y las páginas se cortan en los mismos puntos que en Word. En Mac, Calibri iba a la fuente instalada más parecida, y el mismo documento podía maquetarse distinto de un ordenador a otro.
- **Una fuente que Word tampoco conocería** recibe la sustituta de Calibri, como Word usa Calibri, donde antes recibía Liberation Sans. Dos documentos de nuestro conjunto de prueba tienen ahora el número de páginas de Word.
- **Los caracteres de Wingdings, Webdings y Symbol** se ven como los símbolos que representan: una estrella, una marca de verificación, una carita, donde una Wingdings ausente mostraba letras.

## Otros cambios

- **En macOS, Libera Suite está entre tus aplicaciones.** El script de instalación pone `Libera.app` en tu carpeta Aplicaciones, y `libera --launcher-install` hace lo mismo después de Homebrew: el Finder la ofrece en *Abrir con*, un doble clic en un documento puede abrirlo en ella, y el Dock muestra Libera, donde mostraba Python.
- **El Markdown conserva sus títulos.** Un archivo Markdown abierto, editado y guardado convertía cada título en un párrafo en negrita.
- **Revisión ortográfica en neerlandés**, con el diccionario de OpenTaal. Cada diccionario viene ahora con su licencia.
- **En Linux, el menú Archivo muestra sus atajos:** Nuevo, Abrir y Cerrar muestran Ctrl-N, Ctrl-O y Ctrl-W.
- **Un archivo OpenDocument sin estilos de página maestra conserva sus estilos**, donde cada párrafo se abría con el estilo predeterminado.

## Lo que no cambia

- **Linux en arm64** sigue instalando la 0.4.1: aún no hay compilación arm64 de la 0.6.

[Qué funciona hoy](../main/status.md) indica qué está hecho, qué está a medias y qué no se ha empezado todavía.

## Cuéntanos

Libera Suite es joven, y cada informe cuenta. El más útil sigue siendo un documento que sale mal, adjunto a tu mensaje con la salida de `libera --diagnose`. [Comentarios](../feedback.md) explica cómo contactar con nosotros.

*Abilian*
