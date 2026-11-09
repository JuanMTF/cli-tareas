"""Conversión de PDF a HTML: una carpeta por manual, con índice compartido.

Qué se genera dentro de la carpeta de destino:

- ``<destino>/<nombre-del-pdf>/index.html``  el manual, con una imagen por página
  (``pagina-01.png``, ``pagina-02.png``...) y encima una capa de texto
  transparente, para que el navegador pueda buscar y copiar (Ctrl+B).
- ``<destino>/estilos.css`` y ``<destino>/script.js``: UNA sola copia, compartida
  por el índice general y por todos los manuales.
- ``<destino>/manuales.json``: la «base de datos» con los metadatos de cada PDF.
- ``<destino>/index.html``: la galería que lista todos los manuales.

La orden ``tareas indexar`` reutiliza estas mismas funciones: revisa la carpeta,
convierte solo los PDF que falten y actualiza el JSON sin tocar lo ya hecho.
"""

from __future__ import annotations

import json
from datetime import datetime
from html import escape as escapar
from pathlib import Path
from typing import Any
from urllib.parse import quote

from tareas.errores import TareasError

# Píxeles por punto del PDF (72 dpi): 2.0 = 144 dpi, nítido para manuales.
ESCALA = 2.0

NOMBRE_ESTILOS = "estilos.css"
NOMBRE_SCRIPT = "script.js"
NOMBRE_JSON = "manuales.json"
NOMBRE_INDICE = "index.html"

# --------------------------------------------------------------------------
# Recursos compartidos (una sola copia en la raíz del destino)
# --------------------------------------------------------------------------

ESTILOS = """/* Estilos compartidos: los usa el index.html de la galería y cada manual. */
:root {
  --tinta: #1d2430;
  --apagado: #66707f;
  --fondo: #f4f6f8;
  --tarjeta: #ffffff;
  --borde: #d9dee6;
  --acento: #1a56c4;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  color: var(--tinta);
  background: var(--fondo);
  line-height: 1.5;
}
a { color: var(--acento); }

/* --- Galería (index.html de la raíz) --- */
.galeria { max-width: 62rem; margin: 0 auto; padding: 2rem 1rem 4rem; }
.galeria h1 { margin: 0 0 .25rem; }
.galeria .subtitulo { margin: 0 0 1.5rem; color: var(--apagado); }
#buscar {
  width: 100%; padding: .7rem .9rem; font-size: 1rem;
  border: 1px solid var(--borde); border-radius: .5rem; background: var(--tarjeta);
}
#buscar:focus { outline: 2px solid var(--acento); border-color: var(--acento); }
.tarjetas {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: 1rem; padding: 0; margin: 1.5rem 0 0; list-style: none;
}
.tarjeta { background: var(--tarjeta); border: 1px solid var(--borde); border-radius: .6rem; }
.tarjeta:hover { box-shadow: 0 .25rem .75rem rgba(0, 0, 0, .08); }
.tarjeta a { display: block; padding: 1rem; text-decoration: none; color: inherit; }
.tarjeta h2 { margin: 0 0 .35rem; font-size: 1.05rem; word-break: break-word; }
.tarjeta .meta, .tarjeta .origen { margin: 0; font-size: .85rem; color: var(--apagado); }
#sin-resultados { color: var(--apagado); margin-top: 2rem; }

/* --- Manual (carpeta de cada PDF) --- */
.manual .cabecera {
  position: sticky; top: 0; z-index: 5; background: var(--tarjeta);
  border-bottom: 1px solid var(--borde); padding: .7rem 1rem;
}
.manual .cabecera h1 { margin: .25rem 0 0; font-size: 1.15rem; word-break: break-word; }
.manual .datos { margin: .15rem 0 0; font-size: .85rem; color: var(--apagado); }
.manual .volver { font-size: .9rem; }
.paginas {
  display: flex; flex-wrap: wrap; gap: .35rem; padding: .7rem 1rem;
  background: var(--tarjeta); border-bottom: 1px solid var(--borde);
}
.paginas a {
  text-decoration: none; border: 1px solid var(--borde); border-radius: .35rem;
  padding: .15rem .45rem; font-size: .8rem; color: var(--tinta);
}
.paginas a:hover { border-color: var(--acento); color: var(--acento); }
.pagina {
  position: relative; margin: 1.5rem auto; max-width: min(95vw, 60rem);
  background: #fff; box-shadow: 0 .2rem .8rem rgba(0, 0, 0, .12);
}
.pagina img { display: block; width: 100%; height: auto; }
/* Capa de texto: invisible, pero el navegador la busca y la copia. */
.capa-texto { position: absolute; inset: 0; overflow: hidden; color: transparent; }
.capa-texto span { position: absolute; white-space: pre; }
.pie-manual { text-align: center; padding: 1.5rem 1rem; color: var(--apagado); font-size: .9rem; }
@media (max-width: 40rem) { .pagina { margin: .75rem .25rem; } }
"""

