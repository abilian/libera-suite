# Lizenz und Namensnennung

## Zwei Lizenzen für zwei Bestandteile

| | |
| :--- | :--- |
| **Die Host-Anwendung**: das Paket `libera`, alles in `src/libera/` | [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| **Die Komponenten**: Euro-Office mit unserer Patch-Reihe | [AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html) |

Sie sind getrennt paketiert und bleiben getrennt. Die Host-Anwendung besteht aus einigen hundert Kilobyte Python und JavaScript auf PyPI, als `libera`; die Komponenten sind dort zwei eigene Pakete, `libera-core` und `libera-web`, zusammen etwa 90 MB, oder der Inhalt eines Flatpak-Pakets. Nichts davon ist in das Wheel der Host-Anwendung eingebaut.

Führen Sie `libera --payload-status` aus, um die verwendeten Komponenten und die Upstream-Revisionen zu sehen, aus denen sie gebaut wurden.

## Woraus es gebaut ist

Libera Suite enthält Komponenten von [**Euro-Office**](https://github.com/Euro-Office), einem AGPL-Fork von **ONLYOFFICE**, das von Ascensio System SIA entwickelt wird. Diese Komponenten sind verändert; unsere Änderungen bilden die unten beschriebene Patch-Reihe. Die Bearbeitungskomponenten, die Dokument-Engine und die Unterstützung der Formate sind ihre; die Host-Anwendung, die Paketierung und die Einbindung in den Desktop sind unsere.

Wir sind beiden dankbar. Das Schwierigste an einer Office-Suite sind die zwanzig Jahre, in denen man lernt, die `.docx`-Dateien anderer richtig zu lesen. Diesen Teil erben wir.

## Zugehöriger Quellcode {#corresponding-source}

Die Komponenten stehen unter der AGPL. Diese verlangt, dass Sie den Quellcode dessen erhalten können, was Sie ausführen, einschließlich unserer Änderungen daran.

Jede Version von Libera Suite schreibt drei Dinge in das Manifest ihrer Komponenten:

- die genaue Upstream-Revision jedes Repositorys, aus dem sie gebaut wurde, festgelegt über den Commit-Hash;
- den Commit von Libera Suite selbst;
- die Repositorys, aus denen sich beides abrufen lässt.

Unsere Änderungen am Upstream-Projekt werden als Patch-Reihe auf diesen festgelegten Revisionen geführt. Die Frage „Was hat Libera Suite verändert?“ hat also eine kurze, überprüfbare Antwort. Siehe [The patch queue](/en/develop/patches/), auf Englisch.

Wir verweisen auf öffentliche Repositorys; Archive stellen wir nicht bereit.
