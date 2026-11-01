# Installeren

Libera Suite draait op **Windows 10 en 11 (x64)**, **Linux (x86_64 en arm64)** en **macOS (Apple Silicon)**. Voor de installatie heb je geen beheerderswachtwoord nodig: ze geldt alleen voor jouw account. Op Linux arm64 installeert het installatiescript versie 0.4.1, de laatste die ervoor gebouwd is, tot er weer een nieuwere wordt gebouwd.

## Windows {#windows}

Download het installatieprogramma en dubbelklik erop:

<https://cdn.abilian.com/libera/bundles/Libera-Suite-Setup.exe>

Het zet Libera Suite in het Startmenu en op het bureaublad, en voegt het toe aan *Openen met* in de Verkenner. Alles zit erin, dus daarna hoef je niets meer te downloaden.

Werk je liever met een opdracht, dan doet deze regel in PowerShell hetzelfde en controleert hij de download bovendien aan de hand van de gepubliceerde vingerafdruk:

```powershell
irm https://cdn.abilian.com/libera/install.ps1 | iex
```

De eerste keer vraagt Windows twee dingen:

- **"Uw pc is beschermd door Windows"**, wanneer je het gedownloade installatieprogramma opent. Het installatieprogramma is nog niet ondertekend met een certificaat, en daar kijkt deze waarschuwing naar. Kies *Meer info* en daarna *Toch uitvoeren*. De PowerShell-regel roept deze waarschuwing niet op.
- **"Hoe wilt u dit bestand openen?"**, de eerste keer dat je dubbelklikt op een document dat ook een ander programma, zoals Word, kan openen. Kies Libera Suite en vink *Altijd* aan. Je kunt dit later wijzigen via *Instellingen › Apps › Standaard-apps*.

## Linux

Open een terminal en voer uit:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

Heeft je computer Flatpak, dan installeert dit Libera Suite als Flatpak, met alles wat het nodig heeft erin, en zet het in je toepassingenmenu. Anders installeert het de opdracht `libera`; de eerste keer dat je die uitvoert, noemt hij de systeempakketten die je distributie mist, met de precieze opdracht om ze te installeren.

Het werkt op Ubuntu 22.04, Debian 12, Fedora 36, RHEL 9 en de afgeleiden daarvan, en alles wat nieuwer is. Zonder Flatpak is ook Python 3.12 of nieuwer nodig; ontbreekt dat, dan meldt het script het voordat het iets verandert.

Gebruik je Homebrew op Linux, dan werkt de Homebrew-regel uit het macOS-gedeelte hieronder daar ook.

## macOS

Met [Homebrew](https://brew.sh) open je Terminal en voer je uit:

```sh
brew install abilian/tap/libera
```

Homebrew bouwt Libera Suite op je Mac. De eerste keer dat je `libera` uitvoert, biedt het aan de componenten te downloaden, ongeveer 90 MB.

Zonder Homebrew heb je Python 3.12 of nieuwer nodig, en dat zit niet in macOS: installeer het via [python.org](https://www.python.org/downloads/macos/). Voer daarna uit:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

In beide gevallen krijg je de opdracht `libera`. Op macOS start je Libera Suite voorlopig vanuit een terminal: een programma om op te dubbelklikken staat [op de roadmap](/en/develop/roadmap/).

## Starten

- **Windows:** via het Startmenu of het bureaublad, of door op een document te dubbelklikken.
- **Linux:** via je toepassingenmenu, of met `libera` in een terminal.
- **macOS:** met `libera` in Terminal. Geef er een document aan mee om precies dat document te openen:

```sh
libera ~/Documents/verslag.docx
```

Zonder argument opent `libera` het startvenster, waar je een document kunt maken, er een kunt openen of een recent document kunt kiezen:

![Het startvenster, met een tegel New voor elk van Document, Spreadsheet en Presentation, een knop Open en een lijst Recent met drie documenten.](../assets/start.png)

De volgende pagina is [Werken met documenten](../guide/documents.md): openen, opslaan, exporteren en afdrukken.

## Bijwerken {#update}

Voer hetzelfde installatieprogramma of dezelfde opdracht opnieuw uit. De geïnstalleerde versie wordt vervangen door de nieuwste.

Met Homebrew voer je `brew upgrade libera` uit. Heeft een nieuwe versie nieuwe componenten nodig, dan biedt Libera Suite bij de volgende start aan ze te downloaden.

## Verwijderen {#uninstall}

- **Windows:** *Instellingen › Apps › Geïnstalleerde apps › Libera Suite › Verwijderen*.
- **Linux, geïnstalleerd als Flatpak** (`flatpak list` toont `eu.liberasuite.Libera`):

    ```sh
    flatpak uninstall --user eu.liberasuite.Libera
    rm -f ~/.local/share/applications/eu.liberasuite.Libera.desktop ~/.local/share/icons/hicolor/*/apps/eu.liberasuite.Libera.*
    ```

- **Linux, anders geïnstalleerd:**

    ```sh
    libera --launcher-remove
    rm -rf ~/.local/bin/libera ~/.local/share/libera
    ```

- **macOS:**

    ```sh
    libera --payload-remove
    rm -rf ~/.local/bin/libera ~/.local/share/libera
    ```

- **Homebrew**, op beide systemen:

    ```sh
    libera --payload-remove
    brew uninstall libera
    ```

Je documenten blijven altijd onaangeroerd. Wat Libera Suite tussen twee sessies bewaart, zoals de lijst met recente documenten en niet-opgeslagen sessies, blijft achter: in `~/Library/Application Support/Libera Suite` op macOS, en in `~/.var/app/eu.liberasuite.Libera` voor de Flatpak. Verwijder die map om elk spoor te wissen.

## Als er iets misgaat {#if-something-goes-wrong}

Voer dit uit in een terminal (op Windows, in PowerShell: `& "$env:LOCALAPPDATA\Programs\Libera Suite\libera-cli.exe" --diagnose`):

```sh
libera --diagnose
```

De opdracht toont één scherm. Twee regels zijn het belangrijkst:

- **`window`** hoort `ok` te zeggen. Op Linux betekent `NOT AVAILABLE` dat er systeempakketten ontbreken; wanneer je `libera` uitvoert, toont het de opdracht om ze te installeren.
- **`payload`** noemt de componenten en waar ze vandaan komen. `MISSING` betekent dat ze niet zijn gedownload: voer `libera --payload-install` uit.

[Wat er vandaag werkt](status.md) somt de problemen op die we al kennen. Voor al het andere: [laat het ons weten](../feedback.md), met de uitvoer van `libera --diagnose` erbij geplakt.

Om te installeren met `pipx` of `uv`, de Flatpak met de hand te installeren of opties aan het installatiescript mee te geven, lees je [Andere manieren om te installeren](alt-install.md).
