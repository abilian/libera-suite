---
date: 2026-10-26
description: Libera Suite 0.6 parla tutte le lingue delle sue applicazioni, impagina come Word quando manca un carattere, mantiene i titoli Markdown e controlla l'ortografia olandese.
---

# Libera Suite 0.6: tutte le lingue, e pagine che vanno a capo come in Word

Libera Suite 0.6 è disponibile. I suoi menu e le sue finestre parlano ora le 44 lingue delle sue applicazioni, e un documento di cui non avete i caratteri si impagina come in Word.

Libera Suite è una suite per ufficio libera e open source per Windows, macOS e Linux: Libera Words per i testi, Libera Tables per i fogli di calcolo, Libera Slides per le presentazioni e Libera Diagrams, un visualizzatore di disegni Visio. Apre e salva i formati di Microsoft Office e di LibreOffice, sul vostro computer, senza account né servizi cloud.

[Installare Libera Suite](../main/install.md){ .md-button .md-button--primary }

La usate già? Chiudete Libera Suite se è aperta, poi rilanciate il programma di installazione o il comando di installazione, oppure `brew upgrade libera` se usate Homebrew. Questa versione installa nuovi componenti, uno scaricamento unico di circa 90 MB.

## Tutte le lingue

Dalla 0.5 le applicazioni seguono la lingua del vostro sistema, ma la barra dei menu, la finestra iniziale e le finestre di dialogo lo facevano solo in italiano, francese, tedesco e spagnolo. Ora seguono in tutte le 44 lingue, dall'arabo al vietnamita, e in arabo, ebraico e urdu la finestra iniziale si legge da destra a sinistra.

Solo le traduzioni italiana, francese, tedesca e spagnola sono state riviste da un madrelingua. Le altre sono bozze: se una parola nella vostra lingua è sbagliata o goffa, [scriveteci](../feedback.md), e la vostra correzione entrerà nella versione successiva.

## Pagine che vanno a capo come in Word

Quando un documento chiede un carattere che il vostro computer non ha, Libera Suite ora lo sostituisce come Word:

- **Calibri, Cambria, Arial, Times New Roman e Courier New** ricevono Carlito, Caladea e Liberation, che hanno le stesse larghezze, così righe e pagine vanno a capo negli stessi punti che in Word. Sul Mac, Calibri andava al carattere installato più somigliante, e lo stesso documento poteva impaginarsi in modo diverso da un computer all'altro.
- **Un carattere che neanche Word conoscerebbe** riceve il sostituto di Calibri, come Word usa Calibri, dove prima riceveva Liberation Sans. Due documenti della nostra raccolta di prova hanno ora il numero di pagine di Word.
- **I caratteri Wingdings, Webdings e Symbol** si vedono come i simboli che rappresentano: una stella, un segno di spunta, una faccina, dove un Wingdings mancante mostrava lettere.

## Altre novità

- **Su macOS, Libera Suite è tra le tue applicazioni.** Lo script di installazione mette `Libera.app` nella cartella Applicazioni, e `libera --launcher-install` fa lo stesso dopo Homebrew: il Finder la propone in *Apri con*, un doppio clic su un documento può aprirlo lì, e il Dock mostra Libera, dove mostrava Python.
- **Il Markdown mantiene i titoli.** Un file Markdown aperto, modificato e salvato trasformava ogni titolo in un paragrafo in grassetto.
- **Il controllo ortografico in olandese**, con il dizionario OpenTaal. Ogni dizionario ora arriva con la sua licenza.
- **Su Linux, il menu File mostra le scorciatoie:** Nuovo, Apri e Chiudi mostrano Ctrl-N, Ctrl-O e Ctrl-W.
- **Un file OpenDocument senza stili di pagina master mantiene i suoi stili**, dove ogni paragrafo si apriva nello stile predefinito.

## Cosa resta uguale

- **Linux su arm64** installa ancora la 0.4.1: non c'è ancora una build arm64 della 0.6.

[Cosa funziona oggi](../main/status.md) indica cosa è pronto, cosa è a metà e cosa non è ancora iniziato.

## Segnalateci i problemi

Libera Suite è giovane, e ogni segnalazione conta. La più utile resta un documento che viene fuori sbagliato, allegato al vostro messaggio con l'output di `libera --diagnose`. [Commenti](../feedback.md) spiega come contattarci.

*Abilian*
