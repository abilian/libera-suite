# Travailler sur des documents

L'interface de Libera Suite est en anglais : les menus et les boutons sont cités ici tels qu'ils apparaissent à l'écran.

## Ouvrir

```sh
libera                             # la fenêtre de démarrage
libera ~/Documents/note.docx
libera ~/Documents/budget.xlsx
libera ~/Documents/reseau.vsdx
```

**C'est le document qui décide de l'éditeur.** Aucune commande ne sert à en choisir un, de même qu'on ne choisit pas d'éditeur de texte pour ouvrir un `.txt` : vous ouvrez le document et le bon éditeur apparaît. Un `.xlsx` s'ouvre dans Tables, un `.pptx` dans Slides, un `.vsdx` dans Diagrams.

![La fenêtre de démarrage, avec une tuile New pour chacun des types Document, Spreadsheet et Presentation, un bouton Open, et une liste Recent de trois documents.](../assets/start.png)

Seule, la commande `libera` ouvre la **fenêtre de démarrage** : un nouveau document de n'importe quel type, une boîte de dialogue d'ouverture, vos documents récents et la provenance des éditeurs. Choisissez quelque chose et la fenêtre de démarrage s'efface devant le document.

Libera Suite ouvre **un document par fenêtre**, si bien qu'un motif du shell se comporte comme prévu :

```sh
libera ~/Documents/*.docx     # une fenêtre chacun
```

Vous pouvez aussi ouvrir un document depuis l'éditeur, par **File ▸ Open** ou **File ▸ Open Recent**. L'un et l'autre ouvrent une nouvelle fenêtre et laissent en place le document déjà ouvert.

**File ▸ New** propose un document (Document), une feuille de calcul (Spreadsheet) ou une présentation (Presentation) depuis n'importe quelle fenêtre, chacun dans sa propre fenêtre. Sous macOS, `⌘N` en crée un du même type que la fenêtre au premier plan. Dans l'éditeur, **File ▸ Create New** vous demande lequel des trois créer.

## Enregistrer

**File ▸ Save** réécrit le document que vous avez ouvert. **File ▸ Save As** demande où le placer. À partir de là, c'est ce document-là que vous modifiez.

L'enregistrement reconvertit le format de travail de l'éditeur en un vrai document, en une seconde environ.

## Exporter

Save As sert aussi à exporter : sa boîte de dialogue comporte une liste **File Format**.

| | |
| :--- | :--- |
| Word Document | `.docx` |
| Word Template | `.dotx` |
| OpenDocument Text | `.odt` |
| OpenDocument Template | `.ott` |
| PDF | `.pdf` |
| Rich Text Format | `.rtf` |
| HTML | `.html` |
| Markdown | `.md` |
| EPUB | `.epub` |
| FictionBook | `.fb2` |
| Plain Text | `.txt` |

Choisir un format renomme le fichier dans la boîte de dialogue. Les deux ne peuvent pas diverger : vous ne pouvez pas obtenir un fichier ODT nommé `.docx`.

Le convertisseur ne sait pas écrire tous les formats qu'il sait lire. Le `.doc`, en particulier, s'ouvre mais ne s'enregistre pas ; utilisez `.docx` ou `.rtf` pour un document qui doit repartir vers une ancienne version de Word.

Si vous cherchez une entrée **Download As** dans le menu File, il n'y en a pas. Les éditeurs la masquent quand ils fonctionnent comme une application de bureau hors ligne ; ils mettent Save As à sa place : la même fonction, une entrée plus haut dans le menu.

## La barre de menus

Sous Linux et Windows, la barre se trouve dans la fenêtre : **File**, **Edit**, **View** et **Help**, ce dernier contenant *Libera Help* et *About Libera Suite*. Le menu y impose trois différences. Aucun élément n'a de raccourci clavier : les touches ci-dessous appartiennent à l'éditeur et fonctionnent dans la page. **Open Recent** est construit au lancement de l'application : un document ouvert aujourd'hui y apparaît demain. Rien n'est grisé : Save sans rien à enregistrer ne fait rien.

