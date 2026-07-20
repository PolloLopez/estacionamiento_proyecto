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

    # ── Datos adicionales para inspectores ──────────────────────────────────
    telefono         = models.CharField(max_length=30, blank=True, default="",
                           verbose_name="Teléfono de contacto")
    numero_dni       = models.CharField(max_length=20, blank=True, default="",
                           verbose_name="Número de DNI")
    numero_legajo    = models.CharField(max_length=30, blank=True, default="",
                           verbose_name="Número de legajo", help_text="Opcional")

    # ── Datos adicionales para vendedores / kioscos ─────────────────────────
    nombre_propietario = models.CharField(max_length=200, blank=True, default="",
                             verbose_name="Nombre del propietario")
    documento_cuil     = models.CharField(max_length=20, blank=True, default="",
                             verbose_name="Documento / CUIL")
    horario_atencion   = models.CharField(max_length=200, blank=True, default="",
                             verbose_name="Horarios de atención",
                             help_text="Ej: Lun-Vie 9-18, Sáb 9-13")

    es_conductor = models.BooleanField(default=True)
    es_inspector = models.BooleanField(default=False)
    es_vendedor = models.BooleanField(default=False)
    es_admin     = models.BooleanField(default=False)
    es_tesorero  = models.BooleanField(default=False)

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

    @property
    def apellido(self):
        """Alias de last_name para consistencia con el sistema."""
        return self.last_name or ""

    @apellido.setter
    def apellido(self, valor):
        self.last_name = valor

    def nombre_completo(self):
        """Devuelve nombre y apellido, o correo si no tiene datos."""
        partes = [self.first_name, self.last_name]
        completo = " ".join(p for p in partes if p)
        return completo or self.correo or f"Usuario #{self.id}"

    def __str__(self):
        return self.correo or f"Usuario #{self.id}"

class Municipio(models.Model):
    nombre = models.CharField(max_length=100, blank=True)
    apellido = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)

    # Configuración de negocio
    comision_vendedor = models.DecimalField(
        max_digits=5, decimal_places=2, default=7,
        verbose_name='Comisión vendedor (%)',
        help_text='Porcentaje que retiene el vendedor de cada cobro.',
    )
    tolerancia_multa_minutos = models.IntegerField(
        default=5,
        verbose_name='Tolerancia multa (min)',
        help_text='Minutos de gracia: si el conductor paga la multa dentro de este plazo, se cancela automáticamente.',
    )

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

    TIPOS_VEHICULO = [('auto', 'Auto'), ('moto', 'Moto')]
    tipo = models.CharField(
        max_length=10, choices=TIPOS_VEHICULO, default='auto',
        verbose_name='Tipo de vehículo',
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

    # Monto fijo que se aplica a cada infracción generada por inspectores.
    # El admin lo configura desde Tarifas. El inspector no puede modificarlo.
    monto_infraccion = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Monto fijo cobrado por cada infracción."
    )

    # Tarifa para motos (precio por hora). null = usar tarifa de autos.
    precio_por_hora_moto = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        verbose_name="Precio/hora moto",
        help_text="Tarifa por hora para motos. Vacío = igual que autos.",
    )

    # Abono mensual
    precio_abono_auto = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name="Precio abono mensual (auto)",
    )
    precio_abono_moto = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name="Precio abono mensual (moto)",
    )

    def __str__(self):
        return f"${self.precio_por_hora}/hora | infracción: ${self.monto_infraccion}"

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

    duracion_horas = models.IntegerField(default=1, verbose_name="Duración (horas)")

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
    medio_pago = models.CharField(
        max_length=20, default='efectivo',
        choices=[('efectivo', 'Efectivo'), ('mercadopago', 'MercadoPago')],
        verbose_name='Medio de pago',
    )
    comision_monto = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Comisión generada',
        help_text='Monto que retiene el vendedor como comisión en este movimiento.',
    )

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

    # auditoria — quién generó el cierre
    creado_en = models.DateTimeField(default=timezone.now)
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="cierres_creados")

    # 💰 Comisión aplicada al momento del cierre (snapshot)
    porcentaje_ganancia_aplicado = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Porcentaje de ganancia del usuario al momento del cierre."
    )
    ganancia_usuario = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Monto que retiene el usuario (comisión)."
    )
    monto_municipio = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Monto neto que le corresponde al municipio."
    )

    # período declarado por el vendedor al cerrar
    PERIODOS = [('diario', 'Diario'), ('semanal', 'Semanal'), ('mensual', 'Mensual')]
    periodo = models.CharField(
        max_length=10, choices=PERIODOS, blank=True, default='',
        verbose_name='Período',
    )

    # certificación por el admin
    certificado = models.BooleanField(default=False, help_text="El admin auditó y certificó este cierre.")
    certificado_en = models.DateTimeField(null=True, blank=True, help_text="Fecha en que el admin certificó el cierre.")
    certificado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cierres_certificados",
        help_text="Admin que certificó el cierre.",
    )

    class Meta:
        ordering = ["-fecha_cierre"]

    def __str__(self):
        estado = "✅" if self.certificado else "⏳"
        return f"{estado} Cierre {self.usuario} — ${self.total_cobrado} ({self.fecha_cierre:%d/%m/%Y})"

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
    # Motivo requerido cuando el admin anula una infracción desde el panel
    motivo_anulacion = models.TextField(blank=True, default="")

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

