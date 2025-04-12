# Third Party
from datatables.views import DatatablesView  # classe utilitaire pour DataTables

# Django
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from .forms import BlueprintRequestForm
from .models import Blueprint, BlueprintRequest, IndustryJob


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("blueprints.basic_access", raise_exception=True),
    name="dispatch",
)
class LibraryView(TemplateView):
    """Vue principale affichant la bibliothèque de blueprints."""

    template_name = "blueprints/library.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Filtrer les blueprints affichés selon permissions:
        user = self.request.user
        if user.has_perm("blueprints.view_alliance_blueprints"):
            # Affiche tous les blueprints (toute l'alliance)
            bps = Blueprint.objects.select_related("eve_type", "owner").all()
        else:
            # Sinon, limite aux blueprints de la corp de l'utilisateur (ou de ses persos)
            corp_ids = set()
            char_ids = set()
            # Récupère les corp IDs de tous les persos de l'utilisateur
            for (
                char
            ) in user.profile.characters.all():  # user.profile.characters via AA core
                corp_ids.add(char.corporation_id)
                char_ids.add(char.character_id)
            # Filtre: blueprints dont owner est perso de l'utilisateur ou corp de l'utilisateur
            bps = Blueprint.objects.select_related("eve_type", "owner").filter(
                (Q(owner__is_corporation=True) & Q(owner__corporation_id__in=corp_ids))
                | (
                    Q(owner__is_corporation=False)
                    & Q(owner__character__character_id__in=char_ids)
                )
            )
        context["blueprint_count"] = bps.count()
        # La liste détaillée est chargée via DataTables en JS, on n'injecte ici que le compte et autres infos éventuelles.
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("blueprints.basic_access", raise_exception=True),
    name="dispatch",
)
class BlueprintDataView(DatatablesView):
    """Retourne les données JSON pour la table des blueprints (utilisé par DataTables en AJAX)."""

    model = Blueprint
    # Colonnes à retourner (définir les noms correspondant aux champs ou annotations)
    columns = [
        "eve_type.name",
        "runs",
        "material_efficiency",
        "time_efficiency",
        "location_name",
    ]
    # Colonnes qui peuvent être triées (même liste ici)
    order_columns = [
        "eve_type.name",
        "runs",
        "material_efficiency",
        "time_efficiency",
        "location_name",
    ]

    def get_initial_queryset(self, request=None):
        user = self.request.user
        # Filtre de base identique à LibraryView
        if user.has_perm("blueprints.view_alliance_blueprints"):
            qs = Blueprint.objects.select_related("eve_type", "owner").all()
        else:
            corp_ids = {char.corporation_id for char in user.profile.characters.all()}
            char_ids = {char.character_id for char in user.profile.characters.all()}
            qs = Blueprint.objects.select_related("eve_type", "owner").filter(
                (Q(owner__is_corporation=True) & Q(owner__corporation_id__in=corp_ids))
                | (
                    Q(owner__is_corporation=False)
                    & Q(owner__character__character_id__in=char_ids)
                )
            )
        return qs

    def filter_queryset(self, qs):
        # Applique le filtre de recherche global de DataTables
        search = self.request.GET.get("search[value]", None)
        if search:
            qs = qs.filter(
                Q(eve_type__name__icontains=search) | Q(location_id__icontains=search)
            )
        return qs


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("blueprints.basic_access", raise_exception=True),
    name="dispatch",
)
class BlueprintDetailView(DetailView):
    """Vue détaillée pour un blueprint spécifique."""

    model = Blueprint
    template_name = "blueprints/blueprint_detail.html"
    context_object_name = "blueprint"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bp = self.object
        # Si user a la permission, on ajoute les jobs liés (via item_id du blueprint)
        user = self.request.user
        if user.has_perm("blueprints.view_industry_jobs"):
            jobs = IndustryJob.objects.filter(blueprint=bp)
            context["industry_jobs"] = jobs
        # Indiquer si l'utilisateur peut faire une requête sur ce blueprint
        context["can_request"] = user.has_perm("blueprints.request_blueprints")
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("blueprints.request_blueprints", raise_exception=True),
    name="dispatch",
)
class CreateRequestView(FormView):
    """Formulaire de création d'une demande de blueprint."""

    form_class = BlueprintRequestForm
    template_name = "blueprints/create_request.html"
    success_url = reverse_lazy("blueprints:my_requests")

    def form_valid(self, form):
        # Attache l'utilisateur et enregistre la demande
        request_obj = form.save(commit=False)
        request_obj.requested_by = self.request.user
        request_obj.status = "open"
        request_obj.save()
        # On pourrait émettre ici une notification interne informant les managers d'une nouvelle demande.
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("blueprints.basic_access", raise_exception=True),
    name="dispatch",
)
class MyRequestsView(ListView):
    """Liste des demandes de blueprint de l'utilisateur courant."""

    model = BlueprintRequest
    template_name = "blueprints/my_requests.html"
    context_object_name = "requests"

    def get_queryset(self):
        return BlueprintRequest.objects.filter(requested_by=self.request.user).order_by(
            "-requested_at"
        )


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("blueprints.manage_requests", raise_exception=True),
    name="dispatch",
)
class OpenRequestsView(ListView):
    """Liste des demandes de blueprint ouvertes (pour les gestionnaires)."""

    model = BlueprintRequest
    template_name = "blueprints/open_requests.html"
    context_object_name = "open_requests"

    def get_queryset(self):
        return BlueprintRequest.objects.filter(status="open").order_by("requested_at")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("blueprints.manage_requests", raise_exception=True),
    name="dispatch",
)
class ProcessRequestView(View):
    """Vue pour traiter une demande (approbation ou refus)."""

    def post(self, request, *args, **kwargs):
        req_id = kwargs.get("pk")
        action = request.POST.get("action")  # 'approve' ou 'deny'
        req = get_object_or_404(BlueprintRequest, pk=req_id)
        if req.status != "open":
            # Déjà traitée
            return redirect("blueprints:open_requests")
        if action == "approve":
            req.status = "approved"
            # (Éventuellement, notifier le demandeur de l'approbation ici)
        elif action == "deny":
            req.status = "denied"
            # (On pourrait stocker une raison de refus si le formulaire la fournissait)
        req.save()
        # Redirige vers la liste des demandes ouvertes
        return redirect("blueprints:open_requests")
