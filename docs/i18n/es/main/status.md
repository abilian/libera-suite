# Qué funciona hoy

Libera Suite es joven. Esta página recoge su estado: qué está hecho, qué lo está solo en parte y qué no se ha empezado todavía.

La interfaz de Libera Suite está en inglés: los menús y botones se citan aquí tal como los verás en pantalla.

## Qué funciona

| | |
| :--- | :--- |
| **Cuatro aplicaciones** | Windows 10 y 11 en x64, Linux en x86_64 (arm64 con la 0.4.1), macOS en Apple Silicon. Words, Tables y Slides editan; Diagrams lee archivos de Visio. |
| **Abrir y guardar** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Save, Save As, New. |
| **Exportar** | Save As ofrece una lista de formatos para cada aplicación, PDF incluido. Cada formato ofrecido se comprueba con una conversión real, cuyo texto se vuelve a leer. |
| **Imágenes** | Se conservan al abrir y al guardar; Insertar ▸ Imagen funciona. |
| **Imprimir** | Genera un PDF, pregunta dónde guardarlo y lo abre en tu visor de PDF. |
| **Corrección ortográfica** | Seis idiomas, con sugerencias. Más abajo, los detalles. |
| **En tu idioma** | Las aplicaciones siguen el idioma de tu sistema, y un documento nuevo parte de la plantilla en blanco de tu región: papel A4 en todas partes salvo en Estados Unidos, y corrección ortográfica en tu idioma. También los siguen la barra de menús, la ventana de inicio y los diálogos, en todos los idiomas de las aplicaciones, y en árabe, hebreo y urdu la ventana de inicio se lee de derecha a izquierda. Solo las traducciones española, francesa, alemana e italiana las ha revisado un hablante nativo; las demás son borradores, y [las correcciones son bienvenidas](../feedback.md). |
| **Documentos recientes** | Archivo ▸ Abrir reciente recuerda los últimos 20. |
| **Varios documentos a la vez** | También de tipos distintos, una ventana para cada uno, o en macOS una pestaña para cada uno cuando el sistema prefiere pestañas: desde Archivo ▸ Nuevo o Archivo ▸ Abrir, con doble clic en el gestor de archivos o con `libera *.docx`. El tipo de archivo elige la aplicación. |
| **En el menú Inicio y en el menú de aplicaciones** | En Windows, el instalador añade Libera Suite al menú Inicio y al escritorio, y la incluye en *Abrir con* del Explorador de archivos. En Linux, el Flatpak la añade al menú de aplicaciones con su icono y sus asociaciones de archivos; `libera --launcher-install` hace lo mismo con cualquier otra instalación. |
| **Una ventana de inicio** | `libera` sin argumentos: documento nuevo, abrir, documentos recientes y procedencia de los componentes. |
| **Recuperación tras un cierre inesperado** | Los cambios sin guardar se te ofrecen la próxima vez que abres el documento. |
| **Un documento abierto en otro lugar** | Si LibreOffice u otra instancia de Libera Suite ya lo tiene abierto, se marca como *bloqueado para edición*: puedes leerlo y modificarlo, y al guardar se pregunta dónde, de modo que el archivo de la otra instancia nunca se sobrescribe. Abrir un documento que ya muestra una ventana trae esa ventana al frente. Microsoft Office y Libera Suite no ven los bloqueos del otro: un documento abierto en Word no está protegido. |
| **Al cerrar, pregunta** | Una ventana con cambios sin guardar ofrece Guardar, No guardar o Cancelar. |
| **Una barra de menús** | File, Edit, View y Help en todas las plataformas. macOS añade Window junto con los atajos habituales. |
| **Acerca de** | Quién escribió los componentes y con qué licencia: `Archivo ▸ Acerca de` en la ventana del documento, `Ayuda ▸ Acerca de Libera Suite` en Linux y Windows. macOS lo pone en el menú de la aplicación. |
| **Los ajustes se conservan** | El tema, las unidades, el idioma de la corrección y ajustes similares siguen ahí tras reiniciar. |
| **Instalación de los componentes** | Desde el servidor, o desde una carpeta local de artefactos compilados. En ambos casos, cada artefacto se comprueba con las huellas incluidas en la aplicación. |

## Problemas conocidos

**No hace falta informar de ninguno**: ya los conocemos. Las secciones siguientes los detallan.

