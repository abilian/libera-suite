---
date: 2026-10-01
description: Libera Suite, una suite ofimática libre y gratuita para Linux, Windows y macOS, entra en beta pública. Abre y guarda los formatos de Microsoft Office y OpenDocument, sin cuenta y sin servicios en línea.
---

# Libera Suite entra en beta pública

**Libera Suite** es una suite ofimática libre y gratuita para Linux, Windows y macOS. Incluye un procesador de textos, una hoja de cálculo, un programa de presentaciones y un visor de archivos de Visio. Funciona en tu ordenador, sin cuenta, sin servicios en línea y sin telemetría. Abre y guarda los formatos de Microsoft Office y OpenDocument. Su beta pública empieza hoy.

[Instalar Libera Suite](../main/install.md){ .md-button .md-button--primary }

![Libera Words con un documento abierto: la barra de herramientas del editor en el morado de Libera Words y, debajo, una página maquetada.](../assets/words.png)

## Cuatro aplicaciones

| | | |
| :--- | :--- | :--- |
| **Libera Words** | Documentos de texto | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | Hojas de cálculo | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | Presentaciones | `.pptx` `.odp` |
| **Libera Diagrams** | Un visor de dibujos de Visio | `.vsdx` |

Un archivo de Word, Excel o PowerPoint se abre con su maquetación: fuentes, imágenes, tablas y control de cambios incluidos. Al guardar se obtiene un archivo en el mismo formato, que Microsoft Office y LibreOffice abren como cualquier otro.

Las cuatro aplicaciones comparten una ventana de inicio con los documentos recientes, corrección ortográfica en cinco idiomas, exportación a PDF, impresión y recuperación del trabajo tras un cierre inesperado.

## Libre y gratuita

Libera Suite no pide licencia ni suscripción. Puedes instalarla en tantos ordenadores como quieras y conservarla todo el tiempo que quieras. Para funcionar no depende de ningún servidor nuestro.

Es software libre: cualquiera puede leer su código fuente, modificarlo y compartirlo. La aplicación tiene licencia Apache 2.0 y los componentes de Euro-Office, GNU AGPL v3. [Licencia y atribución](../licence.md) explica cómo obtener el código fuente exacto de cada versión.

## Tus documentos se quedan en tu ordenador

Libera Suite lee y escribe tus documentos en tu disco y no los envía a ninguna parte. No nos transmite ninguna información sobre ti, tus documentos o tu forma de usarla.

Se conecta para descargar los componentes de Euro-Office durante la instalación. [La documentación enumera](../index.md#what-leaves-your-machine) cada una de sus conexiones, y el código fuente permite comprobarlo.

## Cómo instalarla

- **Linux** (x86_64 y arm64): un comando en el terminal, que instala un paquete Flatpak cuando Flatpak está presente.
- **macOS** (Apple Silicon): un comando en el terminal, con o sin Homebrew.
- **Windows** 10 y 11 (x64): un instalador, sin derechos de administrador.

La [página de instalación](../main/install.md) da los comandos.

## Los límites de la beta

Cada documento tiene su propia ventana, sin pestañas. Todavía nada impide que dos ventanas editen el mismo documento: la última en guardar sobrescribe el trabajo de la otra. Diagrams lee archivos de Visio pero no puede guardarlos. El instalador de Windows aún no está firmado, así que Windows muestra una advertencia al abrirlo. [La página de estado](../main/status.md) da la lista completa y se mantiene al día.

## Tus comentarios

El motor de maquetación está probado: cuando un documento se ve mal en Libera Suite, la causa suele estar en nuestro empaquetado, en una fuente o un recurso que falta. Son defectos que se corrigen rápido, siempre que los veamos. El comentario más útil es, por tanto, un documento que se ve mal, adjunto a tu mensaje.

Si eliges el software de una organización, dinos qué funciones necesitaría para adoptar Libera Suite.

[Comentarios](../feedback.md) explica cómo escribirnos.

## Quién la desarrolla

Libera Suite la desarrolla [Abilian](https://abilian.com), una empresa francesa de software libre. Está construida sobre los componentes de [Euro-Office](https://github.com/Euro-Office), un fork de [ONLYOFFICE](https://www.onlyoffice.com/), el software de Ascensio System SIA. Esos componentes aportan el motor de documentos y la compatibilidad con los formatos. Abilian escribió la aplicación de escritorio que los aloja: las ventanas, los menús, la apertura y el guardado de archivos y el empaquetado.

Compilamos los componentes de Euro-Office desde su código fuente, en revisiones fijadas. Las correcciones que les aplicamos están [publicadas y explicadas](/en/develop/patches/).

*Abilian*

---

Microsoft, Word, Excel, PowerPoint, Visio y Windows son marcas comerciales del grupo de empresas Microsoft. LibreOffice es una marca de The Document Foundation. ONLYOFFICE es una marca de Ascensio System SIA. Los demás nombres son marcas de sus respectivos propietarios. Libera Suite no está afiliada a ninguno de ellos ni cuenta con su respaldo.
