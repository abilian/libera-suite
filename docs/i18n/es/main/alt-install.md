# Otras formas de instalar

[Instalar](install.md) explica la forma habitual para cada plataforma, la que le sirve a la mayoría. Esta página trata todo lo demás: elegir tú mismo un canal, instalar a mano y saber dónde acaban los archivos.

## Las opciones del script de instalación

`install.sh` acepta opciones. Cuando se ejecuta a través de una tubería, necesita `sh -s --` delante de ellas:

```sh
curl -fsSL https://cdn.abilian.com/libera/install.sh | sh -s -- --prefix ~/apps
curl -fsSL https://cdn.abilian.com/libera/install.sh | bash -s -- --help
```

| | |
| :--- | :--- |
| `--prefix DIR` | instalar en otro sitio (por defecto: `~/.local`) |
| `--channel pip` | en Linux, instalar el paquete de Python aunque haya Flatpak |
| `--origin URL` | descargar desde un servidor distinto del público |

Solo escribe en `~/.local/bin` y `~/.local/share`. Abre su dirección en un navegador para leerlo antes de ejecutarlo.

## pipx o uv

Libera Suite está en PyPI con el nombre `libera` y necesita Python 3.12 o posterior. Sus [componentes](#the-editors) vienen con ella. En macOS y Windows:

```sh
uv tool install libera      # o bien: pipx install libera
```

Para probarla sin instalarla, `uvx libera` la ejecuta desde una caché.

En Linux, la ventana la dibuja GTK, cuyos enlaces de Python vienen de tu distribución y están compilados para su propio Python. Un entorno aislado no los ve, así que `pipx` necesita dos opciones:

```sh
pipx install --python /usr/bin/python3 --system-site-packages libera
```

Sin ellas, Libera Suite se instala sin errores y luego no abre ninguna ventana. `uv tool` no tiene equivalente de `--system-site-packages`: en Linux, usa `pipx`. La primera vez que se ejecuta, `libera` indica los paquetes de GTK que le faltan a tu distribución; conoce apt, dnf, pacman y zypper.

## El Flatpak, a mano

Esto es lo que hace el script de instalación cuando hay Flatpak:

```sh
arch=amd64     # o arm64, según tu máquina
ver=$(curl -fsSL https://cdn.abilian.com/libera/bundles/latest)
# en arm64: ver=0.4.1, la última versión compilada para esa plataforma
curl -fLO "https://cdn.abilian.com/libera/bundles/libera-$ver-$arch.flatpak"
flatpak install --user "./libera-$ver-$arch.flatpak"
flatpak run eu.liberasuite.Libera
```

`bundles/latest` contiene el número de la versión actual, así que estas líneas siguen siendo válidas de una versión a otra. El paquete, de unos 70 MB, contiene los componentes. Funciona sobre el entorno de ejecución de GNOME, que `flatpak` descarga de Flathub la primera vez; una máquina sin el repositorio de Flathub debe añadirlo antes:

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

## Los componentes {#the-editors}

Todos los canales instalan los componentes con la aplicación. El instalador de Windows y el Flatpak los contienen. Con pip, pipx o uv son dos paquetes de Python que `libera` requiere: `libera-core`, el motor de documentos, compilado para cada plataforma, y `libera-web`, los componentes de edición y las fuentes. Juntos suponen unos 90 MB de descarga. Después, la primera ejecución crea el índice de fuentes de tu máquina, lo que tarda un momento.

PyPI tiene `libera-core` para Windows x64, Linux x86_64 y macOS en Apple Silicon. En cualquier otra máquina, pip lo compila desde el código fuente, lo que lleva casi una hora y necesita las herramientas que enumera [Compilar los componentes](/en/develop/build/), en inglés.

Las versiones anteriores a la 0.7 descargaban sus componentes por separado, en las carpetas que aparecen más abajo. `libera --payload-remove` borra lo que dejaron allí.

## Dónde están los archivos

| | |
| :--- | :--- |
| Linux | `$XDG_DATA_HOME/libera/` o `~/.local/share/libera/` |
| Linux, Flatpak | `~/.var/app/eu.liberasuite.Libera/` |
| macOS | `~/Library/Application Support/Libera Suite/` |
| Windows | `%LOCALAPPDATA%\Libera Suite\` |

Ahí guarda Libera Suite lo que necesita entre una ejecución y otra, como la lista de documentos recientes y las sesiones sin guardar. Los componentes no están ahí: se instalan con la aplicación, y `libera --payload-status` indica dónde. Para usar componentes que están en otro sitio, por ejemplo una compilación local, pon su carpeta en `LIBERA_PAYLOAD`; prevalece sobre los instalados.

## Una entrada en el menú de aplicaciones de Linux {#a-launcher-entry-on-linux}

El script de instalación y el Flatpak añaden ambos Libera Suite al menú de aplicaciones. Tras cualquier otra instalación, este comando hace lo mismo, solo para tu cuenta: un icono, *Abrir con* y documentos que se abren con doble clic.

```sh
libera --launcher-install
libera --launcher-remove     # para quitarla
```

## Una aplicación que se abra con doble clic en macOS {#a-double-clickable-application-on-macos}

El script de instalación escribe una, `Libera.app`, en la carpeta Aplicaciones de tu carpeta de inicio. Después de cualquier otra instalación, como Homebrew, `pipx` o `uv tool`, este comando hace lo mismo:

```sh
libera --launcher-install
libera --launcher-remove     # para quitarla
```

Abre los documentos con doble clic y muestra el icono de Libera en el Dock. Es un pequeño lanzador para el Python de la instalación que la escribió: después de desinstalarla, o de pasarla a otro Python, vuelve a ejecutar `libera --launcher-install`.

A partir de una copia del código fuente, puedes compilar una para esa copia:

```sh
build/macos/macos-app.sh          # compila build/out/Libera.app
open build/out/Libera.app
```

Usa el Python de esa copia del código, así que depende de ella: déjala donde está; si la copia cambia de sitio, vuelve a compilarla. No está firmada: la primera vez, macOS dice **«no se puede abrir porque no se puede verificar el desarrollador»**. A partir de macOS 15, para seguir adelante, ve a *Ajustes del Sistema ▸ Privacidad y seguridad ▸ Abrir igualmente*.
