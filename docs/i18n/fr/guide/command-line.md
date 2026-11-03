# Ligne de commande

Libera Suite s'utilise depuis ses fenêtres, mais un terminal donne accès à quelques opérations qu'aucune fenêtre n'offre : convertir tout un dossier de documents d'un coup et rédiger le rapport qu'un bogue demande.

La commande est `libera`, sous Linux et macOS. Installée en Flatpak, elle s'écrit `flatpak run eu.liberasuite.Libera`, suivie des mêmes options. Sous Windows, c'est `libera-cli.exe`, dans le dossier d'installation de Libera Suite ; elle n'est pas dans le `PATH`.

## Ouvrir

| | |
| :--- | :--- |
| `libera` | la fenêtre d'accueil : nouveau, ouvrir, récents |
| `libera FICHIER...` | chaque document dans sa propre fenêtre ; le fichier décide de l'application. [Plus de détails](documents.md#open) |

## Convertir

| | |
| :--- | :--- |
| `libera --convert FICHIER... -t FORMAT` | chaque document écrit au `FORMAT` voulu, à côté de l'original, sans fenêtre. `FORMAT` est une extension : `pdf`, `odt`, `docx`, `xlsx`, `csv`... |
| `-o FICHIER` | pour un seul document : le fichier à écrire, dont l'extension donne le format, sauf si `-t` en dit un autre. `-o -` écrit sur la sortie standard |
| `--outdir DOSSIER` | écrire dans `DOSSIER` plutôt qu'à côté de chaque document |

[Plus de détails, avec des exemples](documents.md#from-the-command-line).

## Les composants

| | |
| :--- | :--- |
| `libera --payload-status` | l'emplacement des [composants](../main/alt-install.md#the-editors), leur version et le [code source](../licence.md#corresponding-source) dont ils sont issus |
| `libera --payload-remove` | supprimer les composants que téléchargeaient les versions antérieures à la 0.7, dont celle-ci ne se sert pas. [Plus de détails](../main/install.md#update) |

## Le menu des applications et Ouvrir avec

| | |
| :--- | :--- |
| `libera --launcher-install` | ajouter Libera Suite à vos applications, avec *Ouvrir avec* : au menu des applications sous Linux ([plus de détails](../main/alt-install.md#a-launcher-entry-on-linux)), en tant que `Libera.app` dans votre dossier Applications sous macOS ([plus de détails](../main/alt-install.md#a-double-clickable-application-on-macos)). |
| `libera --launcher-remove` | l'en retirer |

Le Flatpak, l'installateur Windows et, sous macOS, le script d'installation s'en chargent eux-mêmes.

## En cas de problème

| | |
| :--- | :--- |
| `libera --diagnose` | toutes les informations utiles à un rapport de bogue, sur un seul écran. [Plus de détails](../main/install.md#if-something-goes-wrong) |
| `libera --version` | la version de l'application et celle des composants |
| `-v`, `-vv`, `-vvv` | dire les actions en cours ; leur détail ; chaque requête aux composants |
| `-q` | les erreurs seulement |

`libera --help` liste toutes les options, et `libera --convert --help` celles du convertisseur.
