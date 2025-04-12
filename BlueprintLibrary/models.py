# Django
from django.contrib.auth.models import User
from django.db import models

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter

# Alliance Auth (External Libs)
from eveuniverse.models import (
    EveType,  # EveUniverse: types d'objets EVE (blueprint types)
)


class BlueprintOwner(models.Model):
    """Propriétaire de blueprints (personnage ou corporation) suivi par le module."""

    character = models.ForeignKey(
        EveCharacter,
        on_delete=models.CASCADE,
        help_text="Personnage EVE utilisé pour récupérer les données",
    )
    corporation_id = models.BigIntegerField(
        null=True, blank=True, help_text="ID EVE de la corporation (si corporate)"
    )
    is_corporation = models.BooleanField(
        default=False, help_text="True si ce propriétaire est une corporation"
    )

    def __str__(self):
        if self.is_corporation:
            # Nom de la corporation via le personnage (EveCharacter stocke corp_name)
            return f"Corp: {self.character.corporation_name}"
        else:
            return f"Perso: {self.character.character_name}"

    class Meta:
        verbose_name = "Propriétaire de Blueprint"
        verbose_name_plural = "Propriétaires de Blueprints"
        # Permissions personnalisées du module
        permissions = [
            ("basic_access", "Peut accéder à l'application Blueprints"),
            ("request_blueprints", "Peut faire des demandes de blueprint"),
            (
                "manage_requests",
                "Peut gérer (approuver/refuser) les demandes de blueprint",
            ),
            ("add_personal_blueprint_owner", "Peut ajouter ses plans personnels"),
            (
                "add_corporate_blueprint_owner",
                "Peut ajouter les plans de sa corporation",
            ),
            ("view_alliance_blueprints", "Peut voir les plans de toute l'alliance"),
            ("view_industry_jobs", "Peut voir tous les travaux d'industrie en cours"),
        ]


class Blueprint(models.Model):
    """Blueprint EVE détenu par un propriétaire (personnage ou corporation)."""

    owner = models.ForeignKey(
        BlueprintOwner, on_delete=models.CASCADE, related_name="blueprints"
    )
    item_id = models.BigIntegerField(
        help_text="Identifiant unique de l'item blueprint dans EVE"
    )
    eve_type = models.ForeignKey(
        EveType, on_delete=models.CASCADE, help_text="Type EVE du blueprint"
    )
    quantity = models.IntegerField(
        help_text="Quantité (ESI: -1 original, -2 copie, >0 pile d'originaux)"
    )
    time_efficiency = models.PositiveSmallIntegerField(
        help_text="Efficacité temporelle (TE %)"
    )
    material_efficiency = models.PositiveSmallIntegerField(
        help_text="Efficacité matérielle (ME %)"
    )
    runs = models.IntegerField(
        help_text="Nombre de runs restant (ou -1 si BPO original à runs infinis)"
    )
    location_id = models.BigIntegerField(
        help_text="ID de l'emplacement (station, structure ou conteneur)"
    )
    location_flag = models.CharField(
        max_length=50, help_text="Flag d'emplacement (ex: CorpSAG1, PersonalHangar)"
    )

    def __str__(self):
        return f"{self.eve_type.name} ({'BPO' if self.is_original else 'BPC'})"

    @property
    def is_original(self):
        """Indique si le blueprint est un original (BPO) ou une copie."""
        return self.runs == -1 or self.quantity == -1

    @property
    def location_name(self):
        """Nom de l'emplacement du blueprint (si connu)."""
        # On tente de résoudre via EveUniverse (stations) ou table interne des structures
        name = None
        # EveUniverse peut connaître certaines stations par type d'entité:
        # Alliance Auth (External Libs)
        from eveuniverse.models import EveEntity

        try:
            entity = EveEntity.objects.get(id=self.location_id)
            name = entity.name
        except EveEntity.DoesNotExist:
            # Pas trouvé dans EveUniverse (peut être une structure joueur)
            try:
                loc = BlueprintLocation.objects.get(id=self.location_id)
                name = loc.name
            except Exception:
                name = str(self.location_id)
        return name or str(self.location_id)

    class Meta:
        unique_together = [
            ("owner", "item_id")
        ]  # Un item blueprint unique par propriétaire
        verbose_name = "Blueprint"
        verbose_name_plural = "Blueprints"


class BlueprintRequest(models.Model):
    """Demande utilisateur pour obtenir une copie de blueprint."""

    requested_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="blueprint_requests"
    )
    blueprint_type = models.ForeignKey(
        EveType, on_delete=models.CASCADE, help_text="Type de blueprint demandé"
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = [
        ("open", "Ouverte"),
        ("approved", "Approuvée"),
        ("denied", "Refusée"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    # Optionnellement, on pourrait ajouter un champ 'notes' ou 'reason' pour justifier refus, etc.

    def __str__(self):
        return f"Demande de {self.blueprint_type.name} par {self.requested_by.username} [{self.status}]"

    class Meta:
        verbose_name = "Demande de Blueprint"
        verbose_name_plural = "Demandes de Blueprints"


class IndustryJob(models.Model):
    """Job industriel en cours lié aux blueprints (par ex: copie, invention, production)."""

    owner = models.ForeignKey(
        BlueprintOwner, on_delete=models.CASCADE, related_name="industry_jobs"
    )
    job_id = models.BigIntegerField(
        unique=True, help_text="Identifiant du job d'industrie EVE"
    )
    activity = models.CharField(
        max_length=50, help_text="Type d'activité (manufacture, copy, invent, etc.)"
    )
    status = models.CharField(
        max_length=50, help_text="Statut du job (active, paused, finished, etc.)"
    )
    blueprint = models.ForeignKey(
        Blueprint,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Blueprint lié au job si disponible",
    )
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    # On peut ajouter d'autres champs si nécessaires (ex: produit fabriqué, runs, etc.)

    def __str__(self):
        return f"Job {self.job_id} ({self.activity}) - {self.status}"

    class Meta:
        verbose_name = "Job Industriel"
        verbose_name_plural = "Jobs Industriels"


# Modèle auxiliaire pour stocker les noms des emplacements (structures)
class BlueprintLocation(models.Model):
    """Emplacement connu d'un blueprint (station NPC ou structure joueur)"""

    id = models.BigIntegerField(primary_key=True)  # l'ID de la station/structure
    name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=50, help_text="Type d'emplacement: Station, Structure, etc."
    )

    def __str__(self):
        return f"[{self.category}] {self.name}"
