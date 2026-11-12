"""CLI de tareas: órdenes de la aplicación: aquí solo hay órdenes, opciones y salida."""

from __future__ import annotations

import difflib
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, NoReturn

from tareas import traduccion

# Antes que typer, para que sus rótulos, su ayuda y sus errores salgan en
# español (ver traduccion.py).
traduccion.instalar()

import typer
from click.shell_completion import CompletionItem
from rich.console import Console
from rich.markup import escape
from rich.table import Table

import tareas
from tareas import config
from tareas import html as mod_html
from tareas.acciones import (
    ErrorConfiguracion,
    NAVEGADORES,
    RUTA_ACCIONES,
    Resultado,
    abrir_en_navegador,
    abrir_por_defecto,
    buscar_navegador,
    cargar_acciones,
    validar_acciones,
)
from tareas.errores import ConfigError, TareasError
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


@app.callback()
def principal(
    ctx: typer.Context,
    config_ruta: Annotated[
        Path,
        typer.Option(
            "--config",
            help=(
                "Fichero JSON de acciones. Opción GLOBAL: va justo después de "
                "«cliWork», con su valor, y ANTES de la orden "
                "(ej.: cliWork --config ~/mi-acciones.json validar). "
                "Por defecto, el empaquetado. Admite ~."
            ),
            show_default=False,
            metavar="",
        ),
    ] = config.RUTA_ACCIONES,
) -> None:
    """Opciones globales de la CLI (se ponen justo después de «cliWork»)."""
    ctx.obj = {"ruta_config": config_ruta.expanduser()}


def _error(mensaje: str, codigo: int = 1) -> NoReturn:
    """Error previsto: mensaje en rojo por stderr, sin traceback, y sale con el código."""
    consola_err.print(f"[red]Error:[/red] {escape(mensaje)}")
    raise typer.Exit(code=codigo)


def _error_validacion(mensaje: str, codigo: int = 3) -> NoReturn:
    """Error de validación (ConfigError): igual que _error, con código 3 por defecto."""
    _error(mensaje, codigo)


def _ruta_config(ctx: Any) -> Path:
    """La ruta del fichero de acciones que guardó el callback global en ctx.obj.

    Si no hay ctx (autocompletado fuera de la CLI) o no lleva obj, se usa la
    empaquetada.
    """
    obj = ctx.obj if ctx is not None and isinstance(ctx.obj, dict) else {}
    return Path(obj.get("ruta_config") or config.RUTA_ACCIONES).expanduser()


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
    """Muestra la versión de cliWork."""
    typer.echo(f"cliWork {tareas.__version__}")


@app.command(
    epilog=(
        "Ejemplos: cliWork listar ~/pruebas-tareas   ·   la carpeta admite ~ y "
        "se escribe entre comillas si lleva espacios: cliWork listar \"~/mi carpeta\"."
    )
)
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


@app.command(
    epilog=(
        "Con NOMBRE muestra el detalle de esa acción (tipo, filtro, origen...): "
        "cliWork acciones ordenar-descargas.   ·   El fichero de acciones se "
        "cambia con la opción global --config (va antes de la orden)."
    )
)
def acciones(
    ctx: typer.Context,
    nombre: Annotated[
        str | None,
        typer.Argument(
            help="Nombre de la acción a ver en detalle. Sin argumento, lista todas."
        ),
    ] = None,
) -> None:
    """Muestra las acciones definidas en el fichero de acciones."""
    ruta_config = _ruta_config(ctx)
    try:
        lista = cargar_acciones(ruta_config)
    except ErrorConfiguracion as exc:
        _error(str(exc), codigo=3)

    errores, avisos = validar_acciones(lista)
    for aviso in avisos:
        consola_err.print(f"[yellow]Aviso:[/yellow] {escape(aviso)}")
    if errores:
        for error in errores:
            consola_err.print(f"[red]Error:[/red] {escape(error)}")
        _error(f"El fichero {ruta_config} tiene {len(errores)} error(es).", codigo=3)

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
    tabla = Table(title=f"Acciones de {escape(str(ruta_config))}")
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


