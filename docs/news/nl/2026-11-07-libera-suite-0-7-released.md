---
date: 2026-11-07
description: Met Libera Suite 0.7 kun je pdf's van opmerkingen voorzien, invullen en herschikken, documenten onder hun wachtwoord houden en digitale handtekeningen lezen en maken. Haar componenten worden nu met haar geïnstalleerd.
---

# Libera Suite 0.7: pdf's, wachtwoorden en handtekeningen

Libera Suite 0.7 is uit. Je kunt nu pdf's van opmerkingen voorzien, invullen en herschikken, documenten met een wachtwoord openen en opslaan, en digitale handtekeningen lezen en maken.

Libera Suite is een vrije en open-source kantoorsuite voor Windows, macOS en Linux: Libera Words voor tekst, Libera Tables voor rekenbladen, Libera Slides voor presentaties, Libera PDF voor pdf's en Libera Diagrams, een viewer voor Visio-tekeningen. Ze opent en bewaart de formaten van Microsoft Office en LibreOffice, op je eigen computer, zonder account en zonder clouddienst.

[Libera Suite installeren](../main/install.md){ .md-button .md-button--primary }

Gebruik je haar al? Sluit Libera Suite af als ze draait en voer dan het installatieprogramma of de installatieopdracht opnieuw uit, of `brew upgrade libera` als je Homebrew gebruikt. Met pip, pipx of Homebrew worden de componenten nu met de toepassing geïnstalleerd, ongeveer 100 MB, dus bij de eerste start wordt niets gedownload. Het startvenster biedt één keer aan om te verwijderen wat eerdere versies hebben gedownload, en `libera --payload-remove` doet het op elk moment.

## Pdf's

![Libera PDF met een geopende pdf, het tabblad Opmerking met zijn gereedschappen, en een opmerking op de pagina die in het paneel Opmerkingen staat.](../assets/pdf.png)

Een pdf opent in Libera PDF. Je kunt opmerkingen, markeringen, tekeningen en tekstvakken toevoegen, kleine tekstcorrecties maken, en pagina's toevoegen, verwijderen, draaien en verplaatsen. Je kunt ook formulieren invullen: een Franse Cerfa en de Amerikaanse IRS-formulieren zijn er enkele die we hebben geprobeerd.

Bij het opslaan komen je wijzigingen achter het origineel, dat in het bestand blijft zoals het was. Een pagina die je verwijdert of tekst die je corrigeert, is dus nog uit het opgeslagen bestand te halen: reken op geen van beide om iets vertrouwelijks te verwijderen uit een pdf die je verstuurt.

