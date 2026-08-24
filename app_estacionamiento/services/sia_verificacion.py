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
    Extrae campos del HTML de ANDIS. Soporta dos estructuras de tabla:

    A) Clave-valor por fila — cada <tr> tiene 2 celdas: label y valor.
       Es el formato de los tests y un posible formato alternativo de ANDIS.
         <tr><td>Dominio</td><td>AA123BB</td></tr>

    B) Encabezados en fila 1, valores en fila 2 — N columnas.
       Es el formato real que devuelve ANDIS actualmente.
         <tr><th>NCI</th><th>Dominio</th><th>Vencimiento</th></tr>
         <tr><td>123</td><td>AA123BB</td><td>2027-12-31</td></tr>

    El parser detecta automáticamente cuál usar.
    Como último recurso intenta "Campo: valor" en texto plano.

    Bug que esto corrige: con estructura B, el regex original
    "Dominio</td><td>Vencimiento" capturaba "Vencimiento" como valor de Dominio.
    """
    # Extraer todas las filas con sus celdas (texto limpio, sin tags internos)
    def es_encabezado(fila_html: str) -> bool:
        """True si la fila tiene al menos un <th> (encabezado de tabla)."""
        return bool(re.search(r"<th[^>]*>", fila_html, re.IGNORECASE))

    def celdas_de(fila_html: str) -> list:
        celdas = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", fila_html, re.IGNORECASE | re.DOTALL)
        return [re.sub(r"<[^>]+>", "", c).strip() for c in celdas]

    filas_html = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.IGNORECASE | re.DOTALL)
    tabla = {}

    # Estrategia B: hay filas <th> → encabezados en esa fila, valores en la siguiente.
    # ANDIS real usa <th>Dominio</th><th>Vencimiento</th> + <td>ABC123</td><td>...</td>.
    # Nota: si usáramos Strategy A con 2 columnas, trataría la fila de encabezados como
    # par ("Dominio", "Vencimiento"), poniendo "Vencimiento" como valor de "dominio" — bug original.
    if any(es_encabezado(f) for f in filas_html):
        encabezados = []
        for fila_html in filas_html:
            if es_encabezado(fila_html):
                encabezados = celdas_de(fila_html)
            elif encabezados:
                valores = celdas_de(fila_html)
                for enc, val in zip(encabezados, valores):
                    if enc and val:
                        tabla[enc.lower()] = val
                break  # solo la primera fila de datos

    # Estrategia A: todas las filas son <td> con 2 celdas → clave-valor por fila.
    # Usada por los tests y posibles formatos alternativos de ANDIS.
    if not tabla:
        for fila_html in filas_html:
            celdas = celdas_de(fila_html)
            if len(celdas) == 2 and celdas[0] and celdas[1]:
                tabla[celdas[0].lower()] = celdas[1]

    def buscar_tabla(campo: str) -> str:
        """Busca el campo en la tabla por substring, case-insensitive."""
        campo_l = campo.lower()
        for clave, valor in tabla.items():
            if campo_l in clave:
                return valor
        return ""

    def extraer_texto(campo: str) -> str:
        """Fallback: 'Campo: valor' en texto plano (sin tags HTML)."""
        patron = rf"{re.escape(campo)}\s*[:\-]\s*([^\n<]{{1,100}})"
        m = re.search(patron, html, re.IGNORECASE)
        return m.group(1).strip() if m else ""

    def buscar(campo: str, alternativas: list = None) -> str:
        for c in [campo] + (alternativas or []):
            v = buscar_tabla(c) or extraer_texto(c)
            if v:
                return v
        return ""

    return {
        "nci":         buscar("NCI", ["Trámite", "Caso"]),
        "nombre":      buscar("Nombre"),
        "apellido":    buscar("Apellido"),
        "dominio":     buscar("Dominio", ["Patente"]),
        "vencimiento": buscar("Vencimiento", ["Vigencia", "Expira"]),
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
