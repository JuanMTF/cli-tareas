# Changelog

Formato de [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
versionado SemVer. La versión vive en `pyproject.toml` y la imprime
`cliWork version`.

## [1.1.0] - 2026-11-17

Oportunidades por defecto por ordenador: el mismo repo y el mismo `acciones.json`
sirve en varios equipos (rutas de red distintas por PC, Linux…) con un
fichero de usuario que se crea self en `~/.cliWork/configUsuario.json`
(ADR-0014). Suite: 172 pruebas.

### Añadido

- `~/.cliWork/configUsuario.json`: tus opciones por defecto (`origen`,
  `destino`, `extensiones`, `confirmar`), creado al primer uso con una
  `_ayuda` en español dentro del fichero. Lo vacío no cambia nada: manda
  `acciones.json`. Si está roto, avisa con fichero/línea/columna y sale 3.
- Prioridad de origen y destino: opción de la CLI > TU fichero > el JSON >
  «.» (menú, `mover`, `copiar`, `comprimir`, `renombrar`, `borrar`,
  `transformar`).
- Opción `--extensiones/-x` en `ejecutar` (comas o espacios, el punto se
  añade solo): manda sobre el JSON y sobre tu fichero; las extensiones
  por defecto del usuario solo entran en filtros que no traigan las suyas.
- Confirmaciones: tu `confirmar: false` apaga las preguntas de las acciones
  con «confirmar»; las de tipo `borrar` preguntan SIEMPRE con aviso
  «⚠ ATENCIÓN» (no hay papelera).

## [1.0.0] - 2026-11-19

Primera versión con la que se entrega la herramienta lista para usar: se
instala con una orden y ya incluye acciones, ayuda con IA y estado del
equipo.

### Añadido

- Instalación con una sola orden (`uv tool install .`) y fichero de
  configuración de ejemplo (`.env.example`).
- Acciones sobre ficheros definidas en el fichero de acciones: mover,
  copiar, comprimir, renombrar con plantilla, borrar, abrir en el
  navegador y transformar PDF a HTML.
- Ayuda con inteligencia artificial: resumir textos, renombrar descriptivo,
  clasificar y comprobar la conexión, con opción de simular.
- Estado del equipo: informe con uso de CPU, memoria y discos y avisos si
  se supera un umbral.
- Modo simulación (`--simular`) y menú numérico para ensayar sin tocar
  nada.
- Errores previstos en español con códigos de salida y sin trazas.

### Cambiado

- El informe del estado del equipo se pinta como tabla y las rutas se
  abrevian con `~`.

### Corregido

- El informe del estado del equipo podía fallar en equipos donde el sensor
  de frecuencia no está disponible.

## [0.1.0]

Semanas 1-2: esqueleto con uv+Typer, motor de acciones sobre `acciones.json`,
`listar`, `validar`, `--config`, plantillas de renombrar, `limpiar-usb`,
`transformar-pdf-html` e `indexar`, menú numérico y 97 pruebas.
