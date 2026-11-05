"""Acciones del fichero acciones.json: carga, validación y ejecución.

Aquí NO hay órdenes de terminal (eso está en cli.py): solo leer el JSON,
comprobar que está bien escrito y lanzar el navegador para tipo "abrir".
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import webbrowser
from pathlib import Path
from typing import Any, Callable

from tareas.errores import TareasError

# Fichero de configuración. Relativo a la carpeta del proyecto (ejecutar desde ahí).
RUTA_ACCIONES = Path("src/tareas/docs/acciones.json")

VERSION_ESPERADA = 1

# Catálogo de tipos: si el tipo no está aquí, la acción no se puede ejecutar.
TIPOS_CONOCIDOS = ("mover", "renombrar", "borrar", "abrir", "transformar", "comprimir")

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
}

# Campos que se reconocen dentro de 'filtro'.
FILTRO_CONOCIDO = ("extensiones", "patron", "mas_antiguo_que_dias")

# nombre en kebab-case: minúsculas, números, guiones, tildes y espacios. Ej.: abrir-nav
_NOMBRE_KEBAB = re.compile(r"^[a-z0-9áéíóúüñ]+(?:[ -áéíóúüñ][a-z0-9áéíóúüñ]+)*$")

# Navegadores pedibles con -e, -g o -f: clave -> nombre para los mensajes.
NAVEGADORES: dict[str, str] = {
    "edge": "Microsoft Edge",
    "chrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
}


class Resultado:
    """Resultado de ejecutar una acción."""

    def __init__(self, exito: bool, mensaje: str) -> None:
        self.exito = exito
        self.mensaje = mensaje


class Accion:
    """Acción resuelta desde su configuración de acciones.json."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    @staticmethod
    def desde_config(config: dict[str, Any]) -> "Accion":
        return Accion(config)

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
    ) -> list[Resultado]:
        """Ejecuta la acción sobre los ficheros elegidos (o abre las URLs si es abrir)."""
        tipo = self.config.get("tipo")
        if tipo == "abrir":
            return self._ejecutar_abrir(simular, urls, abrir)
        raise TareasError(
            f"La acción «{self.config.get('nombre')}» es de tipo «{tipo}» "
            f"y todavía no está implementado (solo «abrir»)."
        )

    def _ejecutar_abrir(
        self,
        simular: bool,
        urls: list[str] | None,
        abrir: Callable[[list[str]], None] | None,
    ) -> list[Resultado]:
        urls_efectivas = list(urls or self.config.get("urls") or [])
        if simular:
            return [
                Resultado(
                    True,
                    f"SIMULACIÓN: no se abre ni se toca nada. Acción: {self.config.get('nombre')} "
                    f"Navegador: el explorador por defecto Ventana: 1 con {len(urls_efectivas)} pestañas: "
                    + " ".join(urls_efectivas),
                )
            ]
        ejecutar = abrir or (lambda urls_a: [webbrowser.open(url, new=1) for url in urls_a])
        try:
            ejecutar(urls_efectivas)
        except OSError as exc:
            raise TareasError(f"No se pudo abrir el navegador: {exc}") from exc
        return [Resultado(True, f"Navegador abierto con {len(urls_efectivas)} URL(s).")]


class ErrorConfiguracion(Exception):
    """El fichero de acciones no se puede leer o no tiene la forma esperada."""


def cargar_acciones(ruta: Path) -> list[dict[str, Any]]:
    """Lee el JSON y devuelve la lista de acciones.

    Lanza ErrorConfiguracion si el fichero no existe, no es JSON válido
    o no tiene la estructura "version" + "acciones".
    """
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError as exc:
        raise ErrorConfiguracion(f"No se pudo leer {ruta}: {exc}") from exc

    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ErrorConfiguracion(
            f"JSON inválido en {ruta} (línea {exc.lineno}): {exc.msg}"
        ) from exc

    if not isinstance(datos, dict):
        raise ErrorConfiguracion(
            f"{ruta}: se esperaba un objeto JSON con 'version' y 'acciones'."
        )

    if datos.get("version") != VERSION_ESPERADA:
        raise ErrorConfiguracion(
            f"{ruta}: 'version' debe ser {VERSION_ESPERADA} "
            f"(encontrado: {datos.get('version')!r})."
        )

    acciones = datos.get("acciones")
    if not isinstance(acciones, list):
        raise ErrorConfiguracion(f"{ruta}: 'acciones' debe ser una lista.")

    return acciones


