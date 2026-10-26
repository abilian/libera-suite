# Línea de comandos

Libera Suite se usa desde sus ventanas, pero un terminal llega a algunas cosas que ninguna ventana ofrece: convertir de una vez una carpeta entera de documentos, instalar los componentes en una máquina a la que se accede por SSH, preparar el informe que pide un error.

El comando es `libera`, en Linux y macOS. Instalado como Flatpak es `flatpak run eu.liberasuite.Libera`, seguido de las mismas opciones. En Windows es `libera-cli.exe`, en la carpeta donde se instaló Libera Suite; no está en el `PATH`.

## Abrir

| | |
| :--- | :--- |
| `libera` | la ventana de inicio: nuevo, abrir, recientes |
| `libera ARCHIVO...` | cada documento en su propia ventana; el archivo decide la aplicación. [Más](documents.md#open) |

## Convertir

| | |
| :--- | :--- |
| `libera --convert ARCHIVO... -t FORMATO` | cada documento escrito en `FORMATO`, junto al original, sin ventana. `FORMATO` es una extensión: `pdf`, `odt`, `docx`, `xlsx`, `csv`... |
| `-o ARCHIVO` | para un solo documento: el archivo que se escribe, con el formato que indica su extensión, salvo que `-t` diga otro. `-o -` escribe en la salida estándar |
| `--outdir CARPETA` | escribir en `CARPETA` en vez de junto a cada documento |

[Más, con ejemplos](documents.md#from-the-command-line).

## Los componentes

| | |
| :--- | :--- |
| `libera --payload-install` | descargar, comprobar e instalar los componentes. `--from CARPETA` los instala desde una carpeta. [Más](../main/alt-install.md#the-editors) |
| `libera --payload-status` | dónde están los componentes, su versión y el [código fuente](../licence.md#corresponding-source) del que se compilaron |
| `libera --payload-remove` | borrarlos. [Más](../main/install.md#uninstall) |

## El menú de aplicaciones y Abrir con

| | |
| :--- | :--- |
| `libera --launcher-install` | añadir Libera Suite a tus aplicaciones, con *Abrir con*: al menú de aplicaciones en Linux ([más](../main/alt-install.md#a-launcher-entry-on-linux)), como `Libera.app` en tu carpeta Aplicaciones en macOS ([más](../main/alt-install.md#a-double-clickable-application-on-macos)). |
| `libera --launcher-remove` | quitarlo de nuevo |

El Flatpak, el instalador de Windows y, en macOS, el script de instalación lo hacen por sí mismos.

## Si algo sale mal

| | |
| :--- | :--- |
| `libera --diagnose` | todo lo que necesita un informe de error, en una sola pantalla. [Más](../main/install.md#if-something-goes-wrong) |
| `libera --version` | la versión de la aplicación y la de los componentes |
| `-v`, `-vv`, `-vvv` | decir qué está haciendo; cómo; cada petición a los componentes |
| `-q` | solo errores |

`libera --help` enumera todas las opciones, y `libera --convert --help` las del conversor.
