# Changelog

Formato de [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
versionado SemVer. La versión vive en `pyproject.toml` y la imprime
`cliWork version`.

## [1.0.0] - 2026-11-17

Primera versión «para quien la usa»: se instala con una orden
(`uv tool install .`), el `.env.example` documenta la configuración y la
suite (156 pruebas) corre en CI en Ubuntu, macOS y Windows.

### Añadido

- Acciones sobre ficheros definidas en `acciones.json` (ADR-0001): mover,
  copiar, comprimir, renombrar con plantilla, borrar, abrir URLs y
  transformar PDF a HTML (páginas en imagen + texto buscable, ADR-0005).
- Capa IA detrás de una interfaz (ADR-0002/0003): `ProveedorIA` abstracta y
  `ProveedorCentro` compatible con la API de OpenAI, configurado por `.env`
  (`CENTRO_IA_URL/KEY/MODELO/CA`, sin claves en el código ni en el repo).
- Acciones IA: `resumir` (con pypdf/pymupdf), `renombrar-ia` y `clasificar`.
  `comprobar-ia` para ver si el proveedor va bien sin enseñar la clave.
- Seguro ante el modelo: la respuesta se limpia y valida antes de usarla —
  `a_nombre_seguro` para nombres (jamás una ruta) y categorías cerradas del
  JSON con `sin-clasificar/` como salida de escape; los ficheros sin texto
  (PDF escaneado, fichero vacío) se saltan sin gastar una llamada.
- `estado-pc`: informe del equipo (CPU, memoria, discos, temperaturas,
  batería, arranque) en tabla, con avisos por umbrales del JSON (ADR-0008/0009).
- `--simular` para ensayar sin tocar nada (cuenta caracteres, no llama al
  modelo), `--menu` con números e `indexar` para lo ya convertido.
- Salida limpia de errores previstos: `TareasError` con mensajes en español,
  códigos de salida 1/3/4 según el tipo, nunca un traceback (ADR-0011).
- Suite de 156 pruebas con fixtures en `tests/conftest.py` (sin red) y CI en
  GitHub Actions para Ubuntu, macOS y Windows (`.github/workflows/pruebas.yml`).

### Cambiado

- El informe de `estado-pc` es multilínea y la CLI lo pinta como tabla;
  las etiquetas de disco van sin la barra final («Disco C», ADR-0010).
- Las rutas de la simulación se abrevian con `~` y la columna «Detalle»
  solo aparece si algún resultado la trae.
- La batería de `pruebas/` reordena su carpeta de pytest antes de correr
  (si quedó bloqueada, usa otra) y reintenta el 429 y los 5xx del modelo
  gratuito (hasta 3 intentos).

### Corregido

- El modo `-Interactivo` de la batería marcaba fallos donde no los había:
  preguntaba «¿ha salido OK?» también en los pasos cuyo resultado bueno
  es un error rojo (JSON roto, `max_caracteres` fuera de rango). Esos
  pasos ahora avisan y la pregunta es «¿la salida es la esperada?»; el
  resumen final nombra cada paso fallido (ADR-0012).
- La línea «Para el examen:» de los resúmenes salía vacía: instrucciones v2
  con prefijo literal y formato cerrado.
- `clasificar` con una categoría fuera de la lista acumulaba carpetas
  sueltas: ahora todo lo que no encaja va a `sin-clasificar/`.

## [0.1.0]

Semanas 1-2: esqueleto con uv+Typer, motor de acciones sobre `acciones.json`,
`listar`, `validar`, `--config`, plantillas de renombrar, `limpiar-usb`,
`transformar-pdf-html` e `indexar`, menú numérico y 97 pruebas.
