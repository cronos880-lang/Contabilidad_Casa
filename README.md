# Contabilidad Casa — fuentes originales V0.3.9

**Archivo histórico independiente**. Esta rama se crea a partir del paquete original usado para compilar el instalador V0.3.9 de Windows. Se han anonimizado únicamente referencias personales en cuatro líneas de documentación/comentarios del archivo `app/Contabilidad_Casa.py`; no se ha cambiado su lógica. No es la versión actual del programa.

## Instalador base

El instalador se conserva como asset de la [Release V0.3.9-base](https://github.com/cronos880-lang/Contabilidad_Casa/releases/tag/V0.3.9-base):

- `Instalar_Contabilidad_Casa_V0.3.9.exe`
- SHA-256 del EXE: `c7b7aece9eb135e5c56cd9d0731c036e937f9f160425d4540edcc20fffb67aa0`
- Tamaño: 17.117.337 bytes
- EXE sin firma digital; comprobar con Defender antes de instalar o distribuir.

## Fuentes históricas

`app/` contiene Python y HTML/CSS/JS de V0.3.9, más `Plantilla_Cuentas.xlsx`, sin datos personales. En la raíz se encuentra el proyecto `Instalador_Contabilidad_Casa_V0.3.9.iss` (Inno Setup), el script de compilación original y el icono. Se conservan como referencia histórica, **sin actualizar funciones ni lógica** ni prometer compatibilidad con compiladores de versiones posteriores.

Archivo ZIP fuente del que se ha recuperado el contenido:

- `Contabilidad_Casa_V0.3.9_Instalador_WINDOWS_COMPILACION_CORREGIDA.zip`
- SHA-256: `9e93053b6bf920872d73a5f78198b519a2ca87496b73ff5bafbc697626ad5a64`

## Relación con la versión actual

- **Instalación base Windows:** V0.3.9.
- **Código actual en `main`:** V0.3.13 (al crear este archivo histórico).
- Las actualizaciones del programa pueden instalarse sobre la instalación original, sin reinstalar y manteniendo sus contabilidades.
- **No utilizar** estas fuentes V0.3.9 para sustituir el código actual ni los datos del usuario.

## Privacidad

No se publican `Cuentas.xlsx` con movimientos, `Gastos_detallados.json`, `perfiles.json`, perfiles activos o copias de seguridad. Los nombres que puedan aparecer en comentarios históricos no deben interpretarse como datos financieros personales: la plantilla está vacía. En caso de reutilizar el código, conviene modernizar y anonimizar los comentarios fuera de esta rama de archivo.
