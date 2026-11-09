# Licentie en naamsvermelding

## Twee licenties, voor twee onderdelen

| | |
| :--- | :--- |
| **De hosttoepassing**: het pakket `libera`, alles in `src/libera/` | [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| **De componenten**: Euro-Office en onze patchreeks daarop | [AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html) |

Ze zijn apart verpakt en blijven apart. De hosttoepassing is een paar honderd kilobyte Python en JavaScript op PyPI, als `libera`; de componenten zijn daar twee eigen pakketten, `libera-core` en `libera-web`, samen ongeveer 100 MB, of de inhoud van een Flatpak-bundel. Niets van de componenten zit in het pakket van de hosttoepassing.

Voer `libera --payload-status` uit om te zien welke componenten in gebruik zijn en uit welke upstream-revisies ze gebouwd zijn.

## Waaruit het gebouwd is

Libera Suite bevat componenten van [**Euro-Office**](https://github.com/Euro-Office), een AGPL-fork van **ONLYOFFICE**, dat ontwikkeld wordt door Ascensio System SIA. Die componenten zijn aangepast; onze wijzigingen vormen de patchreeks die hieronder beschreven staat. De bewerkingscomponenten, de documentengine en de ondersteuning van formaten zijn van hen; de hosttoepassing, de verpakking en de integratie in de desktop zijn van ons.

We zijn hun allebei dankbaar. Het moeilijke deel van een kantoorsuite zijn de twintig jaar waarin geleerd is de `.docx`-bestanden van anderen correct te lezen. Dat deel erven we.

## Bijbehorende broncode {#corresponding-source}

De componenten vallen onder de AGPL, die eist dat je de broncode kunt krijgen van wat je draait, onze wijzigingen daaraan inbegrepen.

Elke release van Libera Suite schrijft drie dingen in het manifest van haar componenten:

- de precieze upstream-revisie van elke repository waaruit ze gebouwd is, vastgelegd met de commit-hash;
- de commit van Libera Suite zelf;
- de repository's waar beide op te halen zijn.

Onze wijzigingen aan upstream worden bijgehouden als een patchreeks op die vastgelegde revisies, zodat de vraag „wat heeft Libera Suite veranderd?” een kort en controleerbaar antwoord heeft. Zie [The patch queue](/en/develop/patches/), in het Engels.

We verwijzen naar openbare repository's; we bieden geen tarballs aan.
