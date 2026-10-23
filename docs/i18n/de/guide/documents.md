# Mit Dokumenten arbeiten

Die Oberfläche von Libera Suite ist englisch: Menüs und Schaltflächen werden hier so genannt, wie sie auf dem Bildschirm erscheinen.

## Öffnen {#open}

```sh
libera                             # das Startfenster
libera ~/Documents/notiz.docx
libera ~/Documents/budget.xlsx
libera ~/Documents/netzwerk.vsdx
```

**Das Dokument bestimmt, welche Anwendung Sie bekommen.** Es gibt keinen Befehl, eine auszuwählen, so wie man auch keinen Texteditor für eine `.txt`-Datei auswählt: Sie öffnen das Dokument, und die richtige Anwendung erscheint. Eine `.xlsx`-Datei öffnet sich in Tables, eine `.pptx`-Datei in Slides, eine `.vsdx`-Datei in Diagrams.

![Das Startfenster mit je einer Kachel New für Document, Spreadsheet und Presentation, einer Schaltfläche Open und einer Liste Recent mit drei Dokumenten.](../assets/start.png)

Ohne Argument öffnet `libera` das **Startfenster**: ein neues Dokument jeder Art, einen Öffnen-Dialog, Ihre zuletzt verwendeten Dokumente und die Herkunft der Komponenten. Wählen Sie etwas aus, und das Startfenster verschwindet; das Dokument bleibt.

Libera Suite öffnet **ein Dokument pro Fenster**, daher tut ein Platzhalter der Shell, wonach er aussieht:

```sh
libera ~/Documents/*.docx     # jedes in seinem Fenster
```

Sie können ein Dokument auch aus dem Dokumentfenster heraus öffnen, über **Datei ▸ Öffnen** oder **Datei ▸ Zuletzt benutztes Dokument öffnen**. Beides öffnet ein neues Fenster und lässt das bereits geöffnete Dokument unberührt.

**Unter macOS können sich Dokumente als Tabs** eines Fensters öffnen. Libera Suite folgt der Systemeinstellung *Beim Öffnen von Dokumenten Tabs bevorzugen* unter Systemeinstellungen ▸ Schreibtisch & Dock, wie jede Dokumentanwendung auf dem Mac. Steht sie auf *Immer*, öffnet sich jedes Dokument als Tab. Sonst öffnet es sich in einem eigenen Fenster, und **Fenster ▸ Merge All Windows** führt sie zusammen. Das **+** am Ende der Tableiste öffnet das Startfenster als neuen Tab, und das dort gewählte Dokument nimmt seinen Platz ein. Einen Tab ziehen Sie mit der Maus in ein eigenes Fenster.

**Ein Dokument, das Sie** auf ein Fenster von Libera Suite ziehen, das Startfenster eingeschlossen, öffnet sich in einem eigenen Fenster. Ein Bild, das Sie auf ein Dokument ziehen, wird darin eingefügt.

**Datei ▸ Neu** bietet aus jedem Fenster ein Dokument, eine Tabelle oder eine Präsentation an, jeweils in einem eigenen Fenster. Unter macOS erzeugt `⌘N` eines von der Art des vorderen Fensters. Im Dokumentfenster selbst fragt **Datei ▸ Neues Dokument erstellen**, welches der drei Sie anlegen möchten.

## Speichern

**Datei ▸ Speichern** schreibt in das Dokument zurück, das Sie geöffnet haben. **Datei ▸ Speichern unter** fragt, wohin es soll. Von da an bearbeiten Sie dieses Dokument.

Beim Speichern wird das Arbeitsformat wieder in ein echtes Dokument umgewandelt, was etwa eine Sekunde dauert.

## Exportieren

Speichern unter dient auch zum Exportieren: Sein Dialog hat eine Liste **Dateiformat**.

| | |
| :--- | :--- |
| Word-Dokument | `.docx` |
| Word-Vorlage | `.dotx` |
| OpenDocument-Text | `.odt` |
| OpenDocument-Vorlage | `.ott` |
| PDF | `.pdf` |
| Rich Text Format | `.rtf` |
| HTML | `.html` |
| Markdown | `.md` |
| EPUB | `.epub` |
| FictionBook | `.fb2` |
| Nur-Text | `.txt` |

Die Wahl eines Formats benennt die Datei im Dialog um. Der Dialog lässt nicht zu, dass beides auseinanderläuft: Sie können keine ODT-Datei mit der Endung `.docx` erhalten.