def validar_acciones(acciones: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Comprueba todas las acciones. Devuelve (errores, avisos)."""
    errores: list[str] = []
    avisos: list[str] = []

    if not acciones:
        avisos.append("No hay ninguna acción definida.")
        return errores, avisos

    nombres_vistos: set[str] = set()
    for indice, accion in enumerate(acciones, start=1):
        err, aviso = _validar_accion(accion, indice, nombres_vistos)
        errores.extend(err)
        avisos.extend(aviso)

    return errores, avisos


def _validar_accion(
    accion: Any, indice: int, nombres_vistos: set[str]
) -> tuple[list[str], list[str]]:
    """Comprueba una sola acción. Devuelve (errores, avisos)."""
    errores: list[str] = []
    avisos: list[str] = []

    if not isinstance(accion, dict):
        return [f"acción {indice}: debe ser un objeto JSON con sus campos."], []

    nombre = accion.get("nombre")
    etiqueta = f"acción {indice}" + (f" «{nombre}»" if isinstance(nombre, str) else "")

    # nombre
    if not isinstance(nombre, str) or not nombre:
        errores.append(f"{etiqueta}: falta el campo 'nombre'.")
    else:
        if not _NOMBRE_KEBAB.match(nombre):
            errores.append(
                f"{etiqueta}: 'nombre' debe ir en minúsculas con guiones (kebab-case)."
            )
        if nombre in nombres_vistos:
            errores.append(f"{etiqueta}: 'nombre' duplicado; cada acción debe ser única.")
        nombres_vistos.add(nombre)

    # descripcion
    descripcion = accion.get("descripcion")
    if not isinstance(descripcion, str) or not descripcion.strip():
        errores.append(f"{etiqueta}: falta 'descripcion' (un texto no vacío).")

    # tipo
    tipo = accion.get("tipo")
    if not isinstance(tipo, str) or not tipo:
        errores.append(f"{etiqueta}: falta el campo 'tipo'.")
        return errores, avisos
    if tipo not in TIPOS_CONOCIDOS:
        errores.append(
            f"{etiqueta}: tipo «{tipo}» desconocido. "
            f"Válidos: {', '.join(TIPOS_CONOCIDOS)}."
        )
        return errores, avisos

    # confirmar, si está, tiene que ser booleano
    if "confirmar" in accion and not isinstance(accion["confirmar"], bool):
        errores.append(f"{etiqueta}: 'confirmar' debe ser true o false.")

    # campos que el tipo necesita sí o sí
    for campo in CAMPOS_POR_TIPO[tipo]:
        if campo not in accion:
            errores.append(
                f"{etiqueta}: al tipo «{tipo}» le falta el campo «{campo}»."
            )

    # urls (solo tipo abrir)
    if tipo == "abrir" and "urls" in accion:
        urls = accion["urls"]
        if not isinstance(urls, list) or not urls:
            errores.append(
                f"{etiqueta}: 'urls' debe ser una lista con al menos una dirección."
            )
        else:
            for indice_url, url in enumerate(urls, start=1):
                if not isinstance(url, str) or not url.startswith(
                    ("http://", "https://")
                ):
                    errores.append(
                        f"{etiqueta}: la URL {indice_url} no empieza por "
                        f"http:// o https://: {url!r}."
                    )

    # filtro, si está, tiene forma de comprobar
    if "filtro" in accion:
        filtro = accion["filtro"]
        if not isinstance(filtro, dict):
            errores.append(f"{etiqueta}: 'filtro' debe ser un objeto JSON.")
        else:
            if "extensiones" in filtro and not isinstance(filtro["extensiones"], list):
                errores.append(f"{etiqueta}: 'filtro.extensiones' debe ser una lista.")
            if not ("extensiones" in filtro or "patron" in filtro):
                errores.append(
                    f"{etiqueta}: 'filtro' necesita 'extensiones' o 'patron'."
                )
            if tipo == "borrar" and "patron" not in filtro:
                errores.append(f"{etiqueta}: al tipo «borrar» le falta 'filtro.patron'.")

            # mas_antiguo_que_dias, si está, tiene que ser un número de días
            if "mas_antiguo_que_dias" in filtro:
                dias = filtro["mas_antiguo_que_dias"]
                if isinstance(dias, bool) or not isinstance(dias, int) or dias <= 0:
                    errores.append(
                        f"{etiqueta}: 'filtro.mas_antiguo_que_dias' debe ser un "
                        f"número de días mayor que 0 (encontrado: {dias!r})."
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
        valor = accion.get(campo)
        if campo in accion and (not isinstance(valor, str) or not valor.strip()):
            errores.append(f"{etiqueta}: '{campo}' debe ser un texto no vacío.")

    # campos que no le tocan a este tipo -> aviso, no error
    de_mas = sorted(set(accion) - set(CAMPOS_COMUNES) - set(CAMPOS_POR_TIPO[tipo]))
    if de_mas:
        avisos.append(
            f"{etiqueta}: campos que no le tocan a «{tipo}»: {', '.join(de_mas)}."
        )

    return errores, avisos


def _bases_windows() -> tuple[str, ...]:
    """Carpetas de instalación habituales en Windows (solo se leen variables)."""
    return tuple(
        base
        for base in (
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("ProgramFiles"),
            os.environ.get("LocalAppData"),
        )
        if base
    )


def buscar_edge() -> Path | None:
    """Devuelve la ruta de Microsoft Edge, o None si no está instalado."""
    candidatos: list[Path] = []

    if sys.platform == "win32":
        for base in _bases_windows():
            candidatos.append(
                Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            )
    elif sys.platform == "darwin":
        candidatos.append(
            Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")
        )

    # Linux (y Windows si msedge estuviera en el PATH)
    for nombre in ("msedge", "microsoft-edge", "microsoft-edge-stable"):
        encontrado = shutil.which(nombre)
        if encontrado:
            candidatos.append(Path(encontrado))

    return _primero_que_existe(candidatos)


def buscar_chrome() -> Path | None:
    """Devuelve la ruta de Google Chrome (o Chromium), o None si no está."""
    candidatos: list[Path] = []

    if sys.platform == "win32":
        for base in _bases_windows():
            candidatos.append(
                Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"
            )
    elif sys.platform == "darwin":
        candidatos.append(
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        )

    for nombre in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        encontrado = shutil.which(nombre)
        if encontrado:
            candidatos.append(Path(encontrado))

    return _primero_que_existe(candidatos)


def buscar_firefox() -> Path | None:
    """Devuelve la ruta de Mozilla Firefox, o None si no está instalado."""
    candidatos: list[Path] = []

    if sys.platform == "win32":
        for base in _bases_windows():
            candidatos.append(Path(base) / "Mozilla Firefox" / "firefox.exe")
    elif sys.platform == "darwin":
        candidatos.append(Path("/Applications/Firefox.app/Contents/MacOS/firefox"))

    for nombre in ("firefox", "firefox-esr"):
        encontrado = shutil.which(nombre)
        if encontrado:
            candidatos.append(Path(encontrado))

    return _primero_que_existe(candidatos)


def _primero_que_existe(candidatos: list[Path]) -> Path | None:
    """Devuelve la primera ruta que es un fichero, o None si no hay ninguna."""
    for ruta in candidatos:
        if ruta.is_file():
            return ruta
    return None


def buscar_navegador(clave: str) -> Path | None:
    """Devuelve la ruta del navegador pedido ('edge', 'chrome' o 'firefox').

    Si la clave no existe o el navegador no está instalado, devuelve None.
    """
    buscadores = {"edge": buscar_edge, "chrome": buscar_chrome, "firefox": buscar_firefox}
    buscador = buscadores.get(clave)
    if buscador is None:
        return None
    return buscador()


def abrir_en_navegador(clave: str, urls: list[str]) -> None:
    """Abre 1 ventana nueva del navegador indicado con todas las URLs como pestañas.

    Se usa el módulo estándar webbrowser: sin subprocess y sin shell=True, que es
    la norma del proyecto.
    """
    for url in urls:
        webbrowser.open(url, new=1)


def abrir_por_defecto(urls: list[str]) -> None:
    """Abre cada URL con el explorador por defecto del sistema.

    Usa el módulo estándar webbrowser (sin shell, sirve en Windows, Linux y
    macOS). Quién decide si abre pestaña o ventana nueva es el navegador.
    """
    for url in urls:
        if not webbrowser.open(url):
            raise OSError(f"el explorador por defecto no quiso abrir {url}")
