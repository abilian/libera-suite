# Libera Suite

**Libera Suite** ist eine freie und quelloffene Office-Suite für Windows, macOS und Linux, entwickelt von Abilian. Schreiben Sie Texte, bearbeiten Sie Tabellen und erstellen Sie Präsentationen auf Ihrem eigenen Computer, mit Ihren eigenen Dateien, ohne Konto und ohne Cloud-Dienst.

Sie öffnet und speichert die Dateiformate von Microsoft Office und LibreOffice, sodass Sie Dokumente mit allen austauschen können, gleich welche Software sie verwenden. Sie ist eine kostenlose Alternative zu Microsoft Word, Excel und PowerPoint, und als freie Software darf jeder ihren Quellcode lesen, ändern und weitergeben.

- **Libera Words** für Texte: `.docx`, `.odt`, `.rtf`, `.txt`, `.md` und weitere
- **Libera Tables** für Tabellen: `.xlsx`, `.ods`, `.csv`
- **Libera Slides** für Präsentationen: `.pptx`, `.odp`
- **Libera Diagrams**, ein Betrachter für Visio-Zeichnungen (`.vsdx`)

![Libera Words mit einem geöffneten Dokument: die Symbolleiste des Editors im Violett von Libera Words, darunter eine gesetzte Seite.](assets/words.png)

[Libera Suite installieren](main/install.md){ .md-button .md-button--primary }

## Wo das Projekt steht

Alle vier laufen heute unter **Windows** 10 und 11 (x64), **Linux** (x86_64 und arm64) und **macOS** (Apple Silicon). Das Projekt ist jung. [Was heute funktioniert](main/status.md) führt den Stand auf: was gebaut ist, was halb fertig ist und was noch nicht begonnen wurde.

Zum Ausprobieren beginnen Sie mit [Installieren](main/install.md): Unter Linux und macOS genügt ein Befehl, Windows hat ein Installationsprogramm. Zum Selberbauen beginnen Sie mit der [Übersicht für Entwickler](/en/develop/), auf Englisch. In jedem Fall: [Sagen Sie uns, wie es gelaufen ist](feedback.md).

## Warum

Der größte Teil der Arbeit an einer Office-Suite steckt in der Dokument-Engine, dem Teil, der eine `.docx`-Datei aus der Software eines anderen liest und so setzt, wie ihr Verfasser sie gemeint hat. Diese Engine gibt es bereits als freie Software, und sie läuft bereits offline: Die Editoren von Libera Suite sind die von [Euro-Office](https://github.com/Euro-Office), einem AGPL-Fork von ONLYOFFICE, entwickelt von Ascensio System SIA, und laufen lokal mit derselben Dokument-Engine und derselben Unterstützung der Formate. Der Engine fehlte eine Desktop-Anwendung, die klein genug ist, damit ein einziges Team sie verantworten kann.

Libera Suite ist diese Anwendung: einige tausend Zeilen Python und JavaScript. Alles andere stammt aus dem Upstream-Projekt.

## Was Ihren Rechner verlässt {#what-leaves-your-machine}

Ihre Dokumente verlassen ihn nie.

Libera Suite hat **keine Telemetrie**, keine Nutzungsstatistik, keine Absturzberichte und keine Konten: Sie sendet uns nichts über Sie, Ihre Dokumente oder Ihre Nutzung. Sollte je etwas dieser Art hinzukommen, bleibt es ausgeschaltet, bis Sie es einschalten.

Für Downloads verbindet sie sich allerdings mit unserem Server. Heute betrifft das die Editoren, bei der Installation von Libera Suite und erneut, wenn eine neue Version neue Editoren braucht. Sobald Libera Suite nach Updates sucht, wird sie Ihnen eine neue Version melden und fragen, bevor sie sie herunterlädt. Wie jede Anfrage im Web zeigt jeder dieser Downloads unserem Server Ihre IP-Adresse, und sonst nichts über Sie.

Die Tabelle führt jede Verbindung auf, die die Anwendung heute herstellt, damit Sie die Aussage prüfen können. Jede neue, die Suche nach Updates eingeschlossen, erscheint hier mit der Version, die sie einführt.

| | |
| :--- | :--- |
| **Die Editoren** | Bei der Installation von Libera Suite von `cdn.abilian.com` heruntergeladen, und erneut nur, wenn eine neue Version neue Editoren braucht. Jeder Download wird anhand der Prüfsummen geprüft, die in der Anwendung mitgeliefert werden. |
| **Der eigene Verkehr des Editors** | Ein Webserver auf `127.0.0.1`, Teil der Anwendung, der den Editor an ein Fenster auf demselben Rechner ausliefert. Von anderswo ist er nicht erreichbar. |
| **Links, die Sie anklicken** | Die Hilfe und Ähnliches öffnen sich in *Ihrem* Browser. Libera Suite ruft sie nicht selbst ab. |

Ihre Dokumente werden auf Ihrer Festplatte gelesen und geschrieben, von einem Konverter auf Ihrer Festplatte. Sie werden nie hochgeladen, indiziert oder ausgewertet.

## Lizenz und Quellcode

Libera Suite ist freie Software: Die Host-Anwendung steht unter der [Apache-2.0](licence.md); die Editoren, die sie ausführt, stehen unter der AGPL v3, ebenso wie der Euro-Office-Code, aus dem sie gebaut werden. Jede Version hält die genauen Upstream-Revisionen fest, aus denen sie gebaut wurde, und die Patches, die darauf angewendet wurden. Der zugehörige Quellcode ist also immer ein Commit plus eine Patch-Reihe, die sich nachweislich darauf anwenden lässt.

---

Microsoft, Word, Excel, PowerPoint, Visio und Windows sind Marken der Microsoft-Unternehmensgruppe. LibreOffice ist eine Marke von The Document Foundation. ONLYOFFICE ist eine Marke von Ascensio System SIA. Andere Namen sind Marken ihrer jeweiligen Inhaber. Libera Suite ist mit keinem von ihnen verbunden und wird von keinem von ihnen unterstützt.
