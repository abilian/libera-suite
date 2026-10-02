# Licenza e attribuzione

## Due licenze per due componenti

| | |
| :--- | :--- |
| **L'applicazione host**: il pacchetto `libera`, tutto ciò che si trova in `src/libera/` | [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| **Gli editor**: Euro-Office con la nostra serie di patch | [AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html) |

Arrivano separati e restano separati. L'applicazione host è un pacchetto di poche centinaia di kilobyte di Python e JavaScript su PyPI; gli editor sono un download di circa 120 MB, o il contenuto di un pacchetto Flatpak. Nulla degli editor è incorporato nel pacchetto Python.

Esegui `libera --payload-status` per vedere gli editor in uso e le revisioni del progetto originale da cui sono stati costruiti.

## Da cosa è costruita

Libera Suite include componenti di [**Euro-Office**](https://github.com/Euro-Office), un fork sotto AGPL di **ONLYOFFICE**, sviluppato da Ascensio System SIA. Questi componenti sono modificati; le nostre modifiche formano la serie di patch descritta più avanti. Gli editor, il motore dei documenti e il supporto dei formati sono loro; l'applicazione host, il pacchetto e l'integrazione con il desktop sono nostri.

Siamo grati a entrambi. La parte più difficile di una suite per ufficio sono vent'anni passati a leggere correttamente i file `.docx` degli altri. Quella parte la ereditiamo.

## Codice sorgente corrispondente

Gli editor sono sotto AGPL, che richiede che tu possa ottenere il codice sorgente di ciò che esegui, comprese le nostre modifiche.

Ogni versione di Libera Suite scrive tre cose nel manifesto dei suoi editor:

- la revisione esatta di ogni repository del progetto originale da cui è stata costruita, fissata con l'hash del commit;
- il commit di Libera Suite stessa;
- i repository da cui si possono scaricare entrambi.

Le nostre modifiche al progetto originale sono tenute come una serie di patch su quelle revisioni fissate: la domanda «cosa ha cambiato Libera Suite?» ha quindi una risposta breve e verificabile. Vedi [The patch queue](/en/develop/patches/), in inglese.

Rimandiamo a repository pubblici; non distribuiamo archivi.
