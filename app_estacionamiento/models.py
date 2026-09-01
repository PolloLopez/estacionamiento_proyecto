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
        # PROTECT: no permite borrar un municipio que tenga usuarios.
        # Era CASCADE y borrar el municipio destruía todos sus usuarios silenciosamente.
        on_delete=models.PROTECT,
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
    # El admin puede deshabilitar por vendedor si no debe gestionar abonos mensuales.
    puede_vender_abono = models.BooleanField(
        default=True,
        verbose_name="Puede vender abono mensual",
        help_text="Si está deshabilitado, el vendedor no verá la opción de cobrar abono."
    )

    # ── Datos adicionales para conductores ──────────────────────────────────
    # Fundamental para identificar frentistas y eventualmente el módulo de reintegro.
    domicilio = models.CharField(
        max_length=255, blank=True, default="",
        verbose_name="Domicilio",
        help_text="Dirección del conductor. Requerido para exención de frentista."
    )

    es_conductor   = models.BooleanField(default=True)
    es_inspector   = models.BooleanField(default=False)
    es_vendedor    = models.BooleanField(default=False)
    es_admin       = models.BooleanField(default=False)
    es_tesorero    = models.BooleanField(default=False)
    # Superadmin global: no pertenece a ningún municipio, gestiona todo el sistema.
    # municipio = null para este rol.
    es_superadmin  = models.BooleanField(default=False)

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
    minutos_entre_infracciones = models.PositiveIntegerField(
        default=15,
        verbose_name='Minutos entre infracciones (mismo vehículo)',
        help_text='Tiempo mínimo antes de poder infraccionar de nuevo al mismo vehículo. Defecto: 15 min.',
    )
    monto_minimo_carga = models.PositiveIntegerField(
        default=500,
        verbose_name='Monto mínimo de carga MP ($)',
        help_text='Monto mínimo que puede cargar un conductor via MercadoPago.',
    )
    monto_maximo_carga = models.PositiveIntegerField(
        default=50000,
        verbose_name='Monto máximo de carga MP ($)',
        help_text='Monto máximo que puede cargar un conductor via MercadoPago en una sola operación.',
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
    icono_app = models.ImageField(
        upload_to="municipios/iconos/",
        null=True, blank=True,
        verbose_name="Ícono de la app (acceso directo)",
        help_text="PNG cuadrado, mínimo 192×192px. Aparece como ícono al instalar la PWA en el celular.",
    )
    color_primario = models.CharField(
        max_length=7, default="#1a7a3c",
        verbose_name="Color primario",
        help_text="Color principal de la barra de navegación y botones (ej: #1a7a3c).",
    )
    color_secundario = models.CharField(
        max_length=7, default="#444444",
        verbose_name="Color secundario",
        help_text="Color del footer y textos de soporte (ej: #444444).",
    )
    color_acento = models.CharField(
        max_length=7, default="#bed630",
        verbose_name="Color acento",
        help_text="Color de botones secundarios y highlights (ej: #bed630).",
        blank=True,
    )
    nombre_sistema = models.CharField(
        max_length=200, blank=True,
        default="Estacionamiento Medido",
        verbose_name="Nombre del sistema",
        help_text="Texto que aparece en la barra de navegación si no hay logo.",
    )

    # ── Información institucional ────────────────────────────────────────────
    # Textos que el superadmin puede configurar para cada municipio.
    # Se muestran en el conductor home y/o la landing pública.
    leyenda_horarios = models.TextField(
        blank=True, default="",
        verbose_name="Leyenda de horarios",
        help_text="Ej: Lunes a viernes de 8 a 20 hs · Sábados de 8 a 13 hs.",
    )
    texto_ordenanza = models.TextField(
        blank=True, default="",
        verbose_name="Marco legal / Ordenanza",
        help_text="Ej: Ordenanza N° 1234/2023 — Estacionamiento Medido Municipal.",
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

    # Fecha hasta la que rige la exención (opcional; None = indefinida)
    vigencia_exencion = models.DateField(
        null=True, blank=True,
        verbose_name="Vigencia de exención",
        help_text="Fecha hasta la que rige la exención. Vacío = sin vencimiento.",
    )

    # Datos del titular del SIA — se completan automáticamente al verificar el QR de ANDIS.
    # Permiten al admin consultar y filtrar vehículos exentos por titular/DNI sin abrir cada uno.
    sia_titular_nombre   = models.CharField(max_length=100, blank=True, default="", verbose_name="Nombre titular SIA")
    sia_titular_apellido = models.CharField(max_length=100, blank=True, default="", verbose_name="Apellido titular SIA")
    sia_titular_dni      = models.CharField(max_length=15,  blank=True, default="", verbose_name="DNI titular SIA")
    sia_nci              = models.CharField(max_length=30,  blank=True, default="", verbose_name="NCI verificación SIA")

    # Marca si el admin ya revisó y completó los datos de la exención.
    # Los vehículos importados desde Excel arrancan con False (pendientes de
    # que el admin contacte al titular para completar email, condición, etc.)
    # Los cargados manualmente desde panel_exenciones arrancan en True.
    exencion_verificada = models.BooleanField(
        default=True,
        verbose_name="Exención verificada",
        help_text="False = importado, pendiente de verificación por el admin.",
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

    # Coordenadas del centroide de la cuadra.
    # Opcionales: cuando están cargadas, el inspector puede usar GPS para
    # preseleccionar su subcuadra automáticamente desde verificar.html.
    lat = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        verbose_name='Latitud',
    )
    lon = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        verbose_name='Longitud',
    )

    class Meta:
        # municipio incluido: distintos municipios pueden tener la misma calle+altura
        unique_together = ("municipio", "calle", "altura")

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

    precio_por_hora = models.DecimalField(max_digits=10, decimal_places=2)

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

    # DecimalField con 1 decimal para soportar medias horas (1.5h, 2.5h, etc.)
    # Antes era IntegerField, lo que truncaba Decimal("1.5") → 1 silenciosamente,
    # haciendo que el estacionamiento venciera 30 min antes de lo pagado.
    duracion_horas = models.DecimalField(
        max_digits=4, decimal_places=1, default=1,
        verbose_name="Duración (horas)"
    )

    costo_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    @property
    def activo(self):
        return self.estado == Estado.ACTIVO

    @property
    def hora_vencimiento(self):
        """
        Hora estimada de vencimiento para estacionamientos ACTIVOS.
        Se calcula como hora_inicio + duracion_horas.
        No reemplaza hora_fin (que se registra al finalizar el turno),
        sino que sirve para mostrar cuándo vence visualmente.
        """
        from datetime import timedelta
        if self.hora_inicio and self.duracion_horas:
            return self.hora_inicio + timedelta(hours=float(self.duracion_horas))
        return None

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["vehiculo"],
                condition=Q(estado="ACTIVO"),
                name="unique_estacionamiento_activo_por_vehiculo",
            )
        ]

