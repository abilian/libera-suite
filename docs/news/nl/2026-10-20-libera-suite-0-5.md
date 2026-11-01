---
date: 2026-10-20
description: Libera Suite 0.5 spreekt jouw taal, toont documenten in de lettertypen die op je computer zijn geïnstalleerd, opent ze sneller en ruimt na haar eigen updates op.
---

# Libera Suite 0.5: in jouw taal, met jouw lettertypen

Libera Suite 0.5 is uit. Ze volgt nu de taal van je systeem en toont een document in de lettertypen die op je computer zijn geïnstalleerd.

Libera Suite is een vrije en open-source kantoorsuite voor Windows, macOS en Linux: Libera Words voor tekst, Libera Tables voor rekenbladen, Libera Slides voor presentaties en Libera Diagrams, een viewer voor Visio-tekeningen. Ze opent en bewaart de formaten van Microsoft Office en LibreOffice, op je eigen computer, zonder account en zonder clouddienst.

[Libera Suite installeren](../main/install.md){ .md-button .md-button--primary }

Gebruik je haar al? Sluit Libera Suite af als ze draait en voer dan het installatieprogramma of de installatieopdracht opnieuw uit, of `brew upgrade libera` als je Homebrew gebruikt. Deze versie installeert nieuwe componenten, een eenmalige download van ongeveer 90 MB.

## In jouw taal

Tot nu toe sprak de interface van Libera Suite alleen Engels. De vier toepassingen volgen nu de taal van je systeem, en met de regel `ui_language` in het [configuratiebestand](../guide/documents.md#your-name-in-documents) kies je een andere. In het Frans, Duits, Italiaans en Spaans volgen ook de menubalk, het startvenster en de dialoogvensters, en opent Help deze documentatie in die taal.

Een nieuw document begint met een lege pagina voor jouw taal en regio: A4-papier overal behalve in de Verenigde Staten, waar het vroeger voor iedereen US Letter was, en met spellingcontrole in jouw taal als Libera Suite er een woordenboek voor heeft; voor het Nederlands nog niet.

## Met jouw lettertypen

Een document in een lettertype dat je hebt geïnstalleerd, verschijnt nu ook in dat lettertype, op het scherm en in de PDF, waar het vroeger een vervanger kreeg. Libera Suite inventariseert je lettertypen als ze haar componenten installeert, en opnieuw telkens als je er een installeert of verwijdert; er wordt niets gekopieerd. De regel `installed_fonts = false` houdt het bij de lettertypen die Libera Suite meelevert.

## Sneller op het scherm

Het venster van een document opent nu meteen, terwijl het document nog wordt voorbereid. Op onze Mac staat een klein tekstdocument ongeveer een seconde eerder op het scherm. Een bestand dat Libera Suite niet kan lezen, opent nu een venster dat dat meldt, en sluit het daarna.

## Andere wijzigingen

- **Bijgewerkte componenten**, van oktober, met de correcties die upstream sinds de vorige versie zijn aangebracht.
- **Een strenger beveiligingsbeleid.** De componenten kunnen niets laden of versturen behalve naar Libera Suite zelf. De uitzondering is een afbeelding waarnaar een document via haar webadres verwijst; die wordt opgehaald zoals in elke kantoorsuite.
- **Macro's staan uit, en blijven bewaard.** De macro's van de componenten zijn JavaScript en voeren geen VBA uit documenten van Microsoft Office uit, dus staan ze uit. De macro's van een document blijven bewaard: bij het opslaan van een `.docm`, `.xlsm` of `.pptm` blijft de VBA zoals hij was, en Libera Words opent en bewaart nu `.docm`.
- **Oude componenten worden verwijderd.** Elke update liet tot nu toe de vorige versie op schijf staan, telkens ongeveer 400 MB. Een versie die vier weken door niets is gebruikt, wordt nu verwijderd.
- **Correcties.** Het lettertypemenu toont elke naam volledig. Een `.xlsb`-werkmap opent, waar die vroeger als lege presentatie opende. Op macOS blijven na afsluiten met Cmd-Q geen documenten meer vergrendeld. Op Windows toont de lijst *Recent* de naam van elk document en raakt ze geen items meer kwijt.

## Wat verdwijnt

- **Opslaan als `.xlsb`.** Het schrijven ervan liep vast op Linux. Sla in plaats daarvan op als `.xlsx`; Excel opent beide.
- **Linux op arm64, voorlopig.** Er is geen arm64-build van 0.5. Het installatiescript installeert 0.4.1 op die machines; een latere versie bouwt weer voor arm64.

[Wat vandaag werkt](../main/status.md) somt op wat gebouwd is, wat half gebouwd is en waar nog niet aan begonnen is.

## Laat het ons weten

Libera Suite is jong, en elke melding telt. De nuttigste is een document dat verkeerd uitkomt, als bijlage bij je bericht, samen met de uitvoer van `libera --diagnose`. [Feedback](../feedback.md) zegt hoe je ons bereikt.

*Abilian*
