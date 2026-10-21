# Libera Suite en Euro-Office Desktop

**Dezelfde motor, een andere schil.**

Libera Suite en Euro-Office Desktop Editors gebruiken dezelfde componenten. `sdkjs`, `web-apps` en de converter `x2t` komen uit de repository's van Euro-Office, op de revisies van hun gepubliceerde releases. Een document wordt daarom in beide op dezelfde manier weergegeven, geïmporteerd en geëxporteerd, afgezien van onze correcties. Het verschil zit vooral in de applicatie rond de componenten.

**Euro-Office Desktop Editors** behoudt de architectuur van ONLYOFFICE Desktop: een ingebouwde Chromium-browser (CEF) en een Qt-interface, in C++ (de repository's `desktop-sdk` en `desktop-apps`).

**Libera Suite** vervangt die laag door een paar duizend regels Python en JavaScript. De componenten worden weergegeven in de webengine die het systeem al heeft: WebKit op macOS en Linux, WebView2 op Windows. De componenten merken het verschil niet. Ze praten met dezelfde native interface (`AscDesktopEditor`), die wij hebben herschreven.

Die keuze heeft een aantal gevolgen.

- **Grootte.** Voor versie 9.3.5-2 is de macOS-`.dmg` van Euro-Office 926 MB en het zelfstandige Windows-installatieprogramma 616 MB. Libera Suite downloadt ongeveer 90 MB aan componenten, plus een applicatie van een paar megabyte.
- **Installatie.** `pip` of `pipx`, Homebrew (macOS en Linux), Flatpak, een Windows-installatieprogramma of één `curl | sh`-regel.
- **Opdrachtregel.** `libera --convert *.docx -t pdf` converteert documenten zonder een venster te openen.
- **Correcties.** We bouwen alles uit de broncode van Euro-Office, met een [gepubliceerde reeks patches](/en/develop/patches/). Die gaat vooral over de converter, voor OpenDocument- en CSV-bestanden. De releases van Euro-Office bevatten die correcties vandaag niet.
- **Licentie.** De applicatie valt onder Apache 2.0, en de componenten blijven onder de AGPL.

Euro-Office Desktop heeft vandaag een paar functies die Libera Suite nog niet heeft: tabbladen op Linux en Windows, PDF-bewerking en formulieren, digitale handtekeningen, en verbinding met een Nextcloud-, ownCloud- of Seafile-server om samen te bewerken. [De roadmap](/en/develop/roadmap/) zegt wanneer ze komen.

**Kortom:** wie heel ONLYOFFICE Desktop in een Europees project wil, kiest terecht voor Euro-Office Desktop. Libera Suite gokt op iets anders: een lichtere applicatie, gemaakt van korte code die een klein team kan lezen en onderhouden, en die functies toevoegt zonder aan de bewerkingsengine te komen.
