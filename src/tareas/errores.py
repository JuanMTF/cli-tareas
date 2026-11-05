"""Errores de tareas: base, configuración y acciones no válidas."""

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
