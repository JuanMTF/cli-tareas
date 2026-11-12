# auditoria.ps1 - auditoria del Paso 8 de la CLI cliWork.
#
# Que hace:
#   1. Prepara el sandbox ~/pruebas-tareas/auditoria con auditoria_setup.py
#      (nombres con tildes/espacios, FOTO1.JPG en mayusculas, dos PNG con la
#      misma fecha para forzar una colision al renombrar, y un JSON propio
#      con 4 acciones: mover-png, mover-jpg, copiar-docx, ren-fecha).
#   2. Recorre las 8 preguntas de la auditoria y muestra el codigo de salida
#      de cada orden (simulaciones, destino que no existe, nombres repetidos,
#      errores humanos, borrar sin --si...).
#
# Solo toca ~/pruebas-tareas. Las ordenes "reales" se ejecutan solo dentro
# del sandbox, nunca fuera.
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\pruebas\auditoria.ps1
# (o desde cualquier carpeta; el script se coloca el solo en la raiz del repo)
#
# NOTA: solo ASCII. PowerShell 5.1 lee los .ps1 como ANSI si no llevan BOM.
$ErrorActionPreference = "Continue"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

# Sube a la raiz del proyecto para que "uv run" encuentre el pyproject.toml.
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "=== [0] Sandbox de auditoria ===" -ForegroundColor Green
& uv run python "pruebas\auditoria_setup.py"
if ($LASTEXITCODE -ne 0) { Write-Host "El sandbox no se pudo crear." -ForegroundColor Red; exit 1 }

$raiz = "$HOME\pruebas-tareas\auditoria"
$cfg = "$raiz\mis-acciones.json"

function Cli-Work {
    param([string[]]$Argumentos, [string]$Stdin = "")
    Write-Host ""
    Write-Host (">> cliWork {0}" -f ($Argumentos -join " ")) -ForegroundColor Cyan
    if ($Stdin) {
        $salida = $Stdin | & uv run cliWork @Argumentos 2>&1
    } else {
        $salida = & uv run cliWork @Argumentos 2>&1
    }
    $salida | ForEach-Object { Write-Host ("   {0}" -f $_) }
    Write-Host ("   >>> codigo de salida = {0}" -f $LASTEXITCODE) -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== [1] SIMULACIONES: nada se crea ni se toca ===" -ForegroundColor Green
Cli-Work @("--config", $cfg, "ejecutar", "mover-png", "--simular")
Cli-Work @("--config", $cfg, "ejecutar", "mover-jpg", "--simular")
Cli-Work @("--config", $cfg, "ejecutar", "ren-fecha", "--simular")
Cli-Work @("--config", $cfg, "ejecutar", "copiar-docx", "--simular")
Write-Host ""
Write-Host ("? Existe el destino tras las simulaciones? (debe ser False): {0}" -f (Test-Path "$raiz\destino"))
Write-Host ("Contenido de {0}: {1}" -f $raiz, ((Get-ChildItem $raiz -Name) -join ", "))

Write-Host ""
Write-Host "=== [2] REALES: el destino se crea al ejecutar ===" -ForegroundColor Green
Cli-Work @("--config", $cfg, "ejecutar", "mover-png", "--si")
Write-Host ("   destino creado: {0}" -f (Test-Path "$raiz\destino"))
Cli-Work @("--config", $cfg, "ejecutar", "mover-jpg", "--si")
Cli-Work @("--config", $cfg, "ejecutar", "copiar-docx", "--si")   # 1a copia
Cli-Work @("--config", $cfg, "ejecutar", "copiar-docx", "--si")   # 2a copia: " (1)"
Cli-Work @("listar", "$raiz\destino")

Write-Host ""
Write-Host "=== [3] mover dos veces: la 2a no encuentra nada ===" -ForegroundColor Green
Cli-Work @("ejecutar", "ordenar-descargas", "$raiz\origen-orden", "-d", "$raiz\destino-orden", "--si")
Cli-Work @("ejecutar", "ordenar-descargas", "$raiz\origen-orden", "-d", "$raiz\destino-orden", "--si")

Write-Host ""
Write-Host "=== [4] borrar SIN --si: pregunta; 'n' = no borra, codigo != 0 ===" -ForegroundColor Green
Cli-Work @("ejecutar", "limpiar-temporales", "$raiz\origen-tmp") -Stdin "n"
Write-Host ("   el .tmp sigue ahi (debe ser True): {0}" -f (Test-Path "$raiz\origen-tmp\viejo.tmp"))
Cli-Work @("ejecutar", "limpiar-temporales", "$raiz\origen-tmp", "--si")
Write-Host ("   el .tmp borrado (debe ser True): {0}" -f (-not (Test-Path "$raiz\origen-tmp\viejo.tmp")))

Write-Host ""
Write-Host "=== [5] ERRORES humanos: sin traceback, codigo 1 ===" -ForegroundColor Green
Cli-Work @("--config", $cfg, "ejecutar", "mover-png", "$raiz\no-existe")   # origen inexistente
Cli-Work @("--config", $cfg, "ejecutar", "mover-pngs")                     # accion inexistente

Write-Host ""
Write-Host "=== [6] renombrar REAL con colision: nada se pierde, aparece ' (1)' ===" -ForegroundColor Green
Cli-Work @("--config", $cfg, "ejecutar", "ren-fecha", "--si")
Cli-Work @("listar", "$raiz\origen-ren")

Write-Host ""
Write-Host "=== [7] renombrar-fotos repetido: estable, sin _001_001 ===" -ForegroundColor Green
# Requiere el sandbox de la bateria (pruebas.ps1): fotos ya renombradas.
Cli-Work @("ejecutar", "renombrar-fotos", "$HOME\pruebas-tareas\bateria\fotos", "--si")
Cli-Work @("ejecutar", "renombrar-fotos", "$HOME\pruebas-tareas\bateria\fotos", "--si")
