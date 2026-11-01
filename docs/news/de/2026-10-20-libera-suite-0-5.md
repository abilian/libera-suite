---
date: 2026-10-20
description: Libera Suite 0.5 spricht Ihre Sprache, zeigt Dokumente in den Schriften, die auf Ihrem Computer installiert sind, öffnet sie schneller und räumt nach ihren eigenen Updates auf.
---

# Libera Suite 0.5: in Ihrer Sprache, mit Ihren Schriften

Libera Suite 0.5 ist erschienen. Sie folgt jetzt der Sprache Ihres Systems und zeigt ein Dokument in den Schriften, die auf Ihrem Computer installiert sind.

Libera Suite ist eine freie und quelloffene Office-Suite für Windows, macOS und Linux: Libera Words für Texte, Libera Tables für Tabellen, Libera Slides für Präsentationen und Libera Diagrams, ein Betrachter für Visio-Zeichnungen. Sie öffnet und speichert die Formate von Microsoft Office und LibreOffice, auf Ihrem eigenen Computer, ohne Konto und ohne Cloud-Dienst.

[Libera Suite installieren](../main/install.md){ .md-button .md-button--primary }

Sie nutzen sie schon? Beenden Sie Libera Suite, falls sie läuft, und starten Sie dann das Installationsprogramm oder den Installationsbefehl erneut, oder `brew upgrade libera`, wenn Sie Homebrew verwenden. Diese Version installiert neue Komponenten, ein einmaliger Download von etwa 90 MB.

## In Ihrer Sprache

Bisher sprach Libera Suite nur Englisch. Ihre vier Anwendungen folgen jetzt der Sprache Ihres Systems, und die Zeile `ui_language` in der [Konfigurationsdatei](../guide/documents.md#your-name-in-documents) wählt eine andere. Auf Deutsch, Französisch, Italienisch und Spanisch folgen auch die Menüleiste, das Startfenster und die Dialoge, und die Hilfe öffnet diese Dokumentation in derselben Sprache.

Ein neues Dokument beginnt mit einer leeren Seite für Ihre Sprache und Region: A4-Papier überall außer in den Vereinigten Staaten, wo es bisher für alle US Letter war, und mit Rechtschreibprüfung in Ihrer Sprache.

## Mit Ihren Schriften

Ein Dokument in einer Schrift, die Sie installiert haben, erscheint jetzt in dieser Schrift, auf dem Bildschirm und im PDF, wo es bisher einen Ersatz bekam. Libera Suite erfasst Ihre Schriften, wenn sie ihre Komponenten installiert, und erneut, sobald Sie eine Schrift installieren oder entfernen; nichts wird kopiert. Die Zeile `installed_fonts = false` beschränkt sie auf die Schriften, die Libera Suite mitbringt.

## Schneller auf dem Bildschirm

Das Fenster eines Dokuments öffnet sich jetzt sofort, während das Dokument noch vorbereitet wird. Auf unserem Mac ist ein kleines Textdokument etwa eine Sekunde früher zu sehen. Eine Datei, die Libera Suite nicht lesen kann, öffnet jetzt ein Fenster, das dies meldet, und schließt es wieder.

## Weitere Änderungen

- **Aktualisierte Komponenten**, vom Oktober, mit den Upstream-Korrekturen seit der vorigen Version.
- **Eine strengere Sicherheitsrichtlinie.** Die Komponenten können nichts laden und nichts senden, außer an Libera Suite selbst. Die Ausnahme ist ein Bild, auf das ein Dokument über seine Webadresse verweist; es wird wie in jeder Office-Suite abgerufen.
- **Makros sind abgeschaltet und bleiben erhalten.** Die Makros der Komponenten sind JavaScript und führen kein VBA aus Dokumenten von Microsoft Office aus, daher sind sie abgeschaltet. Die Makros eines Dokuments bleiben erhalten: Das Speichern einer `.docm`-, `.xlsm`- oder `.pptm`-Datei lässt ihr VBA unverändert, und Libera Words öffnet und speichert jetzt `.docm`.
- **Alte Komponenten werden entfernt.** Jedes Update ließ bisher die vorige Version auf der Festplatte, jeweils etwa 400 MB. Eine Version, die vier Wochen lang nicht benutzt wurde, wird jetzt entfernt.
- **Korrekturen.** Das Schriftmenü zeigt jeden Namen vollständig. Eine `.xlsb`-Arbeitsmappe öffnet sich, statt als leere Präsentation. Unter macOS bleiben nach dem Beenden mit Cmd-Q keine Dokumente mehr gesperrt. Unter Windows zeigt die Liste „Zuletzt verwendet“ den Namen jedes Dokuments und verliert keine Einträge mehr.

## Was wegfällt

- **Speichern als `.xlsb`.** Das Schreiben einer solchen Datei stürzte unter Linux ab. Speichern Sie stattdessen als `.xlsx`; Excel öffnet beide.
- **Linux auf arm64, vorerst.** Von 0.5 gibt es keinen arm64-Build. Das Installationsskript installiert auf diesen Rechnern 0.4.1; eine spätere Version unterstützt arm64 wieder.

[Was heute funktioniert](../main/status.md) zeigt, was fertig ist, was halb fertig ist und was noch nicht begonnen wurde.

## Ihre Rückmeldung

Libera Suite ist jung, und jede Meldung zählt. Am nützlichsten ist weiterhin ein Dokument, das falsch dargestellt wird, an Ihre Nachricht angehängt, zusammen mit der Ausgabe von `libera --diagnose`. [Rückmeldung](../feedback.md) erklärt, wie Sie uns erreichen.

*Abilian*
