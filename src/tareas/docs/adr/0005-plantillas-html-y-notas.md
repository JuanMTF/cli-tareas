# ADR-0005: HTML de manuales con plantillas por tipo y notas en el navegador

- Estado: aceptada
- Fecha: 2026-11-14

## Contexto

Los tres tipos de manuales que uso están en PDF: hay que descargarlos,
abrirlos y no se pueden modificar. La acción `transformar` ya los pasa a
HTML (página en imagen + capa de texto seleccionable, galería y
manuales.json), pero todas las plantillas salen iguales y no se les puede
añadir notas ni correcciones. El profesor planteó dos caminos: usar la IA
o enseñarle al comando plantillas según el tipo de archivo.

## Qué hay por ahí (investigación, 14-11-2026)

- **pdf2htmlEX**: el estándar de PDF→HTML con el texto nativo y el diseño
  exacto. Descartado: binario C++ aparte, dependencia externa pesada en
  Windows, y no aporta editor.
- **PyMuPDF `page.get_text("html")`**: genera HTML con CSS y posiciones
  con la dependencia que ya tenemos. Nuestro enfoque actual (imagen +
  capa de texto con `get_text("words")`) es el equivalente y ya funciona.
- **pdf-annotate.js / Hypothesis / VeloraPDF / Gamma**: capas de
  anotación sobre documentos con persistencia conectable (localStorage,
  servidor o JSON sidecar junto al fichero). Nada de esto sirve tal cual
  para HTML generado por nosotros, pero marca el modelo a copiar: las
  notas viven FUERA del HTML (sidecar o almacén del navegador) para
  sobrevivir a regenerarlo.
- **LVFS/fwupd** (firmware) y **Snappy Driver Installer Origin**
  (drivers): el modelo de catálogo que se consulta y actualiza con
  metadatos y fecha; las webs de soporte de los fabricantes no tienen
  API pública, así que lo realista es un catálogo propio de enlaces
  verificados (fecha de comprobación), no descarga automática.

Ninguna herramienta combina las tres cosas (plantillas por tipo +
editor de notas persistente + índice de firmware/drivers): se construye
paso a paso sobre la CLI.

## Decisión

1. **Paso 1 (hecho hoy): plantillas por tipo de manual.** Campo
   `plantilla` opcional en las acciones `transformar` (catálogo
   `PLANTILLAS` en config.py: `tecnico`, `esquema`, `guia`; defecto
   `tecnico`, validado como los demás campos). La plantilla va como
   clase en `<body>` y su CSS vive en el `estilos.css` compartido:
   `p-esquema` (páginas grandes, clic para hacer zoom, fondo oscuro,
   para planos y datasheets) y `p-guia` (página estrecha de lectura).
   `manuales.json` guarda qué plantilla llevó cada manual. Añadir un
   tipo de manual = una acción nueva en el JSON con su `plantilla`,
   sin tocar código (coherente con ADR-0001).
2. **Paso 2: notas y correcciones (modo editor).** Overlay en
   JavaScript sobre las páginas; las notas se guardan en el
   **localStorage** del navegador con **exportar/importar JSON** como
   copia de seguridad (límites asumidos: no viajan a otro PC ni
   navegador salvo exportando, y borrar datos del navegador las borra).
   Descartado un mini-servidor (`servir`) por ahora: es lo más robusto
   pero rompe el «doble clic y abre».
3. **Paso 3: registro enriquecido** en `manuales.json` (modelo del
   aparato, checksum y fecha del PDF) para poder avisar de que el
   original cambió y conviene regenerar.
4. **Paso 4: índice de firmware/drivers/programas**: campo `enlaces`
   por manual con fecha de comprobación; acción que los verifica
   (petición HEAD) y otra que, con la IA, extrae el modelo del manual
   para proponer la búsqueda (el patrón `clasificar` de la capa IA).
5. Más adelante: elegir plantilla con la IA a partir del contenido
   (hoy se elige con el JSON) y emparejar hardware por hardware ID.

## Alternativas consideradas

1. **pdf2htmlEX** como conversor: máxima fidelidad, pero dependencia
   externa y binaria; nuestra capa texto+imagen cubre la necesidad.
2. **Notas en un mini-servidor** (`cliWork servir`): persistencia a
   fichero garantizada (JSON sidecar), pero exige tener el servidor
   abierto; se deja para el paso 2 si el localStorage se queda corto.
3. **Notas incrustadas dentro del HTML** (descargar el HTML con las
   notas dentro): portátil al 100%, pero «guardar» implica descargar
   el fichero cada vez; peor experiencia que localStorage.
4. **IA que decida la plantilla** en el paso 1: añade una llamada al
   modelo (gasto, 429...) para algo que el JSON ya resuelve; se deja
   para más adelante.

## Consecuencias

- Positivas: cada tipo de manual se ve como le toca sin tocar código;
  la conversión no cambia de formato (mismos PNG + capa de texto) y la
  galería/JSON siguen igual; el camino de las notas está decidido y
  documentado; `manuales.json` ya lleva la semilla del registro
  enriquecido (plantilla).
- Negativas: el CSS de las tres plantillas viaja entero en
  `estilos.css` (unos bytes de más por manual); las notas del paso 2
  dependen del navegador/equipo (mitigado con exportar/importar).
- Qué haré si cambia: si el localStorage se queda corto (varios
  equipos, notas compartidas), se añade `cliWork servir` con JSON
  sidecar y su propio ADR.

## Verificación (14-11-2026)

101 tests en verde (4 nuevos: plantilla en `<body>` y registro,
defecto `tecnico` con campo vacío, plantilla inexistente rechazada,
validación del campo `plantilla`).
