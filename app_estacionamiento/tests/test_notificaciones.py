import pytest
from app_estacionamiento.models import Usuario, Notificacion

@pytest.mark.django_db
def test_crear_notificacion_y_str():
    # Crear usuario destinatario
    usuario = Usuario.objects.create_user(
        email="destinatario@test.com",
        password="1234",
        es_conductor=True
    )

    # Crear notificación
    notif = Notificacion.objects.create(
        destinatario=usuario,
        mensaje="Tu saldo está bajo"
    )

    # Verificar que se guarda correctamente
    assert notif.destinatario == usuario
    assert notif.mensaje == "Tu saldo está bajo"
    assert notif.leida is False

    # Verificar que __str__ devuelve el correo
    assert str(notif) == f"Notificación para {usuario.email}"
