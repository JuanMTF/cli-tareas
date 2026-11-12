"""Tests de las órdenes de la CLI (acciones, validar, ejecutar)."""

from __future__ import annotations

import json
import os
import time
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


def test_validar_json_con_bom_carga_igual(tmp_path: Path) -> None:
    """Los ficheros escritos con el Bloc de notas o PowerShell llevan BOM: se admiten."""
    bom = tmp_path / "bom.json"
    bom.write_text('{"version": 1, "acciones": []}', encoding="utf-8-sig")
    resultado = runner.invoke(app, ["validar", str(bom)])
    assert resultado.exit_code == 0
    assert "acciones válidas" in _texto(resultado)


def test_validar_json_roto_mensaje_en_espanol(tmp_path: Path) -> None:
    """El motivo del fallo se traduce: nada de 'Expecting value' en inglés."""
    roto = tmp_path / "roto.json"
    roto.write_text('{"version": 1, "acciones": [', encoding="utf-8")
    resultado = runner.invoke(app, ["validar", str(roto)])
    assert resultado.exit_code == 3
    texto = _texto(resultado)
    assert "se esperaba" in texto
    assert "Expecting" not in texto


def test_validar_codificacion_no_utf8_da_3_sin_traceback(tmp_path: Path) -> None:
    """Un JSON guardado en ANSI (byte 0xF1 no válido en UTF-8) da error limpio."""
    raro = tmp_path / "ansi.json"
    raro.write_bytes(b'{"version": 1, "acciones": ["\xf1"]}')
    resultado = runner.invoke(app, ["validar", str(raro)])
    assert resultado.exit_code == 3
    texto = _texto(resultado)
    assert "JSON inválido" in texto or "UTF-8" in texto
    assert "Traceback" not in texto


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


def test_ejecutar_mover_simulado_no_toca_nada(tmp_path: Path) -> None:
    """La acción mover ya está implementada: en simulación no toca nada."""
    origen = tmp_path / "origen"
    origen.mkdir()
    (origen / "doc.pdf").write_text("x", encoding="utf-8")

    resultado = runner.invoke(
        app, ["ejecutar", "ordenar-descargas", "--simular", "--carpeta", str(origen)]
    )
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "SIMULACIÓN" in texto
    assert "doc.pdf" in texto
    # el fichero sigue donde estaba
    assert (origen / "doc.pdf").exists()


def test_ejecutar_comprimir_simulado_no_toca_nada(tmp_path: Path) -> None:
    """La acción comprimir ya está implementada: en simulación no toca nada."""
    origen = tmp_path / "origen"
    origen.mkdir()
    viejo = origen / "viejo.pdf"
    viejo.write_text("x", encoding="utf-8")
    # el filtro pide más de 400 días: lo envejecemos a propósito
    antiguo = time.time() - 500 * 86400
    os.utime(viejo, (antiguo, antiguo))

    resultado = runner.invoke(
        app, ["ejecutar", "comprimir-antiguos", "--simular", "--carpeta", str(origen)]
    )
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "SIMULACIÓN" in texto
    assert not list(tmp_path.rglob("*.zip"))  # no se creó ningún zip


def test_ejecutar_comprimir_antiguedad_selecciona_segun_opcion(tmp_path: Path) -> None:
    """--antiguedad/-an <N> manda sobre el «mas_antiguo_que_dias» del fichero."""
    origen = tmp_path / "origen"
    origen.mkdir()
    viejo = origen / "viejo.pdf"
    viejo.write_text("x", encoding="utf-8")
    # El fichero tiene 20 días: con --antiguedad 10 sí es "más antiguo"; con 30 no.
    antiguo = time.time() - 20 * 86400
    os.utime(viejo, (antiguo, antiguo))

    # «-an 10»: 20 días > 10, así que sí se comprime.
    resultado = runner.invoke(
        app,
        [
            "ejecutar",
            "comprimir-antiguos",
            "--simular",
            "-an",
            "10",
            "--carpeta",
            str(origen),
        ],
    )
    assert resultado.exit_code == 0
    assert "1 fichero(s)" in _texto(resultado)

    # «--antiguedad 30»: 20 días < 30, así que no se comprime.
    resultado = runner.invoke(
        app,
        [
            "ejecutar",
            "comprimir-antiguos",
            "--simular",
            "--antiguedad",
            "30",
            "--carpeta",
            str(origen),
        ],
    )
    assert resultado.exit_code == 0
    assert "No hay ficheros que cumplan el filtro" in _texto(resultado)

    # Sin la opción se usa el valor del fichero (400 días): tampoco se comprime.
    resultado = runner.invoke(
        app, ["ejecutar", "comprimir-antiguos", "--simular", "--carpeta", str(origen)]
    )
    assert resultado.exit_code == 0
    assert "No hay ficheros que cumplan el filtro" in _texto(resultado)


