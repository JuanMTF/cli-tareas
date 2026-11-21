"""Tests de la acción «ip-conf»: configuración de red por adaptador.

Mismo enfoque que «estado-pc»: psutil lista adaptadores, la acción interactúa
(selección y valores) y con --simular no escribe nada. Aquí se comprueba el
registro, la validación del JSON y el listado de adaptadores.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from tareas.acciones import IpConfig, cargar_acciones, validar_acciones
from tareas import config as mod_config


def _config() -> dict:
    return {
        "nombre": "ip-conf-prueba",
        "descripcion": "configurar la red de prueba",
        "tipo": "ip-conf",
    }


# --- validación --------------------------------------------------------------


def test_el_tipo_pasa_la_validacion(tmp_path: Path) -> None:
    ruta = tmp_path / "acciones.json"
    ruta.write_text(
        json.dumps({"version": 1, "acciones": [_config()]}),
        encoding="utf-8",
    )
    acciones = cargar_acciones(ruta)
    errores, _ = validar_acciones(acciones)
    assert errores == []


def test_esta_registrado_en_el_json_real() -> None:
    # Ruta absoluta del JSON empaquetado: no depende del cwd del test.
    acciones = cargar_acciones(mod_config.RUTA_ACCIONES)
    assert any(accion.get("tipo") == "ip-conf" for accion in acciones)


# --- ejecución ----------------------------------------------------------------


def test_simular_no_configura() -> None:
    accion = IpConfig(_config())
    resultados = accion.ejecutar([], True)
    assert len(resultados) == 1
    assert resultados[0].estado == "simulado"
    assert "SIMULACIÓN" in resultados[0].mensaje


def test_sin_adaptadores_no_configura() -> None:
    import psutil

    def _vacio() -> dict:
        return {}

    original = psutil.net_if_addrs
    psutil.net_if_addrs = _vacio  # type: ignore[assignment]
    try:
        accion = IpConfig(_config())
        resultados = accion.ejecutar([], False)
    finally:
        psutil.net_if_addrs = original  # type: ignore[assignment]
    assert len(resultados) == 1
    assert resultados[0].estado == "hecho"
    assert "No se encontró ningún adaptador" in resultados[0].mensaje


def test_lista_adaptadores(monkeypatch) -> None:
    import psutil

    monkeypatch.setattr(
        psutil,
        "net_if_addrs",
        lambda: {"eth0": [SimpleNamespace(address="192.168.1.10", netmask="255.255.255.0")]},
    )
    adaptadores = IpConfig(_config())._listar_adaptadores()
    assert adaptadores == [
        {"nombre": "eth0", "info": "192.168.1.10/255.255.255.0"},
    ]
