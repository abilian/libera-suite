# Trabajar con documentos

La interfaz de Libera Suite está en inglés: los menús y botones se citan aquí tal como aparecen en pantalla.

## Abrir {#open}

```sh
libera                             # la ventana de inicio
libera ~/Documents/nota.docx
libera ~/Documents/presupuesto.xlsx
libera ~/Documents/red.vsdx
```

**Es el documento el que decide qué aplicación obtienes.** No hay ningún comando para elegir uno, igual que no se elige un editor de texto para abrir un `.txt`: abres el documento y aparece la aplicación adecuada. Un `.xlsx` se abre en Tables, un `.pptx` en Slides, un `.vsdx` en Diagrams.

![La ventana de inicio, con una tarjeta New para cada uno de Document, Spreadsheet y Presentation, un botón Open y una lista Recent de tres documentos.](../assets/start.png)

Sin argumentos, `libera` abre la **ventana de inicio**: un documento nuevo de cualquier tipo, un diálogo para abrir, tus documentos recientes y la procedencia de los componentes. Elige algo y la ventana de inicio da paso al documento.

Libera Suite abre **un documento por ventana**, así que un comodín de la shell hace lo que parece:

```sh
libera ~/Documents/*.docx     # una ventana para cada uno
```

También puedes abrir un documento desde la ventana del documento, con **Archivo ▸ Abrir** o **Archivo ▸ Abrir reciente**. Los dos abren una ventana nueva y no tocan el documento que ya tienes abierto.

**En macOS, los documentos pueden abrirse como pestañas** de una misma ventana. Libera Suite sigue el ajuste del sistema, *Preferir pestañas al abrir documentos* en Ajustes del Sistema ▸ Escritorio y Dock, como cualquier aplicación de documentos en Mac. Con *Siempre*, cada documento se abre en una pestaña. Si no, se abre en su propia ventana, y **Ventana ▸ Merge All Windows** las reúne. El **+** al final de la barra de pestañas abre la ventana de inicio en una pestaña nueva, y el documento que eliges ahí ocupa su lugar. Una pestaña se arrastra fuera para tener su propia ventana.

**Un documento que sueltas** sobre una ventana de Libera Suite, incluida la ventana de inicio, se abre en una ventana propia. Una imagen que sueltas sobre un documento se inserta en él.

**Archivo ▸ Nuevo** ofrece, desde cualquier ventana, un documento, una hoja de cálculo o una presentación, cada uno en su propia ventana. En macOS, `⌘N` crea uno del mismo tipo que la ventana en primer plano. En la propia ventana del documento, **Archivo ▸ Crear nuevo** te pregunta cuál de los tres quieres crear.

## Guardar

**Archivo ▸ Guardar** vuelve a escribir el documento que abriste. **Archivo ▸ Guardar como** pregunta dónde ponerlo. A partir de ahí, ese es el documento que estás editando.

Al guardar, el formato de trabajo se convierte de nuevo en un documento de verdad, lo que tarda alrededor de un segundo.

## Exportar

Guardar como sirve también para exportar: su diálogo tiene una lista **Formato de archivo**.

| | |
| :--- | :--- |
| Documento de Word | `.docx` |
| Plantilla de Word | `.dotx` |
| Texto de OpenDocument | `.odt` |
| Plantilla de OpenDocument | `.ott` |
| PDF | `.pdf` |
| Formato de texto enriquecido | `.rtf` |
| HTML | `.html` |
| Markdown | `.md` |
| EPUB | `.epub` |
| FictionBook | `.fb2` |
| Texto sin formato | `.txt` |

Elegir un formato cambia el nombre del archivo en el diálogo. No pueden quedar desalineados: no puedes acabar con un archivo ODT llamado `.docx`.

El conversor no sabe escribir todos los formatos que sabe leer. En particular, `.doc` se abre pero no se guarda; usa `.docx` o `.rtf` para algo que tenga que volver a una versión antigua de Word.

Si buscas una entrada **Descargar como** en el menú Archivo, no existe. Los componentes la ocultan cuando funcionan como aplicación de escritorio sin conexión y ponen Guardar como en su lugar: la misma función, una entrada más arriba.

### Desde la línea de comandos {#from-the-command-line}

`libera --convert` hace lo mismo sin abrir ninguna ventana, para un documento o para cien. El formato se indica por su extensión, con `-t`, o se toma del nombre dado a `-o`:

```sh
libera --convert *.docx -t pdf             # informe.pdf junto a informe.docx, etc.
libera --convert charla.pptx -o charla.odp # un solo documento, con nombre
libera --convert *.xlsx -t ods --outdir ods/
libera --convert informe.docx -t pdf -o - | lp   # a la salida estándar
```

Un archivo que ya tiene el nuevo nombre se reemplaza. El documento que se convierte nunca se sobrescribe, y dos documentos que acabarían con el mismo nombre se rechazan antes de convertir nada. Las opciones son las de pandoc, salvo `-f`: la extensión dice qué es un documento.

## La barra de menús

En Linux y Windows la barra está dentro de la ventana: **Archivo**, **Edición**, **Ver** y **Ayuda**, este último con *Ayuda de Libera* y *Acerca de Libera Suite*. De lo que ofrece allí el menú se derivan tres diferencias. En Linux, Nuevo, Abrir y Cerrar muestran Ctrl-N, Ctrl-O y Ctrl-W, y ningún otro elemento muestra su tecla; en Windows, ninguno. Ctrl-N, Ctrl-O, Ctrl-W, Ctrl-S, Ctrl-Mayús-S, Ctrl-P y Ctrl-Z hacen allí lo que las teclas ⌘ de abajo hacen en un Mac. **Abrir reciente** se construye al iniciar la aplicación: un documento que abres hoy aparece en él mañana. Nada se atenúa: Guardar sin nada que guardar no hace nada.

