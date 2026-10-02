# Trabajar con documentos

La interfaz de Libera Suite está en inglés: los menús y botones se citan aquí tal como aparecen en pantalla.

## Abrir

```sh
libera                             # la ventana de inicio
libera ~/Documents/nota.docx
libera ~/Documents/presupuesto.xlsx
libera ~/Documents/red.vsdx
```

**Es el documento el que decide qué editor obtienes.** No hay ningún comando para elegir uno, igual que no se elige un editor de texto para abrir un `.txt`: abres el documento y aparece el editor adecuado. Un `.xlsx` se abre en Tables, un `.pptx` en Slides, un `.vsdx` en Diagrams.

![La ventana de inicio, con una tarjeta New para cada uno de Document, Spreadsheet y Presentation, un botón Open y una lista Recent de tres documentos.](../assets/start.png)

Sin argumentos, `libera` abre la **ventana de inicio**: un documento nuevo de cualquier tipo, un diálogo para abrir, tus documentos recientes y la procedencia de los editores. Elige algo y la ventana de inicio da paso al documento.

Libera Suite abre **un documento por ventana**, así que un comodín de la shell hace lo que parece:

```sh
libera ~/Documents/*.docx     # una ventana para cada uno
```

También puedes abrir un documento desde el editor, con **File ▸ Open** o **File ▸ Open Recent**. Los dos abren una ventana nueva y no tocan el documento que ya tienes abierto.

**File ▸ New** ofrece, desde cualquier ventana, un documento (Document), una hoja de cálculo (Spreadsheet) o una presentación (Presentation), cada uno en su propia ventana. En macOS, `⌘N` crea uno del mismo tipo que la ventana en primer plano. En el propio editor, **File ▸ Create New** te pregunta cuál de los tres quieres crear.

## Guardar

**File ▸ Save** vuelve a escribir el documento que abriste. **File ▸ Save As** pregunta dónde ponerlo. A partir de ahí, ese es el documento que estás editando.

Al guardar, el formato de trabajo del editor se convierte de nuevo en un documento de verdad, lo que tarda alrededor de un segundo.

## Exportar

Save As sirve también para exportar: su diálogo tiene una lista **File Format**.

| | |
| :--- | :--- |
| Word Document | `.docx` |
| Word Template | `.dotx` |
| OpenDocument Text | `.odt` |
| OpenDocument Template | `.ott` |
| PDF | `.pdf` |
| Rich Text Format | `.rtf` |
| HTML | `.html` |
| Markdown | `.md` |
| EPUB | `.epub` |
| FictionBook | `.fb2` |
| Plain Text | `.txt` |

Elegir un formato cambia el nombre del archivo en el diálogo. No pueden quedar desalineados: no puedes acabar con un archivo ODT llamado `.docx`.

El conversor no sabe escribir todos los formatos que sabe leer. En particular, `.doc` se abre pero no se guarda; usa `.docx` o `.rtf` para algo que tenga que volver a una versión antigua de Word.

Si buscas una entrada **Download As** en el menú File, no existe. Los editores la ocultan cuando funcionan como aplicación de escritorio sin conexión y ponen Save As en su lugar: la misma función, una entrada más arriba.

## La barra de menús

En Linux y Windows la barra está dentro de la ventana: **File**, **Edit**, **View** y **Help**, este último con *Libera Help* y *About Libera Suite*. De lo que ofrece allí el menú se derivan tres diferencias. Ningún elemento tiene atajo de teclado, así que las teclas de abajo pertenecen al editor y funcionan en la página. **Open Recent** se construye al iniciar la aplicación: un documento que abres hoy aparece en él mañana. Nada se atenúa: Save sin nada que guardar no hace nada.

En macOS es una barra de menús de Mac de verdad, con los mismos elementos más **Window**. Los atajos habituales funcionan allí, tenga o no el foco el editor:

| | |
| :--- | :--- |
| `⌘N` `⌘O` | Nuevo (del tipo de la ventana en primer plano), Abrir: cada uno en su propia ventana |
| `⌘S` `⇧⌘S` | Guardar, Guardar como |
| `⌘P` | Imprimir |
| `⌘W` | Cerrar, preguntando antes qué hacer con los cambios sin guardar |
| `⌘Z` `⇧⌘Z` | Deshacer, Rehacer |
| `⌘F` | Buscar |
| `⌘?` | Esta documentación |
| `⌘+` `⌘-` `⌘0` | Ampliar, reducir, ajustar la página |
| `⌘8` | Marcas de formato |

**File ▸ Open Recent** se reconstruye cada vez que lo abres. El menú **Window** enumera todos los documentos abiertos.

Save, Undo y Redo aparecen atenuados cuando no hay nada que guardar o deshacer. El editor rechaza esas órdenes sin decir nada: un elemento de menú que siguiera activo parecería roto.

## Cerrar

Al cerrar una ventana con cambios sin guardar, primero se pregunta: **Save**, **Don't Save** o **Cancel**.

Elegir Don't Save no es definitivo. Libera Suite conserva lo que escribiste y te lo ofrece la próxima vez que abres ese documento.

## Imprimir

**File ▸ Print**, o el botón de la impresora, genera un PDF del documento y lo abre en el visor de PDF de tu sistema, donde está el diálogo de impresión.

Por ahora esa es la opción elegida: el visor que ya tienes te da intervalos de páginas, tamaño de papel, escala y vista previa, y nada de eso lo haríamos mejor en una primera versión.

## Imágenes

Las imágenes incrustadas en un documento se conservan al abrir y al guardar. **Insert ▸ Image** añade una imagen desde el disco.

## Corrección ortográfica {#spell-checking}

Las faltas se subrayan; el clic derecho ofrece sugerencias. El diccionario que se usa depende del **idioma del documento**, que fijas en la **barra de estado** de la parte inferior de la ventana, documento a documento.

Se incluyen diccionarios para cinco idiomas: inglés (de Estados Unidos y del Reino Unido), francés, alemán, español e italiano. Un idioma sin diccionario no es un error; sus palabras simplemente se consideran correctas. Las palabras que añades con *Add to dictionary* vuelven a aparecer subrayadas en la sesión siguiente, porque los diccionarios personales todavía no se guardan.

## Tu nombre en los documentos {#your-name-in-documents}

Los cambios registrados y los comentarios se atribuyen a una persona, cuyo nombre se escribe en el archivo guardado. Libera Suite lo toma de tu cuenta: tu nombre completo tal como lo conoce macOS, el nombre para mostrar de tu cuenta de Windows o el campo «nombre completo» de tu cuenta Unix en Linux, y si no hay ninguno, tu nombre de inicio de sesión.

Todavía no hay ningún ajuste para cambiarlo. Si un documento tiene que salir con otro nombre, [dínoslo](../feedback.md).

## Dónde van tus archivos de trabajo

Mientras un documento está abierto, Libera Suite mantiene una carpeta de sesión junto a sus datos de aplicación. Contiene la copia de trabajo del editor y un registro continuo de tus cambios, lo que hace que guardar sea rápido y deshacer sea fiable. No es una copia de seguridad: el documento está donde lo guardaste.

---

La página siguiente es [Qué funciona hoy](../main/status.md): qué está hecho y los problemas que ya conocemos. Si te encuentras con uno que no aparece allí, [escríbenos](../feedback.md).
