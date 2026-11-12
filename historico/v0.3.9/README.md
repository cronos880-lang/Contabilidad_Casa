# Contabilidad Casa V0.3.9 — fuente histórica del instalador

**Estado:** documento histórico de la **instalación base Windows**. La rama principal sigue en V0.3.13.

Se recuperaron los archivos de construcción V0.3.9 de un paquete generado anteriormente en la conversación. En este directorio se conservan los dos ficheros **originales** de configuración del instalador: el proyecto Inno Setup y el BAT de construcción (sin datos personales). El ZIP completo de fuentes recuperadas incluye también `Contabilidad_Casa.py`, `Contabilidad_Casa_Windows.py`, `perfiles.py`, `web/`, la plantilla vacía y el icono, pero **todavía no se ha incorporado ese ZIP completo a GitHub**.

**El instalador compilado `Instalar_Contabilidad_Casa_V0.3.9.exe` ya ha sido entregado por el usuario y verificado estáticamente.** Sus metadatos y SHA-256 se registran en [INSTALADOR_BASE_SHA256.txt](INSTALADOR_BASE_SHA256.txt). **El EXE no está todavía adjunto a ninguna Release de GitHub.** No debe confundirse con el antiguo instalador V0.3 ni con la herramienta para compilar el instalador.

Para mantener un histórico auténtico, no se reemplaza el código V0.3.9 por código V0.3.13 ni se etiqueta un EXE posterior como V0.3.9.

## Verificación de archivos recuperados
- Paquete fuente original: SHA-256 `9e93053b6bf920872d73a5f78198b519a2ca87496b73ff5bafbc697626ad5a64`.
- Copia ZIP de fuentes históricas empaquetada: SHA-256 `acb75aab3532ea44fcf616f1f74e0203e8a618e270cb4f9a1535e61607b8693e`.
- `Instalador_Contabilidad_Casa_V0.3.9.iss`: SHA-256 `668a2f27c62a906a26b6f19a7f97ddce0b3652348f20d6d75bdc2b201cabbd4b`.
- `CREAR_INSTALADOR_WINDOWS.bat`: SHA-256 `43eb87254a9e14d5239a0e3be315b4fcc3d80bb6b2d1b4ce7760b1eb570c3175`.

**Limitación:** el BAT histórico puede presentar problemas con rutas largas en Windows. Se conserva como referencia y no sustituye al script de compilación V0.3.13 que está en la raíz del repositorio. No se ha verificado la compilación final de V0.3.9 desde este entorno.

## Pendientes
1. Subir el ZIP de fuentes V0.3.9 a una publicación histórica o incorporar sus archivos al repositorio, sin datos personales.
2. Publicar el EXE original V0.3.9 (ya recibido) como asset de una Release, después de analizarlo con Microsoft Defender; consignar su SHA-256 documentado. Las herramientas de GitHub disponibles en esta sesión no admiten adjuntar archivos binarios a Releases.
