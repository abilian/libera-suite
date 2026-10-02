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
| `--no-payload` | installare subito il comando, scaricare gli editor più tardi |
| `--origin URL` | scaricare da un server diverso da quello pubblico |

Scrive solo in `~/.local/bin` e `~/.local/share`. Apri il suo indirizzo in un browser per leggerlo prima di eseguirlo.

## pipx o uv

Libera Suite è su PyPI con il nome `libera` e richiede Python 3.12 o più recente. Su macOS:

```sh
uv tool install libera      # oppure: pipx install libera
libera --payload-install
```

Su Linux la finestra è disegnata da GTK, i cui collegamenti Python vengono dalla tua distribuzione e sono compilati per il suo Python. Un ambiente isolato non li vede, quindi `pipx` ha bisogno di due opzioni:

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
libera --payload-install
```

Senza di esse, Libera Suite si installa senza errori e poi non apre alcuna finestra. `uv tool` non ha un equivalente di `--system-site-packages`: su Linux usa `pipx`. Al primo avvio, `libera` indica i pacchetti GTK che mancano alla tua distribuzione; conosce apt, dnf, pacman e zypper.

## Il Flatpak, a mano

Ecco cosa fa lo script di installazione quando c'è Flatpak:

```sh
arch=amd64     # oppure arm64, secondo la tua macchina
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

`bundles/latest` contiene il numero della versione attuale, quindi queste righe restano valide da una versione all'altra. Il pacchetto, di circa 82 MB, contiene gli editor. Gira sull'ambiente di esecuzione GNOME, che `flatpak` scarica da Flathub la prima volta; una macchina senza la sorgente Flathub deve prima aggiungerla:

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

## Gli editor

Il programma di installazione per Windows e il Flatpak includono gli editor. Tutti gli altri canali li scaricano una volta, dopo l'applicazione. `libera` lo propone al primo avvio; questo comando avvia direttamente il download:

```sh
libera --payload-install
```

Scarica circa 120 MB da `cdn.abilian.com` e verifica ogni file con le impronte fornite con l'applicazione, fermandosi al primo che non corrisponde. Poi costruisce l'indice dei caratteri della tua macchina, il che richiede un momento.

Per installare editor che hai costruito tu, o che ti sono stati forniti, indicagli la loro cartella:

```sh
libera --payload-install --from /percorso/degli/artefatti
```

[Build the payload](/en/develop/build/), in inglese, spiega come costruirli. `libera --payload-remove` li elimina; occupano circa 450 MB su disco.

## Dove si trovano i file

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/` oppure `~/.local/share/libera/` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |
| Windows | `%LOCALAPPDATA%\Libera Suite\` |

Gli editor si trovano lì, in `payload/<version>/`. Per usare editor che stanno altrove, per esempio una build locale, imposta `LIBERA_PAYLOAD` sulla loro cartella; prevale su tutto quanto sopra.

## Una voce nel menu delle applicazioni su Linux

Lo script di installazione e il Flatpak aggiungono entrambi Libera Suite al menu delle applicazioni. Dopo qualsiasi altra installazione, questo comando fa lo stesso, solo per il tuo account: un'icona, *Apri con* e documenti che si aprono con un doppio clic.

```sh
libera --launcher-install
libera --launcher-remove     # per toglierla
```

## Un'applicazione da aprire con un doppio clic su macOS {#a-double-clickable-application-on-macos}

Non ne esiste ancora una pronta. A partire da una copia del codice sorgente, puoi costruirtene una:

```sh
build/macos-app.sh          # costruisce build/out/Libera.app
open build/out/Libera.app
```

Apre i documenti con un doppio clic e mostra l'icona di Libera nel Dock. Usa il Python con cui è stata costruita, quindi dipende da quella copia del codice: lasciala dov'è; se la copia si sposta, ricostruiscila. Non è firmata: al primo avvio macOS dice **«impossibile aprire l'app perché non è possibile verificare lo sviluppatore»**. Da macOS 15 in poi, per andare avanti usa *Impostazioni di Sistema ▸ Privacy e sicurezza ▸ Apri comunque*.