En macOS es una barra de menús de Mac de verdad, con los mismos elementos más **Ventana**. Los atajos habituales funcionan allí, tenga o no el foco el documento:

| | |
| :--- | :--- |
| `⌘N` `⌘O` | Nuevo (del tipo de la ventana en primer plano), Abrir: cada uno en su propia ventana, o pestaña |
| `⌘S` `⇧⌘S` | Guardar, Guardar como |
| `⌘P` | Imprimir |
| `⌘W` | Cerrar, preguntando antes qué hacer con los cambios sin guardar |
| `⌘Z` `⇧⌘Z` | Deshacer, Rehacer |
| `⌘F` | Buscar |
| `⌘?` | Esta documentación |
| `⌘+` `⌘-` `⌘0` | Ampliar, reducir, ajustar la página |
| `⌘8` | Marcas de formato |

**Archivo ▸ Abrir reciente** se reconstruye cada vez que lo abres. El menú **Ventana** enumera todos los documentos abiertos.

Guardar, Deshacer y Rehacer aparecen atenuados cuando no hay nada que guardar o deshacer. Los componentes rechazan esas órdenes sin decir nada: un elemento de menú que siguiera activo parecería roto.

## Cerrar

Al cerrar una ventana con cambios sin guardar, primero se pregunta: **Guardar**, **No guardar** o **Cancelar**.

Elegir No guardar no es definitivo. Libera Suite conserva lo que escribiste y te lo ofrece la próxima vez que abres ese documento.

## Imprimir

**Archivo ▸ Imprimir**, o el botón de la impresora, genera un PDF del documento, pregunta dónde guardarlo (en la carpeta del documento, salvo que elijas otra) y lo abre en el visor de PDF de tu sistema, donde está el diálogo de impresión.

Por ahora esa es la opción elegida: el visor que ya tienes te da intervalos de páginas, tamaño de papel, escala y vista previa, y nada de eso lo haríamos mejor en una primera versión.

## Imágenes

Las imágenes incrustadas en un documento se conservan al abrir y al guardar. **Insertar ▸ Imagen** añade una imagen desde el disco.

## Corrección ortográfica {#spell-checking}

Las faltas se subrayan; el clic derecho ofrece sugerencias. El diccionario que se usa depende del **idioma del documento**, que fijas en la **barra de estado** de la parte inferior de la ventana, documento a documento.

Se incluyen diccionarios para cinco idiomas: inglés (de Estados Unidos y del Reino Unido), francés, alemán, español e italiano. Un idioma sin diccionario no es un error; sus palabras simplemente se consideran correctas. Las palabras que añades con *Add to dictionary* se conservan: desde ese momento son correctas en todos los documentos y en todos los idiomas.

## Tu nombre en los documentos {#your-name-in-documents}

Los cambios registrados y los comentarios se atribuyen a una persona, cuyo nombre se escribe en el archivo guardado. Libera Suite lo toma de tu cuenta: tu nombre completo tal como lo conoce macOS, el nombre para mostrar de tu cuenta de Windows o el campo «nombre completo» de tu cuenta Unix en Linux, y si no hay ninguno, tu nombre de inicio de sesión.

Para usar otro nombre, escríbelo en el archivo de configuración, y crea el archivo si no existe:

```toml
user_name = "Jeanne Dupont"
```

| | |
| :--- | :--- |
| Linux | `$XDG_CONFIG_HOME/libera/config.toml`, or `~/.config/libera/config.toml` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/config/libera/config.toml` |
| macOS | `~/Library/Application Support/Libera Suite/config.toml` |
| Windows | `%USERPROFILE%\.config\libera\config.toml` |

El nombre se aplica a las ventanas que se abran tras el siguiente inicio de Libera Suite. Los documentos ya guardados conservan el nombre con el que se guardaron.

El mismo archivo desactiva la búsqueda diaria de una versión nueva, con una línea aparte:

```toml
check_updates = false
```

Otra se limita a las fuentes que incluye Libera Suite, sin las instaladas en tu máquina, para que un documento se vea igual en todos los ordenadores:

```toml
installed_fonts = false
```

Y otra fija el idioma de las aplicaciones, cuando no debe ser el de tu sistema. Un documento nuevo sigue tomando el tamaño de papel de la región de tu sistema:

```toml
ui_language = "fr"
```

Para usar otro archivo durante un arranque, sin tocar este, indíquelo con `libera --config ARCHIVO` (o `-c ARCHIVO`), o en la variable de entorno `LIBERA_CONFIG`. Un Libera Suite iniciado así no entrega sus documentos a uno que ya esté abierto, que los abriría con su propia configuración: ciérrelo primero.

## Dónde van tus archivos de trabajo

Mientras un documento está abierto, Libera Suite mantiene una carpeta de sesión junto a sus datos de aplicación. Contiene la copia de trabajo y un registro continuo de tus cambios, lo que hace que guardar sea rápido y deshacer sea fiable. No es una copia de seguridad: el documento está donde lo guardaste.

---

La página siguiente es [Qué funciona hoy](../main/status.md): qué está hecho y los problemas que ya conocemos. Si te encuentras con uno que no aparece allí, [escríbenos](../feedback.md).
