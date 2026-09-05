from django.urls import path

from .views import (
    AssignProblemView,
    DashboardSummaryView,
    GovernmentProblemListView,
    UpdateProblemStatusView,
)

app_name = "government"

urlpatterns = [
    path("dashboard/", DashboardSummaryView.as_view(), name="dashboard"),
    path("problems/", GovernmentProblemListView.as_view(), name="problems"),
    path("problems/<uuid:problem_id>/status/", UpdateProblemStatusView.as_view(), name="status"),
    path("problems/<uuid:problem_id>/assign/", AssignProblemView.as_view(), name="assign"),
]
