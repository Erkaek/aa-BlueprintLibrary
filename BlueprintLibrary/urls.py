# Django
from django.urls import path

from . import views

app_name = "blueprints"

urlpatterns = [
    # Vue principale listant les blueprints
    path("", views.LibraryView.as_view(), name="library"),
    # Endpoint pour les données AJAX de la datatable
    path("data/", views.BlueprintDataView.as_view(), name="data"),
    # Détails d'un blueprint (pk = identifiant du blueprint en base)
    path("blueprint/<int:pk>/", views.BlueprintDetailView.as_view(), name="detail"),
    # Création d'une demande (formulaire)
    path("requests/new/", views.CreateRequestView.as_view(), name="create_request"),
    # Mes demandes
    path("requests/mine/", views.MyRequestsView.as_view(), name="my_requests"),
    # Demandes ouvertes à traiter (gestionnaires)
    path("requests/open/", views.OpenRequestsView.as_view(), name="open_requests"),
    # Action d'approbation/refus sur une demande (POST)
    path(
        "requests/<int:pk>/process/",
        views.ProcessRequestView.as_view(),
        name="process_request",
    ),
]
