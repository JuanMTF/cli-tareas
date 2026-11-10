"""Prueba que el completador NombresAccion devuelve las acciones."""
from click.testing import CliRunner

from tareas.cli import app, NombresAccion


def test_completa_nombres():
    c = NombresAccion()
    items = c.shell_complete(None, "")  # sin prefijo: todas
    nombres = [i.value for i in items]
    assert "abrir-nav" in nombres
    assert "ordenar-descargas" in nombres


def test_completa_con_prefijo():
    c = NombresAccion()
    items = c.shell_complete(None, "abrir")
    nombres = [i.value for i in items]
    assert nombres == ["abrir-nav"]


def test_json_roto_devuelve_vacio(tmp_path):
    """Si el JSON esta roto, el TAB no explota: devuelve lista vacia."""
    c = NombresAccion()
    from tareas import config
    original = config.RUTA_ACCIONES
    config.RUTA_ACCIONES = tmp_path / "no-existe.json"
    try:
        assert c.shell_complete(None, "") == []
    finally:
        config.RUTA_ACCIONES = original
