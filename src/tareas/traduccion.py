"""Ayuda y mensajes de Typer/Click en español.

Typer escribe en inglés varias cadenas fijas de la CLI: la línea «Usage:»,
los rótulos «Options/Arguments/Commands», el texto de --help, el de las
opciones de autocompletado (--install-completion y --show-completion) y los
errores de uso («Got unexpected extra argument(s)» y parecidos).

Aquí NO se modifica ningún fichero de la librería: se parchean unos cuantos
puntos concretos de Typer desde fuera (gettext, el prefijo «Usage:», la ayuda
de --help y de autocompletado, y los errores de uso). Solo cambia el texto
que se ve en pantalla: los códigos de salida y el comportamiento son los
mismos.

Forma de uso (lo hace cli.py): importar este módulo y llamar a instalar()
ANTES de `import typer`, para que los rótulos fijos se calculen ya en
español. Si typer ya venía importado de antes, instalar() también lo arregla.
"""

from __future__ import annotations

import gettext as mod_gettext
import inspect
import os
import re
import sys
from typing import Any, Callable

# Guardamos las funciones originales de gettext para poder reconocerlas
# (y cambiarlas) en los módulos que ya se hayan importado.
_gettext_original = mod_gettext.gettext
_ngettext_original = mod_gettext.ngettext

# Rótulos fijos que typer/rich_utils.py calcula al importarse.
_CONSTANTES_RICH = (
    "DEPRECATED_STRING",
    "DEFAULT_STRING",
    "ENVVAR_STRING",
    "REQUIRED_LONG_STRING",
    "ARGUMENTS_PANEL_TITLE",
    "OPTIONS_PANEL_TITLE",
    "COMMANDS_PANEL_TITLE",
    "ERRORS_PANEL_TITLE",
    "ABORTED_TEXT",
    "RICH_HELP",
)

# Textos de Typer/Click, tal y como aparecen en el código de la librería.
CADENAS: dict[str, str] = {
    # Rótulos que Typer deja en gettext (typer/core.py y typer/rich_utils.py).
    "(dynamic)": "(dinámico)",
    "(deprecated) ": "(obsoleto) ",
    "Aborted!": "¡Cancelado!",
    "Aborted.": "Cancelado.",
    "Arguments": "Argumentos",
    "Commands": "Comandos",
    "Missing command.": "Falta la orden.",
    "No such command {name!r}.": "No existe la orden {name!r}.",
    "Options": "Opciones",
    "default: {default}": "por defecto: {default}",
    "env var: {var}": "var. entorno: {var}",
    "required": "obligatorio",
    "[default: {}]": "[por defecto: {}]",
    "[env var: {}]": "[var. entorno: {}]",
    "[required]": "[obligatorio]",
    "Try [blue]'{command_path} {help_option}'[/] for help.": (
        "Prueba [blue]'{command_path} {help_option}'[/] para ver la ayuda."
    ),
    # Literales que no pasan por gettext: la ayuda de --help y de autocompletado.
    "Show this message and exit.": "Muestra este mensaje y sale.",
    "Install completion for the current shell.": (
        "Instala el autocompletado en el shell actual."
    ),
    "Show completion for the current shell, to copy it or customize the installation.": (
        "Muestra el autocompletado del shell actual para copiarlo o personalizarlo."
    ),
    "Install completion for the specified shell.": (
        "Instala el autocompletado en el shell indicado."
    ),
    "Show completion for the specified shell, to copy it or customize the installation.": (
        "Muestra el autocompletado del shell indicado para copiarlo o personalizarlo."
    ),
}

