# Libera Suite ed Euro-Office Desktop

**Lo stesso motore, un altro involucro.**

Libera Suite ed Euro-Office Desktop Editors usano gli stessi componenti. `sdkjs`, `web-apps` e il convertitore `x2t` vengono dai repository di Euro-Office, alle revisioni delle loro versioni pubblicate. Un documento si visualizza, si importa e si esporta quindi allo stesso modo in entrambi, a parte le nostre correzioni. I due differiscono soprattutto per l'applicazione che li circonda.

**Euro-Office Desktop Editors** riprende l'architettura di ONLYOFFICE Desktop: un browser Chromium incorporato (CEF) e un'interfaccia Qt, in C++ (i repository `desktop-sdk` e `desktop-apps`).

**Libera Suite** sostituisce questo strato con qualche migliaio di righe di Python e JavaScript. I componenti vengono mostrati nel motore web già presente nel sistema: WebKit su macOS e Linux, WebView2 su Windows. Non vedono la differenza. Si rivolgono alla stessa interfaccia nativa (`AscDesktopEditor`), che abbiamo riscritto.

Questa scelta ha diverse conseguenze.

- **Dimensioni.** Per la versione 9.3.5-2, il `.dmg` per macOS di Euro-Office pesa 926 MB e il programma di installazione autonomo per Windows 616 MB. Libera Suite scarica circa 90 MB di componenti, più un'applicazione di pochi megabyte.
- **Installazione.** `pip` o `pipx`, Homebrew (macOS e Linux), Flatpak, un programma di installazione per Windows, o una riga `curl | sh`.
- **Riga di comando.** `libera --convert *.docx -t pdf` converte documenti senza aprire una finestra.
- **Correzioni.** Compiliamo tutto dai sorgenti di Euro-Office, con una [serie di correzioni pubblicata](/en/develop/patches/). Riguarda soprattutto il convertitore, per i file OpenDocument e CSV. Le versioni di Euro-Office oggi non le contengono.
- **Licenza.** L'applicazione è sotto Apache 2.0 e i componenti restano sotto AGPL.

Euro-Office Desktop ha oggi alcune funzioni che Libera Suite non ha ancora: la modifica dei PDF e i moduli, le firme digitali, e la connessione a un server Nextcloud, ownCloud o Seafile per la modifica condivisa. [La roadmap](/en/develop/roadmap/) dice quando arrivano. Ha anche le schede su Linux e Windows, dove Libera Suite tiene una finestra per documento: in una sola finestra i documenti condividerebbero un solo processo, e uno occupato bloccherebbe gli altri.

**In breve:** per ritrovare tutto ONLYOFFICE Desktop in un progetto europeo, Euro-Office Desktop è la scelta giusta. Libera Suite fa un'altra scommessa: un'applicazione più leggera, fatta di codice breve che un piccolo team può leggere e mantenere, che aggiunge funzioni senza toccare il motore di modifica.
