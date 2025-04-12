"""App Configuration"""

# Django
from django.apps import AppConfig

# BlueprintLibrary
# AA Example App
from BlueprintLibrary import __version__


class BlueprintLibraryConfig(AppConfig):
    """App Config"""

    name = "BlueprintLibrary"
    label = "BlueprintLibrary"
    verbose_name = f"BlueprintLibrary App v{__version__}"
