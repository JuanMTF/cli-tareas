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
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from tareas import config as mod_config
from tareas.errores import TareasError

# Fichero de configuración. Ruta absoluta (dentro del paquete): sirve desde cualquier carpeta.
RUTA_ACCIONES = mod_config.RUTA_ACCIONES

VERSION_ESPERADA = mod_config.VERSION_ESPERADA

# Catálogo de tipos y campos: la fuente única vive en config.py.
TIPOS_CONOCIDOS = mod_config.TIPOS_CONOCIDOS
CAMPOS_COMUNES = mod_config.CAMPOS_COMUNES
CAMPOS_POR_TIPO = mod_config.CAMPOS_POR_TIPO
FILTRO_CONOCIDO = mod_config.FILTRO_CONOCIDO
_NOMBRE_KEBAB = mod_config._NOMBRE_KEBAB

# Navegadores pedibles con -e, -g o -f: clave -> nombre para los mensajes.
NAVEGADORES: dict[str, str] = {
    "edge": "Microsoft Edge",
    "chrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
}


def destino_libre(destino: Path) -> Path:
    """Devuelve una ruta libre: si ya existe, añade « (1)», « (2)»... sin sobrescribir."""
    if not destino.exists():
        return destino
    sufijo = destino.suffix
    base = destino.name[: -len(sufijo)] if sufijo else destino.name
    n = 1
    while True:
        candidato = destino.with_name(f"{base} ({n}){sufijo}")
        if not candidato.exists():
            return candidato
        n += 1


_HUECO = re.compile(r"\{([^{}]+)\}")


