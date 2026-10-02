# État des lieux

Libera Suite est jeune. Cette page recense les fonctions disponibles, celles qui sont en chantier et celles qui ne sont pas encore commencées.

L'interface de Libera Suite est en anglais : les noms des menus et des boutons sont donc cités tels que vous les verrez à l'écran.

## Disponible

| | |
| :--- | :--- |
| **Quatre éditeurs** | Windows 10 et 11 sur x64, Linux sur x86_64 et arm64, macOS sur Apple Silicon. Words, Tables et Slides modifient les documents ; Diagrams lit les fichiers Visio. |
| **Ouvrir et enregistrer** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Save, Save As, New. |
| **Exporter** | Save As propose une liste de formats pour chaque éditeur, PDF compris. Chaque format proposé a été vérifié par une conversion réelle. |
| **Images** | Conservées à l'ouverture et à l'enregistrement ; Insert ▸ Image fonctionne. |
| **Imprimer** | Produit un PDF et l'ouvre dans votre lecteur de PDF. |
| **Correction orthographique** | Cinq langues, avec suggestions. Voir plus bas. |
| **Documents récents** | File ▸ Open Recent retient les 20 derniers. |
| **Plusieurs documents à la fois** | De tous types, une fenêtre chacun : par File ▸ New ou File ▸ Open, d'un double-clic dans le gestionnaire de fichiers, ou avec `libera *.docx`. Le type du fichier choisit l'éditeur. |
| **Dans le menu Démarrer et le menu des applications** | Sous Windows, l'installateur ajoute Libera Suite au menu Démarrer, sur le bureau et dans *Ouvrir avec* de l'Explorateur. Sous Linux, le Flatpak l'ajoute au menu des applications avec son icône et ses associations de fichiers ; `libera --launcher-install` fait de même pour toute autre installation. |
| **Une fenêtre de démarrage** | `libera` seul : nouveau document, ouvrir, documents récents et provenance des éditeurs. |
| **Récupération après plantage** | Les modifications non enregistrées vous sont proposées à la prochaine ouverture du document. |
| **La fermeture demande confirmation** | Une fenêtre qui contient des modifications non enregistrées propose Save, Don't Save ou Cancel. |
| **Une barre de menus** | File, Edit, View et Help sur toutes les plateformes. macOS y ajoute Window ainsi que les raccourcis habituels. |
| **À propos** | Qui a écrit les éditeurs et sous quelle licence : `File ▸ About` dans l'éditeur, `Help ▸ About Libera Suite` sous Linux et Windows. macOS le place dans le menu de l'application. |
| **Les réglages sont conservés** | Le thème, les unités, la langue de correction et les réglages de ce genre sont toujours là après un redémarrage. |
| **Installation des éditeurs** | Depuis le serveur, ou depuis un dossier local d'artefacts construits. Dans les deux cas, chaque artefact est vérifié par rapport aux empreintes livrées dans l'application. |

## Problèmes connus

**Inutile de signaler ceux-ci** : nous les connaissons. Les sections qui suivent les détaillent.

