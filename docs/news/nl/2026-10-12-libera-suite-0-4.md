---
date: 2026-10-12
description: Libera Suite 0.4 markeert een document dat al elders open staat, in Libera Suite of in LibreOffice, geeft OpenDocument-bestanden getrouwer weer, en voegt slepen en neerzetten, een persoonlijk woordenboek en conversie vanaf de opdrachtregel toe.
---

# Libera Suite 0.4: veiliger in een gedeelde map, getrouwer aan OpenDocument

Libera Suite 0.4 is uit. Ze beschermt een document dat iemand anders open heeft, in Libera Suite of in LibreOffice. De componenten lezen en schrijven de OpenDocument-formaten nauwkeuriger.

[Libera Suite bijwerken](../main/install.md#update){ .md-button .md-button--primary }

Sluit Libera Suite af en voer dan het installatieprogramma of de installatieopdracht opnieuw uit, of `brew upgrade libera`. Deze versie installeert nieuwe componenten, een eenmalige download van ongeveer 100 MB.

## Documentvergrendeling

Tot nu toe hield niets twee vensters tegen om hetzelfde document te bewerken: het venster dat het laatst opsloeg, overschreef het werk van het andere. De bèta noemde dit bij haar grenzen. Versie 0.4 lost het op tussen twee vensters van Libera Suite, en tussen Libera Suite en LibreOffice. Microsoft Office ziet deze vergrendelingen nog niet, dus een document dat in Word open staat, blijft kwetsbaar.

- **Libera Suite zet een vergrendeling in het formaat van LibreOffice.** Als ze een document opent, maakt ze ernaast het kleine vergrendelingsbestand dat LibreOffice gebruikt. Ze respecteert ook de vergrendelingen die LibreOffice zet. Een document dat al elders open staat, opent *vergrendeld voor bewerking*: je kunt het lezen en wijzigen, maar bij opslaan wordt om een andere plek gevraagd. Het origineel blijft onaangeroerd.
- **Een document opnieuw openen brengt het venster naar voren**, zonder een tweede te openen.
- **Een venster toont niet-opgeslagen wijzigingen**: een stip in de sluitknop op macOS, een `*` voor de titel op Linux en Windows.

## Getrouwer aan de OpenDocument-formaten

De componenten in 0.4 bevatten **68 correcties voor de OpenDocument-formaten** (`.odt`, `.ods`, `.odp`), elk gevonden met de eigen testdocumenten van LibreOffice. Ook twee fouten in CSV zijn verholpen. Een emoji verhinderde het opslaan van een CSV; een grote CSV verloor bij het inlezen één teken op de 500.000.

## Melding van nieuwe versies

Nieuw in 0.4: hoogstens één keer per dag leest Libera Suite het nummer van de nieuwste versie op onze downloadserver. Is die nieuwer dan de jouwe, dan meldt ze dat één keer, met de stappen voor de manier waarop je haar hebt geïnstalleerd. Ze downloadt niets en stuurt niets over jou of je documenten; offline doet ze niets. De regel `check_updates = false` in het [configuratiebestand](../guide/documents.md#your-name-in-documents) schakelt dit uit.

## Andere wijzigingen

- **Slepen en neerzetten.** Een document dat je op een venster neerzet, wordt geopend; een afbeelding die je op een document neerzet, wordt ingevoegd.
- **Het persoonlijke woordenboek.** Een woord dat je met *Add to dictionary* toevoegt, blijft bewaard, voor alle documenten en alle talen.
- **Je naam in bijgehouden wijzigingen en opmerkingen**, in te stellen met `user_name` in het configuratiebestand.
- **Ctrl-N, Ctrl-O en Ctrl-W** op Linux en Windows.
- **Afdrukken** vraagt waar de PDF moet worden opgeslagen, te beginnen in de map van het document.
- **Conversie vanaf de opdrachtregel**: `libera --convert *.docx -t pdf` schrijft naast elk document een PDF, zonder een venster te openen.
- **Het venster About** toont de geïnstalleerde versie, het eerste wat je in een foutmelding vermeldt.

De resterende grenzen, waaronder het ontbreken van tabbladen en een installatieprogramma voor Windows dat nog niet ondertekend is, staan op [de statuspagina](../main/status.md).

## Problemen melden

De nuttigste melding blijft een document dat verkeerd uitkomt, als bijlage bij je bericht, samen met de uitvoer van `libera --diagnose`. [Feedback](../feedback.md) zegt hoe je ons bereikt.

*Abilian*