SCRIPT = """/* Script compartido: galería (buscador) y manual (flechas de teclado). */
(function () {
  "use strict";

  // Buscador del índice: filtra las tarjetas mientras se escribe.
  var buscar = document.getElementById("buscar");
  if (buscar) {
    var items = Array.prototype.slice.call(document.querySelectorAll("[data-buscar]"));
    var vacio = document.getElementById("sin-resultados");
    buscar.addEventListener("input", function () {
      var texto = buscar.value.toLowerCase().trim();
      var visibles = 0;
      items.forEach(function (item) {
        var coincide = item.getAttribute("data-buscar").indexOf(texto) !== -1;
        item.hidden = !coincide;
        if (coincide) {
          visibles += 1;
        }
      });
      if (vacio) {
        vacio.hidden = visibles !== 0;
      }
    });
  }

  // Manual: flechas del teclado para pasar de página (Home/End = primera/última).
  var paginas = Array.prototype.slice.call(document.querySelectorAll(".pagina"));
  if (paginas.length) {
    var actual = 0;
    function irA(indice) {
      actual = Math.max(0, Math.min(paginas.length - 1, indice));
      paginas[actual].scrollIntoView({ behavior: "smooth", block: "start" });
    }
    document.addEventListener("keydown", function (evento) {
      var destino = evento.target;
      if (destino && /^(INPUT|TEXTAREA)$/.test(destino.tagName)) {
        return;
      }
      if (evento.key === "ArrowRight" || evento.key === "PageDown") {
        irA(actual + 1);
      } else if (evento.key === "ArrowLeft" || evento.key === "PageUp") {
        irA(actual - 1);
      } else if (evento.key === "Home") {
        irA(0);
      } else if (evento.key === "End") {
        irA(paginas.length - 1);
      }
    });
  }
})();
"""


def escribir_recursos(destino: Path, solo_si_faltan: bool = False) -> list[Path]:
    """Escribe estilos.css y script.js en la raíz del destino (compartidos).

    Con ``solo_si_faltan`` no se toca lo que ya existe: es lo que usa «indexar».
    """
    escritos: list[Path] = []
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, contenido in ((NOMBRE_ESTILOS, ESTILOS), (NOMBRE_SCRIPT, SCRIPT)):
        ruta = destino / nombre
        if solo_si_faltan and ruta.exists():
            continue
        ruta.write_text(contenido, encoding="utf-8")
        escritos.append(ruta)
    return escritos


# --------------------------------------------------------------------------
# manuales.json: la «base de datos» de los PDF convertidos
# --------------------------------------------------------------------------


def leer_manuales(destino: Path) -> list[dict[str, Any]]:
    """Lee manuales.json; devuelve [] si no existe o no se puede leer."""
    ruta = destino / NOMBRE_JSON
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    lista = datos.get("manuales") if isinstance(datos, dict) else None
    if not isinstance(lista, list):
        return []
    return [item for item in lista if isinstance(item, dict)]


