"""CLI de tareas: órdenes de la aplicación: aquí solo hay órdenes, opciones y salida."""

from __future__ import annotations

import difflib
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, NoReturn

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

import tareas
from tareas import config
from tareas.acciones import (
    CAMPOS_POR_TIPO,
    ErrorConfiguracion,
    NAVEGADORES,
    RUTA_ACCIONES,
    TIPOS_CONOCIDOS,
    abrir_en_navegador,
    abrir_por_defecto,
    buscar_navegador,
    cargar_acciones,
    validar_acciones,
)
from tareas.acciones import _NOMBRE_KEBAB
from tareas.errores import AccionNoValida, TareasError
from tareas.motor import Motor

consola = Console()
consola_err = Console(stderr=True)

# El fichero de acciones lleva texto en español: la consola escribe UTF-8.
for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError, OSError):
        pass

app = typer.Typer(
    help="Automatiza tareas repetitivas con ficheros desde la terminal.",
    add_completion=True,
    no_args_is_help=True,
)


def _error(mensaje: str, codigo: int = 1) -> NoReturn:
    """Escribe un mensaje en stderr y sale con el código indicado (1 por defecto)."""
    typer.echo(mensaje, err=True)
    raise typer.Exit(code=codigo)


def _error_validacion(mensaje: str, codigo: int = 3) -> NoReturn:
    """Error de validación: mensaje en rojo por stderr, sin traceback, con el código."""
    consola_err.print(f"[red]Error:[/red] {escape(mensaje)}")
    raise typer.Exit(code=codigo)


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


def _mensaje_no_existe(nombre: str, lista: list[dict[str, Any]]) -> str:
    """Mensaje de «no existe la acción»; si hay una parecida, la sugiere."""
    nombres = [str(item.get("nombre", "")) for item in lista]
    sugerencias = difflib.get_close_matches(nombre, nombres, n=1, cutoff=0.6)
    if sugerencias:
        return f"No existe la acción: {nombre}. ¿Quisiste decir «{sugerencias[0]}»?"
    return f"No existe la acción: {nombre}"


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


@app.command()
def acciones(
    nombre: Annotated[
        str | None,
        typer.Argument(
            help="Nombre de la acción a ver en detalle. Sin argumento, lista todas."
        ),
    ] = None,
) -> None:
    """Muestra las acciones definidas en el fichero de acciones."""
    try:
        lista = cargar_acciones(RUTA_ACCIONES)
    except ErrorConfiguracion as exc:
        _error(str(exc), codigo=3)

    errores, avisos = validar_acciones(lista)
    for aviso in avisos:
        consola_err.print(f"[yellow]Aviso:[/yellow] {escape(aviso)}")
    if errores:
        for error in errores:
            consola_err.print(f"[red]Error:[/red] {escape(error)}")
        _error(f"El fichero {RUTA_ACCIONES} tiene {len(errores)} error(es).", codigo=3)

    if not lista:
        typer.echo("Aviso: no hay ninguna acción definida.", err=True)
        return

    if nombre is not None:
        accion = next(
            (item for item in lista if item.get("nombre") == nombre), None
        )
        if accion is None:
            _error(_mensaje_no_existe(nombre, lista))
        _mostrar_detalle(accion)
        return

    filas = sorted(lista, key=lambda accion: str(accion.get("nombre", "")))
    tabla = Table(title=f"Acciones de {escape(str(RUTA_ACCIONES))}")
    tabla.add_column("Nombre", style="cyan")
    tabla.add_column("Tipo")
    tabla.add_column("Descripción")
    for accion in filas:
        tabla.add_row(
            escape(str(accion.get("nombre", ""))),
            escape(str(accion.get("tipo", ""))),
            escape(str(accion.get("descripcion", ""))),
        )
    consola.print(tabla)


def _mostrar_detalle(accion: dict[str, Any]) -> None:
    """Muestra una acción en una tabla de campo/valor."""
    tabla = Table(title=f"Acción {escape(str(accion.get('nombre', '')))}")
    tabla.add_column("Campo", style="cyan")
    tabla.add_column("Valor")
    for campo, valor in accion.items():
        if isinstance(valor, list):
            texto = "\n".join(str(item) for item in valor)
        elif isinstance(valor, dict):
            texto = ", ".join(f"{clave}: {valor[clave]}" for clave in valor)
        else:
            texto = str(valor)
        tabla.add_row(escape(str(campo)), escape(texto))
    consola.print(tabla)


