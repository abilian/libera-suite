---
date: 2026-10-01
description: Libera Suite, une suite bureautique libre et gratuite pour Windows, macOS et Linux, est en bêta. Elle ouvre les fichiers Word, Excel et PowerPoint, ne demande aucun compte et garde vos documents sur votre propre ordinateur.
---

# Libera Suite : vos documents, sur votre propre machine

Nous ouvrons aujourd'hui la bêta de **Libera Suite**, une suite bureautique libre et gratuite pour Windows, macOS et Linux. Rédigez vos courriers et vos rapports, suivez vos chiffres dans un tableur, préparez une présentation, le tout sur votre propre ordinateur, avec vos propres fichiers. Pas de compte à créer, pas d'abonnement à payer.

[Installer Libera Suite](../main/install.md){ .md-button .md-button--primary }

![Libera Words, avec un document ouvert : la barre d'outils de l'éditeur dans le violet de Libera Words, et une page mise en forme en dessous.](../assets/words.png)

## Elle ouvre les fichiers qu'on vous envoie

Tout le monde envoie des `.docx`. Libera Suite les ouvre, comme les `.xlsx` et les `.pptx` qui les accompagnent, et les met en page telles que leurs auteurs les voyaient : polices, images, tableaux et suivi des modifications compris. À l'enregistrement, vous obtenez un fichier du même format, que vos collègues ouvrent dans Microsoft Office ou LibreOffice comme n'importe quel autre.

Le mérite en revient à un moteur de documents qui reçoit depuis vingt ans les fichiers des autres. Libera Suite fait tourner ce moteur sur votre ordinateur.

| | | |
| :--- | :--- | :--- |
| **Libera Words** | Documents texte | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | Feuilles de calcul | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | Présentations | `.pptx` `.odp` |
| **Libera Diagrams** | Une visionneuse de dessins Visio | `.vsdx` |

Vous trouvez aussi le reste d'une suite bureautique : une fenêtre d'accueil avec vos documents récents, la correction orthographique en cinq langues, l'export PDF, l'impression, et une récupération qui vous rend votre travail si l'ordinateur s'arrête en cours de route.

## Gratuite, et à vous pour de bon

Aucune licence à payer, aucune facture mensuelle. Installez-la sur autant d'ordinateurs que vous voulez, gardez-la aussi longtemps que vous voulez. Aucun serveur ne doit rester payé pour qu'elle continue de fonctionner, et personne ne peut l'éteindre à distance.

Libera Suite est un logiciel libre : chacun peut en lire le code source, le modifier et le partager. L'application est sous licence Apache 2.0 et les éditeurs sous GNU AGPL v3. La page [Licence et attribution](../licence.md) explique comment obtenir le code source exact de chaque version.

## Vos documents restent sur votre ordinateur

Libera Suite lit et écrit vos documents sur votre disque, avec un logiciel installé sur votre disque, et ne les envoie jamais nulle part. Il n'y a ni compte ni nuage derrière elle, ni télémétrie, ni statistiques d'usage, ni rapports de plantage : elle ne nous envoie rien sur vous, ni sur vos documents, ni sur votre usage.

Elle se connecte pour télécharger ses éditeurs à l'installation. [La documentation recense](../index.md#what-leaves-your-machine) chacune de ses connexions, et le code source est public : vous pouvez vérifier.

## Une bêta, aux lacunes affichées

Libera Suite fonctionne sous **Windows 10 et 11 (x64)**, **macOS (Apple Silicon)** et **Linux (x86_64 et arm64)**. Windows a son installateur, Linux un unique fichier Flatpak qui contient les éditeurs, et macOS une commande dans le terminal.

Les lacunes connues sont [publiées en entier](../main/status.md) et tenues à jour. Chaque document a sa propre fenêtre, faute d'onglets pour l'instant. Rien n'empêche deux fenêtres de modifier le même document, et l'une des deux perdra ses modifications. Diagrams lit les fichiers Visio sans pouvoir les enregistrer. Windows se méfie de l'installateur tant qu'il n'est pas signé.

## Dites-nous ce qui coince

Le plus utile que vous puissiez nous envoyer, c'est **un document qui s'affiche mal, en pièce jointe**. Le moteur est mûr : quand un fichier s'affiche mal, la cause se trouve bien plus probablement de notre côté, une police que nous n'avons pas livrée, une ressource que nous n'avons pas servie. Nous corrigeons vite ces défauts, dès que quelqu'un nous en montre un.

Si vous choisissez les logiciels d'une organisation, dites-nous **de quoi elle aurait besoin** pour changer. Aujourd'hui, la réponse est encore facile à orienter.

L'[installation](../main/install.md) prend une minute, et la page [Vos retours](../feedback.md) explique comment nous joindre.

## Qui la fait

Libera Suite est développée par [Abilian](https://abilian.com), une entreprise française qui fait du logiciel libre. Ses éditeurs viennent d'[Euro-Office](https://github.com/Euro-Office), lui-même un fork d'[ONLYOFFICE](https://www.onlyoffice.com/), développé par Ascensio System SIA. Le moteur de documents et la prise en charge des formats, la partie difficile d'une suite bureautique, sont les leurs, et nous n'en avons rien réécrit. Nous avons construit l'application de bureau autour : les fenêtres, les menus, l'ouverture et l'enregistrement, et l'empaquetage.

Le moteur reste celui de l'amont, construit depuis les sources à des révisions exactes, avec [une courte série de correctifs](/en/develop/patches/) de notre main. La partie que nous maintenons est petite, et une petite équipe peut s'y engager sur la durée.

*Abilian*

---

Microsoft, Word, Excel, PowerPoint, Visio et Windows sont des marques du groupe Microsoft. LibreOffice est une marque de The Document Foundation. ONLYOFFICE est une marque d'Ascensio System SIA. Les autres noms cités sont des marques de leurs propriétaires respectifs. Libera Suite n'est ni affiliée à ces titulaires, ni approuvée par eux.
