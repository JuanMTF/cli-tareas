# ADR-0001: Las acciones viven en acciones.json, no en el código

- Estado: aceptada
- Fecha: 2026-11-04
- Autor/a: Juan Manuel Tudo

## Contexto

Mi herramienta «tareas» automatiza tareas repetitivas con ficheros
(ordenar Descargas, renombrar fotos, limpiar temporales...). Cada persona
que la use tendrá carpetas y manías distintas, y yo mismo voy a querer
añadir acciones nuevas cada pocas semanas. [Añade TU situación: qué
acciones tienes y quién más la va a usar.]

## Decisión

Las acciones se describen en un fichero JSON externo (acciones.json) con
un esquema documentado en el README. El código solo contiene el MOTOR que
lee, valida y ejecuta ese fichero. Añadir una acción = editar el JSON.

## Alternativas consideradas

1. Escribir cada acción como una función en Python.
   - A favor: [...]
   - En contra: cada cambio exige tocar el código y volver a instalar; quien
     no programa no puede añadir acciones.
2. Usar YAML o TOML en vez de JSON.
   - A favor: [ A favor: admite comentarios (#) dentro del propio fichero, así que
     cada acción puede explicarse junto a sus datos; sintaxis menos
     ruidosa (claves sin comillas, listas más cortas); es el formato que
     este mismo proyecto ya usa en pyproject.toml y uv.lock, así que hay
     un ejemplo cerca.]
   - En contra: [ - En contra: habría que convertir el acciones.json que ya existe y
     reescribir la lectura en config.py (el validador casi no cambia);
     el coloreado de TOML es menos común en editores básicos que el de
     JSON; sería una decisión «por afinidad con uv», no por necesidad.
]
3. INI con configparser (stdlib, sin dependencias).
   - A favor: formato de toda la vida en Windows; nada que instalar.
   - En contra: configparser no tiene listas nativas y cada acción lleva
     varias (filtro.extensiones, categorias, urls...): habría que inventar
     una convención de valores separados por comas encima de un formato
     que ya se queda pequeño para los campos de las acciones IA.

## Consecuencias

- Positivas: añadir una acción no toca el código; el JSON se puede validar
  antes de ejecutar nada; [...]
- Negativas: hay que mantener la validación al día cuando el esquema
  crezca; los errores de escritura en el JSON solo se ven al ejecutar
  validar; [...]
- Qué haré si el esquema cambia: [por ejemplo, subir "version" a 2 y ...]

