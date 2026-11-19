"""Tests de tus opciones por defecto: ~/.cliWork/configUsuario.json (ADR-0014).

El aislado de conftest apunta HOME y USERPROFILE al tmp_path, así que
usuario.ruta() cae en el sandbox: aquí no se toca el fichero del usuario
de verdad. Cada test escribe (o no) su configUsuario.json y comprueba las
prioridades que decidieron el ADR: lo tuyo manda si lo defines, lo vacío
no cambia nada, y «borrar» pregunta SIEMPRE con su aviso ⚠.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tareas import usuario
from tareas.cli import app
from tareas.errores import ConfigError
from tareas.motor import Motor


def escribir_usuario(datos: dict[str, Any]) -> Path:
    """Escribe TU configUsuario.json en el sandbox y devuelve su ruta."""
    camino = usuario.ruta()
    camino.parent.mkdir(parents=True, exist_ok=True)
    camino.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return camino


def accion_mover(origen: str, destino: str, filtro: dict[str, Any]) -> dict[str, Any]:
    """Una acción mover válida para montar Motor directamente."""
    return {
        "nombre": "probar-movimiento",
        "descripcion": "mover de prueba para configUsuario",
        "tipo": "mover",
        "origen": origen,
        "filtro": filtro,
        "destino": destino,
    }


# --- creación y lectura ------------------------------------------------------


def test_se_crea_al_primer_uso_con_lo_vacio() -> None:
    assert not usuario.ruta().exists()
    datos = usuario.cargar()
    assert usuario.ruta().exists()
    # Lo vacío: sin origen ni destino ni extensiones (no cambia nada) y
    # pidiendo confirmación (como siempre).
    assert usuario.origen_defecto() is None
    assert usuario.destino_defecto() is None
    assert usuario.extensiones_defecto() == []
    assert usuario.confirmar_por_defecto() is True
    assert datos["origen"] == ""


def test_la_ayuda_viaja_dentro_del_fichero() -> None:
    usuario.cargar()
    texto = usuario.ruta().read_text(encoding="utf-8")
    assert "_ayuda" in texto
    # La ayuda explica lo que la gente cambiará (y el ⚠ del borrar):
    assert "borrar" in texto
    assert "no cambiar nada" in texto


def test_normalizar_extensiones_acepta_comas_espacios_y_sin_punto() -> None:
    assert usuario.normalizar_extensiones("pdf, .JPG  tmp") == [
        ".pdf",
        ".JPG",
        ".tmp",
    ]
    assert usuario.normalizar_extensiones("") == []


# --- fichero roto o con erratas -----------------------------------------------


def test_fichero_roto_da_configerror() -> None:
    escribir_usuario_raw = usuario.ruta()
    escribir_usuario_raw.parent.mkdir(parents=True, exist_ok=True)
    escribir_usuario_raw.write_text("{ esto no es json", encoding="utf-8")
    with pytest.raises(ConfigError) as fallo_capturado:
        usuario.cargar()
    assert "no es JSON válido" in str(fallo_capturado.value)


def test_campo_desconocido_avisa_con_su_nombre() -> None:
    escribir_usuario({"extension": [".pdf"]})  # errata: falta la «s» final
    with pytest.raises(ConfigError) as fallo_capturado:
        usuario.cargar()
    assert "extension" in str(fallo_capturado.value)


def test_tipos_malos_se_rechazan() -> None:
    escribir_usuario({"extensiones": "pdf"})  # texto, no lista
    with pytest.raises(ConfigError):
        usuario.cargar()
    escribir_usuario({"confirmar": "no"})  # texto, no booleano
    with pytest.raises(ConfigError):
        usuario.cargar()


# --- origen y destino: lo tuyo manda sobre el JSON -----------------------------


def test_tu_origen_manda_sobre_el_del_json(descargas: Path, tmp_path: Path) -> None:
    # La acción apunta a una carpeta que NO existe: si el JSON mandara,
    # el motor saldría con «La carpeta ... no existe».
    escribir_usuario({"origen": str(descargas)})
    destino_json = tmp_path / "DestinoDelJSON"
    accion = accion_mover(
        origen=str(tmp_path / "NoExiste"),
        destino=str(destino_json),
        filtro={"extensiones": [".tmp"]},
    )
    Motor([accion]).ejecutar("probar-movimiento", None, False)
    assert (destino_json / "viejo.tmp").is_file()
    assert not (descargas / "viejo.tmp").exists()


def test_tu_destino_manda_sobre_el_del_json(descargas: Path, tmp_path: Path) -> None:
    escribir_usuario({"destino": str(tmp_path / "MiDestino")})
    accion = accion_mover(
        origen=str(descargas),
        destino=str(tmp_path / "OtroDestino"),
        filtro={"extensiones": [".pdf"]},
    )
    Motor([accion]).ejecutar("probar-movimiento", None, False)
    assert (tmp_path / "MiDestino" / "factura.pdf").is_file()
    assert not (tmp_path / "OtroDestino").exists()


def test_sin_nada_tuyo_manda_el_json(descargas: Path, tmp_path: Path) -> None:
    # Sin fichero de usuario (o vacío): el comportamiento de siempre.
    destino_json = tmp_path / "DestinoDelJSON"
    accion = accion_mover(
        origen=str(descargas),
        destino=str(destino_json),
        filtro={"extensiones": [".JPG"]},
    )
    Motor([accion]).ejecutar("probar-movimiento", None, False)
    assert (destino_json / "FOTO1.JPG").is_file()


# --- extensiones: CLI > acción > lo tuyo (solo si el filtro no trae) ------------


def test_tus_extensiones_entran_en_filtros_sin_extensiones(
    descargas: Path, tmp_path: Path
) -> None:
    escribir_usuario({"extensiones": [".tmp"]})
    destino = tmp_path / "Destino"
    accion = accion_mover(
        origen=str(descargas),
        destino=str(destino),
        # El filtro solo mira la antigüedad: sin tus extensiones cogería TODO.
        filtro={"mas_antiguo_que_dias": 40},
    )
    Motor([accion]).ejecutar("probar-movimiento", None, False)
    # viejo.tmp (40 días) entra; los demás no: tu lista decidió.
    assert (destino / "viejo.tmp").is_file()
    assert not (destino / "factura.pdf").exists()
    assert (descargas / "factura.pdf").is_file()


def test_la_opcion_de_la_cli_manda_sobre_todo(descargas: Path, tmp_path: Path) -> None:
    # Acción con .docx y tú con .pdf: la CLI pide .tmp → gana la CLI.
    escribir_usuario({"extensiones": [".pdf"]})
    destino = tmp_path / "Destino"
    accion = accion_mover(
        origen=str(descargas),
        destino=str(destino),
        filtro={"extensiones": [".docx"]},
    )
    Motor([accion]).ejecutar(
        "probar-movimiento", None, False, extensiones=[".tmp"]
    )
    assert (destino / "viejo.tmp").is_file()
    assert (descargas / "apuntes de redes.docx").exists()


def test_tus_extensiones_no_tochan_los_filtros_que_traen_las_suyas(
    descargas: Path, tmp_path: Path
) -> None:
    escribir_usuario({"extensiones": [".pdf"]})
    destino = tmp_path / "Destino"
    accion = accion_mover(
        origen=str(descargas),
        destino=str(destino),
        filtro={"extensiones": [".JPG"]},
    )
    Motor([accion]).ejecutar("probar-movimiento", None, False)
    assert (destino / "FOTO1.JPG").is_file()


# --- confirmar y el aviso ⚠ de borrar ------------------------------------------


def test_borrar_pregunta_siempre_y_avisa(
    runner: CliRunner, texto, descargas: Path, tmp_path: Path, monkeypatch
) -> None:
    escribir_usuario({"confirmar": False})  # no salva al borrar
    ruta_json = tmp_path / "acciones.json"
    ruta_json.write_text(
        json.dumps(
            {
                "version": 1,
                "acciones": [
                    {
                        "nombre": "limpiar-tmp",
                        "descripcion": "borra los .tmp de prueba",
                        "tipo": "borrar",
                        "origen": str(descargas),
                        "filtro": {"patron": r".*\.tmp$"},
                        "confirmar": True,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # Sin responder a la pregunta: cancela (abort), y ANTES salió el ⚠.
    resultado = runner.invoke(
        app, ["--config", str(ruta_json), "ejecutar", "limpiar-tmp"]
    )
    assert resultado.exit_code == 1
    assert "ATENCIÓN" in texto(resultado)
    assert (descargas / "viejo.tmp").exists()
    # Respondiendo «y»: borra de verdad (en el sandbox).
    resultado = runner.invoke(
        app, ["--config", str(ruta_json), "ejecutar", "limpiar-tmp"], input="y\n"
    )
    assert resultado.exit_code == 0
    assert not (descargas / "viejo.tmp").exists()


def test_confirmar_false_quita_la_pregunta_de_las_demas(
    runner: CliRunner, texto, tmp_path: Path, monkeypatch
) -> None:
    escribir_usuario({"confirmar": False})
    capturado: dict[str, list[str]] = {}

    def _falso_abrir(urls: list[str]) -> None:
        capturado["urls"] = urls

    monkeypatch.setattr("tareas.cli.abrir_por_defecto", _falso_abrir)
    ruta_json = tmp_path / "acciones.json"
    ruta_json.write_text(
        json.dumps(
            {
                "version": 1,
                "acciones": [
                    {
                        "nombre": "abrir-nav",
                        "descripcion": "abre de prueba",
                        "tipo": "abrir",
                        "urls": ["https://ejemplo.com/"],
                        "confirmar": True,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # Sin input: si preguntara, abortaría. No pregunta: abre directamente.
    resultado = runner.invoke(
        app, ["--config", str(ruta_json), "ejecutar", "abrir-nav"]
    )
    assert resultado.exit_code == 0
    assert capturado["urls"] == ["https://ejemplo.com/"]


def test_confirmar_true_sigue_pidiendo(
    runner: CliRunner, texto, tmp_path: Path
) -> None:
    escribir_usuario({})  # sin tocar nada: como siempre
    ruta_json = tmp_path / "acciones.json"
    ruta_json.write_text(
        json.dumps(
            {
                "version": 1,
                "acciones": [
                    {
                        "nombre": "abrir-nav",
                        "descripcion": "abre de prueba",
                        "tipo": "abrir",
                        "urls": ["https://ejemplo.com/"],
                        "confirmar": True,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    resultado = runner.invoke(
        app, ["--config", str(ruta_json), "ejecutar", "abrir-nav"]
    )
    assert resultado.exit_code == 1  # sin responder: cancela, como siempre


# --- desde fuera: un fichero de usuario roto sale con 3 ------------------------


def test_ejecutar_con_usuario_roto_da_codigo_3(
    runner: CliRunner, texto, descargas: Path, tmp_path: Path
) -> None:
    escribir_usuario_raw = usuario.ruta()
    escribir_usuario_raw.parent.mkdir(parents=True, exist_ok=True)
    escribir_usuario_raw.write_text("no soy json", encoding="utf-8")
    # Con una acción de ficheros (mover): es la rama del motor que lee
    # TU fichero (origen_defecto). --simular para no mover nada de verdad.
    ruta_json = tmp_path / "acciones.json"
    ruta_json.write_text(
        json.dumps(
            {
                "version": 1,
                "acciones": [
                    {
                        "nombre": "mover-de-prueba",
                        "descripcion": "mover de prueba",
                        "tipo": "mover",
                        "origen": str(descargas),
                        "filtro": {"extensiones": [".tmp"]},
                        "destino": str(tmp_path / "Destino"),
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    resultado = runner.invoke(
        app,
        ["--config", str(ruta_json), "ejecutar", "mover-de-prueba", "--carpeta", str(descargas), "--simular"],
    )
    assert resultado.exit_code == 3
    assert "no es JSON" in texto(resultado)
