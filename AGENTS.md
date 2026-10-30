# AGENTS.md

Proyecto `tareas`: CLI en Python (Typer) para automatizar tareas repetitivas con ficheros.
Repo pequeño, un solo paquete. Esto es lo que no se deduce solo de leer los nombres de ficheros.

# tareas · CLI de tareas con ficheros (proyecto de 1º DAM)
## Stack y órdenes
- Python 3.12 + Typer + Rich, gestionado con uv (src layout, paquete src/tareas).
- Ejecutar: `uv run tareas --help` · Validar config: `uv run tareas validar` · Pruebas (semana 4): `uv run pytest`.
## Normas
- Mensajes y comentarios en español; código claro antes que listo.
- pathlib siempre, encoding="utf-8", nada de os.system ni shell=True: tiene que funcionar en Linux, Windows y macOS.
- Nunca ejecutes acciones sobre carpetas reales: solo en ~/pruebas-tareas y con --simular.
- No toques .env ni escribas claves en ningún fichero. No hagas git push ni commits: los hace el responsable despues de verificar codigo.
- Antes de cambiar un fichero, explica en 2-3 líneas qué vas a hacer.

## Comandos

- Instalar/sincronizar deps: `uv sync` (crea/actualiza `.venv`; no hay `requirements.txt`)
- Añadir dependencia: `uv add <pkg>` (edita `pyproject.toml` + `uv.lock`; no editar a mano)
- Ejecutar la CLI: `uv run tareas --help`
- Ejecutar un comando concreto: `uv run tareas validar <fichero>` (eso es lo que permite `opencode.json`)
- Tests: `uv run pytest` — **pytest NO está instalado**: falta `uv add --dev pytest` y aún no existe `tests/`

No hay lint, formatter, typecheck ni CI configurados. No inventes órdenes de verificación:
no existe ninguna `lint -> typecheck -> test`.

## Estado real del código (verificado ejecutando)

1. `src/tareas/__init__.py:3` tiene un `SyntaxError`: `_version_=0.1.0`. Mientras siga ahí,
   **todo** (`uv run tareas`, `import tareas`) falla al importar. Usar `_version_ = "0.1.0"`.
2. `pyproject.toml` declara `tareas = "tareas.cli:app"`, pero **`src/tareas/cli.py` no existe**.
   Hay que crearlo exportando `app = typer.Typer()` (o `typer.run`). Hasta entonces:
   `ModuleNotFoundError: No module named 'tareas.cli'`.

Si la CLI "no arranca", son estos dos puntos, no algo del entorno.

## Estructura

- `src/tareas/` (src-layout, backend `uv_build`): único paquete. Entrada real = `tareas.cli:app`
  definida en `pyproject.toml [project.scripts]`.
- `README.md` está vacío pero lo referencia `pyproject.toml`; rellenarlo si se documenta la CLI.
- Python `>=3.12` (fijado en `.python-version`: `3.12`). Deps actuales: `typer` (+`rich`,
  `shellingham` indirectas). Nada más.

## Entorno y convenciones

- La ruta del repo tiene espacios: usa comillas en rutas de shell.
- Idioma del repo: español (comentarios, mensajes y docs en español; mantenerlo).
- `.env` y derivados: prohibidos por `opencode.json` (denegados en `read`) y por `.gitignore`.
  Nunca commitear secretos.
- Git: un solo commit. `opencode.json` está sin commitear. `opencode.json` deniega
  `git push`, `git reset`, `rm`, `sudo` y pide confirmación en `edit`, `git commit` y
  casi todo `bash`. El agente `plan` tiene `edit` denegado.
