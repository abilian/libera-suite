# Lavorare con i documenti

L'interfaccia di Libera Suite è in inglese: menu e pulsanti sono citati qui come appaiono sullo schermo.

## Aprire {#open}

```sh
libera                             # la finestra iniziale
libera ~/Documents/nota.docx
libera ~/Documents/budget.xlsx
libera ~/Documents/rete.vsdx
```

**È il documento a decidere quale applicazione ottieni.** Non c'è un comando per sceglierne uno, così come non si sceglie un editor di testo per aprire un `.txt`: apri il documento e compare l'applicazione giusta. Un `.xlsx` si apre in Tables, un `.pptx` in Slides, un `.vsdx` in Diagrams, un `.pdf` in Libera PDF.

![La finestra iniziale, con un riquadro New per ciascuno fra Document, Spreadsheet e Presentation, un pulsante Open e un elenco Recent di tre documenti.](../assets/start.png)

Da solo, `libera` apre la **finestra iniziale**: un nuovo documento di qualsiasi tipo, una finestra di apertura, i tuoi documenti recenti e la provenienza dei componenti. Scegli qualcosa e la finestra iniziale lascia il posto al documento.

Libera Suite apre **un documento per finestra**, quindi un carattere jolly della shell fa quello che sembra:

```sh
libera ~/Documents/*.docx     # una finestra ciascuno
```

Puoi anche aprire un documento dalla finestra del documento, con **File ▸ Apri** o **File ▸ Apri recenti**. Entrambi aprono una nuova finestra e lasciano stare il documento già aperto.

**Su macOS i documenti possono aprirsi come schede** di un'unica finestra. Libera Suite segue l'impostazione del sistema, *Apri nuovo documento come pannello* in Impostazioni di Sistema ▸ Scrivania e Dock, come ogni applicazione per documenti su Mac. Se è su *Sempre*, ogni documento si apre in una scheda. Altrimenti si apre in una finestra propria, e **Finestra ▸ Merge All Windows** le riunisce. Il **+** in fondo alla barra delle schede apre la finestra iniziale in una nuova scheda, e il documento che scegli lì ne prende il posto. Una scheda si trascina fuori in una finestra propria.

**Un documento trascinato** su una finestra di Libera Suite, compresa la finestra iniziale, si apre in una finestra tutta sua. Un'immagine trascinata su un documento vi viene inserita.

**File ▸ Nuovo** propone, da qualsiasi finestra, un documento, un foglio di calcolo o una presentazione, ciascuno nella propria finestra. Su macOS, `⌘N` ne crea uno dello stesso tipo della finestra in primo piano. Nella finestra del documento, **File ▸ Crea nuovo** ti chiede quale dei tre creare.

## Salvare

**File ▸ Salva** riscrive il documento che hai aperto. **File ▸ Salva con nome** chiede dove metterlo. Da quel momento è quello il documento che stai modificando.

Il salvataggio riconverte il formato di lavoro in un vero documento, il che richiede circa un secondo.

## Esportare

Salva con nome serve anche a esportare: la sua finestra ha un elenco **Formato file**.

| | |
| :--- | :--- |
| Documento di Word | `.docx` |
| Modello di Word | `.dotx` |
| Testo OpenDocument | `.odt` |
| Modello OpenDocument | `.ott` |
| PDF | `.pdf` |
| Rich Text Format | `.rtf` |
| HTML | `.html` |
| Markdown | `.md` |
| EPUB | `.epub` |
| FictionBook | `.fb2` |
| Testo normale | `.txt` |

Scegliere un formato rinomina il file nella finestra. Le due cose non possono divergere: non puoi ottenere un file ODT chiamato `.docx`.

Il convertitore non sa scrivere tutti i formati che sa leggere. In particolare `.doc` si apre ma non si salva; usa `.docx` o `.rtf` per un documento che deve tornare a una vecchia versione di Word.

Se cerchi una voce **Scarica come** nel menu File, non c'è. I componenti la nascondono quando funzionano come applicazione desktop offline e mettono Salva con nome al suo posto: la stessa funzione, una voce più in alto.

### Dalla riga di comando {#from-the-command-line}

`libera --convert` fa lo stesso senza aprire una finestra, per un documento o per cento. Il formato si indica con la sua estensione, con `-t`, oppure si ricava dal nome dato a `-o`:

```sh
libera --convert *.docx -t pdf             # relazione.pdf accanto a relazione.docx, ecc.
libera --convert talk.pptx -o talk.odp     # un solo documento, con il suo nome
libera --convert *.xlsx -t ods --outdir ods/
libera --convert relazione.docx -t pdf -o - | lp   # sull'output standard
```

Un file che ha già il nuovo nome viene sostituito. Il documento convertito non viene mai sovrascritto, e due documenti che finirebbero con lo stesso nome vengono rifiutati prima di convertire alcunché. Le opzioni sono quelle di pandoc, tranne `-f`: è l'estensione a dire che cosa è un documento.

## La barra dei menu

Su Linux e Windows la barra sta nella finestra: **File**, **Modifica**, **Visualizza** e **Aiuto**, quest'ultimo con *Guida di Libera* e *Informazioni su Libera Suite*. Da ciò che il menu offre lì derivano tre differenze. Su Linux, Nuovo, Apri e Chiudi mostrano Ctrl-N, Ctrl-O e Ctrl-W, e nessun'altra voce mostra il suo tasto; su Windows nessuna. Ctrl-N, Ctrl-O, Ctrl-W, Ctrl-S, Ctrl-Maiusc-S, Ctrl-P e Ctrl-Z fanno lì quello che i tasti ⌘ qui sotto fanno su un Mac. **Apri recenti** viene costruito all'avvio dell'applicazione: un documento aperto oggi vi compare domani. Nulla viene disattivato: Salva senza nulla da salvare non fa nulla.

Su macOS è una vera barra dei menu del Mac, con le stesse voci più **Finestra**. Le solite scorciatoie vi funzionano, che il documento abbia il focus o no:

| | |
| :--- | :--- |
| `⌘N` `⌘O` | Nuovo (del tipo della finestra in primo piano), Apri: ciascuno nella propria finestra, o scheda |
| `⌘S` `⇧⌘S` | Salva, Salva con nome |
| `⌘P` | Stampa |
| `⌘W` | Chiudi, chiedendo prima cosa fare delle modifiche non salvate |
| `⌘Z` `⇧⌘Z` | Annulla, Ripeti |
| `⌘F` | Trova |
| `⌘?` | Questa documentazione |
| `⌘+` `⌘-` `⌘0` | Ingrandisci, riduci, adatta la pagina |
| `⌘8` | Segni di formattazione |

**File ▸ Apri recenti** viene ricostruito ogni volta che lo apri. Il menu **Finestra** elenca tutti i documenti aperti.

Salva, Annulla e Ripeti sono disattivati quando non c'è nulla da salvare o annullare. I componenti rifiutano questi comandi senza dire nulla: una voce di menu rimasta attiva sembrerebbe guasta.

## Chiudere

Chiudere una finestra con modifiche non salvate chiede prima cosa fare: **Salva**, **Non salvare** o **Annulla**.

Scegliere Non salvare non è definitivo. Libera Suite conserva ciò che hai scritto e te lo ripropone alla successiva apertura di quel documento.

## Stampare