| | |
| :--- | :--- |
| **macOS parle d'un développeur non identifié** | Seulement pour un `Libera.app` que vous avez construit vous-même : il n'est pas signé avec un identifiant de développeur, si bien que Gatekeeper s'y oppose la première fois. [Autres façons d'installer](alt-install.md#a-double-clickable-application-on-macos) explique comment passer outre. Une installation par `pip`, `pipx` ou Homebrew n'y est jamais confrontée. |
| **Lancée depuis un terminal, le Dock affiche « Python »** | Seulement quand vous lancez `libera` depuis une installation `pipx` ou un environnement virtuel. Une icône du Dock prend le nom du paquet d'application depuis lequel le programme a été lancé : ici celui de l'interpréteur Python, que l'application ne peut pas changer. L'icône et la barre de menus sont les nôtres dans tous les cas ; `Libera.app` affiche bien Libera. |
| **Diagrams ne peut pas enregistrer** | Il ouvre un `.vsdx` et l'affiche. Le convertisseur ne sait écrire aucun format Visio : il n'y a donc rien à enregistrer, ni de modèle vierge pour commencer. |
| **Un CSV ou un `.txt` contenant un emoji ne peut pas être enregistré tel quel** | Sous macOS et Linux, le convertisseur abîme le texte brut contenant un caractère situé au-delà des 65 536 premiers d'Unicode, un emoji par exemple. Libera Suite refuse alors l'enregistrement et laisse le fichier intact. Save As en `.xlsx` ou en `.docx` conserve tout. Une correction du convertisseur est prévue pour la prochaine version des éditeurs. |
| **Dans un CSV de plus de 500 Ko environ, une ligne peut être mal lue** | Le convertisseur saute un caractère sur 500 000. Quand ce caractère est un guillemet, une virgule ou un saut de ligne, une cellule est coupée en deux, ou deux cellules ou deux lignes se retrouvent fusionnées. Libera Suite indique les lignes touchées à l'ouverture du fichier : vérifiez-les avant d'enregistrer, car l'enregistrement écrit le contenu affiché par la feuille. Une correction du convertisseur est prévue pour la prochaine version des éditeurs. |
| **Pas de modification des PDF** | Les PDF sont seulement produits. L'ouverture d'un PDF pour le modifier n'est pas branchée. |
| **Une barre de menus réduite, sans raccourcis sous Linux et Windows** | Linux et Windows ont File, Edit, View et Help, dessinés dans la fenêtre, sans raccourci clavier ; les raccourcis propres à l'éditeur, Ctrl-S, Ctrl-P et Ctrl-Z, fonctionnent toujours dans la page. macOS a les mêmes menus plus Window, avec les raccourcis habituels. |
| **Pas d'onglets** | Une fenêtre par document. |
| **Pas de verrouillage des fichiers** | Modifier le même document dans deux fenêtres fera perdre l'une des deux séries de modifications. |
| **Windows avertit au sujet de l'installateur** | L'installateur téléchargé n'est pas encore signé : la première fois, SmartScreen affiche *« Windows a protégé votre ordinateur »*. [Installer](install.md#windows) explique comment passer outre. L'installation par la ligne PowerShell n'y est jamais confrontée. |

Si vous rencontrez un problème qui ne figure *pas* dans cette liste, [signalez-le-nous](../feedback.md).

## En chantier

**La barre de menus sous Linux et Windows.** Elle est dessinée dans la fenêtre, avec File, Edit, View et Help ; chaque élément fonctionne. Aucun n'a de raccourci clavier propre ; les touches que vous utilisez déjà vont donc à l'éditeur, où Ctrl-S, Ctrl-P et Ctrl-Z fonctionnent. Ctrl-N ne fait rien sous Linux ; sous Windows, cela n'a pas été vérifié. File ▸ New ▸ Document, Spreadsheet ou Presentation fonctionne, tout comme les tuiles New de la fenêtre de démarrage et l'onglet File de l'éditeur.

**`Libera.app` sous macOS.** `build/macos-app.sh` le construit. Il ouvre un document d'un double-clic, apparaît dans *Ouvrir avec* et affiche la marque Libera dans le Dock. Mais c'est un lanceur autour de l'interpréteur avec lequel il a été construit (rien n'y est intégré, signé ni notarié) : ce n'est pas encore quelque chose que l'on peut donner à quelqu'un d'autre.

## Pas encore commencé

### Dans l'éditeur

- **Les documents protégés par mot de passe.** Ni leur ouverture ni leur enregistrement.
- **Les signatures numériques.**
- **Le publipostage.**
- **Les modules complémentaires.** Ils sont désactivés en amont dans ce fork : le panneau n'apparaît jamais.

### Dans l'application

