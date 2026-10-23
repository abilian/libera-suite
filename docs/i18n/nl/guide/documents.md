# Werken met documenten

De menu's en vensters van Libera Suite zelf zijn in het Engels; die van de componenten zijn in het Nederlands. Menu's en knoppen staan hier zoals ze op het scherm verschijnen.

## Openen {#open}

```sh
libera                             # het startvenster
libera ~/Documents/notitie.docx
libera ~/Documents/budget.xlsx
libera ~/Documents/netwerk.vsdx
```

**Het document bepaalt welk programma je krijgt.** Er is geen opdracht om er een te kiezen, net zoals je geen teksteditor kiest voor een `.txt`: je opent het document en het juiste programma verschijnt. Een `.xlsx` opent in Tables, een `.pptx` in Slides, een `.vsdx` in Diagrams.

![Het startvenster, met een tegel New voor elk van Document, Spreadsheet en Presentation, een knop Open, en een lijst Recent met drie documenten.](../assets/start.png)

`libera` zonder meer opent het **startvenster**: een nieuw document van elke soort, een dialoogvenster om te openen, je recente documenten, en waar de componenten vandaan komen. Kies iets en het startvenster verdwijnt; het document blijft.

Libera Suite opent **één document per venster**, dus een jokerteken van de shell doet wat je ervan verwacht:

```sh
libera ~/Documents/*.docx     # elk in een eigen venster
```

Je kunt een document ook vanuit een open document openen, via **Bestand ▸ Openen** of **Bestand ▸ Recente openen**. Allebei openen ze een nieuw venster; het document dat je al open hebt, blijft ongemoeid.

**Op macOS kunnen documenten als tabbladen** van één venster openen. Libera Suite volgt de systeeminstelling *Open documenten in tabbladen* in Systeeminstellingen ▸ Bureaublad en Dock, zoals elk documentprogramma op de Mac. Staat die op *Altijd*, dan opent elk document als tabblad. Anders opent het in een eigen venster, en **Window ▸ Merge All Windows** voegt ze samen. De **+** aan het eind van de tabbladbalk opent het startvenster als nieuw tabblad, en het document dat je daar kiest neemt de plaats ervan in. Een tabblad sleep je naar buiten tot een eigen venster.

**Een document dat je** op een venster van Libera Suite sleept, het startvenster inbegrepen, opent in een eigen venster. Een afbeelding die je op een document sleept, wordt erin ingevoegd.

**File ▸ New** biedt vanuit elk venster een Document, een Spreadsheet of een Presentation aan, elk in een eigen venster. Op macOS maakt `⌘N` er een van dezelfde soort als het voorste venster. Binnen het document zelf krijg je dezelfde keuze via **Bestand ▸ Nieuw maken**.

## Opslaan

**Bestand ▸ Opslaan** schrijft terug naar het document dat je hebt geopend. **Bestand ▸ Opslaan als** vraagt waar het heen moet. Vanaf dan is dat het document dat je bewerkt.

Bij het opslaan wordt het werkformaat weer omgezet in een echt document; dat duurt ongeveer een seconde.

## Exporteren

Met Opslaan als exporteer je ook: het dialoogvenster heeft een keuzelijst **File Format**.

| | |
| :--- | :--- |
| Word Document | `.docx` |
| Word Template | `.dotx` |
| OpenDocument Text | `.odt` |
| OpenDocument Template | `.ott` |
| PDF | `.pdf` |
| Rich Text Format | `.rtf` |
| HTML | `.html` |
| Markdown | `.md` |
| EPUB | `.epub` |
| FictionBook | `.fb2` |
| Plain Text | `.txt` |

Een formaat kiezen geeft het bestand in het dialoogvenster een andere naam. Het dialoogvenster laat de twee niet uit elkaar lopen: je kunt niet eindigen met een ODT die `.docx` heet.

Niet elk formaat dat de converter kan lezen, kan hij ook schrijven. Vooral `.doc` opent wel maar wordt niet opgeslagen; gebruik `.docx` of `.rtf` voor iets dat terug moet naar een oude Word.

Zoek je in het menu Bestand naar **Downloaden als**, dan is dat er niet. De componenten verbergen het wanneer ze als offline desktopapplicatie draaien, en zetten Opslaan als op die plek: hetzelfde werk, één menu-item eerder.

### Vanaf de opdrachtregel {#from-the-command-line}

`libera --convert` doet hetzelfde zonder een venster te openen, voor één document of honderd. Het formaat geef je aan met zijn extensie, met `-t`, of het volgt uit de naam die je aan `-o` geeft:

```sh
libera --convert *.docx -t pdf             # rapport.pdf naast rapport.docx, enzovoort
libera --convert lezing.pptx -o lezing.odp # één document, met naam
libera --convert *.xlsx -t ods --outdir ods/
libera --convert rapport.docx -t pdf -o - | lp   # naar de standaarduitvoer
```

Een bestand dat al onder de nieuwe naam bestaat, wordt vervangen. Het bestand dat geconverteerd wordt, wordt nooit overschreven, en twee bestanden die onder dezelfde naam zouden eindigen, worden geweigerd voordat er iets geconverteerd wordt. De opties zijn die van pandoc, alleen zonder `-f`: de extensie zegt wat een bestand is.

## De menubalk

Op Linux en Windows zit de balk in het venster: **File**, **Edit**, **View** en **Help**, met in die laatste *Libera Help* en *About Libera Suite*. Wat het menu daar biedt, levert drie verschillen op. Op Linux tonen New, Open en Close Ctrl-N, Ctrl-O en Ctrl-W, en geen ander item toont zijn toets; op Windows geen enkel. Ctrl-N, Ctrl-O, Ctrl-W, Ctrl-S, Ctrl-Shift-S, Ctrl-P en Ctrl-Z doen wat de ⌘-toetsen hieronder op een Mac doen. **Open Recent** wordt opgebouwd wanneer de applicatie start, dus een document dat je vandaag opent, verschijnt er morgen in. Niets wordt grijs, dus Save zonder iets om op te slaan doet niets.

