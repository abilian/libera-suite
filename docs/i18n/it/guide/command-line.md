# Riga di comando

Libera Suite si usa dalle sue finestre, ma un terminale arriva dove nessuna finestra arriva: convertire in un colpo solo un'intera cartella di documenti, installare i componenti su una macchina raggiunta via SSH, preparare il rapporto che un bug richiede.

Il comando è `libera`, su Linux e macOS. Installato come Flatpak diventa `flatpak run eu.liberasuite.Libera`, seguito dalle stesse opzioni. Su Windows è `libera-cli.exe`, nella cartella in cui è installato Libera Suite; non è nel `PATH`.

## Aprire

| | |
| :--- | :--- |
| `libera` | la finestra iniziale: nuovo, apri, recenti |
| `libera FILE...` | ogni documento in una finestra sua; è il file a scegliere l'applicazione. [Altro](documents.md#open) |

## Convertire

| | |
| :--- | :--- |
| `libera --convert FILE... -t FORMATO` | ogni documento scritto nel `FORMATO`, accanto all'originale, senza finestra. `FORMATO` è un'estensione: `pdf`, `odt`, `docx`, `xlsx`, `csv`... |
| `-o FILE` | per un solo documento: il file da scrivere, il cui formato viene dall'estensione, salvo diversa indicazione di `-t`. `-o -` scrive sull'output standard |
| `--outdir CARTELLA` | scrivere in `CARTELLA` invece che accanto a ogni documento |

[Altro, con esempi](documents.md#from-the-command-line).

## I componenti

| | |
| :--- | :--- |
| `libera --payload-install` | scaricare, verificare e installare i componenti. `--from CARTELLA` li installa da una cartella. [Altro](../main/alt-install.md#the-editors) |
| `libera --payload-status` | dove sono i componenti, la loro versione e il [codice sorgente](../licence.md#corresponding-source) da cui sono stati compilati |
| `libera --payload-remove` | eliminarli. [Altro](../main/install.md#uninstall) |

## Il menu delle applicazioni su Linux

| | |
| :--- | :--- |
| `libera --launcher-install` | aggiungere Libera Suite al menu delle applicazioni, con *Apri con*. [Altro](../main/alt-install.md#a-launcher-entry-on-linux) |
| `libera --launcher-remove` | toglierlo di nuovo |

Il Flatpak lo fa da sé.

## Se qualcosa va storto

| | |
| :--- | :--- |
| `libera --diagnose` | tutto quello che serve a una segnalazione di bug, in una sola schermata. [Altro](../main/install.md#if-something-goes-wrong) |
| `libera --version` | la versione dell'applicazione e quella dei componenti |
| `-v`, `-vv`, `-vvv` | dire che cosa sta facendo; come; ogni richiesta ai componenti |
| `-q` | solo gli errori |

`libera --help` elenca tutte le opzioni, e `libera --convert --help` quelle del convertitore.