- **Les onglets.** Les fenêtres existent et le menu Window les liste, mais elles ne peuvent pas être réunies dans une seule fenêtre.
- **Le verrouillage des fichiers.** Deux instances de Libera Suite qui modifient le même fichier ne s'en rendent pas compte.
- **Une application redistribuable sous macOS.** `Libera.app` fonctionne depuis votre propre copie du code et n'embarque ni interpréteur ni éditeurs. Windows en a une : son installateur apporte tout.
- **Le glisser-déposer** sur la fenêtre ou sur l'icône du Dock.
- **Les mises à jour automatiques** et **la signature du code**. macOS traite un `Libera.app` que vous avez construit comme un logiciel d'un développeur non identifié. Windows avertit au sujet de l'installateur téléchargé.
- **Une aide hors ligne**, lisible sans navigateur ni réseau. Le menu Help ouvre ce site ; About fonctionne hors ligne. Voir plus bas.

### Ailleurs

- **La modification des diagrammes.** Diagrams ouvre un `.vsdx` et l'affiche. Le convertisseur ne sait écrire aucun format Visio : il n'y a donc rien à enregistrer, ni de modèle vierge pour commencer.
- **La modification des PDF.** Les éditeurs en comportent un. Rien n'y mène encore.
- **La collaboration, le stockage en ligne, les comptes, la télémétrie.** Rien de tout cela n'est construit, ni en cours. [La feuille de route](/en/develop/roadmap/), en anglais, décrit à quoi chacun ressemblerait s'il arrivait. [Vos données restent chez vous](../index.md#what-leaves-your-machine) recense toute l'utilisation du réseau par l'application.

## Précisions sur certains manques

### Aide

Il existe un menu **Help**, sur toutes les plateformes, qui ouvre ce site dans votre navigateur. Aucune aide n'est intégrée *dans* l'application, où elle serait lisible avec la machine hors ligne. L'amont fournit un manuel complet. Libera Suite ne l'inclut pas : il documente ONLYOFFICE et pèse 84 Mo en huit langues. L'aide hors ligne reviendra quand notre propre documentation sera assez fournie pour être livrée.

### Correction orthographique

Libera Suite fournit des dictionnaires pour **l'anglais (américain et britannique), le français, l'allemand, l'espagnol et l'italien** : 9,5 Mo, retenus parce que l'ensemble complet en pèse 327. Ajouter une langue demande une ligne dans `build/dictionaries.txt` et une reconstruction des éditeurs.

Une langue sans dictionnaire n'est pas une erreur : ses mots sont simplement considérés comme corrects, comme dans l'application de bureau de l'amont. Les dictionnaires personnels (*Add to dictionary*) ne sont pas encore conservés : un mot ajouté réapparaît souligné à la session suivante.

La façon de régler la langue d'un document est expliquée dans [Travailler sur des documents](../guide/documents.md#spell-checking).

### Votre nom dans les documents

Les modifications suivies et les commentaires sont attribués à une personne, dont le nom est écrit dans le fichier enregistré. Libera Suite le prend dans votre compte : le nom complet sous lequel macOS vous connaît, le nom affiché de votre compte Windows, ou le champ « nom complet » de votre compte Unix sous Linux. Il n'est pas encore possible de le changer. [Travailler sur des documents](../guide/documents.md#your-name-in-documents) donne le détail.

### Polices

Libera Suite fournit un jeu de polices de base : Liberation, Carlito, Caladea, Open Sans et quelques autres, de quoi afficher fidèlement des documents ordinaires, pour 7 Mo. L'ensemble complet pèse 248 Mo. Un document qui demande une police absente de ce jeu comme des polices installées sur votre machine reçoit une police de substitution. L'élargissement de ce jeu, notamment aux écritures chinoise, japonaise et coréenne, reste à décider.

### Fidélité du rendu

Le moteur de mise en page vient de l'amont et il est éprouvé. Si vous voyez une erreur, la cause la plus probable est notre empaquetage (une police ou une ressource manquante). Ces signalements sont donc particulièrement utiles : envoyez-nous [vos retours](../feedback.md) avec le fichier.
