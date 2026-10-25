---
date: 2026-10-26
description: Libera Suite 0.6 spricht jede Sprache ihrer Anwendungen, setzt Dokumente wie Word, wenn eine Schrift fehlt, behält Markdown-Überschriften und prüft niederländische Rechtschreibung.
---

# Libera Suite 0.6: jede Sprache, und Seiten, die umbrechen wie in Word

Libera Suite 0.6 ist erschienen. Ihre Menüs und Fenster sprechen jetzt alle 44 Sprachen ihrer Anwendungen, und ein Dokument, dessen Schriften Ihnen fehlen, wird gesetzt wie in Word.

Libera Suite ist eine freie und quelloffene Office-Suite für Windows, macOS und Linux: Libera Words für Texte, Libera Tables für Tabellen, Libera Slides für Präsentationen und Libera Diagrams, ein Betrachter für Visio-Zeichnungen. Sie öffnet und speichert die Formate von Microsoft Office und LibreOffice, auf Ihrem eigenen Computer, ohne Konto und ohne Cloud-Dienst.

[Libera Suite installieren](../main/install.md){ .md-button .md-button--primary }

Sie nutzen sie schon? Beenden Sie Libera Suite, falls sie läuft, und starten Sie dann das Installationsprogramm oder den Installationsbefehl erneut, oder `brew upgrade libera`, wenn Sie Homebrew verwenden. Diese Version installiert neue Komponenten, ein einmaliger Download von etwa 90 MB.

## Jede Sprache

Seit 0.5 folgen die Anwendungen der Sprache Ihres Systems, Menüleiste, Startfenster und Dialoge aber nur auf Deutsch, Französisch, Italienisch und Spanisch. Jetzt folgen sie in allen 44 Sprachen, von Arabisch bis Vietnamesisch, und auf Arabisch, Hebräisch und Urdu liest sich das Startfenster von rechts nach links.

Nur die deutsche, französische, italienische und spanische Übersetzung hat ein Muttersprachler durchgesehen. Die anderen sind Entwürfe: Ist ein Wort in Ihrer Sprache falsch oder holprig, [schreiben Sie uns](../feedback.md), und Ihre Korrektur kommt in die nächste Version.

## Seiten, die umbrechen wie in Word

Verlangt ein Dokument eine Schrift, die Ihr Computer nicht hat, ersetzt Libera Suite sie jetzt wie Word:

- **Calibri, Cambria, Arial, Times New Roman und Courier New** erhalten Carlito, Caladea und Liberation, die dieselben Breiten haben, sodass Zeilen und Seiten an denselben Stellen umbrechen wie in Word. Auf dem Mac ging Calibri bisher an die ähnlichste installierte Schrift, sodass dasselbe Dokument von Computer zu Computer anders gesetzt sein konnte.
- **Eine Schrift, die auch Word nicht kennen würde,** erhält den Ersatz für Calibri, wie Word sie in Calibri setzt, wo sie bisher Liberation Sans bekam. Zwei Dokumente unserer Testsammlung haben jetzt die Seitenzahl von Word.
- **Zeichen aus Wingdings, Webdings und Symbol** erscheinen als die Symbole, für die sie stehen: ein Stern, ein Häkchen, ein Smiley, wo eine fehlende Wingdings Buchstaben zeigte.

## Weitere Änderungen

- **Markdown behält seine Überschriften.** Eine Markdown-Datei, geöffnet, bearbeitet und gespeichert, machte bisher aus jeder Überschrift einen fetten Absatz.
- **Niederländische Rechtschreibprüfung**, mit dem Wörterbuch von OpenTaal. Jedes Wörterbuch kommt jetzt mit seiner Lizenz.
- **Unter Linux zeigt das Menü Datei seine Tastenkürzel:** Neu, Öffnen und Schließen zeigen Strg-N, Strg-O und Strg-W.
- **Eine OpenDocument-Datei ohne Masterseiten-Stile behält ihre Stile**, wo bisher jeder Absatz im Standardstil geöffnet wurde.

## Was gleich bleibt

- **Linux auf arm64** installiert weiterhin 0.4.1: Von 0.6 gibt es noch keinen arm64-Build.

[Was heute funktioniert](../main/status.md) zeigt, was fertig ist, was halb fertig ist und was noch nicht begonnen wurde.

## Ihre Rückmeldung

Libera Suite ist jung, und jede Meldung zählt. Am nützlichsten ist weiterhin ein Dokument, das falsch dargestellt wird, an Ihre Nachricht angehängt, zusammen mit der Ausgabe von `libera --diagnose`. [Rückmeldung](../feedback.md) erklärt, wie Sie uns erreichen.

*Abilian*
