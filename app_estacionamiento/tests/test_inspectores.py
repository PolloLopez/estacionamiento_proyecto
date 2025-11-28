import pytest
from django.urls import reverse
from decimal import Decimal
from app_estacionamiento.models import Usuario, Vehiculo, Subcuadra, Estacionamiento, Infraccion

@pytest.mark.django_db
def test_inspector_verifica_vehiculo_exento_global(client):
    inspector = Usuario.objects.create_user(
        email="insp@test.com",
        password="1234",
        es_inspector=True
    )
    client.force_login(inspector)

    vehiculo = Vehiculo.objects.create(patente="EXENTO123", exento_global=True)
    subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)

    url = reverse("inspectores_verificar_vehiculo")
    response = client.post(url, {"patente": vehiculo.patente, "subcuadra_id": subcuadra.id})

    assert response.status_code == 200
    assert b"exento" in response.content.lower()
    assert not Estacionamiento.objects.filter(vehiculo=vehiculo).exists()
    assert not Infraccion.objects.filter(vehiculo=vehiculo).exists()


@pytest.mark.django_db
def test_inspector_verifica_vehiculo_exento_parcial(client):
    inspector = Usuario.objects.create_user(
        email="insp@test.com",
        password="1234",
        es_inspector=True
    )
    client.force_login(inspector)

    subcuadra_exenta, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=100)
    subcuadra_no_exenta, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=200)

    vehiculo = Vehiculo.objects.create(patente="PARCIAL456")
    vehiculo.exento_parcial.add(subcuadra_exenta)

    # Caso en subcuadra exenta → Exento
    url = reverse("inspectores_verificar_vehiculo")
    response = client.post(url, {"patente": vehiculo.patente, "subcuadra_id": subcuadra_exenta.id})
    assert response.status_code == 200
    assert b"exento" in response.content.lower()
    assert not Infraccion.objects.filter(vehiculo=vehiculo).exists()

    # Caso en subcuadra no exenta → Impago + infracción
    url = reverse("inspectores_verificar_vehiculo")
    response = client.post(url, {"patente": vehiculo.patente, "subcuadra_id": subcuadra_no_exenta.id})
    assert response.status_code == 200
    assert b"impago" in response.content.lower()
    assert Infraccion.objects.filter(vehiculo=vehiculo).exists()


@pytest.mark.django_db
def test_inspector_verifica_vehiculo_pagado(client):
    inspector = Usuario.objects.create_user(
        email="insp@test.com",
        password="1234",
        es_inspector=True
    )
    client.force_login(inspector)

    usuario = Usuario.objects.create_user(
        email="juan@test.com",
        password="1234",
        es_conductor=True,
        saldo=Decimal("50.00")
    )
    vehiculo = Vehiculo.objects.create(patente="PAGO789")
    subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)

    Estacionamiento.objects.create(
        vehiculo=vehiculo,
        subcuadra=subcuadra,
        registrado_por=usuario,
        activo=True,
        costo=Decimal("10.00")
    )

    url = reverse("inspectores_verificar_vehiculo")
    response = client.post(url, {"patente": vehiculo.patente, "subcuadra_id": subcuadra.id})

    assert response.status_code == 200
    assert b"pagado" in response.content.lower()
    assert not Infraccion.objects.filter(vehiculo=vehiculo).exists()


@pytest.mark.django_db
def test_inspector_verifica_vehiculo_activo(client):
    inspector = Usuario.objects.create_user(
        email="insp@test.com",
        password="1234",
        es_inspector=True
    )
    client.force_login(inspector)

    vehiculo = Vehiculo.objects.create(patente="XYZ789")
    subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)
    Estacionamiento.objects.create(vehiculo=vehiculo, subcuadra=subcuadra, registrado_por=inspector)

    url = reverse("inspectores_verificar_vehiculo")
    response = client.post(url, {"patente": "XYZ789"})
    assert response.status_code == 200
    assert b"Estado: Pagado" in response.content
    assert b"Estacionamiento activo" in response.content


@pytest.mark.django_db
def test_inspector_verifica_vehiculo_sin_estacionamiento(client):
    inspector = Usuario.objects.create_user(
        email="insp@test.com",
        password="1234",
        es_inspector=True
    )
    client.force_login(inspector)

    vehiculo = Vehiculo.objects.create(patente="NOPARK123")
    subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)

    url = reverse("inspectores_verificar_vehiculo")
    response = client.post(url, {"patente": vehiculo.patente, "subcuadra_id": subcuadra.id})

    assert response.status_code == 200
    assert b"impago" in response.content.lower()
    assert Infraccion.objects.filter(vehiculo=vehiculo).exists()
