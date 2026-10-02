# Mit Dokumenten arbeiten

Die Oberfläche von Libera Suite ist englisch: Menüs und Schaltflächen werden hier so genannt, wie sie auf dem Bildschirm erscheinen.

## Öffnen

```sh
libera                             # das Startfenster
libera ~/Documents/notiz.docx
libera ~/Documents/budget.xlsx
libera ~/Documents/netzwerk.vsdx
```

**Das Dokument bestimmt, welchen Editor Sie bekommen.** Es gibt keinen Befehl, einen auszuwählen, so wie man auch keinen Texteditor für eine `.txt`-Datei auswählt: Sie öffnen das Dokument, und der richtige Editor erscheint. Eine `.xlsx`-Datei öffnet sich in Tables, eine `.pptx`-Datei in Slides, eine `.vsdx`-Datei in Diagrams.

![Das Startfenster mit je einer Kachel New für Document, Spreadsheet und Presentation, einer Schaltfläche Open und einer Liste Recent mit drei Dokumenten.](../assets/start.png)

Ohne Argument öffnet `libera` das **Startfenster**: ein neues Dokument jeder Art, einen Öffnen-Dialog, Ihre zuletzt verwendeten Dokumente und die Herkunft der Editoren. Wählen Sie etwas aus, und das Startfenster verschwindet; das Dokument bleibt.

Libera Suite öffnet **ein Dokument pro Fenster**, daher tut ein Platzhalter der Shell, wonach er aussieht:

```sh
libera ~/Documents/*.docx     # jedes in seinem Fenster
```

Sie können ein Dokument auch aus dem Editor heraus öffnen, über **File ▸ Open** oder **File ▸ Open Recent**. Beides öffnet ein neues Fenster und lässt das bereits geöffnete Dokument unberührt.

**File ▸ New** bietet aus jedem Fenster ein Dokument (Document), eine Tabelle (Spreadsheet) oder eine Präsentation (Presentation) an, jeweils in einem eigenen Fenster. Unter macOS erzeugt `⌘N` eines von der Art des vorderen Fensters. Im Editor selbst fragt **File ▸ Create New**, welches der drei Sie anlegen möchten.

## Speichern

**File ▸ Save** schreibt in das Dokument zurück, das Sie geöffnet haben. **File ▸ Save As** fragt, wohin es soll. Von da an bearbeiten Sie dieses Dokument.

Beim Speichern wird das Arbeitsformat des Editors wieder in ein echtes Dokument umgewandelt, was etwa eine Sekunde dauert.

## Exportieren

Save As dient auch zum Exportieren: Sein Dialog hat eine Liste **File Format**.

| | |
| :--- | :--- |
| Word Document | `.docx` |
| Word Template | `.dotx` |
| OpenDocument Text | `.odt` |
| OpenDocument Template | `.ott` |
| PDF | `.pdf` |
| Rich Text Format | `.rtf` |
| HTML | `.html` |
| Markdown | `.md` |
| EPUB | `.epub` |
| FictionBook | `.fb2` |
| Plain Text | `.txt` |

Die Wahl eines Formats benennt die Datei im Dialog um. Der Dialog lässt nicht zu, dass beides auseinanderläuft: Sie können keine ODT-Datei mit der Endung `.docx` erhalten.

Nicht jedes Format, das der Konverter lesen kann, kann er auch schreiben. Insbesondere `.doc` lässt sich öffnen, aber nicht speichern; verwenden Sie `.docx` oder `.rtf` für etwas, das zurück an ein altes Word gehen muss.

Falls Sie im Menü File einen Eintrag **Download As** suchen: Es gibt keinen. Die Editoren blenden ihn aus, wenn sie als Offline-Desktop-Anwendung laufen, und setzen Save As an seine Stelle: dieselbe Aufgabe, einen Menüeintrag weiter oben.

## Die Menüleiste

Unter Linux und Windows sitzt die Leiste im Fenster: **File**, **Edit**, **View** und **Help**, Letzteres mit *Libera Help* und *About Libera Suite*. Aus dem, was das Menü dort bietet, ergeben sich drei Unterschiede. Kein Eintrag hat ein Tastenkürzel, daher gehören die Tasten unten zum Editor und funktionieren in der Seite. **Open Recent** wird beim Start der Anwendung aufgebaut; ein Dokument, das Sie heute öffnen, erscheint dort also morgen. Nichts wird ausgegraut: Save ohne etwas zu speichern tut nichts.

