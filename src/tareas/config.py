"""Carga del fichero de acciones: src/tareas/docs/acciones.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tareas.errores import AccionNoValida, ConfigError

VERSION_ESPERADA = 1

# Ruta absoluta junto al propio paquete: así funciona desde cualquier carpeta,
# no solo desde la raíz del proyecto (src/tareas/docs/acciones.json).
RUTA_ACCIONES = Path(__file__).resolve().parent / "docs" / "acciones.json"

# Catálogo de tipos: si el tipo no está aquí, la acción no se puede ejecutar.
TIPOS_CONOCIDOS = ("mover", "renombrar", "borrar", "abrir", "transformar",
                   "comprimir", "copiar")

# Campos que puede llevar cualquier acción.
CAMPOS_COMUNES = ("nombre", "descripcion", "tipo", "confirmar")

# Campos obligatorios de cada tipo.
CAMPOS_POR_TIPO: dict[str, tuple[str, ...]] = {
    "mover": ("origen", "filtro", "destino"),
    "renombrar": ("filtro", "plantilla"),
    "borrar": ("filtro", "confirmar"),
    "abrir": ("urls",),
    "transformar": ("origen", "filtro", "destino"),
    "comprimir": ("origen", "filtro", "destino"),
    "copiar": ("origen", "filtro", "destino"),
}

# Campos que se reconocen dentro de 'filtro'.
FILTRO_CONOCIDO = ("extensiones", "patron", "mas_antiguo_que_dias", "mayor_que_mb")

# nombre en kebab-case: minúsculas, números, guiones, tildes y espacios. Ej.: abrir-nav
_NOMBRE_KEBAB = re.compile(r"^[a-z0-9áéíóúüñ]+(?:[ -áéíóúüñ][a-z0-9áéíóúüñ]+)*$")


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


def validar_acciones(acciones: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Valida todas las acciones. Devuelve (errores, avisos).

    Cada error es un texto listo para imprimir. Usa validar() por acción.
    """
    errores: list[str] = []
    avisos: list[str] = []

    if not acciones:
        avisos.append("No hay ninguna acción definida.")
        return errores, avisos

    nombres_vistos: set[str] = set()
    for indice, accion in enumerate(acciones, start=1):
        try:
            avisos.extend(validar(accion, indice, nombres_vistos))
        except AccionNoValida as exc:
            errores.append(str(exc))

    return errores, avisos


