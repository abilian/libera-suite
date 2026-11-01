# Libera Suite

**Libera Suite** est une suite bureautique libre (open source) et gratuite pour Windows, macOS et Linux, développée par Abilian. Rédigez des documents, travaillez sur des feuilles de calcul et préparez des présentations sur votre propre ordinateur, avec vos propres fichiers, sans compte ni service en ligne.

Elle ouvre et enregistre les formats de fichiers de Microsoft Office et de LibreOffice : vous échangez des documents avec n'importe qui, quel que soit son logiciel. C'est une alternative gratuite à Microsoft Word, Excel et PowerPoint, et un logiciel libre : chacun peut en lire le code source, le modifier et le partager.

- **Libera Words**, pour le texte : `.docx`, `.odt`, `.rtf`, `.txt`, `.md`, entre autres
- **Libera Tables**, pour les feuilles de calcul : `.xlsx`, `.ods`, `.csv`
- **Libera Slides**, pour les présentations : `.pptx`, `.odp`
- **Libera Diagrams**, une visionneuse de dessins Visio (`.vsdx`)

![Libera Words, avec un document ouvert : la barre d'outils dans le violet de Libera Words, et une page mise en forme en dessous.](assets/words.png)

[Installer Libera Suite](main/install.md){ .md-button .md-button--primary }

## En six diapositives

<div class="deck" data-pdf="/en/pdf/Libera%20Suite.pdf"><a href="/en/pdf/Libera%20Suite.pdf">Libera Suite, en six diapositives (PDF)</a></div>

## Où en est le projet

Les quatre fonctionnent dès aujourd'hui, sous **Windows** 10 et 11 (x64), **Linux** (x86_64, et arm64 avec la version 0.4.1) et **macOS** (Apple Silicon). Le projet est jeune. La page [État des lieux](main/status.md) détaille les fonctions terminées, celles qui sont en chantier et celles qui restent à entreprendre.

Pour l'essayer, commencez par [Installer](main/install.md) : une commande suffit sous Linux et macOS ; Windows a son installateur. Pour le construire, commencez par la [présentation pour les développeurs](/en/develop/), en anglais. Dans tous les cas, [dites-nous comment cela s'est passé](feedback.md).

## Pourquoi

L'essentiel du travail d'une suite bureautique tient dans le moteur de documents, la partie qui lit un `.docx` écrit par le logiciel de quelqu'un d'autre et le met en page comme son auteur l'entendait. Ce moteur existe déjà en logiciel libre et fonctionne déjà hors ligne : les composants d'édition de Libera Suite sont ceux d'[Euro-Office](https://github.com/Euro-Office), un fork sous AGPL d'ONLYOFFICE, développé par Ascensio System SIA, exécutés en local avec le même moteur de documents et la même prise en charge des formats. Il manquait à ce moteur une application hôte pour le bureau, assez petite pour qu'une seule équipe puisse s'en charger.

Libera Suite est cette application hôte : quelques milliers de lignes de Python et de JavaScript. Tout le reste vient de l'amont.

## Vos données restent chez vous {#what-leaves-your-machine}

Rien que vous n'ayez envoyé. Libera Suite n'envoie vos documents nulle part d'elle-même : ils vont là où vous les envoyez.

Libera Suite ne comporte **aucune télémétrie**, ni statistiques d'usage, ni rapports de plantage, ni comptes : elle ne nous envoie rien sur vous, ni sur vos documents, ni sur votre usage. Si une fonction de ce genre était ajoutée un jour, elle resterait désactivée tant que vous ne l'activez pas.

Elle se connecte en revanche à notre serveur pour des téléchargements. Aujourd'hui, il s'agit des composants, à l'installation de Libera Suite puis quand une nouvelle version en demande de nouveaux. Une fois par jour au plus, elle vérifie aussi si une version plus récente est sortie, et vous le dit une fois ; elle ne télécharge rien, et vous indique comment mettre à jour. Comme toute requête web, chacun de ces téléchargements montre votre adresse IP à notre serveur, et rien d'autre sur vous.

Le tableau recense chaque connexion établie aujourd'hui par l'application, pour que vous puissiez le vérifier. Toute nouvelle connexion, recherche de mises à jour comprise, y figurera dès la version qui l'introduit.

| | |
| :--- | :--- |
| **Les composants** | Téléchargés depuis `cdn.abilian.com` à l'installation de Libera Suite, puis seulement quand une nouvelle version en demande de nouveaux. Chaque téléchargement est vérifié par rapport aux empreintes livrées dans l'application. |
| **La recherche de mises à jour** | Une fois par jour au plus, le numéro de la dernière version, lu sur `cdn.abilian.com`. Une version plus récente est signalée une fois ; rien n'est téléchargé. Hors ligne, rien ne se passe. `check_updates = false` dans le [fichier de configuration](guide/documents.md#your-name-in-documents) la désactive. |
| **Le trafic propre des composants** | Un serveur web sur `127.0.0.1`, qui fait partie de l'application et sert les composants à une fenêtre de la même machine. Un autre ordinateur ne peut pas le joindre. Il ne répond à un programme de votre machine que si celui-ci présente une clé que seul votre compte peut lire. Leur page n'a le droit de joindre rien d'autre, hormis les images liées par un document. |
| **Les images liées par un document** | Un document peut afficher une image par son adresse web au lieu de la contenir. Libera Suite la télécharge alors depuis cette adresse à l'ouverture ou à la conversion du document, comme toute suite bureautique, et ce serveur voit votre adresse IP. Le document lui-même n'est pas envoyé. |
| **Les liens sur lesquels vous cliquez** | L'aide et les liens de ce type s'ouvrent dans *votre* navigateur. Libera Suite ne les télécharge pas. |

Vos documents sont lus et écrits sur votre disque, par un convertisseur installé sur votre disque. Ils ne sont jamais envoyés, indexés ni examinés.

## Licence et code source

Libera Suite est un logiciel libre : l'application hôte est sous licence [Apache-2.0](licence.md) ; les composants qu'elle exécute sont sous AGPL v3, comme le code d'Euro-Office à partir duquel ils sont construits. Chaque version enregistre les révisions exactes de l'amont dont elle est issue et les correctifs qui leur ont été appliqués : le code source correspondant est donc toujours un commit plus une série de correctifs dont on peut vérifier qu'elle s'y applique.

---

Microsoft, Word, Excel, PowerPoint, Visio et Windows sont des marques du groupe Microsoft. LibreOffice est une marque de The Document Foundation. ONLYOFFICE est une marque d'Ascensio System SIA. Les autres noms cités sont des marques de leurs propriétaires respectifs. Libera Suite n'est ni affiliée à ces titulaires, ni approuvée par eux.
