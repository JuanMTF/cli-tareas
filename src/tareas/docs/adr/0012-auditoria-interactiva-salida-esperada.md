# ADR-0012: La auditoría interactiva pregunta por la salida esperada, no por «si salió bien»

- Estado: aceptada
- Fecha: 2026-11-17

## Contexto

La batería de `pruebas/` tiene un modo `-Interactivo` en el que, después de
cada paso que la máquina da por bueno, pregunta al auditor humano si lo que
ha visto en pantalla es correcto; un «n» convierte el paso en fallo.

En la sesión 4, una pasada interactiva acabó con 4 fallos que no eran
fallos de la CLI: los 4 «Marcado FALLO por el auditor» cayeron exactamente
en los 4 pasos cuyo resultado **bueno es un error rojo**:

- `validar` con un JSON roto → «Error: JSON inválido…» (código 3, es lo
  que se está probando).
- `validar` con `max_caracteres` fuera de rango → «Se encontraron 1
  errores: …» (también lo esperado).

La pregunta era «¿A la vista, ha salido OK? (s/n) [s]»: quien acaba de ver
un «Error:» en rojo contesta «n» con toda la lógica, y el test se apunta un
fallo que no existe. Peor: el resumen solo decía «48 pasos, 4 fallo(s)»,
sin decir cuáles, así que esos 4 fallos parecían un bug de la CLI.

La batería no interactiva, ejecutada en el mismo estado, dio 48/48 y
23/23 en `-SoloSimular`: el código estaba bien y lo que estaba mal era la
pregunta.

## Decisión

1. **`Paso` acepta `-ErrorEsperado`**. Los pasos que muestran un error a
   propósito lo marcan, y en modo interactivo avisan antes de preguntar:
   «(el error rojo de arriba ES lo esperado en este paso)».
2. **La pregunta cambia de forma**: «¿La salida es la esperada? (s/n) [s]»
   en vez de «¿ha salido OK?». Enter sigue siendo `s` (el caso normal) y
   un «n» se anota como verdadero fallo del auditor.
3. **El resumen final nombra los fallos**. `Paso` guarda en `$listaFallos`
   el nombre de cada paso fallido —de la máquina o del auditor, este
   último con el sufijo «(auditor)»— y el resumen los imprime antes de
   salir con código 1.

## Alternativas consideradas

1. **No preguntar nada en los pasos de error esperado**: se pierde justo
   la revisión que interesa (que el mensaje rojo se lea bien y no asuste).
2. **Auto-marcar esos pasos como OK sin preguntar**: el auditor deja de
   mirarlos y un mensaje ilegible pasaría por bueno.
3. **Contadores separados (pasos / fallos / fallos del auditor)**: más
   números en pantalla para la misma información; con el nombre del paso
   en el resumen se localiza igual de rápido.
4. **Dejar el texto «¿ha salido OK?» y solo documentarlo**: el texto es la
   causa del falso positivo; documentarlo no lo evita.

## Consecuencias

- Positivas: cero falsos fallos en los pasos de error previsto; el
  resumen es autodocumentado (se copia y se pega en el ADR o en el issue);
  el auditor sabe qué está mirando sin leerse el script.
- Negativas: la pregunta es más larga y hay que recordar marcar
  `-ErrorEsperado` al añadir un paso nuevo cuyo resultado bueno sea un
  error; si se olvida, vuelve el falso positivo (mitigado por el aviso
  previo que ya imprime el propio paso: «el error rojo DEBE salir»).
- Qué haré si cambia: si aparecen pasos con resultados «raros» que no son
  ni OK ni error (p. ej. una cancelación), se añadirá otro aviso con el
  mismo mecanismo y se documentará aquí.

## Verificación (17-11-2026)

- `pruebas.ps1 -SoloSimular`: **23 pasos, 0 fallos**, código 0.
- `pruebas.ps1` completa: **48 pasos, 0 fallos** (con dos 503 del modelo
  gratuito reintentados solos, según ADR-0004).
- Modo interactivo simulado con respuestas `n` en los 4 primeros pasos:
  el resumen lista `pytest pasa los tests (auditor)`, `version imprime
  1.0.0 (auditor)`, … y sale con código 1; respondiendo `s`, 0 fallos.
- Los 4 pasos de error previsto muestran el aviso «(el error rojo de
  arriba ES lo esperado en este paso)» antes de la pregunta.
