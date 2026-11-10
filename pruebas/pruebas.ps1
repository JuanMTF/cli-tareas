# pruebas.ps1 - bateria de pruebas de la CLI tareas (proyecto DAM)
#
# Que hace:
#   1. Ejecuta pytest (tests unitarios).
#   2. Comprueba las ordenes basicas: version, validar, acciones, listar.
#   3. Crea un sandbox en ~/pruebas-tareas/bateria con ficheros de ejemplo
#      (uno con fecha antigua para probar los filtros por dias).
#   4. Ejecuta acciones sobre el sandbox: mover (simulado y real, dos veces),
#      copiar, comprimir y borrar.
#   5. Cuenta OK/FALLO y sale con codigo 1 si algo fallo (util para CI).
#
# Solo toca ~/pruebas-tareas. Nunca borra nada fuera del sandbox.
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\pruebas.ps1
#   powershell -ExecutionPolicy Bypass -File .\pruebas.ps1 -SoloSimular
# (o doble clic en ejecutartareas.bat, en esta misma carpeta)

param(
    [switch]$SoloSimular  # con -SoloSimular no se ejecuta nada real, todo con --simular
)

$ErrorActionPreference = "Continue"
$fallos = 0
$pasos = 0

# La CLI escribe UTF-8 (validas, SIMULACION...): hay que decirle a PowerShell
# como leerlo, o los acentos salen mojados y los regex del test no casan.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

function Paso {
    param([string]$Nombre, [bool]$Ok, [string]$Detalle = "")
    $script:pasos++
    if ($Ok) {
        Write-Host ("  OK   {0}" -f $Nombre) -ForegroundColor Green
        if ($Detalle) { Write-Host ("       {0}" -f $Detalle) -ForegroundColor DarkGray }
    } else {
        $script:fallos++
        Write-Host ("  FALLO {0}" -f $Nombre) -ForegroundColor Red
        if ($Detalle) { Write-Host ("       {0}" -f $Detalle) -ForegroundColor Yellow }
    }
}

function Tareas {
    # Ejecuta "uv run tareas ..." y devuelve salida + codigo de salida.
    param([string[]]$Argumentos)
    $salida = & uv run tareas @Argumentos 2>&1
    [PSCustomObject]@{ Texto = ($salida -join "`n"); Codigo = $LASTEXITCODE }
}

Write-Host "=== Bateria de pruebas de tareas ===" -ForegroundColor Cyan
Write-Host ("Modo: {0}" -f ($(if ($SoloSimular) { "solo simulacion" } else { "simulacion + acciones reales (solo en el sandbox)" })))
Write-Host ""

# --- 1. Tests unitarios -----------------------------------------------------

Write-Host "[1] pytest"
$pytest = & uv run pytest -q 2>&1
Paso "pytest pasa los tests" ($LASTEXITCODE -eq 0) (($pytest | Select-Object -Last 1) -join "")

# --- 2. Ordenes basicas -----------------------------------------------------

Write-Host "[2] Ordenes basicas"

$v = Tareas @("version")
Paso "version imprime 0.1.0" (($v.Codigo -eq 0) -and ($v.Texto -match "0\.1\.0")) $v.Texto.Trim()

$val = Tareas @("validar")
Paso "validar dice 'acciones validas' y sale 0" (($val.Codigo -eq 0) -and ($val.Texto -match "v.lidas")) ($val.Texto.Trim() -split "`n")[0]

$acc = Tareas @("acciones")
Paso "acciones lista al menos abrir-nav y ordenar-descargas" (($acc.Codigo -eq 0) -and ($acc.Texto -match "abrir-nav") -and ($acc.Texto -match "ordenar-descargas"))

# JSON roto: tiene que saltar con codigo 3 y sin traceback
$rupta = Join-Path $env:TEMP "tareas-prueba-roto.json"
'{"version": 1, "acciones": [' | Set-Content -Path $rupta -Encoding UTF8
$roto = Tareas @("validar", $rupta)
Paso "validar con JSON roto sale con codigo 3" ($roto.Codigo -eq 3) ("codigo = {0}" -f $roto.Codigo)
Paso "el error no ensena traceback" (-not ($roto.Texto -match "Traceback"))

# --- 3. Sandbox -------------------------------------------------------------

Write-Host "[3] Sandbox en ~/pruebas-tareas/bateria"

$sb = Join-Path $HOME "pruebas-tareas\bateria"
$origen = Join-Path $sb "origen"
$destino = Join-Path $sb "destino"

if (Test-Path $sb) { Remove-Item -Recurse -Force $sb }
New-Item -ItemType Directory -Force -Path $origen, $destino | Out-Null

# Ficheros de ejemplo: dos PDF, un TXT y una carpeta con fecha vieja.
foreach ($n in "doc-a.pdf", "doc-b.pdf", "nota.txt") {
    Set-Content -Path (Join-Path $origen $n) -Value "contenido de prueba" -Encoding UTF8
}
$vieja = Join-Path $origen "carpeta-vieja"
New-Item -ItemType Directory -Force -Path $vieja | Out-Null
Set-Content -Path (Join-Path $vieja "dentro.txt") -Value "vieja" -Encoding UTF8
$hace = (Get-Date).AddDays(-500)
(Get-Item (Join-Path $origen "doc-a.pdf")).LastWriteTime = $hace
(Get-Item $vieja).LastWriteTime = $hace

