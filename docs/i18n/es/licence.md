# Licencia y atribución

## Dos licencias para dos componentes

| | |
| :--- | :--- |
| **La aplicación anfitriona**: el paquete `libera`, todo lo que hay en `src/libera/` | [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| **Los componentes**: Euro-Office con nuestra serie de parches | [AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html) |

Se empaquetan por separado y siguen separados. La aplicación anfitriona son unos cientos de kilobytes de Python y JavaScript en PyPI, como `libera`; los componentes son allí dos paquetes propios, `libera-core` y `libera-web`, de unos 100 MB en total, o el contenido de un paquete Flatpak. Nada de ellos está incluido en el paquete de Python de la aplicación anfitriona.

Ejecuta `libera --payload-status` para ver los componentes en uso y las revisiones del proyecto original a partir de las que se compilaron.

## A partir de qué está hecha

Libera Suite incluye componentes de [**Euro-Office**](https://github.com/Euro-Office), un fork bajo AGPL de **ONLYOFFICE**, desarrollado por Ascensio System SIA. Esos componentes están modificados; nuestros cambios forman la serie de parches que se describe más abajo. Los componentes de edición, el motor de documentos y la compatibilidad con los formatos son suyos; la aplicación anfitriona, el empaquetado y la integración con el escritorio son nuestros.

Estamos agradecidos a ambos. Lo más difícil de una suite ofimática son los veinte años aprendiendo a leer bien los archivos `.docx` de los demás. Esa parte la heredamos.

## Código fuente correspondiente {#corresponding-source}

Los componentes tienen licencia AGPL, que exige que puedas obtener el código fuente de lo que ejecutas, incluidas nuestras modificaciones.

Cada versión de Libera Suite escribe tres cosas en el manifiesto de sus componentes:

- la revisión exacta de cada repositorio del proyecto original a partir del que se compiló, fijada por el hash del commit;
- el commit de la propia Libera Suite;
- los repositorios de los que se pueden obtener ambos.

Nuestros cambios al proyecto original se guardan como una serie de parches sobre esas revisiones fijadas: la pregunta «¿qué ha cambiado Libera Suite?» tiene, por tanto, una respuesta breve y comprobable. Consulta [The patch queue](/en/develop/patches/), en inglés.

Remitimos a repositorios públicos; no distribuimos archivos comprimidos.
