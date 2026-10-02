# Cosa funziona oggi

Libera Suite è giovane. Questa pagina ne descrive lo stato: cosa è costruito, cosa lo è solo in parte e cosa non è ancora iniziato.

L'interfaccia di Libera Suite è in inglese: menu e pulsanti sono citati qui come li vedrai sullo schermo.

## Cosa funziona

| | |
| :--- | :--- |
| **Quattro editor** | Windows 10 e 11 su x64, Linux su x86_64 e arm64, macOS su Apple Silicon. Words, Tables e Slides modificano; Diagrams legge i file Visio. |
| **Aprire e salvare** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Save, Save As, New. |
| **Esportare** | Save As propone un elenco di formati per ogni editor, PDF compreso. Ogni formato proposto è stato verificato con una conversione reale. |
| **Immagini** | Conservate all'apertura e al salvataggio; Insert ▸ Image funziona. |
| **Stampare** | Genera un PDF e lo apre nel tuo lettore di PDF. |
| **Controllo ortografico** | Cinque lingue, con suggerimenti. Vedi sotto. |
| **Documenti recenti** | File ▸ Open Recent ricorda gli ultimi 20. |
| **Più documenti insieme** | Anche di tipi diversi, una finestra ciascuno: da File ▸ New o File ▸ Open, con un doppio clic nel gestore dei file o con `libera *.docx`. Il tipo di file sceglie l'editor. |
| **Nel menu Start e nel menu delle applicazioni** | Su Windows, il programma di installazione aggiunge Libera Suite al menu Start e al desktop, e la inserisce in *Apri con* di Esplora file. Su Linux, il Flatpak la aggiunge al menu delle applicazioni con la sua icona e le associazioni dei file; `libera --launcher-install` fa lo stesso per qualsiasi altra installazione. |
| **Una finestra iniziale** | `libera` da solo: nuovo documento, apri, documenti recenti e provenienza degli editor. |
| **Recupero dopo un crash** | Le modifiche non salvate ti vengono riproposte alla successiva apertura del documento. |
| **La chiusura chiede conferma** | Una finestra con modifiche non salvate propone Save, Don't Save o Cancel. |
| **Una barra dei menu** | File, Edit, View e Help su tutte le piattaforme. macOS aggiunge Window insieme alle solite scorciatoie. |
| **Informazioni** | Chi ha scritto gli editor e con quale licenza: `File ▸ About` nell'editor, `Help ▸ About Libera Suite` su Linux e Windows. macOS lo mette nel menu dell'applicazione. |
| **Le impostazioni restano** | Tema, unità di misura, lingua del controllo ortografico e simili sono ancora impostati dopo un riavvio. |
| **Installazione degli editor** | Dal server, oppure da una cartella locale di artefatti costruiti. In entrambi i casi ogni artefatto viene verificato con le impronte fornite nell'applicazione. |

## Problemi noti

**Non serve segnalarli**: li conosciamo. Le sezioni seguenti li descrivono.

