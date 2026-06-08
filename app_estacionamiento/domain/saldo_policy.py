from decimal import Decimal

class SaldoPolicy:

    @staticmethod
    def tiene_saldo(usuario, costo: Decimal):
        return usuario.saldo >= costo