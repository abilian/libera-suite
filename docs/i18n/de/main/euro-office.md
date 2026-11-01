# Libera Suite und Euro-Office Desktop

**Dieselbe Engine, eine andere Hülle.**

Libera Suite und Euro-Office Desktop Editors verwenden dieselben Komponenten. `sdkjs`, `web-apps` und der Konverter `x2t` stammen aus den Repositorys von Euro-Office, in den Revisionen ihrer veröffentlichten Versionen. Ein Dokument wird deshalb in beiden gleich angezeigt, importiert und exportiert, bis auf unsere Korrekturen. Die beiden unterscheiden sich vor allem in der Anwendung, die sie umgibt.

**Euro-Office Desktop Editors** übernimmt die Architektur von ONLYOFFICE Desktop: einen eingebetteten Chromium-Browser (CEF) und eine Qt-Oberfläche, in C++ (die Repositorys `desktop-sdk` und `desktop-apps`).

**Libera Suite** ersetzt diese Schicht durch einige tausend Zeilen Python und JavaScript. Die Komponenten erscheinen in der Web-Engine, die das System schon mitbringt: WebKit unter macOS und Linux, WebView2 unter Windows. Die Komponenten merken keinen Unterschied. Sie sprechen mit derselben nativen Schnittstelle (`AscDesktopEditor`), die wir neu geschrieben haben.

Diese Wahl hat mehrere Folgen.

- **Größe.** In Version 9.3.5-2 ist das macOS-`.dmg` von Euro-Office 926 MB groß und das eigenständige Windows-Installationsprogramm 616 MB. Libera Suite lädt etwa 90 MB Komponenten herunter, dazu eine Anwendung von wenigen Megabyte.
- **Installation.** `pip` oder `pipx`, Homebrew (macOS und Linux), Flatpak, ein Windows-Installationsprogramm oder eine Zeile `curl | sh`.
- **Kommandozeile.** `libera --convert *.docx -t pdf` konvertiert Dokumente, ohne ein Fenster zu öffnen.
- **Korrekturen.** Wir bauen alles aus den Quellen von Euro-Office, mit einer [veröffentlichten Patch-Reihe](/en/develop/patches/). Sie betrifft vor allem den Konverter, für OpenDocument- und CSV-Dateien. Die Versionen von Euro-Office enthalten diese Korrekturen heute nicht.
- **Lizenz.** Die Anwendung steht unter Apache 2.0, die Komponenten bleiben unter der AGPL.

Euro-Office Desktop hat heute einige Funktionen, die Libera Suite noch nicht hat: Tabs, PDF-Bearbeitung und Formulare, digitale Signaturen und die Verbindung zu einem Nextcloud-, ownCloud- oder Seafile-Server für gemeinsames Bearbeiten. [Die Roadmap](/en/develop/roadmap/) sagt, wann sie kommen.

**Kurz gesagt:** Wer ganz ONLYOFFICE Desktop in einem europäischen Projekt sucht, ist mit Euro-Office Desktop richtig. Libera Suite setzt auf etwas anderes: eine leichtere Anwendung aus kurzem Code, den ein kleines Team lesen und pflegen kann, und die Funktionen ergänzt, ohne die Bearbeitungs-Engine anzufassen.
