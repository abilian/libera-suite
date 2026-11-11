---
date: 2026-11-10
description: Avec Libera Suite 0.7, vous pouvez annoter, remplir et réorganiser les PDF, garder les documents sous leur mot de passe, lire et créer des signatures numériques. Ses composants s'installent désormais avec elle.
---

# Libera Suite 0.7 : PDF, mots de passe et signatures

Libera Suite 0.7 est disponible. Vous pouvez désormais annoter, remplir et réorganiser les PDF, ouvrir et enregistrer les documents protégés par un mot de passe, lire et créer des signatures numériques.

Libera Suite est une suite bureautique libre (open source) pour Windows, macOS et Linux : Libera Words pour le texte, Libera Tables pour les feuilles de calcul, Libera Slides pour les présentations, Libera PDF pour les PDF, et Libera Diagrams, une visionneuse de dessins Visio. Elle ouvre et enregistre les formats de Microsoft Office et de LibreOffice, sur votre propre ordinateur, sans compte ni service en ligne.

[Installer Libera Suite](../main/install.md){ .md-button .md-button--primary }

Vous l'utilisez déjà ? Quittez Libera Suite si elle est ouverte, puis relancez l'installateur ou la commande d'installation, ou `brew upgrade libera` si vous passez par Homebrew. Avec pip, pipx ou Homebrew, les composants s'installent désormais avec l'application, environ 100 Mo, et rien n'est téléchargé au premier démarrage. La fenêtre d'accueil propose une fois de supprimer ce que les versions précédentes ont téléchargé, et `libera --payload-remove` le fait à tout moment.

## PDF

