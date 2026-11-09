@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 exit /b 1
if not exist "Salida_Portable" mkdir "Salida_Portable"
set "LOG=%CD%\COMPILACION_PORTABLE_V0.3.11.log"
> "%LOG%" echo Contabilidad Casa V0.3.11 - compilacion portable Windows

echo Contabilidad Casa V0.3.11 - version portable Windows
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
if not exist ".compilacion_portable\Scripts\python.exe" (
  %PY_CMD% -m venv ".compilacion_portable" >> "%LOG%" 2>&1
  if errorlevel 1 goto FALLO
)
set "PY=.compilacion_portable\Scripts\python.exe"
"%PY%" -m pip install --disable-pip-version-check "PyInstaller>=6.12,<7" "pywebview>=5,<7" >> "%LOG%" 2>&1
if errorlevel 1 goto FALLO
set "RAIZ=%CD%"
"%PY%" -m PyInstaller --noconfirm --clean --onedir --windowed --noupx ^
 --name "ContabilidadCasa" --icon "%RAIZ%\Contabilidad_Casa.ico" ^
 --distpath "%RAIZ%\Salida_Portable" --workpath "%RAIZ%\.compilacion_portable\build" --specpath "%RAIZ%\.compilacion_portable" ^
 --paths "%RAIZ%" --add-data "%RAIZ%\web;web" --add-data "%RAIZ%\Plantilla_Cuentas.xlsx;." ^
 --collect-all webview --collect-all pythonnet --collect-all clr_loader ^
 --hidden-import clr --hidden-import tkinter --hidden-import tkinter.filedialog ^
 --hidden-import webview.platforms.winforms ^
 "%RAIZ%\Contabilidad_Casa_Windows.py" >> "%LOG%" 2>&1
if errorlevel 1 goto FALLO
if not exist "Salida_Portable\ContabilidadCasa\ContabilidadCasa.exe" goto FALLO
if not exist "Salida_Portable\ContabilidadCasa\_internal\web\app.js" goto FALLO
echo.
echo EXITO. Ejecutable: Salida_Portable\ContabilidadCasa\ContabilidadCasa.exe
pause
popd
exit /b 0
:FALLO
echo ERROR. Consulta el archivo COMPILACION_PORTABLE_V0.3.11.log
pause
popd
exit /b 1
