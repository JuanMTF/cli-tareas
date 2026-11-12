@echo off
rem Ejecuta la bateria de pruebas de la CLI cliWork (doble clic y listo).
rem Vive en la carpeta pruebas\: sube a la raiz del proyecto para que
rem "uv run" encuentre el pyproject.toml.
rem Todo queda en ~/pruebas-tareas; con "solo-simular" no toca el disco.
rem Uso: ejecutartareas.bat [-i] [solo-simular]
rem   -i            interactivo: tras cada paso OK pregunta si ha salido
rem                 bien a la vista (tablas y ficheros); un "n" es un fallo.
rem   solo-simular  no ejecuta acciones reales (todo con --simular).

rem %~dp0 = carpeta de este .bat (...\pruebas\) -> padre = raiz del proyecto
cd /d "%~dp0.."
if errorlevel 1 exit /b 1

rem Se recogen los argumentos en cualquier orden: -i y solo-simular.
set "MODO="
set "SWITCHES="
:parse
if "%~1"=="" goto run
if /i "%~1"=="solo-simular" set "MODO=solo-simular"
if /i "%~1"=="-i" set "SWITCHES=%SWITCHES% -Interactivo"
if /i "%~1"=="interactivo" set "SWITCHES=%SWITCHES% -Interactivo"
shift
goto parse
:run
if "%MODO%"=="solo-simular" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "pruebas\pruebas.ps1" -SoloSimular%SWITCHES%
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "pruebas\pruebas.ps1"%SWITCHES%
)
echo.
pause
