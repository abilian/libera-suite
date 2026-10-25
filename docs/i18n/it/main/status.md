# Cosa funziona oggi

Libera Suite è giovane. Questa pagina ne descrive lo stato: cosa è costruito, cosa lo è solo in parte e cosa non è ancora iniziato.

L'interfaccia di Libera Suite è in inglese: menu e pulsanti sono citati qui come li vedrai sullo schermo.

## Cosa funziona

| | |
| :--- | :--- |
| **Quattro applicazioni** | Windows 10 e 11 su x64, Linux su x86_64 (arm64 con la 0.4.1), macOS su Apple Silicon. Words, Tables e Slides modificano; Diagrams legge i file Visio. |
| **Aprire e salvare** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Save, Save As, New. |
| **Esportare** | Save As propone un elenco di formati per ogni applicazione, PDF compreso. Ogni formato proposto è verificato con una conversione reale, di cui si rilegge il testo. |
| **Immagini** | Conservate all'apertura e al salvataggio; Inserisci ▸ Immagine funziona. |
| **Stampare** | Genera un PDF, chiede dove conservarlo e lo apre nel tuo lettore di PDF. |
| **Controllo ortografico** | Cinque lingue, con suggerimenti. Vedi sotto. |
| **Nella tua lingua** | Le applicazioni seguono la lingua del tuo sistema, e un nuovo documento parte dal modello vuoto della tua regione: carta A4 ovunque tranne che negli Stati Uniti, e controllo ortografico nella tua lingua. Seguono anche la barra dei menu, la finestra iniziale e le finestre di dialogo, in ogni lingua delle applicazioni, e in arabo, ebraico e urdu la finestra iniziale si legge da destra a sinistra. Solo le traduzioni italiana, francese, tedesca e spagnola sono state riviste da un madrelingua; le altre sono bozze, e [le correzioni sono benvenute](../feedback.md). |
| **Documenti recenti** | File ▸ Apri recenti ricorda gli ultimi 20. |
| **Più documenti insieme** | Anche di tipi diversi, una finestra ciascuno, o su macOS una scheda ciascuno quando il sistema preferisce le schede: da File ▸ Nuovo o File ▸ Apri, con un doppio clic nel gestore dei file o con `libera *.docx`. Il tipo di file sceglie l'applicazione. |
| **Nel menu Start e nel menu delle applicazioni** | Su Windows, il programma di installazione aggiunge Libera Suite al menu Start e al desktop, e la inserisce in *Apri con* di Esplora file. Su Linux, il Flatpak la aggiunge al menu delle applicazioni con la sua icona e le associazioni dei file; `libera --launcher-install` fa lo stesso per qualsiasi altra installazione. |
| **Una finestra iniziale** | `libera` da solo: nuovo documento, apri, documenti recenti e provenienza dei componenti. |
| **Recupero dopo un crash** | Le modifiche non salvate ti vengono riproposte alla successiva apertura del documento. |
| **Un documento aperto altrove** | Se LibreOffice o un'altra istanza di Libera Suite lo ha già aperto, viene segnato come *bloccato per la modifica*: puoi leggerlo e modificarlo, e il salvataggio chiede dove, così il file dell'altra istanza non viene mai sovrascritto. Aprire un documento già mostrato in una finestra porta quella finestra in primo piano. Microsoft Office e Libera Suite non vedono i blocchi l'uno dell'altro: un documento aperto in Word non è protetto. |
| **La chiusura chiede conferma** | Una finestra con modifiche non salvate propone Salva, Non salvare o Annulla. |
| **Una barra dei menu** | File, Edit, View e Help su tutte le piattaforme. macOS aggiunge Window insieme alle solite scorciatoie. |
| **Informazioni** | Chi ha scritto i componenti e con quale licenza: `File ▸ Informazioni su` nella finestra del documento, `Aiuto ▸ Informazioni su Libera Suite` su Linux e Windows. macOS lo mette nel menu dell'applicazione. |
| **Le impostazioni restano** | Tema, unità di misura, lingua del controllo ortografico e simili sono ancora impostati dopo un riavvio. |
| **Installazione dei componenti** | Dal server, oppure da una cartella locale di artefatti costruiti. In entrambi i casi ogni artefatto viene verificato con le impronte fornite nell'applicazione. |

## Problemi noti

**Non serve segnalarli**: li conosciamo. Le sezioni seguenti li descrivono.

