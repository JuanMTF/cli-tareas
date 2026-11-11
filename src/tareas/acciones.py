"""Acciones del fichero acciones.json: validación y ejecución.

Aquí NO hay órdenes de terminal (eso está en cli.py): solo comprobar que
las acciones están bien escritas y lanzar el navegador para tipo "abrir".
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import webbrowser
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

from tareas import config as mod_config
from tareas import html as mod_html
from tareas.errores import ConfigError, TareasError

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


def aplicar_plantilla(
    plantilla: str, fichero: Path, n: int, fecha: datetime, base: str = "Captura"
) -> str:
    """Rellena los huecos de una plantilla: {fecha:...}, {n:03}, {n}, {ext}, {nombre}, {base}."""

    def _sustituir(match: re.Match[str]) -> str:
        hueco = match.group(1)
        if hueco.startswith("fecha:"):
            return fecha.strftime(hueco[len("fecha:") :])
        if hueco == "n":
            # Número de orden sin ceros: 1, 2, 3...
            return str(n)
        if hueco.startswith("n:"):
            ancho = hueco[len("n:") :]
            return f"{n:0{int(ancho)}d}" if ancho.isdigit() else str(n)
        if hueco == "ext":
            return fichero.suffix
        if hueco == "nombre":
            return fichero.stem
        if hueco == "base":
            # Nombre genérico que pasa la CLI con --nombre (ej.: -n Capturas).
            return base
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


@dataclass
class Resultado:
    """Resultado de aplicar la acción sobre un elemento.

    origen/destino: rutas implicadas (None si el tipo no las usa, p. ej. abrir).
    estado: «hecho» (tocó el disco), «simulado» (con --simular, no tocó nada)
    o «saltado» (no se hizo: no había nada que procesar o fallo sin importancia).
    """

    origen: Path | None
    destino: Path | None
    estado: Literal["hecho", "simulado", "saltado"]
    mensaje: str

    @property
    def exito(self) -> bool:
        """Compatible con la CLI: «saltado» por filtro vacío no es un fallo."""
        return True


class Accion(ABC):
    """Acción resuelta desde su configuración de acciones.json (clase base abstracta).

    El «tipo» no se decide con if/elif repartido por el código: cada tipo tiene
    su subclase registrada en REGISTRO y la fábrica Accion.desde_config crea la
    que toca. Añadir un tipo nuevo = crear subclase + registrar.

    Las subclases solo implementan aplicar(fichero, n, simular) sobre UN
    elemento; ejecutar() recorre la lista y arma los list[Resultado].
    Con simular=True NADA del camino de escribir se ejecuta: ni mkdir, ni
    move, ni unlink.
    """

    # Registro de subclases por tipo: «abrir» -> Abrir, «copiar» -> Copiar, ...
    REGISTRO: dict[str, type[Accion]] = {}

    # Acción destructiva: la CLI pide confirmación siempre (salvo --si).
    destructiva = False

    # Acciones que archivan (comprimir, copiar): la selección admite carpetas.
    elige_carpetas = False

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
        """Recorre los elementos elegidos llamando a aplicar() sobre cada uno.

        Si no hay ninguno, devuelve el aviso del filtro (estado «saltado»).
        Preparar el entorno (mkdir del destino) pasa por preparar(), que las
        subclases sobrescriben dejando pasar solo las lecturas.
        """
        if not ficheros:
            return self._resultados_vacio()
        self.preparar(ficheros, simular, destino)
        return [
            self.aplicar(fichero, n, simular, urls=urls, abrir=abrir, destino=destino)
            for n, fichero in enumerate(ficheros, start=1)
        ] + self.terminar(simular)

    def terminar(self, simular: bool) -> list[Resultado]:
        """Resultados extra tras recorrer todo (p. ej. reescribir índices).

        Con simular=True devuelve lista vacía. Por defecto no añade nada.
        """
        return []

    def preparar(
        self,
        ficheros: list[Path],
        simular: bool,
        destino: Path | None = None,
    ) -> None:
        """Creaciones de una sola vez por ejecución (el mkdir del destino).

        Con simular=True no se toca NADA: ni mkdir. Por defecto no hace nada.
        """

    @abstractmethod
    def aplicar(
        self,
        fichero: Path,
        n: int,
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> Resultado:
        """Aplica la acción sobre UN elemento y devuelve su Resultado.

        Con simular=True solo puede leer (exists/stat) y devolver el
        Resultado con estado «simulado».
        """
        raise NotImplementedError

    def _destino(self) -> Path:
        """Carpeta destino expandiendo ~ (o la raíz actual si no tiene destino)."""
        return Path(self.config.get("destino") or ".").expanduser()

    def _origen(self) -> Path:
        """Carpeta origen expandiendo ~."""
        return Path(self.config.get("origen") or ".").expanduser()

    def _destino_final(self, destino: Path | None) -> Path:
        """El destino que manda: la opción de la CLI sobre el del JSON."""
        return destino if destino is not None else self._destino()

    def _resultados_vacio(self) -> list[Resultado]:
        """Aviso cuando ningún fichero cumple el filtro (diciendo cuál es)."""
        detalle = describir_filtro(self.config.get("filtro") or {})
        if detalle:
            return [
                Resultado(
                    None,
                    None,
                    "saltado",
                    f"No hay ficheros que cumplan el filtro ({detalle}).",
                )
            ]
        return [
            Resultado(
                None, None, "saltado", "No hay ficheros que cumplan el filtro."
            )
        ]


@Accion.registrar("abrir")
class Abrir(Accion):
    """Abre las URLs de la acción en el navegador (o describe la simulación).

    No selecciona ficheros: el motor la ejecuta con la lista vacía y abrir()
    hace su trabajo dentro de aplicar(), que aquí se llama una sola vez.
    """

    def aplicar(
        self,
        fichero: Path,
        n: int,
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> Resultado:
        """Abre las URLs (o describe la simulación). «fichero» no se usa aquí."""
        urls_efectivas = list(urls) if urls else list(self.config.get("urls") or [])
        detalle_urls = " ".join(urls_efectivas)
        if simular:
            return Resultado(
                None,
                None,
                "simulado",
                f"SIMULACIÓN: no se abre ni se toca nada. Acción: {self.config.get('nombre')} "
                f"Navegador: el explorador por defecto Ventana: 1 con {len(urls_efectivas)} pestañas: "
                + detalle_urls,
            )
        lanzar = abrir or (lambda urls_a: [webbrowser.open(url, new=1) for url in urls_a])
        try:
            lanzar(urls_efectivas)
        except OSError as exc:
            raise TareasError(f"No se pudo abrir el navegador: {exc}") from exc
        return Resultado(
            None,
            None,
            "hecho",
            f"Navegador abierto con {len(urls_efectivas)} URL(s).",
        )

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        """Una sola pasada: «abrir» trabaja con URLs, no con ficheros."""
        return [self.aplicar(Path("."), 1, simular, urls, abrir, destino)]


@Accion.registrar("copiar")
class Copiar(Accion):
    """Copia los ficheros elegidos al destino, sin borrar el original."""

    elige_carpetas = True

    def preparar(
        self,
        ficheros: list[Path],
        simular: bool,
        destino: Path | None = None,
    ) -> None:
        """Crea la carpeta destino una sola vez; con simular=True no hace nada."""
        if not simular:
            self._destino_final(destino).mkdir(parents=True, exist_ok=True)

    def aplicar(
        self,
        fichero: Path,
        n: int,
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> Resultado:
        """Copia un elemento al destino (el original se queda donde estaba)."""
        destino_final = self._destino_final(destino)
        original = destino_final / fichero.name
        libre = destino_libre(original)
        # Nunca se pisa: si ya hay algo con ese nombre, se renombra con « (1)».
        nota = " (ya existía: renombrado)" if libre != original else ""
        if simular:
            return Resultado(
                fichero,
                libre,
                "simulado",
                f"SIMULACIÓN: copiaría «{fichero.name}» → «{libre}»{nota}",
            )
        if fichero.is_dir():
            shutil.copytree(fichero, libre, dirs_exist_ok=True)
        else:
            shutil.copy2(str(fichero), str(libre))
        return Resultado(
            fichero, libre, "hecho", f"Copiado: «{fichero.name}» → «{libre}»{nota}"
        )


@Accion.registrar("mover")
class Mover(Accion):
    """Mueve los ficheros elegidos al destino, sin sobrescribir nunca."""

    def preparar(
        self,
        ficheros: list[Path],
        simular: bool,
        destino: Path | None = None,
    ) -> None:
        """Crea la carpeta destino una sola vez; con simular=True no hace nada."""
        if not simular:
            self._destino_final(destino).mkdir(parents=True, exist_ok=True)

    def aplicar(
        self,
        fichero: Path,
        n: int,
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> Resultado:
        """Mueve un elemento al destino; si el nombre está ocupado, « (1)»."""
        libre = destino_libre(self._destino_final(destino) / fichero.name)
        if simular:
            return Resultado(
                fichero,
                libre,
                "simulado",
                f"SIMULACIÓN: movería «{fichero.name}» → «{libre}»",
            )
        shutil.move(str(fichero), str(libre))
        return Resultado(
            fichero, libre, "hecho", f"Movido: «{fichero.name}» → «{libre}»"
        )


@Accion.registrar("renombrar")
class Renombrar(Accion):
    """Renombra cada fichero con la plantilla, sin sobrescribir nunca."""

    def aplicar(
        self,
        fichero: Path,
        n: int,
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> Resultado:
        """Renombra un elemento en su misma carpeta según la plantilla."""
        plantilla = self.config.get("plantilla", "{nombre}{ext}")
        # {base} es el nombre genérico: llega con --nombre (motor lo inyecta
        # como «nombre_generico»); si no se pidió, se usa «Captura».
        base = str(self.config.get("nombre_generico") or "Captura")
        # stat() es solo lectura: vale incluso en simulación.
        fecha = datetime.fromtimestamp(fichero.stat().st_mtime)
        nuevo_nombre = aplicar_plantilla(plantilla, fichero, n, fecha, base)
        if nuevo_nombre == fichero.name:
            # Ya cumple la plantilla: tocarlo solo crearía « (1)» sin sentido.
            return Resultado(
                fichero,
                None,
                "saltado",
                f"Saltado (ya cumple la plantilla): «{fichero.name}»",
            )
        nuevo = destino_libre(fichero.with_name(nuevo_nombre))
        if simular:
            return Resultado(
                fichero,
                nuevo,
                "simulado",
                f"SIMULACIÓN: renombraría «{fichero.name}» → «{nuevo.name}»",
            )
        fichero.rename(nuevo)
        return Resultado(
            fichero,
            nuevo,
            "hecho",
            f"Renombrado: «{fichero.name}» → «{nuevo.name}»",
        )


@Accion.registrar("borrar")
class Borrar(Accion):
    """Borra cada fichero (destructiva: la confirmación la pide la CLI)."""

    destructiva = True

    def aplicar(
        self,
        fichero: Path,
        n: int,
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> Resultado:
        """Borra un elemento (la confirmación la pide la CLI antes de llegar aquí)."""
        if simular:
            return Resultado(
                fichero,
                None,
                "simulado",
                f"SIMULACIÓN: borraría «{fichero.name}»",
            )
        fichero.unlink()
        return Resultado(fichero, None, "hecho", f"Borrado: «{fichero.name}»")


@Accion.registrar("transformar")
class Transformar(Accion):
    """Convierte cada PDF en una carpeta con su index.html y sus páginas en imagen.

    En el destino se dejan compartidos estilos.css, script.js, manuales.json y
    el index.html que lista todos los manuales (ver tareas.html). El índice se
    reescribe una vez, al final (terminar()), no por PDF.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        # Acumula los manuales de esta ejecución para escribir el índice al final.
        self._manuales: dict[str, Any] = {}
        # Destino real de la ejecución (lo pone ejecutar()/preparar()).
        self._destino_ejecucion: Path | None = None

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        """Guarda el destino de esta ejecución (terminar() lo necesita)."""
        self._destino_ejecucion = self._destino_final(destino)
        return super().ejecutar(ficheros, simular, urls, abrir, destino)

    def preparar(
        self,
        ficheros: list[Path],
        simular: bool,
        destino: Path | None = None,
    ) -> None:
        """Recursos compartidos y manuales ya convertidos. Nada con simular."""
        if simular:
            return
        destino_final = self._destino_final(destino)
        destino_final.mkdir(parents=True, exist_ok=True)
        mod_html.escribir_recursos(destino_final)
        self._manuales = {
            str(item.get("nombre", "")): item
            for item in mod_html.leer_manuales(destino_final)
        }

    def aplicar(
        self,
        fichero: Path,
        n: int,
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> Resultado:
        """Convierte un PDF (la lógica vive en tareas/html.py)."""
        if simular:
            return Resultado(
                fichero,
                self._destino_final(destino) / fichero.stem / mod_html.NOMBRE_INDICE,
                "simulado",
                f"SIMULACIÓN: convertiría «{fichero.name}» → "
                f"«{fichero.stem}/{mod_html.NOMBRE_INDICE}»",
            )
        destino_final = self._destino_final(destino)
        registro = mod_html.convertir_pdf(fichero, destino_final)
        self._manuales[str(registro["nombre"])] = registro
        return Resultado(
            fichero,
            destino_final / str(registro["carpeta"]) / mod_html.NOMBRE_INDICE,
            "hecho",
            f"Convertido: «{fichero.name}» → "
            f"«{registro['carpeta']}/{mod_html.NOMBRE_INDICE}» "
            f"({registro['paginas']} página(s))",
        )

    def terminar(self, simular: bool) -> list[Resultado]:
        """Reescribe manuales.json y el index.html de la galería, una sola vez."""
        if simular:
            return []
        destino_final = self._destino_ejecucion or self._destino()
        lista = list(self._manuales.values())
        mod_html.guardar_manuales(destino_final, lista)
        mod_html.escribir_galeria(destino_final, lista)
        return [
            Resultado(
                None,
                destino_final / mod_html.NOMBRE_INDICE,
                "hecho",
                f"Índice actualizado: «{mod_html.NOMBRE_JSON}» y "
                f"«{mod_html.NOMBRE_INDICE}» con {len(lista)} manual(es).",
            )
        ]


@Accion.registrar("comprimir")
class Comprimir(Accion):
    """Comprime los ficheros y carpetas elegidos en un .zip, sin sobrescribir nunca.

    Un solo Resultado: el zip se hace de golpe con TODOS los elementos, así que
    aquí ejecutar() no recorre la lista sino que llama a aplicar() una vez con
    el primero como representante (la lista completa se guarda en _pendientes).
    """

    elige_carpetas = True

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        # Elementos de la ejecución en curso (los pone ejecutar()).
        self._pendientes: list[Path] = []

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        """Una sola pasada: el .zip se escribe de golpe con todos los elementos."""
        if not ficheros:
            return self._resultados_vacio()
        self._pendientes = list(ficheros)
        return [self.aplicar(ficheros[0], 1, simular, urls, abrir, destino)]

    def aplicar(
        self,
        fichero: Path,
        n: int,
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> Resultado:
        """Escribe (o simula) el .zip con todos los elementos seleccionados."""
        destino_final = self._destino_final(destino)
        # El .zip se llama como la carpeta origen; si se pidió --nombre, manda ese
        # (el motor lo deja en «nombre_zip» de la configuración solo para ejecutar).
        nombre = str(self.config.get("nombre_zip") or fichero.parent.name).strip()
        nombre = nombre or str(self.config.get("nombre") or "cliWork")
        libre = destino_libre(destino_final / f"{nombre}.zip")
        nota = " (ya existía: renombrado)" if libre.name != f"{nombre}.zip" else ""
        if simular:
            nombrados = ", ".join(f"«{p.name}»" for p in self._pendientes)
            return Resultado(
                fichero,
                libre,
                "simulado",
                f"SIMULACIÓN: comprimiría {len(self._pendientes)} fichero(s) en «{libre}»"
                f"{nota}: {nombrados}",
            )
        destino_final.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(libre, "w", zipfile.ZIP_DEFLATED) as archivo:
            for pendiente in self._pendientes:
                if pendiente.is_dir():
                    # Una carpeta seleccionada: se comprime su contenido entero.
                    for contenido in sorted(pendiente.rglob("*")):
                        if contenido.is_file():
                            archivo.write(
                                contenido, arcname=contenido.relative_to(pendiente.parent)
                            )
                else:
                    archivo.write(pendiente, arcname=pendiente.name)
        return Resultado(
            fichero,
            libre,
            "hecho",
            f"Comprimido: {len(self._pendientes)} fichero(s) → «{libre}»{nota}",
        )


# Claves del registro que limpia «limpiar-usb» (huellas de USB y de impresoras).
# Rutas de HKLM/HKCU en formato de reg.exe (sin la montura HKLM\...).
_CLAVES_HKLM = (
    r"HKLM\SYSTEM\CurrentControlSet\Enum\USBSTOR",
    r"HKLM\SYSTEM\CurrentControlSet\Enum\USB",
    r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Print\Printers",
    r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports",
)
_CLAVE_HKCU = (
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2"
)
_CABECERA_REG = "Windows Registry Editor Version 5.00"


@Accion.registrar("limpiar-usb")
class LimpiarUSB(Accion):
    """Limpia del registro de Windows las huellas de USB y de impresoras.

    Solo Windows y con permisos de administrador (menos en --simular, que
    solo enumera). Borra: impresoras (desinstalándolas de verdad y vaciando
    sus claves), los puertos USB00x que no estén en «puertos_conservar» y el
    historial (Enum\\USBSTOR, Enum\\USB, MountPoints2). Antes exporta una
    copia .reg restaurable. El reinicio del equipo lo pide la CLI al terminar.
    """

    destructiva = True

    def ejecutar(
        self,
        ficheros: list[Path],
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        """Una sola pasada: trabaja con el registro, no con ficheros."""
        if sys.platform != "win32":
            raise TareasError(
                "La acción «limpiar-usb» solo funciona en Windows: el registro "
                "de Windows no existe en este sistema."
            )
        if not simular and not self._es_administrador():
            raise TareasError(
                "Se necesitan permisos de administrador para limpiar el registro "
                "de Windows: vuelve a lanzar la CLI desde un terminal de "
                "administrador."
            )
        resultados: list[Resultado] = []

        # Copia de seguridad .reg de TODAS las claves que se van a tocar.
        copia = Path(str(self.config.get("copia_seguridad"))).expanduser()
        resultado_copia = self._exportar_copia(copia, simular)
        if resultado_copia is not None:
            resultados.append(resultado_copia)

        resultados.extend(self._limpiar_impresoras(simular))
        resultados.extend(self._limpiar_puertos(simular))
        resultados.extend(self._limpiar_historial(simular))
        return resultados

    def aplicar(
        self,
        fichero: Path,
        n: int,
        simular: bool,
        urls: list[str] | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        destino: Path | None = None,
    ) -> Resultado:
        """No se usa: «limpiar-usb» trabaja con el registro, no por fichero."""
        raise NotImplementedError("limpiar-usb no trabaja por ficheros.")

    # --- copia de seguridad ---------------------------------------------------

    def _exportar_copia(self, copia: Path, simular: bool) -> Resultado | None:
        """Exporta con reg.exe todas las claves a UN fichero .reg restaurable."""
        if simular:
            return Resultado(
                None,
                copia,
                "simulado",
                f"SIMULACIÓN: guardaría la copia de seguridad en «{copia}».",
            )
        partes: list[str] = [_CABECERA_REG]
        for clave in (*_CLAVES_HKLM, _CLAVE_HKCU):
            with tempfile.TemporaryDirectory() as tmp:
                trozo = Path(tmp) / "trozo.reg"
                hecho = subprocess.run(
                    ["reg", "export", clave, str(trozo), "/y"],
                    capture_output=True,
                    text=False,
                    check=False,
                )
            if hecho.returncode != 0:
                # La clave no existe o no se puede leer: se sigue sin ella.
                continue
            texto = trozo.read_text(encoding="utf-16")
            lineas = texto.splitlines()
            # Se quita la cabecera repetida y las líneas en blanco del principio.
            cuerpo = [l for l in lineas[1:] if l.strip()]
            partes.extend(cuerpo)
        copia.parent.mkdir(parents=True, exist_ok=True)
        copia.write_text("\r\n".join(partes) + "\r\n", encoding="utf-16")
        return Resultado(
            None,
            copia,
            "hecho",
            f"Copia de seguridad guardada en «{copia}» (se puede restaurar con regedit).",
        )

    # --- impresoras -----------------------------------------------------------

    def _limpiar_impresoras(self, simular: bool) -> list[Resultado]:
        """Desinstala las impresoras de verdad y vacía su clave de conexiones."""
        import winreg

        resultados: list[Resultado] = []
        try:
            con_clave = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Print\Printers",
            )
        except FileNotFoundError:
            return resultados
        with con_clave:
            nombres = self._listar_subclaves(con_clave)
        for nombre in nombres:
            if simular:
                resultados.append(
                    Resultado(
                        None, None, "simulado",
                        f"SIMULACIÓN: desinstalaría la impresora «{nombre}».",
                    )
                )
                continue
            hecho = subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    f"Remove-Printer -Name '{nombre}'",
                ],
                capture_output=True, text=True, check=False,
            )
            if hecho.returncode == 0:
                resultados.append(
                    Resultado(None, None, "hecho", f"Desinstalada la impresora «{nombre}».")
                )
            else:
                resultados.append(
                    Resultado(
                        None, None, "saltado",
                        f"No se pudo desinstalar la impresora «{nombre}»: "
                        f"{(hecho.stderr or '').strip()}",
                    )
                )
        # La clave de conexiones que se borra a mano (SOFTWARE\...\Print\Printers).
        resultados.extend(
            self._borrar_subclaves(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Print\Printers",
                simular,
                etiqueta="claves de conexiones de impresora",
            )
        )
        return resultados

    # --- puertos USB ----------------------------------------------------------

    def _limpiar_puertos(self, simular: bool) -> list[Resultado]:
        """Borra de la clave Ports los puertos USB00x que no se conservan."""
        import winreg

        conservar = {
            str(p).upper()
            for p in (self.config.get("puertos_conservar") or [])
        }
        resultados: list[Resultado] = []
        try:
            con_clave = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports",
                0,
                # Con --simular basta leer; para borrar hace falta escribir.
                winreg.KEY_READ if simular else winreg.KEY_ALL_ACCESS,
            )
        except FileNotFoundError:
            return resultados
        except PermissionError:
            if simular:
                return [
                    Resultado(
                        None, None, "saltado",
                        "Sin permisos para leer la clave «Ports».",
                    )
                ]
            return [
                Resultado(
                    None, None, "saltado",
                    "Sin permisos para tocar la clave «Ports»: ejecuta la CLI "
                    "como administrador.",
                )
            ]
        with con_clave:
            puertos = []
            indice = 0
            while True:
                try:
                    nombre, _, _ = winreg.EnumValue(con_clave, indice)
                except OSError:
                    break
                indice += 1
                if nombre.upper().startswith("USB") and nombre.upper() not in conservar:
                    puertos.append(nombre)
        for puerto in puertos:
            if simular:
                resultados.append(
                    Resultado(
                        None, None, "simulado",
                        f"SIMULACIÓN: borraría el puerto «{puerto}» "
                        f"(se conservan: {', '.join(sorted(conservar))}).",
                    )
                )
                continue
            try:
                winreg.DeleteValue(
                    winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports",
                        0,
                        winreg.KEY_SET_VALUE,
                    ),
                    puerto,
                )
                resultados.append(
                    Resultado(None, None, "hecho", f"Borrado el puerto «{puerto}».")
                )
            except OSError as exc:
                resultados.append(
                    Resultado(
                        None, None, "saltado",
                        f"No se pudo borrar el puerto «{puerto}»: {exc}",
                    )
                )
        if not resultados:
            resultados.append(
                Resultado(
                    None, None, "saltado",
                    f"No hay puertos USB00x que borrar "
                    f"(se conservan: {', '.join(sorted(conservar))}).",
                )
            )
        return resultados

    # --- historial de USB -----------------------------------------------------

    def _limpiar_historial(self, simular: bool) -> list[Resultado]:
        """Vacía Enum\\USBSTOR, Enum\\USB y MountPoints2 (huellas de USB)."""
        import winreg

        resultados: list[Resultado] = []
        for hive, clave, etiqueta in (
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\USBSTOR",
             "USBSTOR (memorias conectadas)"),
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\USB",
             "Enum\\USB (dispositivos USB)"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion"
             r"\Explorer\MountPoints2",
             "MountPoints2 (letras de unidad)"),
        ):
            resultados.extend(
                self._borrar_subclaves(hive, clave, simular, etiqueta=etiqueta)
            )
        return resultados

    # --- utilidades de registro ------------------------------------------------

    @staticmethod
    def _es_administrador() -> bool:
        """True si el proceso va con el token elevado de administrador."""
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except (AttributeError, OSError):
            return False

    @staticmethod
    def _listar_subclaves(con_clave: Any) -> list[str]:
        """Los nombres de las subclaves de una clave abierta."""
        import winreg

        subclaves = []
        indice = 0
        while True:
            try:
                subclaves.append(winreg.EnumKey(con_clave, indice))
            except OSError:
                break
            indice += 1
        return subclaves

    def _borrar_subclaves(
        self, hive: Any, clave: str, simular: bool, etiqueta: str
    ) -> list[Resultado]:
        """Borra (o enumera, con --simular) TODAS las subclaves de una clave."""
        import winreg

        resultado: list[Resultado] = []
        try:
            con_clave = winreg.OpenKey(hive, clave)
        except FileNotFoundError:
            return []
        with con_clave:
            subclaves = self._listar_subclaves(con_clave)
        if not subclaves:
            resultado.append(
                Resultado(None, None, "saltado", f"«{etiqueta}» ya está vacía.")
            )
            return resultado
        for subclave in subclaves:
            ruta = f"{clave}\\{subclave}"
            if simular:
                resultado.append(
                    Resultado(
                        None, None, "simulado",
                        f"SIMULACIÓN: borraría la clave «{ruta}».",
                    )
                )
                continue
            if self._borrar_clave_recursivo(hive, ruta):
                resultado.append(
                    Resultado(None, None, "hecho", f"Borrada la clave «{ruta}».")
                )
            else:
                resultado.append(
                    Resultado(
                        None, None, "saltado",
                        f"No se pudo borrar «{ruta}»: sin permisos (SYSTEM). "
                        f"Toma posesión a mano con regedit si hace falta.",
                    )
                )
        return resultado

    @staticmethod
    def _borrar_clave_recursivo(hive: Any, ruta: str) -> bool:
        """Borra una clave y todas sus subclaves. True si se borró."""
        import winreg

        try:
            con_clave = winreg.OpenKey(hive, ruta, 0, winreg.KEY_ALL_ACCESS)
        except (FileNotFoundError, PermissionError):
            return False
        with con_clave:
            for subclave in LimpiarUSB._listar_subclaves(con_clave):
                if not LimpiarUSB._borrar_clave_recursivo(hive, f"{ruta}\\{subclave}"):
                    return False
        try:
            winreg.DeleteKey(hive, ruta)
        except (FileNotFoundError, PermissionError, OSError):
            return False
        return True


class ErrorConfiguracion(ConfigError):
    """Nombre antiguo de ConfigError: lo usa cli.py y los tests.

    Es SubClase de ConfigError, así que quien capture TareasError también
    los captura. La carga real vive en config.cargar(): aquí solo se delega
    para re-etiquetar la excepción (fuente única en config.py).
    """


def cargar_acciones(ruta: Path) -> list[dict[str, Any]]:
    """Lee el JSON y devuelve la lista de acciones (delegando en config.cargar).

    Lanza ErrorConfiguracion (un ConfigError) si la ruta no es un fichero
    legible, el JSON está roto (con línea y columna) o la estructura no es
    la de "version" + "acciones".
    """
    try:
        return mod_config.cargar(ruta)
    except ConfigError as exc:
        raise ErrorConfiguracion(str(exc)) from exc


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
