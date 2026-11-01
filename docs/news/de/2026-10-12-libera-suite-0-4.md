---
date: 2026-10-12
description: Libera Suite 0.4 kennzeichnet ein Dokument, das bereits anderswo geöffnet ist, in Libera Suite oder in LibreOffice, gibt OpenDocument-Dateien genauer wieder und bringt Ziehen und Ablegen, ein persönliches Wörterbuch und die Konvertierung auf der Kommandozeile.
---

# Libera Suite 0.4: sicherer im geteilten Ordner, genauer mit OpenDocument

Libera Suite 0.4 ist erschienen. Sie schützt ein Dokument, das jemand anderes geöffnet hat, in Libera Suite wie in LibreOffice. Ihre Editoren lesen und schreiben die OpenDocument-Formate genauer.

[Libera Suite aktualisieren](../main/install.md#update){ .md-button .md-button--primary }

Beenden Sie Libera Suite und starten Sie dann das Installationsprogramm oder den Installationsbefehl erneut, oder `brew upgrade libera`. Diese Version installiert neue Editoren, ein einmaliger Download von etwa 100 MB.

## Sperren von Dokumenten

Bisher hinderte nichts zwei Fenster daran, dasselbe Dokument zu bearbeiten: Das zuletzt speichernde überschrieb die Arbeit des anderen. Die Beta führte das unter ihren Grenzen auf. Version 0.4 behebt es zwischen zwei Fenstern von Libera Suite sowie zwischen Libera Suite und LibreOffice. Microsoft Office sieht diese Sperren noch nicht, ein in Word geöffnetes Dokument bleibt also ungeschützt.

- **Libera Suite setzt eine Sperre im Format von LibreOffice.** Beim Öffnen eines Dokuments legt sie daneben die kleine Sperrdatei an, die LibreOffice verwendet. Sie beachtet auch die Sperren, die LibreOffice setzt. Ein Dokument, das bereits anderswo geöffnet ist, öffnet sich als *locked for editing*: Sie können es lesen und ändern, doch beim Speichern wird nach einem anderen Ort gefragt. Das Original bleibt unverändert.
- **Ein erneutes Öffnen holt das Fenster des Dokuments nach vorn**, ohne ein zweites zu öffnen.
- **Ein Fenster zeigt ungespeicherte Änderungen an**: einen Punkt im Schließen-Knopf unter macOS, ein `*` vor dem Titel unter Linux und Windows.

## Genauere Wiedergabe der OpenDocument-Formate

Die Editoren in 0.4 enthalten **68 Korrekturen für die OpenDocument-Formate** (`.odt`, `.ods`, `.odp`), jede mit den Testdokumenten von LibreOffice gefunden. Auch zwei Fehler bei CSV-Dateien sind behoben. Ein Emoji verhinderte das Speichern einer CSV-Datei; eine große CSV-Datei verlor beim Lesen eines von 500.000 Zeichen.

## Hinweis auf neue Versionen

Neu in 0.4: Höchstens einmal am Tag liest Libera Suite die Nummer der neuesten Version von unserem Download-Server. Ist sie neuer als Ihre, sagt sie es Ihnen einmal, mit den Schritten für Ihre Installationsart. Sie lädt nichts herunter und sendet nichts über Sie oder Ihre Dokumente; ohne Netz tut sie nichts. Die Zeile `check_updates = false` in der [Konfigurationsdatei](../guide/documents.md#your-name-in-documents) schaltet es ab.

## Weitere Neuerungen

- **Ziehen und Ablegen.** Ein auf ein Fenster gezogenes Dokument öffnet sich; ein auf ein Dokument gezogenes Bild wird eingefügt.
- **Das persönliche Wörterbuch.** Ein mit *Add to dictionary* hinzugefügtes Wort bleibt erhalten, für alle Dokumente und alle Sprachen.
- **Ihr Name in Änderungsverfolgung und Kommentaren**, festgelegt mit `user_name` in der Konfigurationsdatei.
- **Strg-N, Strg-O und Strg-W** unter Linux und Windows.
- **Drucken** fragt, wo das PDF gespeichert werden soll, beginnend im Ordner des Dokuments.
- **Konvertierung auf der Kommandozeile**: `libera --convert *.docx -t pdf` schreibt neben jedes Dokument ein PDF, ohne ein Fenster zu öffnen.
- **Das Fenster About** zeigt die installierte Version, die erste Angabe in einem Fehlerbericht.

Die verbleibenden Grenzen, darunter fehlende Tabs und ein noch nicht signiertes Windows-Installationsprogramm, stehen auf [der Statusseite](../main/status.md).

## Probleme melden

Die nützlichste Meldung bleibt ein Dokument, das falsch herauskommt, als Anhang Ihrer Nachricht, zusammen mit der Ausgabe von `libera --diagnose`. [Rückmeldung](../feedback.md) sagt, wie Sie uns erreichen.

*Abilian*
