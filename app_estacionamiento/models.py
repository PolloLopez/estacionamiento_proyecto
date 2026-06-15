# app_estacionamiento/models.py

import math
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.db.models import Q, UniqueConstraint

# 👤 Usuario del sistema 
class UsuarioManager(BaseUserManager):

    def create_user(self, correo=None, email=None, password=None, **extra_fields):
        correo = correo or email

        if not correo:
            raise ValueError("El correo es obligatorio")

        correo = self.normalize_email(correo)

        extra_fields.setdefault("is_active", True)

        user = self.model(correo=correo, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, correo=None, email=None, password=None, **extra_fields):
        correo = correo or email

        if not correo:
            raise ValueError("El correo es obligatorio")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("es_admin", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superuser debe tener is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superuser debe tener is_superuser=True")

        return self.create_user(correo=correo, password=password, **extra_fields)

class Usuario(AbstractUser):
    username = None

    correo = models.EmailField(unique=True)

    municipio = models.ForeignKey(
        "Municipio",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    saldo_operativo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    vehiculos = models.ManyToManyField(
        "Vehiculo",
        through="VehiculoUsuario",
        related_name="usuarios"
    )

    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ⚙️ Configuración de rendición (aplica a inspectores y vendedores)
    saldo_limite = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Límite de deuda antes de bloquear al usuario. 0 = sin límite."
    )
    porcentaje_ganancia = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Porcentaje del total cobrado que el usuario retiene como ganancia."
    )
    periodicidad_rendicion = models.CharField(
        max_length=10,
        choices=[("diaria", "Diaria"), ("semanal", "Semanal"), ("mensual", "Mensual")],
        default="semanal",
        help_text="Con qué frecuencia debe rendir cuentas al municipio."
    )

    # 🎭 Roles
    es_conductor = models.BooleanField(default=True)
    es_inspector = models.BooleanField(default=False)
    es_vendedor = models.BooleanField(default=False)
    es_admin = models.BooleanField(default=False)

    # ✅ Verificación de identidad del conductor (aprobada por el admin)
    es_verificado = models.BooleanField(
        default=False,
        help_text="El admin verificó la identidad del conductor."
    )

    # 🔐 Django admin / permisos
    #is_staff → acceso admin Django
    #es_admin → lógica de negocio
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "correo"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    @property
    def nombre(self):
        """Alias de first_name para consistencia con el sistema."""
        return self.first_name or ""

    @nombre.setter
    def nombre(self, valor):
        self.first_name = valor

    def __str__(self):
        return self.correo or f"Usuario #{self.id}"

class Municipio(models.Model):
    nombre = models.CharField(max_length=100, blank=True)
    apellido = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)

    # ── Branding por municipio ────────────────────────────────────────────────
    # El admin carga el logo y elige los colores; cada municipio tiene su propia
    # identidad visual sin tocar el código.
    logo = models.ImageField(
        upload_to="municipios/logos/",
        null=True, blank=True,
        verbose_name="Logo del municipio",
        help_text="Imagen PNG/SVG con fondo transparente. Altura recomendada: 80px.",
    )
    color_primario = models.CharField(
        max_length=7, default="#1a7a3c",
        verbose_name="Color primario",
        help_text="Color principal de la barra de navegación y botones (ej: #1a7a3c).",
    )
    color_secundario = models.CharField(
        max_length=7, default="#155f2e",
        verbose_name="Color secundario",
        help_text="Color de hover y acento (ej: #155f2e). Suele ser el primario más oscuro.",
    )
    nombre_sistema = models.CharField(
        max_length=200, blank=True,
        default="Estacionamiento Medido",
        verbose_name="Nombre del sistema",
        help_text="Texto que aparece en la barra de navegación si no hay logo.",
    )

    def __str__(self):
        return self.nombre
    
# 🚗 Vehículo asociado a uno o varios usuarios
TIPOS_EXENCION = [
    ("discapacitado",    "Discapacitado"),
    ("vecino_frentista", "Vecino frentista"),
    ("jubilado",         "Jubilado"),
    ("fuerza",           "Fuerzas de seguridad / Policía"),
    ("vehiculo_oficial", "Vehículo oficial"),
]

class Vehiculo(models.Model):
    patente = models.CharField(max_length=10, unique=True)
    exento_global = models.BooleanField(default=False)
    exento_parcial = models.BooleanField(default=False)
    subcuadras_exentas = models.ManyToManyField("Subcuadra", blank=True)
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)

    # Motivo de la exención (admin lo carga al aprobar)
    tipo_exencion = models.CharField(
        max_length=30, choices=TIPOS_EXENCION,
        null=True, blank=True,
        verbose_name="Tipo de exención"
    )
    notas_exencion = models.TextField(
        null=True, blank=True,
        verbose_name="Notas (nro de documento, certificado, etc.)"
    )

    def __str__(self):
        return self.patente

    def esta_exento_en(self, subcuadra):
        if self.exento_global:
            return True
        return self.subcuadras_exentas.filter(id=subcuadra.id).exists()   