def test_ejecutar_copiar_antiguos_simulado_no_toca_nada(tmp_path: Path) -> None:
    """El tipo «copiar» se ejecuta vía subclase del registro: en simulación no toca nada."""
    origen = tmp_path / "origen"
    origen.mkdir()
    viejo = origen / "viejo.pdf"
    viejo.write_text("x", encoding="utf-8")
    antiguo = time.time() - 500 * 86400
    os.utime(viejo, (antiguo, antiguo))

    resultado = runner.invoke(
        app, ["ejecutar", "copiar-antiguos", "--simular", "--carpeta", str(origen)]
    )
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "SIMULACIÓN" in texto
    assert "viejo.pdf" in texto


def test_ejecutar_acepta_carpeta_en_posicion_2(tmp_path: Path) -> None:
    """Si la acción no abre URLs, la posición 2 se toma como carpeta de origen."""
    origen = tmp_path / "origen"
    origen.mkdir()
    (origen / "doc.pdf").write_text("x", encoding="utf-8")

    resultado = runner.invoke(
        app, ["ejecutar", "ordenar-descargas", str(origen), "--simular"]
    )
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "SIMULACIÓN" in texto
    assert "doc.pdf" in texto
    assert (origen / "doc.pdf").exists()


def test_ejecutar_url_a_accion_que_no_abre_urls_da_1(tmp_path: Path) -> None:
    """Una URL en una acción de ficheros avisa en vez de ignorarse."""
    resultado = runner.invoke(
        app,
        ["ejecutar", "ordenar-descargas", "https://ejemplo.com/", "--simular"],
    )
    assert resultado.exit_code == 1
    texto = _texto(resultado)
    assert "no abre URLs" in texto
    assert "--carpeta" in texto


def test_ejecutar_carpeta_en_posicion_2_y_como_opcion_da_1(tmp_path: Path) -> None:
    """La carpeta solo puede indicarse una vez."""
    resultado = runner.invoke(
        app,
        [
            "ejecutar",
            "ordenar-descargas",
            str(tmp_path),
            "--carpeta",
            str(tmp_path),
            "--simular",
        ],
    )
    assert resultado.exit_code == 1
    assert "una sola vez" in _texto(resultado)


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

    registros: list[tuple[str, object]] = []

    def _falso_register(
        nombre: str, klass: object, instance: object = None, **_: object
    ) -> None:
        registros.append((nombre, instance))

    monkeypatch.setattr(mod_acciones.webbrowser, "open", _falso_abrir)
    monkeypatch.setattr(mod_acciones.webbrowser, "register", _falso_register)
    monkeypatch.setattr(
        "tareas.cli.buscar_navegador", lambda clave: Path("C:/fake/msedge.exe")
    )

    resultado = runner.invoke(app, ["ejecutar", "abrir-nav", "-e"], input="y\n")
    assert resultado.exit_code == 0

    assert vistos == _urls_abrir_nav()
    # El navegador que se registra es el pedido («edge» para -e): no el por defecto.
    assert len(registros) == 1
    assert registros[0][0] == "edge"
    assert getattr(registros[0][1], "name", None) == str(Path("C:/fake/msedge.exe"))


def test_ejecutar_real_con_url_abre_solo_esa_url(monkeypatch) -> None:
    capturado: dict[str, list[str]] = {}

    vistos: list[str] = []

    def _falso_abrir(url: str, new: int = 0) -> bool:
        vistos.append(url)
        return True

    registros: list[tuple[str, object]] = []

    def _falso_register(
        nombre: str, klass: object, instance: object = None, **_: object
    ) -> None:
        registros.append((nombre, instance))

    monkeypatch.setattr(mod_acciones.webbrowser, "open", _falso_abrir)
    monkeypatch.setattr(mod_acciones.webbrowser, "register", _falso_register)
    monkeypatch.setattr(
        "tareas.cli.buscar_navegador", lambda clave: Path("C:/fake/firefox.exe")
    )

    resultado = runner.invoke(
        app, ["ejecutar", "abrir-nav", "-f", "https://epson.com"], input="y\n"
    )
    assert resultado.exit_code == 0

    assert vistos == ["https://epson.com"]
    # El navegador que se registra es el pedido («firefox» para -f): no el por defecto.
    assert len(registros) == 1
    assert registros[0][0] == "firefox"
    assert getattr(registros[0][1], "name", None) == str(Path("C:/fake/firefox.exe"))


