---
name: acciones-json
description: Reglas del fichero acciones.json de la CLI cliWork (campos, tipos, filtros, plantillas y validación). Úsala siempre que crees o cambies acciones o el código que las lee (config.py, acciones.py, motor.py).
---
# Esquema de acciones.json
- Raíz: {"version": 1, "acciones": [...]}. Cada acción: nombre (único, minúsculas-con-guiones), descripcion, tipo.
- Tipos (los de TIPOS_CONOCIDOS, en config.py):
  - `abrir` → requiere `urls` (lista de http:// o https://). Abre pestañas en el navegador.
  - `mover` → requiere `origen`, `filtro` y `destino`. Mueve sin sobrescribir.
  - `copiar` → requiere `origen`, `filtro` y `destino`. Copia sin borrar el original.
  - `renombrar` → requiere `filtro` y `plantilla`. Renombra en su misma carpeta. Admite
    opcionalmente `origen` (carpeta por defecto cuando la CLI no pasa `-r`/`-c`; está en
    `CAMPOS_OPCIONALES_POR_TIPO` para que `validar` no avise de que «le sobra»).
  - `borrar` → requiere `filtro` y `confirmar`. Borra; **siempre pide confirmación salvo `--si`**.
    Admite `origen` opcional (como las demás acciones sobre ficheros: el motor la usa
    de carpeta de trabajo y el menú la propone por defecto).
  - `transformar` → requiere `origen`, `filtro` y `destino`. Convierte **cada PDF** en una
    carpeta `<destino>/<nombre>/index.html` con `pagina-NN.png` + capa de texto (PyMuPDF),
    y escribe en la raíz `estilos.css`, `script.js`, `manuales.json` e `index.html` (galería).
    El filtro debe ser solo `.pdf`. Lógica en `tareas/html.py` (no en `acciones.py`).
    Opcional: `plantilla` (una de `tecnico`, `esquema`, `guia`; por defecto `tecnico`,
    validado en `config.validar()`): la elegida va como clase en `<body>` (`p-esquema`
    = páginas grandes y clic para hacer zoom, para planos; `p-guia` = página estrecha
    de lectura) y queda guardada en `manuales.json`. Con una acción por tipo de manual
    se elige la plantilla sin tocar código.
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
  - `estado-pc` → sin campos propios (ni carpeta ni ficheros). Informe SOLO LECTURA del
    equipo: CPU (uso, núcleos, frecuencia), memoria RAM y swap, discos montados (% y
    libres), temperaturas, batería y cuándo se encendió. Lee con `psutil` (dependencia
    del proyecto): no escribe ni toca nada del sistema. Cada bloque va con try/except:
    lo que el sistema no exponga (p. ej. temperaturas en mucha placa Windows) sale como
    «no disponible» y el informe sigue. El motor la ejecuta sin ficheros (caso especial
    en `motor.py`) y el menú NO le pregunta carpeta. No es acción IA.
    Opcional: `avisos` (objeto con umbrales en %: `disco_pct`, `memoria_pct`, `cpu_pct`;
    enteros del 1 al 100, validados en `config.validar()`): si lo medido llega al
    umbral, el informe acaba con líneas «AVISO: ...» (el estado sigue siendo «hecho»,
    un aviso no es un error). Sin `avisos`, ningún aviso.
  - `resumir` (acción IA, en `TIPOS_IA`) → requiere `filtro` e `instrucciones` (lo que se le
    pide al modelo, texto no vacío). Opcionales: `origen` (carpeta; la CLI manda con `-c`),
    `destino` (si no hay, el resumen se escribe junto al fichero), `max_caracteres` (entero
    de 500 a 50000; por defecto 12000: tope de texto que se envía al modelo, se valida en
    `config.validar_ia()`) y `categorias` (lista no vacía; el mensaje del sistema solo
    acepta respuestas de esa lista). Escribe «`<nombre>.resumen.md`» en el destino con
    `destino_libre` (nunca pisa). El motor inyecta el proveedor (`ProveedorCentro.desde_entorno()`,
    lee el `.env`) antes de ejecutar; con `--simular` NO se construye el proveedor ni se
    llama al modelo: solo dice cuántos caracteres enviaría. El documento va entre
    `<documento>` y `</documento>` y el sistema avisa de que eso es material a tratar,
    nunca instrucciones. `leer_texto()` lee .txt/.md (utf-8) y .pdf con pymupdf.
  - `renombrar-ia` (acción IA, en `TIPOS_IA`) → requiere `filtro` e `instrucciones`.
    Opcionales: `origen`, `destino` (sin destino renombra en la propia carpeta del
    fichero) y `max_caracteres`. Pide al modelo un nombre (2-6 palabras, minúsculas,
    guiones) y la respuesta pasa SIEMPRE por `a_nombre_seguro()`: primera línea,
    fuera la extensión si la pone, sin tildes, solo [a-z0-9-], 60 caracteres como
    mucho (una respuesta con `/` o `\` → vacío). Vacío → «saltado» y no se toca nada.
    Conserva la extensión original y renombra con `destino_libre` (nunca pisa).
  - `clasificar` (acción IA, en `TIPOS_IA`) → requiere `filtro`, `categorias` y
    `destino`. Opcionales: `origen`, `instrucciones` (el mensaje lo genera la acción,
    con `categorias` como únicas respuestas válidas) y `max_caracteres`. El modelo
    elige UNA categoría (se compara limpiando ambas con `a_nombre_seguro`); los
    ficheros cuya respuesta no encaja se acumulan en `destino/sin-clasificar/`.
    Siempre se mueve con `destino_libre` (nunca pisa).
- `confirmar` (bool, opcional): si es true, la CLI pregunta antes de ejecutar. En `borrar` se pregunta siempre.
- filtro opcional: extensiones (lista, en minúsculas), patron (regex válida), mas_antiguo_que_dias, mayor_que_mb.
  - **Basta con UNO de los cuatro.** `{"mas_antiguo_que_dias": 400}` es un filtro válido y
    coge cualquier tipo de fichero (por eso `comprimir-antiguos` ya no lleva `extensiones`).
  - Un filtro vacío o sin ningún criterio reconocido es **error**.
  - `mas_antiguo_que_dias` y `mayor_que_mb` tienen que ser números > 0.
  - Un campo de filtro que no se reconozca es **aviso**, no error.
  - Si no se elige nada, el mensaje dice el filtro que se aplicó
    («No hay ficheros que cumplan el filtro (más antiguos que 400 días).»).
- plantilla: huecos {fecha:%Y-%m-%d}, {n}, {n:03}, {ext}, {nombre}, {base}.
  - `{fecha:...}` usa la fecha de modificación del fichero y admite cualquier formato de strftime.
  - `{n}` es el número de orden sin ceros (1, 2, 3...); `{n:03}` lo pone con ceros (001).
  - `{base}` es el nombre genérico que pasa la CLI con `--nombre`/`-N`; sin ella cae a «Captura».
    El motor lo inyecta como `nombre_generico` en la configuración (ver motor.py).

## Órdenes relacionadas
- `cliWork --menu` (o `cliWork menu`) → menú con números: tabla de acciones,
  eliges el número y ejecuta de verdad (reutiliza «ejecutar», así que salen
  las confirmaciones de borrar/abrir). La carpeta se pregunta con la «origen»
  del JSON como defecto visible (Intro la usa tal cual; sin «origen» hay que
  escribirla). Para `--simular`, navegador o carpetas distintas, la orden es
  `cliWork ejecutar NOMBRE ...`. Si una acción falla, el menú sigue vivo.
- `cliWork validar [FICHERO]` → comprueba el JSON; errores con código de salida 3.
- `cliWork acciones [NOMBRE]` → lista todas o muestra el detalle de una.
- `cliWork ejecutar NOMBRE [CARPETA|URL] [--simular] [--si] [--carpeta RUTA] [--destino RUTA] [--antiguedad N] [--nombre TEXTO]` → ejecuta.
  - Opción global `--config RUTA` (en el callback, va después de `cliWork`): fichero JSON de
    acciones; por defecto, el empaquetado `src/tareas/docs/acciones.json`.
  - La posición 2: si el tipo es `abrir`, es la URL (tiene que empezar por http/https); para el
    resto de tipos es la carpeta de origen. Indicarla en los dos sitios a la vez es error.
  - `--destino`/`-d RUTA` tiene prioridad sobre el `destino` del JSON (comprimir, copiar, mover,
    transformar): solo cambia dónde se escribe, **nunca pisa lo que ya hay** (destino_libre).
  - `--antiguedad`/`-an N`/`-n N` tiene prioridad sobre `filtro.mas_antiguo_que_dias` del JSON
    (por defecto el del fichero). Sirve para comprimir y copiar.
  - `--nombre`/`-N TEXTO`: en `comprimir` nombra el `.zip`; en `renombrar` es el nombre
    genérico para el hueco `{base}` (por defecto, «Captura»). En cualquier otro tipo es error (código 1).
  - `--carpeta`/`-c`/`-r RUTA` tiene prioridad sobre el `origen` del JSON (para los tipos
    que tienen carpeta: mover, copiar, comprimir, transformar, renombrar...).
  - `comprimir` y `copiar` también eligen **carpetas** (los filtros de extensión/patrón solo aplican a ficheros).
  - `comprimir` y `copiar` **nunca sobrescriben**: si ya hay algo con ese nombre, renombran con
    ` (1)` y lo dicen en el mensaje (`(ya existía: renombrado)`).
  - `--simular` no toca nada y **no pregunta**.
  - `--si` salta la confirmación (imprescindible para borrar sin interacción).
  - La ruta puede ser relativa, absoluta o `~`; se expande con `expanduser` (igual en Windows y Linux).
- `cliWork indexar CARPETA [--destino RUTA] [--simular]` → revisa una carpeta de PDF.
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
