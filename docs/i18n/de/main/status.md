# Was heute funktioniert

Libera Suite ist jung. Diese Seite führt den Stand auf: was gebaut ist, was halb fertig ist und was noch nicht begonnen wurde.

Die Oberfläche von Libera Suite ist englisch: Menüs und Schaltflächen werden hier so genannt, wie Sie sie auf dem Bildschirm sehen.

## Was funktioniert

| | |
| :--- | :--- |
| **Vier Anwendungen** | Windows 10 und 11 auf x64, Linux auf x86_64 (arm64 mit 0.4.1), macOS auf Apple Silicon. Words, Tables und Slides bearbeiten; Diagrams liest Visio-Dateien. |
| **Öffnen und speichern** | Words `.docx .odt .rtf .txt .md`, Tables `.xlsx .ods .csv`, Slides `.pptx .odp`. Save, Save As, New. |
| **Exportieren** | Save As bietet für jede Anwendung eine Formatliste an, PDF eingeschlossen. Jedes angebotene Format wird durch eine echte Konvertierung geprüft, deren Text danach wieder gelesen wird. |
| **Bilder** | Bleiben beim Öffnen und Speichern erhalten; Einfügen ▸ Bild funktioniert. |
| **Drucken** | Erzeugt ein PDF, fragt, wo es aufbewahrt werden soll, und öffnet es in Ihrem PDF-Betrachter. |
| **Rechtschreibprüfung** | Fünf Sprachen, mit Vorschlägen. Siehe unten. |
| **In Ihrer Sprache** | Die Anwendungen folgen der Sprache Ihres Systems, und ein neues Dokument beginnt mit der leeren Vorlage Ihrer Region: A4-Papier überall außer in den USA, und Rechtschreibprüfung in Ihrer Sprache. Auf Deutsch, Französisch, Italienisch und Spanisch folgen auch Menüleiste, Startfenster und Dialoge; in jeder anderen Sprache sind sie auf Englisch. |
| **Zuletzt verwendete Dokumente** | Datei ▸ Zuletzt verwendet merkt sich die letzten 20. |
| **Mehrere Dokumente gleichzeitig** | Auch verschiedener Art, jedes in seinem Fenster, unter macOS jedes in seinem Tab, wenn das System Tabs bevorzugt: über Datei ▸ Neu oder Datei ▸ Öffnen, per Doppelklick im Dateimanager oder mit `libera *.docx`. Der Dateityp bestimmt die Anwendung. |
| **Im Startmenü und im Anwendungsmenü** | Unter Windows legt das Installationsprogramm Libera Suite im Startmenü und auf dem Desktop ab und trägt sie im Explorer unter *Öffnen mit* ein. Unter Linux trägt das Flatpak sie mit Symbol und Dateizuordnungen in das Anwendungsmenü ein; `libera --launcher-install` tut dasselbe für jede andere Installation. |
| **Ein Startfenster** | `libera` ohne Argument: neues Dokument, öffnen, zuletzt verwendete Dokumente und die Herkunft der Komponenten. |
| **Wiederherstellung nach Abstürzen** | Nicht gespeicherte Änderungen werden beim nächsten Öffnen des Dokuments wieder angeboten. |
| **Ein anderswo geöffnetes Dokument** | Ist es bereits in LibreOffice oder einer anderen Instanz von Libera Suite geöffnet, wird es als *zur Bearbeitung gesperrt* markiert: Sie können es lesen und ändern, und beim Speichern wird nach dem Ort gefragt, sodass die Datei der anderen Instanz nie überschrieben wird. Ein Dokument, das bereits in einem Fenster angezeigt wird, holt beim erneuten Öffnen dieses Fenster nach vorn. Microsoft Office und Libera Suite sehen die Sperren des jeweils anderen nicht: Ein in Word geöffnetes Dokument ist nicht geschützt. |
| **Schließen fragt nach** | Ein Fenster mit nicht gespeicherten Änderungen bietet Speichern, Nicht speichern oder Abbrechen an. |
| **Eine Menüleiste** | File, Edit, View und Help auf allen Plattformen. macOS ergänzt Window sowie die üblichen Tastenkürzel. |
| **Über** | Wer die Komponenten geschrieben hat und unter welcher Lizenz: `Datei ▸ Über das Produkt` im Dokumentfenster, `Hilfe ▸ Über Libera Suite` unter Linux und Windows. macOS legt es in das Anwendungsmenü. |
| **Einstellungen bleiben erhalten** | Design, Maßeinheiten, Sprache der Rechtschreibprüfung und Ähnliches sind nach einem Neustart noch gesetzt. |
| **Installation der Komponenten** | Vom Server oder aus einem lokalen Ordner mit gebauten Artefakten. In beiden Fällen wird jedes Artefakt anhand der Prüfsummen geprüft, die mit der Anwendung geliefert werden. |

## Bekannte Probleme

**Keines davon muss gemeldet werden**: Wir kennen sie. Die folgenden Abschnitte erläutern sie.

