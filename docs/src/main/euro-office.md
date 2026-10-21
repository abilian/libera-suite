# Libera Suite and Euro-Office Desktop

**The same engine, a different shell.**

Libera Suite and Euro-Office Desktop Editors use the same components. `sdkjs`, `web-apps` and the `x2t` converter come from the Euro-Office repositories, at the revisions of their published releases. A document therefore displays, imports and exports the same way in both, our fixes apart. What differs is mostly the application around them.

**Euro-Office Desktop Editors** keeps the architecture of ONLYOFFICE Desktop: an embedded Chromium browser (CEF) and a Qt interface, in C++ (the `desktop-sdk` and `desktop-apps` repositories).

**Libera Suite** replaces that layer with a few thousand lines of Python and JavaScript. The components are displayed in the web engine the system already has: WebKit on macOS and Linux, WebView2 on Windows. They cannot tell the difference. They talk to the same native interface (`AscDesktopEditor`), which we rewrote.

That choice has several consequences.

- **Size.** For version 9.3.5-2, Euro-Office's macOS `.dmg` is 926 MB and its standalone Windows installer 616 MB. Libera Suite downloads about 90 MB of components, plus an application of a few megabytes.
- **Installation.** `pip` or `pipx`, Homebrew (macOS and Linux), Flatpak, a Windows installer, or one `curl | sh` line.
- **Command line.** `libera --convert *.docx -t pdf` converts documents without opening a window.
- **Fixes.** We build everything from Euro-Office's sources, with a [published patch queue](../develop/patches.md). It is mostly about the converter, for OpenDocument and CSV files. Euro-Office's releases do not include those fixes today.
- **Licence.** The application is under Apache 2.0, and the components stay under the AGPL.

Euro-Office Desktop has a few features today that Libera Suite does not have yet: tabs on Linux and Windows, PDF editing and forms, digital signatures, and connection to a Nextcloud, ownCloud or Seafile server for co-editing. [The roadmap](../develop/roadmap.md) says when they arrive.

**In short:** to get all of ONLYOFFICE Desktop in a European project, Euro-Office Desktop is the right choice. Libera Suite makes a different bet: a lighter application, made of short code that a small team can read and maintain, which adds features without touching the editing engine.
