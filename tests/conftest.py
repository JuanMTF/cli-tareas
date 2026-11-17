"""Fixtures compartidas por toda la suite (sesión 4).

Las usan test_config, test_acciones, test_ia, test_acciones_ia y test_cli:
un solo CliRunner, un JSON de acciones de ejemplo y los dobles del
proveedor de IA. NINGÚN test sale a la red: el proveedor es un doble que
contesta lo suyo o rompe si alguien lo llama, y el entorno (el .env y las
variables CENTRO_IA_*) se simula con monkeypatch.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tareas.ia import ProveedorIA, Respuesta


class _ProveedorFijo(ProveedorIA):
    """Proveedor de pruebas: contesta siempre el mismo texto."""

    def __init__(self, texto: str) -> None:
        self.texto = texto

    def completar(
        self, sistema: str, usuario: str, max_tokens: int = 800
    ) -> Respuesta:
        return Respuesta(self.texto, 1, 1, 0.0)


class _ProveedorRompe(ProveedorIA):
    """Proveedor de pruebas que FALLA si le llaman.

    Si un test llega a consultar al modelo es que algún camino se ha
    saltado un guard: rompe aquí, con el motivo claro.
    """

    def completar(
        self, sistema: str, usuario: str, max_tokens: int = 800
    ) -> Respuesta:
        raise AssertionError("El modelo no debía recibir ninguna llamada")


@pytest.fixture(scope="session")
def runner() -> CliRunner:
    """Un solo CliRunner para toda la suite (no guarda estado entre órdenes)."""
    return CliRunner()


@pytest.fixture
def texto() -> Callable[[Any], str]:
    """Todo lo que imprimió una orden: stdout y stderr, venga por donde venga.

    Los mensajes de error van a stderr y según la versión de click pueden
    no estar en .stdout, así que se concatenan todas las vías.
    """

    def _juntar(resultado: Any) -> str:
        partes = []
        for attr in ("output", "stdout", "stderr"):
            valor = getattr(resultado, attr, None)
            if isinstance(valor, str):
                partes.append(valor)
        return "".join(partes)

    return _juntar


@pytest.fixture
def accion_abrir() -> dict[str, Any]:
    """Una acción válida de tipo «abrir», para montar configs a medida."""
    return {
        "nombre": "abrir-nav",
        "descripcion": "Abre el explorador por defecto con 4 páginas.",
        "tipo": "abrir",
        "urls": ["https://ejemplo.com/"],
        "confirmar": True,
    }


@pytest.fixture
def escribir_config(tmp_path: Path) -> Callable[..., Path]:
    """Escribe un acciones.json con lo que le pases y devuelve su ruta.

    Con ensure_ascii=False y UTF-8: las tildes del JSON son parte de la
    prueba (el fichero real de acciones va en español).
    """

    def _escribir(datos: Any, nombre: str = "acciones.json") -> Path:
        ruta = tmp_path / nombre
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        return ruta

    return _escribir


@pytest.fixture
def proveedor_que_contesta() -> Callable[[str], ProveedorIA]:
    """Un proveedor IA que contesta SIEMPRE el texto que se le dé."""

    def _crear(texto: str) -> ProveedorIA:
        return _ProveedorFijo(texto)

    return _crear


@pytest.fixture
def proveedor_que_rompe() -> ProveedorIA:
    """Un proveedor IA que levanta AssertionError si se le llama."""
    return _ProveedorRompe()


@pytest.fixture
def env_sin_ia(monkeypatch: pytest.MonkeyPatch) -> None:
    """El entorno como si NO hubiera .env ni variables del centro."""
    for var in ("CENTRO_IA_URL", "CENTRO_IA_KEY", "CENTRO_IA_MODELO", "CENTRO_IA_CA"):
        monkeypatch.setenv(var, "")


@pytest.fixture
def env_con_ia(monkeypatch: pytest.MonkeyPatch) -> None:
    """El entorno con una config de IA de prueba.

    La clave es falsa A PROPÓSITO: los tests comprueban que nunca aparece
    en ningún mensaje, así que ha de ser reconocible si algún día sale.
    """
    monkeypatch.setenv("CENTRO_IA_URL", "http://prueba.local/v1")
    monkeypatch.setenv("CENTRO_IA_KEY", "SECRETA-AUDITORIA-NO-IMPRIMIR")
    monkeypatch.setenv("CENTRO_IA_MODELO", "modelo-de-prueba")
    monkeypatch.setenv("CENTRO_IA_CA", "")
