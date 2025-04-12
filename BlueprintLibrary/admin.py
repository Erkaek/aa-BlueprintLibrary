# Django
from django.contrib import admin

from .models import Blueprint, BlueprintOwner, BlueprintRequest, IndustryJob


@admin.register(BlueprintOwner)
class BlueprintOwnerAdmin(admin.ModelAdmin):
    list_display = ("__str__", "is_corporation", "character", "corporation_id")
    list_filter = ("is_corporation",)
    search_fields = ("character__character_name", "character__corporation_name")


@admin.register(Blueprint)
class BlueprintAdmin(admin.ModelAdmin):
    list_display = (
        "eve_type",
        "owner",
        "is_original",
        "runs",
        "material_efficiency",
        "time_efficiency",
        "location_id",
    )
    list_filter = ("owner__is_corporation", "material_efficiency", "time_efficiency")
    search_fields = (
        "eve_type__name",
        "owner__character__character_name",
        "owner__character__corporation_name",
    )


@admin.register(BlueprintRequest)
class BlueprintRequestAdmin(admin.ModelAdmin):
    list_display = ("blueprint_type", "requested_by", "status", "requested_at")
    list_filter = ("status",)
    search_fields = ("blueprint_type__name", "requested_by__username")


@admin.register(IndustryJob)
class IndustryJobAdmin(admin.ModelAdmin):
    list_display = (
        "job_id",
        "activity",
        "status",
        "owner",
        "blueprint",
        "start_date",
        "end_date",
    )
    list_filter = ("activity", "status")
    search_fields = (
        "job_id",
        "owner__character__character_name",
        "owner__character__corporation_name",
    )
