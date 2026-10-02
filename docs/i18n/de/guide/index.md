# Libera Suite verwenden

Libera Suite öffnet ein Dokument in einem Fenster und lässt Sie es bearbeiten und speichern. Words, Tables und Slides arbeiten alle so; Diagrams öffnet Visio-Dokumente zum Lesen.

Beginnen Sie mit [Installieren](../main/install.md). Diese drei Seiten sind zum Lesen der Reihe nach gedacht:

1. [Installieren](../main/install.md): auf Ihren Rechner bringen, mit einem Befehl.
2. [Mit Dokumenten arbeiten](documents.md): öffnen, speichern, exportieren, drucken.
3. [Was heute funktioniert](../main/status.md): was gebaut ist, und die Probleme, die wir bereits kennen.

Jeder Editor hat seine eigene Farbe. Alles andere am Fenster ist gleich:

![Libera Tables mit einer leeren Tabelle; die Symbolleiste im Blaugrün von Libera Tables.](../assets/tables.png)

![Libera Slides mit einer Titelfolie; die Symbolleiste im Gold von Libera Slides.](../assets/slides.png)

## Wie es aufgebaut ist

Libera Suite besteht aus zwei Teilen, die getrennt ankommen.

**Die Anwendung** ist ein kleines Python-Paket von einigen hundert Kilobyte: das Fenster, die Befehlszeile und die Host-Anwendung, mit der der Editor spricht.

**Die Editoren** sind alles andere: die Dokument-Engine, die Editoren selbst, die Schriften. Die Anwendung nennt das den *Payload*. Er ist komprimiert etwa 110 MB groß unter macOS und 120 MB unter Linux. Sie laden oder installieren ihn einmal; das Python-Paket enthält ihn nicht.

Beide haben getrennte Versionsnummern. Die Anwendung prüft, ob die Editoren, die sie findet, die erwarteten sind. Eine Korrektur an der Anwendung bedeutet deshalb nicht, die Editoren erneut herunterzuladen.

Das Windows-Installationsprogramm und das Linux-Flatpak enthalten beide Teile. Alle anderen Installationswege richten zuerst die Anwendung ein und laden dann einmal die Editoren herunter.

## Was es nicht ist

Libera Suite spricht mit keinem Server, braucht kein Konto und lädt Ihre Dokumente nie hoch. Der Editor läuft als lokaler Webinhalt, der über `127.0.0.1` an ein Fenster auf Ihrem eigenen Rechner ausgeliefert wird. Es gibt keine Zusammenarbeit, keinen Cloud-Speicher und keine Telemetrie, weil nichts davon gebaut ist.