def guardar_manuales(destino: Path, manuales: list[dict[str, Any]]) -> Path:
    """Escribe manuales.json ordenado por nombre (nunca guarda duplicados)."""
    destino.mkdir(parents=True, exist_ok=True)
    vistos: dict[str, dict[str, Any]] = {}
    for registro in manuales:
        clave = str(registro.get("nombre", ""))
        if clave:
            vistos[clave] = registro
    datos = {
        "version": 1,
        "actualizado": datetime.now().isoformat(timespec="seconds"),
        "manuales": [vistos[clave] for clave in sorted(vistos, key=str.lower)],
    }
    ruta = destino / NOMBRE_JSON
    ruta.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return ruta


def _tamano_legible(n: int) -> str:
    """Convierte bytes en texto: 532 B, 1.2 KB, 3.4 MB..."""
    if n < 1024:
        return f"{n} B"
    valor = float(n)
    unidad = "B"
    for unidad in ("KB", "MB", "GB", "TB"):
        valor /= 1024
        if valor < 1024:
            break
    return f"{valor:.1f} {unidad}"


# --------------------------------------------------------------------------
# Galería: el index.html de la raíz
# --------------------------------------------------------------------------


def escribir_galeria(destino: Path, manuales: list[dict[str, Any]]) -> Path:
    """(Re)escribe el index.html que lista todos los manuales convertidos."""
    destino.mkdir(parents=True, exist_ok=True)
    ordenados = sorted(manuales, key=lambda m: str(m.get("nombre", "")).lower())

    filas: list[str] = []
    for registro in ordenados:
        nombre = str(registro.get("nombre", ""))
        carpeta = quote(str(registro.get("carpeta") or nombre), safe="/")
        paginas = int(registro.get("paginas") or 0)
        tamano = _tamano_legible(int(registro.get("tamano") or 0))
        fecha = str(registro.get("fecha_pdf") or "")[:10]
        origen = str(registro.get("pdf") or "")
        filas.append(
            '      <li class="tarjeta" data-buscar="'
            + escapar(f"{nombre} {origen}".lower(), quote=True)
            + '">\n'
            f'        <a href="{escapar(carpeta, quote=True)}/{NOMBRE_INDICE}">\n'
            f"          <h2>{escapar(nombre)}</h2>\n"
            f'          <p class="meta">{paginas} página(s) · {tamano}'
            + (f" · {fecha}" if fecha else "")
            + "</p>\n"
            f'          <p class="origen">{escapar(origen)}</p>\n'
            "        </a>\n"
            "      </li>\n"
        )

    total = len(ordenados)
    plural = "manual" if total == 1 else "manuales"
    cuerpo = (
        "".join(filas)
        if filas
        else '      <li id="sin-resultados">Todavía no hay manuales convertidos.</li>\n'
    )
    indice = (
        "<!DOCTYPE html>\n"
        '<html lang="es">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>Manuales ({total})</title>\n"
        f'  <link rel="stylesheet" href="{NOMBRE_ESTILOS}">\n'
        "</head>\n"
        '<body class="galeria">\n'
        "  <header>\n"
        "    <h1>Manuales</h1>\n"
        f'    <p class="subtitulo">{total} {plural} · actualizado '
        f'{datetime.now().strftime("%Y-%m-%d %H:%M")}</p>\n'
        '    <input id="buscar" type="search" placeholder="Buscar manual..." '
        'aria-label="Buscar manual">\n'
        "  </header>\n"
        '  <ul class="tarjetas">\n'
        f"{ cuerpo }"
        "  </ul>\n"
        f'  <script src="{NOMBRE_SCRIPT}"></script>\n'
        "</body>\n"
        "</html>\n"
    )
    ruta = destino / NOMBRE_INDICE
    ruta.write_text(indice, encoding="utf-8")
    return ruta


# --------------------------------------------------------------------------
# Conversión de un PDF
# --------------------------------------------------------------------------


def _pymupdf():
    """Importa PyMuPDF tarde: solo hace falta al convertir de verdad."""
    try:
        import pymupdf
    except ImportError as exc:  # pragma: no cover - dependencia faltante
        raise TareasError(
            "Falta la dependencia «pymupdf» para convertir PDF. "
            "Instálala con «uv add pymupdf». Si además usas «tareas» instalado con "
            "«uv tool install», repite «uv tool install --editable .» para que la "
            "herramienta también la tenga."
        ) from exc
    return pymupdf


