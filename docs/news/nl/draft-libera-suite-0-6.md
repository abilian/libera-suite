---
date: 2026-10-26
description: Libera Suite 0.6 spreekt elke taal van haar toepassingen, maakt documenten op zoals Word als een lettertype ontbreekt, houdt Markdown-koppen en controleert Nederlandse spelling.
---

# Libera Suite 0.6: elke taal, en pagina's die afbreken zoals in Word

Libera Suite 0.6 is uit. Haar menu's en vensters spreken nu alle 44 talen van haar toepassingen, en een document waarvan je de lettertypen niet hebt, wordt opgemaakt zoals in Word.

Libera Suite is een vrije en open-source kantoorsuite voor Windows, macOS en Linux: Libera Words voor tekst, Libera Tables voor rekenbladen, Libera Slides voor presentaties en Libera Diagrams, een viewer voor Visio-tekeningen. Ze opent en bewaart de formaten van Microsoft Office en LibreOffice, op je eigen computer, zonder account en zonder clouddienst.

[Libera Suite installeren](../main/install.md){ .md-button .md-button--primary }

Gebruik je haar al? Sluit Libera Suite af als ze draait en voer dan het installatieprogramma of de installatieopdracht opnieuw uit, of `brew upgrade libera` als je Homebrew gebruikt. Deze versie installeert nieuwe componenten, een eenmalige download van ongeveer 90 MB.

## Elke taal

Sinds 0.5 volgen de toepassingen de taal van je systeem, maar de menubalk, het startvenster en de dialoogvensters deden dat alleen in het Frans, Duits, Italiaans en Spaans. Nu volgen ze in alle 44 talen, van Arabisch tot Vietnamees, het Nederlands inbegrepen, en in het Arabisch, Hebreeuws en Urdu loopt het startvenster van rechts naar links.

Alleen de Franse, Duitse, Italiaanse en Spaanse vertaling is nagelezen door iemand met die taal als moedertaal. De andere, ook de Nederlandse, zijn concepten: staat er een verkeerd of onhandig woord in jouw taal, [laat het ons weten](../feedback.md), en je verbetering komt in de volgende versie.

## Pagina's die afbreken zoals in Word

Vraagt een document om een lettertype dat je computer niet heeft, dan vervangt Libera Suite het nu zoals Word:

- **Calibri, Cambria, Arial, Times New Roman en Courier New** krijgen Carlito, Caladea en Liberation, die dezelfde breedtes hebben, zodat regels en pagina's afbreken op dezelfde plaatsen als in Word. Op een Mac ging Calibri naar het geïnstalleerde lettertype dat er het meest op leek, zodat hetzelfde document van computer tot computer anders opgemaakt kon zijn.
- **Een lettertype dat ook Word niet zou kennen,** krijgt de vervanger van Calibri, zoals Word het in Calibri zet, waar het eerder Liberation Sans kreeg. Twee documenten uit onze testset hebben nu het aantal pagina's van Word.
- **Tekens uit Wingdings, Webdings en Symbol** verschijnen als de symbolen waarvoor ze staan: een ster, een vinkje, een smiley, waar een ontbrekend Wingdings letters toonde.

## Andere wijzigingen

- **Markdown houdt zijn koppen.** Een Markdown-bestand dat je opende, bewerkte en bewaarde, maakte van elke kop een vette alinea.
- **Nederlandse spellingcontrole**, met het woordenboek van OpenTaal. Elk woordenboek komt nu met zijn licentie.
- **Op Linux toont het menu Bestand zijn sneltoetsen:** Nieuw, Openen en Sluiten tonen Ctrl-N, Ctrl-O en Ctrl-W.
- **Een OpenDocument-bestand zonder basispaginastijlen houdt zijn stijlen**, waar elke alinea eerder in de standaardstijl openging.

## Wat hetzelfde blijft

- **Linux op arm64** installeert nog steeds 0.4.1: er is nog geen arm64-build van 0.6.

[Wat vandaag werkt](../main/status.md) somt op wat gebouwd is, wat half gebouwd is en waar nog niet aan begonnen is.

## Laat het ons weten

Libera Suite is jong, en elke melding telt. De nuttigste is een document dat verkeerd uitkomt, als bijlage bij je bericht, samen met de uitvoer van `libera --diagnose`. [Feedback](../feedback.md) zegt hoe je ons bereikt.

*Abilian*
