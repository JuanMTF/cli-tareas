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
| `tareas indexar CARPETA` | Revisa una carpeta de PDF: convierte los que falten y actualiza `manuales.json` sin tocar lo ya hecho. |
| `tareas ejecutar NOMBRE [CARPETA\|URL]` | Ejecuta una acción. La posición 2 es URL si el tipo es `abrir`; si no, la carpeta. |

### Opciones de `indexar`

- `CARPETA` (obligatoria) — carpeta donde están los PDF a revisar. Admite `~`, `/` y `\`.
- `--destino RUTA` / `-d RUTA` — carpeta donde están los manuales convertidos. Por defecto, la del JSON (`transformar-pdf-html`).
- `--simular` — solo muestra qué haría: **no convierte ni escribe nada**.

```bash
tareas indexar C:\Users\yo\Downloads\DAM --simular   # primero mira qué haría
tareas indexar C:\Users\yo\Downloads\DAM              # convierte los nuevos y actualiza el JSON
```

### Opciones de `ejecutar`

- `--config RUTA` (global: va después de `tareas` y antes de la orden) — fichero JSON de acciones. Por defecto, el empaquetado `src/tareas/docs/acciones.json`.
- `--simular` — solo muestra qué haría: **no pregunta, no toca nada**.
- `--si` — salta la confirmación. Imprescindible para borrar sin interacción.
- `--carpeta RUTA` / `-c RUTA` — carpeta de origen; tiene prioridad sobre la del fichero. Admite `~`, `/` y `\`.
- `--destino RUTA` / `-d RUTA` — carpeta de destino; tiene prioridad sobre la del fichero de acciones. Admite `~`, `/` y `\`. Sirve para `comprimir`, `copiar`, `mover` y `transformar`.
- `--antiguedad <N>` / `-an <N>` / `-n <N>` — solo lo más viejo que N días (por defecto, el del fichero: 400 días). Sirve para `comprimir` y `copiar`.
- `--nombre TEXTO` / `-N TEXTO` — nombre del `.zip` que hace `comprimir`. Por defecto, **el de la carpeta origen** (`~/Descargas` → `Descargas.zip`).
- **Posición 2** (la que va justo después del nombre): si la acción es de tipo `abrir`, es la URL a abrir; para el resto de tipos es la carpeta de origen (lo mismo que `--carpeta`, pero no se pueden indicar las dos veces).
- `--google` / `-g`, `--firefox` / `-f`, `--edge` / `-e` — navegador (solo tipo `abrir`).

```bash
uv run tareas ejecutar ordenar-descargas ~/pruebas-tareas --simular   # carpeta en posición 2
uv run tareas ejecutar abrir-nav https://github.com --simular         # URL en posición 2
uv run tareas ejecutar comprimir-antiguos -n 10 --simular             # lo de más de 10 días
uv run tareas ejecutar comprimir-antiguos -n 30 --nombre respaldo     # .zip llamado respaldo.zip
```

**`comprimir` y `copiar` nunca sobrescriben:** si en el destino ya hay algo con ese
mismo nombre, lo renombra con ` (1)`, ` (2)`... y lo dice en el mensaje
(`(ya existía: renombrado)`). No se pierde nada de lo que ya tenías.

## Tipos de acción

Definidas en `src/tareas/docs/acciones.json`; el esquema completo está en la skill
`.opencode/skills/actions-json/skill.md`.

| Tipo | Campos necesarios | Qué hace |
|------|-------------------|----------|
| `abrir` | `urls` | Abre las URLs en el navegador. |
| `mover` | `origen`, `filtro`, `destino` | Mueve ficheros al destino. |
| `renombrar` | `filtro`, `plantilla` | Renombra con plantillas `{fecha:%Y-%m-%d}_{n:03}{ext}`. |
| `borrar` | `filtro`, `confirmar` | Borra ficheros. Siempre pregunta salvo `--simular` o `--si`. |
| `transformar` | `origen`, `filtro`, `destino` | Convierte cada PDF en una carpeta con su HTML (ver «Manuales PDF → HTML»). |
| `comprimir` | `origen`, `filtro`, `destino` | Crea un `.zip` con los ficheros y carpetas elegidos; el nombre es el de la carpeta origen (o el de `--nombre`). |
| `copiar` | `origen`, `filtro`, `destino` | Copia ficheros y carpetas al destino sin borrar el original. |
| `limpiar-usb` | `puertos_conservar`, `copia_seguridad` | Solo Windows + administrador: limpia del registro las huellas de USB e impresoras (ver «usb-del»). |

**Nunca sobrescribe:** si en el destino ya hay algo con ese nombre, añade ` (1)`, ` (2)`... (`destino_libre`) y lo avisa con `(ya existía: renombrado)`.

**`comprimir` y `copiar` también eligen carpetas:** los filtros `mas_antiguo_que_dias` y `mayor_que_mb` se aplican a carpetas y ficheros; `extensiones` y `patron` solo a ficheros. Los demás tipos (`mover`, `borrar`, `renombrar`, `transformar`) siguen siendo solo de ficheros.

**Filtro:** `extensiones` (lista), `patron` (regex), `mas_antiguo_que_dias`, `mayor_que_mb`. Basta con **uno** de los cuatro: por ejemplo, `{"mas_antiguo_que_dias": 400}` solo pide antigüedad y coge **cualquier** tipo de fichero. Si no sale nada, el mensaje dice el filtro que se aplicó.

Ejemplo mínimo:

```bash
uv run tareas validar
uv run tareas ejecutar ordenar-descargas ~/pruebas-tareas --simular  # primero mira qué haría
uv run tareas ejecutar ordenar-descargas ~/pruebas-tareas --si       # luego, sin preguntar
```

## Manuales PDF → HTML

`transformar-pdf-html` y `tareas indexar` comparten el módulo `src/tareas/html.py`.
Convierten **solo PDF** (PyMuPDF) y dejan esto en el destino:

```
HTMLtransformados/
├── index.html          ← galería con buscador: lista todos los manuales
├── estilos.css         ← UN solo css, compartido por la galería y cada manual
├── script.js           ← UN solo js: buscador + flechas de teclado
├── manuales.json       ← la «base de datos» (nombre, PDF, páginas, tamaño, fechas)
├── DATOS/
│   ├── index.html      ← el manual
│   ├── pagina-01.png   ← una imagen por página (144 dpi)
│   └── ...
└── Documento sin título/
    └── ...
