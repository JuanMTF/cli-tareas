"""La ayuda y los errores de la CLI tienen que salir en español.

Typer escribe en inglés sus rótulos y sus mensajes; traduccion.py se los
cambia antes de que se imprima nada.
"""

from __future__ import annotations

from typer.testing import CliRunner

from tareas.cli import app
from tareas.traduccion import traducir, traducir_mensajes

runner = CliRunner()


def _texto(resultado) -> str:
    """Todo lo que imprimió la orden (stdout y stderr), con espacios seguidos juntos.

    Los errores van a stderr y dependiendo de la versión de click pueden no
    estar en .stdout, así que se concatenan todas las vías.
    """
    partes = []
    for attr in ("output", "stdout", "stderr"):
        valor = getattr(resultado, attr, None)
        if isinstance(valor, str):
            partes.append(valor)
    return " ".join(" ".join(partes).split())


# --- diccionario y reglas ---------------------------------------------------


def test_traducir_conoce_los_rotulos_de_typer() -> None:
    assert traducir("Options") == "Opciones"
    assert traducir("Arguments") == "Argumentos"
    assert traducir("Show this message and exit.") == "Muestra este mensaje y sale."


def test_traducir_no_toca_lo_que_no_conoce() -> None:
    assert traducir("Ayuda de tareas") == "Ayuda de tareas"
    assert traducir_mensajes("No hay ficheros que cumplan el filtro.") == (
        "No hay ficheros que cumplan el filtro."
    )


def test_traducir_mensajes_conserva_el_dato_que_van_dentro() -> None:
    mensaje = traducir_mensajes("Got unexpected extra argument(s) (sobra)")
    assert mensaje == "Argumentos inesperados: sobra"


# --- ayuda ------------------------------------------------------------------


def test_ayuda_principal_en_espanol() -> None:
    resultado = runner.invoke(app, ["--help"])
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "Uso: " in texto
    assert "[OPTIONS] COMMAND [ARGS]" in texto
    assert "Opciones" in texto
    assert "Comandos" in texto
    assert "Muestra este mensaje y sale." in texto
    assert "Instala el autocompletado en el shell actual." in texto
    assert "Usage:" not in texto
    assert "Show this message" not in texto


def test_ayuda_de_ejecutar_en_espanol() -> None:
    resultado = runner.invoke(app, ["ejecutar", "--help"])
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "Uso: " in texto
    assert "ejecutar [OPTIONS]" in texto
    assert "Argumentos" in texto
    assert "[obligatorio]" in texto
    assert "Options" not in texto


def test_ayuda_de_listar_en_espanol() -> None:
    resultado = runner.invoke(app, ["listar", "--help"])
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "Opciones" in texto
    assert "Muestra este mensaje y sale." in texto


# --- errores de uso ---------------------------------------------------------


def test_argumento_inesperado_en_espanol() -> None:
    resultado = runner.invoke(app, ["version", "sobra"])
    assert resultado.exit_code == 2
    texto = _texto(resultado)
    assert "Argumentos inesperados: sobra" in texto
    assert "Got unexpected" not in texto


def test_comando_inexistente_en_espanol() -> None:
    resultado = runner.invoke(app, ["noexiste"])
    assert resultado.exit_code == 2
    texto = _texto(resultado)
    assert "No existe la orden 'noexiste'." in texto
    assert "No such command" not in texto


def test_opcion_inexistente_en_espanol() -> None:
    resultado = runner.invoke(app, ["-t"])
    assert resultado.exit_code == 2
    texto = _texto(resultado)
    assert "No existe la opción: -t" in texto
    assert "No such option" not in texto