class VehiculoUsuario(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)

    es_propietario = models.BooleanField(default=False)
    verificado = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if self.es_propietario:
            VehiculoUsuario.objects.filter(
                vehiculo=self.vehiculo,
                es_propietario=True
            ).exclude(id=self.id).update(es_propietario=False)

        super().save(*args, **kwargs)

# 🏙️ Subcuadra representa una altura específica de una calle
class Subcuadra(models.Model):
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    calle = models.CharField(max_length=100)
    altura = models.IntegerField()

    class Meta:
        unique_together = ("calle", "altura")

    def __str__(self):
        # Zona Única (altura=0) no muestra el número
        if self.altura == 0:
            return self.calle
        return f"{self.calle} {self.altura}"
    
class Estado(models.TextChoices):
    ACTIVO = "ACTIVO", "Activo"
    FINALIZADO = "FINALIZADO", "Finalizado"

# 💰 Tarifa por hora de estacionamiento
class Tarifa(models.Model):
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    precio_por_hora = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"${self.precio_por_hora}/hora"

class Estacionamiento(models.Model):
    vehiculo = models.ForeignKey("Vehiculo", on_delete=models.CASCADE)
    subcuadra = models.ForeignKey("Subcuadra", on_delete=models.PROTECT)

    usuario = models.ForeignKey(
        "Usuario",
        on_delete=models.PROTECT,
        null=True
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ACTIVO
    )

    hora_inicio = models.DateTimeField(auto_now_add=True)
    hora_fin = models.DateTimeField(null=True, blank=True)

    duracion_min = models.IntegerField(default=60)

    costo_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    @property
    def activo(self):
        return self.estado == Estado.ACTIVO

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["vehiculo"],
                condition=Q(estado="ACTIVO"),
                name="unique_estacionamiento_activo_por_vehiculo",
            )
        ]

class MovimientoCaja(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10)  # egreso / ingreso
    descripcion = models.TextField(blank=True, null=True)
    cerrado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            original = MovimientoCaja.objects.get(pk=self.pk)
            if original.cerrado:
                raise Exception("No se puede modificar un movimiento cerrado")
        super().save(*args, **kwargs)
    
class CierreCaja(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)

    total_cobrado = models.DecimalField(max_digits=10, decimal_places=2)

    fecha_apertura = models.DateTimeField()
    fecha_cierre = models.DateTimeField(auto_now_add=True)

    cantidad_movimientos = models.IntegerField(default=0)

    # auditoria
    creado_en = models.DateTimeField(default=timezone.now)
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="cierres_creados")

    def __str__(self):
        return f"Cierre {self.usuario} - {self.total_cobrado}"

class VerificacionInspector(models.Model):
    inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    infraccion_generada = models.BooleanField(default=False)
    resultado = models.CharField(max_length=50)

class Infraccion(models.Model):
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=[("pendiente", "Pendiente"), ("pagada", "Pagada"), ("anulada", "Anulada")], default="pendiente")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE, null=True, blank=True)
    estacionamiento = models.ForeignKey(Estacionamiento, on_delete=models.SET_NULL, null=True, blank=True)
    motivo = models.CharField(max_length=255, default="Impago")
    foto = models.ImageField(upload_to="infracciones/", null=True, blank=True)
    qr_code = models.CharField(max_length=255, null=True, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creado_en = models.DateTimeField(auto_now_add=True)   # única fecha de creación
    fecha_pago = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.municipio:
            if self.inspector and self.inspector.municipio:
                self.municipio = self.inspector.municipio
            elif self.subcuadra and self.subcuadra.municipio:
                self.municipio = self.subcuadra.municipio

        super().save(*args, **kwargs)

# 🔔 Notificación enviada a un usuario
# 📅 Horario de cobro semanal por municipio
class HorarioEstacionamiento(models.Model):
    DIAS = [
        (0, "Lunes"), (1, "Martes"), (2, "Miércoles"),
        (3, "Jueves"), (4, "Viernes"), (5, "Sábado"), (6, "Domingo"),
    ]

    municipio    = models.ForeignKey(Municipio, on_delete=models.CASCADE)
    dia_semana   = models.IntegerField(choices=DIAS)
    hora_inicio  = models.TimeField()
    hora_fin     = models.TimeField()
    activo       = models.BooleanField(default=True)

    class Meta:
        unique_together = ("municipio", "dia_semana")
        ordering = ["dia_semana"]

    def __str__(self):
        estado = "✅" if self.activo else "❌"
        return f"{estado} {self.get_dia_semana_display()} {self.hora_inicio}–{self.hora_fin}"


# 📌 Días especiales: feriados, festivos, duelos (anulan el horario semanal)
class DiaEspecial(models.Model):
    TIPOS = [
        ("feriado",  "Feriado nacional"),
        ("festivo",  "Festivo local"),
        ("duelo",    "Duelo / Luto"),
        ("otro",     "Otro"),
    ]

    municipio     = models.ForeignKey(Municipio, on_delete=models.CASCADE)
    fecha         = models.DateField()
    tipo          = models.CharField(max_length=20, choices=TIPOS, default="feriado")
    descripcion   = models.CharField(max_length=200)
    cobro_activo  = models.BooleanField(
        default=False,
        verbose_name="¿Se cobra ese día?",
        help_text="Por defecto los días especiales son libres de cobro."
    )

    class Meta:
        unique_together = ("municipio", "fecha")
        ordering = ["fecha"]

    def __str__(self):
        return f"{self.fecha} — {self.descripcion}"


class Notificacion(models.Model):
    destinatario = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # Usuario
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)

    def __str__(self):
        # Usamos 'correo' porque los tests esperan ese campo en Usuario
        return f"Notificación para {self.destinatario.correo}"


