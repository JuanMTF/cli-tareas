"""Tests de las clases de acciones a nivel UNIDAD (sesión 4).

Seis pruebas del comportamiento de las piezas de acciones.py: la fábrica
Accion.desde_config, que ningún movimiento pise un fichero (destino_libre),
la plantilla de renombrar y el mensaje del filtro vacío. La validación del
JSON vive en test_config.py y la integración con la CLI, en test_cli.py.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from tareas.acciones import (
    Abrir,
    Accion,
    Mover,
    aplicar_plantilla,
    describir_filtro,
    destino_libre,
)


def _config_mover() -> dict:
    return {
        "nombre": "mover-prueba",
        "descripcion": "mueve los .txt",
        "tipo": "mover",
        "origen": "origen",
        "filtro": {"extensiones": [".txt"]},
        "destino": "destino",
    }


# --- destino_libre: nunca se pisa un fichero --------------------------------


def test_destino_libre_no_pisa_y_propone_1(tmp_path: Path) -> None:
    ocupado = tmp_path / "a.txt"
    ocupado.write_text("x", encoding="utf-8")
    libre = destino_libre(tmp_path / "a.txt")
    assert libre == tmp_path / "a (1).txt"
    assert ocupado.read_text(encoding="utf-8") == "x"  # el original, intacto


def test_destino_libre_encadena_2_y_3(tmp_path: Path) -> None:
    for nombre in "a.txt", "a (1).txt", "a (2).txt":
        (tmp_path / nombre).write_text("x", encoding="utf-8")
    assert destino_libre(tmp_path / "a.txt") == tmp_path / "a (3).txt"


# --- plantillas del tipo renombrar ------------------------------------------


def test_plantilla_rellena_fecha_n_y_ext() -> None:
    relleno = aplicar_plantilla(
        "{fecha:%Y-%m-%d}_{n:03}{ext}",
        Path("fotos/foto.jpg"),
        7,
        datetime(2026, 3, 14, 10, 30),
    )
    assert relleno == "2026-03-14_007.jpg"


def test_plantilla_base_y_n_sin_ceros() -> None:
    """{base} es el nombre genérico de la CLI (--nombre) y {n} va sin ceros."""
    relleno = aplicar_plantilla(
        "{base}_{n}{ext}",
        Path("fotos/foto.jpg"),
        7,
        datetime(2026, 3, 14),
        base="Capturas",
    )
    assert relleno == "Capturas_7.jpg"


# --- la fábrica y el filtro -------------------------------------------------


def test_desde_config_fabrica_la_clase_de_cada_tipo() -> None:
    """Accion.desde_config decide la clase por el campo «tipo» del JSON."""
    mover = Accion.desde_config(_config_mover())
    assert isinstance(mover, Mover)
    abrir = Accion.desde_config(
        {"nombre": "nav", "descripcion": "d", "tipo": "abrir", "urls": ["https://x.dev"]}
    )
    assert isinstance(abrir, Abrir)


def test_describir_filtro_explica_el_criterio() -> None:
    """El aviso de «no hay ficheros» enseña el criterio que mandó, no el del JSON."""
    texto = describir_filtro({"extensiones": [".txt"], "mas_antiguo_que_dias": 30})
    assert ".txt" in texto
    assert "30" in texto