def _capa_texto(pagina: Any) -> str:
    """Posiciones de cada palabra, transparente, encima de la imagen de la página."""
    trozos: list[str] = []
    for x0, y0, x1, y1, palabra, *_ in pagina.get_text("words"):
        texto = str(palabra).strip()
        if not texto:
            continue
        izquierda = round(x0 * ESCALA)
        arriba = round(y0 * ESCALA)
        alto = max(1, round((y1 - y0) * ESCALA))
        tamano = max(6, round(alto * 0.85))
        trozos.append(
            f'<span style="left:{izquierda}px;top:{arriba}px;font-size:{tamano}px">'
            f"{escapar(texto)}</span>"
        )
    return "".join(trozos)


def convertir_pdf(pdf: Path, destino: Path) -> dict[str, Any]:
    """Convierte un PDF en su carpeta con index.html + páginas en imagen.

    Devuelve el registro que va a manuales.json. Si la carpeta ya existía con
    imágenes, se rehacen (esta función solo se llama para convertir de verdad).
    """
    pymupdf = _pymupdf()
    carpeta = destino / pdf.stem
    carpeta.mkdir(parents=True, exist_ok=True)

    # Se limpian las imágenes viejas: si el PDF cambió, no quedan páginas huérfanas.
    for vieja in carpeta.glob("pagina-*.png"):
        vieja.unlink()

    secciones: list[str] = []
    try:
        with pymupdf.open(str(pdf)) as documento:
            for numero, pagina in enumerate(documento, start=1):
                pix = pagina.get_pixmap(
                    matrix=pymupdf.Matrix(ESCALA, ESCALA), alpha=False
                )
                nombre_png = f"pagina-{numero:02d}.png"
                pix.save(str(carpeta / nombre_png))
                secciones.append(
                    f'    <section class="pagina" id="pagina-{numero:02d}">\n'
                    f'      <img src="{nombre_png}" alt="Página {numero}" '
                    f'width="{pix.width}" height="{pix.height}">\n'
                    f'      <div class="capa-texto">{_capa_texto(pagina)}</div>\n'
                    "    </section>\n"
                )
            total_paginas = documento.page_count
    except Exception as exc:
        raise TareasError(f"No se pudo convertir «{pdf.name}»: {exc}") from exc

    st = pdf.stat()
    registro: dict[str, Any] = {
        "nombre": pdf.stem,
        "pdf": pdf.name,
        "carpeta": carpeta.name,
        "paginas": total_paginas,
        "tamano": st.st_size,
        "fecha_pdf": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "convertido": datetime.now().isoformat(timespec="seconds"),
    }
    carpeta.joinpath(NOMBRE_INDICE).write_text(
        _html_manual(registro, secciones), encoding="utf-8"
    )
    return registro


def _html_manual(registro: dict[str, Any], secciones: list[str]) -> str:
    """Index.html de un manual: cabecera, menú de páginas y las páginas."""
    nombre = str(registro.get("nombre", ""))
    paginas = int(registro.get("paginas") or 0)
    tamano = _tamano_legible(int(registro.get("tamano") or 0))
    convertido = str(registro.get("convertido") or "")[:10]

    enlaces = "".join(
        f'<a href="#pagina-{n:02d}">{n}</a>' for n in range(1, paginas + 1)
    )
    menu = f'\n  <nav class="paginas">{enlaces}</nav>\n' if enlaces else ""

    datos = [f"{paginas} página(s)", tamano]
    if convertido:
        datos.append(f"convertido {convertido}")

    return (
        "<!DOCTYPE html>\n"
        '<html lang="es">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{escapar(nombre)}</title>\n"
        f'  <link rel="stylesheet" href="../{NOMBRE_ESTILOS}">\n'
        "</head>\n"
        '<body class="manual">\n'
        '  <header class="cabecera">\n'
        f'    <a class="volver" href="../{NOMBRE_INDICE}">← Todos los manuales</a>\n'
        f"    <h1>{escapar(nombre)}</h1>\n"
        f'    <p class="datos">{" · ".join(datos)}</p>\n'
        "  </header>\n"
        f"{menu}"
        "  <main>\n"
        + "".join(secciones)
        + "  </main>\n"
        f'  <p class="pie-manual">Flechas ← → para pasar de página; '
        f"Ctrl+B para buscar en el texto.</p>\n"
        f'  <script src="../{NOMBRE_SCRIPT}"></script>\n'
        "</body>\n"
        "</html>\n"
    )


