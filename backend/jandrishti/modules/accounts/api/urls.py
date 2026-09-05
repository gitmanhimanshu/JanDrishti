from django.urls import path

from .views import (
    MeView,
    ProfessionalProfileView,
    PublicProfileView,
    SelectUserTypeView,
)

app_name = "accounts"

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("me/user-type/", SelectUserTypeView.as_view(), name="select-user-type"),
    path(
        "me/professional-profile/", ProfessionalProfileView.as_view(), name="professional-profile"
    ),
    path("<uuid:user_id>/", PublicProfileView.as_view(), name="public-profile"),
]
