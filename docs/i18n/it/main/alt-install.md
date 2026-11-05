# Altri modi di installare

[Installare](install.md) indica il modo abituale per ogni piattaforma, adatto alla maggior parte delle persone. Questa pagina tratta tutto il resto: scegliere da sé un canale, installare a mano, sapere dove finiscono i file.

## Le opzioni dello script di installazione

`install.sh` accetta opzioni. Quando lo si esegue tramite una pipe, ha bisogno di `sh -s --` davanti a esse:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh -s -- --prefix ~/apps
curl -fsSL https://cdn.abilian.com/libera/install.sh | bash -s -- --help
```

| | |
| :--- | :--- |
| `--prefix DIR` | installare altrove (predefinito: `~/.local`) |
| `--channel pip` | su Linux, installare il pacchetto Python anche se c'è Flatpak |
| `--origin URL` | scaricare da un server diverso da quello pubblico |

Scrive solo in `~/.local/bin` e `~/.local/share`. Apri il suo indirizzo in un browser per leggerlo prima di eseguirlo.

## pipx o uv

Libera Suite è su PyPI con il nome `libera` e richiede Python 3.12 o più recente. I suoi [componenti](#the-editors) arrivano con lei. Su macOS e Windows:

```sh
uv tool install libera      # oppure: pipx install libera
```

Per provarla senza installarla, `uvx libera` la avvia da una cache.

Su Linux la finestra è disegnata da GTK, i cui collegamenti Python vengono dalla tua distribuzione e sono compilati per il suo Python. Un ambiente isolato non li vede, quindi `pipx` ha bisogno di due opzioni:

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
```

Senza di esse, Libera Suite si installa senza errori e poi non apre alcuna finestra. `uv tool` non ha un equivalente di `--system-site-packages`: su Linux usa `pipx`. Al primo avvio, `libera` indica i pacchetti GTK che mancano alla tua distribuzione; conosce apt, dnf, pacman e zypper.

## Il Flatpak, a mano

Ecco cosa fa lo script di installazione quando c'è Flatpak:

```sh
arch=amd64     # oppure arm64, secondo la tua macchina
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
# su arm64: ver=0.4.1, l'ultima versione compilata per questa piattaforma
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

`bundles/latest` contiene il numero della versione attuale, quindi queste righe restano valide da una versione all'altra. Il pacchetto, di circa 70 MB, contiene i componenti. Gira sull'ambiente di esecuzione GNOME, che `flatpak` scarica da Flathub la prima volta; una macchina senza la sorgente Flathub deve prima aggiungerla:

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

Dalla versione 0.7.0 ogni pacchetto ha accanto la sua firma, così puoi verificare prima di installarlo che sia proprio il nostro. Nella stessa cartella, con `ver` e `arch` impostati come sopra:

```sh
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak.asc"
curl -fsSL https://keys.openpgp.org/vks/v1/by-fingerprint/E1B31B9935BEDA0C53D21A1DD35A9ACA9BE0C732 | gpg --import
gpg --verify "libera-$ver-$arch.flatpak.asc" "libera-$ver-$arch.flatpak"
```

GnuPG deve dire `Firma valida da "Libera Suite release signing <releases@liberasuite.eu>"` (in inglese `Good signature from`), e l'impronta della chiave primaria che mostra deve essere `E1B3 1B99 35BE DA0C 53D2 1A1D D35A 9ACA 9BE0 C732`. L'avviso che la chiave non è certificata significa solo che non hai detto a GnuPG di fidarti di questa chiave. Lo script di installazione non fa questo controllo.

## I componenti {#the-editors}

Ogni canale installa i componenti insieme all'applicazione. Il programma di installazione per Windows e il Flatpak li contengono. Con pip, pipx o uv sono due pacchetti Python richiesti da `libera`: `libera-core`, il motore dei documenti, compilato per ciascuna piattaforma, e `libera-web`, i componenti di modifica e i caratteri. Insieme sono circa 90 MB da scaricare. Il primo avvio costruisce poi l'indice dei caratteri della tua macchina, il che richiede un momento.

PyPI ha `libera-core` per Windows x64, Linux x86_64 e macOS su Apple Silicon. Su qualsiasi altra macchina, pip lo compila dai sorgenti, il che richiede quasi un'ora e gli strumenti elencati in [Costruire i componenti](/en/develop/build/), in inglese.

Le versioni precedenti alla 0.7 scaricavano i loro componenti a parte, nelle cartelle qui sotto. `libera --payload-remove` elimina ciò che vi hanno lasciato.

## Dove si trovano i file

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/` oppure `~/.local/share/libera/` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |
| Windows | `%LOCALAPPDATA%\Libera Suite\` |

Lì Libera Suite conserva ciò che le serve da un avvio all'altro, come l'elenco Recenti e le sessioni non salvate. I componenti non sono lì: sono installati con l'applicazione, e `libera --payload-status` dice dove. Per usare componenti che stanno altrove, per esempio una build locale, imposta `LIBERA_PAYLOAD` sulla loro cartella; prevale su quelli installati.

## Una voce nel menu delle applicazioni su Linux {#a-launcher-entry-on-linux}

Lo script di installazione e il Flatpak aggiungono entrambi Libera Suite al menu delle applicazioni. Dopo qualsiasi altra installazione, questo comando fa lo stesso, solo per il tuo account: un'icona, *Apri con* e documenti che si aprono con un doppio clic.

```sh
libera --launcher-install
libera --launcher-remove     # per toglierla
```

## Un'applicazione da aprire con un doppio clic su macOS {#a-double-clickable-application-on-macos}

Lo script di installazione ne scrive una, `Libera.app`, nella cartella Applicazioni della tua cartella Inizio. Dopo qualsiasi altra installazione, come Homebrew, `pipx` o `uv tool`, questo comando fa lo stesso:

```sh
libera --launcher-install
libera --launcher-remove     # per toglierla
```

Apre i documenti con un doppio clic e mostra l'icona di Libera nel Dock. È un piccolo lanciatore per il Python dell'installazione che l'ha scritta: dopo averla disinstallata, o averla spostata su un altro Python, esegui di nuovo `libera --launcher-install`.

A partire da una copia del codice sorgente, puoi costruirne una per quella copia:

```sh
build/macos/macos-app.sh          # costruisce build/out/Libera.app
open build/out/Libera.app
```

Usa il Python di quella copia del codice, quindi ne dipende: lasciala dov'è; se la copia si sposta, ricostruiscila. Non è firmata: al primo avvio macOS dice **«impossibile aprire l'app perché non è possibile verificare lo sviluppatore»**. Da macOS 15 in poi, per andare avanti usa *Impostazioni di Sistema ▸ Privacy e sicurezza ▸ Apri comunque*.