| | |
| :--- | :--- |
| **macOS parla di uno sviluppatore non identificato** | Solo per una `Libera.app` costruita da te: non è firmata con un Developer ID, quindi Gatekeeper la blocca la prima volta. [Altri modi di installare](alt-install.md#a-double-clickable-application-on-macos) spiega come andare avanti. Un'installazione con `pip`, `pipx` o Homebrew non incontra mai il problema. |
| **Avviata da un terminale, il Dock dice «Python»** | Solo quando avvii `libera` da un'installazione `pipx` o da un ambiente virtuale. Un'icona del Dock prende il nome del pacchetto applicativo da cui è stata avviata, qui quello dell'interprete Python, e l'applicazione non può cambiarlo. Icona e barra dei menu sono comunque le nostre; `Libera.app` mostra Libera. |
| **Diagrams non può salvare** | Apre un file `.vsdx` e lo mostra. Il convertitore non sa scrivere alcun formato Visio: non c'è quindi nulla da salvare né un modello vuoto da cui partire. |
| **Un CSV o un `.txt` con un'emoji non si può salvare come tale** | Su macOS e Linux il convertitore altera il testo semplice che contiene un carattere oltre i primi 65.536 di Unicode, per esempio un'emoji. Libera Suite rifiuta allora il salvataggio e lascia il file com'era. Save As in `.xlsx` o in `.docx` conserva tutto. Una correzione del convertitore è prevista per la prossima versione degli editor. |
| **In un CSV oltre i 500 KB circa, una riga può essere letta male** | Il convertitore salta un carattere ogni 500.000. Quando quel carattere è una virgoletta, una virgola o un a capo, una cella viene divisa in due, oppure due celle o due righe si fondono. All'apertura del file Libera Suite indica le righe interessate: controllale prima di salvare, perché il salvataggio scrive il contenuto mostrato dal foglio. Una correzione del convertitore è prevista per la prossima versione degli editor. |
| **Nessuna modifica dei PDF** | I PDF vengono solo generati. Aprire un PDF per modificarlo non è collegato. |
| **Una barra dei menu ridotta, senza scorciatoie su Linux e Windows** | Linux e Windows hanno File, Edit, View e Help, disegnati nella finestra, senza scorciatoie da tastiera; le scorciatoie proprie dell'editor, Ctrl-S, Ctrl-P e Ctrl-Z, funzionano comunque nella pagina. macOS ha gli stessi menu più Window, con le solite scorciatoie. |
| **Niente schede** | Una finestra per documento. |
| **Nessun blocco dei file** | Modificare lo stesso documento in due finestre fa perdere una delle due serie di modifiche. |
| **Windows avverte sul programma di installazione** | Il programma di installazione scaricato non è ancora firmato, quindi la prima volta SmartScreen mostra *«PC protetto da Windows»*. [Installare](install.md#windows) spiega come andare avanti. L'installazione con la riga PowerShell non incontra mai il problema. |

Se incontri qualcosa che *non* è in questo elenco, [segnalacelo](../feedback.md).

## In parte costruito

**La barra dei menu su Linux e Windows.** È disegnata nella finestra, con File, Edit, View e Help; ogni voce funziona. Nessuna ha una scorciatoia propria, quindi i tasti che usi già vanno all'editor: Ctrl-S, Ctrl-P e Ctrl-Z funzionano nella pagina. Ctrl-N non fa nulla su Linux; su Windows non è stato verificato. File ▸ New ▸ Document, Spreadsheet o Presentation funziona, così come i riquadri New della finestra iniziale e la scheda File dell'editor.

**`Libera.app` su macOS.** `build/macos-app.sh` la costruisce. Apre un documento con un doppio clic, compare in *Apri con* e mostra il marchio Libera nel Dock. Ma è un avviatore attorno all'interprete con cui è stata costruita (nulla è incorporato, firmato o autenticato): non è ancora qualcosa da dare a qualcun altro.

## Non ancora iniziato

### Nell'editor

- **Documenti protetti da password.** Né aprirli né salvarli.
- **Firme digitali.**
- **Stampa unione.**
- **Plugin.** Disattivati nel progetto originale di questo fork, quindi il pannello non compare mai.

### Nell'applicazione

- **Schede.** Le finestre esistono e il menu Window le elenca, ma non si possono riunire in una sola finestra.
- **Blocco dei file.** Due istanze di Libera Suite che modificano lo stesso file non si accorgono l'una dell'altra.
- **Un'applicazione ridistribuibile su macOS.** `Libera.app` funziona dalla tua copia del codice e non incorpora né interprete né editor. Windows ne ha una: il suo programma di installazione porta tutto con sé.
- **Trascinamento** sulla finestra o sull'icona del Dock.
- **Aggiornamenti automatici** e **firma del codice**. macOS tratta una `Libera.app` costruita da te come software di uno sviluppatore non identificato. Windows avverte sul programma di installazione scaricato.
- **Una guida offline**, leggibile senza browser né rete. Il menu Help apre questo sito; About funziona offline. Vedi sotto.

### Altrove

- **Modificare i diagrammi.** Diagrams apre un file `.vsdx` e lo mostra. Il convertitore non sa scrivere alcun formato Visio: non c'è quindi nulla da salvare né un modello vuoto da cui partire.
- **Modificare i PDF.** Gli editor ne comprendono uno. Per ora nulla vi conduce.
- **Collaborazione, archiviazione in cloud, account, telemetria.** Nulla di tutto ciò è costruito, né è in lavorazione. [La roadmap](/en/develop/roadmap/), in inglese, descrive come sarebbe ciascuno se arrivasse. [Cosa lascia la tua macchina](../index.md#what-leaves-your-machine) elenca tutto l'uso della rete da parte dell'applicazione.

## Note su alcune mancanze

### Guida

C'è un menu **Help**, su tutte le piattaforme, che apre questo sito nel tuo browser. Nessuna guida si trova *dentro* l'applicazione, dove sarebbe leggibile con la macchina offline. Il progetto originale fornisce un manuale completo. Libera Suite non lo include: descrive ONLYOFFICE e pesa 84 MB in otto lingue. La guida offline arriverà quando la nostra documentazione sarà abbastanza ampia da essere distribuita.

### Controllo ortografico

Libera Suite fornisce dizionari per **inglese (americano e britannico), francese, tedesco, spagnolo e italiano**: 9,5 MB, scelti perché l'insieme completo ne pesa 327. Aggiungere una lingua richiede una riga in `build/dictionaries.txt` e una ricostruzione degli editor.

Una lingua senza dizionario non è un errore: le sue parole vengono semplicemente considerate corrette, come nell'applicazione desktop del progetto originale. I dizionari personali (*Add to dictionary*) non vengono ancora conservati: una parola aggiunta torna sottolineata alla sessione successiva.

Come impostare la lingua di un documento è spiegato in [Lavorare con i documenti](../guide/documents.md#spell-checking).

### Il tuo nome nei documenti

Le revisioni e i commenti sono attribuiti a una persona, il cui nome viene scritto nel file salvato. Libera Suite lo prende dal tuo account: il nome completo con cui macOS ti conosce, il nome visualizzato del tuo account Windows, oppure il campo «nome completo» del tuo account Unix su Linux. Non è ancora possibile cambiarlo. [Lavorare con i documenti](../guide/documents.md#your-name-in-documents) spiega i dettagli.

### Caratteri

Libera Suite fornisce un insieme di caratteri di base: Liberation, Carlito, Caladea, Open Sans e pochi altri, abbastanza per mostrare fedelmente documenti ordinari, in 7 MB. L'insieme completo pesa 248 MB. Un documento che chiede un carattere assente sia da questo insieme sia dai caratteri installati sulla tua macchina riceve un carattere sostitutivo. Se ampliare l'insieme, in particolare per cinese, giapponese e coreano, è ancora da decidere.

### Fedeltà della resa

Il motore di impaginazione viene dal progetto originale ed è maturo. Se vedi qualcosa di sbagliato, la causa più probabile è il nostro pacchetto (un carattere o una risorsa mancante). Queste segnalazioni sono quindi particolarmente utili: mandaci [un commento](../feedback.md) con il file.
