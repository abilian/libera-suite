# Installieren

Libera Suite läuft unter **Windows 10 und 11 (x64)**, **Linux (x86_64 und arm64)** und **macOS (Apple Silicon)**. Die Installation braucht kein Administratorkennwort: Sie gilt nur für Ihr Benutzerkonto.

## Windows {#windows}

Laden Sie das Installationsprogramm herunter und doppelklicken Sie darauf:

<https://cdn.abilian.com/libera/bundles/Libera-Suite-Setup.exe>

Es legt Libera Suite im Startmenü und auf dem Desktop ab und trägt sie im Explorer unter *Öffnen mit* ein. Alles ist enthalten, danach muss nichts mehr heruntergeladen werden.

Wenn Sie einen Befehl vorziehen: Diese Zeile in PowerShell tut dasselbe und prüft den Download zusätzlich anhand seiner veröffentlichten Prüfsumme:

```powershell
irm https://cdn.abilian.com/libera/install.ps1 | iex
```

Beim ersten Mal fragt Windows zweierlei:

- **„Der Computer wurde durch Windows geschützt“**, wenn Sie das heruntergeladene Installationsprogramm öffnen. Es ist noch nicht mit einem Zertifikat signiert, und genau darauf achtet diese Warnung. Wählen Sie *Weitere Informationen*, dann *Trotzdem ausführen*. Die PowerShell-Zeile löst sie nicht aus.
- **„Wie möchten Sie diese Datei öffnen?“**, wenn Sie zum ersten Mal ein Dokument doppelklicken, das auch ein anderes Programm öffnen kann, etwa Word. Wählen Sie Libera Suite und dann *Immer*. Ändern können Sie das später unter *Einstellungen › Apps › Standard-Apps*.

## Linux

Öffnen Sie ein Terminal und führen Sie aus:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

Ist Flatpak auf Ihrem Rechner vorhanden, installiert dies Libera Suite als Flatpak mit allem, was sie braucht, und trägt sie in das Anwendungsmenü ein. Andernfalls installiert es den Befehl `libera`; beim ersten Start nennt dieser die Systempakete, die Ihrer Distribution fehlen, samt dem genauen Befehl, um sie zu installieren.

Es funktioniert unter Ubuntu 22.04, Debian 12, Fedora 35, RHEL 9 und allen neueren Versionen. Ohne Flatpak braucht es außerdem Python 3.12 oder neuer; fehlt es, meldet das Skript dies, bevor es irgendetwas ändert.

Wenn Sie Homebrew unter Linux verwenden, funktioniert die Homebrew-Zeile aus dem macOS-Abschnitt unten auch dort.

## macOS

Mit [Homebrew](https://brew.sh) öffnen Sie das Terminal und führen aus:

```sh
brew install abilian/tap/libera
```

Homebrew baut Libera Suite auf Ihrem Mac. Beim ersten Start von `libera` bietet sie an, die Editoren herunterzuladen, etwa 110 MB.

Ohne Homebrew brauchen Sie Python 3.12 oder neuer, das macOS nicht mitbringt: Installieren Sie es von [python.org](https://www.python.org/downloads/macos/). Führen Sie dann aus:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

In beiden Fällen erhalten Sie den Befehl `libera`. Unter macOS wird Libera Suite vorerst aus einem Terminal gestartet: Eine Anwendung zum Doppelklicken steht [auf der Roadmap](/en/develop/roadmap/).

## Starten

- **Windows:** über das Startmenü oder den Desktop, oder per Doppelklick auf ein Dokument.
- **Linux:** über das Anwendungsmenü, oder mit `libera` in einem Terminal.
- **macOS:** mit `libera` im Terminal. Geben Sie ein Dokument an, um genau dieses zu öffnen:

```sh
libera ~/Documents/bericht.docx
```

Ohne Argument öffnet `libera` das Startfenster, in dem Sie ein Dokument anlegen, eines öffnen oder ein zuletzt verwendetes wählen:

![Das Startfenster mit je einer Kachel New für Document, Spreadsheet und Presentation, einer Schaltfläche Open und einer Liste Recent mit drei Dokumenten.](../assets/start.png)

Die nächste Seite ist [Mit Dokumenten arbeiten](../guide/documents.md): öffnen, speichern, exportieren und drucken.

## Aktualisieren

Führen Sie dasselbe Installationsprogramm oder denselben Befehl erneut aus. Die installierte Version wird durch die neueste ersetzt.

Mit Homebrew führen Sie `brew upgrade libera` aus. Braucht eine neue Version neue Editoren, bietet Libera Suite beim nächsten Start an, sie herunterzuladen.

## Deinstallieren

- **Windows:** *Einstellungen › Apps › Installierte Apps › Libera Suite › Deinstallieren*.
- **Linux, als Flatpak installiert** (`flatpak list` zeigt `eu.liberasuite.Libera`):

    ```sh
    flatpak uninstall --user eu.liberasuite.Libera
    rm -f ~/.local/share/applications/eu.liberasuite.Libera.desktop ~/.local/share/icons/hicolor/*/apps/eu.liberasuite.Libera.*
    ```

- **Linux, anders installiert:**

    ```sh
    libera --launcher-remove
    rm -rf ~/.local/bin/libera ~/.local/share/libera
    ```

- **macOS:**

    ```sh
    libera --payload-remove
    rm -rf ~/.local/bin/libera ~/.local/share/libera
    ```

- **Homebrew**, auf beiden Systemen:

    ```sh
    libera --payload-remove
    brew uninstall libera
    ```

Ihre Dokumente werden nie angerührt. Was Libera Suite zwischen zwei Sitzungen aufbewahrt, etwa die Liste der zuletzt verwendeten Dokumente und nicht gespeicherte Sitzungen, bleibt zurück: unter macOS in `~/Library/Application Support/Libera Suite`, beim Flatpak in `~/.var/app/eu.liberasuite.Libera`. Löschen Sie diesen Ordner, um jede Spur zu entfernen.

## Wenn etwas nicht klappt

Führen Sie dies in einem Terminal aus (unter Windows in PowerShell: `& "$env:LOCALAPPDATA\Programs\Libera Suite\libera-cli.exe" --diagnose`):

```sh
libera --diagnose
```

Der Befehl gibt eine Bildschirmseite aus. Zwei Zeilen zählen vor allem:

- **`window`** sollte `ok` lauten. Unter Linux bedeutet `NOT AVAILABLE`, dass Systempakete fehlen; `libera` gibt beim Start den Befehl aus, um sie zu installieren.
- **`payload`** nennt die Editoren und ihre Herkunft. `MISSING` heißt, dass sie nicht heruntergeladen wurden: Führen Sie `libera --payload-install` aus.

[Was heute funktioniert](status.md) führt die Probleme auf, die wir bereits kennen. Für alles andere [schreiben Sie uns](../feedback.md) und fügen Sie die Ausgabe von `libera --diagnose` ein.

Um mit `pipx` oder `uv` zu installieren, das Flatpak von Hand zu installieren oder dem Installationsskript Optionen mitzugeben, lesen Sie [Weitere Installationswege](alt-install.md).
