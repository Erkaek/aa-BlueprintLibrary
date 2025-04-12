# Django
from django.apps import AppConfig


class BlueprintsConfig(AppConfig):
    """Configuration de l'application Blueprints pour Alliance Auth."""

    name = "blueprints"
    label = "blueprints"
    verbose_name = "Blueprints"

    # Django 3.2+ : champ auto par défaut pour les clés primaires
    default_auto_field = "django.db.models.AutoField"
