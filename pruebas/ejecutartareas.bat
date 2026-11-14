@echo off
rem Ejecuta la bateria de pruebas de la CLI cliWork (doble clic y listo).
rem Vive en la carpeta pruebas\: sube a la raiz del proyecto para que
rem "uv run" encuentre el pyproject.toml.
rem Todo queda en ~/pruebas-tareas; con "solo-simular" no toca el disco.
rem Uso: ejecutartareas.bat [-i] [solo-simular|ia|resumir|validar]
rem   -i            interactivo: tras cada paso OK pregunta si ha salido
rem                 bien a la vista (tablas y ficheros); un "n" es un fallo.
rem   solo-simular  la bateria no ejecuta acciones reales (todo con --simular).
rem   ia            prueba las 4 acciones IA con --simular (no llama al modelo).
rem   resumir       ejecuta resumir-apuntes de verdad (hace falta .env).
rem   validar       solo comprueba acciones.json.
rem   Sin argumentos: menu para elegir sin teclear.

rem %~dp0 = carpeta de este .bat (...\pruebas\) -> padre = raiz del proyecto
cd /d "%~dp0.."
if errorlevel 1 exit /b 1

rem Se recogen los argumentos en cualquier orden.
set "MODO="
set "SWITCHES="
:parse
if "%~1"=="" goto run
if /i "%~1"=="solo-simular" set "MODO=solo-simular"
if /i "%~1"=="-i" set "SWITCHES=%SWITCHES% -Interactivo"
if /i "%~1"=="interactivo" set "SWITCHES=%SWITCHES% -Interactivo"
if /i "%~1"=="ia" set "MODO=ia"
if /i "%~1"=="ia-real" set "MODO=ia-real"
if /i "%~1"=="resumir" set "MODO=resumir"
if /i "%~1"=="validar" set "MODO=validar"
shift
goto parse

:run
if not "%MODO%"=="" goto %MODO%

rem Sin argumentos: menu con la bateria y las acciones IA.
echo.
echo  cliWork - pruebas y acciones IA
echo  -------------------------------
echo   1) Bateria completa (pytest + acciones reales solo en el sandbox)
echo   2) Bateria solo con --simular (no toca nada)
echo   3) Acciones IA con --simular (cuenta caracteres, no gasta tokens)
echo   4) resumir-apuntes real (llama al modelo: hace falta .env)
echo   5) Solo validar acciones.json
echo   6) Las 3 acciones IA reales (limpiar-ocr, renombrar y clasificar)
choice /c 123456 /n /m "Opcion: "
if errorlevel 6 goto ia-real
if errorlevel 5 goto validar
if errorlevel 4 goto resumir
if errorlevel 3 goto ia
if errorlevel 2 goto solo-simular
goto bateria

:solo-simular
powershell -NoProfile -ExecutionPolicy Bypass -File "pruebas\pruebas.ps1" -SoloSimular%SWITCHES%
goto fin

:bateria
powershell -NoProfile -ExecutionPolicy Bypass -File "pruebas\pruebas.ps1"%SWITCHES%
goto fin

:ia
echo.
rem Carpeta con los ficheros de prueba (Enter = la de siempre, en ~/pruebas-tareas)
set "CARPETA="
set /p CARPETA="Carpeta de origen (Enter = %USERPROFILE%\pruebas-tareas\Apuntes): "
if not defined CARPETA set "CARPETA=%USERPROFILE%\pruebas-tareas\Apuntes"
if "%CARPETA: =%"=="" set "CARPETA=%USERPROFILE%\pruebas-tareas\Apuntes"
rem Solo si se usa la carpeta por defecto (del sandbox) se crea si no existe.
if /i "%CARPETA%"=="%USERPROFILE%\pruebas-tareas\Apuntes" if not exist "%CARPETA%" mkdir "%CARPETA%"
echo.
echo --- Acciones IA en simulacion (no se llama al modelo) ---
echo Carpeta: %CARPETA%
echo.
uv run cliWork ejecutar resumir-apuntes "%CARPETA%" --simular
uv run cliWork ejecutar limpiar-ocr "%CARPETA%" --simular
uv run cliWork ejecutar renombrar-descriptivo "%CARPETA%" --simular
uv run cliWork ejecutar clasificar-descargas "%CARPETA%" --simular
goto fin

:resumir
echo.
rem Carpeta con los apuntes a resumir (Enter = la de siempre, en ~/pruebas-tareas)
set "CARPETA="
set /p CARPETA="Carpeta de origen (Enter = %USERPROFILE%\pruebas-tareas\Apuntes): "
if not defined CARPETA set "CARPETA=%USERPROFILE%\pruebas-tareas\Apuntes"
if "%CARPETA: =%"=="" set "CARPETA=%USERPROFILE%\pruebas-tareas\Apuntes"
rem Solo si se usa la carpeta por defecto (del sandbox) se crea si no existe.
if /i "%CARPETA%"=="%USERPROFILE%\pruebas-tareas\Apuntes" if not exist "%CARPETA%" mkdir "%CARPETA%"
echo.
echo --- resumir-apuntes real (lee el .env; el resumen queda en ~/pruebas-tareas\Resumenes) ---
echo Carpeta: %CARPETA%
echo.
uv run cliWork ejecutar resumir-apuntes "%CARPETA%"
goto fin

:ia-real
echo.
rem Carpeta con los ficheros de prueba (Enter = la de siempre, en ~/pruebas-tareas)
set "CARPETA="
set /p CARPETA="Carpeta de origen (Enter = %USERPROFILE%\pruebas-tareas\Apuntes): "
if not defined CARPETA set "CARPETA=%USERPROFILE%\pruebas-tareas\Apuntes"
if "%CARPETA: =%"=="" set "CARPETA=%USERPROFILE%\pruebas-tareas\Apuntes"
rem Solo si se usa la carpeta por defecto (del sandbox) se crea si no existe.
if /i "%CARPETA%"=="%USERPROFILE%\pruebas-tareas\Apuntes" if not exist "%CARPETA%" mkdir "%CARPETA%"
echo.
echo --- Las 3 acciones IA reales (leen el .env) ---
echo Carpeta: %CARPETA%
echo Resultados en: TextoLimpio (limpiar-ocr), NombresIA (renombrar-descriptivo)
echo                y ClasificacionIA (clasificar-descargas), en ~/pruebas-tareas
echo.
uv run cliWork ejecutar limpiar-ocr "%CARPETA%"
uv run cliWork ejecutar renombrar-descriptivo "%CARPETA%"
uv run cliWork ejecutar clasificar-descargas "%CARPETA%"
goto fin

:validar
echo.
uv run cliWork validar
goto fin

:fin
echo.
pause
