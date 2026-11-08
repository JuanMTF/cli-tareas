"""Motor de ejecución de acciones: búsqueda, selección y efectos."""

from __future__ import annotations

import difflib
import re
import time
from pathlib import Path
from typing import Any, Callable

from tareas.acciones import Accion, NAVEGADORES, Resultado
from tareas.errores import TareasError


class Motor:
    """Ejecuta las acciones del fichero: las busca, selecciona y ejecuta."""

    # Acciones que archivan (comprimir, copiar): admite «carpetas» como origen,
    # no solo ficheros sueltos. Mover/borrar/renombrar se aplican a ficheros.
    TIPOS_CON_CARPETAS = ("comprimir", "copiar")

    def __init__(self, acciones: list[dict[str, Any]]) -> None:
        self.acciones = {a["nombre"]: Accion.desde_config(a) for a in acciones}

    @staticmethod
    def seleccionar(
        carpeta: Path, filtro: dict[str, Any], incluye_carpetas: bool = False
    ) -> list[Path]:
        """Devuelve los ficheros (y carpetas, si se pide) que cumplen el filtro."""
        exts = {e.lower() for e in filtro.get("extensiones", [])}
        patron = re.compile(filtro["patron"]) if "patron" in filtro else None
        dias = filtro.get("mas_antiguo_que_dias")
        mb = filtro.get("mayor_que_mb")
        ahora = time.time()
        elegidos = []
        for f in sorted(carpeta.iterdir()):
            if not incluye_carpetas and not f.is_file():
                continue
            if f.is_file():
                if exts and f.suffix.lower() not in exts:
                    continue
                if patron and not patron.search(f.name):
                    continue
            if dias and ahora - f.stat().st_mtime < dias * 86400:
                continue
            if mb and f.stat().st_size < mb * 1024 * 1024:
                continue
            elegidos.append(f)
        return elegidos

    def ejecutar(
        self,
        nombre: str,
        carpeta: Path | None,
        simular: bool,
        urls: list[str] | None = None,
        navegador: str | None = None,
        ruta_navegador: str | None = None,
        abrir: Callable[[list[str]], None] | None = None,
        antiguedad: int | None = None,
        destino: Path | None = None,
    ) -> list[Resultado]:
        """Ejecuta una acción y devuelve la lista de resultados.

        Para el tipo «abrir» abre las URLs (o describe la simulación); para el
        resto selecciona ficheros en la carpeta y los mueve/borra/etc.
        """
        accion = self.acciones.get(nombre)
        if accion is None:
            sugerencias = difflib.get_close_matches(
                nombre, list(self.acciones), n=1, cutoff=0.6
            )
            detalle = f" ¿Quisiste decir «{sugerencias[0]}»?" if sugerencias else ""
            raise TareasError(f"No existe la acción: {nombre}.{detalle}")

        tipo = accion.config.get("tipo")

        if tipo == "abrir":
            urls_efectivas = list(urls) if urls else list(accion.config.get("urls") or [])

            if simular:
                navegador_mensaje = NAVEGADORES[navegador] if navegador else "el explorador por defecto"
                mensaje = (
                    f"SIMULACIÓN: no se abre ni se toca nada. Acción: {nombre} "
                    f"Navegador: {navegador_mensaje} Ventana: 1 con {len(urls_efectivas)} pestañas: "
                    + " ".join(urls_efectivas)
                )
                if ruta_navegador:
                    mensaje += f" Ejecutable: {ruta_navegador}"
                return [Resultado(True, mensaje)]

            if navegador and ruta_navegador is None:
                raise TareasError(f"No se encontró {NAVEGADORES[navegador]} en este equipo.")

            return accion.ejecutar([], False, urls_efectivas, abrir=abrir)

        # Acciones sobre ficheros: mover, renombrar, borrar, transformar, comprimir.
        carpeta_ejecucion = (carpeta or Path(accion.config.get("origen") or ".")).expanduser()
        if not carpeta_ejecucion.is_dir():
            raise TareasError(
                f"La carpeta {carpeta_ejecucion} no existe. "
                f"Crea la carpeta o indica otra con --carpeta RUTA (admite ~)."
            )

        filtro = dict(accion.config.get("filtro") or {})
        if antiguedad is not None:
            # La opción de la CLI manda sobre el valor del fichero («mas_antiguo_que_dias»).
            filtro["mas_antiguo_que_dias"] = antiguedad
        ficheros = self.seleccionar(
            carpeta_ejecucion,
            filtro,
            incluye_carpetas=tipo in self.TIPOS_CON_CARPETAS,
        )
        return accion.ejecutar(ficheros, simular, urls, abrir, destino)
