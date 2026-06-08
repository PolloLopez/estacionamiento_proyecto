from django.template import loader
from pathlib import Path

templates = Path("templates").rglob("*.html")

errors = 0

for t in templates:
    try:
        loader.get_template(
            str(t)
            .replace("\\", "/")
            .replace("templates/", "")
        )

        print(f"OK: {t}")

    except Exception as e:
        errors += 1

        print(f"\nERROR: {t}")
        print(e)
        print("-" * 50)

print(f"\nTemplates con errores: {errors}")