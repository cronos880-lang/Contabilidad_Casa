# V0.3.9 — Instalación base e histórico de fuentes

La instalación original de Windows se realizó con **Contabilidad Casa V0.3.9**. Esta carpeta de `main` es únicamente un **índice histórico**: contiene el proyecto Inno Setup, el script original de compilación y comprobaciones del ejecutable. No sustituye el código actual V0.3.13.

## Instalador V0.3.9 publicado

**[Release `V0.3.9-base`](https://github.com/cronos880-lang/Contabilidad_Casa/releases/tag/V0.3.9-base)**

- Nombre del archivo: `Instalar_Contabilidad_Casa_V0.3.9.exe`
- Tamaño: 17.117.337 bytes
- SHA-256: `c7b7aece9eb135e5c56cd9d0731c036e937f9f160425d4540edcc20fffb67aa0`
- Formato Inno Setup; firma digital ausente. Revisión estática satisfactoria, pero falta análisis antivirus en Windows antes de recomendar su distribución.

Consulta [INSTALADOR_BASE_SHA256.txt](INSTALADOR_BASE_SHA256.txt) para verificar la copia original.

## Código histórico

El archivo histórico original de V0.3.9 **sí se ha recuperado**: contiene `app/Contabilidad_Casa.py`, `app/perfiles.py`, `app/web/`, `app/Plantilla_Cuentas.xlsx`, el icono, el BAT de compilación y el proyecto `.iss`.

- SHA-256 del ZIP de origen: `9e93053b6bf920872d73a5f78198b519a2ca87496b73ff5bafbc697626ad5a64`
- SHA-256 del `.iss` original: `668a2f27c62a906a26b6f19a7f97ddce0b3652348f20d6d75bdc2b201cabbd4b`
- SHA-256 del BAT original: `43eb87254a9e14d5239a0e3be315b4fcc3d80bb6b2d1b4ce7760b1eb570c3175`

**Pendiente:** subir el contenido completo como rama Git independiente `historico/v0.3.9-fuentes`, para que no se mezcle con `main`.

## Etiqueta de la Release — corrección pendiente

La etiqueta **`V0.3.9-base` está mal situada**: hoy apunta a un commit de la V0.3.13. El botón `Source code (ZIP)` de la Release no es V0.3.9, aunque su EXE sí lo sea.

La corrección correcta, cuando se publique la rama histórica, consiste en mover esa etiqueta al commit con **las fuentes originales V0.3.9**, manteniendo la Release y su instalador. Para ello se ha preparado un paquete de Git para Windows con verificación previa del SHA antiguo y `--force-with-lease`, que impide sobrescribir un cambio ajeno de la etiqueta. Esta operación aún **no se ha ejecutado**.

No recompilar V0.3.9 con fuentes V0.3.13 ni renombrar un EXE posterior para resolver la discrepancia.

## Nota

Los scripts históricos pueden presentar errores con rutas largas en Windows. Se conservan por fidelidad histórica. No modificar ni reinstalar Contabilidad Casa para actualizar solo GitHub.
