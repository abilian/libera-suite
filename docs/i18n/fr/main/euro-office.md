# Libera Suite et Euro-Office Desktop

**Le même moteur, une autre enveloppe.**

Libera Suite et Euro-Office Desktop Editors utilisent les mêmes composants. `sdkjs`, `web-apps` et le convertisseur `x2t` viennent des dépôts Euro-Office, aux révisions de leurs versions publiées. Un document s'affiche, s'importe et s'exporte donc de la même façon dans les deux, à nos correctifs près. Les deux diffèrent essentiellement par l'application qui entoure ces composants.

**Euro-Office Desktop Editors** reprend l'architecture d'ONLYOFFICE Desktop : un navigateur Chromium embarqué (CEF) et une interface Qt, en C++ (dépôts `desktop-sdk` et `desktop-apps`).

**Libera Suite** remplace cette couche par quelques milliers de lignes de Python et de JavaScript. Les composants s'affichent dans le moteur web déjà présent sur le système : WebKit sur macOS et Linux, WebView2 sur Windows. Ils ne voient pas la différence. Ils s'adressent à la même interface native (`AscDesktopEditor`), que nous avons réécrite.

Ce choix a plusieurs conséquences.

- **Taille.** Pour la version 9.3.5-2, le `.dmg` macOS d'Euro-Office pèse 926 Mo et l'installeur Windows autonome 616 Mo. Libera Suite télécharge environ 90 Mo de composants, plus une application de quelques mégaoctets.
- **Installation.** `pip` ou `pipx`, Homebrew (macOS et Linux), Flatpak, un installeur Windows, ou une ligne `curl | sh`.
- **Ligne de commande.** `libera --convert *.docx -t pdf` convertit des documents sans ouvrir de fenêtre.
- **Correctifs.** Nous compilons tout à partir des sources d'Euro-Office, avec une [série de correctifs publiée](/en/develop/patches/). Ils portent surtout sur le convertisseur, pour les fichiers OpenDocument et CSV. Les versions d'Euro-Office ne les contiennent pas aujourd'hui.
- **Licence.** L'application est sous Apache 2.0, et les composants restent sous AGPL.

Euro-Office Desktop a aujourd'hui quelques fonctions que Libera Suite n'a pas encore : les onglets, l'édition de PDF et les formulaires, les signatures numériques, et la connexion à un serveur Nextcloud, ownCloud ou Seafile pour la co-édition. [La feuille de route](/en/develop/roadmap/) dit quand elles arrivent.

**En résumé :** pour retrouver tout ONLYOFFICE Desktop dans un projet européen, Euro-Office Desktop est le bon choix. Libera Suite fait un autre pari : une application plus légère, faite d'un code court qu'une petite équipe peut lire et maintenir, qui ajoute des fonctions sans toucher au moteur d'édition.
