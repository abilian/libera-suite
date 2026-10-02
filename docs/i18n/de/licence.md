# Lizenz und Namensnennung

## Zwei Lizenzen für zwei Bestandteile

| | |
| :--- | :--- |
| **Die Host-Anwendung**: das Paket `libera`, alles in `src/libera/` | [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| **Die Editoren**: Euro-Office mit unserer Patch-Reihe | [AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html) |

Sie kommen getrennt an und bleiben getrennt. Die Host-Anwendung besteht aus einigen hundert Kilobyte Python und JavaScript auf PyPI; die Editoren sind ein Download von etwa 120 MB oder der Inhalt eines Flatpak-Pakets. Nichts von den Editoren ist in das Python-Paket eingebaut.

Führen Sie `libera --payload-status` aus, um die verwendeten Editoren und die Upstream-Revisionen zu sehen, aus denen sie gebaut wurden.

## Woraus es gebaut ist

Libera Suite enthält Komponenten von [**Euro-Office**](https://github.com/Euro-Office), einem AGPL-Fork von **ONLYOFFICE**, das von Ascensio System SIA entwickelt wird. Diese Komponenten sind verändert; unsere Änderungen bilden die unten beschriebene Patch-Reihe. Die Editoren, die Dokument-Engine und die Unterstützung der Formate sind ihre; die Host-Anwendung, die Paketierung und die Einbindung in den Desktop sind unsere.

Wir sind beiden dankbar. Das Schwierigste an einer Office-Suite sind die zwanzig Jahre, in denen man lernt, die `.docx`-Dateien anderer richtig zu lesen. Diesen Teil erben wir.

## Zugehöriger Quellcode

Die Editoren stehen unter der AGPL. Sie verlangt, dass Sie den Quellcode dessen erhalten können, was Sie ausführen, einschließlich unserer Änderungen daran.

Jede Version von Libera Suite schreibt drei Dinge in das Manifest ihrer Editoren:

- die genaue Upstream-Revision jedes Repositorys, aus dem sie gebaut wurde, festgelegt über den Commit-Hash;
- den Commit von Libera Suite selbst;
- die Repositorys, aus denen sich beides abrufen lässt.

Unsere Änderungen am Upstream-Projekt werden als Patch-Reihe auf diesen festgelegten Revisionen geführt. Die Frage „Was hat Libera Suite verändert?“ hat also eine kurze, überprüfbare Antwort. Siehe [The patch queue](/en/develop/patches/), auf Englisch.

Wir verweisen auf öffentliche Repositorys; Archive stellen wir nicht bereit.