class MovimientoCaja(models.Model):
    # PROTECT: no permite borrar un usuario que tenga movimientos de caja (historial contable).
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    TIPOS = [("ingreso", "Ingreso"), ("egreso", "Egreso")]
    tipo = models.CharField(max_length=10, choices=TIPOS)
    descripcion = models.TextField(blank=True, null=True)
    cerrado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    MEDIOS_PAGO = [
        ('efectivo',      'Efectivo'),
        ('transferencia', 'Transferencia bancaria'),
        ('debito',        'Débito'),
        ('credito',       'Crédito'),
        ('qr',            'QR'),
        ('mercadopago',   'MercadoPago'),
    ]
    medio_pago = models.CharField(
        max_length=20, default='efectivo',
        choices=MEDIOS_PAGO,
        verbose_name='Medio de pago',
    )
    comision_monto = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Comisión generada',
        help_text='Monto que retiene el vendedor como comisión en este movimiento.',
    )
    # ID del pago en MercadoPago. Solo se usa para cobros via MP (webhook/exitoso).
    # Permite verificar idempotencia con una query exacta en lugar de LIKE sobre
    # la descripción, que es frágil ante cambios de formato.
    # unique=True garantiza a nivel DB que no se acredite el mismo pago dos veces.
    mp_payment_id = models.CharField(
        max_length=50, null=True, blank=True, unique=True,
        verbose_name='ID de pago MercadoPago',
    )

    def save(self, *args, **kwargs):
        if self.pk:
            # values_list trae solo el booleano "cerrado" en vez del objeto completo.
            # Evita una query SELECT * innecesaria cuando lo único que necesitamos
            # es chequear ese campo.
            cerrado = MovimientoCaja.objects.filter(pk=self.pk).values_list("cerrado", flat=True).first()
            if cerrado:
                raise Exception("No se puede modificar un movimiento cerrado")
        super().save(*args, **kwargs)
    