Bewerkte tekst loopt niet opnieuw door. Een pdf die tegen elke wijziging is gecertificeerd, kan niet worden opgeslagen: het opslaan mislukt, en het bestand blijft zoals het was. Een formulier maken of een pdf naar een document omzetten kan nog niet. Libera Suite wordt voor een pdf aangeboden bij *Openen met*, nooit als standaard. [Werken met documenten](../guide/documents.md#pdfs) heeft de details.

## Wachtwoorden

Een Word-, Excel-, PowerPoint-, OpenDocument- of pdf-bestand met een wachtwoord vraagt erom bij het openen, en blijft beveiligd bij het opslaan. Bestand ▸ Beveiligen voegt het wachtwoord van een document toe, verandert het en verwijdert het. Opslaan in een formaat dat geen wachtwoord kan bewaren (tekst, CSV, RTF, HTML, Markdown, EPUB) vraagt het eerst. Een beveiligd document waarmee is geknoeid, wordt geweigerd, dankzij een correctie van ElixirOffice.

Standaard versleutelt LibreOffice 26 OpenDocument-bestanden op een manier die Libera Suite nog niet kan lezen, en Libera Suite zegt dat in plaats van om het wachtwoord te vragen. Zolang een beveiligd document open is, is de werkkopie ervan op je schijf niet versleuteld, zodat een crash je wijzigingen niet kost. [Werken met documenten](../guide/documents.md#passwords) heeft de details.

## Digitale handtekeningen

Een ondertekend Word-, Excel- of PowerPoint-document toont zijn handtekeningen bij het openen, elk geldig of niet, en opent als alleen-lezen. *Beveiliging* ▸ *Handtekening* ondertekent er een met een sleutelbestand (PKCS#12 of PEM) en zijn wachtzin, en je kunt handtekeningen verwijderen. We hebben handtekeningen die in Libera Suite zijn gemaakt gecontroleerd met Microsoft Office en LibreOffice, en handtekeningen die door beide zijn gemaakt in Libera Suite.

*Geldig* betekent dat het document niet is veranderd sinds het is ondertekend: wie het certificaat heeft uitgegeven en of het is verlopen, wordt nog niet gecontroleerd. Een beveiligd document, een OpenDocument-bestand of een pdf ondertekenen kan nog niet. [Werken met documenten](../guide/documents.md#signatures) heeft de details.

## Andere veranderingen

- **Word 97-2003-documenten openen.** Geen enkel `.doc`-bestand had ooit geopend. Webarchieven (`.mht`), FictionBook (`.fb2`) en EPUB-boeken openen nu ook.
- **De converter start in ongeveer de helft van de tijd**, dus elk openen en opslaan gaat iets sneller.
- **Een bestand op een venster neerzetten werkt op Linux**: een document opent in een eigen venster, en een afbeelding gaat het document in. De Flatpak kan nu ook bestanden op USB-sticks en aangekoppelde schijven openen.
- **Een document dat iemand anders open heeft, zegt dat nu, in welk venster het ook opent.** Elk venster kreeg de toestand van het eerste te horen.
- **Op Windows opent een venster niet meer groter dan het scherm.**

## Beveiliging

Alle eerdere versies hebben deze problemen, dus werk alsjeblieft bij.

- **Een document kan geen afbeeldingen van je schijf meer in zichzelf kopiëren.** Een afbeelding die naar een pad op je schijf verwees, werd gekopieerd naar elk document dat ervan werd opgeslagen of geconverteerd, zodat wie het document terugstuurde ook de afbeelding meestuurde. Een gekoppelde afbeelding wordt nu alleen nog van een webadres gelezen.
- **Drie cross-site-scripting-lekken (XSS) zijn gedicht.** Een gemanipuleerd document kon een script in de editor laten draaien als je een bijgehouden wijziging selecteerde, de Functie-assistent opende of op een `javascript:`-link klikte. Alle drie worden nu als tekst getoond of geweigerd. De pagina van de editor laadt bovendien alleen nog afbeeldingen van Libera Suite, zodat een script niets meer naar buiten kan sturen in het adres van een afbeelding.
- **De converter schrijft geen stukken van zijn eigen geheugen meer in de bestanden die hij maakt.**
- **Een klein document kan de converter niet meer tot gigabytes aan geheugen brengen.**

## Ondertekende downloads, en de broncode

De Flatpak-bundels zijn ondertekend met onze OpenPGP-sleutel, en [Andere manieren om te installeren](../main/alt-install.md) zegt hoe je er een controleert. Het Windows-installatieprogramma en `Libera.app` zijn nog niet ondertekend. [Installeren](../main/install.md) zegt hoe je voorbij de waarschuwing over het installatieprogramma komt; de PowerShell-opdracht van één regel, pip, pipx en Homebrew krijgen geen waarschuwing.

De broncode van de wheels van de converter is het bronpakket `libera-core` op PyPI: de upstream-commits die het vastlegt, onze patches en de buildscripts. De broncode van de toepassing is de tag `0.7.0` van [abilian/libera-suite](https://github.com/abilian/libera-suite).

## Ongewijzigd

- **Linux op arm64** installeert nog steeds 0.4.1: er is nog geen arm64-build van 0.7.

[Wat vandaag werkt](../main/status.md) somt op wat gebouwd is, wat half gebouwd is en waar nog niet aan begonnen is, en [de roadmap](/en/develop/roadmap/), in het Engels, zegt wat er hierna komt.

## Laat het ons weten

Libera Suite is jong: elke melding telt. De nuttigste is een document dat verkeerd uitkomt, als bijlage bij je bericht, samen met de uitvoer van `libera --diagnose`. [Feedback](../feedback.md) zegt hoe je ons bereikt.

*Abilian*
