# Libera Suite gebruiken

Libera Suite opent een document in een venster, waarna je het kunt bewerken en opslaan. Words, Tables en Slides werken allemaal zo; Diagrams opent Visio-bestanden om te lezen.

Begin bij [Installeren](../main/install.md). Deze drie pagina's zijn bedoeld om op volgorde te lezen:

1. [Installeren](../main/install.md): het op je computer zetten, met één opdracht.
2. [Werken met documenten](documents.md): openen, opslaan, exporteren, afdrukken.
3. [Wat vandaag werkt](../main/status.md): wat er gebouwd is, en de problemen die we al kennen.

Elk programma heeft zijn eigen kleur. Verder is het venster overal hetzelfde:

![Libera Tables met een leeg werkblad; de werkbalk heeft het blauwgroen van Libera Tables.](../assets/tables.png)

![Libera Slides met een titeldia; de werkbalk heeft het goud van Libera Slides.](../assets/slides.png)

## Hoe het in elkaar zit

Libera Suite bestaat uit twee delen, die apart verpakt zijn.

**De applicatie** is een klein Python-pakket van een paar honderd kilobyte: het venster, de opdrachtregel en de host waarmee de componenten communiceren.

**De componenten** zijn al het andere: de documentengine, de bewerkingscomponenten, de lettertypen. De opdrachtregel noemt ze de *payload*. Gecomprimeerd zijn ze ongeveer 100 MB, in twee eigen Python-pakketten, `libera-core` en `libera-web`.

Ze hebben elk hun eigen versienummer. De applicatie controleert of de componenten die ze vindt de verwachte zijn. Een correctie in de applicatie betekent dus niet dat je de componenten opnieuw moet downloaden.

Elke manier van installeren brengt beide mee. Het Windows-installatieprogramma en de Linux-Flatpak bevatten ze, en pip installeert de componenten samen met de applicatie, die ze vereist.

## Wat het niet is

Libera Suite praat met geen enkele server, heeft geen account nodig en uploadt je documenten nooit uit zichzelf. De componenten draaien als lokale webinhoud, via `127.0.0.1` geserveerd aan een venster op je eigen computer. Er is geen samenwerking, geen cloudopslag en geen telemetrie, omdat niets daarvan gebouwd is.
