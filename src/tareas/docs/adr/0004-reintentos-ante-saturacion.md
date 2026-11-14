# ADR-0004: Ante la saturación del proveedor: reintentar con espera, no rendirse

- Estado: aceptada
- Fecha: 2026-11-14

## Contexto

En casa el programa no usa el servidor del instituto sino un proveedor
gratuito (Z.ai, Google...). Con los modelos gratuitos pasa que, de vez en
cuando, el servidor responde 429 (demasiadas peticiones) o tarda más de
un minuto en contestar: su cola está saturada porque la comparte todo el
mundo. La primera versión se rendía a la primera y la batería de pruebas
fallaba aunque el sistema estuviera bien.

## Decisión

El programa ya manda las peticiones de una en una (una llamada por cada
fichero, sin paralelismo). Para soportar la saturación, `ia.py` añade
paciencia: si el servidor responde 429, espera 60 s (`ESPERA_429`) y
reintenta, hasta 3 intentos en total (`INTENTOS_429`); y el tiempo de
lectura pasa de 60 a 120 s (`TIEMPO_ESPERA`), porque los modelos
gratuitos cargados tardan más de un minuto en contestar. El tiempo de
espera NO cuenta en el resumen de tokens/segundos de la respuesta. Si
tras los reintentos sigue sin ir, se avisa con el mensaje de siempre
(IANoDisponible, código de salida 4) y las acciones sin IA siguen.

## Alternativas consideradas

1. Rendirse a la primera (código de referencia del profesor).
   - A favor: código más simple; el mensaje ya dice «espera un minuto».
   - En contra: una petición que iba a salir bien a los 90 segundos
     falla, y la batería de pruebas da fallos falsos.
2. Hacer una cola de peticiones propia con limitador de ritmo.
   - A favor: control total del envío.
   - En contra: el límite no lo disparamos nosotros (es la cola del
     proveedor compartido); un limitador local no lo arregla y añade
     código que no sirve.
3. La elegida: reintento con espera (429) y margen de lectura más largo.

## Consecuencias

- Positivas: los picos de saturación se aguatan solos; la batería ya no
  falla por 429 (reintenta una vez tras esperar 60 s); la respuesta
  correcta a los 90 s ya no se pierde por el tiempo agotado; el usuario
  solo ve error cuando de verdad no hay manera.
- Negativas: si el servidor está caído de verdad, el usuario espera
  hasta 3×60 s más el tiempo de cada intento antes de ver el aviso;
  cualquier peticionario impaciente puede pensar que se colgó (el
  mensaje final lo aclara, pero tarde).
- Qué haré si cambia: si los proveedores gratuitos endurecen los límites
  (más 429), se subirá INTENTOS_429 o se añadirá una espera creciente
  (60, 120, 240 s) — y si se vuelve loco el gasto, un limitador de
  ritmo propio con su propio ADR.

## Verificación (14-11-2026)

Confirmado en la práctica: la batería dio primero 429 y después
tiempo agotado; con el reintento y el margen de 120 s, los resúmenes
reales salieron (8 ficheros en ~/pruebas-tareas/Resúmenes) con
comprobar-ia en verde y 97 tests unitarios pasando.