# Mensajes que llevan valores dentro (errores y avisos): se traducen con
# expresiones regulares para no perder el dato que van en medio.
REGLAS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^Got unexpected extra argument\(s\) \((?P<args>.+)\)$"),
        r"Argumentos inesperados: \g<args>",
    ),
    (
        re.compile(r"^No such option: (?P<opcion>.+)$"),
        r"No existe la opción: \g<opcion>",
    ),
    (re.compile(r"^Invalid value for "), "Valor no válido para "),
    (re.compile(r"^Invalid value: "), "Valor no válido: "),
    (re.compile(r"^Missing argument"), "Falta el argumento"),
    (re.compile(r"^Missing option"), "Falta la opción"),
    (re.compile(r"^Missing parameter"), "Falta el parámetro"),
    (
        re.compile(r"^Try '(?P<comando>[^']+)' for help\."),
        r"Prueba '\g<comando>' para ver la ayuda.",
    ),
    # Avisos de las opciones de autocompletado.
    (
        re.compile(r"^(?P<shell>\w+) completion installed in (?P<ruta>.+)$"),
        r"Autocompletado de \g<shell> instalado en \g<ruta>",
    ),
    (
        re.compile(r"^Completion will take effect once you restart the terminal$"),
        "El autocompletado funcionará cuando reinicies la terminal.",
    ),
    # Errores de las opciones de autocompletado (p. ej. shell no admitido).
    (
        re.compile(r"^Shell (?P<shell>\S+) not supported\.$"),
        r"No se admite el shell \g<shell>.",
    ),
    (
        re.compile(r"^Shell (?P<shell>\S+) is not supported\.$"),
        r"No se admite el shell \g<shell>.",
    ),
    (
        re.compile(r'^Completion instruction "(?P<instruccion>[^"]+)" not supported\.$'),
        r'No se admite la instrucción de autocompletado "\g<instruccion>".',
    ),
)

_instalado = False


def traducir(texto: str) -> str:
    """Traduce un texto fijo si está en CADENAS; si no, devuelve el original."""
    return CADENAS.get(texto, texto)


def traducir_mensajes(texto: str) -> str:
    """Traduce un mensaje completo: primero el diccionario y luego las reglas."""
    resultado = traducir(texto)
    for patron, cambio in REGLAS:
        resultado = patron.sub(cambio, resultado)
    return resultado


def en_modo_completado() -> bool:
    """Detecta si Typer está respondiendo a un autocompletado (shell completion).

    Typer guarda el «instrucción» de completion en variables de entorno con
    nombre distinto según el shell; todas empiezan por «_TYPER_COMPLETE» o son
    la de prog propio («_TAREAS_COMPLETE» para «tareas»).
    """
    for nombre, valor in os.environ.items():
        if valor and (nombre.startswith("_TYPER_COMPLETE") or nombre == "_TAREAS_COMPLETE"):
            return True
    return False


def _gettext(texto: str) -> str:
    """Sustituye a gettext.gettext: traduce si conoce el texto, si no lo deja."""
    return traducir(texto)


def _ngettext(singular: str, plural: str, n: int) -> str:
    """Sustituye a gettext.ngettext (singular/plural), con el mismo criterio."""
    elegido = singular if n == 1 else plural
    return traducir(elegido)


