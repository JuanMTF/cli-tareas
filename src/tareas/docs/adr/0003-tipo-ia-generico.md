# ADR-0003: Un único tipo IA («resumir») con instrucciones en el JSON

- Estado: aceptada
- Fecha: 2026-11-14

## Contexto

Las acciones con IA necesitan decirle al modelo qué hacer con cada fichero
(resumir apuntes, limpiar un OCR, proponer nombres, clasificar...). La
primera idea fue crear un tipo de acción por cada cosa («resumir»,
«limpiar-ocr», «clasificar»...), pero eso significa copiar cinco veces el
mismo motor (leer fichero → preguntar a la IA → escribir respuesta) y
tocar código cada vez que se quiera una tarea nueva de IA.

## Decisión

Un único tipo de acción con IA («resumir», en `TIPOS_IA` de config.py).
Lo que cambia de una acción a otra vive en el JSON: `instrucciones` (lo
que se le pide al modelo), `max_caracteres` (cuánto texto se envía como
máximo, 500–50000, por defecto 12000) y `categorias` (si va, limita las
respuestas del modelo a esa lista). La clase base `AccionIA` construye la
pregunta con el documento entre `<documento>...</documento>` y el sistema
avisando de que eso es material a tratar, NUNCA instrucciones; el motor
inyecta el proveedor (que lee el `.env`) y con `--simular` no se llama al
modelo: solo se cuenta cuántos caracteres se enviarían.

## Alternativas consideradas

1. Un tipo por tarea (resumir, limpiar-ocr, clasificar...).
   - A favor: los nombres del JSON describen la intención de un vistazo.
   - En contra: el mismo código cinco veces; cada acción nueva toca
     config.py, acciones.py, la skill y las pruebas.
2. Meter la IA dentro de los tipos ya existentes (p. ej. una opción
   «resumir: true» en «transformar»).
   - A favor: menos tipos en el catálogo.
   - En contra: mezcla lo que funciona sin red con lo que necesita
     proveedor; si la IA falla, la transformación quedaría coja.
3. El elegido: un tipo IA genérico y acciones «resumir» con
   instrucciones distintas en el JSON (resumir-apuntes, limpiar-ocr,
   renombrar-descriptivo, clasificar-descargas).

## Consecuencias

- Positivas: añadir una acción IA = editar el JSON (igual que el resto,
  ADR-0001); el texto del fichero NUNCA se interpreta como instrucciones
  (van en <documento>); --simular no gasta tokens ni pide .env; la
  validación vive en config.py (validar_ia) como el resto de campos.
- Negativas: el nombre del tipo («resumir») no siempre describe lo que
  hace la acción (limpiar-ocr «resume» un OCR); las instrucciones son
  texto libre y un despiste ahí se paga en respuestas raras del modelo.
- Qué haré si cambia: si una acción IA necesita hacer algo que «resumir»
  no cubre (por ejemplo, renombrar ficheros de verdad a partir de la
  respuesta del modelo), se creará una subclase nueva de AccionIA con su
  propio tipo y su ADR.

## Verificación (14-11-2026)

Funciona de verdad: 8 resúmenes reales de apuntes generados con
resumir-apuntes en ~/pruebas-tareas/Resúmenes (con servidor de Z.ai y con
el de Google), y la batería de pruebas lo cubre en simulación.

La referencia del profesor de la semana 3 confirma esta decisión y
aporta un formato que se adoptó: el resumen .md lleva la cabecera
«# Resumen de <nombre>». En cambio, su validar_ia NO exige
«instrucciones»; aquí sí, porque una acción IA sin instrucciones
preguntaría al modelo con el mensaje del sistema vacío.

La misma referencia anuncia «renombrar-ia» y «clasificar» como tipos
propios: cuando llegue esa parte, serán subclases de AccionIA (renombrar
aplicará el nombre propuesto validándolo; clasificar moverá por
categoría o informará), y «clasificar-descargas» cambiará de
«resumir» a «clasificar». El tipo genérico «resumir» se queda tal cual
para el resto (limpiar-ocr, resumir-apuntes).
