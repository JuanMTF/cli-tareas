"""Tests de la acción «estado-pc»: informe del equipo, solo lectura.

psutil es una dependencia real (no hay red ni .env): los tests ejecutan la
acción de verdad, que lo único que hace es LEER el sistema. Comprueban que
el informe sale «hecho» con sus bloques, que «--simular» no lee nada y que
el tipo pasa la validación del JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tareas.acciones import EstadoPC, cargar_acciones, validar_acciones
from tareas import config as mod_config
from tareas.errores import AccionNoValida


def _config() -> dict:
    return {
        "nombre": "estado-pc-prueba",
        "descripcion": "informe del equipo de prueba",
        "tipo": "estado-pc",
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
    assert any(accion.get("tipo") == "estado-pc" for accion in acciones)


# --- ejecución ----------------------------------------------------------------


def test_simular_no_lee_nada() -> None:
    accion = EstadoPC(_config())
    resultados = accion.ejecutar([], True)
    assert len(resultados) == 1
    assert resultados[0].estado == "simulado"
    assert "SIMULACIÓN" in resultados[0].mensaje


def test_informe_real_es_hecho_con_los_bloques() -> None:
    """Ejecuta de verdad (solo lectura): el informe lleva CPU y memoria."""
    accion = EstadoPC(_config())
    resultados = accion.ejecutar([], False)
    assert len(resultados) == 1
    assert resultados[0].estado == "hecho"
    mensaje = resultados[0].mensaje
    assert "Estado del equipo" in mensaje
    assert "CPU" in mensaje
    assert "Memoria" in mensaje
    assert "Encendido desde" in mensaje


def test_informe_real_no_modifica_nada(tmp_path: Path) -> None:
    """Después del informe, la carpeta de pruebas sigue igual (solo lectura)."""
    antes = sorted(p.name for p in tmp_path.iterdir())
    accion = EstadoPC(_config())
    accion.ejecutar([], False)
    despues = sorted(p.name for p in tmp_path.iterdir())
    assert antes == despues


# --- avisos (umbrales del JSON) ------------------------------------------------


def _config_avisos(avisos: object) -> dict:
    return {**_config(), "avisos": avisos}


def test_avisos_validos_pasan_la_validacion(tmp_path: Path) -> None:
    ruta = tmp_path / "acciones.json"
    ruta.write_text(
        json.dumps(
            {
                "version": 1,
                "acciones": [
                    _config_avisos({"disco_pct": 70, "memoria_pct": 85, "cpu_pct": 90})
                ],
            }
        ),
        encoding="utf-8",
    )
    errores, _ = validar_acciones(cargar_acciones(ruta))
    assert errores == []


@pytest.mark.parametrize(
    "avisos",
    [
        {"disco_pct": 101},          # fuera de rango
        {"cpu_pct": 0},              # fuera de rango
        {"memoria_pct": "ochenta"},  # no es un entero
        {"disco_pct": True},         # bool no vale
        {"temperatura_pct": 90},     # clave desconocida
        "no-soy-un-objeto",          # tiene que ser un objeto
    ],
)
def test_avisos_mal_puestos_se_rechazan(avisos: object) -> None:
    """config.validar() rechaza los umbrales mal puestos, con su motivo."""
    with pytest.raises(AccionNoValida) as exc:
        mod_config.validar(_config_avisos(avisos), 1, set())
    assert "avisos" in str(exc.value)


def test_aviso_cuando_se_supera_el_umbral() -> None:
    """Umbral 1%: CPU, memoria y discos lo pasan siempre → salen AVISO."""
    accion = EstadoPC(_config_avisos({"cpu_pct": 1, "memoria_pct": 1, "disco_pct": 1}))
    mensaje = accion.ejecutar([], False)[0].mensaje
    assert "AVISO: CPU al" in mensaje
    assert "AVISO: Memoria al" in mensaje
    assert "AVISO: Disco" in mensaje


def test_sin_avisos_no_hay_avisos() -> None:
    """Sin campo «avisos» en el JSON, el informe no saca ningún AVISO."""
    accion = EstadoPC(_config())
    mensaje = accion.ejecutar([], False)[0].mensaje
    assert "AVISO" not in mensaje


def test_aviso_no_cambia_el_estado() -> None:
    """Un aviso no es un error: el resultado sigue siendo «hecho»."""
    accion = EstadoPC(_config_avisos({"cpu_pct": 1, "memoria_pct": 1, "disco_pct": 1}))
    resultado = accion.ejecutar([], False)[0]
    assert resultado.estado == "hecho"
