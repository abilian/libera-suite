# Libera Suite

**Libera Suite** è una suite per ufficio libera e open source per Windows, macOS e Linux, realizzata da Abilian. Scrivi documenti, lavora su fogli di calcolo e prepara presentazioni sul tuo computer, con i tuoi file, senza account né servizi cloud.

Apre e salva i formati di file di Microsoft Office e di LibreOffice, così puoi scambiare documenti con chiunque, qualunque programma usi. È un'alternativa gratuita a Microsoft Word, Excel e PowerPoint e, in quanto software libero, chiunque può leggerne il codice sorgente, modificarlo e condividerlo.

- **Libera Words**, per i testi: `.docx`, `.odt`, `.rtf`, `.txt`, `.md` e altri
- **Libera Tables**, per i fogli di calcolo: `.xlsx`, `.ods`, `.csv`
- **Libera Slides**, per le presentazioni: `.pptx`, `.odp`
- **Libera Diagrams**, un visualizzatore di disegni Visio (`.vsdx`)

![Libera Words con un documento aperto: la barra degli strumenti nel viola di Libera Words e, sotto, una pagina impaginata.](assets/words.png)

[Installa Libera Suite](main/install.md){ .md-button .md-button--primary }

## In sei diapositive

<div class="deck" data-pdf="/en/pdf/Libera%20Suite.pdf"><a href="/en/pdf/Libera%20Suite.pdf">Libera Suite, in sei diapositive (PDF)</a></div>

## A che punto è il progetto

Tutti e quattro funzionano già oggi su **Windows** 10 e 11 (x64), **Linux** (x86_64, e arm64 con la versione 0.4.1) e **macOS** (Apple Silicon). Il progetto è giovane. [Cosa funziona oggi](main/status.md) ne descrive lo stato: cosa è costruito, cosa lo è solo in parte e cosa non è ancora iniziato.

Per provarlo, comincia da [Installare](main/install.md): su Linux e macOS basta un comando; Windows ha il suo programma di installazione. Per costruirlo, comincia dalla [panoramica per sviluppatori](/en/develop/), in inglese. In ogni caso, [facci sapere com'è andata](feedback.md).

## Perché

Gran parte del lavoro di una suite per ufficio sta nel motore dei documenti, la parte che legge un `.docx` scritto dal software di qualcun altro e lo impagina come l'autore intendeva. Quel motore esiste già come software libero e funziona già offline: i componenti di modifica di Libera Suite sono quelli di [Euro-Office](https://github.com/Euro-Office), un fork sotto AGPL di ONLYOFFICE, sviluppato da Ascensio System SIA, eseguiti in locale con lo stesso motore dei documenti e lo stesso supporto dei formati. A quel motore mancava un'applicazione host per il desktop, abbastanza piccola da poter essere curata da un solo gruppo.

Libera Suite è quell'applicazione: qualche migliaio di righe di Python e JavaScript. Tutto il resto viene dal progetto originale.

## Cosa lascia la tua macchina {#what-leaves-your-machine}

Nulla che tu non abbia inviato. Libera Suite non invia i tuoi documenti da nessuna parte di sua iniziativa: vanno dove li mandi tu.

Libera Suite non ha **nessuna telemetria**, nessuna statistica d'uso, nessuna segnalazione di crash, nessun account: non ci invia nulla su di te, sui tuoi documenti o sul modo in cui la usi. Se mai venisse aggiunto qualcosa del genere, resterebbe disattivato finché non lo attivi tu.

Si collega però al nostro server per scaricare dei file. Oggi si tratta dei componenti, durante l'installazione di Libera Suite e di nuovo quando una nuova versione ne richiede di nuovi. Al massimo una volta al giorno controlla anche se è uscita una versione più recente, e te lo dice una volta; non scarica nulla, e ti indica come aggiornare. Come ogni richiesta web, ciascuno di questi download mostra al nostro server il tuo indirizzo IP, e nient'altro su di te.

La tabella elenca ogni connessione che l'applicazione stabilisce oggi, così puoi verificarlo. Ogni nuova connessione, ricerca degli aggiornamenti compresa, comparirà qui con la versione che la introduce.

| | |
| :--- | :--- |
| **I componenti** | Scaricati da `cdn.abilian.com` durante l'installazione di Libera Suite, e di nuovo solo quando una nuova versione ne richiede di nuovi. Ogni download viene verificato con le impronte fornite nell'applicazione. |
| **La ricerca degli aggiornamenti** | Al massimo una volta al giorno, il numero dell'ultima versione, letto da `cdn.abilian.com`. Una versione più recente viene segnalata una volta; non si scarica nulla. Senza connessione, non succede nulla. `check_updates = false` nel [file di configurazione](guide/documents.md#your-name-in-documents) la disattiva. |
| **Il traffico proprio dei componenti** | Un server web su `127.0.0.1`, parte dell'applicazione, che serve i componenti a una finestra sulla stessa macchina. Un altro computer non può raggiungerlo. Risponde a un programma sul tuo solo se questo presenta una chiave che solo il tuo account può leggere. La loro pagina non può raggiungere nient'altro, a parte le immagini collegate da un documento. |
| **Immagini collegate da un documento** | Un documento può mostrare un'immagine tramite il suo indirizzo web invece di contenerla. Libera Suite la scarica allora da quell'indirizzo quando il documento viene aperto o convertito, come qualsiasi suite per ufficio, e quel server vede il tuo indirizzo IP. Il documento in sé non viene inviato. |
| **I link su cui fai clic** | La guida e simili si aprono nel *tuo* browser. Libera Suite non li scarica. |

I tuoi documenti vengono letti e scritti sul tuo disco, da un convertitore che si trova sul tuo disco. Non vengono mai caricati, indicizzati né esaminati.

## Licenza e codice sorgente

Libera Suite è software libero: l'applicazione host è sotto licenza [Apache-2.0](licence.md); i componenti che esegue sono sotto AGPL v3, come il codice di Euro-Office da cui sono costruiti. Ogni versione registra le revisioni esatte del progetto originale da cui è stata costruita e le patch applicate: il codice sorgente corrispondente è quindi sempre un commit più una serie di patch che si può verificare che vi si applichi.

---

Microsoft, Word, Excel, PowerPoint, Visio e Windows sono marchi del gruppo di società Microsoft. LibreOffice è un marchio di The Document Foundation. ONLYOFFICE è un marchio di Ascensio System SIA. Gli altri nomi sono marchi dei rispettivi proprietari. Libera Suite non è affiliata a nessuno di essi né da essi approvata.
