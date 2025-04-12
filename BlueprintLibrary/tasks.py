# Third Party
import requests
from celery import shared_task

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter

# Alliance Auth (External Libs)
from eveuniverse.models import EveEntity, EveType

from .models import Blueprint, BlueprintLocation, BlueprintOwner, IndustryJob

ESI_BASE_URL = "https://esi.evetech.net/latest"


@shared_task
def update_all_blueprints():
    """Met à jour la liste de tous les blueprints pour l'ensemble des propriétaires."""
    for owner in BlueprintOwner.objects.all():
        try:
            # Récupération du token ESI via le personnage associé
            eve_char = owner.character
            token = (
                eve_char.fetch_token()
            )  # Méthode hypothétique pour obtenir le token ESI du perso
        except Exception:
            continue  # personnage sans token valide, on passe

        # Choix de l’endpoint selon perso ou corp
        if owner.is_corporation:
            corp_id = owner.corporation_id
            url = f"{ESI_BASE_URL}/corporations/{corp_id}/blueprints/"
            headers = {"Authorization": f"Bearer {token.access_token}"}
        else:
            char_id = owner.character.character_id
            url = f"{ESI_BASE_URL}/characters/{char_id}/blueprints/"
            headers = {"Authorization": f"Bearer {token.access_token}"}

        # Appel API (on suppose un seul appel, pagination à gérer en pratique)
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            continue  # en cas d'erreur API, on saute ce propriétaire
        data = response.json()
        # data est une liste de blueprints (dictionnaires)
        seen_item_ids = []
        for bp in data:
            seen_item_ids.append(bp["item_id"])
            # Cherche le type EVE (EveType) correspondant
            type_id = bp["type_id"]
            eve_type, _ = EveType.objects.get_or_create(
                id=type_id, defaults={"name": f"Type {type_id}"}
            )
            # Localisation : station ou structure
            loc_id = bp.get("location_id")
            loc_flag = bp.get("location_flag")
            # Création ou mise à jour du blueprint
            blueprint_obj, created = Blueprint.objects.update_or_create(
                owner=owner,
                item_id=bp["item_id"],
                defaults={
                    "eve_type": eve_type,
                    "quantity": bp.get("quantity", 0),
                    "time_efficiency": bp.get("time_efficiency", 0),
                    "material_efficiency": bp.get("material_efficiency", 0),
                    "runs": bp.get("runs", -1),
                    "location_id": loc_id,
                    "location_flag": loc_flag,
                },
            )
            # Marque les structures pour résolution de nom ultérieure si non connue
            if loc_id and loc_flag and loc_id not in (None, 0):
                # Si l'emplacement semble être une structure joueur (ex: flag contient "CorpSAG" ou autre,
                # et loc_id pas dans EveEntity), on l'enregistrera pour résolution
                if not EveEntity.objects.filter(id=loc_id).exists():
                    BlueprintLocation.objects.get_or_create(
                        id=loc_id, defaults={"name": "", "category": "Structure"}
                    )
        # Supprime les blueprints qui n'existent plus pour ce owner (non reçus dans data)
        Blueprint.objects.filter(owner=owner).exclude(
            item_id__in=seen_item_ids
        ).delete()
    # Fin de la tâche: on pourrait logguer l'achèvement ou le nombre de BPs mis à jour.


@shared_task
def update_all_industry_jobs():
    """Met à jour la liste de tous les jobs d'industrie pour chaque propriétaire."""
    for owner in BlueprintOwner.objects.all():
        try:
            eve_char = owner.character
            token = eve_char.fetch_token()
        except Exception:
            continue
        if owner.is_corporation:
            corp_id = owner.corporation_id
            url = f"{ESI_BASE_URL}/corporations/{corp_id}/industry/jobs/?include_completed=false"
            headers = {"Authorization": f"Bearer {token.access_token}"}
        else:
            char_id = owner.character.character_id
            url = f"{ESI_BASE_URL}/characters/{char_id}/industry/jobs/?include_completed=false"
            headers = {"Authorization": f"Bearer {token.access_token}"}
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            continue
        jobs_data = response.json()
        current_job_ids = []
        for job in jobs_data:
            current_job_ids.append(job["job_id"])
            # Determine blueprint instance si possible
            bp_item_id = job.get("blueprint_id")
            bp_instance = None
            if bp_item_id:
                try:
                    bp_instance = Blueprint.objects.get(owner=owner, item_id=bp_item_id)
                except Blueprint.DoesNotExist:
                    bp_instance = None
            IndustryJob.objects.update_or_create(
                job_id=job["job_id"],
                defaults={
                    "owner": owner,
                    "activity": job.get(
                        "activity_name", str(job.get("activity_id", ""))
                    ),
                    "status": job.get("status", "active"),
                    "blueprint": bp_instance,
                    "start_date": job.get("start_date"),
                    "end_date": job.get("end_date"),
                },
            )
        # Supprimer les jobs qui ne sont plus actifs (plus présents)
        IndustryJob.objects.filter(owner=owner).exclude(
            job_id__in=current_job_ids
        ).delete()


@shared_task
def update_all_locations():
    """Résout les noms des emplacements (structures) pour tous les IDs non résolus."""
    # On récupère tous les BlueprintLocation sans nom connu
    to_resolve = BlueprintLocation.objects.filter(name__exact="")
    if not to_resolve:
        return
    ids = [loc.id for loc in to_resolve]
    # L'ESI /universe/names peut résoudre certains IDs en nom (stations, systèmes, etc.), mais pour les structures privées,
    # il faut /universe/structures/{id} avec jeton. Ici, on tente l'approche générale:
    try:
        response = requests.post(
            f"{ESI_BASE_URL}/universe/names/", json=ids, timeout=30
        )
        if response.status_code == 200:
            results = response.json()
        else:
            results = []
    except Exception:
        results = []
    # results devrait contenir des dict avec {"id": ..., "name": ..., "category": ...}
    for entry in results:
        loc_id = entry.get("id")
        name = entry.get("name", "")
        category = entry.get("category", "")
        BlueprintLocation.objects.filter(id=loc_id).update(name=name, category=category)
    # Pour les IDs non résolus par universe/names (typiquement les structures Upwell privées),
    # il faudrait appeler /universe/structures/{id} individuellement avec un token possédant le scope.
    # On parcourt encore ceux sans nom:
    unresolved = BlueprintLocation.objects.filter(name__exact="")
    if unresolved.exists():
        # On utilise un token (ex: le premier directeur dispo) pour résoudre chaque structure
        # (Simplification: on prend le premier personnage ayant scope structure)
        try:
            any_char = EveCharacter.objects.filter(roles__icontains="Director")[0]
            token = any_char.fetch_token()
        except Exception:
            token = None
        if token:
            for loc in unresolved:
                struct_url = f"{ESI_BASE_URL}/universe/structures/{loc.id}/"
                res = requests.get(
                    struct_url,
                    headers={"Authorization": f"Bearer {token.access_token}"},
                )
                if res.status_code == 200:
                    struct_data = res.json()
                    loc.name = struct_data.get("name", f"Structure {loc.id}")
                    loc.category = "Structure"
                    loc.save()