```

- **Cada PDF tiene su carpeta** con el mismo nombre (sin extensión).
- **Cada página es un PNG** y encima lleva una capa de texto transparente: en el
  navegador se ve la página original y aun así funcionan Ctrl+B y copiar.
- El HTML del manual enlaza `../estilos.css` y `../script.js` (por eso hay que
  mover la carpeta entera, no suelto una sola carpeta de PDF).
- **Nunca sobrescribe lo ya convertido:** si la carpeta del PDF ya tiene su
  `index.html`, se salta.

### `tareas indexar` (mantener el índice al día)

```bash
tareas indexar C:\Users\yo\Downloads\DAM
```

Revisa la carpeta y hace **solo** esto:

1. Los PDF que **ya están convertidos**: no los toca (ni el HTML ni los PNG).
2. Los PDF **nuevos**: los convierte en su carpeta.
3. Actualiza `manuales.json` y regenera el `index.html` de la galería.
4. Si `estilos.css` o `script.js` faltan, los crea; si están, no los toca.

Si borras `manuales.json`, lo vuelve a montar con lo que ya está convertido.

## Acciones definidas

Fichero: `src/tareas/docs/acciones.json` (9 acciones válidas).

| Acción | Tipo | Qué hace |
|--------|------|----------|
| `abrir-nav` | abrir | Abre en el navegador las URLs de soporte (con `-e`/`-g`/`-f` elige el navegador). |
| `borrar-descargas` | mover | Borra de la carpeta descargas los ficheros indicados con más de 30 días. |
| `comprimir-antiguos` | comprimir | Comprime en un `.zip` (llamado como la carpeta) todo lo de más de 400 días. |
| `copiar-antiguos` | copiar | Copia todo lo de más de 400 días al destino sin borrar el original. |
| `limpiar-temporales` | borrar | Borra los `.tmp` con más de 30 días. |
| `ordenar-descargas` | mover | Mueve los PDF y documentos de Descargas a Documentos/PDF. |
| `renombrar-fotos` | renombrar | Renombra fotos con su fecha. |
| `transformar-pdf-html` | transformar | Convierte cada PDF en una carpeta con su HTML, páginas en imagen y texto buscable. |
| `usb-del` | limpiar-usb | Limpia del registro las huellas de USB e impresoras (solo Windows, como administrador). |

### `usb-del` (limpiar el registro de USB e impresoras)

Solo Windows y con **permisos de administrador** (en otro sistema o sin
elevar, error claro con código 1). Qué hace, en orden:

1. **Copia de seguridad**: exporta con `reg.exe` las claves que va a tocar a
   un único `.reg` restaurable (`copia_seguridad` del JSON; por defecto
   `~/pruebas-tareas/usb-backup.reg`).
2. **Desinstala las impresoras de verdad** (`Remove-Printer`) y vacía su clave
   de conexiones `SOFTWARE\...\CurrentVersion\Print\Printers`.
3. **Puertos USB**: borra de `SOFTWARE\...\CurrentVersion\Ports` los `USB00x`
   que no estén en `puertos_conservar` (por defecto se conservan `USB001` y `USB002`).
4. **Historial de USB**: vacía `Enum\USBSTOR`, `Enum\USB` y `MountPoints2`.
5. **Reinicio obligatorio**: avisa al empezar, y al terminar pregunta si
   reiniciar ya (con `--si` reinicia solo; con `shutdown /r`). Si respondes
   que no, deja el aviso en pantalla: **hasta reiniciar, Windows puede
   reescribir las claves**.

```bash
uv run tareas ejecutar usb-del --simular    # lista qué tocaría, sin tocar nada
uv run tareas ejecutar usb-del              # pide confirmación y pregunta el reinicio
```

Las claves de `SYSTEM\Enum` pertenecen a SYSTEM: si alguna se resiste, la
acción lo reporta como «saltado» y no aborta; la copia `.reg` permite volver
atrás desde regedit (a ser necesario con psexec -s).

## Seguridad

**Nunca hará:** borrar sin preguntar ni tocar ficheros fuera de la carpeta que le indique.

## Desarrollo

- Instalar/sincronizar dependencias: `uv sync`.
- Ejecutar: `uv run tareas --help`.
- Validar config: `uv run tareas validar`.
- Tests: `uv run pytest`.

### Instalado en el PATH (`uv tool`)

`tareas` está instalado con `uv tool install --editable .`, y eso crea **un entorno
propio** (`%APPDATA%\u\uv\tools\tareas`), distinto del `.venv` del proyecto.

**Consecuencia:** si añades una dependencia (`uv add pymupdf`), solo entra en el
entorno del proyecto. Para que la herramienta instalada también la tenga, repite:

```bash
uv tool install --editable .   # sincroniza dependencias en el entorno de la herramienta
```

Si al convertir PDF dice *«Falta la dependencia pymupdf»*, es por esto (no hace
falta reiniciar la terminal, pero sí repetir ese comando).
