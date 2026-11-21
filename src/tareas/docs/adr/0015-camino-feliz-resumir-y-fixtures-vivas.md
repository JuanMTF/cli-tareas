# ADR-0015: Toda fixture del conftest vive de un test; resumir, con camino feliz

- Estado: aceptada
- Fecha: 2026-11-19

## Contexto

La auditoría de la sesión 4 (fixture `escribir_config` y tabla «las
fixtures, y quién las pide» de la guía del profesor) destapó dos huecos
en la suite de 172 pruebas:

1. **`modelo_falso` y su clase `ProveedorFalso` eran código muerto**:
   ningún test los pedía. La tabla de la guía decía que los usaba
   `test_ia.py`, pero aquí la capa IA se probaba con
   `proveedor_que_contesta`/`proveedor_que_rompe`; el doble que graba
   las preguntas no se usaba para nada.
2. **`resumir` no tenía camino feliz**: solo los negativos
   (`sin_texto_salta`, `simular_con_fichero_sin_texto`). En ningún
   momento se comprobaba que el `.resumen.md` se escribe de verdad con
   la respuesta del modelo ni que la pregunta viaja con el documento
   entre `<documento>` y `</documento>` — que es justo lo que la guía
   pide auditar («qué comprueba cada assert»).

Además, `test_codigo_3_json_roto` pedía la fixture `escribir_config` en
su firma y nunca la llamaba (escribe el JSON roto a mano en
`tmp_path`): un parámetro muerto que confunde a quien lea el test.

Un tercer punto, ya decidido en el Prompt 19 pero que conviene dejar
fijado aquí: **`escribir_config` no se puede sustituir por la versión
del profesor**. La suya solo acepta `str` y lista (todo lo demás lo
envuelve en `{"version": 1, "acciones": …}`), y nuestros tests le pasan
dicts completos: saldría una doble envoltura
(`{"version":1,"acciones":{"version":1,…}}`) que rompería
`test_carga_un_json_correcto` y `test_acepta_tildes_y_utf8`, y haría
pasar `test_version_distinta` y `test_acciones_no_lista` **por el
motivo equivocado**. Su versión además usa `ensure_ascii=True` por
defecto: escribe las tildes como `\u00e1` (ASCII puro, comprobado por
bytes) y `test_acepta_tildes_y_utf8` dejaría de probar UTF-8 real.

## Decisión

1. **Regla: toda fixture del conftest tiene al menos un test que la
   pida.** Si una fixture no la usa nadie, o se le escribe su test o se
   elimina. La tabla «fixtures y quién las pide» del repo es la que
   manda (la de la guía describe la suite de 28 pruebas, no la nuestra
   de 174).
2. **`resumir` gana camino feliz** (`test_resumir_escribe_el_resumen`
   en `tests/test_acciones_ia.py`), con `modelo_falso` (que por fin
   vive): estado `hecho`, el `.resumen.md` existe, contiene la
   respuesta del doble y la cabecera `# Resumen de <original>`, y en lo
   que se le preguntó está el documento entre `<documento>` y
   `</documento>`.
3. **`--simular` de resumir no pregunta al modelo**
   (`test_resumir_simular_no_pregunta_al_modelo`): se inyecta
   `proveedor_que_rompe` (revienta si le llaman) y se afirma que no se
   escribe ningún `.resumen.md`.
4. **Firma limpia**: `test_codigo_3_json_roto` deja de pedir
   `escribir_config`.
5. **`escribir_config` se queda como está** (contrato str/lista/dict +
   `ensure_ascii=False`): es un superconjunto compatible de la versión
   del profesor, pensado para los dicts de `test_config.py` y para que
   las tildes sean UTF-8 real en el fichero.

## Alternativas consideradas

1. **Sustituir `escribir_config` por la del profesor**: rompe 2 tests y
   desvirtúa 2 (ya razonado arriba); su contrato es para su suite de
   listas, el nuestro para nuestra convención de dicts. No se copia un
   fixture sin mirar quién lo llama.
2. **Que `modelo_falso` siga sin usarse (borrarlo)**: sería viable
   (`proveedor_que_contesta` cubre lo mismo para renombrar/clasificar),
   pero el ejemplo de la guía (`test_resumir_con_un_modelo_falso`)
   necesita justo el doble que GRABA preguntas, y sin él no se puede
   afirmar que el documento viaja bien formado. Elegimos darle uso.
3. **Probar `resumir` contra el modelo de verdad**: no entra en pytest
   (el modelo no contesta siempre igual y una prueba con red falla
   cuando no la hay); eso es `cliWork comprobar-ia`, como en el resto
   de la capa IA.
4. **Arreglar los 2 tests rotos adaptándolos a la versión del profe**
   (pasarles lista en vez de dict): cambiaría 4 tests y el significado
   de `test_acepta_tildes_y_utf8` para encajar en un fixture ajeno;
   nosotros no cambiamos tests para que encaje un fixture.

## Consecuencias

- Positivas: 174 pruebas, sin código muerto en el conftest; `resumir`
  tiene ahora sus dos caras cubiertas (camino feliz + sin texto), que es
  lo que pide la rúbrica («camino feliz y 3 casos feos»); las
  afirmaciones del camino feliz son auditables: cada `assert` dice qué
  comprueba (estado, fichero, cabecera, contenido, pregunta).
- Negativas: la regla «toda fixture se usa» hay que revisarla cuando se
  añade un test nuevo (si se muere un test, la fixture queda huérfana);
  `modelo_falso` devuelve la instancia mientras que el de la guía
  devuelve la clase — si algún día se copia un test de la guía hay que
  adaptarlo (`modelo_falso(...)` no funcionaría: nuestra fixture no es
  fábrica).
- Qué haré si cambia: si la guía trae tests nuevos que usan
  `modelo_falso("texto")` como fábrica, se decide entonces si pasar la
  fixture a fábrica (y tocar los usos) o adaptar el test copiado; la
  regla del punto 1 sigue mandando.

## Verificación (19-11-2026)

- `uv run pytest`: **174 passed in 15.65 s**, código 0 (172 + los 2
  nuevos).
- `test_resumir_escribe_el_resumen` en verde: el `.resumen.md` se
  escribe con la respuesta del doble y el `<documento>` llega en la
  pregunta.
- `test_resumir_simular_no_pregunta_al_modelo` en verde con
  `proveedor_que_rompe` inyectado: `--simular` no toca el modelo.
- `test_codigo_3_json_roto` sigue en verde sin pedir `escribir_config`.
- Comprobación empírica previa (Prompt 21): la versión del profe de
  `escribir_config`, ejecutada sobre los dicts de `test_config.py`,
  produce doble envoltura y ASCII con `\u00e1`; la nuestra, JSON
  correcto y UTF-8 real.
