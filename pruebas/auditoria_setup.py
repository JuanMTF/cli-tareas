# Prepara el sandbox de auditoría del Paso 8 en ~/pruebas-tareas/auditoria.
# Solo toca ~/pruebas-tareas: borra y recrea la carpeta auditoria.
# El destino NO se crea: lo tiene que crear la acción de verdad (auditoría).
#
# Uso: uv run python pruebas/auditoria_setup.py
# (auditoria.ps1 lo llama él solo; también se puede ejecutar a mano)
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

raiz = Path.home() / "pruebas-tareas" / "auditoria"
origen_mover = raiz / "origen-mover"
origen_orden = raiz / "origen-orden"
origen_ren = raiz / "origen-ren"
origen_tmp = raiz / "origen-tmp"
destino = raiz / "destino"

if raiz.exists():
    shutil.rmtree(raiz)

for carpeta in (origen_mover, origen_orden, origen_ren, origen_tmp):
    carpeta.mkdir(parents=True)

# Nombres con tildes, eñes y espacios
(origen_mover / "cumpleaños 2.png").write_text("png", encoding="utf-8")
(origen_mover / "apuntes de redes.docx").write_text("docx", encoding="utf-8")
(origen_mover / "FOTO1.JPG").write_text("jpg", encoding="utf-8")

# PDF para ordenar-descargas (la acción del JSON por defecto)
(origen_orden / "doc-1.pdf").write_text("pdf", encoding="utf-8")
(origen_orden / "doc-2.pdf").write_text("pdf", encoding="utf-8")

# Dos PNG con la MISMA fecha de modificación: colisión forzada al renombrar
(origen_ren / "foto-a.png").write_text("a", encoding="utf-8")
(origen_ren / "foto-b.png").write_text("b", encoding="utf-8")
marca = (datetime.now() - timedelta(days=1)).timestamp()
os.utime(origen_ren / "foto-a.png", (marca, marca))
os.utime(origen_ren / "foto-b.png", (marca, marca))

# Un .tmp viejo para probar borrar sin --si
(origen_tmp / "viejo.tmp").write_text("tmp", encoding="utf-8")
marca_tmp = (datetime.now() - timedelta(days=60)).timestamp()
os.utime(origen_tmp / "viejo.tmp", (marca_tmp, marca_tmp))

# Config propio de la auditoría (utf-8 sin BOM): demuestra también --config
acciones = {
    "version": 1,
    "acciones": [
        {
            "nombre": "mover-png",
            "descripcion": "Auditoría: mueve los .png (nombres con tildes y espacios).",
            "tipo": "mover",
            "origen": str(origen_mover),
            "filtro": {"extensiones": [".png"]},
            "destino": str(destino),
        },
        {
            "nombre": "mover-jpg",
            "descripcion": "Auditoría: mueve los .jpg (prueba de extensión en MAYÚSCULAS).",
            "tipo": "mover",
            "origen": str(origen_mover),
            "filtro": {"extensiones": [".jpg"]},
            "destino": str(destino),
        },
        {
            "nombre": "copiar-docx",
            "descripcion": "Auditoría: copia el .docx sin borrar el original.",
            "tipo": "copiar",
            "origen": str(origen_mover),
            "filtro": {"extensiones": [".docx"]},
            "destino": str(destino),
        },
        {
            "nombre": "ren-fecha",
            "descripcion": "Auditoría: renombra .png solo con la fecha (sin {n}) para forzar colisión.",
            "tipo": "renombrar",
            "origen": str(origen_ren),
            "filtro": {"extensiones": [".png"]},
            "plantilla": "{fecha:%Y-%m-%d}{ext}",
        },
    ],
}
ruta_json = raiz / "mis-acciones.json"
ruta_json.write_text(
    json.dumps(acciones, ensure_ascii=False, indent=2), encoding="utf-8"
)

print("sandbox listo en", raiz)
print("destino creado de antemano?", destino.exists())