| | |
| :--- | :--- |
| **macOS parla di uno sviluppatore non identificato** | Solo per una `Libera.app` costruita da te: non è firmata con un Developer ID, quindi Gatekeeper la blocca la prima volta. [Altri modi di installare](alt-install.md#a-double-clickable-application-on-macos) spiega come andare avanti. Un'installazione con `pip`, `pipx` o Homebrew non incontra mai il problema. |
| **Avviata da un terminale, il Dock dice «Python»** | Solo quando avvii `libera` da un'installazione `pipx` o da un ambiente virtuale. Un'icona del Dock prende il nome del pacchetto applicativo da cui è stata avviata, qui quello dell'interprete Python, e l'applicazione non può cambiarlo. Icona e barra dei menu sono comunque le nostre; `Libera.app` mostra Libera. Un documento trascinato su quell'icona di Python viene rifiutato a nome di Python; l'icona di `Libera.app` lo accetta. |
| **Diagrams non può salvare** | Apre un file `.vsdx` e lo mostra. Il convertitore non sa scrivere alcun formato Visio: non c'è quindi nulla da salvare né un modello vuoto da cui partire. |
| **Nessuna modifica dei PDF** | I PDF vengono solo generati. Aprire un PDF per modificarlo non è collegato. |
| **Una barra dei menu ridotta, con poche scorciatoie mostrate su Linux e nessuna su Windows** | Linux e Windows hanno File, Edit, View e Help, disegnati nella finestra. Su Linux, Nuovo, Apri e Chiudi mostrano Ctrl-N, Ctrl-O e Ctrl-W, e nessun'altra voce mostra il suo tasto; su Windows nessuna. I tasti funzionano comunque: Ctrl-N, Ctrl-O, Ctrl-W, Ctrl-S, Ctrl-Maiusc-S, Ctrl-P e Ctrl-Z. macOS ha gli stessi menu più Window, con le solite scorciatoie. |
| **Niente schede su Linux e Windows** | Lì una finestra per documento. macOS ha le schede. |
| **Windows avverte sul programma di installazione** | Il programma di installazione scaricato non è ancora firmato, quindi la prima volta SmartScreen mostra *«PC protetto da Windows»*. [Installare](install.md#windows) spiega come andare avanti. L'installazione con la riga PowerShell non incontra mai il problema. |

Se incontri qualcosa che *non* è in questo elenco, [segnalacelo](../feedback.md).

## In parte costruito

**La barra dei menu su Linux e Windows.** È disegnata nella finestra, con File, Modifica, Visualizza e Aiuto; ogni voce funziona. Su Linux, Nuovo, Apri e Chiudi mostrano la loro scorciatoia, e nessun'altra voce; su Windows nessuna. I tasti consueti funzionano comunque: Ctrl-N crea un nuovo documento dello stesso tipo, Ctrl-O ne apre uno, Ctrl-W chiude la finestra (chiedendo prima delle modifiche non salvate), e anche le scorciatoie proprie dei componenti, Ctrl-S, Ctrl-Maiusc-S (Salva con nome), Ctrl-P e Ctrl-Z, funzionano. Su Windows, Ctrl-N, Ctrl-O e Ctrl-W non sono ancora stati verificati su una macchina reale. File ▸ Nuovo ▸ Documento, Foglio di calcolo o Presentazione funziona, così come i riquadri Nuovo della finestra iniziale e la scheda File del documento.

**`Libera.app` su macOS.** `build/macos/macos-app.sh` la costruisce. Apre un documento con un doppio clic o trascinato sulla sua icona del Dock, compare in *Apri con* e mostra il marchio Libera nel Dock. Ma è un avviatore attorno all'interprete con cui è stata costruita (nulla è incorporato, firmato o autenticato): non è ancora qualcosa da dare a qualcun altro.

## Non ancora iniziato

### Nella finestra del documento

- **Documenti protetti da password.** Né aprirli né salvarli.
- **Firme digitali.**
- **Stampa unione.**
- **Plugin.** Disattivati nel progetto originale di questo fork, quindi il pannello non compare mai.
- **Macro.** Disattivate. Le macro proprie dei componenti sono in JavaScript e non eseguono il VBA dei documenti di Microsoft Office, quindi le macro di un documento non vengono eseguite. Vengono però conservate: salvando un `.docm`, un `.xlsm` o un `.pptm` il suo VBA resta intatto. [La roadmap](/en/develop/roadmap/), in inglese, descrive cosa arriverà al loro posto.

### Nell'applicazione

- **Schede su Linux e Windows.** Lì una finestra per documento, che la barra delle applicazioni raggruppa.
- **Un'applicazione ridistribuibile su macOS.** `Libera.app` funziona dalla tua copia del codice e non incorpora né interprete né componenti. Windows ne ha una: il suo programma di installazione porta tutto con sé.
- **Aggiornamenti automatici** e **firma del codice**. macOS tratta una `Libera.app` costruita da te come software di uno sviluppatore non identificato. Windows avverte sul programma di installazione scaricato.
- **Una guida offline**, leggibile senza browser né rete. Il menu Help apre questo sito; About funziona offline. Vedi sotto.

### Altrove

- **Modificare i diagrammi.** Diagrams apre un file `.vsdx` e lo mostra. Il convertitore non sa scrivere alcun formato Visio: non c'è quindi nulla da salvare né un modello vuoto da cui partire.
- **Modificare i PDF.** Il progetto originale ha un editor di PDF; i componenti installati da Libera Suite non lo comprendono ancora, perché nulla lo aprirebbe.
- **Collaborazione, archiviazione in cloud, account, telemetria.** Nulla di tutto ciò è costruito, né è in lavorazione. [La roadmap](/en/develop/roadmap/), in inglese, descrive come sarebbe ciascuno se arrivasse. [Cosa lascia la tua macchina](../index.md#what-leaves-your-machine) elenca tutto l'uso della rete da parte dell'applicazione.

## Note su alcune mancanze

### Guida

C'è un menu **Aiuto**, su tutte le piattaforme, che apre questo sito nel tuo browser. Nessuna guida si trova *dentro* l'applicazione, dove sarebbe leggibile con la macchina offline. Il progetto originale fornisce un manuale completo. Libera Suite non lo include: descrive ONLYOFFICE e pesa 84 MB in otto lingue. La guida offline arriverà quando la nostra documentazione sarà abbastanza ampia da essere distribuita.

### Controllo ortografico

Libera Suite fornisce dizionari per **inglese (americano e britannico), francese, tedesco, spagnolo e italiano**: 9,5 MB, scelti perché l'insieme completo ne pesa 327. Aggiungere una lingua richiede una riga in `build/payload/dictionaries.txt` e una ricostruzione dei componenti.

Una lingua senza dizionario non è un errore: le sue parole vengono semplicemente considerate corrette, come nell'applicazione desktop del progetto originale. Le parole aggiunte con *Add to dictionary* vengono conservate, per tutti i documenti e tutte le lingue.

Come impostare la lingua di un documento è spiegato in [Lavorare con i documenti](../guide/documents.md#spell-checking).

### Il tuo nome nei documenti

Le revisioni e i commenti sono attribuiti a una persona, il cui nome viene scritto nel file salvato. Libera Suite lo prende dal tuo account: il nome completo con cui macOS ti conosce, il nome visualizzato del tuo account Windows, oppure il campo «nome completo» del tuo account Unix su Linux. Se ne può impostare un altro nel file di configurazione; non c'è ancora una voce di menu per farlo. [Lavorare con i documenti](../guide/documents.md#your-name-in-documents) spiega i dettagli.

### Caratteri

Libera Suite fornisce un insieme di caratteri di base: Liberation, Carlito, Caladea, Open Sans e pochi altri, abbastanza per mostrare fedelmente documenti ordinari, in 7 MB. L'insieme completo pesa 248 MB. Un documento che chiede un carattere assente da questo insieme usa quello installato sulla tua macchina, sullo schermo come nel suo PDF, e riceve un carattere sostitutivo solo se nemmeno la tua macchina lo ha. Fanno eccezione Calibri, Cambria, Arial, Times New Roman e Courier New: se la tua macchina non li ha, un documento riceve Carlito, Caladea o Liberation, che hanno le stesse larghezze, e le sue pagine si interrompono negli stessi punti che in Word, qualunque altro carattere sia installato. Libera Suite fa l'elenco dei tuoi caratteri al primo avvio, e di nuovo in sottofondo ogni volta che ne installi o ne rimuovi uno; le finestre aperte dopo usano il nuovo elenco. Se ampliare l'insieme, in particolare per cinese, giapponese e coreano, è ancora da decidere.

### Fedeltà della resa

Il motore di impaginazione viene dal progetto originale ed è maturo. Se vedi qualcosa di sbagliato, la causa più probabile è il nostro pacchetto (un carattere o una risorsa mancante). Queste segnalazioni sono quindi particolarmente utili: mandaci [un commento](../feedback.md) con il file.
