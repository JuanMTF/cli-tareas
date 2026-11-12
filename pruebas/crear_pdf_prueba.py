"""Crea un PDF real (1 página) con pymupdf para la batería de pruebas.

Uso: uv run python pruebas/crear_pdf_prueba.py RUTA.pdf

Es lo único que permite auditar «transformar-pdf-html» de verdad: los
«PDF» de texto del sandbox no los acepta ningún conversor.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf


def crear(ruta: Path) -> None:
    """Escribe un PDF mínimo de una página con título y dos líneas."""
    with pymupdf.open() as documento:
        pagina = documento.new_page()
        pagina.insert_text((72, 90), "Manual de prueba de la bateria", fontsize=18)
        pagina.insert_text(
            (72, 130),
            "PDF generado por pruebas/crear_pdf_prueba.py para auditar",
            fontsize=11,
        )
        pagina.insert_text(
            (72, 150),
            "la conversion real de transformar-pdf-html en cliWork.",
            fontsize=11,
        )
        ruta.parent.mkdir(parents=True, exist_ok=True)
        documento.save(str(ruta))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: uv run python pruebas/crear_pdf_prueba.py RUTA.pdf", file=sys.stderr)
        raise SystemExit(2)
    crear(Path(sys.argv[1]))
