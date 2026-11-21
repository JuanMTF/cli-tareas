# ADR-0013: Los tests corren aislados del equipo real: cwd, HOME y IA sellados en conftest

- Estado: aceptada
- Fecha: 2026-11-17

## Contexto

La suite de la sesión 4 (156 tests) llegaba a verde, pero no tenía
garantías de aislamiento: nada impedía que un test nuevo leyera el
`.env` real del repo, expandiera `~` sobre `C:\Users\juant` (el JSON
empaquetado trae `origen: "C:/Users/juant/OneDrive/..."` y destinos
`~/Documentos/...`) o llegara a llamar al servidor de IA por un descuido
en un guard. El profesor pide que las pruebas no toquen nada de verdad.

Además, en esta máquina pytest se caía **después** del último test (con
los 156 ya en verde) en `cleanup_dead_symlinks` con `PermissionError`
sobre `%TEMP%\pytest-of-juant\pytest-current`: el enlace al último
directorio numerado quedó con ACLs podadas (no se puede ni borrar sin
admin), así que `uv run pytest` salía con código 1 a pesar de todo bien.

## Decisión

1. **`aislado` (autouse en `tests/conftest.py`)**: para todo test, sin
   que lo pida, `monkeypatch.chdir(tmp_path)` (el cwd es un temporal de
   pytest y el `.env` real deja de ser visible para
   `find_dotenv(usecwd=True)`), `HOME` y `USERPROFILE` apuntan al
   `tmp_path` (cualquier `expanduser()` de «~» cae en el sandbox), y
   `CENTRO_IA_URL/KEY/CA` se quitan del entorno (sin config, el proveedor
   sale con `IANoDisponible` antes de intentar ninguna conexión). Los
   autouse se montan antes que `env_con_ia`/`env_sin_ia`, que siguen
   funcionando encima.
2. **`descargas`**: carpeta `tmp_path/Descargas` con los cinco casos
   típicos (factura.pdf, «apuntes de redes.docx», FOTO1.JPG —mayúsculas—,
   «cumpleaños 2.png» —espacio— y viejo.tmp con mtime de 40 días forzado
   con `os.utime`), lista para los filtros.
3. **`ProveedorFalso` + `modelo_falso`**: proveedor público que GRABA
   `(sistema, usuario, max_tokens)` de cada llamada y contesta lo
   programado: los tests de la capa IA afirman contra lo grabado (p. ej.
   el documento entre `<documento>` y `</documento>`) sin red ni `.env`.
4. **`--basetemp=.pytest-tmp` en `pyproject.toml`**: con basetemp propio
   pytest no crea el árbol numerado `pytest-of-<usuario>` ni el enlace
   `pytest-current`, así que el `cleanup_dead_symlinks` que revienta
   nunca se ejecuta (solo corre cuando no hay basetemp:
   `_pytest/tmpdir.py:366`). El directorio se vacía al empezar cada
   sesión y va al `.gitignore`.
5. **Ruta del JSON empaquetado SIEMPRE absoluta**: los 5 tests que leían
   `"src/tareas/docs/acciones.json"` relativo ahora usan
   `tareas.config.RUTA_ACCIONES` (anclada a `__file__`). Mismo fichero,
   pero no dependen del cwd que `aislado` mueve.

## Alternativas consideradas

1. **Reparar el `%TEMP%\pytest-of-juant`** (borrarlo, arrancar pytest
   como admin): no es borrable con el usuario normal y el arreglo
   desaparecería con la siguiente basura de ACLs; el basetemp lo esquiva
   de raíz y es reproducible en cualquier máquina.
2. **Marcar los 5 tests con `cwd=raíz` o pasarles la ruta absoluta a
   mano**: parcheo por test y se olvida; la regla «la ruta empaquetada
   viene del módulo» vale para todos de una vez.
3. **Que `aislado` NO sea autouse**: cada test tendría que acordarse de
   pedirlo; el primero que se olvide lee el `.env` real o escribe en
   `C:\Users\juant`. El aislamiento no es opcional: es el suelo.
4. **Un servidor IA de mentira en un puerto local** (p. ej. un httpx
   MockTransport global): para la capa IA ya hay dobles y httpx
   fabricado (Prompt 15); un servidor real aunque sea local complica CI
   sin ganar nada hoy.

## Consecuencias

- Positivas: ningún test puede tocar carpetas del usuario ni llamar al
  servidor (dos capas: sin variables no hay proveedor, y los dobles
  rompen con un mensaje claro si alguien salta un guard); `uv run
  pytest` sale 0 limpio en Windows; los tests de filtros tienen su
  Descargas de juguete con los casos feos ya montados.
- Negativas: cualquier ruta relativa que quede en la suite es una bomba
  (la autouse la descubre al momento, como pasó con los 5 tests); el
  `--basetemp` añade una opción a `pyproject.toml` que hay que explicar
  (está comentado in situ); `.pytest-tmp` vive dentro del repo (vacío
  tras cada sesión, ignorado por git).
- Qué haré si cambia: si algún día pytest arregla el
  `cleanup_dead_symlinks` en Windows, se puede quitar el basetemp; si
  los tests necesitan un `.env` de mentira, se escribe en el tmp_path
  (nunca el real) — `find_dotenv(usecwd=True)` lo encontraría porque el
  cwd es el sandbox.

## Verificación (17-11-2026)

- `uv run pytest`: **156 passed in 10.81 s**, código 0, sin traceback de
  limpieza al final (antes: crash `PermissionError` tras el 100 %).
- Con el aislado activo, los 5 tests del JSON empaquetado pasan usando
  `RUTA_ACCIONES` (la ruta absoluta del paquete).
- `uv add --dev pytest`: sincroniza sin cambios (el grupo dev ya lo
  declaraba y la .venv lo tenía).
- Las fixtures nuevas (`aislado`, `descargas`, `ProveedorFalso`,
  `modelo_falso`) están listas para los tests de config/acciones/IA de
  esta sesión, que todavía no las usan.