**File ▸ Stampa**, o il pulsante della stampante, genera un PDF del documento, chiede dove conservarlo (nella cartella del documento, se non ne scegli un'altra) e lo apre nel lettore di PDF del tuo sistema, dove si trova la finestra di stampa.

Per ora la scelta è questa: il lettore che hai già ti offre intervalli di pagine, formato della carta, ridimensionamento e un'anteprima, e nessuna di queste cose la faremmo meglio in una prima versione.

## Immagini

Le immagini incorporate in un documento vengono conservate all'apertura e al salvataggio. **Inserisci ▸ Immagine** aggiunge un'immagine dal disco.

## PDF {#pdfs}

Un `.pdf` si apre in **Libera PDF**. Libera Suite è proposto in *Apri con* per un PDF, mai come predefinito: un doppio clic lo apre sempre nel tuo lettore abituale.

- **Commentare.** La scheda **Commenta** offre *Commento del testo*, *Evidenzia*, una penna, delle forme e una casella di testo.
- **Compilare un modulo.** Fai clic in un campo e scrivi, spunta una casella, scegli da un elenco. Molti moduli ufficiali sono fatti con Adobe LiveCycle Designer e portano una seconda copia del modulo, che legge solo Acrobat. Il salvataggio lascia fuori quella copia, perché Acrobat mostri i valori inseriti, come fanno gli altri lettori.
- **Modificare le pagine.** Un clic destro su una pagina offre *Inserisci pagina vuota dopo*, *Elimina pagina* e *Ruota la pagina*. Trascina la miniatura di una pagina per spostarla.
- **Correggere una riga di testo**, con *Modifica PDF*, poi *Modifica Testo*. Serve per piccole correzioni. Le parole nuove sono composte in uno dei nostri caratteri quando quello del PDF non si può usare, e una riga che si allunga non si ricompone: la parte che non ci sta più va su una riga a sé.

**Il salvataggio si aggiunge al file.** Le tue modifiche sono scritte dopo il contenuto originale del PDF, che resta esattamente com'era. Una pagina che elimini o un testo che correggi si può quindi ancora recuperare dal file salvato: non contare su nessuno dei due per togliere qualcosa di riservato da un PDF che invii. Una firma che consente i commenti resta quindi valida per la parte firmata. Un PDF si salva solo come PDF.

**Un PDF che chiede una password** si apre quando dai la password, e si salva con le tue modifiche, sempre sotto la stessa password. **Un PDF certificato non si può salvare**, anche se la sua certificazione consente i commenti: il salvataggio non riesce con un messaggio di errore generico, il file resta com'era, e le tue modifiche restano nella finestra.

Non è ancora possibile creare un modulo, né convertire un PDF in un documento.

## Documenti protetti da password {#passwords}

Un documento protetto da una password, da Word, LibreOffice o Libera Suite, la chiede all'apertura, e di nuovo dopo una password sbagliata. Il salvataggio conserva la password: il file viene scritto protetto, com'era. Una stampa è un PDF protetto dalla stessa password. Alcuni formati non possono conservare una password: testo, CSV, TSV, RTF, HTML, Markdown, EPUB e FB2. Il salvataggio in uno di essi chiede prima, e *Salva senza password* scrive il file senza protezione; la finestra ha poi quel file aperto, senza password.

**La protezione propria di LibreOffice 26 non si legge ancora.** Per impostazione predefinita, LibreOffice 26 cifra un file OpenDocument in un modo che Libera Suite non legge, e Libera Suite lo dice invece di chiedere la password. LibreOffice scrive la cifratura precedente, che Libera Suite legge, quando la sua versione del formato ODF è impostata su 1.3.

**File ▸ Proteggi** dà una password a un documento con *Aggiungi password*, e propone *Cambia password* (in Tables, Slides e per un PDF *Modifica password*) ed *Elimina password* quando ne ha una. Ciascuno salva subito il documento. È proposto per i file Word, Excel, PowerPoint, OpenDocument e PDF, i formati che possono portare una password. La nuova password di un PDF riscrive l'intero file: Proteggi non è quindi proposto per un PDF firmato, le cui firme non sopravvivrebbero, né per uno il cui autore ha limitato la stampa, la copia o la modifica, perché la nuova password toglierebbe quei limiti, né per uno che lascia una parte di sé non cifrata, che la riscrittura rovinerebbe.

## Documenti firmati {#signatures}

Un documento Word, Excel o PowerPoint può portare firme digitali, fatte da Word, da Libera Suite o da Euro-Office. Libera Suite le verifica all'apertura del documento e le elenca nel pannello *Firma*, ciascuna valida o no, con chi ha firmato e quando. Un documento firmato si apre in sola lettura, perché niente cambi quanto è stato firmato. *Valida* significa che il documento non è cambiato da quando è stato firmato. Chi ha emesso il certificato non viene ancora verificato: il nome del firmatario è quello che il certificato stesso dichiara, quindi guarda i *Dettagli firma* prima di fidarti.

**Firmare.** *Protezione* ▸ *Firma* ▸ *Aggiungi firma digitale*, oppure *Aggiungi riga di firma* per una firma disegnata nel documento, poi *Seleziona* nella finestra *Firma documento*. Libera Suite chiede un file di chiave, PKCS#12 (`.p12`, `.pfx`) o PEM, il file del certificato quando il file di chiave non ne contiene, e la passphrase della chiave; il firmatario e le date del certificato compaiono allora nella finestra prima di firmare. La passphrase resta finché la finestra è aperta, e non viene mai scritta. Un documento con modifiche viene prima salvato, perché un documento viene firmato com'è sul disco.

**Modificare un documento firmato ne rimuove le firme.** *File* ▸ *Proteggi* ▸ *Modifica documento* lo dice e chiede prima; *Rimuovi firma*, nel pannello *Firma*, ne rimuove una. *Dettagli firma* mostra il certificato del firmatario.

**Non ancora**: firmare un documento protetto da password, un file OpenDocument o un PDF, e i certificati dell'archivio proprio di Windows; un file di chiave funziona su ogni sistema. **Un certificato scaduto firma**, e la sua firma risulta valida: controlla le date del certificato nella finestra prima di firmare.

## Controllo ortografico {#spell-checking}

Gli errori vengono sottolineati; il clic destro propone dei suggerimenti. Il dizionario usato dipende dalla **lingua del documento**, che imposti nella **barra di stato** in fondo alla finestra, documento per documento.

Sono forniti dizionari per sei lingue: inglese (americano e britannico), francese, tedesco, spagnolo, italiano e olandese. Una lingua senza dizionario non è un errore; le sue parole vengono semplicemente considerate corrette. Le parole aggiunte con *Add to dictionary* vengono conservate: da quel momento sono corrette in tutti i documenti e in tutte le lingue.

## Il tuo nome nei documenti {#your-name-in-documents}

Le revisioni e i commenti sono attribuiti a una persona, il cui nome viene scritto nel file salvato. Libera Suite lo prende dal tuo account: il tuo nome completo come lo conosce macOS, il nome visualizzato del tuo account Windows oppure il campo «nome completo» del tuo account Unix su Linux, e in mancanza il tuo nome di accesso.

Per usare un altro nome, scrivilo nel file di configurazione, creando il file se non esiste:

```toml
user_name = "Jeanne Dupont"
```

| | |
| :--- | :--- |
| Linux | `$XDG_CONFIG_HOME/libera/config.toml`, or `~/.config/libera/config.toml` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/config/libera/config.toml` |
| macOS | `~/Library/Application Support/Libera Suite/config.toml` |
| Windows | `%USERPROFILE%\.config\libera\config.toml` |

Il nome vale per le finestre aperte dopo il prossimo avvio di Libera Suite. I documenti già salvati conservano il nome con cui sono stati salvati.

Lo stesso file disattiva la ricerca quotidiana di una nuova versione, con una riga a parte:

```toml
check_updates = false
```

Un'altra si limita ai caratteri forniti da Libera Suite, senza quelli installati sulla tua macchina, perché un documento appaia uguale su ogni computer:

```toml
installed_fonts = false
```

E una fissa la lingua delle applicazioni, quando non deve essere quella del tuo sistema. Un nuovo documento prende comunque il formato della carta dalla regione del tuo sistema:

```toml
ui_language = "fr"
```

Per usare un altro file per un solo avvio, senza toccare questo, indicatelo con `libera --config FILE` (o `-c FILE`), oppure nella variabile d'ambiente `LIBERA_CONFIG`. Un Libera Suite avviato così non affida i suoi documenti a uno già in esecuzione, che li aprirebbe con la propria configurazione: chiudete prima quello.

## Dove finiscono i tuoi file di lavoro

Finché un documento è aperto, Libera Suite tiene una cartella di sessione accanto ai suoi dati applicativi. Contiene la copia di lavoro e un registro continuo delle tue modifiche, il che rende il salvataggio rapido e l'annullamento affidabile. Non è una copia di sicurezza: il documento è dove l'hai salvato.

Per un documento protetto da password, quella copia di lavoro non è cifrata mentre il documento è aperto: qualunque programma possa leggere i file del tuo account può leggerla. Viene conservata comunque, come per ogni documento, perché le tue modifiche sopravvivano a un arresto anomalo, e recuperarle chiede di nuovo la password.

---

La pagina successiva è [Cosa funziona oggi](../main/status.md): cosa è costruito e i problemi che conosciamo già. Se ne incontri uno che non è elencato lì, [scrivici](../feedback.md).
