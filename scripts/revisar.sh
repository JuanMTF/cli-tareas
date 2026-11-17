#!/usr/bin/env bash
# Revisión automática del código con opencode (sesión 4).
#
# Lanza al agente revisor de opencode en modo SOLO lectura: revisa los
# cambios sin commitear (o un commit concreto) y señala bugs, sin editar
# nada. El veredicto se imprime por pantalla; el commit lo hace siempre
# el responsable, después de leerlo.
#
# Uso:
#   bash scripts/revisar.sh          # revisa lo SIN commitear
#   bash scripts/revisar.sh SHA      # revisa el commit SHA (ej. git show)
#
# En Windows: Git Bash o WSL (PowerShell no ejecuta .sh). En Linux/macOS,
# bash directo. opencode debe estar en el PATH.
set -euo pipefail

if ! command -v opencode >/dev/null 2>&1; then
    echo "No encuentro opencode en el PATH: instálalo antes de revisar." >&2
    exit 1
fi

if [ "$#" -gt 0 ]; then
    objetivo="el commit $1 (git show $1) de este proyecto"
else
    objetivo="los cambios SIN commitear (git diff) y los ficheros nuevos (git status --short) de este proyecto"
fi

exec opencode run "Agente revisor, SOLO lectura: no edites ni crees ficheros. Revisa $objetivo (una CLI en Python 3.12 con Typer+Rich, paquete en src/tareas, normas en AGENTS.md). Busca: 1) bugs reales, con el escenario concreto en el que fallan; 2) cambios de comportamiento no intencionados; 3) incumplimientos de las normas (pathlib, encoding utf-8, mensajes en español, sin os.system). No revises código que no toca el cambio. Termina con una lista corta en tres bloques: GRAVE (bugs), MEJORAR (sugerencias), OK (lo comprobado y sin queja)."
