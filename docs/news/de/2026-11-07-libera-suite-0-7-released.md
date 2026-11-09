---
date: 2026-11-07
description: Mit Libera Suite 0.7 können Sie PDFs kommentieren, ausfüllen und neu ordnen, Dokumente unter ihrem Kennwort halten und digitale Signaturen lesen und erstellen. Ihre Komponenten werden jetzt mit ihr installiert.
---

# Libera Suite 0.7: PDFs, Kennwörter und Signaturen

Libera Suite 0.7 ist erschienen. Sie können jetzt PDFs kommentieren, ausfüllen und neu ordnen, kennwortgeschützte Dokumente öffnen und speichern und digitale Signaturen lesen und erstellen.

Libera Suite ist eine freie und quelloffene Office-Suite für Windows, macOS und Linux: Libera Words für Texte, Libera Tables für Tabellen, Libera Slides für Präsentationen, Libera PDF für PDFs und Libera Diagrams, ein Betrachter für Visio-Zeichnungen. Sie öffnet und speichert die Formate von Microsoft Office und LibreOffice, auf Ihrem eigenen Computer, ohne Konto und ohne Cloud-Dienst.

[Libera Suite installieren](../main/install.md){ .md-button .md-button--primary }

Sie nutzen sie schon? Beenden Sie Libera Suite, falls sie läuft, und starten Sie dann das Installationsprogramm oder den Installationsbefehl erneut, oder `brew upgrade libera`, wenn Sie Homebrew verwenden. Mit pip, pipx oder Homebrew werden die Komponenten jetzt mit der Anwendung installiert, etwa 100 MB, sodass beim ersten Start nichts heruntergeladen wird. Das Startfenster bietet einmal an, zu löschen, was frühere Versionen heruntergeladen haben, und `libera --payload-remove` tut es jederzeit.

## PDFs

![Libera PDF mit einem geöffneten PDF, der Registerkarte Kommentar mit ihren Werkzeugen und einem Kommentar auf der Seite, der im Bereich Kommentare aufgeführt ist.](../assets/pdf.png)

Ein PDF öffnet sich in Libera PDF. Sie können Kommentare, Markierungen, Zeichnungen und Textfelder hinzufügen, kleine Textkorrekturen vornehmen und Seiten einfügen, löschen, drehen und verschieben. Sie können auch Formulare ausfüllen: Ein französisches Cerfa und die US-Formulare der IRS gehören zu denen, die wir ausprobiert haben.

Beim Speichern kommen Ihre Änderungen hinter das Original, das unverändert in der Datei bleibt. Eine gelöschte Seite oder ein korrigierter Text lässt sich also aus der gespeicherten Datei noch wiederherstellen: Verlassen Sie sich auf keines von beiden, um etwas Vertrauliches aus einem PDF zu entfernen, das Sie verschicken.

