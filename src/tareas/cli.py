"""CLI de tareas: órdenes de la aplicación: aquí solo hay órdenes, opciones y salida."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

import tareas

consola = Console()
consola_err = Console(stderr=True)

app = typer.Typer(
    help="Automatiza tareas repetitivas con ficheros desde la terminal.",
    add_completion=False,
    no_args_is_help=True,
)


def _error(mensaje: str) -> NoReturn:
    """Escribe un mensaje en stderr y sale con código 1."""
    typer.echo(mensaje, err=True)
    raise typer.Exit(code=1)


def tamano_legible(n: int) -> str:
    """Convierte bytes en texto: 532 B, 1.2 KB, 3.4 MB..."""
    if n < 1024:
        return f"{n} B"
    tamano = float(n)
    unidad = "B"
    for unidad in ("KB", "MB", "GB", "TB"):
        tamano /= 1024
        if tamano < 1024:
            break
    return f"{tamano:.1f} {unidad}"


def _fecha_hora(momento: float) -> str:
    """Formatea un timestamp como AAAA-MM-DD HH:MM."""
    return datetime.fromtimestamp(momento).strftime("%Y-%m-%d %H:%M")


@app.command()
def version() -> None:
    """Muestra la versión de tareas."""
    typer.echo(f"tareas {tareas.__version__}")


@app.command()
def listar(
    carpeta: Annotated[
        Path,
        typer.Argument(help="Carpeta a listar. Por defecto, la actual. Admite ~."),
    ] = Path("."),
) -> None:
    """Muestra el contenido de una carpeta en una tabla."""
    ruta = carpeta.expanduser()

    if not ruta.is_dir():
        if ruta.exists():
            _error(f"No es una carpeta: {ruta}")
        _error(f"No existe la carpeta: {ruta}")

    try:
        entradas = list(ruta.iterdir())
    except OSError:
        _error(f"No se puede leer la carpeta: {ruta}")

    if not entradas:
        typer.echo(f"Aviso: la carpeta {ruta} está vacía.", err=True)
        return

    filas: list[tuple[bool, str, list[str]]] = []
    for entrada in entradas:
        try:
            datos = entrada.stat()
        except OSError:
            continue
        es_carpeta = entrada.is_dir()
        if es_carpeta:
            tipo = "carpeta"
            tamano = "—"
        else:
            tipo = entrada.suffix or "—"
            tamano = tamano_legible(datos.st_size)
        celdas = [
            escape(entrada.name),
            escape(tipo),
            tamano,
            _fecha_hora(datos.st_mtime),
        ]
        filas.append((es_carpeta, entrada.name, celdas))

    if not filas:
        typer.echo(f"Aviso: no se pudo leer ningún contenido de {ruta}.", err=True)
        return

    filas.sort(key=lambda fila: (not fila[0], fila[1].casefold()))

    tabla = Table(title=f"Contenido de {escape(str(ruta))}")
    tabla.add_column("Nombre", style="cyan")
    tabla.add_column("Tipo")
    tabla.add_column("Tamaño", justify="right")
    tabla.add_column("Modificado")
    for _, _, celdas in filas:
        tabla.add_row(*celdas)
    consola.print(tabla)
