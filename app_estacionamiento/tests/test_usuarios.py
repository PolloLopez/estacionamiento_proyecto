import pytest
from django.urls import reverse
from decimal import Decimal
from app_estacionamiento.models import Usuario, Vehiculo, Subcuadra, Estacionamiento, Infraccion

@pytest.mark.django_db
def test_usuario_finaliza_estacionamiento_con_saldo(client):
    usuario = Usuario.objects.create(
        nombre="Juan",
        correo="juan@test.com",
        es_conductor=True,
        saldo=Decimal("100.00")
    )
    vehiculo = Vehiculo.objects.create(patente="AAA111")
    subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)
    est = Estacionamiento.objects.create(
        vehiculo=vehiculo,
        subcuadra=subcuadra,
        registrado_por=usuario
    )

    # Simulamos sesión
    session = client.session
    session["usuario_id"] = usuario.id
    session.save()

    url = reverse("usuarios_finalizar_estacionamiento", args=[est.id])
    response = client.get(url)

    assert response.status_code == 302
    est.refresh_from_db()
    usuario.refresh_from_db()

    # El estacionamiento debe estar finalizado
    assert est.activo is False
    # El saldo debe haberse descontado (en este caso queda en 0.00)
    assert usuario.saldo == Decimal("0.00")


@pytest.mark.django_db
def test_usuario_finaliza_estacionamiento_sin_saldo(client):
    usuario = Usuario.objects.create(
        nombre="Juan",
        correo="juan@test.com",
        es_conductor=True,
        saldo=Decimal("0.00")
    )
    vehiculo = Vehiculo.objects.create(patente="BBB222")
    subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)
    est = Estacionamiento.objects.create(
        vehiculo=vehiculo,
        subcuadra=subcuadra,
        registrado_por=usuario
    )

    # Simulamos sesión
    session = client.session
    session["usuario_id"] = usuario.id
    session.save()

    url = reverse("usuarios_finalizar_estacionamiento", args=[est.id])
    response = client.get(url)

    # debería redirigir a historial con error
    assert response.status_code == 302
    assert reverse("usuarios_historial") in response.url

    est.refresh_from_db()
    usuario.refresh_from_db()

    # El estacionamiento debe seguir activo porque no había saldo
    assert est.activo is True
    # El saldo debe seguir igual
    assert usuario.saldo == Decimal("0.00")

@pytest.mark.django_db
def test_inspector_verifica_vehiculo_sin_estacionamiento(client):
    inspector = Usuario.objects.create_user(
    email="juan@test.com",
    password="1234",
    es_conductor=True
)

    vehiculo = Vehiculo.objects.create(patente="NOPARK123")
    subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)

    session = client.session
    session["usuario_id"] = inspector.id
    session.save()

    url = reverse("inspectores_verificar_vehiculo")
    response = client.post(url, {"patente": vehiculo.patente, "subcuadra_id": subcuadra.id})

    assert response.status_code == 200
    # debería marcar como impago y generar infracción
    assert b"impago" in response.content.lower()
    assert Infraccion.objects.filter(vehiculo=vehiculo).exists()

@pytest.mark.django_db
def test_usuario_finaliza_estacionamiento_exento(client):
    usuario = Usuario.objects.create(
        nombre="Pedro",
        correo="pedro@test.com",
        es_conductor=True,
        saldo=Decimal("50.00")
    )
    # Vehículo marcado como exento en toda la zona
    vehiculo = Vehiculo.objects.create(
        patente="EXENTO999",
        exento_global=True
    )
    subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)
    est = Estacionamiento.objects.create(
        vehiculo=vehiculo,
        subcuadra=subcuadra,
        registrado_por=usuario
    )

    # Simulamos sesión
    session = client.session
    session["usuario_id"] = usuario.id
    session.save()

    url = reverse("usuarios_finalizar_estacionamiento", args=[est.id])
    response = client.get(url)

    assert response.status_code == 302
    est.refresh_from_db()
    usuario.refresh_from_db()

    # El estacionamiento debe estar finalizado
    assert est.activo is False
    # El costo debe ser cero porque el vehículo es exento
    assert est.costo == Decimal("0.00")
    # El saldo del usuario no debe haberse descontado
    assert usuario.saldo == Decimal("50.00")

@pytest.mark.django_db
def test_usuario_historial(client):
    usuario = Usuario.objects.create_user(email="test@test.com", password="1234", es_conductor=True)
    client.force_login(usuario)   # 👈 asegura login

    response = client.get(reverse("usuarios_historial"))
    assert response.status_code == 200
