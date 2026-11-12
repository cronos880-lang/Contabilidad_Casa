# Contabilidad Casa V0.3.13 — código fuente genérico

Esta es la **versión genérica de la aplicación Windows V0.3.13**, separada de las contabilidades reales del usuario. La aplicación permite crear perfiles, registrar gastos e ingresos, exportar/restaurar copias ZIP y mostrar resúmenes. Incluye el código Python, la interfaz web local, el icono y una plantilla XLSX **sin importes ni perfiles**.

## Contenido

- `Contabilidad_Casa.py`: servidor local y operaciones de contabilidad.
- `Contabilidad_Casa_Windows.py`: ventana Windows con WebView2 (pywebview).
- `perfiles.py`: creación, exportación, restauración y selección de contabilidades.
- `web/`: interfaz HTML, CSS y JavaScript.
- `Plantilla_Cuentas.xlsx`: plantilla vacía de 2026 y 2027, con nombres genéricos.
- `Contabilidad_Casa.ico`: icono.
- `COMPILAR_PORTABLE_WINDOWS.bat`: construcción local de una versión portable para Windows.

## Ejecutar desde el código

Instala Python 3.10 o posterior. Desde la carpeta del proyecto:

```console
python Contabilidad_Casa.py
```

La versión en navegador abre un servidor local y no exige dependencias externas. Para la versión de escritorio Windows se necesita WebView2 y la dependencia `pywebview`. Si vas a compilar el portable Windows, ejecuta el BAT incluido; instalará PyInstaller y pywebview en un entorno virtual separado.

## Datos de cada usuario

La primera ejecución parte **sin contabilidades precreadas** y crea perfiles cuando el usuario lo decide. Por defecto los perfiles se registran en la carpeta de configuración de la aplicación en el perfil de Windows y cada contabilidad se guarda aparte en la carpeta elegida por el usuario. Los datos pueden restaurarse desde una copia ZIP generada por la aplicación.

**No subas a GitHub:** `Cuentas.xlsx` con movimientos, `Gastos_detallados.json`, `perfiles.json`, perfiles reales, carpetas de datos ni copias de seguridad. `.gitignore` ayuda a excluirlos, pero no sustituye una revisión antes de hacer `git add`.

La plantilla distribuida en este proyecto no contiene datos económicos, y los ingresos y cuentas figuran con nombres genéricos. Se han cambiado las referencias internas a personas concretas por nombres neutros **sin alterar la lógica del programa**.

## Estado de distribución

La V0.3.13 está publicada como **código fuente**, pero aún no se ha confirmado una compilación e instalación final satisfactoria en Windows. **No se ha validado todavía un instalador completo V0.3.13 construido desde cero.** El script portable es una ayuda de compilación, no un instalador Inno Setup y no debe confundirse con una Release definitiva.

El código de Suite CAD V0.4 es independiente y no está incluido aquí.


## Cambios de V0.3.13 (12/11/2026)

- Nueva pestaña **Gráfica mensual**: gráfico de anillo por **categoría individual**, no solo por grupo.
- Selección de año/mes, incluye categorías originales y personalizadas activas con gasto, importes y porcentajes.
- No duplica anotaciones: toma los totales de Gastos del mes; muestra aviso si hay ajustes negativos.
- **Gráficas anuales** sin cambios en su agrupación original.
- **Instalación base V0.3.9** (Inno Setup): el actualizador lleva directamente la versión que se esté ejecutando, por ejemplo V0.3.10, a **V0.3.13** sin pasar por las versiones de prueba V0.3.11/12. **No** copiar solo archivos Python al programa PyInstaller.
- El repositorio contiene fuentes y plantilla sin datos personales; no incluye historiales de compras, Excel reales ni copias de seguridad.
- La compilación del EXE debe ejecutarse y verificarse en Windows.

## Ejecutables, instalador base y actualizaciones

Consulta [Estado de los ejecutables Windows](docs/ESTADO_EJECUTABLES_WINDOWS.md). **El instalador V0.3.9 no está publicado en este repositorio ni en una Release**. La V0.3.9 es la instalación histórica de Windows, sobre la que se aplican las actualizaciones. El script `COMPILAR_PORTABLE_WINDOWS.bat` compila el programa *actual* V0.3.13, **no** recupera el ejecutable original V0.3.9. Para evitar el error de rutas largas de Windows, el entorno de compilación se crea bajo `%LOCALAPPDATA%\CCBuild313`.
