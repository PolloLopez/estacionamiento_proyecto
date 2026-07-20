# app_estacionamiento/services_caja.py
# SHIM de compatibilidad — la lógica vive en services/caja.py
# Importar desde: from .services.caja import generar_cierre_caja
from .services.caja import generar_cierre_caja  # noqa: F401
