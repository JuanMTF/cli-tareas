"""Acciones del fichero acciones.json: validación y ejecución.

Aquí NO hay órdenes de terminal (eso está en cli.py): solo comprobar que
las acciones están bien escritas y lanzar el navegador para tipo "abrir".
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
from tareas import html as mod_html
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


def describir_filtro(filtro: dict[str, Any]) -> str:
    """El filtro explicado en palabras normales, para el mensaje de «no hay ficheros».

    Así se ve de un vistazo por qué no se ha elegido nada («más antiguos que
    400 días», «solo .pdf», etc.).
    """
    partes: list[str] = []
    extensiones = filtro.get("extensiones") or []
    if extensiones:
        partes.append("extensiones " + ", ".join(str(e) for e in extensiones))
    if filtro.get("patron"):
        partes.append(f"nombre como «{filtro['patron']}»")
    if filtro.get("mas_antiguo_que_dias"):
        partes.append(f"más antiguos que {filtro['mas_antiguo_que_dias']} días")
    if filtro.get("mayor_que_mb"):
        partes.append(f"más grandes que {filtro['mayor_que_mb']} MB")
    return "; ".join(partes)


class Resultado:
    """Resultado de ejecutar una acción."""

    def __init__(self, exito: bool, mensaje: str) -> None:
        self.exito = exito
        self.mensaje = mensaje


class Accion:
    """Acción resuelta desde su configuración de acciones.json.

    El «tipo» no se decide con if/elif repartido por el código: cada tipo tiene
    su subclase registrada en REGISTRO y la fábrica Accion.desde_config crea la
    que toca. Añadir un tipo nuevo = crear subclase + registrar.
    """

    # Registro de subclases por tipo: «abrir» -> Abrir, «copiar» -> Copiar, ...
    REGISTRO: dict[str, type[Accion]] = {}

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    @classmethod
    def desde_config(cls, config: dict[str, Any]) -> "Accion":
        """Fábrica: instancia la subclase registrada para el campo «tipo»."""
        subclase = cls.REGISTRO.get(config.get("tipo") or "")
        if subclase is None:
            raise TareasError(
                f"La acción «{config.get('nombre')}» tiene el tipo «{config.get('tipo')}» "
                f"que todavía no está implementado."
            )
        return subclase(config)

    @classmethod
    def registrar(cls, tipo: str) -> Callable[[type[Accion]], type[Accion]]:
        """Registra la subclase que se encargará de un tipo concreto."""

        def decorador(subclase: type[Accion]) -> type[Accion]:
            subclase.TIPO = tipo  # type: ignore[attr-defined]
            cls.REGISTRO[tipo] = subclase
            return subclase

        return decorador

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        """Ejecuta la acción sobre los ficheros elegidos (o abre las URLs si es abrir)."""
        subclase = self.REGISTRO.get(self.config.get("tipo") or "")
        if subclase is None:
            raise TareasError(
                f"La acción «{self.config.get('nombre')}» tiene el tipo «{self.config.get('tipo')}» "
                f"que todavía no está implementado."
            )
        return subclase(self.config).ejecutar(ficheros, simular, urls, abrir, destino)

    def _destino(self) -> Path:
        """Carpeta destino expandiendo ~ (o la raíz actual si no tiene destino)."""
        return Path(self.config.get("destino") or ".").expanduser()

    def _origen(self) -> Path:
        """Carpeta origen expandiendo ~."""
        return Path(self.config.get("origen") or ".").expanduser()

    def _resultados_vacio(self) -> list[Resultado]:
        """Aviso de éxito cuando ningún fichero cumple el filtro (diciendo cuál es)."""
        detalle = describir_filtro(self.config.get("filtro") or {})
        if detalle:
            return [
                Resultado(
                    True,
                    f"No hay ficheros que cumplan el filtro ({detalle}).",
                )
            ]
        return [Resultado(True, "No hay ficheros que cumplan el filtro.")]


@Accion.registrar("abrir")
class Abrir(Accion):
    """Abre las URLs de la acción en el navegador (o describe la simulación)."""

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        """Abre las URLs (o describe la simulación) cuando la acción es «abrir»."""
        urls_efectivas = list(urls) if urls else list(self.config.get("urls") or [])
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


@Accion.registrar("copiar")
class Copiar(Accion):
    """Copia los ficheros elegidos al destino, sin borrar el original."""

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        """Copia los ficheros al destino (el original se queda en la carpeta de origen)."""
        destino_final = destino if destino is not None else self._destino()
        if not ficheros:
            return self._resultados_vacio()
        if not simular:
            destino_final.mkdir(parents=True, exist_ok=True)
        resultados: list[Resultado] = []
        for fichero in ficheros:
            original = destino_final / fichero.name
            libre = destino_libre(original)
            # Nunca se pisa: si ya hay algo con ese nombre, se renombra con « (1)».
            nota = " (ya existía: renombrado)" if libre != original else ""
            if simular:
                resultados.append(
                    Resultado(
                        True,
                        f"SIMULACIÓN: copiaría «{fichero.name}» → «{libre}»{nota}",
                    )
                )
            elif fichero.is_dir():
                shutil.copytree(fichero, libre, dirs_exist_ok=True)
                resultados.append(
                    Resultado(True, f"Copiado: «{fichero.name}» → «{libre}»{nota}")
                )
            else:
                shutil.copy2(str(fichero), str(libre))
                resultados.append(
                    Resultado(True, f"Copiado: «{fichero.name}» → «{libre}»{nota}")
                )
        return resultados


@Accion.registrar("mover")
class Mover(Accion):
    """Mueve los ficheros elegidos al destino, sin sobrescribir nunca."""

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        destino_final = destino if destino is not None else self._destino()
        if not ficheros:
            return self._resultados_vacio()
        if not simular:
            destino_final.mkdir(parents=True, exist_ok=True)
        resultados: list[Resultado] = []
        for fichero in ficheros:
            libre = destino_libre(destino_final / fichero.name)
            if simular:
                resultados.append(
                    Resultado(True, f"SIMULACIÓN: movería «{fichero.name}» → «{libre}»")
                )
            else:
                shutil.move(str(fichero), str(libre))
                resultados.append(Resultado(True, f"Movido: «{fichero.name}» → «{libre}»"))
        return resultados


@Accion.registrar("renombrar")
class Renombrar(Accion):
    """Renombra cada fichero con la plantilla, sin sobrescribir nunca."""

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        plantilla = self.config.get("plantilla", "{nombre}{ext}")
        if not ficheros:
            return self._resultados_vacio()
        resultados: list[Resultado] = []
        for indice, fichero in enumerate(ficheros, start=1):
            fecha = datetime.fromtimestamp(fichero.stat().st_mtime)
            nuevo_nombre = aplicar_plantilla(plantilla, fichero, indice, fecha)
            destino = destino_libre(fichero.with_name(nuevo_nombre))
            if simular:
                resultados.append(
                    Resultado(True, f"SIMULACIÓN: renombraría «{fichero.name}» → «{destino.name}»")
                )
            else:
                fichero.rename(destino)
                resultados.append(Resultado(True, f"Renombrado: «{fichero.name}» → «{destino.name}»"))
        return resultados


@Accion.registrar("borrar")
class Borrar(Accion):
    """Borra cada fichero (la confirmación la pide la CLI)."""

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        if not ficheros:
            return self._resultados_vacio()
        resultados: list[Resultado] = []
        for fichero in ficheros:
            if simular:
                resultados.append(Resultado(True, f"SIMULACIÓN: borraría «{fichero.name}»"))
            else:
                fichero.unlink()
                resultados.append(Resultado(True, f"Borrado: «{fichero.name}»"))
        return resultados


@Accion.registrar("transformar")
class Transformar(Accion):
    """Convierte cada PDF en una carpeta con su index.html y sus páginas en imagen.

    En el destino se dejan compartidos estilos.css, script.js, manuales.json y
    el index.html que lista todos los manuales (ver tareas.html).
    """

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        destino_final = destino if destino is not None else self._destino()
        if not ficheros:
            return self._resultados_vacio()
        if simular:
            return [
                Resultado(
                    True,
                    f"SIMULACIÓN: convertiría «{fichero.name}» → "
                    f"«{fichero.stem}/{mod_html.NOMBRE_INDICE}»",
                )
                for fichero in ficheros
            ]

        destino_final.mkdir(parents=True, exist_ok=True)
        mod_html.escribir_recursos(destino_final)
        manuales = {
            str(item.get("nombre", "")): item
            for item in mod_html.leer_manuales(destino_final)
        }
        resultados: list[Resultado] = []
        for fichero in ficheros:
            registro = mod_html.convertir_pdf(fichero, destino_final)
            manuales[str(registro["nombre"])] = registro
            resultados.append(
                Resultado(
                    True,
                    f"Convertido: «{fichero.name}» → "
                    f"«{registro['carpeta']}/{mod_html.NOMBRE_INDICE}» "
                    f"({registro['paginas']} página(s))",
                )
            )
        lista = list(manuales.values())
        mod_html.guardar_manuales(destino_final, lista)
        mod_html.escribir_galeria(destino_final, lista)
        resultados.append(
            Resultado(
                True,
                f"Índice actualizado: «{mod_html.NOMBRE_JSON}» y "
                f"«{mod_html.NOMBRE_INDICE}» con {len(lista)} manual(es).",
            )
        )
        return resultados


@Accion.registrar("comprimir")
class Comprimir(Accion):
    """Comprime los ficheros y carpetas elegidos en un .zip, sin sobrescribir nunca."""

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        destino_final = destino if destino is not None else self._destino()
        if not ficheros:
            return self._resultados_vacio()
        # El .zip se llama como la carpeta origen; si se pidió --nombre, manda ese
        # (el motor lo deja en «nombre_zip» de la configuración solo para ejecutar).
        nombre = str(self.config.get("nombre_zip") or ficheros[0].parent.name).strip()
        nombre = nombre or str(self.config.get("nombre") or "tareas")
        libre = destino_libre(destino_final / f"{nombre}.zip")
        nota = " (ya existía: renombrado)" if libre.name != f"{nombre}.zip" else ""
        if simular:
            nombrados = ", ".join(f"«{fichero.name}»" for fichero in ficheros)
            return [
                Resultado(
                    True,
                    f"SIMULACIÓN: comprimiría {len(ficheros)} fichero(s) en «{libre}»"
                    f"{nota}: {nombrados}",
                )
            ]
        destino_final.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(libre, "w", zipfile.ZIP_DEFLATED) as archivo:
            for fichero in ficheros:
                if fichero.is_dir():
                    # Una carpeta seleccionada: se comprime su contenido entero.
                    for contenido in sorted(fichero.rglob("*")):
                        if contenido.is_file():
                            archivo.write(contenido, arcname=contenido.relative_to(fichero.parent))
                else:
                    archivo.write(fichero, arcname=fichero.name)
        return [
            Resultado(
                True,
                f"Comprimido: {len(ficheros)} fichero(s) → «{libre}»{nota}",
            )
        ]


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


def abrir_en_navegador(
    clave: str, urls: list[str], ruta: Path | None = None
) -> None:
    """Abre 1 ventana nueva del navegador indicado con todas las URLs como pestañas.

    Se usa el módulo estándar webbrowser: sin subprocess y sin shell=True, que es
    la norma del proyecto.

    webbrowser.open() abre el explorador POR DEFECTO, así que antes hay que
    registrar el ejecutable del navegador pedido (-e edge, -g chrome, -f firefox)
    y pedir ese. Si no se hace, la opción elegida no se respeta y se abre el
    por defecto (Google Chrome) aunque se pidiera Edge.
    """
    ejecutable = ruta if ruta is not None else buscar_navegador(clave)
    if ejecutable is None:
        raise TareasError(f"No se encontró {NAVEGADORES[clave]} en este equipo.")
    webbrowser.register(
        clave, None, webbrowser.BackgroundBrowser(str(ejecutable)), preferred=True
    )
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
