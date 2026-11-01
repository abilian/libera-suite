---
date: 2026-10-12
description: Libera Suite 0.4 segnala un documento già aperto altrove, in Libera Suite o in LibreOffice, rende più fedelmente i file OpenDocument e aggiunge il trascinamento, un dizionario personale e la conversione da riga di comando.
---

# Libera Suite 0.4: più sicura in una cartella condivisa, più fedele a OpenDocument

Libera Suite 0.4 è disponibile. Protegge un documento aperto da qualcun altro, in Libera Suite come in LibreOffice. I suoi editor leggono e scrivono con più precisione i formati OpenDocument.

[Aggiornare Libera Suite](../main/install.md#update){ .md-button .md-button--primary }

Chiudete Libera Suite, poi rilanciate il programma di installazione o il comando di installazione, oppure `brew upgrade libera`. Questa versione installa nuovi editor, uno scaricamento unico di circa 100 MB.

## Il blocco dei documenti

Finora niente impediva a due finestre di modificare lo stesso documento: l'ultima a salvare sovrascriveva il lavoro dell'altra. La beta lo elencava tra i suoi limiti. La 0.4 lo elimina tra due finestre di Libera Suite come tra Libera Suite e LibreOffice. Microsoft Office non vede ancora questi blocchi: un documento aperto in Word resta esposto.

- **Libera Suite mette un blocco nel formato di LibreOffice.** Quando apre un documento, crea accanto a esso il piccolo file di blocco che usa LibreOffice. Rispetta anche i blocchi messi da LibreOffice. Un documento già aperto altrove si apre in modalità *locked for editing*: potete leggerlo e modificarlo, ma il salvataggio chiede un'altra posizione. L'originale resta intatto.
- **Riaprire un documento porta in primo piano la sua finestra**, senza aprirne una seconda.
- **Una finestra segnala le modifiche non salvate**: un punto nel pulsante di chiusura su macOS, un `*` davanti al titolo su Linux e Windows.

## Più fedeltà ai formati OpenDocument

Gli editor della 0.4 includono **68 correzioni per i formati OpenDocument** (`.odt`, `.ods`, `.odp`), ciascuna trovata con i documenti di prova di LibreOffice. Spariscono anche due difetti dei file CSV. Un emoji impediva di salvare un CSV; un CSV grande perdeva un carattere ogni 500.000 alla lettura.

## L'avviso delle nuove versioni

Novità della 0.4: al massimo una volta al giorno, Libera Suite legge dal nostro server di download il numero dell'ultima versione. Se è più recente della vostra, ve lo dice una volta, con i passi adatti a come l'avete installata. Non scarica nulla e non invia nulla su di voi o sui vostri documenti; senza rete non fa nulla. La riga `check_updates = false` nel [file di configurazione](../guide/documents.md#your-name-in-documents) lo disattiva.

## Le altre novità

- **Il trascinamento.** Un documento rilasciato su una finestra si apre; un'immagine rilasciata su un documento vi viene inserita.
- **Il dizionario personale.** Una parola aggiunta con *Add to dictionary* resta, per tutti i documenti e tutte le lingue.
- **Il vostro nome nelle revisioni e nei commenti**, impostato con `user_name` nel file di configurazione.
- **Ctrl-N, Ctrl-O e Ctrl-W** su Linux e Windows.
- **La stampa** chiede dove salvare il PDF, partendo dalla cartella del documento.
- **La conversione da riga di comando**: `libera --convert *.docx -t pdf` scrive un PDF accanto a ogni documento, senza aprire finestre.
- **La finestra About** mostra la versione installata, la prima informazione da dare in una segnalazione.

I limiti che restano, tra cui la mancanza di schede e un programma di installazione per Windows non ancora firmato, sono nella [pagina di stato](../main/status.md).

## Segnalateci i problemi

La segnalazione più utile resta un documento che esce male, allegato al tuo messaggio insieme all'output di `libera --diagnose`. [Commenti](../feedback.md) spiega come scriverci.

*Abilian*