def test_ejecutar_real_cancelado_por_el_usuario_da_1() -> None:
    resultado = runner.invoke(app, ["ejecutar", "abrir-nav"], input="n\n")
    assert resultado.exit_code == 1


def test_ejecutar_con_si_no_pregunta_y_ejecuta(monkeypatch) -> None:
    """--si salta la confirmación: no hace falta responder a la pregunta."""
    capturado: dict[str, list[str]] = {}

    def _falso_abrir(urls: list[str]) -> None:
        capturado["urls"] = urls

    monkeypatch.setattr("tareas.cli.abrir_por_defecto", _falso_abrir)

    # sin input: si preguntara, abortaría con código 1
    resultado = runner.invoke(app, ["ejecutar", "abrir-nav", "--si"])
    assert resultado.exit_code == 0
    assert capturado["urls"] == _urls_abrir_nav()


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


# --- retoques: carpetas, --destino y solo PDF ------------------------------


def test_ejecutar_comprimir_incluye_carpetas_viejas(tmp_path: Path) -> None:
    """comprimir (y copiar) también elige carpetas antiguas, no solo ficheros."""
    origen = tmp_path / "origen"
    (origen / "carpeta-vieja").mkdir(parents=True)
    (origen / "carpeta-vieja" / "nino.txt").write_text("hola", encoding="utf-8")
    antiguo = time.time() - 500 * 86400
    os.utime(origen / "carpeta-vieja", (antiguo, antiguo))

    resultado = runner.invoke(
        app, ["ejecutar", "comprimir-antiguos", "--simular", "--carpeta", str(origen)]
    )
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "carpeta-vieja" in texto
    assert not list(tmp_path.rglob("*.zip"))


def test_ejecutar_copiar_incluye_carpetas_viejas(tmp_path: Path) -> None:
    """La acción copiar también acepta carpetas como origen."""
    origen = tmp_path / "origen"
    (origen / "carpeta-vieja").mkdir(parents=True)
    antiguo = time.time() - 500 * 86400
    os.utime(origen / "carpeta-vieja", (antiguo, antiguo))

    resultado = runner.invoke(
        app, ["ejecutar", "copiar-antiguos", "--simular", "--carpeta", str(origen)]
    )
    assert resultado.exit_code == 0
    assert "carpeta-vieja" in _texto(resultado)


def test_ejecutar_mover_no_elige_carpetas(tmp_path: Path) -> None:
    """Mover sigue siendo solo de ficheros: no arrastra carpetas del origen."""
    origen = tmp_path / "origen"
    (origen / "carpeta-vieja").mkdir(parents=True)
    antiguo = time.time() - 500 * 86400
    os.utime(origen / "carpeta-vieja", (antiguo, antiguo))

    resultado = runner.invoke(
        app, ["ejecutar", "ordenar-descargas", "--simular", "--carpeta", str(origen)]
    )
    assert resultado.exit_code == 0
    assert "carpeta-vieja" not in _texto(resultado)


def test_ejecutar_comprimir_destino_de_la_opcion(tmp_path: Path) -> None:
    """--destino/-d sobreescribe el «destino» del fichero de acciones."""
    origen = tmp_path / "origen"
    origen.mkdir()
    viejo = origen / "viejo.pdf"
    viejo.write_text("x", encoding="utf-8")
    antiguo = time.time() - 500 * 86400
    os.utime(viejo, (antiguo, antiguo))
    salida = tmp_path / "mi-salida"

    resultado = runner.invoke(
        app,
        [
            "ejecutar",
            "comprimir-antiguos",
            "--simular",
            "--carpeta",
            str(origen),
            "--destino",
            str(salida),
        ],
    )
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    # La ruta completa se pliega en la tabla (ancho 80): comprobamos el nombre.
    assert salida.name in texto
    # sin la opción manda la del fichero de acciones (~/Documentos/PDF)
    resultado = runner.invoke(
        app, ["ejecutar", "comprimir-antiguos", "--simular", "--carpeta", str(origen)]
    )
    assert str(salida) not in _texto(resultado)


