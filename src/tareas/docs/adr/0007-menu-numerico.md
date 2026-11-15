# ADR-0007: Menú con números («cliWork --menu») que reutiliza «ejecutar»

- Estado: aceptada
- Fecha: 2026-11-15

## Contexto

Escribir las órdenes a mano cuesta y a veces se teclea mal (nombres
largos en kebab-case, opciones, rutas). El autocompletado del shell
(`NombresAccion` en cli.py) ayuda, pero no sustituye al tecleo. Se pide
un menú con números para lanzar las acciones, sin preguntas de más: se
elige la acción y se ejecuta de verdad; lo «diferente» (`--simular`,
navegador, opciones) se teclea en la orden `ejecutar` de siempre.

## Decisión

1. **Se lanza con la opción global `--menu`, usada sola** (`cliWork
   --menu`) o como orden (`cliWork menu`). En el callback, `--menu` con
   otra orden detrás es error (código 1). La app va con
   `invoke_without_command=True` para poder llamarla sin orden; `cliWork`
   a secas sigue mostrando la ayuda de siempre.
2. **Tabla numerada** de las acciones ordenadas por nombre (la misma
   lista que `cliWork acciones`) y tres pasos: número de acción
   (`0` sale), carpeta de origen y ejecución.
3. **La carpeta por defecto es la «origen» del JSON, visible en el
   prompt** («Carpeta de origen (Intro = C:\...\Descargas)»): Intro la
   usa tal cual. Si la acción no tiene `origen`, no hay defecto y se
   pide (por eso el JSON real lleva «origen» en todas las acciones sobre
   ficheros, y hay un test que lo exige). «abrir» (URLs) y «limpiar-usb»
   (registro) no preguntan carpeta porque no la usan.
4. **Ejecuta DE VERDAD y reutiliza la orden `ejecutar`** (se llama a la
   misma función): hereda confirmaciones de «borrar»/«abrir»,
   navegador, tabla de simulación, resumen y códigos de salida. Sin
   preguntas de modo ni de navegador: si una acción falla o se cancela
   una confirmación con «n», el menú avisa y SIGUE vivo (atrapa
   `typer.Exit`/`Abort`/`KeyboardInterrupt`/`EOFError`).
5. Las rutas por defecto del JSON empaquetado son las de un equipo
   normal (`~/Descargas`, `~/Imágenes`, `~/Documentos/...`), no las de
   desarrollo: para probar se usa `--config` con un JSON gemelo apuntando
   a `~/pruebas-tareas`, o `--simular`.

## Alternativas consideradas

1. **Preguntar modo en el menú (1 simular / 2 ejecutar)**: primera
   versión; se quitó a petición del que usa la CLI (fricción: el menú es
   para no teclear). La simulación queda en `ejecutar --simular`.
2. **Preguntar navegador en «abrir»**: por el mismo motivo, fuera;
   `-e/-g/-f` se teclean.
3. **Bucle propio que ejecute la acción directamente**: duplicaría la
   lógica de confirmaciones, navegador y resumen; descartado por
   reutilizar `ejecutar` (un solo camino de código).
4. **Menú visual con flechas** (questionary/rich.prompt interactivo):
   dependencia nueva y menos portable; los números son suficientes.

## Consecuencias

- Positivas: cero tecleo para el uso diario; las carpetas por defecto
  las decide el JSON (ADR-0001) y el menú las muestra antes de usarlas;
  un solo camino de ejecución (todo pasa por `ejecutar`); un error de
  una acción no cierra el menú.
- Negativas: un Intro despistado sobre una acción sin `confirmar` hace
  el trabajo de verdad (mitigado: las destructivas siempre confirman, y
  la primera vez conviene `--simular`); `cliWork` a secas sale con el
  código 2 de click (`no_args_is_help`), igual que antes del cambio.
- Qué haré si cambia: si el menú necesitara opciones avanzadas
  (`--antiguedad`, `--destino`, `--nombre`), se pasarían por `_bucle_menu`
  con sus propias preguntas; si hiciera falta marcar acciones como
  «ocultas en el menú», se haría con un campo del JSON, no con código.

## Verificación (15-11-2026)

128 tests en verde, 7 de menú en `tests/test_cli.py` (ayuda, salir con
0, respuestas raras avisan y repiten, confirmación de «abrir» cancelada
con «n» sin cerrar el menú, `--menu` como opción global, combinación con
otra orden rechazada y «origen» del JSON como defecto visible con un
`--config` temporal). Pruebas de humo con entrada redirigida: número →
confirmación → vuelta al menú. README y skill `acciones-json`
documentados.
