# Was heute funktioniert

Libera Suite ist jung. Diese Seite führt den Stand auf: was gebaut ist, was halb fertig ist und was noch nicht begonnen wurde.

Die Oberfläche von Libera Suite ist englisch: Menüs und Schaltflächen werden hier so genannt, wie Sie sie auf dem Bildschirm sehen.

## Was funktioniert

| | |
| :--- | :--- |
| **Vier Editoren** | Windows 10 und 11 auf x64, Linux auf x86_64 und arm64, macOS auf Apple Silicon. Words, Tables und Slides bearbeiten; Diagrams liest Visio-Dateien. |
| **Öffnen und speichern** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Save, Save As, New. |
| **Exportieren** | Save As bietet für jeden Editor eine Formatliste an, PDF eingeschlossen. Jedes angebotene Format wurde durch eine echte Konvertierung geprüft. |
| **Bilder** | Bleiben beim Öffnen und Speichern erhalten; Insert ▸ Image funktioniert. |
| **Drucken** | Erzeugt ein PDF und öffnet es in Ihrem PDF-Betrachter. |
| **Rechtschreibprüfung** | Fünf Sprachen, mit Vorschlägen. Siehe unten. |
| **Zuletzt verwendete Dokumente** | File ▸ Open Recent merkt sich die letzten 20. |
| **Mehrere Dokumente gleichzeitig** | Auch verschiedener Art, jedes in seinem Fenster: über File ▸ New oder File ▸ Open, per Doppelklick im Dateimanager oder mit `libera *.docx`. Der Dateityp bestimmt den Editor. |
| **Im Startmenü und im Anwendungsmenü** | Unter Windows legt das Installationsprogramm Libera Suite im Startmenü und auf dem Desktop ab und trägt sie im Explorer unter *Öffnen mit* ein. Unter Linux trägt das Flatpak sie mit Symbol und Dateizuordnungen in das Anwendungsmenü ein; `libera --launcher-install` tut dasselbe für jede andere Installation. |
| **Ein Startfenster** | `libera` ohne Argument: neues Dokument, öffnen, zuletzt verwendete Dokumente und die Herkunft der Editoren. |
| **Wiederherstellung nach Abstürzen** | Nicht gespeicherte Änderungen werden beim nächsten Öffnen des Dokuments wieder angeboten. |
| **Schließen fragt nach** | Ein Fenster mit nicht gespeicherten Änderungen bietet Save, Don't Save oder Cancel an. |
| **Eine Menüleiste** | File, Edit, View und Help auf allen Plattformen. macOS ergänzt Window sowie die üblichen Tastenkürzel. |
| **Über** | Wer die Editoren geschrieben hat und unter welcher Lizenz: `File ▸ About` im Editor, `Help ▸ About Libera Suite` unter Linux und Windows. macOS legt es in das Anwendungsmenü. |
| **Einstellungen bleiben erhalten** | Design, Maßeinheiten, Sprache der Rechtschreibprüfung und Ähnliches sind nach einem Neustart noch gesetzt. |
| **Installation der Editoren** | Vom Server oder aus einem lokalen Ordner mit gebauten Artefakten. In beiden Fällen wird jedes Artefakt anhand der Prüfsummen geprüft, die mit der Anwendung geliefert werden. |

## Bekannte Probleme

**Keines davon muss gemeldet werden**: Wir kennen sie. Die folgenden Abschnitte erläutern sie.