Bearbeiteter Text wird nicht neu umbrochen. Ein PDF, das gegen jede Änderung zertifiziert ist, lässt sich nicht speichern: Das Speichern schlägt fehl, und die Datei bleibt, wie sie war. Ein Formular erstellen oder ein PDF in ein Dokument umwandeln können Sie noch nicht. Libera Suite wird für ein PDF unter *Öffnen mit* angeboten, nie als Standard. [Mit Dokumenten arbeiten](../guide/documents.md#pdfs) hat die Einzelheiten.

## Kennwörter

Eine kennwortgeschützte Word-, Excel-, PowerPoint-, OpenDocument- oder PDF-Datei fragt beim Öffnen danach, und beim Speichern bleibt sie geschützt. Datei ▸ Schützen fügt das Kennwort eines Dokuments hinzu, ändert und löscht es. Beim Speichern in ein Format, das kein Kennwort behalten kann (Text, CSV, RTF, HTML, Markdown, EPUB), wird zuerst nachgefragt. Ein geschütztes Dokument, das manipuliert wurde, wird abgelehnt, dank einer Korrektur von ElixirOffice.

Standardmäßig verschlüsselt LibreOffice 26 OpenDocument-Dateien auf eine Weise, die Libera Suite noch nicht lesen kann, und Libera Suite sagt das, statt nach dem Kennwort zu fragen. Solange ein geschütztes Dokument geöffnet ist, ist seine Arbeitskopie auf Ihrem Datenträger nicht verschlüsselt, damit ein Absturz Ihre Änderungen nicht verliert. [Mit Dokumenten arbeiten](../guide/documents.md#passwords) hat die Einzelheiten.

## Digitale Signaturen

Ein signiertes Word-, Excel- oder PowerPoint-Dokument zeigt beim Öffnen seine Signaturen, jede gültig oder nicht, und öffnet sich schreibgeschützt. *Schutz* ▸ *Signatur* signiert eines mit einer Schlüsseldatei (PKCS#12 oder PEM) und ihrer Passphrase, und Sie können Signaturen entfernen. Wir haben in Libera Suite erstellte Signaturen mit Microsoft Office und LibreOffice geprüft, und von beiden erstellte Signaturen in Libera Suite.

*Gültig* heißt, dass sich das Dokument seit der Signatur nicht geändert hat: Wer das Zertifikat ausgestellt hat und ob es abgelaufen ist, wird noch nicht geprüft. Ein geschütztes Dokument, eine OpenDocument-Datei oder ein PDF lässt sich noch nicht signieren. [Mit Dokumenten arbeiten](../guide/documents.md#signatures) hat die Einzelheiten.

## Weitere Änderungen

- **Word-97-2003-Dokumente öffnen sich.** Noch nie hatte sich eine `.doc`-Datei geöffnet. Webarchive (`.mht`), FictionBook (`.fb2`) und EPUB-Bücher öffnen sich jetzt ebenfalls.
- **Der Konverter startet in etwa der halben Zeit**, sodass jedes Öffnen und Speichern etwas schneller geht.
- **Eine Datei auf ein Fenster zu ziehen funktioniert unter Linux**: Ein Dokument öffnet sich in einem eigenen Fenster, und ein Bild kommt ins Dokument. Das Flatpak kann jetzt auch Dateien auf USB-Sticks und eingehängten Laufwerken öffnen.
- **Ein Dokument, das jemand anderes geöffnet hat, sagt das jetzt, in welchem Fenster es sich auch öffnet.** Jedes Fenster bekam den Zustand des ersten mitgeteilt.
- **Unter Windows öffnet sich ein Fenster nicht mehr größer als der Bildschirm.**

## Sicherheit

Alle früheren Versionen haben diese Probleme, bitte aktualisieren Sie.

- **Ein Dokument kann keine Bilder mehr von Ihrem Datenträger in sich selbst kopieren.** Ein Bild, das auf einen Pfad auf Ihrem Datenträger verwies, wurde in jedes daraus gespeicherte oder konvertierte Dokument kopiert, sodass mit dem zurückgeschickten Dokument auch das Bild verschickt wurde. Ein verknüpftes Bild wird jetzt nur noch von einer Webadresse gelesen.
- **Drei Cross-Site-Scripting-Lücken (XSS) sind geschlossen.** Ein präpariertes Dokument konnte im Editor ein Skript ausführen, wenn Sie eine nachverfolgte Änderung auswählten, den Funktions-Assistenten öffneten oder auf einen `javascript:`-Link klickten. Alle drei werden jetzt als Text angezeigt oder abgelehnt. Die Seite des Editors lädt Bilder außerdem nur noch von Libera Suite, sodass ein Skript nichts mehr in der Adresse eines Bildes nach außen schicken kann.
- **Der Konverter schreibt keine Teile seines eigenen Speichers mehr in die Dateien, die er erstellt.**
- **Ein kleines Dokument kann den Konverter nicht mehr auf Gigabytes an Speicher treiben.**

## Signierte Downloads und der Quellcode

Die Flatpak-Pakete sind mit unserem OpenPGP-Schlüssel signiert, und [Weitere Installationswege](../main/alt-install.md) erklärt, wie Sie eines prüfen. Das Windows-Installationsprogramm und `Libera.app` sind noch nicht signiert. [Installieren](../main/install.md) zeigt den Weg an der Warnung zum Installationsprogramm vorbei; der einzeilige PowerShell-Befehl, pip, pipx und Homebrew begegnen keiner Warnung.

Der Quellcode der Wheels des Konverters ist das Quellpaket `libera-core` auf PyPI: die Upstream-Commits, die es festlegt, unsere Patches und die Build-Skripte. Der Quellcode der Anwendung ist der Tag `0.7.0` von [abilian/libera-suite](https://github.com/abilian/libera-suite).

## Unverändert

- **Linux auf arm64** installiert weiterhin 0.4.1: Von 0.7 gibt es noch keinen arm64-Build.

[Was heute funktioniert](../main/status.md) zeigt, was fertig ist, was halb fertig ist und was noch nicht begonnen wurde, und [die Roadmap](/en/develop/roadmap/), auf Englisch, sagt, was als Nächstes kommt.

## Ihre Rückmeldung

Libera Suite ist jung: Jede Meldung zählt. Am nützlichsten ist ein Dokument, das falsch dargestellt wird, an Ihre Nachricht angehängt, zusammen mit der Ausgabe von `libera --diagnose`. [Rückmeldung](../feedback.md) erklärt, wie Sie uns erreichen.

*Abilian*
