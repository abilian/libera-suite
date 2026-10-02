# Acerca de

Libera Suite la desarrolla [Abilian](https://abilian.com), una empresa francesa que hace software libre. Stefane Fermigier dirige el proyecto.

Su código fuente es público, en [github.com/abilian/libera-suite](https://github.com/abilian/libera-suite). La aplicación anfitriona, la parte que hemos escrito nosotros, tiene licencia Apache 2.0; los editores, licencia GNU AGPL v3. [Licencia y atribución](../licence.md) da los detalles, incluido cómo obtener el código fuente exacto de cada versión.

## Agradecimientos

Libera Suite se apoya en el trabajo de otras personas. Casi todo lo que ves al editar un documento es suyo.

### Los editores

Libera Suite incluye componentes de [**Euro-Office**](https://github.com/Euro-Office), a su vez un fork de **ONLYOFFICE**, desarrollado por Ascensio System SIA. El motor de documentos, los cuatro editores, el conversor de formatos y la compatibilidad con cada formato vienen de ahí, modificados por [una breve serie de parches](/en/develop/patches/) nuestra. Lo más difícil de una suite ofimática son veinte años aprendiendo a leer bien los documentos `.docx` de los demás. Esa parte es suya.

De la misma organización vienen las plantillas en blanco de las que parte cada documento nuevo, los diccionarios de la corrección ortográfica (inglés, francés, alemán, español e italiano) y las fuentes que incluye Libera Suite: Liberation, Carlito, Caladea, Open Sans y Asana Math, entre otras, cada una con su propia licencia libre.

Bajo los editores hay muchas otras bibliotecas, V8 y Boost entre las mayores, que trae consigo la compilación de Euro-Office.

### La aplicación

- [**Python**](https://www.python.org), en el que está escrita toda la aplicación anfitriona.
- [**pywebview**](https://pywebview.flowrl.com), que coloca una vista web en una ventana nativa en cada plataforma. En macOS pasa por [**PyObjC**](https://pyobjc.readthedocs.io); en Linux, por [**PyGObject**](https://pygobject.gnome.org) y WebKitGTK.
- Los motores web que muestran los editores: **WebKit** en macOS y Linux; **WebView2** de Microsoft en Windows.
- En Linux, el [**entorno de ejecución de GNOME**](https://flathub.org/apps/org.gnome.Platform) sobre el que funciona el Flatpak, y el propio [**Flatpak**](https://flatpak.org).
- En Windows, [**PyInstaller**](https://pyinstaller.org), que empaqueta la aplicación con su propio Python; [**Inno Setup**](https://jrsoftware.org/isinfo.php) crea el instalador.

### Este sitio

Hecho con [**Zensical**](https://zensical.org). Las fuentes, [**Inter**](https://rsms.me/inter/) y [**JetBrains Mono**](https://www.jetbrains.com/lp/mono/), tienen licencia SIL Open Font License y se sirven desde este mismo sitio.

## Contacto

Para un error, una pregunta o una sugerencia, consulta [Comentarios](../feedback.md).
