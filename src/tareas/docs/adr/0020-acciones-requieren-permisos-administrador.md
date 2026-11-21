# ADR-0020: Acciones que requieren consola con permisos de administrador

- Estado: aceptada
- Fecha: 2026-2026-11-21

## Contexto

Con el build de `ip-conf` (configuración de red por adaptador) y el ya
existente de `limpiar-usb` (borrado de registro de puertos USB), algunas
acciones escriben en el sistema operativo:

- `ip-conf`: `netsh interface ip set addresses` (Windows) / `networksetup
  -setmanual` (macOS) / `ip addr add` (Linux) → escriben en el sistema.
- `limpiar-usb`: `winreg` sobre `HKLM\...\Ports` → borra del registro.

Sin consola con permisos de administrador, el usuario ve fallos crudos (el
comando de red no se aplica; el borrado del registro se rechaza).

## Decisión

1. **Acciones que escriben en el sistema** (`ip-conf`, `limpiar-usb`) requieren
   consola con permisos de administrador.
2. **Con `--simular` ninguna escribe** y no requiere permisos.
3. El requisito se documenta en la ayuda de la orden (`ejecutar`) y en el
   README; `limpiar-usb` comprueba el token de administrador
   (`_es_administrador`) y avisa si no va con él.

## Alternativas consideradas

1. **Pedir permisos dentro de la propia acción** (elevación automática):
   descartada para esta fase (requeriría lógica de elevación propia y no estaba
   en el plan).
2. **No documentar**: descartada (el fallo sin permisos sería un error crudo y
   sin contexto).

## Consecuencias

- Positivas: el usuario sabe que `ip-conf`/`limpiar-usb` necesitan admin.
- Negativas: ninguna (con `--simular` no cambia nada); el requisito ya estaba
  en el comportamiento (`_es_administrador` para `limpiar-usb`).

## Verificación (21-11-2026)

- `uv run pytest`: **184 passed** (documentación de ayuda/README no rompe la
  suite; el help ampliado se verifica con `cliWork ejecutar --help`).
- Help ampliado: «Acciones que escriben en el sistema (ip-conf, limpiar-usb) requieren
  consola con permisos de administrador; con --simular no.»