@app.command(
    epilog=(
        "Ejemplos: cliWork validar (el JSON empaquetado, o el de --config)   ·   "
        "cliWork validar ~/mi-acciones.json (otro fichero).   ·   Si algo falla, "
        "dice cada error y sale con el código 3."
    )
)
def validar(
    ctx: typer.Context,
    fichero: Annotated[
        Path | None,
        typer.Argument(
            help="Fichero JSON a validar. Por defecto, el que marca la opción global --config."
        ),
    ] = None,
) -> None:
    """Comprueba que el fichero de acciones está bien escrito."""
    ruta = fichero.expanduser() if fichero is not None else _ruta_config(ctx)

    try:
        acciones = config.cargar(ruta)
    except TareasError as exc:
        _error_validacion(str(exc), exc.codigo_salida)

    # Acumula TODOS los errores y avisos de una sola pasada.
    errores, avisos = validar_acciones(acciones)

    for aviso in avisos:
        consola.print(f"[yellow]Aviso:[/yellow] {escape(aviso)}")

    if errores:
        consola_err.print(f"[red]Se encontraron {len(errores)} errores:[/red]")
        for error in errores:
            consola_err.print(f"[red]- {escape(error)}[/red]")
        raise typer.Exit(code=ConfigError.codigo_salida)

    consola.print(f"[green]✔ {len(acciones)} acciones válidas[/green]")


def _reiniciar_equipo() -> None:
    """Programa el reinicio de Windows (aviso de 10 s, se puede cancelar)."""
    try:
        subprocess.run(
            ["shutdown", "/r", "/t", "10", "/c",
             "cliWork: reinicio obligatorio tras limpiar el registro de USB"],
            check=False,
        )
    except OSError as exc:
        _error(f"No se pudo programar el reinicio: {exc}")
    consola.print(
        "[yellow]El equipo se reiniciará en 10 segundos "
        "(cancela con «shutdown /a» si te ha pillado).[/yellow]"
    )


def _destino_transformar() -> Path | None:
    """Destino por defecto de «indexar»: el de la acción transformar del JSON."""
    try:
        acciones = config.cargar(RUTA_ACCIONES)
    except TareasError:
        return None
    for accion in acciones:
        if accion.get("tipo") == "transformar" and accion.get("destino"):
            return Path(str(accion["destino"])).expanduser()
    return None


@app.command(
    epilog=(
        "Ejemplos: cliWork indexar ~/Downloads/DAM --simular (solo mira qué "
        "haría: no convierte ni escribe nada)   ·   cliWork indexar "
        "~/Downloads/DAM (convierte y actualiza manuales.json)   ·   el destino "
        "se cambia con -d/--destino (por defecto, el del JSON)."
    )
)
def indexar(
    carpeta: Annotated[
        str,
        typer.Argument(
            help="Carpeta con los PDF a revisar (ej.: C:\\Users\\x\\Downloads\\DAM). Admite ~."
        ),
    ],
    destino: Annotated[
        str | None,
        typer.Option(
            "--destino",
            "-d",
            help="Carpeta donde están los manuales convertidos. Por defecto, la del JSON.",
        ),
    ] = None,
    simular: Annotated[
        bool,
        typer.Option(
            "--simular",
            help="Solo muestra qué haría: no convierte ni escribe nada.",
        ),
    ] = False,
) -> None:
    """Revisa una carpeta de PDF: convierte solo los que falten y actualiza manuales.json.

    Lo ya convertido no se toca: solo se añaden los PDF nuevos al JSON y a la
    galería (index.html).
    """
    origen = Path(carpeta).expanduser()
    destino_final = Path(destino).expanduser() if destino else _destino_transformar()
    if destino_final is None:
        _error(
            "No hay ninguna acción «transformar» con destino en el fichero de acciones: "
            "indica uno con --destino RUTA.",
            codigo=3,
        )

    try:
        mensajes = mod_html.indexar(origen, destino_final, simular=simular)
    except TareasError as exc:
        _error(str(exc), codigo=exc.codigo_salida)

    for mensaje in mensajes:
        typer.echo(mensaje)


def _mostrar_simulacion(nombre: str, resultados: list[Resultado]) -> None:
    """Tabla «fichero → destino» con estado para --simular; no toca nada.

    Los resultados sin rutas (el tipo «abrir» y el aviso de filtro vacío)
    no van en la tabla: se muestran como texto, como hasta ahora.
    """
    tabla = Table(title=f"Simulación de «{escape(nombre)}»: no se toca nada")
    tabla.add_column("Fichero", style="cyan")
    tabla.add_column("Destino")
    tabla.add_column("Estado")
    tabla.add_column("Detalle")
    filas: list[tuple[str, str, str, str]] = []
    for resultado in resultados:
        if resultado.origen is None and resultado.destino is None:
            # El aviso de «no hay ficheros que cumplan el filtro» lo muestra
            # el resumen; aquí solo salen los demás mensajes sin ficheros.
            if "No hay ficheros que cumplan el filtro" not in resultado.mensaje:
                typer.echo(resultado.mensaje)
            continue
        filas.append(
            (
                resultado.origen.name if resultado.origen else "—",
                resultado.destino.name if resultado.destino else "—",
                f"[yellow]{escape(resultado.estado)}[/yellow]",
                escape(resultado.mensaje),
            )
        )
    if filas:
        for fichero, destino_celda, estado_celda, detalle_celda in filas:
            tabla.add_row(escape(fichero), escape(destino_celda), estado_celda, detalle_celda)
        # Si todas las filas van a la misma carpeta, se indica una sola vez.
        destinos_padre = {
            resultado.destino.parent
            for resultado in resultados
            if resultado.destino is not None
        }
        if len(destinos_padre) == 1:
            carpeta = destinos_padre.pop()
            tabla.caption = f"Todo dentro de: {escape(str(carpeta))}"
        consola.print(tabla)


