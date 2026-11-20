"""Carga del fichero de acciones: src/tareas/docs/acciones.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tareas.errores import AccionNoValida, ConfigError

VERSION_ESPERADA = 1

# Ruta absoluta junto al propio paquete: así funciona desde cualquier carpeta,
# no solo desde la raíz del proyecto (src/tareas/docs/acciones.json).
RUTA_ACCIONES = Path(__file__).resolve().parent / "docs" / "acciones.json"

# Catálogo de tipos: si el tipo no está aquí, la acción no se puede ejecutar.
TIPOS_CONOCIDOS = ("mover", "renombrar", "borrar", "abrir", "transformar",
                   "comprimir", "copiar", "limpiar-usb", "resumir",
                   "renombrar-ia", "clasificar", "estado-pc", "ip-conf")

# Tipos que consultan al proveedor de IA (ProveedorCentro, en ia.py): el
# motor les inyecta el proveedor y, con --simular, no se llama al modelo.
TIPOS_IA = ("resumir", "renombrar-ia", "clasificar")

# Límites del campo «max_caracteres» de las acciones IA (cuánto texto del
# fichero se manda como máximo al modelo).
MAX_CARACTERES_MIN = 500
MAX_CARACTERES_MAX = 50000
MAX_CARACTERES_DEFECTO = 12000

# Campos que puede llevar cualquier acción.
CAMPOS_COMUNES = ("nombre", "descripcion", "tipo", "confirmar")

# Plantillas del tipo «transformar»: cómo se ve el HTML generado (la elegida
# se marca como clase en <body> y el estilo vive en html.py).
PLANTILLAS = ("tecnico", "esquema", "guia")
PLANTILLA_DEFECTO = "tecnico"

# Umbrales del campo «avisos» del tipo «estado-pc»: % a partir del cual el
# informe saca un «AVISO: ...» (medido >= umbral).
AVISOS_CONOCIDOS = ("cpu_pct", "memoria_pct", "disco_pct")

# Campos obligatorios de cada tipo.
CAMPOS_POR_TIPO: dict[str, tuple[str, ...]] = {
    "mover": ("origen", "filtro", "destino"),
    "renombrar": ("filtro", "plantilla"),
    "borrar": ("filtro", "confirmar"),
    "abrir": ("urls",),
    "transformar": ("origen", "filtro", "destino"),
    "comprimir": ("origen", "filtro", "destino"),
    "copiar": ("origen", "filtro", "destino"),
    # Limpieza del registro de Windows (huellas de USB): conserva esos puertos
    # USB00x del JSON y guarda antes una copia .reg en la ruta indicada.
    "limpiar-usb": ("puertos_conservar", "copia_seguridad"),
    # Acción IA: el texto a mandar y las instrucciones van en el JSON. La
    # carpeta origen la pasa la CLI (o el JSON); sin destino, el resumen se
    # escribe junto al fichero.
    "resumir": ("filtro", "instrucciones"),
    # Acción IA que renombra: el modelo propone el nombre (primera línea
    # limpia con a_nombre_seguro) y el motor renombra NUNCA con la respuesta
    # tal cual. Sin destino, renombra en su misma carpeta.
    "renombrar-ia": ("filtro", "instrucciones"),
    # Acción IA que clasifica: el modelo elige UNA categoría de la lista y
    # el fichero se mueve a destino/categoría/ (nada de rutas del modelo).
    "clasificar": ("filtro", "categorias", "destino"),
    # Informe del equipo (CPU, memoria, discos, temperaturas...): solo lectura,
    # sin carpeta ni ficheros (como «limpiar-usb», no lleva campos propios).
    "estado-pc": (),
    # Configuración de red (IP, máscara, puerta, DNS) por adaptador: interactiva
    # (listado + selección + valores en la ejecución), sin campos de fichero
    # (como «estado-pc»): no lleva campos propios.
    "ip-conf": (),
}

# Campos que se reconocen dentro de 'filtro'.
FILTRO_CONOCIDO = ("extensiones", "patron", "mas_antiguo_que_dias", "mayor_que_mb")

# Campos opcionales que el motor SÍ usa en cada tipo (no deben avisar como «de más»).
# Ej.: en «renombrar», «origen» es la carpeta por defecto cuando la CLI no pasa ninguna.
CAMPOS_OPCIONALES_POR_TIPO: dict[str, tuple[str, ...]] = {
    "renombrar": ("origen",),
    # En «borrar», «origen» es la carpeta donde busca los .tmp (el motor la
    # usa igual que en mover/copiar; el menú la propone por defecto).
    "borrar": ("origen",),
    # En las acciones IA, origen/destino son opcionales (destino cae a «junto
    # al fichero») y el tope de caracteres tiene valor por defecto.
    "resumir": ("origen", "destino", "max_caracteres", "categorias"),
    # En «renombrar-ia», sin destino se renombra en la propia carpeta del
    # fichero; «clasificar» exige categorias y destino (no son opcionales).
    "renombrar-ia": ("origen", "destino", "max_caracteres"),
    "clasificar": ("origen", "max_caracteres", "instrucciones"),
    # En «transformar», la plantilla del HTML (tecnico/esquema/guia).
    "transformar": ("plantilla",),
    # En «estado-pc», los umbrales de los avisos (disco/memoria/CPU en %).
    "estado-pc": ("avisos",),
}

# nombre en kebab-case: minúsculas, números, guiones, tildes y espacios. Ej.: abrir-nav
_NOMBRE_KEBAB = re.compile(r"^[a-z0-9áéíóúüñ]+(?:[ -áéíóúüñ][a-z0-9áéíóúüñ]+)*$")

# json.JSONDecodeError explica el fallo en inglés (exc.msg): se traducen los
# textos que puede soltar la librería estándar. Si algún día aparece uno nuevo,
# se muestra tal cual en inglés (nunca un traceback).
_MENSAJES_JSON_ES: dict[str, str] = {
    "Expecting value": "se esperaba un valor",
    "Expecting property name enclosed in double quotes": (
        "se esperaba el nombre de la propiedad entre comillas dobles"
    ),
    "Expecting property name enclosed in single quotes": (
        "se esperaba el nombre de la propiedad entre comillas simples"
    ),
    "Expecting ',' delimiter": "se esperaba una coma (,)",
    "Expecting ':' delimiter": "se esperaban los dos puntos (:)",
    "Unterminated string starting at": "hay una cadena sin cerrar (empezó aquí)",
    "Invalid control character at": "hay un carácter de control no válido",
    "Invalid \\escape": "hay una secuencia de escape no válida",
    "Extra data": "hay datos de más después del JSON",
}


def _mensaje_json(msg: str) -> str:
    """Traduce al español el motivo del fallo que da la librería json."""
    return _MENSAJES_JSON_ES.get(msg, msg)


def cargar(ruta: Path) -> list[dict[str, Any]]:
    """Lee el JSON y devuelve la lista de acciones.

    Lanza ConfigError si la ruta no es un fichero legible, si el JSON no es
    válido (con línea y columna) o si no tiene la estructura esperada.
    """
    if ruta.exists() and not ruta.is_file():
        raise ConfigError(f"{ruta}: no es un fichero, parece una carpeta.")

    # utf-8-sig: igual que utf-8, pero si el fichero empieza por BOM (lo
    # escriben así el Bloc de notas o PowerShell con -Encoding UTF8) lo quita
    # en vez de fallar. Sin BOM funciona exactamente igual.
    try:
        texto = ruta.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise ConfigError(
            f"{ruta}: no se puede leer como UTF-8 (parece estar en otra "
            "codificación, p. ej. ANSI). Vuelve a guardarlo como UTF-8."
        ) from None
    except OSError as exc:
        raise ConfigError(f"No se pudo leer {ruta}: {exc}") from exc

    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"JSON inválido en {ruta} (línea {exc.lineno}, columna {exc.colno}): "
            f"{_mensaje_json(exc.msg)}"
        ) from exc

    if not isinstance(datos, dict):
        raise ConfigError(
            f"{ruta}: se esperaba un objeto JSON con 'version' y 'acciones'."
        )

    if datos.get("version") != VERSION_ESPERADA:
        raise ConfigError(
            f"{ruta}: 'version' debe ser {VERSION_ESPERADA} "
            f"(encontrado: {datos.get('version')!r})."
        )

    acciones = datos.get("acciones")
    if not isinstance(acciones, list):
        raise ConfigError(f"{ruta}: 'acciones' debe ser una lista.")

    return acciones


def validar_acciones(acciones: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Valida todas las acciones. Devuelve (errores, avisos).

    Cada error es un texto listo para imprimir. Usa validar() por acción.
    """
    errores: list[str] = []
    avisos: list[str] = []

    if not acciones:
        avisos.append("No hay ninguna acción definida.")
        return errores, avisos

    nombres_vistos: set[str] = set()
    for indice, accion in enumerate(acciones, start=1):
        try:
            avisos.extend(validar(accion, indice, nombres_vistos))
        except AccionNoValida as exc:
            errores.append(str(exc))

    return errores, avisos