| | |
| :--- | :--- |
| **macOS spricht von einem nicht verifizierten Entwickler** | Nur bei einer `Libera.app`, die Sie selbst gebaut haben: Sie ist nicht mit einer Developer ID signiert, daher erhebt Gatekeeper beim ersten Mal Einspruch. [Weitere Installationswege](alt-install.md#a-double-clickable-application-on-macos) zeigt, wie Sie darüber hinwegkommen. Eine Installation über `pip`, `pipx` oder Homebrew ist nie betroffen. |
| **Aus einem Terminal gestartet, zeigt das Dock „Python“** | Nur wenn Sie `libera` aus einer `pipx`-Installation oder einer virtuellen Umgebung starten. Ein Dock-Symbol trägt den Namen des Programmpakets, aus dem es gestartet wurde, hier den des Python-Interpreters, und daran kann die Anwendung nichts ändern. Symbol und Menüleiste sind in jedem Fall unsere; `Libera.app` zeigt Libera an. |
| **Diagrams kann nicht speichern** | Es öffnet eine `.vsdx`-Datei und zeigt sie an. Der Konverter kann kein Visio-Format schreiben, also gibt es nichts zu speichern und keine leere Vorlage für den Anfang. |
| **Eine CSV- oder `.txt`-Datei mit einem Emoji lässt sich nicht als solche speichern** | Unter macOS und Linux verfälscht der Konverter reinen Text, der ein Zeichen jenseits der ersten 65.536 von Unicode enthält, etwa ein Emoji. Libera Suite verweigert dann das Speichern und lässt die Datei unverändert. Save As als `.xlsx` oder `.docx` behält alles. Eine Korrektur des Konverters ist für die nächste Version der Editoren geplant. |
| **In einer CSV-Datei über etwa 500 KB kann eine Zeile falsch gelesen werden** | Der Konverter überspringt eines von 500.000 Zeichen. Ist dieses Zeichen ein Anführungszeichen, ein Komma oder ein Zeilenumbruch, wird eine Zelle in zwei geteilt, oder zwei Zellen oder zwei Zeilen laufen zusammen. Libera Suite nennt beim Öffnen der Datei die betroffenen Zeilen: Prüfen Sie sie vor dem Speichern, denn beim Speichern wird geschrieben, was das Blatt zeigt. Eine Korrektur des Konverters ist für die nächste Version der Editoren geplant. |
| **Keine PDF-Bearbeitung** | PDFs werden nur erzeugt. Ein PDF zum Bearbeiten zu öffnen, ist nicht angebunden. |
| **Eine schmale Menüleiste, ohne Tastenkürzel unter Linux und Windows** | Linux und Windows haben File, Edit, View und Help, im Fenster gezeichnet, ohne Tastenkürzel; die eigenen Kürzel des Editors, Ctrl-S, Ctrl-P und Ctrl-Z, funktionieren weiterhin in der Seite. macOS hat dieselben Menüs plus Window, mit den üblichen Tastenkürzeln. |
| **Keine Tabs** | Ein Fenster pro Dokument. |
| **Keine Dateisperre** | Wird dasselbe Dokument in zwei Fenstern bearbeitet, geht eine der beiden Änderungsreihen verloren. |
| **Windows warnt vor dem Installationsprogramm** | Das heruntergeladene Installationsprogramm ist noch nicht signiert, daher zeigt SmartScreen beim ersten Mal *„Der Computer wurde durch Windows geschützt“*. [Installieren](install.md#windows) zeigt, wie Sie darüber hinwegkommen. Die Installation per PowerShell-Zeile ist nie betroffen. |

Wenn Sie auf etwas stoßen, das *nicht* auf dieser Liste steht, [melden Sie es uns](../feedback.md).

## Halb fertig

**Die Menüleiste unter Linux und Windows.** Sie ist im Fenster gezeichnet, mit File, Edit, View und Help; jeder Eintrag funktioniert. Keiner hat ein eigenes Tastenkürzel, also gehen die Tasten, die Sie ohnehin verwenden, an den Editor: Ctrl-S, Ctrl-P und Ctrl-Z funktionieren in der Seite. Ctrl-N tut unter Linux nichts; unter Windows wurde es noch nicht geprüft. File ▸ New ▸ Document, Spreadsheet oder Presentation funktioniert, ebenso die Kacheln New im Startfenster und der Reiter File des Editors.

**`Libera.app` unter macOS.** `build/macos-app.sh` baut sie. Sie öffnet ein Dokument per Doppelklick, erscheint unter *Öffnen mit* und zeigt das Libera-Zeichen im Dock. Sie ist aber ein Starter um den Interpreter, mit dem sie gebaut wurde (nichts ist eingebettet, signiert oder notarisiert), und damit noch nichts, was man jemand anderem geben kann.

## Noch nicht begonnen

### Im Editor

- **Kennwortgeschützte Dokumente.** Weder öffnen noch speichern.
- **Digitale Signaturen.**
- **Serienbriefe.**
- **Plugins.** In diesem Fork vom Upstream-Projekt abgeschaltet, daher erscheint das Panel nie.

### In der Anwendung

- **Tabs.** Die Fenster gibt es, und das Menü Window listet sie auf, aber sie lassen sich nicht in einem Fenster zusammenführen.
- **Dateisperren.** Zwei Instanzen von Libera Suite, die dieselbe Datei bearbeiten, bemerken einander nicht.
- **Eine weitergebbare Anwendung unter macOS.** `Libera.app` läuft aus Ihrer eigenen Kopie des Quellcodes und bettet weder Interpreter noch Editoren ein. Windows hat eine: Sein Installationsprogramm bringt alles mit.
- **Ziehen und Ablegen** auf das Fenster oder das Dock-Symbol.
- **Automatische Aktualisierungen** und **Code-Signatur**. macOS behandelt eine selbst gebaute `Libera.app` als Software eines nicht verifizierten Entwicklers. Windows warnt vor dem heruntergeladenen Installationsprogramm.
- **Eine Offline-Hilfe**, lesbar ohne Browser und ohne Netz. Das Menü Help öffnet diese Website; About funktioniert offline. Siehe unten.

### Anderswo

- **Diagramme bearbeiten.** Diagrams öffnet eine `.vsdx`-Datei und zeigt sie an. Der Konverter kann kein Visio-Format schreiben, also gibt es nichts zu speichern und keine leere Vorlage für den Anfang.
- **PDF-Bearbeitung.** Die Editoren enthalten einen Editor dafür. Noch führt nichts zu ihm.
- **Zusammenarbeit, Cloud-Speicher, Konten, Telemetrie.** Nichts davon ist gebaut, und an nichts davon wird gearbeitet. [Die Roadmap](/en/develop/roadmap/), auf Englisch, beschreibt, wie jedes davon aussähe, falls es käme. [Was Ihren Rechner verlässt](../index.md#what-leaves-your-machine) führt die gesamte Netzwerknutzung der Anwendung auf.

## Hinweise zu einzelnen Lücken

### Hilfe

Es gibt ein Menü **Help**, auf allen Plattformen, und es öffnet diese Website in Ihrem Browser. *In* der Anwendung gibt es keine Hilfe, die ohne Netz lesbar wäre. Das Upstream-Projekt liefert ein vollständiges Handbuch. Libera Suite lässt es weg: Es beschreibt ONLYOFFICE und ist in acht Sprachen 84 MB groß. Eine Offline-Hilfe kommt, sobald unsere eigene Dokumentation umfangreich genug ist, um sie mitzuliefern.

### Rechtschreibprüfung

Libera Suite liefert Wörterbücher für **Englisch (USA und Großbritannien), Französisch, Deutsch, Spanisch und Italienisch** mit: 9,5 MB, ausgewählt, weil der vollständige Satz 327 MB umfasst. Eine Sprache hinzuzufügen, erfordert eine Zeile in `build/dictionaries.txt` und einen Neubau der Editoren.

Eine Sprache ohne Wörterbuch ist kein Fehler: Ihre Wörter gelten schlicht als richtig, wie in der Desktop-Anwendung des Upstream-Projekts. Persönliche Wörterbücher (*Add to dictionary*) werden noch nicht gespeichert; ein hinzugefügtes Wort ist in der nächsten Sitzung wieder unterstrichen.

Wie Sie die Sprache eines Dokuments einstellen, steht unter [Mit Dokumenten arbeiten](../guide/documents.md#spell-checking).

### Ihr Name in Dokumenten

Nachverfolgte Änderungen und Kommentare werden einer Person zugeordnet, deren Name in die gespeicherte Datei geschrieben wird. Libera Suite übernimmt ihn aus Ihrem Konto: den vollständigen Namen, unter dem macOS Sie kennt, den Anzeigenamen Ihres Windows-Kontos oder das Feld für den vollständigen Namen Ihres Unix-Kontos unter Linux. Ändern lässt er sich noch nicht. [Mit Dokumenten arbeiten](../guide/documents.md#your-name-in-documents) erläutert die Einzelheiten.

### Schriften

Libera Suite liefert einen Grundbestand an Schriften mit: Liberation, Carlito, Caladea, Open Sans und einige weitere, genug, um gewöhnliche Dokumente originalgetreu darzustellen, bei 7 MB. Der vollständige Satz umfasst 248 MB. Ein Dokument, das eine Schrift verlangt, die weder in diesem Bestand noch unter den auf Ihrem Rechner installierten Schriften ist, erhält eine Ersatzschrift. Ob der Bestand erweitert wird, besonders für Chinesisch, Japanisch und Koreanisch, ist noch offen.

### Treue der Darstellung

Die Layout-Engine stammt aus dem Upstream-Projekt und ist ausgereift. Wenn Sie etwas Falsches sehen, liegt die Ursache eher in unserer Paketierung (eine fehlende Schrift, eine fehlende Ressource). Solche Meldungen sind deshalb besonders nützlich; schicken Sie uns [eine Rückmeldung](../feedback.md) mit der Datei.
