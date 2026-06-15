from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class NoUsernameAccountAdapter(DefaultAccountAdapter):
    """
    Adapter de cuenta: desactiva el campo username ya que usamos 'correo'.
    """

    def generate_unique_username(self, txts, regex=None):
        return None

    def populate_username(self, request, user):
        # No usar username nunca
        return


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter para login social (Google OAuth).

    Problema: allauth asume que el campo email del modelo se llama 'email',
    pero nuestro modelo usa 'correo' como USERNAME_FIELD.
    Este adapter copia el email de Google al campo 'correo' al crear el usuario.
    """

    def populate_user(self, request, sociallogin, data):
        # Llamar al adapter base para rellenar los campos estándar
        user = super().populate_user(request, sociallogin, data)

        # Copiar el email al campo 'correo' (nuestro campo personalizado)
        email = data.get("email", "")
        if email and not getattr(user, "correo", None):
            user.correo = email

        return user

    def save_user(self, request, sociallogin, form=None):
        from .models import Municipio

        user = super().save_user(request, sociallogin, form)

        # Asegurar que correo esté seteado después de guardar
        if not getattr(user, "correo", None):
            email = sociallogin.account.extra_data.get("email", "")
            if email:
                user.correo = email
                user.save(update_fields=["correo"])

        # Los usuarios que ingresan por Google son conductores por defecto
        campos_a_guardar = []
        if not user.es_conductor and not user.es_inspector and not user.es_vendedor and not user.es_admin:
            user.es_conductor = True
            campos_a_guardar.append("es_conductor")

        # Si hay exactamente un municipio activo, asignarlo automáticamente.
        # Si hay más de uno, el middleware redirigirá al usuario a completar_perfil.
        if not user.municipio_id:
            municipios = Municipio.objects.filter(activo=True)
            if municipios.count() == 1:
                user.municipio = municipios.first()
                campos_a_guardar.append("municipio")

        if campos_a_guardar:
            user.save(update_fields=campos_a_guardar)

        return user