# 🗓️ Abono mensual de estacionamiento por vehículo
class AbonoMensual(models.Model):
    """
    Habilita a un vehículo para estacionar libremente durante un mes
    sin necesidad de registrar cada sesión.
    El inspector ve 'abono activo' al verificar la patente.
    """
    MEDIOS_PAGO = [('efectivo', 'Efectivo'), ('mercadopago', 'MercadoPago'), ('saldo', 'Saldo digital')]

    vehiculo    = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='abonos')
    municipio   = models.ForeignKey(Municipio, on_delete=models.CASCADE, related_name='abonos')
    # Primer día del mes al que corresponde el abono (ej: 2026-07-01)
    mes         = models.DateField(verbose_name='Mes del abono')
    monto       = models.DecimalField(max_digits=10, decimal_places=2)
    medio_pago  = models.CharField(max_length=20, choices=MEDIOS_PAGO, default='efectivo')
    vendedor    = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='abonos_cobrados',
        help_text='Vendedor/kiosco que cobró el abono (null si fue digital).',
    )
    conductor   = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='abonos_contratados',
        help_text='Conductor que contrató el abono (null si lo cargó el vendedor sin usuario).',
    )
    movimiento_caja = models.ForeignKey(
        MovimientoCaja, on_delete=models.SET_NULL, null=True, blank=True,
    )
    creado_en   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vehiculo', 'municipio', 'mes')
        ordering = ['-mes']
        verbose_name = 'Abono mensual'
        verbose_name_plural = 'Abonos mensuales'

    @property
    def esta_activo(self):
        """True si el abono corresponde al mes actual."""
        hoy = timezone.localdate()
        return self.mes.year == hoy.year and self.mes.month == hoy.month

    def __str__(self):
        return f"{self.vehiculo.patente} — {self.mes.strftime('%B %Y')}"


# 📊 Rendición de cuentas del admin a Tesorería
class Rendicion(models.Model):
    """
    El admin cierra un período y genera una rendición con el desglose
    de efectivo vs. digital y las comisiones de vendedores.
    El tesorero puede ver, observar o validar cada rendición.
    """
    PERIODOS = [('diario', 'Diario'), ('semanal', 'Semanal'), ('mensual', 'Mensual')]
    ESTADOS  = [
        ('pendiente',  'Pendiente de validación'),
        ('validada',   'Validada por tesorería'),
        ('observada',  'Con observaciones'),
    ]

    municipio    = models.ForeignKey(Municipio, on_delete=models.CASCADE, related_name='rendiciones')
    admin        = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name='rendiciones_generadas',
    )
    periodo      = models.CharField(max_length=10, choices=PERIODOS)
    fecha_desde  = models.DateField()
    fecha_hasta  = models.DateField()

    # Totales (se calculan al generar la rendición y quedan como snapshot)
    total_efectivo    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_digital     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_comisiones  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_neto        = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Total a rendir = efectivo + digital - comisiones.',
    )

    estado          = models.CharField(max_length=15, choices=ESTADOS, default='pendiente')
    notas_tesorero  = models.TextField(blank=True, verbose_name='Observaciones del tesorero')

    creado_en    = models.DateTimeField(auto_now_add=True)
    tesorero     = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rendiciones_validadas',
    )
    validado_en  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Rendición'
        verbose_name_plural = 'Rendiciones'

    def __str__(self):
        return f"{self.get_periodo_display()} {self.fecha_desde} → {self.fecha_hasta} [{self.get_estado_display()}]"


# 💰 Liquidación de comisiones a vendedores
class LiquidacionComision(models.Model):
    """
    Representa el pago de comisiones acumuladas de un vendedor para un período.

    Flujo:
      1. Las comisiones se acumulan en MovimientoCaja.comision_monto al cobrar.
      2. Al cerrar una rendición, Tesorería genera una LiquidacionComision
         por cada vendedor del período (sum de sus comision_monto).
      3. Tesorería marca como 'depositada' cuando transfiere el dinero al vendedor.
      4. El vendedor certifica que recibió el monto correctamente.
    """
    ESTADOS = [
        ('pendiente',   'Pendiente de depósito'),
        ('depositada',  'Depositada por tesorería'),
        ('certificada', 'Certificada por el vendedor'),
    ]

    vendedor     = models.ForeignKey(
        Usuario, on_delete=models.PROTECT,
        related_name='liquidaciones_comision',
    )
    municipio    = models.ForeignKey(Municipio, on_delete=models.CASCADE)
    rendicion    = models.ForeignKey(
        'Rendicion', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='liquidaciones',
        help_text='Rendición que originó esta liquidación.',
    )
    fecha_desde  = models.DateField()
    fecha_hasta  = models.DateField()
    monto_total  = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text='Suma de comisiones del período.',
    )
    estado       = models.CharField(max_length=15, choices=ESTADOS, default='pendiente')

    # Tesorería deposita
    depositada_en  = models.DateTimeField(null=True, blank=True)
    depositada_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='liquidaciones_depositadas',
    )
    notas_tesorero = models.TextField(blank=True)

    # Vendedor certifica recibo
    certificada_en = models.DateTimeField(null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Liquidación de comisión'
        verbose_name_plural = 'Liquidaciones de comisión'

    def __str__(self):
        return f"{self.vendedor} — ${self.monto_total} [{self.get_estado_display()}]"
