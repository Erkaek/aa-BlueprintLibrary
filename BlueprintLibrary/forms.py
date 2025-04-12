# Django
from django import forms

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter

from .models import BlueprintOwner, BlueprintRequest


class BlueprintOwnerForm(forms.ModelForm):
    """Formulaire pour ajouter un propriétaire de blueprints (perso ou corp)."""

    # Champ pour choisir un de ses personnages existants
    character = forms.ModelChoiceField(
        queryset=None,
        label="Personnage EVE",
        help_text="Choisissez l'un de vos personnages pour ajouter ses plans.",
    )
    add_corporation = forms.BooleanField(
        required=False,
        label="Ajouter la corporation de ce personnage",
        help_text="Cocher si vous voulez ajouter les plans de la corporation (nécessite d'être DG/CEO).",
    )

    class Meta:
        model = BlueprintOwner
        fields = ["character"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop(
            "user"
        )  # on passe l'utilisateur dans la vue lors de l'instanciation
        super().__init__(*args, **kwargs)
        # Restreint la liste des personnages à ceux de l'utilisateur courant
        self.fields["character"].queryset = EveCharacter.objects.filter(user=user)
        # On désactive la validation unique auto pour pouvoir gérer nous-mêmes la logique corp/perso
        self._validate_unique = False

    def clean(self):
        cleaned_data = super().clean()
        char = cleaned_data.get("character")
        add_corp = cleaned_data.get("add_corporation")
        if char:
            if add_corp:
                # Vérifie qu'il n'y a pas déjà un BlueprintOwner corp pour cette corp
                corp_id = char.corporation_id
                exists = BlueprintOwner.objects.filter(
                    is_corporation=True, corporation_id=corp_id
                ).exists()
                if exists:
                    raise forms.ValidationError(
                        "Les plans de cette corporation sont déjà suivis."
                    )
            else:
                # Vérifie que le perso n'existe pas déjà comme propriétaire perso
                exists = BlueprintOwner.objects.filter(
                    is_corporation=False, character=char
                ).exists()
                if exists:
                    raise forms.ValidationError(
                        "Les plans de ce personnage sont déjà ajoutés."
                    )
        return cleaned_data

    def save(self, commit=True):
        char = self.cleaned_data["character"]
        add_corp = self.cleaned_data.get("add_corporation", False)
        owner = BlueprintOwner(character=char)
        if add_corp:
            owner.is_corporation = True
            owner.corporation_id = char.corporation_id
        else:
            owner.is_corporation = False
            owner.corporation_id = None
        if commit:
            owner.save()
        return owner


class BlueprintRequestForm(forms.ModelForm):
    """Formulaire pour faire une demande de copie de blueprint."""

    class Meta:
        model = BlueprintRequest
        fields = ["blueprint_type"]
        labels = {"blueprint_type": "Blueprint désiré"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On peut filtrer les choix de blueprint_type si besoin (par ex. seulement les BPO disponibles)
        # Ici on laisse tous les types pour simplicité.
        self.fields["blueprint_type"].queryset = self.fields[
            "blueprint_type"
        ].queryset.order_by("name")
