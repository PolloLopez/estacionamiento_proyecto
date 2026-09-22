from decimal import Decimal


class SaldoPolicy:

    @staticmethod
    def tiene_saldo(conductor, costo: Decimal, municipio=None):
        """
        Verifica si el conductor tiene saldo suficiente para cubrir el costo.

        Si se provee `municipio`, consulta la BilleteraConductor del municipio.
        Si no, cae en conductor.saldo (legacy, solo para tests sin municipio).
        """
        if municipio is not None:
            from app_estacionamiento.models import BilleteraConductor
            billetera = BilleteraConductor.objects.filter(
                conductor=conductor, municipio=municipio
            ).first()
            saldo_disponible = billetera.saldo if billetera else Decimal("0")
        else:
            saldo_disponible = conductor.saldo
        return saldo_disponible >= costo