class CierreCaja(models.Model):
    # PROTECT: no permite borrar un usuario que tenga cierres de caja (historial contable).
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)

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

    # Desglose por medio de pago (calculado automáticamente al cerrar caja)
    total_efectivo = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Total cobrado en efectivo.",
    )
    total_transferencia = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Total cobrado por transferencia bancaria.",
    )
    total_digital = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Total cobrado por débito/crédito/QR (va directo a tesorería).",
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

    # Rendición a la que pertenece este cierre (null = aún no rendido)
    rendicion = models.ForeignKey(
        'Rendicion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cierres',
        help_text="Rendición en la que se incluyó este cierre. Null = pendiente de rendir.",
    )

    class Meta:
        ordering = ["-fecha_cierre"]

    def __str__(self):
        estado = "✅" if self.certificado else "⏳"
        return f"{estado} Cierre {self.usuario} — ${self.total_cobrado} ({self.fecha_cierre:%d/%m/%Y})"

class VerificacionInspector(models.Model):
    inspector = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    vehiculo  = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE)
    fecha     = models.DateTimeField(auto_now_add=True)
    infraccion_generada = models.BooleanField(default=False)
    # "verificado" es el único valor que se guarda actualmente.
    # choices documentan los valores válidos sin depender de texto libre.
    RESULTADOS = [("verificado", "Verificado")]
    resultado  = models.CharField(max_length=50, choices=RESULTADOS, default="verificado")

    class Meta:
        indexes = [
            # Índice compuesto para la query más frecuente sobre esta tabla:
            #   filter(vehiculo=v).order_by("-fecha").first()
            # Sin este índice, Postgres ordena todos los registros del vehículo en memoria.
            # Con ~75.000 registros/año (3 inspectores × 100 checks/día × 250 días),
            # el impacto se nota antes del primer año en producción municipal.
            models.Index(fields=["vehiculo", "-fecha"], name="idx_verif_vehiculo_fecha"),
        ]

