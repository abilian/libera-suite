# Licence et attribution

## Deux licences, pour deux composants

| | |
| :--- | :--- |
| **L'application hôte** : le paquet `libera`, tout le contenu de `src/libera/` | [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| **Les éditeurs** : Euro-Office avec notre série de correctifs | [AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html) |

Ils arrivent séparément et restent séparés. L'application hôte est un paquet de quelques centaines de kilo-octets de Python et de JavaScript sur PyPI ; les éditeurs sont un téléchargement d'environ 120 Mo, ou le contenu d'un paquet Flatpak. Rien des éditeurs n'est intégré au paquet Python.

Lancez `libera --payload-status` pour voir les éditeurs utilisés et les révisions de l'amont dont ils sont issus.

## À partir de quoi c'est construit

Libera Suite intègre des composants d'[**Euro-Office**](https://github.com/Euro-Office), un fork sous AGPL d'**ONLYOFFICE**, développé par Ascensio System SIA. Ces composants sont modifiés ; nos modifications forment la série de correctifs décrite plus bas. Les éditeurs, le moteur de documents et la prise en charge des formats sont les leurs ; l'application hôte, l'empaquetage et l'intégration au bureau sont les nôtres.

Nous leur en sommes reconnaissants. Le plus difficile dans une suite bureautique, ce sont vingt ans de lecture correcte des fichiers `.docx` des autres. Cette partie, nous en héritons.

## Code source correspondant

Les éditeurs sont sous AGPL, qui exige que vous puissiez obtenir le code source des programmes que vous exécutez, modifications comprises.

Chaque version de Libera Suite inscrit trois choses dans le manifeste de ses éditeurs :

- la révision exacte de chaque dépôt de l'amont dont elle est issue, désignée par son empreinte de commit ;
- le commit de Libera Suite elle-même ;
- les dépôts où l'on peut récupérer les deux.

Nos modifications de l'amont sont conservées sous forme d'une série de correctifs appliquée à ces révisions précises : la question « qu'a modifié Libera Suite ? » a donc une réponse courte et vérifiable. Voyez [The patch queue](/en/develop/patches/), en anglais.

Nous renvoyons à des dépôts publics ; nous ne distribuons pas d'archives.