Nicht jedes Format, das der Konverter lesen kann, kann er auch schreiben. Insbesondere `.doc` lässt sich öffnen, aber nicht speichern; verwenden Sie `.docx` oder `.rtf` für etwas, das zurück an ein altes Word gehen muss.

Falls Sie im Menü Datei einen Eintrag **Herunterladen als** suchen: Es gibt keinen. Die Komponenten blenden ihn aus, wenn sie als Offline-Desktop-Anwendung laufen, und setzen Speichern unter an seine Stelle: dieselbe Aufgabe, einen Menüeintrag weiter oben.

### Auf der Kommandozeile {#from-the-command-line}

`libera --convert` tut dasselbe, ohne ein Fenster zu öffnen, für ein Dokument oder hundert. Das Format wird mit `-t` über seine Endung angegeben oder aus dem Namen hinter `-o` gelesen:

```sh
libera --convert *.docx -t pdf             # bericht.pdf neben bericht.docx usw.
libera --convert vortrag.pptx -o vortrag.odp   # ein Dokument, mit Namen
libera --convert *.xlsx -t ods --outdir ods/
libera --convert bericht.docx -t pdf -o - | lp   # auf die Standardausgabe
```

Eine Datei, die schon unter dem neuen Namen existiert, wird ersetzt. Das umgewandelte Dokument selbst wird nie überschrieben, und zwei Dokumente, die denselben Namen bekämen, werden abgelehnt, bevor irgendetwas umgewandelt wird. Die Optionen sind die von pandoc, nur ohne `-f`: Was ein Dokument ist, sagt seine Endung.

## Die Menüleiste

Unter Linux und Windows sitzt die Leiste im Fenster: **Datei**, **Bearbeiten**, **Ansicht** und **Hilfe**, Letzteres mit *Libera-Hilfe* und *Über Libera Suite*. Aus dem, was das Menü dort bietet, ergeben sich drei Unterschiede. Unter Linux zeigen Neu, Öffnen und Schließen Ctrl-N, Ctrl-O und Ctrl-W, und kein anderer Eintrag zeigt seine Taste; unter Windows keiner. Ctrl-N, Ctrl-O, Ctrl-W, Ctrl-S, Ctrl-Umschalt-S, Ctrl-P und Ctrl-Z tun dort, was die ⌘-Tasten unten auf einem Mac tun. **Zuletzt verwendet** wird beim Start der Anwendung aufgebaut; ein Dokument, das Sie heute öffnen, erscheint dort also morgen. Nichts wird ausgegraut: Speichern ohne etwas zu speichern tut nichts.

Unter macOS ist es eine echte Mac-Menüleiste, mit denselben Einträgen plus **Fenster**. Die üblichen Tastenkürzel funktionieren dort, ob das Dokument den Fokus hat oder nicht:

| | |
| :--- | :--- |
| `⌘N` `⌘O` | Neu (von der Art des vorderen Fensters), Öffnen: jeweils in einem eigenen Fenster oder Tab |
| `⌘S` `⇧⌘S` | Speichern, Speichern unter |
| `⌘P` | Drucken |
| `⌘W` | Schließen, zuvor Nachfrage zu nicht gespeicherten Änderungen |
| `⌘Z` `⇧⌘Z` | Rückgängig, Wiederholen |
| `⌘F` | Suchen |
| `⌘?` | Diese Dokumentation |
| `⌘+` `⌘-` `⌘0` | Vergrößern, verkleinern, Seite einpassen |
| `⌘8` | Formatierungszeichen |

**Datei ▸ Zuletzt verwendet** wird bei jedem Öffnen neu aufgebaut. Das Menü **Fenster** listet alle geöffneten Dokumente auf.

Speichern, Rückgängig und Wiederholen sind ausgegraut, wenn es nichts zu speichern oder rückgängig zu machen gibt. Die Komponenten lehnen diese Befehle stillschweigend ab; ein Menüeintrag, der verfügbar bliebe, sähe kaputt aus.

## Schließen

Beim Schließen eines Fensters mit nicht gespeicherten Änderungen wird zuerst gefragt: **Speichern**, **Nicht speichern** oder **Abbrechen**.

Nicht speichern ist nicht endgültig. Libera Suite bewahrt auf, was Sie geschrieben haben, und bietet es beim nächsten Öffnen dieses Dokuments wieder an.

## Drucken

