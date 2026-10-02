---
date: 2026-10-01
description: Libera Suite, una suite ofimática libre y gratuita para Windows, macOS y Linux, está en beta. Abre archivos de Word, Excel y PowerPoint, no pide ninguna cuenta y mantiene tus documentos en tu propio ordenador.
---

# Libera Suite: tus documentos, en tu propia máquina

Hoy abrimos la beta de **Libera Suite**, una suite ofimática libre y gratuita para Windows, macOS y Linux. Escribe cartas e informes, lleva tus cuentas en una hoja de cálculo, prepara una presentación, todo en tu propio ordenador, con tus propios archivos. Sin cuenta que crear y sin suscripción que pagar.

[Instala Libera Suite](../main/install.md){ .md-button .md-button--primary }

![Libera Words con un documento abierto: la barra de herramientas del editor en el morado de Libera Words y, debajo, una página maquetada.](../assets/words.png)

## Abre lo que te envían

Todo el mundo envía `.docx`. Libera Suite los abre, junto con los `.xlsx` y los `.pptx` que los acompañan, y los maqueta tal como los veían sus autores: fuentes, imágenes, tablas y control de cambios incluidos. Al guardar, obtienes un archivo en el mismo formato, que tus compañeros abren en Microsoft Office o en LibreOffice como cualquier otro.

El mérito es de un motor de documentos que lleva veinte años recibiendo los archivos de los demás. Libera Suite ejecuta ese motor en tu ordenador.

| | | |
| :--- | :--- | :--- |
| **Libera Words** | Documentos de texto | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | Hojas de cálculo | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | Presentaciones | `.pptx` `.odp` |
| **Libera Diagrams** | Un visor de dibujos de Visio | `.vsdx` |

También tienes el resto de una suite ofimática: una ventana de inicio con tus documentos recientes, corrección ortográfica en cinco idiomas, exportación a PDF, impresión y una recuperación que te devuelve tu trabajo si el ordenador se detiene a mitad.

## Gratuita, y tuya para siempre

Sin licencia que pagar y sin factura mensual. Instálala en todos los ordenadores que quieras y consérvala todo el tiempo que quieras. Ningún servidor tiene que seguir pagado para que siga funcionando, y nadie puede apagarla a distancia.

Libera Suite es software libre: cualquiera puede leer su código fuente, modificarlo y compartirlo. La aplicación tiene licencia Apache 2.0 y los editores, GNU AGPL v3. [Licencia y atribución](../licence.md) explica cómo obtener el código fuente exacto de cada versión.

## Tus documentos se quedan en tu ordenador

Libera Suite lee y escribe tus documentos en tu disco, con software que está en tu disco, y nunca los sube a ninguna parte. Detrás no hay cuenta ni nube, ni telemetría, ni estadísticas de uso, ni informes de errores: no nos envía nada sobre ti, tus documentos o tu forma de usarla.

Se conecta a internet para descargar sus editores al instalarla. [La documentación recoge](../index.md#what-leaves-your-machine) cada una de sus conexiones, y el código fuente es público: puedes comprobarlo.

## Una beta, con sus carencias a la vista

Libera Suite funciona en **Windows 10 y 11 (x64)**, **macOS (Apple Silicon)** y **Linux (x86_64 y arm64)**. Windows tiene su instalador, Linux un único archivo Flatpak con los editores dentro, y macOS un comando en el terminal.

Las carencias conocidas están [publicadas al completo](../main/status.md) y se mantienen al día. Cada documento tiene su propia ventana, porque todavía no hay pestañas. Nada impide que dos ventanas editen el mismo documento, y una de ellas perderá sus cambios. Diagrams lee archivos de Visio pero no puede guardarlos. Windows desconfía del instalador mientras no esté firmado.

## Cuéntanos qué falla

Lo más útil que puedes enviarnos es **un documento que se ve mal, adjunto**. El motor está maduro: cuando un archivo se ve mal, la causa está mucho más probablemente de nuestro lado, una fuente que no incluimos, un recurso que no servimos. Lo corregimos rápido, en cuanto alguien nos enseña un caso.

Si eliges el software de una organización, cuéntanos **qué necesitaría** para cambiar. Hoy la respuesta todavía es fácil de orientar.

La [instalación](../main/install.md) lleva un minuto, y [Comentarios](../feedback.md) explica cómo contactarnos.

## Quién la hace

Libera Suite la desarrolla [Abilian](https://abilian.com), una empresa francesa que hace software libre. Sus editores vienen de [Euro-Office](https://github.com/Euro-Office), a su vez un fork de [ONLYOFFICE](https://www.onlyoffice.com/), desarrollado por Ascensio System SIA. El motor de documentos y la compatibilidad con los formatos, la parte difícil de una suite ofimática, son suyos, y no hemos reescrito nada de ello. Nosotros construimos alrededor la aplicación de escritorio: las ventanas, los menús, abrir y guardar, y los paquetes.

El motor sigue siendo el del proyecto original, compilado desde las fuentes en revisiones exactas, con [una breve serie de parches](/en/develop/patches/) nuestra. La parte que mantenemos es pequeña, y un equipo pequeño puede comprometerse con ella a largo plazo.

*Abilian*

---

Microsoft, Word, Excel, PowerPoint, Visio y Windows son marcas comerciales del grupo de empresas Microsoft. LibreOffice es una marca de The Document Foundation. ONLYOFFICE es una marca de Ascensio System SIA. Los demás nombres son marcas de sus respectivos propietarios. Libera Suite no está afiliada a ninguno de ellos ni cuenta con su respaldo.
