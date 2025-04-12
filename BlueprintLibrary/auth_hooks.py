# Third Party
# Importation des urls du module
# Third Party
import blueprints.urls

# Alliance Auth
from allianceauth import hooks
from allianceauth.menu import hooks as menu_hooks
from allianceauth.services.hooks import UrlHook


@hooks.register("url_hook")
def register_blueprints_urls():
    """Enregistre les URLs de l'app Blueprints dans Alliance Auth."""
    # Inclut les URLs du module sous le préfixe 'blueprints/'
    return UrlHook(blueprints.urls, "blueprints", r"^blueprints/")


@hooks.register("menu_hook")
def register_blueprints_menu():
    """Ajoute un élément de menu pour le module Blueprints dans le menu latéral."""
    # Icône FontAwesome (par ex: 'fa-book' pour symboliser un blueprint)
    return menu_hooks.MenuItemHook(
        # Texte du menu
        "Blueprints",
        # Classes CSS de l'icône du menu (utilise FontAwesome 5+ via BS5)
        "fas fa-scroll fa-fw",  # exemple d'icône (rouleau de parchemin)
        # Nom de l'URL à utiliser pour ce menu (vue index de Blueprints)
        "blueprints:library",
        # Ordre d'affichage du menu ( >1000 pour ne pas empiéter sur le core Auth)
        order=1000,
    )
