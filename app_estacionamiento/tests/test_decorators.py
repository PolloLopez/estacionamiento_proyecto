import pytest
from django.urls import reverse
from app_estacionamiento.models import Usuario

@pytest.mark.django_db
def test_require_login_redirige_si_no_hay_sesion(client):
    url = reverse("usuarios_cargar_saldo")
    response = client.get(url)
    assert response.status_code == 302
    assert "/login" in response.url

@pytest.mark.django_db
def test_require_role_redirige_si_no_tiene_rol(client):
    usuario = Usuario.objects.create(nombre="Juan", correo="juan@test.com", es_conductor=False)
    session = client.session
    session["usuario_id"] = usuario.id
    session.save()

    url = reverse("inicio_usuarios")
    response = client.get(url)
    assert response.status_code == 302
    assert "/inicio" in response.url or "/login" in response.url

@pytest.mark.django_db
def test_require_role_permite_si_tiene_rol(client):
    usuario = Usuario.objects.create(nombre="Juan", correo="juan@test.com", es_conductor=True)
    session = client.session
    session["usuario_id"] = usuario.id
    session.save()

    url = reverse("inicio_usuarios")
    response = client.get(url)
    assert response.status_code == 200
    assert b"Bienvenido" in response.content
