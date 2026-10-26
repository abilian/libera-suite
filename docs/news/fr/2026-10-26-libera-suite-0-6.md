---
date: 2026-10-26
description: Libera Suite 0.6 parle toutes les langues de ses applications, met en page comme Word quand une police manque, garde les titres Markdown et vérifie l'orthographe en néerlandais.
---

# Libera Suite 0.6 : toutes les langues, et des pages qui se coupent comme dans Word

Libera Suite 0.6 est disponible. Ses menus et ses fenêtres parlent désormais les 44 langues de ses applications, et un document dont vous n'avez pas les polices se met en page comme dans Word.

Libera Suite est une suite bureautique libre (open source) pour Windows, macOS et Linux : Libera Words pour le texte, Libera Tables pour les feuilles de calcul, Libera Slides pour les présentations, et Libera Diagrams, une visionneuse de dessins Visio. Elle ouvre et enregistre les formats de Microsoft Office et de LibreOffice, sur votre propre ordinateur, sans compte ni service en ligne.

[Installer Libera Suite](../main/install.md){ .md-button .md-button--primary }

Vous l'utilisez déjà ? Quittez Libera Suite si elle est ouverte, puis relancez l'installateur ou la commande d'installation, ou `brew upgrade libera` si vous passez par Homebrew. Cette version installe de nouveaux composants, téléchargés une seule fois (environ 90 Mo).

## Toutes les langues

Depuis la 0.5, les applications suivent la langue de votre système, mais la barre de menus, la fenêtre d'accueil et les boîtes de dialogue ne le faisaient qu'en français, en allemand, en italien et en espagnol. Elles suivent désormais dans les 44 langues, de l'arabe au vietnamien, et en arabe, en hébreu et en ourdou la fenêtre d'accueil se lit de droite à gauche.

Seules les traductions française, allemande, italienne et espagnole ont été relues par un locuteur natif. Les autres sont des ébauches : si un mot de votre langue est faux ou maladroit, [écrivez-nous](../feedback.md), et votre correction entrera dans la version suivante.

## Des pages qui se coupent comme dans Word

Quand un document demande une police absente de votre ordinateur, Libera Suite la remplace désormais comme Word :

- **Calibri, Cambria, Arial, Times New Roman et Courier New** reçoivent Carlito, Caladea et Liberation, qui ont les mêmes largeurs : les lignes et les pages se coupent aux mêmes endroits que dans Word. Sur Mac, Calibri allait à la police installée la plus ressemblante, si bien qu'un même document pouvait se mettre en page différemment d'un ordinateur à l'autre.
- **Une police que Word ne connaîtrait pas non plus** prend la remplaçante de Calibri, comme Word prend Calibri, là où elle recevait Liberation Sans. Deux documents de notre jeu d'essai ont maintenant le même nombre de pages que dans Word.
- **Les caractères Wingdings, Webdings et Symbol** s'affichent comme les symboles qu'ils représentent : une étoile, une coche, un sourire, là où une police Wingdings absente montrait des lettres.

## Autres changements

- **Sous macOS, Libera Suite figure parmi vos applications.** Le script d'installation place `Libera.app` dans votre dossier Applications, et `libera --launcher-install` fait de même après Homebrew : le Finder la propose dans *Ouvrir avec*, un double-clic sur un document peut l'y ouvrir, et le Dock affiche Libera, là où il affichait Python.
- **Le Markdown garde ses titres.** Un fichier Markdown ouvert, modifié et enregistré transformait chaque titre en paragraphe gras.
- **La vérification orthographique en néerlandais**, avec le dictionnaire OpenTaal. Chaque dictionnaire est désormais accompagné de sa licence.
- **Sous Linux, le menu Fichier affiche ses raccourcis :** Nouveau, Ouvrir et Fermer montrent Ctrl-N, Ctrl-O et Ctrl-W.
- **Un fichier OpenDocument sans styles de page maîtres garde ses styles**, là où chaque paragraphe s'ouvrait dans le style par défaut.

## Sans changement

- **Linux sur arm64** installe toujours la 0.4.1 : il n'existe pas encore de version arm64 de la 0.6.

La page [État des lieux](../main/status.md) indique l'état de chaque fonction : terminée, à moitié faite ou pas encore commencée.

## Vos retours

Libera Suite est un projet jeune, et chaque signalement compte. Le plus utile reste un document qui s'affiche mal, joint à votre message avec la sortie de `libera --diagnose`. La page [Vos retours](../feedback.md) explique comment nous écrire.

*Abilian*
