# manage.py
import os
import sys

def main():
    """Punto de entrada a la app estacionamiento"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitio.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Está instalado y en el entorno virtual?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
