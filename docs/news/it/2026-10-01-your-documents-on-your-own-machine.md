---
date: 2026-10-01
description: Libera Suite, una suite per ufficio libera e gratuita per Windows, macOS e Linux, è in beta. Apre i file di Word, Excel e PowerPoint, non chiede nessun account e tiene i tuoi documenti sul tuo computer.
---

# Libera Suite: i tuoi documenti, sulla tua macchina

Oggi apriamo la beta di **Libera Suite**, una suite per ufficio libera e gratuita per Windows, macOS e Linux. Scrivi lettere e relazioni, tieni i tuoi conti in un foglio di calcolo, prepara una presentazione, tutto sul tuo computer, con i tuoi file. Nessun account da creare, nessun abbonamento da pagare.

[Installa Libera Suite](../main/install.md){ .md-button .md-button--primary }

![Libera Words con un documento aperto: la barra degli strumenti dell'editor nel viola di Libera Words e, sotto, una pagina impaginata.](../assets/words.png)

## Apre i file che ti mandano

Tutti mandano `.docx`. Libera Suite li apre, insieme ai `.xlsx` e ai `.pptx` che li accompagnano, e li impagina come li vedevano i loro autori: caratteri, immagini, tabelle e revisioni comprese. Quando salvi, ottieni un file nello stesso formato, che i tuoi colleghi aprono in Microsoft Office o in LibreOffice come qualsiasi altro.

Il merito è di un motore dei documenti che da vent'anni si vede consegnare i file degli altri. Libera Suite fa girare quel motore sul tuo computer.

| | | |
| :--- | :--- | :--- |
| **Libera Words** | Documenti di testo | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | Fogli di calcolo | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | Presentazioni | `.pptx` `.odp` |
| **Libera Diagrams** | Un visualizzatore di disegni Visio | `.vsdx` |

Trovi anche il resto di una suite per ufficio: una finestra iniziale con i documenti recenti, il controllo ortografico in cinque lingue, l'esportazione in PDF, la stampa e un ripristino che ti restituisce il lavoro se il computer si ferma a metà.

## Gratuita, e tua per sempre

Nessuna licenza da pagare, nessuna bolletta mensile. Installala su tutti i computer che vuoi e tienila finché vuoi. Nessun server deve restare pagato perché continui a funzionare, e nessuno può spegnerla a distanza.

Libera Suite è software libero: chiunque può leggerne il codice sorgente, modificarlo e condividerlo. L'applicazione è sotto Apache License 2.0 e gli editor sotto GNU AGPL v3. [Licenza e attribuzione](../licence.md) spiega come ottenere il codice sorgente esatto di ogni versione.

## I tuoi documenti restano sul tuo computer

Libera Suite legge e scrive i tuoi documenti sul tuo disco, con un software che si trova sul tuo disco, e non li carica mai da nessuna parte. Dietro non ci sono né account né cloud, e non c'è telemetria, né statistica d'uso, né segnalazione di crash: non ci invia nulla su di te, sui tuoi documenti o sul modo in cui la usi.

Si collega a internet per scaricare i suoi editor durante l'installazione. [La documentazione elenca](../index.md#what-leaves-your-machine) ogni sua connessione, e il codice sorgente è pubblico: puoi verificarlo.

## Una beta, con le lacune in vista

Libera Suite funziona su **Windows 10 e 11 (x64)**, **macOS (Apple Silicon)** e **Linux (x86_64 e arm64)**. Windows ha il suo programma di installazione, Linux un unico file Flatpak con dentro gli editor, e macOS un comando nel terminale.

Le lacune note sono [pubblicate per intero](../main/status.md) e tenute aggiornate. Ogni documento ha la sua finestra, perché le schede non ci sono ancora. Niente impedisce a due finestre di modificare lo stesso documento, e una delle due perderà le sue modifiche. Diagrams legge i file Visio ma non li salva. Windows diffida del programma di installazione finché non è firmato.

## Dicci cosa non va

La cosa più utile che puoi mandarci è **un documento che viene male, in allegato**. Il motore è maturo: quando un file viene male, la causa è molto più probabilmente dalla nostra parte, un carattere che non abbiamo incluso, una risorsa che non abbiamo servito. Li correggiamo in fretta, appena qualcuno ce ne mostra uno.

Se scegli il software per un'organizzazione, dicci **di cosa avrebbe bisogno** per cambiare. Oggi la risposta è ancora facile da orientare.

L'[installazione](../main/install.md) richiede un minuto, e [Commenti](../feedback.md) spiega come raggiungerci.

## Chi la fa

Libera Suite è sviluppata da [Abilian](https://abilian.com), un'azienda francese che fa software libero. I suoi editor vengono da [Euro-Office](https://github.com/Euro-Office), a sua volta un fork di [ONLYOFFICE](https://www.onlyoffice.com/), sviluppato da Ascensio System SIA. Il motore dei documenti e il supporto dei formati, la parte difficile di una suite per ufficio, sono loro, e non ne abbiamo riscritto nulla. Noi abbiamo costruito intorno l'applicazione desktop: le finestre, i menu, l'apertura e il salvataggio, e i pacchetti.

Il motore resta quello del progetto originale, costruito dai sorgenti a revisioni esatte, con [una breve serie di patch](/en/develop/patches/) nostra. La parte che manteniamo è piccola, e un gruppo piccolo può impegnarsi a curarla nel tempo.

*Abilian*

---

Microsoft, Word, Excel, PowerPoint, Visio e Windows sono marchi del gruppo di società Microsoft. LibreOffice è un marchio di The Document Foundation. ONLYOFFICE è un marchio di Ascensio System SIA. Gli altri nomi sono marchi dei rispettivi proprietari. Libera Suite non è affiliata a nessuno di essi né da essi approvata.
