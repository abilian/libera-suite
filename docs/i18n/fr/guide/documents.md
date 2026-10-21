# Travailler sur des documents

L'interface de Libera Suite est en anglais : les menus et les boutons sont cités ici tels qu'ils apparaissent à l'écran.

## Ouvrir {#open}

```sh
libera                             # la fenêtre de démarrage
libera ~/Documents/note.docx
libera ~/Documents/budget.xlsx
libera ~/Documents/reseau.vsdx
```

**C'est le document qui décide de l'application.** Aucune commande ne sert à en choisir une, de même qu'on ne choisit pas d'éditeur de texte pour ouvrir un `.txt` : vous ouvrez le document et la bonne application apparaît. Un `.xlsx` s'ouvre dans Tables, un `.pptx` dans Slides, un `.vsdx` dans Diagrams.

![La fenêtre de démarrage, avec une tuile New pour chacun des types Document, Spreadsheet et Presentation, un bouton Open, et une liste Recent de trois documents.](../assets/start.png)

Seule, la commande `libera` ouvre la **fenêtre de démarrage** : un nouveau document de n'importe quel type, une boîte de dialogue d'ouverture, vos documents récents et la provenance des composants. Choisissez quelque chose et la fenêtre de démarrage s'efface devant le document.

Libera Suite ouvre **un document par fenêtre**, si bien qu'un motif du shell se comporte comme prévu :

```sh
libera ~/Documents/*.docx     # une fenêtre chacun
```

Vous pouvez aussi ouvrir un document depuis la fenêtre du document, par **Fichier ▸ Ouvrir** ou **Fichier ▸ Ouvrir récent**. L'un et l'autre ouvrent une nouvelle fenêtre et laissent en place le document déjà ouvert.

**Sous macOS, les documents peuvent s'ouvrir en onglets** d'une même fenêtre. Libera Suite suit le réglage du système, *Préférer les onglets lors de l'ouverture de documents* dans Réglages Système ▸ Bureau et Dock, comme toute application de documents sur Mac. Réglé sur *Toujours*, chaque document s'ouvre dans un onglet. Sinon, il s'ouvre dans sa propre fenêtre, et **Fenêtre ▸ Merge All Windows** les rassemble. Le **+** au bout de la barre d'onglets ouvre la fenêtre de démarrage dans un nouvel onglet, et le document choisi prend sa place. Un onglet se détache en une fenêtre par glisser-déposer.

**Un document déposé** sur une fenêtre de Libera Suite, fenêtre de démarrage comprise, s'ouvre dans sa propre fenêtre. Une image déposée sur un document y est insérée.

**Fichier ▸ Nouveau** propose un document, une feuille de calcul ou une présentation depuis n'importe quelle fenêtre, chacun dans sa propre fenêtre. Sous macOS, `⌘N` en crée un du même type que la fenêtre au premier plan. Dans la fenêtre du document, **Fichier ▸ Nouveau document** vous demande lequel des trois créer.

## Enregistrer

**Fichier ▸ Enregistrer** réécrit le document que vous avez ouvert. **Fichier ▸ Enregistrer sous** demande où le placer. À partir de là, c'est ce document-là que vous modifiez.

L'enregistrement reconvertit le format de travail en un vrai document, en une seconde environ.

## Exporter

Enregistrer sous sert aussi à exporter : sa boîte de dialogue comporte une liste **Format de fichier**.

| | |
| :--- | :--- |
| Document Word | `.docx` |
| Modèle Word | `.dotx` |
| Texte OpenDocument | `.odt` |
| Modèle OpenDocument | `.ott` |
| PDF | `.pdf` |
| Texte mis en forme | `.rtf` |
| HTML | `.html` |
| Markdown | `.md` |
| EPUB | `.epub` |
| FictionBook | `.fb2` |
| Texte brut | `.txt` |

