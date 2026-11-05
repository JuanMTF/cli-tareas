"""Tests de las órdenes de la CLI (acciones, validar, ejecutar)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from tareas import acciones as mod_acciones
from tareas.cli import app

runner = CliRunner()
RUTA_REAL = Path("src/tareas/docs/acciones.json")


def _texto(resultado) -> str:
    """Todo lo que imprimió la orden: stdout y stderr, venga por donde venga.

    Los mensajes de error van a stderr y dependiendo de la versión de click
    pueden no estar en .stdout, así que se concatenan todas las vías.
    """
    partes = []
    for attr in ("output", "stdout", "stderr"):
        valor = getattr(resultado, attr, None)
        if isinstance(valor, str):
            partes.append(valor)
    return "".join(partes)


def _urls_abrir_nav() -> list[str]:
    """Las URLs reales de la acción abrir-nav en el JSON del proyecto."""
    datos = json.loads(RUTA_REAL.read_text(encoding="utf-8"))
    accion = next(
        item for item in datos["acciones"] if item.get("nombre") == "abrir-nav"
    )
    return list(accion["urls"])


# --- validar ---------------------------------------------------------------


def test_validar_el_fichero_real_da_0() -> None:
    resultado = runner.invoke(app, ["validar"])
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "acciones válidas" in texto


def test_validar_json_roto_da_3(tmp_path: Path) -> None:
    roto = tmp_path / "roto.json"
    roto.write_text("{esto no es json", encoding="utf-8")
    resultado = runner.invoke(app, ["validar", str(roto)])
    assert resultado.exit_code == 3
    assert "JSON inválido" in _texto(resultado)


def test_validar_fichero_inexistente_da_3(tmp_path: Path) -> None:
    resultado = runner.invoke(app, ["validar", str(tmp_path / "no.json")])
    assert resultado.exit_code == 3


def test_validar_tipo_mal_escrito_da_3(tmp_path: Path) -> None:
    datos = json.loads(RUTA_REAL.read_text(encoding="utf-8"))
    datos["acciones"][3]["tipo"] = "abirr"  # errata a propósito
    malo = tmp_path / "mal.json"
    malo.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    resultado = runner.invoke(app, ["validar", str(malo)])
    assert resultado.exit_code == 3
    assert "abirr" in _texto(resultado)


# --- acciones --------------------------------------------------------------


def test_acciones_lista_todas() -> None:
    resultado = runner.invoke(app, ["acciones"])
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "abrir-nav" in texto
    assert "limpiar-temporales" in texto
    assert "comprimir-antiguos" in texto


def test_acciones_con_nombre_da_el_detalle() -> None:
    resultado = runner.invoke(app, ["acciones", "abrir-nav"])
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "abrir-nav" in texto
    assert "https://mi-es.solutions30.com" in texto


def test_acciones_nombre_inexistente_da_1() -> None:
    resultado = runner.invoke(app, ["acciones", "no-existe"])
    assert resultado.exit_code == 1
    assert "No existe la acción" in _texto(resultado)


# --- ejecutar --------------------------------------------------------------


def test_ejecutar_nombre_inexistente_da_1() -> None:
    resultado = runner.invoke(app, ["ejecutar", "esta-no-existe"])
    assert resultado.exit_code == 1
    assert "No existe la acción" in _texto(resultado)


def test_ejecutar_nombre_parecido_lo_sugiere() -> None:
    resultado = runner.invoke(app, ["ejecutar", "limpiar-descargas"])
    assert resultado.exit_code == 1
    texto = _texto(resultado)
    assert "¿Quisiste decir" in texto
    # alguna de las dos acciones reales que se le parecen
    assert "limpiar-temporales" in texto or "borrar-descargas" in texto


def test_acciones_nombre_parecido_lo_sugiere() -> None:
    resultado = runner.invoke(app, ["acciones", "abrir-navv"])
    assert resultado.exit_code == 1
    assert "¿Quisiste decir" in _texto(resultado)


def test_ejecutar_tipo_no_implementado_da_1() -> None:
    resultado = runner.invoke(app, ["ejecutar", "ordenar-descargas"])
    assert resultado.exit_code == 1
    assert "no está implementado" in _texto(resultado)


def test_ejecutar_comprimir_todavia_no_implementado_da_1() -> None:
    resultado = runner.invoke(app, ["ejecutar", "comprimir-antiguos"])
    assert resultado.exit_code == 1
    assert "no está implementado" in _texto(resultado)


def test_ejecutar_simular_no_abre_nada(monkeypatch) -> None:
    llamadas: list[list[str]] = []

    def _falso_abrir(urls: list[str]) -> None:
        llamadas.append(urls)

    # cli.py importó las funciones por nombre: se parchea también ahí
    monkeypatch.setattr("tareas.cli.abrir_por_defecto", _falso_abrir)

    resultado = runner.invoke(app, ["ejecutar", "abrir-nav", "--simular"])
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "SIMULACIÓN" in texto
    assert "https://mi-es.solutions30.com" in texto
    assert "explorador por defecto" in texto
    assert llamadas == []  # no se abrió nada


def test_ejecutar_simular_con_e_no_abre_nada(monkeypatch) -> None:
    monkeypatch.setattr(
        "tareas.cli.buscar_navegador", lambda clave: Path("C:/fake/msedge.exe")
    )
    resultado = runner.invoke(app, ["ejecutar", "abrir-nav", "-e", "--simular"])
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "Microsoft Edge" in texto
    assert "msedge.exe" in texto


def test_ejecutar_real_abre_el_explorador_por_defecto(monkeypatch) -> None:
    capturado: dict[str, list[str]] = {}

    def _falso_abrir(urls: list[str]) -> None:
        capturado["urls"] = urls

    monkeypatch.setattr("tareas.cli.abrir_por_defecto", _falso_abrir)

    resultado = runner.invoke(app, ["ejecutar", "abrir-nav"], input="y\n")
    assert resultado.exit_code == 0
    # las mismas URLs que hay en el fichero (hoy 6, mañana las que pongas)
    assert capturado["urls"] == _urls_abrir_nav()
    assert f"abierto con {len(_urls_abrir_nav())}" in _texto(resultado)


def test_ejecutar_real_con_e_abre_edge_con_las_urls_del_fichero(monkeypatch) -> None:
    capturado: dict[str, list[str]] = {}

    vistos: list[str] = []

    def _falso_abrir(url: str, new: int = 0) -> bool:
        vistos.append(url)
        return True

    monkeypatch.setattr(mod_acciones.webbrowser, "open", _falso_abrir)
    monkeypatch.setattr(
        "tareas.cli.buscar_navegador", lambda clave: Path("C:/fake/msedge.exe")
    )

    resultado = runner.invoke(app, ["ejecutar", "abrir-nav", "-e"], input="y\n")
    assert resultado.exit_code == 0

    assert vistos == _urls_abrir_nav()


def test_ejecutar_real_con_url_abre_solo_esa_url(monkeypatch) -> None:
    capturado: dict[str, list[str]] = {}

    vistos: list[str] = []

    def _falso_abrir(url: str, new: int = 0) -> bool:
        vistos.append(url)
        return True

    monkeypatch.setattr(mod_acciones.webbrowser, "open", _falso_abrir)
    monkeypatch.setattr(
        "tareas.cli.buscar_navegador", lambda clave: Path("C:/fake/firefox.exe")
    )

    resultado = runner.invoke(
        app, ["ejecutar", "abrir-nav", "-f", "https://epson.com"], input="y\n"
    )
    assert resultado.exit_code == 0

    assert vistos == ["https://epson.com"]


def test_ejecutar_real_cancelado_por_el_usuario_da_1() -> None:
    resultado = runner.invoke(app, ["ejecutar", "abrir-nav"], input="n\n")
    assert resultado.exit_code == 1


def test_ejecutar_dos_navegadores_da_1() -> None:
    resultado = runner.invoke(app, ["ejecutar", "abrir-nav", "-g", "-f"])
    assert resultado.exit_code == 1
    assert "un solo navegador" in _texto(resultado)


def test_ejecutar_url_sin_http_da_1() -> None:
    resultado = runner.invoke(app, ["ejecutar", "abrir-nav", "epson.com"])
    assert resultado.exit_code == 1
    assert "http" in _texto(resultado)


def test_ejecutar_navegador_no_instalado_da_1(monkeypatch) -> None:
    monkeypatch.setattr("tareas.cli.buscar_navegador", lambda clave: None)
    resultado = runner.invoke(app, ["ejecutar", "abrir-nav", "-e"], input="y\n")
    assert resultado.exit_code == 1
    assert "No se encontró Microsoft Edge" in _texto(resultado)
