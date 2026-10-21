# État des lieux

Libera Suite est jeune. Cette page recense les fonctions disponibles, celles qui sont en chantier et celles qui ne sont pas encore commencées.

L'interface de Libera Suite est en anglais : les noms des menus et des boutons sont donc cités tels que vous les verrez à l'écran.

## Disponible

| | |
| :--- | :--- |
| **Quatre applications** | Windows 10 et 11 sur x64, Linux sur x86_64 (arm64 en 0.4.1), macOS sur Apple Silicon. Words, Tables et Slides modifient les documents ; Diagrams lit les fichiers Visio. |
| **Ouvrir et enregistrer** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Save, Save As, New. |
| **Exporter** | Save As propose une liste de formats pour chaque application, PDF compris. Chaque format proposé est vérifié par une conversion réelle, dont le texte est relu. |
| **Images** | Conservées à l'ouverture et à l'enregistrement ; Insertion ▸ Image fonctionne. |
| **Imprimer** | Produit un PDF, demande où le conserver et l'ouvre dans votre lecteur de PDF. |
| **Correction orthographique** | Cinq langues, avec suggestions. Voir plus bas. |
| **Dans votre langue** | Les applications suivent la langue de votre système, et un nouveau document part du modèle vierge de votre région : papier A4 partout sauf aux États-Unis, et correction orthographique dans votre langue. En français, en allemand, en italien et en espagnol, la barre de menus, la fenêtre d'accueil et les boîtes de dialogue suivent aussi ; dans toute autre langue, elles restent en anglais. |
| **Documents récents** | Fichier ▸ Ouvrir un fichier récent retient les 20 derniers. |
| **Plusieurs documents à la fois** | De tous types, une fenêtre chacun, ou sous macOS un onglet chacun quand le système préfère les onglets : par Fichier ▸ Nouveau ou Fichier ▸ Ouvrir, d'un double-clic dans le gestionnaire de fichiers, ou avec `libera *.docx`. Le type du fichier choisit l'application. |
| **Dans le menu Démarrer et le menu des applications** | Sous Windows, l'installateur ajoute Libera Suite au menu Démarrer, sur le bureau et dans *Ouvrir avec* de l'Explorateur. Sous Linux, le Flatpak l'ajoute au menu des applications avec son icône et ses associations de fichiers ; `libera --launcher-install` fait de même pour toute autre installation. |
| **Une fenêtre de démarrage** | `libera` seul : nouveau document, ouvrir, documents récents et provenance des composants. |
| **Récupération après plantage** | Les modifications non enregistrées vous sont proposées à la prochaine ouverture du document. |
| **Un document ouvert ailleurs** | Ouvert alors que LibreOffice ou une autre instance de Libera Suite l'a déjà, il est marqué *verrouillé pour la modification* : vous pouvez le lire et le modifier, et l'enregistrement demande où, si bien que le fichier de l'autre instance n'est jamais écrasé. Ouvrir un document déjà affiché dans une fenêtre fait passer cette fenêtre au premier plan. Microsoft Office et Libera Suite ne voient pas les verrous l'un de l'autre : un document ouvert dans Word n'est pas protégé. |
| **La fermeture demande confirmation** | Une fenêtre qui contient des modifications non enregistrées propose Enregistrer, Ne pas enregistrer ou Annuler. |
| **Une barre de menus** | File, Edit, View et Help sur toutes les plateformes. macOS y ajoute Window ainsi que les raccourcis habituels. |
| **À propos** | Qui a écrit les composants et sous quelle licence : `Fichier ▸ À propos` dans la fenêtre du document, `Aide ▸ À propos de Libera Suite` sous Linux et Windows. macOS le place dans le menu de l'application. |
| **Les réglages sont conservés** | Le thème, les unités, la langue de correction et les réglages de ce genre sont toujours là après un redémarrage. |
| **Installation des composants** | Depuis le serveur, ou depuis un dossier local d'artefacts construits. Dans les deux cas, chaque artefact est vérifié par rapport aux empreintes livrées dans l'application. |

## Problèmes connus

**Inutile de signaler ceux-ci** : nous les connaissons. Les sections qui suivent les détaillent.