def _validar_accion(accion: Any, indice: int, nombres_vistos: set[str]) -> None:
    """Comprueba una sola acción y lanza AccionNoValida si no cumple el esquema."""
    if not isinstance(accion, dict):
        raise AccionNoValida(
            {"nombre": f"acción {indice}"},
            "estructura",
            "debe ser un objeto JSON con sus campos.",
        )

    nombre = accion.get("nombre")
    if not isinstance(nombre, str) or not nombre:
        raise AccionNoValida(accion, "nombre", "falta el campo «nombre».")
    if not _NOMBRE_KEBAB.match(nombre):
        raise AccionNoValida(
            accion, "nombre", "debe ir en minúsculas con guiones (kebab-case)."
        )
    if nombre in nombres_vistos:
        raise AccionNoValida(accion, "nombre", "duplicado; cada acción debe ser única.")
    nombres_vistos.add(nombre)

    descripcion = accion.get("descripcion")
    if not isinstance(descripcion, str) or not descripcion.strip():
        raise AccionNoValida(accion, "descripcion", "falta «descripcion» (un texto no vacío).")

    tipo = accion.get("tipo")
    if not isinstance(tipo, str) or not tipo:
        raise AccionNoValida(accion, "tipo", "falta el campo «tipo».")
    if tipo not in TIPOS_CONOCIDOS:
        raise AccionNoValida(
            accion, "tipo", f"tipo «{tipo}» desconocido. Válidos: {', '.join(TIPOS_CONOCIDOS)}."
        )

    if "confirmar" in accion and not isinstance(accion["confirmar"], bool):
        raise AccionNoValida(accion, "confirmar", "debe ser true o false.")

    for campo in CAMPOS_POR_TIPO[tipo]:
        if campo not in accion:
            raise AccionNoValida(accion, campo, f"al tipo «{tipo}» le falta el campo «{campo}».")

    if tipo == "abrir":
        urls = accion.get("urls")
        if not isinstance(urls, list) or not urls:
            raise AccionNoValida(accion, "urls", "debe ser una lista con al menos una dirección.")
        for indice_url, url in enumerate(urls, start=1):
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                raise AccionNoValida(
                    accion, "urls", f"la URL {indice_url} no empieza por http:// o https://: {url!r}."
                )

    if "filtro" in accion:
        filtro = accion["filtro"]
        if not isinstance(filtro, dict):
            raise AccionNoValida(accion, "filtro", "debe ser un objeto JSON.")
        if "extensiones" in filtro and not isinstance(filtro["extensiones"], list):
            raise AccionNoValida(accion, "filtro.extensiones", "debe ser una lista.")
        if "extensiones" not in filtro and "patron" not in filtro:
            raise AccionNoValida(accion, "filtro", "necesita «extensiones» o «patron».")
        if tipo == "borrar" and "patron" not in filtro:
            raise AccionNoValida(accion, "filtro", f"al tipo «borrar» le falta «filtro.patron».")
        if "mas_antiguo_que_dias" in filtro:
            dias = filtro["mas_antiguo_que_dias"]
            if isinstance(dias, bool) or not isinstance(dias, int) or dias <= 0:
                raise AccionNoValida(
                    accion,
                    "filtro.mas_antiguo_que_dias",
                    f"debe ser un número de días mayor que 0 (encontrado: {dias!r}).",
                )

    for campo in ("origen", "destino", "plantilla"):
        if campo in accion and (not isinstance(accion[campo], str) or not accion[campo].strip()):
            raise AccionNoValida(accion, campo, f"«{campo}» debe ser un texto no vacío.")


@app.command()
def validar(
    fichero: Annotated[
        Path,
        typer.Argument(
            help="Fichero JSON a validar. Por defecto, src/tareas/docs/acciones.json."
        ),
    ] = config.RUTA_ACCIONES,
) -> None:
    """Comprueba que el fichero de acciones está bien escrito."""
    ruta = fichero.expanduser()

    try:
        acciones = config.cargar(ruta)
        nombres_vistos: set[str] = set()
        for indice, accion in enumerate(acciones, start=1):
            _validar_accion(accion, indice, nombres_vistos)
    except TareasError as exc:
        _error_validacion(str(exc), exc.codigo_salida)

    consola.print(f"[green]✔ {len(acciones)} acciones válidas[/green]")


