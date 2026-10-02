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
| `--no-payload` | den Befehl jetzt installieren, die Editoren später herunterladen |
| `--origin URL` | von einem anderen als dem öffentlichen Server herunterladen |

Es schreibt nur nach `~/.local/bin` und `~/.local/share`. Öffnen Sie seine Adresse im Browser, um es vor dem Ausführen zu lesen.

## pipx oder uv

Libera Suite steht auf PyPI unter dem Namen `libera` und braucht Python 3.12 oder neuer. Unter macOS:

```sh
uv tool install libera      # oder: pipx install libera
libera --payload-install
```

Unter Linux zeichnet GTK das Fenster. Dessen Python-Anbindung stammt aus Ihrer Distribution und ist für deren eigenes Python gebaut. Eine isolierte Umgebung sieht sie nicht, deshalb braucht `pipx` zwei Optionen:

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
libera --payload-install
```

Ohne sie installiert sich Libera Suite fehlerfrei und öffnet dann kein Fenster. `uv tool` hat keine Entsprechung zu `--system-site-packages`; verwenden Sie unter Linux also `pipx`. Beim ersten Start nennt `libera` die GTK-Pakete, die Ihrer Distribution fehlen; es kennt apt, dnf, pacman und zypper.

## Das Flatpak von Hand

So geht das Installationsskript vor, wenn Flatpak vorhanden ist:

```sh
arch=amd64     # oder arm64, je nach Rechner
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

`bundles/latest` enthält die aktuelle Versionsnummer, daher bleiben diese Zeilen von Version zu Version gültig. Das Paket ist etwa 82 MB groß und enthält die Editoren. Es läuft auf der GNOME-Laufzeitumgebung, die `flatpak` beim ersten Mal von Flathub lädt; auf einem Rechner ohne Flathub-Quelle muss diese zuerst hinzugefügt werden:

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

## Die Editoren

Das Windows-Installationsprogramm und das Flatpak enthalten die Editoren. Alle anderen Kanäle laden sie einmal herunter, nach der Anwendung. `libera` bietet das beim ersten Start an; dieser Befehl stößt es direkt an:

```sh
libera --payload-install
```

Er lädt etwa 120 MB von `cdn.abilian.com` herunter und prüft jede Datei anhand der Prüfsummen, die mit der Anwendung geliefert wurden. Bei der ersten Abweichung bricht er ab. Danach erstellt er den Schriftenindex für Ihren Rechner, was einen Moment dauert.

Um Editoren zu installieren, die Sie selbst gebaut oder bekommen haben, geben Sie ihm deren Ordner an:

```sh
libera --payload-install --from /pfad/zu/den/artefakten
```

[Build the payload](/en/develop/build/), auf Englisch, erklärt, wie man sie baut. `libera --payload-remove` entfernt sie wieder; sie belegen etwa 450 MB auf der Festplatte.

## Wo die Dateien liegen

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/` oder `~/.local/share/libera/` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |
| Windows | `%LOCALAPPDATA%\Libera Suite\` |

Die Editoren liegen dort unter `payload/<version>/`. Um Editoren von woanders zu verwenden, etwa einen lokalen Build, setzen Sie `LIBERA_PAYLOAD` auf deren Ordner; das hat Vorrang vor allem oben Genannten.

## Ein Eintrag im Anwendungsmenü unter Linux

Das Installationsskript und das Flatpak tragen Libera Suite beide in Ihr Anwendungsmenü ein. Nach jeder anderen Installation erledigt das dieser Befehl, nur für Ihr Konto: ein Symbol, *Öffnen mit* und Dokumente, die sich per Doppelklick öffnen.

```sh
libera --launcher-install
libera --launcher-remove     # um ihn wieder zu entfernen
```

## Eine Anwendung zum Doppelklicken unter macOS {#a-double-clickable-application-on-macos}

Eine fertige gibt es noch nicht. Aus einer Kopie des Quellcodes können Sie sich selbst eine bauen:

```sh
build/macos-app.sh          # baut build/out/Libera.app
open build/out/Libera.app
```

Sie öffnet Dokumente per Doppelklick und zeigt das Libera-Symbol im Dock. Sie verwendet das Python, mit dem sie gebaut wurde, und gehört damit zu dieser Kopie des Quellcodes: Lassen Sie sie dort, und bauen Sie sie neu, wenn die Kopie umzieht. Sie ist nicht signiert, daher meldet macOS beim ersten Start **„kann nicht geöffnet werden, da der Entwickler nicht verifiziert werden kann“**. Ab macOS 15 kommen Sie darüber hinweg mit *Systemeinstellungen ▸ Datenschutz & Sicherheit ▸ Trotzdem öffnen*.
