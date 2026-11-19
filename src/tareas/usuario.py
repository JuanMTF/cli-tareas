"""Tus opciones por defecto: ~/.cliWork/configUsuario.json (ADR-0014).

Cada ordenador tiene el suyo (vive en el home de cada usuario): el mismo
repo y el mismo acciones.json sirven en los 3 equipos con rutas distintas
(una ruta de red por PC, o Linux con rutas de Linux). Lo que no pongas —o
dejes vacío— no cambia nada: manda lo que diga acciones.json. Se crea solo,
la primera vez que ejecutas una acción, con una _ayuda en español.

Las prioridades quedan así (ADR-0014):
- origen y destino: opción de la CLI > TU fichero > acciones.json > «.»
- extensiones: opción --extensiones de la CLI > el filtro de la acción >
  TU fichero (solo entra en filtros que no traigan las suyas) > todas
- confirmar: TU fichero (las destructivas «borrar» SIEMPRE preguntan)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tareas.errores import ConfigError
from tareas.config import _mensaje_json

# Valores de fábrica: VACÍOS = «no cambiar nada, manda acciones.json».
DEFECTOS: dict[str, Any] = {
    "origen": "",
    "destino": "",
    "extensiones": [],
    "confirmar": True,
}

# La explicación de cada campo VIAJA DENTRO del fichero: quien no sepa
# programar abre el JSON y ve qué es cada cosa sin ir al README.
_AYUDA: dict[str, str] = {
    "_ayuda": (
        "Tus opciones por defecto de cliWork (un fichero por ordenador). "
        "Lo vacío (\"\") o [] = «no cambiar nada: manda acciones.json». "
        "Si borras este fichero se vuelve a crear con estos valores."
    ),
    "origen": (
        "Tu carpeta de origen por defecto, para TODAS las acciones que no "
        "la traigan y para cuando el menú no sepa qué proponer. Manda sobre "
        "la de acciones.json. Ej.: \"~/Descargas\" o \"//SERVIDOR/Compartido\"."
    ),
    "destino": (
        "Tu carpeta de destino por defecto: manda sobre la de acciones.json "
        "si la pones. Ej.: \"~/Documentos\"."
    ),
    "extensiones": (
        "Extensiones por defecto (con su punto: [\".pdf\", \".jpg\"]) para los "
        "filtros que NO traigan las suyas. [] = todas, como hasta ahora. "
        "Para un día concreto, usa --extensiones .pdf,.jpg en la orden."
    ),
    "confirmar": (
        "true = las acciones con confirmar piden autorización (como siempre). "
        "false = esas dejan de preguntar. Las de tipo «borrar» preguntan "
        "SIEMPRE, con aviso ⚠, porque borran de verdad (no hay papelera)."
    ),
}

CAMPOS_VALIDOS = ("origen", "destino", "extensiones", "confirmar")


def ruta() -> Path:
    """Dónde vive TU fichero: ~/.cliWork/configUsuario.json.

    Se calcula AQUÍ (no al importar el módulo): Path.home() mira HOME o
    USERPROFILE en el momento de la llamada, así que los tests —que
    apuntan esas variables a su sandbox— no crean el fichero del usuario
    de verdad.
    """
    return Path.home() / ".cliWork" / "configUsuario.json"


def preparar() -> Path:
    """Crea el fichero con los valores de fábrica si no existe (devuelve la ruta)."""
    camino = ruta()
    if not camino.is_file():
        camino.parent.mkdir(parents=True, exist_ok=True)
        datos: dict[str, Any] = {"_ayuda": _AYUDA, **DEFECTOS}
        texto = json.dumps(datos, ensure_ascii=False, indent=2)
        camino.write_text(texto + "\n", encoding="utf-8")
    return camino


def cargar() -> dict[str, Any]:
    """Tus opciones. Si el fichero no está, lo crea; si está roto, ConfigError."""
    camino = preparar()
    try:
        texto = camino.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ConfigError(
            f"No se pudo leer tu fichero de usuario {camino}: {exc}"
        ) from exc
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Tu fichero {camino} no es JSON válido "
            f"(línea {exc.lineno}, columna {exc.colno}): "
            f"{_mensaje_json(exc.msg)}"
        ) from exc
    if not isinstance(datos, dict):
        raise ConfigError(f"{camino}: debe ser un objeto JSON con tus opciones.")
    _validar(datos, camino)
    return datos


def _validar(datos: dict[str, Any], camino: Path) -> None:
    """Comprueba los tipos; una errata avisa con nombre y apellidos."""
    desconocidos = sorted(set(datos) - set(CAMPOS_VALIDOS) - {"_ayuda"})
    if desconocidos:
        raise ConfigError(
            f"{camino}: campos que no se reconocen: {', '.join(desconocidos)}. "
            f"Válidos: {', '.join(CAMPOS_VALIDOS)} (más la _ayuda)."
        )
    for campo in ("origen", "destino"):
        if campo in datos and not isinstance(datos[campo], str):
            raise ConfigError(
                f"{camino}: «{campo}» debe ser un texto (tu carpeta) "
                f"o \"\" para no cambiar nada (encontrado: {datos[campo]!r})."
            )
    if "extensiones" in datos and not (
        isinstance(datos["extensiones"], list)
        and all(isinstance(e, str) and e for e in datos["extensiones"])
    ):
        raise ConfigError(
            f"{camino}: «extensiones» debe ser una lista de textos con su "
            f"punto (ej.: [\".pdf\"]) o [] para todas "
            f"(encontrado: {datos['extensiones']!r})."
        )
    if "confirmar" in datos and not isinstance(datos["confirmar"], bool):
        raise ConfigError(
            f"{camino}: «confirmar» debe ser true o false "
            f"(encontrado: {datos['confirmar']!r})."
        )


def origen_defecto() -> str | None:
    """Tu origen por defecto (None = no cambio nada)."""
    origen = cargar().get("origen")
    return origen if isinstance(origen, str) and origen.strip() else None


def destino_defecto() -> str | None:
    """Tu destino por defecto (None = no cambio nada)."""
    destino = cargar().get("destino")
    return destino if isinstance(destino, str) and destino.strip() else None


def extensiones_defecto() -> list[str]:
    """Tus extensiones por defecto ([] = todas, no se inyecta nada)."""
    extensiones = cargar().get("extensiones")
    if not isinstance(extensiones, list):
        return []
    return [e for e in extensiones if isinstance(e, str) and e]


def confirmar_por_defecto() -> bool:
    """¿Piden confirmación las acciones con «confirmar»? (true por defecto)."""
    confirmar = cargar().get("confirmar")
    return confirmar if isinstance(confirmar, bool) else True


def normalizar_extensiones(texto: str) -> list[str]:
    """La lista de --extensiones: «pdf, .JPG tmp» → [".pdf", ".JPG", ".tmp"].

    Acepta comas o espacios como separadores y añade el punto si falta:
    quien no sabe programar escribe «pdf» y espera que funcione.
    """
    normalizadas = []
    for trozo in texto.replace(",", " ").split():
        normalizadas.append(trozo if trozo.startswith(".") else "." + trozo)
    return normalizadas
