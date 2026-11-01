---
date: 2026-10-20
description: Libera Suite 0.5 parle votre langue, affiche les documents dans les polices installées sur votre ordinateur, les ouvre plus vite et fait le ménage après ses propres mises à jour.
---

# Libera Suite 0.5 : dans votre langue, avec vos polices

Libera Suite 0.5 est disponible. Elle suit désormais la langue de votre système et affiche un document dans les polices installées sur votre ordinateur.

Libera Suite est une suite bureautique libre (open source) pour Windows, macOS et Linux : Libera Words pour le texte, Libera Tables pour les feuilles de calcul, Libera Slides pour les présentations, et Libera Diagrams, une visionneuse de dessins Visio. Elle ouvre et enregistre les formats de Microsoft Office et de LibreOffice, sur votre propre ordinateur, sans compte ni service en ligne.

[Installer Libera Suite](../main/install.md){ .md-button .md-button--primary }

Vous l'utilisez déjà ? Quittez Libera Suite si elle est ouverte, puis relancez l'installateur ou la commande d'installation, ou `brew upgrade libera` si vous passez par Homebrew. Cette version installe de nouveaux composants, téléchargés une seule fois (environ 90 Mo).

## Dans votre langue

Jusqu'ici, Libera Suite ne parlait qu'anglais. Ses quatre applications suivent désormais la langue de votre système, et la ligne `ui_language` du [fichier de configuration](../guide/documents.md#your-name-in-documents) en choisit une autre. En français, en allemand, en italien et en espagnol, la barre de menus, la fenêtre d'accueil et les boîtes de dialogue suivent aussi, et l'aide ouvre cette documentation dans la même langue.

Un nouveau document part d'une page vierge adaptée à votre langue et à votre région : papier A4 partout sauf aux États-Unis, là où il était jusqu'ici au format US Letter pour tout le monde, et vérification orthographique dans votre langue.

## Avec vos polices

Un document composé dans une police installée sur votre ordinateur s'affiche désormais dans cette police, à l'écran comme dans son PDF, au lieu d'une police de substitution. Libera Suite recense vos polices à l'installation de ses composants, puis à chaque police installée ou supprimée ; rien n'est copié. La ligne `installed_fonts = false` la limite aux polices fournies avec Libera Suite.

## Plus vite à l'écran

La fenêtre d'un document s'ouvre maintenant tout de suite, pendant la préparation du document. Sur notre Mac, un petit document texte s'affiche environ une seconde plus tôt. Un fichier illisible pour Libera Suite ouvre maintenant une fenêtre qui le signale, puis la referme.

## Les autres changements

- **Des composants à jour**, d'octobre, avec les corrections apportées en amont depuis la version précédente.
- **Une politique de sécurité plus stricte.** Les composants ne peuvent rien charger ni rien envoyer ailleurs que vers Libera Suite elle-même. Seule exception : une image liée par un document à son adresse web, téléchargée comme dans toute suite bureautique.
- **Les macros sont désactivées, mais conservées.** Les macros des composants sont écrites en JavaScript et n'exécutent pas le VBA des documents de Microsoft Office : elles sont donc désactivées. Les macros d'un document sont conservées : enregistrer un `.docm`, un `.xlsm` ou un `.pptm` laisse son VBA intact, et Libera Words ouvre et enregistre désormais les `.docm`.
- **Les anciens composants sont supprimés.** Chaque mise à jour laissait la version précédente sur le disque, environ 400 Mo à chaque fois. Une version inutilisée depuis quatre semaines est maintenant supprimée.
- **Des corrections.** Le menu des polices affiche chaque nom en entier. Un classeur `.xlsb` s'ouvre, au lieu de s'ouvrir comme une présentation vide. Sous macOS, quitter avec Cmd-Q ne laisse plus de documents verrouillés. Sous Windows, la liste Récents affiche le nom de chaque document et ne perd plus ses entrées.

## Les retraits

- **L'enregistrement au format `.xlsb`.** L'écriture d'un tel fichier plantait sous Linux. Enregistrez plutôt en `.xlsx` ; Excel ouvre les deux.
- **Linux sur arm64, pour l'instant.** La 0.5 n'existe pas pour arm64. Sur ces machines, le script d'installation installe la 0.4.1 ; une version ultérieure prendra de nouveau en charge arm64.

La page [État des lieux](../main/status.md) indique l'état de chaque fonction : terminée, à moitié faite ou pas encore commencée.

## Vos retours

Libera Suite est un projet jeune, et chaque signalement compte. Le plus utile reste un document qui s'affiche mal, joint à votre message avec la sortie de `libera --diagnose`. La page [Vos retours](../feedback.md) explique comment nous écrire.

*Abilian*
