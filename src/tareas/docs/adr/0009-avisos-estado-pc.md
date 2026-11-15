# ADR-0009: Avisos de «estado-pc» con umbrales en el JSON («avisos»)

- Estado: aceptada
- Fecha: 2026-11-15

## Contexto

El informe de «estado-pc» (ADR-0008) da los datos pero no opina: hay que
leer el 73% del disco C: y pensar si eso es mucho. El propio ADR-0008 lo
dejaba previsto: «si se quisieran alertas (aviso si un disco pasa del
90%), sería un campo nuevo del JSON (avisos, umbrales) con su ADR». Lo que
se pide ahora es justo eso: que el informe AVISE cuando algo va alto, sin
que el usuario tenga que interpretar cifras.

## Decisión

1. **Campo opcional `avisos` en las acciones de tipo `estado-pc`**: un
   objeto con umbrales en % — `{"disco_pct": 70, "memoria_pct": 85,
   "cpu_pct": 90}`. Claves conocidas: `disco_pct`, `memoria_pct`,
   `cpu_pct` (`AVISOS_CONOCIDOS` en config.py); valores enteros del 1 al
   100 (un `bool` no vale). Sin el campo, ningún aviso.
2. **Aviso = medido >= umbral.** Al final del informe se añaden líneas
   «AVISO: Disco C:\ al 73% (umbral 70%)» — al final porque es lo que hay
   que leer primero. Un aviso NO es un error: el estado del Resultado
   sigue siendo «hecho» y el código de salida 0 (solo informa; el que
   decide qué hacer con el aviso es quien lee).
3. **Cada disco se avisa por separado** (el C: puede ir lleno y el D: no).
   Los sensores que no están disponibles no generan aviso (no hay medida,
   no hay comparación).
4. La validación vive en `config.validar()` (claves y rangos, con
   `AccionNoValida`) y el campo va en `CAMPOS_OPCIONALES_POR_TIPO` para
   que `validar` no lo avise como «campo de más».

## Alternativas consideradas

1. **Umbrales por defecto en el código** (avisa siempre, el JSON solo los
   cambia): rompería ADR-0001 (la configuración manda) y sorprendería a
   quien no pidió avisos. Descartado: sin `avisos`, cero avisos.
2. **Nuevo estado de Resultado «aviso»**: rompería el recuento del
   resumen (hechos/simulados/saltados) y el «nada que hacer» del final;
   el aviso es contenido del informe, no un estado de la ejecución.
3. **Umbral por disco** (`avisos: {"C:": 70}`): más fino pero obliga a
   conocer las etiquetas de cada equipo y no se traslada entre máquinas;
   un solo `disco_pct` para todos es simple y suficiente aquí.
4. **Avisos en rojo por stderr como los errores**: confundiría aviso con
   fallo. Los avisos van dentro del informe, en su texto.

## Consecuencias

- Positivas: el informe dice lo que importa sin interpretarlo; umbrales
  editables por acción en el JSON (cada equipo los suyos, ADR-0001);
  validación con mensaje claro; el aviso no altera códigos de salida ni
  automatizaciones existentes.
- Negativas: los avisos de CPU son momentáneos (la carga se mide en una
  muestra de 0,5 s — un pico de un segundo puede avisar); un aviso no
  persiste ni se historiza (eso sería otra decisión con otro ADR).
- Qué haré si cambia: si hicieran falta avisos por temperatura o batería,
  se añadirían claves a `AVISOS_CONOCIDOS` (el diseño ya lo soporta); si
  se quisiera historial/alertas programadas, tendría su propio ADR.

## Verificación (15-11-2026)

`uv run cliWork validar` → ✔ 15 acciones; **144 tests en verde** con 10
nuevos en `tests/test_estado_pc.py`: umbrales válidos pasan, 6 casos mal
puestos rechazados (rango, tipo, bool, clave desconocida, no-objeto),
umbral 1% dispara AVISO de CPU/memoria/disco, sin `avisos` no hay avisos
y el aviso no cambia el estado («hecho»). Prueba real en este equipo:
«AVISO: Disco C:\ al 73% (umbral 70%)» al final del informe. Skill y
README actualizados.
