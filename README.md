# cliWork · CLI de tareas con ficheros (DAM)

Automatiza tareas repetitivas con ficheros desde la terminal: mover, copiar,
comprimir, renombrar, borrar, convertir PDF a HTML y limpiar huellas de USB.
Las acciones viven en un JSON (`acciones.json`): añadir una acción = editar el
JSON, nunca el código (ADR-0001).

## Órdenes

- `uv run cliWork --help` — ayuda con todos los comandos.
- `uv run cliWork version` — versión.
- `uv run cliWork validar [FICHERO]` — comprueba el JSON de acciones.
- `uv run cliWork acciones [NOMBRE]` — lista las acciones o muestra el detalle.
- `uv run cliWork listar CARPETA` — tabla con el contenido de una carpeta.
- `uv run cliWork ejecutar NOMBRE [CARPETA|URL] [--simular] [--si] ...` — ejecuta.
- `uv run cliWork comprobar-ia` — comprueba la conexión con el servidor de IA.
- `uv run cliWork indexar CARPETA` — convierte solo los PDF que falten.

## Cambiar carpetas y filtros sin tocar el código

Todo lo que varía por persona (carpetas de origen/destino, extensiones,
patrones, antigüedad…) vive en el JSON. Con la opción global `--config` se usa
otro fichero de acciones en vez del empaquetado, sin tocar el código:

```powershell
uv run cliWork --config C:\ruta\mis-acciones.json validar
uv run cliWork --config C:\ruta\mis-acciones.json ejecutar ordenar-descargas --simular
```

(`--config` va justo después de `cliWork`, antes del comando.)

## Acciones con IA (tipo «resumir»)

Las acciones de tipo `resumir` mandan el texto de cada fichero (.txt, .md o
.pdf) al modelo con las `instrucciones` de la acción y escriben
`<nombre>.resumen.md` en `destino` (o junto al fichero). La configuración del
proveedor (compatible con la API de OpenAI) va en el `.env`, nunca en el
código: `CENTRO_IA_URL`, `CENTRO_IA_KEY`, `CENTRO_IA_MODELO`, `CENTRO_IA_CA`
(mira `.env.example`). `max_caracteres` (500–50000, por defecto 12000) acota el
texto que se envía; `categorias` limita las respuestas del modelo a esa lista.

- Con `--simular` NO se llama al modelo: solo dice cuántos caracteres enviaría.
- Sin IA disponible (sin clave, sin red…) la acción sale con el código 4 y el
  resto del programa sigue funcionando.

## Desarrollo

- Dependencias con uv: `uv sync` (añadir: `uv add <paquete>`).
- Pruebas: `uv run pytest` o la batería completa con `pruebas\ejecutartareas.bat`
  (todo en `~/pruebas-tareas`; con `solo-simular` no toca nada).
- Documentación del proyecto: `src/tareas/docs/` (prompts, ADR, skill).
