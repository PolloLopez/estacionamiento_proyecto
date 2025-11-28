#app_estacionamiento/tests/test_models.py
import pytest
from django.utils import timezone
from decimal import Decimal
from app_estacionamiento.models import Usuario, Vehiculo, Subcuadra, Estacionamiento

@pytest.mark.django_db
def test_finalizar_estacionamiento_calcula_costo_y_inactiva():
    usuario = Usuario.objects.create_user(
    email="juan@test.com",
    password="1234",
    es_conductor=True
)

    vehiculo = Vehiculo.objects.create(patente="ABC123")
    subcuadra, _ = Subcuadra.objects.get_or_create(calle="Zona Única", altura=0)

    est = Estacionamiento.objects.create(vehiculo=vehiculo, subcuadra=subcuadra, registrado_por=usuario)

    assert est.activo is True
    costo = est.finalizar()
    assert est.activo is False
    assert est.costo == pytest.approx(costo, 0.01)

@pytest.mark.django_db
def test_subcuadra_unicidad():
    Subcuadra.objects.create(calle="Zona Única", altura=0)
    with pytest.raises(Exception):
        Subcuadra.objects.create(calle="Zona Única", altura=0)
