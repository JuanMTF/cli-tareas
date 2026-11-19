# ADR-0014: Tus opciones por defecto por ordenador en ~/.cliWork/configUsuario.json

- Estado: aceptada
- Fecha: 2026-11-17

## Contexto

El `acciones.json` empaquetado va dentro del repo: las carpetas de
origen/destino son iguales en cualquier máquina donde corra. Pero el
caso real son **3 ordenadores**: en cada uno la ruta de red es distinta
(`//SERVIDOR/Compartido` en uno, otra unidad en otro), y en Linux las
rutas directamente no se parecen. Con solo el JSON, o se edita el JSON
por PC (rompiendo el «añadir una acción = editar el JSON, nunca el
código» con una ensalada de rutas), o se lleva un `--config` distinto
por máquina a mano en cada orden.

Además, pedía la persona que usa la CLI: poder decir «hoy solo quiero
los PDF» sin editar nada, y controlar si las acciones preguntan antes de
hacerse — salvo las de `borrar`, que deben preguntar SIEMPRE.

## Decisión

1. **Un fichero por usuario y ordenador**: `~/.cliWork/configUsuario.json`.
   Vive en el home de cada máquina, así que el mismo repo y el mismo
   `acciones.json` sirven en los 3 PCs sin tocar nada compartido.
2. **Se crea solo al primer uso** (`usuario.preparar()`, llamada desde
   `usuario.cargar()`), con valores vacíos y una clave `_ayuda` que
   explica cada campo en español DENTRO del fichero: quien no sepa
   programar abre el JSON y ve qué es cada cosa sin ir al README.
3. **Lo vacío no cambia nada**: `""` (origen/destino) o `[]`
   (extensiones) significan «manda `acciones.json` como hasta hoy».
   El fichero solo tiene poder sobre lo que definas en él.
4. **Prioridad**: opción de la CLI (`--carpeta`, `--destino`,
   `--extensiones`) > TU fichero > `acciones.json` > valores de
   fábrica. Origen y destino se leen en `motor.ejecutar` y
   `Accion._destino`; el menú propone primero tu `origen`.
5. **Extensiones** (nueva opción `--extensiones/-x` en `ejecutar`,
   comas o espacios, el punto se añade solo): la CLI manda sobre el
   filtro del JSON; si el filtro no trae `extensiones`, entran las
   tuyas. Un filtro con las suyas (p. ej. `clasificar-descargas`) no
   se toca: «hoy solo los PDF» se resuelve con `--extensiones .pdf`
   en la orden, sin editar nada.
6. **Confirmaciones**: `confirmar: false` en tu fichero apaga las
   preguntas de las acciones con `confirmar: true` en el JSON. Las de
   tipo `borrar` preguntan SIEMPRE, con aviso «⚠ ATENCIÓN» impreso
   antes (borran de verdad, no hay papelera).
7. **El fichero roto es un error de config** (código 3, como
   acciones.json): `usuario.cargar()` valida tipos y campos
   desconocidos y avisa con fichero, línea y columna. La ruta se
   calcula EN LA LLAMADA (`Path.home()`, no al importar) para que el
   sandbox de los tests (`aislado`) siga valiendo.

## Alternativas consideradas

1. **Tu fichero siempre encima del JSON** (sin huecos): un
   `ordenar-descargas` definido para `~/Descargas` iría a tu carpeta
   aunque el JSON diga otra; contradice «lo vacío no cambia nada».
2. **Poner las rutas por PC en el JSON con claves por máquina**
   (`origen-windows`, `origen-linux`): el JSON deja de ser
   compartible y quien añade una acción tiene que pensar en las 3
   máquinas; el fichero por PC ya resuelve el problema sin tocar el
   compartido.
3. **Inyectar las extensiones del usuario en TODOS los filtros**:
   rompería filtros que traen las suyas a propósito; se decidió que
   solo entren donde falta (y para el día puntual, `--extensiones`).
4. **Un comando `cliWork preparar-config`**: más control, pero una
   persona que no sabe programar puede no enterarse de que existe;
   crearse solo al primer uso con la ayuda dentro es a prueba de
   olvidos (y borrarlo regenera los valores de fábrica).

## Consecuencias

- Positivas: el repo y el `acciones.json` son 100 % portables entre
  máquinas; el cambio diario («solo PDF») es una opción de la orden;
  la ayuda viaja en el fichero; `borrar` no se puede silenciar por
  config. Suite: 172 pruebas (16 nuevas en `tests/test_usuario.py`).
- Negativas: hay DOS ficheros de config y hay que explicar la
  prioridad (README + `_ayuda`); la validación duplica parte de la de
  `config.py` (se reutiliza `_mensaje_json` y el estilo de los
  mensajes); cada acceso a `usuario.cargar()` lee y parsea el fichero
  (sin caché: es un JSON de 8 líneas, no hace falta).
- Qué haré si cambia: si un día hace falta un perfil por PC DENTRO del
  mismo fichero (p. ej. `trabajo`/`casa`), se añade como objeto
  `perfiles` con la misma regla de prioridad; si alguien necesita
  silenciar el `borrar`, será con una opción de la orden explícita
  (`--si`), nunca con el fichero de usuario.

## Verificación (17-11-2026)

- `uv run pytest`: **172 passed in 12.50 s** (156 + 16 nuevos).
- `tests/test_usuario.py` cubre: creación al primer uso con `_ayuda`,
  JSON roto → `ConfigError`, campo desconocido y tipos malos →
  `ConfigError`, tu origen/destino mandan sobre el JSON, sin nada tuyo
  manda el JSON, tus extensiones entran en filtros sin extensiones, la
  CLI manda sobre todo, los filtros con las suyas no se tocan,
  `borrar` pregunta siempre y avisa con `confirmar: false`, el
  `confirmar: false` apaga la pregunta de las demás, y una acción
  `mover` con tu fichero roto sale con código 3 y el aviso.
- `uv run cliWork version` → `cliWork 1.1.0` (pyproject, `__init__`,
  `pruebas.ps1`, README y CHANGELOG actualizados).
