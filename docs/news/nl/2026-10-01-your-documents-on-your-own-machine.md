---
date: 2026-10-01
description: Libera Suite, een vrije kantoorsuite voor Linux, Windows en macOS, gaat in publieke bèta. Ze opent en bewaart de formaten van Microsoft Office en OpenDocument, zonder account en zonder onlinedienst.
---

# Libera Suite gaat in publieke bèta

**Libera Suite** is een vrije kantoorsuite voor Linux, Windows en macOS. Ze bevat een tekstverwerker, een rekenblad, een presentatieprogramma en een viewer voor Visio-bestanden. Ze draait op je eigen computer, zonder account, zonder onlinedienst en zonder telemetrie. Ze opent en bewaart de formaten van Microsoft Office en OpenDocument. De publieke bèta begint vandaag.

[Libera Suite installeren](../main/install.md){ .md-button .md-button--primary }

![Libera Words, met een geopend document: de werkbalk in het paars van Libera Words, en daaronder een opgemaakte pagina.](../assets/words.png)

## Vier toepassingen

| | | |
| :--- | :--- | :--- |
| **Libera Words** | Tekstdocumenten | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | Rekenbladen | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | Presentaties | `.pptx` `.odp` |
| **Libera Diagrams** | Een viewer voor Visio-tekeningen | `.vsdx` |

Een Word-, Excel- of PowerPoint-bestand opent met de opmaak intact: lettertypen, afbeeldingen, tabellen en bijgehouden wijzigingen inbegrepen. Opslaan levert een bestand in hetzelfde formaat op, dat Microsoft Office en LibreOffice openen zoals elk ander bestand.

De vier toepassingen delen een startvenster met je recente documenten, spellingcontrole in vijf talen, export naar PDF, afdrukken en herstel van je werk na een crash.

## Vrije software, zonder kosten

Libera Suite vraagt geen licentie en geen abonnement. Je kunt ze op zoveel computers installeren als je wilt en zo lang houden als je wilt. Ze heeft geen server van ons nodig om te werken.

Het is vrije software: iedereen kan de broncode lezen, aanpassen en delen. De toepassing valt onder de Apache License 2.0 en de Euro-Office-componenten onder de GNU AGPL v3. [Licentie en naamsvermelding](../licence.md) legt uit hoe je de exacte broncode van elke versie krijgt.

## Je documenten blijven op je computer

Libera Suite leest en schrijft je documenten op je eigen schijf en stuurt ze nergens heen. Ze stuurt ons geen informatie over jou, je documenten of de manier waarop je haar gebruikt.

Ze gaat online om bij de installatie de Euro-Office-componenten te downloaden. [De documentatie somt](../index.md#what-leaves-your-machine) elke verbinding op die ze maakt, en met de broncode kun je dat controleren.

## Zo installeer je Libera Suite

- **Linux** (x86_64 en arm64): één opdracht in de terminal, die een Flatpak-pakket installeert als Flatpak aanwezig is.
- **macOS** (Apple Silicon): één opdracht in de terminal, met of zonder Homebrew.
- **Windows** 10 en 11 (x64): een installatieprogramma, zonder beheerdersrechten.

De [installatiepagina](../main/install.md) geeft de opdrachten.

## De grenzen van de bèta

Elk document heeft een eigen venster, zonder tabbladen. Niets houdt twee vensters nog tegen om hetzelfde document te bewerken: het venster dat het laatst opslaat, overschrijft het werk van het andere. Diagrams leest Visio-bestanden, maar kan ze niet opslaan. Het installatieprogramma voor Windows is nog niet ondertekend, dus Windows toont een waarschuwing als je het opent. [De statuspagina](../main/status.md) geeft de volledige lijst en wordt bijgehouden.

## Jouw feedback

De opmaakengine is grondig beproefd: als een document er in Libera Suite verkeerd uitziet, ligt de oorzaak meestal in onze verpakking, bij een ontbrekend lettertype of een ontbrekende bron. Zulke fouten zijn snel verholpen, zodra we ze zien. De nuttigste feedback is dus een document dat er verkeerd uitziet, als bijlage bij je bericht.

Kies je software voor een organisatie, laat ons dan weten welke functies die nodig zou hebben om Libera Suite in gebruik te nemen.

[Feedback](../feedback.md) legt uit hoe je ons schrijft.

## Wie haar ontwikkelt

Libera Suite wordt ontwikkeld door [Abilian](https://abilian.com), een Frans bedrijf in vrije software. Ze is gebouwd op de componenten van [Euro-Office](https://github.com/Euro-Office), een fork van [ONLYOFFICE](https://www.onlyoffice.com/), de software van Ascensio System SIA. Die componenten leveren de documentengine en de ondersteuning van de formaten. Abilian schreef de desktoptoepassing waarin ze draaien: de vensters, de menu's, het openen en opslaan van bestanden, en de verpakking.

We bouwen de Euro-Office-componenten vanuit hun broncode, op vaste revisies. De correcties die we erop toepassen, zijn [gepubliceerd en toegelicht](/en/develop/patches/).

*Abilian*

---

Microsoft, Word, Excel, PowerPoint, Visio en Windows zijn handelsmerken van de Microsoft-groep. LibreOffice is een handelsmerk van The Document Foundation. ONLYOFFICE is een handelsmerk van Ascensio System SIA. Andere namen zijn handelsmerken van hun respectieve eigenaars. Libera Suite is niet verbonden aan of goedgekeurd door een van hen.
