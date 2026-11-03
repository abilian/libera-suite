# Libera Suite verwenden

Libera Suite öffnet ein Dokument in einem Fenster und lässt Sie es bearbeiten und speichern. Words, Tables und Slides arbeiten alle so; Diagrams öffnet Visio-Dokumente zum Lesen.

Beginnen Sie mit [Installieren](../main/install.md). Diese drei Seiten sind zum Lesen der Reihe nach gedacht:

1. [Installieren](../main/install.md): auf Ihren Rechner bringen, mit einem Befehl.
2. [Mit Dokumenten arbeiten](documents.md): öffnen, speichern, exportieren, drucken.
3. [Was heute funktioniert](../main/status.md): was gebaut ist, und die Probleme, die wir bereits kennen.

Jede Anwendung hat ihre eigene Farbe. Alles andere am Fenster ist gleich:

![Libera Tables mit einer leeren Tabelle; die Symbolleiste im Blaugrün von Libera Tables.](../assets/tables.png)

![Libera Slides mit einer Titelfolie; die Symbolleiste im Gold von Libera Slides.](../assets/slides.png)

## Wie es aufgebaut ist

Libera Suite besteht aus zwei Teilen, die getrennt paketiert sind.

**Die Anwendung** ist ein kleines Python-Paket von einigen hundert Kilobyte: das Fenster, die Befehlszeile und die Host-Anwendung, mit der die Komponenten sprechen.

**Die Komponenten** sind alles andere: die Dokument-Engine, die Bearbeitungskomponenten, die Schriften. Die Befehlszeile nennt sie den *Payload*. Sie sind komprimiert etwa 90 MB groß, in zwei eigenen Python-Paketen, `libera-core` und `libera-web`.

Beide haben getrennte Versionsnummern. Die Anwendung prüft, ob die Komponenten, die sie findet, die erwarteten sind. Eine Korrektur an der Anwendung bedeutet deshalb nicht, die Komponenten erneut herunterzuladen.

Jeder Installationsweg bringt beide mit. Das Windows-Installationsprogramm und das Linux-Flatpak enthalten sie, und pip installiert die Komponenten mit der Anwendung, die sie voraussetzt.

## Was es nicht ist

Libera Suite spricht mit keinem Server, braucht kein Konto und lädt Ihre Dokumente nie hoch. Die Komponenten laufen als lokaler Webinhalt, der über `127.0.0.1` an ein Fenster auf Ihrem eigenen Rechner ausgeliefert wird. Es gibt keine Zusammenarbeit, keinen Cloud-Speicher und keine Telemetrie, weil nichts davon gebaut ist.