Op macOS is het een echte Mac-menubalk, met dezelfde items plus **Window**. De gebruikelijke sneltoetsen werken daar, of het document nu de focus heeft of niet:

| | |
| :--- | :--- |
| `⌘N` `⌘O` | New (van de soort van het voorste venster), Open: elk in een eigen venster of tabblad |
| `⌘S` `⇧⌘S` | Save, Save As |
| `⌘P` | Print |
| `⌘W` | Close, met eerst een vraag over niet-opgeslagen wijzigingen |
| `⌘Z` `⇧⌘Z` | Undo, Redo |
| `⌘F` | Find |
| `⌘?` | Deze documentatie |
| `⌘+` `⌘-` `⌘0` | Zoom In, Zoom Out, Fit Page |
| `⌘8` | Formatting Marks |

**File ▸ Open Recent** wordt opnieuw opgebouwd telkens als je het opent. Het menu **Window** toont alle geopende documenten.

Save, Undo en Redo zijn grijs als er niets op te slaan of ongedaan te maken is. De componenten weigeren die opdrachten zonder iets te zeggen: een menu-item dat beschikbaar bleef, zou kapot lijken.

## Sluiten

Wie een venster met niet-opgeslagen wijzigingen sluit, krijgt eerst een vraag: **Save**, **Don't Save** of **Cancel**.

Kiezen voor Don't Save is niet definitief. Libera Suite bewaart wat je geschreven hebt, en biedt het opnieuw aan wanneer je dat document de volgende keer opent.

## Afdrukken

**Bestand ▸ Afdrukken**, of de printerknop, zet het document om in een pdf, vraagt waar die moet blijven (in de map van het document, tenzij je een andere kiest), en opent hem in de pdf-viewer van je systeem, waar het afdrukvenster zit.

Dat is voorlopig de keuze: de viewer die je al hebt, geeft je paginabereiken, papierformaat, schalen en een voorbeeld, en niets daarvan zouden we in een eerste versie beter bouwen.

## Afbeeldingen

Afbeeldingen die in een document zijn ingesloten, blijven bewaard bij openen en opslaan. **Invoegen ▸ Afbeelding** voegt een afbeelding van schijf toe.

## Spellingcontrole {#spell-checking}

Spelfouten worden onderstreept, en met de rechtermuisknop krijg je suggesties. Welk woordenboek gebruikt wordt, volgt **de taal van het document**, die je per document instelt in de **statusbalk** onder in het venster.

Er worden woordenboeken voor vijf talen meegeleverd: Engels (VS en VK), Frans, Duits, Spaans en Italiaans. Een taal zonder woordenboek is geen fout; de woorden ervan gelden gewoon als juist. Woorden die je toevoegt met *Toevoegen aan woordenboek* blijven bewaard: vanaf dan zijn ze juist in elk document en elke taal.

## Je naam in documenten {#your-name-in-documents}

Bijgehouden wijzigingen en opmerkingen worden toegeschreven aan een persoon, wiens naam in het opgeslagen bestand wordt geschreven. Libera Suite haalt die uit je account: je volledige naam zoals macOS die kent, de weergavenaam van je Windows-account, of het veld voor de volledige naam van je Unix-account op Linux, en anders je inlognaam.

Wil je een andere naam gebruiken, zet die dan in het configuratiebestand, en maak het bestand aan als het er niet is:

```toml
user_name = "Jeanne Dupont"
```

| | |
| :--- | :--- |
| Linux | `$XDG_CONFIG_HOME/libera/config.toml`, of `~/.config/libera/config.toml` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/config/libera/config.toml` |
| macOS | `~/Library/Application Support/Libera Suite/config.toml` |
| Windows | `%USERPROFILE%\.config\libera\config.toml` |

De naam geldt voor de vensters die geopend worden nadat Libera Suite opnieuw is gestart. Documenten die eerder zijn opgeslagen, houden de naam waarmee ze zijn opgeslagen.

Hetzelfde bestand zet de dagelijkse controle op een nieuwere versie uit, met een eigen regel:

```toml
check_updates = false
```

Een andere regel houdt het bij de lettertypen die Libera Suite meelevert, zonder die op je computer geïnstalleerd zijn, zodat een document er op elke computer hetzelfde uitziet:

```toml
installed_fonts = false
```

En een laatste stelt de taal van de programma's in, als die niet die van je systeem moet zijn. Een nieuw document neemt zijn papierformaat nog steeds over van de regio van je systeem:

```toml
ui_language = "fr"
```

Wil je voor één keer een ander bestand gebruiken, zonder dit bestand aan te raken, geef het dan op met `libera --config BESTAND` (of `-c BESTAND`), of in de omgevingsvariabele `LIBERA_CONFIG`. Een Libera Suite die zo gestart is, geeft zijn documenten niet door aan een exemplaar dat al draait en ze met zijn eigen configuratie zou openen: sluit dat eerst af.

## Waar je werkbestanden staan

Zolang een document open is, houdt Libera Suite een sessiemap bij naast zijn applicatiegegevens. Daarin staan de werkkopie en een doorlopend logboek van je wijzigingen, waardoor opslaan snel gaat en ongedaan maken betrouwbaar is. Het is geen back-up: het document staat waar je het hebt opgeslagen.

---

[Wat vandaag werkt](../main/status.md) is de volgende pagina: wat er gebouwd is en de problemen die we al kennen. Kom je er een tegen die niet in die lijst staat, [laat het ons weten](../feedback.md).
