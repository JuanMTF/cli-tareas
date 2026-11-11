@echo off
rem Ejecuta la bateria de pruebas de la CLI cliWork (doble clic y listo).
rem Vive en la carpeta pruebas\: sube a la raiz del proyecto para que
rem "uv run" encuentre el pyproject.toml.
rem Todo queda en ~/pruebas-tareas; con "solo-simular" no toca el disco.
rem Uso: ejecutartareas.bat            (normal)
rem      ejecutartareas.bat solo-simular

rem %~dp0 = carpeta de este .bat (...\pruebas\) -> padre = raiz del proyecto
cd /d "%~dp0.."
if errorlevel 1 exit /b 1

if /i "%~1"=="solo-simular" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "pruebas\pruebas.ps1" -SoloSimular
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "pruebas\pruebas.ps1"
)
echo.
pause
