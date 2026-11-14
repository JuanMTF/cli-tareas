"""Errores de tareas: base, configuración, acciones no válidas e IA no disponible."""

from __future__ import annotations

from typing import Any


class TareasError(Exception):
    """Error base de tareas. La orden termina con este código de salida."""

    codigo_salida = 1


class ConfigError(TareasError):
    """El fichero de acciones no se puede leer o no tiene la forma esperada."""

    codigo_salida = 3


class AccionNoValida(ConfigError):
    """Una acción del fichero no cumple el esquema de acciones.json."""

    def __init__(self, accion: dict[str, Any], campo: str, motivo: str) -> None:
        self.accion = accion
        self.campo = campo
        self.motivo = motivo
        nombre = accion.get("nombre") if isinstance(accion, dict) else None
        etiqueta = f"«{nombre}»" if isinstance(nombre, str) and nombre else "«sin nombre»"
        super().__init__(f"Acción {etiqueta}, campo «{campo}»: {motivo}")


class IANoDisponible(TareasError):
    """La capa de IA no puede usarse ahora (config, red, certificado, servidor...).

    Cualquier fallo del proveedor (sin clave, sin red, certificado que no
    valida, 401, 429, tiempo agotado, respuesta con otro formato) se traduce
    aquí con un mensaje humano: la CLI lo imprime sin traceback y sale con 4,
    y las acciones sin IA siguen funcionando.
    """

    codigo_salida = 4