def validar(accion: Any, indice: int, nombres_vistos: set[str]) -> list[str]:
    """Valida una acción. Devuelve los avisos.

    Lanza AccionNoValida en el primer error que encuentre.
    """
    avisos: list[str] = []

    if not isinstance(accion, dict):
        raise AccionNoValida(
            {"nombre": f"acción {indice}"},
            "estructura",
            "debe ser un objeto JSON con sus campos.",
        )

    nombre = accion.get("nombre")
    etiqueta = f"acción {indice}" + (f" «{nombre}»" if isinstance(nombre, str) else "")

    # nombre
    if not isinstance(nombre, str) or not nombre:
        raise AccionNoValida(accion, "nombre", "falta el campo «nombre».")
    if not _NOMBRE_KEBAB.match(nombre):
        raise AccionNoValida(
            accion, "nombre", "debe ir en minúsculas con guiones (kebab-case)."
        )
    if nombre in nombres_vistos:
        raise AccionNoValida(
            accion, "nombre", "duplicado; cada acción debe ser única."
        )
    nombres_vistos.add(nombre)

    # descripcion
    descripcion = accion.get("descripcion")
    if not isinstance(descripcion, str) or not descripcion.strip():
        raise AccionNoValida(
            accion, "descripcion", "falta «descripcion» (un texto no vacío)."
        )

    # tipo
    tipo = accion.get("tipo")
    if not isinstance(tipo, str) or not tipo:
        raise AccionNoValida(accion, "tipo", "falta el campo «tipo».")
    if tipo not in TIPOS_CONOCIDOS:
        raise AccionNoValida(
            accion,
            "tipo",
            f"tipo «{tipo}» desconocido. Válidos: {', '.join(TIPOS_CONOCIDOS)}.",
        )

    # confirmar, si está, tiene que ser booleano
    if "confirmar" in accion and not isinstance(accion["confirmar"], bool):
        raise AccionNoValida(accion, "confirmar", "debe ser true o false.")

    # campos que el tipo necesita sí o sí
    for campo in CAMPOS_POR_TIPO[tipo]:
        if campo not in accion:
            raise AccionNoValida(
                accion, campo, f"al tipo «{tipo}» le falta el campo «{campo}»."
            )

    # urls (solo tipo abrir)
    if tipo == "abrir" and "urls" in accion:
        urls = accion["urls"]
        if not isinstance(urls, list) or not urls:
            raise AccionNoValida(
                accion, "urls", "debe ser una lista con al menos una dirección."
            )
        for indice_url, url in enumerate(urls, start=1):
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                raise AccionNoValida(
                    accion,
                    "urls",
                    f"la URL {indice_url} no empieza por http:// o https://: {url!r}.",
                )

    # filtro, si está, tiene forma de comprobar
    if "filtro" in accion:
        filtro = accion["filtro"]
        if not isinstance(filtro, dict):
            raise AccionNoValida(accion, "filtro", "debe ser un objeto JSON.")
        if "extensiones" in filtro and not isinstance(filtro["extensiones"], list):
            raise AccionNoValida(
                accion, "filtro.extensiones", "debe ser una lista."
            )
        # El filtro tiene que servir para algo: al menos un criterio reconocido.
        # (Se puede filtrar solo por antigüedad, sin «extensiones» ni «patron».)
        if not any(clave in filtro for clave in FILTRO_CONOCIDO):
            raise AccionNoValida(
                accion,
                "filtro",
                "necesita al menos uno de: «extensiones», «patron», "
                "«mas_antiguo_que_dias» o «mayor_que_mb».",
            )
        if tipo == "borrar" and "patron" not in filtro:
            raise AccionNoValida(
                accion, "filtro", f"al tipo «borrar» le falta «filtro.patron»."
            )
        if "mas_antiguo_que_dias" in filtro:
            dias = filtro["mas_antiguo_que_dias"]
            if isinstance(dias, bool) or not isinstance(dias, int) or dias <= 0:
                raise AccionNoValida(
                    accion,
                    "filtro.mas_antiguo_que_dias",
                    f"debe ser un número de días mayor que 0 (encontrado: {dias!r}).",
                )
        if "mayor_que_mb" in filtro:
            mb = filtro["mayor_que_mb"]
            if isinstance(mb, bool) or not isinstance(mb, (int, float)) or mb <= 0:
                raise AccionNoValida(
                    accion,
                    "filtro.mayor_que_mb",
                    f"debe ser un número de MB mayor que 0 (encontrado: {mb!r}).",
                )
        # una errata en el filtro (ej.: mas_antiguio_que_dias) se avisa
        desconocidos = sorted(set(filtro) - set(FILTRO_CONOCIDO))
        if desconocidos:
            avisos.append(
                f"{etiqueta}: campos en 'filtro' que no se reconocen: "
                f"{', '.join(desconocidos)}."
            )

    # campos de texto que no pueden estar vacíos
    for campo in ("origen", "destino", "plantilla"):
        if campo in accion and (
            not isinstance(accion[campo], str) or not accion[campo].strip()
        ):
            raise AccionNoValida(
                accion, campo, f"«{campo}» debe ser un texto no vacío."
            )

    # campos que no le tocan a este tipo -> aviso, no error
    de_mas = sorted(set(accion) - set(CAMPOS_COMUNES) - set(CAMPOS_POR_TIPO[tipo]))
    if de_mas:
        avisos.append(
            f"{etiqueta}: campos que no le tocan a «{tipo}»: {', '.join(de_mas)}."
        )

    return avisos
