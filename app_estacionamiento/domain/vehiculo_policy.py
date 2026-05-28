class VehiculoPolicy:

    @staticmethod
    def generar_warnings(usuario, vehiculo, relaciones):

        warnings = []

        if relaciones.filter(es_propietario=True).exists() and not relaciones.filter(usuario=usuario, es_propietario=True).exists():
            warnings.append("🚨 Otro propietario registrado")

        if relaciones.exclude(usuario=usuario).exists():
            warnings.append("⚠️ Múltiples usuarios asociados")

        relacion = relaciones.filter(usuario=usuario).first()

        if relacion and not relacion.verificado:
            warnings.append("⛔ Usuario no verificado")

        return warnings