# About

Libera Suite is made by [Abilian](https://abilian.com), a French company that builds free software. Stefane Fermigier leads the project.

Its source is public at [github.com/abilian/libera-suite](https://github.com/abilian/libera-suite). The host, the part we wrote, is under the Apache License 2.0; the editors are under the GNU AGPL v3. [Licence and attribution](../licence.md) has the detail, including how to get the exact source of any release.

## Credits

Libera Suite stands on other people's work. Most of what you see when you edit a document is theirs.

### The editors

Libera Suite includes components from [**Euro-Office**](https://github.com/Euro-Office), itself a fork of **ONLYOFFICE**, developed by Ascensio System SIA. The document engine, the four editors, the format converter and the support for each format all come from there, modified by [a short patch queue](../develop/patches.md) of our own. An office suite's hard part is twenty years of reading other people's `.docx` documents correctly, and that part is theirs.

From the same organisation come the blanks every new document starts from, the spell-check dictionaries (English, French, German, Spanish and Italian) and the fonts Libera Suite ships: Liberation, Carlito, Caladea, Open Sans and Asana Math, among others, each under its own free licence.

Underneath the editors sit many more libraries, V8 and Boost among the largest, which the Euro-Office build brings with it.

### The application

- [**Python**](https://www.python.org), which the whole host is written in.
- [**pywebview**](https://pywebview.flowrl.com), which puts a web view in a native window on every platform. On macOS it goes through [**PyObjC**](https://pyobjc.readthedocs.io); on Linux through [**PyGObject**](https://pygobject.gnome.org) and WebKitGTK.
- The web engines that draw the editors: **WebKit** on macOS and Linux, and Microsoft **WebView2** on Windows.
- On Linux, the [**GNOME runtime**](https://flathub.org/apps/org.gnome.Platform) that the Flatpak runs on, and [**Flatpak**](https://flatpak.org) itself.
- On Windows, [**PyInstaller**](https://pyinstaller.org), which packages the application with its own Python, and [**Inno Setup**](https://jrsoftware.org/isinfo.php), which builds the installer.

### This site

Built with [**Zensical**](https://zensical.org). Its fonts, [**Inter**](https://rsms.me/inter/) and [**JetBrains Mono**](https://www.jetbrains.com/lp/mono/), are under the SIL Open Font License and served from this site itself.

## Contact

For a bug, a question or a suggestion, see [Feedback](../feedback.md).
