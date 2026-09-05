from django.urls import path

from .views import (
    ProblemCreateView,
    ProblemDetailView,
    ProblemEvidenceView,
    ProblemListView,
    ProblemResponseView,
    ProblemSupportView,
    ProblemTabsView,
)

app_name = "problems"

urlpatterns = [
    path("", ProblemListView.as_view(), name="list"),
    path("create/", ProblemCreateView.as_view(), name="create"),
    path("tabs/", ProblemTabsView.as_view(), name="tabs"),
    path("<uuid:problem_id>/", ProblemDetailView.as_view(), name="detail"),
    path("<uuid:problem_id>/support/", ProblemSupportView.as_view(), name="support"),
    path("<uuid:problem_id>/evidence/", ProblemEvidenceView.as_view(), name="evidence"),
    path("<uuid:problem_id>/responses/", ProblemResponseView.as_view(), name="responses"),
]