Sous macOS, c'est une vraie barre de menus Mac, avec les mêmes éléments plus **Window**. Les raccourcis habituels y fonctionnent, que l'éditeur ait le focus ou non :

| | |
| :--- | :--- |
| `⌘N` `⌘O` | Nouveau (du type de la fenêtre au premier plan), Ouvrir : chacun dans sa propre fenêtre |
| `⌘S` `⇧⌘S` | Enregistrer, Enregistrer sous |
| `⌘P` | Imprimer |
| `⌘W` | Fermer, en demandant d'abord quoi faire des modifications non enregistrées |
| `⌘Z` `⇧⌘Z` | Annuler, Rétablir |
| `⌘F` | Rechercher |
| `⌘?` | Cette documentation |
| `⌘+` `⌘-` `⌘0` | Zoom avant, arrière, ajuster la page |
| `⌘8` | Marques de mise en forme |

**File ▸ Open Recent** est reconstruit à chaque ouverture du menu. Le menu **Window** liste tous les documents ouverts.

Save, Undo et Redo sont grisés quand il n'y a rien à enregistrer ou à annuler. L'éditeur refuse ces commandes sans rien dire : un élément de menu resté actif aurait l'air cassé.

## Fermer

Fermer une fenêtre qui contient des modifications non enregistrées demande d'abord quoi faire : **Save**, **Don't Save** ou **Cancel**.

Choisir Don't Save n'est pas définitif. Libera Suite conserve votre travail et vous le propose à la prochaine ouverture de ce document.

## Imprimer

**File ▸ Print**, ou le bouton de l'imprimante, produit un PDF du document et l'ouvre dans le lecteur de PDF de votre système, où se trouve la boîte de dialogue d'impression.

C'est le choix fait pour l'instant : le lecteur que vous avez déjà vous donne les plages de pages, le format du papier, la mise à l'échelle et un aperçu, que nous ne ferions pas mieux dans une première version.

## Images

Les images intégrées à un document sont conservées à l'ouverture et à l'enregistrement. **Insert ▸ Image** ajoute une image depuis le disque.

## Correction orthographique {#spell-checking}

Les fautes sont soulignées ; le clic droit propose des suggestions. Le dictionnaire utilisé dépend de **la langue du document**, que vous réglez dans la **barre d'état** en bas de la fenêtre, pour chaque document.

Des dictionnaires sont fournis pour cinq langues : l'anglais (américain et britannique), le français, l'allemand, l'espagnol et l'italien. Une langue sans dictionnaire n'est pas une erreur ; ses mots sont simplement considérés comme corrects. Les mots ajoutés par *Add to dictionary* réapparaissent soulignés à la session suivante, parce que les dictionnaires personnels ne sont pas encore conservés.

## Votre nom dans les documents {#your-name-in-documents}

Les modifications suivies et les commentaires sont attribués à une personne, dont le nom est écrit dans le fichier enregistré. Libera Suite le prend dans votre compte : votre nom complet tel que macOS le connaît, le nom affiché de votre compte Windows, ou le champ « nom complet » de votre compte Unix sous Linux, à défaut votre identifiant de connexion.

Il n'existe pas encore de réglage pour le changer. Si un document doit partir sous un autre nom, [dites-le-nous](../feedback.md).

## Où vont vos fichiers de travail

Tant qu'un document est ouvert, Libera Suite conserve un dossier de session à côté de ses données d'application. Il contient la copie de travail de l'éditeur et le journal de vos modifications : l'enregistrement est ainsi rapide et l'annulation fiable. Ce n'est pas une sauvegarde : le document est là où vous l'avez enregistré.

---

La page suivante est l'[État des lieux](../main/status.md) : les fonctions disponibles et les problèmes que nous connaissons déjà. Si vous en rencontrez un qui n'y figure pas, [écrivez-nous](../feedback.md).
