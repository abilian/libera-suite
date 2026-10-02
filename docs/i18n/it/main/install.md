# Installare

Libera Suite funziona su **Windows 10 e 11 (x64)**, **Linux (x86_64 e arm64)** e **macOS (Apple Silicon)**. L'installazione non chiede la password di amministratore: vale solo per il tuo account.

## Windows {#windows}

Scarica il programma di installazione e fai doppio clic:

<https://cdn.abilian.com/libera/bundles/Libera-Suite-Setup.exe>

Aggiunge Libera Suite al menu Start e al desktop, e la inserisce in *Apri con* di Esplora file. Tutto è incluso: dopo non c'è altro da scaricare.

Se preferisci un comando, questa riga in PowerShell fa la stessa cosa e in più verifica il download con la sua impronta pubblicata:

```powershell
irm https://cdn.abilian.com/libera/install.ps1 | iex
```

La prima volta Windows ti chiederà due cose:

- **«PC protetto da Windows»**, quando apri il programma di installazione scaricato. Non è ancora firmato con un certificato, ed è proprio questo che l'avviso controlla. Scegli *Ulteriori informazioni*, poi *Esegui comunque*. La riga PowerShell non lo attiva.
- **«Come vuoi aprire questo file?»**, la prima volta che fai doppio clic su un documento che anche un altro programma, come Word, sa aprire. Scegli Libera Suite, poi *Sempre*. Potrai cambiarlo in seguito in *Impostazioni › App › App predefinite*.

## Linux

Apri un terminale ed esegui:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

Se sulla tua macchina c'è Flatpak, questo installa Libera Suite come Flatpak, con tutto ciò che le serve, e la aggiunge al menu delle applicazioni. Altrimenti installa il comando `libera`; al primo avvio, questo indica i pacchetti di sistema che mancano alla tua distribuzione e il comando esatto per installarli.

Funziona su Ubuntu 22.04, Debian 12, Fedora 35, RHEL 9 e qualsiasi versione più recente. Senza Flatpak serve anche Python 3.12 o più recente; se manca, lo script lo segnala prima di cambiare qualsiasi cosa.

Se usi Homebrew su Linux, la riga Homebrew della sezione macOS qui sotto funziona anche lì.

## macOS

Con [Homebrew](https://brew.sh), apri il Terminale ed esegui:

```sh
brew install abilian/tap/libera
```

Homebrew costruisce Libera Suite sul tuo Mac. Al primo avvio di `libera`, ti propone di scaricare gli editor, circa 110 MB.

Senza Homebrew ti serve Python 3.12 o più recente, che macOS non include: installalo da [python.org](https://www.python.org/downloads/macos/). Poi esegui:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

In entrambi i casi ottieni il comando `libera`. Su macOS, per ora Libera Suite si avvia da un terminale: un'applicazione da aprire con un doppio clic è [nella roadmap](/en/develop/roadmap/).

## Avviarla

- **Windows:** dal menu Start o dal desktop, oppure con un doppio clic su un documento.
- **Linux:** dal menu delle applicazioni, oppure con `libera` in un terminale.
- **macOS:** con `libera` nel Terminale. Indica un documento per aprire proprio quello:

```sh
libera ~/Documents/relazione.docx
```

Da solo, `libera` apre la finestra iniziale, dove puoi creare un documento, aprirne uno o sceglierne uno recente:

![La finestra iniziale, con un riquadro New per ciascuno fra Document, Spreadsheet e Presentation, un pulsante Open e un elenco Recent di tre documenti.](../assets/start.png)

La pagina successiva è [Lavorare con i documenti](../guide/documents.md): aprire, salvare, esportare e stampare.

## Aggiornare

Esegui di nuovo lo stesso programma di installazione o lo stesso comando. La versione installata viene sostituita dalla più recente.

Con Homebrew, esegui `brew upgrade libera`. Se una nuova versione ha bisogno di nuovi editor, Libera Suite ti propone di scaricarli al suo avvio successivo.

## Disinstallare

- **Windows:** *Impostazioni › App › App installate › Libera Suite › Disinstalla*.
- **Linux, installata come Flatpak** (`flatpak list` mostra `eu.liberasuite.Libera`):

    ```sh
    flatpak uninstall --user eu.liberasuite.Libera
    rm -f ~/.local/share/applications/eu.liberasuite.Libera.desktop ~/.local/share/icons/hicolor/*/apps/eu.liberasuite.Libera.*
    ```

- **Linux, in altro modo:**

    ```sh
    libera --launcher-remove
    rm -rf ~/.local/bin/libera ~/.local/share/libera
    ```

- **macOS:**

    ```sh
    libera --payload-remove
    rm -rf ~/.local/bin/libera ~/.local/share/libera
    ```

- **Homebrew**, su entrambi i sistemi:

    ```sh
    libera --payload-remove
    brew uninstall libera
    ```

I tuoi documenti non vengono mai toccati. Ciò che Libera Suite conserva da una sessione all'altra, come l'elenco dei documenti recenti e le sessioni non salvate, resta al suo posto: in `~/Library/Application Support/Libera Suite` su macOS, in `~/.var/app/eu.liberasuite.Libera` per il Flatpak. Elimina quella cartella per non lasciare traccia.

## Se qualcosa va storto

Esegui questo in un terminale (su Windows, in PowerShell: `& "$env:LOCALAPPDATA\Programs\Libera Suite\libera-cli.exe" --diagnose`):

```sh
libera --diagnose
```

Il comando stampa una schermata. Contano soprattutto due righe:

- **`window`** dovrebbe dire `ok`. Su Linux, `NOT AVAILABLE` significa che mancano pacchetti di sistema; avviare `libera` mostra il comando per installarli.
- **`payload`** indica gli editor e la loro provenienza. `MISSING` significa che non sono stati scaricati: esegui `libera --payload-install`.

[Cosa funziona oggi](status.md) elenca i problemi che conosciamo già. Per tutto il resto, [scrivici](../feedback.md) e incolla l'output di `libera --diagnose`.

Per installare con `pipx` o `uv`, installare il Flatpak a mano o passare opzioni allo script di installazione, leggi [Altri modi di installare](alt-install.md).
