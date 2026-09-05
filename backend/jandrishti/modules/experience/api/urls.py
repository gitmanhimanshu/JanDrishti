from django.urls import path

from .views import (
    ExperienceCreateView,
    ExperienceDetailView,
    ExperienceLinkProblemView,
    ExperienceListView,
    ExperienceSupportView,
    ProblemRelatedExperiencesView,
)

app_name = "experience"

urlpatterns = [
    path("", ExperienceListView.as_view(), name="list"),
    path("create/", ExperienceCreateView.as_view(), name="create"),
    path(
        "for-problem/<uuid:problem_id>/",
        ProblemRelatedExperiencesView.as_view(),
        name="for-problem",
    ),
    path("<uuid:experience_id>/", ExperienceDetailView.as_view(), name="detail"),
    path("<uuid:experience_id>/support/", ExperienceSupportView.as_view(), name="support"),
    path(
        "<uuid:experience_id>/link-problem/",
        ExperienceLinkProblemView.as_view(),
        name="link-problem",
    ),
]
