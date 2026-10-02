# Qué funciona hoy

Libera Suite es joven. Esta página recoge su estado: qué está hecho, qué lo está solo en parte y qué no se ha empezado todavía.

La interfaz de Libera Suite está en inglés: los menús y botones se citan aquí tal como los verás en pantalla.

## Qué funciona

| | |
| :--- | :--- |
| **Cuatro editores** | Windows 10 y 11 en x64, Linux en x86_64 y arm64, macOS en Apple Silicon. Words, Tables y Slides editan; Diagrams lee archivos de Visio. |
| **Abrir y guardar** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Save, Save As, New. |
| **Exportar** | Save As ofrece una lista de formatos para cada editor, PDF incluido. Cada formato ofrecido se ha comprobado con una conversión real. |
| **Imágenes** | Se conservan al abrir y al guardar; Insert ▸ Image funciona. |
| **Imprimir** | Genera un PDF y lo abre en tu visor de PDF. |
| **Corrección ortográfica** | Cinco idiomas, con sugerencias. Más abajo, los detalles. |
| **Documentos recientes** | File ▸ Open Recent recuerda los últimos 20. |
| **Varios documentos a la vez** | También de tipos distintos, una ventana para cada uno: desde File ▸ New o File ▸ Open, con doble clic en el gestor de archivos o con `libera *.docx`. El tipo de archivo elige el editor. |
| **En el menú Inicio y en el menú de aplicaciones** | En Windows, el instalador añade Libera Suite al menú Inicio y al escritorio, y la incluye en *Abrir con* del Explorador de archivos. En Linux, el Flatpak la añade al menú de aplicaciones con su icono y sus asociaciones de archivos; `libera --launcher-install` hace lo mismo con cualquier otra instalación. |
| **Una ventana de inicio** | `libera` sin argumentos: documento nuevo, abrir, documentos recientes y procedencia de los editores. |
| **Recuperación tras un cierre inesperado** | Los cambios sin guardar se te ofrecen la próxima vez que abres el documento. |
| **Al cerrar, pregunta** | Una ventana con cambios sin guardar ofrece Save, Don't Save o Cancel. |
| **Una barra de menús** | File, Edit, View y Help en todas las plataformas. macOS añade Window junto con los atajos habituales. |
| **Acerca de** | Quién escribió los editores y con qué licencia: `File ▸ About` en el editor, `Help ▸ About Libera Suite` en Linux y Windows. macOS lo pone en el menú de la aplicación. |
| **Los ajustes se conservan** | El tema, las unidades, el idioma de la corrección y ajustes similares siguen ahí tras reiniciar. |
| **Instalación de los editores** | Desde el servidor, o desde una carpeta local de artefactos compilados. En ambos casos, cada artefacto se comprueba con las huellas incluidas en la aplicación. |

## Problemas conocidos

**No hace falta informar de ninguno**: ya los conocemos. Las secciones siguientes los detallan.

