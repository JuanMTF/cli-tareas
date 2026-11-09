"""Tests de carga y validación del fichero de acciones."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tareas.acciones import (
    ErrorConfiguracion,
    cargar_acciones,
    validar_acciones,
)


def _escribir(tmp_path: Path, datos: object) -> Path:
    """Escribe un JSON de prueba y devuelve su ruta."""
    ruta = tmp_path / "acciones.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return ruta


def _abrir() -> dict:
    """Acción de ejemplo de tipo abrir."""
    return {
        "nombre": "abrir-nav",
        "descripcion": "Abre el explorador por defecto con 4 páginas.",
        "tipo": "abrir",
        "urls": ["https://ejemplo.com/"],
        "confirmar": True,
    }


# --- cargar_acciones -------------------------------------------------------


def test_carga_un_json_correcto(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path, {"version": 1, "acciones": [_abrir()]})
    assert cargar_acciones(ruta) == [_abrir()]


def test_json_roto_da_error_configuracion(tmp_path: Path) -> None:
    ruta = tmp_path / "roto.json"
    ruta.write_text('{"version": 1, "acciones": [', encoding="utf-8")
    with pytest.raises(ErrorConfiguracion):
        cargar_acciones(ruta)


def test_fichero_inexistente_da_error_configuracion(tmp_path: Path) -> None:
    with pytest.raises(ErrorConfiguracion):
        cargar_acciones(tmp_path / "no-existe.json")


def test_version_distinta_da_error_configuracion(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path, {"version": 2, "acciones": []})
    with pytest.raises(ErrorConfiguracion):
        cargar_acciones(ruta)


def test_acciones_no_lista_da_error_configuracion(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path, {"version": 1, "acciones": "ninguna"})
    with pytest.raises(ErrorConfiguracion):
        cargar_acciones(ruta)


def test_acepta_tildes_y_encoding_utf8(tmp_path: Path) -> None:
    datos = {"version": 1, "acciones": [{"nombre": "áacción"}]}
    ruta = _escribir(tmp_path, datos)
    assert cargar_acciones(ruta)[0]["nombre"] == "áacción"


# --- validar_acciones ------------------------------------------------------


def test_accion_bien_formada_no_da_nada() -> None:
    assert validar_acciones([_abrir()]) == ([], [])


def test_lista_vacia_solo_da_aviso() -> None:
    errores, avisos = validar_acciones([])
    assert errores == []
    assert len(avisos) == 1


def test_tipo_desconocido_es_error() -> None:
    accion = _abrir()
    accion["tipo"] = "Tranformar"
    errores, _ = validar_acciones([accion])
    assert any("desconocido" in error for error in errores)


def test_abrir_sin_urls_es_error() -> None:
    accion = _abrir()
    del accion["urls"]
    errores, _ = validar_acciones([accion])
    assert any("urls" in error for error in errores)


def test_url_sin_http_es_error() -> None:
    accion = _abrir()
    accion["urls"] = ["mi-es.solutions30.com"]
    errores, _ = validar_acciones([accion])
    assert any("http" in error for error in errores)


def test_nombre_duplicado_es_error() -> None:
    errores, _ = validar_acciones([_abrir(), _abrir()])
    assert any("duplicado" in error for error in errores)


def test_nombre_mayusculas_es_error() -> None:
    accion = _abrir()
    accion["nombre"] = "Abre_Edge"
    errores, _ = validar_acciones([accion])
    assert any("kebab-case" in error for error in errores)


def test_campo_que_no_le_toca_es_aviso_no_error() -> None:
    accion = _abrir()
    accion["destino"] = "~/nada"
    errores, avisos = validar_acciones([accion])
    assert errores == []
    assert any("destino" in aviso for aviso in avisos)


def test_borrar_sin_confirmar_es_error() -> None:
    accion = {
        "nombre": "limpiar-temporales",
        "descripcion": "Borra .tmp",
        "tipo": "borrar",
        "filtro": {"patron": ".*\\.tmp$"},
    }
    errores, _ = validar_acciones([accion])
    assert any("confirmar" in error for error in errores)


def test_fichero_real_del_proyecto_es_valido() -> None:
    ruta = Path("src/tareas/docs/acciones.json")
    acciones = cargar_acciones(ruta)
    errores, _ = validar_acciones(acciones)
    assert errores == []
    assert len(acciones) >= 6
    nombres = [accion["nombre"] for accion in acciones]
    assert "abrir-nav" in nombres
    assert "comprimir-antiguos" in nombres


def test_comprimir_es_un_tipo_conocido() -> None:
    accion = {
        "nombre": "comprimir-antiguos",
        "descripcion": "Comprime lo viejo",
        "tipo": "comprimir",
        "origen": "~/Descargas",
        "filtro": { "extensiones": [".pdf"], "mas_antiguo_que_dias": 400 },
        "destino": "~/Documentos/PDF",
    }
    errores, _ = validar_acciones([accion])
    assert errores == []


def test_comprimir_sin_origen_es_error() -> None:
    accion = {
        "nombre": "comprimir-antiguos",
        "descripcion": "Comprime lo viejo",
        "tipo": "comprimir",
        "filtro": { "extensiones": [".pdf"] },
        "destino": "~/Documentos/PDF",
    }
    errores, _ = validar_acciones([accion])
    assert any("origen" in error for error in errores)


def test_copiar_es_un_tipo_conocido() -> None:
    accion = {
        "nombre": "copiar-antiguos",
        "descripcion": "Copia lo viejo",
        "tipo": "copiar",
        "origen": "~/Descargas",
        "filtro": { "extensiones": [".pdf"], "mas_antiguo_que_dias": 400 },
        "destino": "~/Documentos/PDFcopias",
    }
    errores, _ = validar_acciones([accion])
    assert errores == []


def test_copiar_sin_origen_es_error() -> None:
    accion = {
        "nombre": "copiar-antiguos",
        "descripcion": "Copia lo viejo",
        "tipo": "copiar",
        "filtro": { "extensiones": [".pdf"] },
        "destino": "~/Documentos/PDFcopias",
    }
    errores, _ = validar_acciones([accion])
    assert any("origen" in error for error in errores)


def test_mas_antiguo_que_dias_no_numerico_es_error() -> None:
    accion = _abrir()
    accion["tipo"] = "comprimir"
    accion["origen"] = "~/Descargas"
    accion["destino"] = "~/nada"
    accion["filtro"] = { "extensiones": [".pdf"], "mas_antiguo_que_dias": "muchos" }
    errores, _ = validar_acciones([accion])
    assert any("mas_antiguo_que_dias" in error for error in errores)


def test_errata_en_el_filtro_es_aviso() -> None:
    accion = _abrir()
    accion["tipo"] = "comprimir"
    accion["origen"] = "~/Descargas"
    accion["destino"] = "~/nada"
    accion["filtro"] = { "extensiones": [".pdf"], "mas_antiguio_que_dias": 400 }
    errores, avisos = validar_acciones([accion])
    assert errores == []
    assert any("mas_antiguio_que_dias" in aviso for aviso in avisos)


def test_mayor_que_mb_es_un_filtro_reconocido() -> None:
    """mayor_que_mb lo usa motor.py: no debe salir como «no reconocido»."""
    accion = {
        "nombre": "grandes",
        "descripcion": "Ficheros grandes",
        "tipo": "comprimir",
        "origen": "~/Descargas",
        "filtro": { "extensiones": [".zip"], "mayor_que_mb": 100 },
        "destino": "~/nada",
    }
    errores, avisos = validar_acciones([accion])
    assert errores == []
    assert not any("mayor_que_mb" in aviso for aviso in avisos)


def test_mayor_que_mb_no_positivo_es_error() -> None:
    accion = {
        "nombre": "grandes",
        "descripcion": "Ficheros grandes",
        "tipo": "comprimir",
        "origen": "~/Descargas",
        "filtro": { "extensiones": [".zip"], "mayor_que_mb": 0 },
        "destino": "~/nada",
    }
    errores, _ = validar_acciones([accion])
    assert any("mayor_que_mb" in error for error in errores)
