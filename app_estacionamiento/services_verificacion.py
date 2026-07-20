# app_estacionamiento/services_verificacion.py
# SHIM de compatibilidad — la lógica vive en services/verificacion.py
# Importar desde: from .services.verificacion import verificar_estado_vehiculo
from .services.verificacion import verificar_estado_vehiculo  # noqa: F401
# Estos imports son necesarios para mantener compatibilidad con el código existente que importa desde este módulo.