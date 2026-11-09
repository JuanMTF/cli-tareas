"""Pruebas de la conversión PDF → HTML: carpeta por manual, JSON y galería.

Todos los tests usan carpetas de tmp_path y siempre pasan --destino: no se
toca nunca el destino real del fichero de acciones.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from tareas import html as mod_html
from tareas.cli import app

runner = CliRunner()


def _texto(resultado) -> str:
    """Todo lo que imprimió la orden: stdout y stderr, venga por donde venga."""
    partes = []
    for attr in ("output", "stdout", "stderr"):
        valor = getattr(resultado, attr, None)
        if isinstance(valor, str):
            partes.append(valor)
    return "".join(partes)


def _crear_pdf(ruta: Path, titulo: str = "Manual", paginas: int = 2) -> Path:
    """Crea un PDF de verdad con pymupdf (es lo que hay que convertir)."""
    import pymupdf

    documento = pymupdf.open()
    for n in range(paginas):
        pagina = documento.new_page(width=595, height=842)
        pagina.insert_text((72, 72), f"{titulo} pagina {n + 1}", fontsize=12)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    documento.save(str(ruta))
    documento.close()
    return ruta


def _convertir(origen: Path, destino: Path) -> str:
    """Ejecuta la acción transformar-pdf-html de verdad (sin preguntar)."""
    resultado = runner.invoke(
        app,
        [
            "ejecutar",
            "transformar-pdf-html",
            "--si",
            "--carpeta",
            str(origen),
            "--destino",
            str(destino),
        ],
    )
    assert resultado.exit_code == 0, _texto(resultado)
    return _texto(resultado)


# --- conversión -----------------------------------------------------------


def test_transformar_crea_carpeta_paginas_y_recursos(tmp_path: Path) -> None:
    """Cada PDF acaba en su carpeta con index.html, PNG por página y css/js comunes."""
    origen = tmp_path / "origen"
    destino = tmp_path / "salida"
    _crear_pdf(origen / "mi-manual.pdf", paginas=3)

    texto = _convertir(origen, destino)

    carpeta = destino / "mi-manual"
    assert (carpeta / "index.html").exists()
    assert (carpeta / "pagina-01.png").exists()
    assert (carpeta / "pagina-02.png").exists()
    assert (carpeta / "pagina-03.png").exists()
    # Recursos compartidos: una sola copia en la raíz.
    assert (destino / "estilos.css").exists()
    assert (destino / "script.js").exists()
    assert "3 página(s)" in texto


def test_manual_tiene_texto_buscable_y_enlaces(tmp_path: Path) -> None:
    """El HTML del manual enlaza los recursos de la raíz y lleva capa de texto."""
    origen = tmp_path / "origen"
    destino = tmp_path / "salida"
    _crear_pdf(origen / "epson.pdf", titulo="Epson LX-350", paginas=2)

    _convertir(origen, destino)

    pagina = (destino / "epson" / "index.html").read_text(encoding="utf-8")
    assert 'href="../estilos.css"' in pagina
    assert 'src="../script.js"' in pagina
    assert 'href="../index.html"' in pagina
    assert 'class="capa-texto"' in pagina
    assert "Epson" in pagina  # el texto del PDF queda en la capa
    assert 'id="pagina-02"' in pagina


def test_transformar_escribe_el_json_y_la_galeria(tmp_path: Path) -> None:
    """La acción también deja manuales.json y el index.html que lista los manuales."""
    origen = tmp_path / "origen"
    destino = tmp_path / "salida"
    _crear_pdf(origen / "brother.pdf", paginas=1)

    _convertir(origen, destino)

    datos = json.loads((destino / "manuales.json").read_text(encoding="utf-8"))
    assert datos["version"] == 1
    assert [m["nombre"] for m in datos["manuales"]] == ["brother"]
    assert datos["manuales"][0]["paginas"] == 1
    assert datos["manuales"][0]["pdf"] == "brother.pdf"

    galeria = (destino / "index.html").read_text(encoding="utf-8")
    assert 'href="brother/index.html"' in galeria
    assert 'id="buscar"' in galeria


def test_dos_pdf_comparten_los_mismos_recursos(tmp_path: Path) -> None:
    """Varios PDF en la misma carpeta: un solo css y un solo js para todos."""
    origen = tmp_path / "origen"
    destino = tmp_path / "salida"
    _crear_pdf(origen / "canon.pdf")
    _crear_pdf(origen / "hp.pdf")

    _convertir(origen, destino)

    assert (destino / "canon" / "index.html").exists()
    assert (destino / "hp" / "index.html").exists()
    recursos = [p.name for p in destino.iterdir() if p.suffix in (".css", ".js")]
    assert sorted(recursos) == ["estilos.css", "script.js"]
    datos = json.loads((destino / "manuales.json").read_text(encoding="utf-8"))
    assert len(datos["manuales"]) == 2


def test_simular_no_convierte_nada(tmp_path: Path) -> None:
    """--simular solo anuncia la carpeta: no crea ni el JSON ni los PNG."""
    origen = tmp_path / "origen"
    destino = tmp_path / "salida"
    _crear_pdf(origen / "falso.pdf")

    resultado = runner.invoke(
        app,
        [
            "ejecutar",
            "transformar-pdf-html",
            "--simular",
            "--carpeta",
            str(origen),
            "--destino",
            str(destino),
        ],
    )
    assert resultado.exit_code == 0
    assert "falso/index.html" in _texto(resultado)
    assert not destino.exists()


# --- indexar --------------------------------------------------------------


def _indice(origen: Path, destino: Path, *extras: str) -> str:
    """Ejecuta «tareas indexar» con las opciones indicadas."""
    resultado = runner.invoke(
        app,
        ["indexar", str(origen), "--destino", str(destino), *extras],
    )
    assert resultado.exit_code == 0, _texto(resultado)
    return _texto(resultado)


def test_indexar_convierte_todo_lo_que_hay(tmp_path: Path) -> None:
    """La primera pasada convierte todos los PDF y deja el JSON al día."""
    origen = tmp_path / "origen"
    destino = tmp_path / "salida"
    _crear_pdf(origen / "canon.pdf", paginas=1)
    _crear_pdf(origen / "epson.pdf", paginas=2)

    texto = _indice(origen, destino)

    assert "Convertido: «canon.pdf»" in texto
    assert "Convertido: «epson.pdf»" in texto
    datos = json.loads((destino / "manuales.json").read_text(encoding="utf-8"))
    assert len(datos["manuales"]) == 2


def test_indexar_no_toca_lo_que_ya_esta_hecho(tmp_path: Path) -> None:
    """Un PDF nuevo no rehace ni reescribe lo ya convertido: solo se añade."""
    origen = tmp_path / "origen"
    destino = tmp_path / "salida"
    _crear_pdf(origen / "viejo.pdf", paginas=1)
    _indice(origen, destino)

    hecho = destino / "viejo" / "index.html"
    antes = hecho.read_bytes()
    mtime_antes = (destino / "viejo" / "pagina-01.png").stat().st_mtime_ns

    _crear_pdf(origen / "nuevo.pdf", paginas=1)
    texto = _indice(origen, destino)

    assert "Convertido: «nuevo.pdf»" in texto
    assert "Ya estaba: «viejo.pdf» (no se toca)" in texto
    # Lo antiguo byte a byte idéntico y con la misma fecha.
    assert hecho.read_bytes() == antes
    assert (destino / "viejo" / "pagina-01.png").stat().st_mtime_ns == mtime_antes
    # Y lo nuevo está en el JSON.
    datos = json.loads((destino / "manuales.json").read_text(encoding="utf-8"))
    assert sorted(m["nombre"] for m in datos["manuales"]) == ["nuevo", "viejo"]


def test_indexar_sin_cambios_no_reescribe_el_json(tmp_path: Path) -> None:
    """Segunda pasada sin PDF nuevos: el manuales.json no se vuelve a tocar."""
    origen = tmp_path / "origen"
    destino = tmp_path / "salida"
    _crear_pdf(origen / "unico.pdf", paginas=1)
    _indice(origen, destino)

    json_ruta = destino / "manuales.json"
    antes = json_ruta.read_bytes()

    texto = _indice(origen, destino)

    assert "Ya estaba: «unico.pdf»" in texto
    assert "Actualizado" not in texto
    assert json_ruta.read_bytes() == antes


def test_indexar_registra_lo_convertido_fuera_del_json(tmp_path: Path) -> None:
    """Si borran el JSON, lo vuelve a montar con lo que ya está convertido."""
    origen = tmp_path / "origen"
    destino = tmp_path / "salida"
    _crear_pdf(origen / "perdido.pdf", paginas=2)
    _indice(origen, destino)
    (destino / "manuales.json").unlink()

    texto = _indice(origen, destino)

    assert "Registrado: «perdido.pdf»" in texto
    datos = json.loads((destino / "manuales.json").read_text(encoding="utf-8"))
    assert datos["manuales"][0]["paginas"] == 2


def test_indexar_simular_no_escribe_nada(tmp_path: Path) -> None:
    """Con --simular no se crea ni la carpeta de destino."""
    origen = tmp_path / "origen"
    destino = tmp_path / "salida"
    _crear_pdf(origen / "mirar.pdf")

    texto = _indice(origen, destino, "--simular")

    assert "SIMULACIÓN: convertiría «mirar.pdf»" in texto
    assert not destino.exists()


def test_indexar_sin_pdfs_da_aviso(tmp_path: Path) -> None:
    """Una carpeta sin PDF no crea nada y lo dice."""
    origen = tmp_path / "vacia"
    origen.mkdir()
    destino = tmp_path / "salida"

    texto = _indice(origen, destino)

    assert "No hay PDF" in texto
    assert not destino.exists()


def test_indexar_carpeta_inexistente_da_1(tmp_path: Path) -> None:
    """Si la carpeta no existe, avisa y sale con código 1."""
    resultado = runner.invoke(
        app,
        ["indexar", str(tmp_path / "no-existe"), "--destino", str(tmp_path / "salida")],
    )
    assert resultado.exit_code == 1
    assert "No existe la carpeta" in _texto(resultado)


def test_indexar_sin_destino_ni_json_da_3(tmp_path: Path, monkeypatch) -> None:
    """Sin acción transformar en el JSON hay que indicar --destino (código 3)."""
    monkeypatch.setattr("tareas.cli._destino_transformar", lambda: None)
    origen = tmp_path / "origen"
    origen.mkdir()

    resultado = runner.invoke(app, ["indexar", str(origen)])

    assert resultado.exit_code == 3
    assert "--destino" in _texto(resultado)


def test_indexar_usa_el_destino_del_json(tmp_path: Path, monkeypatch) -> None:
    """Sin --destino, indexar guarda donde diga la acción transformar del JSON."""
    origen = tmp_path / "origen"
    destino = tmp_path / "json-destino"
    _crear_pdf(origen / "auto.pdf")
    monkeypatch.setattr("tareas.cli._destino_transformar", lambda: destino)

    resultado = runner.invoke(app, ["indexar", str(origen)])

    assert resultado.exit_code == 0, _texto(resultado)
    assert (destino / "auto" / "index.html").exists()


def test_indexar_y_transformar_escriben_en_el_mismo_sitio(tmp_path: Path) -> None:
    """Lo que convierte una orden lo reconoce la otra (mismo JSON)."""
    origen = tmp_path / "origen"
    destino = tmp_path / "salida"
    _crear_pdf(origen / "compartido.pdf")

    _convertir(origen, destino)
    texto = _indice(origen, destino)

    assert "Ya estaba: «compartido.pdf» (no se toca)" in texto
    datos = json.loads((destino / "manuales.json").read_text(encoding="utf-8"))
    assert [m["nombre"] for m in datos["manuales"]] == ["compartido"]


def test_leer_manuales_sobre_json_roto_devuelve_vacio(tmp_path: Path) -> None:
    """Un manuales.json corrupto no rompe indexar: se trata como vacío."""
    (tmp_path / mod_html.NOMBRE_JSON).write_text("{roto", encoding="utf-8")
    assert mod_html.leer_manuales(tmp_path) == []