def _paginas_de_carpeta(carpeta: Path) -> int:
    """Cuenta las imágenes de una carpeta ya convertida (sin abrir el PDF)."""
    return len(list(carpeta.glob("pagina-*.png")))


# --------------------------------------------------------------------------
# indexar: revisa una carpeta y añade solo lo que falta
# --------------------------------------------------------------------------


def indexar(origen: Path, destino: Path, simular: bool = False) -> list[str]:
    """Revisa «origen», convierte solo los PDF que falten y actualiza manuales.json.

    Lo ya convertido no se toca: solo se regenera el índice general y el JSON.
    Con ``simular`` no se escribe nada.
    """
    if not origen.is_dir():
        raise TareasError(f"No existe la carpeta: {origen}")

    pdfs = sorted(
        (
            fichero
            for fichero in origen.iterdir()
            if fichero.is_file() and fichero.suffix.lower() == ".pdf"
        ),
        key=lambda fichero: fichero.name.lower(),
    )
    if not pdfs:
        return [f"No hay PDF en «{origen}»."]

    mensajes: list[str] = []
    registros = leer_manuales(destino)
    por_nombre = {str(item.get("nombre", "")): item for item in registros}
    cambios = False

    for pdf in pdfs:
        carpeta = destino / pdf.stem
        ya_convertido = (carpeta / NOMBRE_INDICE).exists()

        if ya_convertido:
            if pdf.stem in por_nombre:
                mensajes.append(f"Ya estaba: «{pdf.name}» (no se toca)")
            else:
                # Convertido pero fuera del JSON: se registra sin volver a convertir.
                st = pdf.stat()
                por_nombre[pdf.stem] = {
                    "nombre": pdf.stem,
                    "pdf": pdf.name,
                    "carpeta": carpeta.name,
                    "paginas": _paginas_de_carpeta(carpeta),
                    "tamano": st.st_size,
                    "fecha_pdf": datetime.fromtimestamp(st.st_mtime).isoformat(
                        timespec="seconds"
                    ),
                    "convertido": "",
                }
                cambios = True
                mensajes.append(f"Registrado: «{pdf.name}» (ya estaba convertido)")
            continue

        if simular:
            mensajes.append(
                f"SIMULACIÓN: convertiría «{pdf.name}» → «{carpeta.name}/{NOMBRE_INDICE}»"
            )
            continue

        registro = convertir_pdf(pdf, destino)
        por_nombre[pdf.stem] = registro
        cambios = True
        mensajes.append(
            f"Convertido: «{pdf.name}» → «{registro['carpeta']}/{NOMBRE_INDICE}» "
            f"({registro['paginas']} página(s))"
        )

    if simular:
        pendientes = sum(1 for m in mensajes if m.startswith("SIMULACIÓN"))
        mensajes.append(
            f"SIMULACIÓN: {pendientes} PDF por convertir; no se escribe nada."
        )
        return mensajes

    # Recursos compartidos: solo si faltan (indexar no toca lo que ya existe).
    escritos = escribir_recursos(destino, solo_si_faltan=True)
    if escritos:
        mensajes.append("Creado: " + ", ".join(f"«{p.name}»" for p in escritos))

    if cambios or not (destino / NOMBRE_INDICE).exists():
        guardar_manuales(destino, list(por_nombre.values()))
        mensajes.append(f"Actualizado: «{NOMBRE_JSON}» con {len(por_nombre)} manual(es)")
        escribir_galeria(destino, list(por_nombre.values()))
        mensajes.append(f"Actualizado: «{NOMBRE_INDICE}» (galería)")

    return mensajes