| | |
| :--- | :--- |
| **macOS parle d'un développeur non identifié** | Seulement pour un `Libera.app` que vous avez construit vous-même : il n'est pas signé avec un identifiant de développeur, si bien que Gatekeeper s'y oppose la première fois. [Autres façons d'installer](alt-install.md#a-double-clickable-application-on-macos) explique comment passer outre. Une installation par `pip`, `pipx` ou Homebrew n'y est jamais confrontée. |
| **Lancée depuis un terminal, le Dock affiche « Python »** | Seulement quand vous lancez `libera` depuis une installation `pipx` ou un environnement virtuel. Une icône du Dock prend le nom du paquet d'application depuis lequel le programme a été lancé : ici celui de l'interpréteur Python, que l'application ne peut pas changer. L'icône et la barre de menus sont les nôtres dans tous les cas ; `Libera.app` affiche bien Libera. Un document déposé sur cette icône Python est refusé au nom de Python ; celle de `Libera.app` l'accepte. |
| **Diagrams ne peut pas enregistrer** | Il ouvre un `.vsdx` et l'affiche. Le convertisseur ne sait écrire aucun format Visio : il n'y a donc rien à enregistrer, ni de modèle vierge pour commencer. |
| **Pas de modification des PDF** | Les PDF sont seulement produits. L'ouverture d'un PDF pour le modifier n'est pas branchée. |
| **Une barre de menus réduite, sans raccourcis affichés sous Linux et Windows** | Linux et Windows ont File, Edit, View et Help, dessinés dans la fenêtre, sans raccourci clavier affiché. Les touches fonctionnent pourtant : Ctrl-N, Ctrl-O, Ctrl-W, Ctrl-S, Ctrl-Maj-S, Ctrl-P et Ctrl-Z. macOS a les mêmes menus plus Window, avec les raccourcis habituels. |
| **Pas d'onglets sous Linux ni Windows** | Une fenêtre par document. macOS a les onglets. |
| **Windows avertit au sujet de l'installateur** | L'installateur téléchargé n'est pas encore signé : la première fois, SmartScreen affiche *« Windows a protégé votre ordinateur »*. [Installer](install.md#windows) explique comment passer outre. L'installation par la ligne PowerShell n'y est jamais confrontée. |

Si vous rencontrez un problème qui ne figure *pas* dans cette liste, [signalez-le-nous](../feedback.md).

## En chantier

**La barre de menus sous Linux et Windows.** Elle est dessinée dans la fenêtre, avec Fichier, Édition, Affichage et Aide ; chaque élément fonctionne. Aucun n'affiche de raccourci clavier, mais les touches habituelles fonctionnent : Ctrl-N crée un nouveau document du même type, Ctrl-O en ouvre un, Ctrl-W ferme la fenêtre (en demandant d'abord quoi faire des modifications non enregistrées), et les raccourcis propres aux composants, Ctrl-S, Ctrl-Maj-S (Enregistrer sous), Ctrl-P et Ctrl-Z, fonctionnent aussi. Sous Windows, Ctrl-N, Ctrl-O et Ctrl-W n'ont pas encore été vérifiés sur une vraie machine. Fichier ▸ Nouveau ▸ Document, Feuille de calcul ou Présentation fonctionne, tout comme les tuiles Nouveau de la fenêtre de démarrage et l'onglet Fichier du document.

**`Libera.app` sous macOS.** `build/macos/macos-app.sh` le construit. Il ouvre un document d'un double-clic ou déposé sur son icône du Dock, apparaît dans *Ouvrir avec* et affiche la marque Libera dans le Dock. Mais c'est un lanceur autour de l'interpréteur avec lequel il a été construit (rien n'y est intégré, signé ni notarié) : ce n'est pas encore quelque chose que l'on peut donner à quelqu'un d'autre.

## Pas encore commencé

### Dans la fenêtre du document

- **Les documents protégés par mot de passe.** Ni leur ouverture ni leur enregistrement.
- **Les signatures numériques.**
- **Le publipostage.**
- **Les modules complémentaires.** Ils sont désactivés en amont dans ce fork : le panneau n'apparaît jamais.
- **Les macros.** Désactivées. Les macros des composants sont écrites en JavaScript et n'exécutent pas le VBA des documents de Microsoft Office : les macros d'un document ne sont donc pas exécutées. Elles sont conservées : l'enregistrement d'un `.docm`, d'un `.xlsm` ou d'un `.pptm` laisse son VBA intact. [La feuille de route](/en/develop/roadmap/), en anglais, décrit la suite.