class Infraccion(models.Model):
    # SET_NULL: desnormalización intencional para queries sin JOIN con inspector.
    # Si el municipio se borra, la infracción queda sin municipio en vez de borrarse.
    municipio = models.ForeignKey(Municipio, on_delete=models.SET_NULL, null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=[("pendiente", "Pendiente"), ("pagada", "Pagada"), ("anulada", "Anulada")],
        default="pendiente",
    )
    # PROTECT: no permite borrar un vehículo o inspector con infracciones (historial contable).
    vehiculo  = models.ForeignKey(Vehiculo, on_delete=models.PROTECT)
    inspector = models.ForeignKey(Usuario,  on_delete=models.PROTECT)
    subcuadra = models.ForeignKey(Subcuadra, on_delete=models.CASCADE, null=True, blank=True)
    estacionamiento = models.ForeignKey(Estacionamiento, on_delete=models.SET_NULL, null=True, blank=True)
    motivo = models.CharField(max_length=255, default="Impago")
    foto   = models.ImageField(upload_to="infracciones/", null=True, blank=True)
    # qr_code eliminado: campo muerto desde migración 0008, nunca se usó.
    monto  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creado_en = models.DateTimeField(auto_now_add=True)   # única fecha de creación
    fecha_pago = models.DateTimeField(null=True, blank=True)
    # Motivo requerido cuando el admin anula una infracción desde el panel
    motivo_anulacion = models.TextField(blank=True, default="")

    # ── Verificación SIA (Símbolo Internacional de Acceso / ANDIS) ──────────
    # Se completan cuando el inspector escanea el QR del SIA durante la fiscalización.
    # Permite auditar si el SIA fue presentado, verificado y con qué resultado.
    sia_presentado    = models.BooleanField(default=False)
    sia_verificado    = models.BooleanField(default=False)
    sia_estado        = models.CharField(max_length=40, blank=True, default="")
    sia_url           = models.CharField(max_length=500, blank=True, default="")
    sia_code          = models.CharField(max_length=100, blank=True, default="")
    sia_patente_sia   = models.CharField(max_length=20, blank=True, default="")
    sia_vencimiento   = models.DateField(null=True, blank=True)
    sia_nci           = models.CharField(max_length=30, blank=True, default="")
    sia_titular       = models.CharField(max_length=200, blank=True, default="")
    sia_verificado_en = models.DateTimeField(null=True, blank=True)
    # Observación automática generada cuando el SIA no pudo verificarse
    sia_observacion   = models.TextField(blank=True, default="")

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


