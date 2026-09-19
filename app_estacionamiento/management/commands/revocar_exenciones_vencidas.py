"""
Management command: revocar_exenciones_vencidas

Revoca automáticamente las exenciones de vehículos cuya fecha de vigencia ya venció.
Está diseñado principalmente para exenciones SIA/discapacitado, que tienen una
duración de 180 días fija. Las demás exenciones (frentista, jubilado, fuerzas)
generalmente no tienen fecha de vencimiento.

Uso:
    python manage.py revocar_exenciones_vencidas
    python manage.py revocar_exenciones_vencidas --dry-run   # muestra sin modificar

Railway: se puede ejecutar como cron job diario desde el panel de Railway → Cron Jobs,
o como tarea programada en manage.py. El comando es idempotente: si no hay vencidas, no hace nada.
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from app_estacionamiento.models import Vehiculo
from app_estacionamiento.services.notificaciones import enviar_notificacion


class Command(BaseCommand):
    help = "Revoca exenciones de vehículos cuya vigencia venció. Pensado para SIA/discapacitado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra los vehículos afectados sin modificar nada.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        hoy     = date.today()

        # Vehículos exentos (global o parcial) con vigencia vencida
        vencidos = Vehiculo.objects.filter(
            vigencia_exencion__lt=hoy,
        ).filter(
            exento_global=True
        ) | Vehiculo.objects.filter(
            vigencia_exencion__lt=hoy,
        ).filter(
            exento_parcial=True
        )

        # Evitar duplicados por el OR
        vencidos = vencidos.distinct()

        if not vencidos.exists():
            self.stdout.write("✅ Sin exenciones vencidas hoy.")
            return

        self.stdout.write(
            f"{'[DRY RUN] ' if dry_run else ''}Vehículos con exención vencida: {vencidos.count()}"
        )

        for vehiculo in vencidos:
            self.stdout.write(
                f"  → {vehiculo.patente} | tipo: {vehiculo.tipo_exencion} "
                f"| venció: {vehiculo.vigencia_exencion}"
            )

            if dry_run:
                continue

            with transaction.atomic():
                vehiculo.exento_global  = False
                vehiculo.exento_parcial = False
                vehiculo.subcuadras_exentas.clear()
                # Conservamos tipo_exencion y notas para trazabilidad histórica.
                # El admin puede reaprobar si el conductor renueva su documentación.
                vehiculo.save(update_fields=["exento_global", "exento_parcial"])

            # Notificar a cada conductor vinculado al vehículo
            for vinculo in vehiculo.vehiculousuario_set.select_related("usuario"):
                conductor = vinculo.usuario
                enviar_notificacion(
                    destinatario=conductor,
                    mensaje=(
                        f"⚠️ La exención del vehículo {vehiculo.patente} venció el "
                        f"{vehiculo.vigencia_exencion.strftime('%d/%m/%Y')}. "
                        "Contactá al municipio para renovarla."
                    ),
                    tipo="exencion",
                )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {vencidos.count()} exención(es) revocadas. "
                    "Los conductores afectados fueron notificados."
                )
            )
