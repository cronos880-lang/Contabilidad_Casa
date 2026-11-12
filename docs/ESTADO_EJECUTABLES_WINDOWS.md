# Estado de ejecutables de Contabilidad Casa en Windows

Actualizado: 12/11/2026.

## Resultado de la comprobación

- **Rama principal:** `main`, código fuente de **V0.3.13**.
- **Ejecutable / instalador original V0.3.9:** **NO está en la rama principal**.
- **Releases de GitHub:** **no hay Releases publicadas**, por lo que tampoco hay instalador V0.3.9 en Assets.
- El archivo `.gitignore` excluye `*.exe` para que los ejecutables generados no entren en el código fuente por accidente.
- El repositorio sí incluye `COMPILAR_PORTABLE_WINDOWS.bat`, pero genera una **versión portable V0.3.13** a partir de las fuentes actuales, no el instalador base V0.3.9 de Inno Setup.

## Instalación base y actualizaciones

La instalación histórica en Windows se hizo con el instalador **V0.3.9**, creando icono, acceso directo y desinstalador. Las versiones posteriores se aplican sobre esa instalación, sin desinstalarla. Que Windows siga mostrando V0.3.9 en *Aplicaciones instaladas* es normal: es la versión del instalador original. La aplicación muestra su versión real (por ejemplo, V0.3.10 o V0.3.13) en la cabecera.

La actualización V0.3.13 debe sustituir el ejecutable y la carpeta `_internal`, conservando las carpetas de contabilidades del usuario. Nunca distribuir `Cuentas.xlsx` real, `Gastos_detallados.json` ni respaldos personales.

## Cómo publicar el ejecutable V0.3.9 original

1. Localizar en el ordenador donde se compiló el archivo **`Instalar_Contabilidad_Casa_V0.3.9.exe`** (instalador Inno Setup) o identificar inequívocamente el **`ContabilidadCasa.exe`** de esa versión. Son archivos distintos: el segundo no sirve por sí solo como instalador.
2. Comprobar que es el archivo original correcto, ejecutarlo en un Windows de prueba y analizarlo con Microsoft Defender. Si hay una detección de seguridad, no distribuirlo sin resolverla.
3. Obtener su SHA-256 en PowerShell, por ejemplo `Get-FileHash -Algorithm SHA256 -Path '.\\Instalar_Contabilidad_Casa_V0.3.9.exe'`.
4. En GitHub, crear una **Release** con etiqueta `v0.3.9` y adjuntar el instalador revisado en **Assets**; registrar la suma SHA-256 en la descripción. Publicar la Release solo cuando se haya verificado.

**No se debe reconstruir un instalador V0.3.9 con código V0.3.13 ni renombrar un archivo posterior**: eso falsearía la versión y puede perjudicar a futuras actualizaciones.

## Compilación portable actual

Ejecutar `COMPILAR_PORTABLE_WINDOWS.bat` en Windows con Python 3.10+; utilizará una ruta corta bajo `%LOCALAPPDATA%\\CCBuild313` para evitar los fallos de longitud de ruta de `pip`/PyInstaller. El EXE resultante debe validarse en Windows antes de distribuirlo. El script no crea un instalador Inno Setup ni publica una Release.

## Fuentes históricas recuperadas (12/11/2026)

Se han añadido a [`historico/v0.3.9/`](../historico/v0.3.9/) los archivos `.iss` y `CREAR_INSTALADOR_WINDOWS.bat` originales, más un manifiesto del paquete de fuentes V0.3.9 disponible para descargar en la conversación. **Estos ficheros no son el EXE compilado**. El código completo histórico sigue pendiente de incorporarse a GitHub; no está en el historial anterior de `main` (que comienza con V0.3.11). No hay Release de V0.3.9. Para publicarla habrá que encontrar el EXE original en el PC de compilación, verificarlo y adjuntarlo manualmente como asset de Release, porque el acceso actual a GitHub no permite subir archivos binarios a Releases.

## Comprobación de archivo original recibido (12/11/2026)

Se recibió `Instalar_Contabilidad_Casa_V0.3.9.exe` (17.117.337 bytes). El archivo presenta estructura de Inno Setup 6.7.0 y metadatos de versión 0.3.9. SHA-256: `c7b7aece9eb135e5c56cd9d0731c036e937f9f160425d4540edcc20fffb67aa0`. No se encontró firma Authenticode; la revisión estática **no sustituye** un análisis antivirus ni la validación en Windows. El checksum está publicado en [historico/v0.3.9/INSTALADOR_BASE_SHA256.txt](../historico/v0.3.9/INSTALADOR_BASE_SHA256.txt). **El archivo ejecutable aún no se ha adjuntado a una Release**: el conector GitHub disponible no admite la subida de binarios a Assets.
