# tareas

Mi herramienta de línea de órdenes para automatizar tareas repetitivas con ficheros.

## Spec (versión 0 · 26/10/2026)
1. **Problema:** cada semana pierdo tiempo en Descargar el Firmware y manuales de varios equipos,  (ej.: ordenar Descargas a mano).
2. **Para quién:** para mí y para la oficina.
3. **Cómo se usa:** `tareas ORDEN [CARPETA] [opciones]` desde cualquier terminal.
4. **Órdenes de la semana 1:** `tareas --help`, `tareas version`, `tareas listar [CARPETA]`.
5. **Órdenes previstas:** `tareas acciones`, `tareas validar`, `tareas ejecutar NOMBRE --simular`.
6. **Mis 3 acciones (borrador):** descargar , Cambiar nombre, ordenar .
7. **Nunca hará:** borrar sin preguntar ni tocar ficheros fuera de la carpeta que le indique.
8. **Plataformas:** Linux primero; también Windows y macOS.
9. **Códigos de salida:** 0 bien · 1 fallo al ejecutar · 2 uso incorrecto · 3 configuración inválida.
10. **Instalación:** `uv tool install --editable .` (lo completo en la semana 4).

## Órdenes disponibles

| Orden | Qué hace |
|-------|----------|
| `tareas --help` | Ayuda general. |
| `tareas version` | Muestra la versión (`tareas 0.1.0`). |
| `tareas listar [CARPETA]` | Tabla con el contenido de una carpeta (por defecto, la actual). |
| `tareas acciones [NOMBRE]` | Lista las acciones o muestra el detalle de una. |
| `tareas validar [FICHERO]` | Comprueba el JSON de acciones. Sale con código 3 si algo falla. |
| `tareas ejecutar NOMBRE [CARPETA\|URL]` | Ejecuta una acción. La posición 2 es URL si el tipo es `abrir`; si no, la carpeta. |

### Opciones de `ejecutar`

- `--simular` — solo muestra qué haría: **no pregunta, no toca nada**.
- `--si` — salta la confirmación. Imprescindible para borrar sin interacción.
- `--carpeta RUTA` / `-c RUTA` — carpeta de origen, sobreescribe la del fichero. Admite `~`, `/` y `\`.
- **Posición 2** (la que va justo después del nombre): si la acción es de tipo `abrir`, es la URL a abrir; para el resto de tipos es la carpeta de origen (lo mismo que `--carpeta`, pero no se pueden indicar las dos veces).
- `--google` / `-g`, `--firefox` / `-f`, `--edge` / `-e` — navegador (solo tipo `abrir`).

```bash
uv run tareas ejecutar ordenar-descargas ~/pruebas-tareas --simular   # carpeta en posición 2
uv run tareas ejecutar abrir-nav https://github.com --simular         # URL en posición 2
```

## Tipos de acción

Definidas en `src/tareas/docs/acciones.json`; el esquema completo está en la skill
`.opencode/skills/acciones-json/skill.md`.

| Tipo | Campos necesarios | Qué hace |
|------|-------------------|----------|
| `abrir` | `urls` | Abre las URLs en el navegador. |
| `mover` | `origen`, `filtro`, `destino` | Mueve ficheros al destino. |
| `renombrar` | `filtro`, `plantilla` | Renombra con plantillas `{fecha:%Y-%m-%d}_{n:03}{ext}`. |
| `borrar` | `filtro`, `confirmar` | Borra ficheros. Siempre pregunta salvo `--simular` o `--si`. |
| `transformar` | `origen`, `filtro`, `destino` | Genera un HTML por fichero para verlo en el navegador. |
| `comprimir` | `origen`, `filtro`, `destino` | Crea un `.zip` con los ficheros elegidos. |

**Nunca sobrescribe:** si el destino ya existe, añade ` (1)`, ` (2)`... (`destino_libre`).

**Filtro:** `extensiones` (lista), `patron` (regex), `mas_antiguo_que_dias`, `mayor_que_mb`.

Ejemplo mínimo:

```bash
uv run tareas validar
uv run tareas ejecutar ordenar-descargas ~/pruebas-tareas --simular  # primero mira qué haría
uv run tareas ejecutar ordenar-descargas ~/pruebas-tareas --si       # luego, sin preguntar
```