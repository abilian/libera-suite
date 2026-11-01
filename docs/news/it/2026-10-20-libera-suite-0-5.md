---
date: 2026-10-20
description: Libera Suite 0.5 parla la vostra lingua, mostra i documenti con i caratteri installati sul vostro computer, li apre prima e fa pulizia dopo i propri aggiornamenti.
---

# Libera Suite 0.5: nella vostra lingua, con i vostri caratteri

Libera Suite 0.5 è disponibile. Ora segue la lingua del vostro sistema e mostra un documento con i caratteri installati sul vostro computer.

Libera Suite è una suite per ufficio libera e open source per Windows, macOS e Linux: Libera Words per i testi, Libera Tables per i fogli di calcolo, Libera Slides per le presentazioni e Libera Diagrams, un visualizzatore di disegni Visio. Apre e salva i formati di Microsoft Office e di LibreOffice, sul vostro computer, senza account né servizi cloud.

[Installare Libera Suite](../main/install.md){ .md-button .md-button--primary }

La usate già? Chiudete Libera Suite se è aperta, poi rilanciate il programma di installazione o il comando di installazione, oppure `brew upgrade libera` se usate Homebrew. Questa versione installa nuovi componenti, uno scaricamento unico di circa 90 MB.

## Nella vostra lingua

Finora Libera Suite parlava solo inglese. Le sue quattro applicazioni ora seguono la lingua del vostro sistema, e la riga `ui_language` del [file di configurazione](../guide/documents.md#your-name-in-documents) ne sceglie un'altra. In italiano, francese, tedesco e spagnolo seguono anche la barra dei menu, la finestra iniziale e le finestre di dialogo, e la Guida apre questa documentazione nella stessa lingua.

Un nuovo documento parte da una pagina vuota per la vostra lingua e regione: carta A4 ovunque tranne che negli Stati Uniti, dove finora era US Letter per tutti, e controllo ortografico nella vostra lingua.

## Con i vostri caratteri

Un documento composto con un carattere che avete installato ora appare con quel carattere, sullo schermo e nel PDF, dove prima riceveva un sostituto. Libera Suite elenca i vostri caratteri quando installa i suoi componenti, e di nuovo ogni volta che ne installate o rimuovete uno; nulla viene copiato. La riga `installed_fonts = false` la limita ai caratteri forniti con Libera Suite.

## Prima sullo schermo

La finestra di un documento ora si apre subito, mentre il documento è ancora in preparazione. Sul nostro Mac, un piccolo documento di testo appare circa un secondo prima. Un file che Libera Suite non riesce a leggere ora apre una finestra che lo segnala, poi la chiude.

## Altre novità

- **Componenti aggiornati**, di ottobre, con le correzioni apportate a monte dalla versione precedente.
- **Una politica di sicurezza più rigorosa.** I componenti non possono caricare né inviare nulla altrove che a Libera Suite stessa. L'eccezione è un'immagine a cui un documento rimanda con il suo indirizzo web, che viene scaricata come in qualsiasi suite per ufficio.
- **Le macro sono disattivate, e conservate.** Le macro dei componenti sono JavaScript e non eseguono il VBA dei documenti di Microsoft Office, perciò sono disattivate. Le macro di un documento vengono conservate: salvare un `.docm`, un `.xlsm` o un `.pptm` lascia il suo VBA com'era, e Libera Words ora apre e salva i `.docm`.
- **I vecchi componenti vengono rimossi.** Ogni aggiornamento lasciava sul disco la versione precedente, circa 400 MB ciascuna. Una versione inutilizzata da quattro settimane ora viene rimossa.
- **Correzioni.** Il menu dei caratteri mostra ogni nome per intero. Una cartella di lavoro `.xlsb` si apre, invece di aprirsi come una presentazione vuota. Su macOS, uscire con Cmd-Q non lascia più documenti bloccati. Su Windows, l'elenco Recenti mostra il nome di ogni documento e non perde più le sue voci.

## Cosa viene tolto

- **Il salvataggio in `.xlsb`.** La scrittura di un file del genere andava in crash su Linux. Salvate invece in `.xlsx`; Excel apre entrambi.
- **Linux su arm64, per ora.** Non esiste una build arm64 della 0.5. Su queste macchine lo script di installazione installa la 0.4.1; una versione successiva tornerà a supportare arm64.

[Cosa funziona oggi](../main/status.md) indica cosa è pronto, cosa è a metà e cosa non è ancora iniziato.

## Segnalateci i problemi

Libera Suite è giovane, e ogni segnalazione conta. La più utile resta un documento che viene fuori sbagliato, allegato al vostro messaggio con l'output di `libera --diagnose`. [Commenti](../feedback.md) spiega come contattarci.

*Abilian*
