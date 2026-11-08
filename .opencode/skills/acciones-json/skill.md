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
  - `transformar` → requiere `origen`, `filtro` y `destino`. Escribe un HTML por fichero.
  - `comprimir` → requiere `origen`, `filtro` y `destino`. Crea un .zip con los elegidos.
- `confirmar` (bool, opcional): si es true, la CLI pregunta antes de ejecutar. En `borrar` se pregunta siempre.
- filtro opcional: extensiones (lista, en minúsculas), patron (regex válida), mas_antiguo_que_dias, mayor_que_mb.
  - `mas_antiguo_que_dias` y `mayor_que_mb` tienen que ser números > 0.
  - Un campo de filtro que no se reconozca es **aviso**, no error.
- plantilla: huecos {fecha:%Y-%m-%d}, {n:03}, {ext}, {nombre}.
  - `{fecha:...}` usa la fecha de modificación del fichero y admite cualquier formato de strftime.
  - `{n:03}` es el número de orden con ceros a la izquierda.

## Órdenes relacionadas
- `tareas validar [FICHERO]` → comprueba el JSON; errores con código de salida 3.
- `tareas acciones [NOMBRE]` → lista todas o muestra el detalle de una.
- `tareas ejecutar NOMBRE [CARPETA|URL] [--simular] [--si] [--carpeta RUTA] [--destino RUTA] [--antiguedad N]` → ejecuta.
  - La posición 2: si el tipo es `abrir`, es la URL (tiene que empezar por http/https); para el
    resto de tipos es la carpeta de origen. Indicarla en los dos sitios a la vez es error.
  - `--destino`/`-d RUTA` sobreescribe el `destino` del JSON (comprimir, copiar, mover, transformar).
  - `--antiguedad`/`-an N` sobreescribe `filtro.mas_antiguo_que_dias` del JSON (por defecto el del fichero).
  - `comprimir` y `copiar` también eligen **carpetas** (los filtros de extensión/patrón solo aplican a ficheros).
  - `--simular` no toca nada y **no pregunta**.
  - `--si` salta la confirmación (imprescindible para borrar sin interacción).
  - La ruta puede ser relativa, absoluta o `~`; se expande con `expanduser` (igual en Windows y Linux).

## Reglas al programar
- Valida el JSON en config.py ANTES de ejecutar; errores con AccionNoValida(accion, campo, motivo).
  - La fuente única está en `config.py`: `validar()`, `validar_acciones()` y las constantes
    (TIPOS_CONOCIDOS, CAMPOS_POR_TIPO, FILTRO_CONOCIDO...). `acciones.py` solo delega.
- pathlib y shutil (y zipfile para comprimir); encoding="utf-8"; nunca shell=True; nunca sobrescribir (destino_libre).
- Toda acción admite --simular y devuelve list[Resultado].
- Si añades un campo o un tipo nuevo, documéntalo en el README y en esta skill.
