---
date: 2026-10-01
description: Libera Suite, eine freie und kostenlose Office-Suite für Windows, macOS und Linux, ist als Beta erschienen. Sie öffnet Word-, Excel- und PowerPoint-Dateien, braucht kein Konto und lässt Ihre Dokumente auf Ihrem eigenen Computer.
---

# Libera Suite: Ihre Dokumente, auf Ihrem eigenen Rechner

Heute erscheint die Beta von **Libera Suite**, einer freien und kostenlosen Office-Suite für Windows, macOS und Linux. Schreiben Sie Briefe und Berichte, führen Sie Ihre Zahlen in einer Tabelle, bereiten Sie eine Präsentation vor, alles auf Ihrem eigenen Computer, mit Ihren eigenen Dateien. Sie brauchen kein Konto und zahlen kein Abonnement.

[Libera Suite installieren](../main/install.md){ .md-button .md-button--primary }

![Libera Words mit einem geöffneten Dokument: die Symbolleiste des Editors im Violett von Libera Words, darunter eine gesetzte Seite.](../assets/words.png)

## Sie öffnet, was man Ihnen schickt

Alle schicken `.docx`. Libera Suite öffnet es, ebenso die `.xlsx`- und `.pptx`-Dateien, die dazugehören, und setzt sie so, wie ihre Verfasser sie gesehen haben: mit Schriften, Bildern, Tabellen und nachverfolgten Änderungen. Beim Speichern erhalten Sie eine Datei im selben Format, die Ihre Kollegen in Microsoft Office oder LibreOffice öffnen wie jede andere.

Das verdanken Sie einer Dokument-Engine, die seit zwanzig Jahren die Dateien anderer Leute vorgesetzt bekommt. Libera Suite lässt diese Engine auf Ihrem Computer laufen.

| | | |
| :--- | :--- | :--- |
| **Libera Words** | Textdokumente | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | Tabellen | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | Präsentationen | `.pptx` `.odp` |
| **Libera Diagrams** | Ein Betrachter für Visio-Zeichnungen | `.vsdx` |

Dazu kommt der Rest einer Office-Suite: ein Startfenster mit Ihren zuletzt geöffneten Dokumenten, Rechtschreibprüfung in fünf Sprachen, PDF-Export, Drucken und eine Wiederherstellung, die Ihnen Ihre Arbeit zurückgibt, wenn der Computer mittendrin ausfällt.

## Kostenlos, und für immer Ihre

Keine Lizenzgebühr, keine monatliche Rechnung. Installieren Sie sie auf so vielen Computern, wie Sie möchten, und behalten Sie sie, so lange Sie möchten. Kein Server muss bezahlt bleiben, damit sie weiter funktioniert, und niemand kann sie aus der Ferne abschalten.

Libera Suite ist freie Software: Jeder darf ihren Quellcode lesen, ändern und weitergeben. Die Anwendung steht unter der Apache License 2.0, die Editoren unter der GNU AGPL v3. [Lizenz und Namensnennung](../licence.md) erklärt, wie Sie den genauen Quellcode jeder Version erhalten.

## Ihre Dokumente bleiben auf Ihrem Computer

Libera Suite liest und schreibt Ihre Dokumente auf Ihrer Festplatte, mit Software auf Ihrer Festplatte, und lädt sie nie hoch. Hinter ihr stehen weder Konto noch Cloud, und sie hat keine Telemetrie, keine Nutzungsstatistik und keine Absturzberichte: Sie sendet uns nichts über Sie, Ihre Dokumente oder Ihre Nutzung.

Online geht sie, um bei der Installation ihre Editoren herunterzuladen. [Die Dokumentation führt](../index.md#what-leaves-your-machine) jede ihrer Verbindungen auf, und der Quellcode ist öffentlich: Sie können es nachprüfen.

## Eine Beta, mit offen gelegten Lücken

Libera Suite läuft unter **Windows 10 und 11 (x64)**, **macOS (Apple Silicon)** und **Linux (x86_64 und arm64)**. Windows bekommt ein Installationsprogramm, Linux eine einzige Flatpak-Datei mit den Editoren darin und macOS einen Befehl im Terminal.

Die bekannten Lücken sind [vollständig veröffentlicht](../main/status.md) und werden aktuell gehalten. Jedes Dokument hat sein eigenes Fenster, denn Tabs gibt es noch nicht. Nichts hindert zwei Fenster daran, dasselbe Dokument zu bearbeiten, und eines davon verliert dann seine Änderungen. Diagrams liest Visio-Dateien, kann sie aber nicht speichern. Windows warnt vor dem Installationsprogramm, bis es signiert ist.

## Sagen Sie uns, was hakt

Das Nützlichste, was Sie uns schicken können, ist **ein Dokument, das falsch aussieht, als Anhang**. Die Engine ist ausgereift: Sieht eine Datei falsch aus, liegt die Ursache weit eher bei uns, etwa eine Schrift, die wir nicht mitgeliefert haben, oder eine Ressource, die wir nicht ausgeliefert haben. So etwas beheben wir schnell, sobald jemand es uns zeigt.

Wenn Sie Software für eine Organisation auswählen, sagen Sie uns, **was sie für einen Umstieg bräuchte**. Heute lässt sich die Antwort noch am leichtesten beeinflussen.

Die [Installation](../main/install.md) dauert eine Minute, und [Rückmeldung](../feedback.md) sagt, wie Sie uns erreichen.

## Wer sie macht

Libera Suite wird von [Abilian](https://abilian.com) entwickelt, einem französischen Unternehmen, das freie Software baut. Ihre Editoren stammen von [Euro-Office](https://github.com/Euro-Office), selbst ein Fork von [ONLYOFFICE](https://www.onlyoffice.com/), entwickelt von Ascensio System SIA. Die Dokument-Engine und die Unterstützung der Formate, der schwierige Teil einer Office-Suite, sind deren Werk, und wir haben nichts davon neu geschrieben. Wir haben die Desktop-Anwendung darum herum gebaut: die Fenster, die Menüs, das Öffnen und Speichern und die Pakete.

Die Engine bleibt die des Upstream-Projekts, aus dem Quellcode gebaut, auf genaue Revisionen festgelegt, mit [einer kurzen Patch-Reihe](/en/develop/patches/) von uns. Der Teil, den wir pflegen, ist klein, und ein kleines Team kann sich langfristig darauf verpflichten.

*Abilian*

---

Microsoft, Word, Excel, PowerPoint, Visio und Windows sind Marken der Microsoft-Unternehmensgruppe. LibreOffice ist eine Marke von The Document Foundation. ONLYOFFICE ist eine Marke von Ascensio System SIA. Andere Namen sind Marken ihrer jeweiligen Inhaber. Libera Suite ist mit keinem von ihnen verbunden und wird von keinem von ihnen unterstützt.
