# Kommandozeile

Libera Suite wird über seine Fenster bedient, doch ein Terminal erreicht einiges, das kein Fenster bietet: einen ganzen Ordner von Dokumenten auf einmal umwandeln, die Komponenten auf einem Rechner installieren, der nur per SSH erreichbar ist, den Bericht erstellen, den ein Fehler braucht.

Der Befehl heißt unter Linux und macOS `libera`. Als Flatpak installiert lautet er `flatpak run eu.liberasuite.Libera`, gefolgt von denselben Optionen. Unter Windows ist es `libera-cli.exe` im Installationsordner von Libera Suite; er liegt nicht im `PATH`.

## Öffnen

| | |
| :--- | :--- |
| `libera` | das Startfenster: neu, öffnen, zuletzt verwendet |
| `libera DATEI...` | jedes Dokument in einem eigenen Fenster; die Datei bestimmt die Anwendung. [Mehr](documents.md#open) |

## Umwandeln

| | |
| :--- | :--- |
| `libera --convert DATEI... -t FORMAT` | jedes Dokument im `FORMAT` geschrieben, neben dem Original, ohne Fenster. `FORMAT` ist eine Endung: `pdf`, `odt`, `docx`, `xlsx`, `csv`... |
| `-o DATEI` | für ein einzelnes Dokument: die zu schreibende Datei, deren Endung das Format angibt, sofern `-t` nichts anderes sagt. `-o -` schreibt auf die Standardausgabe |
| `--outdir ORDNER` | in `ORDNER` schreiben statt neben jedes Dokument |

[Mehr, mit Beispielen](documents.md#from-the-command-line).

## Die Komponenten

| | |
| :--- | :--- |
| `libera --payload-install` | die Komponenten herunterladen, prüfen und installieren. `--from ORDNER` installiert sie stattdessen aus einem Ordner. [Mehr](../main/alt-install.md#the-editors) |
| `libera --payload-status` | wo die Komponenten liegen, ihre Version und der [Quellcode](../licence.md#corresponding-source), aus dem sie gebaut wurden |
| `libera --payload-remove` | sie löschen. [Mehr](../main/install.md#uninstall) |

## Das Anwendungsmenü und Öffnen mit

| | |
| :--- | :--- |
| `libera --launcher-install` | Libera Suite zu Ihren Anwendungen hinzufügen, mit *Öffnen mit*: unter Linux ins Anwendungsmenü ([mehr](../main/alt-install.md#a-launcher-entry-on-linux)), unter macOS als `Libera.app` in Ihren Programme-Ordner ([mehr](../main/alt-install.md#a-double-clickable-application-on-macos)). |
| `libera --launcher-remove` | sie wieder entfernen |

Das Flatpak, das Windows-Installationsprogramm und unter macOS das Installationsskript erledigen das selbst.

## Wenn etwas nicht klappt

| | |
| :--- | :--- |
| `libera --diagnose` | alles, was ein Fehlerbericht braucht, auf einem Bildschirm. [Mehr](../main/install.md#if-something-goes-wrong) |
| `libera --version` | die Version der Anwendung und die der Komponenten |
| `-v`, `-vv`, `-vvv` | ausgeben, was gerade geschieht; wie; jede Anfrage an die Komponenten |
| `-q` | nur Fehler |

`libera --help` listet alle Optionen auf, `libera --convert --help` die des Konverters.
