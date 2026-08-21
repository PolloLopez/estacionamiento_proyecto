# app_estacionamiento/tests_sia.py
"""
Tests unitarios del servicio de verificación SIA (Símbolo Internacional de Acceso — ANDIS).

Cubren:
- Validación de URL ANDIS (SSRF prevention)
- Parseo del HTML de respuesta
- Verificación de vigencia
- Comparación de patentes
- Todos los estados posibles de ResultadoSia
- Vista verificar_sia (integración con BD)
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase, Client
from django.urls import reverse

from .models import Municipio, Usuario, Vehiculo
from .services.sia_verificacion import (
    ResultadoSia,
    normalizar_patente,
    validar_url_andis,
    verificar_sia,
    _parsear_respuesta,
    _parsear_fecha,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de test
# ─────────────────────────────────────────────────────────────────────────────

def _html_andis(dominio="AA123BB", nombre="Juan", apellido="Pérez",
                nci="NCI-001", vencimiento="2027-12-31"):
    """Genera un HTML de respuesta ANDIS mínimo pero realista."""
    return f"""
    <html><body>
    <table>
      <tr><td>NCI</td><td>{nci}</td></tr>
      <tr><td>Nombre</td><td>{nombre}</td></tr>
      <tr><td>Apellido</td><td>{apellido}</td></tr>
      <tr><td>Dominio</td><td>{dominio}</td></tr>
      <tr><td>Vencimiento</td><td>{vencimiento}</td></tr>
    </table>
    </body></html>
    """

def _mock_respuesta(html, status_code=200):
    """Mock de requests.Response."""
    resp = MagicMock()
    resp.ok = status_code < 400
    resp.status_code = status_code
    resp.text = html
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# Tests: normalizar_patente
# ─────────────────────────────────────────────────────────────────────────────

class NormalizarPatenteTest(TestCase):

    def test_mayusculas(self):
        self.assertEqual(normalizar_patente("aa123bb"), "AA123BB")

    def test_sin_guion(self):
        self.assertEqual(normalizar_patente("AA-123-BB"), "AA123BB")

    def test_sin_espacios(self):
        self.assertEqual(normalizar_patente("AA 123 BB"), "AA123BB")

    def test_string_vacio(self):
        self.assertEqual(normalizar_patente(""), "")

    def test_none(self):
        self.assertEqual(normalizar_patente(None), "")


# ─────────────────────────────────────────────────────────────────────────────
# Tests: validar_url_andis
# ─────────────────────────────────────────────────────────────────────────────

class ValidarUrlAndisTest(TestCase):
    URL_VALIDA = "https://apps.andis.gob.ar/qr-simbolo?code=ABC123"

    def test_url_valida(self):
        ok, code = validar_url_andis(self.URL_VALIDA)
        self.assertTrue(ok)
        self.assertEqual(code, "ABC123")

    def test_rechaza_http(self):
        ok, _ = validar_url_andis("http://apps.andis.gob.ar/qr-simbolo?code=ABC")
        self.assertFalse(ok)

    def test_rechaza_dominio_falso(self):
        ok, _ = validar_url_andis("https://apps-andis.gob.ar/qr-simbolo?code=ABC")
        self.assertFalse(ok)

    def test_rechaza_path_diferente(self):
        ok, _ = validar_url_andis("https://apps.andis.gob.ar/otro-path?code=ABC")
        self.assertFalse(ok)

    def test_rechaza_sin_code(self):
        ok, _ = validar_url_andis("https://apps.andis.gob.ar/qr-simbolo")
        self.assertFalse(ok)

    def test_rechaza_code_vacio(self):
        ok, _ = validar_url_andis("https://apps.andis.gob.ar/qr-simbolo?code=")
        self.assertFalse(ok)

    def test_rechaza_url_aleatoria(self):
        ok, _ = validar_url_andis("https://malicious.com/steal?code=ABC")
        self.assertFalse(ok)

    def test_rechaza_string_vacio(self):
        ok, _ = validar_url_andis("")
        self.assertFalse(ok)


# ─────────────────────────────────────────────────────────────────────────────
# Tests: _parsear_respuesta
# ─────────────────────────────────────────────────────────────────────────────

class ParsearRespuestaTest(TestCase):

    def test_parsea_campos_tabla(self):
        html = _html_andis(dominio="AA123BB", nombre="Juan", apellido="Pérez",
                           nci="NCI-001", vencimiento="2027-12-31")
        datos = _parsear_respuesta(html)
        self.assertEqual(datos["dominio"], "AA123BB")
        self.assertEqual(datos["nombre"], "Juan")
        self.assertEqual(datos["apellido"], "Pérez")
        self.assertEqual(datos["nci"], "NCI-001")
        self.assertEqual(datos["vencimiento"], "2027-12-31")

    def test_html_vacio_devuelve_strings_vacios(self):
        datos = _parsear_respuesta("<html></html>")
        self.assertEqual(datos["dominio"], "")
        self.assertEqual(datos["nci"], "")


# ─────────────────────────────────────────────────────────────────────────────
# Tests: _parsear_fecha
# ─────────────────────────────────────────────────────────────────────────────

class ParsearFechaTest(TestCase):

    def test_formato_iso(self):
        self.assertEqual(_parsear_fecha("2027-12-31"), date(2027, 12, 31))

    def test_formato_ddmmyyyy(self):
        self.assertEqual(_parsear_fecha("31/12/2027"), date(2027, 12, 31))

    def test_texto_invalido(self):
        self.assertIsNone(_parsear_fecha("no-es-fecha"))

    def test_string_vacio(self):
        self.assertIsNone(_parsear_fecha(""))


# ─────────────────────────────────────────────────────────────────────────────
# Tests: verificar_sia (servicio completo — mockea requests)
# ─────────────────────────────────────────────────────────────────────────────

QR_URL = "https://apps.andis.gob.ar/qr-simbolo?code=TESTCODE"
PATENTE = "AA123BB"


class VerificarSiaTest(TestCase):

    @patch("app_estacionamiento.services.sia_verificacion.requests.get")
    def test_valido_patente_coincidente(self, mock_get):
        vencimiento = (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")
        mock_get.return_value = _mock_respuesta(_html_andis(dominio=PATENTE, vencimiento=vencimiento))
        resultado = verificar_sia(QR_URL, PATENTE)
        self.assertEqual(resultado.estado, "VALIDO_PATENTE_COINCIDENTE")
        self.assertTrue(resultado.es_valido)
        self.assertEqual(resultado.patente_sia, PATENTE)

    @patch("app_estacionamiento.services.sia_verificacion.requests.get")
    def test_patente_no_coincide(self, mock_get):
        vencimiento = (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")
        mock_get.return_value = _mock_respuesta(_html_andis(dominio="ZZ999ZZ", vencimiento=vencimiento))
        resultado = verificar_sia(QR_URL, PATENTE)
        self.assertEqual(resultado.estado, "PATENTE_NO_COINCIDE")
        self.assertFalse(resultado.es_valido)

    @patch("app_estacionamiento.services.sia_verificacion.requests.get")
    def test_sia_vencido(self, mock_get):
        vencimiento = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        mock_get.return_value = _mock_respuesta(_html_andis(dominio=PATENTE, vencimiento=vencimiento))
        resultado = verificar_sia(QR_URL, PATENTE)
        self.assertEqual(resultado.estado, "SIA_VENCIDO")

    @patch("app_estacionamiento.services.sia_verificacion.requests.get")
    def test_sia_sin_dominio(self, mock_get):
        html = _html_andis(dominio="", vencimiento="2027-12-31")
        mock_get.return_value = _mock_respuesta(html)
        resultado = verificar_sia(QR_URL, PATENTE)
        self.assertEqual(resultado.estado, "SIA_SIN_DOMINIO")

    def test_qr_url_invalida(self):
        resultado = verificar_sia("https://malicious.com/?code=XYZ", PATENTE)
        self.assertEqual(resultado.estado, "QR_URL_INVALIDA")
        # No debe haber llamado a requests — ningún side effect externo
        self.assertFalse(resultado.es_valido)

    @patch("app_estacionamiento.services.sia_verificacion.requests.get",
           side_effect=__import__("requests").exceptions.Timeout)
    def test_andis_no_disponible_timeout(self, mock_get):
        resultado = verificar_sia(QR_URL, PATENTE)
        self.assertEqual(resultado.estado, "ANDIS_NO_DISPONIBLE")

    @patch("app_estacionamiento.services.sia_verificacion.requests.get",
           side_effect=__import__("requests").exceptions.ConnectionError)
    def test_andis_no_disponible_conexion(self, mock_get):
        resultado = verificar_sia(QR_URL, PATENTE)
        self.assertEqual(resultado.estado, "ANDIS_NO_DISPONIBLE")

    @patch("app_estacionamiento.services.sia_verificacion.requests.get")
    def test_andis_error_http(self, mock_get):
        mock_get.return_value = _mock_respuesta("", status_code=503)
        resultado = verificar_sia(QR_URL, PATENTE)
        self.assertEqual(resultado.estado, "ANDIS_ERROR")

    @patch("app_estacionamiento.services.sia_verificacion.requests.get")
    def test_respuesta_invalida_html_sin_datos(self, mock_get):
        mock_get.return_value = _mock_respuesta("<html><body>Mantenimiento</body></html>")
        resultado = verificar_sia(QR_URL, PATENTE)
        self.assertEqual(resultado.estado, "RESPUESTA_INVALIDA")

    @patch("app_estacionamiento.services.sia_verificacion.requests.get")
    def test_vigencia_sin_fecha_se_acepta(self, mock_get):
        """SIA sin fecha de vencimiento → se considera indefinido (vigente)."""
        html = _html_andis(dominio=PATENTE, vencimiento="")
        mock_get.return_value = _mock_respuesta(html)
        resultado = verificar_sia(QR_URL, PATENTE)
        # Sin vencimiento, no puede estar vencido → compara patente
        self.assertEqual(resultado.estado, "VALIDO_PATENTE_COINCIDENTE")

    @patch("app_estacionamiento.services.sia_verificacion.requests.get")
    def test_patente_normalizada_guion(self, mock_get):
        """Patente con guión en el SIA debe coincidir igual que sin guión."""
        vencimiento = (date.today() + timedelta(days=100)).strftime("%Y-%m-%d")
        html = _html_andis(dominio="AA-123-BB", vencimiento=vencimiento)
        mock_get.return_value = _mock_respuesta(html)
        resultado = verificar_sia(QR_URL, "AA123BB")
        self.assertEqual(resultado.estado, "VALIDO_PATENTE_COINCIDENTE")


# ─────────────────────────────────────────────────────────────────────────────
# Tests: vista verificar_sia (integración con BD)
# ─────────────────────────────────────────────────────────────────────────────

class VistaSiaTest(TestCase):
    def setUp(self):
        self.municipio = Municipio.objects.create(
            nombre="Test",
            slug="test",
            tarifa_por_hora="10.00",
        )
        self.inspector = Usuario.objects.create_user(
            correo="inspector@test.com",
            password="pass1234",
            rol="inspector",
            municipio=self.municipio,
        )
        self.client = Client()
        self.client.login(username="inspector@test.com", password="pass1234")
        self.url = reverse("inspectores_verificar_sia")

    def test_get_devuelve_405(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 405)

    def test_post_sin_patente_devuelve_400(self):
        import json
        resp = self.client.post(
            self.url,
            data=json.dumps({"qr_url": QR_URL}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_sin_qr_url_devuelve_400(self):
        import json
        resp = self.client.post(
            self.url,
            data=json.dumps({"patente": PATENTE}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_url_invalida_no_crea_exencion(self):
        """Si el QR es inválido, no debe crearse ni actualizarse ningún Vehiculo con exención.
        No necesita mock: validar_url_andis rechaza sin llamar a requests.get."""
        import json
        resp = self.client.post(
            self.url,
            data=json.dumps({"patente": PATENTE, "qr_url": "https://malicious.com/?x=1"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["estado"], "QR_URL_INVALIDA")
        self.assertFalse(data["es_valido"])
        # No debe haber creado un Vehiculo exento
        self.assertFalse(
            Vehiculo.objects.filter(patente=PATENTE, exento_global=True).exists()
        )

    @patch("app_estacionamiento.services.sia_verificacion.requests.get")
    def test_post_valido_crea_exencion_en_bd(self, mock_get):
        """Un SIA válido debe registrar la exención en el Vehiculo."""
        import json
        vencimiento = date(2027, 6, 30)
        mock_get.return_value = _mock_respuesta(
            _html_andis(dominio=PATENTE, vencimiento="2027-06-30")
        )
        resp = self.client.post(
            self.url,
            data=json.dumps({"patente": PATENTE, "qr_url": QR_URL}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["es_valido"])
        # El Vehiculo debe quedar exento en la BD
        vehiculo = Vehiculo.objects.get(patente=PATENTE)
        self.assertTrue(vehiculo.exento_global)
        self.assertEqual(vehiculo.tipo_exencion, "discapacitado")
        self.assertEqual(vehiculo.vigencia_exencion, vencimiento)
        self.assertTrue(vehiculo.exencion_verificada)

    @patch("app_estacionamiento.services.sia_verificacion.requests.get")
    def test_post_valido_actualiza_vehiculo_existente(self, mock_get):
        """Si el Vehiculo ya existe, la vista actualiza sus campos de exención."""
        import json
        Vehiculo.objects.create(patente=PATENTE, municipio=self.municipio)
        mock_get.return_value = _mock_respuesta(
            _html_andis(dominio=PATENTE, vencimiento="2027-06-30")
        )
        resp = self.client.post(
            self.url,
            data=json.dumps({"patente": PATENTE, "qr_url": QR_URL}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        vehiculo = Vehiculo.objects.get(patente=PATENTE)
        self.assertTrue(vehiculo.exento_global)

    def test_requiere_login(self):
        import json
        self.client.logout()
        resp = self.client.post(
            self.url,
            data=json.dumps({"patente": PATENTE, "qr_url": QR_URL}),
            content_type="application/json",
        )
        # El decorator @require_role redirige al login
        self.assertIn(resp.status_code, [302, 403])
