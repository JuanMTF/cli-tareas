# cliWork · CLI de tareas con ficheros (DAM)

Automatiza tareas repetitivas con ficheros desde la terminal: mover, copiar,
comprimir, renombrar, borrar, convertir PDF a HTML y limpiar huellas de USB.
Las acciones viven en un JSON (`acciones.json`): añadir una acción = editar el
JSON, nunca el código (ADR-0001).

## Instalar con una orden

Necesitas [uv](https://docs.astral.sh/uv/). Desde GitHub (la release):

```bash
uv tool install git+https://github.com/JuanMTF/cli-tareas@v1.0.0
cliWork --help
cliWork version        # debe decir: 1.0.0
```

Con el repositorio clonado, `uv tool install .` deja el comando `cliWork` en el
PATH. Para probarlo sin instalar nada: `uvx --from . cliWork --help`. Para
desarrollar, desde la carpeta del proyecto: `uv sync` y `uv run cliWork --help`.

## Órdenes

- `uv run cliWork --help` — ayuda con todos los comandos.
- `uv run cliWork version` — versión.
- `uv run cliWork validar [FICHERO]` — comprueba el JSON de acciones.
- `uv run cliWork acciones [NOMBRE]` — lista las acciones o muestra el detalle.
- `uv run cliWork listar CARPETA` — tabla con el contenido de una carpeta.
- `uv run cliWork ejecutar estado-pc` — informe del estado del equipo (CPU,
  memoria, discos, temperaturas, batería, arranque) en una tabla, con avisos
  si algo pasa los umbrales del JSON (`avisos`: disco/memoria/CPU en %).
  Solo lectura.
- `uv run cliWork --menu` — menú con números para lanzar acciones sin teclear
  órdenes: eliges acción y ejecuta de verdad (con sus confirmaciones); al
  acabar vuelve al menú solo (solo `0` o Ctrl+C salen). La carpeta que
  propone por defecto es tu `configUsuario.json` y, si no, la «origen» del
  JSON (en ese prompt solo va la RUTA: para opciones como `--destino` o
  `--extensiones`, usa `ejecutar`). Lo mismo con la orden `uv run cliWork menu`.
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

## Tus opciones por defecto: `configUsuario.json`

Cada ordenador (y cada usuario) puede tener **sus propias opciones por
defecto** en un fichero que vive en tu carpeta personal:
`~/.cliWork/configUsuario.json` (en Windows,
`C:\Users\TuUsuario\.cliWork\configUsuario.json`).

**No hay que crearlo**: se crea solo la primera vez que ejecutas una acción,
con todos los valores vacíos («no cambiar nada») y una `_ayuda` dentro que
explica cada campo en español. Si lo borras, vuelve a nacer igual.

Lo pensado para el caso de **varios ordenadores**: el mismo repo y el mismo
`acciones.json` sirven en los 3 equipos; solo cambia el fichero de usuario de
cada uno (una ruta de red por PC, o rutas de Linux si lo usas en Ubuntu).
Lo que **no** pongas no cambia nada: manda lo que diga `acciones.json`.

| Campo | Qué hace | Vacío (`""` o `[]`) significa |
|---|---|---|
| `origen` | Tu carpeta de origen por defecto para las acciones que no traigan una, y la que propone el menú | Manda la del JSON |
| `destino` | Tu carpeta de destino por defecto: manda sobre la del JSON | Manda la del JSON |
| `extensiones` | Extensiones por defecto (ej.: `[".pdf", ".jpg"]`) para los filtros que **no** traigan las suyas | Todas, como hasta ahora |
| `confirmar` | `true` = las acciones con «confirmar» piden autorización; `false` = dejan de preguntar | `true` |

**Prioridad** (quién manda, de más a menos):

1. Lo que escribes en la orden: `--carpeta`, `--destino`, `--extensiones`.
2. **Tu `configUsuario.json`** (si el campo va relleno).
3. Lo que dice `acciones.json`.
4. Los valores de fábrica.

**Ejemplo de fichero** (en un PC concreto, con la ruta de red de esa casa):

```json
{
  "_ayuda": "(explicación de cada campo, en español, dentro del fichero)",
  "origen": "//SERVIDOR/Compartido/Descargas",
  "destino": "",
  "extensiones": [],
  "confirmar": true
}
```

**Para un día concreto** («tengo muchos PDF y solo quiero esos»), no edites el
fichero: usa la opción en la orden, que manda sobre todo:

```powershell
uv run cliWork ejecutar comprimir-antiguos --extensiones .pdf --simular
```

⚠ **Las acciones de tipo `borrar` preguntan SIEMPRE**, con su aviso
«ATENCIÓN», aunque pongas `confirmar: false`: borran de verdad y no hay
papelera. Si tu fichero tiene una errata (una coma de más, un campo mal
escrito), `cliWork` avisa con el fichero, la línea y la columna y no ejecuta
nada. (ADR-0014.)

## Manuales en HTML con plantillas (tipo «transformar»)

`transformar-pdf-html` convierte cada PDF en una carpeta con su
`index.html`: páginas en imagen + capa de texto seleccionable, galería con
buscador y `manuales.json` con los metadatos. El campo opcional `plantilla`
elige cómo se ve: `tecnico` (por defecto), `esquema` (páginas grandes y
clic para hacer zoom, para planos y datasheets) o `guia` (página estrecha
de lectura). Una acción por tipo de manual = un `plantilla` distinto, sin
tocar código (ADR-0005).

## Acciones con IA («resumir», «renombrar-ia», «clasificar»)

Las acciones de tipo `resumir` mandan el texto de cada fichero (.txt, .md o
.pdf) al modelo con las `instrucciones` de la acción y escriben
`<nombre>.resumen.md` en `destino` (o junto al fichero). La configuración del
proveedor (compatible con la API de OpenAI) va en el `.env`, nunca en el
código: `CENTRO_IA_URL`, `CENTRO_IA_KEY`, `CENTRO_IA_MODELO`, `CENTRO_IA_CA`
(mira `.env.example`). `max_caracteres` (500–50000, por defecto 12000) acota el
texto que se envía; `categorias` limita las respuestas del modelo a esa lista.

- `renombrar-ia` pide al modelo un nombre corto (2-6 palabras, minúsculas,
  guiones). La respuesta pasa SIEMPRE por `a_nombre_seguro()`: primera línea,
  sin extensión ni tildes, solo `[a-z0-9-]`, 60 caracteres como mucho (si trae
  barras se rechaza). Respuesta vacía → «saltado» y el fichero no se toca.
  Se conserva la extensión original y nunca se sobrescribe (`destino_libre`).
- `clasificar` pide al modelo que elija UNA de `categorias` y mueve el fichero
  a `destino/categoria/`. Si responde otra cosa o vacío, el fichero se mueve a
  `destino/sin-clasificar/` para que nada se quede suelto. La categoría sale de
  la lista del JSON, no del texto del modelo.

- Con `--simular` NO se llama al modelo: solo dice cuántos caracteres enviaría.
- Sin IA disponible (sin clave, sin red…) la acción sale con el código 4 y el
  resto del programa sigue funcionando.

## Desarrollo

- Dependencias con uv: `uv sync` (añadir: `uv add <paquete>`).
- Pruebas: `uv run pytest` o la batería completa con `pruebas\ejecutartareas.bat`
  (todo en `~/pruebas-tareas`; con `solo-simular` no toca nada).
- Documentación del proyecto: `src/tareas/docs/` (prompts, ADR, skill).
