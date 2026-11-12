@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 (
  echo ERROR: No se puede abrir la carpeta donde has descomprimido el ZIP.
  pause
  exit /b 1
)

rem Carpeta Salida visible incluso si falla alguno de los pasos de compilacion.
if not exist "Salida" mkdir "Salida"
if not exist "Salida" (
  echo ERROR: No se puede crear la carpeta Salida. Comprueba los permisos.
  pause
  popd
  exit /b 1
)
set "LOG=%CD%\COMPILACION_V0.3.9.log"
set "RESULTADO=%CD%\Salida\Instalar_Contabilidad_Casa_V0.3.9.exe"
> "%LOG%" echo CONTABILIDAD CASA V0.3.9 - INFORME DE COMPILACION
>> "%LOG%" echo Carpeta: %CD%
>> "%LOG%" echo Fecha: %DATE% %TIME%

echo.
echo ============================================================
echo   CONTABILIDAD CASA V0.3.9 - COMPILACION CORREGIDA
echo ============================================================
echo.
echo Carpeta Salida creada: "%CD%\Salida"
echo Informe de compilacion: "%LOG%"
echo.

if not exist "app\Contabilidad_Casa_Windows.py" (
  set "MOTIVO=Faltan archivos. Debes descomprimir el ZIP COMPLETO."
  goto FALLO
)
if not exist "app\Plantilla_Cuentas.xlsx" (
  set "MOTIVO=No se encuentra la plantilla del programa."
  goto FALLO
)
if not exist "Instalador_Contabilidad_Casa_V0.3.9.iss" (
  set "MOTIVO=No se encuentra el proyecto de Inno Setup."
  goto FALLO
)

rem No dejar un instalador antiguo con el mismo nombre si la recompilacion falla.
if exist "%RESULTADO%" (
  del /f /q "%RESULTADO%" >nul 2>&1
  if exist "%RESULTADO%" (
    set "MOTIVO=No se puede reemplazar el EXE anterior. Cierra o mueve ese archivo."
    goto FALLO
  )
)

echo [1/4] Comprobando Python 3...
set "PY_CMD="
where py.exe >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; assert sys.version_info >= (3, 10), 'Se necesita Python 3.10 o posterior'" >> "%LOG%" 2>&1
  if not errorlevel 1 set "PY_CMD=py -3"
)
if not defined PY_CMD (
  where python.exe >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; assert sys.version_info >= (3, 10), 'Se necesita Python 3.10 o posterior'" >> "%LOG%" 2>&1
    if not errorlevel 1 set "PY_CMD=python"
  )
)
if not defined PY_CMD (
  set "MOTIVO=No se ha encontrado un Python 3.10 o posterior utilizable."
  goto FALLO
)
%PY_CMD% --version
%PY_CMD% --version >> "%LOG%" 2>&1

echo [2/4] Localizando Inno Setup...
set "ISCC="
for %%I in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" "%ProgramFiles%\Inno Setup 7\ISCC.exe") do (
  if exist "%%~fI" if not defined ISCC set "ISCC=%%~fI"
)
if not defined ISCC (
  for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%~fI"
)
if not defined ISCC (
  echo No encuentro ISCC.exe en las carpetas habituales.
  echo Abre Inno Setup y localiza ISCC.exe, o deja la ruta vacia para cancelar.
  set /p "ISCC=Ruta COMPLETA de ISCC.exe: "
)
if not exist "%ISCC%" (
  set "MOTIVO=No se ha encontrado ISCC.exe de Inno Setup."
  goto FALLO
)
echo Inno Setup encontrado: "%ISCC%"
>> "%LOG%" echo Inno Setup: "%ISCC%"

if not exist ".entorno_compilacion\Scripts\python.exe" (
  echo Creando entorno de compilacion...
  %PY_CMD% -m venv ".entorno_compilacion" >> "%LOG%" 2>&1
  if errorlevel 1 (
    set "MOTIVO=Fallo al crear el entorno de Python."
    goto FALLO
  )
)
set "PY=.entorno_compilacion\Scripts\python.exe"
if not exist "%PY%" (
  set "MOTIVO=No se encuentra Python dentro del entorno de compilacion."
  goto FALLO
)
echo Instalando/verificando PyInstaller y pywebview...
"%PY%" -m pip install --disable-pip-version-check --upgrade "PyInstaller>=6.12,<7" "pywebview>=5,<7" >> "%LOG%" 2>&1
if errorlevel 1 (
  set "MOTIVO=No se han podido instalar las dependencias. Revisa Internet, Python y el archivo de informe."
  goto FALLO
)

echo [3/4] Creando el programa de Windows...
"%PY%" -m PyInstaller --noconfirm --clean --onedir --windowed --noupx ^
  --name "ContabilidadCasa" ^
  --icon "Contabilidad_Casa.ico" ^
  --paths "app" ^
  --add-data "app\web;web" ^
  --add-data "app\Plantilla_Cuentas.xlsx;." ^
  --collect-all webview ^
  --collect-all pythonnet ^
  --collect-all clr_loader ^
  --hidden-import clr ^
  --hidden-import tkinter ^
  --hidden-import tkinter.filedialog ^
  --hidden-import webview.platforms.winforms ^
  "app\Contabilidad_Casa_Windows.py" >> "%LOG%" 2>&1
if errorlevel 1 (
  set "MOTIVO=PyInstaller no ha podido crear el programa."
  goto FALLO
)
if not exist "dist\ContabilidadCasa\ContabilidadCasa.exe" (
  set "MOTIVO=PyInstaller no ha generado dist\ContabilidadCasa\ContabilidadCasa.exe."
  goto FALLO
)

echo [4/4] Creando instalador con Inno Setup...
"%ISCC%" "Instalador_Contabilidad_Casa_V0.3.9.iss" >> "%LOG%" 2>&1
if errorlevel 1 (
  set "MOTIVO=Inno Setup ha encontrado un error."
  goto FALLO
)
if not exist "%RESULTADO%" (
  set "MOTIVO=Inno Setup termino, pero no encuentro el instalador esperado."
  goto FALLO
)

echo.
echo ============================================================
echo   INSTALADOR CREADO CORRECTAMENTE
echo ============================================================
echo.
echo Archivo: "%RESULTADO%"
echo.
echo Conserva tu copia ZIP de la contabilidad antes de instalar.
echo Puedes abrir Salida desde esta misma carpeta.
echo.
pause
popd
exit /b 0

:FALLO
echo.
echo ============================================================
echo   ERROR: NO SE HA CREADO EL INSTALADOR
echo ============================================================
echo.
echo %MOTIVO%
echo.
echo Carpeta Salida: "%CD%\Salida"
echo Informe: "%LOG%"
echo.
echo Si quieres que corrija el problema, enviame el archivo
echo COMPILACION_V0.3.9.log o una captura del error.
echo.
>> "%LOG%" echo.
>> "%LOG%" echo ERROR: %MOTIVO%
pause
popd
exit /b 1