### Dans l'application

- **Les onglets sous Linux et Windows.** Une fenêtre par document, que la barre des tâches regroupe.
- **Une application redistribuable sous macOS.** `Libera.app` fonctionne depuis votre propre copie du code et n'embarque ni interpréteur ni composants. Windows en a une : son installateur apporte tout.
- **Les mises à jour automatiques** et **la signature du code**. macOS traite un `Libera.app` que vous avez construit comme un logiciel d'un développeur non identifié. Windows avertit au sujet de l'installateur téléchargé.
- **Une aide hors ligne**, lisible sans navigateur ni réseau. Le menu Help ouvre ce site ; About fonctionne hors ligne. Voir plus bas.

### Ailleurs

- **La modification des diagrammes.** Diagrams ouvre un `.vsdx` et l'affiche. Le convertisseur ne sait écrire aucun format Visio : il n'y a donc rien à enregistrer, ni de modèle vierge pour commencer.
- **La modification des PDF.** L'amont a un éditeur de PDF ; les composants installés par Libera Suite ne le contiennent pas encore, puisque rien ne l'ouvrirait.
- **La collaboration, le stockage en ligne, les comptes, la télémétrie.** Rien de tout cela n'est construit, ni en cours. [La feuille de route](/en/develop/roadmap/), en anglais, décrit à quoi chacun ressemblerait s'il arrivait. [Vos données restent chez vous](../index.md#what-leaves-your-machine) recense toute l'utilisation du réseau par l'application.

## Précisions sur certains manques

### Aide

Il existe un menu **Aide**, sur toutes les plateformes, qui ouvre ce site dans votre navigateur. Aucune aide n'est intégrée *dans* l'application, où elle serait lisible avec la machine hors ligne. L'amont fournit un manuel complet. Libera Suite ne l'inclut pas : il documente ONLYOFFICE et pèse 84 Mo en huit langues. L'aide hors ligne reviendra quand notre propre documentation sera assez fournie pour être livrée.

### Correction orthographique

Libera Suite fournit des dictionnaires pour **l'anglais (américain et britannique), le français, l'allemand, l'espagnol et l'italien** : 9,5 Mo, retenus parce que l'ensemble complet en pèse 327. Ajouter une langue demande une ligne dans `build/payload/dictionaries.txt` et une reconstruction des composants.

Une langue sans dictionnaire n'est pas une erreur : ses mots sont simplement considérés comme corrects, comme dans l'application de bureau de l'amont. Les mots ajoutés par *Add to dictionary* sont conservés, pour tous les documents et toutes les langues.

La façon de régler la langue d'un document est expliquée dans [Travailler sur des documents](../guide/documents.md#spell-checking).

### Votre nom dans les documents

Les modifications suivies et les commentaires sont attribués à une personne, dont le nom est écrit dans le fichier enregistré. Libera Suite le prend dans votre compte : le nom complet sous lequel macOS vous connaît, le nom affiché de votre compte Windows, ou le champ « nom complet » de votre compte Unix sous Linux. Un autre nom se règle dans le fichier de configuration ; aucun menu ne le permet encore. [Travailler sur des documents](../guide/documents.md#your-name-in-documents) donne le détail.

### Polices

Libera Suite fournit un jeu de polices de base : Liberation, Carlito, Caladea, Open Sans et quelques autres, de quoi afficher fidèlement des documents ordinaires, pour 7 Mo. L'ensemble complet pèse 248 Mo. Un document qui demande une police absente de ce jeu utilise celle installée sur votre machine, à l'écran comme dans son PDF, et ne reçoit une police de substitution que si votre machine ne l'a pas non plus. Libera Suite dresse la liste de vos polices au premier démarrage, puis de nouveau en arrière-plan chaque fois que vous en installez ou en retirez une ; les fenêtres ouvertes ensuite utilisent la nouvelle liste. L'élargissement de ce jeu, notamment aux écritures chinoise, japonaise et coréenne, reste à décider.

### Fidélité du rendu

Le moteur de mise en page vient de l'amont et il est éprouvé. Si vous voyez une erreur, la cause la plus probable est notre empaquetage (une police ou une ressource manquante). Ces signalements sont donc particulièrement utiles : envoyez-nous [vos retours](../feedback.md) avec le fichier.