def _mostrar_resumen(resultados: list[Resultado]) -> None:
    """Resumen final: N hechos, N simulados y N saltados.

    Si el motor devolvió el aviso de «no hay ficheros que cumplan el filtro»
    (un «saltado» sin origen), se destaca antes del recuento.
    """
    if not resultados:
        typer.echo("Aviso: la acción no produjo ningún resultado.", err=True)
        return

    vacio = next(
        (
            resultado
            for resultado in resultados
            if resultado.estado == "saltado"
            and resultado.origen is None
            and "No hay ficheros que cumplan el filtro" in resultado.mensaje
        ),
        None,
    )
    if vacio is not None:
        consola_err.print(f"[yellow]Aviso:[/yellow] {escape(vacio.mensaje)}")

    hechos = sum(1 for r in resultados if r.estado == "hecho")
    simulados = sum(1 for r in resultados if r.estado == "simulado")
    saltados = sum(1 for r in resultados if r.estado == "saltado")
    partes: list[str] = []
    if hechos:
        partes.append(f"[green]{hechos} hecho(s)[/green]")
    if simulados:
        partes.append(f"[yellow]{simulados} simulado(s)[/yellow]")
    if saltados:
        partes.append(escape(f"{saltados} saltado(s)"))
    recuento = ", ".join(partes) if partes else "nada que hacer"
    consola.print(f"Resumen: {recuento}.")


class NombresAccion:
    """Autocompletado de nombres de acción leyendo acciones.json.

    Con esto, `cliwork ejecutar <TAB>` propone las acciones del fichero
    (ordenar-descargas, abrir-nav...) evitando errores de tecleo. Si el
    JSON no se puede leer, devuelve la lista vacía y ya validará bien.
    """

    def shell_complete(self, ctx: Any, incomplete: str) -> list[Any]:
        try:
            lista = config.cargar(_ruta_config(ctx))
        except TareasError:
            return []
        return [
            CompletionItem(str(accion["nombre"]))
            for accion in lista
            if isinstance(accion.get("nombre"), str)
            and accion["nombre"].startswith(incomplete)
        ]