class SolicitudVerificacion(models.Model):
    """
    Solicitud de verificación de identidad (y opcionalmente de exención)
    que un conductor envía para que el admin la revise.

    Flujo de identidad:
      conductor llena formulario → estado=pendiente
      admin aprueba → estado=aprobada → usuario.es_verificado=True
      admin rechaza → estado=rechazada + notas_admin

    Flujo de exención (opcional, dentro de la misma solicitud):
      conductor marca solicita_exencion=True, elige tipo y vehículo, adjunta docs
      admin aprueba → estado_exencion=aprobada → setea exención en vehiculo
      admin rechaza → estado_exencion=rechazada + notas_exencion_admin

    Documentos requeridos según tipo:
      discapacidad  → documento_1 = CUD
      frentista     → documento_1 = licencia de conducir
                      documento_2 = cédula del domicilio
    """
    ESTADOS = [
        ("pendiente",  "Pendiente"),
        ("aprobada",   "Aprobada"),
        ("rechazada",  "Rechazada"),
    ]

    TIPOS_EXENCION_SOLICITADOS = [
        ("discapacidad",     "Discapacidad (CUD)"),
        ("vecino_frentista", "Vecino frentista"),
    ]

    # ── Identidad ────────────────────────────────────────────────────────────
    usuario         = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name="solicitud_verificacion"
    )
    nombre          = models.CharField(max_length=100, verbose_name="Nombre")
    apellido        = models.CharField(max_length=100, verbose_name="Apellido")
    dni             = models.CharField(max_length=20,  verbose_name="DNI")
    telefono        = models.CharField(max_length=30, blank=True, verbose_name="Teléfono")
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    estado          = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    notas_admin     = models.TextField(
        blank=True,
        verbose_name="Notas del admin (identidad)",
        help_text="Motivo de rechazo de identidad u observaciones."
    )

    # ── Exención (opcional) ───────────────────────────────────────────────────
    solicita_exencion = models.BooleanField(
        default=False,
        verbose_name="¿Solicita exención?",
    )
    tipo_exencion_solicitado = models.CharField(
        max_length=30,
        choices=TIPOS_EXENCION_SOLICITADOS,
        blank=True,
        verbose_name="Tipo de exención solicitada",
    )
    vehiculo = models.ForeignKey(
        "Vehiculo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_exencion",
        verbose_name="Vehículo a exentar",
    )
    # documento_1:
    #   discapacidad  → CUD
    #   frentista     → Licencia de conducir
    documento_1 = models.FileField(
        upload_to="solicitudes_verificacion/",
        null=True,
        blank=True,
        verbose_name="Documento principal",
    )
    # documento_2:
    #   frentista     → Cédula con domicilio en zona de estacionamiento
    #   discapacidad  → no se usa
    documento_2 = models.FileField(
        upload_to="solicitudes_verificacion/",
        null=True,
        blank=True,
        verbose_name="Cédula / domicilio (solo frentista)",
    )
    estado_exencion = models.CharField(
        max_length=20,
        choices=ESTADOS,
        blank=True,
        default="",
        verbose_name="Estado de la exención",
    )
    notas_exencion_admin = models.TextField(
        blank=True,
        verbose_name="Notas del admin (exención)",
        help_text="Motivo de rechazo de la exención."
    )

    class Meta:
        ordering = ["-fecha_solicitud"]
        verbose_name = "Solicitud de verificación"
        verbose_name_plural = "Solicitudes de verificación"

    def __str__(self):
        return f"{self.usuario} — {self.estado}"