def test_ejecutar_copiar_destino_de_la_opcion_copia_de_verdad(tmp_path: Path) -> None:
    """Con --destino la copia real acaba en la carpeta indicada."""
    origen = tmp_path / "origen"
    origen.mkdir()
    viejo = origen / "viejo.pdf"
    viejo.write_text("x", encoding="utf-8")
    antiguo = time.time() - 500 * 86400
    os.utime(viejo, (antiguo, antiguo))
    salida = tmp_path / "mi-salida"

    resultado = runner.invoke(
        app,
        [
            "ejecutar",
            "copiar-antiguos",
            "--si",
            "--carpeta",
            str(origen),
            "--destino",
            str(salida),
        ],
    )
    assert resultado.exit_code == 0
    assert (salida / "viejo.pdf").exists()
    assert viejo.exists()  # el original se queda


def test_ejecutar_comprimir_destino_abreviado_d(tmp_path: Path) -> None:
    """La opción también se puede escribir abreviada: -d."""
    origen = tmp_path / "origen"
    origen.mkdir()
    viejo = origen / "viejo.pdf"
    viejo.write_text("x", encoding="utf-8")
    antiguo = time.time() - 500 * 86400
    os.utime(viejo, (antiguo, antiguo))
    salida = tmp_path / "otra-salida"

    resultado = runner.invoke(
        app,
        ["ejecutar", "comprimir-antiguos", "--simular", "-c", str(origen), "-d", str(salida)],
    )
    assert resultado.exit_code == 0
    # La ruta completa se pliega en la tabla (ancho 80): comprobamos el nombre.
    assert salida.name in _texto(resultado)


def test_transformar_pdf_html_solo_elige_pdf(tmp_path: Path) -> None:
    """La acción transformar-pdf-html ignora los .docx y el resto de ficheros."""
    origen = tmp_path / "origen"
    origen.mkdir()
    (origen / "apuntes.pdf").write_text("x", encoding="utf-8")
    (origen / "contrato.docx").write_text("x", encoding="utf-8")
    (origen / "instalador.exe").write_text("x", encoding="utf-8")

    resultado = runner.invoke(
        app,
        ["ejecutar", "transformar-pdf-html", "--simular", "--carpeta", str(origen)],
    )
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "apuntes/index.html" in texto
    assert "contrato" not in texto
    assert "instalador" not in texto


# --- retoques: solo fecha, nombre del .zip y nada de sobrescribir ----------


