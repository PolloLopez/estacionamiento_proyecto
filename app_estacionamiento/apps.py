# app_estacionamiento/apps.py

from django.apps import AppConfig


class AppEstacionamientoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_estacionamiento'

    def ready(self):
        """
        Conectar señales de allauth al arrancar la app.
        Usamos ready() porque las señales deben registrarse una sola vez,
        después de que todos los modelos estén cargados.
        """
        from allauth.account.signals import email_confirmed
        from django.contrib import messages
        from django.dispatch import receiver

        @receiver(email_confirmed)
        def mostrar_mensaje_verificacion(sender, request, email_address, **kwargs):
            """
            Después de que el usuario hace clic en el link de verificación,
            allauth emite esta señal. Aprovechamos para agregar un mensaje de
            Django que la página de login va a mostrar.
            """
            messages.success(
                request,
                "¡Tu email fue verificado! Ya podés iniciar sesión.",
            )
