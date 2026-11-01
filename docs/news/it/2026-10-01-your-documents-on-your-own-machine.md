---
date: 2026-10-01
description: Libera Suite, una suite per ufficio libera e gratuita per Linux, Windows e macOS, entra in beta pubblica. Apre e salva i formati di Microsoft Office e OpenDocument, senza account e senza servizi online.
---

# Libera Suite entra in beta pubblica

**Libera Suite** è una suite per ufficio libera e gratuita per Linux, Windows e macOS. Comprende un elaboratore di testi, un foglio di calcolo, un programma di presentazioni e un visualizzatore di file Visio. Funziona sul tuo computer, senza account, senza servizi online e senza telemetria. Apre e salva i formati di Microsoft Office e OpenDocument. La sua beta pubblica inizia oggi.

[Installa Libera Suite](../main/install.md){ .md-button .md-button--primary }

![Libera Words con un documento aperto: la barra degli strumenti dell'editor nel viola di Libera Words, e sotto una pagina impaginata.](../assets/words.png)

## Quattro applicazioni

| | | |
| :--- | :--- | :--- |
| **Libera Words** | Documenti di testo | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | Fogli di calcolo | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | Presentazioni | `.pptx` `.odp` |
| **Libera Diagrams** | Un visualizzatore di disegni Visio | `.vsdx` |

Un file Word, Excel o PowerPoint si apre con la sua impaginazione: caratteri, immagini, tabelle e revisioni comprese. Il salvataggio produce un file nello stesso formato, che Microsoft Office e LibreOffice aprono come qualsiasi altro.

Le quattro applicazioni condividono una finestra iniziale con i documenti recenti, il controllo ortografico in cinque lingue, l'esportazione in PDF, la stampa e il recupero del lavoro dopo un arresto anomalo.

## Libera e gratuita

Libera Suite non chiede né licenza né abbonamento. Puoi installarla su tutti i computer che vuoi e tenerla finché vuoi. Per funzionare non dipende da nessun nostro server.

È software libero: chiunque può leggerne il codice sorgente, modificarlo e condividerlo. L'applicazione è sotto licenza Apache 2.0 e i componenti di Euro-Office sotto GNU AGPL v3. [Licenza e attribuzione](../licence.md) spiega come ottenere il codice sorgente esatto di ogni versione.

## I tuoi documenti restano sul tuo computer

Libera Suite legge e scrive i tuoi documenti sul tuo disco e non li invia da nessuna parte. Non ci trasmette alcuna informazione su di te, sui tuoi documenti o sul modo in cui la usi.

Si collega a internet per scaricare i componenti di Euro-Office durante l'installazione. [La documentazione elenca](../index.md#what-leaves-your-machine) ciascuna delle sue connessioni, e il codice sorgente permette di verificarlo.

## Come installarla

- **Linux** (x86_64 e arm64): un comando nel terminale, che installa un pacchetto Flatpak quando Flatpak è presente.
- **macOS** (Apple Silicon): un comando nel terminale, con o senza Homebrew.
- **Windows** 10 e 11 (x64): un programma di installazione, senza diritti di amministratore.

La [pagina di installazione](../main/install.md) riporta i comandi.

## I limiti della beta

Ogni documento ha la sua finestra, senza schede. Ancora nulla impedisce a due finestre di modificare lo stesso documento: l'ultima che salva sovrascrive il lavoro dell'altra. Diagrams legge i file Visio ma non può salvarli. Il programma di installazione per Windows non è ancora firmato, quindi Windows mostra un avviso quando lo apri. [La pagina sullo stato](../main/status.md) riporta l'elenco completo e viene tenuta aggiornata.

## I tuoi commenti

Il motore di impaginazione è collaudato: quando un documento si vede male in Libera Suite, la causa sta quasi sempre nel nostro pacchetto, in un carattere o una risorsa mancante. Sono difetti che si correggono in fretta, a patto di vederli. Il commento più utile è quindi un documento che si vede male, allegato al tuo messaggio.

Se scegli il software per un'organizzazione, dicci quali funzioni le servirebbero per adottare Libera Suite.

[Commenti](../feedback.md) spiega come scriverci.

## Chi la sviluppa

Libera Suite è sviluppata da [Abilian](https://abilian.com), un'azienda francese di software libero. È costruita sui componenti di [Euro-Office](https://github.com/Euro-Office), un fork di [ONLYOFFICE](https://www.onlyoffice.com/), il software di Ascensio System SIA. Questi componenti forniscono il motore dei documenti e il supporto dei formati. Abilian ha scritto l'applicazione desktop che li ospita: le finestre, i menu, l'apertura e il salvataggio dei file, il pacchetto.

Compiliamo i componenti di Euro-Office dai loro sorgenti, a revisioni fissate. Le correzioni che vi applichiamo sono [pubblicate e spiegate](/en/develop/patches/).

*Abilian*

---

Microsoft, Word, Excel, PowerPoint, Visio e Windows sono marchi del gruppo di società Microsoft. LibreOffice è un marchio di The Document Foundation. ONLYOFFICE è un marchio di Ascensio System SIA. Gli altri nomi sono marchi dei rispettivi proprietari. Libera Suite non è affiliata a nessuno di essi né da essi approvata.