| | |
| :--- | :--- |
| **macOS spricht von einem nicht verifizierten Entwickler** | Nur bei einer `Libera.app`, die Sie selbst gebaut haben: Sie ist nicht mit einer Developer ID signiert, daher erhebt Gatekeeper beim ersten Mal Einspruch. [Weitere Installationswege](alt-install.md#a-double-clickable-application-on-macos) zeigt, wie Sie darüber hinwegkommen. Eine Installation über `pip`, `pipx` oder Homebrew ist nie betroffen. |
| **Aus einem Terminal gestartet, zeigt das Dock „Python“** | Nur wenn Sie `libera` aus einer `pipx`-Installation oder einer virtuellen Umgebung starten. Ein Dock-Symbol trägt den Namen des Programmpakets, aus dem es gestartet wurde, hier den des Python-Interpreters, und daran kann die Anwendung nichts ändern. Symbol und Menüleiste sind in jedem Fall unsere; `Libera.app` zeigt Libera an. Ein Dokument, das Sie auf dieses Python-Symbol ziehen, wird im Namen von Python abgelehnt; das Symbol von `Libera.app` nimmt es an. |
| **Diagrams kann nicht speichern** | Es öffnet eine `.vsdx`-Datei und zeigt sie an. Der Konverter kann kein Visio-Format schreiben, also gibt es nichts zu speichern und keine leere Vorlage für den Anfang. |
| **Keine PDF-Bearbeitung** | PDFs werden nur erzeugt. Ein PDF zum Bearbeiten zu öffnen, ist nicht angebunden. |
| **Eine schmale Menüleiste, ohne angezeigte Tastenkürzel unter Linux und Windows** | Linux und Windows haben File, Edit, View und Help, im Fenster gezeichnet, ohne angezeigte Tastenkürzel. Die Tasten funktionieren trotzdem: Ctrl-N, Ctrl-O, Ctrl-W, Ctrl-S, Ctrl-Umschalt-S, Ctrl-P und Ctrl-Z. macOS hat dieselben Menüs plus Window, mit den üblichen Tastenkürzeln. |
| **Keine Tabs unter Linux und Windows** | Dort ein Fenster pro Dokument. macOS hat Tabs. |
| **Windows warnt vor dem Installationsprogramm** | Das heruntergeladene Installationsprogramm ist noch nicht signiert, daher zeigt SmartScreen beim ersten Mal *„Der Computer wurde durch Windows geschützt“*. [Installieren](install.md#windows) zeigt, wie Sie darüber hinwegkommen. Die Installation per PowerShell-Zeile ist nie betroffen. |

Wenn Sie auf etwas stoßen, das *nicht* auf dieser Liste steht, [melden Sie es uns](../feedback.md).

## Halb fertig

**Die Menüleiste unter Linux und Windows.** Sie ist im Fenster gezeichnet, mit Datei, Bearbeiten, Ansicht und Hilfe; jeder Eintrag funktioniert. Keiner zeigt ein Tastenkürzel an, aber die üblichen Tasten funktionieren: Ctrl-N legt ein neues Dokument derselben Art an, Ctrl-O öffnet eines, Ctrl-W schließt das Fenster (und fragt vorher nach ungespeicherten Änderungen), und die eigenen Kürzel der Komponenten, Ctrl-S, Ctrl-Umschalt-S (Speichern unter), Ctrl-P und Ctrl-Z, funktionieren ebenfalls. Unter Windows wurden Ctrl-N, Ctrl-O und Ctrl-W noch nicht auf einem echten Rechner geprüft. Datei ▸ Neu ▸ Dokument, Tabelle oder Präsentation funktioniert, ebenso die Kacheln Neu im Startfenster und der Reiter Datei des Dokuments.

**`Libera.app` unter macOS.** `build/macos/macos-app.sh` baut sie. Sie öffnet ein Dokument per Doppelklick oder wenn es auf ihr Dock-Symbol gezogen wird, erscheint unter *Öffnen mit* und zeigt das Libera-Zeichen im Dock. Sie ist aber ein Starter um den Interpreter, mit dem sie gebaut wurde (nichts ist eingebettet, signiert oder notarisiert), und damit noch nichts, was man jemand anderem geben kann.

## Noch nicht begonnen

### Im Dokumentfenster

- **Kennwortgeschützte Dokumente.** Weder öffnen noch speichern.
- **Digitale Signaturen.**
- **Serienbriefe.**
- **Plugins.** In diesem Fork vom Upstream-Projekt abgeschaltet, daher erscheint das Panel nie.
- **Makros.** Abgeschaltet. Die Makros der Komponenten sind JavaScript und führen kein VBA aus Microsoft-Office-Dokumenten aus, daher werden die Makros eines Dokuments nicht ausgeführt. Sie bleiben erhalten: Beim Speichern einer `.docm`-, `.xlsm`- oder `.pptm`-Datei bleibt ihr VBA unverändert. [Die Roadmap](/en/develop/roadmap/), auf Englisch, beschreibt, was stattdessen kommt.

### In der Anwendung

- **Tabs unter Linux und Windows.** Dort ein Fenster pro Dokument, die die Taskleiste gruppiert.
- **Eine weitergebbare Anwendung unter macOS.** `Libera.app` läuft aus Ihrer eigenen Kopie des Quellcodes und bettet weder Interpreter noch Komponenten ein. Windows hat eine: Sein Installationsprogramm bringt alles mit.
- **Automatische Aktualisierungen** und **Code-Signatur**. macOS behandelt eine selbst gebaute `Libera.app` als Software eines nicht verifizierten Entwicklers. Windows warnt vor dem heruntergeladenen Installationsprogramm.
- **Eine Offline-Hilfe**, lesbar ohne Browser und ohne Netz. Das Menü Help öffnet diese Website; About funktioniert offline. Siehe unten.

### Anderswo

- **Diagramme bearbeiten.** Diagrams öffnet eine `.vsdx`-Datei und zeigt sie an. Der Konverter kann kein Visio-Format schreiben, also gibt es nichts zu speichern und keine leere Vorlage für den Anfang.
- **PDF-Bearbeitung.** Das Upstream-Projekt hat einen PDF-Editor; die Komponenten, die Libera Suite installiert, enthalten ihn noch nicht, weil nichts ihn öffnen würde.
- **Zusammenarbeit, Cloud-Speicher, Konten, Telemetrie.** Nichts davon ist gebaut, und an nichts davon wird gearbeitet. [Die Roadmap](/en/develop/roadmap/), auf Englisch, beschreibt, wie jedes davon aussähe, falls es käme. [Was Ihren Rechner verlässt](../index.md#what-leaves-your-machine) führt die gesamte Netzwerknutzung der Anwendung auf.

## Hinweise zu einzelnen Lücken

### Hilfe

Es gibt ein Menü **Hilfe**, auf allen Plattformen, und es öffnet diese Website in Ihrem Browser. *In* der Anwendung gibt es keine Hilfe, die ohne Netz lesbar wäre. Das Upstream-Projekt liefert ein vollständiges Handbuch. Libera Suite lässt es weg: Es beschreibt ONLYOFFICE und ist in acht Sprachen 84 MB groß. Eine Offline-Hilfe kommt, sobald unsere eigene Dokumentation umfangreich genug ist, um sie mitzuliefern.

### Rechtschreibprüfung

Libera Suite liefert Wörterbücher für **Englisch (USA und Großbritannien), Französisch, Deutsch, Spanisch und Italienisch** mit: 9,5 MB, ausgewählt, weil der vollständige Satz 327 MB umfasst. Eine Sprache hinzuzufügen, erfordert eine Zeile in `build/payload/dictionaries.txt` und einen Neubau der Komponenten.

Eine Sprache ohne Wörterbuch ist kein Fehler: Ihre Wörter gelten schlicht als richtig, wie in der Desktop-Anwendung des Upstream-Projekts. Über *Add to dictionary* hinzugefügte Wörter bleiben erhalten, für alle Dokumente und alle Sprachen.

Wie Sie die Sprache eines Dokuments einstellen, steht unter [Mit Dokumenten arbeiten](../guide/documents.md#spell-checking).

### Ihr Name in Dokumenten

Nachverfolgte Änderungen und Kommentare werden einer Person zugeordnet, deren Name in die gespeicherte Datei geschrieben wird. Libera Suite übernimmt ihn aus Ihrem Konto: den vollständigen Namen, unter dem macOS Sie kennt, den Anzeigenamen Ihres Windows-Kontos oder das Feld für den vollständigen Namen Ihres Unix-Kontos unter Linux. Ein anderer lässt sich in der Konfigurationsdatei eintragen; einen Menüeintrag dafür gibt es noch nicht. [Mit Dokumenten arbeiten](../guide/documents.md#your-name-in-documents) erläutert die Einzelheiten.

### Schriften

Libera Suite liefert einen Grundbestand an Schriften mit: Liberation, Carlito, Caladea, Open Sans und einige weitere, genug, um gewöhnliche Dokumente originalgetreu darzustellen, bei 7 MB. Der vollständige Satz umfasst 248 MB. Ein Dokument, das eine Schrift außerhalb dieses Bestands verlangt, verwendet die auf Ihrem Rechner installierte, auf dem Bildschirm wie im PDF, und erhält nur dann eine Ersatzschrift, wenn auch Ihr Rechner sie nicht hat. Libera Suite erfasst Ihre Schriften beim ersten Start und erneut im Hintergrund, wann immer Sie eine installieren oder entfernen; die danach geöffneten Fenster verwenden die neue Liste. Ob der Bestand erweitert wird, besonders für Chinesisch, Japanisch und Koreanisch, ist noch offen.

### Treue der Darstellung

Die Layout-Engine stammt aus dem Upstream-Projekt und ist ausgereift. Wenn Sie etwas Falsches sehen, liegt die Ursache eher in unserer Paketierung (eine fehlende Schrift, eine fehlende Ressource). Solche Meldungen sind deshalb besonders nützlich; schicken Sie uns [eine Rückmeldung](../feedback.md) mit der Datei.