def aplicar_plantilla(plantilla: str, fichero: Path, n: int, fecha: datetime) -> str:
    """Rellena los huecos de una plantilla: {fecha:...}, {n:03}, {ext}, {nombre}."""

    def _sustituir(match: re.Match[str]) -> str:
        hueco = match.group(1)
        if hueco.startswith("fecha:"):
            return fecha.strftime(hueco[len("fecha:") :])
        if hueco.startswith("n:"):
            ancho = hueco[len("n:") :]
            return f"{n:0{int(ancho)}d}" if ancho.isdigit() else str(n)
        if hueco == "ext":
            return fichero.suffix
        if hueco == "nombre":
            return fichero.stem
        return match.group(0)

    return _HUECO.sub(_sustituir, plantilla)


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
        if tipo == "mover":
            return self._mover(ficheros, simular)
        if tipo == "renombrar":
            return self._renombrar(ficheros, simular)
        if tipo == "borrar":
            return self._borrar(ficheros, simular)
        if tipo == "transformar":
            return self._transformar(ficheros, simular)
        if tipo == "comprimir":
            return self._comprimir(ficheros, simular)
        raise TareasError(
            f"La acción «{self.config.get('nombre')}» es de tipo «{tipo}» "
            f"y todavía no está implementado (solo «abrir»)."
        )

    def _destino(self) -> Path:
        """Carpeta destino expandiendo ~ (o la raíz actual si no tiene destino)."""
        return Path(self.config.get("destino") or ".").expanduser()

    def _origen(self) -> Path:
        """Carpeta origen expandiendo ~."""
        return Path(self.config.get("origen") or ".").expanduser()

    def _mover(self, ficheros: list[Path], simular: bool) -> list[Resultado]:
        """Mueve cada fichero al destino, sin sobrescribir nunca."""
        destino = self._destino()
        if not ficheros:
            return [Resultado(True, "No hay ficheros que cumplan el filtro.")]
        if not simular:
            destino.mkdir(parents=True, exist_ok=True)
        resultados: list[Resultado] = []
        for fichero in ficheros:
            libre = destino_libre(destino / fichero.name)
            if simular:
                resultados.append(
                    Resultado(
                        True,
                        f"SIMULACIÓN: movería «{fichero.name}» → «{libre}»",
                    )
                )
            else:
                shutil.move(str(fichero), str(libre))
                resultados.append(
                    Resultado(True, f"Movido: «{fichero.name}» → «{libre}»")
                )
        return resultados

    def _renombrar(self, ficheros: list[Path], simular: bool) -> list[Resultado]:
        """Renombra cada fichero con la plantilla, sin sobrescribir nunca."""
        plantilla = self.config.get("plantilla", "{nombre}{ext}")
        if not ficheros:
            return [Resultado(True, "No hay ficheros que cumplan el filtro.")]
        resultados: list[Resultado] = []
        for indice, fichero in enumerate(ficheros, start=1):
            fecha = datetime.fromtimestamp(fichero.stat().st_mtime)
            nuevo_nombre = aplicar_plantilla(plantilla, fichero, indice, fecha)
            destino = destino_libre(fichero.with_name(nuevo_nombre))
            if simular:
                resultados.append(
                    Resultado(
                        True,
                        f"SIMULACIÓN: renombraría «{fichero.name}» → «{destino.name}»",
                    )
                )
            else:
                fichero.rename(destino)
                resultados.append(
                    Resultado(
                        True, f"Renombrado: «{fichero.name}» → «{destino.name}»"
                    )
                )
        return resultados

    def _borrar(self, ficheros: list[Path], simular: bool) -> list[Resultado]:
        """Borra cada fichero (la confirmación la pide la CLI)."""
        if not ficheros:
            return [Resultado(True, "No hay ficheros que cumplan el filtro.")]
        resultados: list[Resultado] = []
        for fichero in ficheros:
            if simular:
                resultados.append(
                    Resultado(True, f"SIMULACIÓN: borraría «{fichero.name}»")
                )
            else:
                fichero.unlink()
                resultados.append(Resultado(True, f"Borrado: «{fichero.name}»"))
        return resultados

    def _transformar(self, ficheros: list[Path], simular: bool) -> list[Resultado]:
        """Genera un HTML por fichero que lo incrusta/abre en el navegador."""
        destino = self._destino()
        if not ficheros:
            return [Resultado(True, "No hay ficheros que cumplan el filtro.")]
        if not simular:
            destino.mkdir(parents=True, exist_ok=True)
        resultados: list[Resultado] = []
        for fichero in ficheros:
            salida = destino_libre(destino / f"{fichero.stem}.html")
            if simular:
                resultados.append(
                    Resultado(
                        True,
                        f"SIMULACIÓN: generaría «{salida.name}» para «{fichero.name}»",
                    )
                )
            else:
                uri = fichero.resolve().as_uri()
                html = (
                    "<!DOCTYPE html>\n<html lang=\"es\">\n<head>\n"
                    "  <meta charset=\"UTF-8\">\n"
                    f"  <title>{fichero.name}</title>\n"
                    "</head>\n<body>\n"
                    f"  <h1>{fichero.name}</h1>\n"
                    f"  <iframe src=\"{uri}\" width=\"100%\" height=\"90vh\"></iframe>\n"
                    f"  <p><a href=\"{uri}\">Abrir el original</a></p>\n"
                    "</body>\n</html>\n"
                )
                salida.write_text(html, encoding="utf-8")
                resultados.append(
                    Resultado(
                        True,
                        f"Transformado: «{fichero.name}» → «{salida.name}»",
                    )
                )
        return resultados

    def _comprimir(self, ficheros: list[Path], simular: bool) -> list[Resultado]:
        """Comprime los ficheros en un .zip en el destino, sin sobrescribir."""
        destino = self._destino()
        if not ficheros:
            return [Resultado(True, "No hay ficheros que cumplan el filtro.")]
        nombre_zip = destino / f"{self.config.get('nombre', 'tareas')}.zip"
        libre = destino_libre(nombre_zip)
        if simular:
            return [
                Resultado(
                    True,
                    f"SIMULACIÓN: comprimiría {len(ficheros)} fichero(s) en «{libre}»",
                )
            ]
        destino.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(libre, "w", zipfile.ZIP_DEFLATED) as archivo:
            for fichero in ficheros:
                archivo.write(fichero, arcname=fichero.name)
        return [
            Resultado(
                True,
                f"Comprimido: {len(ficheros)} fichero(s) → «{libre}»",
            )
        ]

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
    """Comprueba todas las acciones. Devuelve (errores, avisos).

    La validación real vive en config.py (AccionNoValida); aquí solo se
    delega para no tener dos versiones distintas.
    """
    return mod_config.validar_acciones(acciones)


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
