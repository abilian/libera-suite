# Libera Suite

**Libera Suite** is een vrije en opensource kantoorsuite voor Windows, macOS en Linux, gemaakt door Abilian. Schrijf documenten, werk aan spreadsheets en maak presentaties op je eigen computer, met je eigen bestanden, zonder account en zonder clouddienst.

Ze opent en bewaart de bestandsformaten van Microsoft Office en LibreOffice, zodat je documenten kunt uitwisselen met iedereen, welke software die ook gebruikt. Het is een gratis alternatief voor Microsoft Word, Excel en PowerPoint, en omdat het vrije software is, mag iedereen de broncode lezen, aanpassen en delen.

- **Libera Words**, voor tekst: `.docx`, `.odt`, `.rtf`, `.txt`, `.md` en meer
- **Libera Tables**, voor spreadsheets: `.xlsx`, `.ods`, `.csv`
- **Libera Slides**, voor presentaties: `.pptx`, `.odp`
- **Libera Diagrams**, een viewer voor Visio-tekeningen (`.vsdx`)

![Libera Words met een geopend document: de werkbalk in het paars van Libera Words, met daaronder een opgemaakte pagina.](assets/words.png)

[Libera Suite installeren](main/install.md){ .md-button .md-button--primary }

## In zes dia's

<div class="deck" data-pdf="/en/pdf/Libera%20Suite.pdf"><a href="/en/pdf/Libera%20Suite.pdf">Libera Suite, in zes dia's (PDF)</a></div>

## Waar het project staat

Alle vier werken vandaag al, op **Windows** 10 en 11 (x64), **Linux** (x86_64, en arm64 met versie 0.4.1) en **macOS** (Apple Silicon). Het project is jong. [Wat vandaag werkt](main/status.md) is een overzicht van de stand van zaken: wat af is, wat half af is en waar nog niet aan begonnen is.

Wil je het uitproberen, begin dan met [Installeren](main/install.md): op Linux en macOS volstaat één opdracht, Windows heeft een installatieprogramma. Wil je het zelf bouwen, begin dan met het [overzicht voor ontwikkelaars](/en/develop/), in het Engels. Hoe dan ook: [laat ons weten hoe het ging](feedback.md).

## Waarom

Het meeste werk in een kantoorsuite zit in de documentengine, het deel dat een `.docx` uit andermans software leest en die opmaakt zoals de auteur het bedoelde. Die engine bestaat al als vrije software en werkt al offline. De bewerkingscomponenten van Libera Suite zijn die van [Euro-Office](https://github.com/Euro-Office), een AGPL-fork van ONLYOFFICE van Ascensio System SIA, die lokaal draaien met dezelfde documentengine en dezelfde ondersteuning van formaten. Wat de engine nog miste, was een desktoptoepassing die klein genoeg is om door één team beheerd te worden.

Libera Suite is die toepassing: een paar duizend regels Python en JavaScript. Al het andere komt van upstream.

## Wat je computer verlaat {#what-leaves-your-machine}

Niets wat je niet zelf verstuurt. Libera Suite stuurt je documenten uit zichzelf nergens heen: ze gaan waar jij ze heen stuurt.

Libera Suite heeft **geen telemetrie**, geen gebruiksstatistieken, geen crashrapporten en geen accounts: ze stuurt ons niets over jou, je documenten of de manier waarop je haar gebruikt. Als er ooit iets van die aard bijkomt, staat het uit tot jij het aanzet.

Ze maakt wel verbinding met onze server om dingen te downloaden. Op dit moment zijn dat de componenten, wanneer je Libera Suite installeert en opnieuw wanneer een nieuwe versie nieuwe componenten nodig heeft. Hooguit één keer per dag vraagt ze ook of er een nieuwere versie is, en meldt dat één keer; ze downloadt niets en vertelt je hoe je bijwerkt. Zoals elk webverzoek laat elk van deze downloads onze server je IP-adres zien, en verder niets over jou.

De tabel noemt elke verbinding die de toepassing vandaag maakt, zodat je dit zelf kunt controleren. Elke nieuwe verbinding, controles op updates inbegrepen, verschijnt hier in de versie die haar toevoegt.

| | |
| :--- | :--- |
| **De componenten** | Gedownload van `cdn.abilian.com` wanneer je Libera Suite installeert, en daarna alleen opnieuw wanneer een nieuwe versie nieuwe componenten nodig heeft. Elke download wordt gecontroleerd aan de hand van hashes die in de toepassing zelf zitten. |
| **De controle op updates** | Hooguit één keer per dag het versienummer van de nieuwste release, gelezen van `cdn.abilian.com`. Een nieuwere versie wordt één keer gemeld; er wordt niets gedownload. Offline gebeurt er niets. `check_updates = false` in het [configuratiebestand](guide/documents.md#your-name-in-documents) zet de controle uit. |
| **Het eigen verkeer van de componenten** | Een webserver op `127.0.0.1` die deel uitmaakt van de toepassing en de componenten aan een venster op dezelfde computer levert. Een andere computer kan hem niet bereiken. Een programma op jouw computer krijgt alleen antwoord als het een sleutel laat zien die alleen jouw account kan lezen. De pagina van de componenten mag niets anders bereiken, op afbeeldingen na waarnaar een document verwijst. |
| **Afbeeldingen waarnaar een document verwijst** | Een document kan een afbeelding tonen via haar webadres in plaats van haar zelf te bevatten. Libera Suite haalt haar dan op van dat adres wanneer het document wordt geopend of geconverteerd, zoals elke kantoorsuite doet, en die server ziet je IP-adres. Het document zelf wordt niet verstuurd. |
| **Links waarop je klikt** | Help en dergelijke openen in *jouw* browser. Libera Suite haalt ze niet zelf op. |

Je documenten worden gelezen en geschreven op je eigen schijf, door een converter op je eigen schijf. Ze worden nooit geüpload, geïndexeerd of bekeken.

## Licentie en broncode

Libera Suite is vrije software: de hosttoepassing valt onder de [Apache-2.0](licence.md), en de componenten die ze draait vallen onder de AGPL v3, net als de Euro-Office-code waaruit ze gebouwd worden. Elke release legt de precieze upstream-revisies vast waaruit ze gebouwd is en de patches die daarop zijn toegepast. De bijbehorende broncode is dus altijd een commit plus een patchreeks waarvan aantoonbaar is dat ze erop van toepassing is.

---

Microsoft, Word, Excel, PowerPoint, Visio en Windows zijn handelsmerken van de Microsoft-groep. LibreOffice is een handelsmerk van The Document Foundation. ONLYOFFICE is een handelsmerk van Ascensio System SIA. Andere namen zijn handelsmerken van hun respectieve eigenaren. Libera Suite is niet verbonden aan en wordt niet onderschreven door een van hen.