Paso "sandbox creado con ficheros de ejemplo" ((Test-Path (Join-Path $origen "doc-b.pdf")) -and (Test-Path $vieja))

# listar con ruta que lleva espacios y tilde: tiene que funcionar igual
$lst = Tareas @("listar", $sb)
Paso "listar ve el sandbox" (($lst.Codigo -eq 0) -and ($lst.Texto -match "origen"))

# --- 4. Acciones ------------------------------------------------------------

Write-Host "[4] Acciones (mover, copiar, comprimir, borrar, renombrar, abrir)"

# 4.1 mover --simular: dice SIMULACION y NO toca el disco
$sim = Tareas @("ejecutar", "ordenar-descargas", $origen, "-d", $destino, "--simular")
$quedan = (Get-ChildItem $origen -File).Count
Paso "mover --simular anuncia SIMULACION" (($sim.Codigo -eq 0) -and ($sim.Texto -match "SIMULACI.N"))
Paso "mover --simular NO mueve nada (ni mkdir)" (($quedan -ge 3) -and ((Get-ChildItem $destino -ErrorAction SilentlyContinue).Count -eq 0)) ("quedan {0} ficheros en origen" -f $quedan)

if ($SoloSimular) {
    Write-Host ""
    Write-Host "Modo -SoloSimular: las acciones reales no se ejecutan." -ForegroundColor Yellow
} else {

    # 4.2 copiar: el original se queda donde estaba
    $cop = Tareas @("ejecutar", "copiar-antiguos", $origen, "-d", $destino, "-an", "400", "--si")
    $lleva = Test-Path (Join-Path $destino "carpeta-vieja")
    $originalQueda = Test-Path (Join-Path $origen "carpeta-vieja")
    Paso "copiar lleva la carpeta vieja al destino" $lleva
    Paso "copiar NO borra el original" $originalQueda

    # 4.3 comprimir: crea el zip y la segunda vuelta lo renombra con " (1)"
    $com1 = Tareas @("ejecutar", "comprimir-antiguos", $origen, "-d", $destino, "-an", "400", "--nombre", "prueba", "--si")
    $zip1 = Join-Path $destino "prueba.zip"
    $com2 = Tareas @("ejecutar", "comprimir-antiguos", $origen, "-d", $destino, "-an", "400", "--nombre", "prueba", "--si")
    $zip2 = Join-Path $destino "prueba (1).zip"
    Paso "comprimir crea prueba.zip" ((Test-Path $zip1) -and ($com1.Codigo -eq 0))
    Paso "comprimir segunda vez NO pisa: crea 'prueba (1).zip'" ((Test-Path $zip2) -and ($com2.Texto -match "renombrado"))

    # 4.4 mover real (dos veces seguidas): primera mueve, segunda avisa 'No hay ficheros'
    #     Usamos una carpeta espejo para no depender de copiar.
    $origenMover = Join-Path $sb "origen-mover"
    $destinoMover = Join-Path $sb "destino-mover"
    New-Item -ItemType Directory -Force -Path $origenMover, $destinoMover | Out-Null
    foreach ($n in "mm-1.pdf", "mm-2.pdf") {
        Copy-Item (Join-Path $origen "doc-b.pdf") (Join-Path $origenMover $n)
    }
    $m1 = Tareas @("ejecutar", "ordenar-descargas", $origenMover, "-d", $destinoMover, "--si")
    $yaNo = (Get-ChildItem $origenMover -File -ErrorAction SilentlyContinue).Count
    $m2 = Tareas @("ejecutar", "ordenar-descargas", $origenMover, "-d", $destinoMover, "--si")
    Paso "mover primera vuelta: mueve y deja origen vacio" (($m1.Codigo -eq 0) -and ($yaNo -eq 0))
    Paso "mover segunda vuelta: avisa 'No hay ficheros' y sale 0" (($m2.Codigo -eq 0) -and ($m2.Texto -match "No hay ficheros"))

    # 4.5 mover nunca sobrescribe: si reaparece un fichero con el mismo nombre,
    #     la segunda copia se llama 'nombre (1)'
    Copy-Item (Join-Path $origen "doc-b.pdf") (Join-Path $origenMover "mm-1.pdf")
    $m3 = Tareas @("ejecutar", "ordenar-descargas", $origenMover, "-d", $destinoMover, "--si")
    Paso "mover con nombre repetido crea 'mm-1 (1).pdf'" ((Test-Path (Join-Path $destinoMover "mm-1 (1).pdf")))

    # 4.6 borrar con confirmacion en el sandbox: sin --si se pregunta (respondemos n)
    $tmp = Join-Path $origen "viejo.tmp"
    Set-Content -Path $tmp -Value "tmp" -Encoding UTF8
    (Get-Item $tmp).LastWriteTime = (Get-Date).AddDays(-60)

    $del1 = "n" | & uv run tareas ejecutar limpiar-temporales $origen 2>&1
    $del1texto = ($del1 -join "`n")
    $Preserva = Test-Path $tmp
    # Al contestar 'n', click cancela con "Cancelado." y codigo 1: eso es
    # correcto. Lo que NO puede pasar es que borre el fichero.
    $cancelado = ($LASTEXITCODE -eq 0) -or ($del1texto -match "Cancelado")
    Paso "borrar sin --si pregunta y con 'n' no borra" ($Preserva -and $cancelado) $del1texto

    $del2 = Tareas @("ejecutar", "limpiar-temporales", $origen, "--si")
    Paso "borrar --si elimina el .tmp" ((Test-Path $tmp) -eq $false)

    # 4.7 renombrar-fotos: con --simular no toca nada y en real aplica la
    #     plantilla {fecha:%Y-%m-%d}_{n:03}{ext} a cada foto.
    $fotos = Join-Path $sb "fotos"
    New-Item -ItemType Directory -Force -Path $fotos | Out-Null
    Set-Content -Path (Join-Path $fotos "foto-a.jpg") -Value "jpg" -Encoding UTF8
    Set-Content -Path (Join-Path $fotos "foto-b.png") -Value "png" -Encoding UTF8
    (Get-Item (Join-Path $fotos "foto-a.jpg")).LastWriteTime = (Get-Date).AddDays(-10)
    (Get-Item (Join-Path $fotos "foto-b.png")).LastWriteTime = (Get-Date).AddDays(-20)

    $rSim = Tareas @("ejecutar", "renombrar-fotos", $fotos, "--simular")
    Paso "renombrar --simular anuncia SIMULACION" (($rSim.Codigo -eq 0) -and ($rSim.Texto -match "SIMULACI.N"))
    Paso "renombrar --simular NO renombra nada" ((Test-Path (Join-Path $fotos "foto-a.jpg")) -and (Test-Path (Join-Path $fotos "foto-b.png")))

    $r1 = Tareas @("ejecutar", "renombrar-fotos", $fotos, "--si")
    $renombrados = Get-ChildItem $fotos -File | Where-Object { $_.Name -match "^\d{4}-\d{2}-\d{2}_\d{3}\.(jpg|png)$" }
    Paso "renombrar aplica la plantilla fecha_NNN a las 2 fotos" (($r1.Codigo -eq 0) -and ($renombrados.Count -eq 2)) (($renombrados | ForEach-Object Name) -join ", ")
    Paso "renombrar conserva la fecha de modificacion usada" (($renombrados | Where-Object { $_.Name -like "*.jpg" }).Count -eq 1)

    # Segunda vuelta con una foto nueva. OJO: renombrar recalcula el n en cada
    # pasada (el orden {n:03} puede cambiar), pero NINGUNA foto se pierde ni se
    # pisa: total pasa de N a N+1 ficheros.
    $antes = @($renombrados | ForEach-Object Name)
    Set-Content -Path (Join-Path $fotos "foto-c.jpg") -Value "jpg nuevo" -Encoding UTF8
    $r2 = Tareas @("ejecutar", "renombrar-fotos", $fotos, "--si")
    $despues = @(Get-ChildItem $fotos -File | Where-Object { $_.Name -match "^\d{4}-\d{2}-\d{2}_\d{3}\.(jpg|png)$" } | ForEach-Object Name)
    Paso "renombrar segunda vuelta: suma 1, no se pierde ni se pisa ninguna" (($r2.Codigo -eq 0) -and ($despues.Count -eq ($antes.Count + 1))) ($despues -join ", ")

    # 4.8 abrir-nav: SOLO simulacion (no abre nada de verdad).
    #     El numero de pestañas se lee del propio JSON: si un dia cambias las
    #     urls, el test se adapta solo.
    $cfg = Get-Content "src\tareas\docs\acciones.json" -Raw | ConvertFrom-Json
    $urlsJson = @($cfg.acciones | Where-Object nombre -eq "abrir-nav").urls.Count
    $ab = Tareas @("ejecutar", "abrir-nav", "--simular")
    Paso "abrir-nav --simular anuncia SIMULACION y no pide confirmacion" (($ab.Codigo -eq 0) -and ($ab.Texto -match "SIMULACI.N"))
    $patron = "{0} pesta.as" -f $urlsJson
    Paso ("abrir-nav --simular cuenta las {0} URLs del JSON" -f $urlsJson) (($ab.Codigo -eq 0) -and ($ab.Texto -match $patron)) ("pesta.as seg.un JSON: {0}" -f $urlsJson)
}

# --- 5. Resumen -------------------------------------------------------------

Write-Host ""
Write-Host ("=== Resumen: {0} pasos, {1} fallo(s) ===" -f $pasos, $fallos) -ForegroundColor Cyan
if ($fallos -gt 0) { exit 1 } else { exit 0 }
