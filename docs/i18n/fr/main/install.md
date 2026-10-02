# Installer

Libera Suite fonctionne sous **Windows 10 et 11 (x64)**, **Linux (x86_64 et arm64)** et **macOS (Apple Silicon)**. L'installation ne demande aucun mot de passe administrateur : elle se fait pour votre compte seulement.

## Windows {#windows}

Téléchargez l'installateur et double-cliquez dessus :

<https://cdn.abilian.com/libera/bundles/Libera-Suite-Setup.exe>

Il ajoute Libera Suite au menu Démarrer, sur le bureau et dans *Ouvrir avec* de l'Explorateur. Tout est inclus : il n'y a rien à télécharger ensuite.

Si vous préférez une commande, cette ligne dans PowerShell fait la même chose et vérifie en plus le téléchargement par rapport à son empreinte publiée :

```powershell
irm https://cdn.abilian.com/libera/install.ps1 | iex
```

La première fois, Windows vous demandera deux choses :

- **« Windows a protégé votre ordinateur »**, à l'ouverture de l'installateur téléchargé. Cet avertissement vise les programmes sans signature : l'installateur n'a pas encore de certificat. Choisissez *Informations complémentaires*, puis *Exécuter quand même*. La ligne PowerShell ne le déclenche pas.
- **« Comment voulez-vous ouvrir ce fichier ? »**, la première fois que vous double-cliquez sur un document qu'un autre programme, Word par exemple, sait aussi ouvrir. Choisissez Libera Suite et cochez *Toujours*. Vous pourrez changer ce choix dans *Paramètres › Applications › Applications par défaut*.

## Linux

Ouvrez un terminal et lancez :

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

Si votre machine dispose de Flatpak, cette commande installe Libera Suite sous forme de Flatpak, avec toutes ses dépendances, puis l'ajoute au menu des applications. Sinon, elle installe la commande `libera` ; au premier lancement, celle-ci indique les paquets système qui manquent à votre distribution et la commande exacte pour les installer.

Elle fonctionne sous Ubuntu 22.04, Debian 12, Fedora 35, RHEL 9 et toute version plus récente. Sans Flatpak, il lui faut aussi Python 3.12 ou plus récent ; s'il manque, elle le signale avant de modifier quoi que ce soit.

Si vous utilisez Homebrew sous Linux, la ligne Homebrew de la section macOS ci-dessous fonctionne aussi.

## macOS

Avec [Homebrew](https://brew.sh), ouvrez le Terminal et lancez :

```sh
brew install abilian/tap/libera
```

Homebrew construit Libera Suite sur votre Mac. Au premier lancement de `libera`, celle-ci propose de télécharger les éditeurs, environ 110 Mo.

Sans Homebrew, il vous faut Python 3.12 ou plus récent, que macOS ne fournit pas : installez-le depuis [python.org](https://www.python.org/downloads/macos/). Lancez ensuite :

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

Dans les deux cas, vous obtenez la commande `libera`. Sous macOS, Libera Suite se lance pour l'instant depuis un terminal : une application à double-cliquer figure [dans la feuille de route](/en/develop/roadmap/).

## La lancer

- **Windows :** depuis le menu Démarrer ou le bureau, ou en double-cliquant sur un document.
- **Linux :** depuis le menu des applications, ou avec `libera` dans un terminal.
- **macOS :** avec `libera` dans le Terminal. Donnez-lui un document pour ouvrir celui-là :

```sh
libera ~/Documents/rapport.docx
```

Seule, la commande `libera` ouvre la fenêtre de démarrage, où vous pouvez créer un document, en ouvrir un ou en choisir un récent :

![La fenêtre de démarrage, avec une tuile New pour chacun des types Document, Spreadsheet et Presentation, un bouton Open, et une liste Recent de trois documents.](../assets/start.png)

La page suivante est [Travailler sur des documents](../guide/documents.md) : ouvrir, enregistrer, exporter et imprimer.

## Mettre à jour

Relancez le même installateur ou la même commande. La version installée est remplacée par la plus récente.

Avec Homebrew, lancez `brew upgrade libera`. Si une nouvelle version a besoin de nouveaux éditeurs, Libera Suite propose de les télécharger à son lancement suivant.

## Désinstaller

- **Windows :** *Paramètres › Applications › Applications installées › Libera Suite › Désinstaller*.
- **Linux, installée en Flatpak** (`flatpak list` affiche `eu.liberasuite.Libera`) :

    ```sh
    flatpak uninstall --user eu.liberasuite.Libera
    rm -f ~/.local/share/applications/eu.liberasuite.Libera.desktop ~/.local/share/icons/hicolor/*/apps/eu.liberasuite.Libera.*
    ```

- **Linux, autrement :**

    ```sh
    libera --launcher-remove
    rm -rf ~/.local/bin/libera ~/.local/share/libera
    ```

- **macOS :**

    ```sh
    libera --payload-remove
    rm -rf ~/.local/bin/libera ~/.local/share/libera
    ```

- **Homebrew**, sur l'un ou l'autre système :

    ```sh
    libera --payload-remove
    brew uninstall libera
    ```

Vos documents ne sont jamais touchés. Les données que Libera Suite conserve d'une session à l'autre, comme la liste des documents récents et les sessions non enregistrées, restent en place : dans `~/Library/Application Support/Libera Suite` sous macOS et dans `~/.var/app/eu.liberasuite.Libera` pour le Flatpak. Supprimez ce dossier pour n'en laisser aucune trace.

## En cas de problème

Lancez ceci dans un terminal (sous Windows, dans PowerShell : `& "$env:LOCALAPPDATA\Programs\Libera Suite\libera-cli.exe" --diagnose`) :

```sh
libera --diagnose
```

La commande affiche un écran. Deux lignes comptent surtout :

- **`window`** doit indiquer `ok`. Sous Linux, `NOT AVAILABLE` signifie qu'il manque des paquets système ; lancer `libera` affiche la commande pour les installer.
- **`payload`** désigne les éditeurs et leur provenance. `MISSING` signifie qu'ils n'ont pas été téléchargés : lancez `libera --payload-install`.

La page [État des lieux](status.md) recense les problèmes que nous connaissons déjà. Pour tout le reste, [écrivez-nous](../feedback.md), en collant la sortie de `libera --diagnose`.

Pour installer avec `pipx` ou `uv`, installer le Flatpak à la main ou passer des options au script d'installation, lisez [Autres façons d'installer](alt-install.md).