Unter macOS ist es eine echte Mac-Menüleiste, mit denselben Einträgen plus **Window**. Die üblichen Tastenkürzel funktionieren dort, ob der Editor den Fokus hat oder nicht:

| | |
| :--- | :--- |
| `⌘N` `⌘O` | Neu (von der Art des vorderen Fensters), Öffnen: jeweils in einem eigenen Fenster |
| `⌘S` `⇧⌘S` | Speichern, Speichern unter |
| `⌘P` | Drucken |
| `⌘W` | Schließen, zuvor Nachfrage zu nicht gespeicherten Änderungen |
| `⌘Z` `⇧⌘Z` | Rückgängig, Wiederholen |
| `⌘F` | Suchen |
| `⌘?` | Diese Dokumentation |
| `⌘+` `⌘-` `⌘0` | Vergrößern, verkleinern, Seite einpassen |
| `⌘8` | Formatierungszeichen |

**File ▸ Open Recent** wird bei jedem Öffnen neu aufgebaut. Das Menü **Window** listet alle geöffneten Dokumente auf.

Save, Undo und Redo sind ausgegraut, wenn es nichts zu speichern oder rückgängig zu machen gibt. Der Editor lehnt diese Befehle stillschweigend ab; ein Menüeintrag, der verfügbar bliebe, sähe kaputt aus.

## Schließen

Beim Schließen eines Fensters mit nicht gespeicherten Änderungen wird zuerst gefragt: **Save**, **Don't Save** oder **Cancel**.

Don't Save ist nicht endgültig. Libera Suite bewahrt auf, was Sie geschrieben haben, und bietet es beim nächsten Öffnen dieses Dokuments wieder an.

## Drucken

**File ▸ Print** oder die Drucker-Schaltfläche erzeugt ein PDF des Dokuments und öffnet es im PDF-Betrachter Ihres Systems, in dem sich der Druckdialog befindet.

Das ist vorerst die Wahl: Der Betrachter, den Sie schon haben, bietet Seitenbereiche, Papierformat, Skalierung und eine Vorschau, und nichts davon würden wir in einer ersten Version besser bauen.

## Bilder

In ein Dokument eingebettete Bilder bleiben beim Öffnen und Speichern erhalten. **Insert ▸ Image** fügt ein Bild von der Festplatte ein.

## Rechtschreibprüfung {#spell-checking}

Fehler werden unterstrichen; ein Rechtsklick bietet Vorschläge an. Welches Wörterbuch verwendet wird, richtet sich nach **der Sprache des Dokuments**, die Sie in der **Statusleiste** am unteren Fensterrand einstellen, für jedes Dokument einzeln.

Mitgeliefert werden Wörterbücher für fünf Sprachen: Englisch (USA und Großbritannien), Französisch, Deutsch, Spanisch und Italienisch. Eine Sprache ohne Wörterbuch ist kein Fehler; ihre Wörter gelten schlicht als richtig. Wörter, die Sie über *Add to dictionary* hinzufügen, sind in der nächsten Sitzung wieder unterstrichen, weil persönliche Wörterbücher noch nicht gespeichert werden.

## Ihr Name in Dokumenten {#your-name-in-documents}

Nachverfolgte Änderungen und Kommentare werden einer Person zugeordnet, deren Name in die gespeicherte Datei geschrieben wird. Libera Suite übernimmt ihn aus Ihrem Konto: Ihren vollständigen Namen, wie macOS ihn kennt, den Anzeigenamen Ihres Windows-Kontos oder das Feld für den vollständigen Namen Ihres Unix-Kontos unter Linux, ersatzweise Ihren Anmeldenamen.

Eine Einstellung dafür gibt es noch nicht. Wenn ein Dokument unter einem anderen Namen hinausgehen muss, [sagen Sie es uns](../feedback.md).

## Wo Ihre Arbeitsdateien liegen

Solange ein Dokument geöffnet ist, hält Libera Suite einen Sitzungsordner neben ihren Anwendungsdaten. Er enthält die Arbeitskopie des Editors und ein laufendes Protokoll Ihrer Änderungen, was das Speichern schnell und das Rückgängigmachen zuverlässig macht. Er ist keine Sicherung: Das Dokument liegt dort, wo Sie es gespeichert haben.

---

Die nächste Seite ist [Was heute funktioniert](../main/status.md): was gebaut ist, und die Probleme, die wir bereits kennen. Wenn Sie auf eines stoßen, das dort nicht steht, [schreiben Sie uns](../feedback.md).
