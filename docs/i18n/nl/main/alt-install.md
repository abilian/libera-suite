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
| `--no-payload` | de opdracht nu installeren, de componenten later downloaden |
| `--origin URL` | van een andere server downloaden dan de openbare |

Het schrijft naar `~/.local/bin` en `~/.local/share`, en nergens anders. Open de URL in een browser om het script te lezen voordat je het uitvoert.

## pipx of uv

Libera Suite staat op PyPI als `libera` en heeft Python 3.12 of nieuwer nodig. Op macOS en Windows:

```sh
uv tool install libera      # of: pipx install libera
libera --payload-install
```

Om het uit te proberen zonder het te installeren, voert `uvx libera` het uit vanuit een cache; de eerste keer biedt het aan de componenten te downloaden.

Op Linux tekent GTK het venster. De Python-bindings daarvan komen van je distributie en zijn gebouwd voor haar eigen Python. Een geïsoleerde omgeving ziet ze niet, dus `pipx` heeft twee opties nodig:

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
libera --payload-install
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

Het Windows-installatieprogramma en de Flatpak bevatten de componenten. Elk ander kanaal downloadt ze één keer, na de applicatie. `libera` biedt dat aan de eerste keer dat het draait; deze opdracht doet het expliciet:

```sh
libera --payload-install
```

Ze downloadt ongeveer 90 MB van `cdn.abilian.com` en controleert elk bestand aan de hand van vingerafdrukken die met de applicatie zijn meegeleverd, en stopt bij het eerste bestand dat niet klopt. Daarna bouwt ze een lettertype-index voor je computer, wat even duurt.

Om componenten te installeren die je zelf hebt gebouwd of van iemand hebt gekregen, geef je de map ervan op:

```sh
libera --payload-install --from /pad/naar/artefacten
```

[Build the components](/en/develop/build/), in het Engels, legt uit hoe je ze bouwt. `libera --payload-remove` verwijdert ze weer; ze nemen ongeveer 350 MB schijfruimte in.

## Waar alles staat

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/`, of `~/.local/share/libera/` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |
| Windows | `%LOCALAPPDATA%\Libera Suite\` |

De componenten staan daar onder `payload/<version>/`. Een update zet een nieuwe versie naast de oude, en Libera Suite verwijdert een oude versie zodra niets haar vier weken lang heeft gebruikt: een Libera Suite die op een andere manier onder hetzelfde account is geïnstalleerd, kan er nog op draaien. `libera --payload-status` geeft ze weer, met wanneer elke versie voor het laatst is gebruikt. Wil je componenten van elders gebruiken, bijvoorbeeld een lokale build, zet dan `LIBERA_PAYLOAD` op hun map; dat gaat voor alles hierboven.

## Een item in het toepassingenmenu op Linux {#a-launcher-entry-on-linux}

Het installatiescript en de Flatpak zetten Libera Suite allebei in je toepassingenmenu. Na elke andere installatie doet deze opdracht hetzelfde, alleen voor jouw account: een pictogram, *Openen met* en documenten die met een dubbelklik openen.

```sh
libera --launcher-install
libera --launcher-remove     # om het weer weg te halen
```

## Een programma om op te dubbelklikken op macOS {#a-double-clickable-application-on-macos}

Een kant-en-klaar programma is er nog niet. Vanuit een kopie van de broncode kun je er zelf een bouwen:

```sh
build/macos/macos-app.sh          # bouwt build/out/Libera.app
open build/out/Libera.app
```

Het opent documenten met een dubbelklik en toont het Libera-pictogram in het Dock. Het gebruikt de Python waarmee het is gebouwd, dus het hoort bij die kopie van de code: laat het daar staan, en bouw het opnieuw als de kopie verhuist. Het is niet ondertekend, dus bij de eerste start meldt macOS **"kan niet worden geopend omdat de ontwikkelaar niet kan worden geverifieerd"**. Op macOS 15 en later kom je erlangs via *Systeeminstellingen ▸ Privacy en beveiliging ▸ Open toch*.
