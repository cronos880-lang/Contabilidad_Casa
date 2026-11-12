@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 exit /b 1
set "RAIZ=%CD%"
set "BUILD=%LOCALAPPDATA%\CCBuild313"
if not defined LOCALAPPDATA set "BUILD=%TEMP%\CCBuild313"
set "SALIDA=%RAIZ%\Salida_Portable_V0.3.13"
if exist "%SALIDA%\ContabilidadCasa" (
  echo ERROR: Ya existe una version compilada en "%SALIDA%".
  echo Mueve o renombra esa carpeta antes de compilar de nuevo.
  pause
  popd
  exit /b 1
)
if not exist "%BUILD%" mkdir "%BUILD%"
if errorlevel 1 goto FALLO
set "LOG=%BUILD%\COMPILACION_PORTABLE_V0.3.13.log"
> "%LOG%" echo Contabilidad Casa V0.3.13 - compilacion portable Windows

echo =================================================
echo CONTABILIDAD CASA V0.3.13 - PORTABLE WINDOWS
echo =================================================
echo Se compila usando una ruta corta: "%BUILD%"
echo.
set "PY_CMD="
where py.exe >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; assert sys.version_info >= (3,10)" >> "%LOG%" 2>&1
  if not errorlevel 1 set "PY_CMD=py -3"
)
if not defined PY_CMD (
  where python.exe >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; assert sys.version_info >= (3,10)" >> "%LOG%" 2>&1
    if not errorlevel 1 set "PY_CMD=python"
  )
)
if not defined PY_CMD goto FALLO
if not exist "%BUILD%\venv\Scripts\python.exe" (
  %PY_CMD% -m venv "%BUILD%\venv" >> "%LOG%" 2>&1
  if errorlevel 1 goto FALLO
)
set "PY=%BUILD%\venv\Scripts\python.exe"
if not exist "%PY%" goto FALLO
"%PY%" -m pip install --disable-pip-version-check "PyInstaller>=6.12,<7" "pywebview>=5,<7" >> "%LOG%" 2>&1
if errorlevel 1 goto FALLO
if not exist "%RAIZ%\web\app.js" goto FALLO
if not exist "%RAIZ%\Plantilla_Cuentas.xlsx" goto FALLO
if not exist "%RAIZ%\Contabilidad_Casa_Windows.py" goto FALLO
"%PY%" -m PyInstaller --noconfirm --clean --onedir --windowed --noupx ^
 --name "ContabilidadCasa" --icon "%RAIZ%\Contabilidad_Casa.ico" ^
 --distpath "%BUILD%\dist" --workpath "%BUILD%\work" --specpath "%BUILD%\spec" ^
 --paths "%RAIZ%" --add-data "%RAIZ%\web;web" --add-data "%RAIZ%\Plantilla_Cuentas.xlsx;." ^
 --collect-all webview --collect-all pythonnet --collect-all clr_loader ^
 --hidden-import clr --hidden-import tkinter --hidden-import tkinter.filedialog ^
 --hidden-import webview.platforms.winforms ^
 "%RAIZ%\Contabilidad_Casa_Windows.py" >> "%LOG%" 2>&1
if errorlevel 1 goto FALLO
if not exist "%BUILD%\dist\ContabilidadCasa\ContabilidadCasa.exe" goto FALLO
if not exist "%BUILD%\dist\ContabilidadCasa\_internal\web\app.js" goto FALLO
echo Copiando resultado a "%SALIDA%"...
robocopy "%BUILD%\dist\ContabilidadCasa" "%SALIDA%\ContabilidadCasa" /E /R:1 /W:1 >> "%LOG%" 2>&1
if errorlevel 8 goto FALLO
if not exist "%SALIDA%\ContabilidadCasa\ContabilidadCasa.exe" goto FALLO
echo.
echo COMPILACION COMPLETADA.
echo Ejecutable: "%SALIDA%\ContabilidadCasa\ContabilidadCasa.exe"
echo Este EXE portable NO es el instalador base V0.3.9.
echo Pruebalo en Windows antes de distribuirlo.
pause
popd
exit /b 0
:FALLO
echo.
echo ERROR: No se pudo generar la version portable.
echo Consulta el informe "%LOG%"
pause
popd
exit /b 1
