import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

logger = logging.getLogger(__name__)


class NoUsernameAccountAdapter(DefaultAccountAdapter):
    """
    Adapter de cuenta: desactiva el campo username ya que usamos 'correo'.
    """

    def generate_unique_username(self, txts, regex=None):
        return None

    def populate_username(self, request, user):
        # No usar username nunca
        return

    def send_mail(self, template_prefix, email, context):
        """
        Envía un email transaccional (ej: recuperación de contraseña).

        Por qué wrapeamos con try-except:
        - Si el backend de email falla (Brevo rechaza, credenciales incorrectas, etc.),
          sin este wrapper la excepción llega hasta la vista de allauth y Django
          devuelve un 500 en lugar de redirigir al usuario a la página de "correo enviado".
        - Desde el punto de vista del usuario, siempre debe ver la pantalla de confirmación
          (por seguridad: no revelar si el correo existe o no).
        - El error real queda logueado para que lo podamos diagnosticar en Railway.
        """
        try:
            super().send_mail(template_prefix, email, context)
        except Exception as exc:
            logger.error(
                "Error enviando email '%s' a '%s': %s",
                template_prefix, email, exc,
                exc_info=True,
            )


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter para login social (Google OAuth).

    Problema: allauth asume que el campo email del modelo se llama 'email',
    pero nuestro modelo usa 'correo' como USERNAME_FIELD.
    Este adapter copia el email de Google al campo 'correo' al crear el usuario,
    y tambien copia nombre y apellido del perfil de Google.

    Seguridad: `pre_social_login` bloquea el auto-connect cuando el email ya
    existe en la BD sin una cuenta Google asociada. Sin esta protección, un
    atacante podría crear una cuenta Google con el email de otra persona y
    tomar control de su cuenta (account takeover vía SOCIALACCOUNT_AUTO_SIGNUP).
    """

    def pre_social_login(self, request, sociallogin):
        """
        Bloquea el intento de login si el email de Google ya pertenece
        a un usuario registrado por otra vía (ej: email + contraseña).

        Flujo normal (no bloquea):
        - El sociallogin ya está conectado a un usuario existente.
        - El email no existe en la BD (usuario nuevo → auto-signup).
        - El email existe Y ya tiene cuenta Google asociada (re-login).

        Flujo bloqueado:
        - El email existe en la BD sin cuenta Google → posible takeover.
        """
        from allauth.exceptions import ImmediateHttpResponse
        from allauth.socialaccount.models import SocialAccount
        from django.shortcuts import render

        # Ya conectado a un usuario: flujo normal de re-login
        if sociallogin.is_existing:
            return

        # Obtener el email que Google devuelve
        email = (sociallogin.account.extra_data or {}).get("email", "")
        if not email and sociallogin.email_addresses:
            email = sociallogin.email_addresses[0].email
        if not email:
            # Sin email no podemos verificar — dejamos que allauth maneje
            return

        from .models import Usuario
        try:
            usuario_existente = Usuario.objects.get(correo__iexact=email)
        except Usuario.DoesNotExist:
            # Email nuevo → auto-signup normal
            return

        # El email existe: verificar si ya tiene cuenta Google vinculada
        tiene_google = SocialAccount.objects.filter(
            user=usuario_existente, provider="google"
        ).exists()

        if not tiene_google:
            # Email registrado sin Google → bloquear para prevenir takeover
            logger.warning(
                "pre_social_login bloqueado: correo='%s' ya existe sin cuenta Google. ip=%s",
                email,
                request.META.get("REMOTE_ADDR", "-"),
            )
            raise ImmediateHttpResponse(
                render(request, "account/email_conflicto_google.html", {
                    "correo": email,
                })
            )

    def populate_user(self, request, sociallogin, data):
        # Llamar al adapter base para rellenar los campos estandar
        user = super().populate_user(request, sociallogin, data)

        # Copiar el email al campo 'correo' (nuestro campo personalizado)
        email = data.get("email", "")
        if email and not getattr(user, "correo", None):
            user.correo = email

        return user

    def save_user(self, request, sociallogin, form=None):
        from .models import Municipio

        user = super().save_user(request, sociallogin, form)

        # Datos que Google devuelve en extra_data
        extra = sociallogin.account.extra_data
        campos_a_guardar = []

        # Correo: asegurar que este seteado
        if not getattr(user, "correo", None):
            email = extra.get("email", "")
            if email:
                user.correo = email
                campos_a_guardar.append("correo")

        # Nombre (given_name en Google)
        if not user.first_name:
            nombre = extra.get("given_name", "")
            if not nombre and extra.get("name"):
                # fallback: primer token del nombre completo
                nombre = extra["name"].split()[0]
            if nombre:
                user.first_name = nombre
                campos_a_guardar.append("first_name")

        # Apellido (family_name en Google)
        if not user.last_name:
            apellido = extra.get("family_name", "")
            if apellido:
                user.last_name = apellido
                campos_a_guardar.append("last_name")

        # Los usuarios que ingresan por Google son conductores por defecto
        if not user.es_conductor and not user.es_inspector and not user.es_vendedor and not user.es_admin:
            user.es_conductor = True
            campos_a_guardar.append("es_conductor")

        # Si hay exactamente un municipio activo, asignarlo automaticamente.
        # Si hay mas de uno, el middleware redirigira al usuario a completar_perfil.
        if not user.municipio_id:
            municipios = Municipio.objects.filter(activo=True)
            if municipios.count() == 1:
                user.municipio = municipios.first()
                campos_a_guardar.append("municipio")

        if campos_a_guardar:
            user.save(update_fields=campos_a_guardar)

        return user
