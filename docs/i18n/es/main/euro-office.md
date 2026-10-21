# Libera Suite y Euro-Office Desktop

**El mismo motor, otra envoltura.**

Libera Suite y Euro-Office Desktop Editors usan los mismos componentes. `sdkjs`, `web-apps` y el conversor `x2t` vienen de los repositorios de Euro-Office, en las revisiones de sus versiones publicadas. Por eso un documento se muestra, se importa y se exporta igual en los dos, salvo nuestras correcciones. Lo que cambia es sobre todo la aplicación que los rodea.

**Euro-Office Desktop Editors** mantiene la arquitectura de ONLYOFFICE Desktop: un navegador Chromium integrado (CEF) y una interfaz Qt, en C++ (los repositorios `desktop-sdk` y `desktop-apps`).

**Libera Suite** sustituye esa capa por unos pocos miles de líneas de Python y JavaScript. Los componentes se muestran en el motor web que el sistema ya tiene: WebKit en macOS y Linux, WebView2 en Windows. No notan la diferencia. Hablan con la misma interfaz nativa (`AscDesktopEditor`), que hemos reescrito.

Esa elección tiene varias consecuencias.

- **Tamaño.** En la versión 9.3.5-2, el `.dmg` de Euro-Office para macOS ocupa 926 MB y su instalador autónomo para Windows 616 MB. Libera Suite descarga unos 90 MB de componentes, más una aplicación de pocos megabytes.
- **Instalación.** `pip` o `pipx`, Homebrew (macOS y Linux), Flatpak, un instalador para Windows o una línea `curl | sh`.
- **Línea de comandos.** `libera --convert *.docx -t pdf` convierte documentos sin abrir ninguna ventana.
- **Correcciones.** Compilamos todo a partir de las fuentes de Euro-Office, con una [serie de parches publicada](/en/develop/patches/). Se centra en el conversor, para los archivos OpenDocument y CSV. Las versiones de Euro-Office no incluyen hoy esas correcciones.
- **Licencia.** La aplicación tiene licencia Apache 2.0 y los componentes siguen bajo AGPL.

Euro-Office Desktop tiene hoy algunas funciones que Libera Suite todavía no tiene: las pestañas en Linux y Windows, la edición de PDF y los formularios, las firmas digitales y la conexión a un servidor Nextcloud, ownCloud o Seafile para la coedición. [La hoja de ruta](/en/develop/roadmap/) indica cuándo llegan.

**En resumen:** para tener todo ONLYOFFICE Desktop en un proyecto europeo, Euro-Office Desktop es la elección adecuada. Libera Suite apuesta por otra cosa: una aplicación más ligera, hecha de un código breve que un equipo pequeño puede leer y mantener, y que añade funciones sin tocar el motor de edición.
