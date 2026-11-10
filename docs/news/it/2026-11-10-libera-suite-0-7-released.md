---
date: 2026-11-10
description: Con Libera Suite 0.7 potete commentare, compilare e riordinare i PDF, mantenere i documenti sotto la loro password, leggere e creare firme digitali. I suoi componenti ora si installano con lei.
---

# Libera Suite 0.7: PDF, password e firme

Libera Suite 0.7 è disponibile. Ora potete commentare, compilare e riordinare i PDF, aprire e salvare i documenti protetti da password, leggere e creare firme digitali.

Libera Suite è una suite per ufficio libera e open source per Windows, macOS e Linux: Libera Words per i testi, Libera Tables per i fogli di calcolo, Libera Slides per le presentazioni, Libera PDF per i PDF e Libera Diagrams, un visualizzatore di disegni Visio. Apre e salva i formati di Microsoft Office e di LibreOffice, sul vostro computer, senza account né servizi cloud.

[Installare Libera Suite](../main/install.md){ .md-button .md-button--primary }

La usate già? Chiudete Libera Suite se è aperta, poi rilanciate il programma di installazione o il comando di installazione, oppure `brew upgrade libera` se usate Homebrew. Con pip, pipx o Homebrew i componenti ora si installano con l'applicazione, circa 100 MB, così al primo avvio non viene scaricato nulla. La finestra iniziale propone una volta di eliminare ciò che le versioni precedenti hanno scaricato, e `libera --payload-remove` lo fa in qualsiasi momento.

## PDF

![Libera PDF con un PDF aperto, la scheda Commento che mostra i suoi strumenti, e un commento sulla pagina elencato nel pannello Commenti.](../assets/pdf.png)

Un PDF si apre in Libera PDF. Potete aggiungere commenti, evidenziazioni, disegni e caselle di testo, fare piccole correzioni al testo e aggiungere, eliminare, ruotare e spostare pagine. Potete anche compilare moduli: un Cerfa francese e i moduli dell'IRS statunitense sono tra quelli che abbiamo provato.

Il salvataggio aggiunge le vostre modifiche dopo l'originale, che resta nel file com'era. Una pagina che eliminate o un testo che correggete si può quindi ancora recuperare dal file salvato: non contate su nessuno dei due per togliere qualcosa di riservato da un PDF che inviate.

Il testo modificato non si reimpagina. Un PDF certificato contro ogni modifica non si può salvare: il salvataggio non riesce, e il file resta com'era. Non potete ancora creare un modulo né convertire un PDF in un documento. Libera Suite è proposta in *Apri con* per un PDF, mai come predefinita. [Lavorare con i documenti](../guide/documents.md#pdfs) ha i dettagli.

## Password

Un file Word, Excel, PowerPoint, OpenDocument o PDF protetto da password la chiede all'apertura, e il salvataggio lo mantiene protetto. File ▸ Proteggi aggiunge, cambia ed elimina la password di un documento. Un salvataggio in un formato che non può mantenere una password (testo, CSV, RTF, HTML, Markdown, EPUB) chiede prima conferma. Un documento protetto che è stato alterato viene rifiutato, grazie a una correzione di ElixirOffice.

Per impostazione predefinita, LibreOffice 26 cifra i file OpenDocument in un modo che Libera Suite non sa ancora leggere, e Libera Suite lo dice invece di chiedere la password. Finché un documento protetto è aperto, la sua copia di lavoro sul vostro disco non è cifrata, perché un arresto anomalo non vi faccia perdere le modifiche. [Lavorare con i documenti](../guide/documents.md#passwords) ha i dettagli.

## Firme digitali

Un documento Word, Excel o PowerPoint firmato mostra le sue firme all'apertura, ciascuna valida o no, e si apre in sola lettura. *Protezione* ▸ *Firma* ne firma uno con un file di chiave (PKCS#12 o PEM) e la sua passphrase, e potete rimuovere le firme. Abbiamo verificato con Microsoft Office e LibreOffice le firme fatte in Libera Suite, e in Libera Suite le firme fatte da entrambi.

*Valida* significa che il documento non è cambiato da quando è stato firmato: chi ha emesso il certificato, e se è scaduto, non viene ancora controllato. Non è ancora possibile firmare un documento protetto, un file OpenDocument o un PDF. [Lavorare con i documenti](../guide/documents.md#signatures) ha i dettagli.

## Altre novità

- **I documenti Word 97-2003 si aprono.** Nessun file `.doc` si era mai aperto. Ora si aprono anche gli archivi web (`.mht`), FictionBook (`.fb2`) e i libri EPUB.
- **Il convertitore si avvia in circa metà del tempo**, così ogni apertura e ogni salvataggio sono un po' più rapidi.
- **Trascinare un file su una finestra funziona su Linux**: un documento si apre in una finestra propria, e un'immagine entra nel documento. Il Flatpak ora può anche aprire i file su chiavette USB e unità montate.
- **Un documento aperto da qualcun altro ora lo dice, in qualunque finestra si apra.** Ogni finestra riceveva lo stato della prima.
- **Su Windows una finestra non si apre più più grande dello schermo.**

## Sicurezza

Tutte le versioni precedenti hanno questi problemi: aggiornate, per favore.

- **Un documento non può più copiare in sé immagini dal vostro disco.** Un'immagine collegata a un percorso del vostro disco veniva copiata in ogni documento salvato o convertito da esso, così rispedendo il documento si spediva anche l'immagine. Ora un'immagine collegata viene letta solo da un indirizzo web.
- **Tre falle di cross-site scripting (XSS) sono chiuse.** Un documento costruito ad arte poteva eseguire uno script nell'editor quando selezionavate una modifica rilevata, aprivate la Procedura guidata funzione o cliccavate su un link `javascript:`. Tutti e tre ora vengono mostrati come testo o rifiutati. Inoltre la pagina dell'editor carica immagini solo da Libera Suite, così uno script non può più mandare fuori nulla nell'indirizzo di un'immagine.
- **Il convertitore non scrive più parti della propria memoria nei file che crea.**
- **Un piccolo documento non può più portare il convertitore a gigabyte di memoria.**

## Download firmati e codice sorgente

I pacchetti Flatpak sono firmati con la nostra chiave OpenPGP, e [Altri modi di installare](../main/alt-install.md) spiega come verificarne uno. Il programma di installazione per Windows e `Libera.app` non sono ancora firmati. [Installare](../main/install.md) spiega come superare l'avviso sul programma di installazione; il comando PowerShell di una riga, pip, pipx e Homebrew non ne incontrano nessuno.

Il codice sorgente dei wheel del convertitore è il pacchetto sorgente `libera-core` su PyPI: i commit a monte che fissa, le nostre patch e gli script di compilazione. Il codice sorgente dell'applicazione è il tag `0.7.0` di [abilian/libera-suite](https://github.com/abilian/libera-suite).

## Senza modifiche

- **Linux su arm64** installa ancora la 0.4.1: non c'è ancora una build arm64 della 0.7.

[Cosa funziona oggi](../main/status.md) indica cosa è pronto, cosa è a metà e cosa non è ancora iniziato, e [la roadmap](/en/develop/roadmap/), in inglese, dice cosa viene dopo.

## Segnalateci i problemi

Libera Suite è giovane: ogni segnalazione conta. La più utile è un documento che viene fuori sbagliato, allegato al vostro messaggio con l'output di `libera --diagnose`. [Commenti](../feedback.md) spiega come contattarci.

*Abilian*
