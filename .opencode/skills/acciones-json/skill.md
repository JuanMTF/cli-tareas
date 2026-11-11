---
name: acciones-json
description: Reglas del fichero acciones.json de la CLI tareas (campos, tipos, filtros, plantillas y validación). Úsala siempre que crees o cambies acciones o el código que las lee (config.py, acciones.py, motor.py).
---
# Esquema de acciones.json
- Raíz: {"version": 1, "acciones": [...]}. Cada acción: nombre (único, minúsculas-con-guiones), descripcion, tipo.
- Tipos (los 7 de TIPOS_CONOCIDOS, en config.py):
  - `abrir` → requiere `urls` (lista de http:// o https://). Abre pestañas en el navegador.
  - `mover` → requiere `origen`, `filtro` y `destino`. Mueve sin sobrescribir.
  - `copiar` → requiere `origen`, `filtro` y `destino`. Copia sin borrar el original.
  - `renombrar` → requiere `filtro` y `plantilla`. Renombra en su misma carpeta.
  - `borrar` → requiere `filtro` y `confirmar`. Borra; **siempre pide confirmación salvo `--si`**.
  - `transformar` → requiere `origen`, `filtro` y `destino`. Convierte **cada PDF** en una
    carpeta `<destino>/<nombre>/index.html` con `pagina-NN.png` + capa de texto (PyMuPDF),
    y escribe en la raíz `estilos.css`, `script.js`, `manuales.json` e `index.html` (galería).
    El filtro debe ser solo `.pdf`. Lógica en `tareas/html.py` (no en `acciones.py`).
  - `comprimir` → requiere `origen`, `filtro` y `destino`. Crea un .zip con los elegidos;
    el nombre es el de la carpeta `origen` salvo que la CLI pase `--nombre` (lo inyecta el
    motor como `nombre_zip` en la configuración). Nunca sobrescribe: `destino_libre`.
  - `limpiar-usb` → requiere `puertos_conservar` (lista de nombres de puerto, ej. ["USB001","USB002"])
    y `copia_seguridad` (ruta del .reg). Solo Windows y con permisos de administrador: limpia
    del registro las huellas de USB e impresoras (Enum\USBSTOR, Enum\USB, MountPoints2,
    desinstala impresoras y borra los puertos USB00x que no se conservan). Exporta antes una
    copia .reg restaurable. La lógica vive en `acciones.py` (clase LimpiarUSB); el motor la
    ejecuta sin ficheros (caso especial en `motor.py`). El reinicio obligatorio lo pregunta
    la CLI al terminar (`--si` reinicia solo).
- `confirmar` (bool, opcional): si es true, la CLI pregunta antes de ejecutar. En `borrar` se pregunta siempre.
- filtro opcional: extensiones (lista, en minúsculas), patron (regex válida), mas_antiguo_que_dias, mayor_que_mb.
  - **Basta con UNO de los cuatro.** `{"mas_antiguo_que_dias": 400}` es un filtro válido y
    coge cualquier tipo de fichero (por eso `comprimir-antiguos` ya no lleva `extensiones`).
  - Un filtro vacío o sin ningún criterio reconocido es **error**.
  - `mas_antiguo_que_dias` y `mayor_que_mb` tienen que ser números > 0.
  - Un campo de filtro que no se reconozca es **aviso**, no error.
  - Si no se elige nada, el mensaje dice el filtro que se aplicó
    («No hay ficheros que cumplan el filtro (más antiguos que 400 días).»).
- plantilla: huecos {fecha:%Y-%m-%d}, {n:03}, {ext}, {nombre}.
  - `{fecha:...}` usa la fecha de modificación del fichero y admite cualquier formato de strftime.
  - `{n:03}` es el número de orden con ceros a la izquierda.

## Órdenes relacionadas
- `tareas validar [FICHERO]` → comprueba el JSON; errores con código de salida 3.
- `tareas acciones [NOMBRE]` → lista todas o muestra el detalle de una.
- `tareas ejecutar NOMBRE [CARPETA|URL] [--simular] [--si] [--carpeta RUTA] [--destino RUTA] [--antiguedad N] [--nombre TEXTO]` → ejecuta.
  - Opción global `--config RUTA` (en el callback, va después de `tareas`): fichero JSON de
    acciones; por defecto, el empaquetado `src/tareas/docs/acciones.json`.
  - La posición 2: si el tipo es `abrir`, es la URL (tiene que empezar por http/https); para el
    resto de tipos es la carpeta de origen. Indicarla en los dos sitios a la vez es error.
  - `--destino`/`-d RUTA` tiene prioridad sobre el `destino` del JSON (comprimir, copiar, mover,
    transformar): solo cambia dónde se escribe, **nunca pisa lo que ya hay** (destino_libre).
  - `--antiguedad`/`-an N`/`-n N` tiene prioridad sobre `filtro.mas_antiguo_que_dias` del JSON
    (por defecto el del fichero). Sirve para comprimir y copiar.
  - `--nombre`/`-N TEXTO` nombra el `.zip` de `comprimir`; en cualquier otro tipo es error (código 1).
  - `comprimir` y `copiar` también eligen **carpetas** (los filtros de extensión/patrón solo aplican a ficheros).
  - `comprimir` y `copiar` **nunca sobrescriben**: si ya hay algo con ese nombre, renombran con
    ` (1)` y lo dicen en el mensaje (`(ya existía: renombrado)`).
  - `--simular` no toca nada y **no pregunta**.
  - `--si` salta la confirmación (imprescindible para borrar sin interacción).
  - La ruta puede ser relativa, absoluta o `~`; se expande con `expanduser` (igual en Windows y Linux).
- `tareas indexar CARPETA [--destino RUTA] [--simular]` → revisa una carpeta de PDF.
  - Convierte **solo los PDF que falten**; lo ya convertido no se toca.
  - Actualiza `manuales.json` y regenera el `index.html` de la galería.
  - Por defecto guarda en el `destino` de la acción `transformar` del JSON.
  - No es una acción del JSON: es una orden propia en `cli.py` que llama a `tareas/html.py`.

## Reglas al programar
- Valida el JSON en config.py ANTES de ejecutar; errores con AccionNoValida(accion, campo, motivo).
  - La fuente única está en `config.py`: `validar()`, `validar_acciones()` y las constantes
    (TIPOS_CONOCIDOS, CAMPOS_POR_TIPO, FILTRO_CONOCIDO...). `acciones.py` solo delega.
- pathlib y shutil (y zipfile para comprimir); encoding="utf-8"; nunca shell=True; nunca sobrescribir (destino_libre).
- Para PDF se usa **pymupdf** (dependencia de `pyproject.toml`; instalada con `uv add pymupdf`), importándolo dentro de la función que convierte.
- Toda acción admite --simular y devuelve list[Resultado].
- Si añades un campo o un tipo nuevo, documéntalo en el README y en esta skill.
