---
date: 2026-10-01
description: Libera Suite, une suite bureautique libre et gratuite pour Linux, Windows et macOS, passe en bêta publique. Elle ouvre et enregistre les formats de Microsoft Office et OpenDocument, sans compte ni service en ligne.
---

# Libera Suite passe en bêta publique

**Libera Suite** est une suite bureautique libre et gratuite pour Linux, Windows et macOS. Elle comprend un traitement de texte, un tableur, un logiciel de présentation et une visionneuse de fichiers Visio. Elle fonctionne sur votre ordinateur, sans compte, sans service en ligne et sans télémétrie. Elle sait ouvrir et enregistrer les formats de Microsoft Office et OpenDocument. Sa bêta publique commence aujourd'hui.

[Installer Libera Suite](../main/install.md){ .md-button .md-button--primary }

![Libera Words, avec un document ouvert : la barre d'outils de l'éditeur dans le violet de Libera Words, et une page mise en forme en dessous.](../assets/words.png)

## Quatre applications

| | | |
| :--- | :--- | :--- |
| **Libera Words** | Documents texte | `.docx` `.odt` `.rtf` `.txt` `.md` |
| **Libera Tables** | Feuilles de calcul | `.xlsx` `.ods` `.csv` |
| **Libera Slides** | Présentations | `.pptx` `.odp` |
| **Libera Diagrams** | Une visionneuse de dessins Visio | `.vsdx` |

Un fichier Word, Excel ou PowerPoint s'ouvre avec sa mise en page : polices, images, tableaux et suivi des modifications compris. L'enregistrement produit un fichier du même format, que Microsoft Office et LibreOffice ouvrent comme n'importe quel autre.

Les quatre applications partagent une fenêtre d'accueil avec les documents récents, la correction orthographique en cinq langues, l'export PDF, l'impression et la récupération du travail après un plantage.

## Libre et gratuite

Libera Suite ne demande ni licence ni abonnement. Vous pouvez l'installer sur autant d'ordinateurs que vous voulez et la garder aussi longtemps que vous voulez. Elle ne dépend d'aucun serveur à nous pour fonctionner.

C'est un logiciel libre : chacun peut en lire le code source, le modifier et le partager. L'application est sous licence Apache 2.0 et les composants d'Euro-Office sous GNU AGPL v3. La page [Licence et attribution](../licence.md) explique comment obtenir le code source exact de chaque version.

## Vos documents restent sur votre ordinateur

Libera Suite lit et écrit vos documents sur votre disque et ne les envoie nulle part. Elle ne nous transmet aucune information sur vous, sur vos documents ou sur votre usage.

Elle se connecte pour télécharger les composants d'Euro-Office à l'installation. [La documentation recense](../index.md#what-leaves-your-machine) chacune de ses connexions ; le code source permet de le vérifier.

## Comment l'installer

- **Linux** (x86_64 et arm64) : une commande dans le terminal, qui installe un paquet Flatpak quand Flatpak est présent.
- **macOS** (Apple Silicon) : une commande dans le terminal, avec Homebrew ou sans.
- **Windows** 10 et 11 (x64) : un installateur, sans droits d'administration.

La [page d'installation](../main/install.md) donne les commandes.

## Les limites de la bêta

Chaque document a sa propre fenêtre, sans onglets. Rien n'empêche encore deux fenêtres de modifier le même document : la dernière à enregistrer écrase le travail de l'autre. Diagrams lit les fichiers Visio sans pouvoir les enregistrer. L'installateur Windows n'est pas encore signé : Windows affiche un avertissement à son ouverture. La page [État des lieux](../main/status.md) donne la liste complète et reste à jour.

## Vos retours

Le moteur de mise en page est éprouvé : quand un document s'affiche mal dans Libera Suite, la cause se trouve le plus souvent dans notre empaquetage, une police ou une ressource manquante. Ces défauts se corrigent vite, à condition de les voir. Le retour le plus utile est donc un document qui s'affiche mal, joint à votre message.

Si vous choisissez les logiciels d'une organisation, dites-nous de quelles fonctions elle aurait besoin pour adopter Libera Suite.

La page [Vos retours](../feedback.md) explique comment nous écrire.

## Qui la développe

Libera Suite est développée par [Abilian](https://abilian.com), une entreprise française de logiciel libre. Elle est bâtie sur les composants d'[Euro-Office](https://github.com/Euro-Office), un fork d'[ONLYOFFICE](https://www.onlyoffice.com/), le logiciel d'Ascensio System SIA. Ces composants apportent le moteur de documents et la prise en charge des formats. Abilian a écrit l'application de bureau qui les héberge : les fenêtres, les menus, l'ouverture et l'enregistrement des fichiers, l'empaquetage.

Nous compilons les composants d'Euro-Office depuis ses sources, à des révisions fixées. Les correctifs que nous y appliquons sont [publiés et expliqués](/en/develop/patches/).

*Abilian*

---

Microsoft, Word, Excel, PowerPoint, Visio et Windows sont des marques du groupe Microsoft. LibreOffice est une marque de The Document Foundation. ONLYOFFICE est une marque d'Ascensio System SIA. Les autres noms cités sont des marques de leurs propriétaires respectifs. Libera Suite n'est ni affiliée à ces titulaires, ni approuvée par eux.
