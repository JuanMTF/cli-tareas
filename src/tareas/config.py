"""Carga del fichero de acciones: src/tareas/docs/acciones.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tareas.errores import ConfigError

VERSION_ESPERADA = 1

RUTA_ACCIONES = Path("src/tareas/docs/acciones.json")


def cargar(ruta: Path) -> list[dict[str, Any]]:
    """Lee el JSON y devuelve la lista de acciones.

    Lanza ConfigError si el fichero no se puede leer, si el JSON no es
    válido (con línea y columna) o si no tiene la estructura esperada.
    """
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"No se pudo leer {ruta}: {exc}") from exc

    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"JSON inválido en {ruta} (línea {exc.lineno}, columna {exc.colno}): {exc.msg}"
        ) from exc

    if not isinstance(datos, dict):
        raise ConfigError(
            f"{ruta}: se esperaba un objeto JSON con 'version' y 'acciones'."
        )

    if datos.get("version") != VERSION_ESPERADA:
        raise ConfigError(
            f"{ruta}: 'version' debe ser {VERSION_ESPERADA} "
            f"(encontrado: {datos.get('version')!r})."
        )

    acciones = datos.get("acciones")
    if not isinstance(acciones, list):
        raise ConfigError(f"{ruta}: 'acciones' debe ser una lista.")

    return acciones
