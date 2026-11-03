# Andere manieren om te installeren

[Installeren](install.md) beschrijft de gebruikelijke weg voor elk platform, en die past bij de meeste mensen. Deze pagina gaat over al het andere: zelf een kanaal kiezen, met de hand installeren en weten waar alles terechtkomt.

## De opties van het installatiescript

`install.sh` accepteert opties. Via een pipe heeft het `sh -s --` ervoor nodig:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh -s -- --prefix ~/apps
curl -fsSL https://cdn.abilian.com/libera/install.sh | bash -s -- --help
```

| | |
| :--- | :--- |
| `--prefix DIR` | ergens anders installeren (standaard: `~/.local`) |
| `--channel pip` | op Linux het Python-pakket installeren, ook als Flatpak aanwezig is |
| `--origin URL` | van een andere server downloaden dan de openbare |

Het schrijft naar `~/.local/bin` en `~/.local/share`, en nergens anders. Open de URL in een browser om het script te lezen voordat je het uitvoert.

## pipx of uv

Libera Suite staat op PyPI als `libera` en heeft Python 3.12 of nieuwer nodig. De [componenten](#the-editors) worden meegeïnstalleerd. Op macOS en Windows:

```sh
uv tool install libera      # of: pipx install libera
```

Om het uit te proberen zonder het te installeren, voert `uvx libera` het uit vanuit een cache.

Op Linux tekent GTK het venster. De Python-bindings daarvan komen van je distributie en zijn gebouwd voor haar eigen Python. Een geïsoleerde omgeving ziet ze niet, dus `pipx` heeft twee opties nodig:

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
```

Zonder die opties installeert Libera Suite zonder fouten en opent het daarna geen venster. `uv tool` heeft geen equivalent van `--system-site-packages`, dus gebruik op Linux `pipx`. De eerste keer dat je `libera` uitvoert, noemt het de GTK-pakketten die je distributie mist; het kent apt, dnf, pacman en zypper.

## De Flatpak, met de hand

Dit doet het installatiescript wanneer Flatpak aanwezig is:

```sh
arch=amd64     # of arm64, afhankelijk van je computer
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
# op arm64: ver=0.4.1, de laatste versie die ervoor gebouwd is
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

`bundles/latest` bevat het huidige versienummer, zodat deze regels van de ene release naar de volgende blijven kloppen. De bundel, ongeveer 70 MB, bevat de componenten. Hij draait op de GNOME-runtime, die `flatpak` de eerste keer van Flathub downloadt; op een computer zonder de Flathub-remote moet je die eerst toevoegen:

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

## De componenten {#the-editors}

Elk kanaal installeert de componenten samen met de applicatie. Het Windows-installatieprogramma en de Flatpak bevatten ze. Met pip, pipx of uv zijn het twee Python-pakketten die `libera` vereist: `libera-core`, de documentengine, gebouwd voor elk platform, en `libera-web`, de bewerkingscomponenten en de lettertypen. Samen zijn ze ongeveer 90 MB om te downloaden. Bij de eerste start wordt daarna een lettertype-index voor je computer gebouwd, wat even duurt.

PyPI heeft `libera-core` voor Windows x64, Linux x86_64 en macOS op Apple Silicon. Op elke andere computer bouwt pip het vanuit de broncode. Dat duurt het grootste deel van een uur en vraagt de tools die [Build the components](/en/develop/build/), in het Engels, opsomt.

Versies vóór 0.7 downloadden hun componenten apart, in de mappen hieronder. `libera --payload-remove` verwijdert wat ze daar hebben achtergelaten.

## Waar alles staat

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/`, of `~/.local/share/libera/` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |
| Windows | `%LOCALAPPDATA%\Libera Suite\` |

Daar bewaart Libera Suite wat het tussen twee sessies nodig heeft, zoals de lijst met recente documenten en niet-opgeslagen sessies. De componenten staan daar niet: ze worden met de applicatie geïnstalleerd, en `libera --payload-status` zegt waar. Wil je componenten van elders gebruiken, bijvoorbeeld een lokale build, zet dan `LIBERA_PAYLOAD` op hun map; dat gaat voor de geïnstalleerde componenten.

## Een item in het toepassingenmenu op Linux {#a-launcher-entry-on-linux}

Het installatiescript en de Flatpak zetten Libera Suite allebei in je toepassingenmenu. Na elke andere installatie doet deze opdracht hetzelfde, alleen voor jouw account: een pictogram, *Openen met* en documenten die met een dubbelklik openen.

```sh
libera --launcher-install
libera --launcher-remove     # om het weer weg te halen
```

## Een programma om op te dubbelklikken op macOS {#a-double-clickable-application-on-macos}

Het installatiescript zet er een, `Libera.app`, in de map Programma's van je thuismap. Na elke andere installatie, zoals Homebrew, `pipx` of `uv tool`, doet deze opdracht hetzelfde:

```sh
libera --launcher-install
libera --launcher-remove     # om het weer weg te halen
```

Het opent documenten met een dubbelklik en toont het Libera-pictogram in het Dock. Het is een klein startprogramma voor de Python van de installatie die het heeft geschreven: heb je die verwijderd of op een andere Python gezet, voer dan `libera --launcher-install` opnieuw uit.

Vanuit een kopie van de broncode kun je er een bouwen voor die kopie:

```sh
build/macos/macos-app.sh          # bouwt build/out/Libera.app
open build/out/Libera.app
```

Het gebruikt de Python van die kopie van de code, dus het hoort erbij: laat het daar staan, en bouw het opnieuw als de kopie verhuist. Het is niet ondertekend, dus bij de eerste start meldt macOS **"kan niet worden geopend omdat de ontwikkelaar niet kan worden geverifieerd"**. Op macOS 15 en later kom je erlangs via *Systeeminstellingen ▸ Privacy en beveiliging ▸ Open toch*.
