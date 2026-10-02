# Lavorare con i documenti

L'interfaccia di Libera Suite è in inglese: menu e pulsanti sono citati qui come appaiono sullo schermo.

## Aprire

```sh
libera                             # la finestra iniziale
libera ~/Documents/nota.docx
libera ~/Documents/budget.xlsx
libera ~/Documents/rete.vsdx
```

**È il documento a decidere quale editor ottieni.** Non c'è un comando per sceglierne uno, così come non si sceglie un editor di testo per aprire un `.txt`: apri il documento e compare l'editor giusto. Un `.xlsx` si apre in Tables, un `.pptx` in Slides, un `.vsdx` in Diagrams.

![La finestra iniziale, con un riquadro New per ciascuno fra Document, Spreadsheet e Presentation, un pulsante Open e un elenco Recent di tre documenti.](../assets/start.png)

Da solo, `libera` apre la **finestra iniziale**: un nuovo documento di qualsiasi tipo, una finestra di apertura, i tuoi documenti recenti e la provenienza degli editor. Scegli qualcosa e la finestra iniziale lascia il posto al documento.

Libera Suite apre **un documento per finestra**, quindi un carattere jolly della shell fa quello che sembra:

```sh
libera ~/Documents/*.docx     # una finestra ciascuno
```

Puoi anche aprire un documento dall'editor, con **File ▸ Open** o **File ▸ Open Recent**. Entrambi aprono una nuova finestra e lasciano stare il documento già aperto.

**File ▸ New** propone, da qualsiasi finestra, un documento (Document), un foglio di calcolo (Spreadsheet) o una presentazione (Presentation), ciascuno nella propria finestra. Su macOS, `⌘N` ne crea uno dello stesso tipo della finestra in primo piano. Nell'editor, **File ▸ Create New** ti chiede quale dei tre creare.

## Salvare

**File ▸ Save** riscrive il documento che hai aperto. **File ▸ Save As** chiede dove metterlo. Da quel momento è quello il documento che stai modificando.

Il salvataggio riconverte il formato di lavoro dell'editor in un vero documento, il che richiede circa un secondo.

## Esportare

Save As serve anche a esportare: la sua finestra ha un elenco **File Format**.

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

Scegliere un formato rinomina il file nella finestra. Le due cose non possono divergere: non puoi ottenere un file ODT chiamato `.docx`.

Il convertitore non sa scrivere tutti i formati che sa leggere. In particolare `.doc` si apre ma non si salva; usa `.docx` o `.rtf` per un documento che deve tornare a una vecchia versione di Word.

Se cerchi una voce **Download As** nel menu File, non c'è. Gli editor la nascondono quando funzionano come applicazione desktop offline e mettono Save As al suo posto: la stessa funzione, una voce più in alto.

## La barra dei menu

Su Linux e Windows la barra sta nella finestra: **File**, **Edit**, **View** e **Help**, quest'ultimo con *Libera Help* e *About Libera Suite*. Da ciò che il menu offre lì derivano tre differenze. Nessuna voce ha una scorciatoia da tastiera, quindi i tasti qui sotto appartengono all'editor e funzionano nella pagina. **Open Recent** viene costruito all'avvio dell'applicazione: un documento aperto oggi vi compare domani. Nulla viene disattivato: Save senza nulla da salvare non fa nulla.

Su macOS è una vera barra dei menu del Mac, con le stesse voci più **Window**. Le solite scorciatoie vi funzionano, che l'editor abbia il focus o no:

| | |
| :--- | :--- |
| `⌘N` `⌘O` | Nuovo (del tipo della finestra in primo piano), Apri: ciascuno nella propria finestra |
| `⌘S` `⇧⌘S` | Salva, Salva con nome |
| `⌘P` | Stampa |
| `⌘W` | Chiudi, chiedendo prima cosa fare delle modifiche non salvate |
| `⌘Z` `⇧⌘Z` | Annulla, Ripeti |
| `⌘F` | Trova |
| `⌘?` | Questa documentazione |
| `⌘+` `⌘-` `⌘0` | Ingrandisci, riduci, adatta la pagina |
| `⌘8` | Segni di formattazione |

**File ▸ Open Recent** viene ricostruito ogni volta che lo apri. Il menu **Window** elenca tutti i documenti aperti.

Save, Undo e Redo sono disattivati quando non c'è nulla da salvare o annullare. L'editor rifiuta questi comandi senza dire nulla: una voce di menu rimasta attiva sembrerebbe guasta.

## Chiudere

Chiudere una finestra con modifiche non salvate chiede prima cosa fare: **Save**, **Don't Save** o **Cancel**.

Scegliere Don't Save non è definitivo. Libera Suite conserva ciò che hai scritto e te lo ripropone alla successiva apertura di quel documento.

## Stampare

**File ▸ Print**, o il pulsante della stampante, genera un PDF del documento e lo apre nel lettore di PDF del tuo sistema, dove si trova la finestra di stampa.

Per ora la scelta è questa: il lettore che hai già ti offre intervalli di pagine, formato della carta, ridimensionamento e un'anteprima, e nessuna di queste cose la faremmo meglio in una prima versione.

## Immagini

Le immagini incorporate in un documento vengono conservate all'apertura e al salvataggio. **Insert ▸ Image** aggiunge un'immagine dal disco.

## Controllo ortografico {#spell-checking}

Gli errori vengono sottolineati; il clic destro propone dei suggerimenti. Il dizionario usato dipende dalla **lingua del documento**, che imposti nella **barra di stato** in fondo alla finestra, documento per documento.

Sono forniti dizionari per cinque lingue: inglese (americano e britannico), francese, tedesco, spagnolo e italiano. Una lingua senza dizionario non è un errore; le sue parole vengono semplicemente considerate corrette. Le parole aggiunte con *Add to dictionary* tornano sottolineate alla sessione successiva, perché i dizionari personali non vengono ancora conservati.

## Il tuo nome nei documenti {#your-name-in-documents}

Le revisioni e i commenti sono attribuiti a una persona, il cui nome viene scritto nel file salvato. Libera Suite lo prende dal tuo account: il tuo nome completo come lo conosce macOS, il nome visualizzato del tuo account Windows oppure il campo «nome completo» del tuo account Unix su Linux, e in mancanza il tuo nome di accesso.

Non esiste ancora un'impostazione per cambiarlo. Se un documento deve uscire con un altro nome, [diccelo](../feedback.md).

## Dove finiscono i tuoi file di lavoro

Finché un documento è aperto, Libera Suite tiene una cartella di sessione accanto ai suoi dati applicativi. Contiene la copia di lavoro dell'editor e un registro continuo delle tue modifiche, il che rende il salvataggio rapido e l'annullamento affidabile. Non è una copia di sicurezza: il documento è dove l'hai salvato.

---

La pagina successiva è [Cosa funziona oggi](../main/status.md): cosa è costruito e i problemi che conosciamo già. Se ne incontri uno che non è elencato lì, [scrivici](../feedback.md).