def _viejo(ruta: Path, dias: int = 500) -> Path:
    """Crea el fichero si hacía falta y le pone la antigüedad indicada."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not ruta.exists():
        ruta.write_text("x", encoding="utf-8")
    antiguo = time.time() - dias * 86400
    os.utime(ruta, (antiguo, antiguo))
    return ruta


def test_comprimir_no_filtra_por_tipo_de_fichero(tmp_path: Path) -> None:
    """comprimir-antiguos solo filtra por fecha: coge .txt, .exe, lo que sea."""
    origen = tmp_path / "mi-carpeta"
    origen.mkdir()
    for nombre in ("notas.txt", "instalador.exe", "foto.jpg"):
        (origen / nombre).write_text("x", encoding="utf-8")
        _viejo(origen / nombre)
    (origen / "nuevo.pdf").write_text("x", encoding="utf-8")  # hoy: no entra

    resultado = runner.invoke(
        app, ["ejecutar", "comprimir-antiguos", "--simular", "--carpeta", str(origen)]
    )
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "notas.txt" in texto
    assert "instalador.exe" in texto
    assert "foto.jpg" in texto
    assert "nuevo.pdf" not in texto


def test_comprimir_el_zip_se_llama_como_la_carpeta(tmp_path: Path) -> None:
    """Sin opción de nombre, el .zip se llama como la carpeta de origen."""
    origen = tmp_path / "descargas-viejas"
    origen.mkdir()
    _viejo(origen / "a.txt")
    destino = tmp_path / "salida"

    resultado = runner.invoke(
        app,
        [
            "ejecutar",
            "comprimir-antiguos",
            "--si",
            "--carpeta",
            str(origen),
            "--destino",
            str(destino),
        ],
    )
    assert resultado.exit_code == 0, _texto(resultado)
    assert (destino / "descargas-viejas.zip").exists()
    # Antes se llamaba como la acción: eso ya no pasa.
    assert not (destino / "comprimir-antiguos.zip").exists()


def test_comprimir_opcion_nombre_para_el_zip(tmp_path: Path) -> None:
    """--nombre/-N cambia el nombre del .zip."""
    origen = tmp_path / "origen"
    origen.mkdir()
    _viejo(origen / "a.txt")
    destino = tmp_path / "salida"

    resultado = runner.invoke(
        app,
        [
            "ejecutar",
            "comprimir-antiguos",
            "--si",
            "-c",
            str(origen),
            "-d",
            str(destino),
            "-N",
            "respaldo-enero",
        ],
    )
    assert resultado.exit_code == 0, _texto(resultado)
    assert (destino / "respaldo-enero.zip").exists()


def test_comprimir_no_sobreescribe_renombra_el_zip(tmp_path: Path) -> None:
    """Si el .zip ya existe se renombra con « (1)»: nunca se pisa."""
    origen = tmp_path / "origen"
    origen.mkdir()
    _viejo(origen / "a.txt")
    destino = tmp_path / "salida"
    destino.mkdir()
    (destino / "origen.zip").write_text("ZIP VIEJO", encoding="utf-8")

    resultado = runner.invoke(
        app,
        ["ejecutar", "comprimir-antiguos", "--si", "-c", str(origen), "-d", str(destino)],
    )
    assert resultado.exit_code == 0, _texto(resultado)
    texto = _texto(resultado)
    assert "origen (1).zip" in texto
    assert "ya existía: renombrado" in texto
    assert (destino / "origen.zip").read_text(encoding="utf-8") == "ZIP VIEJO"


def test_copiar_no_sobreescribe_renombra(tmp_path: Path) -> None:
    """Si en el destino ya hay algo con ese nombre, se renombra y no se pisa."""
    origen = tmp_path / "origen"
    (origen / "Ajustes").mkdir(parents=True)
    (origen / "Ajustes" / "nuevo.txt").write_text("NUEVO", encoding="utf-8")
    _viejo(origen / "Ajustes")
    destino = tmp_path / "destino"
    (destino / "Ajustes").mkdir(parents=True)
    (destino / "Ajustes" / "vacio.txt").write_text("NO BORRAR", encoding="utf-8")

    resultado = runner.invoke(
        app,
        ["ejecutar", "copiar-antiguos", "--si", "-c", str(origen), "-d", str(destino)],
    )
    assert resultado.exit_code == 0, _texto(resultado)
    texto = _texto(resultado)
    assert "Ajustes (1)" in texto
    assert "ya existía: renombrado" in texto
    # Lo que ya estaba sigue intacto y lo nuevo está al lado.
    assert (destino / "Ajustes" / "vacio.txt").read_text(encoding="utf-8") == "NO BORRAR"
    assert (destino / "Ajustes (1)" / "nuevo.txt").read_text(encoding="utf-8") == "NUEVO"


def test_n_es_abreviatura_de_antiguedad(tmp_path: Path) -> None:
    """-n N hace lo mismo que -an N y --antiguedad N."""
    origen = tmp_path / "origen"
    origen.mkdir()
    _viejo(origen / "veinte-dias.pdf", dias=20)

    for opcion in ("-n", "-an", "--antiguedad"):
        resultado = runner.invoke(
            app,
            ["ejecutar", "comprimir-antiguos", "--simular", opcion, "10", "-c", str(origen)],
        )
        assert resultado.exit_code == 0, _texto(resultado)
        assert "veinte-dias.pdf" in _texto(resultado), opcion

    # Con 30 días no entra (20 < 30).
    resultado = runner.invoke(
        app,
        ["ejecutar", "comprimir-antiguos", "--simular", "-n", "30", "-c", str(origen)],
    )
    assert resultado.exit_code == 0
    assert "veinte-dias.pdf" not in _texto(resultado)


def test_nombre_en_una_accion_que_no_comprime_da_1(tmp_path: Path) -> None:
    """--nombre solo tiene sentido en comprimir: en el resto avisa y sale con 1."""
    origen = tmp_path / "origen"
    origen.mkdir()
    (origen / "a.txt").write_text("x", encoding="utf-8")

    resultado = runner.invoke(
        app,
        [
            "ejecutar",
            "copiar-antiguos",
            "--simular",
            "-c",
            str(origen),
            "--destino",
            str(tmp_path / "salida"),
            "--nombre",
            "cualquiera",
        ],
    )
    assert resultado.exit_code == 1
    assert "solo sirve para acciones de tipo «comprimir»" in _texto(resultado)


def test_mensaje_vacio_explica_el_filtro(tmp_path: Path) -> None:
    """Si no hay nada que elegir, dice por qué (qué filtro se aplicó)."""
    origen = tmp_path / "origen"
    origen.mkdir()
    (origen / "reciente.pdf").write_text("x", encoding="utf-8")  # hoy

    resultado = runner.invoke(
        app,
        ["ejecutar", "comprimir-antiguos", "--simular", "-n", "30", "-c", str(origen)],
    )
    assert resultado.exit_code == 0
    texto = _texto(resultado)
    assert "No hay ficheros que cumplan el filtro" in texto
    assert "más antiguos que 30 días" in texto
