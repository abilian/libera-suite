# Over Libera Suite

Libera Suite wordt gemaakt door [Abilian](https://abilian.com), een Frans bedrijf dat vrije software bouwt. Stefane Fermigier leidt het project.

De broncode is openbaar, op [github.com/abilian/libera-suite](https://github.com/abilian/libera-suite). De hosttoepassing, het deel dat wij hebben geschreven, valt onder de Apache License 2.0; de componenten vallen onder de GNU AGPL v3. [Licentie en naamsvermelding](../licence.md) geeft de details, ook hoe je de exacte broncode van elke release krijgt.

## Dankwoord

Libera Suite bouwt voort op het werk van anderen. Het meeste van wat je ziet als je een document bewerkt, is van hen.

### De componenten

Libera Suite bevat componenten van [**Euro-Office**](https://github.com/Euro-Office), zelf een fork van **ONLYOFFICE**, ontwikkeld door Ascensio System SIA. De documentengine, de bewerkingscomponenten, de formaatconverter en de ondersteuning voor elk formaat komen allemaal daarvandaan, aangepast met [een korte reeks patches](/en/develop/patches/) van onszelf. Het moeilijke deel van een kantoorsuite is twintig jaar lang de `.docx`-documenten van anderen correct leren lezen, en dat deel is van hen.

Van dezelfde organisatie komen de lege sjablonen waarmee elk nieuw document begint, de spellingwoordenboeken (Engels, Frans, Duits, Spaans en Italiaans) en de lettertypen die Libera Suite meelevert: onder meer Liberation, Carlito, Caladea, Open Sans en Asana Math, elk onder een eigen vrije licentie.

Onder de componenten zitten nog veel meer bibliotheken, met V8 en Boost als de grootste, die de build van Euro-Office meebrengt.

### De applicatie

- [**Python**](https://www.python.org), waarin de hele hosttoepassing is geschreven.
- [**pywebview**](https://pywebview.flowrl.com), dat op elk platform een webweergave in een native venster zet. Op macOS gaat dat via [**PyObjC**](https://pyobjc.readthedocs.io), op Linux via [**PyGObject**](https://pygobject.gnome.org) en WebKitGTK.
- De webengines die de componenten weergeven: **WebKit** op macOS en Linux, en **WebView2** van Microsoft op Windows.
- Op Linux de [**GNOME-runtime**](https://flathub.org/apps/org.gnome.Platform) waarop de Flatpak draait, en [**Flatpak**](https://flatpak.org) zelf.
- Op Windows [**PyInstaller**](https://pyinstaller.org), dat de applicatie met een eigen Python verpakt, en [**Inno Setup**](https://jrsoftware.org/isinfo.php), dat het installatieprogramma bouwt.

### Deze site

Gebouwd met [**Zensical**](https://zensical.org). De lettertypen, [**Inter**](https://rsms.me/inter/) en [**JetBrains Mono**](https://www.jetbrains.com/lp/mono/), vallen onder de SIL Open Font License en worden door deze site zelf geleverd.

## Contact

Voor een bug, een vraag of een suggestie, zie [Feedback](../feedback.md).
