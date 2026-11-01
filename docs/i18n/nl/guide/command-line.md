# Opdrachtregel

Libera Suite gebruik je via de vensters, maar een terminal bereikt een paar dingen die geen venster biedt: een hele map documenten in één keer converteren, de componenten installeren op een computer die je via SSH bereikt, het rapport dat een bug nodig heeft.

De opdracht is `libera`, op Linux en macOS. Als Flatpak geïnstalleerd is het `flatpak run eu.liberasuite.Libera`, gevolgd door dezelfde opties. Op Windows is het `libera-cli.exe`, in de map waarin Libera Suite is geïnstalleerd; die staat niet in het `PATH`.

## Openen

| | |
| :--- | :--- |
| `libera` | het startvenster: nieuw, openen, recent |
| `libera BESTAND...` | elk document in een eigen venster; het bestand bepaalt het programma. [Meer](documents.md#open) |

## Converteren

| | |
| :--- | :--- |
| `libera --convert BESTAND... -t FORMAAT` | elk document weggeschreven in `FORMAAT`, ernaast, zonder venster. `FORMAAT` is een extensie: `pdf`, `odt`, `docx`, `xlsx`, `csv`... |
| `-o BESTAND` | voor één document: het bestand dat geschreven wordt, met het formaat van zijn extensie, tenzij `-t` iets anders zegt. `-o -` schrijft naar de standaarduitvoer |
| `--outdir MAP` | in `MAP` schrijven in plaats van naast elk document |

[Converteren vanaf de opdrachtregel](documents.md#from-the-command-line) geeft voorbeelden.

## De componenten

| | |
| :--- | :--- |
| `libera --payload-install` | de componenten downloaden, controleren en installeren. `--from MAP` installeert ze in plaats daarvan uit een map. [Meer](../main/alt-install.md#the-editors) |
| `libera --payload-status` | waar de componenten staan, hun versie, en de [broncode](../licence.md#corresponding-source) waaruit ze gebouwd zijn |
| `libera --payload-remove` | ze verwijderen. [Meer](../main/install.md#uninstall) |

## Het toepassingenmenu op Linux

| | |
| :--- | :--- |
| `libera --launcher-install` | Libera Suite in het toepassingenmenu zetten, met *Openen met*. [Meer](../main/alt-install.md#a-launcher-entry-on-linux) |
| `libera --launcher-remove` | het er weer uit halen |

De Flatpak doet dit zelf.

## Als er iets misgaat

| | |
| :--- | :--- |
| `libera --diagnose` | alles wat een bugrapport nodig heeft, op één scherm. [Meer](../main/install.md#if-something-goes-wrong) |
| `libera --version` | de versie van de applicatie en die van de componenten |
| `-v`, `-vv`, `-vvv` | laten zien wat het doet; hoe; elk verzoek van de componenten |
| `-q` | alleen fouten |

`libera --help` toont alle opties, en `libera --convert --help` die van de converter.
