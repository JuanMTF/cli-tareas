# ADR-0002: El proveedor de IA es cualquier servidor compatible con la API de OpenAI, configurado en .env

- Estado: aceptada
- Fecha: 2026-11-14

## Contexto

La capa de IA (`src/tareas/ia.py`) sirve para que la CLI consulte a un
modelo: comprobar la conexión (`comprobar-ia`) y, más adelante, clasificar
o resumir ficheros. El servidor previsto es el del instituto, pero solo se
llega a él estando en su red, y yo trabajo en casa la mayor parte del
tiempo. Además no todos los proveedores hablan el mismo protocolo
(OpenAI, Anthropic...), y la clave no puede escribirse en el código ni
commitarse.

## Decisión

El código no conoce ningún servidor concreto: `ProveedorCentro` habla el
formato de la API de OpenAI (`POST {url}/chat/completions` con
`Authorization: Bearer`) y todo lo variable vive en `.env`
(`CENTRO_IA_URL`, `CENTRO_IA_KEY`, `CENTRO_IA_MODELO`, `CENTRO_IA_CA`).
En casa apunto a un proveedor público compatible con ese formato
(https://api.z.ai/api/paas/v4 con un modelo gratuito como
`glm-4.7-flash`); en el centro cambio las tres líneas del `.env` por las
del servidor del instituto. El nombre `CENTRO_IA_*` es solo el nombre de
la variable: no obliga a usar el servidor del centro.

## Alternativas consideradas

1. Fijar la URL y el modelo del centro dentro del código (constantes).
   - A favor: cero configuración; no se puede equivocar nadie el `.env`.
   - En contra: en casa no funciona (la red del centro no se alcanza),
     y cualquier cambio de servidor o modelo obliga a tocar código y
     reinstalar; la clave acabaría tentando a escribirla cerca.
2. Un proveedor por protocolo, con clases separadas (OpenAI, Anthropic...)
   y una variable que elija cuál usar.
   - A favor: aprovecharía las funciones específicas de cada proveedor.
   - En contra: mucho código para algo que la CLI solo usa para pedir
     texto y recibir texto; más dependencias y más superficie de error.
3. Un solo formato (el de OpenAI) y que quien quiera usar otro proveedor
   lo exponga con un servidor compatible (es lo que hacen casi todos).
   - Es la elegida: el centro puede levantar su servidor compatible y en
     casa vale cualquier proveedor con endpoint `/chat/completions`.

## Consecuencias

- Positivas: mismo código en casa y en el centro (solo cambia el `.env`);
  el `.env` no se sube a git, así que las claves no se commitean; los
  errores de red, clave, certificado y formato se traducen a
  `IANoDisponible` con mensaje en español y código de salida 4; añadir un
  modelo nuevo es una línea del `.env`.
- Negativas: la configuración es fácil de equivocar (el fallo del
  400 del 13-11 fue texto pegado dentro de `CENTRO_IA_MODELO`); el `.env`
  solo se encuentra ejecutando desde la carpeta del proyecto, porque se
  busca desde el directorio actual; en casa gasto cuota del proveedor
  público (por eso las pruebas usan `max_tokens=5`).

- Documentación: la plantilla `.env.example` vive en la raíz del
  repositorio y el README la explica (copiarla como `.env`, que git ignora);
  sin cambio en la decisión, solo se precisó dónde está la plantilla. El
  `.env` se busca primero en la raíz del proyecto y luego en `~/.cliWork/`
  (config personal de la instalación), para que `comprobar-ia` funcione desde
  cualquier carpeta.

- Qué haré si cambia algo: si el centro cambia de modelo, se marca en
  `CENTRO_IA_MODELO` sin tocar código; si algún día un proveedor deja de
  ser compatible con el formato de OpenAI, entonces se planteará la
  alternativa 2 (un proveedor por protocolo) en otro ADR.
