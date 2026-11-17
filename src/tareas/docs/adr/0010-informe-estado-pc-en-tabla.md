# ADR-0010: El informe de «estado-pc» se pinta como tabla en la CLI

- Estado: aceptada
- Fecha: 2026-11-15

## Contexto

Con los avisos (ADR-0009), el informe de «estado-pc» se quedó todo en UNA
línea larga unida por « · »: fácil de perderse, y los «AVISO: ...» se
mezclan con las medidas. La CLI ya usa Rich para las demás tablas (menú,
«acciones», simulación), así que lo natural es que el informe se vea como
una tabla también.

## Decisión

1. **La acción devuelve el informe MULTILÍNEA** (una medida por línea, en
   la forma «Componente: dato», y los «AVISO: ...» al final): el
   `Resultado.mensaje` sigue siendo un texto plano, así que cualquier
   camino que lo imprima (echo, simulación, logs) sigue funcionando sin
   conocer Rich.
2. **La CLI lo pinta como tabla** (`_mostrar_informe_estado` en cli.py):
   título = primera línea («Estado del equipo (win32)»), columnas
   «Componente / Dato», cortando cada línea en el PRIMER «: » (los discos
   llevan su dos puntos en la etiqueta y el separador es «dos puntos +
   espacio»). Los «AVISO: ...» van como fila a lo ancho, destacados en
   amarillo. `--simular` y el resumen de «1 hecho(s)» no cambian.
3. **Las etiquetas de disco van SIN la barra final** («Disco C», no
   «Disco C:\»): el mountpoint de psutil es «C:\» y el escapado de Rich
   lo dejaba feo (y «Disco C:\» + «: » de separador confunde el corte).
   `rstrip("\\/: ")` sobre el mountpoint (en Linux «/» se conserva).

## Alternativas consideradas

1. **Tabla construida dentro de la acción** (acciones.py importando Rich):
   mezclaría presentación con datos; la acción pertenece al motor y puede
   ejecutarse sin la CLI (tests, automatización). Descartado.
2. **Un Resultado por medida** (filas «gratis»): rompería el resumen
   («1 hecho(s)» pasaría a «8 hecho(s)») y obligaría a inventar
   origen/destino falsos para la tabla de simulación.
3. **JSON estructurado en el mensaje** para parsearlo en la CLI: más frágil
   que el formato «Componente: dato» que ya es legible por sí mismo.
4. **Dejar el texto de una línea**: el usuario pidió tabla; Rich ya está
   en las dependencias.

## Consecuencias

- Positivas: el informe se lee de un vistazo; los avisos destacados y sin
  confusión; la acción sigue devolviendo texto plano (compatible con
  `--simular`, tests y cualquier echo); un solo sitio que pinta (la CLI).
- Negativas: el formato del mensaje («Componente: dato») es un contrato
  entre acciones.py y cli.py — si se cambia el formato del informe, la
  tabla hay que tocarla; las líneas que no encajan caen a la columna
  «Componente» a lo ancho (pérdida elegante, no traceback).
- Qué haré si cambia: si una acción quisiera SU tabla propia, se seguiría
  el mismo patrón (mensaje multilínea + pintor en cli.py); si el informe
  necesitara columnas distintas por bloque, entonces sí haría falta un
  formato estructurado con su ADR.

## Verificación (15-11-2026)

`uv run cliWork validar` → ✔ 15 acciones; **146 tests en verde** con 1
nuevo (`test_estado_pc_se_pinta_como_tabla`: título, cabecera
«Componente», fila de memoria y «AVISO: CPU al» dentro de la tabla, con
umbrales a 1% para que dispen seguros). Prueba real: la tabla sale con
CPU, Memoria, Disco C / Disco D (sin barra en la etiqueta), Temperaturas,
Batería y el AVISO del disco en amarillo. Skill y README actualizados.
