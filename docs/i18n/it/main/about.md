# Informazioni

Libera Suite è sviluppata da [Abilian](https://abilian.com), un'azienda francese che produce software libero. Stefane Fermigier guida il progetto.

Il codice sorgente è pubblico, su [github.com/abilian/libera-suite](https://github.com/abilian/libera-suite). L'applicazione host, la parte scritta da noi, è sotto licenza Apache 2.0; gli editor sono sotto GNU AGPL v3. [Licenza e attribuzione](../licence.md) spiega i dettagli, compreso come ottenere il codice sorgente esatto di ogni versione.

## Riconoscimenti

Libera Suite si regge sul lavoro di altri. Gran parte di ciò che vedi quando modifichi un documento è loro.

### Gli editor

Libera Suite include componenti di [**Euro-Office**](https://github.com/Euro-Office), a sua volta un fork di **ONLYOFFICE**, sviluppato da Ascensio System SIA. Il motore dei documenti, i quattro editor, il convertitore di formati e il supporto di ogni formato vengono da lì, modificati da [una breve serie di patch](/en/develop/patches/) nostra. La parte più difficile di una suite per ufficio sono vent'anni passati a leggere correttamente i documenti `.docx` degli altri. Quella parte è loro.

Dalla stessa organizzazione vengono i modelli vuoti da cui parte ogni nuovo documento, i dizionari del controllo ortografico (inglese, francese, tedesco, spagnolo e italiano) e i caratteri forniti con Libera Suite: Liberation, Carlito, Caladea, Open Sans e Asana Math, tra gli altri, ciascuno con la propria licenza libera.

Sotto gli editor ci sono molte altre librerie, V8 e Boost tra le più grandi, che la build di Euro-Office porta con sé.

### L'applicazione

- [**Python**](https://www.python.org), in cui è scritta tutta l'applicazione host.
- [**pywebview**](https://pywebview.flowrl.com), che mette una vista web in una finestra nativa su ogni piattaforma. Su macOS passa per [**PyObjC**](https://pyobjc.readthedocs.io); su Linux per [**PyGObject**](https://pygobject.gnome.org) e WebKitGTK.
- I motori web che mostrano gli editor: **WebKit** su macOS e Linux; **WebView2** di Microsoft su Windows.
- Su Linux, l'[**ambiente di esecuzione GNOME**](https://flathub.org/apps/org.gnome.Platform) su cui gira il Flatpak, e [**Flatpak**](https://flatpak.org) stesso.
- Su Windows, [**PyInstaller**](https://pyinstaller.org), che impacchetta l'applicazione con il suo Python; [**Inno Setup**](https://jrsoftware.org/isinfo.php) costruisce il programma di installazione.

### Questo sito

Costruito con [**Zensical**](https://zensical.org). I caratteri, [**Inter**](https://rsms.me/inter/) e [**JetBrains Mono**](https://www.jetbrains.com/lp/mono/), sono sotto SIL Open Font License e vengono serviti da questo sito stesso.

## Contatti

Per un bug, una domanda o un suggerimento, vedi [Commenti](../feedback.md).
