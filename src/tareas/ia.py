"""Capa de IA: proveedores de chat (API de OpenAI) y la respuesta medida.

Estructura del código de referencia del profesor; los fallos raros (JSON con
otro formato, CA que no existe, URL mal escrita) se traducen a
IANoDisponible con mensaje en español: nada de tracebacks para el usuario.
La clave del centro nunca se imprime ni se escribe en fichero.
"""

from __future__ import annotations

import os
import ssl
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import find_dotenv, load_dotenv

from tareas.errores import IANoDisponible

# Variables de entorno (el .env se lee con python-dotenv antes de mirarlas).
VAR_URL = "CENTRO_IA_URL"
VAR_CLAVE = "CENTRO_IA_KEY"
VAR_MODELO = "CENTRO_IA_MODELO"
VAR_CA = "CENTRO_IA_CA"

# Modelo fijo del servidor del centro (nombre dado por el profesor):
# «centro/qwen3.8-flash-next». El .env solo necesita URL y KEY; si algún día
# cambia el modelo, se puede marcar igualmente en .env con CENTRO_IA_MODELO.
MODELO_POR_DEFECTO = "centro/qwen3.8-flash-next"

# httpx agota por defecto todo a 5 s: para un modelo que está generando
# texto hace falta margen al leer (del profesor: Timeout(60, connect=5)).
# Los modelos gratuitos van a veces cargados y tardan más de un minuto en
# contestar: la lectura admite 120 s (la conexión sigue a 5).
TIEMPO_ESPERA = httpx.Timeout(120, connect=5)

# Con los modelos gratuitos el servidor a veces responde 429 (demasiadas
# peticiones: su cola está saturada). Como la CLI manda las peticiones de
# una en una, lo que satura no somos nosotros: se espera un minuto y se
# reintenta antes de rendirse y avisar.
ESPERA_429 = 60  # segundos entre reintento y reintento
INTENTOS_429 = 3  # intentos totales (el normal + 2 con espera)

# Pregunta mínima de «comprobar-ia»: el sistema pide contestación de 1 palabra
# y max_tokens=5 acota el gasto del centro.
SISTEMA_PRUEBA = "Eres un asistente de pruebas: contesta MUY corto, una sola palabra."


@dataclass
class Respuesta:
    """Lo que contesta el modelo: el texto, lo que costó y cuánto tardó."""

    texto: str
    tokens_entrada: int
    tokens_salida: int
    segundos: float

    def resumen(self) -> str:
        """El gasto y el tiempo en una línea: «12+3 tokens · 0.3 s»."""
        return f"{self.tokens_entrada}+{self.tokens_salida} tokens · {self.segundos:.1f} s"


class ProveedorIA(ABC):
    """Lo único que el resto del programa sabe de la IA: le das texto y te devuelve texto."""

    @abstractmethod
    def completar(self, sistema: str, usuario: str, max_tokens: int = 800) -> Respuesta: ...


