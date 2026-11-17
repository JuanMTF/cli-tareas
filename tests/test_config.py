"""Tests de la carga y validación del fichero de acciones (sesión 4).

Ocho pruebas, una por regla del esquema: version, JSON legible, acciones
en lista, tipos conocidos y el rango de max_caracteres de las acciones IA.
Prueban cargar_acciones a nivel UNIDAD (sin pasar por la CLI, que tiene
sus propios tests en test_cli.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tareas.acciones import cargar_acciones, validar_acciones
from tareas.config import MAX_CARACTERES_MAX, MAX_CARACTERES_MIN, validar_ia
from tareas.errores import AccionNoValida, ConfigError


# --- carga correcta ---------------------------------------------------------


def test_carga_un_json_correcto(accion_abrir: dict, escribir_config) -> None:
    ruta = escribir_config({"version": 1, "acciones": [accion_abrir]})
    assert cargar_acciones(ruta) == [accion_abrir]


# --- errores de config (ConfigError, código de salida 3) --------------------


def test_json_roto_da_error_configuracion(tmp_path: Path) -> None:
    ruta = tmp_path / "roto.json"
    ruta.write_text('{"version": 1, "acciones": [', encoding="utf-8")
    with pytest.raises(ConfigError):
        cargar_acciones(ruta)


def test_fichero_inexistente_da_error_configuracion(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        cargar_acciones(tmp_path / "no-existe.json")


def test_version_distinta_da_error_configuracion(accion_abrir: dict, escribir_config) -> None:
    ruta = escribir_config({"version": 2, "acciones": [accion_abrir]})
    with pytest.raises(ConfigError):
        cargar_acciones(ruta)


def test_acciones_no_lista_da_error_configuracion(escribir_config) -> None:
    ruta = escribir_config({"version": 1, "acciones": "una-sola"})
    with pytest.raises(ConfigError):
        cargar_acciones(ruta)


# --- reglas del esquema (validar_acciones / validar_ia) ---------------------
#
# cargar_acciones valida el FICHERO (version, JSON legible, acciones en
# lista); las reglas de cada acción (tipos, campos, rangos) las comprueba
# validar_acciones, que es lo que usa la orden «validar».


def test_tipo_desconocido_da_error_de_validacion(accion_abrir: dict) -> None:
    """Un tipo que no está en TIPOS_CONOCIDOS no se puede ejecutar: rechaza."""
    mala = {**accion_abrir, "tipo": "inventar-doctores"}
    errores, _avisos = validar_acciones([mala])
    assert errores and "abrir-nav" in errores[0]


def test_campo_obligatorio_faltante_da_error_de_validacion(accion_abrir: dict) -> None:
    """«abrir» exige urls: sin ella, la validación lo señala por su campo."""
    mala = {clave: valor for clave, valor in accion_abrir.items() if clave != "urls"}
    errores, _avisos = validar_acciones([mala])
    assert errores and "abrir-nav" in errores[0]


@pytest.mark.parametrize(
    "maximo",
    [MAX_CARACTERES_MIN - 100, MAX_CARACTERES_MAX + 1000],
)
def test_max_caracteres_fuera_de_rango_da_error_de_validacion(maximo: int) -> None:
    """Las acciones IA acotan el texto al modelo: fuera de 500..50000, rechaza."""
    accion = {
        "nombre": "resumen-malo",
        "descripcion": "prueba de validacion IA",
        "tipo": "resumir",
        "filtro": {"extensiones": [".txt"]},
        "instrucciones": "resume",
        "max_caracteres": maximo,
    }
    with pytest.raises(AccionNoValida) as error:
        validar_ia(accion)
    assert "max_caracteres" in str(error.value)


# --- encoding ---------------------------------------------------------------


def test_acepta_tildes_y_utf8(accion_abrir: dict, escribir_config) -> None:
    """Las descripciones van en español: el JSON se lee como UTF-8 con tildes."""
    con_tildes = {**accion_abrir, "descripcion": "Mueve los .pdf a Documentos/áéíóú"}
    ruta = escribir_config({"version": 1, "acciones": [con_tildes]})
    cargadas = cargar_acciones(ruta)
    assert cargadas[0]["descripcion"].endswith("áéíóú")
