"""
Helper script to ensure all backend apps have __init__.py, apps.py, and urls.py
"""
import os

apps_dir = os.path.join("backend", "apps")
for app in os.listdir(apps_dir):
    p = os.path.join(apps_dir, app)
    if not os.path.isdir(p) or app.startswith("__"):
        continue

    init_f = os.path.join(p, "__init__.py")
    if not os.path.exists(init_f):
        with open(init_f, "w", encoding="utf-8") as f:
            f.write(f'"""SIH26002 — {app} app init."""\n')

    apps_f = os.path.join(p, "apps.py")
    if not os.path.exists(apps_f):
        class_name = "".join(word.capitalize() for word in app.split("_")) + "Config"
        title = app.replace("_", " ").title()
        with open(apps_f, "w", encoding="utf-8") as f:
            f.write(
                f'from django.apps import AppConfig\n\n'
                f'class {class_name}(AppConfig):\n'
                f'    default_auto_field = "django.db.models.BigAutoField"\n'
                f'    name = "apps.{app}"\n'
                f'    verbose_name = "{title}"\n'
            )

    urls_f = os.path.join(p, "urls.py")
    if not os.path.exists(urls_f):
        with open(urls_f, "w", encoding="utf-8") as f:
            f.write(
                f'"""SIH26002 — {app} URLs."""\n'
                f'from django.urls import path\n\n'
                f'urlpatterns = []\n'
            )

print("Scaffolded remaining backend apps successfully.")