| | |
| :--- | :--- |
| **macOS habla de un desarrollador no identificado** | Solo con una `Libera.app` que has compilado tú: no está firmada con un Developer ID, así que Gatekeeper la bloquea la primera vez. [Otras formas de instalar](alt-install.md#a-double-clickable-application-on-macos) explica cómo seguir adelante. Una instalación con `pip`, `pipx` o Homebrew nunca se encuentra con esto. |
| **Iniciada desde un terminal, el Dock dice «Python»** | Solo cuando inicias `libera` desde una instalación con `pipx` o un entorno virtual. Un icono del Dock toma el nombre del paquete de aplicación desde el que se inició, aquí el del intérprete de Python, y la aplicación no puede cambiarlo. El icono y la barra de menús son los nuestros en cualquier caso; `Libera.app` muestra Libera. Un documento que sueltas sobre ese icono de Python se rechaza en nombre de Python; el icono de `Libera.app` lo acepta. |
| **Diagrams no puede guardar** | Abre un archivo `.vsdx` y lo muestra. El conversor no sabe escribir ningún formato de Visio: no hay nada que guardar ni una plantilla en blanco con la que empezar. |
| **No se pueden editar PDF** | Los PDF solo se generan. Abrir uno para editarlo no está conectado. |
| **Una barra de menús reducida, con pocos atajos visibles en Linux y ninguno en Windows** | Linux y Windows tienen File, Edit, View y Help, dibujados en la ventana. En Linux, Nuevo, Abrir y Cerrar muestran Ctrl-N, Ctrl-O y Ctrl-W, y ningún otro elemento muestra su tecla; en Windows, ninguno. Las teclas funcionan igualmente: Ctrl-N, Ctrl-O, Ctrl-W, Ctrl-S, Ctrl-Mayús-S, Ctrl-P y Ctrl-Z. macOS tiene los mismos menús más Window, con los atajos habituales. |
| **Sin pestañas en Linux ni Windows** | Allí, una ventana por documento. macOS tiene pestañas. |
| **Windows avisa sobre el instalador** | El instalador descargado aún no está firmado, así que la primera vez SmartScreen muestra *«Windows protegió su PC»*. [Instalar](install.md#windows) explica cómo seguir adelante. La instalación con la línea de PowerShell nunca se encuentra con esto. |

Si te encuentras con algo que *no* está en esta lista, [cuéntanoslo](../feedback.md).

## Hecho en parte

**La barra de menús en Linux y Windows.** Está dibujada en la ventana, con Archivo, Edición, Ver y Ayuda; cada elemento funciona. En Linux, Nuevo, Abrir y Cerrar muestran su atajo, y ningún otro elemento; en Windows, ninguno. Las teclas habituales funcionan igualmente: Ctrl-N crea un documento nuevo del mismo tipo, Ctrl-O abre uno, Ctrl-W cierra la ventana (preguntando antes por los cambios sin guardar), y los atajos propios de los componentes, Ctrl-S, Ctrl-Mayús-S (Guardar como), Ctrl-P y Ctrl-Z, también funcionan. En Windows, Ctrl-N, Ctrl-O y Ctrl-W aún no se han comprobado en una máquina real. Archivo ▸ Nuevo ▸ Documento, Hoja de cálculo o Presentación funciona, igual que las tarjetas Nuevo de la ventana de inicio y la pestaña Archivo del propio documento.

**`Libera.app` en macOS.** `build/macos/macos-app.sh` la compila. Abre un documento con doble clic o soltado sobre su icono del Dock, aparece en *Abrir con* y muestra la marca de Libera en el Dock. Pero es un lanzador alrededor del intérprete con el que se compiló (no incluye, firma ni notariza nada): todavía no es algo que se pueda dar a otra persona.

## Sin empezar

### En la ventana del documento

- **Documentos protegidos con contraseña.** Ni abrirlos ni guardarlos.
- **Firmas digitales.**
- **Combinar correspondencia.**
- **Complementos.** Desactivados en el proyecto original de este fork, así que el panel nunca aparece.
- **Macros.** Desactivadas. Las macros propias de los componentes son JavaScript y no ejecutan el VBA de los documentos de Microsoft Office, así que las macros de un documento no se ejecutan. Se conservan: al guardar un `.docm`, `.xlsm` o `.pptm`, su VBA queda intacto. [La hoja de ruta](/en/develop/roadmap/), en inglés, describe qué llegará en su lugar.

### En la aplicación

- **Pestañas en Linux y Windows.** Allí, una ventana por documento, que la barra de tareas agrupa.
- **Una aplicación redistribuible en macOS.** `Libera.app` funciona desde tu propia copia del código y no incluye ni intérprete ni componentes. Windows tiene una: su instalador lo trae todo.
- **Actualizaciones automáticas** y **firma de código**. macOS trata una `Libera.app` compilada por ti como software de un desarrollador no identificado. Windows avisa sobre el instalador descargado.
- **Una ayuda sin conexión**, legible sin navegador ni red. El menú Help abre este sitio; About funciona sin conexión. Más abajo, los detalles.

### En otros ámbitos

- **Editar diagramas.** Diagrams abre un archivo `.vsdx` y lo muestra. El conversor no sabe escribir ningún formato de Visio: no hay nada que guardar ni una plantilla en blanco con la que empezar.
- **Editar PDF.** El proyecto original tiene un editor de PDF; los componentes que instala Libera Suite todavía no lo incluyen, porque nada lo abriría.
- **Colaboración, almacenamiento en la nube, cuentas, telemetría.** Nada de esto está hecho ni en marcha. [La hoja de ruta](/en/develop/roadmap/), en inglés, describe cómo sería cada uno si llegara. [Qué sale de tu máquina](../index.md#what-leaves-your-machine) recoge todo el uso de la red por parte de la aplicación.

## Notas sobre algunas carencias

### Ayuda

Hay un menú **Ayuda**, en todas las plataformas, que abre este sitio en tu navegador. No hay ayuda *dentro* de la aplicación, donde se podría leer sin conexión. El proyecto original incluye un manual completo. Libera Suite no lo incluye: documenta ONLYOFFICE y ocupa 84 MB en ocho idiomas. La ayuda sin conexión llegará cuando nuestra propia documentación sea lo bastante amplia como para distribuirla.

### Corrección ortográfica

Libera Suite incluye diccionarios de **inglés (de Estados Unidos y del Reino Unido), francés, alemán, español, italiano y neerlandés**: 12 MB con sus licencias, elegidos porque el conjunto completo ocupa 327. Añadir un idioma requiere una línea en `build/payload/dictionaries.txt` y volver a compilar los componentes.

Un idioma sin diccionario no es un error: sus palabras simplemente se consideran correctas, como en la aplicación de escritorio del proyecto original. Las palabras añadidas con *Add to dictionary* se conservan, para todos los documentos y todos los idiomas.

Cómo fijar el idioma de un documento se explica en [Trabajar con documentos](../guide/documents.md#spell-checking).

### Tu nombre en los documentos

Los cambios registrados y los comentarios se atribuyen a una persona, cuyo nombre se escribe en el archivo guardado. Libera Suite lo toma de tu cuenta: el nombre completo con el que macOS te conoce, el nombre para mostrar de tu cuenta de Windows o el campo «nombre completo» de tu cuenta Unix en Linux. Se puede poner otro en el archivo de configuración; todavía no hay una opción de menú para ello. [Trabajar con documentos](../guide/documents.md#your-name-in-documents) da los detalles.

### Fuentes

Libera Suite incluye un conjunto básico de fuentes: Liberation, Carlito, Caladea, Open Sans y algunas más, suficientes para mostrar fielmente documentos corrientes, en 7 MB. El conjunto completo ocupa 248 MB. Un documento que pide una fuente que no está en este conjunto usa la instalada en tu máquina, en pantalla y en su PDF, y solo recibe una fuente sustituta si tu máquina tampoco la tiene. Calibri, Cambria, Arial, Times New Roman y Courier New son la excepción: si tu máquina no las tiene, un documento recibe Carlito, Caladea o Liberation, que tienen los mismos anchos, y sus páginas se cortan en los mismos puntos que en Word, sean cuales sean las demás fuentes instaladas. Libera Suite hace la lista de tus fuentes en el primer arranque, y de nuevo en segundo plano cada vez que instalas o quitas una; las ventanas que abras después usan la lista nueva. Está por decidir si se amplía el conjunto, sobre todo para el chino, el japonés y el coreano.

### Fidelidad de la presentación

El motor de maquetación viene del proyecto original y está maduro. Si ves algo mal, lo más probable es que la causa sea nuestro empaquetado (una fuente o un recurso que falta). Por eso esos informes son especialmente útiles: envíanos [tus comentarios](../feedback.md) con el archivo.
