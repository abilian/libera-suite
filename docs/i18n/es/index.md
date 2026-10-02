# Libera Suite

**Libera Suite** es una suite ofimática libre y de código abierto para Windows, macOS y Linux, creada por Abilian. Escribe documentos, trabaja con hojas de cálculo y prepara presentaciones en tu propio ordenador, con tus propios archivos, sin cuenta ni servicio en la nube.

Abre y guarda los formatos de archivo de Microsoft Office y de LibreOffice, así que puedes intercambiar documentos con cualquiera, use el programa que use. Es una alternativa gratuita a Microsoft Word, Excel y PowerPoint y, como software libre, cualquiera puede leer su código fuente, modificarlo y compartirlo.

- **Libera Words**, para textos: `.docx`, `.odt`, `.rtf`, `.txt`, `.md` y otros
- **Libera Tables**, para hojas de cálculo: `.xlsx`, `.ods`, `.csv`
- **Libera Slides**, para presentaciones: `.pptx`, `.odp`
- **Libera Diagrams**, un visor de dibujos de Visio (`.vsdx`)

![Libera Words con un documento abierto: la barra de herramientas del editor en el morado de Libera Words y, debajo, una página maquetada.](assets/words.png)

[Instala Libera Suite](main/install.md){ .md-button .md-button--primary }

## En qué punto está el proyecto

Los cuatro funcionan hoy en **Windows** 10 y 11 (x64), **Linux** (x86_64 y arm64) y **macOS** (Apple Silicon). El proyecto es joven. [Qué funciona hoy](main/status.md) recoge su estado: qué está hecho, qué lo está solo en parte y qué no se ha empezado.

Para probarlo, empieza por [Instalar](main/install.md): en Linux y macOS basta un comando; Windows tiene su instalador. Para compilarlo, empieza por la [presentación para desarrolladores](/en/develop/), en inglés. En cualquier caso, [cuéntanos cómo ha ido](feedback.md).

## Por qué

La mayor parte del trabajo de una suite ofimática está en el motor de documentos, la parte que lee un `.docx` escrito por el programa de otra persona y lo maqueta como su autor quería. Ese motor ya existe como software libre y ya funciona sin conexión: los editores de Libera Suite son los de [Euro-Office](https://github.com/Euro-Office), un fork bajo AGPL de ONLYOFFICE, desarrollado por Ascensio System SIA, y se ejecutan en local con el mismo motor de documentos y la misma compatibilidad con los formatos. A ese motor le faltaba una aplicación anfitriona de escritorio, lo bastante pequeña como para que un solo equipo pudiera hacerse cargo.

Libera Suite es esa aplicación: unos pocos miles de líneas de Python y JavaScript. Todo lo demás viene del proyecto original.

## Qué sale de tu máquina {#what-leaves-your-machine}

Tus documentos, nunca.

Libera Suite no tiene **telemetría**, ni estadísticas de uso, ni informes de errores, ni cuentas: no nos envía nada sobre ti, tus documentos o tu forma de usarla. Si algún día se añadiera algo así, estaría desactivado hasta que tú lo activaras.

Sí se conecta a nuestro servidor para descargar archivos. Hoy se trata de los editores, al instalar Libera Suite y de nuevo cuando una versión nueva necesita otros nuevos. Cuando Libera Suite empiece a buscar actualizaciones, te avisará de que hay una versión nueva y te pedirá permiso antes de descargarla. Como cualquier petición web, cada una de estas descargas muestra a nuestro servidor tu dirección IP, y nada más sobre ti.

La tabla recoge cada conexión que la aplicación establece hoy, para que puedas comprobarlo. Cualquier conexión nueva, incluida la búsqueda de actualizaciones, aparecerá aquí con la versión que la introduzca.

| | |
| :--- | :--- |
| **Los editores** | Se descargan de `cdn.abilian.com` al instalar Libera Suite, y de nuevo solo cuando una versión nueva necesita otros nuevos. Cada descarga se verifica con las huellas incluidas en la aplicación. |
| **El tráfico propio del editor** | Un servidor web en `127.0.0.1`, que forma parte de la aplicación y sirve el editor a una ventana de la misma máquina. No es accesible desde ningún otro lugar. |
| **Los enlaces en los que haces clic** | La ayuda y similares se abren en *tu* navegador. Libera Suite no los descarga. |

Tus documentos se leen y se escriben en tu disco, mediante un conversor que está en tu disco. Nunca se suben, se indexan ni se examinan.

## Licencia y código fuente

Libera Suite es software libre: la aplicación anfitriona tiene licencia [Apache-2.0](licence.md); los editores que ejecuta tienen licencia AGPL v3, igual que el código de Euro-Office a partir del cual se compilan. Cada versión registra las revisiones exactas del proyecto original de las que parte y los parches que se les aplicaron: el código fuente correspondiente es siempre un commit más una serie de parches que se puede comprobar que se le aplica.

---

Microsoft, Word, Excel, PowerPoint, Visio y Windows son marcas comerciales del grupo de empresas Microsoft. LibreOffice es una marca de The Document Foundation. ONLYOFFICE es una marca de Ascensio System SIA. Los demás nombres son marcas de sus respectivos propietarios. Libera Suite no está afiliada a ninguno de ellos ni cuenta con su respaldo.
