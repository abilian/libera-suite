# Wat vandaag werkt

Libera Suite is jong. Deze pagina is een overzicht van de stand van zaken: wat af is, wat half af is en waar nog niet aan begonnen is.

De menubalk, het startvenster en de dialoogvensters van Libera Suite zijn in het Nederlands, net als de componenten. Die vertaling van Libera Suite zelf is nog niet nagelezen door iemand met Nederlands als moedertaal: zie je een verkeerd of onhandig woord, [laat het ons weten](../feedback.md). Menu's en knoppen staan hier zoals je ze op het scherm ziet.

## Wat werkt

| | |
| :--- | :--- |
| **Vier programma's** | Windows 10 en 11 op x64, Linux op x86_64 (arm64 met 0.4.1), macOS op Apple Silicon. Words, Tables en Slides bewerken; Diagrams leest Visio-bestanden. |
| **Openen en opslaan** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Opslaan, Opslaan als, Nieuw. |
| **Exporteren** | Save As biedt per programma een lijst met formaten, pdf inbegrepen. Elk aangeboden formaat is gecontroleerd door er een document naar te converteren en de tekst ervan terug te lezen. |
| **Afbeeldingen** | Blijven behouden bij openen en opslaan; Invoegen ▸ Afbeelding werkt. |
| **Afdrukken** | Maakt een pdf, vraagt waar je die wilt bewaren en opent hem in je pdf-viewer. |
| **Spellingcontrole** | Zes talen, met suggesties. Zie hieronder. |
| **In je eigen taal** | De componenten volgen de taal van je systeem, en een nieuw document begint met het lege sjabloon van je regio: A4-papier overal behalve in de VS, en spellingcontrole in je eigen taal als daar een woordenboek voor is (zie [Spellingcontrole](#spell-checking)). De menubalk, het startvenster en de dialoogvensters volgen ook, in elke taal van de toepassingen, en in het Arabisch, Hebreeuws en Urdu loopt het startvenster van rechts naar links. Alleen de Franse, Duitse, Italiaanse en Spaanse vertaling is nagelezen door iemand met die taal als moedertaal; de andere, de Nederlandse inbegrepen, zijn concepten, en [verbeteringen zijn welkom](../feedback.md). |
| **Recente documenten** | Bestand ▸ Recent openen onthoudt de laatste 20. |
| **Meerdere documenten tegelijk** | Van elk type, elk in een eigen venster, of op macOS elk in een eigen tabblad als het systeem tabbladen verkiest: via Bestand ▸ Nieuw of Bestand ▸ Openen, door te dubbelklikken in je bestandsbeheerder, of met `libera *.docx`. Het bestandstype bepaalt welk programma het document opent. |
| **Tussen je programma's** | Op Windows zet het installatieprogramma Libera Suite in het menu Start, op het bureaublad en onder *Openen met* in Verkenner. Op Linux voegt de Flatpak het met pictogram en bestandskoppelingen toe aan het toepassingenmenu, en `libera --launcher-install` doet hetzelfde voor elke andere installatie. Op macOS zet het installatiescript `Libera.app` in je map Programma's, en `libera --launcher-install` doet hetzelfde na Homebrew: de Finder biedt het aan onder *Open met*, en het Dock toont zijn pictogram en naam. |
| **Een startvenster** | `libera` zonder argumenten: nieuw, openen, recent, en waar de componenten vandaan komen. |
| **Herstel na een crash** | Niet-opgeslagen wijzigingen worden je teruggeboden wanneer je het document opnieuw opent. |
| **Een document dat elders open is** | Open je een document dat LibreOffice of een ander exemplaar van Libera Suite al open heeft, dan wordt het gemarkeerd als *vergrendeld voor bewerken*: je kunt het lezen en wijzigen, en bij opslaan wordt gevraagd waar, zodat het bestand van het andere exemplaar nooit wordt overschreven. Open je een document dat al in een venster staat, dan komt dat venster naar voren. Microsoft Office en Libera Suite zien elkaars vergrendelingen niet, dus een document dat in Word open is, is niet beschermd. |
| **Sluiten vraagt eerst** | Een venster met niet-opgeslagen wijzigingen biedt Opslaan, Niet opslaan of Annuleren aan. |
| **Een menubalk** | Bestand, Bewerken, Weergave en Help op elk platform. macOS voegt Venster toe, en de gebruikelijke sneltoetsen. |
| **Over** | Wie de componenten geschreven heeft, en onder welke licentie: `Bestand ▸ Over` in het documentvenster, en `Help ▸ Over Libera Suite` op Linux en Windows. macOS zet het in het programmamenu. |
| **Instellingen blijven bewaard** | Thema, maateenheden, taal van de spellingcontrole en dergelijke staan na een herstart nog steeds goed. |
| **Installatie van de componenten** | Van de server, of uit een lokale map met gebouwde artefacten. In beide gevallen wordt elk artefact gecontroleerd aan de hand van hashes die in de toepassing zelf zitten. |

## Bekende problemen

**Geen van deze hoef je te melden**: we kennen ze al. De secties hieronder geven de details.

| | |
| :--- | :--- |
| **macOS spreekt van een onbekende ontwikkelaar** | Alleen bij een `Libera.app` die vanuit een kopie van de broncode is gebouwd: die is niet ondertekend met een Developer ID, dus Gatekeeper maakt de eerste keer bezwaar. [Andere manieren om te installeren](alt-install.md#a-double-clickable-application-on-macos) legt uit hoe je daarlangs komt. Een installatie via `pip`, `pipx` of Homebrew heeft er nooit last van. |
| **Gestart vanuit een terminal, toont het Dock „Python”** | Alleen wanneer je `libera` op macOS in een terminal start. Een symbool in het Dock krijgt de naam van de bundel waaruit het gestart is: hier die van de Python-interpreter, en daar kan niets in de toepassing iets aan veranderen. Het pictogram en de menubalk zijn hoe dan ook van ons; `Libera.app` toont gewoon Libera. Een document dat je op dat Python-symbool sleept, wordt in naam van Python geweigerd; het symbool van `Libera.app` neemt het wel aan. |
| **Diagrams kan niet opslaan** | Het opent een `.vsdx` en toont die. De converter kan geen enkel Visio-formaat schrijven, dus er valt niets op te slaan en er is geen leeg sjabloon om mee te beginnen. |
| **Geen pdf-bewerking** | Pdf's worden alleen geschreven. Een pdf openen om te bewerken is nog niet aangesloten. |
| **Een beperkte menubalk, met weinig zichtbare sneltoetsen op Linux en geen op Windows** | Linux en Windows krijgen Bestand, Bewerken, Weergave en Help, getekend in het venster. Op Linux tonen Nieuw, Openen en Sluiten Ctrl-N, Ctrl-O en Ctrl-W, en geen ander item toont zijn toets; op Windows geen enkel. De toetsen werken wel: Ctrl-N, Ctrl-O, Ctrl-W, Ctrl-S, Ctrl-Shift-S, Ctrl-P en Ctrl-Z. macOS krijgt die menu's plus Window, met de gebruikelijke sneltoetsen. |
| **Geen tabbladen op Linux en Windows** | Daar één venster per document. macOS heeft tabbladen. |
| **Windows waarschuwt voor het installatieprogramma** | Het gedownloade installatieprogramma is nog niet digitaal ondertekend, dus SmartScreen zegt de eerste keer *„Windows heeft uw pc beschermd”*. [Installeren](install.md#windows) legt uit hoe je daarlangs komt. De installatie met één regel PowerShell heeft er nooit last van. |

Loop je tegen iets aan dat *niet* op deze lijst staat, [laat het ons weten](../feedback.md).

## Half af

**De menubalk op Linux en Windows.** Die wordt in het venster getekend, met Bestand, Bewerken, Weergave en Help, en elk item werkt. Op Linux tonen Nieuw, Openen en Sluiten hun sneltoets, en geen ander item; op Windows geen enkel. De gebruikelijke toetsen werken wel. Ctrl-N maakt een nieuw document van hetzelfde type en Ctrl-O opent er een. Ctrl-W sluit het venster en vraagt eerst wat er met niet-opgeslagen wijzigingen moet gebeuren. De eigen Ctrl-S, Ctrl-Shift-S (Opslaan als), Ctrl-P en Ctrl-Z van de componenten werken ook. Op Windows zijn Ctrl-N, Ctrl-O en Ctrl-W nog niet op een echte machine gecontroleerd. File ▸ New ▸ Document, Spreadsheet of Presentation werkt, net als de tegels New in het startvenster en het eigen tabblad Bestand van het document.

**`Libera.app` op macOS.** Het installatiescript zet hem in je map Programma's, en `libera --launcher-install` doet hetzelfde na elke andere installatie. Hij opent een document als je erop dubbelklikt of het op zijn symbool in het Dock sleept, staat in *Open met* en toont het Libera-logo in het Dock. Maar het is een starter rond de Python van je installatie (niets is ingebed, ondertekend of genotariseerd), dus nog niet iets wat je aan iemand anders kunt geven.

## Nog niet begonnen

### In het documentvenster

- **Documenten met een wachtwoord.** Openen noch opslaan.
- **Digitale handtekeningen.**
- **Afdruk samenvoegen.**
- **Plug-ins.** In deze fork upstream uitgeschakeld, dus het paneel verschijnt nooit.
- **Macro's.** Uitgeschakeld. De eigen macro's van de componenten zijn JavaScript en voeren geen VBA uit documenten van Microsoft Office uit, dus de macro's van een document worden niet uitgevoerd. Ze blijven wel bewaard: bij het opslaan van een `.docm`, `.xlsm` of `.pptm` blijft de VBA zoals hij was. [De roadmap](/en/develop/roadmap/), in het Engels, beschrijft wat ervoor in de plaats komt.

### In de toepassing

- **Tabbladen op Linux en Windows.** Daar één venster per document, die de taakbalk groepeert.
- **Een toepassing voor macOS die je kunt doorgeven.** `Libera.app` gebruikt de Python van je eigen installatie en bevat geen interpreter en geen componenten. Windows heeft er wel een: het installatieprogramma brengt alles mee.
- **Automatische updates** en **code-ondertekening**. macOS behandelt een `Libera.app` die vanuit een kopie van de broncode is gebouwd als software van een onbekende ontwikkelaar. Windows waarschuwt voor het gedownloade installatieprogramma.
- **Offline help**, leesbaar zonder browser of netwerk. Het menu Help opent deze site; About werkt offline. Zie hieronder.

### Elders

- **Diagrammen bewerken.** Diagrams opent een `.vsdx` en toont die. De converter kan geen enkel Visio-formaat schrijven, dus er valt niets op te slaan en er is geen leeg sjabloon om mee te beginnen.
- **Pdf-bewerking.** Upstream heeft een component om pdf's te bewerken. Libera Suite installeert die nog niet, omdat de hosttoepassing er nog geen pdf in kan openen.
- **Samenwerken, cloudopslag, accounts, telemetrie.** Niets daarvan is gebouwd, en aan niets daarvan wordt gewerkt. [De roadmap](/en/develop/roadmap/), in het Engels, beschrijft hoe elk ervan eruit zou zien als het er kwam. [Wat je computer verlaat](../index.md#what-leaves-your-machine) noemt al het netwerkgebruik van de toepassing.

## Toelichting bij enkele ontbrekende onderdelen

### Help

Er is een menu **Help**, op elk platform, en het opent deze site in je browser. Er zit geen help *in* de toepassing, waar je hem zou kunnen lezen terwijl je computer offline is. Upstream levert een volledige handleiding mee. Libera Suite laat die weg: ze beschrijft ONLYOFFICE en weegt 84 MB in acht talen. Offline help komt terug zodra er genoeg eigen documentatie is om mee te leveren.

### Spellingcontrole {#spell-checking}

Libera Suite levert woordenboeken mee voor **Engels (VS en VK), Frans, Duits, Spaans, Italiaans en Nederlands**: 12 MB met hun licenties, gekozen omdat de volledige set 327 MB is. Een taal toevoegen kost één regel in `build/payload/dictionaries.txt` en een nieuwe build van de componenten.

Een taal zonder woordenboek is geen fout: de woorden worden dan gewoon als correct beschouwd, zoals de eigen desktoptoepassing van upstream ook doet. Woorden die je toevoegt met *Toevoegen aan woordenboek* blijven bewaard, voor elk document en elke taal.

Hoe je de taal van een document instelt, staat in [Werken met documenten](../guide/documents.md#spell-checking).

### Je naam in documenten

Bijgehouden wijzigingen en opmerkingen worden aan een persoon toegeschreven, wiens naam in het opgeslagen bestand wordt geschreven. Libera Suite haalt die uit je account: de volledige naam waaronder macOS je kent, de weergavenaam van je Windows-account, of het veld voor de volledige naam van je Unix-account op Linux. Een andere naam kun je instellen in het configuratiebestand; daar is nog geen menu-item voor. [Werken met documenten](../guide/documents.md#your-name-in-documents) geeft de details.

### Lettertypen

Libera Suite levert een basisset lettertypen mee: Liberation, Carlito, Caladea, Open Sans en een paar andere, genoeg om gewone documenten getrouw weer te geven, voor 7 MB. De volledige set is 248 MB. Een document dat om een lettertype buiten die set vraagt, gebruikt het lettertype dat op je computer geïnstalleerd is, op het scherm en in de pdf, en krijgt alleen een vervanger als je computer het ook niet heeft. Calibri, Cambria, Arial, Times New Roman en Courier New zijn de uitzondering: als je computer ze niet heeft, krijgt een document Carlito, Caladea of Liberation, die dezelfde breedtes hebben, zodat de pagina's op dezelfde plaatsen afbreken als in Word, welke lettertypen er verder ook geïnstalleerd zijn. Libera Suite maakt een lijst van je lettertypen bij de eerste start, en opnieuw op de achtergrond telkens wanneer je er een installeert of verwijdert; de vensters die je daarna opent, gebruiken de nieuwe lijst. Of de set wordt uitgebreid, vooral voor Chinees, Japans en Koreaans, is nog niet beslist.

### Getrouwe weergave

De opmaakengine komt van upstream en is volwassen. Zie je iets wat niet klopt, dan ligt de oorzaak waarschijnlijker bij onze verpakking (een ontbrekend lettertype, een ontbrekende resource). Daarom zijn zulke meldingen extra nuttig; stuur ons [feedback](../feedback.md) met het bestand.
