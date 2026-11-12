@echo off
cd /d "%~dp0"
title Contabilidad Casa V0.3.8
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "Contabilidad_Casa.py"
  goto end
)
where python >nul 2>nul
if not errorlevel 1 (
  python "Contabilidad_Casa.py"
  goto end
)
echo.
echo No encuentro Python 3 en este ordenador.
echo Instala Python 3 para Windows desde https://www.python.org/downloads/
echo No se necesitan librerias adicionales.
pause
:end
