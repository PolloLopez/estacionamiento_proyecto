# app_estacionamiento/services/sia_verificacion.py
"""
Servicio de verificación del Símbolo Internacional de Acceso (SIA) de ANDIS.

Encapsula toda la interacción con el servicio oficial.
Si ANDIS cambia el formato, solo hay que actualizar _parsear_respuesta().

Estados posibles del resultado:
  VALIDO_PATENTE_COINCIDENTE  — SIA válido, vigente, patente coincide → aplicar exención
  PATENTE_NO_COINCIDE         — SIA válido pero la patente del SIA es distinta
  SIA_VENCIDO                 — SIA respondió correctamente pero está vencido
  SIA_SIN_DOMINIO             — ANDIS respondió pero no hay patente/dominio en el SIA
  QR_URL_INVALIDA             — La URL no es del dominio oficial de ANDIS
  ANDIS_NO_DISPONIBLE         — Timeout o error de conexión
  ANDIS_ERROR                 — ANDIS devolvió un error HTTP (4xx, 5xx)
  RESPUESTA_INVALIDA          — ANDIS respondió pero el formato no es reconocible
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from urllib.parse import urlparse, parse_qs

import requests

# URL oficial del servicio ANDIS. Si cambia, actualizar solo estas constantes.
_ANDIS_DOMINIO = "apps.andis.gob.ar"
_ANDIS_PATH    = "/qr-simbolo"
_TIMEOUT_SEG   = 8

ESTADOS_SIA = (
    "VALIDO_PATENTE_COINCIDENTE",
    "PATENTE_NO_COINCIDE",
    "SIA_VENCIDO",
    "SIA_SIN_DOMINIO",
    "QR_URL_INVALIDA",
    "ANDIS_NO_DISPONIBLE",
    "ANDIS_ERROR",
    "RESPUESTA_INVALIDA",
)


@dataclass
class ResultadoSia:
    estado: str                        # uno de ESTADOS_SIA
    sia_code: str          = ""        # el code extraído del QR
    sia_url: str           = ""        # URL completa del QR (para auditoría)
    patente_sia: str       = ""        # dominio registrado en ANDIS (normalizado)
    vencimiento: Optional[date] = None # fecha de vencimiento del SIA
    nci: str               = ""        # número de caso ANDIS
    titular: str           = ""        # "Nombre Apellido" del titular
    error_tecnico: str     = ""        # descripción interna (solo para logs, nunca al inspector)

    @property
    def es_valido(self) -> bool:
        return self.estado == "VALIDO_PATENTE_COINCIDENTE"


def normalizar_patente(patente: str) -> str:
    """Normaliza una patente: mayúsculas, sin espacios ni guiones."""
    return re.sub(r"[\s\-]", "", patente or "").upper()


def validar_url_andis(qr_url: str) -> tuple:
    """
    Valida que la URL sea del servicio oficial de ANDIS.
    Devuelve (es_valida: bool, code: str).
    Solo acepta: https://apps.andis.gob.ar/qr-simbolo?code=...
    """
    try:
        parsed = urlparse(qr_url)
    except Exception:
        return False, ""

    if parsed.scheme != "https":
        return False, ""
    if parsed.netloc != _ANDIS_DOMINIO:
        return False, ""
    if parsed.path != _ANDIS_PATH:
        return False, ""

    params = parse_qs(parsed.query)
    codes  = params.get("code", [])
    if not codes or not codes[0].strip():
        return False, ""

    return True, codes[0].strip()


def _parsear_respuesta(html: str) -> dict:
    """
    Extrae los campos del HTML de respuesta de ANDIS.
    Usa regex tolerante para no romperse con cambios menores de formato.
    Si ANDIS cambia el HTML, actualizar solo esta función.
    """
    def extraer(campo: str) -> str:
        patrones = [
            # "Campo: valor" en texto plano o dentro de HTML
            rf"{re.escape(campo)}\s*[:\-]\s*([^\n<]{{1,100}})",
            # "Campo</td><td>valor" en tabla HTML
            rf"{re.escape(campo)}</\w+>\s*<\w+[^>]*>\s*([^<]{{1,100}})",
        ]
        for patron in patrones:
            m = re.search(patron, html, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""

    return {
        "nci":        extraer("NCI"),
        "nombre":     extraer("Nombre"),
        "apellido":   extraer("Apellido"),
        # "Dominio" es el campo principal; "Patente" como alternativa
        "dominio":    extraer("Dominio") or extraer("Patente"),
        # "Vencimiento" del dominio; "Expira En" como alternativa
        "vencimiento": extraer("Vencimiento") or extraer("Expira En"),
    }


def _parsear_fecha(texto: str) -> Optional[date]:
    """Intenta parsear una fecha en formatos ISO o DD/MM/YYYY."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def verificar_sia(qr_url: str, patente_inspector: str) -> ResultadoSia:
    """
    Verifica un SIA de ANDIS contra la patente ingresada por el inspector.
    No lanza excepciones: siempre devuelve un ResultadoSia con estado claro.

    Si ANDIS no está disponible, el resultado deja constancia de que el SIA
    fue presentado pero no pudo verificarse — nunca dice "SIA falso".
    """
    # 1. Validar que la URL sea del dominio oficial de ANDIS (previene SSRF)
    es_valida, code = validar_url_andis(qr_url)
    if not es_valida:
        return ResultadoSia(
            estado="QR_URL_INVALIDA",
            sia_url=qr_url,
            error_tecnico=f"URL rechazada por no cumplir el formato oficial: {qr_url}",
        )

    # 2. Consultar el servicio de ANDIS
    try:
        resp = requests.get(qr_url, timeout=_TIMEOUT_SEG)
    except requests.exceptions.Timeout:
        return ResultadoSia(
            estado="ANDIS_NO_DISPONIBLE",
            sia_url=qr_url,
            sia_code=code,
            error_tecnico="Timeout al contactar ANDIS",
        )
    except requests.exceptions.ConnectionError as exc:
        return ResultadoSia(
            estado="ANDIS_NO_DISPONIBLE",
            sia_url=qr_url,
            sia_code=code,
            error_tecnico=f"Error de conexión: {exc}",
        )
    except Exception as exc:
        return ResultadoSia(
            estado="ANDIS_NO_DISPONIBLE",
            sia_url=qr_url,
            sia_code=code,
            error_tecnico=f"Error inesperado: {exc}",
        )

    if not resp.ok:
        return ResultadoSia(
            estado="ANDIS_ERROR",
            sia_url=qr_url,
            sia_code=code,
            error_tecnico=f"HTTP {resp.status_code} desde ANDIS",
        )

    # 3. Parsear la respuesta
    datos      = _parsear_respuesta(resp.text)
    dominio    = normalizar_patente(datos.get("dominio", ""))
    vencimiento = _parsear_fecha(datos.get("vencimiento", ""))
    titular    = f"{datos.get('nombre', '')} {datos.get('apellido', '')}".strip()
    nci        = datos.get("nci", "")

    # Validación básica: si no se pudo extraer ningún dato útil, el HTML no fue reconocible
    if not dominio and not nci and not titular:
        return ResultadoSia(
            estado="RESPUESTA_INVALIDA",
            sia_url=qr_url,
            sia_code=code,
            error_tecnico="No se pudo extraer datos del HTML de ANDIS",
        )

    if not dominio:
        return ResultadoSia(
            estado="SIA_SIN_DOMINIO",
            sia_url=qr_url,
            sia_code=code,
            nci=nci,
            titular=titular,
            vencimiento=vencimiento,
            error_tecnico="ANDIS respondió pero no hay dominio/patente en el SIA",
        )

    # 4. Verificar vigencia
    if vencimiento and vencimiento < date.today():
        return ResultadoSia(
            estado="SIA_VENCIDO",
            sia_url=qr_url,
            sia_code=code,
            patente_sia=dominio,
            vencimiento=vencimiento,
            nci=nci,
            titular=titular,
        )

    # 5. Comparar patentes (normalizado)
    if dominio != normalizar_patente(patente_inspector):
        return ResultadoSia(
            estado="PATENTE_NO_COINCIDE",
            sia_url=qr_url,
            sia_code=code,
            patente_sia=dominio,
            vencimiento=vencimiento,
            nci=nci,
            titular=titular,
        )

    # 6. Todo OK
    return ResultadoSia(
        estado="VALIDO_PATENTE_COINCIDENTE",
        sia_url=qr_url,
        sia_code=code,
        patente_sia=dominio,
        vencimiento=vencimiento,
        nci=nci,
        titular=titular,
    )