![Libera PDF avec un PDF ouvert, l'onglet Commentaire affichant ses outils, et un commentaire sur la page listé dans le panneau Commentaires.](../assets/pdf.png)

Un PDF s'ouvre dans Libera PDF. Vous pouvez y ajouter des commentaires, des surlignages, des dessins et des zones de texte, faire de petites corrections de texte, et ajouter, supprimer, pivoter et déplacer des pages. Vous pouvez aussi remplir des formulaires : un Cerfa français et les formulaires de l'IRS américain figurent parmi ceux que nous avons essayés.

L'enregistrement ajoute vos modifications après l'original, qui reste dans le fichier tel qu'il était. Une page supprimée ou un texte corrigé peut donc encore être retrouvé dans le fichier enregistré : ne comptez ni sur l'un ni sur l'autre pour retirer une information confidentielle d'un PDF que vous envoyez.

Un texte modifié ne se recompose pas. Un PDF certifié ne peut pas être enregistré, même si sa certification autorise les commentaires : l'enregistrement échoue, et le fichier reste tel qu'il était. Vous ne pouvez pas encore créer de formulaire ni convertir un PDF en document. Libera Suite est proposée dans *Ouvrir avec* pour un PDF, jamais par défaut. [Travailler avec les documents](../guide/documents.md#pdfs) donne le détail.

## Mots de passe

Un fichier Word, Excel, PowerPoint, OpenDocument ou PDF protégé par un mot de passe le demande à l'ouverture, et l'enregistrement le garde protégé. Fichier ▸ Protéger ajoute, modifie et supprime le mot de passe d'un document. Un enregistrement vers un format qui ne peut pas garder de mot de passe (texte, CSV, RTF, HTML, Markdown, EPUB) demande d'abord confirmation. Un document protégé qui a été altéré est refusé, grâce à un correctif d'ElixirOffice.

Par défaut, LibreOffice 26 chiffre les fichiers OpenDocument d'une façon que Libera Suite ne sait pas encore lire, et Libera Suite le dit au lieu de demander le mot de passe. Tant qu'un document protégé est ouvert, sa copie de travail sur votre disque n'est pas chiffrée, pour qu'un plantage ne vous fasse pas perdre vos modifications. [Travailler avec les documents](../guide/documents.md#passwords) donne le détail.

## Signatures numériques

Un document Word, Excel ou PowerPoint signé montre ses signatures à l'ouverture, chacune valide ou non, et s'ouvre en lecture seule. *Protection* ▸ *Signature* en signe un avec un fichier de clé (PKCS#12 ou PEM) et sa phrase secrète, et vous pouvez supprimer des signatures. Nous avons vérifié avec Microsoft Office et LibreOffice les signatures faites dans Libera Suite, et dans Libera Suite les signatures faites par ces deux logiciels.

*Valide* signifie que le document n'a pas changé depuis sa signature : l'émetteur du certificat et sa date d'expiration ne sont pas encore vérifiés. Signer un document protégé, un fichier OpenDocument ou un PDF n'est pas encore possible. [Travailler avec les documents](../guide/documents.md#signatures) donne le détail.

## Autres changements

- **Les documents Word 97-2003 s'ouvrent.** Aucun fichier `.doc` ne s'était jamais ouvert. Les archives web (`.mht`), FictionBook (`.fb2`) et les livres EPUB s'ouvrent aussi désormais.
- **Le convertisseur démarre environ deux fois plus vite**, et chaque ouverture et chaque enregistrement y gagnent un peu.
- **Déposer un fichier sur une fenêtre fonctionne sous Linux** : un document s'ouvre dans sa propre fenêtre, et une image entre dans le document. Le Flatpak peut aussi ouvrir désormais les fichiers des clés USB et des disques montés.
- **Un document ouvert par quelqu'un d'autre le signale désormais, quelle que soit la fenêtre où il s'ouvre.** Chaque fenêtre recevait l'état de la première.
- **Sous Windows, une fenêtre ne s'ouvre plus plus grande que l'écran.**

## Sécurité

Les versions précédentes ont tous ces problèmes : merci de mettre à jour.

- **Un document ne peut plus copier en lui-même des images de votre disque.** Une image liée à un chemin de votre disque était copiée dans chaque document enregistré ou converti à partir de lui, si bien que renvoyer le document renvoyait aussi l'image. Une image liée ne se lit plus désormais que depuis une adresse web.
- **Trois failles de cross-site scripting (XSS) sont corrigées.** Un document fabriqué pouvait exécuter un script dans l'éditeur quand vous sélectionniez une modification suivie, ouvriez l'Assistant Fonction ou cliquiez sur un lien `javascript:`. Les trois sont désormais affichés comme du texte ou refusés. La page de l'éditeur ne charge plus d'images que depuis Libera Suite, si bien qu'un script ne peut plus rien envoyer au dehors dans l'adresse d'une image.
- **Le convertisseur n'écrit plus de morceaux de sa propre mémoire dans les fichiers qu'il crée.**
- **Un petit document ne peut plus pousser le convertisseur à plusieurs gigaoctets de mémoire.**

## Téléchargements signés, et code source

Les paquets Flatpak sont signés avec notre clé OpenPGP, et [Autres façons d'installer](../main/alt-install.md) explique comment en vérifier un. L'installateur Windows et `Libera.app` ne sont pas encore signés. [Installer](../main/install.md) explique comment passer l'avertissement sur l'installateur ; la commande PowerShell en une ligne, pip, pipx et Homebrew n'en affichent aucun.

Le code source des wheels du convertisseur est le paquet source `libera-core` sur PyPI : les commits amont qu'il épingle, nos correctifs et les scripts de construction. Le code source de l'application est le tag `0.7.0` de [abilian/libera-suite](https://github.com/abilian/libera-suite).

## Sans changement

- **Linux sur arm64** installe toujours la 0.4.1 : il n'existe pas encore de version arm64 de la 0.7.

La page [État des lieux](../main/status.md) indique ce qui est terminé, ce qui est à moitié fait et ce qui n'est pas encore commencé, et [la feuille de route](/en/develop/roadmap/), en anglais, dit ce qui vient ensuite.

## Vos retours

Libera Suite est un projet jeune : chaque signalement compte. Le plus utile est un document qui s'affiche mal, joint à votre message avec la sortie de `libera --diagnose`. La page [Vos retours](../feedback.md) explique comment nous écrire.

*Abilian*
