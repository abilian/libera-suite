# À propos

Libera Suite est développée par [Abilian](https://abilian.com), une entreprise française qui fait du logiciel libre. Stefane Fermigier dirige le projet.

Son code source est public, sur [github.com/abilian/libera-suite](https://github.com/abilian/libera-suite). L'application hôte, la partie que nous avons écrite, est sous licence Apache 2.0 ; les éditeurs sont sous GNU AGPL v3. [Licence et attribution](../licence.md) donne le détail, y compris la façon d'obtenir le code source exact de chaque version.

## Remerciements

Libera Suite repose sur le travail d'autres personnes. Quand vous modifiez un document, l'essentiel du travail vient d'eux.

### Les éditeurs

Libera Suite intègre des composants d'[**Euro-Office**](https://github.com/Euro-Office), lui-même un fork d'**ONLYOFFICE**, développé par Ascensio System SIA. Le moteur de documents, les quatre éditeurs, le convertisseur de formats et la prise en charge de chaque format viennent de là, modifiés par [une courte série de correctifs](/en/develop/patches/) de notre main. Le plus difficile dans une suite bureautique, ce sont vingt ans de lecture correcte des documents `.docx` des autres. Cette partie est la leur.

De la même organisation viennent les modèles vierges dont part chaque nouveau document, les dictionnaires de correction (anglais, français, allemand, espagnol et italien) et les polices fournies avec Libera Suite : Liberation, Carlito, Caladea, Open Sans et Asana Math, entre autres, chacune sous sa propre licence libre.

Sous les éditeurs se trouvent bien d'autres bibliothèques, dont V8 et Boost pour les plus grosses, fournies avec la construction d'Euro-Office.

### L'application

- [**Python**](https://www.python.org), dans lequel toute l'application hôte est écrite.
- [**pywebview**](https://pywebview.flowrl.com), qui place une vue web dans une fenêtre native sur chaque plateforme. Sous macOS, il passe par [**PyObjC**](https://pyobjc.readthedocs.io) ; sous Linux, par [**PyGObject**](https://pygobject.gnome.org) et WebKitGTK.
- Les moteurs web qui affichent les éditeurs : **WebKit** sous macOS et Linux ; **WebView2** de Microsoft sous Windows.
- Sous Linux, l'[**environnement GNOME**](https://flathub.org/apps/org.gnome.Platform) sur lequel tourne le Flatpak, ainsi que [**Flatpak**](https://flatpak.org) lui-même.
- Sous Windows, [**PyInstaller**](https://pyinstaller.org), qui empaquette l'application avec son propre Python ; [**Inno Setup**](https://jrsoftware.org/isinfo.php) construit l'installateur.

### Ce site

Construit avec [**Zensical**](https://zensical.org). Ses polices, [**Inter**](https://rsms.me/inter/) et [**JetBrains Mono**](https://www.jetbrains.com/lp/mono/), sont sous SIL Open Font License et servies par ce site lui-même.

## Contact

Pour un bogue, une question ou une suggestion, voyez [Vos retours](../feedback.md).
