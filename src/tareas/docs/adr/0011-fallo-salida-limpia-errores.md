# ADR-0011: Salida limpia de errores previstos con un único helper `fallo()`

- Estado: aceptada
- Fecha: 2026-11-15

## Contexto

Tras revisar los fragmentos de `cli.py` del profesor (sesión 3), se detectó
una diferencia de diseño: su `fallo(e: TareasError)` hace TODO en un solo
sitio — línea en rojo, el aviso de «las acciones sin IA siguen
funcionando» cuando la excepción es `IANoDisponible`, y `typer.Exit(e.codigo_salida)`.

En el nuestro esos pasos iban pegados a mano en cada punto de captura:
`_aviso_sin_ia(exc)` seguido de `_error(str(exc), exc.codigo_salida)`
repetido en los dos `except` de `ejecutar` y en los dos de
`comprobar_ia`. Funcionaba, pero era frágil: cualquier `except
TareasError` nuevo podría olvidar el aviso de la IA, y el texto del aviso
no apuntaba al comando que lista las acciones.

## Decisión

1. **Un helper único `fallo(exc: TareasError) -> NoReturn`** en cli.py:
   llama a `_aviso_sin_ia(exc)` y a `_error(str(exc),
   codigo=exc.codigo_salida)`. Todo `except TareasError` de la CLI
   (los 2 de `ejecutar` y los 2 de `comprobar_ia`) se limita a
   `fallo(exc)`.
2. **El aviso apunta al comando**: «...mira cuáles son con «cliWork
   acciones»» (la orden `acciones` muestra la columna IA con «sí / —»).
3. **Se mantienen `_error` y `_aviso_sin_ia` como piezas** (con el
   prefijo «Error:», no el «✘» del profe): `fallo` las compone, y
   `_error` sigue sirviendo solo para errores que no vienen del motor
   (configuración, órdenes propias como `indexar`).

## Alternativas consideradas

1. **Copiar el `fallo(e)` del profesor tal cual** (prefijo «✘», texto
   «tareas acciones»): el nombre del programa aquí es `cliWork` (decisión
   del usuario; «tareas» es como se llama el programa del profesor), y el
   prefijo «Error:» ya está asentado en toda la CLI. Descartado el copia-pega.
2. **Dejar los cuatro pares `_aviso_sin_ia` + `_error`**: hoy son
   consistentes, pero el riesgo de olvido en un catch futuro no compensa
   las tres líneas de helper.
3. **Que `_error` reciba la excepción en vez del texto**: mezclaría las
   dos piezas; el helper ya resuelve la composición sin tocar `_error`.

## Consecuencias

- Positivas: imposible olvidar el aviso de IA en un catch nuevo; los
  cuatro puntos de captura quedan en una línea; el aviso enseña el
  camino («cliWork acciones»); sin cambios de comportamiento observable
  (mismos mensajes, mismo código de salida).
- Negativas: un nivel más de indirección (`fallo` → `_aviso_sin_ia` +
  `_error`); los errores que no vienen de `TareasError` siguen llamando
  a `_error` a mano (correcto, pero son dos caminos que conviene no confundir).
- Qué haré si cambia: si algún catch necesita un tratamiento distinto
  (p. ej. seguir tras el error en vez de salir), llamará a las piezas
  directamente y se documentará en su ADR.

## Verificación (15-11-2026)

**147 tests en verde** y `uv run cliWork validar` → ✔ 15 acciones
válidas, sin tocar ningún test (ninguno dependía de los textos). Se
documentó en `docs/prompts.md` (Prompt 12) la revisión completa: qué se
adoptó (la idea del helper único) y qué se mantuvo distinto y por qué
(prefijo «Error:», `comprobar_ia` con certificado y `SISTEMA_PRUEBA`,
inyección del proveedor en `motor.py` según ADR-0003, nombre `cliWork`).
