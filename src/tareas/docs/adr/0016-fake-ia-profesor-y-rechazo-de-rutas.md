# ADR-0016: El fake de IA del profesor y la barrera anti-ruta: se revisa, se mantiene

- Estado: aceptada
- Fecha: 2026-11-19

## Contexto

El profesor ha enviado el código de sus tests de la capa IA (sin red, sin token):
el `ProveedorFalso` con `preguntas`, el `test_limpieza` parametrizado con ids en
español (tildes y signos, ruta peligrosa, extensión, vacía), el
`test_resumir_con_un_modelo_falso` con `Motor([...]).ejecutar(...)`, el
`test_simular_no_pregunta_al_modelo`, el `test_categoria_rara_va_a_sin_clasificar`,
los de sin clave y sin red (`test_sin_red_el_mensaje_es_humano`).

## Decisión

1. **Fake `ProveedorFalso`**: comparado con el nuestro (ADR-0015), se mantiene el
   nuestro (instancia con respuesta por defecto que graba `llamadas` con
   (sistema, usuario, max_tokens)) y se deja constancia del del profe
   (fábrica con respuesta por llamada y `preguntas`). La información que los
   tests necesitan (la pregunta lleva `<documento>`) está en ambos; no se copia
   el contrato del profe sin mirar quién lo llama.
2. **Respuesta vacía**: `a_nombre_seguro("") → ""` (renombrar-ia: «saltado») se
   adopta como caso testeado (parametrizado, id `vacia`).
3. **Nombres con ruta**: el profe esperaba el sanitizado
   (`../../etc/passwd → etc-passwd`); el repo **rechaza** (`→ ""`) por la
   barrera anti-inyección. **Se mantiene el rechazo** (decisión ya tomada y
   blindada con tests; no se cambia src/ sin proponerlo).

## Alternativas consideradas

1. Adaptar `a_nombre_seguro` a sanitizar en vez de rechazar: descartada (cambio de
   comportamiento sobre una decisión ya tomada y con tests).
2. Copiar el `ProveedorFalso` del profe (fábrica + `preguntas`): descartada de
   plano (contrato distinto, misma regla que en ADR-0015: mirar quién llama antes
   de adoptar un fixture/fábrica ajena).

## Consecuencias

- Positivas: el checklist de tests de IA queda cubierto sin tocar `src/`.
- Negativas: si el profe insiste en el sanitizado de rutas, habría que reabrir
  la decisión (y con ella los tests).

## Verificación (19-11-2026)

- `uv run pytest -v`: **176 passed**.
- Snippets del profe convertidos o alineados: limpieza (tildes/signos, ruta,
  extensión, vacía), resumir con fake + `<documento>`, simular (`preguntas == []`),
  sin-clasificar, sin clave, sin red («No llego»).
