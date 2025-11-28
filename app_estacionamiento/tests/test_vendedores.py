# app_estacionamiento/tests/test_vendedores.py
import pytest
from django.urls import reverse
from decimal import Decimal
from app_estacionamiento.models import Usuario, Vehiculo, Estacionamiento, Subcuadra

@pytest.mark.django_db
def test_vendedor_registra_estacionamiento(client):
    vendedor = Usuario.objects.create(nombre="Vend", correo="vend@test.com", es_vendedor=True)
    cliente = Usuario.objects.create(nombre="Cliente", correo="cli@test.com", es_conductor=True)

    session = client.session
    session["usuario_id"] = vendedor.id
    session.save()

    url = reverse("vendedores_registrar_estacionamiento")
    response = client.post(url, {
        "patente": "ABC123",
        "duracion": "1",
        "cliente_email": cliente.correo
    })

    assert response.status_code == 302
    assert response.url == reverse("vendedores_resumen_caja")

    # Verificar que se creó el estacionamiento
    est = Estacionamiento.objects.get(vehiculo__patente="ABC123")
    assert est.activo is True
    assert est.registrado_por == vendedor

    # Verificar que el vehículo quedó asociado al cliente
    vehiculo = Vehiculo.objects.get(patente="ABC123")
    assert cliente in vehiculo.usuarios.all()
