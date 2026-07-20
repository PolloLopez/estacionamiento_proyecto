# app_estacionamiento/services_infracciones.py
# SHIM de compatibilidad — la lógica vive en services/infracciones.py
# Importar desde: from .services.infracciones import crear_infraccion, ErrorInfraccion
from .services.infracciones import crear_infraccion, ErrorInfraccion  # noqa: F401
# Estos imports son necesarios para mantener compatibilidad con el código existente que importa desde este módulo.