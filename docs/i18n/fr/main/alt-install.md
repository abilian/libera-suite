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
| `--origin URL` | télécharger depuis un autre serveur que le serveur public |

Il n'écrit que dans `~/.local/bin` et `~/.local/share`. Ouvrez son adresse dans un navigateur pour le lire avant de le lancer.

## pipx ou uv

Libera Suite est publiée sur PyPI sous le nom `libera` ; elle demande Python 3.12 ou plus récent. Ses [composants](#the-editors) l'accompagnent. Sous macOS et Windows :

```sh
uv tool install libera      # ou : pipx install libera
```

Pour l'essayer sans l'installer, `uvx libera` la lance depuis un cache.

Sous Linux, la fenêtre est dessinée par GTK, dont les liaisons Python viennent de votre distribution et sont compilées pour son propre Python. Un environnement isolé ne les voit pas, si bien que `pipx` a besoin de deux options :

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
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

À partir de la version 0.7.0, chaque paquet a sa signature à côté de lui : vous pouvez vérifier, avant de l'installer, qu'il s'agit bien du nôtre. Dans le même dossier, avec `ver` et `arch` définis comme ci-dessus :

```sh
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak.asc"
curl -fsSL https://keys.openpgp.org/vks/v1/by-fingerprint/E1B31B9935BEDA0C53D21A1DD35A9ACA9BE0C732 | gpg --import
gpg --verify "libera-$ver-$arch.flatpak.asc" "libera-$ver-$arch.flatpak"
```

GnuPG doit afficher `Bonne signature de « Libera Suite release signing <releases@liberasuite.eu> »` (`Good signature from` en anglais), et l'empreinte de la clé principale doit être `E1B3 1B99 35BE DA0C 53D2 1A1D D35A 9ACA 9BE0 C732`. Son avertissement sur une clé non certifiée signifie seulement que vous n'avez pas déclaré à GnuPG votre confiance en cette clé. Le script d'installation ne fait pas cette vérification.

## Les composants {#the-editors}

Tous les canaux installent les composants avec l'application. L'installateur Windows et le Flatpak les contiennent. Avec pip, pipx ou uv, ce sont deux paquets Python dont `libera` a besoin : `libera-core`, le moteur de documents, compilé pour chaque plateforme, et `libera-web`, les composants d'édition et les polices. Ils représentent ensemble environ 90 Mo à télécharger. Le premier lancement construit ensuite, en quelques instants, l'index des polices de votre machine.

PyPI propose `libera-core` pour Windows x64, Linux x86_64 et macOS sur Apple Silicon. Sur toute autre machine, pip le construit depuis les sources : la construction prend près d'une heure et demande les outils listés dans [Build the components](/en/develop/build/), en anglais.

Les versions antérieures à la 0.7 téléchargeaient leurs composants à part, dans les dossiers ci-dessous. `libera --payload-remove` supprime les fichiers qu'elles y ont laissés.

## Où sont les fichiers

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/`, ou `~/.local/share/libera/` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |
| Windows | `%LOCALAPPDATA%\Libera Suite\` |

Libera Suite y conserve les données dont elle a besoin d'une session à l'autre, comme la liste des documents récents et les sessions non enregistrées. Les composants ne s'y trouvent pas : ils sont installés avec l'application, et `libera --payload-status` indique leur emplacement. Pour utiliser des composants situés ailleurs, une construction locale par exemple, indiquez leur dossier dans `LIBERA_PAYLOAD` ; ce réglage l'emporte sur les composants installés.

## Une entrée dans le menu des applications sous Linux {#a-launcher-entry-on-linux}

Le script d'installation et le Flatpak ajoutent tous deux Libera Suite au menu des applications. Après toute autre installation, cette commande fait de même, pour votre compte seulement : une icône, *Ouvrir avec* et des documents qui s'ouvrent d'un double-clic.

```sh
libera --launcher-install
libera --launcher-remove     # pour la retirer
```

## Une application à double-cliquer sous macOS {#a-double-clickable-application-on-macos}

Le script d'installation en écrit une, `Libera.app`, dans le dossier Applications de votre dossier personnel. Après toute autre installation, comme Homebrew, `pipx` ou `uv tool`, cette commande en fait autant :

```sh
libera --launcher-install
libera --launcher-remove     # pour la retirer
```

Elle ouvre les documents d'un double-clic et affiche l'icône de Libera dans le Dock. C'est un petit lanceur pour le Python de l'installation qui l'a écrite : après la désinstallation de celle-ci, ou son passage à un autre Python, relancez `libera --launcher-install`.

Depuis une copie du code source, vous pouvez en construire une pour cette copie :

```sh
build/macos/macos-app.sh          # construit build/out/Libera.app
open build/out/Libera.app
```

Elle utilise le Python de cette copie du code et en dépend donc : laissez-la en place ; si la copie change d'emplacement, reconstruisez-la. Elle n'est pas signée : au premier lancement, macOS indique **« impossible d'ouvrir l'app car le développeur ne peut pas être vérifié »**. Sous macOS 15 et ultérieur, pour passer outre, allez dans *Réglages Système ▸ Confidentialité et sécurité ▸ Ouvrir quand même*.