def validar_ia(accion: dict[str, Any]) -> list[str]:
    """Valida los campos de las acciones con IA (TIPOS_IA). Devuelve avisos.

    «instrucciones» es obligatoria en «resumir» y «renombrar-ia» (texto no
    vacío; en «clasificar» es opcional, porque el mensaje lo genera la
    propia acción). «max_caracteres» es un entero entre MAX_CARACTERES_MIN
    y MAX_CARACTERES_MAX (si no está, vale MAX_CARACTERES_DEFECTO) y
    «categorias», si está, una lista no vacía de textos no vacíos.
    """
    tipo = accion.get("tipo")
    instrucciones = accion.get("instrucciones")
    if instrucciones is not None and (
        not isinstance(instrucciones, str) or not instrucciones.strip()
    ):
        raise AccionNoValida(
            accion,
            "instrucciones",
            "si está, tiene que ser un texto no vacío.",
        )
    if tipo in ("resumir", "renombrar-ia") and instrucciones is None:
        raise AccionNoValida(
            accion,
            "instrucciones",
            "falta «instrucciones» (lo que le pedimos al modelo, texto no vacío).",
        )

    if "max_caracteres" in accion:
        tope = accion["max_caracteres"]
        if (
            isinstance(tope, bool)
            or not isinstance(tope, int)
            or not (MAX_CARACTERES_MIN <= tope <= MAX_CARACTERES_MAX)
        ):
            raise AccionNoValida(
                accion,
                "max_caracteres",
                f"debe ser un entero entre {MAX_CARACTERES_MIN} y "
                f"{MAX_CARACTERES_MAX} (encontrado: {tope!r}).",
            )

    if "categorias" in accion:
        categorias = accion["categorias"]
        if not isinstance(categorias, list) or not categorias or not all(
            isinstance(c, str) and c.strip() for c in categorias
        ):
            raise AccionNoValida(
                accion,
                "categorias",
                "debe ser una lista no vacía de nombres de carpeta (textos no vacíos).",
            )

    return []


