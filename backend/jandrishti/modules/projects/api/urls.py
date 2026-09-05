from django.urls import path

from .views import (
    ProjectCreateView,
    ProjectDetailView,
    ProjectListView,
    ProjectStatusView,
    ProjectUpdateView,
)

app_name = "projects"

urlpatterns = [
    path("", ProjectListView.as_view(), name="list"),
    path("create/", ProjectCreateView.as_view(), name="create"),
    path("<uuid:project_id>/", ProjectDetailView.as_view(), name="detail"),
    path("<uuid:project_id>/updates/", ProjectUpdateView.as_view(), name="update"),
    path("<uuid:project_id>/status/", ProjectStatusView.as_view(), name="status"),
]