Choisir un format renomme le fichier dans la boîte de dialogue. Les deux ne peuvent pas diverger : vous ne pouvez pas obtenir un fichier ODT nommé `.docx`.

Le convertisseur ne sait pas écrire tous les formats qu'il sait lire. Le `.doc`, en particulier, s'ouvre mais ne s'enregistre pas ; utilisez `.docx` ou `.rtf` pour un document qui doit repartir vers une ancienne version de Word.

Si vous cherchez une entrée **Télécharger comme** dans le menu Fichier, il n'y en a pas. Les composants la masquent quand ils fonctionnent comme une application de bureau hors ligne ; ils mettent Enregistrer sous à sa place : la même fonction, une entrée plus haut dans le menu.

### En ligne de commande {#from-the-command-line}

`libera --convert` fait la même chose sans ouvrir de fenêtre, pour un document ou pour cent. Le format se nomme par son extension, avec `-t`, ou se lit dans le nom donné à `-o` :

```sh
libera --convert *.docx -t pdf             # rapport.pdf à côté de rapport.docx, etc.
libera --convert expose.pptx -o expose.odp # un seul document, nommé
libera --convert *.xlsx -t ods --outdir ods/
libera --convert rapport.docx -t pdf -o - | lp   # sur la sortie standard
```

Un fichier qui porte déjà le nouveau nom est remplacé. Le document converti n'est jamais écrasé, et deux documents qui aboutiraient au même nom sont refusés avant toute conversion. Les options sont celles de pandoc, sauf `-f` : l'extension dit de quel document il s'agit.

## La barre de menus

Sous Linux et Windows, la barre se trouve dans la fenêtre : **Fichier**, **Édition**, **Affichage** et **Aide**, ce dernier contenant *Aide de Libera* et *À propos de Libera Suite*. Le menu y impose trois différences. Aucun élément n'affiche de raccourci clavier, mais Ctrl-N, Ctrl-O, Ctrl-W, Ctrl-S, Ctrl-Maj-S, Ctrl-P et Ctrl-Z font sur ces systèmes l'équivalent des touches ⌘ ci-dessous sur un Mac. **Ouvrir un fichier récent** est construit au lancement de l'application : un document ouvert aujourd'hui y apparaît demain. Rien n'est grisé : Enregistrer sans rien à enregistrer ne fait rien.

Sous macOS, c'est une vraie barre de menus Mac, avec les mêmes éléments plus **Fenêtre**. Les raccourcis habituels y fonctionnent, que le document ait le focus ou non :

| | |
| :--- | :--- |
| `⌘N` `⌘O` | Nouveau (du type de la fenêtre au premier plan), Ouvrir : chacun dans sa propre fenêtre, ou son onglet |
| `⌘S` `⇧⌘S` | Enregistrer, Enregistrer sous |
| `⌘P` | Imprimer |
| `⌘W` | Fermer, en demandant d'abord quoi faire des modifications non enregistrées |
| `⌘Z` `⇧⌘Z` | Annuler, Rétablir |
| `⌘F` | Rechercher |
| `⌘?` | Cette documentation |
| `⌘+` `⌘-` `⌘0` | Zoom avant, arrière, ajuster la page |
| `⌘8` | Marques de mise en forme |

**Fichier ▸ Ouvrir un fichier récent** est reconstruit à chaque ouverture du menu. Le menu **Fenêtre** liste tous les documents ouverts.

Enregistrer, Annuler et Rétablir sont grisés quand il n'y a rien à enregistrer ou à annuler. Les composants refusent ces commandes sans rien dire : un élément de menu resté actif aurait l'air cassé.

## Fermer

Fermer une fenêtre qui contient des modifications non enregistrées demande d'abord quoi faire : **Enregistrer**, **Ne pas enregistrer** ou **Annuler**.

Choisir Ne pas enregistrer n'est pas définitif. Libera Suite conserve votre travail et vous le propose à la prochaine ouverture de ce document.