| | |
| :--- | :--- |
| **macOS habla de un desarrollador no identificado** | Solo con una `Libera.app` que has compilado tú: no está firmada con un Developer ID, así que Gatekeeper la bloquea la primera vez. [Otras formas de instalar](alt-install.md#a-double-clickable-application-on-macos) explica cómo seguir adelante. Una instalación con `pip`, `pipx` o Homebrew nunca se encuentra con esto. |
| **Iniciada desde un terminal, el Dock dice «Python»** | Solo cuando inicias `libera` desde una instalación con `pipx` o un entorno virtual. Un icono del Dock toma el nombre del paquete de aplicación desde el que se inició, aquí el del intérprete de Python, y la aplicación no puede cambiarlo. El icono y la barra de menús son los nuestros en cualquier caso; `Libera.app` muestra Libera. |
| **Diagrams no puede guardar** | Abre un archivo `.vsdx` y lo muestra. El conversor no sabe escribir ningún formato de Visio: no hay nada que guardar ni una plantilla en blanco con la que empezar. |
| **Un CSV o un `.txt` con un emoji no se puede guardar como tal** | En macOS y Linux, el conversor estropea el texto plano que contiene un carácter más allá de los primeros 65 536 de Unicode, por ejemplo un emoji. Libera Suite rechaza entonces el guardado y deja el archivo como estaba. Save As en `.xlsx` o en `.docx` lo conserva todo. Está prevista una corrección del conversor para la próxima versión de los editores. |
| **En un CSV de más de unos 500 KB, una fila puede leerse mal** | El conversor se salta un carácter de cada 500 000. Cuando ese carácter es una comilla, una coma o un salto de línea, una celda se parte en dos, o dos celdas o dos filas se juntan. Al abrir el archivo, Libera Suite indica las filas afectadas: compruébalas antes de guardar, porque al guardar se escribe el contenido que muestra la hoja. Está prevista una corrección del conversor para la próxima versión de los editores. |
| **No se pueden editar PDF** | Los PDF solo se generan. Abrir uno para editarlo no está conectado. |
| **Una barra de menús reducida, sin atajos en Linux y Windows** | Linux y Windows tienen File, Edit, View y Help, dibujados en la ventana, sin atajos de teclado; los atajos propios del editor, Ctrl-S, Ctrl-P y Ctrl-Z, siguen funcionando en la página. macOS tiene los mismos menús más Window, con los atajos habituales. |
| **Sin pestañas** | Una ventana por documento. |
| **Sin bloqueo de archivos** | Editar el mismo documento en dos ventanas hará perder una de las dos series de cambios. |
| **Windows avisa sobre el instalador** | El instalador descargado aún no está firmado, así que la primera vez SmartScreen muestra *«Windows protegió su PC»*. [Instalar](install.md#windows) explica cómo seguir adelante. La instalación con la línea de PowerShell nunca se encuentra con esto. |

Si te encuentras con algo que *no* está en esta lista, [cuéntanoslo](../feedback.md).

## Hecho en parte

**La barra de menús en Linux y Windows.** Está dibujada en la ventana, con File, Edit, View y Help; cada elemento funciona. Ninguno tiene atajo de teclado propio, así que las teclas que ya usas van al editor: Ctrl-S, Ctrl-P y Ctrl-Z funcionan en la página. Ctrl-N no hace nada en Linux; en Windows no se ha comprobado. File ▸ New ▸ Document, Spreadsheet o Presentation funciona, igual que las tarjetas New de la ventana de inicio y la pestaña File del editor.

**`Libera.app` en macOS.** `build/macos-app.sh` la compila. Abre un documento con doble clic, aparece en *Abrir con* y muestra la marca de Libera en el Dock. Pero es un lanzador alrededor del intérprete con el que se compiló (no incluye, firma ni notariza nada): todavía no es algo que se pueda dar a otra persona.

## Sin empezar

### En el editor

- **Documentos protegidos con contraseña.** Ni abrirlos ni guardarlos.
- **Firmas digitales.**
- **Combinar correspondencia.**
- **Complementos.** Desactivados en el proyecto original de este fork, así que el panel nunca aparece.

### En la aplicación

- **Pestañas.** Las ventanas existen y el menú Window las enumera, pero no se pueden reunir en una sola ventana.
- **Bloqueo de archivos.** Dos instancias de Libera Suite que editan el mismo archivo no se dan cuenta la una de la otra.
- **Una aplicación redistribuible en macOS.** `Libera.app` funciona desde tu propia copia del código y no incluye ni intérprete ni editores. Windows tiene una: su instalador lo trae todo.
- **Arrastrar y soltar** sobre la ventana o el icono del Dock.
- **Actualizaciones automáticas** y **firma de código**. macOS trata una `Libera.app` compilada por ti como software de un desarrollador no identificado. Windows avisa sobre el instalador descargado.
- **Una ayuda sin conexión**, legible sin navegador ni red. El menú Help abre este sitio; About funciona sin conexión. Más abajo, los detalles.

### En otros ámbitos

- **Editar diagramas.** Diagrams abre un archivo `.vsdx` y lo muestra. El conversor no sabe escribir ningún formato de Visio: no hay nada que guardar ni una plantilla en blanco con la que empezar.
- **Editar PDF.** Los editores incluyen uno para ello. Todavía nada lleva hasta él.
- **Colaboración, almacenamiento en la nube, cuentas, telemetría.** Nada de esto está hecho ni en marcha. [La hoja de ruta](/en/develop/roadmap/), en inglés, describe cómo sería cada uno si llegara. [Qué sale de tu máquina](../index.md#what-leaves-your-machine) recoge todo el uso de la red por parte de la aplicación.

## Notas sobre algunas carencias

### Ayuda

Hay un menú **Help**, en todas las plataformas, que abre este sitio en tu navegador. No hay ayuda *dentro* de la aplicación, donde se podría leer sin conexión. El proyecto original incluye un manual completo. Libera Suite no lo incluye: documenta ONLYOFFICE y ocupa 84 MB en ocho idiomas. La ayuda sin conexión llegará cuando nuestra propia documentación sea lo bastante amplia como para distribuirla.

### Corrección ortográfica

Libera Suite incluye diccionarios de **inglés (de Estados Unidos y del Reino Unido), francés, alemán, español e italiano**: 9,5 MB, elegidos porque el conjunto completo ocupa 327. Añadir un idioma requiere una línea en `build/dictionaries.txt` y volver a compilar los editores.

Un idioma sin diccionario no es un error: sus palabras simplemente se consideran correctas, como en la aplicación de escritorio del proyecto original. Los diccionarios personales (*Add to dictionary*) todavía no se guardan: una palabra añadida vuelve a aparecer subrayada en la sesión siguiente.

Cómo fijar el idioma de un documento se explica en [Trabajar con documentos](../guide/documents.md#spell-checking).

### Tu nombre en los documentos

Los cambios registrados y los comentarios se atribuyen a una persona, cuyo nombre se escribe en el archivo guardado. Libera Suite lo toma de tu cuenta: el nombre completo con el que macOS te conoce, el nombre para mostrar de tu cuenta de Windows o el campo «nombre completo» de tu cuenta Unix en Linux. Todavía no se puede cambiar. [Trabajar con documentos](../guide/documents.md#your-name-in-documents) da los detalles.

### Fuentes

Libera Suite incluye un conjunto básico de fuentes: Liberation, Carlito, Caladea, Open Sans y algunas más, suficientes para mostrar fielmente documentos corrientes, en 7 MB. El conjunto completo ocupa 248 MB. Un documento que pide una fuente que no está ni en este conjunto ni entre las instaladas en tu máquina recibe una fuente sustituta. Está por decidir si se amplía el conjunto, sobre todo para el chino, el japonés y el coreano.

### Fidelidad de la presentación

El motor de maquetación viene del proyecto original y está maduro. Si ves algo mal, lo más probable es que la causa sea nuestro empaquetado (una fuente o un recurso que falta). Por eso esos informes son especialmente útiles: envíanos [tus comentarios](../feedback.md) con el archivo.