def validar(accion: Any, indice: int, nombres_vistos: set[str]) -> list[str]:
    """Valida una acción. Devuelve los avisos.

    Lanza AccionNoValida en el primer error que encuentre.
    """
    avisos: list[str] = []

    if not isinstance(accion, dict):
        raise AccionNoValida(
            {"nombre": f"acción {indice}"},
            "estructura",
            "debe ser un objeto JSON con sus campos.",
        )

    nombre = accion.get("nombre")
    etiqueta = f"acción {indice}" + (f" «{nombre}»" if isinstance(nombre, str) else "")

    # nombre
    if not isinstance(nombre, str) or not nombre:
        raise AccionNoValida(accion, "nombre", "falta el campo «nombre».")
    if not _NOMBRE_KEBAB.match(nombre):
        raise AccionNoValida(
            accion, "nombre", "debe ir en minúsculas con guiones (kebab-case)."
        )
    if nombre in nombres_vistos:
        raise AccionNoValida(
            accion, "nombre", "duplicado; cada acción debe ser única."
        )
    nombres_vistos.add(nombre)

    # descripcion
    descripcion = accion.get("descripcion")
    if not isinstance(descripcion, str) or not descripcion.strip():
        raise AccionNoValida(
            accion, "descripcion", "falta «descripcion» (un texto no vacío)."
        )

    # tipo
    tipo = accion.get("tipo")
    if not isinstance(tipo, str) or not tipo:
        raise AccionNoValida(accion, "tipo", "falta el campo «tipo».")
    if tipo not in TIPOS_CONOCIDOS:
        raise AccionNoValida(
            accion,
            "tipo",
            f"tipo «{tipo}» desconocido. Válidos: {', '.join(TIPOS_CONOCIDOS)}.",
        )

    # confirmar, si está, tiene que ser booleano
    if "confirmar" in accion and not isinstance(accion["confirmar"], bool):
        raise AccionNoValida(accion, "confirmar", "debe ser true o false.")

    # campos que el tipo necesita sí o sí
    for campo in CAMPOS_POR_TIPO[tipo]:
        if campo not in accion:
            raise AccionNoValida(
                accion, campo, f"al tipo «{tipo}» le falta el campo «{campo}»."
            )

    # urls (solo tipo abrir)
    if tipo == "abrir" and "urls" in accion:
        urls = accion["urls"]
        if not isinstance(urls, list) or not urls:
            raise AccionNoValida(
                accion, "urls", "debe ser una lista con al menos una dirección."
            )
        for indice_url, url in enumerate(urls, start=1):
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                raise AccionNoValida(
                    accion,
                    "urls",
                    f"la URL {indice_url} no empieza por http:// o https://: {url!r}.",
                )

    # limpiar-usb: puertos_conservar (lista de nombres) y copia_seguridad (ruta)
    if tipo == "limpiar-usb":
        conservar = accion.get("puertos_conservar")
        if not isinstance(conservar, list) or not conservar or not all(
            isinstance(p, str) and p.strip() for p in conservar
        ):
            raise AccionNoValida(
                accion,
                "puertos_conservar",
                "debe ser una lista de nombres de puerto no vacía (ej.: [\"USB001\", \"USB002\"]).",
            )
        copia = accion.get("copia_seguridad")
        if not isinstance(copia, str) or not copia.strip():
            raise AccionNoValida(
                accion,
                "copia_seguridad",
                "falta la ruta del .reg de copia de seguridad (texto no vacío).",
            )

    # transformar: la plantilla del HTML, si viene, tiene que existir
    if tipo == "transformar" and "plantilla" in accion:
        plantilla = accion["plantilla"]
        if not isinstance(plantilla, str) or plantilla not in PLANTILLAS:
            raise AccionNoValida(
                accion,
                "plantilla",
                f"debe ser una de: {', '.join(PLANTILLAS)} "
                f"(encontrado: {plantilla!r}).",
            )

    # estado-pc: los umbrales de «avisos», si vienen, tienen que ser
    # claves conocidas con un entero del 1 al 100 (bool no vale).
    if tipo == "estado-pc" and "avisos" in accion:
        umbrales = accion["avisos"]
        if not isinstance(umbrales, dict):
            raise AccionNoValida(
                accion,
                "avisos",
                "debe ser un objeto con umbrales en % "
                f"(claves: {', '.join(AVISOS_CONOCIDOS)}).",
            )
        for clave, valor in umbrales.items():
            if clave not in AVISOS_CONOCIDOS:
                raise AccionNoValida(
                    accion,
                    "avisos",
                    f"clave «{clave}» desconocida; válidas: "
                    f"{', '.join(AVISOS_CONOCIDOS)}.",
                )
            if isinstance(valor, bool) or not isinstance(valor, int) or not (
                1 <= valor <= 100
            ):
                raise AccionNoValida(
                    accion,
                    "avisos",
                    f"«{clave}» debe ser un entero del 1 al 100 "
                    f"(encontrado: {valor!r}).",
                )

    # Acciones con IA: instrucciones, max_caracteres y categorias
    if tipo in TIPOS_IA:
        avisos.extend(validar_ia(accion))

    # filtro, si está, tiene forma de comprobar
    if "filtro" in accion:
        filtro = accion["filtro"]
        if not isinstance(filtro, dict):
            raise AccionNoValida(accion, "filtro", "debe ser un objeto JSON.")
        if "extensiones" in filtro:
            if not isinstance(filtro["extensiones"], list):
                raise AccionNoValida(
                    accion, "filtro.extensiones", "debe ser una lista."
                )
            for ext in filtro["extensiones"]:
                if not isinstance(ext, str) or not ext.startswith("."):
                    raise AccionNoValida(
                        accion,
                        "filtro.extensiones",
                        f"cada extensión debe empezar por «.» (encontrado: {ext!r}).",
                    )
        # El filtro tiene que servir para algo: al menos un criterio reconocido.
        # (Se puede filtrar solo por antigüedad, sin «extensiones» ni «patron».)
        if not any(clave in filtro for clave in FILTRO_CONOCIDO):
            raise AccionNoValida(
                accion,
                "filtro",
                "necesita al menos uno de: «extensiones», «patron», "
                "«mas_antiguo_que_dias» o «mayor_que_mb».",
            )
        if tipo == "borrar" and "patron" not in filtro:
            raise AccionNoValida(
                accion, "filtro", f"al tipo «borrar» le falta «filtro.patron»."
            )
        if "mas_antiguo_que_dias" in filtro:
            dias = filtro["mas_antiguo_que_dias"]
            if isinstance(dias, bool) or not isinstance(dias, int) or dias <= 0:
                raise AccionNoValida(
                    accion,
                    "filtro.mas_antiguo_que_dias",
                    f"debe ser un número de días mayor que 0 (encontrado: {dias!r}).",
                )
        if "mayor_que_mb" in filtro:
            mb = filtro["mayor_que_mb"]
            if isinstance(mb, bool) or not isinstance(mb, (int, float)) or mb <= 0:
                raise AccionNoValida(
                    accion,
                    "filtro.mayor_que_mb",
                    f"debe ser un número de MB mayor que 0 (encontrado: {mb!r}).",
                )
        # una errata en el filtro (ej.: mas_antiguio_que_dias) se avisa
        desconocidos = sorted(set(filtro) - set(FILTRO_CONOCIDO))
        if desconocidos:
            avisos.append(
                f"{etiqueta}: campos en 'filtro' que no se reconocen: "
                f"{', '.join(desconocidos)}."
            )

    # campos de texto que no pueden estar vacíos
    for campo in ("origen", "destino", "plantilla"):
        if campo in accion and (
            not isinstance(accion[campo], str) or not accion[campo].strip()
        ):
            raise AccionNoValida(
                accion, campo, f"«{campo}» debe ser un texto no vacío."
            )

    # campos que no le tocan a este tipo -> aviso, no error
    de_mas = sorted(
        set(accion)
        - set(CAMPOS_COMUNES)
        - set(CAMPOS_POR_TIPO[tipo])
        - set(CAMPOS_OPCIONALES_POR_TIPO.get(tipo, ()))
    )
    if de_mas:
        avisos.append(
            f"{etiqueta}: campos que no le tocan a «{tipo}»: {', '.join(de_mas)}."
        )

    return avisos
