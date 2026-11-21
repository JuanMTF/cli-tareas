# ADR-0017: Los tests de salida de la CLI (códigos 0-4) con `--config`: se comparan, no se sustituyen

- Estado: aceptada
- Fecha: 2026-11-19

## Contexto

El profesor ha enviado sus versiones de los tests de salida de la CLI con
`typer.testing.CliRunner`:

- `test_json_roto_sale_con_3_y_sin_traza(escribir_config)`: `--config` con JSON
  roto → `validar` → exit 3, «no es JSON válido», sin traceback.
- `test_accion_que_no_existe_sale_con_1(escribir_config, descargas)`: `--config`
  con una acción → `ejecutar inventada <descargas>` → exit 1.
- `test_opcion_que_no_existe_sale_con_2`: `listar --inventada` → exit 2.
- `test_ia_sin_clave_sale_con_4(escribir_config, tmp_path)`: `--config` con una
  acción IA → `ejecutar res <tmp>` → exit 4, «las acciones sin IA siguen
  funcionando».

## Decisión

1. Los códigos 0-4 ya están testeados con su test (0, 1, 2, 3, 4) comprobando
   `exit_code` y una frase corta de `r.output`, sin traceback donde aplica.
2. Los snippets del profe son **formulaciones alternativas** que llegan al
   mismo código por caminos distintos (con `--config` + JSON temporal, acción
   concreta, comando concreto); se comparan con los nuestros, no se sustituyen.
3. Frases: el repo dice «JSON inválido en {ruta} (línea X, columna Y)…» (y
   «las acciones sin IA siguen funcionando»); el profe en su snippet pide
   «no es JSON válido». Divergencia de redacción, mismo código.

## Alternativas consideradas

1. Sustituir los tests por los del profe: descartada (redundante; `--config`
   con JSON temporal ya se prueba en config/usuario, y el camino canónico ya
   cubre el código).
2. Adaptar los tests al estilo del profe: descartada (cambio de test por estilo
   ajeno, como con el fixture `escribir_config`).

## Consecuencias

- Positivas: el checklist de salidas (0-4) queda documentado contra la suite.
- Negativas: si el profe insiste en los snippets como única fuente, habría que
  decidir si se amplían los tests (no se elimina lo que ya cubre).

## Verificación (19-11-2026)

- `uv run pytest -v`: **176 passed**.
- Fragmentos revisados: JSON roto (frase «JSON inválido» vs «no es JSON válido»),
  acción inexistente, opción inexistente, IA sin clave («siguen funcionando»).
