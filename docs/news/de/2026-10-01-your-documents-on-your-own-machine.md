---
date: 2026-10-01
description: Libera Suite, eine freie und kostenlose Office-Suite für Linux, Windows und macOS, geht in die öffentliche Beta. Sie öffnet und speichert die Formate von Microsoft Office und OpenDocument, ohne Konto und ohne Onlinedienst.
---

# Libera Suite geht in die öffentliche Beta

**Libera Suite** ist eine freie und kostenlose Office-Suite für Linux, Windows und macOS. Sie umfasst eine Textverarbeitung, eine Tabellenkalkulation, ein Präsentationsprogramm und einen Betrachter für Visio-Dateien. Sie läuft auf Ihrem Computer, ohne Konto, ohne Onlinedienst und ohne Telemetrie. Sie öffnet und speichert die Formate von Microsoft Office und OpenDocument. Ihre öffentliche Beta beginnt heute.

[Libera Suite installieren](../main/install.md){ .md-button .md-button--primary }

![Libera Words mit einem geöffneten Dokument: die Symbolleiste des Editors im Violett von Libera Words, darunter eine gesetzte Seite.](../assets/words.png)

## Vier Anwendungen

| | | |
| :--- | :--- | :--- |
| **Libera Words** | Textdokumente | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | Tabellen | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | Präsentationen | `.pptx` `.odp` |
| **Libera Diagrams** | Ein Betrachter für Visio-Zeichnungen | `.vsdx` |

Eine Word-, Excel- oder PowerPoint-Datei öffnet sich mit ihrem Layout: Schriften, Bilder, Tabellen und nachverfolgte Änderungen inbegriffen. Beim Speichern entsteht eine Datei im selben Format, die Microsoft Office und LibreOffice öffnen wie jede andere.

Die vier Anwendungen teilen sich ein Startfenster mit den zuletzt verwendeten Dokumenten, Rechtschreibprüfung in fünf Sprachen, PDF-Export, Drucken und die Wiederherstellung Ihrer Arbeit nach einem Absturz.

## Frei und kostenlos

Libera Suite verlangt weder Lizenz noch Abonnement. Sie können sie auf so vielen Computern installieren, wie Sie möchten, und so lange behalten, wie Sie möchten. Sie hängt von keinem Server von uns ab, um zu funktionieren.

Sie ist freie Software: Jeder darf ihren Quellcode lesen, ändern und weitergeben. Die Anwendung steht unter der Apache License 2.0, die Komponenten von Euro-Office unter der GNU AGPL v3. [Lizenz und Namensnennung](../licence.md) erklärt, wie Sie den genauen Quellcode jeder Version erhalten.

## Ihre Dokumente bleiben auf Ihrem Computer

Libera Suite liest und schreibt Ihre Dokumente auf Ihrer Festplatte und schickt sie nirgendwohin. Sie übermittelt uns keine Informationen über Sie, Ihre Dokumente oder Ihre Nutzung.

Online geht sie, um bei der Installation die Komponenten von Euro-Office herunterzuladen. [Die Dokumentation führt](../index.md#what-leaves-your-machine) jede ihrer Verbindungen auf, und der Quellcode erlaubt es, das nachzuprüfen.

## So installieren Sie sie

- **Linux** (x86_64 und arm64): ein Befehl im Terminal, der ein Flatpak-Paket installiert, wenn Flatpak vorhanden ist.
- **macOS** (Apple Silicon): ein Befehl im Terminal, mit oder ohne Homebrew.
- **Windows** 10 und 11 (x64): ein Installationsprogramm, ohne Administratorrechte.

Die [Installationsseite](../main/install.md) nennt die Befehle.

## Die Grenzen der Beta

Jedes Dokument hat sein eigenes Fenster, ohne Tabs. Noch hindert nichts zwei Fenster daran, dasselbe Dokument zu bearbeiten: Das zuletzt speichernde überschreibt die Arbeit des anderen. Diagrams liest Visio-Dateien, kann sie aber nicht speichern. Das Windows-Installationsprogramm ist noch nicht signiert, daher zeigt Windows beim Öffnen eine Warnung. [Die Statusseite](../main/status.md) enthält die vollständige Liste und wird aktuell gehalten.

## Ihre Rückmeldungen

Die Layout-Engine ist bewährt: Sieht ein Dokument in Libera Suite falsch aus, liegt die Ursache meist in unserer Paketierung, bei einer fehlenden Schrift oder Ressource. Solche Fehler sind schnell behoben, sobald wir sie sehen. Die nützlichste Rückmeldung ist deshalb ein Dokument, das falsch aussieht, als Anhang Ihrer Nachricht.

Wenn Sie Software für eine Organisation auswählen, sagen Sie uns, welche Funktionen sie für einen Umstieg auf Libera Suite bräuchte.

[Rückmeldung](../feedback.md) erklärt, wie Sie uns schreiben.

## Wer sie entwickelt

Libera Suite wird von [Abilian](https://abilian.com) entwickelt, einem französischen Unternehmen für freie Software. Sie baut auf den Komponenten von [Euro-Office](https://github.com/Euro-Office) auf, einem Fork von [ONLYOFFICE](https://www.onlyoffice.com/), der Software von Ascensio System SIA. Diese Komponenten liefern die Dokument-Engine und die Unterstützung der Formate. Abilian hat die Desktop-Anwendung geschrieben, in der sie laufen: die Fenster, die Menüs, das Öffnen und Speichern von Dateien und die Paketierung.

Wir bauen die Komponenten von Euro-Office aus ihrem Quellcode, auf festgelegten Revisionen. Die Korrekturen, die wir darauf anwenden, sind [veröffentlicht und erklärt](/en/develop/patches/).

*Abilian*

---

Microsoft, Word, Excel, PowerPoint, Visio und Windows sind Marken der Microsoft-Unternehmensgruppe. LibreOffice ist eine Marke von The Document Foundation. ONLYOFFICE ist eine Marke von Ascensio System SIA. Andere Namen sind Marken ihrer jeweiligen Inhaber. Libera Suite ist mit keinem von ihnen verbunden und wird von keinem von ihnen unterstützt.
