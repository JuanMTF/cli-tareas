"""Fixtures compartidas por toda la suite (sesión 4).

Las usan test_config, test_acciones, test_ia, test_acciones_ia y test_cli:
un solo CliRunner, un JSON de acciones de ejemplo y los dobles del
proveedor de IA. NINGÚN test sale a la red: el proveedor es un doble que
contesta lo suyo o rompe si alguien lo llama, y el entorno (el .env y las
variables CENTRO_IA_*) se simula con monkeypatch.
"""

from __future__ import annotations

import json
import os
import time
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
    """Escribe un acciones.json a medida y devuelve su ruta.

    Acepta lo mismo que el del profe: una LISTA de acciones (se envuelve
    en {"version": 1, "acciones": [...]}), un TEXTO tal cual (para los
    JSON rotos: lo que le pases sale tal cual en el fichero) o un dict
    completo (se serializa como venga). Con ensure_ascii=False y UTF-8:
    las tildes del JSON son parte de la prueba.
    """

    def _escribir(acciones: Any, nombre: str = "acciones.json") -> Path:
        ruta = tmp_path / nombre
        if isinstance(acciones, str):
            texto = acciones
        elif isinstance(acciones, list):
            texto = json.dumps(
                {"version": 1, "acciones": acciones}, ensure_ascii=False
            )
        else:
            texto = json.dumps(acciones, ensure_ascii=False)
        ruta.write_text(texto, encoding="utf-8")
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


@pytest.fixture(autouse=True)
def aislado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ningún test toca carpetas de verdad ni al servidor de IA.

    Para TODO test, sin que tenga que pedirlo:
    - el directorio actual es un tmp_path de pytest (el .env real del repo
      deja de ser visible: find_dotenv(usecwd=True) no lo encuentra);
    - HOME y USERPROFILE apuntan al tmp_path: cualquier expanduser() de
      «~» (motor, destinos del JSON) cae en el sandbox, no en el usuario;
    - las variables del centro IA se quitan: sin config no hay forma de
      construir el proveedor, y ProveedorCentro sale con IANoDisponible
      antes de intentar ninguna conexión.

    Se define ANTES de env_con_ia/env_sin_ia: los autouse se montan
    primero, así que esos fixtures pueden volver a poner variables.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    for var in ("CENTRO_IA_URL", "CENTRO_IA_KEY", "CENTRO_IA_CA"):
        monkeypatch.delenv(var, raising=False)


DIAS_VIEJO = 40
SEGUNDOS_POR_DIA = 86400


@pytest.fixture
def descargas(tmp_path: Path) -> Path:
    """Una carpeta «Descargas» del sandbox con los casos típicos.

    factura.pdf y «apuntes de redes.docx» son los documentos del filtro;
    FOTO1.JPG prueba que la comparación de extensiones no distingue
    mayúsculas; «cumpleaños 2.png», que un espacio en el nombre no rompe
    nada; y viejo.tmp, el .tmp más antiguo que el filtro de 30 días
    (se le fuerza el mtime con os.utime: los ficheros nuevos tienen
    mtime de ahora, que no es «antiguo» para ningún test).
    """
    carpeta = tmp_path / "Descargas"
    carpeta.mkdir()
    for nombre in ("factura.pdf", "apuntes de redes.docx", "FOTO1.JPG",
                   "cumpleaños 2.png", "viejo.tmp"):
        (carpeta / nombre).write_text(f"contenido de {nombre}", encoding="utf-8")
    viejo = carpeta / "viejo.tmp"
    os.utime(viejo, (time.time() - DIAS_VIEJO * SEGUNDOS_POR_DIA,) * 2)
    return carpeta


class ProveedorFalso(ProveedorIA):
    """Proveedor de pruebas que GRABA lo que le preguntan y contesta lo suyo.

    Sin red, sin .env y sin httpx: el test le pone las respuestas que el
    modelo contestaría (la última vale para el resto) y puede afirmar
    contra self.llamadas qué sistema/usuario/max_tokens recibió (p. ej.
    que el documento va entre <documento> y </documento>).
    """

    def __init__(self, texto: str = "respuesta del modelo falso") -> None:
        self.texto = texto
        self.segundos = 0.1
        self.tokens_entrada = 12
        self.tokens_salida = 3
        # (sistema, usuario, max_tokens) de cada llamada, en orden.
        self.llamadas: list[tuple[str, str, int]] = []

    def completar(
        self, sistema: str, usuario: str, max_tokens: int = 800
    ) -> Respuesta:
        self.llamadas.append((sistema, usuario, max_tokens))
        return Respuesta(
            self.texto, self.tokens_entrada, self.tokens_salida, self.segundos
        )


@pytest.fixture
def modelo_falso() -> ProveedorFalso:
    """Un ProveedorFalso nuevo por test (sus llamadas no se comparten)."""
    return ProveedorFalso()
