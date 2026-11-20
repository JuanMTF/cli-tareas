# ADR-0018: CI en GitHub Actions (matriz de 3 sistemas) y el scope `workflow` de la PAT

- Estado: aceptada
- Fecha: 2026-11-20

## Contexto

La rúbrica de la sesión 4 exige que la suite corra en GitHub Actions en
los 3 sistemas (Ubuntu, Windows y macOS). El fichero
`.github/workflows/pruebas.yml` ya está creado y commiteado (commit
`412d812`), pero el push se rechazó:

    ! [remote rejected] Sesion-4 -> Sesion-4 (refusing to allow a
    Personal Access Token to create or update workflow
    .github/workflows/pruebas.yml without workflow scope)

GitHub exige el scope `workflow` en la PAT para tocar ficheros bajo
`.github/workflows/`.

## Decisión

1. **Un solo workflow, matriz de 3 sistemas**: `push` y `pull_request`
   lanzan el job `pytest` en `ubuntu-latest`, `macos-latest` y
   `windows-latest`, con `fail-fast: false` para ver TODOS los fallos de
   la semana, no solo el primero.
2. **Pasos mínimos**: `actions/checkout@v7`, `astral-sh/setup-uv@v10.3.3`
   con Python 3.12, `uv sync` y `uv run pytest -v` (decidido el 20-11:
   la guía pide `-v`). Nada más: ni caché de dependencias ni publicación
   de artefactos ni cobertura. (Las versiones se subieron el 20-11:
   `checkout@v4` y `setup-uv@v5` usaban Node.js 20, obsoleto, y GitHub
   enseñaba 3 avisos en cada ejecución.)
3. **Sin red ni claves en el runner**: los tests de IA usan dobles
   (`tests/conftest.py`) y las fixtures simulan el entorno, así que CI
   no necesita `.env` ni `CENTRO_IA_*`.
4. **La PAT necesita el scope `workflow`**: para subir o cambiar el
   workflow hay que marcar `workflow` en la PAT (GitHub → Settings →
   Developer settings → Personal access tokens). Sin él, el push se
   rechaza aunque el resto del repo suba bien.
5. **Diagnóstico por anotaciones**: si la suite falla, un paso extra
   (`if: failure()`) repite pytest con `--tb=no -q -rfE` y convierte cada
   línea `FAILED`/`ERROR` en una anotación `::error::`. Motivo: el log
   completo de GitHub exige iniciar sesión (la API devuelve 403 sin
   token), pero la API de anotaciones es pública (`GET
   /repos/.../check-runs/{id}/annotations`): así el test culpable se lee
   desde fuera sin que nadie tenga que copiar nada. El paso solo salta
   cuando algo ya ha fallado, así que la ejecución normal sigue siendo
   el workflow mínimo de arriba.

## Alternativas consideradas

1. **Caché de dependencias (`uv` cache)**: descartada por ahora — la
   suite corre en ~16 s y la caché añade complejidad; se puede añadir
   más adelante si el CI se hace lento.
2. **Publicar cobertura o artefactos**: descartada (la rúbrica solo pide
   la suite en verde en los 3 sistemas).
3. **Solo Ubuntu**: descartada (la rúbrica pide los 3 sistemas).
4. **SSH o `gh auth login` en vez de PAT**: posible, pero el repo ya se
   autentica por HTTPS con PAT; se queda el scope `workflow` como única
   pieza que falta.
5. **Bajar el log del job por la API (`/actions/jobs/{id}/logs`)**:
   descartada — GitHub devuelve 403 sin token («Sign in to view logs»).
   Pedirle a alguien que copie el log a mano es incómodo y propenso a
   pegar el aviso equivocado (así pasó: se pegó el de Node.js 20, que
   estaba arriba de todo). La vía elegida son las anotaciones (decisión 5).

## Consecuencias

- Positivas: la rúbrica de pruebas en CI queda cubierta; `fail-fast: false`
  garantiza que un fallo en un SO no tape los otros.
- Negativas: 3 máquinas × cada push = más tiempo de CI; y cualquier
  cambio futuro en el workflow vuelve a requerir el scope `workflow` de
  la PAT.

## Verificación (20-11-2026)

- Batería completa (`pruebas/ejecutartareas.bat`, opción 1): **48 pasos,
  0 fallos**, con `uv run pytest` → **176 passed**.
- Push reintentado con la PAT con scope `workflow`: subió y Actions corrió
  la ejecución 1 («ropemos la ia») — **ROJA en los 3 sistemas** en
  `uv run pytest` (`uv sync` bien en las tres). Causa (Prompt 28): dos
  tests exigían «AVISO: CPU al» con la CPU real ≥1%, y en una VM ociosa
  la muestra de 0,5 s sale 0% → arreglados con un doble de
  `psutil.cpu_percent` a 42%. El workflow se actualizó a la vez
  (acciones sin Node 20 + paso de anotaciones).
- `uv run pytest` en local → **176 passed** con todos los cambios.
  **Pendiente: push y ver las 3 máquinas en verde** (si aún sale rojo, el
  paso de anotaciones dirá qué test es, vía la API pública).
- Segunda ronda (Prompts 28-29): la ejecución salió **ROJA otra vez** y
  los tests fallidos fueron (desde el log copiado y los anotaciones):
  `test_opcion_inexistente_en_espanol` (las 3 SO: el error de opción se
  pinta con ANSI, `No existe la opción: \x1b[1;32m-t\x1b[0m` — se limpia en
  `_texto`) y, en macOS, `AttributeError: module 'psutil' has no attribute
  'cpu_freq'` (7 tests: se captura `AttributeError` en el informe).
  `uv run pytest` en local → **176 passed** con los arreglos. Pendiente:
  push y ver las 3 en verde.