@app.command(
    epilog=(
        "Opción global --config: el fichero de acciones se pasa justo después de "
        "«cliWork», con su valor, y antes de la orden "
        "(ej.: cliWork --config ~/mi-acciones.json ejecutar ordenar-descargas --simular)."
    )
)
def ejecutar(
    ctx: typer.Context,
    nombre: Annotated[
        str,
        typer.Argument(
            help="Nombre de la acción a ejecutar (ej.: abrir-nav).",
            autocompletion=NombresAccion,
        ),
    ],
    entrada: Annotated[
        str | None,
        typer.Argument(
            help=(
                "URL si la acción es de tipo «abrir» (ej.: https://epson.com); "
                "carpeta de origen para el resto (ej.: ~/pruebas-tareas)."
            ),
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
    carpeta: Annotated[
        str | None,
        typer.Option(
            "--carpeta",
            "-c",
            "-r",
            help="Carpeta de origen; tiene prioridad sobre la del fichero de acciones. Admite ~.",
        ),
    ] = None,
    si: Annotated[
        bool,
        typer.Option(
            "--si",
            help="No pregunta: acepta la confirmación (para borrar y las que tengan 'confirmar').",
        ),
    ] = False,
    antiguedad: Annotated[
        int | None,
        typer.Option(
            "--antiguedad",
            "-an",
            "-n",
            help=(
                "Días de antigüedad mínima: solo lo más viejo que N días; "
                "tiene prioridad sobre el del fichero (400 por defecto)."
            ),
        ),
    ] = None,
    destino: Annotated[
        str | None,
        typer.Option(
            "--destino",
            "-d",
            help="Carpeta de destino; tiene prioridad sobre la del fichero de acciones. Admite ~.",
        ),
    ] = None,
    nombre_zip: Annotated[
        str | None,
        typer.Option(
            "--nombre",
            "-N",
            help=(
                "«comprimir»: nombre del .zip (por defecto, el de la carpeta origen). "
                "«renombrar»: nombre genérico para el hueco {base} (por defecto, Captura)."
            ),
        ),
    ] = None,
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
    destino_navegador = NAVEGADORES[navegador] if navegador else "el explorador por defecto"
    ruta_navegador = buscar_navegador(navegador) if navegador else None

    try:
        lista = config.cargar(_ruta_config(ctx))
    except TareasError as exc:
        _error(str(exc), codigo=exc.codigo_salida)

    errores, _ = validar_acciones(lista)
    if errores:
        _error(
            f"El fichero de acciones tiene {len(errores)} error(es). "
            f"Ejecuta «cliWork validar» para verlos.",
            codigo=3,
        )

    motor = Motor(lista)
    accion = motor.acciones.get(nombre)

    if accion is None:
        _error(_mensaje_no_existe(nombre, lista), codigo=1)

    tipo = accion.config.get("tipo")

    # La segunda posición es URL si la acción abre URLs; si no, es la carpeta.
    es_url = bool(entrada) and entrada.lower().startswith(("http://", "https://"))
    url: str | None = None
    if tipo == "abrir":
        if entrada is not None and not es_url:
            _error(
                f"La acción «{nombre}» es de tipo «abrir»: la URL debe empezar "
                f"por http:// o https://: {entrada}",
                codigo=1,
            )
        url = entrada if es_url else None
    elif entrada is not None:
        if es_url:
            _error(
                f"La acción «{nombre}» es de tipo «{tipo}» y no abre URLs: "
                f"pon ahí la carpeta o usa --carpeta RUTA (admite ~).",
                codigo=1,
            )
        if carpeta is not None:
            _error(
                "La carpeta se indica una sola vez: en la posición 2 o con --carpeta, no en las dos.",
                codigo=1,
            )
        carpeta = entrada
        url = None

    if simular:
        try:
            resultados = motor.ejecutar(
                nombre,
                Path(carpeta).expanduser() if carpeta else None,
                True,
                urls=([url] if url is not None else None),
                navegador=navegador,
                ruta_navegador=str(ruta_navegador) if ruta_navegador else None,
                antiguedad=antiguedad,
                destino=Path(destino).expanduser() if destino else None,
                nombre_zip=nombre_zip,
            )
        except TareasError as exc:
            _error(str(exc), codigo=exc.codigo_salida)
        _mostrar_simulacion(nombre, resultados)
        _mostrar_resumen(resultados)
        return

    # --simular ya ha salido arriba; aquí solo falta no preguntar si se pidió --si.
    if not si:
        if tipo == "abrir":
            urls_efectivas = (
                [url] if url is not None else list(accion.config.get("urls") or [])
            )
            pestañas = "1 pestaña" if len(urls_efectivas) == 1 else f"{len(urls_efectivas)} pestañas"
            if accion.config.get("confirmar", False):
                typer.confirm(f"¿Abrir {destino_navegador} con {pestañas}?", abort=True)
        else:
            # Borrar siempre pide confirmación; el resto, solo si «confirmar» es true.
            if tipo == "borrar" or accion.config.get("confirmar", False):
                typer.confirm(f"¿Ejecutar «{nombre}» ({tipo})?", abort=True)

    try:
        resultados = motor.ejecutar(
            nombre,
            Path(carpeta).expanduser() if carpeta else None,
            False,
            urls=([url] if url is not None else None),
            navegador=navegador,
            ruta_navegador=str(ruta_navegador) if ruta_navegador else None,
            abrir=(
                (lambda urls_a: abrir_en_navegador(navegador, urls_a, ruta_navegador))
                if navegador
                else (lambda urls_a: abrir_por_defecto(urls_a))
            ),
            antiguedad=antiguedad,
            destino=Path(destino).expanduser() if destino else None,
            nombre_zip=nombre_zip,
        )
    except TareasError as exc:
        _error(str(exc), codigo=exc.codigo_salida)

    for resultado in resultados:
        typer.echo(resultado.mensaje)
        if not resultado.exito:
            _error(resultado.mensaje, codigo=1)
    _mostrar_resumen(resultados)

    # «limpiar-usb» termina SIEMPRE avisando del reinicio obligatorio; se
    # pregunta (y con --si se reinicia solo) salvo en --simular, que ya salió.
    if tipo == "limpiar-usb":
        if si:
            _reiniciar_equipo()
            return
        if typer.confirm(
            "El registro quedó limpio: hace falta REINICIAR (es obligatorio). "
            "¿Reiniciar ahora?",
            default=True,
        ):
            _reiniciar_equipo()
        else:
            consola_err.print(
                "[yellow]Aviso:[/yellow] el reinicio queda PENDIENTE y es "
                "obligatorio: hasta que reinicies, los USB pueden aparecer "
                "en el registro otra vez. Ejecuta el reinicio a mano cuando "
                "hayas guardado todo."
            )