def instalar() -> None:
    """Traduce la ayuda y los errores de Typer. Se puede llamar varias veces.

    Hay que llamarla ANTES de `import typer` para que los rótulos fijos se
    calculen ya en español; si typer ya estaba importado, aquí se corrigen.
    """
    global _instalado
    if _instalado:
        return
    _instalado = True

    # 1) gettext: typer/core.py y typer/rich_utils.py hacen
    #    «from gettext import gettext as _», así que hay que cambiarlo
    #    antes de que se importen.
    mod_gettext.gettext = _gettext  # type: ignore[assignment]
    mod_gettext.ngettext = _ngettext  # type: ignore[assignment]

    # 2) Typer (y con él, sus rótulos, que ya saldrán en español).
    import typer  # noqa: F401  (se importa aquí a propósito)
    from typer import _click, completion, rich_utils
    from typer._click import decorators, exceptions, formatting, termui

    # Si typer venía importado de antes, sus «_» siguen apuntando al gettext
    # original: aquí se les cambia para las traducciones a futuro.
    for modulo in list(sys.modules.values()):
        if modulo is None:
            continue
        if getattr(modulo, "_", None) is _gettext_original:
            modulo._ = _gettext  # type: ignore[attr-defined]
        if getattr(modulo, "ngettext", None) is _ngettext_original:
            modulo.ngettext = _ngettext  # type: ignore[attr-defined]

    # ...y los rótulos que ya estaban calculados en inglés.
    for constante in _CONSTANTES_RICH:
        valor = getattr(rich_utils, constante, None)
        if isinstance(valor, str):
            setattr(rich_utils, constante, traducir(valor))

    # 3) «Usage: » -> «Uso: » (Typer lo escribe sin pasar por gettext).
    escritor_original = formatting.HelpFormatter.write_usage

    def write_usage(self, prog: str, args: str = "", prefix: str | None = None) -> None:
        if prefix is None:
            prefix = "Uso: "
        return escritor_original(self, prog, args, prefix)

    formatting.HelpFormatter.write_usage = write_usage  # type: ignore[method-assign]

    # El resaltador de Rich también busca «Usage: » para darle color.
    rich_utils.OptionHighlighter.highlights = [
        patron.replace("(?P<usage>Usage: )", "(?P<usage>(Usage:|Uso: ))")
        for patron in rich_utils.OptionHighlighter.highlights
    ]

    # 4) Texto de la opción --help: «Show this message and exit.»
    ayuda_original = decorators.help_option

    def help_option(param_decls: list[str]) -> Callable[[Any], Any]:
        """Igual que el de Typer, pero cambia el texto de la opción --help."""
        decorador = ayuda_original(param_decls)

        def aplicar(comando: Any) -> Any:
            comando = decorador(comando)
            # Typer hace pop() del último parámetro añadido: el de ayuda.
            ultimo = comando.params[-1]
            if getattr(ultimo, "help", None):
                ultimo.help = traducir(ultimo.help)
            return comando

        return aplicar

    decorators.help_option = help_option  # type: ignore[assignment]

    # 5) Textos de las opciones de autocompletado (--install-completion,
    #    --show-completion). Son valores por defecto de dos funciones
    #    auxiliares: se cambian en el propio objeto Option.
    for nombre in (
        "_install_completion_placeholder_function",
        "_install_completion_no_auto_placeholder_function",
    ):
        funcion = getattr(completion, nombre, None)
        if funcion is None:
            continue
        for parametro in inspect.signature(funcion).parameters.values():
            ayuda = getattr(parametro.default, "help", None)
            if ayuda:
                parametro.default.help = traducir(ayuda)

    # 6) Errores de uso («Got unexpected extra argument(s) (...)», «No such
    #    option»...): se traducen en el momento de imprimirlos, para no
    #    perder los valores que llevan dentro. El format_message base vive
    #    en typer.exceptions.TyperException (padre de ClickException), y hay
    #    subclases que lo vuelven a definir (BadParameter, MissingParameter).
    pendientes: list[type] = [exceptions.ClickException]
    candidatas: list[type] = list(exceptions.ClickException.__mro__)
    while pendientes:
        clase = pendientes.pop()
        pendientes.extend(clase.__subclasses__())
        if clase not in candidatas:
            candidatas.append(clase)

    for clase in candidatas:
        original = vars(clase).get("format_message")
        if original is None:
            continue

        def envuelto(self: Any, _original: Callable[[Any], str] = original) -> str:
            """Mensaje ya traducido, conservando el texto original de Typer."""
            return traducir_mensajes(_original(self))

        clase.format_message = envuelto  # type: ignore[method-assign]

    # 7) Avisos de instalación del autocompletado (se imprimen con secho/echo
    #    desde typer/completion.py). Todo lo demás pasa sin cambiar.
    secho_original = termui.secho

    def secho(message: Any = None, *args: Any, **kwargs: Any) -> Any:
        """Igual que el de Typer, traduciendo los avisos de autocompletado."""
        if isinstance(message, str):
            message = traducir_mensajes(message)
        return secho_original(message, *args, **kwargs)

    termui.secho = secho  # type: ignore[assignment]

    echo_original = _click.echo

    def echo(message: Any = None, *args: Any, **kwargs: Any) -> Any:
        """Igual que el de Typer, traduciendo los avisos de autocompletado.

        En modo autocompletado, si no hay resultados que proponer, Typer
        escribía una línea vacía con «_click.echo(… comp.complete())». En
        PowerShell esa línea vacía provoca que el scriptblock del autocompletado
        falle antes de borrar las variables de completion: quedan puestas y los
        siguientes «tareas» se ejecutaban como si fueran peticiones de
        autocompletado (por eso "no respondían"). Aquí no se escribe nada.
        """
        if isinstance(message, str) and message == "" and en_modo_completado():
            return
        if isinstance(message, str):
            message = traducir_mensajes(message)
        return echo_original(message, *args, **kwargs)

    _click.echo = echo  # type: ignore[assignment]
