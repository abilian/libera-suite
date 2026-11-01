# Autres façons d'installer

[Installer](install.md) donne la façon habituelle pour chaque plateforme, qui convient à la plupart des gens. Cette page traite de tout le reste : choisir soi-même un canal, installer à la main, savoir où vont les fichiers.

## Les options du script d'installation

`install.sh` accepte des options. Lorsqu'il est lu depuis un tube, il lui faut `sh -s --` devant elles :

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh -s -- --prefix ~/apps
curl -fsSL https://cdn.abilian.com/libera/install.sh | bash -s -- --help
```

| | |
| :--- | :--- |
| `--prefix DIR` | installer ailleurs (par défaut : `~/.local`) |
| `--channel pip` | sous Linux, installer le paquet Python même quand Flatpak est présent |
| `--no-payload` | installer la commande maintenant, télécharger les composants plus tard |
| `--origin URL` | télécharger depuis un autre serveur que le serveur public |

Il n'écrit que dans `~/.local/bin` et `~/.local/share`. Ouvrez son adresse dans un navigateur pour le lire avant de le lancer.

## pipx ou uv

Libera Suite est publiée sur PyPI sous le nom `libera` ; elle demande Python 3.12 ou plus récent. Sous macOS et Windows :

```sh
uv tool install libera      # ou : pipx install libera
libera --payload-install
```

Pour l'essayer sans l'installer, `uvx libera` la lance depuis un cache ; le premier lancement propose de télécharger les composants.

Sous Linux, la fenêtre est dessinée par GTK, dont les liaisons Python viennent de votre distribution et sont compilées pour son propre Python. Un environnement isolé ne les voit pas, si bien que `pipx` a besoin de deux options :

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
libera --payload-install
```

Sans elles, Libera Suite s'installe proprement puis n'ouvre aucune fenêtre. `uv tool` n'a pas d'équivalent de `--system-site-packages` : sous Linux, utilisez `pipx`. Au premier lancement, `libera` indique les paquets GTK qui manquent à votre distribution ; il connaît apt, dnf, pacman et zypper.

## Le Flatpak, à la main

Quand Flatpak est présent, le script d'installation procède ainsi :

```sh
arch=amd64     # ou arm64, selon votre machine
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
# sous arm64 : ver=0.4.1, la dernière version compilée pour cette plateforme
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

`bundles/latest` contient le numéro de la version actuelle, si bien que ces lignes restent valables d'une version à l'autre. Le paquet, d'environ 70 Mo, contient les composants. Il s'exécute sur l'environnement GNOME, que `flatpak` télécharge depuis Flathub la première fois ; une machine qui n'a pas le dépôt Flathub doit d'abord l'ajouter :

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

## Les composants {#the-editors}

L'installateur Windows et le Flatpak incluent les composants. Tous les autres canaux les téléchargent une fois, après l'application. `libera` le propose à son premier lancement ; cette commande lance le téléchargement directement :

```sh
libera --payload-install
```

Elle télécharge environ 90 Mo depuis `cdn.abilian.com` et vérifie chaque fichier par rapport aux empreintes livrées dans l'application, en s'arrêtant au premier qui ne correspond pas. Elle construit ensuite, en quelques instants, l'index des polices de votre machine.

Pour installer des composants que vous avez construits vous-même, ou qu'on vous a fournis, indiquez-lui leur dossier :

```sh
libera --payload-install --from /chemin/vers/les/artefacts
```

[Build the components](/en/develop/build/), en anglais, explique comment les construire. `libera --payload-remove` les supprime ; ils occupent environ 350 Mo sur le disque.

## Où sont les fichiers

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/`, ou `~/.local/share/libera/` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |
| Windows | `%LOCALAPPDATA%\Libera Suite\` |

Les composants se trouvent là, dans `payload/<version>/`. Une mise à jour installe la nouvelle version à côté de l'ancienne, et Libera Suite supprime une ancienne version quand plus rien ne l'a utilisée depuis quatre semaines : Libera Suite installé autrement sur le même compte peut encore s'en servir. `libera --payload-status` les liste, avec la date de leur dernière utilisation. Pour utiliser des composants situés ailleurs, une construction locale par exemple, indiquez leur dossier dans `LIBERA_PAYLOAD` ; ce réglage l'emporte sur tous les emplacements ci-dessus.

## Une entrée dans le menu des applications sous Linux {#a-launcher-entry-on-linux}

Le script d'installation et le Flatpak ajoutent tous deux Libera Suite au menu des applications. Après toute autre installation, cette commande fait de même, pour votre compte seulement : une icône, *Ouvrir avec* et des documents qui s'ouvrent d'un double-clic.

```sh
libera --launcher-install
libera --launcher-remove     # pour la retirer
```

## Une application à double-cliquer sous macOS {#a-double-clickable-application-on-macos}

Il n'en existe pas encore de toute prête. Depuis une copie du code source, vous pouvez en construire une pour vous-même :

```sh
build/macos/macos-app.sh          # construit build/out/Libera.app
open build/out/Libera.app
```

Elle ouvre les documents d'un double-clic et affiche l'icône de Libera dans le Dock. Elle utilise le Python avec lequel elle a été construite et dépend donc de cette copie du code : laissez-la en place ; si la copie change d'emplacement, reconstruisez-la. Elle n'est pas signée : au premier lancement, macOS indique **« impossible d'ouvrir l'app car le développeur ne peut pas être vérifié »**. Sous macOS 15 et ultérieur, pour passer outre, allez dans *Réglages Système ▸ Confidentialité et sécurité ▸ Ouvrir quand même*.