## Imprimer

**Fichier ▸ Imprimer**, ou le bouton de l'imprimante, produit un PDF du document, demande où le conserver (dans le dossier du document, sauf si vous en choisissez un autre), puis l'ouvre dans le lecteur de PDF de votre système, où se trouve la boîte de dialogue d'impression.

C'est le choix fait pour l'instant : le lecteur que vous avez déjà vous donne les plages de pages, le format du papier, la mise à l'échelle et un aperçu, que nous ne ferions pas mieux dans une première version.

## Images

Les images intégrées à un document sont conservées à l'ouverture et à l'enregistrement. **Insertion ▸ Image** ajoute une image depuis le disque.

## Correction orthographique {#spell-checking}

Les fautes sont soulignées ; le clic droit propose des suggestions. Le dictionnaire utilisé dépend de **la langue du document**, que vous réglez dans la **barre d'état** en bas de la fenêtre, pour chaque document.

Des dictionnaires sont fournis pour cinq langues : l'anglais (américain et britannique), le français, l'allemand, l'espagnol et l'italien. Une langue sans dictionnaire n'est pas une erreur ; ses mots sont simplement considérés comme corrects. Les mots ajoutés par *Add to dictionary* sont conservés : ils sont désormais corrects dans tous les documents et toutes les langues.

## Votre nom dans les documents {#your-name-in-documents}

Les modifications suivies et les commentaires sont attribués à une personne, dont le nom est écrit dans le fichier enregistré. Libera Suite le prend dans votre compte : votre nom complet tel que macOS le connaît, le nom affiché de votre compte Windows, ou le champ « nom complet » de votre compte Unix sous Linux, à défaut votre identifiant de connexion.

Pour utiliser un autre nom, inscrivez-le dans le fichier de configuration, en créant le fichier s'il n'existe pas :

```toml
user_name = "Jeanne Dupont"
```

| | |
| :--- | :--- |
| Linux | `$XDG_CONFIG_HOME/libera/config.toml`, or `~/.config/libera/config.toml` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/config/libera/config.toml` |
| macOS | `~/Library/Application Support/Libera Suite/config.toml` |
| Windows | `%USERPROFILE%\.config\libera\config.toml` |

Le nom s'applique aux fenêtres ouvertes après le prochain démarrage de Libera Suite. Les documents déjà enregistrés gardent le nom sous lequel ils l'ont été.

Le même fichier désactive la recherche quotidienne d'une nouvelle version, sur une ligne à part :

```toml
check_updates = false
```

Une autre s'en tient aux polices fournies par Libera Suite, sans celles installées sur votre machine, pour qu'un document s'affiche de la même façon sur tous les ordinateurs :

```toml
installed_fonts = false
```

Une dernière fixe la langue des applications, quand elle ne doit pas être celle de votre système. Un nouveau document prend toujours son format de papier dans la région de votre système :

```toml
ui_language = "fr"
```

Pour utiliser un autre fichier le temps d'un lancement, sans toucher à celui-ci, indiquez-le avec `libera --config FICHIER` (ou `-c FICHIER`), ou dans la variable d'environnement `LIBERA_CONFIG`. Un Libera Suite lancé ainsi ne confie pas ses documents à celui qui serait déjà ouvert, qui les ouvrirait avec sa propre configuration : quittez d'abord ce dernier.

## Où vont vos fichiers de travail

Tant qu'un document est ouvert, Libera Suite conserve un dossier de session à côté de ses données d'application. Il contient la copie de travail et le journal de vos modifications : l'enregistrement est ainsi rapide et l'annulation fiable. Ce n'est pas une sauvegarde : le document est là où vous l'avez enregistré.

---

La page suivante est l'[État des lieux](../main/status.md) : les fonctions disponibles et les problèmes que nous connaissons déjà. Si vous en rencontrez un qui n'y figure pas, [écrivez-nous](../feedback.md).
