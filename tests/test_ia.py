"""Tests de la capa IA (ia.py) SIN red (sesión 4).

Ningún test conecta con un servidor — ni siquiera con localhost: las
respuestas HTTP se fabrican con httpx.Response y el httpx.post real se
sustituye con monkeypatch. Se prueba: desde_entorno (config en el
entorno), el reintento del 429, la traducción de cada fallo a
IANoDisponible con mensaje humano y que la clave NUNCA aparece.
"""

from __future__ import annotations

import httpx
import pytest

from tareas import ia
from tareas.errores import IANoDisponible
from tareas.ia import ProveedorCentro, Respuesta

CLAVE_PRUEBA = "SECRETA-AUDITORIA-NO-IMPRIMIR"  # la de la fixture env_con_ia


def _respuesta(status: int, cuerpo: dict | None = None) -> httpx.Response:
    """Una respuesta HTTP fabricada, sin red."""
    return httpx.Response(
        status,
        json=cuerpo if cuerpo is not None else {},
        request=httpx.Request("POST", "http://prueba.local/v1/chat/completions"),
    )


def _cuerpo_ok(texto: str = "OK") -> dict:
    """El JSON que devuelve un servidor compatible con la API de OpenAI."""
    return {
        "choices": [{"message": {"content": texto}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3},
    }


def _parchear_post(monkeypatch: pytest.MonkeyPatch, respuestas: list[httpx.Response]) -> list[int]:
    """Sustituye httpx.post por uno que desencola respuestas EN ORDEN.

    Devuelve la lista de llamadas, para contar los reintentos del 429.
    """
    llamadas: list[int] = []

    def _falso(url: str, **_kwargs: object) -> httpx.Response:
        llamadas.append(1)
        return respuestas.pop(0)

    monkeypatch.setattr(ia.httpx, "post", _falso)
    return llamadas


# --- Respuesta --------------------------------------------------------------


def test_resumen_formatea_tokens_y_segundos() -> None:
    respuesta = Respuesta("hola", 12, 3, 0.27)
    assert respuesta.resumen() == "12+3 tokens · 0.3 s"


# --- desde_entorno: la config vive en el entorno, no en el código -----------


def test_desde_entorno_sin_config_da_4_con_mensaje_humano(env_sin_ia) -> None:
    """Sin URL ni clave: IANoDisponible (código 4), en español, sin traceback."""
    with pytest.raises(IANoDisponible) as error:
        ProveedorCentro.desde_entorno()
    assert "Faltan" in str(error.value)
    assert error.value.codigo_salida == 4


def test_desde_entorno_con_config_monta_el_proveedor(env_con_ia) -> None:
    """Con las variables del entorno, el proveedor sale montado (sin llamar a nadie)."""
    proveedor = ProveedorCentro.desde_entorno()
    assert proveedor.url == "http://prueba.local/v1"
    assert proveedor.modelo == "modelo-de-prueba"


# --- la clave, jamás impresa -------------------------------------------------


def test_401_explica_la_clave_sin_ensenarla(env_con_ia, monkeypatch: pytest.MonkeyPatch) -> None:
    """Con una clave rechazada (401) el mensaje ayuda, pero NO enseña la clave."""
    _parchear_post(monkeypatch, [_respuesta(401)])
    proveedor = ProveedorCentro.desde_entorno()
    with pytest.raises(IANoDisponible) as error:
        proveedor.completar("sistema", "usuario")
    assert "clave no es válida" in str(error.value)
    assert CLAVE_PRUEBA not in f"{proveedor!r} {proveedor} {error.value}"


# --- 429: reintento con espera ----------------------------------------------


def test_429_reintenta_hasta_avisar(env_con_ia, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tres 429 seguidos: agota los INTENTOS_429 y avisa; la espera no nos la comemos."""
    monkeypatch.setattr(ia, "ESPERA_429", 0)  # sin esperar 60 s en los tests
    llamadas = _parchear_post(
        monkeypatch, [_respuesta(429), _respuesta(429), _respuesta(429)]
    )
    proveedor = ProveedorCentro.desde_entorno()
    with pytest.raises(IANoDisponible) as error:
        proveedor.completar("sistema", "usuario")
    assert "429" in str(error.value)
    assert len(llamadas) == ia.INTENTOS_429


def test_429_reintenta_y_la_segunda_va_bien(env_con_ia, monkeypatch: pytest.MonkeyPatch) -> None:
    """El servidor se desatascó al segundo intento: sale bien y cuenta los tokens."""
    monkeypatch.setattr(ia, "ESPERA_429", 0)
    llamadas = _parchear_post(monkeypatch, [_respuesta(429), _respuesta(200, _cuerpo_ok())])
    proveedor = ProveedorCentro.desde_entorno()
    respuesta = proveedor.completar("sistema", "usuario")
    assert respuesta.texto == "OK"
    assert respuesta.tokens_entrada == 12 and respuesta.tokens_salida == 3
    assert len(llamadas) == 2


# --- traducción de fallos raros a IANoDisponible -----------------------------


def test_formato_raro_del_servidor_da_4(env_con_ia, monkeypatch: pytest.MonkeyPatch) -> None:
    """Un 200 con un JSON que no es de OpenAI: mensaje humano, no KeyError."""
    _parchear_post(monkeypatch, [_respuesta(200, {"otro": "formato"})])
    proveedor = ProveedorCentro.desde_entorno()
    with pytest.raises(IANoDisponible) as error:
        proveedor.completar("sistema", "usuario")
    assert "formato esperado" in str(error.value)


def test_url_mal_escrita_da_4(env_con_ia, monkeypatch: pytest.MonkeyPatch) -> None:
    """Una URL sin esquema: InvalidURL se traduce a un mensaje en español."""
    monkeypatch.setenv("CENTRO_IA_URL", "no-es-una-url")

    def _falso(_url: str, **_kwargs: object) -> httpx.Response:
        raise httpx.InvalidURL("no tiene esquema")

    monkeypatch.setattr(ia.httpx, "post", _falso)
    proveedor = ProveedorCentro.desde_entorno()
    with pytest.raises(IANoDisponible) as error:
        proveedor.completar("sistema", "usuario")
    assert "no es válida" in str(error.value)


def test_proveedor_centro_no_llega_a_una_url_muerta_da_4(
    env_con_ia, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Con la URL apuntando a un puerto muerto (127.0.0.1:9) no hay red:
    httpx ConnectError → IANoDisponible con «No llego» (código 4)."""
    monkeypatch.setenv("CENTRO_IA_URL", "http://127.0.0.1:9/v1")

    def _falso(_url: str, **_kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("no hay servidor disponible")

    monkeypatch.setattr(ia.httpx, "post", _falso)
    proveedor = ProveedorCentro.desde_entorno()
    with pytest.raises(IANoDisponible) as error:
        proveedor.completar("sistema", "usuario")
    assert "No llego" in str(error.value)
    assert error.value.codigo_salida == 4


def test_mensaje_de_estado_500_y_404() -> None:
    """La tabla de estados: 5xx es «inténtalo más tarde» y 404 apunta al modelo."""
    assert "fallo interno" in ia.ProveedorCentro._mensaje_estado(503)
    assert "CENTRO_IA_MODELO" in ia.ProveedorCentro._mensaje_estado(404)
