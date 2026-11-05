# Weitere Installationswege

[Installieren](install.md) beschreibt den üblichen Weg für jede Plattform, der für die meisten passt. Diese Seite behandelt alles andere: einen Kanal selbst wählen, von Hand installieren und wissen, wo was landet.

## Die Optionen des Installationsskripts

`install.sh` nimmt Optionen an. Über eine Pipe gestartet, braucht es `sh -s --` davor:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh -s -- --prefix ~/apps
curl -fsSL https://cdn.abilian.com/libera/install.sh | bash -s -- --help
```

| | |
| :--- | :--- |
| `--prefix DIR` | an einem anderen Ort installieren (Standard: `~/.local`) |
| `--channel pip` | unter Linux das Python-Paket installieren, auch wenn Flatpak vorhanden ist |
| `--origin URL` | von einem anderen als dem öffentlichen Server herunterladen |

Es schreibt nur nach `~/.local/bin` und `~/.local/share`. Öffnen Sie seine Adresse im Browser, um es vor dem Ausführen zu lesen.

## pipx oder uv

Libera Suite steht auf PyPI unter dem Namen `libera` und braucht Python 3.12 oder neuer. Die [Komponenten](#the-editors) werden mit ihr installiert. Unter macOS und Windows:

```sh
uv tool install libera      # oder: pipx install libera
```

Zum Ausprobieren ohne Installation startet `uvx libera` sie aus einem Zwischenspeicher.

Unter Linux zeichnet GTK das Fenster. Dessen Python-Anbindung stammt aus Ihrer Distribution und ist für deren eigenes Python gebaut. Eine isolierte Umgebung sieht sie nicht, deshalb braucht `pipx` zwei Optionen:

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
```

Ohne sie installiert sich Libera Suite fehlerfrei und öffnet dann kein Fenster. `uv tool` hat keine Entsprechung zu `--system-site-packages`; verwenden Sie unter Linux also `pipx`. Beim ersten Start nennt `libera` die GTK-Pakete, die Ihrer Distribution fehlen; es kennt apt, dnf, pacman und zypper.

## Das Flatpak von Hand

So geht das Installationsskript vor, wenn Flatpak vorhanden ist:

```sh
arch=amd64     # oder arm64, je nach Rechner
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
# unter arm64: ver=0.4.1, die letzte dafür gebaute Version
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

`bundles/latest` enthält die aktuelle Versionsnummer, daher bleiben diese Zeilen von Version zu Version gültig. Das Paket ist etwa 70 MB groß und enthält die Komponenten. Es läuft auf der GNOME-Laufzeitumgebung, die `flatpak` beim ersten Mal von Flathub lädt; auf einem Rechner ohne Flathub-Quelle muss diese zuerst hinzugefügt werden:

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

Ab Version 0.7.0 liegt neben jedem Paket seine Signatur, sodass Sie vor der Installation prüfen können, dass es von uns stammt. Im selben Ordner, mit `ver` und `arch` wie oben gesetzt:

```sh
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak.asc"
curl -fsSL https://keys.openpgp.org/vks/v1/by-fingerprint/E1B31B9935BEDA0C53D21A1DD35A9ACA9BE0C732 | gpg --import
gpg --verify "libera-$ver-$arch.flatpak.asc" "libera-$ver-$arch.flatpak"
```

GnuPG muss `Korrekte Signatur von "Libera Suite release signing <releases@liberasuite.eu>"` melden (auf Englisch `Good signature from`), und der angezeigte Fingerabdruck des Hauptschlüssels muss `E1B3 1B99 35BE DA0C 53D2 1A1D D35A 9ACA 9BE0 C732` sein. Die Warnung, der Schlüssel sei nicht zertifiziert, bedeutet nur, dass Sie GnuPG nicht selbst gesagt haben, diesem Schlüssel zu vertrauen. Das Installationsskript führt diese Prüfung nicht durch.

## Die Komponenten {#the-editors}

Jeder Kanal installiert die Komponenten mit der Anwendung. Das Windows-Installationsprogramm und das Flatpak enthalten sie. Mit pip, pipx oder uv sind sie zwei Python-Pakete, die `libera` voraussetzt: `libera-core`, die Dokument-Engine, für jede Plattform gebaut, und `libera-web`, die Bearbeitungskomponenten und die Schriften. Zusammen sind etwa 90 MB herunterzuladen. Beim ersten Start wird dann der Schriftenindex für Ihren Rechner erstellt, was einen Moment dauert.

Auf PyPI gibt es `libera-core` für Windows x64, Linux x86_64 und macOS auf Apple Silicon. Auf jedem anderen Rechner baut pip es aus dem Quellcode. Das dauert fast eine Stunde und braucht die Werkzeuge, die [Build the payload](/en/develop/build/) (auf Englisch) aufführt.

Versionen vor 0.7 haben ihre Komponenten getrennt heruntergeladen, in die unten genannten Ordner. `libera --payload-remove` löscht, was sie dort hinterlassen haben.

## Wo die Dateien liegen

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/` oder `~/.local/share/libera/` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |
| Windows | `%LOCALAPPDATA%\Libera Suite\` |

Dort bewahrt Libera Suite auf, was sie zwischen zwei Starts braucht, etwa die Liste der zuletzt verwendeten Dokumente und nicht gespeicherte Sitzungen. Die Komponenten liegen nicht dort: Sie werden mit der Anwendung installiert, und `libera --payload-status` zeigt, wo. Um Komponenten von woanders zu verwenden, etwa einen lokalen Build, setzen Sie `LIBERA_PAYLOAD` auf deren Ordner; das hat Vorrang vor den installierten.

## Ein Eintrag im Anwendungsmenü unter Linux {#a-launcher-entry-on-linux}

Das Installationsskript und das Flatpak tragen Libera Suite beide in Ihr Anwendungsmenü ein. Nach jeder anderen Installation erledigt das dieser Befehl, nur für Ihr Konto: ein Symbol, *Öffnen mit* und Dokumente, die sich per Doppelklick öffnen.

```sh
libera --launcher-install
libera --launcher-remove     # um ihn wieder zu entfernen
```

## Eine Anwendung zum Doppelklicken unter macOS {#a-double-clickable-application-on-macos}

Das Installationsskript legt eine an, `Libera.app`, im Programme-Ordner Ihres Benutzerordners. Nach jeder anderen Installation, etwa mit Homebrew, `pipx` oder `uv tool`, erledigt dieser Befehl dasselbe:

```sh
libera --launcher-install
libera --launcher-remove     # um sie wieder zu entfernen
```

Sie öffnet Dokumente per Doppelklick und zeigt das Libera-Symbol im Dock. Sie ist ein kleiner Starter für das Python der Installation, die sie angelegt hat: Nachdem Sie diese deinstalliert oder auf ein anderes Python umgestellt haben, führen Sie `libera --launcher-install` erneut aus.

Aus einer Kopie des Quellcodes können Sie eine für diese Kopie bauen:

```sh
build/macos/macos-app.sh          # baut build/out/Libera.app
open build/out/Libera.app
```

Sie verwendet das Python dieser Kopie des Quellcodes und gehört damit zu ihr: Lassen Sie sie dort, und bauen Sie sie neu, wenn die Kopie umzieht. Sie ist nicht signiert, daher meldet macOS beim ersten Start **„kann nicht geöffnet werden, da der Entwickler nicht verifiziert werden kann“**. Ab macOS 15 kommen Sie darüber hinweg mit *Systemeinstellungen ▸ Datenschutz & Sicherheit ▸ Trotzdem öffnen*.