**Datei ▸ Drucken** oder die Drucker-Schaltfläche erzeugt ein PDF des Dokuments, fragt, wo es aufbewahrt werden soll (im Ordner des Dokuments, sofern Sie keinen anderen wählen), und öffnet es im PDF-Betrachter Ihres Systems, in dem sich der Druckdialog befindet.

Das ist vorerst die Wahl: Der Betrachter, den Sie schon haben, bietet Seitenbereiche, Papierformat, Skalierung und eine Vorschau, und nichts davon würden wir in einer ersten Version besser bauen.

## Bilder

In ein Dokument eingebettete Bilder bleiben beim Öffnen und Speichern erhalten. **Einfügen ▸ Bild** fügt ein Bild von der Festplatte ein.

## Rechtschreibprüfung {#spell-checking}

Fehler werden unterstrichen; ein Rechtsklick bietet Vorschläge an. Welches Wörterbuch verwendet wird, richtet sich nach **der Sprache des Dokuments**, die Sie in der **Statusleiste** am unteren Fensterrand einstellen, für jedes Dokument einzeln.

Mitgeliefert werden Wörterbücher für fünf Sprachen: Englisch (USA und Großbritannien), Französisch, Deutsch, Spanisch und Italienisch. Eine Sprache ohne Wörterbuch ist kein Fehler; ihre Wörter gelten schlicht als richtig. Wörter, die Sie über *Add to dictionary* hinzufügen, bleiben erhalten: Sie gelten von da an in allen Dokumenten und allen Sprachen als richtig.

## Ihr Name in Dokumenten {#your-name-in-documents}

Nachverfolgte Änderungen und Kommentare werden einer Person zugeordnet, deren Name in die gespeicherte Datei geschrieben wird. Libera Suite übernimmt ihn aus Ihrem Konto: Ihren vollständigen Namen, wie macOS ihn kennt, den Anzeigenamen Ihres Windows-Kontos oder das Feld für den vollständigen Namen Ihres Unix-Kontos unter Linux, ersatzweise Ihren Anmeldenamen.

Um einen anderen Namen zu verwenden, tragen Sie ihn in die Konfigurationsdatei ein; legen Sie die Datei an, falls sie noch nicht existiert:

```toml
user_name = "Jeanne Dupont"
```

| | |
| :--- | :--- |
| Linux | `$XDG_CONFIG_HOME/libera/config.toml`, or `~/.config/libera/config.toml` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/config/libera/config.toml` |
| macOS | `~/Library/Application Support/Libera Suite/config.toml` |
| Windows | `%USERPROFILE%\.config\libera\config.toml` |

Der Name gilt für die Fenster, die nach dem nächsten Start von Libera Suite geöffnet werden. Bereits gespeicherte Dokumente behalten den Namen, unter dem sie gespeichert wurden.

Dieselbe Datei schaltet die tägliche Suche nach einer neuen Version ab, mit einer eigenen Zeile:

```toml
check_updates = false
```

Eine weitere beschränkt sich auf die Schriften, die Libera Suite mitliefert, ohne die auf Ihrem Rechner installierten, damit ein Dokument auf jedem Computer gleich aussieht:

```toml
installed_fonts = false
```

Und eine legt die Sprache der Anwendungen fest, wenn es nicht die Ihres Systems sein soll. Ein neues Dokument richtet sein Papierformat weiterhin nach der Region Ihres Systems:

```toml
ui_language = "fr"
```

Um für einen Start eine andere Datei zu verwenden, ohne diese anzutasten, geben Sie sie mit `libera --config DATEI` (oder `-c DATEI`) oder in der Umgebungsvariablen `LIBERA_CONFIG` an. Ein so gestartetes Libera Suite übergibt seine Dokumente nicht an ein bereits laufendes, das sie mit seiner eigenen Konfiguration öffnen würde: Beenden Sie dieses zuerst.

## Wo Ihre Arbeitsdateien liegen

Solange ein Dokument geöffnet ist, hält Libera Suite einen Sitzungsordner neben ihren Anwendungsdaten. Er enthält die Arbeitskopie und ein laufendes Protokoll Ihrer Änderungen, was das Speichern schnell und das Rückgängigmachen zuverlässig macht. Er ist keine Sicherung: Das Dokument liegt dort, wo Sie es gespeichert haben.

---

Die nächste Seite ist [Was heute funktioniert](../main/status.md): was gebaut ist, und die Probleme, die wir bereits kennen. Wenn Sie auf eines stoßen, das dort nicht steht, [schreiben Sie uns](../feedback.md).
