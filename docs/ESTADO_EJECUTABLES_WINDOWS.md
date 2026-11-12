# Estado real de versiones y ejecutables Windows

Actualizado el 12/11/2026.

| Elemento | Estado |
|---|---|
| Código fuente actual V0.3.13 | **Disponible en `main`** |
| EXE instalador base V0.3.9 | **Publicado** en la [Release V0.3.9-base](https://github.com/cronos880-lang/Contabilidad_Casa/releases/tag/V0.3.9-base) |
| Integridad del EXE | **Coincide el SHA-256**: `c7b7aece9eb135e5c56cd9d0731c036e937f9f160425d4540edcc20fffb67aa0` |
| Fuentes originales V0.3.9 | **Recuperadas del ZIP histórico; aún no todas publicadas** |
| Rama histórica independiente | Pendiente de subir |
| Etiqueta `V0.3.9-base` | **Pendiente de corregir**: apunta a código V0.3.13 |
| Compilación actual V0.3.13 en Windows | Usa ruta corta bajo `%LOCALAPPDATA%\\CCBuild313`; verificar en Windows |

## Separación correcta

- `main` conserva el desarrollo actual **V0.3.13**.
- La futura rama `historico/v0.3.9-fuentes` conservará las fuentes **auténticas V0.3.9** en una historia independiente.
- La etiqueta `V0.3.9-base` debe apuntar al commit de esa rama histórica. Su Release conserva el EXE original, ya publicado.
- El programa instalado en Windows se mantiene independiente de esta reorganización de GitHub. No hay que reinstalarlo ni tocar los datos.

El EXE no tiene firma digital. Comprobar con Microsoft Defender antes de recomendarlo a otros usuarios. La comprobación de SHA garantiza identidad de bytes, no ausencia de malware.

## Archivos históricos de referencia

[Índice `historico/v0.3.9/`](../historico/v0.3.9/). Se han recuperado fuentes Python, JS, CSS, HTML, plantilla vacía, icono y scripts originales. No se han publicado archivos económicos reales, `Cuentas.xlsx` con importes, `Gastos_detallados.json`, perfiles o ZIP de copias de seguridad.

**La corrección de la etiqueta aún no se ha aplicado**; debe realizarse después de subir los archivos originales a una rama, mediante un Git autenticado con acceso al repositorio.
