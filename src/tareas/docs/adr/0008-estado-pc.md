# ADR-0008: «estado-pc»: informe del equipo con psutil, sin IA y sin tocar nada

- Estado: aceptada
- Fecha: 2026-11-15

## Contexto

El profesor enseñó un comando que saca el estado del equipo (discos,
memoria, CPU, temperaturas...) sin dañarlo. Se pide implantarlo en la CLI
como acción «estado-pc». Las preguntas de diseño: ¿es acción IA?, ¿usa
carpetas?, y ¿cómo se lee el hardware en Windows/Linux/macOS respetando la
norma del repo (nada de `os.system` ni `shell=True`)?

## Decisión

1. **Tipo propio `estado-pc`, NO acción IA.** Es una acción de solo lectura
   contra el sistema: el modelo no aporta nada aquí (los datos ya están en
   el equipo). No entra en `TIPOS_IA`; el motor no le inyecta proveedor y
   con `--simular` no se lee nada (solo dice qué leería).
2. **Sin carpeta ni ficheros, como «limpiar-usb».** El motor la ejecuta con
   la lista vacía (caso especial en `motor.py` antes del bloque de carpeta)
   y el menú NO le pregunta carpeta. No lleva campos propios en el JSON:
   `CAMPOS_POR_TIPO["estado-pc"] = ()`.
3. **Lectura con `psutil`** (`uv add psutil`): la librería estándar de
   Python para CPU, memoria, discos, temperaturas, batería y arranque, y
   funciona en los tres sistemas. La clase `EstadoPC` (acciones.py)
   sobrescribe `ejecutar()` como `LimpiarUSB` (una pasada, un
   Resultado-informe) y `aplicar()` queda sin usar.
4. **Informe parcial antes que error.** Cada bloque (CPU, memoria, discos,
   temperaturas, batería, arranque) va con try/except: si el sistema no
   expone el sensor (las temperaturas no salen en mucha placa Windows sin
   software del fabricante) se escribe «no disponible» y el informe sigue.

## Alternativas consideradas

1. **Solo biblioteca estándar** (`shutil.disk_usage`, `os.cpu_count`,
   `os.getloadavg`): sin dependencia nueva, pero sin porcentajes de uso de
   CPU reales ni temperaturas ni batería, y `getloadavg` no existe en
   Windows. Descartada por falta de datos.
2. **PowerShell / wmic** (`Get-ComputerInfo`): solo Windows (norma del
   repo: multiplataforma) y exige lanzar procesos externos; también
   descartada.
3. **Acción IA que informe del estado**: fuera de sitio — el modelo no
   puede leer el hardware y gastaría una llamada para repetir datos que
   `psutil` da exactos. Descartada de raíz.
4. **Orden CLI aparte** (`cliWork estado-pc`) en vez de acción del JSON:
   rompería ADR-0001 (todo en `acciones.json`, el código genérico) y no se
   podría combinar con el menú ni desactivar editando el JSON.

## Consecuencias

- Positivas: informe útil en los tres sistemas sin procesos externos;
  nueva acción solo editando el JSON (ADR-0001); el menú la lista como las
  demás; `--simular` gratuito; nada destructivo (sin `destructiva`, sin
  confirmación).
- Negativas: dependencia nueva (`psutil`, pura Python, ~1 MB); las
  temperaturas dependen del hardware/driver — en muchos equipos Windows
  salen «no disponibles»; la muestra de CPU tarda ~0,5 s (interval de
  `cpu_percent`).
- Qué haré si cambia: si se quisiera historial o alertas (aviso si un disco
  pasa del 90%), sería un campo nuevo del JSON (`avisos`, umbrales) con su
  ADR — **hecho: ADR-0009**; si psutil faltara en un equipo, el bloque
  falla a «no disponible», no a un traceback.

## Verificación (15-11-2026)

`uv run cliWork validar` → ✔ 15 acciones; **134 tests en verde** con 6
nuevos (`tests/test_estado_pc.py` + 1 de menú): el tipo valida, está en el
JSON real, `--simular` no lee, la ejecución real devuelve «hecho» con los
bloques y no modifica nada. Prueba en este equipo (win32): CPU, memoria,
dos discos, batería y arranque correctos; temperaturas «no disponibles»
(como espera el diseño). README y skill `acciones-json` actualizados.
