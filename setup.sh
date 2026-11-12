#!/usr/bin/env bash
# setup.sh - instalacion de cliWork en Ubuntu de un solo paso.
#
# Que hace:
#   1. Comprueba si uv esta instalado (si no, lo instala).
#   2. Instala las dependencias del proyecto (uv sync).
#   3. Instala la CLI en el PATH: copia aislada en ~/.local (no editable),
#      asi tocar el codigo del repo NO cambia el programa instalado.
#   4. Comprueba que cliWork responde.
#
# Uso (desde la raiz del repo descargado):
#   chmod +x setup.sh
#   ./setup.sh
set -euo pipefail

echo "== Instalacion de cliWork =="

# [1] uv
if ! command -v uv >/dev/null 2>&1; then
    echo "[1/5] uv no esta instalado: instalando..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "[1/5] uv ya esta instalado: $(uv --version)"
fi

# [2] dependencias del proyecto (crea .venv, descarga Python 3.12 si hace falta)
echo "[2/5] Instalando dependencias (uv sync)..."
uv sync

# [3] instalar la CLI en el PATH (reinstala si ya existia)
echo "[3/5] Instalando cliWork en ~/.local/bin..."
uv tool install --force .

# [4] asegurar que ~/.local/bin esta en el PATH
uv tool update-shell >/dev/null 2>&1 || true
if ! command -v cliWork >/dev/null 2>&1; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# [5] comprobar
echo "[4/5] Comprobando la instalacion..."
if cliWork --help >/dev/null 2>&1; then
    echo "OK: cliWork responde."
elif [ -x "$HOME/.local/bin/cliWork" ]; then
    echo "Aviso: ~/.local/bin no esta en el PATH de esta terminal."
    echo "  Ejecuta:  source ~/.bashrc   (o cierra y abre la terminal)"
fi

echo "[5/5] Prueba rapida:"
cliWork --help 2>/dev/null || "$HOME/.local/bin/cliWork" --help

echo ""
echo "Listo. Ya puedes usar 'cliWork' desde cualquier carpeta:"
echo "  cliWork validar"
echo "  cliWork acciones"
echo "  cliWork --help"
