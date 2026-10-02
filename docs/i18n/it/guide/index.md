# Usare Libera Suite

Libera Suite apre un documento in una finestra e ti permette di modificarlo e salvarlo. Words, Tables e Slides funzionano tutti così; Diagrams apre i documenti Visio in lettura.

Comincia da [Installare](../main/install.md). Queste tre pagine vanno lette in ordine:

1. [Installare](../main/install.md): portarla sulla tua macchina, con un comando.
2. [Lavorare con i documenti](documents.md): aprire, salvare, esportare, stampare.
3. [Cosa funziona oggi](../main/status.md): cosa è costruito e i problemi che conosciamo già.

Ogni editor ha il suo colore. Per il resto la finestra è la stessa:

![Libera Tables con un foglio di calcolo vuoto; la barra degli strumenti è nel verde acqua di Libera Tables.](../assets/tables.png)

![Libera Slides con una diapositiva del titolo; la barra degli strumenti è nell'oro di Libera Slides.](../assets/slides.png)

## Com'è fatta

Libera Suite è composta da due parti che arrivano separatamente.

**L'applicazione** è un piccolo pacchetto Python di poche centinaia di kilobyte: la finestra, la riga di comando e l'applicazione host con cui l'editor comunica.

**Gli editor** sono tutto il resto: il motore dei documenti, gli editor stessi, i caratteri. L'applicazione chiama questo insieme il *payload*. Pesa circa 110 MB compresso su macOS e 120 MB su Linux. Lo scarichi o lo installi una volta; il pacchetto Python non lo include.

Le due parti hanno numeri di versione distinti. L'applicazione verifica che gli editor che trova siano quelli che si aspetta. Una correzione dell'applicazione non obbliga quindi a scaricare di nuovo gli editor.

Il programma di installazione per Windows e il Flatpak per Linux contengono entrambe le parti. Tutti gli altri modi di installare mettono prima al suo posto l'applicazione, poi scaricano gli editor una volta.

## Cosa non è

Libera Suite non parla con alcun server, non chiede alcun account e non carica mai i tuoi documenti. L'editor gira come contenuto web locale, servito su `127.0.0.1` a una finestra sulla tua stessa macchina. Non ci sono collaborazione, archiviazione in cloud né telemetria, perché nulla di tutto ciò è costruito.