class ProveedorCentro(ProveedorIA):
    """Un servidor compatible con la API de OpenAI: el del centro (o cualquier otro)."""

    def __init__(
        self,
        url: str,
        clave: str,
        modelo: str = MODELO_POR_DEFECTO,
        ca: str | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.modelo = modelo
        if not self.modelo:
            raise IANoDisponible(
                f"Falta {VAR_MODELO}: ponla en .env (mira .env.example), "
                "o escribe el modelo fijo del centro en MODELO_POR_DEFECTO (ia.py)."
            )
        self.ca = ca
        self._clave = clave  # «_»: es privada; nunca se imprime ni se escribe
        self._tls = self._contexto_tls(ca)

    @staticmethod
    def desde_entorno() -> ProveedorCentro:
        """Fábrica: lee .env (si lo hay) y las variables de entorno."""
        load_dotenv(find_dotenv(usecwd=True))  # no pisa las variables que ya existen
        url = os.environ.get(VAR_URL)
        clave = os.environ.get(VAR_CLAVE)
        if not url or not clave:
            raise IANoDisponible(
                f"Faltan {VAR_URL} o {VAR_CLAVE}: ponlas en .env (mira .env.example)"
            )
        modelo = os.environ.get(VAR_MODELO, MODELO_POR_DEFECTO)
        return ProveedorCentro(url, clave, modelo, os.environ.get(VAR_CA))

    # ------------------------------------------------------------------ #
    # La llamada al servidor
    # ------------------------------------------------------------------ #
    def completar(self, sistema: str, usuario: str, max_tokens: int = 800) -> Respuesta:
        """Pregunta al modelo y devuelve Respuesta; cualquier fallo → IANoDisponible."""
        cuerpo = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        intento = 0
        while True:
            intento += 1
            # El reloj de la Respuesta arranca en cada intento: el tiempo de
            # espera del 429 no es tiempo del modelo.
            inicio = time.perf_counter()
            try:
                respuesta_http = httpx.post(
                    f"{self.url}/chat/completions",
                    json=cuerpo,
                    headers={"Authorization": f"Bearer {self._clave}"},
                    timeout=TIEMPO_ESPERA,
                    verify=self._tls,
                )
            except httpx.InvalidURL as exc:
                raise IANoDisponible(
                    f"La dirección del servidor no es válida "
                    f"({VAR_URL}: {self.url}): debe empezar por http:// o https://"
                ) from exc
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                # El fallo de certificado llega DENTRO de ConnectError: se mira
                # la causa real (ssl.SSLCertVerificationError) por si es eso.
                cadena = " | ".join(str(nivel) for nivel in (exc, exc.__cause__) if nivel)
                if "CERTIFICATE" in cadena.upper():
                    raise IANoDisponible(
                        "El certificado del servidor no lo valida tu CA: revisa "
                        f"{VAR_CA} en .env (¿es el .crt correcto y vigente?)"
                    ) from exc
                raise IANoDisponible(
                    f"No llego al servidor de IA ({self.url}): ¿estás en la red del centro?"
                ) from exc
            except httpx.TimeoutException as exc:
                raise IANoDisponible("El servidor de IA no ha respondido a tiempo") from exc
            except httpx.UnsupportedProtocol as exc:
                raise IANoDisponible(
                    f"El servidor no usa un protocolo válido: revisa {VAR_URL}"
                ) from exc
            except httpx.HTTPError as exc:  # ReadError, WriteError, ProxyError...
                raise IANoDisponible(
                    f"Se cortó la conexión con el servidor de IA: {exc}"
                ) from exc

            try:
                respuesta_http.raise_for_status()
            except httpx.HTTPStatusError as exc:
                # 429: demasiadas peticiones. Se espera un minuto y se
                # reintenta (INTENTOS_429 veces en total) antes de avisar.
                if (
                    respuesta_http.status_code == 429
                    and intento < INTENTOS_429
                ):
                    time.sleep(ESPERA_429)
                    continue
                raise IANoDisponible(
                    self._mensaje_estado(respuesta_http.status_code)
                ) from exc
            break

        texto, uso = self._leer_json(respuesta_http)
        return Respuesta(
            texto.strip(),
            uso.get("prompt_tokens", 0),
            uso.get("completion_tokens", 0),
            time.perf_counter() - inicio,
        )

    # ------------------------------------------------------------------ #
    # Ayudas privadas
    # ------------------------------------------------------------------ #
    @staticmethod
    def _contexto_tls(ca: str | None) -> ssl.SSLContext:
        """Confianza del sistema y, si hay, la CA del centro (del profesor).

        `create_default_context()` + `load_verify_locations()` equivale a
        `create_default_context(cafile=...)`, pero avisa bien si el fichero
        de la CA no existe o no se puede cargar (sin traceback).
        """
        contexto = ssl.create_default_context()
        if ca:
            ruta = Path(ca).expanduser()
            if not ruta.is_file():
                raise IANoDisponible(
                    f"No encuentro el certificado del centro en «{ca}»: "
                    f"revisa {VAR_CA} en .env"
                )
            try:
                contexto.load_verify_locations(str(ruta))
            except (OSError, ssl.SSLError) as exc:
                raise IANoDisponible(
                    f"No puedo cargar el certificado del centro «{ca}»: "
                    f"revisa {VAR_CA} en .env ({exc})"
                ) from exc
        return contexto

    @staticmethod
    def _leer_json(respuesta_http: httpx.Response) -> tuple[str, dict]:
        """Saca el texto y el uso del JSON de OpenAI; otro formato → error."""
        try:
            datos = respuesta_http.json()
            texto = datos["choices"][0]["message"]["content"] or ""
            uso = datos.get("usage") or {}
        except (KeyError, IndexError, TypeError, AttributeError, ValueError) as exc:
            raise IANoDisponible(
                f"La respuesta del servidor no tiene el formato esperado "
                f"(API de OpenAI): revisa {VAR_URL}"
            ) from exc
        return str(texto), uso

    @staticmethod
    def _mensaje_estado(codigo: int) -> str:
        """(del profesor) cada estado con su motivo; el resto, «algo ha fallado»."""
        motivo = {
            401: "la clave no es válida, revisa CENTRO_IA_KEY",
            403: "sin permiso, revisa CENTRO_IA_KEY",
            404: "no existe el modelo o la ruta, revisa CENTRO_IA_MODELO y CENTRO_IA_URL",
            429: "demasiadas peticiones, espera un minuto",
        }
        if codigo >= 500:
            return (
                f"El servidor de IA responde {codigo}: fallo interno, "
                "inténtalo más tarde"
            )
        return f"El servidor de IA responde {codigo}: {motivo.get(codigo, 'algo ha fallado')}"
