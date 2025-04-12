"""App URLs"""

# Django
from django.urls import path

# BlueprintLibrary
# AA Example App
from BlueprintLibrary import views

app_name: str = "BlueprintLibrary"

urlpatterns = [
    path("", views.index, name="index"),
]
