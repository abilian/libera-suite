# Instalar

Libera Suite funciona en **Windows 10 y 11 (x64)**, **Linux (x86_64 y arm64)** y **macOS (Apple Silicon)**. La instalación no pide contraseña de administrador: se instala solo para tu cuenta. En Linux arm64, el script de instalación instala la 0.4.1, la última versión compilada para esa plataforma, hasta que vuelva a haber una más reciente.

## Windows {#windows}

Descarga el instalador y haz doble clic en él:

<https://cdn.abilian.com/libera/bundles/Libera-Suite-Setup.exe>

Añade Libera Suite al menú Inicio y al escritorio, y la incluye en *Abrir con* del Explorador de archivos. Todo va incluido: después no hay nada más que descargar.

Si prefieres un comando, esta línea en PowerShell hace lo mismo y además comprueba la descarga con su huella publicada:

```powershell
irm https://cdn.abilian.com/libera/install.ps1 | iex
```

La primera vez, Windows te preguntará dos cosas:

- **«Windows protegió su PC»**, al abrir el instalador descargado. Todavía no está firmado con un certificado, y eso es justo lo que comprueba este aviso. Elige *Más información* y luego *Ejecutar de todas formas*. La línea de PowerShell no lo provoca.
- **«¿Cómo quieres abrir este archivo?»**, la primera vez que haces doble clic en un documento que también puede abrir otro programa, como Word. Elige Libera Suite y luego *Siempre*. Puedes cambiarlo más adelante en *Configuración › Aplicaciones › Aplicaciones predeterminadas*.

## Linux

Abre un terminal y ejecuta:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

Si tu máquina tiene Flatpak, esto instala Libera Suite como Flatpak, con todo lo que necesita, y la añade al menú de aplicaciones. Si no, instala el comando `libera`; la primera vez que lo ejecutas, indica los paquetes del sistema que le faltan a tu distribución y el comando exacto para instalarlos.

Funciona en Ubuntu 22.04, Debian 12, Fedora 36, RHEL 9 y sus derivadas, y cualquier versión más reciente. Sin Flatpak necesita además Python 3.12 o posterior; si falta, el script lo avisa antes de cambiar nada.

Si usas Homebrew en Linux, la línea de Homebrew de la sección de macOS que viene a continuación también funciona allí.

## macOS

Con [Homebrew](https://brew.sh), abre el Terminal y ejecuta:

```sh
brew install abilian/tap/libera
```

Homebrew compila Libera Suite en tu Mac. La primera vez que ejecutes `libera`, te ofrecerá descargar sus componentes, unos 90 MB. Después ejecuta esto una vez, para tener Libera Suite en tu carpeta Aplicaciones:

```sh
libera --launcher-install
```

Sin Homebrew necesitas Python 3.12 o posterior, que macOS no incluye: instálalo desde [python.org](https://www.python.org/downloads/macos/). Después ejecuta:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh
```

Este script también pone Libera Suite en tu carpeta Aplicaciones.

En ambos casos obtienes el comando `libera`, y `Libera.app` en la carpeta Aplicaciones de tu carpeta de inicio. El Finder ofrece entonces Libera Suite en *Abrir con*, y Spotlight la encuentra. No se apropia de tus documentos: para que un doble clic abra un `.docx` en Libera Suite, elige *Obtener información* en uno de ellos, selecciona Libera Suite en *Abrir con* y haz clic en *Cambiar todo*.

## Iniciarla

- **Windows:** desde el menú Inicio o el escritorio, o haciendo doble clic en un documento.
- **Linux:** desde el menú de aplicaciones, o con `libera` en un terminal.
- **macOS:** desde tu carpeta Aplicaciones o Spotlight, o con `libera` en el Terminal. Indícale un documento para abrir justo ese:

```sh
libera ~/Documents/informe.docx
```

Sin argumentos, `libera` abre la ventana de inicio, donde puedes crear un documento, abrir uno o elegir uno reciente:

![La ventana de inicio, con una tarjeta New para cada uno de Document, Spreadsheet y Presentation, un botón Open y una lista Recent de tres documentos.](../assets/start.png)

La página siguiente es [Trabajar con documentos](../guide/documents.md): abrir, guardar, exportar e imprimir.

## Actualizar {#update}

Vuelve a ejecutar el mismo instalador o el mismo comando. La versión instalada se sustituye por la más reciente.

Con Homebrew, ejecuta `brew upgrade libera`. Si una versión nueva necesita componentes nuevos, Libera Suite te ofrecerá descargarlos la próxima vez que se inicie.

En macOS, si `Libera.app` deja de abrirse después de una actualización, vuelve a ejecutar `libera --launcher-install`.

## Desinstalar {#uninstall}

- **Windows:** *Configuración › Aplicaciones › Aplicaciones instaladas › Libera Suite › Desinstalar*.
- **Linux, instalada como Flatpak** (`flatpak list` muestra `eu.liberasuite.Libera`):

    ```sh
    flatpak uninstall --user eu.liberasuite.Libera
    rm -f ~/.local/share/applications/eu.liberasuite.Libera.desktop ~/.local/share/icons/hicolor/*/apps/eu.liberasuite.Libera.*
    ```

- **Linux, de otro modo:**

    ```sh
    libera --launcher-remove
    rm -rf ~/.local/bin/libera ~/.local/share/libera
    ```

- **macOS:**

    ```sh
    libera --launcher-remove
    libera --payload-remove
    rm -rf ~/.local/bin/libera ~/.local/share/libera
    ```

- **Homebrew**, en cualquiera de los dos sistemas (`libera --launcher-remove` es para macOS):

    ```sh
    libera --launcher-remove
    libera --payload-remove
    brew uninstall libera
    ```

Tus documentos nunca se tocan. Lo que Libera Suite guarda entre una sesión y otra, como la lista de documentos recientes y las sesiones sin guardar, se queda donde está: en `~/Library/Application Support/Libera Suite` en macOS, en `~/.var/app/eu.liberasuite.Libera` para el Flatpak. Borra esa carpeta para no dejar rastro.

## Si algo sale mal {#if-something-goes-wrong}

Ejecuta esto en un terminal (en Windows, en PowerShell: `& "$env:LOCALAPPDATA\Programs\Libera Suite\libera-cli.exe" --diagnose`):

```sh
libera --diagnose
```

El comando muestra una pantalla. Sobre todo importan dos líneas:

- **`window`** debería decir `ok`. En Linux, `NOT AVAILABLE` significa que faltan paquetes del sistema; al ejecutar `libera` se muestra el comando para instalarlos.
- **`payload`** indica los componentes y su procedencia. `MISSING` significa que no se descargaron: ejecuta `libera --payload-install`.

[Qué funciona hoy](status.md) recoge los problemas que ya conocemos. Para todo lo demás, [escríbenos](../feedback.md) y pega la salida de `libera --diagnose`.

Para instalar con `pipx` o `uv`, instalar el Flatpak a mano o pasar opciones al script de instalación, lee [Otras formas de instalar](alt-install.md).