# 💳 Pago público anónimo vía MercadoPago
class PagoPublico(models.Model):
    """
    Registra el intento de pago de una infracción, estacionamiento o abono
    realizado por una persona sin cuenta en el sistema.

    Ciclo de vida:
    1. Se crea en estado 'pendiente' al iniciar el checkout de MP.
    2. Al confirmar MP (callback o webhook), pasa a 'aprobado' y se ejecuta
       la acción: marcar infracción como pagada / crear Estacionamiento / crear AbonoMensual.
    3. Si MP rechaza o el usuario cancela, pasa a 'fallido'.

    La FK correspondiente al tipo se llena solo al confirmar el pago:
    - tipo='infraccion'      → infraccion FK
    - tipo='estacionamiento' → estacionamiento FK (+ subcuadra + duracion_horas en la preferencia)
    - tipo='abono'           → abono FK (+ mes_abono en la preferencia)
    """
    TIPOS = [
        ('infraccion',      'Infracción'),
        ('estacionamiento', 'Estacionamiento'),
        ('abono',           'Abono mensual'),
    ]
    ESTADOS = [
        ('pendiente', 'Pendiente de pago'),
        ('aprobado',  'Pagado'),
        ('fallido',   'Fallido o cancelado'),
    ]

    tipo             = models.CharField(max_length=20, choices=TIPOS)
    estado           = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    municipio        = models.ForeignKey('Municipio', on_delete=models.PROTECT,
                                          related_name='pagos_publicos')
    patente          = models.CharField(max_length=10, verbose_name='Patente del vehículo')
    monto            = models.DecimalField(max_digits=10, decimal_places=2)
    email_contacto   = models.CharField(max_length=254, blank=True, default='',
                                         verbose_name='Email para comprobante (opcional)')
    mp_preference_id = models.CharField(max_length=100, blank=True, default='',
                                         verbose_name='ID preferencia MercadoPago')
    mp_payment_id    = models.CharField(max_length=50, null=True, blank=True, unique=True,
                                         verbose_name='ID pago MercadoPago')
    creado_en        = models.DateTimeField(auto_now_add=True)
    procesado_en     = models.DateTimeField(null=True, blank=True,
                                             verbose_name='Fecha de procesamiento por MP')

    # FKs opcionales según tipo — solo se llena la correspondiente
    infraccion      = models.ForeignKey('Infraccion', on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='pagos_publicos')
    estacionamiento = models.ForeignKey('Estacionamiento', on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='pagos_publicos')
    abono           = models.ForeignKey('AbonoMensual', on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='pagos_publicos')

    # Datos necesarios para crear el Estacionamiento al confirmar el pago
    subcuadra      = models.ForeignKey('Subcuadra', on_delete=models.SET_NULL,
                                        null=True, blank=True)
    duracion_horas = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    # Primer día del mes del abono (ej: 2026-08-01)
    mes_abono = models.DateField(null=True, blank=True,
                                  verbose_name='Mes del abono (primer día)')

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Pago público'
        verbose_name_plural = 'Pagos públicos'
        indexes = [
            models.Index(fields=['patente', 'estado'], name='idx_pagopub_patente_estado'),
            models.Index(fields=['mp_payment_id'],     name='idx_pagopub_payment_id'),
        ]

    def __str__(self):
        return f"{self.tipo} {self.patente} — {self.estado} — ${self.monto}"


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

    # Totales: auto-calculados desde los CierreCaja vinculados al crear la rendición
    total_efectivo  = models.DecimalField(max_digits=12, decimal_places=2, default=0,
        help_text='Suma del efectivo de todos los cierres incluidos.')
    total_digital   = models.DecimalField(max_digits=12, decimal_places=2, default=0,
        help_text='Total no efectivo (transferencia + débito + crédito + QR) de los cierres incluidos.')
    total_neto      = models.DecimalField(max_digits=12, decimal_places=2, default=0,
        help_text='Total a rendir = efectivo + digital. Las comisiones las gestiona tesorería aparte.')

    # Comprobante de transferencia (si parte del pago fue por transferencia)
    comprobante_archivo = models.FileField(
        upload_to='comprobantes_rendicion/', null=True, blank=True,
        help_text='Comprobante de transferencia bancaria (si aplica).',
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

    # Factura del vendedor (requerida para la liquidación de comisiones)
    factura_presentada = models.BooleanField(
        default=False,
        help_text='El vendedor presentó factura por sus comisiones.',
    )
    factura_archivo = models.FileField(
        upload_to='facturas_comision/', null=True, blank=True,
        help_text='Archivo de la factura presentada.',
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Liquidación de comisión'
        verbose_name_plural = 'Liquidaciones de comisión'

    def __str__(self):
        return f"{self.vendedor} — ${self.monto_total} [{self.get_estado_display()}]"


class DestinatarioInforme(models.Model):
    """
    Email externo (o usuario del sistema) que recibe informes periódicos
    del municipio (rendiciones, infracciones, recaudación).

    El admin gestiona esta lista desde el tab "Informes" en rendiciones.
    Los destinatarios no necesitan tener acceso al sistema.
    """
    municipio = models.ForeignKey(
        Municipio, on_delete=models.CASCADE,
        related_name="destinatarios_informe",
    )
    nombre = models.CharField(max_length=200, verbose_name="Nombre / cargo")
    correo = models.EmailField(verbose_name="Email")
    activo = models.BooleanField(
        default=True,
        help_text="Desactivar para excluir sin borrar el registro.",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        unique_together = [("municipio", "correo")]
        verbose_name = "Destinatario de informe"
        verbose_name_plural = "Destinatarios de informes"

    def __str__(self):
        return f"{self.nombre} <{self.correo}>"


class ModuloMunicipio(models.Model):
    """
    Módulos de pago que el superadmin activa por municipio.

    Cada municipio puede tener habilitado un subconjunto de módulos.
    Las vistas de cada módulo usan el decorator require_modulo() para
    verificar si el municipio del usuario tiene ese módulo activo.
    """

    MODULOS = [
        ("ocupacion_tiempo_real",   "Ocupación en tiempo real"),
        ("reportes_comparativos",   "Reportes comparativos"),
        ("balance_por_dominio",     "Balance por dominio"),
        ("areas_reservadas",        "Áreas reservadas"),
        ("geolocalizacion_inspector", "Geolocalización del inspector"),
        ("notificaciones_conductor", "Notificaciones al conductor"),
        ("informes_automaticos",    "Informes automáticos programados"),
    ]

    municipio      = models.ForeignKey(
        "Municipio",
        on_delete=models.CASCADE,
        related_name="modulos",
    )
    modulo         = models.CharField(max_length=50, choices=MODULOS)
    activo         = models.BooleanField(default=True)
    precio_mensual = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Precio mensual en pesos que el municipio paga por este módulo.",
    )
    activado_en    = models.DateTimeField(auto_now_add=True)
    activado_por   = models.ForeignKey(
        "Usuario",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="modulos_activados",
        help_text="Superadmin que activó este módulo.",
    )

    class Meta:
        # Un municipio no puede tener el mismo módulo dos veces
        unique_together = [("municipio", "modulo")]
        verbose_name        = "Módulo de municipio"
        verbose_name_plural = "Módulos de municipios"

    def __str__(self):
        return f"{self.municipio} — {self.get_modulo_display()}"


class PlantillaDocumento(models.Model):
    """
    Texto personalizado de comprobantes y actas, configurado por el superadmin
    para cada municipio.

    Cada tipo de documento tiene un encabezado, cuerpo y pie que el superadmin
    puede completar libremente usando {variables} que el sistema interpolará al
    generar el documento.  Si no existe una plantilla para un municipio+tipo,
    el sistema usa sus textos hardcodeados por defecto (sin romper nada).

    Variables disponibles por tipo:
      acta:             {patente} {numero_acta} {fecha} {hora} {subcuadra} {monto} {inspector} {motivo}
      cobro_hora:       {patente} {fecha} {hora_inicio} {hora_fin} {duracion} {monto}
      abono:            {patente} {mes} {anio} {monto} {vendedor}
      cobro_infraccion: {patente} {numero_acta} {monto} {fecha_pago}
      anulacion:        {patente} {numero_acta} {motivo_anulacion}
    """

    TIPOS = [
        ("acta",             "Acta de infracción"),
        ("cobro_hora",       "Comprobante cobro por hora"),
        ("abono",            "Comprobante abono mensual"),
        ("cobro_infraccion", "Comprobante pago de infracción"),
        ("anulacion",        "Comprobante anulación de infracción"),
    ]

    municipio  = models.ForeignKey(
        Municipio, on_delete=models.CASCADE,
        related_name="plantillas_documento",
    )
    tipo       = models.CharField(max_length=20, choices=TIPOS)
    encabezado = models.TextField(
        blank=True,
        verbose_name="Encabezado",
        help_text="Texto que aparece arriba del comprobante. Podés usar variables.",
    )
    cuerpo     = models.TextField(
        blank=True,
        verbose_name="Cuerpo / base legal",
        help_text="Texto principal del comprobante. Podés usar variables.",
    )
    pie        = models.TextField(
        blank=True,
        verbose_name="Pie / instrucciones",
        help_text="Texto que aparece al pie. Podés usar variables.",
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("municipio", "tipo")]
        verbose_name        = "Plantilla de documento"
        verbose_name_plural = "Plantillas de documentos"
        ordering            = ["municipio", "tipo"]

    def __str__(self):
        return f"{self.municipio} — {self.get_tipo_display()}"

    def renderizar(self, variables: dict) -> dict:
        """
        Interpola {variables} en encabezado/cuerpo/pie y devuelve un dict
        con las tres secciones ya renderizadas.

        Usa str.format_map con un dict que devuelve '' para claves faltantes
        (nunca lanza KeyError aunque falte una variable en el contexto).
        """
        class _Fallback(dict):
            def __missing__(self, key):
                return ""

        ctx = _Fallback(variables)
        return {
            "encabezado": self.encabezado.format_map(ctx),
            "cuerpo":     self.cuerpo.format_map(ctx),
            "pie":        self.pie.format_map(ctx),
        }
