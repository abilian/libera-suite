# Über Libera Suite

Libera Suite wird von [Abilian](https://abilian.com) entwickelt, einem französischen Unternehmen, das freie Software macht. Stefane Fermigier leitet das Projekt.

Der Quellcode ist öffentlich, auf [github.com/abilian/libera-suite](https://github.com/abilian/libera-suite). Die Host-Anwendung, der Teil, den wir geschrieben haben, steht unter der Apache License 2.0; die Editoren stehen unter der GNU AGPL v3. [Lizenz und Namensnennung](../licence.md) erläutert die Einzelheiten, auch, wie Sie den genauen Quellcode jeder Version erhalten.

## Danksagung

Libera Suite baut auf der Arbeit anderer auf. Das meiste von dem, was Sie beim Bearbeiten eines Dokuments sehen, stammt von ihnen.

### Die Editoren

Libera Suite enthält Komponenten von [**Euro-Office**](https://github.com/Euro-Office), selbst ein Fork von **ONLYOFFICE**, entwickelt von Ascensio System SIA. Die Dokument-Engine, die vier Editoren, der Formatkonverter und die Unterstützung jedes Formats stammen von dort, verändert durch [eine kurze Patch-Reihe](/en/develop/patches/) von uns. Das Schwierigste an einer Office-Suite sind zwanzig Jahre, in denen man lernt, die `.docx`-Dokumente anderer richtig zu lesen. Dieser Teil ist ihrer.

Von derselben Organisation stammen die leeren Vorlagen, mit denen jedes neue Dokument beginnt, die Wörterbücher der Rechtschreibprüfung (Englisch, Französisch, Deutsch, Spanisch und Italienisch) und die Schriften, die Libera Suite mitliefert: Liberation, Carlito, Caladea, Open Sans und Asana Math, neben anderen, jede unter ihrer eigenen freien Lizenz.

Unter den Editoren liegen viele weitere Bibliotheken, V8 und Boost als die größten, die der Build von Euro-Office mitbringt.

### Die Anwendung

- [**Python**](https://www.python.org), in dem die gesamte Host-Anwendung geschrieben ist.
- [**pywebview**](https://pywebview.flowrl.com), das auf jeder Plattform eine Web-Ansicht in ein natives Fenster setzt. Unter macOS geschieht das über [**PyObjC**](https://pyobjc.readthedocs.io), unter Linux über [**PyGObject**](https://pygobject.gnome.org) und WebKitGTK.
- Die Web-Engines, die die Editoren darstellen: **WebKit** unter macOS und Linux; Microsofts **WebView2** unter Windows.
- Unter Linux die [**GNOME-Laufzeitumgebung**](https://flathub.org/apps/org.gnome.Platform), auf der das Flatpak läuft, sowie [**Flatpak**](https://flatpak.org) selbst.
- Unter Windows [**PyInstaller**](https://pyinstaller.org), das die Anwendung mit ihrem eigenen Python verpackt; [**Inno Setup**](https://jrsoftware.org/isinfo.php) baut das Installationsprogramm.

### Diese Website

Gebaut mit [**Zensical**](https://zensical.org). Die Schriften, [**Inter**](https://rsms.me/inter/) und [**JetBrains Mono**](https://www.jetbrains.com/lp/mono/), stehen unter der SIL Open Font License und werden von dieser Website selbst ausgeliefert.

## Kontakt

Für einen Fehler, eine Frage oder einen Vorschlag siehe [Rückmeldung](../feedback.md).
