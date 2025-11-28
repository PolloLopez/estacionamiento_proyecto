import pytest
from django.urls import reverse
from app_estacionamiento.models import Usuario

@pytest.mark.django_db
def test_require_role_redirige_si_no_hay_sesion(client):
    url = reverse("usuarios_estacionar_vehiculo")
    response = client.get(url)
    assert response.status_code == 302
    assert "/login/" in response.url

@pytest.mark.django_db
def test_inicio_usuarios_muestra_usuario(client):
    usuario = Usuario.objects.create_user(
    email="juan@test.com",
    password="1234",
    es_conductor=True
)

    client.session["usuario_id"] = usuario.id
    client.session.save()

    url = reverse("inicio_usuarios")
    response = client.get(url)
    assert response.status_code == 200
    assert b"Bienvenido" in response.content