@app.command()
def ejecutar(
    nombre: Annotated[
        str,
        typer.Argument(help="Nombre de la acción a ejecutar (ej.: abrir-nav)."),
    ],
    url: Annotated[
        str | None,
        typer.Argument(
            help="Abre esta URL en lugar de las del fichero (ej.: https://epson.com)."
        ),
    ] = None,
    simular: Annotated[
        bool,
        typer.Option(
            "--simular",
            help="Solo muestra qué haría: no pregunta, no abre ni toca nada.",
        ),
    ] = False,
    google: Annotated[
        bool,
        typer.Option("--google", "-g", help="Usa Google Chrome."),
    ] = False,
    firefox: Annotated[
        bool,
        typer.Option("--firefox", "-f", help="Usa Mozilla Firefox."),
    ] = False,
    edge: Annotated[
        bool,
        typer.Option("--edge", "-e", help="Usa Microsoft Edge."),
    ] = False,
) -> None:
    """Ejecuta una de las acciones definidas en el fichero de acciones."""
    pedidos = [
        clave
        for clave, activo in (
            ("chrome", google),
            ("firefox", firefox),
            ("edge", edge),
        )
        if activo
    ]
    if len(pedidos) > 1:
        _error("Elige un solo navegador: -g (Chrome), -f (Firefox) o -e (Edge).")
    navegador = pedidos[0] if pedidos else None
    destino = NAVEGADORES[navegador] if navegador else "el explorador por defecto"
    ruta_navegador = buscar_navegador(navegador) if navegador else None

    try:
        lista = config.cargar(RUTA_ACCIONES)
    except TareasError as exc:
        _error(str(exc), codigo=exc.codigo_salida)

    errores, _ = validar_acciones(lista)
    if errores:
        _error(
            f"El fichero de acciones tiene {len(errores)} error(es). "
            f"Ejecuta «tareas validar» para verlos.",
            codigo=3,
        )

    motor = Motor(lista)
    accion = motor.acciones.get(nombre)

    if url is not None and not url.startswith(("http://", "https://")):
        _error(f"La URL debe empezar por http:// o https://: {url}", codigo=1)

    if simular:
        try:
            resultados = motor.ejecutar(
                nombre,
                None,
                True,
                urls=([url] if url is not None else None),
                navegador=navegador,
                ruta_navegador=str(ruta_navegador) if ruta_navegador else None,
            )
        except TareasError as exc:
            _error(str(exc), codigo=exc.codigo_salida)
        for resultado in resultados:
            typer.echo(resultado.mensaje)
            if not resultado.exito:
                _error(resultado.mensaje, codigo=1)
        return

    if accion is None:
        _error(_mensaje_no_existe(nombre, lista), codigo=1)

    if accion.config.get("tipo") != "abrir":
        _error(
            f"La acción «{nombre}» es de tipo «{accion.config.get('tipo')}» y todavía no está "
            f"implementado (solo «abrir»).",
            codigo=1,
        )

    urls_efectivas = (
        list(url) if url is not None else list(accion.config.get("urls") or [])
    )
    pestañas = "1 pestaña" if len(urls_efectivas) == 1 else f"{len(urls_efectivas)} pestañas"

    if accion.config.get("confirmar", False):
        typer.confirm(f"¿Abrir {destino} con {pestañas}?", abort=True)

    try:
        resultados = motor.ejecutar(
            nombre,
            None,
            False,
            urls=([url] if url is not None else None),
            navegador=navegador,
            ruta_navegador=str(ruta_navegador) if ruta_navegador else None,
            abrir=(
                (lambda urls_a: abrir_en_navegador(navegador, urls_a))
                if navegador
                else (lambda urls_a: abrir_por_defecto(urls_a))
            ),
        )
    except TareasError as exc:
        _error(str(exc), codigo=exc.codigo_salida)

    for resultado in resultados:
        typer.echo(resultado.mensaje)
        if not resultado.exito:
            _error(resultado.mensaje, codigo=1)
