# ADR-0019: Fichero personal `mis-acciones.json` como fichero default de `--config`

- Estado: aceptada
- Fecha: 2026-11-21

## Contexto

Tras el fallo del install cruzado (paso-9) y el retag del `v1.0.0`, el usuario
quedó con una duda de configuración muy clara: no quiere definir a mano cómo se
usa `--config` con las opciones (destino, extensiones, origen) de las acciones
de su fichero personal. «Quedamos» que se creara el fichero personal
`mis-acciones.json` al instalar y que, con `--config`, no se pidiera ruta: se
abriera ese fichero, se guardara y ese fichero fuera a mandar sobre todos los
`acciones.json`.

## Decisión

1. **Un fichero personal de acciones**: `~/.cliWork/mis-acciones.json`
   (mis-acciones), con el mismo formato que el JSON empaquetado
   (`{"version": 1, "acciones": [...]}`).
2. **Se crea solo al primer uso** (`config.preparar_mis_acciones()`, con el
   contenido del JSON empaquetado como punto de partida) y se reutiliza si ya
   existe (el usuario edita sus opciones de destino/extensiones/origen).
3. **Por defecto manda el personal**: sin `--config`, todas las órdenes
   (`validar`, `acciones`, `ejecutar`, `menu`, `indexar`) usan el fichero
   personal; con `--config <ruta>` se puede pasar otro fichero explícito.
4. **Sin ruta que teclear**: la opción global `--config` pasa a default `None`
   y `_ruta_config` resuelve el personal; el help y el README se actualizan.

## Alternativas consideradas

1. **Seguir con `--config <ruta>` siempre**: pedir ruta en cada orden — descartada
   por el propio usuario («no quiero definir cómo se configura»).
2. **Reusar `~/.cliWork/configUsuario.json`**: descartada para este cambio: ese
   fichero es de opciones sueltas por campo (origen/destino/extensiones/confirmar)
   y el usuario pidió un fichero de acciones con las opciones por acción
   (destino/extensiones/origen).

## Consecuencias

- Positivas: el usuario configura sus acciones sin tocar el código ni teclear
  rutas; el fichero personal manda sobre el empaquetado.
- Negativas: dos ficheros personales conviven (`configUsuario.json` y
  `mis-acciones.json`); la prioridad entre ambos queda documentada en el README.
- Quedan pendientes: retag/re-release de `v1.0.0` y el paso-9 (install cruzado).

## Verificación (21-11-2026)

- `uv run pytest`: **184 passed** (181 previos + 3 nuevos: fichero personal por
  defecto, `--config` explícito que manda sobre el personal, y creación del
  fichero).
- `uv tool install .` resuelve y el install cruzado (con el retag hecho) debe
  repetirse.
